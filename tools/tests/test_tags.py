"""Tags.example.xml: the tags the game shows but leaves out of its string tables, as one more string table."""
import pathlib
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import sources, tags, units  # noqa: E402

BLUEPRINTS = """<?xml version="1.0" encoding="utf-8"?>
<objects>
  <object Name="Gun" Inherits="BaseGun">
    <part Name="Render" DisplayName="gun" />
    <tag Name="TurretName" Value="gun &amp; turret" />
    <tag Name="Species" Value="robot thing" />
  </object>
  <object Name="Rock">
    <tag Name="Species" Value="mineral thing" />
  </object>
</objects>"""


class Tags(unittest.TestCase):
    def test_only_the_shown_tags_become_units(self):
        xml = tags.example_xml({"Items.xml": BLUEPRINTS}, "2.0.212.31")
        self.assertEqual(units.game_build(xml), "2.0.212.31")
        found = [(u.msgctxt, u.msgid) for u in units.extract(xml, tags.NAME)]
        self.assertEqual(found, [("object[Gun]/tag[TurretName]@Value", "gun & turret")])

    def test_a_commented_out_blueprint_is_no_blueprint(self):
        # the game ships some blueprints commented out; merging with one is a MODERROR on every start
        commented = BLUEPRINTS.replace('  <object Name="Rock">', '  <!--<object Name="Oven">\n'
                                       '    <part Name="TemperatureAdjuster" BehaviorDescription="Heats." />\n'
                                       '  </object>-->\n  <object Name="Rock">')
        xml = tags.example_xml({"Items.xml": commented}, None)
        self.assertNotIn("Oven", xml)
        self.assertIn('Name="Gun"', xml)

    def test_every_merge_has_a_blueprint_in_the_game(self):
        if not sources.GAME_DATA_DIR.is_dir():
            self.skipTest("the game is not installed")
        texts = {p.name: p.read_text(encoding="utf-8-sig")
                 for p in sorted((sources.GAME_DATA_DIR / "StreamingAssets" / "Base" / "ObjectBlueprints").glob("*.xml"))}
        defined = {n for t in texts.values() for n in tags.OBJECT.findall(units.uncommented(t))}
        merged = {o.get("Name") for o in ET.fromstring(tags.example_xml(texts, None)).iter("object")} - {"Key"}
        self.assertEqual(merged - defined, set())

    def test_no_table_without_such_tags(self):
        self.assertIsNone(tags.example_xml({"Items.xml": BLUEPRINTS.replace("TurretName", "Species")}, None))

    def test_the_build_merges_the_translated_tag(self):
        xml = tags.example_xml({"Items.xml": BLUEPRINTS}, "2.0.212.31")
        out, count = units.build(xml, tags.NAME, {("object[Gun]/tag[TurretName]@Value", "gun & turret"): "турель"})
        self.assertEqual(count, 1)
        root = ET.fromstring(out)
        self.assertEqual(root.get("Lang"), "uk")
        obj = root.find("object")
        self.assertEqual((obj.get("Name"), obj.get("Load")), ("Gun", "Merge"))
        self.assertEqual((obj.find("tag").get("Name"), obj.find("tag").get("Value")), ("TurretName", "турель"))


if __name__ == "__main__":
    unittest.main()
