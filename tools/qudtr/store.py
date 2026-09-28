"""The translation store that goes into git: our Ukrainian text, and no English.

Caves of Qud's text belongs to Freehold Games, so the repository keeps only what we write.
Each unit is identified by hashes instead of its English text:

  k  hash(msgctxt, msgid)   exact identity of the unit (a <string>'s ID is its English text)
  p  hash(msgctxt)          its place: the same element/attribute, or the same Context
  s  hash(msgid)            the English it was translated from, to notice changes

The full PO catalogs (with the English msgids) are a local working copy under work/po/,
rebuilt from the installed game's ExampleLanguage files plus this store.

File format: JSON Lines, UTF-8. The first line is a header; every other line is one record:
  {"k": "...", "p": "...", "s": "...", "t": "переклад", "f": 1, "o": 1, "c": ["comment"]}
where "f" marks fuzzy, "o" obsolete (the unit is gone from the current game build), and "c"
holds translator comments. Absent keys mean false/empty.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib

from . import po

FORMAT = "qud-ua-store/1"


def _h(text: str, n: int) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def keys(msgctxt: str | None, msgid: str) -> tuple[str, str, str]:
    ctx = "\x00" if msgctxt is None else msgctxt
    return _h(ctx + "\x04" + msgid, 20), _h("\x05" + ctx, 16), _h(msgid, 12)


def record(e: po.Entry) -> dict:
    k, p, s = keys(e.msgctxt, e.msgid)
    r = {"k": k, "p": p, "s": s, "t": e.msgstr}
    if e.fuzzy:
        r["f"] = 1
    if e.obsolete:
        r["o"] = 1
    if e.translator_comments:
        r["c"] = list(e.translator_comments)
    return r


def export(cat: po.Catalog, orphans: list[dict] = ()) -> list[dict]:
    """Records for every translated entry (live first, then obsolete), plus `orphans`: records
    carried over from the previous store whose English is unknown here."""
    live = [record(e) for e in cat.entries if e.msgstr and not e.obsolete]
    dead = [record(e) for e in cat.entries if e.msgstr and e.obsolete]
    seen = {r["k"] for r in live + dead}
    kept = []
    for r in orphans:
        if r["k"] not in seen:
            r = dict(r, o=1)
            kept.append(r)
            seen.add(r["k"])
    return live + dead + kept


def dumps(records: list[dict], header: dict) -> str:
    lines = [json.dumps(dict(header, format=FORMAT), ensure_ascii=False, sort_keys=True)]
    lines += [json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in records]
    return "\n".join(lines) + "\n"


def loads(text: str) -> tuple[dict, list[dict]]:
    rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not rows or rows[0].get("format") != FORMAT:
        raise ValueError(f"not a {FORMAT} file")
    return rows[0], rows[1:]


def load(path: pathlib.Path) -> tuple[dict, list[dict]]:
    if not path.exists():
        return {}, []
    return loads(path.read_text(encoding="utf-8"))


def dump(path: pathlib.Path, records: list[dict], header: dict) -> None:
    """Write a store file; a file with nothing to store is not created."""
    if not records and not path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    text = dumps(records, header)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")


def apply(cat: po.Catalog, records: list[dict], prefer_store: bool = False) -> tuple[list[dict], collections.Counter]:
    """Bring store translations into a catalog that has the English. Returns (orphans, stats).

    * a record whose `k` matches an entry fills it when the entry has no translation yet, or
      always with `prefer_store` (e.g. after pulling someone else's changes);
    * a record that matches no entry, but shares its place `p` with exactly one untranslated
      entry, is the same attribute/Context with new English: it fills that entry as fuzzy;
    * everything else is an orphan, kept in the store as obsolete.
    """
    stats = collections.Counter()
    by_k = {}
    for e in cat.entries:
        k, p, s = keys(e.msgctxt, e.msgid)
        by_k[k] = e
    orphans = []
    for r in records:
        e = by_k.get(r["k"])
        if e is None:
            orphans.append(r)
            continue
        if e.msgstr and not prefer_store:
            if e.msgstr != r["t"]:
                stats["local-wins"] += 1
            continue
        if e.msgstr != r["t"] or e.fuzzy != bool(r.get("f")):
            stats["from-store"] += 1
        e.msgstr = r["t"]
        e.fuzzy = bool(r.get("f"))
        if r.get("c"):
            e.translator_comments = list(r["c"])
    # English changed at the same place: match orphans by place
    empty_by_p = collections.defaultdict(list)
    texts_by_p = collections.defaultdict(set)
    for e in cat.entries:
        if e.obsolete:
            continue
        p = keys(e.msgctxt, e.msgid)[1]
        if e.msgstr:
            texts_by_p[p].add(e.msgstr)
        else:
            empty_by_p[p].append(e)
    still = []
    orphan_by_p = collections.defaultdict(list)
    for r in orphans:
        orphan_by_p[r["p"]].append(r)
    for r in orphans:
        if r["t"] in texts_by_p.get(r["p"], ()):
            stats["superseded"] += 1   # the catalog already carries this text at that place
            continue
        cands = empty_by_p.get(r["p"], [])
        if len(cands) == 1 and len(orphan_by_p[r["p"]]) == 1:
            e = cands[0]
            e.msgstr = r["t"]
            e.fuzzy = True
            if r.get("c"):
                e.translator_comments = list(r["c"])
            stats["moved"] += 1
        else:
            still.append(r)
    stats["orphans"] = len(still)
    return still, stats
