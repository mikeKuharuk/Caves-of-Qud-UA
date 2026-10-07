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
from xml.sax import saxutils

from . import batch, checks, codetables, held, po, store, units
from .sources import REPO

PO_DIR = REPO / "work" / "po" / "uk"
STORE_DIR = REPO / "translations" / "uk"
OUT_DIR = REPO / "mod" / "Language"
GENDERS_OUT = REPO / "mod" / "Grammar" / "NounGenders.g.cs"
ADJECTIVES_OUT = REPO / "mod" / "Grammar" / "AdjectiveForms.g.cs"
LEXICON_OUT = REPO / "mod" / "Grammar" / "AdjectiveLexicon.g.cs"
CODE_TABLES = REPO / "mod" / "Grammar" / "CodeTables.g.cs"
VARIANT_NAMES = "VariantNames.uk.xml"
CREATURE_TYPES = "CreatureTypes.uk.xml"
MUTATION_NAME = re.compile(r"(?:^|/)mutation\[([^\]]+)\]@DisplayName$")
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

def code_table_of(cat: po.Catalog, include_fuzzy: bool = False, note: re.Pattern | None = None) -> dict[str, str]:
    """English → Ukrainian from a Code.* catalog. With note, only the entries whose translator notes match it, each
    mapped to the note's first group (a vocative) or to its translation (uk-agree)."""
    out = {}
    for e in cat.entries:
        if e.obsolete or not e.msgstr or (e.fuzzy and not include_fuzzy):
            continue
        key = codetables.key_of(e.msgctxt, e.msgid)
        if note is None:
            out[key] = e.msgstr
            continue
        for c in e.translator_comments:
            m = note.match(c)
            if m:
                out[key] = m.group(1) if m.groups() else e.msgstr
    return out


def translations_of(cat: po.Catalog, include_fuzzy: bool = False) -> dict:
    return {e.key: e.msgstr for e in cat.entries
            if not e.obsolete and e.msgstr and (include_fuzzy or not e.fuzzy)}


