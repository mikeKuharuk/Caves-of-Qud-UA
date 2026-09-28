"""Translation workflow for Caves of Qud (Ukrainian).

  py tools/qud.py sync     [--source DIR | --tag 212.31]   ExampleLanguage → translations/uk/*.po
  py tools/qud.py build    [--source DIR | --tag 212.31]   translations/uk/*.po → mod/Language/*.uk.xml
  py tools/qud.py validate [--errors-only]                 markup and typography checks
  py tools/qud.py stats                                    progress per file
  py tools/qud.py import FILE.uk.xml ... [--source ...]    fill PO from existing translated XML

The source of the English string tables defaults to the installed game's
CoQ_Data/StreamingAssets/Base/ExampleLanguage (set QUD_GAME_DIR to override).
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from qudtr import commands, sources  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def with_source(p):
        g = p.add_mutually_exclusive_group()
        g.add_argument("--source", help="folder with *.example.xml (default: the installed game)")
        g.add_argument("--tag", help="tag of the work/example-language mirror, e.g. 212.31")
        return p

    p_sync = with_source(sub.add_parser("sync", help="update PO catalogs from the English string tables"))
    p_sync.add_argument("--dry-run", action="store_true")
    p_build = with_source(sub.add_parser("build", help="generate mod/Language/*.uk.xml"))
    p_build.add_argument("--include-fuzzy", action="store_true", help="also use fuzzy translations (for testing)")
    p_build.add_argument("--force", action="store_true", help="overwrite hand-written output files")
    p_val = sub.add_parser("validate", help="check translations")
    p_val.add_argument("--errors-only", action="store_true")
    sub.add_parser("stats", help="translation progress")
    p_imp = with_source(sub.add_parser("import", help="import existing *.uk.xml into PO"))
    p_imp.add_argument("files", nargs="+", type=pathlib.Path)
    p_imp.add_argument("--overwrite", action="store_true")

    a = ap.parse_args(argv)
    if a.cmd == "sync":
        files, desc = sources.load(a.source, a.tag)
        print(f"source: {desc}")
        total = commands.cmd_sync(files, dry_run=a.dry_run)
        print(f"total: kept {total['kept']}, revived {total['revived']}, new {total['new']}, "
              f"fuzzy {total['fuzzy']}, obsoleted {total['obsoleted']}, duplicates skipped {total['duplicate']}")
        return 0
    if a.cmd == "build":
        files, desc = sources.load(a.source, a.tag)
        print(f"source: {desc}")
        return 1 if commands.cmd_build(files, include_fuzzy=a.include_fuzzy, force=a.force) else 0
    if a.cmd == "validate":
        errors, _ = commands.cmd_validate(show_warnings=not a.errors_only)
        return 1 if errors else 0
    if a.cmd == "stats":
        commands.cmd_stats()
        return 0
    if a.cmd == "import":
        files, desc = sources.load(a.source, a.tag)
        print(f"source: {desc}")
        commands.cmd_import(files, a.files, overwrite=a.overwrite)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
