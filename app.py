import os
import gradio as gr
from PIL import Image
from pathlib import Path
from typing import List, Tuple

from config import PipelineConfig
from detector import OpenCVBubbleDetector, TextRegion
from ocr import GeminiVisionOCR
from translator import ComicTranslator
from inpaint import BubbleInpainter
from typeset import ArabicTypesetter

# Load configurations
config = PipelineConfig()

def translate_single_image(
    input_image: Image.Image,
    source_lang: str,
    api_key: str,
    gemini_model: str,
    skip_sfx: bool,
    progress=gr.Progress(track_tqdm=True)
) -> Tuple[Image.Image, str]:
    if input_image is None:
        return None, "⚠️ الرجاء رفع صورة أولاً!"

    key = api_key.strip() if api_key and api_key.strip() else config.gemini_api_key
    if not key:
        return None, "❌ خطأ: لم يتم العثور على مفتاح Gemini API! ضعه في ملف .env أو في الحقل المخصص."

    progress(0.1, desc="🔍 جارٍ اكتشاف فقاعات الكلام...")
    detector = OpenCVBubbleDetector(skip_sfx=skip_sfx)
    regions = detector.detect(input_image)
    
    if not regions:
        return input_image, "⚠️ لم يتم اكتشاف أي فقاعات نصية في هذه الصفحة."

    progress(0.3, desc="📖 استخراج النصوص (OCR)...")
    ocr_engine = GeminiVisionOCR(api_key=key, model_name=gemini_model, source_lang=source_lang)
    ocr_texts = ocr_engine.extract_texts(input_image, regions)

    progress(0.6, desc="🌐 ترجمة الحوارات إلى العربية الطبيعية...")
    translator = ComicTranslator(
        api_key=key,
        model_name=gemini_model,
        source_lang=source_lang,
        glossary_path=config.glossary_path
    )
    translations = translator.translate_page(ocr_texts)

    progress(0.8, desc="🎨 تفريغ النص الأصلي (Inpainting)...")
    inpainter = BubbleInpainter(mode="auto")
    cleaned_page = inpainter.inpaint(input_image, regions)

    progress(0.9, desc="✍️ تصفيف النص العربي (RTL Typesetting)...")
    typesetter = ArabicTypesetter(
        font_path=config.font_path,
        min_font_size=config.min_font_size,
        max_font_size=config.max_font_size
    )
    final_page = typesetter.typeset_page(cleaned_page, regions, translations)

    # Prepare summary report
    report_lines = [f"✅ تمت الترجمة بنجاح! ({len(regions)} فقاعة مكتشفة)\n---"]
    for reg in regions:
        orig = ocr_texts.get(reg.id, "").replace("\n", " ")
        trans = translations.get(reg.id, "").replace("\n", " ")
        if orig or trans:
            report_lines.append(f"• [فقاعة {reg.id}] الأصل: {orig} ⬅️ الترجمة: {trans}")

    return final_page, "\n".join(report_lines)

# Custom CSS for modern Arabic aesthetic
custom_css = """
body, .gradio-container {
    direction: rtl !important;
    text-align: right !important;
    font-family: 'Segoe UI', Tahoma, sans-serif;
}
.header-box {
    text-align: center;
    padding: 20px;
    background: linear-gradient(135deg, #1e1e2e, #2a2b3d);
    color: white;
    border-radius: 12px;
    margin-bottom: 20px;
}
"""

with gr.Blocks(title="مترجم المانجا والمانهوا إلى العربية | VisualVerse", css=custom_css, theme=gr.themes.Soft()) as demo:
    gr.HTML("""
        <div class="header-box">
            <h1>🎨 مترجم المانجا والمانهوا إلى العربية</h1>
            <p>ارفع أي صفحة مانجا أو مانهوا وسيقوم الذكاء الاصطناعي بتفريغ الفقاعات وترجمتها وتصفيفها بالعربية تلقائياً</p>
        </div>
    """)

    with gr.Row():
        with gr.Column(scale=1):
            input_img = gr.Image(label="📥 اسحب صفحة المانجا الأصلية هنا", type="pil")
            
            with gr.Accordion("⚙️ إعدادات الترجمة", open=True):
                source_lang = gr.Dropdown(
                    label="اللغة الأصلية للمانجا",
                    choices=[("ياباني (مانجا)", "ja"), ("كوري (مانهوا)", "ko"), ("صيني (مانها)", "zh"), ("إنجليزي", "en")],
                    value="ja"
                )
                gemini_model = gr.Dropdown(
                    label="نموذج الذكاء الاصطناعي",
                    choices=["gemini-1.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"],
                    value="gemini-1.5-flash"
                )
                api_key_input = gr.Textbox(
                    label="مفتاح Gemini API (اختياري إذا وضعته في .env)",
                    placeholder="AIzaSy...",
                    type="password"
                )
                skip_sfx = gr.Checkbox(label="تخطي المؤثرات الصوتية (SFX) والتركيز على الحوارات فقط", value=False)

            translate_btn = gr.Button("🚀 ابدأ الترجمة الآن", variant="primary", size="lg")

        with gr.Column(scale=1):
            output_img = gr.Image(label="📤 الصفحة المترجمة بالعربية جاهزة للحفظ", type="pil")
            status_box = gr.Textbox(label="📋 سجل الترجمة والحوارات المكتشفة", lines=8)

    translate_btn.click(
        fn=translate_single_image,
        inputs=[input_img, source_lang, api_key_input, gemini_model, skip_sfx],
        outputs=[output_img, status_box]
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)
