from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple, Optional
import cv2
import numpy as np
from PIL import Image

@dataclass
class TextRegion:
    id: int
    bbox: Tuple[int, int, int, int]  # (x, y, w, h)
    is_bubble: bool = True
    is_sfx: bool = False
    confidence: float = 1.0

class BaseDetector(ABC):
    """Abstract interface for text and bubble detectors."""
    
    @abstractmethod
    def detect(self, image: Image.Image) -> List[TextRegion]:
        """Detect text bubbles/regions on a PIL image."""
        pass

class OpenCVBubbleDetector(BaseDetector):
    """
    Lightweight, fast CPU/GPU OpenCV detector for comic speech bubbles and text regions.
    Identifies high-contrast text clusters and light-background speech bubble contours.
    """
    
    def __init__(self, skip_sfx: bool = False, min_area: int = 300, max_area_ratio: float = 0.5):
        self.skip_sfx = skip_sfx
        self.min_area = min_area
        self.max_area_ratio = max_area_ratio

    def detect(self, image: Image.Image) -> List[TextRegion]:
        img_np = np.array(image.convert("RGB"))
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        h, w = gray.shape
        total_area = h * w

        # 1. Detect bright speech bubbles (common in manga/manhwa)
        # Threshold for high brightness background
        _, thresh = cv2.threshold(gray, 230, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        detected_boxes: List[Tuple[int, int, int, int, bool]] = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if self.min_area < area < (total_area * self.max_area_ratio):
                bx, by, bw, bh = cv2.boundingRect(cnt)
                # Aspect ratio check
                aspect = max(bw / max(bh, 1), bh / max(bw, 1))
                is_sfx = aspect > 4.0
                detected_boxes.append((bx, by, bw, bh, is_sfx))

        # 2. Text stroke edge detection (MSER / Gradient for text regions outside bright bubbles)
        grad_x = cv2.Sobel(gray, cv2.CV_16S, 1, 0)
        grad_y = cv2.Sobel(gray, cv2.CV_16S, 0, 1)
        abs_grad = cv2.convertScaleAbs(cv2.addWeighted(cv2.convertScaleAbs(grad_x), 0.5, cv2.convertScaleAbs(grad_y), 0.5, 0))
        _, text_thresh = cv2.threshold(abs_grad, 40, 255, cv2.THRESH_BINARY)
        text_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
        dilated = cv2.dilate(text_thresh, text_kernel, iterations=2)
        
        text_contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in text_contours:
            area = cv2.contourArea(cnt)
            if 400 < area < (total_area * 0.25):
                bx, by, bw, bh = cv2.boundingRect(cnt)
                # Overlap suppression with already detected bubbles
                overlaps = False
                for existing in detected_boxes:
                    ex, ey, ew, eh, _ = existing
                    # Check intersection over union / inclusion
                    if not (bx + bw < ex or bx > ex + ew or by + bh < ey or by > ey + eh):
                        overlaps = True
                        break
                if not overlaps:
                    aspect = max(bw / max(bh, 1), bh / max(bw, 1))
                    is_sfx = aspect > 3.5
                    detected_boxes.append((bx, by, bw, bh, is_sfx))

        # Sort reading order (Top-Right to Bottom-Left for standard manga reading order)
        # We sort by Y (rows) and then X descending (RTL reading)
        detected_boxes.sort(key=lambda b: (b[1] // 100, -b[0]))

        regions: List[TextRegion] = []
        region_id = 0
        for bx, by, bw, bh, is_sfx in detected_boxes:
            if self.skip_sfx and is_sfx:
                continue
            regions.append(
                TextRegion(
                    id=region_id,
                    bbox=(bx, by, bw, bh),
                    is_bubble=not is_sfx,
                    is_sfx=is_sfx
                )
            )
            region_id += 1

        return regions

class ONNXBubbleDetector(BaseDetector):
    """Placeholder wrapper for pre-trained Comic-Text-Detector or YOLO ONNX models."""
    def __init__(self, model_path: str):
        self.model_path = model_path
        # Will load onnxruntime session dynamically if path provided
        
    def detect(self, image: Image.Image) -> List[TextRegion]:
        # Fallback to OpenCV detector if model path is invalid
        fallback = OpenCVBubbleDetector()
        return fallback.detect(image)
