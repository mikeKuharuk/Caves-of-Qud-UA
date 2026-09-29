"""Checks that a translation keeps the game's markup intact.

Severity:
  error   — breaks the game or the build (unbalanced {{ }}, leftover ▶, changed keys in compound
            values, a shader name that does not exist in the source, lost ~Cmd key tokens, a
            translated marker the code looks for, such as *READOUT*)
  warning — probably wrong, but can be deliberate (a =placeholder= dropped or added, different
            color codes, whitespace at the ends, mixed Latin/Cyrillic inside a word, apostrophe)
"""
from __future__ import annotations

import collections
import dataclasses
import pathlib
import re
import xml.etree.ElementTree as ET

from .units import MARK, TEMPLATE_TEXT_ATTRS

PLACEHOLDER = re.compile(r"=([A-Za-z_][^=\s]*)=")
REPLACERS = pathlib.Path(__file__).with_name("replacers.tsv")  # tools/analysis/replacers.py
CASE_POSTPROCESSORS = frozenset({"capitalize", "initUpper", "initLower", "lower", "upper", "title", "capEachLine"})
SHADER_OPEN = re.compile(r"\{\{([^{}|]*)\|")
COLOR = re.compile(r"(?<!&)&([A-Za-z])|\^([A-Za-z])")
COMMAND = re.compile(r"~(?:Cmd[\w:/]+|UI:[\w:/]+)")
KEYED_PAIR = re.compile(r"(?:^|,)([^,|]*)\|" + MARK)
# Markers the game's code looks for in the text itself: a translated marker silently stops working.
# PostProcessors.CrypticMachine turns a line containing *READOUT* into machine gibberish.
CODE_MARKERS = ("*READOUT*",)
CYR = "а-яА-ЯіїєґІЇЄҐ"
MIXED_WORD = re.compile(rf"\b(?=\w*[A-Za-z])(?=\w*[{CYR}])\w+\b")
APOSTROPHE_IN_WORD = re.compile(rf"(?<=[{CYR}])(['\u02BC`])(?=[{CYR}])")
CANONICAL_APOSTROPHE = "\u2019"


@dataclasses.dataclass
class Issue:
    severity: str   # "error" | "warning"
    code: str
    message: str


def _load_capitalizable(path: pathlib.Path = REPLACERS) -> dict[str, frozenset[str]]:
    """Keys the game also registers with an upper-case first letter, by kind (replacer/post)."""
    keys: dict[str, set[str]] = {"replacer": set(), "post": set()}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            kind, key, cap, _method = line.split("\t")
            if cap == "1":
                keys[kind].add(key)
    return {k: frozenset(v) for k, v in keys.items()}


CAPITALIZABLE = _load_capitalizable()


def _fold(name: str, kind: str) -> str:
    low = name[:1].lower() + name[1:]
    return low if name != low and low in CAPITALIZABLE[kind] else name


def placeholder_key(token: str) -> str:
    """A =placeholder= with the capitalization changes the game accepts folded away.

    =stat.StatDisplayName= and =stat.statDisplayName|capitalize= are the same variable as
    =stat.statDisplayName=: the first uses the upper-case key registered for replacers with
    Capitalization = true, the second adds a post-processor that only changes letter case.
    Capitalizing any other key is kept as a difference: the game would not resolve it.
    """
    head, *posts = token.split("|")
    parts = []
    for segment in head.split("."):
        name, sep, params = segment.partition(":")
        parts.append(_fold(name, "replacer") + sep + params)
    kept = []
    for post in posts:
        name, sep, params = post.partition(":")
        if name not in CASE_POSTPROCESSORS:
            kept.append(_fold(name, "post") + sep + params)
    return "|".join([".".join(parts), *kept])


# =X.v:<3 од.>:<2 мн.>[:<3 мн.>]=, =X.g:<ч.>:<ж.>[:<с.>[:<мн.>]]=, =N.plural:<1>:<2–4>:<5+>= (mod/Grammar)
UK_GRAMMAR = re.compile(r"^(?:[A-Za-z_][\w]*\.)+(v|V|g|G|plural)(?::|$)")
UK_GRAMMAR_FORMS = {"v": (2, 3), "g": (2, 4), "plural": (3, 3)}
# English grammar the game computes for an object: a translation may drop it for Ukrainian grammar
EN_GRAMMAR = re.compile(
    r"^(?:[A-Za-z_]\w*\.)+(?:does|doesly|did|didly|verb|t|a|an|the|it|its|is|are|has|have|was|were|itis|itdoes|"
    r"this|name's|t's|indefinite|definite|subjective|objective|possessive|reflexive|substantivepossessive|"
    r"pronouns|poss|aForNPCSubject|isplural|ifplural|things|pluralize|cardinal)\b", re.I)


