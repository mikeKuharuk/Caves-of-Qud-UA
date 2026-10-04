"""Collect string-table and code-table misses from Player.log files.

With the game option "Log string table lookup misses as errors to Player.log"
(OptionDebugStringTableMisses) on, every lookup that finds no translation is logged as

  String table miss - Lang uk - Context="…" ID="…"

and the mod's own code tables (mod/Patches/CodeText) log, once each, the English they found no key for:

  [uk-miss] Text: You can't do that here.

This script gathers both from one or more logs, de-duplicates them, and prints a summary (by context prefix, and
by code table), or writes them as TSV (--tsv) so they can be prioritised for translation.

Usage:
  py tools/misses.py [LOG ...] [--tsv out.tsv] [--top 40]
Without LOG arguments it reads the game's current Player.log.
"""
import argparse
import collections
import html
import os
import pathlib
import re

DEFAULT_LOG = pathlib.Path(os.environ.get("USERPROFILE", "~")) / "AppData/LocalLow/Freehold Games/CavesOfQud/Player.log"
MISS = re.compile(r'String table miss - Lang (?P<lang>\S+) - (?:Context="(?P<ctx>(?:[^"]|&quot;)*)" )?ID="(?P<id>(?:[^"]|&quot;)*)"')
CODE_MISS = re.compile(r"\[uk-miss\] (?P<table>[\w.]+): (?P<text>.*)$")


def read_misses(paths):
    seen = {}
    for p in paths:
        for line in pathlib.Path(p).read_text(encoding="utf-8", errors="replace").splitlines():
            m = MISS.search(line)
            if m:
                key = (html.unescape(m["ctx"] or ""), html.unescape(m["id"]))
                seen.setdefault(key, m["lang"])
    return seen


def read_code_misses(paths):
    """(table, text) for each [uk-miss] line, in order: English a code table had no key for."""
    seen = {}
    for p in paths:
        for line in pathlib.Path(p).read_text(encoding="utf-8", errors="replace").splitlines():
            m = CODE_MISS.search(line)
            if m:
                seen.setdefault((m["table"], m["text"].rstrip()), None)
    return list(seen)


def prefix(ctx: str) -> str:
    """Group key: the first word(s) of the context, e.g. 'Conversation Barathrum.X' -> 'Conversation'."""
    if not ctx:
        return "<no context>"
    return ctx.split(" ")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("logs", nargs="*", default=[DEFAULT_LOG])
    ap.add_argument("--tsv", help="write all misses as Context<TAB>ID (a code table's: [Table]<TAB>text) to this file")
    ap.add_argument("--top", type=int, default=40)
    a = ap.parse_args()
    misses = read_misses(a.logs)
    groups = collections.Counter(prefix(c) for c, _ in misses)
    print(f"distinct misses: {len(misses)}")
    for g, n in groups.most_common(a.top):
        print(f"{n:6}  {g}")
    code = read_code_misses(a.logs)
    print(f"distinct code-table misses: {len(code)}")
    for table, n in collections.Counter(t for t, _ in code).most_common():
        print(f"{n:6}  Code.{table}")
    if a.tsv:
        with open(a.tsv, "w", encoding="utf-8", newline="\n") as f:
            for (c, i) in sorted(misses):
                f.write(c.replace("\t", " ") + "\t" + i.replace("\t", " ").replace("\n", "\\n") + "\n")
            for (t, text) in sorted(code):
                f.write(f"[{t}]\t" + text.replace("\t", " ") + "\n")
        print(f"written {a.tsv}")


if __name__ == "__main__":
    main()
