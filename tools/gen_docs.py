"""Regenerate the parameter reference in docs/EFFECT_FORMAT.md from the engine's schema.

Run it whenever a layer, warp or filter changes:

    python tools/gen_docs.py          # rewrite the tables
    python tools/gen_docs.py --check  # exit 1 if they're out of date (used by the tests)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from staticfx.effects.engine.filters import BLENDS, FILTERS
from staticfx.effects.engine.layers import LAYERS
from staticfx.effects.engine.schema import Kind, Param
from staticfx.effects.engine.warps import WARPS

DOC = ROOT / "docs" / "EFFECT_FORMAT.md"
START, END = "<!-- reference:start -->", "<!-- reference:end -->"


def describe_param(param: Param) -> str:
    if param.choices:
        values = ", ".join(f"`{c}`" for c in param.choices)
        return f"`{param.name}` | {param.label} | one of {values} | `{param.default}`"
    kind = "whole number" if param.integer else "number"
    low, high = (int(param.low), int(param.high)) if param.integer else (param.low, param.high)
    return f"`{param.name}` | {param.label} | {kind}, {low} to {high} | `{param.default}`"


def section(title: str, kinds: dict[str, Kind]) -> list[str]:
    lines = [f"### {title}", ""]
    for kind in kinds.values():
        summary = f": {kind.summary}" if kind.summary else ""
        lines.append(f"**`{kind.name}`**{summary}")
        lines.append("")
        if kind.params:
            lines += ["Key | Meaning | Values | Default", "--- | --- | --- | ---"]
            lines += [describe_param(p) for p in kind.params]
        else:
            lines.append("No parameters.")
        lines.append("")
    return lines


def reference() -> str:
    lines = [START, ""]
    lines += section("Layers", LAYERS)
    lines += section("Warps", WARPS)
    lines += section("Filters", FILTERS)
    lines += ["### Blends", "", ", ".join(f"`{name}`" for name in BLENDS), "", END]
    return "\n".join(lines)


def updated(text: str) -> str:
    before, _, rest = text.partition(START)
    _, _, after = rest.partition(END)
    return before + reference() + after


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = DOC.read_text(encoding="utf-8")
    new = updated(text)
    if args.check:
        if new != text:
            print(f"{DOC.relative_to(ROOT)} is out of date: run python tools/gen_docs.py")
            return 1
        return 0
    DOC.write_text(new, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
