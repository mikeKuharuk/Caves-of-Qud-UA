"""The sync / save / build / validate / stats / import commands.

Two places hold translations:
* translations/uk/*.jsonl — the store, committed to git: our text only, no English (store.py);
* work/po/uk/*.po — the local working copy with the English msgids, rebuilt from the installed
  game plus the store. Translators edit these; `save` (or `sync`) writes edits to the store.
"""
from __future__ import annotations

import collections
import difflib
import pathlib
import re
import xml.etree.ElementTree as ET

from . import batch, checks, po, store, units
from .sources import REPO

PO_DIR = REPO / "work" / "po" / "uk"
STORE_DIR = REPO / "translations" / "uk"
OUT_DIR = REPO / "mod" / "Language"
GENDERS_OUT = REPO / "mod" / "Grammar" / "NounGenders.g.cs"
ADJECTIVES_OUT = REPO / "mod" / "Grammar" / "AdjectiveForms.g.cs"
DISPLAY_NAME = re.compile(r"^object\[([^\]]+)\]/part\[Render\]@DisplayName$")
QUD_GENDER = re.compile(r"^qud-gender:\s*(m|f|n|pl)\b")
BATCH_DIR = REPO / "work" / "batch"
WORD = re.compile(r"\w+")
TAG = re.compile(r"<[^>]*>")


def _words(e: po.Entry) -> int:
    """English words of a unit; the tags of an XML template are not words."""
    return len(WORD.findall(TAG.sub(" ", e.msgid) if "qud-template" in e.flags else e.msgid))


# Attributes whose translation must be the same wherever the English is the same, because the
# game groups things by this text (the options screen groups options by Category).
CONSISTENT = {("Options.po", "@Category"), ("Mods.po", "@TinkerCategory")}


def store_name(example_name: str) -> str:
    return units.base_name(example_name) + ".jsonl"


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
# sync of one catalog against one example file (English side)

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
        if u.kind == "template" and "qud-template" not in e.flags:
            e.flags.append("qud-template")
        if u.kind == "spice" and "qud-spice" not in e.flags:
            e.flags.append("qud-spice")
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
                                      "Local working copy (not in git). Edit msgstr here, then run "
                                      "`py tools/qud.py save` to update translations/uk/."],
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


# --------------------------------------------------------------------------------------------
# working copy <-> store

def load_catalog(xml_text: str, name: str, po_dir: pathlib.Path = PO_DIR,
                 store_dir: pathlib.Path = STORE_DIR) -> tuple[po.Catalog, list[dict]]:
    """The local catalog for an example file, rebuilt from the store when there is none yet.
    Returns (catalog, store orphans)."""
    path = po_dir / units.po_name(name)
    _, records = store.load(store_dir / store_name(name))
    if path.exists():
        cat = po.load(path)
        ks = {store.keys(e.msgctxt, e.msgid)[0] for e in cat.entries}
        return cat, [r for r in records if r["k"] not in ks]
    cat, _ = sync_file(xml_text, name, None)
    orphans, _ = store.apply(cat, records)
    return cat, orphans


def cmd_sync(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR,
             prefer_store: bool = False, quiet: bool = False) -> collections.Counter:
    """English string tables + store (+ local catalogs) → updated local catalogs and store."""
    total = collections.Counter()
    for name, text in sorted(files.items()):
        path = po_dir / units.po_name(name)
        spath = store_dir / store_name(name)
        _, records = store.load(spath)
        # first align the local catalog with the current English (it knows the old English, so
        # changed units become fuzzy with the previous msgid), then fill it from the store
        cat, stats = sync_file(text, name, po.load(path) if path.exists() else None)
        orphans, applied = store.apply(cat, records, prefer_store)
        stats.update(applied)
        total.update(stats)
        if not quiet and (stats["new"] or stats["fuzzy"] or stats["obsoleted"] or stats["from-store"]
                          or stats["local-wins"] or stats["moved"]):
            print(f"{units.po_name(name):34} kept {stats['kept']:6} new {stats['new']:6} fuzzy {stats['fuzzy']:4} "
                  f"obsoleted {stats['obsoleted']:4} from store {stats['from-store']:4} local wins {stats['local-wins']:3}")
        _write_po(path, cat)
        store.dump(spath, store.export(cat, orphans),
                   {"source": name, "build": units.game_build(text), "lang": "uk"})
    return total