def cmd_build(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR,
              out_dir: pathlib.Path = OUT_DIR, include_fuzzy: bool = False, force: bool = False,
              mutations_xml: str | None = None, creatures_xml: str | None = None) -> int:
    """Write mod/Language/*.uk.xml. Returns the number of problems (0 = fine). mutations_xml and creatures_xml are
    the game's Base/Mutations.xml and ObjectBlueprints/Creatures.xml, for VariantNames.uk.xml and
    CreatureTypes.uk.xml; without them those files are left as they are."""
    problems = 0
    out_dir.mkdir(parents=True, exist_ok=True)
    code_tables: dict[str, dict[str, str]] = {}
    for name, text in sorted(files.items()):
        out = out_dir / units.output_name(name)
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        src_build = units.game_build(text)
        po_build = cat.headers.get("X-Qud-Build")
        if src_build and po_build and src_build != po_build:
            print(f"warning: {units.po_name(name)} was synced against {po_build}, the game has {src_build}; run sync")
        if codetables.is_code_table(name):
            table = codetables.table_name(name)
            code_tables[table] = code_table_of(cat, include_fuzzy)
            code_tables[table + ".voc"] = code_table_of(cat, include_fuzzy, note=codetables.VOCATIVE)
            code_tables[table + ".agree"] = code_table_of(cat, include_fuzzy, note=codetables.AGREE)
            print(f"{CODE_TABLES.name + ' ' + table:40} {len(code_tables[table]):6} translated")
            continue
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
    code = codetables.code_tables_cs({k: v for k, v in code_tables.items() if v})
    if not CODE_TABLES.exists() or CODE_TABLES.read_text(encoding="utf-8") != code:
        CODE_TABLES.write_text(code, encoding="utf-8", newline="\n")
    if mutations_xml is None:
        print(f"warning: no Mutations.xml next to the string tables; {VARIANT_NAMES} not rebuilt")
    else:
        names = variant_names(files, mutations_xml, po_dir, store_dir, include_fuzzy)
        write_generated(out_dir / VARIANT_NAMES, variant_names_xml(names) if names else None)
        print(f"{VARIANT_NAMES:40} {len(names):6} variant names")
    if creatures_xml is None:
        print(f"warning: no ObjectBlueprints/Creatures.xml next to the string tables; {CREATURE_TYPES} not rebuilt")
    else:
        types = cherub_types(creatures_xml)
        write_generated(out_dir / CREATURE_TYPES, tag_merges_xml(
            "AlternateCreatureType", types, "from the game's ObjectBlueprints/Creatures.xml: the creature type of each "
            "cherub, which the game would otherwise cut from the translated name (commands.cherub_types)")
            if types else None)
        print(f"{CREATURE_TYPES:40} {len(types):6} cherub creature types")
    genders = noun_genders(files, po_dir, store_dir)
    words = word_genders(files, po_dir, store_dir)
    code = noun_genders_cs(genders, words)
    GENDERS_OUT.parent.mkdir(parents=True, exist_ok=True)
    if not GENDERS_OUT.exists() or GENDERS_OUT.read_text(encoding="utf-8") != code:
        GENDERS_OUT.write_text(code, encoding="utf-8", newline="\n")
    print(f"{GENDERS_OUT.name:40} {len(genders):6} noun genders, {len(words)} words")
    adjectives = adjective_forms(files, po_dir, store_dir)
    code = adjective_forms_cs(adjectives)
    if not ADJECTIVES_OUT.exists() or ADJECTIVES_OUT.read_text(encoding="utf-8") != code:
        ADJECTIVES_OUT.write_text(code, encoding="utf-8", newline="\n")
    print(f"{ADJECTIVES_OUT.name:40} {len(adjectives):6} adjectives")
    texts = translation_texts(files, po_dir, store_dir)
    lexicon = adjective_lexicon(files, po_dir, store_dir, texts)
    nouns = noun_lexicon(files, lexicon, po_dir, store_dir)
    stems = noun_stems(vocabulary(texts))
    code = adjective_lexicon_cs(lexicon, nouns, stems)
    if not LEXICON_OUT.exists() or LEXICON_OUT.read_text(encoding="utf-8") != code:
        LEXICON_OUT.write_text(code, encoding="utf-8", newline="\n")
    print(f"{LEXICON_OUT.name:40} {len(lexicon):6} masculine adjectives, {len(nouns)} nouns, "
          f"{sum(len(s) for s in stems)} noun stems")
    return problems


def fixed_variants(mutations_xml: str) -> dict[str, str]:
    """Mutation → the variant blueprint it is fixed to, from the game's Base/Mutations.xml
    (<mutation Name="Stinger (Confusing Venom)" … Variant="Stinger Confusion">)."""
    return {m.get("Name"): m.get("Variant") for m in ET.fromstring(mutations_xml).iter("mutation")
            if m.get("Name") and m.get("Variant")}


def variant_names(files: dict[str, str], mutations_xml: str, po_dir: pathlib.Path = PO_DIR,
                  store_dir: pathlib.Path = STORE_DIR, include_fuzzy: bool = False) -> dict[str, str]:
    """Variant blueprint → the Ukrainian name of the mutation fixed to it. The game names such a mutation after the
    variant's VariantName tag, not the mutation's DisplayName (BaseMutation.GetVariantName: «Stinger (Confusing
    Venom)» in character creation and on the character sheet), and tags are not in the string tables."""
    name = next((n for n in files if n.startswith("Mutations.")), None)
    if name is None:
        return {}
    fixed = fixed_variants(mutations_xml)
    cat, _ = load_catalog(files[name], name, po_dir, store_dir)
    out = {}
    for e in cat.entries:
        m = MUTATION_NAME.search(e.msgctxt or "")
        if m and m.group(1) in fixed and not e.obsolete and e.msgstr and (include_fuzzy or not e.fuzzy):
            out[fixed[m.group(1)]] = e.msgstr
    return out


def variant_names_xml(names: dict[str, str], lang: str = "uk") -> str:
    return tag_merges_xml("VariantName", names, f"from translations/{lang}/Mutations.jsonl: the names of the "
                          "mutations with a fixed variant, which the game reads from the VariantName tag", lang)


