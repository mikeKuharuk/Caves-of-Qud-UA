import pathlib
import sys
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import units  # noqa: E402

M = units.MARK

OBJECTS = f"""<?xml version="1.0" encoding="utf-8"?>
<!--
Caves of Qud - Generated Localizable XML 2.0.212.31
-->
<objects Lang="example" Encoding="utf-8">
  <object Name="Ctesiphus" Load="Merge">
    <part Name="Render" DisplayName="{M}Ctesiphus" />
    <part Name="Description" Short="{M}A ray cat. =pronouns.Subjective= purrs." />
    <xtagGrammar Proper="{M}true" adjunctNoun="{M}pair" />
    <tag Name="SimpleConversation" Value="{M}Meow.~{M}Mrrp." />
    <tag Name="StaticHateReason" Value="Joppa,friend,{M}defending their village" />
  </object>
  <object Name="Untouched" Load="Merge">
    <part Name="Render" DisplayName="{M}thing" />
  </object>
</objects>
"""

STRINGS = f"""<?xml version="1.0" encoding="utf-8"?>
<strings Lang="example" Encoding="utf-8">
  <string Context="MainMenu Main" ID="New Game">{M}New Game</string>
  <string Context="Joiner" ID=" or " Value="{M} or " />
  <string ID="No context">{M}No context</string>
  <string Context="Conversation A.B.Text" ID="Line one&#xA;&#xA;Line two">
{M}Line one

    Line two
  </string>
</strings>
"""

HELP = f"""<?xml version="1.0" encoding="utf-8"?>
<help Lang="example" Encoding="utf-8">
  <topic name="Quickstart" DisplayName="{M}Quickstart">{M}
These are nine things.
    Indented line.
</topic>
  <book ID="B"><page>{M}p1</page><page>{M}p2</page></book>
</help>
"""


def by_key(us):
    return {u.key: u for u in us}


class Extract(unittest.TestCase):
    def test_objects(self):
        us = by_key(units.extract(OBJECTS, "Creatures.example.xml"))
        self.assertIn(("object[Ctesiphus]/part[Render]@DisplayName", "Ctesiphus"), us)
        self.assertIn(("object[Ctesiphus]/part[Description]@Short",
                       "A ray cat. =pronouns.Subjective= purrs."), us)
        # grammar switches are keys, never units; adjunctNoun is real text
        self.assertFalse(any(k[0].endswith("@Proper") for k in us))
        self.assertIn(("object[Ctesiphus]/xtagGrammar@adjunctNoun", "pair"), us)
        # compound values keep their markers
        alt = us[("object[Ctesiphus]/tag[SimpleConversation]@Value", f"{M}Meow.~{M}Mrrp.")]
        self.assertTrue(alt.compound)
        keyed = us[("object[Ctesiphus]/tag[StaticHateReason]@Value", f"Joppa,friend,{M}defending their village")]
        self.assertTrue(keyed.compound)

    def test_strings(self):
        us = units.extract(STRINGS, "Strings.example.xml")
        keys = [u.key for u in us]
        self.assertEqual(keys, [("MainMenu Main", "New Game"), ("Joiner", " or "), (None, "No context"),
                                ("Conversation A.B.Text", "Line one\n\nLine two")])
        self.assertTrue(all(u.kind == "string" for u in us))

    def test_text_units_are_unindented_like_the_game(self):
        us = units.extract(HELP, "Manual.example.xml")
        keys = [u.key for u in us]
        self.assertIn(("topic[name=Quickstart]", "These are nine things.\nIndented line."), keys)
        self.assertIn(("topic[name=Quickstart]@DisplayName", "Quickstart"), keys)
        # siblings without identity get an ordinal from the second one on
        self.assertIn(("book[ID=B]/page", "p1"), keys)
        self.assertIn(("book[ID=B]/page#2", "p2"), keys)

    def test_game_build(self):
        self.assertEqual(units.game_build(OBJECTS), "2.0.212.31")

    def test_unindent_matches_game_test_case(self):
        # GameTextTest: "\n     a \n     ab\n     a \n     ab\n    ".Unindent() == "a \nab\na \nab"
        self.assertEqual(units.unindent("\n     a \n     ab\n     a \n     ab\n    "), "a \nab\na \nab")


