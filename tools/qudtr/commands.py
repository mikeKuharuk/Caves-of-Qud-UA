"""The sync / build / validate / stats / import commands."""
from __future__ import annotations

import collections
import difflib
import pathlib
import re
import xml.etree.ElementTree as ET

from . import checks, po, units
from .sources import REPO

PO_DIR = REPO / "translations" / "uk"
OUT_DIR = REPO / "mod" / "Language"
WORD = re.compile(r"\w+")


def _header(build: str | None, name: str) -> dict[str, str]:
    h = {
        "Project-Id-Version": "CavesOfQud-UA",
        "Language": "uk",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Plural-Forms": po.UK_PLURAL_FORMS,
        "X-Qud-Source": name,
    }
    if build:
        h["X-Qud-Build"] = build
    return h


# --------------------------------------------------------------------------------------------
# sync

def sync_file(xml_text: str, name: str, old: po.Catalog | None) -> tuple[po.Catalog, collections.Counter]:
    """Bring a catalog in line with one example file. Returns (catalog, counts)."""
    stats = collections.Counter()
    old = old or po.Catalog()
    old_live = {e.key: e for e in old.entries if not e.obsolete}
    old_dead = {e.key: e for e in old.entries if e.obsolete}   # a unit may come back in a later build
    old_by_ctxt: dict[str | None, list[po.Entry]] = collections.defaultdict(list)
    for e in old.entries:
        if e.msgstr:
            old_by_ctxt[e.msgctxt].append(e)

    unit_list = []
    seen = set()
    for u in units.extract(xml_text, name):
        if u.key in seen:
            stats["duplicate"] += 1
            continue
        seen.add(u.key)
        unit_list.append(u)

    used: set[int] = set()
    entries: list[po.Entry] = []
    for u in unit_list:
        e = old_live.get(u.key) or old_dead.get(u.key)
        if e is not None:
            used.add(id(e))
            stats["revived" if e.obsolete else "kept"] += 1
            e.obsolete = False
        else:
            e = _fuzzy_candidate(u, old_by_ctxt.get(u.msgctxt, []), seen, used)
            if e is not None:
                used.add(id(e))
                e = po.Entry(msgid=u.msgid, msgctxt=u.msgctxt, msgstr=e.msgstr, flags=["fuzzy"],
                             translator_comments=list(e.translator_comments), previous_msgid=e.msgid)
                stats["fuzzy"] += 1
            else:
                e = po.Entry(msgid=u.msgid, msgctxt=u.msgctxt)
                stats["new"] += 1
        e.extracted_comments = [u.note] if u.note else []
        if u.compound and "qud-compound" not in e.flags:
            e.flags.append("qud-compound")
        entries.append(e)

    obsolete = []
    for e in old.entries:
        if id(e) in used or not e.msgstr:
            continue
        if not e.obsolete:
            stats["obsoleted"] += 1
        e.obsolete = True
        obsolete.append(e)

    cat = po.Catalog(headers=_header(units.game_build(xml_text), name),
                     header_comments=[f"Ukrainian translation of Caves of Qud — {name}",
                                      "Source of truth for mod/Language/" + units.output_name(name) + "; run tools/qud.py build."],
                     entries=entries + obsolete)
    return cat, stats


def _fuzzy_candidate(u: units.Unit, candidates: list[po.Entry], current_keys: set, used: set[int]) -> po.Entry | None:
    """An old translation for the same key whose English changed."""
    pool = [c for c in candidates if id(c) not in used and c.key not in current_keys]
    if not pool:
        return None
    if u.kind != "string":
        return pool[0]            # the msgctxt is the element path: same place, new English
    best = max(pool, key=lambda c: difflib.SequenceMatcher(None, c.msgid, u.msgid).ratio())
    return best if difflib.SequenceMatcher(None, best.msgid, u.msgid).ratio() >= 0.5 else None


def cmd_sync(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, dry_run: bool = False) -> collections.Counter:
    po_dir.mkdir(parents=True, exist_ok=True)
    total = collections.Counter()
    for name, text in sorted(files.items()):
        path = po_dir / units.po_name(name)
        old = po.load(path) if path.exists() else None
        cat, stats = sync_file(text, name, old)
        total.update(stats)
        changed = stats["new"] or stats["fuzzy"] or stats["obsoleted"] or not path.exists()
        if changed or not dry_run:
            print(f"{units.po_name(name):40} kept {stats['kept']:6}  new {stats['new']:6}  "
                  f"fuzzy {stats['fuzzy']:5}  obsoleted {stats['obsoleted']:5}")
        if not dry_run:
            new_text = po.dumps(cat)
            if not path.exists() or path.read_text(encoding="utf-8") != new_text:
                path.write_text(new_text, encoding="utf-8", newline="\n")
    return total


# --------------------------------------------------------------------------------------------
# build

def translations_of(cat: po.Catalog, include_fuzzy: bool = False) -> dict:
    return {e.key: e.msgstr for e in cat.entries
            if not e.obsolete and e.msgstr and (include_fuzzy or not e.fuzzy)}


