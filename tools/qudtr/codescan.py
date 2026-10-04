"""English text the game's C# builds itself, found in the decompiled code (work/decompiled/<build>/Assembly-CSharp,
made with ilspycmd). Each string becomes a key of a code table (codetables.py): exact text, or a pattern where
{0}, {1}… stand for the parts the code computes («-{0} DV»). The Harmony patches look up the text the game produced
at run time (mod/Patches), so a key must be the text exactly as the game prints it.

Text that already goes through the string tables is skipped: anything inside _S(…), _T(…), Strings.…, or the old
English message of InlineLocalizationMatch / AssertLocalizationMatch (the game shows the localised one).
"""
from __future__ import annotations

import dataclasses
import pathlib
import re

HOLE = "\u0000"


@dataclasses.dataclass(frozen=True)
class Entry:
    key: str     # the English text or pattern ({0}…)
    where: str   # Class.Method, for the translator's note


# ---- C# source handling --------------------------------------------------------------------------------------

def string_end(text: str, i: int) -> int:
    """The index after the string or char literal starting at text[i] (" ' @" $" $@")."""
    verbatim = False
    j = i
    while text[j] in "$@":
        verbatim = verbatim or text[j] == "@"
        j += 1
    quote = text[j]
    j += 1
    while j < len(text):
        c = text[j]
        if verbatim and c == '"':
            if j + 1 < len(text) and text[j + 1] == '"':
                j += 2
                continue
            return j + 1
        if not verbatim and c == "\\":
            j += 2
            continue
        if c == quote:
            return j + 1
        j += 1
    return j


def literal_value(token: str) -> str | None:
    """The text of a plain C# string literal ("…" or @"…"), or None for anything else (interpolated, char)."""
    if token.startswith('@"'):
        return token[2:-1].replace('""', '"')
    if not token.startswith('"'):
        return None
    body, out, i = token[1:-1], [], 0
    escapes = {"n": "\n", "t": "\t", "r": "\r", "0": "\0", "\\": "\\", '"': '"', "'": "'"}
    while i < len(body):
        c = body[i]
        if c == "\\" and i + 1 < len(body):
            n = body[i + 1]
            if n == "u" and i + 5 < len(body):
                out.append(chr(int(body[i + 2:i + 6], 16)))
                i += 6
                continue
            out.append(escapes.get(n, n))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def mask(text: str) -> str:
    """The source with comments blanked and literals kept: indexes stay the same."""
    out, i, n = list(text), 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out[i:j] = " " * (j - i)
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out[i:j] = " " * (j - i)
            i = j
        elif text[i] in "\"'" or text[i] in "$@" and i + 1 < n and text[i + 1] in "\"$@":
            i = string_end(text, i)
        else:
            i += 1
    return "".join(out)


def matching(text: str, i: int) -> int:
    """The index of the bracket that closes the one at text[i]."""
    pairs = {"(": ")", "{": "}", "[": "]"}
    close, depth, j = pairs[text[i]], 0, i
    while j < len(text):
        c = text[j]
        if c in "\"'" or c in "$@" and j + 1 < len(text) and text[j + 1] in "\"$@":
            j = string_end(text, j)
            continue
        if c == text[i]:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return j
        j += 1
    return -1


def split_top(expr: str, sep: str) -> list[str]:
    """expr split at sep where it is outside brackets and literals."""
    parts, depth, start, j = [], 0, 0, 0
    while j < len(expr):
        c = expr[j]
        if c in "\"'" or c in "$@" and j + 1 < len(expr) and expr[j + 1] in "\"$@":
            j = string_end(expr, j)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and expr.startswith(sep, j):
            parts.append(expr[start:j])
            start = j + len(sep)
            j += len(sep)
            continue
        j += 1
    parts.append(expr[start:])
    return parts


LOCALIZED = re.compile(r"(?:\b_[TS]|Strings\._[TS]|LocalizationMatch|TemplateByID|GetString)\s*\(")


def strip_parens(expr: str) -> str:
    expr = expr.strip()
    while expr.startswith("(") and matching(expr, 0) == len(expr) - 1:
        expr = expr[1:-1].strip()
    return expr


def patterns(expr: str, nested: bool = False) -> list[str]:
    """The texts an expression can produce: literals kept, everything else a hole. A ternary gives both branches.
    An expression with no literal, or one routed through the string tables, gives nothing. nested: a ternary inside
    the concatenation gives both branches too («… on hit» + (chance < 100 ? " " + chance + "% of the time" : "")),
    where it would otherwise be one hole (the tables scanned before it keep their keys)."""
    expr = strip_parens(expr)
    if not expr:
        return []
    alternatives = split_top(expr, "??")
    if len(alternatives) > 1:
        return [p for a in alternatives for p in patterns(a, nested)]
    q = ternary(expr)
    if q:
        return patterns(q[1], nested) + patterns(q[2], nested)
    if LOCALIZED.search(expr):
        return []
    out = [""]
    found = False
    for term in split_top(expr, "+"):
        term = strip_parens(term)
        value = literal_value(term)
        inner = ternary(term) if nested and value is None else None
        options = [p for b in inner[1:] for p in patterns(b, nested) or [HOLE]] if inner else []
        if value is not None:
            found = True
            out = [o + value for o in out]
        elif any(p != HOLE for p in options):
            found = True
            out = [o + p for o in out for p in dict.fromkeys(options)][:16]
        elif term:
            out = [o + HOLE for o in out]
    return [o for o in out if found]


def ternary(expr: str) -> tuple[str, str, str] | None:
    """(condition, then, else) of a top-level «c ? a : b», or None. «?.», «?[» and «??» are not it."""
    depth, j, question = 0, 0, -1
    while j < len(expr):
        c = expr[j]
        if c in "\"'" or c in "$@" and j + 1 < len(expr) and expr[j + 1] in "\"$@":
            j = string_end(expr, j)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and c == "?" and expr[j + 1:j + 2] not in (".", "?", "[") and expr[j - 1:j] != "?":
            question = j
            break
        j += 1
    if question < 0:
        return None
    rest = split_top(expr[question + 1:], ":")
    if len(rest) < 2:
        return None
    return expr[:question], rest[0], ":".join(rest[1:])


def number_holes(text: str) -> str:
    """HOLE marks → {0}, {1}…, merging neighbours."""
    text = re.sub(HOLE + "+", HOLE, text)
    n = 0

    def repl(_):
        nonlocal n
        n += 1
        return "{" + str(n - 1) + "}"
    return re.sub(HOLE, repl, text)


def number_fields(*fields: str) -> list[str]:
    """The HOLE marks of several fields of one key → {0}, {1}… counted across all of them, so that no two holes of
    the key share a number (a translation's {n} is the key's {n}, mod/Patches/CodeText.PatternOf)."""
    return number_holes("\u0001".join(fields)).split("\u0001")


ENGLISH = re.compile(r"[A-Za-z]{2,}")


def useful(text: str) -> bool:
    plain = re.sub(r"\{\{[^|}]*\||\}\}|&[A-Za-z]|\^[A-Za-z]|=[^=\s]+=|\{\d+\}", " ", text)
    return bool(ENGLISH.search(plain))


def lines_of(text: str) -> list[str]:
    """A built text split into its lines, each one a key. A «\\r\\n» line keeps no «\\r»: CodeText looks a line up
    without it (and the XML of the string table would turn it into a space)."""
    return [line.removesuffix("\r") for line in text.split("\n") if useful(line)]


# ---- methods ------------------------------------------------------------------------------------------------

METHOD = re.compile(r"\b(?:public|protected|private|internal)\s+(?:override\s+|virtual\s+|static\s+)*string\s+(\w+)\s*\(([^)]*)\)")
CLASS = re.compile(r"\bclass\s+(\w+)")


def bodies(masked: str, names: set[str]):
    """(method name, body start, body end) for methods named in names that return a string."""
    for m in METHOD.finditer(masked):
        if m.group(1) not in names:
            continue
        j = m.end()
        while j < len(masked) and masked[j] in " \t\r\n":
            j += 1
        if masked.startswith("=>", j):
            yield m.group(1), j + 2, masked.find(";", j)
        elif j < len(masked) and masked[j] == "{":
            yield m.group(1), j + 1, matching(masked, j)


def texts_of_body(src: str, a: int, b: int) -> list[str]:
    """The texts a method body returns or builds: return expressions, and TextBuilder/StringBuilder chains
    (Append/Compound arguments joined in order)."""
    body = src[a:b]
    out = []
    for m in re.finditer(r"\breturn\b", body):
        end = split_top(body[m.end():], ";")[0]
        out += patterns(end)
    built = []
    for m in re.finditer(r"\.(?:Append|AppendLine|Compound)\s*\(", body):
        o = m.end() - 1
        c = matching(body, o)
        if c < 0:
            continue
        args = split_top(body[o + 1:c], ",")
        if m.group(0).startswith(".Compound") and len(args) > 1:
            # Compound(text, separator) puts the separator before the text when the builder is not empty
            sep = args[1].strip()
            built.append(literal_value(sep) or {"'\\n'": "\n", "' '": " "}.get(sep, " "))
        first = patterns(args[0]) if args else []
        if first:
            built.append(first[0])
            if m.group(0).startswith(".AppendLine"):
                built.append("\n")
        elif args and args[0].strip():
            built.append(HOLE)
    if built:
        out.append("".join(built))
    return out


