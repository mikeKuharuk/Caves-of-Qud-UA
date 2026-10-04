"""Finding the game on any system, and linking the mod into its Mods folder (tools/qudtr/game.py, install.py)."""
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from qudtr import game, install  # noqa: E402

VDF = r'''"libraryfolders"
{
	"0"
	{
		"path"		"C:\\Program Files (x86)\\Steam"
		"apps"
		{
			"228980"		"0"
		}
	}
	"1"
	{
		"path"		"E:\\Games\\SteamLibrary"
	}
}
'''


def make_game(folder: pathlib.Path, layout: str) -> pathlib.Path:
    (folder / layout / "StreamingAssets" / "Base").mkdir(parents=True)
    return folder


class FindGame(unittest.TestCase):
    def test_libraries_from_libraryfolders_vdf(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            (root / "steamapps").mkdir()
            (root / "steamapps" / "libraryfolders.vdf").write_text(VDF, encoding="utf-8")
            self.assertEqual(game.libraries(root), [root, pathlib.Path(r"C:\Program Files (x86)\Steam"),
                                                    pathlib.Path(r"E:\Games\SteamLibrary")])

    def test_both_data_layouts(self):
        with tempfile.TemporaryDirectory() as d:
            windows = make_game(pathlib.Path(d) / "a", "CoQ_Data")
            mac = make_game(pathlib.Path(d) / "b", "CoQ.app/Contents/Resources/Data")
            self.assertEqual(game.data_dir(windows), windows / "CoQ_Data")
            self.assertEqual(game.data_dir(mac), mac / "CoQ.app/Contents/Resources/Data")
            self.assertIsNone(game.data_dir(pathlib.Path(d) / "c"))

    def test_the_game_in_another_steam_library_on_macos(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"QUD_GAME_DIR": ""}):
            del os.environ["QUD_GAME_DIR"]
            home = pathlib.Path(d)
            steam = home / "Library" / "Application Support" / "Steam"
            library = home / "Volumes" / "Games"
            (steam / "steamapps").mkdir(parents=True)
            (steam / "steamapps" / "libraryfolders.vdf").write_text(
                '"libraryfolders"\n{\n\t"0"\n\t{\n\t\t"path"\t\t"%s"\n\t}\n}\n' % library.as_posix(), encoding="utf-8")
            coq = make_game(library / "steamapps" / "common" / "Caves of Qud", "CoQ.app/Contents/Resources/Data")
            self.assertEqual(game.find_game("darwin", home), coq)

    def test_the_game_on_linux_and_no_game(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"QUD_GAME_DIR": ""}):
            del os.environ["QUD_GAME_DIR"]
            home = pathlib.Path(d)
            self.assertIsNone(game.find_game("linux", home))
            coq = make_game(home / ".local" / "share" / "Steam" / "steamapps" / "common" / "Caves of Qud", "CoQ_Data")
            self.assertEqual(game.find_game("linux", home), coq)

    def test_qud_game_dir_wins(self):
        with mock.patch.dict(os.environ, {"QUD_GAME_DIR": "/somewhere/Caves of Qud"}):
            self.assertEqual(game.find_game("linux", pathlib.Path("/nohome")), pathlib.Path("/somewhere/Caves of Qud"))

    def test_mods_folders(self):
        home = pathlib.Path("/Users/q")
        self.assertEqual(game.mods_dir("darwin", home),
                         home / "Library" / "Application Support" / "com.FreeholdGames.CavesOfQud" / "Mods")
        self.assertEqual(game.mods_dir("linux", home), home / ".config" / "unity3d" / "Freehold Games" / "CavesOfQud" / "Mods")
        with mock.patch.dict(os.environ, {"USERPROFILE": r"C:\Users\q"}):
            self.assertEqual(game.mods_dir("win32", home),
                             pathlib.Path(r"C:\Users\q") / "AppData" / "LocalLow" / "Freehold Games" / "CavesOfQud" / "Mods")


class Link(unittest.TestCase):
    def setUp(self):
        # the messages are Ukrainian, and a test runner's stdout may not take them (cp1252 on Windows)
        quiet = mock.patch("sys.stdout", io.StringIO())
        quiet.start()
        self.addCleanup(quiet.stop)   # cleanups run after tearDown, which prints too
        self.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(self.tmp.name)
        self.mod = root / "repo" / "mod"
        (self.mod / "Language").mkdir(parents=True)
        (self.mod / "manifest.json").write_text("{}", encoding="utf-8")
        self.mods = root / "Mods"

    def tearDown(self):
        path = self.mods / install.NAME
        if install.link_target(path) is not None:
            install.unlink(self.mods)   # never let the cleanup follow the link into the mod
        self.tmp.cleanup()

    def test_link_relink_and_unlink(self):
        path = install.link(self.mod, self.mods)
        self.assertTrue(install.same_folder(path, self.mod))
        self.assertTrue((path / "manifest.json").exists())
        install.link(self.mod, self.mods)   # already there: nothing to do
        install.unlink(self.mods)
        self.assertFalse(os.path.lexists(path))
        self.assertTrue((self.mod / "manifest.json").exists(), "unlinking must not touch the mod itself")

    def test_a_real_folder_is_never_replaced_or_removed(self):
        (self.mods / install.NAME).mkdir(parents=True)
        (self.mods / install.NAME / "old.xml").write_text("x", encoding="utf-8")
        with self.assertRaises(SystemExit):
            install.link(self.mod, self.mods)
        with self.assertRaises(SystemExit):
            install.unlink(self.mods)
        self.assertTrue((self.mods / install.NAME / "old.xml").exists())

    def test_a_link_elsewhere_is_left_alone(self):
        other = pathlib.Path(self.tmp.name) / "other"
        other.mkdir()
        install.link(other, self.mods)
        with self.assertRaises(SystemExit):
            install.link(self.mod, self.mods)
        self.assertTrue(install.same_folder(self.mods / install.NAME, other))


class TranslatedBuild(unittest.TestCase):
    def test_the_store_header_names_the_build(self):
        with tempfile.TemporaryDirectory() as d:
            store = pathlib.Path(d)
            (store / "A.jsonl").write_text(json.dumps({"build": "2.0.212.31", "lang": "uk"}) + "\n", encoding="utf-8")
            self.assertEqual(install.translated_build(store), "2.0.212.31")


if __name__ == "__main__":
    unittest.main()
