import os
import io
import time
import json
import webview
from pathlib import Path
from tkinter import filedialog
import tkinter as tk

from game_localizer import GameEngineDetector, GameTextTranslator, LocalTranslationMemory
from game_patcher import GamePatcher
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

class MiqbasDesktopApi:
    def __init__(self):
        self.selected_game_dir: Path | None = None
        self.engine_type = "unknown"
        self.found_files: list[Path] = []
        self.memory = LocalTranslationMemory()

    def select_game_folder(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="اختر مجلد اللعبة التي تريد تعريبها")
        root.destroy()

        if not folder:
            return {"status": "cancelled", "message": "لم يتم اختيار مجلد"}

        self.selected_game_dir = Path(folder)
        self.engine_type, self.found_files = GameEngineDetector.detect(self.selected_game_dir)

        engine_names = {
            "unity": "Unity Engine 🎮",
            "unreal": "Unreal Engine (UE4 / UE5) ⚡",
            "rpg_maker": "RPG Maker ⚔️",
            "generic_mod": "Mod / Strategy Game (Mount & Blade / Paradox) 🛡️",
            "generic": "محرك نصوص عام (Generic Text) 📄",
            "unknown": "غير معروف (لم يتم العثور على ملفات نصوص معيارية)"
        }

        # Count total strings cached in memory
        with self.memory.db_path.open("r", encoding="utf-8", errors="ignore") if self.memory.db_path.exists() else io.StringIO():
            pass

        return {
            "status": "ok",
            "folder_name": self.selected_game_dir.name,
            "folder_path": str(self.selected_game_dir),
            "engine": engine_names.get(self.engine_type, self.engine_type),
            "file_count": len(self.found_files),
            "files": [f.name for f in self.found_files[:10]]
        }

    def start_localization(self) -> dict:
        if not self.selected_game_dir:
            return {"status": "error", "message": "الرجاء اختيار مجلد اللعبة أولاً!"}

        if not API_KEY:
            return {"status": "error", "message": "لم يتم العثور على مفتاح GEMINI_API_KEY في ملف .env!"}

        if not self.found_files:
            return {"status": "error", "message": "لم يتم العثور على ملفات نصوص لتعريبها في هذا المجلد."}

        translator = GameTextTranslator(api_key=API_KEY, model_name=MODEL_NAME)
        patcher = GamePatcher(translator)

        total_translated_strings = 0
        patched_files_count = 0
        game_name = self.selected_game_dir.name

        try:
            for file_path in self.found_files:
                ext = file_path.suffix.lower()
                count = 0
                if ext == ".json":
                    count = patcher.patch_json_file(file_path, game_name)
                elif ext in [".csv", ".tsv"]:
                    count = patcher.patch_csv_file(file_path, game_name)
                elif ext == ".xml":
                    count = patcher.patch_xml_file(file_path, game_name)

                if count > 0:
                    total_translated_strings += count
                    patched_files_count += 1

            return {
                "status": "ok",
                "message": f"🎉 تم تعريب اللعبة بنجاح!\n• عدد الجمل المعربة: {total_translated_strings}\n• عدد الملفات المعدلة: {patched_files_count}\n• تم إنشاء نسخة احتياطية (.orig_backup) لجميع الملفات."
            }
        except Exception as e:
            return {"status": "error", "message": f"حدث خطأ أثناء التعريب: {str(e)}"}

    def restore_game(self) -> dict:
        if not self.found_files:
            return {"status": "error", "message": "الرجاء فحص اللعبة أولاً."}

        restored_count = 0
        for f in self.found_files:
            if GamePatcher.restore_backup(f):
                restored_count += 1

        if restored_count > 0:
            return {"status": "ok", "message": f"✅ تم استرجاع النسخة الأصلية للعبة بنجاح ({restored_count} ملف)!"}
        else:
            return {"status": "error", "message": "لم يتم العثور على نسخ احتياطية لاسترجاعها."}

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>Miqbas - أداة تعريب الألعاب التلقائية</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800;900&display=swap');

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: 'Cairo', 'Segoe UI', sans-serif;
      user-select: none;
    }

    body {
      background: radial-gradient(circle at top right, #1a102f, #0d0e15 70%);
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
      padding: 16px 28px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .brand-icon {
      font-size: 30px;
      background: linear-gradient(135deg, #a55eea, #2ed573);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      filter: drop-shadow(0 2px 8px rgba(165, 94, 234, 0.4));
    }

    .brand-title {
      font-size: 20px;
      font-weight: 800;
    }

    .brand-subtitle {
      font-size: 12px;
      color: #a4b0be;
    }

    .container {
      flex: 1;
      display: flex;
      gap: 24px;
      padding: 24px;
      overflow: hidden;
    }

    .panel {
      background: rgba(255, 255, 255, 0.04);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 20px;
      padding: 24px;
      display: flex;
      flex-direction: column;
      backdrop-filter: blur(16px);
    }

    .panel-left {
      width: 380px;
      gap: 18px;
    }

    .panel-right {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .btn {
      width: 100%;
      padding: 14px;
      border: none;
      border-radius: 12px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.25s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 10px;
    }

    .btn-select {
      background: linear-gradient(135deg, #3742fa, #5352ed);
      color: white;
      box-shadow: 0 4px 15px rgba(55, 66, 250, 0.3);
    }

    .btn-select:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 22px rgba(55, 66, 250, 0.5);
    }

    .btn-localize {
      background: linear-gradient(135deg, #10ac84, #1dd1a1);
      color: white;
      font-size: 17px;
      box-shadow: 0 4px 18px rgba(16, 172, 132, 0.35);
    }

    .btn-localize:hover:not(:disabled) {
      transform: translateY(-2px);
      box-shadow: 0 8px 25px rgba(16, 172, 132, 0.5);
    }

    .btn-localize:disabled {
      opacity: 0.4;
      cursor: not-allowed;
      transform: none;
    }

    .btn-restore {
      background: rgba(255, 71, 87, 0.15);
      color: #ff6b81;
      border: 1px solid rgba(255, 71, 87, 0.3);
    }

    .btn-restore:hover:not(:disabled) {
      background: rgba(255, 71, 87, 0.25);
    }

    .info-card {
      background: rgba(0, 0, 0, 0.25);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 14px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .info-row {
      display: flex;
      justify-content: space-between;
      font-size: 13px;
    }

    .info-label {
      color: #a4b0be;
    }

    .info-value {
      color: #ffffff;
      font-weight: 700;
    }

    .files-list {
      flex: 1;
      background: rgba(0, 0, 0, 0.3);
      border: 1px solid rgba(255, 255, 255, 0.06);
      border-radius: 14px;
      padding: 16px;
      overflow-y: auto;
      font-family: 'Consolas', monospace;
      font-size: 12px;
      color: #ced6e0;
      direction: ltr;
      text-align: left;
    }

    .loader {
      display: none;
      width: 22px;
      height: 22px;
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
      <div>
        <div class="brand-title">مقباس | Miqbas Auto Game Localizer</div>
        <div class="brand-subtitle">نظام التعريب الآلي لألعاب الكمبيوتر بالذكاء الاصطناعي (Gemini)</div>
      </div>
    </div>
    <div id="statusBadge" style="background:rgba(255,255,255,0.06); padding:6px 14px; border-radius:20px; font-size:13px; color:#2ed573;">
      🟢 جاهز لفحص الألعاب
    </div>
  </header>

  <div class="container">
    
    <!-- Left Controls Panel -->
    <div class="panel panel-left">
      
      <button class="btn btn-select" onclick="selectFolder()">
        <span>📁</span>
        <span>اختيار مجلد اللعبة</span>
      </button>

      <div class="info-card">
        <div class="info-row">
          <span class="info-label">اسم اللعبة:</span>
          <span class="info-value" id="gameName">-</span>
        </div>
        <div class="info-row">
          <span class="info-label">محرك اللعبة المكتشف:</span>
          <span class="info-value" id="gameEngine">-</span>
        </div>
        <div class="info-row">
          <span class="info-label">ملفات النصوص:</span>
          <span class="info-value" id="fileCount">0 ملف</span>
        </div>
      </div>

      <button id="localizeBtn" class="btn btn-localize" onclick="startLocalizing()" disabled>
        <div id="spinner" class="loader"></div>
        <span id="btnText">🚀 بدء تعريب اللعبة بالكامل</span>
      </button>

      <button id="restoreBtn" class="btn btn-restore" onclick="restoreGame()" disabled>
        🔄 استرجاع النسخة الأصلية للعبة
      </button>

    </div>

    <!-- Right Log & Details Panel -->
    <div class="panel panel-right">
      <div style="font-size:15px; font-weight:700; color:#dfe4ea;">
        📋 ملفات التعريب والنصوص المكتشفة داخل اللعبة:
      </div>
      
      <div class="files-list" id="filesList">
        // اختر مجلد اللعبة ليقوم مقباس بفحص المحرك واستخراج ملفات اللغات تلقائياً...
      </div>
    </div>

  </div>

  <script>
    async function selectFolder() {
      const res = await pywebview.api.select_game_folder();
      if (res.status === 'ok') {
        document.getElementById('gameName').innerText = res.folder_name;
        document.getElementById('gameEngine').innerText = res.engine;
        document.getElementById('fileCount').innerText = res.file_count + ' ملف';

        const listDiv = document.getElementById('filesList');
        if (res.files && res.files.length > 0) {
          listDiv.innerHTML = res.files.map(f => `<div>[+] Found Language file: ${f}</div>`).join('');
          document.getElementById('localizeBtn').disabled = false;
          document.getElementById('restoreBtn').disabled = false;
        } else {
          listDiv.innerHTML = '<div>[!] لم يتم العثور على ملفات نصوص معيارية قابلة للتعريب في هذا المجلد.</div>';
          document.getElementById('localizeBtn').disabled = true;
        }
      }
    }

    async function startLocalizing() {
      const btn = document.getElementById('localizeBtn');
      const spinner = document.getElementById('spinner');
      const btnText = document.getElementById('btnText');
      const badge = document.getElementById('statusBadge');

      btn.disabled = true;
      spinner.style.display = 'block';
      btnText.innerText = 'جارٍ فحص واستخراج وترجمة النصوص...';
      badge.innerText = '⏳ جارٍ التعريب عبر Gemini...';

      try {
        const res = await pywebview.api.start_localization();
        if (res.status === 'ok') {
          alert(res.message);
          badge.innerText = '✅ تم تعريب اللعبة بنجاح!';
        } else {
          alert('خطأ: ' + res.message);
          badge.innerText = '❌ فشل التعريب';
        }
      } catch (err) {
        alert('حدث خطأ: ' + err);
      } finally {
        btn.disabled = false;
        spinner.style.display = 'none';
        btnText.innerText = '🚀 بدء تعريب اللعبة بالكامل';
      }
    }

    async function restoreGame() {
      const res = await pywebview.api.restore_game();
      alert(res.message);
    }
  </script>
</body>
</html>
"""

def main():
    api = MiqbasDesktopApi()
    window = webview.create_window(
        title="مقباس (Miqbas Clone) | أداة تعريب ألعاب الكمبيوتر التلقائية",
        html=HTML_CONTENT,
        js_api=api,
        width=1100,
        height=720,
        resizable=True
    )
    webview.start()

if __name__ == "__main__":
    main()
