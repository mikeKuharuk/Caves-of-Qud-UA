"""Worksheets for translating in batches.

A worksheet is a JSON Lines file under work/batch/ (not in git: it carries the English):

  {"po": "Options.po"}                                              <- header
  {"k": "<unit hash>", "ctx": "option[ID=X]@DisplayText", "en": "Main volume", "uk": ""}

`worksheet` writes one from a local PO catalog; after the "uk" fields are filled in, `apply`
puts them into the catalog (and the store). Lines with an empty "uk" are skipped; a line may
carry "fuzzy": true to mark a doubtful translation, "comment" for a translator comment (it replaces
the old one), and "clear_comment": true to drop the old comment.
"""
from __future__ import annotations

import dataclasses
import json
import pathlib
import re

from . import checks, po, store

KIND_FLAGS = ("qud-compound", "qud-template")   # the checks depend on them


@dataclasses.dataclass
class Report:
    missing: int = 0                                           # rows with no translation yet
    errors: list = dataclasses.field(default_factory=list)     # (k, ctx, message)
    warnings: list = dataclasses.field(default_factory=list)


def check_rows(rows: list[dict]) -> Report:
    """Check filled-in worksheet rows the way validate would, without the PO catalog: a translator
    can check their work while the catalog belongs to whoever applies it. "qud-ok" comments count."""
    report = Report()
    for r in rows:
        uk = r.get("uk") or ""
        if not uk:
            report.missing += 1
            continue
        e = po.Entry(msgid=r["en"], msgstr=uk, msgctxt=r.get("ctx"), flags=list(r.get("flags", [])),
                     translator_comments=r["comment"].split("\n") if r.get("comment") else [])
        for i in checks.check_entry(e):
            (report.errors if i.severity == "error" else report.warnings).append(
                (r["k"], r.get("ctx"), f"{i.code}: {i.message}"))
    return report


def make_worksheet(cat: po.Catalog, po_name: str, ctx_pattern: str | None = None,
                   include_translated: bool = False, limit: int | None = None) -> list[dict]:
    rx = re.compile(ctx_pattern) if ctx_pattern else None
    rows = []
    for e in cat.entries:
        if e.obsolete or (e.msgstr and not include_translated and not e.fuzzy):
            continue
        if rx and not rx.search(e.msgctxt or ""):
            continue
        row = {"k": store.keys(e.msgctxt, e.msgid)[0], "ctx": e.msgctxt, "en": e.msgid, "uk": e.msgstr}
        flags = [f for f in e.flags if f in KIND_FLAGS]
        if flags:
            row["flags"] = flags
        if e.extracted_comments:
            row["note"] = " ".join(e.extracted_comments)
        if e.previous_msgid is not None:
            row["previous_en"] = e.previous_msgid
        rows.append(row)
        if limit and len(rows) >= limit:
            break
    return [{"po": po_name}] + rows


def write(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read(path: pathlib.Path) -> tuple[dict, list[dict]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or "po" not in rows[0]:
        raise ValueError(f"{path}: the first line must be a header with the PO name")
    return rows[0], rows[1:]


def apply_rows(cat: po.Catalog, rows: list[dict]) -> tuple[int, list[str]]:
    """Put worksheet translations into the catalog. Returns (applied, problems)."""
    by_k = {store.keys(e.msgctxt, e.msgid)[0]: e for e in cat.entries if not e.obsolete}
    applied = 0
    problems = []
    for r in rows:
        uk = r.get("uk") or ""
        if not uk:
            continue
        e = by_k.get(r["k"])
        if e is None:
            problems.append(f"unknown unit {r['k']} ({r.get('ctx')}): run sync, or the worksheet is stale")
            continue
        errors = [i for i in checks.check_entry(e, uk) if i.severity == "error"]
        if errors:
            problems.append(f"{e.msgctxt}: " + "; ".join(f"{i.code}: {i.message}" for i in errors))
            continue
        e.msgstr = uk
        e.fuzzy = bool(r.get("fuzzy"))
        if r.get("comment"):
            e.translator_comments = r["comment"].split("\n")
        elif r.get("clear_comment"):
            e.translator_comments = []
        applied += 1
    return applied, problems
