"""Every check is exercised twice: it must stay quiet on a good translation and fire on a bad one."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import checks  # noqa: E402
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


if __name__ == "__main__":
    unittest.main()
