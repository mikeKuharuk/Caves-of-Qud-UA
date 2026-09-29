"""HistorySpice: the fragments the game strings together into the sultans' lives, gospels, murals and village lore.

The official ExampleLanguage files do not cover it. The game reads `Base/HistorySpice.jsonc` and then merges
every mod file named `historyspice.*` whose `"lang"` is the active language (`HistoricSpice.Init`)
**[перевірено в коді]**. `MergeModJson` appends arrays unless the key ends with "=", which replaces the value,
so the translation replaces each top-level branch that has a translated string.

Units: every string leaf under "spice" with words outside its references (`<spice.x.y>`, `<entity.name>`,
`=spice:…=`). msgctxt is the dotted key path without array indexes («spice.commonPhrases.strange»), msgid the
English text, so a unit survives reordering. Object keys are identifiers that references use; they stay.
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
    """A value a translator must see: letters left after removing its references."""
    return bool(LETTER.search(REFERENCE.sub(" ", value)))


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
        if key in seen or not is_text(value):
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


def build(text: str, name: str, translations: dict, lang: str = "uk", source_note: str = "") -> tuple[str | None, int]:
    """The mod file: {"lang", "spice": {"<branch>=": translated branch}} for branches with a translation."""
    from .units import GENERATED_MARKER
    spice = load(text)["spice"]
    out, total = {}, 0
    for branch, node in spice.items():
        counter = [0]
        translated = _translate(copy.deepcopy(node), (branch,), translations, counter)
        if counter[0]:
            out[branch + "="] = translated
            total += counter[0]
    if not out:
        return None, 0
    doc = {"_comment": f"{GENERATED_MARKER} from translations/{lang}/HistorySpice.jsonl. {source_note}".strip(),
           "lang": lang, "spice": out}
    return json.dumps(doc, ensure_ascii=False, indent=1) + "\n", total


def references(value: str) -> list[str]:
    """The references a translation must keep: <spice.x>, <entity.name>, =spice:…=."""
    return sorted(REFERENCE.findall(value))
