"""HistorySpice: the fragments the game strings together into the sultans' lives, gospels, murals and village lore.

The official ExampleLanguage files do not cover it. The game reads `Base/HistorySpice.jsonc` and then merges
every mod file named `historyspice.*` whose `"lang"` is the active language (`HistoricSpice.Init`)
**[перевірено в коді]**. `MergeModJson` appends arrays unless the key ends with "=", which replaces the value,
so the translation replaces each top-level branch that has a translated string.

Units: every string leaf under "spice" with words outside its references (`<spice.x.y>`, `<entity.name>`,
`=spice:…=`). msgctxt is the dotted key path without array indexes («spice.commonPhrases.strange»), msgid the
English text, so a unit survives reordering. Object keys are identifiers that references use; they stay.
So do the values the game reads as identifiers, which are not units (`is_identifier`).
"""
from __future__ import annotations

import copy
import json
import re

NAME = "HistorySpice.jsonc"
REFERENCE = re.compile(r"<[^<>]*>|=[A-Za-z_^][^=\s]*=")
LETTER = re.compile(r"[A-Za-z]")


def strip_comments(text: str) -> str:
    """JSONC → JSON: drop // and /* */ comments outside strings (Newtonsoft allows them, Python's json does not)."""
    out, i, n, in_str = [], 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
        elif c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif text.startswith("//", i):
            while i < n and text[i] != "\n":
                i += 1
        elif text.startswith("/*", i):
            end = text.find("*/", i + 2)
            i = n if end < 0 else end + 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def load(text: str) -> dict:
    # trailing commas are allowed by Newtonsoft too
    return json.loads(re.sub(r",(\s*[}\]])", r"\1", strip_comments(text)))


def is_text(value: str) -> bool:
    """A value a translator must see: letters left after removing its references, or two references or more,
    whose order Ukrainian may need to change («=adjectives= =nouns= =festival=»)."""
    return bool(LETTER.search(REFERENCE.sub(" ", value))) or len(REFERENCE.findall(value)) >= 2


# Keys whose values the game reads as identifiers, never shown:
#   @professions, @types, @mayorTemplate, @siteModifiers…  entity properties and the keys they select
#                                                           (=spice:professions.entity@profession.plural=,
#                                                           "SpecialVillagerHeroTemplate_" + @mayorTemplate)
#   _failureredirect, _staticfailureredirect                a spice path to fall back to
#   baseColor                                               colour codes (CreatureRegionSpice)
IDENTIFIER_KEYS = {"baseColor"}


def is_identifier(path: tuple[str, ...]) -> bool:
    return any(k.startswith(("@", "_")) for k in path) or bool(path) and path[-1] in IDENTIFIER_KEYS