def tag_merges_xml(tag: str, values: dict[str, str], note: str, lang: str = "uk") -> str:
    """A language file that merges one tag into blueprints: blueprint → value."""
    body = "".join(f'  <object Name={saxutils.quoteattr(bp)} Load="Merge">\n'
                   f'    <tag Name="{tag}" Value={saxutils.quoteattr(v)} />\n'
                   f'  </object>\n' for bp, v in sorted(values.items()))
    return (f'<?xml version="1.0" encoding="utf-8"?>\n'
            f'<!-- {units.GENERATED_MARKER} {note}. Do not edit. -->\n'
            f'<objects Lang="{lang}" Encoding="utf-8">\n{body}</objects>\n')


CHERUB = re.compile(r'<object\s+Name="([^"]*? Cherub)"[^>]*>(.*?)</object>', re.S)


def cherub_types(creatures_xml: str) -> dict[str, str]:
    """Cherub blueprint → the creature type the game would cut from its English name («baboon cherub» → baboon).
    CherubimSpawner.ReplaceDescription puts that word into the cherub's description, an English literal in the code:
    from the AlternateCreatureType tag if there is one, else the display name up to its first space. Our names have
    no space («херувим-павіан»), so the cut throws when a tomb crypt or Shesh spawns a cherub, and a mechanical cherub
    would get «механічний». Giving every cherub the tag keeps the English description as it is in English."""
    out = {}
    for name, body in CHERUB.findall(units.uncommented(creatures_xml)):
        m = re.search(r'<part\s+Name="Render"[^>]*\bDisplayName="([^"]*)"', body)
        if m and "AlternateCreatureType" not in body:
            out[name] = m.group(1).replace("mechanical ", "").split(" ")[0]
    return out


def write_generated(out: pathlib.Path, xml: str | None) -> None:
    """Write a generated language file, or remove it when there is nothing to merge."""
    if xml is None:
        out.unlink(missing_ok=True)
        return
    ET.fromstring(xml)  # the output must be well-formed
    if not out.exists() or out.read_text(encoding="utf-8") != xml:
        out.write_text(xml, encoding="utf-8", newline="\n")


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


def word_genders(files: dict[str, str], po_dir: pathlib.Path = PO_DIR,
                 store_dir: pathlib.Path = STORE_DIR) -> dict[str, str]:
    """Ukrainian noun (plain text, lower case) → gender, from the qud-gender note of any unit: a noun the code passes
    as a string, such as a liquid's name, agrees through |uk.agree#primaryNoun (docs/grammar.md)."""
    words: dict[str, str] = {}
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        for e in cat.entries:
            if e.obsolete or not e.msgstr:
                continue
            for c in e.translator_comments:
                g = QUD_GENDER.match(c)
                if g:
                    key = checks.plain_text(e.msgstr).strip().lower()
                    if key:
                        words.setdefault(key, g.group(1))
                    break
    return words


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


# words that end like a masculine adjective but are nouns: never to be read as one
LEXICON_NOUNS = {"змій", "буревій", "водій", "кий", "рій", "гній", "палій", "лиходій"}
LEXICON_WORD = re.compile(r"(?<![\w’'-])([а-щьюяєіїґ’'-]{2,}(?:ий|ій|їй))(?![\w’'])")


def translation_texts(files: dict[str, str], po_dir: pathlib.Path = PO_DIR,
                      store_dir: pathlib.Path = STORE_DIR) -> list[str]:
    """The plain text (no markup) of every translation."""
    texts: list[str] = []
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        texts.extend(checks.plain_text(e.msgstr) for e in cat.entries if not e.obsolete and e.msgstr)
    return texts


def vocabulary(texts: list[str]) -> set[str]:
    """Every word of the texts, in lower case."""
    return {w.lower() for t in texts for w in NAME_WORD.findall(t)}


