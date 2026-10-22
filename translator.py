import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import google.generativeai as genai

class ComicTranslator:
    """Translates comic dialogue to natural Arabic using Google Gemini."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-1.5-flash",
        source_lang: str = "ja",
        glossary_path: Optional[Path] = None,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.source_lang = source_lang
        self.max_retries = max_retries
        self.glossary: Dict[str, str] = {}
        
        if glossary_path and Path(glossary_path).exists():
            try:
                with open(glossary_path, "r", encoding="utf-8") as f:
                    self.glossary = json.load(f)
            except Exception as e:
                print(f"[Warning] Failed to load glossary file {glossary_path}: {e}")

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def _build_prompt(self, page_dialogues: List[Dict[str, object]]) -> str:
        glossary_instructions = ""
        if self.glossary:
            glossary_instructions = (
                "### Mandatory Glossary (Character Names / Specific Terms):\n"
                + json.dumps(self.glossary, ensure_ascii=False, indent=2)
                + "\nAlways adhere to these specific translations.\n\n"
            )

        prompt = f"""You are a professional comic and manga translator specializing in translating dialogues into natural, vivid, and idiomatic Modern Standard Arabic (فصحى مبسطة ومعاصرة تناسب الكوميكس والمانجا).

{glossary_instructions}### Guidelines:
1. Contextual Translation: The input contains all dialogues/bubbles from a single comic page in sequential reading order. Maintain conversational tone, character voice, and dramatic rhythm.
2. Natural Arabic: Avoid stiff, awkward, or overly literal translations. Use concise, expressive Arabic dialogue suitable for speech bubbles (short and punchy).
3. Punctuation & Emotion: Preserve exclamation marks, question marks, and dramatic pauses appropriately for Arabic RTL reading.
4. Output format: You MUST return strictly a valid JSON array of objects. Each object must have "id" (integer) matching the input, and "translation" (string with the Arabic translation).
No markdown backticks, no notes, no commentary.

Input dialogues:
{json.dumps(page_dialogues, ensure_ascii=False, indent=2)}
"""
        return prompt

    def translate_page(self, text_map: Dict[int, str]) -> Dict[int, str]:
        """Translates a mapping of {id: original_text} into {id: arabic_translation}."""
        # Filter out empty or whitespace-only texts
        active_items = [{"id": k, "original": v} for k, v in text_map.items() if v.strip()]
        if not active_items:
            return {k: "" for k in text_map}

        prompt = self._build_prompt(active_items)

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.model.generate_content(prompt)
                raw_text = response.text.strip()
                
                # Strip markdown fences if Gemini outputs ```json ... ```
                if raw_text.startswith("```"):
                    parts = raw_text.split("```")
                    if len(parts) >= 2:
                        raw_text = parts[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
                raw_text = raw_text.strip()

                parsed = json.loads(raw_text)
                translations: Dict[int, str] = {item["id"]: str(item.get("translation", "")) for item in parsed}
                
                # Fill any missing keys
                for item in active_items:
                    req_id = item["id"]
                    if req_id not in translations:
                        translations[req_id] = ""
                        
                return translations

            except Exception as e:
                print(f"[Warning] Translation attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    # Exponential backoff
                    sleep_time = 2 ** attempt
                    time.sleep(sleep_time)
                else:
                    print("[Error] Max retries reached for page translation.")
                    # Fallback to empty string for safety
                    return {k: "" for k in text_map}

        return {k: "" for k in text_map}
