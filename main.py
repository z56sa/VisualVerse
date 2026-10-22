import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any
from tqdm import tqdm
from PIL import ImageDraw, ImageFont

from config import PipelineConfig
from cache import CacheManager
from loader import MangaLoader
from detector import OpenCVBubbleDetector, TextRegion
from ocr import GeminiVisionOCR, LocalTesseractOCR
from translator import ComicTranslator
from inpaint import BubbleInpainter
from typeset import ArabicTypesetter

def draw_debug_page(image, regions: list[TextRegion], ocr_results: dict[int, str] | None = None):
    debug_img = image.copy()
    draw = ImageDraw.Draw(debug_img)
    font = ImageFont.load_default()

    for r in regions:
        bx, by, bw, bh = r.bbox
        # SFX in orange/red, normal bubbles in bright green
        color = (255, 69, 0) if r.is_sfx else (0, 255, 0)
        draw.rectangle([bx, by, bx + bw, by + bh], outline=color, width=3)
        
        # Label ID
        label = f"ID: {r.id}"
        if ocr_results and r.id in ocr_results:
            preview = ocr_results[r.id][:10]
            label += f" | {preview}"
            
        draw.rectangle([bx, by - 16, bx + len(label) * 7, by], fill=color)
        draw.text((bx + 2, by - 14), label, fill=(0, 0, 0), font=font)
        
    return debug_img

def cmd_translate(args, config: PipelineConfig):
    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    cache = CacheManager(config.cache_dir)
    loader = MangaLoader(input_path)
    detector = OpenCVBubbleDetector(skip_sfx=config.skip_sfx)

    # Initialize OCR & Translator
    if not config.gemini_api_key:
        print("[Error] GEMINI_API_KEY is not set. Please add it to your .env file.")
        sys.exit(1)

    ocr_engine = GeminiVisionOCR(
        api_key=config.gemini_api_key,
        model_name=config.gemini_model,
        source_lang=config.source_lang
    )

    translator = ComicTranslator(
        api_key=config.gemini_api_key,
        model_name=config.gemini_model,
        source_lang=config.source_lang,
        glossary_path=Path(args.glossary) if args.glossary else config.glossary_path
    )

    inpainter = BubbleInpainter(mode=config.inpaint_mode, solid_tolerance=config.solid_color_tolerance)
    typesetter = ArabicTypesetter(
        font_path=args.font or config.font_path,
        min_font_size=config.min_font_size,
        max_font_size=config.max_font_size
    )

    print(f"[*] Processing {len(loader.image_paths)} pages from: {input_path}")
    print(f"[*] Target Arabic translation engine: Gemini ({config.gemini_model})")

    all_page_records = {}

    for idx, img_path, img in tqdm(loader.get_valid_pages(), total=len(loader.image_paths), desc="Translating Manga"):
        img_hash = CacheManager.compute_image_hash(img_path)
        cached_entry = cache.get_entry(img_hash)

        if cached_entry:
            # Use cached detections and translations
            regions = [
                TextRegion(
                    id=item["id"],
                    bbox=tuple(item["bbox"]),
                    is_bubble=item.get("is_bubble", True),
                    is_sfx=item.get("is_sfx", False)
                )
                for item in cached_entry.get("regions", [])
            ]
            translations = {int(k): v for k, v in cached_entry.get("translations", {}).items()}
        else:
            # 1. Detection
            regions = detector.detect(img)

            # 2. OCR
            ocr_texts = ocr_engine.extract_texts(img, regions)

            # 3. Translation
            translations = translator.translate_page(ocr_texts)

            # Save to cache
            cache_record = {
                "file_name": img_path.name,
                "regions": [
                    {
                        "id": r.id,
                        "bbox": list(r.bbox),
                        "is_bubble": r.is_bubble,
                        "is_sfx": r.is_sfx,
                        "original_text": ocr_texts.get(r.id, "")
                    }
                    for r in regions
                ],
                "translations": {str(k): v for k, v in translations.items()}
            }
            cache.set_entry(img_hash, cache_record)
            all_page_records[img_path.name] = cache_record

        # 4. Inpainting
        cleaned_page = inpainter.inpaint(img, regions)

        # 5. Arabic Typesetting
        final_page = typesetter.typeset_page(cleaned_page, regions, translations)

        # 6. Save output
        out_file = output_dir / img_path.name
        final_page.save(out_file)

    # Export translations.json for optional manual editing
    translations_json_path = output_dir / "translations.json"
    cache.export_translations(translations_json_path)
    print(f"[+] Translations exported for manual review: {translations_json_path}")

    # Optional CBZ packaging
    if args.cbz or config.save_cbz:
        cbz_name = output_dir.with_suffix(".cbz")
        loader.create_cbz(output_dir, cbz_name)
        print(f"[+] CBZ archive generated: {cbz_name}")

    loader.cleanup()
    print(f"[+] All pages successfully translated and saved to: {output_dir}")

