"""Where the game and its folders are on this computer: the Steam install (any library, Windows, macOS or Linux),
its Unity data folder, and the folder the game loads mods from."""
from __future__ import annotations

import os
import pathlib
import re
import sys

GAME_FOLDER = "Caves of Qud"
# the Unity data folder inside the install: CoQ_Data on Windows and Linux, inside the app bundle on macOS
DATA_LAYOUTS = ("CoQ_Data", "CoQ.app/Contents/Resources/Data")
LIBRARY_PATH = re.compile(r'"path"\s+"((?:[^"\\]|\\.)*)"')


def data_dir(game: pathlib.Path) -> pathlib.Path | None:
    """The game's data folder (StreamingAssets, Managed) in an install folder, or None if it is not one."""
    for layout in DATA_LAYOUTS:
        d = game / layout
        if (d / "StreamingAssets" / "Base").is_dir():
            return d
    return None


def steam_roots(platform: str = sys.platform, home: pathlib.Path | None = None) -> list[pathlib.Path]:
    """Where Steam itself may be installed: the registry on Windows, the usual folders elsewhere."""
    home = home or pathlib.Path.home()
    if platform == "win32":
        roots = []
        try:
            import winreg
            for hive, key, value in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                                     (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath")):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        roots.append(pathlib.Path(winreg.QueryValueEx(k, value)[0]))
                except OSError:
                    pass
        except ImportError:
            pass
        return roots + [pathlib.Path(r"C:\Program Files (x86)\Steam"), pathlib.Path(r"C:\Program Files\Steam")]
    if platform == "darwin":
        return [home / "Library" / "Application Support" / "Steam"]
    return [home / ".steam" / "steam", home / ".local" / "share" / "Steam",
            home / ".var" / "app" / "com.valvesoftware.Steam" / ".local" / "share" / "Steam"]


def libraries(root: pathlib.Path) -> list[pathlib.Path]:
    """A Steam install and the extra libraries its libraryfolders.vdf lists (games on other drives)."""
    found = [root]
    vdf = root / "steamapps" / "libraryfolders.vdf"
    try:
        text = vdf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return found
    for m in LIBRARY_PATH.finditer(text):
        path = pathlib.Path(re.sub(r"\\(.)", r"\1", m.group(1)))
        if path not in found:
            found.append(path)
    return found


def find_game(platform: str = sys.platform, home: pathlib.Path | None = None) -> pathlib.Path | None:
    """The game's install folder: QUD_GAME_DIR if it is set, otherwise the first Steam library that has the game."""
    env = os.environ.get("QUD_GAME_DIR")
    if env:
        return pathlib.Path(env)
    for root in steam_roots(platform, home):
        for library in libraries(root):
            game = library / "steamapps" / "common" / GAME_FOLDER
            if data_dir(game):
                return game
    return None


def mods_dir(platform: str = sys.platform, home: pathlib.Path | None = None) -> pathlib.Path:
    """The folder the game loads local mods from (wiki.cavesofqud.com/wiki/File_locations)."""
    home = home or pathlib.Path.home()
    if platform == "win32":
        profile = pathlib.Path(os.environ.get("USERPROFILE", str(home)))
        return profile / "AppData" / "LocalLow" / "Freehold Games" / "CavesOfQud" / "Mods"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "com.FreeholdGames.CavesOfQud" / "Mods"
    return home / ".config" / "unity3d" / "Freehold Games" / "CavesOfQud" / "Mods"