def soft_adjective(word: str, words: set[str]) -> bool:
    """Whether a word on -ій, -їй is a soft adjective: the translation uses its other forms («синій»: «синього»,
    «синім»). A noun's genitive plural («модифікацій») and a hard adjective's feminine dative («прямокутній») end
    the same way but have none."""
    stem = word[:-2]
    forms = ("його", "йому", "йої", "йою", "їм", "їх", "їми") if word.endswith("їй") else \
        ("ього", "ьому", "ьої", "ьою", "ім", "іх", "іми")
    return any(stem + f in words for f in forms)


def adjective_lexicon(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR,
                      texts: list[str] | None = None) -> set[str]:
    """Every masculine adjective the translation uses: words on -ий (and -ій, -їй when soft_adjective) in lower case.
    mod/Grammar tells an adjective of another gender by them («слонова» is one, «слоновий» being in here; «дочка» is
    not) when it puts a name in a case (UkrainianCases)."""
    texts = translation_texts(files, po_dir, store_dir) if texts is None else texts
    words = vocabulary(texts)
    found = {w for t in texts for w in LEXICON_WORD.findall(t)}
    return {w for w in found if w not in LEXICON_NOUNS and (w.endswith("ий") or soft_adjective(w, words))}


def noun_stems(words: set[str]) -> tuple[set[str], set[str], set[str], set[str]]:
    """Stems of the nouns the translation declines, for UkrainianCases to put a plural in the genitive by: feminine
    by their instrumental, «трубою» → «труб» (hard), «піснею» → «пісн» (soft), «тінню», «кистю» → «тін», «кист» (on a
    consonant), so «труби» → «труб», «пісні» → «пісень», «тіні» → «тіней»; masculine by a genitive plural the
    translation has, «залишків» → «залишк», so «залишки» → «залишків». An adjective's stem («великою») in here does
    no harm: no plural noun is made of it."""
    masculine = {w[:-2] for w in words if w.endswith("ів") and len(w) > 4 and "-" not in w}
    hard = {w[:-2] for w in words if w.endswith("ою") and len(w) > 4 and "-" not in w}
    soft = {w[:-2] for w in words if w.endswith("ею") and len(w) > 4 and "-" not in w}
    # a word on -а, -я with no masculine form beside it («залоза», but no «залоз», «залозом», «залозові»; «гриба» has
    # «гриб»); not on -к, where a masculine's dropped vowel hides its nominative («кілка» of «кілок»)
    hard |= {w[:-1] for w in words if w.endswith("а") and len(w) > 3 and "-" not in w and not w.endswith("ка")
             and not {w[:-1], w[:-1] + "ом", w[:-1] + "ові", w[:-1] + "ів"} & words}
    soft |= {w[:-1] for w in words if w.endswith("я") and len(w) > 3 and "-" not in w
             and not {w[:-1] + "ь", w[:-1] + "й", w[:-1] + "ем", w[:-1] + "єм", w[:-1] + "еві", w[:-1] + "ів",
                      w[:-1] + "їв"} & words}
    third = {w[:-2] for w in words if len(w) > 4 and w.endswith("ю") and w[-2] == w[-3] and w[-2] in "лнтдзсцчжш"}
    third |= {w[:-1] for w in words if len(w) > 4 and w.endswith("стю")}
    return hard - masculine, soft - masculine, third, masculine


NAME_WORD = re.compile(r"[а-щьюяєіїґА-ЩЬЮЯЄІЇҐ’'-]+")
# one noun, then «of» or a possessive before it: «statue of Bel», «apple farmer's daughter»
NOUN_FIRST = re.compile(r"^(?:(?:a|an|the|some) )?[A-Za-z’'-]+ of |^[^']+'s [A-Za-z-]+$")


