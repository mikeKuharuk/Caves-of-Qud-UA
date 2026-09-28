import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import po  # noqa: E402


class RoundTrip(unittest.TestCase):
    def roundtrip(self, cat: po.Catalog) -> po.Catalog:
        text = po.dumps(cat)
        back = po.loads(text)
        self.assertEqual(po.dumps(back), text, "second dump differs from the first")
        return back

    def test_simple_and_header(self):
        cat = po.Catalog(headers={"Language": "uk", "X-Qud-Build": "2.0.212.31"},
                         header_comments=["title"],
                         entries=[po.Entry(msgid="New Game", msgstr="Нова гра", msgctxt="MainMenu Main")])
        back = self.roundtrip(cat)
        self.assertEqual(back.headers["X-Qud-Build"], "2.0.212.31")
        self.assertEqual(back.header_comments, ["title"])
        self.assertEqual(back.entries[0].key, ("MainMenu Main", "New Game"))
        self.assertEqual(back.entries[0].msgstr, "Нова гра")

    def test_escapes_and_multiline(self):
        tricky = 'He said "hi"\\ then\tleft.\nSecond line\n\nThird ▶ ✓'
        cat = po.Catalog(entries=[po.Entry(msgid=tricky, msgstr=tricky.upper(), msgctxt="a\nb")])
        back = self.roundtrip(cat)
        self.assertEqual(back.entries[0].msgid, tricky)
        self.assertEqual(back.entries[0].msgstr, tricky.upper())
        self.assertEqual(back.entries[0].msgctxt, "a\nb")
        self.assertIn('msgid ""\n"He said', po.dumps(cat))

    def test_trailing_and_leading_whitespace_survive(self):
        for s in (" or ", "and ", "\n", "\n\n", "x\n"):
            back = self.roundtrip(po.Catalog(entries=[po.Entry(msgid=s, msgstr=s)]))
            self.assertEqual(back.entries[0].msgid, s)

    def test_no_context_vs_empty_context(self):
        cat = po.Catalog(entries=[po.Entry(msgid="x"), po.Entry(msgid="x", msgctxt="")])
        back = self.roundtrip(cat)
        self.assertEqual([e.msgctxt for e in back.entries], [None, ""])

    def test_flags_comments_previous_obsolete(self):
        e1 = po.Entry(msgid="new text", msgstr="переклад", msgctxt="k", flags=["fuzzy", "qud-compound"],
                      translator_comments=["note from Mike"], extracted_comments=["hint"],
                      previous_msgid="old text")
        e2 = po.Entry(msgid="gone", msgstr="зникло", msgctxt="k2", obsolete=True)
        back = self.roundtrip(po.Catalog(entries=[e1, e2]))
        b1, b2 = back.entries
        self.assertTrue(b1.fuzzy)
        self.assertEqual(b1.flags, ["fuzzy", "qud-compound"])
        self.assertEqual(b1.translator_comments, ["note from Mike"])
        self.assertEqual(b1.extracted_comments, ["hint"])
        self.assertEqual(b1.previous_msgid, "old text")
        self.assertTrue(b2.obsolete)
        self.assertEqual((b2.msgctxt, b2.msgid, b2.msgstr), ("k2", "gone", "зникло"))

    def test_reads_poedit_style_wrapping(self):
        text = ('msgid ""\nmsgstr ""\n"Language: uk\\n"\n\n'
                'msgctxt "c"\nmsgid ""\n"long "\n"line"\nmsgstr ""\n"довгий "\n"рядок"\n')
        cat = po.loads(text)
        self.assertEqual(cat.entries[0].msgid, "long line")
        self.assertEqual(cat.entries[0].msgstr, "довгий рядок")

    def test_control_characters_are_refused(self):
        with self.assertRaises(po.POError):
            po.dumps(po.Catalog(entries=[po.Entry(msgid="bell\a")]))

    def test_bad_input_is_reported_with_line(self):
        with self.assertRaises(po.POError) as ctx:
            po.loads('msgid "a"\nmsgstr "b"\ngarbage\n')
        self.assertIn("line 3", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
