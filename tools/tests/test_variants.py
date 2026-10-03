"""VariantNames.uk.xml: a mutation with a fixed variant is named after the variant's VariantName tag."""
import pathlib
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import commands, units  # noqa: E402

M = units.MARK

EXAMPLE = f"""<?xml version="1.0" encoding="utf-8"?>
<mutations Lang="example" Encoding="utf-8">
  <category Name="Physical">
    <mutation Name="Sting (Odd)" DisplayName="{M}Sting (Odd)" />
    <mutation Name="Wings" DisplayName="{M}Wings" />
  </category>
</mutations>"""

BASE = """<?xml version="1.0" encoding="utf-8"?>
<mutations>
  <category Name="Physical">
    <mutation Name="Sting (Odd)" Cost="3" Class="Sting" Variant="Sting Odd" />
    <mutation Name="Wings" Cost="4" Class="Wings" />
  </category>
</mutations>"""


class VariantNames(unittest.TestCase):
    def test_fixed_variants_come_from_the_variant_attribute(self):
        self.assertEqual(commands.fixed_variants(BASE), {"Sting (Odd)": "Sting Odd"})

    def test_the_variant_takes_the_translated_mutation_name(self):
        name = "Mutations.example.xml"
        with tempfile.TemporaryDirectory() as d:
            tmp = pathlib.Path(d)
            cat, _ = commands.sync_file(EXAMPLE, name, None)
            for e in cat.entries:
                e.msgstr = {"Sting (Odd)": "Жало (дивне)", "Wings": "Крила"}[e.msgid]
            commands._write_po(tmp / units.po_name(name), cat)
            names = commands.variant_names({name: EXAMPLE}, BASE, po_dir=tmp, store_dir=tmp)
        self.assertEqual(names, {"Sting Odd": "Жало (дивне)"})

    def test_xml_merges_the_tag_in_the_active_language_only(self):
        root = ET.fromstring(commands.variant_names_xml({"Sting Odd": "Жало \"дивне\" & ін."}))
        self.assertEqual(root.get("Lang"), "uk")
        obj = root.find("object")
        self.assertEqual((obj.get("Name"), obj.get("Load")), ("Sting Odd", "Merge"))
        tag = obj.find("tag")
        self.assertEqual((tag.get("Name"), tag.get("Value")), ("VariantName", "Жало \"дивне\" & ін."))


if __name__ == "__main__":
    unittest.main()
