"""Every check is exercised twice: it must stay quiet on a good translation and fire on a bad one."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import checks, po  # noqa: E402
from qudtr.units import MARK as M  # noqa: E402


def codes(msgid, msgstr, compound=False, severity=None):
    return {i.code for i in checks.check(msgid, msgstr, compound) if severity in (None, i.severity)}


class Checks(unittest.TestCase):
    def test_clean_translation_passes(self):
        src = "{{W|1. Walk around}} =subject.T= =verb:go= north. Press ~CmdMoveN."
        dst = "{{W|1. Походіть навколо}} =subject.T= =verb:go= на північ. Натисніть ~CmdMoveN."
        self.assertEqual(checks.check(src, dst), [])

    def test_leftover_marker(self):
        self.assertIn("marker", codes("Hello", f"{M}Привіт", severity="error"))

    def test_unbalanced_braces(self):
        self.assertIn("braces", codes("{{W|x}}", "{{W|ікс}", severity="error"))

    def test_markup_left_open_as_in_the_source(self):
        # the preacher's prefix: the code appends the closing «'}}»
        src = "The preacher says, {{W|'"
        self.assertNotIn("braces", codes(src, "Проповідник каже: {{W|'", severity="error"))
        self.assertIn("braces", codes(src, "Проповідник каже: '", severity="error"))

    def test_unknown_shader_name(self):
        # Cyrillic 'о' inside the shader name is a classic typo
        self.assertIn("shader", codes("{{emote|*purrs*}}", "{{emоte|*муркоче*}}", severity="error"))

    def test_placeholder_missing_or_extra(self):
        self.assertIn("placeholder", codes("=subject.T= hits you.", "Хтось б'є вас.", severity="warning"))
        self.assertIn("placeholder", codes("Hits you.", "=subject.T= б'є вас.", severity="warning"))
        self.assertNotIn("placeholder", codes("=a= and =b=", "=b= і =a="))  # reordering is fine

    def test_adjacent_placeholders(self):
        src = "=pronouns.subjective==verb:'re:afterpronoun= here"
        self.assertEqual(sorted(checks.PLACEHOLDER.findall(src)), ["pronouns.subjective", "verb:'re:afterpronoun"])

    def test_capitalized_forms_the_game_registers_are_the_same_placeholder(self):
        # Ukrainian word order often moves a variable to the start of a sentence.
        src = "=glyph:ChargenBullet= minimum =min= =stat.statDisplayName="
        for dst in ("=glyph:ChargenBullet= =stat.StatDisplayName=: щонайменше =min=",       # upper-case key
                    "=glyph:ChargenBullet= =stat.statDisplayName|capitalize=: щонайменше =min="):  # case-only post-processor
            self.assertNotIn("placeholder", codes(src, dst), dst)
        self.assertNotIn("placeholder", codes("=subject.T= hits you.", "=subject.t= б’є вас."))

    def test_capitalizing_a_key_without_an_upper_case_form_warns(self):
        # dayOfYear has no Capitalization: =now.DayOfYear= would not resolve in the game
        self.assertIn("placeholder", codes("Day =now.dayOfYear=.", "=now.DayOfYear=-й день.", severity="warning"))

    def test_replacer_list_is_generated_from_the_game(self):
        self.assertIn("statDisplayName", checks.CAPITALIZABLE["replacer"])
        self.assertIn("t", checks.CAPITALIZABLE["replacer"])
        self.assertNotIn("dayOfYear", checks.CAPITALIZABLE["replacer"])
        self.assertIn("article", checks.CAPITALIZABLE["post"])

    def test_command_tokens(self):
        self.assertIn("command", codes("Press ~CmdLook.", "Натисніть ~CmdLok.", severity="error"))
        self.assertNotIn("command", codes("Press ~CmdLook.", "Натисніть ~CmdLook."))

    def test_dialogue_alternatives_count(self):
        self.assertIn("alternatives", codes("Hi.~Hello.", "Привіт.", severity="warning"))
        self.assertNotIn("alternatives", codes("Hi.~Hello.", "Привіт.~Вітаю."))

    def test_compound_keys(self):
        src = f"Modern|{M}Modern,Classic|{M}Classic"
        self.assertEqual(codes(src, f"Modern|{M}Сучасний,Classic|{M}Класичний", True), set())
        self.assertIn("compound-key", codes(src, f"Сучасний|{M}Сучасний,Classic|{M}Класичний", True, "error"))
        self.assertIn("marker", codes(src, "Modern|Сучасний,Classic|Класичний", True, "error"))
        faction = f"Joppa,friend,{M}defending their village"
        self.assertEqual(codes(faction, f"Joppa,friend,{M}захищали їхнє село", True), set())
        self.assertIn("compound-key", codes(faction, f"Йоппа,friend,{M}захищали їхнє село", True, "error"))

    def test_compound_alternatives_may_change_count(self):
        src = f"{M}Meow.~{M}Mrrp."
        self.assertEqual(codes(src, f"{M}Няв.~{M}Мрр.~{M}Мур.", True, "error"), set())

    def test_color_codes(self):
        self.assertIn("color", codes("&yNormal &Rred", "&yЗвичайний червоний", severity="warning"))
        self.assertNotIn("color", codes("a && b", "а && б"))

    def test_whitespace_at_ends(self):
        self.assertIn("whitespace", codes(" or ", "або", severity="warning"))
        self.assertNotIn("whitespace", codes(" or ", " або "))

    def test_mixed_script(self):
        self.assertIn("mixed-script", codes("Snapjaw", "Клацoщелеп", severity="warning"))  # Latin 'o'
        self.assertNotIn("mixed-script", codes("HP: =hp=", "ОЗ: =hp="))

    def test_apostrophe(self):
        self.assertIn("apostrophe", codes("nine", "дев'ять", severity="warning"))
        self.assertIn("apostrophe", codes("nine", "девʼять", severity="warning"))
        self.assertNotIn("apostrophe", codes("nine", "дев’ять"))

    def test_empty_translation_is_not_checked(self):
        self.assertEqual(checks.check("anything", ""), [])

    def test_acknowledged_warnings(self):
        # "qud-ok: <code>" in a translator comment accepts a deliberate deviation; errors stay
        e = po.Entry(msgid="=unit|value.pluralize=", msgstr="=unit=")
        self.assertEqual({i.code for i in checks.check_entry(e)}, {"placeholder"})
        e.translator_comments = ["qud-ok: placeholder — англійська множина псує кирилицю"]
        self.assertEqual(checks.check_entry(e), [])
        e.msgstr = "=unit= {{W|"
        issues = checks.check_entry(e)
        self.assertIn("braces", {i.code for i in issues})
        self.assertEqual({i.severity for i in issues}, {"error"})


SRC_T = ('<p>You gain +<stat Name="Bonus" /> quickness &amp; <stat Name="Rank" Unit="rank" />.</p>\n<br />\n'
         '<statline Name="Cooldown" DisplayName="Cooldown" />')


def tcodes(msgstr, severity=None):
    return {i.code for i in checks.check(SRC_T, msgstr, template=True) if severity in (None, i.severity)}


class TemplateChecks(unittest.TestCase):
    def test_good_translation_passes(self):
        # stats may move inside the sentence; DisplayName and Unit are translated; &amp; is text, not a color code
        dst = ('<p>Ви отримуєте <stat Name="Rank" Unit="ранг" /> &amp; +<stat Name="Bonus" /> до швидкості.</p>\n<br />\n'
               '<statline Name="Cooldown" DisplayName="Перезаряджання" />')
        self.assertEqual(checks.check(SRC_T, dst, template=True), [])

    def test_broken_xml_is_an_error(self):
        self.assertIn("template-xml", tcodes('<p>Ви отримуєте +<stat Name="Bonus" /> до швидкості.</p', severity="error"))
        self.assertIn("template-xml", tcodes('<p>А & Б</p><br /><statline Name="Cooldown" />', severity="error"))

    def test_lost_or_changed_tags_are_errors(self):
        no_stat = '<p>Ви отримуєте до швидкості <stat Name="Rank" Unit="ранг" />.</p><br /><statline Name="Cooldown" DisplayName="П" />'
        renamed = no_stat.replace("до швидкості", '+<stat Name="Bonuz" /> до швидкості')
        no_br = SRC_T.replace("<br />", "")
        for dst in (renamed, no_br):
            self.assertIn("template-structure", tcodes(dst, severity="error"), dst)

    def test_a_dropped_stat_is_a_warning(self):
        # English-only stats such as an article (<stat Name="MineAn" />) have no place in Ukrainian;
        # dropping one is reviewed with qud-ok. Anything else that changes the tags stays an error.
        no_stat = '<p>Ви отримуєте до швидкості <stat Name="Rank" Unit="ранг" />.</p><br /><statline Name="Cooldown" DisplayName="П" />'
        self.assertEqual(tcodes(no_stat), {"template-stat-dropped"})
        self.assertEqual(tcodes(no_stat, severity="error"), set())

    def test_reordered_blocks_warn(self):
        dst = ('<statline Name="Cooldown" DisplayName="Перезаряджання" />\n<br />\n'
               '<p>Ви отримуєте +<stat Name="Bonus" /> &amp; <stat Name="Rank" Unit="ранг" />.</p>')
        self.assertIn("template-order", tcodes(dst, severity="warning"))
        self.assertNotIn("template-structure", tcodes(dst))


if __name__ == "__main__":
    unittest.main()
