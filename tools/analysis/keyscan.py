"""Aggregate text-bearing (element, attribute) keys across all Base XML files.

Prints keys whose values look like prose (contain a space between words), aggregated over
all files, so an allowlist of translatable fields can be drawn up by hand.
"""
import collections
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from xmlscan import BASE, parse_lenient, words, MARKUP  # noqa: E402

SKIP_VALUE = re.compile(r"^(Sounds/|Assets_|Items/|Creatures/|Terrain/|Tiles|Abilities/|Mutations/|Text/|UI/|sw_|.*\.(bmp|png|wav|ogg))", re.I)


def is_prose(v: str) -> bool:
    s = MARKUP.sub(" ", v).strip()
    return bool(re.search(r"[A-Za-z]{2,} [A-Za-z]{2,}", s)) and not SKIP_VALUE.match(v)


agg = collections.defaultdict(lambda: [0, 0, collections.Counter(), ""])
for path in sorted(BASE.rglob("*.xml")):
    rel = path.relative_to(BASE).as_posix()
    tree = parse_lenient(path)
    for el in tree.iter():
        ctx = el.tag
        if el.tag in ("part", "tag", "stat", "property", "xtag", "intproperty", "mutation", "skill"):
            ctx = f"{el.tag}[{el.get('Name', '?')}]"
        elif el.tag.startswith("xtag"):
            ctx = el.tag
        for k, v in el.attrib.items():
            if is_prose(v):
                a = agg[f"@{ctx}.{k}"]
                a[0] += 1; a[1] += words(v); a[2][rel] += 1; a[3] = a[3] or v[:90]
        t = (el.text or "").strip()
        if t and is_prose(t):
            a = agg[f"<{ctx}>"]
            a[0] += 1; a[1] += words(t); a[2][rel] += 1; a[3] = a[3] or t[:90]

min_words = int(sys.argv[1]) if len(sys.argv) > 1 else 40
total = 0
for key, (n, w, files, sample) in sorted(agg.items(), key=lambda kv: -kv[1][1]):
    if w < min_words:
        continue
    total += w
    top = ",".join(f"{f.split('/')[-1].removesuffix('.xml')}:{c}" for f, c in files.most_common(3))
    print(f"{w:>7}w {n:>6}x  {key:52} [{top}]\n                   | {sample!r}")
print(f"TOTAL words in listed keys: {total}")
