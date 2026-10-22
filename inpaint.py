from typing import List, Tuple
import cv2
import numpy as np
from PIL import Image
from detector import TextRegion

class BubbleInpainter:
    """Removes original text from speech bubbles using smart background filling or OpenCV inpaint."""

    def __init__(self, mode: str = "auto", solid_tolerance: int = 25):
        self.mode = mode
        self.solid_tolerance = solid_tolerance

    def _is_near_solid(self, region_crop: np.ndarray) -> Tuple[bool, Tuple[int, int, int]]:
        """
        Samples the perimeter of the bounding box to find the bubble background color
        and checks if variance is low.
        """
        h, w = region_crop.shape[:2]
        if h < 4 or w < 4:
            return True, (255, 255, 255)

        # Sample border pixels (top, bottom, left, right edges)
        top = region_crop[0, :]
        bottom = region_crop[-1, :]
        left = region_crop[:, 0]
        right = region_crop[:, -1]
        border_pixels = np.concatenate([top, bottom, left, right], axis=0)

        # Compute median color and standard deviation across color channels
        median_color = np.median(border_pixels, axis=0).astype(int)
        std_dev = np.std(border_pixels, axis=0).mean()

        is_solid = std_dev < self.solid_tolerance
        return is_solid, (int(median_color[0]), int(median_color[1]), int(median_color[2]))

    def inpaint(self, image: Image.Image, regions: List[TextRegion]) -> Image.Image:
        """Removes original text from the specified regions on the image."""
        if not regions:
            return image

        img_bgr = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
        img_h, img_w = img_bgr.shape[:2]

        # Create overall inpainting mask for complex regions
        inpaint_mask = np.zeros((img_h, img_w), dtype=np.uint8)
        need_cv2_inpaint = False

        for r in regions:
            x, y, w, h = r.bbox
            x1 = max(0, x)
            y1 = max(0, y)
            x2 = min(img_w, x + w)
            y2 = min(img_h, y + h)

            if x2 <= x1 or y2 <= y1:
                continue

            crop = img_bgr[y1:y2, x1:x2]
            is_solid, bg_color = self._is_near_solid(crop)

            if self.mode == "solid" or (self.mode == "auto" and is_solid):
                # Smart solid fill: fill bubble text interior with sampled background color
                # Add a small 1px border margin to keep bubble contour intact
                pad_x = max(1, int(w * 0.04))
                pad_y = max(1, int(h * 0.04))
                inner_x1 = min(img_w, x1 + pad_x)
                inner_y1 = min(img_h, y1 + pad_y)
                inner_x2 = max(inner_x1, x2 - pad_x)
                inner_y2 = max(inner_y1, y2 - pad_y)

                cv2.rectangle(img_bgr, (inner_x1, inner_y1), (inner_x2, inner_y2), bg_color, thickness=-1)
            else:
                # Text inside patterned or screentone background: use cv2 inpainting
                need_cv2_inpaint = True
                gray_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                # Text strokes usually deviate significantly from median background
                median_val = np.median(gray_crop)
                diff = np.abs(gray_crop.astype(float) - median_val).astype(np.uint8)
                _, text_mask = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
                
                # Dilate slightly to cover text edges
                kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                text_mask = cv2.dilate(text_mask, kernel, iterations=1)
                inpaint_mask[y1:y2, x1:x2] = np.maximum(inpaint_mask[y1:y2, x1:x2], text_mask)

        if need_cv2_inpaint and np.any(inpaint_mask > 0):
            # Apply OpenCV Telea inpainting
            img_bgr = cv2.inpaint(img_bgr, inpaint_mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)

        rgb_result = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb_result)