def scan_effects(src_dir: pathlib.Path) -> list[Entry]:
    """Effect names and descriptions: DisplayName assignments and the string methods the HUD and the character
    sheet show (GetDescription, GetStateDescription, GetDetails), line by line."""
    entries: dict[str, str] = {}
    folder = src_dir / "XRL.World.Effects"
    for path in sorted(folder.glob("*.cs")) if folder.is_dir() else []:
        src = path.read_text(encoding="utf-8-sig")
        masked = mask(src)
        cls = CLASS.search(masked)
        name = cls.group(1) if cls else path.stem
        # a statement, not a parameter's default value («string DisplayName = "running"»)
        for m in re.finditer(r"(?:^|[;{}])\s*(?:this\.|base\.)?DisplayName\s*=(?!=)", masked, re.M):
            expr = split_top(src[m.end():], ";")[0]
            for p in patterns(expr):
                for line in lines_of(p):
                    entries.setdefault(number_holes(line), f"{name}.DisplayName")
        for method, a, b in bodies(masked, {"GetDescription", "GetStateDescription", "GetDetails"}):
            for text in texts_of_body(src, a, b):
                for line in lines_of(text):
                    entries.setdefault(number_holes(line), f"{name}.{method}")
            # and what each return can be, followed through locals, fields, builders in if/else and ternaries: the
            # pass above keeps the keys translated before, this one adds what it missed (Frenzied's lines, Prone's)
            for m in re.finditer(r"\breturn\b", masked[a:b]):
                expr = split_top(src[a + m.end():b], ";")[0]
                for found in computed_texts(expr, src, masked, a + m.start(), [(src, masked)]):
                    for key in code_keys(found):
                        entries.setdefault(key, f"{name}.{method}")
    return [Entry(k, w) for k, w in sorted(entries.items())]


# ---- DidX: the English narration the game conjugates itself ------------------------------------------------

DIDX_CALL = re.compile(r"(?<![\w])(DidX|DidXToY|DidXToYWithZ|XDidY|XDidYToZ|WDidXToYWithZ)\s*\(")
NAMED_ARG = re.compile(r"^\s*([A-Z]\w*)\s*:(?!:)\s*(.*)$", re.S)
# a named argument whatever its case (JournalAPI's gospelText:); the older scans keep NAMED_ARG, and their keys
ANY_NAMED_ARG = re.compile(r"^\s*([A-Za-z_]\w*)\s*:(?!:)\s*(.*)$", re.S)
KINDS = {"DidX": "X", "XDidY": "X", "DidXToY": "XZ", "XDidYToZ": "XZ", "DidXToYWithZ": "WXZ", "WDidXToYWithZ": "WXZ"}


def _is_string(arg: str) -> bool:
    return bool(patterns(arg)) or literal_value(strip_parens(arg)) is not None


def didx_fields(method: str, args: list[str], is_string=None) -> dict[str, str] | None:
    """The message fields of a DidX-family call: Verb, Preposition, IndirectPreposition, Extra, EndMark, by the
    overload the arguments select (IComponent wrappers have no Actor; Messaging statics start with it). is_string
    tells a string variable from an object one, when the caller knows the code around (a computed preposition)."""
    positional = [a for a in args if not NAMED_ARG.match(a)]
    named = {m.group(1): m.group(2) for a in args for m in [NAMED_ARG.match(a)] if m}
    if method.startswith(("X", "W")):
        if not positional or literal_value(strip_parens(positional[0])) is not None:
            return None   # the SubjectOverride overloads: a string instead of the actor
        positional = positional[1:]
    kind = KINDS[method]
    is_string = is_string or _is_string
    # the overload with a preposition: a string second, or a bare null there (no call passes a null object)
    with_preposition = len(positional) > 1 and (is_string(positional[1]) or strip_parens(positional[1]) == "null")
    if kind == "X":
        order = ["Verb", "Extra", "EndMark"]
    elif kind == "XZ":
        order = ["Verb", "Preposition", "Object", "Extra", "EndMark"] if with_preposition \
            else ["Verb", "Object", "Extra", "EndMark"]
    else:
        order = ["Verb", "DirectPreposition", "DirectObject", "IndirectPreposition", "IndirectObject", "Extra", "EndMark"] \
            if with_preposition \
            else ["Verb", "DirectObject", "IndirectPreposition", "IndirectObject", "Extra", "EndMark"]
    fields = dict(zip(order, positional))
    fields.update(named)
    if "DirectPreposition" in fields:
        fields["Preposition"] = fields.pop("DirectPreposition")
    return fields


MARKUP = re.compile(r"\{\{[^|{}]*\||\}\}|&[A-Za-z]|\^[A-Za-z]")


def member_literals(src: str, masked: str, name: str) -> list[str]:
    """The literals a class assigns to a field or property anywhere in the file: «public string Text =
    "immobilized";», «DisplayName = "{{r|bleeding}}";». For a «…Stripped» name, those of the field without the
    «Stripped», with the color markup taken off as Strip() does."""
    stripped = name.endswith("Stripped")
    base = name[:-len("Stripped")] if stripped else name
    out = []
    for m in re.finditer(rf"(?<![\w.]){re.escape(base)}\s*=(?!=)", masked):
        value = literal_value(strip_parens(split_top(src[m.end():], ";")[0]))
        if value:
            out.append(MARKUP.sub("", value) if stripped else value)
    return list(dict.fromkeys(out))


def didx_key(kind: str, verb: str, prep: str, iprep: str, extra: str, end: str) -> str:
    """The key the patch builds at run time (mod/Patches/DidXPatches.cs): null parts empty, EndMark defaults to «.»."""
    return "|".join([kind, verb, prep, iprep, extra, end])


def didx_english(kind: str, verb: str, prep: str, iprep: str, extra: str, end: str) -> str:
    """What the translator sees: the parts in English order, the participants as <subject>, <object>, <indirect>."""
    parts = ["<subject>", verb, prep]
    if kind != "X":
        parts.append("<object>")
    if kind == "WXZ":
        parts += [iprep, "<indirect>"]
    parts.append(extra)
    return " ".join(p for p in parts if p) + end


# a verb the code takes from the game's data: the slot the DidX table keys it by, and the translation fills ({v})
ANY_VERB = "*"
# _S("context", "whiz") / _T(…): a default the string tables may translate; untranslated, it is the English
LOCALIZED_DEFAULT = re.compile(r'_[ST]\s*\(\s*"(?:[^"\\]|\\.)*"\s*,\s*("(?:[^"\\]|\\.)*")\s*\)\s*$')
FIELD_DEFAULT = re.compile(r"\b(?:public|private|protected|internal)\s+(?:static\s+)?(?:readonly\s+)?string\s+(\w+)\s*=([^;]+);")
TAG_LOOKUP = re.compile(r'^(?:[\w.]+\.)?Get(?:TagOrStringProperty|TagOrProperty|StringProperty|Tag)\(\s*"([^"]+)"'
                        r'(?:\s*,\s*("(?:[^"\\]|\\.)*"))?\s*\)$')
MEMBER = re.compile(r"^[A-Za-z_]\w*\.([A-Za-z_]\w*)$")
# blueprint verbs the code passes to a method parameter, out of the scanner's reach: BootSequence.BootUI(…, Verb, …),
# Harvestable.GetVerb() into WDidXToYWithZ, a part's Verb into an effect or an event parameter, a template's =verb=
EXTRA_VERB_FIELDS = (("BootSequence", "VerbOnBootInitialized"), ("BootSequence", "VerbOnBootDone"),
                     ("BootSequence", "VerbOnBootAborted"), ("Harvestable", "HarvestVerb"), ("RefractLight", "Verb"),
                     ("ReflectProjectiles", "Verb"), ("FabricateFromSelf", "FabricateVerb"))
# the default verb a part takes from the string tables, which stays English there to key the Verbs table: «disappear»
# of TeleportTo, «harvest», «butcher», «fabricate» (the templates conjugate it through =verb|uk.v#subject=)
VERB_DEFAULT = re.compile(r'_S\(\s*"([^"]*[Dd]efault[^"]*[Vv]erb[^"]*)"\s*,\s*"([a-z][a-z ]*)"\s*\)')
# a liquid's freezing verb (Liquids.xml), which Die narrates through DidX: «The lava solidifies!»
FREEZE_VERB = re.compile(r'<freezeObject\b[^>]*\bVerb="([^"]+)"')


def default_value(rhs: str) -> str | None:
    """The English an initializer gives: a literal, or the default of a _S/_T lookup."""
    rhs = strip_parens(rhs)
    value = literal_value(rhs)
    if value is not None:
        return value
    m = LOCALIZED_DEFAULT.search(rhs)
    return literal_value(m.group(1)) if m else None


class GameData:
    """What a computed verb can be outside the method: the classes' field defaults and the blueprints' attributes
    and tags."""

    def __init__(self, src_dir: pathlib.Path, blueprints: dict[str, str] | None):
        self.defaults: dict[str, set[str]] = {}      # field → defaults, in any class
        self.class_defaults: dict[tuple[str, str], set[str]] = {}
        self.verb_defaults: dict[str, str] = {}       # a string table's default verb → its context
        for path in src_dir.rglob("*.cs"):
            text = path.read_text(encoding="utf-8-sig")
            for m in FIELD_DEFAULT.finditer(text):
                value = default_value(m.group(2))
                if value:
                    self.defaults.setdefault(m.group(1), set()).add(value)
                    self.class_defaults.setdefault((path.stem, m.group(1)), set()).add(value)
            for context, verb in VERB_DEFAULT.findall(text):
                self.verb_defaults.setdefault(verb, context)
        self.attributes: dict[str, set[str]] = {}    # attribute → values, on any part
        self.part_attributes: dict[tuple[str, str], set[str]] = {}
        self.tags: dict[str, set[str]] = {}
        self.freeze_verbs: set[str] = set()
        for text in (blueprints or {}).values():
            from .units import uncommented
            text = uncommented(text)
            self.freeze_verbs.update(FREEZE_VERB.findall(text))
            for part, attrs in re.findall(r'<part\s+Name="([^"]+)"([^>]*)>', text):
                for a, v in re.findall(r'(\w+)="([^"]*)"', attrs):
                    if v:
                        self.attributes.setdefault(a, set()).add(v)
                        self.part_attributes.setdefault((part, a), set()).add(v)
            for t, v in re.findall(r'<(?:tag|property)\s+Name="([^"]+)"\s+Value="([^"]*)"', text):
                if v:
                    self.tags.setdefault(t, set()).add(v)

    def field(self, cls: str, name: str) -> list[str]:
        """A field of the class: its default and what the blueprints set on the part of that name."""
        return sorted(self.class_defaults.get((cls, name), set()) | self.part_attributes.get((cls, name), set()))

    def member(self, name: str) -> list[str]:
        """x.Name of some other object: the defaults of any field so named and any blueprint attribute so named."""
        return sorted(self.defaults.get(name, set()) | self.attributes.get(name, set()))


