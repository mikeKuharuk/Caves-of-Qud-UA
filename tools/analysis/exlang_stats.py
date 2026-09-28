"""Statistics over the official ExampleLanguage string tables (lang-experimental branch).

Every translatable unit in those files is marked with a leading '▶' — either an attribute value
or an element's text. This script counts units and English words per file and, given two git
tags of the gnarf/caves-of-qud-example-language mirror, reports how many units were added,
removed or changed between builds (a measure of upstream churn).

Usage:
  py tools/analysis/exlang_stats.py [--repo work/example-language] [--tag 212.31]
  py tools/analysis/exlang_stats.py --diff 212.17 212.31
"""
import argparse
import collections
import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

MARK = "▶"  # ▶
WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
MARKUP = re.compile(r"\{\{[^|}]*\||\}\}|&[A-Za-z&]|\^[A-Za-z]|=[a-zA-Z0-9_.:'|\[\]-]+=")
IDENT_ATTRS = ("Name", "ID", "Context", "name", "Code")


def words(s: str) -> int:
    return len(WORD.findall(MARKUP.sub(" ", s)))


def units(xml_text: str, fname: str):
    """Yield (key, english) for every ▶-marked unit in one example file."""
    root = ET.fromstring(xml_text)
    path = []

    def ident(el):
        for a in IDENT_ATTRS:
            if el.get(a) is not None:
                return f"{el.tag}[{a}={el.get(a)}]"
        return el.tag

    def walk(el, parents):
        here = parents + [ident(el)]
        # siblings with identical identity get an ordinal to keep keys unique
        for k, v in el.attrib.items():
            if v.startswith(MARK):
                yield ("/".join(here) + "@" + k, v[1:])
        text = (el.text or "").strip()
        if text.startswith(MARK):
            yield ("/".join(here) + "#text", text[1:])
        seen = collections.Counter()
        for child in el:
            cid = ident(child)
            seen[cid] += 1
            child_parents = here if seen[cid] == 1 else here + [f"#{seen[cid]}"]
            yield from walk(child, child_parents)

    yield from ((f"{fname}:{k}", v) for k, v in walk(root, path))


def load_tag(repo: pathlib.Path, tag: str | None):
    """Return {filename: xml_text} for a tag (or the working tree when tag is None)."""
    out = {}
    if tag is None:
        for p in sorted((repo / "ExampleLanguage").glob("*.xml")):
            out[p.name] = p.read_text(encoding="utf-8-sig")
        return out
    names = subprocess.run(["git", "-C", str(repo), "ls-tree", "--name-only", f"{tag}:ExampleLanguage"],
                           capture_output=True, text=True, check=True).stdout.split()
    for n in names:
        if n.endswith(".xml"):
            blob = subprocess.run(["git", "-C", str(repo), "show", f"{tag}:ExampleLanguage/{n}"],
                                  capture_output=True, check=True).stdout
            out[n] = blob.decode("utf-8-sig")
    return out


def collect(files: dict):
    per_file = {}
    allunits = {}
    for name, text in files.items():
        try:
            us = list(units(text, name))
        except ET.ParseError as e:
            print(f"!! {name}: {e}", file=sys.stderr)
            continue
        per_file[name] = (len(us), sum(words(v) for _, v in us))
        allunits.update(us)
    return per_file, allunits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="work/example-language")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--diff", nargs=2, metavar=("OLD", "NEW"))
    a = ap.parse_args()
    repo = pathlib.Path(a.repo)

    if a.diff:
        _, old = collect(load_tag(repo, a.diff[0]))
        _, new = collect(load_tag(repo, a.diff[1]))
        added = new.keys() - old.keys()
        removed = old.keys() - new.keys()
        changed = [k for k in new.keys() & old.keys() if new[k] != old[k]]
        by_file = collections.Counter(k.split(":", 1)[0] for k in added)
        print(f"{a.diff[0]} -> {a.diff[1]}: units {len(old)} -> {len(new)}; "
              f"added {len(added)} ({sum(words(new[k]) for k in added)} words), "
              f"removed {len(removed)}, changed {len(changed)}")
        for f, c in by_file.most_common(15):
            print(f"  +{c:6}  {f}")
        return

    per_file, allu = collect(load_tag(repo, a.tag))
    total_u = total_w = 0
    print(f"{'file':40} {'units':>7} {'words':>8}")
    for name, (u, w) in sorted(per_file.items(), key=lambda kv: -kv[1][1]):
        total_u += u
        total_w += w
        print(f"{name:40} {u:>7} {w:>8}")
    print(f"{'TOTAL':40} {total_u:>7} {total_w:>8}")
    distinct = len(set(allu.values()))
    print(f"distinct English texts: {distinct}")


if __name__ == "__main__":
    main()