def leaves(node, path: tuple[str, ...] = ()):
    """(key path without indexes, value) for every string under node."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from leaves(v, path + (k,))
    elif isinstance(node, list):
        for v in node:
            yield from leaves(v, path)
    elif isinstance(node, str):
        yield path, node


def context(path: tuple[str, ...]) -> str:
    return "spice." + ".".join(path)


def extract(text: str, name: str = NAME) -> list:
    from .units import Unit  # units dispatches here, so import lazily
    spice = load(text)["spice"]
    out, seen = [], set()
    for path, value in leaves(spice):
        key = (context(path), value)
        if key in seen or is_identifier(path) or not is_text(value):
            continue
        seen.add(key)
        out.append(Unit(file=name, msgctxt=key[0], msgid=value, kind="spice"))
    return out


def _translate(node, path: tuple[str, ...], translations: dict, counter: list):
    if isinstance(node, dict):
        return {k: _translate(v, path + (k,), translations, counter) for k, v in node.items()}
    if isinstance(node, list):
        return [_translate(v, path, translations, counter) for v in node]
    if isinstance(node, str):
        t = translations.get((context(path), node))
        if t:
            counter[0] += 1
            return t
    return node


def overlay_dir(lang: str = "uk"):
    """Our own additions to the spice: lists Ukrainian needs and English does not have, such as an adjective list
    in the feminine (docs/history.md). Only new keys; the English ones are translated through HistorySpice.po.
    One file per translator (translations/uk/HistorySpice.extra/*.json), so parallel work does not collide."""
    from .sources import REPO
    return REPO / "translations" / lang / "HistorySpice.extra"


def overlay_files(lang: str = "uk") -> list:
    d = overlay_dir(lang)
    return sorted(d.glob("*.json")) if d.exists() else []


def overlay_clashes(parts: dict[str, dict], path: tuple[str, ...] = ()) -> list[str]:
    """Key paths that two overlay files both define as a value (they would silently shadow each other)."""
    out, seen = [], {}
    for name, tree in parts.items():
        for p, _ in leaves_paths(tree):
            if p in seen and seen[p] != name:
                out.append(f"spice.{'.'.join(p)} in {seen[p]} and {name}")
            seen.setdefault(p, name)
    return out


def leaves_paths(node, path: tuple[str, ...] = ()):
    """(path, value) for every list or string value of a spice tree, lists counted as one value."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from leaves_paths(v, path + (k,))
    else:
        yield path, node


def load_overlay_parts(lang: str = "uk") -> dict[str, dict]:
    return {p.name: json.loads(p.read_text(encoding="utf-8"))["spice"] for p in overlay_files(lang)}


def load_overlay(lang: str = "uk") -> dict:
    tree: dict = {}
    for part in load_overlay_parts(lang).values():
        tree = merge(tree, part)
    return tree


def overlay_conflicts(spice_root: dict, overlay: dict, path: tuple[str, ...] = ()) -> list[str]:
    """Overlay keys that already exist in the English spice as a list or a value: they belong in HistorySpice.po."""
    out = []
    for k, v in overlay.items():
        here = spice_root.get(k) if isinstance(spice_root, dict) else None
        if here is None:
            continue
        if isinstance(v, dict) and isinstance(here, dict):
            out += overlay_conflicts(here, v, path + (k,))
        else:
            out.append(".".join(path + (k,)))
    return out


def merge(base: dict, extra: dict) -> dict:
    """base with the overlay's new keys added, recursively (the overlay never replaces a value)."""
    out = dict(base)
    for k, v in extra.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = merge(out[k], v)
        elif k not in out:
            out[k] = copy.deepcopy(v)
    return out


def build(text: str, name: str, translations: dict, lang: str = "uk", source_note: str = "",
          overlay: dict | None = None) -> tuple[str | None, int]:
    """The mod file: {"lang", "spice": {"<branch>=": translated branch}} for branches with a translation or an
    addition from the overlay."""
    from .units import GENERATED_MARKER
    spice = load(text)["spice"]
    if overlay is None:
        overlay = load_overlay(lang)
    out, total = {}, 0
    for branch, node in spice.items():
        counter = [0]
        translated = _translate(copy.deepcopy(node), (branch,), translations, counter)
        if branch in overlay and isinstance(translated, dict):
            translated = merge(translated, overlay[branch])
            counter[0] += 1
        if counter[0]:
            out[branch + "="] = translated
            total += counter[0]
    for branch, node in overlay.items():  # branches English does not have at all
        if branch not in spice:
            out[branch + "="] = copy.deepcopy(node)
    if not out:
        return None, 0
    doc = {"_comment": f"{GENERATED_MARKER} from translations/{lang}/HistorySpice.jsonl and HistorySpice.extra/. "
                       f"{source_note}".strip(),
           "lang": lang, "spice": out}
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n", total


# ---------------------------------------------------------------------------------------------------------------
# Do the references lead somewhere?

SPICE_REF = re.compile(r"=spice:([^=|\s]+)|<spice\.([^<>|\s]+)>|=spice\.set:([^:=\s]+):|=\^:([^=|\s]+)")
MODIFIERS = {"capitalize", "pluralize", "article", "title", "lower", "upper"}


def ref_segments(path: str) -> list[str]:
    """«commonPhrases.remember.!random» → [commonPhrases, remember]; variable segments become '*'."""
    segs = []
    for seg in path.split("."):
        if seg.startswith("!") or seg in MODIFIERS:
            break
        segs.append("*" if seg.startswith("$") or "@" in seg or "[" in seg else seg)
    return segs


def resolves(tree, segs: list[str]) -> bool:
    if not segs:
        return True
    head, rest = segs[0], segs[1:]
    if isinstance(tree, dict):
        if head == "*":
            return any(resolves(v, rest) for v in tree.values())
        return head in tree and resolves(tree[head], rest)
    # a list or a value: deeper segments are the engine's selectors (entity properties and the like)
    return True


def relative_base(list_path) -> str:
    """What =^:x= means inside the list at list_path: the list's parent node (HistoricSpice.ParseRelativeLinks
    appends every key of the stack but the last). list_path is a tuple of keys or a dotted "spice.a.b.c"."""
    parts = list_path.split(".") if isinstance(list_path, str) else list(list_path)
    if parts and parts[0] == "spice":
        parts = parts[1:]
    return ".".join(parts[:-1])


def unresolved(text: str, tree: dict, base: str | None = None) -> list[str]:
    """References in one string that lead nowhere in tree (the English spice with the overlay merged in). base is
    the node =^:…= is relative to (relative_base), or None when the string is not inside the spice."""
    bad = []
    for m in SPICE_REF.finditer(text):
        path = next(g for g in m.groups() if g)
        if m.group(4):
            if base is None:
                continue
            path = f"{base}.{path}" if base else path
        segs = ref_segments(path)
        if segs and segs[0] != "*" and not resolves(tree, segs):
            bad.append(path)
    return bad


def references(value: str) -> list[str]:
    """The references a translation must keep: <spice.x>, <entity.name>, =spice:…=."""
    return sorted(REFERENCE.findall(value))
