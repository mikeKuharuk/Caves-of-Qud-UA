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

    def test_true_is_a_syllable_in_the_name_generator(self):
        # "true"/"false" are booleans elsewhere (Proper="▶true" above), but a Templar Mecha name starts with "true"
        naming = (f'<?xml version="1.0" encoding="utf-8"?>\n<namestyles Lang="example" Encoding="utf-8">\n'
                  f'  <namestyle Name="Templar Mecha 1"><prefixes><prefix Name="{M}true" /><prefix Name="{M}ne" />'
                  f'</prefixes></namestyle>\n</namestyles>\n')
        us = [u.msgid for u in units.extract(naming, "Naming.example.xml")]
        self.assertIn("true", us)

    def test_tags_that_are_keys_are_not_units(self):
        # the English article logic reads IndefiniteArticle/DefiniteArticle; PronounSet names a set;
        # the code compares TinkerCategory and DisplayCharacter with English values it holds
        src = OBJECTS.replace('<xtagGrammar', f'<tag Name="IndefiniteArticle" Value="{M}a" />\n'
                              f'    <tag Name="PronounSet" Value="{M}she/her" />\n'
                              f'    <tag Name="TinkerCategory" Value="{M}utility" />\n'
                              f'    <tag Name="DisplayCharacter" Value="{M}A" />\n    <xtagGrammar')
        us = by_key(units.extract(src, "Creatures.example.xml"))
        self.assertFalse([k for k in us if k[0].split("/")[-1].startswith(
            ("tag[IndefiniteArticle]", "tag[PronounSet]", "tag[TinkerCategory]", "tag[DisplayCharacter]"))])
        xml, _ = units.build(src, "Creatures.example.xml",
                             {("object[Ctesiphus]/part[Render]@DisplayName", "Ctesiphus"): "Ктесіф"})
        # objects merge attribute by attribute, so the untouched tags stay the base game's
        names = {t.get("Name") for t in ET.fromstring(xml).iter("tag")}
        self.assertFalse(names & {"IndefiniteArticle", "PronounSet"})

    def test_tinker_category_of_a_mod_is_not_a_unit(self):
        src = (f'<mods>\n  <mod Part="ModSharp" TinkerCategory="{M}melee weapons" '
               f'TinkerDisplayName="{M}sharp" />\n</mods>')
        attrs = {k[0].rsplit("@", 1)[1] for k in by_key(units.extract(src, "Mods.example.xml"))}
        self.assertEqual(attrs, {"TinkerDisplayName"})

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


# <description>, <leveltext> and <template> are LanguageXml.TemplateElement: the whole inner XML
# is one translatable text, and the game replaces the template with the translated one
# (Templates.LoadTemplateFromExternal clears the old nodes).
MUTATIONS = f"""<?xml version="1.0" encoding="utf-8"?>
<!--
Caves of Qud - Generated Localizable XML 2.0.212.31

<mutations>
  <category Name="Key" DisplayName="DisplayText">
    <mutation Name="Key" DisplayName="DisplayText">
      <description>
      <leveltext>
-->
<mutations Lang="example" Encoding="utf-8">
  <category Name="Physical" DisplayName="{M}Physical">
    <mutation Name="Adrenal Control" DisplayName="{M}Adrenal Control">
      <description>{M}
                    <p>You regulate your body's release of adrenaline &amp; more.</p>
                </description>
      <leveltext>{M}
                    <p>You gain +<stat Name="QuicknessBonus" /> quickness and +<stat Name="MutationBonus" Unit="{M}rank" />.</p>
                    <br />
                    <statline Name="Cooldown" DisplayName="{M}Cooldown" />
                </leveltext>
    </mutation>
    <mutation Name="Clairvoyance" DisplayName="{M}Clairvoyance">
      <description>{M}You briefly gain vision of a nearby area.</description>
      <leveltext></leveltext>
    </mutation>
  </category>
</mutations>
"""
LEVELTEXT = ("category[Physical]/mutation[Adrenal Control]/leveltext",
             '<p>You gain +<stat Name="QuicknessBonus" /> quickness and +<stat Name="MutationBonus" Unit="rank" />.</p>\n'
             '<br />\n<statline Name="Cooldown" DisplayName="Cooldown" />')
LEVELTEXT_UK = ('<p>Ви отримуєте +<stat Name="QuicknessBonus" /> до швидкості й +<stat Name="MutationBonus" Unit="ранг" />.</p>\n'
                '<br />\n<statline Name="Cooldown" DisplayName="Перезаряджання" />')


class Templates(unittest.TestCase):
    def test_inner_xml_is_one_unit_without_markers(self):
        us = by_key(units.extract(MUTATIONS, "Mutations.example.xml"))
        self.assertEqual(us[LEVELTEXT].kind, "template")
        desc = ("category[Physical]/mutation[Adrenal Control]/description",
                "<p>You regulate your body's release of adrenaline &amp; more.</p>")
        self.assertEqual(us[desc].kind, "template")
        # nothing inside a template is a unit of its own
        self.assertFalse([k for k in us if "statline" in k[0] or "@Unit" in k[0]])
        # a template without child elements stays a plain text unit; an empty one is no unit
        plain = ("category[Physical]/mutation[Clairvoyance]/description", "You briefly gain vision of a nearby area.")
        self.assertEqual(us[plain].kind, "text")
        self.assertFalse([k for k in us if k[0].endswith("Clairvoyance]/leveltext")])

    def test_template_of_tags_alone_is_no_unit(self):
        src = (f'<templates>\n  <template ID="Effect.A.Details">{M}<saveline Name="DiseaseOnsetSave" '
               f'Type="Disease Onset" /></template>\n'
               f'  <template ID="Effect.B.Details">{M}<statline Name="Cooldown" DisplayName="{M}Cooldown" />'
               f'</template>\n</templates>')
        us = by_key(units.extract(src, "Templates.example.xml"))
        # a DisplayName is text to translate, a save type is a key
        self.assertEqual([k[0] for k in us], ["template[ID=Effect.B.Details]"])

    def test_build_writes_the_translated_markup(self):
        xml, count = units.build(MUTATIONS, "Mutations.example.xml", {LEVELTEXT: LEVELTEXT_UK})
        self.assertEqual(count, 1)
        mutation = ET.fromstring(xml).find("category/mutation")
        level = mutation.find("leveltext")
        self.assertEqual([c.tag for c in level], ["p", "br", "statline"])
        self.assertEqual(level.find("statline").get("DisplayName"), "Перезаряджання")
        self.assertEqual(level.find("p/stat[@Name='MutationBonus']").get("Unit"), "ранг")
        # the untranslated description of the same (complete) entry is restated in English
        self.assertEqual(mutation.find("description/p").text, "You regulate your body's release of adrenaline & more.")
        self.assertNotIn(M, xml)

    def test_import_reads_the_template_back(self):
        xml, _ = units.build(MUTATIONS, "Mutations.example.xml", {LEVELTEXT: LEVELTEXT_UK})
        back = units.ExampleFile(MUTATIONS, "Mutations.example.xml").read_translation(xml)
        self.assertEqual(back[LEVELTEXT], LEVELTEXT_UK)


if __name__ == "__main__":
    unittest.main()
