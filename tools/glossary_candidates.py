"""Candidate terms for the glossary, ranked by how often they occur in the game's text.

Reads the local PO working copies (work/po/uk/*.po, built from the installed game) and writes
work/glossary/candidates.tsv (local only: it quotes the game's English). Sources of candidates:
faction, genotype, subtype, mutation, skill and zone display names, creature display names, and
capitalised multi-word names that recur in dialogue, books and descriptions.

  py tools/glossary_candidates.py [--min 3]
"""
import argparse
import collections
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from qudtr import po  # noqa: E402
from qudtr.commands import PO_DIR  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "work" / "glossary" / "candidates.tsv"
MARKUP = re.compile(r"\{\{[^|}]*\||\}\}|=[A-Za-z_][^=\s]*=|&[A-Za-z]|\^[A-Za-z]|▶")
PROPER = re.compile(r"\b(?:[A-Z][a-z'’]+(?:[- ](?:of|the|de|al|el|[A-Z][a-z'’]+))*)")

SOURCES = [  # (catalog, regex on msgctxt, category)
    ("Factions.po", r"@DisplayName$", "faction"),
    ("ChiliadFactions.po", r"@DisplayName$", "faction"),
    ("Genotypes.po", r"^genotype\[[^/]*@DisplayName$", "genotype"),
    ("Subtypes.po", r"@(DisplayName|ChargenTitle|SingularTitle)$", "subtype"),
    ("Mutations.po", r"mutation\[[^/]*\]@DisplayName$", "mutation"),
    ("HiddenMutations.po", r"mutation\[[^/]*\]@DisplayName$", "mutation"),
    ("Skills.po", r"^skill\[[^/]*\]@DisplayName$", "skill"),
    ("Skills.po", r"/power\[[^/]*\]@DisplayName$", "power"),
    ("Worlds.po", r"@(Name|NameContext|DisplayName)$", "place"),
    ("Creatures.po", r"part\[Render\]@DisplayName$", "creature"),
]


def clean(s: str) -> str:
    return MARKUP.sub(" ", s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=3, help="minimum occurrences in the text")
    a = ap.parse_args()

    cats = {p.name: po.load(p) for p in sorted(PO_DIR.glob("*.po"))}
    corpus = "\n".join(clean(e.msgid) for c in cats.values() for e in c.entries if not e.obsolete)
    corpus_lower = corpus.lower()

    candidates: dict[str, str] = {}
    for name, rx, category in SOURCES:
        r = re.compile(rx)
        for e in cats.get(name, po.Catalog()).entries:
            if not e.obsolete and r.search(e.msgctxt or ""):
                term = clean(e.msgid).strip()
                if term and len(term) < 60:
                    candidates.setdefault(term, category)
    # recurring capitalised names in prose
    for m in collections.Counter(PROPER.findall(corpus)).most_common(3000):
        term, n = m
        if n >= a.min and len(term) > 3 and term not in candidates and " " in term:
            candidates.setdefault(term, "name")

    rows = []
    for term, category in candidates.items():
        n = len(re.findall(r"(?<![\w-])" + re.escape(term.lower()) + r"(?![\w-])", corpus_lower))
        if n >= a.min or category in ("faction", "genotype", "subtype"):
            rows.append((n, category, term))
    rows.sort(key=lambda r: (-r[0], r[2]))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("count\tcategory\tterm\n")
        for n, category, term in rows:
            f.write(f"{n}\t{category}\t{term}\n")
    by_cat = collections.Counter(c for _, c, _ in rows)
    print(f"{OUT}: {len(rows)} candidates {dict(by_cat)}")


if __name__ == "__main__":
    main()
