"""py tools/qud.py install: the translation into the game, from this checkout.

Finds the game (game.py), decompiles its code for the code tables when ilspycmd is installed, builds mod/ from
the game's own English (the repository holds only our Ukrainian), and links mod/ into the game's Mods folder.
Players read it, so it speaks Ukrainian.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

from . import commands, game, sources, units

NAME = "CavesOfQudUA"
# the decompiler the code tables' keys were taken with: another version may write some code differently
ILSPY_VERSION = "11.1.0.9782"
ILSPY_HINT = (f"встановіть .NET SDK (https://dotnet.microsoft.com/download) і виконайте\n"
              f"  dotnet tool install -g ilspycmd --version {ILSPY_VERSION}\n"
              f"а тоді запустіть встановлення ще раз")


def ilspycmd() -> str | None:
    """The decompiler: on PATH, or where `dotnet tool install -g` puts it when PATH does not have that folder."""
    found = shutil.which("ilspycmd")
    if found:
        return found
    local = pathlib.Path.home() / ".dotnet" / "tools" / ("ilspycmd.exe" if sys.platform == "win32" else "ilspycmd")
    return str(local) if local.exists() else None


def decompile(data: pathlib.Path, build: str, repo: pathlib.Path = sources.REPO) -> pathlib.Path | None:
    """work/decompiled/<build>/Assembly-CSharp, which sources.load reads the code tables from: decompiled now if
    it is not there yet (into a side folder first, so a broken run leaves nothing half-done), None without
    ilspycmd."""
    out = repo / "work" / "decompiled" / build / "Assembly-CSharp"
    if out.is_dir():
        return out
    exe = ilspycmd()
    if not exe:
        return None
    version = subprocess.run([exe, "--version"], capture_output=True, text=True).stdout
    if ILSPY_VERSION not in version:
        print(f"Увага: ilspycmd не версії {ILSPY_VERSION}, з якою зроблено переклад, тож частина тексту з коду гри "
              f"може лишитися англійською. Точна версія:\n  dotnet tool update -g ilspycmd --version {ILSPY_VERSION}")
    managed = data / "Managed"
    partial = out.with_name(out.name + ".partial")
    if partial.exists():
        shutil.rmtree(partial)
    partial.parent.mkdir(parents=True, exist_ok=True)
    print(f"Декомпілюю код гри {build} (лише для перекладу, кілька хвилин)…")
    subprocess.run([exe, "-p", "-o", str(partial), "-r", str(managed), str(managed / "Assembly-CSharp.dll")],
                   check=True, stdout=subprocess.DEVNULL)
    partial.rename(out)
    return out


def link_target(path: pathlib.Path) -> str | None:
    """Where a symlink or a Windows junction points, or None when path is a real folder."""
    try:
        return os.readlink(path)
    except (OSError, ValueError):
        return None


def same_folder(a: str | pathlib.Path, b: str | pathlib.Path) -> bool:
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def link(target: pathlib.Path, mods: pathlib.Path) -> pathlib.Path:
    """mods/CavesOfQudUA → target. A junction on Windows (no admin rights needed), a symlink elsewhere. Never
    replaces what is already there unless it is this very link."""
    mods.mkdir(parents=True, exist_ok=True)
    path = mods / NAME
    if os.path.lexists(path):
        current = link_target(path)
        if current is None:
            raise SystemExit(f"{path} уже існує, і це звичайна тека, а не посилання (мабуть, стара копія мода).\n"
                             f"Приберіть її і запустіть встановлення ще раз.")
        if same_folder(path, target):
            print(f"Мод уже підключено: {path}")
            return path
        raise SystemExit(f"{path} веде в іншу теку ({current}).\n"
                         f"Приберіть це посилання: py tools/qud.py install --remove")
    if sys.platform == "win32":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(path), str(target)], check=True, capture_output=True)
    else:
        os.symlink(target, path, target_is_directory=True)
    print(f"Мод підключено: {path} → {target}")
    return path


def unlink(mods: pathlib.Path) -> None:
    """Remove the link mods/CavesOfQudUA, never a real folder and never what the link points to."""
    path = mods / NAME
    if not os.path.lexists(path):
        print(f"Мод не підключено: {path} немає.")
        return
    if link_target(path) is None:
        raise SystemExit(f"{path} — звичайна тека, а не посилання: не чіпаю її. Приберіть її вручну, якщо треба.")
    if sys.platform == "win32":
        os.rmdir(path)   # removes the junction itself; the folder it points to stays
    else:
        os.unlink(path)
    print(f"Мод відключено: посилання {path} прибрано.")


def translated_build(store: pathlib.Path) -> str | None:
    """The game build the translation was made against (the header of the store's files)."""
    for path in sorted(store.glob("*.jsonl")):
        with path.open(encoding="utf-8") as f:
            header = json.loads(f.readline() or "{}")
        if header.get("build"):
            return header["build"]
    return None


def run(game_dir: str | None = None, mods_dir: str | None = None, remove: bool = False,
        with_code: bool = True) -> int:
    mods = pathlib.Path(mods_dir) if mods_dir else game.mods_dir()
    if remove:
        unlink(mods)
        return 0
    install = pathlib.Path(game_dir) if game_dir else game.find_game()
    if install is None:
        raise SystemExit("Не знайшов Caves of Qud у бібліотеках Steam. Вкажіть теку гри:\n"
                         "  py tools/qud.py install --game \"<шлях>/steamapps/common/Caves of Qud\"")
    data = game.data_dir(install)
    if data is None:
        raise SystemExit(f"У {install} немає даних гри (CoQ_Data чи CoQ.app). Вкажіть теку гри через --game.")
    example = data / "StreamingAssets" / "Base" / "ExampleLanguage"
    if not example.is_dir():
        raise SystemExit("У грі немає таблиць рядків для перекладу. Перемкніть її на бета-гілку lang-experimental\n"
                         "(Steam → Caves of Qud → Властивості → Бета-версії) і дочекайтеся оновлення.")
    print(f"Гра: {install}")
    build = next((b for p in sorted(example.glob("*.example.xml"))
                  for b in [units.game_build(p.read_text(encoding="utf-8-sig"))] if b), None)
    ours = translated_build(sources.REPO / "translations" / "uk")
    if build and ours and build != ours:
        print(f"Увага: переклад зроблено для збірки {ours}, а у вас {build}. Нові й змінені рядки гри лишаться "
              f"англійськими, доки переклад не оновиться.")
    if with_code and build and decompile(data, build) is None:
        print("Не знайшов ilspycmd, тож текст, який пише сам код гри (ефекти, розповідь про дії, спливні "
              "вікна), лишиться англійським. Щоб перекласти і його, " + ILSPY_HINT + ".")
    files, _ = sources.load(str(example), None)   # with the code tables when the game's code is decompiled
    base = example.parent
    mutations = base / "Mutations.xml"
    creatures = base / "ObjectBlueprints" / "Creatures.xml"
    problems = commands.cmd_build(files,
                                  mutations_xml=mutations.read_text(encoding="utf-8-sig") if mutations.exists() else None,
                                  creatures_xml=creatures.read_text(encoding="utf-8-sig") if creatures.exists() else None)
    if problems:
        raise SystemExit("Збирання мода не вдалося (див. вище).")
    link(sources.REPO / "mod", mods)
    print("\nГотово. Далі в грі:\n"
          "  1. Запустіть Caves of Qud і дозвольте моди зі скриптами: гра спитає сама, або\n"
          "     Options → Mods → Allow scripting mods. Без цього гра вимикає мод цілком.\n"
          "  2. На титульному екрані внизу ліворуч виберіть мову «Українська». Гра перезапуститься.\n"
          "  3. Почніть нову гру: старі збереження лишаються з текстом, з яким їх створено.")
    return 0
