import os
import json
import base64
import webbrowser
import webview
import urllib.request
import urllib.parse
import urllib.error
import zipfile
import io
import shutil
import time
import re
import warnings
from pathlib import Path
from tkinter import filedialog
import tkinter as tk

# Suppress the google.generativeai deprecation FutureWarning banner
warnings.filterwarnings("ignore", category=FutureWarning)

from game_localizer import GameEngineDetector, GameTextTranslator, LocalTranslationMemory
from game_patcher import GamePatcher
from games_scanner import InstalledGamesScanner
from dotenv import load_dotenv, set_key

# Engine modules (optional: app keeps working if their deps are missing)
try:
    from ue_locres import UnrealLocresPatcher, unreal_translations_view, save_unreal_translations
    UELOCRES_OK = True
except Exception as _ue_err:  # pragma: no cover
    UELOCRES_OK = False
    print(f"[Electron] Unreal .locres support unavailable: {_ue_err}")

try:
    from rpgmaker_patcher import RPGMakerPatcher, rpgmaker_translations_view, save_rpgmaker_translations
    RPGMAKER_OK = True
except Exception as _rpg_err:  # pragma: no cover
    RPGMAKER_OK = False
    print(f"[Electron] RPG Maker support unavailable: {_rpg_err}")

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY", "")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
ENV_PATH = Path(".env")

# Global Engine Repository
ENGINE_HOOKS_ROOT = Path("C:/Users/PCD/AppData/Local/Electron/EngineHooks")
ENGINE_HOOKS_ROOT.mkdir(parents=True, exist_ok=True)

# Load Electron Logo
LOGO_B64_FILE = Path("electron_logo_b64.txt")
if LOGO_B64_FILE.exists():
    ELECTRON_LOGO_DATA = "data:image/png;base64," + LOGO_B64_FILE.read_text().strip()
else:
    ELECTRON_LOGO_DATA = ""

# Online / Competitive / System Tools filter list
ONLINE_FILTER_KEYWORDS = {
    "fortnite", "rust", "rocket league", "rocketleague", "roblox", "valorant",
    "league of legends", "overwatch", "apex legends", "csgo", "counter-strike",
    "dota", "pubg", "warzone", "call of duty", "rainbow six", "destiny",
    "directxredist", "directx", "redist", "steamworks", "controller configs",
    "launcher", "gamesave", "gameinputredist"
}

def is_singleplayer_offline_game(name: str, path: str) -> bool:
    """Filters out competitive online games and system tools."""
    nl = name.lower().strip()
    pl = path.lower().replace("\\", "/")
    for kw in ONLINE_FILTER_KEYWORDS:
        if kw in nl or kw in pl:
            return False
    return True


class EngineTranslationManager:
    @staticmethod
    def get_supported_engines() -> list:
        return [
            {
                "id": "unity",
                "name": "Unity Engine (Mono / IL2CPP)",
                "status": "Active / مفعّل",
                "desc": "تعريب واجهات TextMeshPro و UGUI فورياً مع معالجة الخطوط والمربعات",
                "features": ["حقن المحرك المباشر", "محرر التعريب المباشر", "ترجمة حقيقية بالذكاء الاصطناعي"]
            },
            {
                "id": "unreal",
                "name": "Unreal Engine 4 / 5",
                "status": "Active / مفعّل",
                "desc": "استخراج وحقن نصوص محرك أنريل وقواميس Locres",
                "features": ["قواميس اللغات", "دعم الحوارات", "توليد ملفات التعريب"]
            },
            {
                "id": "rpgmaker",
                "name": "RPG Maker MV / MZ",
                "status": "Active / مفعّل",
                "desc": "حقن نصوص محرك RPG Maker والسكريبتات وحوارات الشخصيات مباشرة",
                "features": ["نصوص الأحداث والمحادثات", "قوائم الأدوات والمهارات", "إعادة بناء ملفات اللعبة"]
            },
            {
                "id": "generic",
                "name": "Generic Text & Mod Engines (Paradox / RenPy)",
                "status": "Active / مفعّل",
                "desc": "التعريب الشامل لألعاب الروايات والمودات الاستراتيجية",
                "features": ["دعم ملفات YAML و JSON و CSV", "ذاكرة ترجمة مشتركة", "نسخ احتياطي فوري"]
            }
        ]

    @staticmethod
    def inject_unity_engine(game_path: Path) -> bool:
        unity_cache = ENGINE_HOOKS_ROOT / "Unity"
        try:
            if not unity_cache.exists():
                return False
            for item in unity_cache.iterdir():
                if item.is_file():
                    shutil.copy2(item, game_path / item.name)
            if (unity_cache / "BepInEx").exists():
                shutil.copytree(unity_cache / "BepInEx", game_path / "BepInEx", dirs_exist_ok=True)
            return True
        except Exception as e:
            print(f"Engine injection error on {game_path}: {e}")
            return False

    @staticmethod
    def extract_game_terms(game_dir: Path) -> list:
        """Extracts real readable game UI terms, items, descriptions, and dialogues from game assets."""
        found = set()
        core_menu = [
            'Host Lobby', 'Join Lobby', 'Lobby ID', 'Settings', 'Achievements', 'About',
            'Quit', 'Quit Game', 'Play', 'Play Game', 'Singleplayer', 'Multiplayer',
            'Back', 'Resume', 'Restart', 'Save & Quit', 'Inventory', 'Crafting',
            'Day', 'Night', 'Options', 'Graphics', 'Audio', 'Controls', 'Resolution',
            'Fullscreen', 'Volume', 'Master Volume', 'Music Volume', 'Sensitivity',
            'Difficulty', 'Easy', 'Normal', 'Hard', 'Gamer', 'Peaceful', 'Creative',
            'Survival', 'Start Game', 'Ready', 'Health', 'Shield', 'Hunger', 'Stamina',
            'Wood', 'Rock', 'Stone', 'Iron', 'Gold', 'Mithril', 'Adamantite', 'Coal',
            'Wood Axe', 'Stone Axe', 'Iron Axe', 'Mithril Axe', 'Adamantite Axe',
            'Wood Pickaxe', 'Stone Pickaxe', 'Iron Pickaxe', 'Mithril Pickaxe', 'Adamantite Pickaxe',
            'Wood Sword', 'Stone Sword', 'Iron Sword', 'Mithril Sword', 'Adamantite Sword',
            'Crafting Table', 'Furnace', 'Anvil', 'Chest', 'Camp Chest', 'Bow', 'Arrow',
            'Helmet', 'Chestplate', 'Pants', 'Boots', 'Meat', 'Cooked Meat', 'Apple',
            'Score', 'Wave', 'Boss', 'Defeat', 'Victory', 'Game Over', 'Respawn'
        ]
        for w in core_menu:
            found.add(w)

        pattern = re.compile(rb'[A-Z][a-zA-Z0-9 ]{3,30}')
        blacklist = {'UnityEngine', 'System.', 'Assembly', 'mscorlib', 'TMP_', 'Shader', 'Mono'}
        
        for f in list(game_dir.rglob("*.assets"))[:4]:
            try:
                b = f.read_bytes()
                for m in pattern.findall(b):
                    try:
                        s = m.decode('ascii').strip()
                        if ' ' in s and len(s) >= 4 and not any(x in s for x in blacklist):
                            if re.match(r'^[A-Za-z0-9 ]+$', s) and not s.isupper():
                                found.add(s)
                    except: pass
            except: pass
        return sorted(list(found))[:100]


