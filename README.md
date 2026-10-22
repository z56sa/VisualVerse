# Manga/Manhwa Arabic Translator (manga_ar)

A modular, high-performance desktop CLI pipeline to automatically translate manga, manhwa, and webtoon chapters into natural Modern Standard Arabic with RTL typesetting.

---

## 🌟 Key Features

- **Full Pipeline**: Image Loader $\to$ Speech Bubble Detection $\to$ Multimodal OCR $\to$ Gemini Comic Translation $\to$ Smart Inpainting $\to$ Arabic Bidi Typesetting.
- **Natural Arabic Dialogue**: Prompt engineering tuned for punchy, conversational Arabic suited for speech bubbles, avoiding stiff literal translations.
- **RTL Arabic Typesetting**: Automatic text reshaping (`arabic-reshaper`), Bidi reordering (`python-bidi`), word-wrapping, and binary search font auto-fitting.
- **Smart Inpainting**: Fast solid-background detection for white manga bubbles + OpenCV Telea inpainting for textured/patterned backgrounds.
- **Zero Heavy Installs**: Relies on Gemini Vision for high-accuracy Japanese/Korean/Chinese OCR without requiring local C++ dependencies or heavy setups on Windows.
- **Caching & Manual Correction**: Results are cached per-image hash. Easily export `translations.json`, edit lines manually, and run `render` to re-draw.
- **Input Flexibility**: Supports folders of images (`.png`, `.jpg`, `.webp`) or `.cbz` / `.zip` archives.

---

## 🛠️ Windows Setup Guide

### 1. Requirements
- Windows 10 or 11
- Python 3.11 or newer

### 2. Installation
Open PowerShell in the project directory:

