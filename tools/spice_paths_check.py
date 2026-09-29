"""Check the HistorySpice references in merged worksheets before they are applied.

  py tools/spice_paths_check.py work/batch/<worksheet>.uk.jsonl [...]

Every =spice:…=, <spice.…>, =^:…= and =spice.set:…= in a translation must lead to a list of the English spice or
of translations/uk/HistorySpice.extra/*.json (docs/history.md). References the English row already has and that
lead nowhere are the game's own and are not reported. Also reports additions that would replace an English list
and two addition files with the same key. Exit code 1 on a problem.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from qudtr import spice  # noqa: E402
from qudtr.sources import DEFAULT_GAME_DIR  # noqa: E402

SPICE_FILE = DEFAULT_GAME_DIR / "CoQ_Data" / "StreamingAssets" / "Base" / "HistorySpice.jsonc"


def main(argv: list[str]) -> int:
    english = spice.load(SPICE_FILE.read_text(encoding="utf-8-sig"))["spice"]
    parts = spice.load_overlay_parts()
    overlay = spice.load_overlay()
    problems = [f"{c}: two files define the same key" for c in spice.overlay_clashes(parts)]
    problems += [f"spice.{p} exists in the English spice; translate it in HistorySpice.po"
                 for p in spice.overlay_conflicts(english, overlay)]
    tree = spice.merge(english, overlay)
    for path, value in spice.leaves(overlay):
        problems += [f"HistorySpice.extra: spice.{'.'.join(path)}: leads nowhere: {r}"
                     for r in spice.unresolved(value, tree, path[0])]
    for name in argv:
        for line in pathlib.Path(name).read_text(encoding="utf-8").splitlines()[1:]:
            r = json.loads(line)
            if not r.get("uk"):
                continue
            ctx = r.get("ctx") or ""
            branch = ctx.split(".")[1] if ctx.startswith("spice.") else None
            new = set(spice.unresolved(r["uk"], tree, branch)) - set(spice.unresolved(r["en"], tree, branch))
            problems += [f"{pathlib.Path(name).name}: {ctx}: leads nowhere: {ref}" for ref in sorted(new)]
    for p in problems:
        print(p)
    print(f"{len(problems)} problem(s); {len(parts)} addition file(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
