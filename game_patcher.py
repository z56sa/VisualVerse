import os
import re
import csv
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Tuple, Any

from game_localizer import GameTextTranslator

class GamePatcher:
    """Extracts strings from game files, translates them, and patches them back."""

    def __init__(self, translator: GameTextTranslator):
        self.translator = translator

    @staticmethod
    def create_backup(file_path: Path) -> Path:
        backup_path = file_path.with_suffix(file_path.suffix + ".orig_backup")
        if not backup_path.exists():
            shutil.copy2(file_path, backup_path)
        return backup_path

    @staticmethod
    def restore_backup(file_path: Path) -> bool:
        backup_path = file_path.with_suffix(file_path.suffix + ".orig_backup")
        if backup_path.exists():
            shutil.copy2(backup_path, file_path)
            return True
        return False

    def patch_json_file(self, json_file: Path, game_name: str) -> int:
        """Extracts text strings from a JSON game file, translates and updates in place."""
        self.create_backup(json_file)
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        strings_to_translate = []
        locators = []  # Pointer paths to update in data

        def collect_strings(obj, path):
            if isinstance(obj, str):
                # Only translate actual sentences/words, avoid codes/ids/paths
                cleaned = obj.strip()
                if len(cleaned) > 1 and not cleaned.startswith("http") and not cleaned.endswith((".png", ".jpg", ".ogg", ".wav")):
                    strings_to_translate.append(cleaned)
                    locators.append(path)
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    collect_strings(v, path + [k])
            elif isinstance(obj, list):
                for i, v in enumerate(obj):
                    collect_strings(v, path + [i])

        collect_strings(data, [])

        if not strings_to_translate:
            return 0

        translated = self.translator.translate_batch(strings_to_translate, game_name)

        # Patch translated texts back into data structure
        for path, trans_text in zip(locators, translated):
            curr = data
            for p in path[:-1]:
                curr = curr[p]
            curr[path[-1]] = trans_text

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return len(strings_to_translate)

    def patch_csv_file(self, csv_file: Path, game_name: str) -> int:
        """Extracts and patches CSV localization files."""
        self.create_backup(csv_file)
        rows = []
        with open(csv_file, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            return 0

        # Usually column 1 or last column contains the display text
        texts = []
        indices = []
        for r_idx, row in enumerate(rows):
            if len(row) >= 2 and row[1].strip():
                texts.append(row[1].strip())
                indices.append((r_idx, 1))

        if not texts:
            return 0

        translated = self.translator.translate_batch(texts, game_name)
        for (r_idx, c_idx), ar_text in zip(indices, translated):
            rows[r_idx][c_idx] = ar_text

        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        return len(texts)

    def patch_xml_file(self, xml_file: Path, game_name: str) -> int:
        """Extracts and patches XML localization (Mount & Blade / Paradox)."""
        self.create_backup(xml_file)
        tree = ET.parse(xml_file)
        root = tree.getroot()

        elements = []
        texts = []
        for elem in root.iter():
            # Check string tag or text attribute
            if elem.text and elem.text.strip():
                txt = elem.text.strip()
                if len(txt) > 1 and not txt.startswith("{"):
                    texts.append(txt)
                    elements.append((elem, "text"))
            elif "text" in elem.attrib and elem.attrib["text"].strip():
                txt = elem.attrib["text"].strip()
                texts.append(txt)
                elements.append((elem, "attrib"))

        if not texts:
            return 0

        translated = self.translator.translate_batch(texts, game_name)
        for (elem, target_type), ar_text in zip(elements, translated):
            if target_type == "text":
                elem.text = ar_text
            else:
                elem.attrib["text"] = ar_text

        tree.write(xml_file, encoding="utf-8", xml_declaration=True)
        return len(texts)
