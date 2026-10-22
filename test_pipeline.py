import unittest
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

from config import PipelineConfig
from cache import CacheManager
from loader import MangaLoader
from detector import OpenCVBubbleDetector, TextRegion
from inpaint import BubbleInpainter
from typeset import ArabicTypesetter

class TestMangaPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_data")
        self.test_dir.mkdir(exist_ok=True)
        
        # Create a synthetic comic page: white background with two speech bubbles
        self.test_img_path = self.test_dir / "sample_page.png"
        img = Image.new("RGB", (600, 800), color=(220, 220, 220))
        draw = ImageDraw.Draw(img)
        
        # Bubble 1 (top right)
        draw.ellipse([350, 100, 550, 250], fill=(255, 255, 255), outline=(0, 0, 0), width=3)
        draw.text((400, 160), "TEST DIALOGUE", fill=(0, 0, 0))
        
        # Bubble 2 (bottom left)
        draw.ellipse([50, 450, 300, 650], fill=(255, 255, 255), outline=(0, 0, 0), width=3)
        draw.text((100, 520), "ANOTHER TEXT", fill=(0, 0, 0))
        
        img.save(self.test_img_path)

    def tearDown(self):
        # Cleanup test files
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_loader(self):
        loader = MangaLoader(self.test_dir)
        self.assertGreaterEqual(len(loader.image_paths), 1)
        loader.cleanup()

    def test_detector_and_inpaint(self):
        img = Image.open(self.test_img_path)
        detector = OpenCVBubbleDetector()
        regions = detector.detect(img)
        self.assertGreaterEqual(len(regions), 1)

        inpainter = BubbleInpainter(mode="auto")
        cleaned = inpainter.inpaint(img, regions)
        self.assertIsNotNone(cleaned)

    def test_arabic_typesetting(self):
        img = Image.open(self.test_img_path)
        typesetter = ArabicTypesetter()
        regions = [
            TextRegion(id=0, bbox=(350, 100, 200, 150), is_bubble=True),
            TextRegion(id=1, bbox=(50, 450, 250, 200), is_bubble=True),
        ]
        translations = {
            0: "مرحباً بك في عالم المانجا المترجمة!",
            1: "هذه جملة عربية تجريبية للتأكد من المحاذاة والتنسيق السليم."
        }
        rendered = typesetter.typeset_page(img, regions, translations)
        self.assertIsNotNone(rendered)
        out_path = self.test_dir / "rendered_output.png"
        rendered.save(out_path)
        self.assertTrue(out_path.exists())

if __name__ == "__main__":
    unittest.main()
