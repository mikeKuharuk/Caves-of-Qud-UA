"""codescan: English the game's C# writes, found in decompiled code, as code-table keys."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import checks, codescan  # noqa: E402

EFFECT = '''using System;
namespace XRL.World.Effects;
public class Confused : Effect
{
    public Confused(int Duration, string DisplayName = "{{R|very confused}}")
    {
        base.Duration = Duration;
        DisplayName = "{{R|confused}}";
    }
    public override string GetDetails()
    {
        using TextBuilder textBuilder = TextBuilder.Get();
        textBuilder.Append("Acts semi-randomly.\n-").Append(Level).Append(" DV");
        if (MentalPenalty > 0)
        {
            textBuilder.Compound("-", "\n").Append(MentalPenalty).Append(" to all mental attributes");
        }
        return textBuilder.ToString();
    }
    public override string GetStateDescription()
    {
        return (Level > 2) ? "{{R|badly confused}}" : _S("Confused State", "{{R|confused}}");
    }
}
'''


class Patterns(unittest.TestCase):
    def test_literals_holes_ternaries_and_coalescing(self):
        self.assertEqual(codescan.patterns('"{{G|poisoned}}"'), ["{{G|poisoned}}"])
        self.assertEqual([codescan.number_holes(p) for p in codescan.patterns('"-" + Penalty + " Quickness"')],
                         ["-{0} Quickness"])
        self.assertEqual(codescan.patterns('(Level > 1) ? "a" : "b"'), ["a", "b"])
        self.assertEqual(codescan.patterns('x?.Name ?? "default"'), ["default"])
        self.assertEqual(codescan.patterns('_S("ctx", "already in the tables")'), [])

    def test_literal_escapes(self):
        self.assertEqual(codescan.literal_value(r'"a\nb\"c"'), 'a\nb"c')
        self.assertEqual(codescan.literal_value('@"say ""hi"""'), 'say "hi"')


class Effects(unittest.TestCase):
    def test_names_and_detail_lines(self):
        with tempfile.TemporaryDirectory() as d:
            folder = pathlib.Path(d) / "XRL.World.Effects"
            folder.mkdir()
            (folder / "Confused.cs").write_text(EFFECT, encoding="utf-8")
            keys = {e.key: e.where for e in codescan.scan_effects(pathlib.Path(d))}
        self.assertEqual(keys.get("{{R|confused}}"), "Confused.DisplayName")
        self.assertNotIn("{{R|very confused}}", keys)          # a parameter's default value, not an assignment
        self.assertIn("Acts semi-randomly.", keys)
        self.assertIn("-{0} DV", keys)
        self.assertIn("-{0} to all mental attributes", keys)   # Compound puts its separator first: its own line
        self.assertIn("{{R|badly confused}}", keys)
        self.assertNotIn("{{R|confused}}", [k for k, w in keys.items() if w.endswith("GetStateDescription")])


class Holes(unittest.TestCase):
    def test_crlf_lines_keep_no_cr(self):
        # the key is what CodeText looks up: a line without its «\r»
        self.assertEqual(codescan.lines_of("Inventory quick keys\r\n\r\n&WCtrl+A&y - Eat\r\n&WCtrl+P&y - Apply"),
                         ["Inventory quick keys", "&WCtrl+A&y - Eat", "&WCtrl+P&y - Apply"])

    def test_every_hole_must_stay(self):
        self.assertEqual(checks.check("-{0} DV", "-{0} ЗУ"), [])
        self.assertIn("code-hole", {i.code for i in checks.check("-{0} DV", "-ЗУ")})
        self.assertIn("code-hole", {i.code for i in checks.check("-{0} DV", "-{1} ЗУ") if i.severity == "error"})
        self.assertEqual(checks.check("{{G|poisoned}}", "{{G|отруєний}}"), [])
        # a hole right before the end of markup is a hole too
        self.assertIn("code-hole", {i.code for i in checks.check("You gain {{C|{0}}} XP!", "Ви отримуєте {{C|}} ОД!")})

    def test_a_word_counted_with_a_hole(self):
        self.assertEqual(checks.check("in {0} rounds.", "через {0} {0:хід:ходи:ходів}."), [])
        errors = lambda uk: {i.code for i in checks.check("in {0} rounds.", uk) if i.severity == "error"}
        self.assertIn("code-hole", errors("через {0} {1:хід:ходи:ходів}."))   # no {1} in the source
        self.assertIn("code-hole", errors("через {0} {0:ходи:ходів}."))       # two forms


DIDX = """public class Healing : Effect
{
    public override void Apply()
    {
        DidX("begin", "healing");
        DidX("die", null, "!");
        DidXToY("strike", "at", target, "with " + weapon.its + " fist", EndMark: "!");
        IComponent<GameObject>.XDidYToZ(Actor, "kick", Object);
        Messaging.WDidXToYWithZ(Actor, "staunch", Object, "with", Bandage);
        DidXToY("juke", Directions.GetDirectionDescription(text) + ", moving", Object, "out of " + ParentObject.its + " way", null, null, null, ParentObject);
    }
    public void DidX(string Verb, string Extra = null) { }
}
"""


class DidXScan(unittest.TestCase):
    def test_calls_become_runtime_keys(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "Healing.cs").write_text(DIDX, encoding="utf-8")
            found = {k: e for k, e, w in codescan.scan_didx(pathlib.Path(d))}
        self.assertEqual(found.get("X|begin|||healing|."), "<subject> begin healing.")
        self.assertIn("X|die||||!", found)
        self.assertEqual(found.get("XZ|strike|at||with {0} fist|!"), "<subject> strike at <object> with {0} fist!")
        self.assertIn("XZ|kick||||.", found)
        self.assertEqual(found.get("WXZ|staunch||with||."), "<subject> staunch <object> with <indirect>.")

    def test_holes_are_counted_across_the_key(self):
        # the run time fills a translation's {n} with the key's {n}: two fields must not both have a {0}
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "Healing.cs").write_text(DIDX, encoding="utf-8")
            found = {k: e for k, e, w in codescan.scan_didx(pathlib.Path(d))}
        self.assertEqual(found.get("XZ|juke|{0}, moving||out of {1} way|."),
                         "<subject> juke {0}, moving <object> out of {1} way.")

    def test_a_template_with_our_variables_passes(self):
        self.assertEqual(checks.check("<subject> die!", "=subject.Name= =subject.v:помирає:помираєте:помирають=!"), [])


if __name__ == "__main__":
    unittest.main()
