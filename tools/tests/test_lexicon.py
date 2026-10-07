"""The words the build gives mod/Grammar/UkrainianCases to read a name by (AdjectiveLexicon.g.cs): adjectives, nouns,
noun stems. The words here are ordinary Ukrainian, not taken from the game."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import commands  # noqa: E402


class Lexicon(unittest.TestCase):
    def test_a_soft_adjective_needs_its_other_forms(self):
        words = {"синій", "синього", "прямокутній", "прямокутний", "модифікацій"}
        self.assertTrue(commands.soft_adjective("синій", words))
        # a hard adjective's feminine dative and a noun's genitive plural end the same way
        self.assertFalse(commands.soft_adjective("прямокутній", words))
        self.assertFalse(commands.soft_adjective("модифікацій", words))

    def test_an_adjective_before_a_noun_agrees_with_it(self):
        self.assertTrue(commands.agrees("уламкова", "кольчуга"))
        self.assertTrue(commands.agrees("слонова", "кість"))
        self.assertTrue(commands.agrees("розкладне", "крісло"))
        self.assertTrue(commands.agrees("кутні", "зуби"))
        self.assertFalse(commands.agrees("дочка", "фермера"))
        self.assertFalse(commands.agrees("пляшка", ""))

    def test_a_name_led_by_its_noun(self):
        self.assertTrue(commands.NOUN_FIRST.match("statue of Bel"))
        self.assertTrue(commands.NOUN_FIRST.match("the box of crayons"))
        self.assertTrue(commands.NOUN_FIRST.match("apple farmer's daughter"))
        self.assertFalse(commands.NOUN_FIRST.match("sapphire figurine of the Crystal Woe"))
        self.assertFalse(commands.NOUN_FIRST.match("blueprints for Q Girl's climber design"))

    def test_noun_stems_by_their_forms(self):
        words = {"трубою", "залоза", "піснею", "тінню", "кистю", "залишків", "гриба", "гриб", "сосна", "соснам"}
        hard, soft, third, masculine = commands.noun_stems(words)
        self.assertIn("труб", hard)       # «трубою»
        self.assertIn("залоз", hard)      # «залоза», and no «залоз», «залозом», «залозові»
        self.assertNotIn("гриб", hard)    # «гриба» has «гриб» beside it
        self.assertIn("пісн", soft)
        self.assertEqual({"тін", "кист"}, third)
        self.assertEqual({"залишк"}, masculine)


if __name__ == "__main__":
    unittest.main()
