import os
import io
import time
import base64
import json
import webview
import mss
import tkinter as tk
from pathlib import Path
from PIL import Image

from config import PipelineConfig
from detector import OpenCVBubbleDetector
from ocr import GeminiVisionOCR
from translator import ComicTranslator
from inpaint import BubbleInpainter
from typeset import ArabicTypesetter

config = PipelineConfig()

class SnippingTool:
    """Lightweight overlay to select an area of the screen with mouse drag."""
    def __init__(self):
        self.root = None
        self.start_x = None
        self.start_y = None
        self.cur_x = None
        self.cur_y = None
        self.rect = None
        self.selected_bbox = None

    def select_screen_region(self):
        self.root = tk.Tk()
        self.root.attributes("-alpha", 0.28)
        self.root.attributes("-fullscreen", True)
        self.root.config(cursor="cross")
        self.root.attributes("-topmost", True)

        self.canvas = tk.Canvas(self.root, cursor="cross", bg="grey")
        self.canvas.pack(fill="both", expand=True)

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Escape>", lambda e: self.root.destroy())

        self.root.mainloop()
        return self.selected_bbox

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline="red", width=2, fill="white")

    def on_drag(self, event):
        self.cur_x, self.cur_y = (event.x, event.y)
        self.canvas.coords(self.rect, self.start_x, self.start_y, self.cur_x, self.cur_y)

    def on_release(self, event):
        x1 = min(self.start_x, event.x)
        y1 = min(self.start_y, event.y)
        x2 = max(self.start_x, event.x)
        y2 = max(self.start_y, event.y)
        if (x2 - x1) > 20 and (y2 - y1) > 20:
            self.selected_bbox = (x1, y1, x2, y2)
        self.root.destroy()

