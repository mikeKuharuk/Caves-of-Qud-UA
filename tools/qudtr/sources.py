"""Where the ExampleLanguage files come from: the installed game, a folder, or a mirror tag."""
from __future__ import annotations

import os
import pathlib
import subprocess

from . import codetables, datatables, tags, units

REPO = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_GAME_DIR = pathlib.Path(os.environ.get("QUD_GAME_DIR", r"D:\Steam\steamapps\common\Caves of Qud"))
GAME_EXAMPLE_DIR = DEFAULT_GAME_DIR / "CoQ_Data" / "StreamingAssets" / "Base" / "ExampleLanguage"
MIRROR = REPO / "work" / "example-language"


def from_dir(path: pathlib.Path) -> dict[str, str]:
    files = {p.name: p.read_text(encoding="utf-8-sig") for p in sorted(path.glob("*.example.xml"))}
    if not files:
        raise SystemExit(f"no *.example.xml files in {path}")
    return files


def from_tag(tag: str, mirror: pathlib.Path = MIRROR) -> dict[str, str]:
    names = subprocess.run(["git", "-C", str(mirror), "ls-tree", "--name-only", f"{tag}:ExampleLanguage"],
                           capture_output=True, text=True, check=True).stdout.split()
    out = {}
    for n in names:
        if n.endswith(".example.xml"):
            blob = subprocess.run(["git", "-C", str(mirror), "show", f"{tag}:ExampleLanguage/{n}"],
                                  capture_output=True, check=True).stdout
            out[n] = blob.decode("utf-8-sig")
    return out


def base_text(source: str | None, tag: str | None, name: str) -> str | None:
    """A game data file next to ExampleLanguage in the Base folder (Mutations.xml), or None when the source has
    none (a mirror tag holds only ExampleLanguage)."""
    if tag:
        return None
    path = (pathlib.Path(source) if source else GAME_EXAMPLE_DIR).parent / name
    return path.read_text(encoding="utf-8-sig") if path.exists() else None


def load(source: str | None, tag: str | None) -> tuple[dict[str, str], str]:
    """Return ({file name: xml text}, human-readable description of the source)."""
    if tag:
        return from_tag(tag), f"mirror tag {tag}"
    path = pathlib.Path(source) if source else GAME_EXAMPLE_DIR
    files = from_dir(path)
    build = next((b for b in map(units.game_build, files.values()) if b), None)
    # HistorySpice has no example file; it lives next to ExampleLanguage in the game's Base folder
    spice = path.parent / "HistorySpice.jsonc"
    if spice.exists():
        files[spice.name] = spice.read_text(encoding="utf-8-sig")
    # nor do the tags and part fields the game shows without exporting them (tags.py); they come from the blueprints
    blueprints = path.parent / "ObjectBlueprints"
    if blueprints.is_dir():
        texts = {p.name: p.read_text(encoding="utf-8-sig") for p in sorted(blueprints.glob("*.xml"))}
        table = tags.example_xml(texts, build)
        if table:
            files[tags.NAME] = table
        # and the words our C# looks up (codetables.py): species
        genotypes = path.parent / "Genotypes.xml"
        table = codetables.species_xml(texts, genotypes.read_text(encoding="utf-8-sig") if genotypes.exists() else None,
                                       build)
        if table:
            files[codetables.SPECIES] = table
    # and the English the game's C# writes itself, from the decompiled code of this very build (ilspycmd, work/)
    decompiled = REPO / "work" / "decompiled" / str(build) / "Assembly-CSharp"
    if decompiled.is_dir():
        table = codetables.effects_xml(decompiled, build)
        if table:
            files[codetables.EFFECTS] = table
    # nor the data files with no export at all, and what the Factions export misses (datatables.py)
    for name, make in ((datatables.COMMANDS, datatables.commands_xml), (datatables.COLORS, datatables.colors_xml)):
        base = path.parent / name.replace(".example.xml", ".xml")
        if base.exists():
            table = make(base.read_text(encoding="utf-8-sig"), build)
            if table:
                files[name] = table
    factions = path.parent / "Factions.xml"
    if "Factions.example.xml" in files and factions.exists():
        files["Factions.example.xml"] = datatables.augment_factions(files["Factions.example.xml"],
                                                                    factions.read_text(encoding="utf-8-sig"))
    return files, str(path)
