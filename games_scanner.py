import os
import re
import json
try:
    import vdf
except ImportError:
    vdf = None
from pathlib import Path
from typing import List, Dict

class InstalledGamesScanner:
    """Scans the PC for all installed games from Steam, Epic, GOG, and common locations."""

    # Common Steam library paths on Windows
    STEAM_PATHS = [
        Path("C:/Program Files (x86)/Steam"),
        Path("C:/Program Files/Steam"),
        Path(os.path.expanduser("~/Steam")),
    ]

    # Common Epic Games install path
    EPIC_MANIFESTS = Path("C:/ProgramData/Epic/EpicGamesLauncher/Data/Manifests")

    # Common GOG paths
    GOG_DB = Path("C:/ProgramData/GOG.com/Galaxy/storage/galaxy.db")

    @staticmethod
    def _get_steam_libraries(steam_root: Path) -> List[Path]:
        """Reads Steam library folders from libraryfolders.vdf or JSON."""
        libraries = [steam_root / "steamapps" / "common"]
        vdf_path = steam_root / "steamapps" / "libraryfolders.vdf"
        if not vdf_path.exists():
            return libraries
        try:
            content = vdf_path.read_text(encoding="utf-8", errors="ignore")
            # Extract paths using regex (works without vdf library)
            extra_paths = re.findall(r'"path"\s*"([^"]+)"', content)
            for p in extra_paths:
                extra_lib = Path(p.replace("\\\\", "/").replace("\\", "/")) / "steamapps" / "common"
                if extra_lib.exists():
                    libraries.append(extra_lib)
        except Exception:
            pass
        return libraries

    @staticmethod
    def _get_steam_game_icon(game_dir: Path) -> str:
        """Returns Steam icon emoji or generic game icon."""
        return "🎮"

    def scan_steam(self) -> List[Dict]:
        games = []
        for steam_root in self.STEAM_PATHS:
            if not steam_root.exists():
                continue
            libraries = self._get_steam_libraries(steam_root)
            for lib in libraries:
                if not lib.exists():
                    continue
                for game_folder in lib.iterdir():
                    if game_folder.is_dir() and not game_folder.name.startswith("."):
                        games.append({
                            "name": game_folder.name,
                            "path": str(game_folder),
                            "source": "Steam",
                            "icon": "🟦"
                        })
        return games

    def scan_epic(self) -> List[Dict]:
        games = []
        if not self.EPIC_MANIFESTS.exists():
            return games
        try:
            for manifest_file in self.EPIC_MANIFESTS.glob("*.item"):
                try:
                    data = json.loads(manifest_file.read_text(encoding="utf-8"))
                    install_loc = data.get("InstallLocation", "")
                    display_name = data.get("DisplayName", "")
                    if install_loc and display_name and Path(install_loc).exists():
                        games.append({
                            "name": display_name,
                            "path": install_loc,
                            "source": "Epic Games",
                            "icon": "🟣"
                        })
                except Exception:
                    pass
        except Exception:
            pass
        return games

    def scan_common_locations(self) -> List[Dict]:
        """Fallback: scan common program files locations."""
        games = []
        common_dirs = [
            Path("C:/Program Files (x86)/Steam/steamapps/common"),
            Path("C:/Program Files/Steam/steamapps/common"),
            Path("C:/Program Files/Epic Games"),
            Path("C:/Program Files (x86)/GOG Galaxy/Games"),
            Path("C:/GOG Games"),
            Path("D:/Games"),
            Path("D:/SteamLibrary/steamapps/common"),
            Path("E:/Games"),
            Path("E:/SteamLibrary/steamapps/common"),
        ]
        seen = set()
        for common in common_dirs:
            if not common.exists():
                continue
            for folder in common.iterdir():
                if folder.is_dir() and str(folder) not in seen:
                    seen.add(str(folder))
                    # Check if it looks like a real game (has exe files)
                    has_exe = any(folder.glob("*.exe"))
                    if has_exe or any(folder.iterdir()):
                        source = "Steam" if "steam" in str(common).lower() else \
                                 "Epic" if "epic" in str(common).lower() else "Other"
                        icon = "🟦" if source == "Steam" else "🟣" if source == "Epic" else "🎮"
                        games.append({
                            "name": folder.name,
                            "path": str(folder),
                            "source": source,
                            "icon": icon
                        })
        return games

    def scan_all(self) -> List[Dict]:
        """Full scan across all game launchers and common directories."""
        all_games = []
        seen_paths = set()

        for game in self.scan_steam() + self.scan_epic() + self.scan_common_locations():
            norm_path = game["path"].lower().replace("\\", "/")
            if norm_path not in seen_paths:
                seen_paths.add(norm_path)
                all_games.append(game)

        # Sort alphabetically
        return sorted(all_games, key=lambda g: g["name"].lower())
