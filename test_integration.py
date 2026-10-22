"""ElectronApi integration test with simulated games (offline, no API key)."""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, ".")

from electron_ui import ElectronApi   # noqa: E402

SIM = Path("C:/Users/PCD/AppData/Local/Temp/opencode/api_sim")


def make_unreal_game(game: Path):
    build_fake = game / "Game" / "Content" / "Localization" / "Game" / "en" / "Game.locres"
    from pylocres import LocresFile, Entry, entry_hash, Namespace
    from unittest.mock import patch
    loc = LocresFile()
    ns = Namespace("UI_FlavorText")
    loc.add(ns)
    for key, src in [("ui_tip_01", "Hold F to tip the cow."),
                     ("ui_title", "Bean Farmer Ultra"), ("q?", "Quest complete!")]:
        ns.add(Entry(key, src, entry_hash(src)))
    build_fake.parent.mkdir(parents=True, exist_ok=True)
    loc.write(str(build_fake))


def make_rpg_game(game: Path):
    data = game / "www" / "data"
    data.mkdir(parents=True, exist_ok=True)
    map001 = {"events": [None, {"pages": [None, {"list": [
        None,
        {"code": 401, "indent": 0, "parameters": ["\\N[2] The mine is sealed!"]},
        {"code": 0, "indent": 0, "parameters": []},
    ]}]}]}
    (data / "Map001.json").write_text(json.dumps(map001, ensure_ascii=False), encoding="utf-8")
    (data / "System.json").write_text(
        json.dumps({"gameTitle": "Mine Delvers MV", "currencyUnit": "MinesBucks"}, ensure_ascii=False),
        encoding="utf-8")
    css = game / "www" / "css"
    css.mkdir(parents=True, exist_ok=True)
    (css / "main.css").write_text('@font-face{font-family:GameFont;src:url(m.ttf);}', encoding="utf-8")


def run_unreal_flow():
    game = SIM / "Steam" / "common" / "BeanFarmerUE"
    if game.exists():
        shutil.rmtree(game)
    make_unreal_game(game)

    api = ElectronApi()
    sel = api.select_game(str(game))
    assert sel["engine_type"] == "unreal", sel

    res = api.localize_game()
    print("UNREAL localize:", res["status"], res.get("patched"))
    assert res["status"] == "ok"

    # editor view: full table present with empty translations
    editor = api.get_game_translations()
    assert editor["engine"] == "unreal"
    assert len(editor["pairs"]) == 3, editor["pairs"]

    # manual edit one row (offline translation)
    pairs = editor["pairs"]
    pairs[0]["trans"] = "نصيحة قهرياً.. أحب الفاصوليا"
    res = api.save_game_translations(pairs)
    assert res["status"] == "ok", res

    loc = json.loads((game / "ElectronLoc" / "en_Game.json").read_text(encoding="utf-8"))
    assert any(v["trans"] == "نصيحة قهرياً.. أحب الفاصوليا" for v in loc.values())

    # restore puts original bytes back
    restore = api.restore_game()
    print("UNREAL restore:", restore)


def run_rpg_flow():
    game = SIM / "Steam" / "common" / "MineDelvers"
    if game.exists():
        shutil.rmtree(game)
    make_rpg_game(game)

    api = ElectronApi()
    sel = api.select_game(str(game))
    assert sel["engine_type"] == "rpg_maker", sel

    res = api.localize_game()
    print("RPG localize:", res["status"], res.get("patched"))
    assert res["status"] == "ok"

    editor = api.get_game_translations()
    assert editor["engine"] == "rpg_maker"
    assert editor["pairs"], "editor must see extracted strings"

    # manually translate all rows
    for p in editor["pairs"]:
        p["trans"] = f"عربي({p['orig'][:8]})"
    save = api.save_game_translations(editor["pairs"])
    assert save["status"] == "ok", save

    data = json.loads((game / "www" / "data" / "Map001.json").read_text(encoding="utf-8"))
    txt = data["events"][1]["pages"][1]["list"][1]["parameters"][0]
    assert "\\N[2]" in txt and "The mine" not in txt, txt
    system = json.loads((game / "www" / "data" / "System.json").read_text(encoding="utf-8"))
    assert system["gameTitle"].startswith("عربي"), system["gameTitle"]
    assert system["currencyUnit"].startswith("عربي")

    restore = api.restore_game()
    data = json.loads((game / "www" / "data" / "Map001.json").read_text(encoding="utf-8"))
    assert data["events"][1]["pages"][1]["list"][1]["parameters"][0] == "\\N[2] The mine is sealed!"
    print("RPG restore:", restore, "-> original text verified")


if __name__ == "__main__":
    if SIM.exists():
        shutil.rmtree(SIM)
    print("== RPG Maker flow ==")
    run_rpg_flow()
    print("== Unreal flow ==")
    run_unreal_flow()
    print("\nINTEGRATION TESTS PASSED")