def verb_sources(expr: str, src: str, masked: str, pos: int, cls: str, data: GameData,
                 depth: int = 0) -> tuple[list[str], list[str]]:
    """(the literals the code writes, the values the game's data gives) a verb expression can be."""
    expr = strip_parens(expr)
    if expr == "null" or depth > 3:
        return [], []
    value = literal_value(expr)
    if value is not None:
        return [value], []
    branches = None
    q = ternary(expr)
    if q:
        branches = [q[1], q[2]]
    elif len(split_top(expr, "??")) > 1:
        branches = split_top(expr, "??")
    if branches:
        code, given = [], []
        for b in branches:
            c, g = verb_sources(b, src, masked, pos, cls, data, depth + 1)
            code += c
            given += g
        return code, given
    m = TAG_LOOKUP.match(expr)
    if m:
        default = literal_value(m.group(2)) if m.group(2) else None
        return [], ([default] if default else []) + sorted(data.tags.get(m.group(1), set()))
    m = MEMBER.match(expr)
    if m and not expr.startswith(("this.", "base.")):
        return [], data.member(m.group(1))
    if IDENT.match(expr) or expr.startswith(("this.", "base.")):
        name = expr.split(".")[-1]
        a, b = enclosing_body(masked, pos)
        code, given = [], []
        for am in re.finditer(rf"(?<![\w.]){re.escape(name)}\s*=(?!=)", masked[a:b]):
            c, g = verb_sources(split_top(src[a + am.end():b], ";")[0], src, masked, pos, cls, data, depth + 1)
            code += c
            given += g
        return code, given + data.field(cls, name)
    return [], []


def expectation_only(args: list[str]) -> bool:
    """A call that only states the message a test expects (its last argument, ExpectMessage, a string): the player
    reads its _T twin from the string tables instead."""
    named = [a for a in args if NAMED_ARG.match(a)]
    if any(NAMED_ARG.match(a).group(1) == "ExpectMessage" for a in named):
        return True
    return len(args) > 8 and not NAMED_ARG.match(args[-1]) and literal_value(strip_parens(args[-1])) is not None


_ANALYSIS: dict = {}


def _analyse_didx(src_dir: pathlib.Path, blueprints: dict[str, str] | None):
    """The DidX keys and the data verbs of every DidX-family call, computed once per source folder."""
    cache_key = (str(src_dir), len(blueprints or {}))
    if cache_key in _ANALYSIS:
        return _ANALYSIS[cache_key]
    data = GameData(src_dir, blueprints)
    found: dict[str, tuple[str, str]] = {}
    verbs: dict[str, str] = {}
    for path in sorted(src_dir.rglob("*.cs")):
        src = path.read_text(encoding="utf-8-sig")
        if "DidX" not in src and "XDidY" not in src:
            continue
        masked = mask(src)
        cls = CLASS.search(masked)
        where = cls.group(1) if cls else path.stem
        for m in DIDX_CALL.finditer(masked):
            o = m.end() - 1
            c = matching(src, o)
            if c < 0 or masked[m.start() - 1:m.start()] in ("void ",) or re.search(r"\bvoid\s+$", masked[max(0, m.start() - 12):m.start()]):
                continue   # a declaration, not a call
            args = split_top(src[o + 1:c], ",")

            def is_string(arg: str) -> bool:
                # a literal or a pattern; or a variable declared a string here, or a string field of some class
                arg = strip_parens(arg)
                if _is_string(arg):
                    return True
                if IDENT.match(arg):
                    return bool(re.search(rf"\bstring\s+{re.escape(arg)}\b", masked))
                m2 = MEMBER.match(arg)
                return bool(m2 and m2.group(1) in data.defaults)
            fields = didx_fields(m.group(1), args, is_string)
            if not fields or "Verb" not in fields:
                continue
            literal = literal_value(strip_parens(fields["Verb"]))
            if literal:
                verb_options = [literal]
            else:
                # a verb the code computes: its literals key the message as any verb would; one the data gives
                # goes to the Verbs table and keys the message by the slot, when the player reads the DidX itself
                code, given = verb_sources(fields["Verb"], src, masked, m.start(), path.stem, data)
                for v in given:
                    verbs.setdefault(v, where)
                verb_options = list(dict.fromkeys(code))
                if given and not expectation_only(args):
                    verb_options.append(ANY_VERB)
            if not verb_options:
                continue
            kind = KINDS[m.group(1)]

            def options(name: str, default: str, expr: str | None = None) -> list[str]:
                # holes stay unnumbered here: they are counted across the key below
                expr = strip_parens(fields.get(name, "null") if expr is None else expr)
                if expr == "null":
                    return [default]
                q = ternary(expr)
                if q:   # each branch, a null one included («past» with a direction or without)
                    return list(dict.fromkeys(options(name, default, q[1]) + options(name, default, q[2])))
                own = patterns(expr)
                if own:
                    return own
                # computed: what the method assigns to the local, or the class to the field, and the field as one
                # hole, since the verb still names the message («begin {0}!»: the bleeding's own liquid term)
                found = resolve(src, masked, m.start(), expr)
                if not found and IDENT.match(expr):
                    found = member_literals(src, masked, expr)
                return found + [HOLE]
            preps = options("Preposition", "") if kind != "X" else [""]
            ipreps = options("IndirectPreposition", "") if kind == "WXZ" else [""]
            extras = options("Extra", "")
            ends = options("EndMark", ".")
            for verb in verb_options:
                shown = "<verb>" if verb == ANY_VERB else verb
                for prep in preps:
                    for iprep in ipreps:
                        for extra in extras:
                            for end in ends:
                                parts = number_fields(prep, iprep, extra, end)
                                key = didx_key(kind, verb, *parts)
                                found.setdefault(key, (didx_english(kind, shown, *parts), where))
    for cls_name, field_name in EXTRA_VERB_FIELDS:
        for v in data.field(cls_name, field_name):
            verbs.setdefault(v, cls_name)
    for v, context in sorted(data.verb_defaults.items()):
        verbs.setdefault(v, f"«{context}» у Strings")
    for v in sorted(data.freeze_verbs):
        verbs.setdefault(v, "Liquids: як застигає рідина (смерть рідини через DidX)")
    result = ([(k, e, w) for k, (e, w) in sorted(found.items())], [Entry(k, w) for k, w in sorted(verbs.items())])
    _ANALYSIS[cache_key] = result
    return result


def scan_didx(src_dir: pathlib.Path, blueprints: dict[str, str] | None = None) -> list[tuple[str, str, str]]:
    """(key, English for the translator, where) for every DidX-family call: literal verbs, verbs the code computes
    from literals, and «*» for a verb the game's data gives."""
    return _analyse_didx(src_dir, blueprints)[0]


def scan_verbs(src_dir: pathlib.Path, blueprints: dict[str, str] | None = None) -> list[Entry]:
    """The verbs the narration takes from the game's data (field defaults, blueprint attributes, tags): the Verbs
    table, with a form for each person, fills the «*» templates and =verb|uk.v#X=."""
    return _analyse_didx(src_dir, blueprints)[1]


# ---- Text: popups, failure messages and the message log ------------------------------------------------------

SINK_CALL = re.compile(
    r"(?<![\w])((?:Popup\.)(?:Show|ShowFail|ShowBlock|ShowYesNo|ShowYesNoCancel|ShowBlockPrompt|ShowBlockSpace|"
    r"ShowBlockWithCopy|WarnYesNo|AskString|AskNumber|ShowAsync|ShowFailAsync|ShowYesNoAsync|ShowYesNoCancelAsync|"
    r"AskStringAsync|AskNumberAsync|ShowSpace|PickOption|PickOptionAsync|ShowOptionList)|(?:[\w.]+\.)?Fail|"
    r"(?:MessageQueue\.|IComponent<GameObject>\.)?AddPlayerMessage|(?:[\w.]+\.)?EmitMessage|"
    r"(?:[\w.]+\.)?DisplayMessage)\s*\(")   # DisplayMessage: journal notices («You note the location of…»)
SKIP_FILE = re.compile(r"Wish|Debug|Test|Cheat|MapEditor")
STRING_ARRAY = re.compile(r"new\s+(?:string\s*\[\s*\d*\s*\]|List<string>(?:\s*\(\s*\))?)\s*\{")
# where an option list, and the intro above it, go among a popup's positional arguments
OPTIONS_INDEX = {"PickOption": 4, "PickOptionAsync": 3, "ShowOptionList": 1}
INTRO_INDEX = {"PickOption": 1, "PickOptionAsync": 1, "ShowOptionList": 4}


def local_options(src: str, masked: str, pos: int, name: str) -> list[str]:
    """The texts a local option list gets in the method around pos: the arrays assigned to it («options = new
    string[5] { "Control Mapping", … }») and what it Adds."""
    a, b = enclosing_body(masked, pos)
    body, mbody = src[a:b], masked[a:b]
    out = []
    for m in re.finditer(rf"(?<![\w.]){re.escape(name)}\s*=(?!=)\s*", mbody):
        arr = STRING_ARRAY.match(mbody, m.end())
        if arr:
            start = arr.end() - 1
            for item in split_top(body[start + 1:matching(body, start)], ","):
                out += patterns(item)
    for m in re.finditer(rf"(?<![\w.]){re.escape(name)}\s*\.\s*Add\s*\(", mbody):
        o = m.end() - 1
        out += patterns(body[o + 1:matching(body, o)])
    return out