class Build(unittest.TestCase):
    def test_nothing_translated_writes_nothing(self):
        xml, n = units.build(OBJECTS, "Creatures.example.xml", {})
        self.assertIsNone(xml)
        self.assertEqual(n, 0)

    def test_objects_partial(self):
        tr = {
            ("object[Ctesiphus]/part[Render]@DisplayName", "Ctesiphus"): "Ктесіф",
            ("object[Ctesiphus]/tag[SimpleConversation]@Value", f"{M}Meow.~{M}Mrrp."): f"{M}Няв.~{M}Мрр.",
        }
        xml, n = units.build(OBJECTS, "Creatures.example.xml", tr)
        self.assertEqual(n, 2)
        root = ET.fromstring(xml)
        self.assertEqual(root.get("Lang"), "uk")
        self.assertEqual(root.get("Encoding"), "utf-8")
        objs = root.findall("object")
        self.assertEqual([o.get("Name") for o in objs], ["Ctesiphus"])       # untouched object pruned
        self.assertEqual(objs[0].get("Load"), "Merge")
        parts = {p.get("Name"): p for p in objs[0].findall("part")}
        self.assertEqual(parts["Render"].get("DisplayName"), "Ктесіф")
        self.assertNotIn("Description", parts)                                # untranslated: left out
        tag = objs[0].find("tag[@Name='SimpleConversation']")
        self.assertEqual(tag.get("Value"), "Няв.~Мрр.")                        # markers stripped
        self.assertIsNone(objs[0].find("xtagGrammar"))                         # nothing translated there
        self.assertIn(units.GENERATED_MARKER, xml)

    def test_strings_use_value_attribute_and_keep_whitespace(self):
        tr = {("Joiner", " or "): " або ", ("Conversation A.B.Text", "Line one\n\nLine two"): "Рядок один\n\nРядок два"}
        xml, n = units.build(STRINGS, "Strings.example.xml", tr)
        self.assertEqual(n, 2)
        root = ET.fromstring(xml)
        s = {(e.get("Context"), e.get("ID")): e.get("Value") for e in root.findall("string")}
        self.assertEqual(s[("Joiner", " or ")], " або ")
        self.assertEqual(s[("Conversation A.B.Text", "Line one\n\nLine two")], "Рядок один\n\nРядок два")
        self.assertEqual(len(s), 2)

    def test_text_units_and_complete_entries(self):
        tr = {("topic[name=Quickstart]", "These are nine things.\nIndented line."): "Ось дев’ять речей.\nРядок.",
              ("book[ID=B]/page#2", "p2"): "с2"}
        xml, n = units.build(HELP, "Manual.example.xml", tr)
        self.assertEqual(n, 2)
        root = ET.fromstring(xml)
        topic = root.find("topic")
        self.assertEqual(topic.get("name"), "Quickstart")
        # not an `objects` file: the entry is written complete, English where untranslated
        self.assertEqual(topic.get("DisplayName"), "Quickstart")
        self.assertEqual(topic.text, "Ось дев’ять речей.\nРядок.")
        # a book redefinition replaces all pages, so every page is written, in order
        pages = root.find("book").findall("page")
        self.assertEqual([p.text for p in pages], ["p1", "с2"])

    def test_positional_siblings_are_all_or_nothing_in_sparse_files(self):
        xml_src = f"""<objects Lang="example" Encoding="utf-8">
  <object Name="X" Load="Merge">
    <part Name="A" Short="{M}untouched" />
    <builder Name="B"><page>{M}one</page><page>{M}two</page><page>{M}three</page></builder>
  </object>
</objects>"""
        xml, _ = units.build(xml_src, "Items.example.xml", {("object[X]/builder[B]/page#3", "three"): "три"})
        root = ET.fromstring(xml)
        self.assertEqual([p.text for p in root.find("object/builder").findall("page")], ["one", "two", "три"])
        self.assertIsNone(root.find("object/part"))   # sparse: untranslated parts stay out

    def test_schema_keys_come_from_the_header(self):
        src = f"""<?xml version="1.0" encoding="utf-8"?>
<!--
<naming>
  <namestyles HyphenSeparator="DisplayText">
    <namestyle Name="Key" Format="" Load="">
      <prefixes Load="" Amount="">
        <prefix Name="DisplayText" Weight="">
-->
<naming Lang="example" Encoding="utf-8">
  <namestyles HyphenSeparator="{M}-">
    <namestyle Name="Qudish" Load="Merge">
      <prefixes Load="Replace" Amount="1">
        <prefix Name="" />
        <prefix Name="{M}fa" />
        <prefix Name="{M}ha" />
      </prefixes>
    </namestyle>
  </namestyles>
</naming>"""
        keys = [u.key for u in units.extract(src, "Naming.example.xml")]
        # Name is display text for <prefix>, never a key: the empty prefix is a positional sibling
        self.assertIn(("namestyles/namestyle[Qudish]/prefixes/prefix#2@Name", "fa"), keys)
        self.assertIn(("namestyles/namestyle[Qudish]/prefixes/prefix#3@Name", "ha"), keys)
        xml, _ = units.build(src, "Naming.example.xml", {("namestyles/namestyle[Qudish]/prefixes/prefix#3@Name", "ha"): "ха"})
        names = [p.get("Name") for p in ET.fromstring(xml).iter("prefix")]
        self.assertEqual(names, ["", "fa", "ха"])

    def test_escaping(self):
        tr = {("object[Ctesiphus]/part[Render]@DisplayName", "Ctesiphus"): 'A & B <"c">\nd'}
        xml, _ = units.build(OBJECTS, "Creatures.example.xml", tr)
        part = ET.fromstring(xml).find("object/part")
        self.assertEqual(part.get("DisplayName"), 'A & B <"c">\nd')


if __name__ == "__main__":
    unittest.main()
