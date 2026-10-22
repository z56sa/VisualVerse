r"""
rpgmaker_patcher.py — RPG Maker MV/MZ engine-level localization for ELECTRON.

Instead of blindly rewriting every string in every data/*.json (which breaks
event scripting), this patcher walks the events with surgical precision:

  * code 401  : dialogue lines          (Show Text, all maps + common events)
  * code 405  : scroll text lines       (battle / map)
  * code 101  : speaker name            (MZ extra parameter)
  * code 102  : choice option texts
  * code 320 / 324 / 325 : actor name / nickname / profile changes
  * System.json : title, currency, element/equip/weapon/armor types, terms
  * Actors.json / Items.json ... : name / description / usage messages

RPG Maker escape codes (\N[1], \C[2], \I[10], \V[4], \{ \} \\ ...) are
protected: after translation, every code must survive in order, otherwise
the original line is kept untouched for manual editing.

Also injects an Arabic-capable font through css/main.css so the game can
actually render the Arabic script (RPG Maker ships Latin-only fonts).
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# -- event command ids -------------------------------------------------------
CMD_DIALOGUE = 401      # Show Text body line
CMD_SCROLL = 405        # Scroll Text body line
CMD_SHOW_TEXT = 101     # MZ: params[4] = speaker name
CMD_CHOICES = 102       # params[0] = list of choice strings
CMD_NAME_ACTOR = 320    # params[1] = name
CMD_NICK_ACTOR = 324    # params[1] = nickname
CMD_PROFILE_ACTOR = 325 # params[1] = profile

# strings written into these data list keys (Items, Skills ...)
ITEM_TEXT_KEYS = ("name", "description", "message1", "message2", "nickname", "profile")

# System.json top-level string LIST fields worth translating
SYSTEM_LIST_FIELDS = (
    "elements", "skillTypes", "equipTypes", "weaponTypes", "armorTypes",
    "switches", "variables",
)

_ID_ONLY_RE = re.compile(r"^[-\w]*(\.png|\.ogg|\.jpg|\.wav|\.ttf|\.webp|https?://)", re.I)
_CODE_TOKEN_RE = re.compile(r"\\[A-Za-z][A-Za-z0-9_]*\[[^\]]*\]")


def translateable_text(text: str) -> bool:
    """Heuristic: real player-facing text, not ids, filenames, pure codes."""
    if not isinstance(text, str):
        return False
    t = text.strip()
    if len(t) < 2 or len(t) > 600:
        return False
    if _ID_ONLY_RE.search(t):
        return False
    letters = sum(1 for c in t if c.isalpha())
    if letters < 2:
        return False
    if t.count("#") > 2 and t.count("\n") > 2:
        return False
    return True


def validate_codes(orig: str, translated: str) -> bool:
    """Ensure escape codes survived translation (order + presence)."""
    orig_codes = _CODE_TOKEN_RE.findall(orig)
    if orig_codes:
        pos, t = 0, translated
        for code in orig_codes:
            found = t.find(code, pos)
            if found == -1:
                return False
            pos = found + len(code)
    # balanced engine braces: \{ opens a bigger font, \} closes it
    if orig.count("\\{") != translated.count("\\{"):
        return False
    if orig.count("\\}") != translated.count("\\}"):
        return False
    if orig.count("\\\\") != translated.count("\\\\"):
        return False
    return True


class RPGMakerPatcher:
    """Extracts, translates and patches RPG Maker MV/MZ data files safely."""

    SIDECAR_NAME = "rpg.json"
    SIDECAR_DIR = "ElectronLoc"
    MAX_AUTO_TRANSLATE = 300

    DEPTH_PROTECT = 12          # max event nesting depth guard
    MAX_EVENTS_PER_MAP = 5000   # per-file event cap (safety)

    def __init__(self, game_dir: Path, translator=None, memory=None):
        self.game_dir = Path(game_dir)
        self.translator = translator
        self.memory = memory
        self.data_dirs: List[Path] = []
        self.sidecar: Dict[str, Dict[str, str]] = {}
        self.font_report: List[str] = []

    # -- discovery -----------------------------------------------------------

    def find_data_dirs(self) -> List[Path]:
        candidates = []
        for pattern in ("www/data", "data"):
            for d in self.game_dir.glob(f"**/{pattern}"):
                has_map = any(d.glob("Map[0-9]*.json")) or any(d.glob("Maps/*.json"))
                if d.is_dir() and (d / "System.json").exists() and has_map:
                    candidates.append(d)
        # dedupe preserving order
        seen, out = set(), []
        for d in candidates:
            if str(d) not in seen:
                seen.add(str(d))
                out.append(d)
        self.data_dirs = out
        return out

    # -- extraction ----------------------------------------------------------

    def _walk_event_commands(self, node, file_id: str, path,
                             out: Dict[str, str], depth: int = 0):
        """Recursively collect translatable strings from event command lists.

        Command dicts ({"code": 401, "parameters": [...]}) are translated at
        precise positions; container dicts/lists (pages, list) are descended.
        """
        if depth > self.DEPTH_PROTECT or node is None:
            return
        path = list(path)

        if isinstance(node, dict):
            code = node.get("code")
            params = node.get("parameters")
            if isinstance(code, int) and isinstance(params, list):
                # A command node: translate at a precise pointer, no children.
                if code in (CMD_DIALOGUE, CMD_SCROLL):
                    if params and isinstance(params[0], str) \
                            and translateable_text(params[0]):
                        out[self._ptr(file_id, path, ["parameters", 0])] = params[0]
                elif code == CMD_SHOW_TEXT:
                    if len(params) >= 5 and isinstance(params[4], str) \
                            and params[4].strip():
                        out[self._ptr(file_id, path, ["parameters", 4])] = params[4]
                elif code == CMD_CHOICES:
                    if params and isinstance(params[0], list):
                        for i, choice in enumerate(params[0]):
                            if isinstance(choice, str) and translateable_text(choice):
                                out[self._ptr(file_id, path,
                                              ["parameters", 0, i])] = choice
                elif code in (CMD_NAME_ACTOR, CMD_NICK_ACTOR, CMD_PROFILE_ACTOR):
                    if len(params) >= 2 and isinstance(params[1], str) \
                            and translateable_text(params[1]):
                        out[self._ptr(file_id, path, ["parameters", 1])] = params[1]
                return
            # Container dict: descend into event command containers only.
            for key in ("pages", "list"):
                child = node.get(key)
                if isinstance(child, list):
                    for i, item in enumerate(child[:self.MAX_EVENTS_PER_MAP]):
                        self._walk_event_commands(item, file_id,
                                                  path + [key, i], out, depth + 1)
        elif isinstance(node, list):
            for i, item in enumerate(node[:self.MAX_EVENTS_PER_MAP]):
                self._walk_event_commands(item, file_id, path + [i], out, depth + 1)

    @staticmethod
    def _ptr(file_id: str, path: List, extra: List) -> str:
        parts = [file_id] + [str(p) for p in path + extra]
        return "/".join(parts)

    def extract_file_strings(self, data_dir: Path) -> Dict[str, str]:
        """Returns {json_pointer: original_text} for one data folder."""
        out: Dict[str, str] = {}

        for map_file in sorted(data_dir.glob("Map[0-9]*.json")):
            try:
                data = json.loads(map_file.read_text(encoding="utf-8"))
            except Exception:
                continue
            self._walk_values(data, map_file.name, [], out)

        for generic_name in ("CommonEvents.json", "Troops.json"):
            f = data_dir / generic_name
            if f.exists():
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                self._walk_values(data, generic_name, [], out)

        # Items / Skills / Actors style files
        item_files = ["Actors.json", "Classes.json", "Items.json", "Skills.json",
                      "Weapons.json", "Armors.json", "Enemies.json", "States.json",
                      "EnemyTroops.json"]
        for name in item_files:
            f = data_dir / name
            if not f.exists():
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data, list):
                for i, row in enumerate(data):
                    if isinstance(row, dict):
                        for field in ITEM_TEXT_KEYS:
                            val = row.get(field)
                            if isinstance(val, str) and translateable_text(val):
                                out[self._ptr(name, [], [str(i), field])] = val

        # System.json
        sys_file = data_dir / "System.json"
        if sys_file.exists():
            try:
                sysdata = json.loads(sys_file.read_text(encoding="utf-8"))
            except Exception:
                sysdata = {}
            title = sysdata.get("gameTitle")
            if isinstance(title, str) and translateable_text(title):
                out[self._ptr("System.json", [], ["gameTitle"])] = title
            currency = sysdata.get("currencyUnit")
            if isinstance(currency, str) and translateable_text(currency):
                out[self._ptr("System.json", [], ["currencyUnit"])] = currency
            for field in SYSTEM_LIST_FIELDS:
                arr = sysdata.get(field)
                if isinstance(arr, list):
                    for i, val in enumerate(arr):
                        if isinstance(val, str) and translateable_text(val):
                            out[self._ptr("System.json", [], [field.replace("/", "·"), str(i)])] = val
            terms = sysdata.get("terms")
            if isinstance(terms, dict):
                self._walk_terms(terms, out)

        return out

    def _walk_terms(self, terms, out: Dict[str, str], prefix: List[str] = None, depth: int = 0):
        """Walk System.json 'terms' including nested lists like basic: [[..],[..]]."""
        prefix = prefix or ["terms"]
        if depth > 4:
            return
        for k, v in terms.items():
            p = prefix + [str(k)]
            if isinstance(v, str) and translateable_text(v):
                out[self._ptr("System.json", [], p)] = v
            elif isinstance(v, list):
                for i, val in enumerate(v):
                    if isinstance(val, str) and translateable_text(val):
                        out[self._ptr("System.json", [], p + [str(i)])] = val
                    elif isinstance(val, (list, dict)):
                        self._walk_terms({str(j): sub for j, sub in
                                          enumerate(val) if isinstance(sub, (str, list, dict))},
                                         out, p + [str(i)], depth + 1)
            elif isinstance(v, dict) and depth < 3:
                self._walk_terms(v, out, p, depth + 1)

    def _walk_values(self, node, file_id: str, path: List, out: Dict[str, str]):
        """Generic recursive walker dispatching to the specific list walkers."""
        if isinstance(node, dict):
            if "pages" in node or "list" in node:
                self._walk_event_commands(node, file_id, path, out)
            else:
                for k, v in list(node.items())[:64]:
                    self._walk_values(v, file_id, path + [k], out)
        elif isinstance(node, list):
            for i, v in enumerate(node[:self.MAX_EVENTS_PER_MAP]):
                self._walk_values(v, file_id, path + [i], out)

    # -- sidecar -------------------------------------------------------------

    def _sidecar_path(self) -> Path:
        sidecar_dir = self.game_dir / self.SIDECAR_DIR
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        return sidecar_dir / self.SIDECAR_NAME

    def build_sidecar(self) -> Path:
        out_texts: Dict[str, str] = {}
        self.find_data_dirs()
        for d in self.data_dirs:
            rel_prefix = str(d.relative_to(self.game_dir)).replace("\\", "/")
            strings = self.extract_file_strings(d)
            for ptr, text in strings.items():
                # pointer already includes the file name; prefix keeps it unique
                out_texts[f"{rel_prefix}/{ptr}"] = text

        self.sidecar = {k: {"orig": v, "trans": ""} for k, v in out_texts.items()}
        path = self._sidecar_path()
        self._write_sidecar(path)
        return path

    def _write_sidecar(self, path: Path):
        path.write_text(json.dumps(self.sidecar, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    # -- translation ----------------------------------------------------------

    def auto_translate_sidecar(self, game_name: str, limit: Optional[int] = None) -> int:
        if not self.translator:
            return 0
        if limit is None:
            limit = self.MAX_AUTO_TRANSLATE

        pending: List[Tuple[str, str]] = []
        for ptr, rec in self.sidecar.items():
            if rec.get("trans"):
                continue
            orig = rec.get("orig", "")
            if not orig.strip():
                continue
            cached = self.memory.get(orig) if self.memory else None
            if cached:
                rec["trans"] = cached
                continue
            pending.append((ptr, orig))
            if len(pending) >= limit:
                break
        if not pending:
            return 0

        translated = self.translator.translate_batch(
            [t for _, t in pending], game_name)

        count = 0
        for (ptr, orig), ar in zip(pending, translated):
            if ar and ar.strip() and ar.strip() != orig.strip() \
                    and validate_codes(orig, ar):
                self.sidecar[ptr]["trans"] = ar
                count += 1
        return count

    # -- patching --------------------------------------------------------------

    @staticmethod
    def _get_path(root, segments: List[str]):
        cur = root
        for seg in segments[:-1]:
            cur = cur[int(seg)] if isinstance(cur, list) else cur.get(seg)
            if cur is None:
                return None
        return cur

    @staticmethod
    def _set_at(root, key_path: List[str], value: str) -> bool:
        cur = root
        for seg in key_path[:-1]:
            cur = cur[int(seg)] if isinstance(cur, list) else cur.get(seg)
            if cur is None:
                return False
        last = key_path[-1]
        if isinstance(cur, list):
            cur[int(last)] = value
        elif isinstance(cur, dict):
            cur[last] = value
        return True

    def apply_sidecar(self) -> Tuple[int, int]:
        """Apply sidecar translations back into the data files. Returns (files, strings)."""
        pointer_by_prefix: Dict[str, Dict[str, str]] = {}
        for ptr, rec in self.sidecar.items():
            trans = rec.get("trans", "").strip()
            if not trans:
                continue
            rel_dir, file_ptr = self._split_pointer(ptr)
            pointer_by_prefix.setdefault(rel_dir, {})[file_ptr] = trans

        files_patched, strings_applied = 0, 0
        for d in self.data_dirs:
            rel_dir = str(d.relative_to(self.game_dir)).replace("\\", "/")
            if rel_dir not in pointer_by_prefix:
                continue
            ptrs = pointer_by_prefix[rel_dir]
            grouped: Dict[str, Dict[str, str]] = {}
            for ptr, trans in ptrs.items():
                fname, *rest = ptr.split("/")
                grouped.setdefault(fname, {})[("/".join(rest))] = trans

            for fname, changes in grouped.items():
                f = d / fname
                if not f.exists():
                    continue
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                applied_here = 0
                for key_path, value in changes.items():
                    segs = key_path.split("/") if key_path else []
                    try:
                        if self._set_at(data, segs, value):
                            applied_here += 1
                    except Exception:
                        continue
                if applied_here:
                    backup = f.with_suffix(f.suffix + ".orig_backup")
                    if not backup.exists():
                        shutil.copy2(f, backup)
                    f.write_text(json.dumps(data, ensure_ascii=False,
                                            separators=(",", ":")),
                                 encoding="utf-8")
                    files_patched += 1
                    strings_applied += applied_here
        return files_patched, strings_applied

    def _split_pointer(self, ptr: str) -> Tuple[str, str]:
        """'www/data/Map001.json/events/0' -> ('www/data', 'Map001.json/events/0')."""
        for d in self.data_dirs:
            rel = str(d.relative_to(self.game_dir)).replace("\\", "/") + "/"
            if ptr.startswith(rel):
                return rel[:-1], ptr[len(rel):]
        # fallback: split on first segment pair (file name ends in .json)
        idx = ptr.find(".json/")
        if idx >= 0:
            split = idx + len(".json")
            return ptr[:split].rstrip("/"), ptr[split:]
        parts = ptr.split("/", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""

    # -- Arabic font injection --------------------------------------------------

    FONT_DIRS = [Path("C:/Windows/Fonts/segoeui.ttf"),
                 Path("C:/Windows/Fonts/tahoma.ttf"),
                 Path("C:/Windows/Fonts/arial.ttf")]

    def inject_arabic_font(self) -> bool:
        """Copy an Arabic-capable font into fonts/ and register it in css/main.css."""
        marker = "/* ELECTRON Arabic Font Patch */"
        css_candidates = list(self.game_dir.glob("**/css/main.css"))
        if not css_candidates:
            self.font_report.append("لم يتم العثور على css/main.css")
            return False

        # 1) source font: engine hooks cache first, then system fonts
        src_font = None
        engine_root = Path("C:/Users/PCD/AppData/Local/Electron/EngineHooks")
        if engine_root.exists():
            for f in engine_root.rglob("*.ttf"):
                if f.stat().st_size > 50_000:
                    src_font = f
                    break
        if not src_font:
            src_font = next((f for f in self.FONT_DIRS if f.exists()), None)
        if not src_font:
            self.font_report.append("لم يُعثر على خط عربي متاح (Segoe UI / Tahoma / Arial)")
            return False

        css = css_candidates[0]
        fonts_dir = css.parent.parent / "fonts"  # <game>/css/main.css -> <game>/fonts/
        fonts_dir.mkdir(parents=True, exist_ok=True)
        font_name = "ElectronArabic.ttf"
        dest = fonts_dir / font_name
        if not dest.exists():
            shutil.copy2(src_font, dest)

        # 2) register in css (replace previous Electron block if any)
        text = css.read_text(encoding="utf-8", errors="ignore")
        pattern = re.compile(re.escape(marker) + r".*?@font-face \{[^}]*\}\n?", re.S)
        text = pattern.sub("", text) + f"""
{marker}
@font-face {{ font-family: GameFont; font-style: normal; font-weight: normal;
  src: url("{font_name}"); }}
