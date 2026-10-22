import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Generator, List, Tuple
import re

try:
    from natsort import natsorted
except ImportError:
    # Built-in lightweight natural sort fallback
    def natsorted(seq, key=lambda x: x):
        def natural_key(item):
            val = str(key(item))
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', val)]
        return sorted(seq, key=natural_key)

from PIL import Image

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

class MangaLoader:
    """Loads images from a folder, ZIP, or CBZ archive with natural sorting."""

    def __init__(self, input_path: Path):
        self.input_path = Path(input_path)
        self._temp_dir: tempfile.TemporaryDirectory | None = None
        self.image_paths: List[Path] = self._resolve_images()

    def _resolve_images(self) -> List[Path]:
        if not self.input_path.exists():
            raise FileNotFoundError(f"Input path does not exist: {self.input_path}")

        # If it's a zip or cbz archive, extract to temp dir
        if self.input_path.is_file() and self.input_path.suffix.lower() in [".zip", ".cbz"]:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="manga_ar_")
            extract_to = Path(self._temp_dir.name)
            with zipfile.ZipFile(self.input_path, "r") as archive:
                archive.extractall(extract_to)
            search_dir = extract_to
        elif self.input_path.is_dir():
            search_dir = self.input_path
        elif self.input_path.is_file() and self.input_path.suffix.lower() in IMAGE_EXTENSIONS:
            return [self.input_path]
        else:
            raise ValueError(f"Unsupported file format: {self.input_path}")

        found_images: List[Path] = []
        for root, _, files in os.walk(search_dir):
            for file in files:
                p = Path(root) / file
                if p.suffix.lower() in IMAGE_EXTENSIONS:
                    found_images.append(p)

        # Sort naturally (e.g. page_1, page_2, ..., page_10)
        return natsorted(found_images, key=lambda p: str(p.name))

    def get_valid_pages(self) -> Generator[Tuple[int, Path, Image.Image], None, None]:
        """Yields (index, file_path, PIL Image), skipping unreadable/corrupted files gracefully."""
        for idx, img_path in enumerate(self.image_paths):
            try:
                with Image.open(img_path) as img:
                    # Convert to RGB mode for consistent downstream processing
                    rgb_img = img.convert("RGB")
                    yield idx, img_path, rgb_img
            except Exception as e:
                print(f"[Warning] Failed to load image {img_path}: {e}")

    def cleanup(self) -> None:
        """Clean up extracted temporary files if any."""
        if self._temp_dir:
            self._temp_dir.cleanup()
            self._temp_dir = None

    @staticmethod
    def create_cbz(folder_path: Path, output_cbz_path: Path) -> Path:
        """Packages a folder of images into a CBZ archive."""
        output_cbz_path = Path(output_cbz_path)
        if output_cbz_path.suffix.lower() != ".cbz":
            output_cbz_path = output_cbz_path.with_suffix(".cbz")

        with zipfile.ZipFile(output_cbz_path, "w", zipfile.ZIP_DEFLATED) as cbz:
            images = [
                p for p in folder_path.iterdir()
                if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
            ]
            for img_file in natsorted(images, key=lambda p: p.name):
                cbz.write(img_file, arcname=img_file.name)
        return output_cbz_path
