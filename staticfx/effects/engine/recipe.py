"""The recipe: a complete, serialisable description of a procedural effect.

Rendering a recipe goes through these stages for every cell::

    warps  ->  layer 1 (blend) layer 2 (blend) layer 3  ->  filters
           ->  extras (trail, pulse)  ->  characters  ->  palette

Recipes are plain data. ``to_dict``/``from_dict`` round-trip them through
JSON, which is the ``recipe`` object inside a ``.sfx`` file (the format is
documented in ``docs/EFFECT_FORMAT.md``).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any

from staticfx.core.color import RGB, parse_hex, to_hex
from staticfx.effects.engine.filters import BLENDS, FILTERS
from staticfx.effects.engine.layers import LAYERS
from staticfx.effects.engine.schema import Kind, Params
from staticfx.effects.engine.warps import WARPS

MAX_LAYERS, MAX_WARPS, MAX_FILTERS = 3, 3, 3

# Character sets ordered dark -> bright. The first character must be a space.
CHARSETS = (
    " .:-=+*#%@",
    " .oO0@",
    " .,:;ox%#@",
    " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$",
    " .:#@",
    " #",
    " .+x*#X@",
    " /\\|-+X#",
    " .:!|",
    " 0123456789",
    " ._-~=+*",
    " ░▒▓█",
    " ▁▂▃▄▅▆▇█",
)
ASCII_FALLBACK = CHARSETS[0]

PALETTES = ("theme", "rainbow", "duo", "angular")
MAGENTA, CYAN = RGB(255, 0, 170), RGB(0, 220, 255)


@dataclass
class Stage:
    """One layer, warp or filter. ``blend`` joins a layer to the ones before it."""

    kind: str
    params: Params
    blend: str = "average"


@dataclass
class Palette:
    """How brightness becomes colour.

    * ``theme`` - follow the current theme
    * ``rainbow`` - hue from brightness (``spread``), drifting over time (``drift``)
    * ``duo`` - black -> ``first`` -> ``second`` -> white
    * ``angular`` - hue from the angle around the centre
    """

    kind: str = "theme"
    spread: float = 1.0
    drift: float = 0.0
    offset: float = 0.0
    first: RGB = MAGENTA
    second: RGB = CYAN


@dataclass
class Recipe:
    layers: list[Stage]
    warps: list[Stage] = field(default_factory=list)
    filters: list[Stage] = field(default_factory=list)
    speed: float = 1.0
    charset: str = CHARSETS[0]
    glyph_rain: bool = False  # draw random tech glyphs instead of the charset
    dither: bool = False
    palette: Palette = field(default_factory=Palette)
    trail: float = 0.0  # 0 = off; otherwise how slowly bright cells fade (0.5-0.98)
    pulse: float = 0.0  # 0 = off; otherwise breaths per second
    scanlines: bool = False
    glitch: bool = False
    sparkle: float = 0.0  # fraction of cells that sparkle each frame
    seed: int = 0  # offsets the animation clock so siblings don't move in lockstep

    def copy(self) -> Recipe:
        return copy.deepcopy(self)

    def to_dict(self) -> dict[str, Any]:
        def stages(items: list[Stage], with_blend: bool = False) -> list[dict[str, Any]]:
            out = []
            for i, stage in enumerate(items):
                entry: dict[str, Any] = {"kind": stage.kind, **stage.params}
                if with_blend and i:
                    entry["blend"] = stage.blend
                out.append(entry)
            return out

        pal = self.palette
        palette: dict[str, Any] = {"kind": pal.kind}
        if pal.kind == "rainbow":
            palette.update(spread=pal.spread, drift=pal.drift, offset=pal.offset)
        elif pal.kind == "duo":
            palette.update(first=to_hex(pal.first), second=to_hex(pal.second))

        return {
            "layers": stages(self.layers, with_blend=True),
            "warps": stages(self.warps),
            "filters": stages(self.filters),
            "speed": self.speed,
            "charset": self.charset,
            "glyph_rain": self.glyph_rain,
            "dither": self.dither,
            "palette": palette,
            "trail": self.trail,
            "pulse": self.pulse,
            "scanlines": self.scanlines,
            "glitch": self.glitch,
            "sparkle": self.sparkle,
            "seed": self.seed,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Recipe:
        """Build a recipe from untrusted JSON.

        Out-of-range numbers are clamped and missing values take defaults;
        anything structurally wrong raises ``ValueError`` listing every problem.
        """
        if not isinstance(data, dict):
            raise ValueError("recipe must be an object")
        problems: list[str] = []

        def stages(key: str, kinds: dict[str, Kind], limit: int) -> list[Stage]:
            entries = data.get(key, [])
            if not isinstance(entries, list) or len(entries) > limit:
                problems.append(f"'{key}' must be a list of at most {limit}")
                return []
            out = []
            for entry in entries:
                kind = entry.get("kind") if isinstance(entry, dict) else entry
                if not isinstance(entry, dict) or not isinstance(kind, str) or kind not in kinds:
                    problems.append(f"unknown {key[:-1]} kind {kind!r}")
                    continue
                try:
                    params = kinds[kind].clean(entry)
                except ValueError as exc:
                    problems.append(f"{kind}: {exc}")
                    continue
                blend = entry.get("blend", "average")
                if not isinstance(blend, str) or blend not in BLENDS:
                    problems.append(f"unknown blend {blend!r}")
                    continue
                out.append(Stage(kind, params, blend))
            return out

        layers = stages("layers", LAYERS, MAX_LAYERS)
        warps = stages("warps", WARPS, MAX_WARPS)
        filters = stages("filters", FILTERS, MAX_FILTERS)
        if not layers and not problems:
            problems.append("a recipe needs at least one layer")

        def number(key: str, default: float, low: float, high: float) -> float:
            value = data.get(key, default)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                problems.append(f"'{key}' must be a number")
                return default
            return min(high, max(low, float(value)))

        charset = data.get("charset", CHARSETS[0])
        if not isinstance(charset, str) or len(charset) < 2 or charset[0] != " ":
            problems.append("'charset' must be a string of 2+ characters starting with a space")
            charset = CHARSETS[0]

        palette = Palette()
        raw = data.get("palette", {"kind": "theme"})
        if not isinstance(raw, dict) or raw.get("kind") not in PALETTES:
            problems.append(f"palette kind must be one of {', '.join(PALETTES)}")
        else:
            palette.kind = raw["kind"]
            try:
                palette.spread = float(raw.get("spread", palette.spread))
                palette.drift = float(raw.get("drift", palette.drift))
                palette.offset = float(raw.get("offset", palette.offset)) % 1.0
                palette.first = parse_hex(str(raw.get("first", to_hex(palette.first))))
                palette.second = parse_hex(str(raw.get("second", to_hex(palette.second))))
            except (TypeError, ValueError) as exc:
                problems.append(f"palette: {exc}")

        recipe = cls(
            layers=layers,
            warps=warps,
            filters=filters,
            speed=number("speed", 1.0, 0.05, 6.0),
            charset=charset,
            glyph_rain=bool(data.get("glyph_rain", False)),
            dither=bool(data.get("dither", False)),
            palette=palette,
            trail=number("trail", 0.0, 0.0, 0.98),
            pulse=number("pulse", 0.0, 0.0, 8.0),
            scanlines=bool(data.get("scanlines", False)),
            glitch=bool(data.get("glitch", False)),
            sparkle=number("sparkle", 0.0, 0.0, 0.05),
            seed=int(number("seed", 0, 0, 2**31)),
        )
        if problems:
            raise ValueError("; ".join(problems))
        return recipe
