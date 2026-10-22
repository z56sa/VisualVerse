"""
ue_locres.py — Unreal Engine .locres support for ELECTRON.

Real engine-level localization: parse the binary .locres files the engine
actually loads at runtime, expose every (namespace, key, source, translation)
tuple, let the AI pipeline translate them, then rebuild valid locres binaries.

Binary container logic is delegated to the `pylocres` package (MIT), which
supports every known LocRes format version:
    Legacy (0), Compact (1), Optimized (2), CityHash (3 - UE5).
Culture selection, safety backups and the AI/translator glue live here.

Author: ELECTRON Game Localizer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pylocres import LocresFile                      # type: ignore
from pylocres.file_io import FString                 # type: ignore
from pylocres.locres import LOCRES_MAGIC             # type: ignore

from binsl import BinReader                          # type: ignore


# ---------------------------------------------------------------------------
# FString hardening
# ---------------------------------------------------------------------------

def _robust_fstring_read(BR, length=None):
    """Drop-in replacement for pylocres.file_io.FString.read.

    UE contract on load (FArchive::operator<<):
      * length <  0 -> UTF-16LE, payload = (-length) * 2 bytes
      * length >  0 -> per-byte ANSI payload of `length` bytes
      * length == 0 -> empty string

    pylocres decodes ANSI as a narrow "ascii" codec, which destroys Western
    accented text on shipped English locres files. We keep the byte/frame
    layout EXACTLY (never guessing lengths, so the cursor stays aligned for
    every subsequent read) and only widen the character decode to cp1252.
    """
    if length is None:
        length = BR.int32()
    if length == 0:
        return ""
    if length < 0:
        size = -length * 2
        data = BR.read(size)
        return data.decode("utf-16-le", "replace").rstrip("\x00")

    data = BR.read(length)
    if data.endswith(b"\x00"):
        data = data[:-1]
    for codec in ("ascii", "cp1252"):
        try:
            return data.decode(codec).rstrip("\x00")
        except UnicodeDecodeError:
            continue
    return data.decode("utf-16-le", "replace").rstrip("\x00")


FString.read = staticmethod(_robust_fstring_read)  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Culture helpers
# ---------------------------------------------------------------------------

PREFERRED_CULTURES = ("en", "en-us", "en-gb")


def guess_culture(locres_path: Path) -> str:
    """Best-effort culture guess for a locres file ('en', 'de', 'unknown'...)."""
    parent = locres_path.parent.name.lower()
    if parent in PREFERRED_CULTURES:
        return "en"
    import re
    if re.fullmatch(r"[a-z]{2,3}(-[a-z0-9]+)?", parent):
        return parent.split("-")[0]
    name = locres_path.name.lower()
    if "en" in name and "locres" in name:
        return "en"
    return "unknown"


def read_locres(path: Path) -> LocresFile:
    """Read a locres from disk into a LocresFile (bytes, per binsl contract)."""
    loc = LocresFile()
    loc.read(Path(path).read_bytes())
    return loc


def write_locres(loc: LocresFile, path: Path) -> None:
    """Serialize the LocresFile back to a valid binary locres."""
    loc.write(str(path))


# ---------------------------------------------------------------------------
# Patcher
# ---------------------------------------------------------------------------

class UnrealLocresPatcher:
    """Reads, exports, patches and writes Unreal .locres resources."""

    SIDECAR_DIR = "ElectronLoc"
    MAX_AUTO_TRANSLATE = 200  # one-click pass ceiling; rest via manual editor

    def __init__(self, game_dir: Path, translator=None, memory=None):
        self.game_dir = Path(game_dir)
        self.translator = translator          # GameTextTranslator (optional)
        self.memory = memory                  # LocalTranslationMemory (optional)
        self.locres_files: List[Path] = []
        self.chosen_files: List[Path] = []
        self.sidecar: Dict[str, Dict[str, str]] = {}
        self.current_file: Optional[Path] = None

    # -- discovery ----------------------------------------------------------

    def find_locres_files(self) -> List[Path]:
        root = self.game_dir
        candidates = root.glob("**/Localization/**/*.locres")
        found = list(candidates)
        if not found:
            found = list(root.glob("**/*.locres"))
        self.locres_files = [p for p in found if p.is_file() and p.stat().st_size > 40]
        return self.locres_files

    def choose_target_files(self) -> List[Path]:
        """Pick which locres files to patch.

        Games ship one locres per culture. The game displays whichever culture
        its launcher/settings select; localizers therefore patch the culture
        the game actually RUNS in. Priority:
          1. en / en-US / en-GB folders  (by far the common shipped culture)
          2. Game.locres (primary namespace file, largest copy)
          3. the only locres in the game
        """
        if not self.locres_files:
            self.find_locres_files()

        english = [f for f in self.locres_files if guess_culture(f) == "en"]
        if english:
            self.chosen_files = english
            return english

        primaries = [f for f in self.locres_files if f.stem.lower() == "game"]
        if primaries:
            self.chosen_files = sorted(primaries, key=lambda p: p.stat().st_size)
            return self.chosen_files

        if len(self.locres_files) == 1:
            self.chosen_files = list(self.locres_files)
        elif self.locres_files:
            biggest = max(self.locres_files, key=lambda p: p.stat().st_size)
            self.chosen_files = [biggest]
        return self.chosen_files

    # -- sidecar (translation editor persistence) ----------------------------

    def _sidecar_path(self, locres_path: Path) -> Path:
        sidecar_dir = self.game_dir / self.SIDECAR_DIR
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        cult = guess_culture(locres_path)
        return sidecar_dir / f"{cult}_{locres_path.stem}.json"

    def read_or_build_sidecar(self, locres_path: Path) -> Path:
        """Load (or bootstrap) the sidecar JSON for one locres file."""
        sidecar_path = self._sidecar_path(locres_path)
        self.current_file = locres_path
        if sidecar_path.exists():
            try:
                self.sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
                return sidecar_path
            except Exception:
                pass  # rebuild on corrupt sidecar

        records = self.export_entries(locres_path)
        self.sidecar = {r["key"]: {"orig": r["orig"], "trans": r["trans"]}
                        for r in records}
        self._write_sidecar(sidecar_path)
        return sidecar_path

    def _write_sidecar(self, path: Path) -> None:
        path.write_text(json.dumps(self.sidecar, ensure_ascii=False, indent=1),
                        encoding="utf-8")

    def export_entries(self, locres_path: Path) -> List[dict]:
        """Flat records: [{"key": "namespace|key", "orig": str, "trans": str}]."""
        try:
            loc = read_locres(locres_path)
        except Exception as e:
            raise RuntimeError(f"تعذر قراءة {locres_path.name}: {e}") from e

        records = []
        for ns in loc:
            for entry in ns:
                records.append({
                    "key": f"{ns.name}|{entry.key}",
                    "orig": entry.translation,
                    "trans": "",
                })
        return records

    # -- one-click AI translation pass ---------------------------------------

    def auto_translate_sidecar(self, game_name: str,
                               limit: Optional[int] = None) -> int:
        """Translate (via AI) up to `limit` untranslated sidecar strings."""
        if not self.translator:
            return 0
        if limit is None:
            limit = self.MAX_AUTO_TRANSLATE

        pending: List[Tuple[str, str]] = []
        for key, rec in self.sidecar.items():
            if rec.get("trans"):
                continue
            orig = rec.get("orig", "")
            if not orig.strip():
                continue
            cached = self.memory.get(orig) if self.memory else None
            if cached:
                rec["trans"] = cached
                continue
            pending.append((key, orig))
            if len(pending) >= limit:
                break
        if not pending:
            return 0

        translated = self.translator.translate_batch(
            [t for _, t in pending], game_name)
        count = 0
        for (key, orig), ar in zip(pending, translated):
            if ar and ar.strip() and ar.strip() != orig.strip():
                self.sidecar[key]["trans"] = ar
                count += 1
        return count

    # -- binary write-back ----------------------------------------------------

    def apply_sidecar_to_file(self, locres_path: Path) -> int:
        """Write sidecar translations back into the binary locres (backup first)."""
        loc = read_locres(locres_path)

        applied = 0
        for ns in loc:
            for entry in ns:
                key = f"{ns.name}|{entry.key}"
                rec = self.sidecar.get(key)
                if rec and rec.get("trans", "").strip():
                    ar = rec["trans"].strip()
                    if ar != (rec.get("orig") or "").strip():
                        entry.translation = ar
                        applied += 1

        if applied:
            backup = locres_path.with_suffix(locres_path.suffix + ".orig_backup")
            if not backup.exists():
                import shutil
                shutil.copy2(locres_path, backup)

            tmp = locres_path.with_suffix(".locres.tmp")
            write_locres(loc, tmp)
            tmp.replace(locres_path)  # atomic swap on same volume
        return applied

    # -- one-click orchestration ----------------------------------------------

    def run(self, game_name: Optional[str] = None) -> dict:
        """Full pipeline: pick files -> sidecar -> AI pass -> patch binaries."""
        self.choose_target_files()
        if not self.chosen_files:
            return {"status": "error",
                    "message": "لم يتم العثور على ملفات Locres قابلة للترجمة. "
                               "قد تكون اللعبة معبأة داخل ملفات .pak مضغوطة."}

        game_name = game_name or self.game_dir.name
        total_extracted = 0
        total_patched = 0
        sidecar_paths = []
        errors = []

        for f in self.chosen_files:
            try:
                sidecar = self.read_or_build_sidecar(f)
                total_extracted += len(self.sidecar)
                self.auto_translate_sidecar(game_name)
                self._write_sidecar(sidecar)
                total_patched += self.apply_sidecar_to_file(f)
                sidecar_paths.append(str(sidecar))
            except Exception as e:
                errors.append(f"{f.name}: {e}")

        if errors and not total_patched:
            return {"status": "error",
                    "message": "فشل تعريب ملفات Locres:\n" + "\n".join(errors[:3])}

        return {
            "status": "ok",
            "total": total_extracted,
            "patched": total_patched,
            "files": len(sidecar_paths),
            "message": (
                f"تم استخراج {total_extracted} نص وترجمة {total_patched} منها "
                f"من {len(sidecar_paths)} ملف Locres!\n"
                "افتح محرر التعريب اليدوي لمراجعة البرمجيات وترجمتها جميعاً."
            ),
        }


# ---------------------------------------------------------------------------
# Integration helpers used by electron_ui.ElectronApi
# ---------------------------------------------------------------------------

def is_unreal_game_dir(game_dir: Path) -> bool:
    return bool(list(Path(game_dir).glob("**/*.locres")))


def unreal_translations_view(game_dir: Path) -> List[dict]:
    """Load sidecar records for the manual translation editor."""
    sidecar_dir = Path(game_dir) / UnrealLocresPatcher.SIDECAR_DIR
    pairs: List[dict] = []
    for f in sorted(sidecar_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for key, rec in data.items():
            pairs.append({"key": key, "orig": rec.get("orig", ""),
                          "trans": rec.get("trans", "")})
    return pairs


def save_unreal_translations(game_dir: Path, pairs: List[dict],
                             translator=None, memory=None) -> dict:
    """Editor save: update every matching sidecar + rebuild binary locres."""
    patcher = UnrealLocresPatcher(game_dir, translator=translator, memory=memory)
    targets = patcher.choose_target_files()
    if not targets:
        return {"status": "error", "message": "لم يُعثر على ملفات Locres لحفظ الترجمات"}

    for f in targets:
        sidecar_path = patcher.read_or_build_sidecar(f)
        for p in pairs:
            key = p.get("key") or ""
            if key and key in patcher.sidecar:
                patcher.sidecar[key]["trans"] = (p.get("trans") or "").strip()
        patcher._write_sidecar(sidecar_path)
        patcher.apply_sidecar_to_file(f)

    return {"status": "ok", "count": len(pairs)}
