import os
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
from detector import TextRegion

class ArabicTypesetter:
    """Renders RTL Arabic text nicely fitted and centered inside comic speech bubbles."""

    def __init__(
        self,
        font_path: Optional[str] = None,
        min_font_size: int = 12,
        max_font_size: int = 46,
        font_color: Tuple[int, int, int] = (0, 0, 0),
        stroke_color: Tuple[int, int, int] = (255, 255, 255),
        stroke_width: int = 2,
        line_spacing: float = 1.2,
        padding_ratio: float = 0.08
    ):
        self.font_path = self._resolve_font_path(font_path)
        self.min_font_size = min_font_size
        self.max_font_size = max_font_size
        self.font_color = font_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width
        self.line_spacing = line_spacing
        self.padding_ratio = padding_ratio

    def _resolve_font_path(self, user_font: Optional[str]) -> str | None:
        if user_font and Path(user_font).exists():
            return user_font

        # Common Windows Arabic fonts as sensible fallbacks
        windows_font_candidates = [
            "C:/Windows/Fonts/seguiemj.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/tahoma.ttf",
            "C:/Windows/Fonts/calibri.ttf",
        ]
        for candidate in windows_font_candidates:
            if Path(candidate).exists():
                return candidate
        return None

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if self.font_path:
            try:
                return ImageFont.truetype(self.font_path, size=size)
            except Exception:
                pass
        return ImageFont.load_default()

    def _format_arabic(self, text: str) -> str:
        """Reshapes Arabic letters (joining) and applies Bidirectional RTL reordering."""
        if not text:
            return ""
        # Configure reshaper for comprehensive ligature support
        configuration = {
            'delete_harakat': False,
            'support_ligatures': True,
        }
        reshaper = arabic_reshaper.ArabicReshaper(configuration=configuration)
        reshaped_text = reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text

    def _wrap_text(self, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
        """Wraps text into lines that fit within max_width at word boundaries."""
        words = text.split()
        if not words:
            return []

        lines: List[str] = []
        current_line: List[str] = []

        for word in words:
            test_line = " ".join(current_line + [word])
            # Measure width
            formatted = self._format_arabic(test_line)
            bbox = font.getbbox(formatted)
            line_w = bbox[2] - bbox[0]

            if line_w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                    current_line = [word]
                else:
                    # Single word exceeds width, force it
                    lines.append(word)
                    current_line = []

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def _text_fits(self, lines: List[str], font: ImageFont.ImageFont, max_w: int, max_h: int) -> bool:
        if not lines:
            return True
        total_h = 0
        for line in lines:
            formatted = self._format_arabic(line)
            bbox = font.getbbox(formatted)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            if w > max_w:
                return False
            total_h += int(h * self.line_spacing)
        return total_h <= max_h

    def _find_best_font_size(self, text: str, max_w: int, max_h: int) -> Tuple[int, List[str]]:
        """Binary search for largest font size where wrapped text fits in box."""
        low = self.min_font_size
        high = self.max_font_size
        best_size = low
        best_lines: List[str] = [text]

        while low <= high:
            mid = (low + high) // 2
            font = self._get_font(mid)
            wrapped = self._wrap_text(text, font, max_w)
            
            if self._text_fits(wrapped, font, max_w, max_h):
                best_size = mid
                best_lines = wrapped
                low = mid + 1  # Try larger
            else:
                high = mid - 1 # Try smaller

        return best_size, best_lines

    def typeset_page(
        self,
        image: Image.Image,
        regions: List[TextRegion],
        translations: dict[int, str]
    ) -> Image.Image:
        """Typesets all translated texts into their corresponding regions on the image."""
        output = image.copy()
        draw = ImageDraw.Draw(output)

        for region in regions:
            text = translations.get(region.id, "").strip()
            if not text:
                continue

            bx, by, bw, bh = region.bbox
            pad_x = int(bw * self.padding_ratio)
            pad_y = int(bh * self.padding_ratio)

            avail_w = max(10, bw - 2 * pad_x)
            avail_h = max(10, bh - 2 * pad_y)

            # Find best fitting font size
            font_size, lines = self._find_best_font_size(text, avail_w, avail_h)
            font = self._get_font(font_size)

            # Calculate total block height
            line_heights = []
            for line in lines:
                formatted = self._format_arabic(line)
                bbox = font.getbbox(formatted)
                line_heights.append(bbox[3] - bbox[1])
            
            line_step = max(line_heights) if line_heights else font_size
            total_block_h = len(lines) * int(line_step * self.line_spacing)

            # Center text vertically in bubble
            start_y = by + pad_y + max(0, (avail_h - total_block_h) // 2)

            curr_y = start_y
            for line in lines:
                formatted_line = self._format_arabic(line)
                bbox = font.getbbox(formatted_line)
                lw = bbox[2] - bbox[0]
                
                # Center horizontally
                curr_x = bx + pad_x + max(0, (avail_w - lw) // 2)

                # Draw stroke if not a standard bubble or configured
                draw_stroke = not region.is_bubble or self.stroke_width > 0
                stroke_w = self.stroke_width if draw_stroke else 0

                draw.text(
                    (curr_x, curr_y),
                    formatted_line,
                    font=font,
                    fill=self.font_color,
                    stroke_width=stroke_w,
                    stroke_fill=self.stroke_color if stroke_w > 0 else None
                )
                curr_y += int(line_step * self.line_spacing)

        return output