IDENT = re.compile(r"^[A-Za-z_]\w*$")
BUILT = re.compile(r"^([A-Za-z_]\w*)\.ToString\(\)$")
METHOD_HEAD = re.compile(r"\)\s*(?:where[^{]*)?$")
CONTROL = re.compile(r"\b(?:if|for|foreach|while|switch|catch|using|lock|else|do|try|finally)\s*(?:\(|$)")


def enclosing_body(masked: str, pos: int) -> tuple[int, int]:
    """The span of the method body around pos: the innermost {…} whose head ends with a parameter list and is not
    a control statement. The whole file if none."""
    depth_starts, j, best = [], 0, (0, len(masked))
    stack = []
    for j, c in enumerate(masked):
        if j >= pos and not stack:
            break
        if c == "{":
            stack.append(j)
        elif c == "}" and stack:
            start = stack.pop()
            if start < pos < j:
                head = masked[max(0, start - 300):start].rstrip()
                line = head[head.rfind("\n") + 1:] if "\n" in head else head
                if METHOD_HEAD.search(head) and not CONTROL.search(line):
                    if j - start < best[1] - best[0]:
                        best = (start + 1, j)
    # blocks still open at pos also enclose it
    for start in stack:
        end = matching(masked, start)
        if end > pos:
            head = masked[max(0, start - 300):start].rstrip()
            line = head[head.rfind("\n") + 1:] if "\n" in head else head
            if METHOD_HEAD.search(head) and not CONTROL.search(line) and end - start < best[1] - best[0]:
                best = (start + 1, end)
    return best


def resolve(src: str, masked: str, pos: int, expr: str) -> list[str]:
    """The texts an argument can be: its own patterns; for a local variable, what the method assigns to it; for
    builder.ToString(), the Append chain of that builder in the method."""
    expr = strip_parens(expr)
    found = patterns(expr)
    if found:
        return found
    a, b = enclosing_body(masked, pos)
    body, mbody = src[a:b], masked[a:b]
    if IDENT.match(expr):
        out = []
        for m in re.finditer(rf"(?<![\w.]){re.escape(expr)}\s*=(?!=)", mbody):
            out += patterns(split_top(body[m.end():], ";")[0])
        return out
    m = BUILT.match(expr)
    if m:
        name = m.group(1)
        built = []
        for call in re.finditer(rf"(?<![\w]){re.escape(name)}\s*\.(Append|AppendLine|Compound)\s*\(|\)\s*\.(Append|AppendLine|Compound)\s*\(", mbody):
            o = call.end() - 1
            c = matching(body, o)
            if c < 0:
                continue
            args = split_top(body[o + 1:c], ",")
            method = call.group(1) or call.group(2)
            if method == "Compound" and len(args) > 1:
                sep = args[1].strip()
                built.append(literal_value(sep) or {"'\n'": "\n", "' '": " "}.get(sep, " "))
            if args and args[0].strip():   # AppendLine() adds the line break alone
                ps = patterns(args[0])
                built.append(ps[0] if ps else HOLE)
            if method == "AppendLine":
                built.append("\n")
        return ["".join(built)] if any(p not in (HOLE, "\n", " ") for p in built) else []
    return []


def specific(text: str) -> bool:
    """A key the patch may look up: English words, and, for a pattern, enough fixed text that it cannot swallow
    unrelated lines («You {0}» could)."""
    if not useful(text):
        return False
    if "{0}" not in text:
        return True
    literal = re.sub(r"\{\d+\}|\{\{[^|}]*\||\}\}", " ", text)
    words = re.findall(r"[A-Za-z]{2,}", literal)
    # a pattern matches the whole line (^…$), so two words of fixed text are enough: «You receive {0}!»
    return len(words) >= 3 or len(words) == 2 and len("".join(words)) >= 6


# ---- A builder across if/else: the hit message Combat assembles piece by piece ---------------------------------

def closing(masked: str, i: int, b: int) -> int:
    """The bracket that closes the one at i, or b when it lies past b (a range cut inside a block)."""
    j = matching(masked, i)
    return j if 0 <= j < b else b


def statement_end(masked: str, i: int, b: int) -> int:
    """Where the statement at i ends (just past it): a {block}, an if/else chain, or up to its «;»."""
    while i < b and masked[i] in " \t\r\n":
        i += 1
    if i >= b:
        return b
    if masked[i] == "{":
        return min(closing(masked, i, b) + 1, b)
    if re.match(r"if\s*\(", masked[i:i + 8]):
        p = masked.index("(", i)
        j = statement_end(masked, closing(masked, p, b) + 1, b)
        k = j
        while k < b and masked[k] in " \t\r\n":
            k += 1
        if re.match(r"else\b", masked[k:k + 5]):
            return statement_end(masked, k + 4, b)
        return j
    depth, j = 0, i
    while j < b:
        c = masked[j]
        if c in "\"'" or c in "$@" and j + 1 < b and masked[j + 1] in "\"$@":
            j = string_end(masked, j)   # «"{{g|You"» holds braces
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth == 0:
            return j + 1
        j += 1
    return b


def statements(masked: str, a: int, b: int):
    """The statements of masked[a:b] in order: ("if", [(condition, start, end)…], else (start, end) or None),
    ("block", start, end) or ("stmt", start, end)."""
    i = a
    while i < b:
        while i < b and masked[i] in " \t\r\n":
            i += 1
        if i >= b:
            return
        if re.match(r"if\s*\(", masked[i:i + 8]):
            branches, other = [], None
            while True:
                p = masked.index("(", i)
                q = closing(masked, p, b)
                end = statement_end(masked, q + 1, b)
                branches.append((re.sub(r"\s+", " ", masked[p + 1:q]).strip(), q + 1, end))
                k = end
                while k < b and masked[k] in " \t\r\n":
                    k += 1
                if not re.match(r"else\b", masked[k:k + 5]):
                    i = end
                    break
                k += 4
                while k < b and masked[k] in " \t\r\n":
                    k += 1
                if re.match(r"if\s*\(", masked[k:k + 8]):
                    i = k
                    continue
                other = (k, statement_end(masked, k, b))
                i = other[1]
                break
            yield ("if", branches, other)
        elif masked[i] == "{":
            j = closing(masked, i, b)
            yield ("block", i + 1, j)
            i = j + 1
        else:
            j = statement_end(masked, i, b)
            yield ("stmt", i, j)
            i = j


def third_person(verb: str) -> str:
    """The English third person singular the game's GetVerb gives: «hit» → «hits», «miss» → «misses»."""
    if re.search(r"(?:s|sh|ch|x|z|o)$", verb):
        return verb + "es"
    if re.search(r"[^aeiou]y$", verb):
        return verb[:-1] + "ies"
    return verb + "s"


GET_VERB = re.compile(r'^[\w.]+\.GetVerb\(\s*"([^"]+)"\s*(?:,\s*PrependSpace:\s*(true|false))?\s*\)$')
SEPARATOR = "separator"   # (SEPARATOR, text): a Compound's separator, there only after some text
PARAMETER_DEFAULT = re.compile(r'\.GetStringParameter\(\s*"(\w+)"\s*,\s*("(?:[^"\\]|\\.)*")\s*\)$')
# an event parameter with this many values or fewer is spelled out where a builder appends it (ShowDamageType:
# «damage» and two more); one with more stays a hole (Message: the damage tails)
FEW_VALUES = 4


def appended(src: str, masked: str, var: str, s: int, e: int, values: dict | None = None):
    """What one statement adds to the builder var: a list of option lists (one per piece), "clear", or None when
    it leaves var alone. A call that takes the builder writes into it: its_(Weapon, sb) a pronoun and a name. A
    local read from an event parameter («E.GetStringParameter("ShowDamageType", "damage")») is its default or
    one of the few values the code passes (values: parameter → literals)."""
    text, mtext = src[s:e], masked[s:e]
    if re.match(rf"\s*{re.escape(var)}\s*\.\s*Clear\s*\(", mtext):
        return "clear"
    passed = re.search(rf"\b(\w+)\s*\([^;]*\b{re.escape(var)}\s*\)", mtext)
    if passed and not re.match(rf"\s*{re.escape(var)}\s*\.", mtext):
        return [[HOLE + " " + HOLE]] if passed.group(1) == "its_" else [[HOLE]]
    if not re.match(rf"\s*{re.escape(var)}\s*\.", mtext):
        return None
    parts = []
    for m in re.finditer(r"\.(Append|AppendLine|Compound|AppendPrefixed|AppendRange)\s*\(", mtext):
        o = m.end() - 1
        c = matching(text, o)
        if c < 0:
            continue
        args = split_top(text[o + 1:c], ",")
        arg = args[0].strip() if args and args[0].strip() else ""
        if m.group(1) in ("AppendPrefixed", "AppendRange"):
            # a list of items the code computes, each after the prefix («\n{{y|:}} » before a mod's title) or between
            # them: one hole, after the prefix's own text
            prefix = literal_value(args[1].strip()) if m.group(1) == "AppendPrefixed" and len(args) > 1 else None
            parts.append([(prefix or "") + HOLE])
            continue
        if m.group(1) == "Compound":
            # the separator goes before the text only when the builder is not empty (a SEPARATOR the paths resolve);
            # «"\n\n"» keeps the lines apart, and with none given it is a space
            sep = args[1].strip() if len(args) > 1 else "' '"
            sep_char = CHAR.match(sep)
            parts.append([(SEPARATOR, literal_value(sep) if literal_value(sep) is not None
                           else {"\\n": "\n"}.get(sep_char.group(1), sep_char.group(1)) if sep_char else " ")])
        if arg:
            char = CHAR.match(arg)
            verb = GET_VERB.match(arg)
            if char:
                parts.append([{"\\n": "\n"}.get(char.group(1), char.group(1))])
            elif verb:
                space = "" if verb.group(2) == "false" else " "
                parts.append([space + third_person(verb.group(1)), space + verb.group(1)])
            elif IDENT.match(arg) and values is not None:
                parts.append(parameter_values(src, masked, arg, s, values) or [HOLE])
            else:
                parts.append(patterns(arg, nested=True) or [HOLE])
        if m.group(1) == "AppendLine":
            parts.append(["\n"])
    return parts


