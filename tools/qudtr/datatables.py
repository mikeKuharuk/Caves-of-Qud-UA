"""Game data with player-visible text that the official string tables leave out, turned into string tables of the
usual shape (docs/research/localization-gaps.md, §1). sources.load builds them from the game's Base folder; from there
they are translated, stored and built like any other catalog, and the build writes language files that the game's
loaders merge into the data.

  Commands.example.xml   key binding names (Commands.xml has no export). The merge must restate UpgradeFrom: the
                         loader resets it to the ID when it is absent (CommandBindingManager.HandleCommandNode).
  Colors.example.xml     colour names in the colour picker; they default to the key. A shader merge must restate
                         Colors, or the loader throws (MarkupShaders.HandleShaderNode).
  augment_factions       adds to the official Factions table what its export misses: the water ritual's dish
                         question (exported as «recipetext», read as «RecipeText»), the interests' BuyDescription and
                         the DefaultAddress; and restates Parent, which the faction loader resets when absent.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from .units import MARK

COMMANDS = "Commands.example.xml"
COLORS = "Colors.example.xml"


def _header(build: str | None, schema: str) -> str:
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!--\n'
            f"Caves of Qud - Generated Localizable XML {build or 'unknown'}\n"
            "Not from the game: tools/qudtr/datatables.py builds it from the Base folder.\n\n"
            f"{schema}\n-->\n")


def _attr(name: str, value: str) -> str:
    return f'{name}="{value.replace("&", "&amp;").replace(chr(34), "&quot;").replace("<", "&lt;")}"'


def commands_xml(base_text: str, build: str | None) -> str | None:
    """The command names of Base/Commands.xml as a string table."""
    lines = []
    for c in ET.fromstring(base_text).iter("command"):
        if not c.get("ID") or not (c.get("DisplayText") or "").strip():
            continue
        attrs = [_attr("ID", c.get("ID")), _attr("DisplayText", MARK + c.get("DisplayText"))]
        if (c.get("ConsoleDisplayText") or "").strip():
            attrs.append(_attr("ConsoleDisplayText", MARK + c.get("ConsoleDisplayText")))
        if c.get("UpgradeFrom"):
            attrs.append(_attr("UpgradeFrom", c.get("UpgradeFrom")))
        lines.append(f"  <command {' '.join(attrs)} />\n")
    if not lines:
        return None
    return (_header(build, '<commands>\n\n  <command ID="Key" DisplayText="DisplayText">\n')
            + f'<commands Lang="example" Encoding="utf-8">\n{"".join(lines)}</commands>\n')


def colors_xml(base_text: str, build: str | None) -> str | None:
    """The names of the colours and shaders the colour picker shows, as a string table. The English name is the
    DisplayName if there is one, else the key."""
    root = ET.fromstring(base_text)
    sections = []
    for section, tag in (("solidcolors", "solidcolor"), ("shaders", "shader")):
        lines = []
        for el in root.iter(tag):
            shown = (el.get("ShowInPicker") or "").lower() == "true" or el.get("DisplayName")
            if not el.get("Name") or not shown:
                continue
            attrs = [_attr("Name", el.get("Name")), _attr("DisplayName", MARK + (el.get("DisplayName") or el.get("Name")))]
            if tag == "shader":
                attrs.append(_attr("Colors", el.get("Colors") or ""))
            lines.append(f"    <{tag} {' '.join(attrs)} />\n")
        if lines:
            sections.append(f"  <{section}>\n{''.join(lines)}  </{section}>\n")
    if not sections:
        return None
    return (_header(build, '<colors>\n\n  <solidcolors>\n\n    <solidcolor Name="Key" DisplayName="DisplayText">\n\n'
                           '  <shaders>\n\n    <shader Name="Key" DisplayName="DisplayText">\n')
            + f'<colors Lang="example" Encoding="utf-8">\n{"".join(sections)}</colors>\n')


def augment_factions(example_text: str, base_text: str) -> str:
    """The official Factions table with what its export misses (module docstring). The header comment, which holds
    the schema, is kept as it is."""
    info = {}
    for f in ET.fromstring(base_text).findall("faction"):
        ritual, interests = f.find("waterritual"), f.find("interests")
        info[f.get("Name")] = {
            "Parent": f.get("Parent"),
            "DefaultAddress": f.get("DefaultAddress"),
            "RecipeText": ritual.get("RecipeText") if ritual is not None else None,
            "BuyDescription": interests.get("BuyDescription") if interests is not None else None,
        }
    start = example_text.index("<factions ")
    root = ET.fromstring(example_text[start:])
    for f in root.findall("faction"):
        d = info.get(f.get("Name"))
        if not d:
            continue
        if d["Parent"] and "Parent" not in f.attrib:
            f.set("Parent", d["Parent"])
        if d["DefaultAddress"] and "DefaultAddress" not in f.attrib:
            f.set("DefaultAddress", MARK + d["DefaultAddress"])
        for child, attr in (("waterritual", "RecipeText"), ("interests", "BuyDescription")):
            if not d[attr]:
                continue
            el = f.find(child)
            if el is None:
                el = ET.SubElement(f, child)
            if attr not in el.attrib:
                el.set(attr, MARK + d[attr])
    return example_text[:start] + ET.tostring(root, encoding="unicode") + "\n"
