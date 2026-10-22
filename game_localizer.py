import os
import re
import json
import hashlib
import sqlite3
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GameEngineDetector:
    """Detects game engine and localization format from game folder."""
    
    @staticmethod
    def detect(game_dir: Path) -> Tuple[str, List[Path]]:
        game_dir = Path(game_dir)
        if not game_dir.exists():
            return "unknown", []

        # 1. Check Unreal Engine (Content/Localization)
        ue_loc_files = list(game_dir.glob("**/Localization/**/*.locres")) + list(game_dir.glob("**/Localization/**/*.archive"))
        if ue_loc_files:
            return "unreal", ue_loc_files

        # 2. Check RPG Maker (data/*.json)
        rpg_data = list(game_dir.glob("**/www/data/*.json")) or list(game_dir.glob("**/data/System.json"))
        if rpg_data:
            return "rpg_maker", list(game_dir.glob("**/data/*.json"))

        # 3. Check Unity Game
        unity_data = list(game_dir.glob("*_Data"))
        if unity_data:
            # Broad scan: StreamingAssets, Resources, and root-level text files
            text_files = (
                list(game_dir.glob("**/*_Data/StreamingAssets/**/*.json")) +
                list(game_dir.glob("**/*_Data/StreamingAssets/**/*.csv")) +
                list(game_dir.glob("**/*_Data/StreamingAssets/**/*.txt")) +
                list(game_dir.glob("**/*_Data/StreamingAssets/**/*.xml")) +
                list(game_dir.glob("**/*_Data/Resources/**/*.json")) +
                list(game_dir.glob("**/*.json")) +
                list(game_dir.glob("**/*.csv")) +
                list(game_dir.glob("**/*.txt")) +
                list(game_dir.glob("**/*.xml"))
            )
            # Deduplicate and filter out tiny/binary files & engine internals
            seen = set()
            filtered = []
            skip_keywords = ["output_log", "player.log", "crash", "boot.config",
                             "unity", "package", "manifest", "app.info"]
            for f in text_files:
                if f in seen:
                    continue
                seen.add(f)
                name_lower = f.name.lower()
                if any(kw in name_lower for kw in skip_keywords):
                    continue
                try:
                    if f.stat().st_size > 50:  # Skip empty/tiny files
                        filtered.append(f)
                except Exception:
                    pass
            return "unity", filtered

        # 4. Check Generic Text / XML / CSV (Mount & Blade, Paradox, RimWorld, etc.)
        xml_csv_files = (
            list(game_dir.glob("**/Languages/**/*.xml")) +
            list(game_dir.glob("**/localization/**/*.csv")) +
            list(game_dir.glob("**/localisation/**/*.yml")) +
            list(game_dir.glob("**/strings/**/*.json"))
        )
        if xml_csv_files:
            return "generic_mod", xml_csv_files

        # Default fallback: scan for any json/csv/xml text files in directory
        generic_files = list(game_dir.glob("**/*.json")) + list(game_dir.glob("**/*.csv")) + list(game_dir.glob("**/*.xml"))
        # Exclude common system/cache configs
        filtered = [f for f in generic_files if "node_modules" not in str(f) and ".cache" not in str(f)]
        return ("generic", filtered) if filtered else ("unknown", [])


class LocalTranslationMemory:
    """SQLite-based shared translation cache (Community/Local memory like Miqbas)."""
    
    def __init__(self, db_path: Path = Path("translations_memory.db")):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory (
                    original_hash TEXT PRIMARY KEY,
                    original_text TEXT,
                    arabic_translation TEXT,
                    game_tag TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @staticmethod
    def _hash(text: str) -> str:
        """Stable cross-session hash (python's hash() is randomized)."""
        return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[str]:
        h = self._hash(text)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT arabic_translation FROM memory WHERE original_hash = ?", (h,))
            row = cursor.fetchone()
            return row[0] if row else None

    def put(self, text: str, translation: str, game_tag: str = "general"):
        h = self._hash(text)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO memory (original_hash, original_text, arabic_translation, game_tag) VALUES (?, ?, ?, ?)",
                (h, text.strip(), translation.strip(), game_tag)
            )
            conn.commit()


class GameTextTranslator:
    """AI Localizer using Gemini with game tag and placeholder preservation."""

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model_name = model_name
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        self.memory = LocalTranslationMemory()

    def translate_batch(self, texts: List[str], game_name: str = "Game") -> List[str]:
        """Translates a batch of texts preserving game codes, tags, and formatting."""
        if not texts:
            return []

        results = [None] * len(texts)
        to_translate = []
        indices = []

        # Check local memory first
        for idx, text in enumerate(texts):
            cached = self.memory.get(text)
            if cached:
                results[idx] = cached
            else:
                to_translate.append({"id": idx, "text": text})
                indices.append(idx)

        if not to_translate:
            return [r if r is not None else "" for r in results]

        # Chunk into groups of 30 strings per Gemini request
        chunk_size = 30
        for i in range(0, len(to_translate), chunk_size):
            chunk = to_translate[i:i + chunk_size]
            prompt = f"""You are a professional video game localizer translating game texts for '{game_name}' into Modern Standard Arabic.

CRITICAL RULES:
1. PRESERVE ALL CODE, VARIABLES AND FORMATTING TAGS EXACTLY AS THEY ARE!
   Examples: {{0}}, {{player_name}}, %s, %d, \\n, <color=#fff>, [b], [/b], $gameVariables.
   NEVER translate or delete these tags!
2. Natural Gaming Arabic: Use immersive, idiomatic Arabic suitable for video games (dialogues, UI menus, quests, items).
3. Output strictly valid JSON array of objects: [{{"id": ..., "ar": "..."}}]
No explanations, no markdown.

Texts to translate:
{json.dumps(chunk, ensure_ascii=False, indent=2)}
"""
            try:
                response = self.model.generate_content(prompt)
                raw = response.text.strip()
                if raw.startswith("```"):
                    parts = raw.split("```")
                    if len(parts) >= 2:
                        raw = parts[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                raw = raw.strip()

                parsed = json.loads(raw)
                for item in parsed:
                    orig_idx = item.get("id")
                    ar_trans = item.get("ar", "").strip()
                    if orig_idx is not None and 0 <= orig_idx < len(texts):
                        results[orig_idx] = ar_trans
                        self.memory.put(texts[orig_idx], ar_trans, game_name)

            except Exception as e:
                print(f"[Warning] Translation chunk error: {e}")
                # Fallback to original text if API fails
                for c in chunk:
                    idx = c["id"]
                    if results[idx] is None:
                        results[idx] = c["text"]

        # Final fill for any missing items
        for idx in range(len(texts)):
            if results[idx] is None:
                results[idx] = texts[idx]

        return [r for r in results if r is not None]