def noun_lexicon(files: dict[str, str], adjectives: set[str], po_dir: pathlib.Path = PO_DIR,
                 store_dir: pathlib.Path = STORE_DIR) -> set[str]:
    """Nouns of the translation, in lower case: a name of one word («мавпа»), a word with a qud-gender note, and the
    word after a known adjective in a name («велетенська амеба» → «амеба»). UkrainianCases takes such a word for a
    noun where an unknown word before a noun would read as an adjective («дочка фермера»)."""
    nouns: set[str] = set()

    def masculine(word: str) -> set[str]:
        stem = word[:-1]
        return {stem + "ий", stem + "ій", stem + "їй"}

    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        for e in cat.entries:
            if e.obsolete or not e.msgstr:
                continue
            named = bool(DISPLAY_NAME.match(e.msgctxt or ""))
            gendered = any(QUD_GENDER.match(c) for c in e.translator_comments)
            if not (named or gendered):
                continue
            text = checks.plain_text(e.msgstr)
            words = [w.lower() for w in NAME_WORD.findall(text)]
            if len(words) == 1 and len(words[0]) > 2:
                nouns.add(words[0])
            # «statue of Bel», «sower's seed»: an English name led by its noun leads with it in Ukrainian too, the
            # genitive after it («статуя Бела», «насінина сіяча»); a capital («Кахова петля») is a possessive
            if (named and len(words) > 1 and NOUN_FIRST.match(checks.plain_text(e.msgid)) and text[:1].islower()
                    and words[0][-1:] in ("а", "я", "е", "є", "о") and not masculine(words[0]) & adjectives):
                nouns.add(words[0])
            for k, (before, word) in enumerate(zip(words, words[1:])):
                after = words[k + 2] if k + 2 < len(words) else ""
                if (before[-1:] in ("а", "я", "е", "є", "і", "ї") and masculine(before) & adjectives and len(word) > 2
                        and not masculine(word) & adjectives and not agrees(word, after)):
                    nouns.add(word)
    return {n for n in nouns if n not in adjectives}


def agrees(word: str, after: str) -> bool:
    """Whether word could be an adjective before the noun after it, by their endings («кристалосталева уламкова
    кольчуга»: «уламкова» is no noun); UkrainianCases.AgreesBeforeNoun reads a name the same way."""
    if word[-1:] in ("а", "я"):
        # -ка ends a noun (дочка, коробка) far more often than an adjective
        if word.endswith("ка") and not word.endswith(("ська", "цька", "зька")):
            return False
        return after[-1:] in ("а", "я", "ь")
    if word[-1:] in ("е", "є"):
        return after[-1:] in ("о", "е", "є", "я")
    if word[-1:] in ("і", "ї"):
        return after[-1:] in ("и", "і", "ї", "а", "я")
    return False


def adjective_lexicon_cs(words: set[str], nouns: set[str] = frozenset(),
                         stems: tuple[set[str], ...] = (frozenset(),) * 4) -> str:
    def fill(name: str, *sets: set[str]) -> str:
        params = ", ".join(f"HashSet<string> t{i}" for i in range(len(sets)))
        body = "".join(f'            t{i}.UnionWith("{" ".join(sorted(s))}".Split(\' \'));\n' for i, s in enumerate(sets))
        return f"        static partial void {name}({params})\n        {{\n{body}        }}\n"
    return ("// <auto-generated> by `py tools/qud.py build` from the words of the translation. Not in git.\n"
            "using System.Collections.Generic;\n\n"
            "namespace CavesOfQudUA.Grammar\n{\n"
            "    public static partial class AdjectiveLexicon\n    {\n"
            + fill("Fill", words) + "\n" + fill("FillNouns", nouns) + "\n" + fill("FillStems", *stems)
            + "    }\n}\n")


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


def noun_genders_cs(genders: dict[str, str], words: dict[str, str] | None = None) -> str:
    def lit(s: str) -> str:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    lines = [f"            t[{lit(bp)}] = {lit(g)};" for bp, g in sorted(genders.items())]
    word_lines = [f"            t[{lit(w)}] = {lit(g)};" for w, g in sorted((words or {}).items())]
    return ("// <auto-generated> by `py tools/qud.py build` from the qud-gender notes of the translation. Not in git.\n"
            "using System.Collections.Generic;\n\n"
            "namespace CavesOfQudUA.Grammar\n{\n"
            "    public static partial class NounGenders\n    {\n"
            "        static partial void Fill(Dictionary<string, string> t)\n        {\n"
            + "\n".join(lines) + "\n        }\n\n"
            "        static partial void FillWords(Dictionary<string, string> t)\n        {\n"
            + "\n".join(word_lines) + "\n        }\n    }\n}\n")


