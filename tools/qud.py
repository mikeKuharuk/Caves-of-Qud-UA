"""Translation workflow for Caves of Qud (Ukrainian).

  py tools/qud.py sync     [--from-store] [--source DIR | --tag 212.31]
        game string tables + translations/uk/*.jsonl → work/po/uk/*.po (and back to the store)
  py tools/qud.py save     work/po/uk/*.po → translations/uk/*.jsonl (after editing the PO files)
  py tools/qud.py build    [--include-fuzzy]   → mod/Language/*.uk.xml
  py tools/qud.py validate [--errors-only]     markup and typography checks
  py tools/qud.py stats                        progress per file
  py tools/qud.py import FILE.uk.xml ...       fill translations from existing translated XML
  py tools/qud.py worksheet PO [--ctx RE]      untranslated units → work/batch/*.jsonl
  py tools/qud.py check-worksheet FILE ...     check a filled-in worksheet (no PO access)
  py tools/qud.py apply FILE ...               filled-in worksheets → PO catalogs

translations/uk/*.jsonl (in git) holds only our Ukrainian text; the English lives in the local
PO working copies, rebuilt from the installed game. The English string tables default to the
installed game's CoQ_Data/StreamingAssets/Base/ExampleLanguage (set QUD_GAME_DIR to override).
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

    p_sync = with_source(sub.add_parser("sync", help="update the local PO catalogs and the store"))
    p_sync.add_argument("--from-store", action="store_true",
                        help="on conflicts take the store's translation (e.g. after pulling others' work)")
    with_source(sub.add_parser("save", help="write edits from the local PO catalogs to the store"))
    p_build = with_source(sub.add_parser("build", help="generate mod/Language/*.uk.xml"))
    p_build.add_argument("--include-fuzzy", action="store_true", help="also use fuzzy translations")
    p_build.add_argument("--force", action="store_true", help="overwrite hand-written output files")
    p_val = with_source(sub.add_parser("validate", help="check translations"))
    p_val.add_argument("--errors-only", action="store_true")
    with_source(sub.add_parser("stats", help="translation progress"))
    p_imp = with_source(sub.add_parser("import", help="import existing *.uk.xml"))
    p_imp.add_argument("files", nargs="+", type=pathlib.Path)
    p_imp.add_argument("--overwrite", action="store_true")
    p_ws = with_source(sub.add_parser("worksheet", help="write a JSONL worksheet of units to translate"))
    p_ws.add_argument("po", help="catalog name, e.g. Options.po")
    p_ws.add_argument("--ctx", help="regex on the unit key (msgctxt)")
    p_ws.add_argument("--all", action="store_true", help="include already translated units")
    p_ws.add_argument("--limit", type=int)
    p_ws.add_argument("--out", type=pathlib.Path)
    p_ap = with_source(sub.add_parser("apply", help="apply filled-in worksheets"))
    p_ap.add_argument("worksheets", nargs="+", type=pathlib.Path)
    p_cw = sub.add_parser("check-worksheet", help="check filled-in worksheets without applying them")
    p_cw.add_argument("worksheets", nargs="+", type=pathlib.Path)

    a = ap.parse_args(argv)
    if a.cmd == "check-worksheet":   # needs no game files and never touches the catalogs
        return 1 if commands.cmd_check_worksheet(a.worksheets) else 0
    files, desc = sources.load(a.source, a.tag)
    print(f"source: {desc}")
    if a.cmd == "sync":
        t = commands.cmd_sync(files, prefer_store=a.from_store)
        print(f"total: kept {t['kept']}, revived {t['revived']}, new {t['new']}, fuzzy {t['fuzzy']}, "
              f"obsoleted {t['obsoleted']}, from store {t['from-store']}, moved {t['moved']}, "
              f"local wins {t['local-wins']}, store orphans {t['orphans']}")
        return 0
    if a.cmd == "save":
        print(f"saved {commands.cmd_save(files)} translation record(s)")
        return 0
    if a.cmd == "build":
        return 1 if commands.cmd_build(files, include_fuzzy=a.include_fuzzy, force=a.force) else 0
    if a.cmd == "validate":
        errors, _ = commands.cmd_validate(files, show_warnings=not a.errors_only)
        return 1 if errors else 0
    if a.cmd == "stats":
        commands.cmd_stats(files)
        return 0
    if a.cmd == "import":
        commands.cmd_import(files, a.files, overwrite=a.overwrite)
        return 0
    if a.cmd == "worksheet":
        commands.cmd_worksheet(files, a.po, a.out, a.ctx, a.all, a.limit)
        return 0
    if a.cmd == "apply":
        return 1 if commands.cmd_apply(files, a.worksheets) else 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
