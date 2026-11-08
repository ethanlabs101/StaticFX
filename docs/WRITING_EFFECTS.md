# Writing a built-in effect

There are two ways to add an effect:

- **Make a recipe** in the Studio or by hand (see [STUDIO.md](STUDIO.md) and
  [EFFECT_FORMAT.md](EFFECT_FORMAT.md)). No code involved, but you're limited
  to what the engine's layers, warps and filters can express.
- **Write a Python class**, like the 50 hand-written built-ins. This guide is
  about that. Anything you can draw with characters is fair game: particles,
  simulations, text, 3D wireframes.

## The contract

Subclass `staticfx.effects.base.Effect` and override what you need:

Method | Called when | Your job
--- | --- | ---
`on_resize()` | The terminal size changes (and on the first frame). `self.width` and `self.height` are already set. | Rebuild anything that depends on size.
`on_reset()` | The user restarts the effect (`Z`). By default it calls `on_resize()`. | Start the animation over.
`advance(dt)` | Every frame, unless paused. `dt` is in seconds, scaled by the speed setting, and always positive. | Move your simulation forward.
`render(frame, theme)` | Every frame. | Draw the current state.

The base class guarantees `advance` and `render` never run before the first
resize, and never with a zero or negative `dt`. `dt` is capped at 0.25 s (×
the speed setting) so a stall doesn't make things jump.

Draw with `frame.put(x, y, char, colour)` and `frame.text(x, y, text, colour)`;
both clip to the screen, so you don't need bounds checks. A space is
transparent, so only draw what's visible.

For colour, map a brightness from 0 to 1 to the current theme with
`self.color_at(theme, value)`, or use `theme.accent` and `theme.bright` for
highlights. Don't hard-code colours: then your effect works with every theme.

Two flags are set for you: `self.unicode` is true when katakana and other
non-ASCII glyphs are allowed, and `self.ascii_only` is true when the terminal
can only show plain ASCII. The test suite checks that effects stay ASCII when
`ascii_only` is set.

Use `self.rng` for randomness, never the `random` module directly, so seeded
runs (`staticfx render --seed 1`) are reproducible.

## An example

Expanding rings that spawn at random points:

```python
import math

from staticfx.core.frame import Frame
from staticfx.effects.base import Effect
from staticfx.themes import Theme


class Raindrops(Effect):
    """Rings spreading out from random points, fading as they grow."""

    LIFETIME = 3.0  # seconds a ring lives
    SPEED = 9.0  # cells per second

    def __init__(self, rng, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.drops: list[list[float]] = []  # [x, y, age]
        self.cooldown = 0.0

    def on_resize(self) -> None:
        self.drops.clear()

    def advance(self, dt: float) -> None:
        self.cooldown -= dt
        if self.cooldown <= 0:
            self.cooldown = self.rng.uniform(0.2, 0.6)
            self.drops.append(
                [self.rng.uniform(0, self.width), self.rng.uniform(0, self.height), 0.0]
            )
        for drop in self.drops:
            drop[2] += dt
        self.drops = [d for d in self.drops if d[2] < self.LIFETIME]

    def render(self, frame: Frame, theme: Theme) -> None:
        for x, y, age in self.drops:
            radius = age * self.SPEED
            fade = 1.0 - age / self.LIFETIME
            colour = self.color_at(theme, 0.2 + 0.8 * fade)
            steps = max(8, int(radius * 6))
            for i in range(steps):
                angle = math.tau * i / steps
                # Terminal cells are about twice as tall as wide: halve the vertical radius.
                px = round(x + math.cos(angle) * radius)
                py = round(y + math.sin(angle) * radius / 2)
                frame.put(px, py, "o" if fade > 0.5 else ".", colour)
```

## Registering it

1. Put the class in the module in `staticfx/effects/builtin/` that fits best
   (`particles.py`, `fields.py`, `shapes.py`, `signals.py`, `simulations.py`
   or `terminal.py`).
2. Add one row to `CATALOGUE` in `staticfx/effects/builtin/__init__.py`:

   ```python
   (("raindrops", "Raindrops", FIELDS, "Rings spreading on a puddle", Raindrops),)
   ```

   The key must be unique, lowercase and stable: it's stored in people's
   favourites and saved looks. The category must be one of `CATEGORIES`.

3. Bump the count in the README if you're adding to the 50.

That's all: the browser, the CLI, `staticfx doctor` and the test suite pick
it up from the catalogue.

## Effects built on a field

If your effect computes a brightness for every cell, like plasma or a
tunnel, subclass `FieldEffect` from `fields.py` instead and implement only
`value(x, y) -> float`. It gives you aspect-corrected coordinates (`self.xs`,
`self.ys`), polar tables (`self.rr`, `self.aa`), a clock (`self.t`) and an
optional starry background.

## Checking it

```bash
python -m pytest tests/test_effects.py -k raindrops   # every size, every timestep, ASCII mode
staticfx render raindrops --size 80x24                 # look at a frame
staticfx -e raindrops                                  # watch it
```

`test_effects.py` runs every built-in at sizes from 1×1 to 250×70 with odd
timesteps and both character modes, checks it draws something, and runs the
long-lived ones for a simulated minute. If your effect passes that, it's
safe to ship.

## Performance

Python draws one cell at a time, so the cost is roughly *cells × work per
cell*. A 250×70 terminal is 17,500 cells; at 30 fps you have about 2 µs per
cell. Some habits that help:

- Precompute anything that only depends on size in `on_resize`.
- In hot loops, copy attributes into locals (`cells = frame.cells`) and
  write to `cells[y][x]` directly; `put` is for convenience.
- Draw only what's visible rather than every cell.
- Use the cached theme palette (`self.palette(theme)`) instead of calling
  `theme.ramp()` per cell.
