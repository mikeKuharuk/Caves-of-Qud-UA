"""Where each HistorySpice list is used, and in what surroundings: the map for translating the world history.

  py tools/spice_map.py [--out work/history-map]

A fragment's Ukrainian form depends on where the game puts it: after a preposition, before a noun, as a
subject. The map lists, for every list under "spice", each reference with the text around it:

- templates in the string tables (Strings.po msgids: HistoricEvent, gospels, murals, villages…);
- other fragments (a fragment may pull in another one);
- the game's code (ExpandString("…<spice.x>…") and literal paths). Text glued in code is English and not in
  any catalog; the map marks those references so the design can plan around them.

References: =spice:PATH=, <spice.PATH>, =^:REL= (relative to the list's parent node), =spice.set:PATH:$var=,
=spice.entity:PROP=. Path segments that are variables ($element, $terrain) become '*'. Output: one text file per
top-level branch plus index.txt with counts; work/ is local (the English text stays out of git).
"""
from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from qudtr import po, spice  # noqa: E402
from qudtr.sources import DEFAULT_GAME_DIR, REPO  # noqa: E402

SPICE_FILE = DEFAULT_GAME_DIR / "CoQ_Data" / "StreamingAssets" / "Base" / "HistorySpice.jsonc"
CODE_DIR = REPO / "work" / "decompiled" / "2.0.212.31" / "Assembly-CSharp"
REF = re.compile(r"=spice:([^=|\s]+)|<spice\.([^<>|\s]+)>|=spice\.set:([^:=\s]+):|=\^:([^=|\s]+)")
CODE_PATH = re.compile(r"\"spice\.([A-Za-z0-9_.$!@]+)\"")
VALID_PATH = re.compile(r"[A-Za-z0-9_' -]+(?:\.(?:[A-Za-z0-9_' -]+|\*))*")


def normalize(path: str) -> str:
    parts = []
    for seg in path.split("."):
        if seg.startswith("!") or seg in ("capitalize", "pluralize", "article"):
            break
        parts.append("*" if seg.startswith("$") or "@" in seg else seg)
    return ".".join(parts)


def around(text: str, start: int, end: int, width: int = 60) -> str:
    return (text[max(0, start - width):start] + "⟦" + text[start:end] + "⟧" + text[end:end + width]).replace("\n", " ⏎ ")


def lists(root: dict) -> set[str]:
    out = set()

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, path + [k])
        elif isinstance(node, list):
            out.add(".".join(path))
    walk(root, [])
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "work" / "history-map"))
    a = ap.parse_args(argv)
    root = spice.load(SPICE_FILE.read_text(encoding="utf-8-sig"))["spice"]
    known = lists(root)
    uses: dict[str, list[tuple[str, str]]] = collections.defaultdict(list)

    def record(path: str, where: str, text: str, m: re.Match):
        key = normalize(path)
        if VALID_PATH.fullmatch(key):  # code builds some paths by concatenation: "<spice." + x
            uses[key].append((where, around(text, m.start(), m.end())))

    # 1. templates in the string tables
    for f in sorted((REPO / "work" / "po" / "uk").glob("*.po")):
        if f.name == "HistorySpice.po":
            continue
        for e in po.load(f).entries:
            if e.obsolete:
                continue
            for m in REF.finditer(e.msgid):
                path = next(g for g in m.groups() if g)
                if m.group(4):  # relative: no branch known outside spice
                    continue
                record(path, f"{f.name} [{e.msgctxt}]", e.msgid, m)
    # 2. fragments that pull in other fragments
    for path_tuple, value in spice.leaves(root):
        for m in REF.finditer(value):
            path = next(g for g in m.groups() if g)
            if m.group(4):  # =^:x= is relative to the list's parent node
                base = spice.relative_base(path_tuple)
                path = f"{base}.{path}" if base else path
            record(path, "spice." + ".".join(path_tuple), value, m)
    # 3. the game's code
    if CODE_DIR.exists():
        for f in CODE_DIR.rglob("*.cs"):
            text = f.read_text(encoding="utf-8", errors="replace")
            if "spice" not in text:
                continue
            rel = f.relative_to(CODE_DIR).as_posix()
            for m in REF.finditer(text):
                path = next(g for g in m.groups() if g)
                if not m.group(4):
                    record(path, "CODE " + rel, text, m)
            for m in CODE_PATH.finditer(text):
                record(m.group(1), "CODE " + rel, text, m)

    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    by_branch: dict[str, list[str]] = collections.defaultdict(list)
    for path in sorted(known | set(uses)):
        by_branch[path.split(".")[0]].append(path)
    index = []
    for branch, paths in sorted(by_branch.items()):
        lines = []
        for path in paths:
            refs = uses.get(path, [])
            # a reference to a prefix (spice.elements.* → elements.glass.materials) counts for the lists under it
            wild = [p for p in uses if "*" in p and re.fullmatch(p.replace(".", r"\.").replace("*", r"[^.]+"), path)]
            refs = refs + [r for p in wild for r in uses[p]]
            code = sum(1 for w, _ in refs if w.startswith("CODE"))
            tag = "" if path in known else "  (not a list: a branch or an unknown path)"
            lines.append(f"## {path}  — {len(refs)} use(s), {code} in code{tag}")
            node = root
            for seg in path.split("."):
                node = node.get(seg) if isinstance(node, dict) else None
            if isinstance(node, list):
                sample = [v for v in node if isinstance(v, str)][:6]
                lines.append("   values: " + " | ".join(sample)[:300])
            for where, ctx in refs[:12]:
                lines.append(f"   {where}: {ctx}")
            if len(refs) > 12:
                lines.append(f"   … {len(refs) - 12} more")
            lines.append("")
            index.append((path, len(refs), code, path in known))
        (out / f"{branch}.txt").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    unused = sum(1 for p, n, _, k in index if k and n == 0)
    in_code = sum(1 for p, n, c, _ in index if c)
    with (out / "index.txt").open("w", encoding="utf-8", newline="\n") as f:
        f.write(f"{len(known)} lists; {unused} never referenced; {in_code} paths referenced from code\n\n")
        for path, n, c, k in sorted(index, key=lambda t: -t[1]):
            f.write(f"{n:5} {c:4}  {path}{'' if k else '  (not a list)'}\n")
    print(f"{len(known)} lists, {unused} never referenced, {in_code} referenced from code → {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