def cmd_save(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR) -> int:
    """Local catalogs → store (after editing in Poedit). Returns the number of records written."""
    n = 0
    for name, text in sorted(files.items()):
        path = po_dir / units.po_name(name)
        if not path.exists():
            continue
        cat = po.load(path)
        spath = store_dir / store_name(name)
        header, records = store.load(spath)
        ks = {store.keys(e.msgctxt, e.msgid)[0] for e in cat.entries}
        recs = store.export(cat, [r for r in records if r["k"] not in ks])
        store.dump(spath, recs, {"source": name, "build": cat.headers.get("X-Qud-Build"), "lang": "uk"})
        n += len(recs)
    return n


def unsaved(cat: po.Catalog, store_dir: pathlib.Path, name: str) -> int:
    """Translations in the local catalog that the store does not have (yet)."""
    _, records = store.load(store_dir / store_name(name))
    have = {(r["k"], r["t"], bool(r.get("f"))) for r in records}
    return sum(1 for r in store.export(cat) if (r["k"], r["t"], bool(r.get("f"))) not in have)


def _write_po(path: pathlib.Path, cat: po.Catalog) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = po.dumps(cat)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------------------------
# build

def translations_of(cat: po.Catalog, include_fuzzy: bool = False) -> dict:
    return {e.key: e.msgstr for e in cat.entries
            if not e.obsolete and e.msgstr and (include_fuzzy or not e.fuzzy)}


def cmd_build(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR,
              out_dir: pathlib.Path = OUT_DIR, include_fuzzy: bool = False, force: bool = False) -> int:
    """Write mod/Language/*.uk.xml. Returns the number of problems (0 = fine)."""
    problems = 0
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, text in sorted(files.items()):
        out = out_dir / units.output_name(name)
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        src_build = units.game_build(text)
        po_build = cat.headers.get("X-Qud-Build")
        if src_build and po_build and src_build != po_build:
            print(f"warning: {units.po_name(name)} was synced against {po_build}, the game has {src_build}; run sync")
        trans = translations_of(cat, include_fuzzy)
        xml, count = units.build(text, name, trans, source_note=f"Game build {src_build}.")
        if len(trans) > count:
            print(f"warning: {units.po_name(name)}: {len(trans) - count} translated entries have no place in the game; run sync")
        n_unsaved = unsaved(cat, store_dir, name)
        if n_unsaved:
            print(f"warning: {units.po_name(name)}: {n_unsaved} translation(s) not saved to translations/uk; run save")
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
        units.check_output(name, xml)  # the output must be well-formed
        if not out.exists() or out.read_text(encoding="utf-8") != xml:
            out.write_text(xml, encoding="utf-8", newline="\n")
        print(f"{out.name:40} {count:6} translated")
    genders = noun_genders(files, po_dir, store_dir)
    code = noun_genders_cs(genders)
    GENDERS_OUT.parent.mkdir(parents=True, exist_ok=True)
    if not GENDERS_OUT.exists() or GENDERS_OUT.read_text(encoding="utf-8") != code:
        GENDERS_OUT.write_text(code, encoding="utf-8", newline="\n")
    print(f"{GENDERS_OUT.name:40} {len(genders):6} noun genders")
    adjectives = adjective_forms(files, po_dir, store_dir)
    code = adjective_forms_cs(adjectives)
    if not ADJECTIVES_OUT.exists() or ADJECTIVES_OUT.read_text(encoding="utf-8") != code:
        ADJECTIVES_OUT.write_text(code, encoding="utf-8", newline="\n")
    print(f"{ADJECTIVES_OUT.name:40} {len(adjectives):6} adjectives")
    return problems


def noun_genders(files: dict[str, str], po_dir: pathlib.Path = PO_DIR,
                 store_dir: pathlib.Path = STORE_DIR) -> dict[str, str]:
    """Blueprint → the grammatical gender of its Ukrainian name, from the qud-gender note of its DisplayName.
    mod/Grammar agrees verbs and adjectives with it (docs/grammar.md)."""
    genders: dict[str, str] = {}
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        for e in cat.entries:
            m = DISPLAY_NAME.match(e.msgctxt or "")
            if e.obsolete or not e.msgstr or not m:
                continue
            for c in e.translator_comments:
                g = QUD_GENDER.match(c)
                if g:
                    genders.setdefault(m.group(1), g.group(1))
                    break
    return genders


def adjective_forms(files: dict[str, str], po_dir: pathlib.Path = PO_DIR,
                    store_dir: pathlib.Path = STORE_DIR) -> dict[str, list[str]]:
    """Masculine adjective (plain text) → [feminine, neuter, plural], from the translators' "uk-forms: ж|с|мн"
    notes. mod/Grammar agrees the adjectives the game puts before a name with the object (docs/grammar.md)."""
    forms: dict[str, list[str]] = {}
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        for e in cat.entries:
            if e.obsolete or not e.msgstr:
                continue
            for c in e.translator_comments:
                m = checks.UK_FORMS.match(c)
                if m:
                    key = checks.plain_text(e.msgstr).strip()
                    if key:
                        forms.setdefault(key, [f.strip() for f in m.group(1).split("|")])
    return forms


