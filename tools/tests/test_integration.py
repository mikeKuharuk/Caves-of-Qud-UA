"""Checks against the real ExampleLanguage files (skipped when neither the game nor the mirror is there).

The roundtrip test builds every file with an identity "translation" (msgstr = msgid) and reads the
result back with the importer: every non-compound unit must come back at the same key with the
same text. That proves the extractor, the builder and the importer agree on every element path
in the game's real data, not just in the hand-written fixtures.
"""
import collections
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from qudtr import commands, sources, units  # noqa: E402


def load_files():
    if sources.GAME_EXAMPLE_DIR.exists():
        return sources.from_dir(sources.GAME_EXAMPLE_DIR)
    if (sources.MIRROR / "ExampleLanguage").exists():
        return sources.from_dir(sources.MIRROR / "ExampleLanguage")
    return None


FILES = load_files()


def attr_of(unit: units.Unit) -> tuple[str, str]:
    """('part', 'DisplayName') for 'object[X]/part[Render]@DisplayName'."""
    path, attr = unit.msgctxt.rsplit("@", 1)
    last = path.rsplit("/", 1)[-1]
    return last.split("[")[0].split("#")[0], attr


@unittest.skipIf(FILES is None, "no ExampleLanguage files available")
class RealData(unittest.TestCase):
    def test_keys_are_unique_except_repeated_strings(self):
        total = 0
        for name, text in FILES.items():
            us = units.extract(text, name)
            counts = collections.Counter(u.key for u in us)
            dupes = [u for u in us if counts[u.key] > 1]
            # the only duplicates allowed are identical <string> Context+ID pairs, which the game
            # stores as one entry anyway
            self.assertTrue(all(u.kind == "string" for u in dupes),
                            f"{name}: non-string duplicate keys {[u.key for u in dupes if u.kind != 'string'][:3]}")
            total += len(us)
        self.assertGreater(total, 20000)

    def test_no_marker_survives_in_msgids_of_simple_units(self):
        for name, text in FILES.items():
            for u in units.extract(text, name):
                if not u.compound:
                    self.assertNotIn(units.MARK, u.msgid, f"{name}: {u.msgctxt}")

    def test_excluded_keys_are_not_units(self):
        for name, text in FILES.items():
            for u in units.extract(text, name):
                if u.kind == "attr":
                    self.assertNotIn(attr_of(u), units.EXCLUDED_ATTRS, f"{name}: {u.msgctxt}")
                    self.assertNotIn(u.msgid.strip(), units.EXCLUDED_VALUES, f"{name}: {u.msgctxt}")

    def test_build_then_import_roundtrip(self):
        for name, text in FILES.items():
            us = units.extract(text, name)
            identity = {u.key: u.msgid for u in us}
            xml, count = units.build(text, name, identity)
            self.assertIsNotNone(xml, name)
            back = commands.import_translation(text, name, xml, skip_identical=False)
            expected = {u.key: u.msgid for u in us if not u.compound}
            missing = {k for k in expected if k not in back}
            wrong = {k for k in expected if k in back and back[k] != expected[k]}
            self.assertFalse(missing, f"{name}: {len(missing)} units lost, e.g. {sorted(missing, key=str)[:3]}")
            self.assertFalse(wrong, f"{name}: {len(wrong)} units changed, e.g. {sorted(wrong, key=str)[:3]}")


if __name__ == "__main__":
    unittest.main()
