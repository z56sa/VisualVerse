"""
game_translator.py — ELECTRON Live Window Translator (experimental).

Real-time in-game translation HUD that never touches game files:
  * F9                -> capture the dialogue zone (or lower screen) and translate
  * Ctrl+Shift+F9     -> re-select the dialogue zone
  * Ctrl+Shift+F8     -> toggle full-screen capture mode
  * Ctrl+Shift+F10    -> toggle the automatic translation loop

Smart behaviours:
  * Translation memory (SQLite) - repeated dialogues never cost another API call
  * Frame hashing - identical screens are skipped entirely (no API burn)
  * Settings + zone geometry persist between sessions
  * Proper Arabic glyph shaping for the HUD (Tk does not do bidi reordering)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path

import mss
import keyboard
import tkinter as tk
from tkinter import ttk
from PIL import Image
from dotenv import load_dotenv
import warnings
warnings.filterwarnings("ignore")

import google.generativeai as genai

from game_localizer import LocalTranslationMemory

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

CONFIG_PATH = Path(os.getenv(
    "APPDATA", str(Path.home()))) / "Electron" / "overlay_config.json"

if API_KEY:
    genai.configure(api_key=API_KEY)

# -- Arabic shaping (Tk has no bidi engine; pre-shape for correct display) ----
try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    def shape_ar(text: str) -> str:
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
except Exception:  # lookup libraries not installed
    def shape_ar(text: str) -> str:
        return text


class Config:
    """Persistent HUD settings (zone, geometry, look & feel)."""

    DEFAULTS = {
        "zone": None,                  # [x, y, w, h] in screen coords
        "geometry": "760x180+280+780",
        "font_size": 15,
        "opacity": 0.90,
        "auto_delay": 2.2,             # seconds between auto scans
    }

    def __init__(self):
        self.data = dict(self.DEFAULTS)
        self._load()

    def _load(self):
        try:
            if CONFIG_PATH.exists():
                saved = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    self.data.update({k: v for k, v in saved.items()
                                      if k in self.DEFAULTS})
        except Exception:
            pass

    def save(self):
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception:
            pass

    def __getitem__(self, key):
        return self.data.get(key, self.DEFAULTS.get(key))

    def __setitem__(self, key, value):
        if key in self.DEFAULTS:
            self.data[key] = value


def shape(text):
    return shape_ar(text)


class GameZoneSelector:
    """Semi-transparent full-screen canvas to drag and select game dialogue box."""
    def __init__(self):
        self.selected_bbox = None

    def select_box(self):
        root = tk.Tk()
        root.attributes("-alpha", 0.3)
        root.attributes("-fullscreen", True)
        root.attributes("-topmost", True)
        root.config(cursor="cross")

        canvas = tk.Canvas(root, cursor="cross", bg="#111")
        canvas.pack(fill="both", expand=True)

        start_x = start_y = [0]
        rect = [None]

        def on_press(e):
            start_x[0], start_y[0] = e.x, e.y
            rect[0] = canvas.create_rectangle(e.x, e.y, e.x, e.y,
                                              outline="#00ffcc", width=3,
                                              fill="#000000")

        def on_drag(e):
            canvas.coords(rect[0], start_x[0], start_y[0], e.x, e.y)

        def on_release(e):
            x1, y1 = min(start_x[0], e.x), min(start_y[0], e.y)
            x2, y2 = max(start_x[0], e.x), max(start_y[0], e.y)
            if (x2 - x1) > 30 and (y2 - y1) > 20:
                self.selected_bbox = (x1, y1, x2 - x1, y2 - y1)
            root.destroy()

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        root.bind("<Escape>", lambda e: root.destroy())

        root.mainloop()
        return self.selected_bbox


class GameTranslatorOverlay(tk.Tk):
    """Always-on-top gaming HUD translating dialogues from screen captures."""

    A = {  # appearance palette
        "bg": "#0f111a", "header": "#1a1c29",
        "accent": "#00d2d3", "accent2": "#feca57", "busy": "#48dbfb",
        "ok": "#1dd1a1", "err": "#ff6b6b", "muted": "#8395a7", "text": "#ffffff",
    }

    def __init__(self):
        super().__init__()
        self.title("ELECTRON Live Translator")
        self.attributes("-topmost", True)
        self.overrideredirect(True)

        self.cfg = Config()
        self.geometry(str(self.cfg["geometry"]))

        self.memory = LocalTranslationMemory(Path("electron_memory.db"))
        zone = self.cfg["zone"]
        self.dialogue_box_bbox = tuple(zone) if zone else None
        self.fullscreen_mode = self.dialogue_box_bbox is None
        self.is_auto_translating = False
        self._auto_thread = None
        self._closing = False
        self._busy = threading.Lock()
        self._save_job = None
        self.last_frame_hash = ""
        self.last_original = ""

        self._build_fonts()
        self._build_ui()
        self._apply_opacity()
        self._setup_hotkeys()
        self._make_draggable()
        self.protocol("WM_DELETE_WINDOW", self._shutdown)

    # ------------------------------------------------------------- helpers
    def _build_fonts(self):
        size = int(self.cfg["font_size"])
        self.font_ar = ("Cairo", size, "bold")
        self.font_orig = ("Segoe UI", max(9, size - 5))
        self.font_hdr = ("Segoe UI", 10, "bold")
        self.font_btn = ("Segoe UI", 9, "bold")
        self.font_ctl = ("Segoe UI", 8)

    def _schedule_save(self):
        """Coalesce save calls (slider/drag spam) into one write."""
        if self._save_job is not None:
            self.after_cancel(self._save_job)
        self._save_job = self.after(700, self._save_now)

    def _save_now(self):
        self._save_job = None
        try:
            self.cfg["geometry"] = self.geometry()
            self.cfg["zone"] = list(self.dialogue_box_bbox) \
                if self.dialogue_box_bbox else None
        except Exception:
            pass
        self.cfg.save()

    def _status(self, text, ok=False):
        try:
            self.lbl_status.config(
                text=shape(text),
                fg=self.A["ok"] if ok else self.A["muted"])
        except Exception:
            pass

    def _msg(self, text, busy=False, err=False, ok=False):
        color = (self.A["busy"] if busy else self.A["err"] if err else
                 self.A["ok"] if ok else self.A["text"])
        try:
            self.lbl_arabic.config(text=shape(text), fg=color)
        except Exception:
            pass

    # ----------------------------------------------------------------- UI
    def _build_ui(self):
        self.configure(bg=self.A["bg"])

        # Header / draggable title bar
        self.header = tk.Frame(self, bg=self.A["header"], height=30)
        self.header.pack(fill="x")

        tk.Label(self.header, text="ELECTRON | مترجم الألعاب الحي",
                 bg=self.A["header"], fg=self.A["accent"],
                 font=self.font_hdr).pack(side="right", padx=10)

        def hbtn(text, color, cmd):
            b = tk.Label(self.header, text=shape(text), bg=self.A["header"],
                         fg=color, font=self.font_btn, cursor="hand2", padx=6)
            b.pack(side="left", padx=3)
            b.bind("<Button-1>", lambda e: cmd())
            return b

        hbtn("✕", self.A["err"], self._shutdown)
        self.btn_fullscr = hbtn("🖥 كامل الشاشة", self.A["text"],
                                self.toggle_fullscreen_mode)
        self.btn_zone = hbtn("🎯 تحديد منطقة", self.A["accent2"],
                             self.set_game_zone)
        self.btn_auto = hbtn("⚡ التلقائي", self.A["busy"],
                             self.toggle_auto_translate)

        # Controls row: opacity + font size
        controls = tk.Frame(self, bg=self.A["bg"], height=26)
        controls.pack(fill="x", padx=10, pady=(2, 0))

        tk.Label(controls, text="شفافية", bg=self.A["bg"], fg=self.A["muted"],
                 font=self.font_ctl).pack(side="right", padx=(6, 2))
        self.opacity_scale = ttk.Scale(controls, from_=0.35, to=1.0,
                                       value=float(self.cfg["opacity"]),
                                       length=100)
        self.opacity_scale.pack(side="right")
        self.opacity_scale.configure(command=self._on_opacity)

        tk.Label(controls, text="حجم الخط", bg=self.A["bg"], fg=self.A["muted"],
                 font=self.font_ctl).pack(side="right", padx=(12, 4))
        b_down = tk.Label(controls, text="A-", bg=self.A["bg"],
                          fg=self.A["text"], font=self.font_ctl, cursor="hand2")
        b_down.pack(side="right")
        b_down.bind("<Button-1>", lambda e: self._change_font(-1))
        b_up = tk.Label(controls, text="A+ ", bg=self.A["bg"], fg=self.A["text"],
                        font=self.font_ctl, cursor="hand2")
        b_up.pack(side="right")
        b_up.bind("<Button-1>", lambda e: self._change_font(+1))

        # Main translation display body
        self.body = tk.Frame(self, bg=self.A["bg"])
        self.body.pack(fill="both", expand=True, padx=12, pady=4)

        self.lbl_arabic = tk.Label(
            self.body, text=shape("اضغط [F9] وأنت باللعبة لترجمة الحوار فوراً | "
                                  "Ctrl+Shift+F9 لتحديد منطقة الحوار"),
            bg=self.A["bg"], fg=self.A["text"], font=self.font_ar,
            wraplength=720, justify="center", pady=4)
        self.lbl_arabic.pack(fill="both", expand=True)

        self.lbl_orig = tk.Label(self.body, text="", bg=self.A["bg"],
                                 fg=self.A["muted"], font=self.font_orig,
                                 wraplength=720, justify="center")
        self.lbl_orig.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(
            self, text=shape("جاهز — التقاط: " +
                             ("كامل الشاشة السفلي" if self.fullscreen_mode
                              else "منطقة محددة")),
            bg=self.A["bg"], fg=self.A["muted"], font=self.font_ctl)
        self.lbl_status.pack(fill="x", side="bottom", pady=(0, 2))

    def _change_font(self, delta):
        new_size = max(10, min(30, int(self.cfg["font_size"]) + delta))
        self.cfg["font_size"] = new_size
        self._schedule_save()
        self._build_fonts()
        self.lbl_arabic.config(font=self.font_ar)
        self.lbl_orig.config(font=self.font_orig)

    def _apply_opacity(self, alpha=None):
        value = alpha if alpha is not None else float(self.cfg["opacity"])
        try:
            self.attributes("-alpha", value)
        except Exception:
            pass

    def _on_opacity(self, value):
        v = round(float(value), 2)
        self.cfg["opacity"] = v
        self._apply_opacity(v)
        self._schedule_save()

    def _make_draggable(self):
        def start_move(e):
            self._drag = (e.x, e.y)

        def do_move(e):
            dx, dy = e.x - self._drag[0], e.y - self._drag[1]
            self.geometry(f"+{self.winfo_x() + dx}+{self.winfo_y() + dy}")
            self._schedule_save()

        self._drag = (0, 0)
        self.header.bind("<ButtonPress-1>", start_move)
        self.header.bind("<B1-Motion>", do_move)

    def _setup_hotkeys(self):
        try:
            keyboard.add_hotkey("F9", self.trigger_translation)
            keyboard.add_hotkey("ctrl+shift+f9", self.set_game_zone)
            keyboard.add_hotkey("ctrl+shift+f8", self.toggle_fullscreen_mode)
            keyboard.add_hotkey("ctrl+shift+f10", self.toggle_auto_translate)
        except Exception as e:
            self._status(f"تعذر تسجيل الاختصارات (جرب التشغيل كمسؤول): {e[:40]}")

    # ------------------------------------------------------------ capture
    def _capture_image(self):
        with mss.mss() as sct:
            if self.dialogue_box_bbox and not self.fullscreen_mode:
                x, y, w, h = self.dialogue_box_bbox
                monitor = {"left": int(x), "top": int(y),
                           "width": int(w), "height": int(h)}
            else:
                m = sct.monitors[1]
                monitor = {
                    "left": m["left"],
                    "top": m["top"] + int(m["height"] * 0.62),
                    "width": m["width"],
                    "height": int(m["height"] * 0.38),
                }
            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

        # frame fingerprint - small grayscale thumbnail hash
        small = img.convert("L").resize((48, 27))
        return img, hashlib.sha1(small.tobytes()).hexdigest()

    # ------------------------------------------------------------ actions
    def set_game_zone(self):
        self.withdraw()
        try:
            time.sleep(0.15)
            bbox = GameZoneSelector().select_box()
        finally:
            self.deiconify()

        if bbox:
            self.dialogue_box_bbox = bbox
            self._schedule_save()
            self._msg("✅ تم حفظ منطقة الحوار — اضغط [F9] للترجمة الفورية", ok=True)
            self._status("وضع الالتقاط: منطقة الحوار المحددة", ok=True)
        else:
            self._status("تم إلغاء تحديد المنطقة")

    def toggle_fullscreen_mode(self):
        self.fullscreen_mode = not self.fullscreen_mode
        self._status("وضع الالتقاط: كامل الشاشة السفلي"
                     if self.fullscreen_mode else "وضع الالتقاط: منطقة الحوار")
        self._schedule_save()

    def toggle_auto_translate(self):
        self.is_auto_translating = not self.is_auto_translating
        self.btn_auto.config(
            text=shape("⏹ إيقاف التلقائي" if self.is_auto_translating
                       else "⚡ التلقائي"),
            fg=self.A["err"] if self.is_auto_translating else self.A["busy"])
        if self.is_auto_translating and \
                (self._auto_thread is None or not self._auto_thread.is_alive()):
            self._auto_thread = threading.Thread(target=self._auto_loop, daemon=True)
            self._auto_thread.start()
        elif not self.is_auto_translating:
            self._status("تم إيقاف الترجمة التلقائية")

    def trigger_translation(self):
        threading.Thread(target=self._process_game_translation,
                         args=(True,), daemon=True).start()

    # ------------------------------------------------------------ pipeline
    def _auto_loop(self):
        while self.is_auto_translating and not self._closing:
            try:
                self._process_game_translation(force=False)
            except Exception:
                pass
            time.sleep(float(self.cfg["auto_delay"]))

    def _process_game_translation(self, force=True):
        if self._closing:
            return
        if not force and not self.is_auto_translating:
            return
        if not API_KEY:
            self._msg("❌ ضع مفتاح GEMINI_API_KEY في ملف .env أولاً!", err=True)
            return
        if not self._busy.acquire(blocking=False):
            return  # a call is already in flight

        try:
            self._msg("⏳ جارٍ قراءة شاشة اللعبة...", busy=True)
            img, frame_hash = self._capture_image()

            # Identical frame => skip the request entirely (auto mode)
            if not force and frame_hash == self.last_frame_hash:
                self._status("الشاشة لم تتغير — تخطي الطلب")
                return
            self.last_frame_hash = frame_hash

            original, arabic = self._semantic_translate(img)
            if not original and not arabic:
                self._msg("لم يتم رصد حوار في المنطقة المحددة")
                return

            # Same dialogue text => display previous result, no extra work
            if original and original == self.last_original:
                self._status("نفس الحوار السابق — بدون طلب جديد")
                return
            if original:
                self.last_original = original

            # Memory-first: cached dialogues cost zero API calls
            if not force and original:
                cached = self.memory.get(original)
                if cached:
                    arabic = cached

            if arabic:
                if original:
                    self.memory.put(original, arabic, "live_overlay")
                self._show_original = original
                self._display_result(original, arabic)
        finally:
            self._busy.release()

    def _semantic_translate(self, img):
        """Gemini Vision: OCR + translate in one call. Returns (original, arabic)."""
        prompt = [
            "You are an instant in-game dialogue translator.\n"
            "Extract the main dialogue/subtitle text shown in this game "
            "screen capture.\n"
            "Then translate it into natural, high-quality Arabic suitable "
            "for gaming subtitles (ترجمة حوارات ألعاب عربية سينمائية وسلسة "
            "ومتقنة).\n"
            'Return strictly valid JSON:\n'
            '{"original": "...", "arabic": "..."}\n'
            "If there is no dialogue text in the image, return empty strings."
        ]
        try:
            model = genai.GenerativeModel(MODEL_NAME)
            response = model.generate_content([*prompt, img])
            data = self._parse_json_response(response.text)
            return data.get("original", "").strip(), data.get("arabic", "").strip()
        except Exception as e:
            self._msg(f"خطأ: {str(e)[:60]}", err=True)
            return "", ""

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            if len(parts) >= 2:
                raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    # -------------------------------------------------------------- views
    def _display_result(self, original: str, arabic: str):
        self._msg(arabic)
        self.lbl_orig.config(text=f"Original: {original}" if original else "")
        self._status("✅ تمت الترجمة", ok=True)

    # ------------------------------------------------------------ shutdown
    def _shutdown(self):
        self._closing = True
        self.is_auto_translating = False
        try:
            self._save_now()
        except Exception:
            pass
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass


def main():
    app = GameTranslatorOverlay()
    app.mainloop()


if __name__ == "__main__":
    main()