def parameter_values(src: str, masked: str, name: str, pos: int, values: dict) -> list[str]:
    """The texts a local holds when the method last set it from an event parameter: the default and the few
    values passed for it; nothing otherwise."""
    a, _ = enclosing_body(masked, pos)
    sets = list(re.finditer(rf"(?<![\w.]){re.escape(name)}\s*=(?!=)", masked[a:pos]))
    if not sets:
        return []
    rhs = split_top(src[a + sets[-1].end():pos], ";")[0].strip()
    m = PARAMETER_DEFAULT.search(rhs)
    if not m or len(values.get(m.group(1), ())) > FEW_VALUES:
        return []
    return list(dict.fromkeys([literal_value(m.group(2))] + sorted(values.get(m.group(1), ()))))


def builder_paths(src: str, masked: str, var: str, a: int, b: int, cap: int = 64,
                  values: dict | None = None) -> list[str]:
    """Every text the builder var can hold after src[a:b]: its pieces in order, each if/else taking each of its
    branches (and none, without an else). A condition decided once keeps its value along the path («if
    (!TerseMessages)» twice), so no impossible mix comes out."""
    touches = re.compile(rf"(?<![\w.]){re.escape(var)}\b")

    def run(a: int, b: int, paths: list) -> list:
        for kind, *rest in statements(masked, a, b):
            if kind == "if":
                span = (rest[0][0][1], rest[1][1] if rest[1] else rest[0][-1][2])
            else:
                span = (rest[0], rest[1])
            if kind != "stmt" and not touches.search(masked, *span):
                continue   # a block that leaves the builder alone: its conditions do not matter here
            if kind == "stmt":
                parts = appended(src, masked, var, rest[0], rest[1], values)
                if parts == "clear":
                    paths = [("", d) for _, d in paths]
                elif parts:
                    for options in parts:
                        paths = [(t + (o[1] if t else "") if isinstance(o, tuple) else t + o, d)
                                 for t, d in paths for o in options][:cap]
            elif kind == "block":
                paths = run(rest[0], rest[1], paths)
            else:
                branches, other = rest
                out = []
                for text, decided in paths:
                    d, taken = dict(decided), False
                    for cond, s, e in branches:
                        if cond in d:
                            if d[cond]:
                                out += run(s, e, [(text, d)])
                                taken = True
                                break
                            continue
                        out += run(s, e, [(text, {**d, cond: True})])
                        d[cond] = False
                    if not taken:
                        out += run(other[0], other[1], [(text, d)]) if other else [(text, d)]
                paths = out[:cap]
        return paths
    return list(dict.fromkeys(t for t, _ in run(a, b, [("", {})])))


PERCENT_CODE = re.compile(r"%[tToOdSe]")
MESSAGE_PARAM = re.compile(r'\.SetParameter\(\s*"Message",\s*(\w+)\.ToString\(\)\s*\)')
NAMED_LITERAL = re.compile(r'\b(\w+):\s*("(?:[^"\\]|\\.)*")')
SET_LITERAL = re.compile(r'\.SetParameter\(\s*"(\w+)"\s*,\s*("(?:[^"\\]|\\.)*")\s*\)')


def parameter_literals(sources) -> dict[str, set[str]]:
    """The literals the code passes for each named argument and event parameter, by name: what a builder may read
    back from an event (parameter_values)."""
    values: dict[str, set[str]] = {}
    for src in sources:
        for pattern in (NAMED_LITERAL, SET_LITERAL):
            for m in pattern.finditer(src):
                value = literal_value(m.group(2))
                if value is not None:
                    values.setdefault(m.group(1), set()).add(value)
    return values


def builder_texts(src: str, masked: str, var: str, pos: int, values: dict) -> list[str]:
    """builder_paths of var up to pos, from its declaration: a method may reuse the name in another block."""
    a, _ = enclosing_body(masked, pos)
    decls = list(re.finditer(rf"\b(?:TextBuilder|StringBuilder|var)\s+{re.escape(var)}\s*=", masked[a:pos]))
    if decls:
        a = masked.index(";", a + decls[-1].end()) + 1
    return builder_paths(src, masked, var, a, pos, values=values)


def scan_text(src_dir: pathlib.Path) -> list[Entry]:
    """Popups, failure messages and message-log lines the game's C# writes, line by line (CodeText splits a text
    into lines when the whole is not a key). A builder's text is followed through if/else as well
    (builder_paths). Also the hit message Combat builds for TakeDamage to show (SetParameter("Message",
    sb.ToString())): Physics puts the attacker's name for its %T."""
    entries: dict[str, str] = {}
    files = []
    for path in sorted(src_dir.rglob("*.cs")):
        rel = path.relative_to(src_dir).as_posix()
        if not SKIP_FILE.search(rel) and not rel.startswith(("XRL.Wish", "XRL.Tests")):
            files.append((path, path.read_text(encoding="utf-8-sig")))
    values = parameter_literals(src for _, src in files)
    for path, src in files:
        if not SINK_CALL.search(src) and not MESSAGE_PARAM.search(src):
            continue
        masked = mask(src)
        cls = CLASS.search(masked)
        where = cls.group(1) if cls else path.stem
        for m in SINK_CALL.finditer(masked):
            name = m.group(1)
            if masked[m.start() - 1:m.start()] == ")" or re.search(r"\)\s*\.\s*$", masked[max(0, m.start() - 8):m.start()]):
                continue   # a ReplaceBuilder chain: the string tables already did it
            if re.search(r"\b(?:void|Keys|Task|bool|string)\s+(?:\w+\s+)*$", masked[max(0, m.start() - 40):m.start()]):
                continue   # a declaration
            o = m.end() - 1
            c = matching(src, o)
            if c < 0:
                continue
            args = split_top(src[o + 1:c], ",")
            exprs = []
            if name.endswith("EmitMessage"):
                exprs = args[:2]
            elif args:
                exprs = [args[0]]
            exprs += [mm.group(2) for a in args for mm in [NAMED_ARG.match(a)] if mm and mm.group(1) in ("Title", "Intro", "Prompt", "Message", "Msg")]
            texts = []
            for e in exprs:
                if NAMED_ARG.match(e) and not NAMED_ARG.match(e).group(1) in ("Title", "Intro", "Prompt", "Message", "Msg"):
                    continue
                texts += resolve(src, masked, m.start(), e)
                built = BUILT.match(strip_parens(e))
                if built:
                    texts += builder_texts(src, masked, built.group(1), m.start(), values)
            # an option list given in place; not an array inside another argument (HotkeySpread.get(new string[2] {
            # "Menus", "UINav" }) names input layers)
            for a in args:
                named = ANY_NAMED_ARG.match(a)
                value = (named.group(2) if named else a).strip()
                arr = STRING_ARRAY.match(value)
                if arr:
                    for item in split_top(value[arr.end():matching(value, arr.end() - 1)], ","):
                        texts += patterns(item)
            # an option list the method fills in a local first (the system menu's «Save and Quit»), and the intro
            # above the options, which is not the first argument («Instruct … to follow at what distance?»)
            short = name.split(".")[-1]
            if short in OPTIONS_INDEX:
                positional = [a for a in args if not ANY_NAMED_ARG.match(a)]
                options = next((mm.group(2) for a in args for mm in [ANY_NAMED_ARG.match(a)] if mm and mm.group(1) == "Options"), None)
                if options is None and len(positional) > OPTIONS_INDEX[short]:
                    options = positional[OPTIONS_INDEX[short]]
                if options is not None and IDENT.match(options.strip()):
                    texts += local_options(src, masked, m.start(), options.strip())
                if len(positional) > INTRO_INDEX[short]:
                    intro = positional[INTRO_INDEX[short]]
                    built = BUILT.match(strip_parens(intro))
                    texts += (builder_texts(src, masked, built.group(1), m.start(), values) if built
                              else resolve(src, masked, m.start(), intro))
            for text in texts:
                for line in lines_of(text):
                    key = number_holes(line)
                    if specific(key):
                        entries.setdefault(key, f"{where} ({name.split('.')[-1]})")
        for m in MESSAGE_PARAM.finditer(masked):
            for text in builder_texts(src, masked, m.group(1), m.start(), values):
                for line in lines_of(PERCENT_CODE.sub(HOLE, text)):
                    key = number_holes(line)
                    if specific(key):
                        entries.setdefault(key, f"{where} (TakeDamage Message)")
    return [Entry(k, w) for k, w in sorted(entries.items())]


# ---- Words: short names the code keeps in constants, shows as they are or puts into a hole -----------------------

GAME_MODE = ("режим гри (ID зі стану GameMode): рядок збереження на екрані завантаження, «Рівень 1, …»; "
             "з малої, з іменником: «класичний режим»")
LAID_GRENADE = ("Tinkering_LayMine: чим стає закладена граната (mine — без таймера, bomb — з таймером); стає на місце "
                "«граната» в її назві, тож іменник жіночого роду: «{{W|фугасна}} міна Mk I»")