```powershell
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Setup Gemini API Key
1. Go to [Google AI Studio](https://aistudio.google.com/) and create a free API key.
2. Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
3. Open `.env` and fill in your key:
```ini
GEMINI_API_KEY=AIzaSy...YourKeyHere
GEMINI_MODEL=gemini-1.5-flash
SOURCE_LANG=ja
```

### 4. Arabic Font Installation
By default, the tool will automatically locate and use standard Windows fonts (`seguiemj.ttf`, `arial.ttf`, or `tahoma.ttf`).

For authentic comic lettering, we recommend downloading a comic or display font from Google Fonts (e.g., **Noto Sans Arabic** or **Lalezar** or **Changa**):
1. Download a font `.ttf` file.
2. Place it in the project directory (e.g. `fonts/NotoSansArabic-Bold.ttf`).
3. Pass it via the `--font` flag.

---

## 🚀 Usage & CLI Commands

### 1. Translate Chapter (Full Pipeline)
Translates all pages in a folder, saves translated pages to `./out`, exports an editable `translations.json`, and caches the results:

```powershell
python main.py translate --input ./chapter1 --output ./out --source ja --glossary glossary.json
```

**Options:**
- `--input`, `-i`: Folder containing images, a single image file, or a `.cbz` / `.zip` file.
- `--output`, `-o`: Directory where translated images will be saved.
- `--source`, `-s`: Source language (`ja` for Japanese, `ko` for Korean, `zh` for Chinese, `en` for English).
- `--glossary`, `-g`: Path to JSON file mapping original terms/names to Arabic.
- `--font`, `-f`: Custom Arabic `.ttf` font path.
- `--cbz`: Additionally bundle the translated pages into a `.cbz` archive.
- `--skip-sfx`: Ignore sound effects and non-dialogue text.

---

### 2. Debug Mode (Visual Inspection)
Detects all bubbles and text boxes, draws colored bounding boxes and IDs, and saves them for inspection:

```powershell
python main.py debug --input ./chapter1 --output ./debug_out
```

---

### 3. Manual Correction & Re-rendering
If you want to fine-tune translations or edit specific lines without re-calling the API:
1. Run `translate` first; it will generate `out/translations.json`.
2. Open `out/translations.json` in any text editor and adjust any Arabic text.
3. Re-render the pages with the updated text:

```powershell
python main.py render --input ./chapter1 --translations ./out/translations.json --output ./final_out
```

---

## 📖 Glossary Support (`glossary.json`)
You can define a series-specific dictionary for consistent character names and terminology:

```json
{
  "Luffy": "لوفي",
  "Zoro": "زورو",
  "Nami": "نامي",
  "Sensei": "أستاذ"
}
```

---

## 📂 Architecture Overview

```
manga_ar/
├── main.py          # CLI entry point (translate, debug, render)
├── config.py        # Central configuration (Pydantic / dotenv)
├── loader.py        # Archive & image loader with natural sorting
├── detector.py      # Speech bubble and text cluster detection
├── ocr.py           # Gemini Vision Multimodal OCR
├── translator.py    # Contextual Arabic comic translation engine
├── inpaint.py       # Bubble background sampling & OpenCV inpainting
├── typeset.py       # Bidi & Arabic reshaping with binary search auto-fit
├── cache.py         # SHA256 image-level caching
├── requirements.txt # Dependencies
├── .env.example     # Environment template
└── README.md        # Documentation
```

---

# 🎮 ELECTRON | Game Engine Localizer (Game Localization Platform)

The same AI pipeline extended to **computer games at engine level**: press Primary one button on
(at engine level), FIRST translate + inject Arabic fonts + full Manual Translation Editor.
Launch it with `Launch_Electron.bat` or `python electron_ui.py`.

## 🔌 Engine Support Status

| Engine | Method | Files | Status |
|---|---|---|---|
| **Unity (Mono/IL2CPP)** | `winhttp.dll` + BepInEx + XUnity AutoTranslator | `_AutoGeneratedTranslations.txt` | ✅ Full (live injection) |
| **Unreal Engine 4/5** | binary `.locres` parse/rewrite (all versions: Legacy→CityHash/UE5) | `Localization/**/Game.locres` | ✅ New: `ue_locres.py` |
| **RPG Maker MV/MZ** | surgical event patching (code 401/405/102/101/320/324/325) + Arabic `@font-face` injection | `data/*.json` + `css/main.css` | ✅ New: `rpgmaker_patcher.py` |
| **Generic (Paradox/RenPy/M&B)** | XML/CSV/JSON string patcher with `{0}`/`%s`/`<color>` guard | `Languages/**`, `*.csv` | ✅ Existing |

### Unreal Engine specifics
- Selects the **culture the game runs in** (`en`, `en-US`, `en-GB` folders first, then primary `Game.locres`).
- Exports the full strings table to an editable sidecar (`ElectronLoc/en_Game.json`) — the manual editor loads it instantly.
- One-click pass auto-translates up to 200 strings via Gemini (memory-cached) then rebuilds the binary atomically (`*.locres.tmp → replace`).
- Pristine original preserved as `*.locres.orig_backup`; **Restore** returns the game byte-exact.

### RPG Maker specifics
- Translates **only player-facing positions**: dialogue lines, scroll text, choice lists, speaker
  names (MZ), actor name/nickname/profile, System.json (title, currency, elements, terms...).
- `note` fields and event scripting are never touched.
- Escape codes (`\C[2]`, `\N[1]`, `\I[10]`, `\V[4]`, `\{`, `\\`...) must survive translation in
  order — translations that drop them are rejected and kept for manual editing.
- Injects an Arabic-capable font (EngineHooks cache → fallback Segoe UI/Tahoma/Arial) through
  `css/main.css` so Arabic actually renders instead of tofu boxes.

## 🪟 Live Window Translator (experimental HUD)
`python game_translator.py` — or the «🎮 تشغيل الترجمة الحية» button in the Live panel.

| Hotkey | Action |
|---|---|
| `F9` | Capture the dialogue zone and translate (OCR + Arabic in a single Gemini call) |
| `Ctrl+Shift+F9` | Re-select the dialogue zone |
| `Ctrl+Shift+F8` | Toggle full-screen capture mode |
| `Ctrl+Shift+F10` | Toggle the automatic loop |

Smart behaviours: SQLite translation memory (`electron_memory.db`) so replayed dialogues cost
zero API calls, frame hashing to skip unchanged screens, persistent zone/geometry/opacity/font
settings, and proper Arabic glyph shaping (`arabic-reshaper` + `bidi`).

## 🛡️ Safety Model (Anti-Cheat aware)
- Steam/Epic/GOG scanning automatically excludes online/competitive titles (Fortnite, Rust,
  Rocket League, Valorant...) — only singleplayer/offline games are offered by default.
- Every patched file keeps a first-run `.orig_backup`; the Restore button returns the game to
  its original state in one click.
- The overlay path touches **no** game files at all (safest for online-friendly ones).

## 🧪 Test Suite (offline, no API key needed)
```
python test_ue_locres.py      # binary locres roundtrip + Arabic utf-16
python test_rpgmaker.py       # event extraction, code preservation, font injection
python test_integration.py    # full ElectronApi flows incl. editor + restore
```

## 📦 New dependency (Unreal support)
```
pip install pylocres           # .locres binary container (MIT), pulls binsl
```
Already listed in `requirements.txt`.
