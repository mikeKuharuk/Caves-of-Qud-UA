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


def patterns(expr: str) -> list[str]:
    """The texts an expression can produce: literals kept, everything else a hole. A ternary gives both branches.
    An expression with no literal, or one routed through the string tables, gives nothing."""
    expr = strip_parens(expr)
    if not expr:
        return []
    alternatives = split_top(expr, "??")
    if len(alternatives) > 1:
        return [p for a in alternatives for p in patterns(a)]
    q = ternary(expr)
    if q:
        return patterns(q[1]) + patterns(q[2])
    if LOCALIZED.search(expr):
        return []
    out = [""]
    found = False
    for term in split_top(expr, "+"):
        term = strip_parens(term)
        value = literal_value(term)
        if value is not None:
            found = True
            out = [o + value for o in out]
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
    return [Entry(k, w) for k, w in sorted(entries.items())]


# ---- DidX: the English narration the game conjugates itself ------------------------------------------------

DIDX_CALL = re.compile(r"(?<![\w])(DidX|DidXToY|DidXToYWithZ|XDidY|XDidYToZ|WDidXToYWithZ)\s*\(")
NAMED_ARG = re.compile(r"^\s*([A-Z]\w*)\s*:(?!:)\s*(.*)$", re.S)
KINDS = {"DidX": "X", "XDidY": "X", "DidXToY": "XZ", "XDidYToZ": "XZ", "DidXToYWithZ": "WXZ", "WDidXToYWithZ": "WXZ"}


def _is_string(arg: str) -> bool:
    return bool(patterns(arg)) or literal_value(strip_parens(arg)) is not None


def didx_fields(method: str, args: list[str]) -> dict[str, str] | None:
    """The message fields of a DidX-family call: Verb, Preposition, IndirectPreposition, Extra, EndMark, by the
    overload the arguments select (IComponent wrappers have no Actor; Messaging statics start with it)."""
    positional = [a for a in args if not NAMED_ARG.match(a)]
    named = {m.group(1): m.group(2) for a in args for m in [NAMED_ARG.match(a)] if m}
    if method.startswith(("X", "W")):
        if not positional or literal_value(strip_parens(positional[0])) is not None:
            return None   # the SubjectOverride overloads: a string instead of the actor
        positional = positional[1:]
    kind = KINDS[method]
    if kind == "X":
        order = ["Verb", "Extra", "EndMark"]
    elif kind == "XZ":
        order = ["Verb", "Preposition", "Object", "Extra", "EndMark"] if len(positional) > 1 and _is_string(positional[1]) \
            else ["Verb", "Object", "Extra", "EndMark"]
    else:
        order = ["Verb", "DirectPreposition", "DirectObject", "IndirectPreposition", "IndirectObject", "Extra", "EndMark"] \
            if len(positional) > 1 and _is_string(positional[1]) \
            else ["Verb", "DirectObject", "IndirectPreposition", "IndirectObject", "Extra", "EndMark"]
    fields = dict(zip(order, positional))
    fields.update(named)
    if "DirectPreposition" in fields:
        fields["Preposition"] = fields.pop("DirectPreposition")
    return fields


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


def scan_didx(src_dir: pathlib.Path) -> list[tuple[str, str, str]]:
    """(key, English for the translator, where) for every DidX-family call with a literal verb."""
    found: dict[str, tuple[str, str]] = {}
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
            fields = didx_fields(m.group(1), split_top(src[o + 1:c], ","))
            if not fields or "Verb" not in fields:
                continue
            verb = literal_value(strip_parens(fields["Verb"]))
            if not verb:
                continue
            kind = KINDS[m.group(1)]

            def options(name: str, default: str) -> list[str]:
                if name not in fields or strip_parens(fields[name]) == "null":
                    return [default]
                return patterns(fields[name])   # holes still unnumbered: they are counted across the key below
            preps = options("Preposition", "") if kind != "X" else [""]
            ipreps = options("IndirectPreposition", "") if kind == "WXZ" else [""]
            extras = options("Extra", "")
            ends = options("EndMark", ".")
            for prep in preps:
                for iprep in ipreps:
                    for extra in extras:
                        for end in ends:
                            parts = number_fields(prep, iprep, extra, end)
                            key = didx_key(kind, verb, *parts)
                            found.setdefault(key, (didx_english(kind, verb, *parts), where))
    return [(k, e, w) for k, (e, w) in sorted(found.items())]


# ---- Text: popups, failure messages and the message log ------------------------------------------------------

SINK_CALL = re.compile(
    r"(?<![\w])((?:Popup\.)(?:Show|ShowFail|ShowBlock|ShowYesNo|ShowYesNoCancel|ShowBlockPrompt|ShowBlockSpace|"
    r"ShowBlockWithCopy|WarnYesNo|AskString|AskNumber|ShowAsync|ShowFailAsync|ShowYesNoAsync|ShowYesNoCancelAsync|"
    r"AskStringAsync|AskNumberAsync|ShowSpace|PickOption|PickOptionAsync|ShowOptionList)|(?:[\w.]+\.)?Fail|"
    r"(?:MessageQueue\.|IComponent<GameObject>\.)?AddPlayerMessage|(?:[\w.]+\.)?EmitMessage|"
    r"(?:[\w.]+\.)?DisplayMessage)\s*\(")   # DisplayMessage: journal notices («You note the location of…»)
SKIP_FILE = re.compile(r"Wish|Debug|Test|Cheat|MapEditor")
STRING_ARRAY = re.compile(r"new\s+(?:string\s*\[\s*\]|List<string>)\s*\{")
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
            ps = patterns(args[0]) if args else []
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


def scan_text(src_dir: pathlib.Path) -> list[Entry]:
    """Popups, failure messages and message-log lines the game's C# writes, line by line (CodeText splits a text
    into lines when the whole is not a key)."""
    entries: dict[str, str] = {}
    for path in sorted(src_dir.rglob("*.cs")):
        rel = path.relative_to(src_dir).as_posix()
        if SKIP_FILE.search(rel) or rel.startswith(("XRL.Wish", "XRL.Tests")):
            continue
        src = path.read_text(encoding="utf-8-sig")
        if not SINK_CALL.search(src):
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
            for arr in STRING_ARRAY.finditer(src[o + 1:c]):
                start = o + 1 + arr.end() - 1
                end = matching(src, start)
                for item in split_top(src[start + 1:end], ","):
                    texts += patterns(item)
            for text in texts:
                for line in lines_of(text):
                    key = number_holes(line)
                    if specific(key):
                        entries.setdefault(key, f"{where} ({name.split('.')[-1]})")
    return [Entry(k, w) for k, w in sorted(entries.items())]