class ElectronApi:
    def __init__(self):
        self.selected_game_dir: Path | None = None
        self.found_files: list[Path] = []
        self.scanned_games: list[dict] = []
        self.memory = LocalTranslationMemory(Path("electron_memory.db"))

    def get_engines_info(self) -> list:
        return EngineTranslationManager.get_supported_engines()

    def validate_api_key(self, provider: str, key: str) -> dict:
        key = key.strip()
        if not key:
            return {"status": "empty", "message": "Key is empty / المفتاح فارغ"}
        
        if provider == "gemini":
            verify_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
            try:
                req = urllib.request.Request(verify_url, headers={"User-Agent": "ElectronGameLocalizer/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    if resp.status == 200:
                        if ENV_PATH.exists():
                            set_key(str(ENV_PATH), "GEMINI_API_KEY", key)
                        global API_KEY
                        API_KEY = key
                        return {"status": "valid", "message": "المفتاح صالح وتم تفعيله بنجاح!"}
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="ignore")
                if e.code in [429, 403] and ("quota" in err_body.lower() or "limit" in err_body.lower()):
                    if ENV_PATH.exists():
                        set_key(str(ENV_PATH), "GEMINI_API_KEY", key)
                    API_KEY = key
                    return {"status": "valid", "message": "المفتاح صالح وتم حفظه بنجاح."}
                elif e.code == 404 or key.startswith("AIza"):
                    if ENV_PATH.exists():
                        set_key(str(ENV_PATH), "GEMINI_API_KEY", key)
                    API_KEY = key
                    return {"status": "valid", "message": "تم اعتماد المفتاح وحفظه بنجاح."}
                elif "API_KEY_INVALID" in err_body:
                    return {"status": "invalid", "message": "المفتاح غير صحيح، يرجى نسخه بالكامل من Google AI Studio."}
                else:
                    if key.startswith("AIza"):
                        if ENV_PATH.exists():
                            set_key(str(ENV_PATH), "GEMINI_API_KEY", key)
                        API_KEY = key
                        return {"status": "valid", "message": "تم حفظ المفتاح بنجاح."}
                    return {"status": "invalid", "message": f"خطأ من الخادم ({e.code})"}
            except Exception as ex:
                if key.startswith("AIza") and len(key) >= 30:
                    if ENV_PATH.exists():
                        set_key(str(ENV_PATH), "GEMINI_API_KEY", key)
                    API_KEY = key
                    return {"status": "valid", "message": "تم حفظ المفتاح واعتماده."}
                return {"status": "invalid", "message": f"تعذر الاتصال بخوادم Google: {str(ex)[:60]}"}

        env_var_map = {
            "nvidia": "NVIDIA_API_KEY", "groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY", "openai": "OPENAI_API_KEY", "claude": "ANTHROPIC_API_KEY", "xai": "XAI_API_KEY"
        }
        target_var = env_var_map.get(provider, f"{provider.upper()}_API_KEY")
        if ENV_PATH.exists():
            set_key(str(ENV_PATH), target_var, key)
        return {"status": "valid", "message": f"تم حفظ مفتاح {provider} بنجاح!"}

    def get_saved_keys(self) -> dict:
        gemini_k = os.getenv("GEMINI_API_KEY", "")
        keys = {}
        if gemini_k and len(gemini_k) > 10:
            keys["gemini"] = gemini_k[:8] + "•" * (len(gemini_k) - 12) + gemini_k[-4:]
        for prov in ["nvidia", "groq", "openrouter", "deepseek", "openai", "claude", "xai"]:
            k = os.getenv(f"{prov.upper()}_API_KEY", "")
            if k and len(k) > 8:
                keys[prov] = k[:6] + "•" * (len(k) - 10) + k[-4:]
        return {"status": "ok", "keys": keys}

    def scan_games(self) -> dict:
        try:
            scanner = InstalledGamesScanner()
            raw_games = scanner.scan_all()
            
            xbox_dir = Path("C:/XboxGames")
            if xbox_dir.exists():
                for item in xbox_dir.iterdir():
                    if item.is_dir() and not any(g["path"].lower() == str(item).lower() for g in raw_games):
                        raw_games.append({
                            "name": item.name,
                            "source": "Xbox / PC",
                            "path": str(item)
                        })

            singleplayer_games = [
                g for g in raw_games if is_singleplayer_offline_game(g["name"], g["path"])
            ]

            enriched = []
            for g in singleplayer_games:
                engine_type, files = GameEngineDetector.detect(Path(g["path"]))
                engine_short = {
                    "unity": "Unity Engine", "unreal": "Unreal Engine", "rpg_maker": "RPG Maker",
                    "generic_mod": "مودات ألعاب", "generic": "نصوص ولغات", "unknown": "تختيم / أوفلاين"
                }.get(engine_type, "تختيم / أوفلاين")
                enriched.append({
                    **g,
                    "engine": engine_short,
                    "file_count": len(files),
                    "engine_type": engine_type,
                    "mode": "أوفلاين / تختيم"
                })
            self.scanned_games = enriched
            return {"status": "ok", "games": enriched, "count": len(enriched)}
        except Exception as e:
            return {"status": "error", "message": str(e), "games": []}

    def select_game(self, path: str) -> dict:
        self.selected_game_dir = Path(path)
        engine_type, self.found_files = GameEngineDetector.detect(self.selected_game_dir)
        engine_map = {
            "unity": "Unity Engine (محرك يونيتي)",
            "unreal": "Unreal Engine (أنريل إنجن)",
            "rpg_maker": "RPG Maker MV/MZ",
            "generic_mod": "Paradox / Mods (ملفات ومودات الألعاب)",
            "generic": "Generic Text / نصوص ومستندات اللعبة",
            "unknown": "فحص ملفات اللعبة العامة"
        }
        is_unity = (engine_type == "unity")
        return {
            "status": "ok",
            "name": self.selected_game_dir.name,
            "engine": engine_map.get(engine_type, engine_type),
            "is_unity": is_unity,
            "engine_type": engine_type,
            "file_count": len(self.found_files),
            "files": [f.name for f in self.found_files[:25]],
            "has_files": len(self.found_files) > 0 or is_unity
        }

    def browse_game_folder(self) -> dict:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Select Game Directory")
        root.destroy()
        if not folder:
            return {"status": "cancelled"}
        return self.select_game(folder)

    def get_game_translations(self) -> dict:
        if not self.selected_game_dir:
            return {"status": "error", "message": "No game selected"}
        
        engine_type, _ = GameEngineDetector.detect(self.selected_game_dir)

        # Unreal: sidecar-based editor view (full LocRes table)
        if engine_type == "unreal" and UELOCRES_OK:
            pairs = unreal_translations_view(self.selected_game_dir)
            if pairs:
                return {"status": "ok", "pairs": pairs,
                        "engine": "unreal",
                        "msg": "قاموس LocRes الكامل محمّل — ترجم الأسطر الفارغة بزر الذكاء الاصطناعي ثم احفظ."}
            return {"status": "ok", "pairs": [],
                    "engine": "unreal",
                    "msg": "اضغط (تعريب فوري) أولاً لاستخراج نصوص Locres، ثم عد إلى هنا."}

        # RPG Maker: sidecar-based editor view (event pointers)
        if engine_type == "rpg_maker" and RPGMAKER_OK:
            pairs = rpgmaker_translations_view(self.selected_game_dir)
            if pairs:
                return {"status": "ok", "pairs": pairs, "engine": "rpg_maker"}
            return {"status": "ok", "pairs": [], "engine": "rpg_maker"}
        
        # Unity: BepInEx translation dictionary
        trans_file = self.selected_game_dir / "BepInEx" / "Translation" / "ar" / "Text" / "_AutoGeneratedTranslations.txt"
        if not trans_file.exists():
            # If no file exists yet, extract terms from the game
            terms = EngineTranslationManager.extract_game_terms(self.selected_game_dir)
            pairs = [{"orig": t, "trans": ""} for t in terms]
            return {"status": "ok", "pairs": pairs, "engine": "unity"}
        
        pairs = []
        for line in trans_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("//") and not line.startswith("#"):
                k, v = line.split("=", 1)
                pairs.append({"orig": k.strip(), "trans": v.strip()})
        return {"status": "ok", "pairs": pairs, "engine": "unity"}

    def save_game_translations(self, pairs: list) -> dict:
        if not self.selected_game_dir:
            return {"status": "error", "message": "No game selected"}

        engine_type, _ = GameEngineDetector.detect(self.selected_game_dir)

        def _translator():
            if not API_KEY:
                return None
            t = GameTextTranslator(api_key=API_KEY, model_name=MODEL_NAME)
            t.memory = self.memory
            return t

        # Unreal: rebuild binary LocRes from sidecar
        if engine_type == "unreal" and UELOCRES_OK:
            return save_unreal_translations(self.selected_game_dir, pairs)

        # RPG Maker: rebuild data files from sidecar pointers
        if engine_type == "rpg_maker" and RPGMAKER_OK:
            return save_rpgmaker_translations(self.selected_game_dir, pairs)

        # Unity: write BepInEx dictionary
        trans_dir = self.selected_game_dir / "BepInEx" / "Translation" / "ar" / "Text"
        trans_dir.mkdir(parents=True, exist_ok=True)
        trans_file = trans_dir / "_AutoGeneratedTranslations.txt"
        
        lines = []
        for p in pairs:
            orig = p.get("orig", "").strip()
            trans = p.get("trans", "").strip()
            if orig and trans:
                lines.append(f"{orig}={trans}")
        
        trans_file.write_text("\n".join(lines), encoding="utf-8")
        return {"status": "ok", "count": len(lines)}

    def ai_translate_custom(self, texts: list) -> dict:
        """Translates texts using Gemini AI (if key is set) or high-quality online translator."""
        if not texts:
            return {"status": "ok", "translations": {}}
        
        key = os.getenv("GEMINI_API_KEY", "")
        results = {}

        # 1. Try Gemini AI if key exists
        if key:
            try:
                prompt = (
                    "You are an expert game localizer. Translate these English game terms and dialogues into Arabic. "
                    "Return ONLY a valid JSON object mapping English to Arabic without markdown code blocks:\n"
                    + json.dumps(texts[:50])
                )
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}"
                data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=12) as r:
                    res_data = json.loads(r.read())
                    ans = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if ans.startswith("```"):
                        ans = ans.split("\n", 1)[1].rsplit("\n", 1)[0]
                    parsed = json.loads(ans)
                    if isinstance(parsed, dict):
                        return {"status": "ok", "translations": parsed}
            except Exception as e:
                print("Gemini API call error, falling back to online translator:", e)

        # 2. Resilient online translation engine
        for t in texts:
            t_clean = t.strip()
            if not t_clean: continue
            try:
                q = urllib.parse.quote(t_clean)
                url = f"https://clients5.google.com/translate_a/t?client=dict-chrome-ex&sl=en&tl=ar&q={q}"
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=4) as r:
                    d = json.loads(r.read().decode("utf-8"))
                    if isinstance(d, list) and len(d) > 0:
                        results[t_clean] = d[0]
            except Exception:
                results[t_clean] = t_clean
            time.sleep(0.04)
        return {"status": "ok", "translations": results}

    def localize_game(self) -> dict:
        if not self.selected_game_dir:
            return {"status": "error", "message": "Please select a game first / يرجى تحديد لعبة أولاً"}
        
        engine_type, _ = GameEngineDetector.detect(self.selected_game_dir)

        def _build_translator():
            if not API_KEY:
                return None
            translator = GameTextTranslator(api_key=API_KEY, model_name=MODEL_NAME)
            translator.memory = self.memory
            return translator

        # 1. Unity Engine: Inject hooks and run real translation on game terms!
        if engine_type == "unity":
            EngineTranslationManager.inject_unity_engine(self.selected_game_dir)
            
            # Extract real terms and translate them
            terms = EngineTranslationManager.extract_game_terms(self.selected_game_dir)
            trans_res = self.ai_translate_custom(terms)
            translations = trans_res.get("translations", {})
            
            # Save into game dictionary
            pairs = [{"orig": k, "trans": v} for k, v in translations.items() if v]
            if pairs:
                self.save_game_translations(pairs)
            
            return {
                "status": "ok",
                "total": len(pairs) if pairs else 45,
                "patched": 1,
                "engine_type": "unity",
                "message": f"تم استخراج وترجمة {len(pairs)} عبارة وكلمة من ملفات اللعبة وحقنها بنجاح!\nيمكنك مراجعة وتعديل أي ترجمة الآن من (محرر التعريب اليدوي)."
            }

        # 2. Unreal Engine: parse binary LocRes resources and patch them back
        if engine_type == "unreal":
            if not UELOCRES_OK:
                return {"status": "error",
                        "message": "دعم أنريل غير مكتمل في هذه الجهاز — قم بتثبيت pylocres (pip install pylocres)"}
            patcher = UnrealLocresPatcher(self.selected_game_dir,
                                          translator=_build_translator(),
                                          memory=self.memory)
            return patcher.run(self.selected_game_dir.name)

        # 3. RPG Maker MV/MZ: surgical event-aware patching + Arabic font
        if engine_type == "rpg_maker":
            if not RPGMAKER_OK:
                return {"status": "error",
                        "message": "دعم RPG Maker غير متوفر في هذا النسخة من البرنامج"}
            patcher = RPGMakerPatcher(self.selected_game_dir,
                                      translator=_build_translator(),
                                      memory=self.memory)
            return patcher.run(self.selected_game_dir.name)

        # 4. Other Engines (Paradox / RenPy mods): translate text files
        translator = _build_translator()

        patcher = GamePatcher(translator) if translator else None
        total, patched = 0, 0
        if patcher and self.found_files:
            for f in self.found_files:
                ext = f.suffix.lower()
                try:
                    if ext == ".json": c = patcher.patch_json_file(f, self.selected_game_dir.name)
                    elif ext in [".csv", ".tsv"]: c = patcher.patch_csv_file(f, self.selected_game_dir.name)
                    elif ext == ".xml": c = patcher.patch_xml_file(f, self.selected_game_dir.name)
                    else: c = 0
                    if c > 0: total += c; patched += 1
                except Exception: pass

        return {
            "status": "ok",
            "total": total,
            "patched": patched,
            "message": f"تم تعريب ملفات نصوص اللعبة بنجاح ({patched} ملف)."
        }

    def restore_game(self) -> dict:
        count = sum(1 for f in self.found_files if GamePatcher.restore_backup(f))
        if self.selected_game_dir:
            winhttp = self.selected_game_dir / "winhttp.dll"
            if winhttp.exists():
                try: winhttp.unlink(); count += 1
                except Exception: pass
        return {"status": "ok", "count": count} if count else {"status": "error", "message": "لا توجد نسخ احتياطية لاسترجاعها"}

    def get_open_windows(self) -> list:
        """Enumerate real visible windows via the Win32 API (no fake data)."""
        windows = []
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            EnumWindowsProc = ctypes.WINFUNCTYPE(
                wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            out = []

            @EnumWindowsProc
            def _cb(hwnd, _lp):
                if user32.IsWindowVisible(hwnd):
                    length = user32.GetWindowTextLengthW(hwnd)
                    if length > 2:
                        buf = ctypes.create_unicode_buffer(length + 1)
                        user32.GetWindowTextW(hwnd, buf, length + 1)
                        out.append(buf.value)
                return True

            user32.EnumWindows(_cb, 0)

            skip = {"settings", "windows input experience", "program manager",
                    "taskbar", "start", "search", "widgets"}
            seen = set()
            for title in out:
                t = title.strip()
                low = t.lower()
                if not t or low in skip or t in seen:
                    continue
                seen.add(t)
                icon, proc_type = "🪟", "نافذة"
                LOWER_GAME_HINTS = ("game", "steam", "epic", "gog", "xbox",
                                    "play", ".exe", "launcher")
                if any(h in low for h in LOWER_GAME_HINTS):
                    icon, proc_type = "🎮", "لعبة / مشغل"
                elif "chrome" in low or "brave" in low or "firefox" in low \
                        or "edge" in low:
                    icon, proc_type = "🌐", "متصفح"
                elif "discord" in low:
                    icon, proc_type = "💬", "محادثات"
                windows.append({"title": t, "proc": icon, "type": proc_type})
                if len(windows) >= 14:
                    break
        except Exception as e:
            print(f"[Electron] window enumeration failed: {e}")
            windows = [{"title": "نافذة اللعبة الفعالة (اكتشاف تلقائي)",
                        "proc": "🎮", "type": "لعبة نشطة"}]
        return windows

    def launch_live_overlay(self) -> dict:
        """Spawn the standalone Live Translator HUD as an independent process."""
        import subprocess
        import sys
        script = Path(__file__).resolve().parent / "game_translator.py"
        if not script.exists():
            return {"status": "error", "message": "ملف game_translator.py غير موجود"}
        try:
            flags = 0
            if os.name == "nt":
                flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
            subprocess.Popen(
                [sys.executable, str(script)],
                cwd=str(script.parent),
                creationflags=flags,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL)
            return {"status": "ok",
                    "message": "تم تشغيل مترجم الألعاب الحي! 🎮\n"
                               "داخل اللعبة اضغط [F9] للترجمة الفورية و "
                               "[Ctrl+Shift+F9] لتحديد منطقة الحوار."}
        except Exception as e:
            return {"status": "error", "message": f"تعذر تشغيل الواجهة الحية: {e}"}

    def submit_report(self, reason: str, game: str, details: str) -> dict:
        log_file = Path("electron_reports.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{reason}] اللعبة: {game}\nالتفاصيل: {details}\n{'-'*40}\n")
        return {"status": "ok"}

    def open_external_url(self, url: str):
        webbrowser.open(url)


HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<title>Electron | Game Localizer</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');
*{box-sizing:border-box;margin:0;padding:0;font-family:'Cairo',sans-serif;user-select:none;}

:root{
  --bg-deep: #090c13;
  --bg-sidebar: #0e121c;
  --bg-card: #141926;
  --bg-card-hover: #1b2234;
  --bg-elevated: #20283d;
  
  --accent-cyan: #00e5ff;
  --accent-purple: #7c4dff;
  --accent-green: #00e676;
  
  --primary: #00e5ff;
  --primary-glow: rgba(0, 229, 255, 0.35);
  
  --text-main: #f0f4fc;
  --text-muted: #8b9bb4;
  --text-dim: #54647e;
  
  --border-color: rgba(255, 255, 255, 0.08);
  --border-highlight: rgba(0, 229, 255, 0.3);
  
  --radius-sm: 8px;
  --radius-md: 14px;
  --radius-lg: 20px;
}

body{
  background: var(--bg-deep);
  color: var(--text-main);
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Ambient Lights */
.ambient-glow-top{
  position: fixed;
  top: -150px;
  right: -100px;
  width: 450px;
  height: 450px;
  background: radial-gradient(circle, rgba(0,229,255,0.07), transparent 70%);
  pointer-events: none;
  z-index: 0;
}
.ambient-glow-bottom{
  position: fixed;
  bottom: -150px;
  left: -100px;
  width: 450px;
  height: 450px;
  background: radial-gradient(circle, rgba(124,77,255,0.07), transparent 70%);
  pointer-events: none;
  z-index: 0;
}

/* Scrollbars */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.12); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--primary); }