"""
        css.write_text(text, encoding="utf-8")
        self.font_report.append(f"تم حقن الخط {src_font.name} في {fonts_dir.name}/")
        return True

    # -- one-click orchestration ----------------------------------------------

    def run(self, game_name: Optional[str] = None) -> dict:
        game_name = game_name or self.game_dir.name
        if not self.find_data_dirs():
            return {"status": "error",
                    "message": "لم يتم العثور على مجلد بيانات RPG Maker (data/www/data)"}

        sidecar = self.build_sidecar()
        total = len(self.sidecar)
        self.auto_translate_sidecar(game_name)
        self._write_sidecar(sidecar)
        files_patched, strings_applied = self.apply_sidecar()
        self.inject_arabic_font()

        msg = (f"تم استخراج {total} نص وترجمة {strings_applied} واحدًا منها "
               f"ونشر الترجمات في {files_patched} ملف بيانات.")
        if self.font_report and any("تم حقن" in r for r in self.font_report):
            msg += "\n" + " ".join(self.font_report)
        else:
            msg += "\nملاحظة: لم يتم حقن خط عربي — قد تظهر مربعات فارغة بدل الحروف."
        return {"status": "ok", "total": total, "patched": strings_applied,
                "files": files_patched, "message": msg}


# ---------------------------------------------------------------------------
# Integration helpers (translation editor)
# ---------------------------------------------------------------------------

def rpgmaker_translations_view(game_dir: Path) -> List[dict]:
    f = Path(game_dir) / RPGMakerPatcher.SIDECAR_DIR / RPGMakerPatcher.SIDECAR_NAME
    if not f.exists():
        return []
    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        return []
    return [{"key": k, "orig": rec.get("orig", ""), "trans": rec.get("trans", "")}
            for k, rec in data.items()]


def save_rpgmaker_translations(game_dir: Path, pairs: List[dict],
                               translator=None, memory=None) -> dict:
    patcher = RPGMakerPatcher(game_dir, translator=translator, memory=memory)
    patcher.build_sidecar()          # refresh pointers against current data
    for p in pairs:
        key = p.get("key") or ""
        if key and key in patcher.sidecar:
            patcher.sidecar[key]["trans"] = (p.get("trans") or "").strip()
    patcher._write_sidecar(patcher._sidecar_path())
    files, strings = patcher.apply_sidecar()
    patcher.inject_arabic_font()
    return {"status": "ok", "count": strings, "files": files}
