"""How much of the translatable XML text uses the game's grammar machinery?

Counts =variable= tokens, {{markup}}, ~alternatives and <spice> refs in the main text fields,
and lists the most common variable names (these become the Ukrainian grammar problem).
"""
import collections
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from xmlscan import BASE, parse_lenient  # noqa: E402

VAR = re.compile(r"=([A-Za-z_][A-Za-z0-9_.:'|-]*)=")
FIELDS = {
    ("part", "Description", "Short"), ("part", "Render", "DisplayName"),
}
TEXT_TAGS = {"text", "choice", "node", "page", "p", "topic", "description"}

strings = 0
with_var = 0
with_markup = 0
with_alt = 0
names = collections.Counter()
for path in sorted(BASE.rglob("*.xml")):
    for el in parse_lenient(path).iter():
        vals = []
        if el.tag == "part":
            for (t, n, a) in FIELDS:
                if el.get("Name") == n and el.get(a):
                    vals.append(el.get(a))
        if el.tag in TEXT_TAGS and (el.text or "").strip():
            vals.append(el.text)
        for v in vals:
            strings += 1
            vs = VAR.findall(v)
            if vs:
                with_var += 1
                for x in vs:
                    names[x.split(":")[0].split("|")[0]] += 1
            if "{{" in v:
                with_markup += 1
            if "~" in v:
                with_alt += 1

print(f"strings={strings} with_vars={with_var} ({with_var*100//max(strings,1)}%) with_markup={with_markup} with_~alternatives={with_alt}")
print("most common variables:")
for n, c in names.most_common(70):
    print(f"{c:6}  ={n}=")
