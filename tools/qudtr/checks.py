"""Checks that a translation keeps the game's markup intact.

Severity:
  error   — breaks the game or the build (unbalanced {{ }}, leftover ▶, changed keys in compound
            values, a shader name that does not exist in the source, lost ~Cmd key tokens)
  warning — probably wrong, but can be deliberate (a =placeholder= dropped or added, different
            color codes, whitespace at the ends, mixed Latin/Cyrillic inside a word, apostrophe)
"""
from __future__ import annotations

import collections
import dataclasses
import pathlib
import re

from .units import MARK

PLACEHOLDER = re.compile(r"=([A-Za-z_][^=\s]*)=")
REPLACERS = pathlib.Path(__file__).with_name("replacers.tsv")  # tools/analysis/replacers.py
CASE_POSTPROCESSORS = frozenset({"capitalize", "initUpper", "initLower", "lower", "upper", "title", "capEachLine"})
SHADER_OPEN = re.compile(r"\{\{([^{}|]*)\|")
COLOR = re.compile(r"(?<!&)&([A-Za-z])|\^([A-Za-z])")
COMMAND = re.compile(r"~(?:Cmd[\w:/]+|UI:[\w:/]+)")
KEYED_PAIR = re.compile(r"(?:^|,)([^,|]*)\|" + MARK)
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


def _strip_markup(s: str) -> str:
    s = PLACEHOLDER.sub(" ", s)
    s = SHADER_OPEN.sub(" ", s)
    s = COLOR.sub(" ", s)
    s = COMMAND.sub(" ", s)
    return s


def check(msgid: str, msgstr: str, compound: bool = False) -> list[Issue]:
    issues: list[Issue] = []
    if not msgstr:
        return issues

    def err(code, msg):
        issues.append(Issue("error", code, msg))

    def warn(code, msg):
        issues.append(Issue("warning", code, msg))

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

    # {{shader|text}}
    if msgstr.count("{{") != msgstr.count("}}"):
        err("braces", f"unbalanced markup: {msgstr.count('{{')} '{{{{' vs {msgstr.count('}}')} '}}}}'")
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
    if missing:
        warn("placeholder", f"placeholder(s) missing: {sorted(missing)}")
    if extra:
        warn("placeholder", f"placeholder(s) not in the source: {sorted(extra)}")

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
