"""HistorySpice references in translations must lead to a list; the overlay may only add keys."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import spice  # noqa: E402

ENGLISH = {
    "commonPhrases": {"historic": ["historic", "famed"], "ruins": ["ruins"]},
    "elements": {"glass": {"adjectives": ["glassy"], "nouns": ["glass"]}, "salt": {"adjectives": ["salty"]}},
}
OVERLAY = {"commonPhrases": {"historic_f": ["історична", "славетна"]}}


class Paths(unittest.TestCase):
    def setUp(self):
        self.tree = spice.merge(ENGLISH, OVERLAY)

    def test_existing_and_added_lists_resolve(self):
        text = "=spice:commonPhrases.historic.!random= і =spice:commonPhrases.historic_f.!random|capitalize= <spice.commonPhrases.ruins.!random>"
        self.assertEqual(spice.unresolved(text, self.tree), [])

    def test_variables_are_wildcards(self):
        self.assertEqual(spice.unresolved("=spice:elements.$element.adjectives.!random=", self.tree), [])
        self.assertEqual(spice.unresolved("=spice:elements.entity@elements[random].nouns.!random=", self.tree), [])

    def test_a_typo_leads_nowhere(self):
        self.assertEqual(spice.unresolved("=spice:commonPhrases.historik_f.!random=", self.tree),
                         ["commonPhrases.historik_f.!random"])
        self.assertEqual(spice.unresolved("=spice:elements.$element.adjectives_f.!random=", self.tree),
                         ["elements.$element.adjectives_f.!random"])

    def test_relative_references_use_the_branch(self):
        self.assertEqual(spice.unresolved("=^:ruins.!random=", self.tree, "commonPhrases"), [])
        self.assertEqual(spice.unresolved("=^:ruinz.!random=", self.tree, "commonPhrases"), ["commonPhrases.ruinz.!random"])

    def test_relative_references_use_the_list_parent(self):
        # HistoricSpice.ParseRelativeLinks: =^:x= inside elements.glass.adjectives means elements.glass.x
        self.assertEqual(spice.relative_base("spice.elements.glass.adjectives"), "elements.glass")
        self.assertEqual(spice.relative_base(("commonPhrases", "historic")), "commonPhrases")
        self.assertEqual(spice.relative_base(("adjectives",)), "")
        base = spice.relative_base("spice.elements.glass.adjectives")
        self.assertEqual(spice.unresolved("=^:nouns.!random=", self.tree, base), [])
        self.assertEqual(spice.unresolved("=^:salt.!random=", self.tree, base), ["elements.glass.salt.!random"])

    def test_two_overlay_files_may_not_define_the_same_key(self):
        parts = {"a.json": {"commonPhrases": {"historic_f": ["x"]}},
                 "b.json": {"commonPhrases": {"historic_f": ["y"], "ruins_gen": ["руїн"]}}}
        self.assertEqual(spice.overlay_clashes(parts), ["spice.commonPhrases.historic_f in a.json and b.json"])

    def test_overlay_only_adds(self):
        self.assertEqual(spice.overlay_conflicts(ENGLISH, OVERLAY), [])
        self.assertEqual(spice.overlay_conflicts(ENGLISH, {"commonPhrases": {"historic": ["x"]}}), ["commonPhrases.historic"])
        merged = spice.merge(ENGLISH, {"commonPhrases": {"historic": ["x"], "new": ["y"]}})
        self.assertEqual(merged["commonPhrases"]["historic"], ["historic", "famed"])  # never replaced
        self.assertEqual(merged["commonPhrases"]["new"], ["y"])


if __name__ == "__main__":
    unittest.main()
