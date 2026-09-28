"""A small, dependency-free reader/writer for gettext PO files.

Only what this project needs: singular entries with msgctxt, translator/extracted comments,
references, flags, previous msgctxt/msgid (#|), and obsolete entries (#~). Output is
deterministic (no width-based wrapping; strings containing newlines are split after each
newline) so that regenerated catalogs produce clean diffs.
"""
from __future__ import annotations

import dataclasses
import re

HEADER_ORDER = (
    "Project-Id-Version", "Language", "MIME-Version", "Content-Type", "Content-Transfer-Encoding",
    "Plural-Forms",
)
UK_PLURAL_FORMS = ("nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && "
                   "(n%100<10 || n%100>=20) ? 1 : 2);")

_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\t": "\\t", "\r": "\\r"}
_UNESCAPES = {"\\": "\\", '"': '"', "n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b",
              "f": "\f", "v": "\v"}


class POError(ValueError):
    pass


@dataclasses.dataclass
class Entry:
    msgid: str
    msgstr: str = ""
    msgctxt: str | None = None
    translator_comments: list[str] = dataclasses.field(default_factory=list)   # "# "
    extracted_comments: list[str] = dataclasses.field(default_factory=list)    # "#."
    references: list[str] = dataclasses.field(default_factory=list)            # "#:"
    flags: list[str] = dataclasses.field(default_factory=list)                 # "#,"
    previous_msgctxt: str | None = None                                        # "#| msgctxt"
    previous_msgid: str | None = None                                          # "#| msgid"
    obsolete: bool = False

    @property
    def key(self) -> tuple[str | None, str]:
        return (self.msgctxt, self.msgid)

    @property
    def fuzzy(self) -> bool:
        return "fuzzy" in self.flags

    @fuzzy.setter
    def fuzzy(self, value: bool) -> None:
        if value and "fuzzy" not in self.flags:
            self.flags.insert(0, "fuzzy")
        elif not value and "fuzzy" in self.flags:
            self.flags.remove("fuzzy")

    @property
    def translated(self) -> bool:
        return bool(self.msgstr) and not self.fuzzy


@dataclasses.dataclass
class Catalog:
    headers: dict[str, str] = dataclasses.field(default_factory=dict)
    header_comments: list[str] = dataclasses.field(default_factory=list)
    entries: list[Entry] = dataclasses.field(default_factory=list)

    def index(self) -> dict[tuple[str | None, str], Entry]:
        return {e.key: e for e in self.entries if not e.obsolete}


# --------------------------------------------------------------------------------------------
# Writing

def escape(s: str) -> str:
    out = []
    for ch in s:
        if ch in _ESCAPES:
            out.append(_ESCAPES[ch])
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            raise POError(f"control character U+{ord(ch):04X} cannot be written to a PO file")
        else:
            out.append(ch)
    return "".join(out)


def _format_string(keyword: str, value: str, prefix: str = "") -> list[str]:
    """Format `keyword "value"`, splitting after each newline for readability."""
    if "\n" in value.rstrip("\n") or (value.count("\n") > 1):
        parts = value.split("\n")
        chunks = [p + "\n" for p in parts[:-1]]
        if parts[-1]:
            chunks.append(parts[-1])
        lines = [f'{prefix}{keyword} ""']
        lines += [f'{prefix}"{escape(c)}"' for c in chunks]
        return lines
    return [f'{prefix}{keyword} "{escape(value)}"']


def format_entry(e: Entry) -> str:
    lines: list[str] = []
    lines += [f"# {c}" if c else "#" for c in e.translator_comments]
    lines += [f"#. {c}" for c in e.extracted_comments]
    lines += [f"#: {r}" for r in e.references]
    if e.flags:
        lines.append("#, " + ", ".join(e.flags))
    if not e.obsolete:  # previous fields of obsolete entries are dropped, not written as "#~|"
        if e.previous_msgctxt is not None:
            lines += _format_string("msgctxt", e.previous_msgctxt, "#| ")
        if e.previous_msgid is not None:
            lines += _format_string("msgid", e.previous_msgid, "#| ")
    body: list[str] = []
    if e.msgctxt is not None:
        body += _format_string("msgctxt", e.msgctxt)
    body += _format_string("msgid", e.msgid)
    body += _format_string("msgstr", e.msgstr)
    if e.obsolete:
        body = ["#~ " + b for b in body]
    return "\n".join(lines + body)


def dumps(cat: Catalog) -> str:
    out = []
    head = [f"# {c}" if c else "#" for c in cat.header_comments]
    ordered = [k for k in HEADER_ORDER if k in cat.headers] + [k for k in cat.headers if k not in HEADER_ORDER]
    header_value = "".join(f"{k}: {cat.headers[k]}\n" for k in ordered)
    head += _format_string("msgid", "")
    head += ['msgstr ""'] + [f'"{escape(line)}"' for line in header_value.splitlines(keepends=True)]
    out.append("\n".join(head))
    live = [e for e in cat.entries if not e.obsolete]
    dead = [e for e in cat.entries if e.obsolete]
    out += [format_entry(e) for e in live + dead]
    return "\n\n".join(out) + "\n"