def placeholder_root(key: str) -> str:
    """The object a placeholder is about: =subject.Does:hit= → subject."""
    return re.split(r"[.:|#]", key, maxsplit=1)[0]


def uk_grammar_problem(key: str) -> str | None:
    """What is wrong with one of the mod's Ukrainian grammar variables, or None."""
    head = key.split("|", 1)[0]
    name = UK_GRAMMAR.match(head).group(1)
    forms = head.split(":")[1:]
    lo, hi = UK_GRAMMAR_FORMS[name.lower()]
    if not lo <= len(forms) <= hi or not all(forms):
        want = str(lo) if lo == hi else f"{lo}–{hi}"
        return f"={key}= needs {want} non-empty forms, has {len(forms)}"
    return None


def _balance(s: str) -> int:
    """How many {{ a text leaves open."""
    return s.count("{{") - s.count("}}")


def _signature(el: ET.Element) -> tuple:
    return el.tag, tuple(sorted((k, v) for k, v in el.attrib.items() if k not in TEMPLATE_TEXT_ATTRS))


def _template_text(root: ET.Element) -> str:
    """The text a template shows: its text nodes and translatable attributes, entities resolved.
    Whitespace around the blocks is not text: the game ignores it at the top level."""
    texts = ["".join(root.itertext()).strip()]
    texts += [el.get(a) for el in root.iter() for a in sorted(TEMPLATE_TEXT_ATTRS) if el.get(a)]
    return "\n".join(texts)


def _strip_markup(s: str) -> str:
    s = PLACEHOLDER.sub(" ", s)
    s = SHADER_OPEN.sub(" ", s)
    s = COLOR.sub(" ", s)
    s = COMMAND.sub(" ", s)
    return s


ACKNOWLEDGE = re.compile(r"^qud-ok:\s*([\w-]+(?:\s*,\s*[\w-]+)*)")


def check_entry(entry, msgstr: str | None = None) -> list[Issue]:
    """check() for a PO entry, the unit kind taken from its flags (qud-compound, qud-template).

    A translator comment "qud-ok: code[, code] — why" accepts those warnings for this entry: a
    deliberate deviation, reviewed once, should not stay noise. Errors cannot be accepted.
    """
    accepted = {code.strip() for c in entry.translator_comments if (m := ACKNOWLEDGE.match(c))
                for code in m.group(1).split(",")}
    issues = check(entry.msgid, entry.msgstr if msgstr is None else msgstr,
                   compound="qud-compound" in entry.flags, template="qud-template" in entry.flags)
    return [i for i in issues if i.severity == "error" or i.code not in accepted]