# (file, pattern, where): each a constant the player reads
WORD_SOURCES = (
    # the journal's tabs: the screen's title shows them as they are (JournalScreen.GetTabDisplayName), and the «noted
    # in the section of your journal» messages put them into a hole
    ("XRL.UI/JournalScreen.cs", re.compile(r'static readonly string STR_\w+ = "([^"]+)";'),
     "JournalScreen: вкладка журналу"),
    # the long blade stances, which the stance narration puts into a hole («switch to the aggressive stance»)
    ("XRL.World.Parts/LongBladesCore.cs", re.compile(r'const string STR_\w+ = "([^"]+)";'),
     "LongBladesCore: стійка довгих клинків"),
    # what flies you, in the flight ability's name: «Fly (Cathedra)»
    ("XRL.World.Parts/CyberneticsCathedra.cs", re.compile(r'FlightSourceDescription => "([^"]+)";'),
     "CyberneticsCathedra: чим ви летите, у назві здібності «Політ (…)»"),
    # how a faction now regards you, in «You are now {{G|favored}} by …» and «… is now … to you»
    ("XRL.World/Reputation.cs", re.compile(r'\btext = "([a-z]+)";'),
     "Reputation: як фракція тепер до вас ставиться (прислівник: «прихильно», «байдуже»)"),
    # the game mode a save names on the load screen («Рівень 1, =gamemode|uk.word=»): the ID the code compares
    ("XRL/XRLGame.cs", re.compile(r'GetStringGameState\("GameMode", "(\w+)"\)'), GAME_MODE),
    ("XRL/CheckpointingSystem.cs", re.compile(r'stringGameState [!=]= "(\w+)"'), GAME_MODE),
    ("XRL.CharacterBuilds.Qud/QudGamemodeModule.cs", re.compile(r'\bMode [!=]= "(\w+)"'), GAME_MODE),
    ("XRL.CharacterBuilds.Qud/QudGamemodeModuleData.cs", re.compile(r'\bMode [!=]= "(\w+)"'), GAME_MODE),
    # the inventory filter's first button, «ALL»
    ("Qud.UI/FilterBarCategoryButton.cs", re.compile(r'categoryTextMap = new Dictionary<string, string> '
                                                     r'\{ \{ "\*All", "([^"]+)" \} \}'),
     "FilterBarCategoryButton: кнопка фільтра «усі категорії» в інвентарі (великими, як в оригіналі)"),
    # what a mine-laying robot is, after the kind of its grenade: «{{W|фугасний}} мінер Mk I» (mod/Patches/MinerPatches)
    ("XRL.World.Parts/Miner.cs", re.compile(r'MineName \+ "(\w+) mk "'),
     "Miner: робот, що ставить міни (miner) чи бомби з таймером (bomber), — іменник після прикметника гранати"),
    # what a laid grenade becomes, in place of «граната» in its name: «{{W|фугасна}} міна Mk I»
    ("XRL.World.Parts.Skill/Tinkering_LayMine.cs", re.compile(r'\(Countdown > 0\) \? "(\w+)"'), LAID_GRENADE),
    ("XRL.World.Parts.Skill/Tinkering_LayMine.cs", re.compile(r'\(Countdown > 0\) \? "\w+" : "(\w+)"'), LAID_GRENADE),
)
BREATH_NAME = re.compile(r'override string GetBreathName\(\)\s*\{\s*return "([^"]+)";')
# labels a Unity prefab carries, which no code or table holds; the mod sets them (mod/Patches/TextPatches.cs)
PREFAB_WORDS = (
    ("delete", "SaveManagementRow: кнопка видалення збереження на екрані завантаження (з малої, як в оригіналі)"),
    ("Mods Differ", "SaveManagementRow: позначка в рядку збереження, коли моди збереження й гри різні"),
)
STAT_VALUE = re.compile(r'\bstats\.Set\("(\w+)",\s*"([^"]+)"')
STAT_WORDS = re.compile(r"[A-Za-z][a-z]*(?:[ /.]+[A-Za-z][a-z]*)*\.?")


def scan_words(src_dir: pathlib.Path) -> list[Entry]:
    """Words the code keeps in constants and the player reads as they are: the journal's tabs, the stances, what
    a breath is made of («a cone of confusion gas»). CodeText translates a hole that holds one exactly."""
    entries: dict[str, str] = {}
    for rel, pattern, where in WORD_SOURCES:
        path = src_dir / rel
        if path.exists():
            for m in pattern.finditer(path.read_text(encoding="utf-8-sig")):
                entries.setdefault(m.group(1), where)
    for path in sorted((src_dir / "XRL.World.Parts.Mutation").glob("*Breather.cs")):
        for m in BREATH_NAME.finditer(path.read_text(encoding="utf-8-sig")):
            entries.setdefault(m.group(1), f"{path.stem}.GetBreathName: з чого подих")
    for word in DAMAGE_TYPES:
        entries.setdefault(word, "ElementalDamage: тип шкоди в «{0} {1} damage» (родовий, як «вогню»)")
    for word, where in PREFAB_WORDS:
        entries.setdefault(word, where)
    # a statistic's value an ability's description shows as it is («Range: sight», «Cooldown: once per night»):
    # words, not the identifiers a template switches on («Pistol», «TrashDivining»)
    for path in sorted(src_dir.rglob("*.cs")):
        text = path.read_text(encoding="utf-8-sig")
        if "stats.Set(" not in text:
            continue
        for key, value in STAT_VALUE.findall(text):
            if len(value) >= 3 and STAT_WORDS.fullmatch(value) and (" " in value or value.islower()):
                entries.setdefault(value, f"{path.stem}: значення рядка статистики «{key}» в описі здібності")
    # a power line's words, in its rules line («Contains wiring enabling it to function as part of a power grid…»)
    for path in sorted((src_dir / "XRL.World.Parts").glob("*PowerTransmission.cs")):
        for field, value in POWER_FIELD.findall(path.read_text(encoding="utf-8-sig")):
            if field == "Assembly":   # through Grammar.A
                value = ("an " if value[0] in "aeiou" else "a ") + value
            entries.setdefault(value, f"{path.stem}.{field}: {POWER_ROLES[field]}")
    return [Entry(k, w) for k, w in sorted(entries.items())]


POWER_FIELD = re.compile(r'\b(Constituent|Assembly|Substance|Activity) = "([^"]+)";')
POWER_ROLES = {"Constituent": "що містить лінія (знахідний: «проводку»)",
               "Assembly": "частиною якої системи вона є (називний, у лапках)",
               "Substance": "що вона передає (знахідний: «заряд», «енергію»)",
               "Activity": "що вона робить (3-тя особа: «проводить»)"}


# the damage types ElementalDamage puts into a rules line in lower case («deals 1d4 acid damage»): the blueprints'
# Attributes of that part («fire» is a breath's word already)
DAMAGE_TYPES = ("acid", "cold", "cosmic", "electric", "heat", "umbral")


# ---- Abilities: what the code names an activated ability ----------------------------------------------------------

ABILITY_CALL = re.compile(r"(?<![\w])(AddMyActivatedAbility|AddActivatedAbility|AddAbility|SetMyActivatedAbilityDisplayName|"
                          r"SetActivatedAbilityDisplayName)\s*\(")
SUBCLASS = re.compile(r"\bclass\s+\w+\s*:\s*(\w+)")
CALLED = re.compile(r"^(\w+)\s*\([^()]*\)$")
# names the string tables keep English because code compares them, which reach AddAbility as English all the same
EXTRA_ABILITY_NAMES = (
    ("Jump", "GetJumpingBehaviorEvent: назва здібності (у Strings лишається «Jump»: з ним порівнює Wings)"),
)


def joined(parts: list[list[str]], cap: int = 16) -> list[str]:
    """Every text a chain of pieces can make, one option from each («Activate»/«Deactivate», then a hole)."""
    out = [""]
    for options in parts:
        out = [o + p for o in out for p in options][:cap]
    return out


CHAR = re.compile(r"^'(\\?.)'$")


def parameters(masked: str, body_start: int) -> set[str]:
    """The parameter names of the method whose body starts at body_start: the last (…) before it."""
    close = masked.rfind(")", 0, body_start)
    depth = 0
    for k in range(close, -1, -1):
        if masked[k] == ")":
            depth += 1
        elif masked[k] == "(":
            depth -= 1
            if depth == 0:
                names = set()
                for p in split_top(masked[k + 1:close], ","):
                    words = re.findall(r"\w+", split_top(p, "=")[0])
                    if len(words) >= 2:
                        names.add(words[-1])
                return names
    return set()


def built_texts(body: str) -> list[str]:
    """What a method returns, its literal returns and the TextBuilder chain it builds, every branch of a ternary
    in the chain included (texts_of_body keeps only the first). Nothing when it returns what the string tables give:
    a chain beside that is only the English it is checked against (ForceEmitter's InlineLocalizationMatch)."""
    returns = [split_top(body[m.end():], ";")[0] for m in re.finditer(r"\breturn\b", body)]
    if any(LOCALIZED.search(r) for r in returns) or "LocalizationMatch" in body:
        return []   # (MeleeWeapon.GetDetailedStats builds its English only to check its _T twin against it)
    out = [p for r in returns for p in patterns(r, nested=True)]
    parts = []
    for m in re.finditer(r"\.(?:Append|Compound)\s*\(", body):
        o = m.end() - 1
        c = matching(body, o)
        if c < 0:
            continue
        args = split_top(body[o + 1:c], ",")
        arg = args[0].strip() if args else ""
        char = CHAR.match(arg)
        if char:
            parts.append([{"\\n": "\n"}.get(char.group(1), char.group(1))])
        else:
            parts.append(patterns(arg, nested=True) or [HOLE])
    if any(p != [HOLE] for p in parts):
        out += joined(parts)
    return out


