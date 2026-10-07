"""The XML documentation of the mod's replacers: the game's wish testlangreplacers reads it as XML
(VariableReplacers.WishTest → XmlWriter.WriteNode), and a stray «<» there («=object.p:<for the player>=») throws and
sends a crash report."""
import pathlib
import re
import unittest
import xml.etree.ElementTree as ET

GRAMMAR = pathlib.Path(__file__).resolve().parents[2] / "mod" / "Grammar"


def doc_blocks(source: str):
    """Each run of /// lines, as one text."""
    block = []
    for line in source.splitlines():
        m = re.match(r"\s*///\s?(.*)$", line)
        if m:
            block.append(m.group(1))
        elif block:
            yield "\n".join(block)
            block = []
    if block:
        yield "\n".join(block)


class ReplacerDocs(unittest.TestCase):
    def test_replacer_docs_are_well_formed_xml(self):
        files = [p for p in GRAMMAR.glob("*.cs") if "HasVariableReplacer" in p.read_text(encoding="utf-8")]
        self.assertTrue(files)
        for path in files:
            for block in doc_blocks(path.read_text(encoding="utf-8")):
                with self.subTest(file=path.name, doc=block[:60]):
                    ET.fromstring(f"<doc>{block}</doc>")


if __name__ == "__main__":
    unittest.main()
