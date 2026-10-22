from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import io
from PIL import Image
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai
from detector import TextRegion

class BaseOCR(ABC):
    """Abstract base class for OCR engines."""
    
    @abstractmethod
    def extract_texts(self, image: Image.Image, regions: List[TextRegion]) -> Dict[int, str]:
        """Extract text for each detected region. Returns mapping of {region_id: text}."""
        pass

class GeminiVisionOCR(BaseOCR):
    """
    Multimodal OCR powered by Google Gemini Vision.
    Zero local dependencies; excels at vertical Japanese, Korean, and stylized comic fonts.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash", source_lang: str = "ja"):
        self.api_key = api_key
        self.model_name = model_name
        self.source_lang = source_lang
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def extract_texts(self, image: Image.Image, regions: List[TextRegion]) -> Dict[int, str]:
        if not regions:
            return {}

        results: Dict[int, str] = {}
        crops: List[Image.Image] = []
        valid_regions: List[TextRegion] = []

        w_img, h_img = image.size
        for r in regions:
            x, y, w, h = r.bbox
            # Add small padding to avoid clipping characters
            x0 = max(0, x - 2)
            y0 = max(0, y - 2)
            x1 = min(w_img, x + w + 2)
            y1 = min(h_img, y + h + 2)
            crop = image.crop((x0, y0, x1, y1))
            crops.append(crop)
            valid_regions.append(r)

        # Batch request to Gemini Vision: Send all cropped regions with ID tags
        prompt_parts: List[object] = [
            f"You are an expert comic OCR tool for language '{self.source_lang}'.\n"
            "Below are cropped text bubbles/regions from a comic page, presented in reading order.\n"
            "For each image, transcribe the text exactly as written in the original language.\n"
            "Output strictly a valid JSON array of objects with 'id' and 'text', like:\n"
            '[{"id": 0, "text": "こんにちは"}, {"id": 1, "text": "誰だ！？"}]\n'
            "If an image contains only art, background or no legible text, return empty string for 'text'.\n"
            "Do not include markdown codeblocks or extra explanations."
        ]

        for reg, crop in zip(valid_regions, crops):
            prompt_parts.append(f"Region ID: {reg.id}")
            prompt_parts.append(crop)

        try:
            response = self.model.generate_content(prompt_parts)
            text_response = response.text.strip()
            
            # Clean possible markdown wrapping like ```json ... ```
            if text_response.startswith("```"):
                text_response = text_response.split("```")[1]
                if text_response.startswith("json"):
                    text_response = text_response[4:]
            text_response = text_response.strip()

            import json
            parsed = json.loads(text_response)
            for item in parsed:
                reg_id = item.get("id")
                txt = item.get("text", "").strip()
                if reg_id is not None:
                    results[int(reg_id)] = txt
        except Exception as e:
            print(f"[Warning] Gemini OCR batch error: {e}. Falling back to individual crops or empty.")
            # Fallback if bulk fails: fill empty
            for r in regions:
                if r.id not in results:
                    results[r.id] = ""

        return results

class LocalTesseractOCR(BaseOCR):
    """Fallback local OCR if pytesseract is installed."""
    def __init__(self, lang: str = "jpn"):
        self.lang = lang

    def extract_texts(self, image: Image.Image, regions: List[TextRegion]) -> Dict[int, str]:
        results = {}
        try:
            import pytesseract
            for r in regions:
                x, y, w, h = r.bbox
                crop = image.crop((x, y, x + w, y + h))
                text = pytesseract.image_to_string(crop, lang=self.lang)
                results[r.id] = text.strip()
        except ImportError:
            for r in regions:
                results[r.id] = ""
        return results
