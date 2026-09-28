"""sync: what happens to existing translations when the English string tables change."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import commands, po, sources, units  # noqa: E402

M = units.MARK


def objects(render_name: str, short: str, extra: str = "") -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!--
Caves of Qud - Generated Localizable XML 2.0.212.99
<objects>
  <object Name="Key" Load="">
    <part Name="Key">
-->
<objects Lang="example" Encoding="utf-8">
  <object Name="Cat" Load="Merge">
    <part Name="Render" DisplayName="{M}{render_name}" />
    <part Name="Description" Short="{M}{short}" />
  </object>{extra}
</objects>"""


def strings(*pairs) -> str:
    body = "\n".join(f'  <string Context="{c}" ID="{i}">{M}{i}</string>' for c, i in pairs)
    return f'<?xml version="1.0" encoding="utf-8"?>\n<strings Lang="example" Encoding="utf-8">\n{body}\n</strings>'


def entry(cat, ctxt):
    return next(e for e in cat.entries if e.msgctxt == ctxt and not e.obsolete)


class SyncFile(unittest.TestCase):
    def test_new_catalog(self):
        cat, stats = commands.sync_file(objects("cat", "A cat."), "Creatures.example.xml", None)
        self.assertEqual(stats["new"], 2)
        self.assertEqual(cat.headers["X-Qud-Build"], "2.0.212.99")
        self.assertEqual(cat.headers["Language"], "uk")

    def test_kept_changed_removed(self):
        extra = f'\n  <object Name="Dog" Load="Merge"><part Name="Render" DisplayName="{M}dog" /></object>'
        cat, _ = commands.sync_file(objects("cat", "A cat.", extra), "Creatures.example.xml", None)
        entry(cat, "object[Cat]/part[Render]@DisplayName").msgstr = "кіт"
        entry(cat, "object[Cat]/part[Description]@Short").msgstr = "Кіт."
        entry(cat, "object[Dog]/part[Render]@DisplayName").msgstr = "пес"
        cat = po.loads(po.dumps(cat))  # as if saved and reopened

        # next build: description rewritten, the dog removed
        cat2, stats = commands.sync_file(objects("cat", "A ray cat."), "Creatures.example.xml", cat)
        self.assertEqual((stats["kept"], stats["fuzzy"], stats["obsoleted"], stats["new"]), (1, 1, 1, 0))
        kept = entry(cat2, "object[Cat]/part[Render]@DisplayName")
        self.assertEqual((kept.msgstr, kept.fuzzy), ("кіт", False))
        changed = entry(cat2, "object[Cat]/part[Description]@Short")
        self.assertEqual((changed.msgid, changed.msgstr, changed.fuzzy, changed.previous_msgid),
                         ("A ray cat.", "Кіт.", True, "A cat."))
        gone = [e for e in cat2.entries if e.obsolete]
        self.assertEqual([(e.msgctxt, e.msgstr) for e in gone], [("object[Dog]/part[Render]@DisplayName", "пес")])
        # a fuzzy translation is not built
        self.assertNotIn(changed.key, commands.translations_of(cat2))
        self.assertIn(changed.key, commands.translations_of(cat2, include_fuzzy=True))

    def test_obsolete_comes_back(self):
        cat, _ = commands.sync_file(strings(("C", "Hello")), "Strings.example.xml", None)
        cat.entries[0].msgstr = "Привіт"
        cat, _ = commands.sync_file(strings(("C", "Other")), "Strings.example.xml", po.loads(po.dumps(cat)))
        cat, stats = commands.sync_file(strings(("C", "Hello")), "Strings.example.xml", po.loads(po.dumps(cat)))
        e = entry(cat, "C")
        self.assertEqual((e.msgid, e.msgstr, e.fuzzy), ("Hello", "Привіт", False))

    def test_string_with_edited_english_becomes_fuzzy_only_when_similar(self):
        cat, _ = commands.sync_file(strings(("Popup", "You feel great.")), "Strings.example.xml", None)
        cat.entries[0].msgstr = "Ви почуваєтеся чудово."
        cat = po.loads(po.dumps(cat))
        similar, _ = commands.sync_file(strings(("Popup", "You feel great!")), "Strings.example.xml", cat)
        e = entry(similar, "Popup")
        self.assertEqual((e.msgid, e.fuzzy, e.previous_msgid), ("You feel great!", True, "You feel great."))
        unrelated, _ = commands.sync_file(strings(("Popup", "Completely different words here")), "Strings.example.xml", cat)
        self.assertEqual(entry(unrelated, "Popup").msgstr, "")


MIRROR_OK = (sources.MIRROR / ".git").exists()


@unittest.skipUnless(MIRROR_OK, "example-language mirror not cloned")
class RealBuildTransition(unittest.TestCase):
    """212.30 → 212.31 with every unit 'translated': nothing may be lost, changes must be fuzzy."""

    def test_212_30_to_212_31(self):
        old_files = sources.from_tag("212.30")
        new_files = sources.from_tag("212.31")
        for name in sorted(set(old_files) & set(new_files)):
            cat, _ = commands.sync_file(old_files[name], name, None)
            for e in cat.entries:
                e.msgstr = "UK:" + e.msgid
            cat = po.loads(po.dumps(cat))
            new_cat, stats = commands.sync_file(new_files[name], name, cat)

            old_keys = {u.key for u in units.extract(old_files[name], name)}
            new_units = units.extract(new_files[name], name)
            for e in new_cat.entries:
                if e.obsolete:
                    self.assertNotIn(e.key, {u.key for u in new_units})
                    continue
                if e.key in old_keys:
                    self.assertEqual((e.msgstr, e.fuzzy), ("UK:" + e.msgid, False), f"{name}: {e.key}")
                elif e.msgstr:
                    self.assertTrue(e.fuzzy, f"{name}: reused translation must be fuzzy: {e.key}")
                    self.assertEqual(e.msgstr, "UK:" + e.previous_msgid)
            # every old translation is either still live or kept as obsolete
            live_or_dead = {e.msgstr for e in new_cat.entries if e.msgstr}
            self.assertTrue({"UK:" + k[1] for k in old_keys} <= live_or_dead, name)


if __name__ == "__main__":
    unittest.main()
