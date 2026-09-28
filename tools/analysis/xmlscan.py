"""Inventory of translatable-looking text in Caves of Qud's StreamingAssets/Base.

For every XML file: which (element, attribute) pairs and which element text nodes carry
prose, with counts of strings and words. JSON/TXT files get a rough word count.
"""
import collections
import os
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

GAME_DIR = pathlib.Path(os.environ.get("QUD_GAME_DIR", r"D:\Steam\steamapps\common\Caves of Qud"))
BASE = GAME_DIR / "CoQ_Data" / "StreamingAssets" / "Base"
WORD = re.compile(r"[A-Za-z][A-Za-z'\-]*")
MARKUP = re.compile(r"\{\{[^|}]*\||\}\}|&[A-Za-z]|\^[A-Za-z]|=[a-zA-Z0-9_.:'|]+=")


def words(s: str) -> int:
    return len(WORD.findall(MARKUP.sub(" ", s)))


def looks_like_text(s: str) -> bool:
    s2 = MARKUP.sub(" ", s)
    # at least one real word of 2+ letters and either a space or a capitalised word
    return bool(re.search(r"[A-Za-z]{2,}", s2)) and (" " in s2.strip() or re.match(r"^[A-Z][a-z]", s2.strip()) is not None)


CHARREF = re.compile(r"&#(x[0-9a-fA-F]+|[0-9]+);")


def _fix_charref(m: re.Match) -> str:
    # The game writes CP437 glyph indices as char refs (&#x7; = bullet); XML 1.0 forbids
    # most control chars, so map them to the Private Use Area to keep a strict parser happy.
    v = m.group(1)
    n = int(v[1:], 16) if v[0] == "x" else int(v)
    if n < 32 and n not in (9, 10, 13):
        return chr(0xE000 + n)
    return m.group(0)


def parse_lenient(path: pathlib.Path) -> ET.ElementTree:
    text = path.read_text(encoding="utf-8-sig")
    return ET.ElementTree(ET.fromstring(CHARREF.sub(_fix_charref, text)))


def scan_xml(path: pathlib.Path):
    stats = collections.defaultdict(lambda: [0, 0])  # key -> [strings, words]
    samples = {}
    try:
        tree = parse_lenient(path)
    except ET.ParseError as e:
        print(f"!! parse error {path.name}: {e}", file=sys.stderr)
        return stats, samples
    for el in tree.iter():
        tag = el.tag
        # attributes: key by element tag, the 'Name' attr for <part>/<tag>, and attribute name
        ctx = tag
        if tag in ("part", "tag", "stat", "property", "xtag", "mutation", "skill", "intproperty"):
            ctx = f"{tag}[{el.get('Name', '?')}]"
        for k, v in el.attrib.items():
            if looks_like_text(v):
                key = f"@{ctx}.{k}"
                stats[key][0] += 1
                stats[key][1] += words(v)
                samples.setdefault(key, v[:100])
        text = (el.text or "").strip()
        if text and looks_like_text(text):
            key = f"<{ctx}>text"
            stats[key][0] += 1
            stats[key][1] += words(text)
            samples.setdefault(key, text[:100])
    return stats, samples


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    per_file = []
    detail = {}
    for path in sorted(BASE.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(BASE).as_posix()
        if only and only not in rel:
            continue
        if path.suffix.lower() == ".xml":
            stats, samples = scan_xml(path)
            total_words = sum(w for _, w in stats.values())
            total_strings = sum(n for n, _ in stats.values())
            per_file.append((rel, total_strings, total_words))
            detail[rel] = (stats, samples)
        elif path.suffix.lower() in (".json", ".txt") and path.stat().st_size < 5_000_000:
            text = path.read_text(encoding="utf-8", errors="replace")
            per_file.append((rel, None, words(text)))
    per_file.sort(key=lambda r: -r[2])
    grand = 0
    print(f"{'file':55} {'strings':>8} {'words':>8}")
    for rel, n, w in per_file:
        grand += w
        print(f"{rel:55} {'' if n is None else n:>8} {w:>8}")
    print(f"{'TOTAL (raw, incl. corpora/json)':55} {'':>8} {grand:>8}")
    if only:
        for rel, (stats, samples) in detail.items():
            print(f"\n=== {rel} ===")
            for key, (n, w) in sorted(stats.items(), key=lambda kv: -kv[1][1])[:60]:
                print(f"{w:>7}w {n:>6}x  {key:55} | {samples[key]!r}")


if __name__ == "__main__":
    main()