def computed_texts(expr: str, src: str, masked: str, pos: int, family: list[tuple[str, str]], depth: int = 0) -> list[str]:
    """What a name expression can be: its literals and patterns; for a local, what the method assigns to it; for a
    field, what the class and its subclasses assign (UrchinBelcher: CommandName = "Belch Urchins"); for a method of
    the class or of a subclass (the breathers' GetCommandDisplayName), what it returns or builds. Text the string
    tables give (_S, _T) is theirs."""
    expr = strip_parens(expr)
    if depth > 3 or expr in ("", "null") or LOCALIZED.search(expr):
        return []
    q = ternary(expr)
    branches = [q[1], q[2]] if q else split_top(expr, "??")
    if len(branches) > 1:
        return [t for b in branches for t in computed_texts(b, src, masked, pos, family, depth + 1)]
    own = patterns(expr, nested=True)
    if own:
        return own
    a, b = enclosing_body(masked, pos)
    name = expr.removeprefix("this.")
    if IDENT.match(name):
        if name in parameters(masked, a):
            return []   # the call that passes it in is the one to read (IComponent.AddMyActivatedAbility)
        assigned = rf"(?<![\w.]){re.escape(name)}\s*=(?!=)"
        if re.search(rf"\b(?:string|var)\s+{re.escape(name)}\b", masked[a:b]):   # a local
            values: list[str] = []
            for m in re.finditer(assigned, masked[a:b]):
                rhs = split_top(src[a + m.end():b], ";")[0]
                terms = split_top(rhs, "+")
                if len(terms) > 1 and any(strip_parens(t) == name for t in terms):
                    # «text = text + " (" + …»: the text so far, grown («Fly» → «Fly ({0})»)
                    grown = " + ".join('"\\u0002"' if strip_parens(t) == name else t for t in terms)
                    values += [p.replace("\u0002", v) for p in patterns(grown, nested=True) for v in values]
                else:
                    values += computed_texts(rhs, src, masked, a + m.start(), family, depth + 1)
            return values
        out = []
        for fsrc, fmasked in family:
            for m in re.finditer(assigned, fmasked):
                rhs = split_top(fsrc[m.end():], ";")[0].strip()
                if "\n" not in rhs:   # not the tail of an object initializer
                    out += patterns(rhs, nested=True)
        return out
    if BUILT.match(expr):
        if "LocalizationMatch" in src[a:b]:
            return []   # a builder beside the English that checks its _T twin (ModRecycling)
        return builder_texts(src, masked, BUILT.match(expr).group(1), pos, {})
    m = CALLED.match(name)
    if m:
        return [t for fsrc, fmasked in family for _, s, e in bodies(fmasked, {m.group(1)}) for t in built_texts(fsrc[s:e])]
    return []


class SourceTree:
    """The decompiled sources, read once: each file's text (masked on demand) and which classes derive from which,
    so that a field a subclass sets and a method it overrides are found (computed_texts)."""

    def __init__(self, src_dir: pathlib.Path):
        self.src_dir = src_dir
        self.raw: dict[pathlib.Path, str] = {}
        self.subclasses: dict[str, list[pathlib.Path]] = {}
        for path in sorted(src_dir.rglob("*.cs")):
            self.raw[path] = path.read_text(encoding="utf-8-sig")
            for m in SUBCLASS.finditer(self.raw[path]):
                self.subclasses.setdefault(m.group(1), []).append(path)
        self._masked: dict[pathlib.Path, tuple[str, str]] = {}

    def text(self, path: pathlib.Path) -> tuple[str, str]:
        if path not in self._masked:
            self._masked[path] = (self.raw[path], mask(self.raw[path]))
        return self._masked[path]

    def family(self, path: pathlib.Path, cls: str) -> list[tuple[str, str]]:
        """This file and those of the class's subclasses, at any depth (a decompiled class is a file of its name)."""
        out, todo = [], [cls]
        while todo:
            for p in self.subclasses.get(todo.pop(), []):
                if p not in out and p != path:
                    out.append(p)
                    todo.append(p.stem)
        return [self.text(path)] + [self.text(p) for p in out]

    def calls(self, call: re.Pattern, declared: str):
        """(where, family, src, masked, match, positional args, named args) for each call outside the skipped
        files; declared: the return types that make it a declaration instead."""
        for path in self.raw:
            if SKIP_FILE.search(path.relative_to(self.src_dir).as_posix()) or not call.search(self.raw[path]):
                continue
            src, masked = self.text(path)
            cls = CLASS.search(masked)
            where = cls.group(1) if cls else path.stem
            family = None
            for m in call.finditer(masked):
                if re.search(rf"\b(?:{declared})\s+$", masked[max(0, m.start() - 24):m.start()]):
                    continue
                o = m.end() - 1
                c = matching(src, o)
                if c < 0:
                    continue
                args = split_top(src[o + 1:c], ",")
                family = family or self.family(path, where)
                yield (where, family, src, masked, m, [x for x in args if not ANY_NAMED_ARG.match(x)],
                       {mm.group(1): mm.group(2) for x in args for mm in [ANY_NAMED_ARG.match(x)] if mm})


def code_keys(text: str) -> list[str]:
    """The keys a computed text gives, a line each with its holes numbered; not a placeholder that names a method
    («[BreatherBase::…]»), nor holes with no word around them («[{{B|{0}}}]»)."""
    out = []
    for line in lines_of(text):
        key = number_holes(line)
        literal = re.sub(r"\{\d+\}", " ", key)
        if "::" in key or "{0}" in key and not re.search(r"[A-Za-z]{3,}", literal):
            continue
        out.append(key)
    return out


# ---- the lines an ability's numbers add under its description: Templates.StatCollector ---------------------------

COLLECTOR_FILE = "XRL/Templates.cs"
COLLECTOR_METHOD = re.compile(r"\bpublic\s+(?:int|void|\([^()]*\))\s+(\w+)\s*\(([^()]*)\)\s*\{")
POSTFIX_STATEMENT = re.compile(r"\bpostfix\s*(?:\+=|=\s*postfix\s*\+)\s*")


def interpolation(token: str) -> list[tuple[str, str]] | None:
    """The pieces of an interpolated literal ($"…"): ("text", s) and ("expr", e); None for anything else."""
    if not token.startswith('$"') or not token.endswith('"'):
        return None
    body, out, i = token[2:-1], [], 0
    text = []
    while i < len(body):
        c = body[i]
        if c in "{}" and body[i + 1:i + 2] == c:
            text.append(c)
            i += 2
        elif c == "{":
            j = matching(body, i)
            if text:
                out.append(("text", literal_value('"' + "".join(text) + '"')))
                text = []
            out.append(("expr", body[i + 1:j].split(":")[0].strip()))
            i = j + 1
        else:
            text.append(c)
            if c == "\\":
                text.append(body[i + 1])
                i += 1
            i += 1
    if text:
        out.append(("text", literal_value('"' + "".join(text) + '"')))
    return out


def collector_methods(src: str) -> dict[str, list[tuple[list[tuple[str, bool]], str]]]:
    """StatCollector's public methods that append a line to its postfix, themselves or through another, by name: for
    each overload, its parameters (name, has a default) and body."""
    cls = re.search(r"\bclass\s+StatCollector\b[^{]*\{", src)
    if not cls:
        return {}
    region = src[cls.end() - 1:matching(src, cls.end() - 1) + 1]
    out: dict[str, list] = {}
    for m in COLLECTOR_METHOD.finditer(region):
        params = [p.strip() for p in split_top(m.group(2), ",") if p.strip()]
        names = [(p.split("=")[0].split()[-1], "=" in p) for p in params]
        body_start = m.end() - 1
        out.setdefault(m.group(1), []).append((names, region[body_start:matching(region, body_start) + 1]))
    appends = {name for name, overloads in out.items()
               if any(POSTFIX_STATEMENT.search(mask(body)) for _, body in overloads)}
    while True:
        callers = {name for name, overloads in out.items() if name not in appends
                   and any(re.search(rf"(?<![\w.])(?:{'|'.join(appends)})\s*\(", mask(body)) for _, body in overloads)}
        if not callers or not appends:
            break
        appends |= callers
    return {name: overloads for name, overloads in out.items() if name in appends}


def postfix_pieces(statement: str) -> list[tuple[str, str]]:
    """The pieces of what a «postfix += …» statement appends: literal text, interpolated holes, concatenated holes."""
    out = []
    for term in split_top(statement, "+"):
        term = term.strip()
        value = literal_value(term)
        parts = interpolation(term)
        if value is not None:
            out.append(("text", value))
        elif parts is not None:
            out.extend(parts)
        elif term:
            out.append(("expr", term))
    if out and out[0][0] == "text":
        out[0] = ("text", out[0][1].removeprefix("\n"))
    return out


def collector_lines(methods: dict, name: str, args: list[str], depth: int = 0) -> list[str]:
    """The lines a call of a StatCollector method appends, with HOLE where the code computes a part. A string
    argument gives its literal text, both texts of a ternary («high strength» / «low strength»), or a hole; any other
    part is a hole. A method that passes its numbers on to another (AddComputePowerPostfix → AddChangePostfix(what,
    change, "compute power")) appends what that one does."""
    out: list[str] = []
    for params, body in methods.get(name, []):
        required = sum(1 for _, default in params if not default)
        if not required <= len(args) <= len(params) or depth > 4:
            continue
        given = {p: args[i] for i, (p, _) in enumerate(params) if i < len(args)}
        # a parameter left out may fall back on another: «if (IsNullOrEmpty(statDisplayName)) statDisplayName = stat;»
        for p, _ in params:
            if p not in given:
                m = re.search(rf"\b{p}\s*=\s*(\w+);", body)
                if m and m.group(1) in given:
                    given[p] = given[m.group(1)]
        masked = mask(body)
        for m in POSTFIX_STATEMENT.finditer(masked):
            end = statement_end(masked, m.end(), len(masked))
            texts = [""]
            for kind, e in postfix_pieces(body[m.end():end].strip().removesuffix(";")):
                options = [e] if kind == "text" else (patterns(given[e]) if e in given else []) or [HOLE]
                texts = [t + o for t in texts for o in dict.fromkeys(options)][:16]
            out.extend(texts)
        for m in re.finditer(rf"(?<![\w.])({'|'.join(methods)})\s*\(", masked):
            o = m.end() - 1
            inner = [a.strip() for a in split_top(body[o + 1:matching(body, o)], ",")]
            # an argument that is one of this method's own parameters passes the caller's value on
            passed = [given.get(a, a) for a in inner]
            out.extend(collector_lines(methods, m.group(1), passed, depth + 1))
    return list(dict.fromkeys(out))


