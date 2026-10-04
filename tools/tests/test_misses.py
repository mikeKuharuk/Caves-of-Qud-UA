"""Reading what Player.log says the translation lacks (tools/misses.py)."""
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import misses  # noqa: E402

LOG = """Initializing engine
String table miss - Lang uk - Context="Combat Hit" ID="You hit!"
INFO - [uk-miss] Text: You can't do that here.
INFO - [uk-miss] Damage: from %t bite.
INFO - [uk-miss] Text: You can't do that here.
"""


class Misses(unittest.TestCase):
    def test_string_and_code_table_misses(self):
        with tempfile.TemporaryDirectory() as d:
            log = pathlib.Path(d) / "Player.log"
            log.write_text(LOG, encoding="utf-8")
            self.assertEqual(list(misses.read_misses([log])), [("Combat Hit", "You hit!")])
            # each [uk-miss] once, in the order the game met them
            self.assertEqual(misses.read_code_misses([log]),
                             [("Text", "You can't do that here."), ("Damage", "from %t bite.")])


if __name__ == "__main__":
    unittest.main()
