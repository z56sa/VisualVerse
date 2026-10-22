from pathlib import Path
from typing import Optional, Literal
import os
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load .env file automatically if present
load_dotenv()

class PipelineConfig(BaseModel):
    # Gemini API settings
    gemini_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    gemini_model: str = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    )
    
    # Language and processing settings
    source_lang: Literal["ja", "ko", "zh", "en", "auto"] = Field(
        default_factory=lambda: os.getenv("SOURCE_LANG", "ja") # type: ignore
    )
    target_lang: str = "ar"
    
    # Device
    device: Literal["auto", "cpu", "cuda"] = Field(
        default_factory=lambda: os.getenv("DEVICE", "auto") # type: ignore
    )
    
    # Typesetting & Fonts
    font_path: Optional[str] = None
    min_font_size: int = 12
    max_font_size: int = 48
    font_color: tuple[int, int, int] = (0, 0, 0) # Black
    stroke_color: tuple[int, int, int] = (255, 255, 255) # White outline
    stroke_width: int = 2
    line_spacing: float = 1.15
    padding_ratio: float = 0.08  # Bubble inner margin
    
    # Inpainting & Detection
    inpaint_mode: Literal["auto", "solid", "telea", "ns"] = "auto"
    solid_color_tolerance: int = 25  # Max standard deviation to consider solid
    skip_sfx: bool = False
    sfx_aspect_ratio_threshold: float = 4.0
    
    # Output settings
    save_cbz: bool = False
    debug: bool = False
    cache_dir: Path = Path(".cache")
    glossary_path: Optional[Path] = None

    def get_effective_device(self) -> str:
        if self.device != "auto":
            return self.device
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"