def cmd_debug(args, config: PipelineConfig):
    input_path = Path(args.input)
    output_dir = Path(args.output or "./debug_output")
    output_dir.mkdir(parents=True, exist_ok=True)

    loader = MangaLoader(input_path)
    detector = OpenCVBubbleDetector(skip_sfx=config.skip_sfx)

    print(f"[*] Running debug detection on: {input_path}")
    for idx, img_path, img in tqdm(loader.get_valid_pages(), total=len(loader.image_paths), desc="Detecting"):
        regions = detector.detect(img)
        annotated = draw_debug_page(img, regions)
        debug_out_path = output_dir / f"debug_{img_path.name}"
        annotated.save(debug_out_path)

    loader.cleanup()
    print(f"[+] Debug images saved with bounding boxes to: {output_dir}")

def cmd_render(args, config: PipelineConfig):
    input_path = Path(args.input)
    translations_file = Path(args.translations)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not translations_file.exists():
        print(f"[Error] Translations file not found: {translations_file}")
        sys.exit(1)

    with open(translations_file, "r", encoding="utf-8") as f:
        translations_data = json.load(f)

    loader = MangaLoader(input_path)
    inpainter = BubbleInpainter(mode=config.inpaint_mode, solid_tolerance=config.solid_color_tolerance)
    typesetter = ArabicTypesetter(
        font_path=args.font or config.font_path,
        min_font_size=config.min_font_size,
        max_font_size=config.max_font_size
    )

    print(f"[*] Re-rendering pages from edited JSON: {translations_file}")
    for idx, img_path, img in tqdm(loader.get_valid_pages(), total=len(loader.image_paths), desc="Rendering"):
        img_hash = CacheManager.compute_image_hash(img_path)
        entry = translations_data.get(img_hash)

        # Fallback search by filename if hash is absent
        if not entry:
            for k, val in translations_data.items():
                if val.get("file_name") == img_path.name:
                    entry = val
                    break

        if not entry:
            print(f"[Warning] No translation entry found for {img_path.name}, skipping.")
            img.save(output_dir / img_path.name)
            continue

        regions = [
            TextRegion(
                id=item["id"],
                bbox=tuple(item["bbox"]),
                is_bubble=item.get("is_bubble", True),
                is_sfx=item.get("is_sfx", False)
            )
            for item in entry.get("regions", [])
        ]
        translations = {int(k): v for k, v in entry.get("translations", {}).items()}

        cleaned = inpainter.inpaint(img, regions)
        final_page = typesetter.typeset_page(cleaned, regions, translations)
        final_page.save(output_dir / img_path.name)

    loader.cleanup()
    print(f"[+] Re-rendered pages saved to: {output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Manga/Manhwa/Webtoon to Arabic Translator (manga_ar)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: translate
    p_trans = subparsers.add_parser("translate", help="Translate comic pages to Arabic")
    p_trans.add_argument("--input", "-i", required=True, help="Input directory, image, or CBZ/ZIP file")
    p_trans.add_argument("--output", "-o", default="./out", help="Output directory for translated pages")
    p_trans.add_argument("--source", "-s", default="ja", choices=["ja", "ko", "zh", "en", "auto"], help="Source language")
    p_trans.add_argument("--glossary", "-g", default=None, help="Path to glossary.json")
    p_trans.add_argument("--font", "-f", default=None, help="Custom TTF/OTF Arabic font path")
    p_trans.add_argument("--cbz", action="store_true", help="Also generate an output CBZ archive")
    p_trans.add_argument("--skip-sfx", action="store_true", help="Skip sound effects and non-dialogue text")

    # Subcommand: render
    p_rend = subparsers.add_parser("render", help="Re-render pages from edited translations.json")
    p_rend.add_argument("--input", "-i", required=True, help="Input directory or original images")
    p_rend.add_argument("--translations", "-t", required=True, help="Path to translations.json")
    p_rend.add_argument("--output", "-o", default="./out", help="Output directory for rendered pages")
    p_rend.add_argument("--font", "-f", default=None, help="Custom TTF/OTF Arabic font path")

    # Subcommand: debug
    p_deb = subparsers.add_parser("debug", help="Detect text regions and save debug images with boxes")
    p_deb.add_argument("--input", "-i", required=True, help="Input directory, image, or CBZ/ZIP file")
    p_deb.add_argument("--output", "-o", default="./debug_out", help="Output directory for debug images")

    args = parser.parse_args()

    # Load configuration
    config = PipelineConfig()
    if hasattr(args, "source") and args.source:
        config.source_lang = args.source
    if hasattr(args, "skip_sfx"):
        config.skip_sfx = args.skip_sfx

    if args.command == "translate":
        cmd_translate(args, config)
    elif args.command == "debug":
        cmd_debug(args, config)
    elif args.command == "render":
        cmd_render(args, config)

if __name__ == "__main__":
    main()
