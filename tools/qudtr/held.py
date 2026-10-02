"""Units left untranslated on purpose: translations/<lang>/held.tsv.

Some units must stay English, or wait until the game's code is patched (docs/plan.md, the Harmony stage):
  keep — the game reads the value as an identifier, or it stays English by decision: words the player types
         to confirm, action labels whose first letter is the hotkey (D12), the Ezra Pound quote
  code — the code wraps the value in English grammar (DidX verbs, articles, adjunct nouns); it waits for a patch
The empty translation of such a unit is deliberate, and `stats` counts it apart from the work still to do.

One line per unit: catalog <TAB> unit key (the store's hash k) <TAB> keep|code <TAB> reason. Lines starting with #
are comments. Units are named by their hash, so the file holds no English (see store.py).
"""
from __future__ import annotations

import dataclasses
import pathlib

STATUSES = ("keep", "code")


@dataclasses.dataclass(frozen=True)
class Held:
    catalog: str
    key: str
    status: str
    reason: str


def path(lang: str = "uk") -> pathlib.Path:
    from .sources import REPO
    return REPO / "translations" / lang / "held.tsv"


def parse(text: str) -> tuple[dict[tuple[str, str], Held], list[str]]:
    """(catalog, key) → Held, and the problems of malformed lines."""
    held, problems = {}, []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 4 or parts[2] not in STATUSES or not parts[3].strip():
            problems.append(f"held.tsv:{n}: write «catalog<TAB>key<TAB>keep|code<TAB>reason»")
            continue
        h = Held(*[p.strip() for p in parts])
        if (h.catalog, h.key) in held:
            problems.append(f"held.tsv:{n}: {h.catalog} {h.key} is listed twice")
        held[(h.catalog, h.key)] = h
    return held, problems


def load(lang: str = "uk") -> tuple[dict[tuple[str, str], Held], list[str]]:
    p = path(lang)
    return parse(p.read_text(encoding="utf-8")) if p.exists() else ({}, [])