def cmd_build(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, out_dir: pathlib.Path = OUT_DIR,
              include_fuzzy: bool = False, force: bool = False) -> int:
    """Write mod/Language/*.uk.xml. Returns the number of problems (0 = fine)."""
    problems = 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in sorted(files.items()):
        path = po_dir / units.po_name(name)
        out = out_dir / units.output_name(name)
        if not path.exists():
            continue
        cat = po.load(path)
        src_build = units.game_build(text)
        po_build = cat.headers.get("X-Qud-Build")
        if src_build and po_build and src_build != po_build:
            print(f"warning: {path.name} was synced against {po_build}, the source is {src_build}; run sync")
        trans = translations_of(cat, include_fuzzy)
        xml, count = units.build(text, name, trans, source_note=f"Game build {src_build}.")
        unused = len(trans) - count
        if unused > 0:
            print(f"warning: {path.name}: {unused} translated entries have no place in the source; run sync")
        existing_generated = out.exists() and units.GENERATED_MARKER in out.read_text(encoding="utf-8")[:300]
        if out.exists() and not existing_generated and not force:
            print(f"error: {out} exists and was not generated by this tool; import it first or use --force")
            problems += 1
            continue
        if xml is None:
            if existing_generated:
                out.unlink()
                print(f"{out.name:40} removed (nothing translated)")
            continue
        ET.fromstring(xml)  # the output must be well-formed
        if not out.exists() or out.read_text(encoding="utf-8") != xml:
            out.write_text(xml, encoding="utf-8", newline="\n")
        print(f"{out.name:40} {count:6} translated")
    return problems


# --------------------------------------------------------------------------------------------
# validate

def cmd_validate(po_dir: pathlib.Path = PO_DIR, show_warnings: bool = True) -> tuple[int, int]:
    errors = warnings = 0
    for path in sorted(po_dir.glob("*.po")):
        cat = po.load(path)
        for e in cat.entries:
            if e.obsolete or not e.msgstr:
                continue
            for issue in checks.check(e.msgid, e.msgstr, compound="qud-compound" in e.flags):
                if issue.severity == "error":
                    errors += 1
                else:
                    warnings += 1
                    if not show_warnings:
                        continue
                where = e.msgctxt if e.msgctxt is not None else "(no context)"
                fuzzy = " [fuzzy]" if e.fuzzy else ""
                print(f"{issue.severity}: {path.name}: {where}{fuzzy}: {issue.code}: {issue.message}\n"
                      f"    en: {e.msgid[:120]!r}\n    uk: {e.msgstr[:120]!r}")
    print(f"{errors} error(s), {warnings} warning(s)")
    return errors, warnings


# --------------------------------------------------------------------------------------------
# stats

def cmd_stats(po_dir: pathlib.Path = PO_DIR) -> None:
    rows = []
    for path in sorted(po_dir.glob("*.po")):
        cat = po.load(path)
        live = [e for e in cat.entries if not e.obsolete]
        done = [e for e in live if e.translated]
        fuzzy = [e for e in live if e.msgstr and e.fuzzy]
        words = sum(len(WORD.findall(e.msgid)) for e in live)
        done_words = sum(len(WORD.findall(e.msgid)) for e in done)
        rows.append((path.name, len(live), len(done), len(fuzzy), words, done_words))
    print(f"{'file':34} {'units':>7} {'done':>7} {'fuzzy':>6} {'words':>8} {'done%':>6}")
    t = [0, 0, 0, 0, 0]
    for name, n, d, f, w, dw in rows:
        t = [t[0] + n, t[1] + d, t[2] + f, t[3] + w, t[4] + dw]
        print(f"{name:34} {n:7} {d:7} {f:6} {w:8} {100 * dw / w if w else 0:5.1f}%")
    print(f"{'TOTAL':34} {t[0]:7} {t[1]:7} {t[2]:6} {t[3]:8} {100 * t[4] / t[3] if t[3] else 0:5.1f}%")


# --------------------------------------------------------------------------------------------
# import

def import_translation(example_xml: str, name: str, translated_xml: str, skip_identical: bool = True) -> dict:
    """Map units of an example file to values found in an existing translated file."""
    return units.ExampleFile(example_xml, name).read_translation(translated_xml, skip_identical)


def cmd_import(files: dict[str, str], translated: list[pathlib.Path], po_dir: pathlib.Path = PO_DIR,
               overwrite: bool = False) -> int:
    """Fill PO entries from existing *.uk.xml files. Returns the number of imported strings."""
    total = 0
    for tpath in translated:
        stem = tpath.name.removesuffix(".uk.xml")
        name = stem + ".example.xml"
        if name not in files:
            print(f"skip {tpath.name}: no {name} in the source")
            continue
        found = import_translation(files[name], name, tpath.read_text(encoding="utf-8-sig"))
        path = po_dir / units.po_name(name)
        cat, _ = sync_file(files[name], name, po.load(path) if path.exists() else None)
        n = 0
        for e in cat.entries:
            if e.obsolete or e.key not in found:
                continue
            if e.msgstr and not overwrite:
                continue
            e.msgstr = found[e.key]
            e.fuzzy = False
            n += 1
        po_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(po.dumps(cat), encoding="utf-8", newline="\n")
        print(f"{tpath.name:40} imported {n} of {len(found)} found")
        total += n
    return total
