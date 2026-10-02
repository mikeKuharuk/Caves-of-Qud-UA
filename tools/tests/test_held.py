"""translations/uk/held.tsv: units left untranslated on purpose."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import held  # noqa: E402


class Held(unittest.TestCase):
    def test_lines_and_comments(self):
        registry, problems = held.parse("# comment\n\nStrings.po\tabc\tkeep\tключ, який код порівнює\n"
                                        "Items.po\tdef\tcode\tдієслово для DidX\n")
        self.assertEqual(problems, [])
        self.assertEqual(registry[("Strings.po", "abc")].status, "keep")
        self.assertEqual(registry[("Items.po", "def")].reason, "дієслово для DidX")

    def test_malformed_and_duplicate_lines(self):
        _, problems = held.parse("Strings.po\tabc\tmaybe\tпричина\nStrings.po\tabc\n")
        self.assertEqual(len(problems), 2)  # an unknown status, a missing reason
        _, problems = held.parse("Strings.po\tabc\tkeep\tx\nStrings.po\tabc\tcode\ty\n")
        self.assertEqual(problems, ["held.tsv:2: Strings.po abc is listed twice"])

    def test_the_repository_file_parses(self):
        _, problems = held.load()
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