def adjective_forms_cs(forms: dict[str, list[str]]) -> str:
    def lit(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    lines = [f"            t[{lit(k)}] = new[] {{ {', '.join(lit(f) for f in v)} }};" for k, v in sorted(forms.items())]
    return ("// <auto-generated> by `py tools/qud.py build` from the uk-forms notes of the translation. Not in git.\n"
            "using System.Collections.Generic;\n\n"
            "namespace CavesOfQudUA.Grammar\n{\n"
            "    public static partial class AdjectiveForms\n    {\n"
            "        static partial void Fill(Dictionary<string, string[]> t)\n        {\n"
            + "\n".join(lines) + "\n        }\n    }\n}\n")


def noun_genders_cs(genders: dict[str, str]) -> str:
    def lit(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    lines = [f"            t[{lit(bp)}] = {lit(g)};" for bp, g in sorted(genders.items())]
    return ("// <auto-generated> by `py tools/qud.py build` from the qud-gender notes of the translation. Not in git.\n"
            "using System.Collections.Generic;\n\n"
            "namespace CavesOfQudUA.Grammar\n{\n"
            "    public static partial class NounGenders\n    {\n"
            "        static partial void Fill(Dictionary<string, string> t)\n        {\n"
            + "\n".join(lines) + "\n        }\n    }\n}\n")


# --------------------------------------------------------------------------------------------
# validate

def cmd_validate(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR,
                 show_warnings: bool = True) -> tuple[int, int]:
    errors = warnings = 0
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        pname = units.po_name(name)
        for e in cat.entries:
            if e.obsolete or not e.msgstr:
                continue
            for issue in checks.check_entry(e):
                if issue.severity == "error":
                    errors += 1
                else:
                    warnings += 1
                    if not show_warnings:
                        continue
                where = e.msgctxt if e.msgctxt is not None else "(no context)"
                fuzzy = " [fuzzy]" if e.fuzzy else ""
                print(f"{issue.severity}: {pname}: {where}{fuzzy}: {issue.code}: {issue.message}\n"
                      f"    en: {e.msgid[:120]!r}\n    uk: {e.msgstr[:120]!r}")
        for po_file, suffix in CONSISTENT:
            if po_file != pname:
                continue
            seen: dict[str, set] = collections.defaultdict(set)
            for e in cat.entries:
                if not e.obsolete and e.msgstr and (e.msgctxt or "").endswith(suffix):
                    seen[e.msgid].add(e.msgstr)
            for en, uks in sorted(seen.items()):
                if len(uks) > 1:
                    errors += 1
                    print(f"error: {pname}: {suffix} {en!r} is translated in different ways {sorted(uks)}; "
                          f"the game groups by this text")
        n_unsaved = unsaved(cat, store_dir, name)
        if n_unsaved:
            warnings += 1
            print(f"warning: {pname}: {n_unsaved} translation(s) not saved to translations/uk; run save")
    errors += check_spice_paths(files, po_dir, store_dir)
    print(f"{errors} error(s), {warnings} warning(s)")
    return errors, warnings


def check_spice_paths(files: dict[str, str], po_dir: pathlib.Path = PO_DIR,
                      store_dir: pathlib.Path = STORE_DIR) -> int:
    """Every HistorySpice reference a translation adds must lead to a list: the English spice with our overlay
    (translations/uk/HistorySpice.extra.json) merged in. The overlay may only add keys. Returns the errors."""
    from . import spice
    source = next((t for n, t in files.items() if units.is_spice(n)), None)
    if source is None:
        return 0
    english = spice.load(source)["spice"]
    parts = spice.load_overlay_parts()
    overlay = spice.load_overlay()
    errors = 0
    for clash in spice.overlay_clashes(parts):
        errors += 1
        print(f"error: HistorySpice.extra: {clash}: two files define the same key")
    for path in spice.overlay_conflicts(english, overlay):
        errors += 1
        print(f"error: HistorySpice.extra: spice.{path} exists in the English spice; translate it in HistorySpice.po")
    tree = spice.merge(english, overlay)
    for path, value in spice.leaves(overlay):
        for ref in spice.unresolved(value, tree, path[0]):
            errors += 1
            print(f"error: HistorySpice.extra: spice.{'.'.join(path)}: reference leads nowhere: {ref}")
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        for e in cat.entries:
            if e.obsolete or not e.msgstr or ("spice" not in e.msgstr and "=^:" not in e.msgstr):
                continue
            branch = e.msgctxt.split(".")[1] if units.is_spice(name) and e.msgctxt else None
            new = set(spice.unresolved(e.msgstr, tree, branch)) - set(spice.unresolved(e.msgid, tree, branch))
            for ref in sorted(new):
                errors += 1
                print(f"error: {units.po_name(name)}: {e.msgctxt}: spice-path: reference leads nowhere: {ref}")
    return errors


# --------------------------------------------------------------------------------------------
# worksheets

def _example_for_po(files: dict[str, str], po_name: str) -> str:
    """The source file of a catalog: 'Items.po' → 'Items.example.xml', 'HistorySpice.po' → 'HistorySpice.jsonc'."""
    for name in files:
        if units.po_name(name) == po_name:
            return name
    raise SystemExit(f"no source file for {po_name}")


def cmd_worksheet(files: dict[str, str], po_name: str, out: pathlib.Path | None, ctx: str | None = None,
                  include_translated: bool = False, limit: int | None = None,
                  po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR) -> pathlib.Path:
    name = _example_for_po(files, po_name)
    cat, _ = load_catalog(files[name], name, po_dir, store_dir)
    rows = batch.make_worksheet(cat, po_name, ctx, include_translated, limit)
    out = out or BATCH_DIR / (po_name.removesuffix(".po") + ".jsonl")
    batch.write(out, rows)
    print(f"{out}: {len(rows) - 1} unit(s)")
    return out


def cmd_check_worksheet(paths: list[pathlib.Path]) -> int:
    """Print the errors and warnings of filled-in worksheets. Returns the number of errors."""
    total = 0
    for path in paths:
        _, rows = batch.read(path)
        report = batch.check_rows(rows)
        for level, issues in (("ERROR", report.errors), ("warning", report.warnings)):
            for k, ctx, message in issues:
                print(f"  {level} {ctx} [{k}]: {message}")
        print(f"{path.name}: {len(rows) - report.missing} filled, {report.missing} empty, "
              f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
        total += len(report.errors)
    return total


def cmd_apply(files: dict[str, str], paths: list[pathlib.Path], po_dir: pathlib.Path = PO_DIR,
              store_dir: pathlib.Path = STORE_DIR) -> int:
    """Worksheets → local catalogs → store. Returns the number of problems."""
    problems_total = 0
    for path in paths:
        header, rows = batch.read(path)
        name = _example_for_po(files, header["po"])
        cat, orphans = load_catalog(files[name], name, po_dir, store_dir)
        applied, problems = batch.apply_rows(cat, rows)
        for p in problems:
            print(f"error: {path.name}: {p}")
        problems_total += len(problems)
        _write_po(po_dir / units.po_name(name), cat)
        store.dump(store_dir / store_name(name), store.export(cat, orphans),
                   {"source": name, "build": units.game_build(files[name]), "lang": "uk"})
        print(f"{path.name}: applied {applied}, problems {len(problems)}")
    return problems_total


# --------------------------------------------------------------------------------------------
# stats

def cmd_stats(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR) -> None:
    rows = []
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        live = [e for e in cat.entries if not e.obsolete]
        done = [e for e in live if e.translated]
        fuzzy = [e for e in live if e.msgstr and e.fuzzy]
        words = sum(map(_words, live))
        done_words = sum(map(_words, done))
        rows.append((units.po_name(name), len(live), len(done), len(fuzzy), words, done_words))
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
               store_dir: pathlib.Path = STORE_DIR, overwrite: bool = False) -> int:
    """Fill local catalogs (and the store) from existing *.uk.xml files. Returns the count imported."""
    total = 0
    for tpath in translated:
        name = tpath.name.removesuffix(".uk.xml") + ".example.xml"
        if name not in files:
            print(f"skip {tpath.name}: no {name} in the source")
            continue
        found = import_translation(files[name], name, tpath.read_text(encoding="utf-8-sig"))
        cat, orphans = load_catalog(files[name], name, po_dir, store_dir)
        cat, _ = sync_file(files[name], name, cat)
        n = 0
        for e in cat.entries:
            if e.obsolete or e.key not in found or (e.msgstr and not overwrite):
                continue
            e.msgstr = found[e.key]
            e.fuzzy = False
            n += 1
        _write_po(po_dir / units.po_name(name), cat)
        store.dump(store_dir / store_name(name), store.export(cat, orphans),
                   {"source": name, "build": units.game_build(files[name]), "lang": "uk"})
        print(f"{tpath.name:40} imported {n} of {len(found)} found")
        total += n
    return total
