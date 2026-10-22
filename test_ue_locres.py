"""Quick roundtrip validation for ue_locres.py (runs without network)."""
import json
import shutil
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from ue_locres import UnrealLocresPatcher, read_locres, unreal_translations_view

SIM_DIR = Path("C:/Users/PCD/AppData/Local/Temp/opencode/ue_sim")


class MemoryStub:
    def __init__(self):
        self.d = {}
    def get(self, t):
        return self.d.get(t.strip())
    def put(self, t, tr, tag=""):
        self.d[t.strip()] = tr.strip()


class TranslatorStub:
    """Pretends to be GameTextTranslator: prefix rule + placeholder safety."""

    def translate_batch(self, texts, game=""):
        out = []
        for t in texts:
            ar = f"[AR] {t}" if len(t) > 2 else t
            out.append(ar)
        return out


def build_fake_locres(path: Path) -> None:
    from pylocres import LocresFile, Entry, entry_hash
    loc = LocresFile()
    ns = loc.add.__self__ if False else None
    from pylocres import Namespace
    ns = Namespace("Game")
    loc.add(ns)
    strings = [
        ("hello", "Hello World"),
        ("goodbye", "Goodbye World"),
        ("std", "Standard"),
        ("needs-trans", "Save the princess!"),
        ("std2", "Standard"),
    ]
    for key, src in strings:
        ns.add(Entry(key, src, entry_hash(src)))
    path.parent.mkdir(parents=True, exist_ok=True)
    loc.write(str(path))


def main():
    game = SIM_DIR / "Steam" / "common" / "TestUEGame"
    if game.exists():
        shutil.rmtree(game)
    build_fake_locres(game / "Game" / "Content" / "Localization" / "Game" / "en" / "Game.locres")

    patcher = UnrealLocresPatcher(game, translator=TranslatorStub(), memory=MemoryStub())
    targets = patcher.choose_target_files()
    assert len(targets) == 1, f"expected 1 target, got {targets}"

    sidecar_path = patcher.read_or_build_sidecar(targets[0])
    print("sidecar records:", len(patcher.sidecar))

    n = patcher.auto_translate_sidecar("TestUEGame")
    print("auto translated:", n)
    assert n == 5, f"expected 5 new translations, got {n}"  # one per unique key

    patcher._write_sidecar(sidecar_path)
    applied = patcher.apply_sidecar_to_file(targets[0])
    print("applied:", applied)
    assert applied == 5, f"expected 5 applied, got {applied}"

    # Verify game file content after rewrite
    loc2 = read_locres(targets[0])
    found = {}
    for ns in loc2:
        for e in ns:
            found[e.key] = e.translation
    print("rewritten entries:", found)
    assert found["hello"] == "[AR] Hello World"
    assert found["std"] == "[AR] Standard"
    assert found["needs-trans"] == "[AR] Save the princess!"

    # Editor roundtrip
    pairs = unreal_translations_view(game)
    print("editor view rows:", len(pairs))
    assert pairs and pairs[0]["key"].endswith("hello")

    # Restore original: backup exists?
    backup = targets[0].with_suffix(targets[0].suffix + ".orig_backup")
    original = backup.read_bytes()
    assert original, "backup missing"

    # Save flow (manual editor)
    pairs[0]["trans"] = "تحية يا بطل"  # Arabic
    from ue_locres import save_unreal_translations
    res = save_unreal_translations(game, pairs)
    assert res["status"] == "ok"
    loc3 = read_locres(targets[0])
    for ns in loc3:
        for e in ns:
            if e.key == "hello":
                assert e.translation == "تحية يا بطل", e.translation

    print("\nALL LOCRES TESTS PASSED")


if __name__ == "__main__":
    main()
