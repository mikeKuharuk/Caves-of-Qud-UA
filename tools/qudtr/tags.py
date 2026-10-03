"""Blueprint text the game shows but leaves out of its string tables: some tags and some part fields.

The string tables carry only the tags listed in ObjectBlueprintLoader.TagNode.displayTags and the part fields marked
[DisplayText]. A few others are text the player reads. This module turns them into one more string table of the
usual shape, Tags.example.xml, built from the game's Base/ObjectBlueprints whenever the commands load their sources
(sources.load). From there they are translated, stored and built like any other catalog: the build writes
Tags.uk.xml, a language file that merges them back (a blueprint merge sets each attribute it names).
"""
from __future__ import annotations

import re

from .units import MARK

NAME = "Tags.example.xml"

# tag → where the game shows it (decompiled 2.0.212.31). A tag the code also reads as a key (Species, Class,
# TinkerCategory, Gender) must not come here: a translation would break the lookup. Nor may text the code glues into
# an English sentence (HologramOf: «An image of X appears.»), which would come out half English.
TAGS = {
    "TitleIfNamed": "the title a creature takes when the player names it (GameObject)",
    "TurretName": "the turret a tinker builds around the weapon (IntegratedWeaponHosts.GetTurretNameFromWeapon)",
    "NoTeleport": "the popup when a teleport into the cell is refused (Physics)",
    "OverlandBlockMessage": "the message when the world map refuses travel (Physics)",
    "PartDescription": "the description of the body part that wings take (Wings)",
    "BodyDisplayName": "the body shown in character creation, «Humanoid» (QudBuildSummaryModule)",
    "CustomDeathMessage": "a creature's own death message, through VariableReplace (GameObject.Die)",
}

# part → its fields without [DisplayText] that the game shows as they are. Left out: verbs and prepositions, which the
# code conjugates with English grammar (DidX), and fragments it glues into an English sentence (Impaler's damage
# message «from %t shrapnel.», FusionReactor's death reason) — those wait for the code patches.
PART_FIELDS = {
    "Nest": ("SpawnMessage", "CollapseMessage"),
    "SlowDangerousMovement": ("PrepMessageSelf", "PrepMessageOther"),
    "NephalProperties": ("PhaseMessage",),
    "TemperatureAdjuster": ("BehaviorDescription",),
    "SapChargeOnHit": ("BehaviorDescription",),
    "FollowersGetTeleport": ("BehaviorDescription",),
    "Enclosing": ("EffectDescriptionPostfix",),
    "FallsApart": ("Message",),
    "SplitOnDeath": ("Message",),
    "Impaler": ("Message",),
    "SpawnVessel": ("SpawnMessage",),
    "Interesting": ("DisplayName", "Explanation"),
    "HiddenRender": ("DisplayName",),
    "ForceProjector": ("PickerLabel",),
}

OBJECT = re.compile(r'<object\s+Name="([^"]+)"')
TAG = re.compile(r'<tag\s+Name="([^"]+)"\s+Value="([^"]*)"')
PART = re.compile(r'<part\s+Name="([^"]+)"([^>]*)>')
ATTR = re.compile(r'(\w+)="([^"]*)"')


def example_xml(blueprints: dict[str, str], build: str | None) -> str | None:
    """The string table for TAGS and PART_FIELDS in the given blueprint files (file name → XML text), or None when
    they have none. Names and values are copied as the raw attribute text, so they stay escaped as they were."""
    found: dict[str, list[str]] = {}
    for _, text in sorted(blueprints.items()):
        current = None
        for line in text.splitlines():
            m = OBJECT.search(line)
            if m:
                current = m.group(1)
            if not current:
                continue
            for tag, value in TAG.findall(line):
                if tag in TAGS and value.strip():
                    found.setdefault(current, []).append(f'<tag Name="{tag}" Value="{MARK}{value}" />')
            for part, attrs in PART.findall(line):
                fields = [(a, v) for a, v in ATTR.findall(attrs) if a in PART_FIELDS.get(part, ()) and v.strip()]
                if fields:
                    marked = " ".join(f'{a}="{MARK}{v}"' for a, v in fields)
                    found.setdefault(current, []).append(f'<part Name="{part}" {marked} />')
    if not found:
        return None
    body = "".join(f'  <object Name="{name}" Load="Merge">\n'
                   + "".join(f"    {line}\n" for line in lines)
                   + "  </object>\n" for name, lines in found.items())
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!--\n'
            f"Caves of Qud - Generated Localizable XML {build or 'unknown'}\n"
            "Not from the game: tools/qudtr/tags.py builds it from Base/ObjectBlueprints.\n\n"
            '<objects>\n\n  <object Name="Key" Load="">\n\n    <part Name="Key">\n\n'
            '    <tag Name="Key" Value="DisplayText">\n\n-->\n'
            f'<objects Lang="example" Encoding="utf-8">\n{body}</objects>\n')