class DesktopApi:
    def __init__(self):
        self.current_orig_img: Image.Image | None = None
        self.current_trans_img: Image.Image | None = None
        self.current_filename = "capture.png"

    def capture_screen_area(self) -> dict:
        """Minimizes/hides or overlays to capture a region selected by the user."""
        try:
            # Let the user select the area
            snipper = SnippingTool()
            bbox = snipper.select_screen_region()

            if not bbox:
                return {"status": "cancelled", "message": "تم إلغاء التحديد"}

            x1, y1, x2, y2 = bbox
            with mss.mss() as sct:
                monitor = {"top": y1, "left": x1, "width": x2 - x1, "height": y2 - y1}
                sct_img = sct.grab(monitor)
                self.current_orig_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                self.current_filename = f"capture_{int(time.time())}.png"

            # Convert to base64 for preview
            buf = io.BytesIO()
            self.current_orig_img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            return {
                "status": "ok",
                "image": f"data:image/png;base64,{img_b64}",
                "message": f"تم التقاط المنطقة ({x2-x1}x{y2-y1})"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def capture_fullscreen(self) -> dict:
        """Instant capture of the entire primary screen."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                self.current_orig_img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                self.current_filename = f"screen_{int(time.time())}.png"

            buf = io.BytesIO()
            self.current_orig_img.save(buf, format="PNG")
            img_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            return {
                "status": "ok",
                "image": f"data:image/png;base64,{img_b64}",
                "message": "تم التقاط الشاشة كاملة"
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def upload_image(self, base64_data: str, filename: str) -> dict:
        try:
            if "," in base64_data:
                base64_data = base64_data.split(",")[1]
            img_bytes = base64.b64decode(base64_data)
            self.current_orig_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            self.current_filename = filename
            return {"status": "ok", "message": f"تم تحميل: {filename}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def translate_page(self, source_lang: str, model_name: str, skip_sfx: bool) -> dict:
        if not self.current_orig_img:
            return {"status": "error", "message": "الرجاء التقاط منطقة من الشاشة أولاً!"}

        if not config.gemini_api_key:
            return {"status": "error", "message": "لم يتم العثور على مفتاح GEMINI_API_KEY في ملف .env!"}

        try:
            detector = OpenCVBubbleDetector(skip_sfx=skip_sfx)
            regions = detector.detect(self.current_orig_img)

            if not regions:
                return {"status": "error", "message": "لم يتم العثور على أي فقاعات أو نصوص في المنطقة المحددة."}

            ocr = GeminiVisionOCR(
                api_key=config.gemini_api_key,
                model_name=model_name or "gemini-1.5-flash",
                source_lang=source_lang
            )
            ocr_texts = ocr.extract_texts(self.current_orig_img, regions)

            translator = ComicTranslator(
                api_key=config.gemini_api_key,
                model_name=model_name or "gemini-1.5-flash",
                source_lang=source_lang,
                glossary_path=config.glossary_path
            )
            translations = translator.translate_page(ocr_texts)

            inpainter = BubbleInpainter(mode="auto")
            cleaned = inpainter.inpaint(self.current_orig_img, regions)

            typesetter = ArabicTypesetter(
                font_path=config.font_path,
                min_font_size=config.min_font_size,
                max_font_size=config.max_font_size
            )
            self.current_trans_img = typesetter.typeset_page(cleaned, regions, translations)

            buffered = io.BytesIO()
            self.current_trans_img.save(buffered, format="PNG")
            img_b64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return {
                "status": "ok",
                "image": f"data:image/png;base64,{img_b64}",
                "count": len(regions)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def save_translated_image(self) -> dict:
        if not self.current_trans_img:
            return {"status": "error", "message": "لا توجد صورة مترجمة لحفظها!"}

        try:
            out_dir = Path("out")
            out_dir.mkdir(exist_ok=True)
            save_path = out_dir / f"translated_{self.current_filename}"
            self.current_trans_img.save(save_path)
            return {"status": "ok", "message": f"تم حفظ الصورة بنجاح في:\n{save_path.absolute()}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>VisualVerse Desktop</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
    
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Cairo', 'Segoe UI', sans-serif;
      user-select: none;
    }

    body {
      background: radial-gradient(circle at top, #1e1f29, #121318);
      color: #f1f2f6;
      height: 100vh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    header {
      background: rgba(255, 255, 255, 0.03);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid rgba(255, 255, 255, 0.08);
      padding: 12px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-icon {
      font-size: 26px;
      background: linear-gradient(135deg, #a55eea, #45aaf2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-title {
      font-size: 18px;
      font-weight: 700;
    }

    .status-badge {
      font-size: 13px;
      padding: 6px 14px;
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.06);
      color: #ced6e0;
      border: 1px solid rgba(255, 255, 255, 0.1);
      transition: all 0.3s;
    }

    .main-layout {
      display: flex;
      flex: 1;
      overflow: hidden;
      gap: 20px;
      padding: 20px;
    }

    .sidebar {
      width: 320px;
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 16px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 14px;
      backdrop-filter: blur(16px);
    }

    .btn-capture {
      background: linear-gradient(135deg, #ff4757, #ff6b81);
      color: white;
      border: none;
      padding: 14px;
      border-radius: 12px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
      box-shadow: 0 4px 15px rgba(255, 71, 87, 0.3);
      transition: all 0.25s;
    }

    .btn-capture:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(255, 71, 87, 0.5);
    }

    .control-group {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    label {
      font-size: 13px;
      font-weight: 600;
      color: #a4b0be;
    }

    select {
      width: 100%;
      padding: 10px 14px;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(255, 255, 255, 0.12);
      border-radius: 10px;
      color: white;
      font-size: 14px;
      outline: none;
    }

    .btn {
      width: 100%;
      padding: 13px;
      border: none;
      border-radius: 10px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.25s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }

    .btn-primary {
      background: linear-gradient(135deg, #a55eea, #2ed573);
      color: white;
      box-shadow: 0 4px 15px rgba(46, 213, 115, 0.25);
    }

    .btn-primary:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(46, 213, 115, 0.4);
    }

    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    .btn-secondary {
      background: rgba(255, 255, 255, 0.08);
      color: #f1f2f6;
      border: 1px solid rgba(255, 255, 255, 0.15);
    }

    .preview-container {
      flex: 1;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      overflow: hidden;
    }

    .preview-card {
      background: rgba(255, 255, 255, 0.02);
      border: 1px solid rgba(255, 255, 255, 0.07);
      border-radius: 16px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      backdrop-filter: blur(8px);
    }

    .card-header {
      padding: 10px 18px;
      font-size: 14px;
      font-weight: 700;
      border-bottom: 1px solid rgba(255, 255, 255, 0.06);
      background: rgba(0, 0, 0, 0.2);
      display: flex;
      justify-content: space-between;
      color: #dfe4ea;
    }

    .card-body {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 12px;
      overflow: auto;
      background: rgba(0, 0, 0, 0.15);
    }

    .card-body img {
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      border-radius: 8px;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }

    .placeholder-text {
      color: #747d8c;
      font-size: 14px;
      text-align: center;
    }

    .loader {
      display: none;
      width: 20px;
      height: 20px;
      border: 3px solid rgba(255,255,255,0.3);
      border-radius: 50%;
      border-top-color: white;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <div class="brand-icon">⚡</div>
      <div class="brand-title">VisualVerse | المترجم الفوري للمانجا والشاشة مباشرة</div>
    </div>
    <div id="statusBadge" class="status-badge">🟢 جاهز للترجمة</div>
  </header>

  <div class="main-layout">
    <div class="sidebar">
      
      <!-- Screen Capture Button -->
      <button class="btn-capture" onclick="captureRegion()">
        <span>✂️</span>
        <span>تحديد وترجمة من الشاشة فوراً</span>
      </button>

      <button class="btn btn-secondary" onclick="captureFull()">
        <span>🖥️</span>
        <span>التقاط الشاشة كاملة</span>
      </button>

      <div class="control-group">
        <label>اللغة الأصلية للمانجا:</label>
        <select id="langSelect">
          <option value="ja">ياباني (مانجا)</option>
          <option value="ko">كوري (مانهوا)</option>
          <option value="zh">صيني (مانها)</option>
          <option value="en">إنجليزي</option>
        </select>
      </div>

      <div class="control-group">
        <label>نموذج الذكاء الاصطناعي:</label>
        <select id="modelSelect">
          <option value="gemini-1.5-flash">Gemini 1.5 Flash (سريع جداً)</option>
          <option value="gemini-2.0-flash">Gemini 2.0 Flash</option>
        </select>
      </div>

      <div style="display:flex; align-items:center; gap:8px;">
        <input type="checkbox" id="skipSfx" style="width:16px; height:16px; cursor:pointer;">
        <label for="skipSfx" style="cursor:pointer;">تخطي المؤثرات (SFX)</label>
      </div>

      <button id="translateBtn" class="btn btn-primary" onclick="startTranslation()" disabled>
        <div id="btnSpinner" class="loader"></div>
        <span id="btnText">🚀 ترجمة الآن</span>
      </button>

      <button id="saveBtn" class="btn btn-secondary" onclick="saveImage()" disabled>
        💾 حفظ النتيجة في مجلد out
      </button>

    </div>

    <!-- Previews -->
    <div class="preview-container">
      <div class="preview-card">
        <div class="card-header">
          <span>اللقطة الأصلية من شاشتك</span>
        </div>
        <div class="card-body">
          <img id="origImg" style="display:none;">
          <div id="origPlaceholder" class="placeholder-text">اضغط على زر (تحديد وترجمة من الشاشة) وحدد أي مانجا مفتوحة أمامك</div>
        </div>
      </div>

      <div class="preview-card">
        <div class="card-header">
          <span>الترجمة المباشرة بالعربية</span>
          <span id="bubbleCount" style="color: #2ed573; font-size:12px;"></span>
        </div>
        <div class="card-body">
          <img id="transImg" style="display:none;">
          <div id="transPlaceholder" class="placeholder-text">ستظهر المانجا مترجمة بالعربية هنا فوراً</div>
        </div>
      </div>
    </div>
  </div>

  <script>
    async function captureRegion() {
      const badge = document.getElementById('statusBadge');
      badge.innerText = '✂️ حدد المنطقة بالماوس على شاشتك...';
      
      const res = await pywebview.api.capture_screen_area();
      if (res.status === 'ok') {
        showOriginal(res.image);
        badge.innerText = '✅ تم الالتقاط! جارٍ الترجمة التلقائية...';
        // Auto trigger translation immediately!
        startTranslation();
      } else {
        badge.innerText = res.message;
      }
    }

    async function captureFull() {
      const badge = document.getElementById('statusBadge');
      badge.innerText = '🖥️ جارٍ التقاط الشاشة كاملة...';
      
      const res = await pywebview.api.capture_fullscreen();
      if (res.status === 'ok') {
        showOriginal(res.image);
        badge.innerText = '✅ تم الالتقاط! جارٍ الترجمة التلقائية...';
        startTranslation();
      } else {
        badge.innerText = res.message;
      }
    }

    function showOriginal(base64Data) {
      const origImg = document.getElementById('origImg');
      origImg.src = base64Data;
      origImg.style.display = 'block';
      document.getElementById('origPlaceholder').style.display = 'none';

      document.getElementById('translateBtn').disabled = false;
      document.getElementById('transImg').style.display = 'none';
      document.getElementById('transPlaceholder').style.display = 'block';
      document.getElementById('saveBtn').disabled = true;
      document.getElementById('bubbleCount').innerText = '';
    }

    async function startTranslation() {
      const btn = document.getElementById('translateBtn');
      const spinner = document.getElementById('btnSpinner');
      const btnText = document.getElementById('btnText');
      const badge = document.getElementById('statusBadge');

      btn.disabled = true;
      spinner.style.display = 'block';
      btnText.innerText = 'جارٍ الترجمة الفورية...';
      badge.innerText = '⏳ جارٍ استخراج النص وتفريغه وترجمته...';

      const lang = document.getElementById('langSelect').value;
      const model = document.getElementById('modelSelect').value;
      const skipSfx = document.getElementById('skipSfx').checked;

      try {
        const res = await pywebview.api.translate_page(lang, model, skipSfx);
        if (res.status === 'ok') {
          const transImg = document.getElementById('transImg');
          transImg.src = res.image;
          transImg.style.display = 'block';
          document.getElementById('transPlaceholder').style.display = 'none';
          document.getElementById('bubbleCount').innerText = `تمت ترجمة وتفريغ ${res.count} فقاعة`;
          document.getElementById('saveBtn').disabled = false;
          badge.innerText = '✅ تمت الترجمة بنجاح!';
        } else {
          alert('خطأ: ' + res.message);
          badge.innerText = '❌ حدث خطأ أثناء الترجمة';
        }
      } catch (err) {
        alert('حدث خطأ: ' + err);
      } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
        btnText.innerText = '🚀 ترجمة الآن';
      }
    }

    async function saveImage() {
      const res = await pywebview.api.save_translated_image();
      alert(res.message);
    }
  </script>
</body>
</html>
"""

def main():
    api = DesktopApi()
    window = webview.create_window(
        title="VisualVerse | المترجم الفوري للمانجا والشاشة مباشرة",
        html=HTML_CONTENT,
        js_api=api,
        width=1180,
        height=780,
        resizable=True
    )
    webview.start()

if __name__ == "__main__":
    main()
