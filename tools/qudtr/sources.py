"""Where the ExampleLanguage files come from: the installed game, a folder, or a mirror tag."""
from __future__ import annotations

import os
import pathlib
import subprocess

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


def load(source: str | None, tag: str | None) -> tuple[dict[str, str], str]:
    """Return ({file name: xml text}, human-readable description of the source)."""
    if tag:
        return from_tag(tag), f"mirror tag {tag}"
    path = pathlib.Path(source) if source else GAME_EXAMPLE_DIR
    return from_dir(path), str(path)