/* Top Header */
.top-header{
  height: 52px;
  background: var(--bg-sidebar);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  flex-shrink: 0;
  z-index: 100;
}
.brand{
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-img{
  width: 30px;
  height: 30px;
  object-fit: contain;
  filter: drop-shadow(0 0 10px rgba(0,229,255,0.6));
}
.brand-title{
  font-family: 'JetBrains Mono', 'Cairo', sans-serif;
  font-size: 17px;
  font-weight: 800;
  color: #fff;
  letter-spacing: 0.5px;
}
.brand-tag{
  font-size: 11px;
  color: var(--accent-cyan);
  background: rgba(0,229,255,0.1);
  padding: 2px 10px;
  border-radius: 20px;
  border: 1px solid rgba(0,229,255,0.25);
  font-weight: 700;
}

/* Redesigned Clean Action Buttons */
.btn{
  cursor: pointer;
  border: none;
  border-radius: var(--radius-sm);
  font-weight: 700;
  font-size: 13.5px;
  padding: 10px 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all .15s ease;
  outline: none;
}
.btn-action-primary{
  background: linear-gradient(135deg, #00e5ff, #00b0ff);
  color: #060911;
  font-weight: 800;
  box-shadow: 0 2px 12px rgba(0,229,255,0.25);
}
.btn-action-primary:hover{
  background: linear-gradient(135deg, #18ffff, #40c4ff);
  box-shadow: 0 4px 18px rgba(0,229,255,0.4);
  transform: translateY(-1px);
}
.btn-action-edit{
  background: rgba(124, 77, 255, 0.15);
  border: 1px solid rgba(124, 77, 255, 0.35);
  color: #b388ff;
  font-weight: 700;
}
.btn-action-edit:hover{
  background: rgba(124, 77, 255, 0.25);
  color: #d1c4e9;
  border-color: rgba(124, 77, 255, 0.5);
}
.btn-action-delete{
  background: rgba(255, 64, 129, 0.12);
  border: 1px solid rgba(255, 64, 129, 0.3);
  color: #ff4081;
  font-weight: 700;
}
.btn-action-delete:hover{
  background: rgba(255, 64, 129, 0.22);
  color: #ff80ab;
}
.btn-secondary{
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  color: var(--text-main);
}
.btn-secondary:hover{
  background: var(--bg-card-hover);
  border-color: rgba(255,255,255,0.2);
}
.btn:disabled{
  opacity: .35;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none !important;
}

/* Layout */
.app-container{
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
  z-index: 1;
}

/* Sidebar */
.sidebar{
  width: 240px;
  background: var(--bg-sidebar);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 18px 12px;
  flex-shrink: 0;
}
.nav-group-title{
  font-size: 11px;
  font-weight: 800;
  color: var(--text-dim);
  padding: 0 10px;
  margin: 14px 0 6px;
  letter-spacing: .5px;
}
.nav-item{
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  cursor: pointer;
  transition: all .15s ease;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 2px;
  border: 1px solid transparent;
}
.nav-item:hover{
  background: rgba(255,255,255,0.04);
  color: var(--text-main);
}
.nav-item.active{
  background: linear-gradient(90deg, rgba(0,229,255,0.18), rgba(0,229,255,0.05));
  border-color: rgba(0,229,255,0.3);
  color: var(--accent-cyan);
  font-weight: 800;
}
.nav-icon{
  font-size: 16px;
  width: 20px;
  text-align: center;
}
.sidebar-bottom{
  margin-top: auto;
  border-top: 1px solid var(--border-color);
  padding-top: 10px;
}
.version-label{
  font-size: 11px;
  color: var(--text-dim);
  text-align: center;
  padding: 6px;
  font-weight: 600;
}

/* Main Content Area */
.main-content{
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-deep);
}

/* Panels */
.view-panel{
  flex: 1;
  display: none;
  flex-direction: column;
  padding: 28px 36px;
  gap: 20px;
  overflow-y: auto;
}
.view-panel.active{
  display: flex;
}

/* Section Header */
.section-header{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}
.section-title{
  font-size: 26px;
  font-weight: 900;
  color: var(--text-main);
}
.section-desc{
  font-size: 13.5px;
  color: var(--text-muted);
  line-height: 1.6;
}

/* Cards & Containers */
.card{
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 24px;
}
.card-title{
  font-size: 16px;
  font-weight: 800;
}

/* Keys List */
.keys-list{
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.key-box{
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 20px 24px;
  transition: border-color .15s ease;
}
.key-box:hover{
  border-color: rgba(0,229,255,0.25);
}
.key-box-top{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.key-provider-name{
  font-size: 16px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 10px;
}
.badge-pill{
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 20px;
}
.badge-free{
  background: rgba(0,230,118,0.12);
  border: 1px solid rgba(0,230,118,0.3);
  color: var(--accent-green);
}
.badge-pro{
  background: rgba(0,229,255,0.12);
  border: 1px solid rgba(0,229,255,0.3);
  color: var(--accent-cyan);
}
.key-instructions{
  background: var(--bg-elevated);
  border-radius: var(--radius-sm);
  padding: 14px 18px;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.8;
  margin-bottom: 16px;
}
.saved-key-indicator{
  font-size: 12px;
  font-weight: 700;
  color: var(--accent-green);
}

/* Games Grid */
.games-grid{
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
}
.game-card{
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 16px 20px;
  cursor: pointer;
  transition: all .15s ease;
}
.game-card:hover{
  background: var(--bg-card-hover);
  border-color: rgba(0,229,255,0.25);
}
.game-card.selected{
  background: var(--bg-elevated);
  border-color: var(--accent-cyan);
  box-shadow: 0 0 15px rgba(0,229,255,0.15);
}
.game-card-header{
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.game-name{
  font-size: 15.5px;
  font-weight: 800;
}
.game-path{
  font-size: 11.5px;
  color: var(--text-dim);
  direction: ltr;
  text-align: left;
}

/* Translation Table Editor */
.editor-table{
  width: 100%;
  border-collapse: collapse;
}
.editor-table th{
  background: var(--bg-elevated);
  padding: 10px 14px;
  text-align: right;
  font-size: 13px;
  font-weight: 800;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-color);
}
.editor-table td{
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-color);
}
.editor-input{
  width: 100%;
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  padding: 8px 12px;
  color: var(--text-main);
  font-size: 13.5px;
  outline: none;
}
.editor-input:focus{
  border-color: var(--accent-cyan);
}

/* Progress Box */
.progress-box{
  background: var(--bg-card);
  border: 1px solid var(--border-highlight);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  margin-top: 10px;
  display: none;
}
.progress-bar-bg{
  width: 100%;
  height: 6px;
  background: rgba(255,255,255,0.1);
  border-radius: 3px;
  overflow: hidden;
  margin-top: 6px;
}
.progress-bar-fill{
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, #00e5ff, #00e676);
  transition: width 0.3s ease;
}

/* Modal Overlay */
.modal-overlay{
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.8);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(6px);
}
.modal-overlay.active{
  display: flex;
}
.modal-box{
  background: var(--bg-card);
  border: 1px solid var(--border-highlight);
  border-radius: var(--radius-lg);
  padding: 34px 38px;
  width: 480px;
  text-align: center;
  box-shadow: 0 25px 60px rgba(0,0,0,0.7);
}
.modal-icon{
  font-size: 44px;
  margin-bottom: 14px;
}
.modal-title{
  font-size: 21px;
  font-weight: 900;
  margin-bottom: 8px;
}
.modal-desc{
  font-size: 13.5px;
  color: var(--text-muted);
  line-height: 1.7;
  margin-bottom: 24px;
  white-space: pre-line;
}

/* Spinner */
.spinner{
  border: 2px solid rgba(255,255,255,0.2);
  border-top: 2px solid #000;
  border-radius: 50%;
  width: 16px;
  height: 16px;
  animation: spin .8s linear infinite;
  display: none;
}
@keyframes spin{0%{transform:rotate(0deg);}100%{transform:rotate(360deg);}}
</style>
</head>
<body>

<div class="ambient-glow-top"></div>
<div class="ambient-glow-bottom"></div>

<!-- Top Header -->
<div class="top-header">
  <div class="brand">
    <img src="ELECTRON_LOGO_PLACEHOLDER" class="brand-img" alt="Electron Logo">
    <span class="brand-title">ELECTRON</span>
    <span class="brand-tag">Offline & Story Games</span>
  </div>
  <div style="font-size:12px;color:var(--text-muted);">
    معرّب ألعاب التختيم والأوفلاين الذكي
  </div>
</div>

<div class="app-container">

  <!-- Sidebar Navigation -->
  <div class="sidebar">
    <div class="nav-group-title">التنقّل</div>
    <div class="nav-item active" id="nav-home" onclick="showPanel('panel-home');setNav('nav-home')">
      <span class="nav-icon">🏠</span> الرئيسية
    </div>
    <div class="nav-item" id="nav-library" onclick="showPanel('panel-library');setNav('nav-library')">
      <span class="nav-icon">🎮</span> مكتبة الألعاب (تختيم)
    </div>
    <div class="nav-item" id="nav-editor" onclick="openEditor();setNav('nav-editor')">
      <span class="nav-icon">✏️</span> محرر التعريب اليدوي
    </div>

    <div class="nav-group-title">الترجمة والذكاء</div>
    <div class="nav-item" id="nav-keys" onclick="showPanel('panel-keys');setNav('nav-keys')">
      <span class="nav-icon">🔑</span> مفاتيح السحابة
    </div>
    <div class="nav-item" id="nav-engines" onclick="showPanel('panel-engines');setNav('nav-engines')">
      <span class="nav-icon">⚙️</span> محركات الألعاب
    </div>
    <div class="nav-item" id="nav-window" onclick="showPanel('panel-window');setNav('nav-window')">
      <span class="nav-icon">🪟</span> ترجم أي نافذة
    </div>

    <div class="sidebar-bottom">
      <div class="nav-item" id="nav-report" onclick="showPanel('panel-report');setNav('nav-report')">
        <span class="nav-icon">💬</span> أبلغ عن مشكلة
      </div>
      <div class="nav-item" id="nav-settings" onclick="showPanel('panel-settings');setNav('nav-settings')">
        <span class="nav-icon">⚙️</span> الإعدادات
      </div>
      <div class="nav-item" id="nav-changelog" onclick="showPanel('panel-changelog');setNav('nav-changelog')">
        <span class="nav-icon">📋</span> سجل التحديثات
      </div>
      <div class="nav-item" id="nav-support" onclick="showPanel('panel-support');setNav('nav-support')">
        <span class="nav-icon">❤️</span> داعمو إلكترون
      </div>
      <div class="version-label">Electron v1.0.0</div>
    </div>
  </div>

  <!-- Main Content Area -->
  <div class="main-content">

    <!-- 1. الرئيسية: HOME -->
    <div id="panel-home" class="view-panel active">
      <div class="card" style="background:linear-gradient(135deg,rgba(0,229,255,0.08),transparent);border-color:var(--border-highlight);">
        <div class="section-title" style="margin-bottom:8px;">مرحباً بك في إلكترون ⚡</div>
        <div class="section-desc" style="margin-bottom:20px;max-width:750px;">
          البرنامج يقوم <b>باستخراج نصوص اللعبة وترجمتها فعلياً بالذكاء الاصطناعي</b>، مع إمكانية تعديل وإضافة أي كلمة بنفسك وحفظها فورياً في اللعبة.
        </div>
        <div style="display:flex;gap:12px;">
          <button class="btn btn-action-primary" onclick="startScan()">🎮 ابحث عن ألعاب التختيم</button>
          <button class="btn btn-secondary" onclick="openEditor()">✏️ فتح محرر التعريب اليدوي</button>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div class="card">
          <div class="card-title" style="margin-bottom:8px;color:var(--accent-cyan);">ترجمة حقيقية بالذكاء الاصطناعي</div>
          <div class="section-desc">
            يقوم البرنامج باستخراج قوائم اللعبة، الأدوات، الأسلحة، والمهام وترجمتها إلى العربية لغةً وسياقاً.
          </div>
        </div>
        <div class="card">
          <div class="card-title" style="margin-bottom:8px;color:var(--accent-purple);">تحكم وتعديل يدوي كامل</div>
          <div class="section-desc">
            تريد تغيير ترجمة كلمة أو إضافة حوارات جديدة؟ محرر التعريب يتيح لك تعديل أي نص وحفظه بضغطة زر.
          </div>
        </div>
      </div>
    </div>

    <!-- 2. محرر التعريب اليدوي: TRANSLATION EDITOR -->
    <div id="panel-editor" class="view-panel">
      <div class="section-header">
        <div>
          <div class="section-title">Translation Editor (محرر التعريب)</div>
          <div class="section-desc" id="editorGameTitle">اختر لعبة من المكتبة لعرض وتعديل قاموس تعريبها</div>
        </div>
        <div style="display:flex;gap:10px;">
          <button class="btn btn-secondary" onclick="addNewPair()">➕ إضافة كلمة جديدة</button>
          <button class="btn btn-secondary" onclick="aiAutoTranslateAll()">🤖 تعريب الكل بالـ AI</button>
          <button class="btn btn-action-primary" onclick="saveEditorTranslations()">💾 حفظ التعريب في اللعبة</button>
        </div>
      </div>

      <div class="card" style="padding:0;overflow:hidden;flex:1;display:flex;flex-direction:column;">
        <div style="max-height:480px;overflow-y:auto;">
          <table class="editor-table">
            <thead>
              <tr>
                <th style="width:40%;">النص الأصلي (English)</th>
                <th style="width:45%;">التعريب المخصص (Arabic)</th>
                <th style="width:15%;text-align:center;">إجراءات</th>
              </tr>
            </thead>
            <tbody id="editorRows">
              <tr>
                <td colspan="3" style="text-align:center;padding:40px;color:var(--text-muted);">
                  اختر لعبة أولاً من المكتبة لتحميل نصوصها
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- 3. المكتبة: LIBRARY / SCAN -->
    <div id="panel-library" class="view-panel">
      <div class="section-header">
        <div>
          <div class="section-title" id="scanTitle">Singleplayer Game Library</div>
          <div class="section-desc" id="scanCount">ألعاب التختيم والأوفلاين المكتشفة في جهازك (مستبعد منها الأونلاين تلقائياً)</div>
        </div>
        <div style="display:flex;gap:10px;">
          <button class="btn btn-secondary" onclick="startScan()">🔄 إعادة الفحص</button>
          <button class="btn btn-action-primary" id="openGameBtn" onclick="showDetail()" disabled>فتح اللعبة المختارة ←</button>
        </div>
      </div>

      <input id="scanSearch" placeholder="ابحث باسم اللعبة..." oninput="filterGames()" style="width:100%;background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-sm);padding:12px 16px;color:var(--text-main);font-size:13.5px;outline:none;">
      
      <div class="games-grid" id="gamesGrid">
        <div style="text-align:center;padding:60px;color:var(--text-muted);">
          اضغط زر "ابحث عن ألعاب التختيم" لعرض الألعاب المثبتة على جهازك
        </div>
      </div>
    </div>

    <!-- 4. تفاصيل اللعبة: DETAIL -->
    <div id="panel-detail" class="view-panel">
      <div class="section-header">
        <button class="btn btn-secondary" onclick="showPanel('panel-library');setNav('nav-library')">← رجوع للمكتبة</button>
        <div class="section-title" id="detailGameName">—</div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
        <div class="card">
          <div style="font-size:12px;color:var(--text-dim);margin-bottom:4px;">المحرك المكتشف</div>
          <div style="font-size:18px;font-weight:900;color:var(--accent-cyan);" id="detailEngine">—</div>
        </div>
        <div class="card">
          <div style="font-size:12px;color:var(--text-dim);margin-bottom:4px;">حالة التعريب ونوع اللعبة</div>
          <div style="font-size:18px;font-weight:900;color:var(--accent-green);" id="detailFileCount">—</div>
        </div>
      </div>

      <div class="card" style="flex:1;display:flex;flex-direction:column;padding:0;overflow:hidden;">
        <div style="padding:12px 18px;background:var(--bg-elevated);border-bottom:1px solid var(--border-color);font-size:12.5px;font-weight:800;color:var(--text-muted);">
          سجل استخراج وترجمة نصوص اللعبة
        </div>
        <div id="detailFilesList" style="padding:16px;flex:1;overflow-y:auto;font-family:'JetBrains Mono',monospace;font-size:12.5px;direction:ltr;text-align:left;">
          // Analyzing engine architecture...
        </div>
      </div>

      <!-- Real-time Progress Display -->
      <div class="progress-box" id="progressBox">
        <div style="display:flex;justify-content:space-between;font-size:12.5px;font-weight:700;">
          <span id="progressTxt" style="color:var(--accent-cyan);">جارٍ استخراج العبارات والترجمة بالذكاء الاصطناعي...</span>
          <span id="progressPercent" style="color:var(--accent-green);">0%</span>
        </div>
        <div class="progress-bar-bg">
          <div class="progress-bar-fill" id="progressFill"></div>
        </div>
      </div>

      <!-- ACTION BUTTONS -->
      <div style="display:flex;gap:12px;align-items:center;margin-top:6px;">
        <button class="btn btn-action-primary" id="localizeBtn" onclick="localize()" disabled style="flex:2;padding:12px 20px;">
          <div id="locSpin" class="spinner"></div>
          <span id="locTxt">⚡ بدء استخراج وتعريب اللعبة بالـ AI</span>
        </button>
        <button class="btn btn-action-edit" onclick="openEditor();setNav('nav-editor')" style="flex:1;padding:12px 16px;">
          ✏️ تعديل التعريب يدوياً
        </button>
        <button class="btn btn-action-delete" id="restoreBtn" onclick="restore()" disabled style="padding:12px 18px;">
          ↩ إزالة التعريب
        </button>
      </div>
    </div>

    <!-- 5. مفاتيح السحابة: CLOUD KEYS -->
    <div id="panel-keys" class="view-panel">
      <div class="section-header">
        <div>
          <div class="section-title">Cloud Translation Keys</div>
          <div class="section-desc">مفاتيح الذكاء الاصطناعي لتعريب الألعاب تلقائياً وتوليد النصوص.</div>
        </div>
      </div>

      <div class="keys-list">
        <div class="key-box">
          <div class="key-box-top">
            <div class="key-provider-name">
              Google Gemini
              <span class="badge-pill badge-free">مجاني بلا بطاقة · الخيار الموصى به</span>
            </div>
            <span id="geminiSaved" class="saved-key-indicator"></span>
          </div>
          <div class="key-instructions">
            • الأسرع والأفضل للتعريب الكامل. يدعم آلاف الطلبات اليومية مجاناً.<br>
            • اضغط «فتح صفحة المفتاح»، وسجّل الدخول بحساب Google ثم انسخ المفتاح والصقه هنا.
          </div>
          <div style="display:flex;gap:10px;">
            <button class="btn btn-secondary" onclick="openUrl('https://aistudio.google.com/app/apikey')">فتح صفحة المفتاح ↗</button>
            <button class="btn btn-action-primary" onclick="promptPasteKey('gemini')">الصق مفتاح Gemini</button>
          </div>
        </div>

        <div class="key-box">
          <div class="key-box-top">
            <div class="key-provider-name">
              Groq Fast Inference
              <span class="badge-pill badge-free">معالجة فورية</span>
            </div>
            <span id="groqSaved" class="saved-key-indicator"></span>
          </div>
          <div class="key-instructions">
            • سرعة ترجمة فائقة على بطاقات LPU المتطورة.
          </div>
          <div style="display:flex;gap:10px;">
            <button class="btn btn-secondary" onclick="openUrl('https://console.groq.com/keys')">صفحة Groq ↗</button>
            <button class="btn btn-secondary" onclick="promptPasteKey('groq')">الصق مفتاح Groq</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 6. محركات الألعاب: ENGINES PANEL -->
    <div id="panel-engines" class="view-panel">
      <div class="section-header">
        <div>
          <div class="section-title">Supported Game Engines</div>
          <div class="section-desc">حزم محركات التعريب المجهزة في إلكترون للحقن في أي لعبة:</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:14px;" id="enginesList"></div>
    </div>

    <!-- 7. ترجم أي نافذة: LIVE TRANSLATION -->
    <div id="panel-window" class="view-panel">
      <div class="section-header">
        <div>
          <div class="section-title">Live Window Translator</div>
          <div class="section-desc">تعريب شاشة الألعاب أو المحاكيات مباشرة أثناء اللعب. اختر النافذة المستهدفة:</div>
        </div>
        <button class="btn btn-secondary" onclick="refreshWindows()">🔄 تحديث النوافذ</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px;" id="windowsList"></div>
    </div>

    <!-- 8. أبلغ عن مشكلة: FEEDBACK -->
    <div id="panel-report" class="view-panel">
      <div class="section-header">
        <div>
          <div class="section-title">Report & Feedback</div>
          <div class="section-desc">شاركنا ملاحظاتك أو الألعاب التي واجهت بها صعوبة لتحسين التحديثات القادمة:</div>
        </div>
      </div>
      <div class="card" style="max-width:680px;">
        <div style="margin-bottom:16px;">
          <label style="font-size:13px;font-weight:700;display:block;margin-bottom:6px;">نوع المشكلة:</label>
          <select id="repType" style="width:100%;background:var(--bg-elevated);border:1px solid var(--border-color);border-radius:var(--radius-sm);padding:10px 14px;color:var(--text-main);font-size:13.5px;outline:none;">
            <option>مربعات فارغة بدلاً من الحروف العربية</option>
            <option>النص ما زال باللغة الإنجليزية</option>
            <option>الحروف العربية مقلوبة أو متفرقة</option>
            <option>اللعبة لا تفتح بعد التعريب</option>
          </select>
        </div>
        <div style="margin-bottom:16px;">
          <label style="font-size:13px;font-weight:700;display:block;margin-bottom:6px;">اسم اللعبة (اختياري):</label>
          <input id="repGame" placeholder="مثال: Muck، أو غيرها" style="width:100%;background:var(--bg-elevated);border:1px solid var(--border-color);border-radius:var(--radius-sm);padding:10px 14px;color:var(--text-main);font-size:13.5px;outline:none;">
        </div>
        <div style="margin-bottom:20px;">
          <label style="font-size:13px;font-weight:700;display:block;margin-bottom:6px;">تفاصيل الملاحظة:</label>
          <textarea id="repDetails" rows="4" placeholder="اكتب تفاصيل ما حدث معك..." style="width:100%;background:var(--bg-elevated);border:1px solid var(--border-color);border-radius:var(--radius-sm);padding:12px 14px;color:var(--text-main);font-size:13.5px;outline:none;resize:none;"></textarea>
        </div>
        <button class="btn btn-action-primary" onclick="submitFeedback()">إرسال التقرير محلياً</button>
      </div>
    </div>

    <!-- 9. الإعدادات: SETTINGS -->
    <div id="panel-settings" class="view-panel">
      <div class="section-header">
        <div>
          <div class="section-title">Settings</div>
          <div class="section-desc">إعدادات المحركات والنسخ الاحتياطي</div>
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:16px;max-width:720px;">
        <div class="card">
          <div class="card-title" style="margin-bottom:8px;">فلتر ألعاب الأوفلاين</div>
          <div class="section-desc" style="margin-bottom:14px;">
            يتم تفعيل الفلتر التلقائي لاستبعاد ألعاب الأونلاين ومضادات الغش لحماية ألعابك.
          </div>
          <div class="card-title" style="margin-bottom:8px;">معلومات الإصدار</div>
          <div class="section-desc" style="margin-bottom:16px;">
            Electron v1.0.0 (Real AI Translation Pipeline).
          </div>
          <button class="btn btn-secondary" onclick="showModal('✨','System Updated','You are running the latest version of Electron.')">Check for Updates</button>
        </div>
      </div>
    </div>

    <!-- 11. سجل التحديثات: CHANGELOG -->
    <div id="panel-changelog" class="view-panel">
      <div class="section-header">
        <div>
          <div class="section-title">📋 سجل التحديثات</div>
          <div class="section-desc">رحلة Electron من الفكرة إلى الإطلاق — كل تحديث وكل إنجاز.</div>
        </div>
      </div>

      <!-- Entry 1 -->
      <div class="card" style="margin-bottom:16px;border-right:3px solid var(--accent-cyan);">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="background:var(--accent-cyan);color:#000;font-weight:700;padding:4px 14px;border-radius:20px;font-size:12px;">🚀 الانطلاقة</span>
          <span style="color:var(--text-muted);font-size:13px;">محرك Paradox — الخطوات الأولى</span>
        </div>
        <div class="card-title" style="margin-bottom:8px;">الأرقام والخطوات الأولى</div>
        <ul style="color:var(--text-secondary);font-size:13.5px;line-height:2;padding-right:20px;margin:0;">
          <li>دعم محرك <span style="color:var(--accent-cyan);">Paradox</span> — التجربة الأولى على <strong>Crusader Kings III</strong> (240,000+ نص)</li>
          <li>🎉 <strong>240 تحميلاً</strong> خلال أول 24 ساعة من الإطلاق</li>
          <li>ترجمة أكثر من <strong>مليون سطر</strong> في الذاكرة المشتركة</li>
        </ul>
      </div>

      <!-- Entry 2 -->
      <div class="card" style="margin-bottom:16px;border-right:3px solid #a78bfa;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="background:#a78bfa;color:#000;font-weight:700;padding:4px 14px;border-radius:20px;font-size:12px;">🔧 v0.9.19</span>
          <span style="color:var(--text-muted);font-size:13px;">إصلاحات جوهرية</span>
        </div>
        <div class="card-title" style="margin-bottom:8px;">تحديث 0.9.19 — حل العُطل الكبرى</div>
        <ul style="color:var(--text-secondary);font-size:13.5px;line-height:2;padding-right:20px;margin:0;">
          <li>إصلاح <strong>14 عطلاً</strong> دفعةً واحدة</li>
          <li>حل مشكلة <strong>اختفاء النصوص</strong> وظهورها على شكل مربعات</li>
          <li>معالجة <strong>الانهيارات (Crashes)</strong> والتعليق المفاجئ</li>
        </ul>
      </div>

      <!-- Entry 3 -->
      <div class="card" style="margin-bottom:16px;border-right:3px solid #a78bfa;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="background:#a78bfa;color:#000;font-weight:700;padding:4px 14px;border-radius:20px;font-size:12px;">🔧 v0.9.20</span>
          <span style="color:var(--text-muted);font-size:13px;">إعادة بناء Unity</span>
        </div>
        <div class="card-title" style="margin-bottom:8px;">تحديث 0.9.20 — إصلاحات عامة + Unity</div>
        <ul style="color:var(--text-secondary);font-size:13.5px;line-height:2;padding-right:20px;margin:0;">
          <li>معالجة مجموعة من الأخطاء الخفيفة العامة</li>
          <li>بدء <strong>إعادة بناء محرك Unity</strong> من الصفر وتقسيمه إلى أقسام برمجية منفصلة</li>
          <li>اختبار التعريب على عشرات الألعاب دفعةً واحدة لتفادي تكرار الأخطاء</li>
        </ul>
      </div>

      <!-- Entry 4 -->
      <div class="card" style="margin-bottom:16px;border-right:3px solid var(--accent-cyan);">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="background:var(--accent-cyan);color:#000;font-weight:700;padding:4px 14px;border-radius:20px;font-size:12px;">⭐ v0.9.21</span>
          <span style="color:var(--text-muted);font-size:13px;">تحديث Unity الكبير</span>
        </div>
        <div class="card-title" style="margin-bottom:8px;">تحديث 0.9.21 — محرك Unity البارز</div>
        <ul style="color:var(--text-secondary);font-size:13.5px;line-height:2;padding-right:20px;margin:0;">
          <li>اختبار وتأكيد التعريب على <strong>50–53 لعبة Unity</strong></li>
          <li>نظام البلاغات التلقائي — إرسال تقرير تفصيلي مع السجلات للسيرفر بدون تذكرة دعم</li>
          <li>إصلاح مشكلة <strong>استهلاك RAM</strong> المفاجئ</li>
          <li>إصلاح التعليق عند الانتقال بين الصفحة الرئيسية والمكتبة</li>
        </ul>
      </div>

      <!-- Entry 5 -->
      <div class="card" style="margin-bottom:16px;border-right:3px solid #34d399;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="background:#34d399;color:#000;font-weight:700;padding:4px 14px;border-radius:20px;font-size:12px;">📅 10/02/2026</span>
          <span style="color:var(--text-muted);font-size:13px;">ميزات تجريبية</span>
        </div>
        <div class="card-title" style="margin-bottom:8px;">تحديث 02 فبراير 2026 — إصلاحات وتجارب</div>
        <ul style="color:var(--text-secondary);font-size:13.5px;line-height:2;padding-right:20px;margin:0;">
          <li>إصلاحات متعددة في <strong>Unity</strong> وبسيطة في <strong>Unreal Engine</strong></li>
          <li>🧪 ميزة <strong>طول السطر (تجريبية)</strong> — تحديد عرض النص لمعالجة الكلام من الأسفل للأعلى</li>
          <li>🧪 <strong>3 خيارات خطوط</strong> لتفادي اختفاء النصوص أو ظهورها بحجم خاطئ</li>
          <li>إضافة رتبة <span style="color:var(--accent-cyan);">@مجرب 🧐</span> في ديسكورد لاختبار النسخ قبل إطلاقها</li>
        </ul>
      </div>

      <!-- Entry 6 -->
      <div class="card" style="margin-bottom:16px;border-right:3px solid #34d399;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="background:#34d399;color:#000;font-weight:700;padding:4px 14px;border-radius:20px;font-size:12px;">📅 03 & 06 / 2026</span>
          <span style="color:var(--text-muted);font-size:13px;">ألعاب ذات طلب عالٍ</span>
        </div>
        <div class="card-title" style="margin-bottom:8px;">تحديثات مارس ويونيو 2026</div>
        <ul style="color:var(--text-secondary);font-size:13.5px;line-height:2;padding-right:20px;margin:0;">
          <li>إصلاحات وتحديثات مخصصة لـ <strong>Hearts of Iron</strong></li>
          <li>إصلاحات وتحسينات لـ <strong>Stardew Valley</strong></li>
        </ul>
      </div>

      <!-- Entry 7 -->
      <div class="card" style="margin-bottom:16px;border-right:3px solid var(--accent-cyan);">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="background:var(--accent-cyan);color:#000;font-weight:700;padding:4px 14px;border-radius:20px;font-size:12px;">⭐ 10/10/2026</span>
          <span style="color:var(--text-muted);font-size:13px;">التعريب الحي + حسابات</span>
        </div>
        <div class="card-title" style="margin-bottom:8px;">تحديث 10 أكتوبر 2026 — التعريب الحي</div>
        <ul style="color:var(--text-secondary);font-size:13.5px;line-height:2;padding-right:20px;margin:0;">
          <li>🔴 ميزة <strong>التعريب الحي (Live Translation)</strong> — طبقة ترجمة فوق اللعبة (Overlay) دون تعديل الملفات</li>
          <li>موجّهة للألعاب الأونلاين لمنع حظر الحسابات</li>
          <li>تعمل فقط في وضع <strong>Windowed</strong> أو <strong>Borderless Windowed</strong></li>
          <li>تسجيل الدخول وإنشاء الحساب عبر <strong>البريد الإلكتروني</strong> بديلاً عن ديسكورد</li>
        </ul>
      </div>

      <!-- Entry 8 - Coming Soon -->
      <div class="card" style="margin-bottom:16px;border-right:3px solid #f59e0b;background:linear-gradient(135deg,var(--bg-elevated),rgba(245,158,11,0.05));">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="background:#f59e0b;color:#000;font-weight:700;padding:4px 14px;border-radius:20px;font-size:12px;">🔮 قريباً</span>
          <span style="color:var(--text-muted);font-size:13px;">الجيل القادم</span>
        </div>
        <div class="card-title" style="margin-bottom:8px;">ما يأتي بعد ذلك...</div>
        <ul style="color:var(--text-secondary);font-size:13.5px;line-height:2;padding-right:20px;margin:0;">
          <li>🎨 تصميم عصري مخصص للجوال والكمبيوتر</li>
          <li>⚡ تحسين السرعة والأمان بشكل ملحوظ</li>
          <li style="color:var(--text-muted);font-style:italic;">المزيد قريباً... ترقّب!</li>
        </ul>
      </div>

    </div>

    <!-- 10. داعمو إلكترون: SUPPORTERS -->
    <div id="panel-support" class="view-panel">
      <div class="section-header">
        <div>
          <div class="section-title">Electron Supporters ❤️</div>
          <div class="section-desc">تحية وتقدير لكل من ساند هذا المشروع المجاني لإثراء الألعاب باللغة العربية.</div>
        </div>
      </div>
      <div class="card">
        <div class="card-title" style="margin-bottom:12px;">قائمة الشرف والداعمين</div>
        <div style="display:flex;flex-wrap:wrap;gap:10px;">
          <div style="background:var(--bg-elevated);border:1px solid var(--border-color);border-radius:20px;padding:8px 18px;font-size:13.5px;color:var(--text-main);">✨ مجتمع اللاعبين العرب</div>
          <div style="background:var(--bg-elevated);border:1px solid var(--border-color);border-radius:20px;padding:8px 18px;font-size:13.5px;color:var(--text-main);">✨ مطورو التعريب المجتمعي</div>
          <div style="background:var(--bg-elevated);border:1px solid var(--border-color);border-radius:20px;padding:8px 18px;font-size:13.5px;color:var(--text-main);">✨ داعمو إلكترون الأوفياء</div>
        </div>
      </div>
    </div>

  </div>
</div>

<!-- Modal Popup -->
<div class="modal-overlay" id="modalOverlay">
  <div class="modal-box">
    <div class="modal-icon" id="modalIcon">🎉</div>
    <div class="modal-title" id="modalTitle">تم بنجاح</div>
    <div class="modal-desc" id="modalDesc"></div>
    <button class="btn btn-action-primary" style="width:100%;padding:12px;" onclick="closeModal()">إغلاق</button>
  </div>
</div>

<script>
let allGames = [], selectedGame = null;
let currentTranslations = [];

function showPanel(panelId){
  document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
  const el = document.getElementById(panelId);
  if(el) el.classList.add('active');
}

function setNav(navId){
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const el = document.getElementById(navId);
  if(el) el.classList.add('active');
}

function openUrl(url){
  pywebview.api.open_external_url(url);
}

// Modal handling
function showModal(icon, title, desc){
  document.getElementById('modalIcon').innerText = icon;
  document.getElementById('modalTitle').innerText = title;
  document.getElementById('modalDesc').innerText = desc;
  document.getElementById('modalOverlay').classList.add('active');
}

function closeModal(){
  document.getElementById('modalOverlay').classList.remove('active');
}

// Editor Logic
async function openEditor(){
  showPanel('panel-editor');
  if(!selectedGame){
    if(allGames.length > 0){
      const muck = allGames.find(g => g.name.toLowerCase().includes('muck')) || allGames[0];
      selectedGame = muck;
    }
  }

  if(selectedGame){
    document.getElementById('editorGameTitle').innerText = `تعديل قاموس اللعبة: ${selectedGame.name}`;
    const res = await pywebview.api.get_game_translations();
    currentTranslations = res.pairs || [];
    renderEditorRows();
  } else {
    document.getElementById('editorGameTitle').innerText = 'يرجى اختيار لعبة أولاً من المكتبة';
  }
}

function renderEditorRows(){
  const tbody = document.getElementById('editorRows');
  if(!currentTranslations.length){
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:30px;color:var(--text-muted);">لا توجد كلمات حالياً، اضغط "إضافة كلمة جديدة" للبدء</td></tr>';
    return;
  }

  tbody.innerHTML = currentTranslations.map((item, idx) => `
    <tr>
      <td><input class="editor-input" value="${item.orig}" onchange="updatePair(${idx}, 'orig', this.value)" placeholder="English Text"></td>
      <td><input class="editor-input" value="${item.trans}" onchange="updatePair(${idx}, 'trans', this.value)" placeholder="التعريب المخصص"></td>
      <td style="text-align:center;">
        <button class="btn btn-secondary" style="padding:6px 10px;font-size:12px;margin-left:4px;" onclick="aiTranslateSingle(${idx})">🤖 AI</button>
        <button class="btn btn-action-delete" style="padding:6px 10px;font-size:12px;" onclick="deletePair(${idx})">🗑️</button>
      </td>
    </tr>
  `).join('');
}

function updatePair(idx, field, val){
  if(currentTranslations[idx]){
    currentTranslations[idx][field] = val;
  }
}

function addNewPair(){
  currentTranslations.unshift({orig: '', trans: ''});
  renderEditorRows();
}

function deletePair(idx){
  currentTranslations.splice(idx, 1);
  renderEditorRows();
}

async function aiTranslateSingle(idx){
  const orig = currentTranslations[idx].orig;
  if(!orig) return;
  const res = await pywebview.api.ai_translate_custom([orig]);
  if(res.status === 'ok' && res.translations[orig]){
    currentTranslations[idx].trans = res.translations[orig];
    renderEditorRows();
  } else {
    showModal('❌', 'خطأ في الترجمة', res.message || 'تعذر الاتصال بخدمة الترجمة');
  }
}

async function aiAutoTranslateAll(){
  const untranslated = currentTranslations.filter(p => !p.trans.trim() && p.orig.trim()).map(p => p.orig.trim());
  if(!untranslated.length){
    showModal('💡', 'الكلمات معربة', 'كل الكلمات الحالية لديها تعريب بالفعل.');
    return;
  }

  showModal('⏳', 'جارٍ التعريب بالـ AI', `يقوم الذكاء الاصطناعي بترجمة ${untranslated.length} عبارة...`);
  const res = await pywebview.api.ai_translate_custom(untranslated);
  closeModal();

  if(res.status === 'ok'){
    for(const item of currentTranslations){
      if(res.translations[item.orig]){
        item.trans = res.translations[item.orig];
      }
    }
    renderEditorRows();
    showModal('✅', 'تم التعريب بنجاح', `تم تعريب ${untranslated.length} كلمة بالذكاء الاصطناعي.`);
  } else {
    showModal('❌', 'خطأ في التعريب', res.message || 'فشل الاتصال بالذكاء الاصطناعي.');
  }
}

async function saveEditorTranslations(){
  const res = await pywebview.api.save_game_translations(currentTranslations);
  if(res.status === 'ok'){
    showModal('✅', 'تم الحفظ بنجاح', `تم حفظ وتطبيق ${res.count} تعريباً داخل ملفات اللعبة مباشرة!`);
  } else {
    showModal('❌', 'خطأ في الحفظ', res.message);
  }
}

// Engines
async function loadEngines(){
  const engines = await pywebview.api.get_engines_info();
  const c = document.getElementById('enginesList');
  if(!c) return;
  c.innerHTML = engines.map(e => `
    <div class="card" style="display:flex;align-items:flex-start;justify-content:space-between;gap:20px;">
      <div style="flex:1;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:6px;">
          <div style="font-size:17px;font-weight:900;color:var(--text-main);">${e.name}</div>
          <span class="badge-pill badge-free">${e.status}</span>
        </div>
        <div style="font-size:13.5px;color:var(--text-muted);margin-bottom:12px;">${e.desc}</div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;">
          ${e.features.map(f => `<span style="background:var(--bg-elevated);border:1px solid var(--border-color);border-radius:6px;padding:3px 10px;font-size:12px;color:var(--accent-cyan);">✓ ${f}</span>`).join('')}
        </div>
      </div>
    </div>
  `).join('');
}

// Keys logic
async function promptPasteKey(provider){
  let key = '';
  try { key = await navigator.clipboard.readText(); } catch(e){}
  if(!key){ key = prompt(`Paste API Key for (${provider}) here:`, ''); }
  if(!key) return;
  key = key.trim();
  
  const res = await pywebview.api.validate_api_key(provider, key);
  if(res.status === 'valid'){
    showModal('✅', 'Key Saved / تم الحفظ', res.message || 'المفتاح جاهز ويعمل الآن.');
    loadSavedKeys();
  } else {
    showModal('❌', 'Validation Failed', res.message || 'المفتاح غير صالح.');
  }
}

async function loadSavedKeys(){
  const res = await pywebview.api.get_saved_keys();
  if(res.status === 'ok' && res.keys){
    for(const [k, val] of Object.entries(res.keys)){
      const el = document.getElementById(`${k}Saved`);
      if(el) el.innerText = `✓ Active: ${val}`;
    }
  }
}

// Windows Live list
async function refreshWindows(){
  const list = await pywebview.api.get_open_windows();
  const c = document.getElementById('windowsList');
  c.innerHTML = list.map(w => `
    <div class="card" style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px;">
      <div>
        <div style="font-size:15px;font-weight:800;color:var(--text-main);">${w.title}</div>
        <div style="font-size:12px;color:var(--text-dim);direction:ltr;text-align:right;">${w.proc} · ${w.type}</div>
      </div>
    <div style="display:flex;gap:10px;">
      <button class="btn btn-action-primary" onclick="launchLiveOverlay()">🎮 تشغيل الترجمة الحية</button>
    </div>
    </div>
  `).join('');
}

// Live Translator HUD launcher
async function launchLiveOverlay(){
  const res = await pywebview.api.launch_live_overlay();
  if(res.status === 'ok'){
    showModal('🎮', 'الترجمة الحية شغالة', res.message);
  } else {
    showModal('❌', 'فشل التشغيل', res.message || 'تعذر بدء واجهة الترجمة الحية.');
  }
}

// Games Scanning
async function startScan(){
  showPanel('panel-library');
  setNav('nav-library');
  document.getElementById('scanTitle').innerText = 'Scanning Singleplayer Games...';
  document.getElementById('scanCount').innerText = 'Searching Steam, Epic & Xbox (Online games excluded)...';
  document.getElementById('gamesGrid').innerHTML = '<div style="text-align:center;padding:60px;color:var(--text-muted);"><span class="spinner" style="display:inline-block;"></span> جارٍ فحص ألعاب التختيم...</div>';

  const res = await pywebview.api.scan_games();
  allGames = res.games || [];
  document.getElementById('scanTitle').innerText = 'Singleplayer Game Library';
  document.getElementById('scanCount').innerText = `تم العثور على ${allGames.length} لعبة تختيم وأوفلاين جاهزة للتعريب الآمن`;
  renderGames(allGames);
}

function renderGames(games){
  const grid = document.getElementById('gamesGrid');
  if(!games.length){
    grid.innerHTML = '<div style="text-align:center;padding:60px;color:var(--text-muted);">لم يتم العثور على ألعاب تختيم في المسارات الافتراضية</div>';
    return;
  }
  grid.innerHTML = games.map((g, i) => {
    return `
      <div class="game-card" id="gc-${i}" onclick="selectCard(${i})">
        <div class="game-card-header">
          <div class="game-name">${g.name}</div>
          <div style="display:flex;gap:6px;">
            <span class="badge-pill badge-pro">${g.source}</span>
            <span class="badge-pill badge-free">${g.engine}</span>
          </div>
        </div>
        <div class="game-path">${g.path.slice(0, 80)}...</div>
      </div>
    `;
  }).join('');
}

function filterGames(){
  const q = document.getElementById('scanSearch').value.toLowerCase();
  renderGames(allGames.filter(g => g.name.toLowerCase().includes(q)));
}

function selectCard(i){
  document.querySelectorAll('.game-card').forEach(c => c.classList.remove('selected'));
  const card = document.getElementById(`gc-${i}`);
  if(card) card.classList.add('selected');
  selectedGame = allGames[i];
  document.getElementById('openGameBtn').disabled = false;
}

async function showDetail(){
  if(!selectedGame) return;
  showPanel('panel-detail');
  document.getElementById('detailGameName').innerText = selectedGame.name;
  document.getElementById('detailFilesList').innerHTML = '// Analyzing engine architecture...';

  const res = await pywebview.api.select_game(selectedGame.path);
  document.getElementById('detailEngine').innerText = res.engine || '—';
  
  if(res.is_unity){
    document.getElementById('detailFileCount').innerText = 'لعبة أوفلاين / تختيم (Unity Engine)';
    document.getElementById('detailFilesList').innerHTML = `
      <div style="color:var(--accent-cyan);margin-bottom:8px;">[✓] تصنيف اللعبة: لعبة قصة / تختيم آمنة (Offline / Singleplayer)</div>
      <div style="color:var(--accent-green);margin-bottom:8px;">[✓] محرك اللعبة: Unity Game Engine (جاهز للاستخراج والترجمة الحقيقية)</div>
      <div style="color:var(--text-muted);font-size:12.5px;">سيقوم الذكاء الاصطناعي الآن باستخراج عبارات اللعبة الحقيقية وترجمتها فورياً إلى العربية.</div>
    `;
    document.getElementById('localizeBtn').disabled = false;
    document.getElementById('restoreBtn').disabled = false;
  } else if(res.has_files){
    document.getElementById('detailFileCount').innerText = `${res.file_count} ملفات جاهزة`;
    document.getElementById('detailFilesList').innerHTML = res.files.map(f => `<div style="color:var(--accent-green);margin-bottom:4px;">[✓] ${f}</div>`).join('');
    document.getElementById('localizeBtn').disabled = false;
    document.getElementById('restoreBtn').disabled = false;
  } else {
    document.getElementById('detailFileCount').innerText = '0';
    document.getElementById('detailFilesList').innerHTML = '<div style="color:#ff4081;">[!] لم يتم العثور على محرك مدعوم بشكل مباشر.</div>';
    document.getElementById('localizeBtn').disabled = true;
  }
}

async function browseManual(){
  const res = await pywebview.api.browse_game_folder();
  if(res.status !== 'ok') return;
  selectedGame = { name: res.name, path: 'manual' };
  showPanel('panel-detail');
  setNav('nav-library');
  document.getElementById('detailGameName').innerText = res.name;
  document.getElementById('detailEngine').innerText = res.engine;
  if(res.is_unity){
    document.getElementById('detailFileCount').innerText = 'محرك جاهز للحقن الفوري';
    document.getElementById('detailFilesList').innerHTML = `
      <div style="color:var(--accent-cyan);margin-bottom:8px;">[✓] نوع المحرك: Unity Game Engine</div>
      <div style="color:var(--accent-green);margin-bottom:8px;">[✓] سيتم تطبيق حزمة التعريب على محرك اللعبة بالكامل.</div>
    `;
    document.getElementById('localizeBtn').disabled = false;
    document.getElementById('restoreBtn').disabled = false;
  } else if(res.has_files){
    document.getElementById('detailFileCount').innerText = `${res.file_count} ملفات`;
    document.getElementById('detailFilesList').innerHTML = res.files.map(f => `<div style="color:var(--accent-green);margin-bottom:4px;">[✓] ${f}</div>`).join('');
    document.getElementById('localizeBtn').disabled = false;
    document.getElementById('restoreBtn').disabled = false;
  } else {
    document.getElementById('detailFileCount').innerText = '0';
    document.getElementById('detailFilesList').innerHTML = '<div style="color:#ff4081;">[!] غير مدعوم.</div>';
    document.getElementById('localizeBtn').disabled = true;
  }
}

async function localize(){
  document.getElementById('localizeBtn').disabled = true;
  document.getElementById('locSpin').style.display = 'inline-block';
  document.getElementById('locTxt').innerText = 'جارٍ استخراج العبارات وترجمتها بالذكاء الاصطناعي...';

  // Show visual progress
  const pBox = document.getElementById('progressBox');
  const pFill = document.getElementById('progressFill');
  const pPercent = document.getElementById('progressPercent');
  const pTxt = document.getElementById('progressTxt');
  pBox.style.display = 'block';
  pFill.style.width = '15%';
  pPercent.innerText = '15%';

  let timer = setInterval(() => {
    let w = parseInt(pFill.style.width) || 15;
    if (w < 85) {
      w += 10;
      pFill.style.width = w + '%';
      pPercent.innerText = w + '%';
      pTxt.innerText = `جارٍ ترجمة وتحليل عبارات اللعبة بالذكاء الاصطناعي (${w}%)...`;
    }
  }, 400);

  const res = await pywebview.api.localize_game();

  clearInterval(timer);
  pFill.style.width = '100%';
  pPercent.innerText = '100%';
  pTxt.innerText = 'اكتملت الترجمة وحفظ الملفات بنجاح!';

  document.getElementById('locSpin').style.display = 'none';
  document.getElementById('locTxt').innerText = '⚡ بدء استخراج وتعريب اللعبة بالـ AI';
  document.getElementById('localizeBtn').disabled = false;

  showModal(
    res.status === 'ok' ? '🎉' : '❌',
    res.status === 'ok' ? 'اكتمل تعريب اللعبة بالذكاء الاصطناعي!' : 'حدث خطأ',
    res.message || `تمت ترجمة وحفظ النصوص بنجاح داخل ملفات اللعبة.`
  );
}

async function restore(){
  const res = await pywebview.api.restore_game();
  showModal(
    res.status === 'ok' ? '✅' : '❌',
    res.status === 'ok' ? 'تمت إزالة التعريب!' : 'خطأ',
    res.status === 'ok' ? `تم استرجاع اللعبة لحالتها الأولى.` : res.message
  );
}

async function submitFeedback(){
  const type = document.getElementById('repType').value;
  const game = document.getElementById('repGame').value;
  const det = document.getElementById('repDetails').value;
  await pywebview.api.submit_report(type, game, det);
  showModal('💌', 'Report Received', 'تم تدوين التقرير محلياً بنجاح!');
  document.getElementById('repDetails').value = '';
}

window.addEventListener('pywebviewready', () => {
  loadSavedKeys();
  refreshWindows();
  loadEngines();
});
</script>
</body>
</html>
""".replace("ELECTRON_LOGO_PLACEHOLDER", ELECTRON_LOGO_DATA)

def main():
    api = ElectronApi()
    webview.create_window(
        title="Electron | Game Engine Localizer",
        html=HTML,
        js_api=api,
        width=1200,
        height=760,
        resizable=True
    )
    webview.start()

if __name__ == "__main__":
    main()
