"""Worksheets: what apply accepts and what it refuses."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import batch, commands, po, store  # noqa: E402

M = "▶"
OPTIONS = f"""<?xml version="1.0" encoding="utf-8"?>
<!--
<options>
  <option ID="Key" DisplayText="DisplayText" Category="DisplayText" Values="DisplayText">
-->
<options Lang="example" Encoding="utf-8">
  <option ID="A" DisplayText="{M}Music" Category="{M}Sound" Values="Modern|{M}Modern,Classic|{M}Classic" />
  <option ID="B" DisplayText="{M}Volume" Category="{M}Sound" />
</options>"""


class Batch(unittest.TestCase):
    def setUp(self):
        self.cat, _ = commands.sync_file(OPTIONS, "Options.example.xml", None)
        self.rows = batch.make_worksheet(self.cat, "Options.po")[1:]

    def row(self, ctx):
        return next(r for r in self.rows if r["ctx"] == ctx)

    def test_worksheet_lists_untranslated_units_with_keys(self):
        self.assertEqual(len(self.rows), 5)
        r = self.row("option[ID=A]@DisplayText")
        self.assertEqual((r["en"], r["uk"]), ("Music", ""))
        self.assertEqual(r["k"], store.keys("option[ID=A]@DisplayText", "Music")[0])

    def test_apply_good_and_refuse_bad(self):
        self.row("option[ID=A]@DisplayText")["uk"] = "Музика"
        self.row("option[ID=A]@Values")["uk"] = f"Modern|{M}Сучасний,Classic|{M}Класичний"
        self.row("option[ID=B]@DisplayText")["uk"] = "{{W|Гучність"          # broken markup
        self.row("option[ID=B]@Category")["uk"] = ""                        # empty: skipped
        applied, problems = batch.apply_rows(self.cat, self.rows + [{"k": "0" * 20, "ctx": "gone", "uk": "x"}])
        self.assertEqual(applied, 2)
        self.assertEqual(len(problems), 2)   # broken markup + unknown unit
        tr = commands.translations_of(self.cat)
        self.assertEqual(tr[("option[ID=A]@DisplayText", "Music")], "Музика")
        self.assertNotIn(("option[ID=B]@DisplayText", "Volume"), tr)

    def test_fuzzy_flag_and_comment(self):
        r = self.row("option[ID=B]@DisplayText")
        r.update(uk="Гучність", fuzzy=True, comment="перевірити в грі")
        batch.apply_rows(self.cat, [r])
        e = next(e for e in self.cat.entries if e.msgctxt == "option[ID=B]@DisplayText")
        self.assertTrue(e.fuzzy)
        self.assertEqual(e.translator_comments, ["перевірити в грі"])

    def test_rows_carry_the_unit_kind(self):
        self.assertEqual(self.row("option[ID=A]@Values")["flags"], ["qud-compound"])
        self.assertNotIn("flags", self.row("option[ID=A]@DisplayText"))

    def test_check_rows_without_the_catalog(self):
        # translators (people or subagents) check a filled worksheet without touching the PO files
        good = dict(self.row("option[ID=A]@Values"), uk=f"Modern|{M}Сучасний,Classic|{M}Класичний")
        broken = dict(self.row("option[ID=B]@DisplayText"), uk="{{W|Гучність")
        drifted = dict(self.row("option[ID=A]@DisplayText"), uk="Музика =x=")
        accepted = dict(drifted, comment="qud-gender: f\nqud-ok: placeholder — навмисно")   # several comments
        empty = self.row("option[ID=B]@Category")
        report = batch.check_rows([good, broken, drifted, accepted, empty])
        self.assertEqual(report.missing, 1)
        self.assertEqual({k for k, _, _ in report.errors}, {broken["k"]})
        self.assertEqual({k for k, _, _ in report.warnings}, {drifted["k"]})
        self.assertEqual(len(report.warnings), 1)   # the same drift with qud-ok is silent

    def test_roundtrip_through_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "w.jsonl"
            batch.write(p, [{"po": "Options.po"}] + self.rows)
            header, rows = batch.read(p)
            self.assertEqual(header, {"po": "Options.po"})
            self.assertEqual(rows, self.rows)


if __name__ == "__main__":
    unittest.main()
