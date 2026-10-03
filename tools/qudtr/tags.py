"""Blueprint tags whose text the game shows but leaves out of its string tables.

The string tables carry only the tags listed in ObjectBlueprintLoader.TagNode.displayTags. A few others are text the
player reads. This module turns them into one more string table of the usual shape, Tags.example.xml, built from the
game's Base/ObjectBlueprints whenever the commands load their sources (sources.load). From there they are translated,
stored and built like any other catalog: the build writes Tags.uk.xml, a language file that merges the tags back.
"""
from __future__ import annotations

import re

from .units import MARK

NAME = "Tags.example.xml"

# tag → where the game shows it (decompiled 2.0.212.31). A tag the code also reads as a key (Species, Class,
# TinkerCategory, Gender) must not come here: a translation would break the lookup.
TAGS = {
    "TitleIfNamed": "the title a creature takes when the player names it (GameObject)",
    "TurretName": "the turret a tinker builds around the weapon (IntegratedWeaponHosts.GetTurretNameFromWeapon)",
    "NoTeleport": "the popup when a teleport into the cell is refused (Physics)",
    "OverlandBlockMessage": "the message when the world map refuses travel (Physics)",
    "PartDescription": "the description of the body part that wings take (Wings)",
}

OBJECT = re.compile(r'<object\s+Name="([^"]+)"')
TAG = re.compile(r'<tag\s+Name="([^"]+)"\s+Value="([^"]*)"')


def example_xml(blueprints: dict[str, str], build: str | None) -> str | None:
    """The string table for TAGS in the given blueprint files (file name → XML text), or None when they have none.
    Names and values are copied as the raw attribute text, so they stay escaped as they were."""
    found: dict[str, list[tuple[str, str]]] = {}
    for _, text in sorted(blueprints.items()):
        current = None
        for line in text.splitlines():
            m = OBJECT.search(line)
            if m:
                current = m.group(1)
            for tag, value in TAG.findall(line):
                if tag in TAGS and current and value.strip():
                    found.setdefault(current, []).append((tag, value))
    if not found:
        return None
    body = "".join(f'  <object Name="{name}" Load="Merge">\n'
                   + "".join(f'    <tag Name="{tag}" Value="{MARK}{value}" />\n' for tag, value in tags)
                   + "  </object>\n" for name, tags in found.items())
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!--\n'
            f"Caves of Qud - Generated Localizable XML {build or 'unknown'}\n"
            "Not from the game: tools/qudtr/tags.py builds it from Base/ObjectBlueprints.\n\n"
            '<objects>\n\n  <object Name="Key" Load="">\n\n    <tag Name="Key" Value="DisplayText">\n\n-->\n'
            f'<objects Lang="example" Encoding="utf-8">\n{body}</objects>\n')
