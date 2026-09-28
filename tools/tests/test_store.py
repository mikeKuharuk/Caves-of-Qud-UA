"""The committed store: our text round-trips, and no English text of the game ever gets into it."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import commands, po, sources, store, units  # noqa: E402

M = units.MARK


def objects(render: str, short: str) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!--
<objects>
  <object Name="Key" Load="">
    <part Name="Key">
-->
<objects Lang="example" Encoding="utf-8">
  <object Name="Cat" Load="Merge">
    <part Name="Render" DisplayName="{M}{render}" />
    <part Name="Description" Short="{M}{short}" />
  </object>
</objects>"""


def entry(cat, ctxt):
    return next(e for e in cat.entries if e.msgctxt == ctxt and not e.obsolete)


class Store(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(self.tmp.name)
        self.po_dir, self.store_dir = base / "po", base / "store"
        self.name = "Creatures.example.xml"

    def tearDown(self):
        self.tmp.cleanup()

    def sync(self, xml, **kw):
        commands.cmd_sync({self.name: xml}, self.po_dir, self.store_dir, quiet=True, **kw)
        return po.load(self.po_dir / "Creatures.po")

    def edit(self, **translations):
        path = self.po_dir / "Creatures.po"
        cat = po.load(path)
        for ctxt, text in translations.items():
            entry(cat, ctxt.replace("__", "/").replace("_at_", "@")).msgstr = text
        po.dump(cat, path)

    def test_roundtrip_through_a_fresh_clone(self):
        xml = objects("cat", "A ray cat.")
        self.sync(xml)
        self.edit(**{"object[Cat]__part[Render]_at_DisplayName": "кіт"})
        commands.cmd_save({self.name: xml}, self.po_dir, self.store_dir)
        # a fresh clone has the store but no local PO
        (self.po_dir / "Creatures.po").unlink()
        cat = self.sync(xml)
        self.assertEqual(entry(cat, "object[Cat]/part[Render]@DisplayName").msgstr, "кіт")
        self.assertFalse(entry(cat, "object[Cat]/part[Render]@DisplayName").fuzzy)

    def test_english_changed_while_only_the_store_knew_the_translation(self):
        self.sync(objects("cat", "A ray cat."))
        self.edit(**{"object[Cat]__part[Description]_at_Short": "Променистий кіт."})
        commands.cmd_save({self.name: objects("cat", "A ray cat.")}, self.po_dir, self.store_dir)
        (self.po_dir / "Creatures.po").unlink()
        cat = self.sync(objects("cat", "A ray cat, purring."))   # new game build, same attribute
        e = entry(cat, "object[Cat]/part[Description]@Short")
        self.assertEqual((e.msgstr, e.fuzzy), ("Променистий кіт.", True))

    def test_orphans_survive(self):
        xml = objects("cat", "A ray cat.")
        self.sync(xml)
        self.edit(**{"object[Cat]__part[Render]_at_DisplayName": "кіт"})
        commands.cmd_save({self.name: xml}, self.po_dir, self.store_dir)
        (self.po_dir / "Creatures.po").unlink()
        other = xml.replace('Name="Cat"', 'Name="Dog"')          # the cat is gone from the game
        self.sync(other)
        _, records = store.load(self.store_dir / "Creatures.jsonl")
        self.assertEqual([(r["t"], r.get("o")) for r in records], [("кіт", 1)])
        self.sync(xml)                                           # ... and comes back
        _, records = store.load(self.store_dir / "Creatures.jsonl")
        self.assertEqual([(r["t"], r.get("o")) for r in records], [("кіт", None)])

    def test_local_edits_win_unless_asked(self):
        xml = objects("cat", "A ray cat.")
        self.sync(xml)
        self.edit(**{"object[Cat]__part[Render]_at_DisplayName": "кіт"})
        commands.cmd_save({self.name: xml}, self.po_dir, self.store_dir)
        self.edit(**{"object[Cat]__part[Render]_at_DisplayName": "котик"})   # local, not saved
        cat = self.sync(xml)
        self.assertEqual(entry(cat, "object[Cat]/part[Render]@DisplayName").msgstr, "котик")
        # someone else's store wins with --from-store
        self.edit(**{"object[Cat]__part[Render]_at_DisplayName": "кицька"})
        cat = self.sync(xml, prefer_store=True)
        self.assertEqual(entry(cat, "object[Cat]/part[Render]@DisplayName").msgstr, "котик")

    def test_unsaved_edits_are_reported(self):
        xml = objects("cat", "A ray cat.")
        self.sync(xml)
        self.edit(**{"object[Cat]__part[Render]_at_DisplayName": "кіт"})
        cat = po.load(self.po_dir / "Creatures.po")
        self.assertEqual(commands.unsaved(cat, self.store_dir, self.name), 1)
        commands.cmd_save({self.name: xml}, self.po_dir, self.store_dir)
        self.assertEqual(commands.unsaved(cat, self.store_dir, self.name), 0)


GAME = sources.GAME_EXAMPLE_DIR.exists()


@unittest.skipUnless(GAME, "the game's ExampleLanguage folder is not available")
class NoEnglishInTheStore(unittest.TestCase):
    """The copyright guard: give every unit of the real game a Ukrainian translation, export the
    store, and make sure no English text (msgid) or key path (msgctxt) of the game is in it."""

    def test_records_carry_no_source_text(self):
        files = sources.from_dir(sources.GAME_EXAMPLE_DIR)
        for name in ("Strings.example.xml", "Creatures.example.xml", "Books.example.xml"):
            cat, _ = commands.sync_file(files[name], name, None)
            for i, e in enumerate(cat.entries):
                e.msgstr = f"переклад {i}"
            text = store.dumps(store.export(cat), {"source": name})
            for e in cat.entries:
                for probe in (e.msgid, e.msgctxt or ""):
                    if len(probe) >= 12:
                        self.assertNotIn(probe, text, f"{name}: English/key text leaked into the store")


if __name__ == "__main__":
    unittest.main()
