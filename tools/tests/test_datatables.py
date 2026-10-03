"""Tables built from game data the string tables leave out: key bindings, colours, factions, code tables."""
import pathlib
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import checks, codetables, datatables, units  # noqa: E402

COMMANDS = """<commands Encoding="utf-8">
  <navcategory ID="Adventure" />
  <command ID="CmdMoveN" DisplayText="Move north" Category="Basic Move" Layer="AdventureNav">
    <keyboardBind Key="UpArrow" />
  </command>
  <command ID="UI:Navigate/up" DisplayText="Navigate up" Category="Menus" UpgradeFrom="CmdMoveN" />
  <command ID="GamepadAlt" DisplayText="Gamepad Alt" ConsoleDisplayText="Modifier Button" />
</commands>"""

COLORS = """<colors Encoding="utf-8">
  <solidcolors>
    <solidcolor Name="dark blue" Color="b" ShowInPicker="true" />
    <solidcolor Name="hidden" Color="k" />
  </solidcolors>
  <shaders>
    <shader Name="amorous" Type="alternation" Colors="r-R-M-m" ShowInPicker="true" />
  </shaders>
</colors>"""


class Commands(unittest.TestCase):
    def test_names_are_units_and_upgrade_from_is_restated(self):
        xml = datatables.commands_xml(COMMANDS, "2.0.212.31")
        found = {(u.msgctxt, u.msgid) for u in units.extract(xml, datatables.COMMANDS)}
        self.assertIn(("command[ID=CmdMoveN]@DisplayText", "Move north"), found)
        self.assertIn(("command[ID=GamepadAlt]@ConsoleDisplayText", "Modifier Button"), found)
        out, _ = units.build(xml, datatables.COMMANDS, {("command[ID=UI:Navigate/up]@DisplayText", "Navigate up"): "Угору"})
        cmd = next(c for c in ET.fromstring(out).iter("command") if c.get("ID") == "UI:Navigate/up")
        # the loader resets UpgradeFrom to the ID when it is absent
        self.assertEqual((cmd.get("DisplayText"), cmd.get("UpgradeFrom")), ("Угору", "CmdMoveN"))


class Colors(unittest.TestCase):
    def test_picker_names_are_units_and_shaders_keep_their_colors(self):
        xml = datatables.colors_xml(COLORS, None)
        found = {(u.msgctxt, u.msgid) for u in units.extract(xml, datatables.COLORS)}
        self.assertEqual(found, {("solidcolors/solidcolor[dark blue]@DisplayName", "dark blue"),
                                 ("shaders/shader[amorous]@DisplayName", "amorous")})
        out, _ = units.build(xml, datatables.COLORS, {("shaders/shader[amorous]@DisplayName", "amorous"): "закоханий"})
        shader = next(ET.fromstring(out).iter("shader"))
        self.assertEqual((shader.get("DisplayName"), shader.get("Colors")), ("закоханий", "r-R-M-m"))


class Factions(unittest.TestCase):
    EXAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<!--
Caves of Qud - Generated Localizable XML 2.0.212.31

<factions>

  <faction Name="Key" DisplayName="DisplayText">

-->
<factions Lang="example" Encoding="utf-8">
  <faction Name="Mopango" DisplayName="▶mopango" />
</factions>"""
    BASE = """<factions>
  <faction Name="Mopango" Parent="Grazers" DefaultAddress="climber">
    <waterritual Liquid="water" RecipeText="Would you share the dish?" />
  </faction>
</factions>"""

    def test_missing_attributes_become_units_and_parent_is_restated(self):
        xml = datatables.augment_factions(self.EXAMPLE, self.BASE)
        found = {(u.msgctxt, u.msgid) for u in units.extract(xml, "Factions.example.xml")}
        self.assertIn(("faction[Mopango]@DefaultAddress", "climber"), found)
        self.assertIn(("faction[Mopango]/waterritual@RecipeText", "Would you share the dish?"), found)
        out, _ = units.build(xml, "Factions.example.xml", {("faction[Mopango]@DisplayName", "mopango"): "мопанго"})
        faction = ET.fromstring(out).find("faction")
        # the loader sets Parent to null when a merge does not name it
        self.assertEqual(faction.get("Parent"), "Grazers")


class CodeTables(unittest.TestCase):
    def test_species_from_tags_and_genotypes(self):
        blueprints = {"Creatures.xml": '<object Name="Bear"><tag Name="Species" Value="bear" /></object>'
                                       '<object Name="Any"><tag Name="Species" Value="*" /></object>'}
        xml = codetables.species_xml(blueprints, '<genotypes><genotype Name="True Kin" Species="human" /></genotypes>', None)
        self.assertEqual(codetables.entries(xml), ["bear", "human"])
        self.assertEqual([u.msgctxt for u in units.extract(xml, codetables.SPECIES)],
                         ["entry[Key=bear]@Text", "entry[Key=human]@Text"])

    def test_the_tables_become_csharp(self):
        cs = codetables.code_tables_cs({"Species": {"human": "людина"}, "Species.voc": {"human": "людино"}})
        self.assertIn('t["Species"] = new Dictionary<string, string>', cs)
        self.assertIn('["human"] = "людино",', cs)

    def test_the_vocative_parameter_passes_the_checks(self):
        self.assertEqual(checks.check("Welcome, =player.species=.", "Вітаємо, =player.species:voc=."), [])


if __name__ == "__main__":
    unittest.main()