def postfix_keys(tree: SourceTree) -> dict[str, str]:
    """The English lines Templates.StatCollector adds under an ability's description, a key each: «Cooldown reduced
    by {0} due to {1}.», «Damage increased by {0}-{1} due to high strength.». Each call outside the collector gives
    its own what and why; a method's own lines (the cooldown's) are keys as they stand."""
    path = tree.src_dir / COLLECTOR_FILE
    methods = collector_methods(tree.raw[path]) if path in tree.raw else {}
    if not methods:
        return {}
    keys: dict[str, str] = {}
    for where, _family, _src, _masked, m, positional, _named in tree.calls(
            re.compile(rf"\.({'|'.join(methods)})\s*\("), "int|void"):
        for line in collector_lines(methods, m.group(1), positional):
            for key in code_keys(line):
                keys.setdefault(key, f"{where}: рядок під описом здібності (Templates.StatCollector)")
    # the cooldown's own lines, with the reason the cooldown event gives
    for params, _body in methods.get("CollectCooldownTurns", []):
        for line in collector_lines(methods, "CollectCooldownTurns", [p for p, _ in params]):
            for key in code_keys(line):
                keys.setdefault(key, "Templates.StatCollector: перезаряджання здібності під її описом")
    return keys


def scan_abilities(src_dir: pathlib.Path) -> list[Entry]:
    """The names the code gives activated abilities (AddMyActivatedAbility("Intimidate", …), «Clone [{0} left]» on a
    rename) and the descriptions it passes along: the ability bar, the manager and the popups show them as the entry
    keeps them. Names the string tables give (_S, _T) are theirs, and so are blueprint values the game's own
    localization XML lists (the «AbilityName» tag). And the lines a description's numbers add under it
    (postfix_keys)."""
    entries: dict[str, str] = {name: where for name, where in EXTRA_ABILITY_NAMES}
    tree = SourceTree(src_dir)
    for key, where in postfix_keys(tree).items():
        entries.setdefault(key, where)
    for where, family, src, masked, m, positional, named in tree.calls(
            ABILITY_CALL, "Guid|void|bool|ActivatedAbilityEntry"):
        if m.group(1).startswith("Set"):
            wanted = [(named.get("DisplayName", positional[1] if len(positional) > 1 else None), "назва")]
        else:
            wanted = [(named.get("Name", positional[0] if positional else None), "назва"),
                      (named.get("Description", positional[3] if len(positional) > 3 else None), "опис")]
        for expr, what in wanted:
            if expr is not None:
                for found in computed_texts(expr, src, masked, m.start(), family):
                    for key in code_keys(found):
                        entries.setdefault(key, f"{where}: {what} здібності")
    return [Entry(k, w) for k, w in sorted(entries.items())]


# ---- Fragments: what the code adds to a name -------------------------------------------------------------------

FRAGMENT_CALL = re.compile(r"\.(AddAdjective|AddHonorific|AddMark|AddTag|AddClause|AddWithClause|AddEpithet|AddTitle)"
                           r"\s*\(")
FRAGMENT_KINDS = {
    "AddAdjective": "прикметник перед назвою",
    "AddHonorific": "прикметник перед назвою",
    "AddMark": "знак перед назвою",
    "AddTag": "позначка після назви",
    "AddClause": "доповнення після назви",
    "AddWithClause": "те, з чим предмет («with …»)",
    "AddEpithet": "епітет після імені",
    "AddTitle": "титул після імені",
}


def scan_fragments(src_dir: pathlib.Path) -> list[Entry]:
    """What the code adds to an object's name in English (GetDisplayNameEvent: E.AddAdjective("keen"),
    E.AddTag("[{{r|rusted}}]")): our DescriptionBuilder looks each one up as it comes in. What the string tables
    give (_S, _T) is theirs."""
    entries: dict[str, str] = {}
    for where, family, src, masked, m, positional, named in SourceTree(src_dir).calls(FRAGMENT_CALL, "void"):
        if positional:
            for found in computed_texts(positional[0], src, masked, m.start(), family):
                for key in code_keys(found):
                    entries.setdefault(key, f"{where}: {FRAGMENT_KINDS[m.group(1)]}")
    return [Entry(k, w) for k, w in sorted(entries.items())]


# ---- Rules: the rules lines of a description ---------------------------------------------------------------------

RULES_CALL = re.compile(r"\.(AppendRules)\s*\(")


def scan_rules(src_dir: pathlib.Path) -> list[Entry]:
    """The rules lines the code writes into a description (E.Postfix.AppendRules(GetDescription(Tier)): «Keen: +2
    to penetration rolls»): Extensions.AppendRules, which every one passes, looks them up. A text an Action builds
    is out of reach; what the string tables give (_S, _T) is theirs."""
    entries: dict[str, str] = {}
    for where, family, src, masked, m, positional, named in SourceTree(src_dir).calls(RULES_CALL,
                                                                                      "StringBuilder|TextBuilder"):
        if positional and "=>" not in positional[0] and not positional[0].lstrip().startswith("delegate"):
            for found in computed_texts(positional[0], src, masked, m.start(), family):
                for key in code_keys(found):
                    entries.setdefault(key, where)
    return [Entry(k, w) for k, w in sorted(entries.items())]


# ---- Damage: the tails of the damage lines -----------------------------------------------------------------------

TAKE_DAMAGE = re.compile(r"(?<![\w])(TakeDamage)\s*\(")
MESSAGE_DEFAULT = re.compile(r'\bstring Message = ("(?:[^"\\]|\\.)*")')
DAMAGE_EVENT = re.compile(r'Event\.New\(\s*"TakeDamage"')
DAMAGE_EVENT_VAR = re.compile(r'(\w+)\s*=\s*Event\.New\(\s*"TakeDamage"')
MESSAGE_LITERAL = re.compile(r'(\w+)\.SetParameter\(\s*"Message",\s*')


def scan_damage(src_dir: pathlib.Path) -> list[Entry]:
    """The tails of the damage lines: what the code passes TakeDamage as its Message («from %t bite.», by default
    «from %t attack.») — named, in its place among the arguments (the ref overload's tenth, the others' second, or
    the third of TakeDamage(Amount, FromAttacker, ShowMessage)), or as the TakeDamage event's parameter. Physics
    puts a head before it and fills its %-codes in English; DamagePatches takes the tail over first."""
    tree = SourceTree(src_dir)
    entries: dict[str, str] = {}

    def add(texts, where):
        for found in texts:
            for key in code_keys(found):
                entries.setdefault(key, where)
    for where, family, src, masked, m, positional, named in tree.calls(TAKE_DAMAGE, "bool|void"):
        expr = named.get("Message", named.get("ShowMessage"))
        if expr is None and positional:
            if positional[0].lstrip().startswith("ref "):
                expr = positional[9] if len(positional) > 9 else None
            elif len(positional) == 3 and not patterns(positional[1], nested=True):
                expr = positional[2]
            elif len(positional) > 1:
                expr = positional[1]
        if expr is not None:
            add(computed_texts(expr, src, masked, m.start(), family), where)
    for path, raw in tree.raw.items():
        if "TakeDamage" not in raw:
            continue
        for m in MESSAGE_DEFAULT.finditer(raw):
            add([literal_value(m.group(1))], path.stem)
        if DAMAGE_EVENT.search(raw):
            src, masked = tree.text(path)
            # only the TakeDamage event's own Message: another event's («Attacked», for the AI) is an identifier
            events = {m.group(1) for m in DAMAGE_EVENT_VAR.finditer(masked)}
            for m in MESSAGE_LITERAL.finditer(masked):
                if m.group(1) not in events:
                    continue
                o = m.start() + m.group(0).index("(")
                args = split_top(src[o + 1:matching(src, o)], ",")
                if len(args) > 1 and not BUILT.match(strip_parens(args[1])):
                    add(computed_texts(args[1], src, masked, m.start(), [(src, masked)]), f"{path.stem} (TakeDamage)")
    return [Entry(k, w) for k, w in sorted(entries.items())]


# ---- Journal: the accomplishments the code writes -----------------------------------------------------------------

ACCOMPLISHMENT = re.compile(r"(?<![\w])JournalAPI\.(AddAccomplishment)\s*\(")
ACCOMPLISHMENT_PARTS = (("text", "запис у журналі (вкладка «Хронологія»)"),
                        ("muralText", "фреска в гробниці гравця; =name= — гравець"),
                        ("gospelText", "євангеліє, яке переказують села наприкінці; =name= — гравець"))


def scan_journal(src_dir: pathlib.Path) -> list[Entry]:
    """What JournalAPI.AddAccomplishment is given in English: the journal's line, the mural's and the gospel's
    (named or in their places), followed through locals, fields and builders. What the string tables give is theirs."""
    entries: dict[str, str] = {}
    for where, family, src, masked, m, positional, named in SourceTree(src_dir).calls(ACCOMPLISHMENT, "void"):
        for i, (name, what) in enumerate(ACCOMPLISHMENT_PARTS):
            expr = named.get(name, positional[i] if len(positional) > i else None)
            if expr is not None:
                for found in computed_texts(expr, src, masked, m.start(), family):
                    for key in code_keys(found):
                        entries.setdefault(key, f"{where}: {what}")
    return [Entry(k, w) for k, w in sorted(entries.items())]