def check(msgid: str, msgstr: str, compound: bool = False, template: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    if not msgstr:
        return issues

    def err(code, msg):
        issues.append(Issue("error", code, msg))

    def warn(code, msg):
        issues.append(Issue("warning", code, msg))

    # XML templates: the tags are the game's; the checks below then look at the text only
    if template:
        src = ET.fromstring(f"<t>{msgid}</t>")
        try:
            dst = ET.fromstring(f"<t>{msgstr}</t>")
        except ET.ParseError as e:
            err("template-xml", f"not well-formed XML ({e}); write & as &amp; and < as &lt;")
            return issues
        src_sig = collections.Counter(map(_signature, src.iter()))
        dst_sig = collections.Counter(map(_signature, dst.iter()))
        missing, extra = src_sig - dst_sig, dst_sig - src_sig
        if extra or any(tag != "stat" for tag, _ in missing):
            err("template-structure", f"tags differ: missing {sorted(missing.elements())}, "
                f"extra {sorted(extra.elements())}")
        elif missing:
            # an English-only value such as an article (<stat Name="MineAn" />): review with qud-ok
            warn("template-stat-dropped", f"<stat> left out: {sorted(dict(a).get('Name', '?') for _, a in missing.elements())}")
        elif [_signature(c) for c in src] != [_signature(c) for c in dst]:
            warn("template-order", "the blocks (<p>, <br />, <statline>…) are in a different order")
        msgid, msgstr = _template_text(src), _template_text(dst)

    # ▶ markers
    n_src, n_dst = msgid.count(MARK), msgstr.count(MARK)
    if not compound and n_dst:
        err("marker", "leftover ▶ in the translation")
    if compound:
        alternatives = f"~{MARK}" in msgid
        if n_dst != n_src and not alternatives:
            err("marker", f"compound value: {n_src} ▶ in the source, {n_dst} in the translation")
        elif n_dst != n_src:
            warn("marker", f"alternatives: {n_src} ▶ in the source, {n_dst} in the translation")
        if n_dst and msgstr.split(MARK, 1)[0] != msgid.split(MARK, 1)[0]:
            err("compound-key", "the fixed part before the first ▶ changed: "
                f"{msgid.split(MARK, 1)[0]!r} → {msgstr.split(MARK, 1)[0]!r}")
        src_keys, dst_keys = KEYED_PAIR.findall(msgid), KEYED_PAIR.findall(msgstr)
        if src_keys and src_keys != dst_keys:
            err("compound-key", f"keys of key|▶value pairs changed: {src_keys} → {dst_keys}")

    # {{shader|text}}. A fragment may leave markup open on purpose (the preacher's prefix «{{W|'» is
    # closed by the postfix the code adds), so the translation must keep the source's balance.
    if _balance(msgstr) != _balance(msgid):
        err("braces", f"unbalanced markup: {msgstr.count('{{')} '{{{{' vs {msgstr.count('}}')} '}}}}'"
                      + (f" (the source leaves {_balance(msgid)} open)" if _balance(msgid) else ""))
    src_sh = collections.Counter(SHADER_OPEN.findall(msgid))
    dst_sh = collections.Counter(SHADER_OPEN.findall(msgstr))
    unknown = [s for s in dst_sh if s not in src_sh]
    if unknown:
        err("shader", f"shader name(s) not in the source: {unknown}")
    elif src_sh != dst_sh:
        warn("shader", f"shader usage differs: {dict(src_sh)} → {dict(dst_sh)}")

    # =placeholders=
    src_ph = collections.Counter(map(placeholder_key, PLACEHOLDER.findall(msgid)))
    dst_ph = collections.Counter(map(placeholder_key, PLACEHOLDER.findall(msgstr)))
    missing = src_ph - dst_ph
    extra = dst_ph - src_ph
    # the mod's Ukrainian grammar (docs/grammar.md) replaces English grammar: its variables are new, and an English
    # one such as =subject.Does:hit= may go as long as the translation still names the same object
    for key in [k for k in extra if UK_GRAMMAR.match(k)]:
        problem = uk_grammar_problem(key)
        if problem:
            err("uk-grammar", problem)
        del extra[key]
    # =subject.Does:hit= → =subject.Name= … : plain variables of an object whose English grammar was replaced
    replaced = {placeholder_root(k) for k in missing if EN_GRAMMAR.match(k)}
    for key in [k for k in extra if placeholder_root(k) in replaced]:
        del extra[key]
    dst_roots = {placeholder_root(k) for k in dst_ph}
    for key in [k for k in missing if EN_GRAMMAR.match(k) and placeholder_root(k) in dst_roots]:
        del missing[key]
    if missing:
        warn("placeholder", f"placeholder(s) missing: {sorted(missing)}")
    if extra:
        warn("placeholder", f"placeholder(s) not in the source: {sorted(extra)}")

    for marker in CODE_MARKERS:
        if msgid.count(marker) != msgstr.count(marker):
            err("code-marker", f"keep {marker} as it is: the game's code looks for it in the text")

    # ~Cmd key tokens (help text); '~' alternatives in dialogue are compared by count
    src_cmd = collections.Counter(COMMAND.findall(msgid))
    dst_cmd = collections.Counter(COMMAND.findall(msgstr))
    if src_cmd != dst_cmd:
        err("command", f"key tokens differ: {sorted((src_cmd - dst_cmd).elements())} missing, "
            f"{sorted((dst_cmd - src_cmd).elements())} extra")
    if not compound:
        src_tilde = msgid.count("~") - sum(src_cmd.values())
        dst_tilde = msgstr.count("~") - sum(dst_cmd.values())
        if src_tilde != dst_tilde:
            warn("alternatives", f"'~' separators: {src_tilde} in the source, {dst_tilde} in the translation")

    # &X / ^X color codes
    src_col = collections.Counter(a or b for a, b in COLOR.findall(msgid))
    dst_col = collections.Counter(a or b for a, b in COLOR.findall(msgstr))
    if src_col != dst_col:
        warn("color", f"color codes differ: {dict(src_col)} → {dict(dst_col)}")

    # whitespace at the ends matters for fragments such as " or "
    if msgid[:1].isspace() != msgstr[:1].isspace() or msgid[-1:].isspace() != msgstr[-1:].isspace():
        warn("whitespace", "leading/trailing whitespace differs from the source")

    # typography
    plain = _strip_markup(msgstr)
    mixed = MIXED_WORD.findall(plain)
    if mixed:
        warn("mixed-script", f"Latin and Cyrillic letters in one word: {mixed[:5]}")
    bad_ap = APOSTROPHE_IN_WORD.findall(plain)
    if bad_ap:
        warn("apostrophe", f"use {CANONICAL_APOSTROPHE} (U+2019) as the apostrophe, found "
             f"{sorted({f'U+{ord(c):04X}' for c in bad_ap})}")
    return issues