# --------------------------------------------------------------------------------------------
# validate

def cmd_validate(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR,
                 show_warnings: bool = True) -> tuple[int, int]:
    errors = warnings = 0
    registry, problems = held.load()
    for p in problems:
        errors += 1
        print(f"error: {p}")
    seen_held = set()
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        pname = units.po_name(name)
        for e in cat.entries:
            k = (pname, store.keys(e.msgctxt, e.msgid)[0])
            if e.obsolete or k not in registry:
                continue
            seen_held.add(k)
            if e.msgstr:
                warnings += 1
                print(f"warning: {pname}: {e.msgctxt}: held: translated now; remove it from held.tsv")
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
    for catalog, key in sorted(set(registry) - seen_held):
        if any(units.po_name(n) == catalog for n in files):
            warnings += 1
            print(f"warning: held.tsv: {catalog} {key}: no such unit in this game build; remove it")
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
        for ref in spice.unresolved(value, tree, spice.relative_base(path)):
            errors += 1
            print(f"error: HistorySpice.extra: spice.{'.'.join(path)}: reference leads nowhere: {ref}")
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        for e in cat.entries:
            if e.obsolete or not e.msgstr or ("spice" not in e.msgstr and "=^:" not in e.msgstr):
                continue
            base = spice.relative_base(e.msgctxt) if units.is_spice(name) and e.msgctxt else None
            new = set(spice.unresolved(e.msgstr, tree, base)) - set(spice.unresolved(e.msgid, tree, base))
            for ref in sorted(new):
                errors += 1
                print(f"error: {units.po_name(name)}: {e.msgctxt}: spice-path: reference leads nowhere: {ref}")
            for ref in spice.glue_references(e.msgstr):
                errors += 1
                print(f"error: {units.po_name(name)}: {e.msgctxt}: spice-path: English article or preposition, "
                      f"drop it: {ref}")
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

def cmd_stats(files: dict[str, str], po_dir: pathlib.Path = PO_DIR, store_dir: pathlib.Path = STORE_DIR,
              list_held: bool = False) -> None:
    """Progress per catalog. held: units left untranslated on purpose (translations/uk/held.tsv); the last column
    counts them as done, since nothing is left to translate there."""
    registry, _ = held.load()
    rows, listing = [], []
    for name, text in sorted(files.items()):
        cat, _ = load_catalog(text, name, po_dir, store_dir)
        pname = units.po_name(name)
        live = [e for e in cat.entries if not e.obsolete]
        done = [e for e in live if e.translated]
        fuzzy = [e for e in live if e.msgstr and e.fuzzy]
        kept = [e for e in live if not e.msgstr and (pname, store.keys(e.msgctxt, e.msgid)[0]) in registry]
        words = sum(map(_words, live))
        done_words = sum(map(_words, done))
        held_words = sum(map(_words, kept))
        rows.append((pname, len(live), len(done), len(kept), len(fuzzy), words, done_words, held_words))
        listing += [(pname, e, registry[(pname, store.keys(e.msgctxt, e.msgid)[0])]) for e in kept]
    print(f"{'file':34} {'units':>7} {'done':>7} {'held':>5} {'fuzzy':>6} {'words':>8} {'done%':>6} {'+held':>6}")
    t = [0] * 7
    for name, *r in rows:
        t = [a + b for a, b in zip(t, r)]
        n, d, h, f, w, dw, hw = r
        print(f"{name:34} {n:7} {d:7} {h:5} {f:6} {w:8} {100 * dw / w if w else 0:5.1f}% {100 * (dw + hw) / w if w else 0:5.1f}%")
    n, d, h, f, w, dw, hw = t
    print(f"{'TOTAL':34} {n:7} {d:7} {h:5} {f:6} {w:8} {100 * dw / w if w else 0:5.1f}% {100 * (dw + hw) / w if w else 0:5.1f}%")
    if list_held:
        for pname, e, h in listing:
            print(f"{h.status:4} {pname}: {e.msgctxt}: {h.reason}")


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
