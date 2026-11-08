"""The quality gate for generated effects.

Renders every generated recipe and measures it. A recipe is excluded when
it is

* **blank** - draws on less than 3% of the screen,
* **frozen** - the picture doesn't change over a second,
* **a wall** - covers almost the whole screen with fewer than 3 distinct
  (character, brightness) combinations: a solid block, not a pattern, or
* **slow** - over 30 ms per frame at 100x30 with full detail, too slow to
  animate smoothly on a large terminal.

Run it after changing the engine or the generator, then commit the result:

    python tools/curate.py            # rewrites staticfx/effects/curated.py's EXCLUDED
    python tools/curate.py --report   # print the measurements, change nothing
    python tools/curate.py --rank 64  # print the best-scoring seeds (Gallery candidates)
"""

from __future__ import annotations

import argparse
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from staticfx.core.frame import Frame
from staticfx.effects.engine import GENERATED_COUNT, EngineEffect, generate
from staticfx.themes import STATIC_THEMES

WIDTH, HEIGHT = 100, 30
MIN_COVERAGE, WALL_COVERAGE, MIN_VARIETY, MAX_MS = 0.03, 0.9, 3, 30.0
CURATED = ROOT / "staticfx" / "effects" / "curated.py"


@dataclass
class Measure:
    seed: int
    coverage: float
    variety: int
    motion: float
    coherence: float  # how often a drawn cell matches its right-hand neighbour
    glyph_rain: bool
    ms: float

    @property
    def problem(self) -> str:
        if self.coverage < MIN_COVERAGE:
            return "blank"
        if self.motion == 0:
            return "frozen"
        if self.variety < MIN_VARIETY and self.coverage > WALL_COVERAGE:
            return "wall"
        if self.ms > MAX_MS:
            return "slow"
        return ""

    @property
    def score(self) -> float:
        """Rough taste, used only to shortlist Gallery candidates for a human to judge:
        visible structure (not noise), some variety and motion, room to breathe."""
        if self.glyph_rain:
            return 0.0  # random glyphs all look alike
        breathing = 1.0 - abs(self.coverage - 0.55)
        return min(self.variety, 24) / 24 + self.coherence + min(self.motion, 0.4) * 2 + breathing


def snapshot(effect: EngineEffect, theme) -> list[tuple[str, int]]:
    frame = Frame(WIDTH, HEIGHT)
    effect.draw(frame, theme)
    return [(cell.char, max(cell.color) // 32) for row in frame.cells for cell in row]


def measure(seed: int) -> Measure:
    recipe, _ = generate(seed)
    effect = EngineEffect(random.Random(seed), recipe=recipe)
    effect.resize(WIDTH, HEIGHT)
    theme = STATIC_THEMES["matrix"]
    for _ in range(30):
        effect.update(1 / 30)
    started = time.perf_counter()
    first = snapshot(effect, theme)
    ms = (time.perf_counter() - started) * 1000
    for _ in range(30):
        effect.update(1 / 30)
    second = snapshot(effect, theme)
    drawn = [cell for cell in second if cell[0] != " "]
    changed = sum(a != b for a, b in zip(first, second, strict=True))
    same = sum(
        1
        for i in range(len(second) - 1)
        if second[i][0] != " " and (i + 1) % WIDTH and second[i][0] == second[i + 1][0]
    )
    return Measure(
        seed=seed,
        coverage=len(drawn) / len(second),
        variety=len(set(drawn)),
        motion=changed / len(second),
        coherence=same / max(1, len(drawn)),
        glyph_rain=recipe.glyph_rain,
        ms=ms,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Quality gate for generated effects.")
    parser.add_argument("--report", action="store_true", help="print measurements only")
    parser.add_argument("--rank", type=int, metavar="N", help="print the N best passing seeds")
    args = parser.parse_args()

    results = [measure(seed) for seed in range(GENERATED_COUNT)]
    failed = [m for m in results if m.problem]
    by_problem: dict[str, list[int]] = {}
    for m in failed:
        by_problem.setdefault(m.problem, []).append(m.seed)
    for problem, seeds in sorted(by_problem.items()):
        shown = " ".join(map(str, seeds[:30])) + (" ..." if len(seeds) > 30 else "")
        print(f"{problem:>7}: {len(seeds):3d}  {shown}")
    print(f"  total: {len(failed)} of {len(results)} excluded")

    if args.rank:
        best = sorted((m for m in results if not m.problem), key=lambda m: -m.score)
        print(" ".join(str(m.seed) for m in best[: args.rank]))
    if args.report or args.rank:
        return

    seeds = ", ".join(str(m.seed) for m in sorted(failed, key=lambda m: m.seed))
    text = re.sub(
        r"EXCLUDED: frozenset\[int\] = frozenset\([^)]*\)",
        f"EXCLUDED: frozenset[int] = frozenset({{{seeds}}})",
        CURATED.read_text(),
    )
    CURATED.write_text(text)
    print(f"wrote {len(failed)} seeds to {CURATED.relative_to(ROOT)}; run `ruff format` on it")


if __name__ == "__main__":
    main()