def dump(cat: Catalog, path) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dumps(cat))


# --------------------------------------------------------------------------------------------
# Reading

_STRING = re.compile(r'^"(.*)"$')
_KEYWORD = re.compile(r'^(msgctxt|msgid|msgid_plural|msgstr(?:\[\d+\])?)\s+"(.*)"$')


def unescape(s: str) -> str:
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch != "\\":
            out.append(ch)
            i += 1
            continue
        if i + 1 >= len(s):
            raise POError("dangling backslash")
        nxt = s[i + 1]
        if nxt in _UNESCAPES:
            out.append(_UNESCAPES[nxt])
            i += 2
        elif nxt == "x":
            m = re.match(r"[0-9A-Fa-f]{1,2}", s[i + 2:])
            if not m:
                raise POError(f"bad \\x escape in {s!r}")
            out.append(chr(int(m.group(), 16)))
            i += 2 + len(m.group())
        elif nxt in "01234567":
            m = re.match(r"[0-7]{1,3}", s[i + 1:])
            out.append(chr(int(m.group(), 8)))
            i += 1 + len(m.group())
        else:
            raise POError(f"unknown escape \\{nxt} in {s!r}")
    return "".join(out)


def loads(text: str) -> Catalog:
    cat = Catalog()
    entries: list[Entry] = []
    cur: dict = {}
    last_field: str | None = None

    def flush():
        nonlocal cur, last_field
        if "msgid" in cur:
            e = Entry(
                msgid=cur["msgid"], msgstr=cur.get("msgstr", ""), msgctxt=cur.get("msgctxt"),
                translator_comments=cur.get("tc", []), extracted_comments=cur.get("ec", []),
                references=cur.get("ref", []), flags=cur.get("flags", []),
                previous_msgctxt=cur.get("prev_msgctxt"), previous_msgid=cur.get("prev_msgid"),
                obsolete=cur.get("obsolete", False),
            )
            entries.append(e)
        elif cur:
            # comments without an entry (e.g. file header comments before the header entry)
            cat.header_comments.extend(cur.get("tc", []))
        cur = {}
        last_field = None

    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            if "msgid" in cur:
                flush()
            continue
        try:
            if line.startswith("#~"):
                body = line[2:].strip()
                if body.startswith("|"):
                    continue  # "#~|" previous-value lines of obsolete entries: not kept
                if "msgid" in cur and not cur.get("obsolete") and last_field in ("msgstr",):
                    flush()
                cur["obsolete"] = True
                line = body
                if not line:
                    continue
            elif line.startswith("#|"):
                body = line[2:].strip()
                m = _KEYWORD.match(body)
                if m:
                    field = "prev_" + m.group(1)
                    cur[field] = unescape(m.group(2))
                    last_field = field
                else:
                    m = _STRING.match(body)
                    if not m or not last_field or not last_field.startswith("prev_"):
                        raise POError(f"bad #| line")
                    cur[last_field] += unescape(m.group(1))
                continue
            elif line.startswith("#"):
                if "msgid" in cur and last_field in ("msgstr",):
                    flush()
                if line.startswith("#."):
                    cur.setdefault("ec", []).append(line[2:].strip())
                elif line.startswith("#:"):
                    cur.setdefault("ref", []).append(line[2:].strip())
                elif line.startswith("#,"):
                    cur.setdefault("flags", []).extend(f.strip() for f in line[2:].split(",") if f.strip())
                else:
                    cur.setdefault("tc", []).append(line[1:].strip() if line.startswith("# ") or line == "#" else line[1:])
                continue
            m = _KEYWORD.match(line)
            if m:
                kw = m.group(1)
                if kw == "msgid_plural" or kw.startswith("msgstr["):
                    raise POError("plural entries are not supported")
                if kw in ("msgctxt", "msgid") and last_field == "msgstr":
                    flush()
                if kw == "msgid" and "msgid" in cur:
                    raise POError("msgid without msgstr")
                cur[kw] = unescape(m.group(2))
                last_field = kw
                continue
            m = _STRING.match(line)
            if m and last_field in ("msgctxt", "msgid", "msgstr"):
                cur[last_field] += unescape(m.group(1))
                continue
            raise POError("unexpected line")
        except POError as err:
            raise POError(f"line {lineno}: {err}: {raw!r}") from None
    flush()

    if entries and entries[0].msgid == "" and entries[0].msgctxt is None:
        header = entries.pop(0)
        cat.header_comments = header.translator_comments or cat.header_comments
        for line in header.msgstr.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                cat.headers[k.strip()] = v.strip()
    cat.entries = entries
    return cat


def load(path) -> Catalog:
    with open(path, encoding="utf-8") as f:
        return loads(f.read())
