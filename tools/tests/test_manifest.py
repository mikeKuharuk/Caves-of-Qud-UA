"""The game loads only the folders mod/manifest.json lists (ModInfo: «Loading path: …» in build_log.txt): a folder
of C# or language files left out of it is silently never compiled or read. tools/patch-tests builds the mod from
the source folders directly, so it cannot notice."""
import json
import pathlib
import unittest

MOD = pathlib.Path(__file__).resolve().parents[2] / "mod"


class Manifest(unittest.TestCase):
    def test_every_folder_with_mod_files_is_listed(self):
        manifest = json.loads((MOD / "manifest.json").read_text(encoding="utf-8"))
        listed = {d["Path"].strip("/") for d in manifest["Directories"]}
        needed = {p.parent.relative_to(MOD).as_posix() for pattern in ("*.cs", "*.xml")
                  for p in MOD.rglob(pattern)}
        self.assertEqual(needed - listed, set(), "folders the game would never load")


if __name__ == "__main__":
    unittest.main()
