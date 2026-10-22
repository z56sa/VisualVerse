import hashlib
import json
from pathlib import Path
from typing import Any, Optional, Dict

class CacheManager:
    """Manages page-level caching using image content hashing."""
    
    def __init__(self, cache_dir: Path = Path(".cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "manga_cache.json"
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def compute_image_hash(image_path: Path) -> str:
        """Compute SHA256 hash of an image file."""
        hasher = hashlib.sha256()
        with open(image_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def get_entry(self, img_hash: str) -> Optional[Dict[str, Any]]:
        return self._data.get(img_hash)

    def set_entry(self, img_hash: str, entry: Dict[str, Any]) -> None:
        self._data[img_hash] = entry
        self.save()

    def export_translations(self, output_path: Path) -> None:
        """Export all cached translations to an editable JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def import_translations(self, json_path: Path) -> None:
        """Import edited translations into the cache."""
        with open(json_path, "r", encoding="utf-8") as f:
            imported = json.load(f)
            self._data.update(imported)
        self.save()
