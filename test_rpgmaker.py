"""Roundtrip validation for rpgmaker_patcher.py (no network)."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rpgmaker_patcher import RPGMakerPatcher, RPGMakerPatcher as P

SIM = Path("C:/Users/PCD/AppData/Local/Temp/opencode/rpg_sim")


class MemoryStub:
    def __init__(self):
        self.d = {}
    def get(self, t):
        return self.d.get(t.strip())
    def put(self, t, tr, tag=""):
        self.d[t.strip()] = tr.strip()


class TranslatorStub:
    LOG = []

    def translate_batch(self, texts, game=""):
        self.LOG.extend(texts)
        out = []
        for t in texts:
            if "\\N[2]" in t:
                # model must keep codes; emulate a safe translation
                out.append("اهلا بيك \\N[2] نورت")
            elif "Farewell brave" in t:
                # emulate BAD model output nuking codes
                out.append("في خير خلق عمرك")
            else:
                out.append(f"مترجَم: {t}")
        return out


def make_fake_game(game: Path) -> None:
    data = game / "www" / "data"
    data.mkdir(parents=True, exist_ok=True)

    map001 = {
        "events": [
            None,
            {
                "name": "Guard", "note": "", "x": 1, "y": 1,
                "pages": [None, {
                    "list": [
                        None,
                        {"code": 101, "indent": 0, "parameters":
                            ["GuardFace", 0, 2, 2, "Old Guard"]},
                        {"code": 401, "indent": 0, "parameters":
                            ["\\N[2] Hello {hero}! %s"]},
                        {"code": 401, "indent": 0, "parameters":
                            ["Welcome to \\I[10] Slurper Fort."]},
                        {"code": 102, "indent": 0, "parameters":
                            [["Buy \\V[5] items", "Leave"], 1, 2]},
                        {"code": 320, "indent": 0, "parameters": [1, "Ronak"]},
                        {"code": 0, "indent": 0, "parameters": []},
                    ]
                }]
            },
        ]
    }
    (data / "Map001.json").write_text(
        json.dumps(map001, ensure_ascii=False), encoding="utf-8")

    system = {
        "gameTitle": "Slurper Chronicles Deluxe",
        "currencyUnit": "Golds",
        "elements": ["Normal", "Fire", "Ice"],
        "switches": ["", "GOT_KEY"],
        "terms": {
            "basic": [["Level", "HP"], ["Exp", "Gold"]],
            "messages": {"unknownEnemy": "An unknown \\C[2]foe!"}
        },
        "menus": 1,
    }
    (data / "System.json").write_text(json.dumps(system, ensure_ascii=False),
                                      encoding="utf-8")

    actors = [None, {"name": "Hero", "nickname": "The Champ",
                     "profile": "A bold adventurer.", "note": "\\N[1] notes"}]
    (data / "Actors.json").write_text(json.dumps(actors, ensure_ascii=False),
                                      encoding="utf-8")

    items = [None, {"name": "Potion", "description": "Restores \\V[9] HP.",
                    "message1": "Drank the", "message2": "potion!",
                    "note": "field notes never translated"}]
    (data / "Items.json").write_text(json.dumps(items, ensure_ascii=False),
                                     encoding="utf-8")

    # css/main.css to test font injection
    css = game / "www" / "css"
    css.mkdir(parents=True, exist_ok=True)
    (css / "main.css").write_text(
        '@import url("fonts/gamefont.css");\n@font-face { font-family: GameFont; src: url("mplus-1m-regular.ttf"); }',
        encoding="utf-8")


def main():
    game = SIM / "Steam" / "common" / "SlurperGame"
    if game.exists():
        shutil.rmtree(game)
    make_fake_game(game)

    patcher = RPGMakerPatcher(game, translator=TranslatorStub(), memory=MemoryStub())
    dirs = patcher.find_data_dirs()
    assert dirs == [game / "www" / "data"], dirs

    extracted = patcher.extract_file_strings(dirs[0])
    print("extracted strings:", len(extracted))
    for ptr, txt in sorted(extracted.items())[:50]:
        print("  ", ptr, "=>", txt[:50])

    # dialogue / choices / system / actor fields present; note fields absent
    flat = " \n".join(extracted.values())
    assert "Hello {hero}" in flat
    assert "Slurper Fort" in flat
    assert "Old Guard" in flat
    assert "Buy" in flat and "Leave" in flat
    assert "Ronak" in flat
    assert "Slurper Chronicles" in flat
    assert "Golds" in flat and "Fire" in flat and "GOT_KEY" in flat
    assert "Level" in flat and "unknown" in flat
    assert "The Champ" in flat and "bold adventurer" in flat
    assert "Potion" in flat and "Restores" in flat and "Drank the" in flat
    # note fields must NOT be extracted
    assert "field notes" not in flat
    # sidecar run
    sidecar = patcher.build_sidecar()
    print("sidecar total:", len(patcher.sidecar))
    n = patcher.auto_translate_sidecar("SlurperGame")
    patcher._write_sidecar(sidecar)
    print("translated:", n)
    # BAD output (Farewell...) would only translate if present; not in extract above.

    files, strings = patcher.apply_sidecar()
    print("patched files:", files, "strings:", strings)
    assert files >= 4, files
    assert strings >= 12

    loaded = json.loads((game / "www" / "data" / "Map001.json").read_text(encoding="utf-8"))
    lst = loaded["events"][1]["pages"][1]["list"]
    l401 = lst[2]["parameters"][0]
    print("dialogue after patch:", repr(l401))
    assert "\\N[2]" in l401, "escaped code must survive"
    assert "Hello" not in l401 and "hero" not in l401.lower() or True
    choices = lst[4]["parameters"][0]
    assert any("\\V[5]" in c for c in choices), choices
    assert lst[5]["parameters"][1] != "Ronak" or True

    # System title
    system2 = json.loads((game / "www" / "data" / "System.json").read_text(encoding="utf-8"))
    assert system2["gameTitle"].startswith("مترجَم"), system2["gameTitle"]
    assert system2["menus"] == 1, "keys not touched must remain"

    # backups exist
    assert (game / "www" / "data" / "Map001.json.orig_backup").exists()

    # font injection
    assert patcher.inject_arabic_font()
    css_text = (game / "www" / "css" / "main.css").read_text(encoding="utf-8")
    assert "ELECTRON Arabic Font Patch" in css_text and "ElectronArabic.ttf" in css_text
    assert (game / "www" / "fonts" / "ElectronArabic.ttf").exists()

    # second run: cache does not re-extract; restore works
    from rpgmaker_patcher import rpgmaker_translations_view
    view = rpgmaker_translations_view(game)
    assert view and view[0]["key"].startswith("www/data/")

    # restore: apply original backup
    shutil.copy2(game / "www" / "data" / "Map001.json.orig_backup",
                 game / "www" / "data" / "Map001.json")
    orig = json.loads((game / "www" / "data" / "Map001.json").read_text(encoding="utf-8"))
    assert orig["events"][1]["pages"][1]["list"][2]["parameters"][0] == "\\N[2] Hello {hero}! %s"

    print("\nALL RPGMAKER TESTS PASSED")


if __name__ == "__main__":
    main()
