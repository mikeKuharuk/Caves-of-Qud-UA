"""HistorySpice: units out of the game's JSONC, and the mod file that replaces translated branches."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import checks, spice, units  # noqa: E402

SAMPLE = """{
  // the game's file has comments
  "spice": {
    "commonPhrases": {
      "strange": ["strange", "odd", "strange"],   /* a duplicate is one unit */
      "ref": ["<spice.commonPhrases.strange.!random>"]
    },
    "professions": {"tinker": {"singular": "tinker", "plural": "tinkers", "weight": 3}},
    "untouched": {"a": ["=spice:x.y="]},
  }
}"""


class Spice(unittest.TestCase):
    def test_units_are_text_leaves_keyed_by_path(self):
        us = units.extract(SAMPLE, "HistorySpice.jsonc")
        self.assertEqual([(u.msgctxt, u.msgid) for u in us], [
            ("spice.commonPhrases.strange", "strange"),
            ("spice.commonPhrases.strange", "odd"),
            ("spice.professions.tinker.singular", "tinker"),
            ("spice.professions.tinker.plural", "tinkers"),
        ])
        self.assertEqual({u.kind for u in us}, {"spice"})

    def test_identifiers_are_not_units(self):
        # FoundAsBabe stores a @professions value; =spice:professions.entity@profession.plural= then selects by it
        sample = """{"spice": {
          "elements": {"glass": {"@professions": ["glassblower"], "nouns": ["glass"]}},
          "regions": {"@types": ["city-states"], "Saltmarsh": {"baseColor": ["y", "w"]}},
          "friendOrFoe": {"_failureredirect": "spice.friendOrFoe.default"}}}"""
        us = units.extract(sample, "HistorySpice.jsonc")
        self.assertEqual([(u.msgctxt, u.msgid) for u in us], [("spice.elements.glass.nouns", "glass")])
        self.assertTrue(spice.is_identifier(("elements", "glass", "@professions")))
        self.assertFalse(spice.is_identifier(("professions", "glassblower", "singular")))

    def test_build_replaces_translated_branches_only(self):
        t = {("spice.commonPhrases.strange", "strange"): "дивний"}
        text, count = spice.build(SAMPLE, "HistorySpice.jsonc", t, overlay={})  # the repo's additions stay out
        doc = json.loads(text)
        self.assertEqual(doc["lang"], "uk")
        self.assertEqual(count, 2)  # both copies of "strange"
        # "=" replaces the branch instead of appending to it (HistoricSpice.MergeModJson)
        self.assertEqual(list(doc["spice"]), ["commonPhrases="])
        branch = doc["spice"]["commonPhrases="]
        self.assertEqual(branch["strange"], ["дивний", "odd", "дивний"])
        self.assertEqual(branch["ref"], ["<spice.commonPhrases.strange.!random>"])
        self.assertIn(units.GENERATED_MARKER, text[:300])

    def test_names(self):
        self.assertEqual(units.po_name("HistorySpice.jsonc"), "HistorySpice.po")
        self.assertEqual(units.output_name("HistorySpice.jsonc"), "historyspice.uk.json")
        self.assertEqual(units.output_name("Creatures.example.xml"), "Creatures.uk.xml")

    def test_references_must_survive(self):
        src = "by trapping <spice.pronouns.object.!random> in a prism"
        self.assertEqual(checks.check(src, "ув’язнивши <spice.pronouns.object.!random> у призмі", spice=True), [])
        issues = checks.check(src, "ув’язнивши когось у призмі", spice=True)
        self.assertIn("spice-reference", {i.code for i in issues if i.severity == "error"})


if __name__ == "__main__":
    unittest.main()
