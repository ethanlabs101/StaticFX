# The `.sfx` effect format

Effects you make in the Studio are saved as `.sfx` files in
`~/.config/staticfx/effects/`. They're plain JSON, small enough to paste into
a chat or a gist, and safe to hand-edit: StaticFX checks every value when it
loads a file and tells you what's wrong instead of crashing.

To share one, use `staticfx export my_neon_sunrise neon.sfx`. To add someone
else's, use `staticfx import neon.sfx` (or drop the file into the effects folder).

## A complete file

```json
{
  "format": "staticfx-effect",
  "version": 3,
  "name": "Neon Sunrise",
  "description": "Spirals through a kaleidoscope",
  "created": "2026-11-07",
  "recipe": {
    "layers": [
      {"kind": "spiral", "scale": 6.0, "speed": 0.8, "arms": 3},
      {"kind": "rings", "scale": 9.0, "speed": -0.5, "shape": "circle", "blend": "screen"}
    ],
    "warps": [{"kind": "kaleidoscope", "segments": 6, "spin": 0.1}],
    "filters": [{"kind": "posterize", "levels": 5}],
    "speed": 1.0,
    "charset": " .:-=+*#%@",
    "glyph_rain": false,
    "dither": true,
    "palette": {"kind": "rainbow", "spread": 1.0, "drift": 0.1, "offset": 0.0},
    "trail": 0.0,
    "pulse": 0.0,
    "scanlines": false,
    "glitch": false,
    "sparkle": 0.0,
    "seed": 0
  }
}
```

The file name is the effect's identity: `neon_sunrise.sfx` plays as
`my_neon_sunrise`. The `name` inside is what's shown in menus.

## How a recipe is drawn

For every cell on screen, StaticFX takes the cell's position and runs it through:

1. **Warps**, in order: each one moves the point (rotating, mirroring, tiling...).
2. **Layers**: each one turns the point into a brightness from 0 to 1. The
   first layer sets the value; each later layer is combined with it using its
   `blend`.
3. **Filters**, in order: each one reshapes the brightness.
4. **Extras**: `trail` keeps bright cells lit for a while, `pulse` makes the
   whole picture breathe.
5. **Characters**: the brightness picks a character from `charset`, which runs
   from dark (always a space) to bright.
6. **Colour**: from the `palette`.

## Top-level fields

Field | Required | Meaning
--- | --- | ---
`format` | yes | Always `"staticfx-effect"`.
`version` | yes | `3`. Version 2 files from StaticFX 1.x are converted when read.
`name` | no | Display name, up to 40 characters. Defaults to "Untitled".
`description` | no | One line shown in the effect browser, up to 200 characters.
`created` | no | Date string; informational only.
`recipe` | yes | See below.

## Recipe fields

Field | Values | Default | Meaning
--- | --- | --- | ---
`layers` | list of 1 to 3 | (required) | Pattern generators; see the reference below.
`warps` | list of 0 to 3 | `[]` | Coordinate warps, applied in order.
`filters` | list of 0 to 3 | `[]` | Brightness filters, applied in order.
`speed` | 0.05 to 6 | `1.0` | Overall animation speed.
`charset` | string, 2+ characters starting with a space | `" .:-=+*#%@"` | Characters from dark to bright. In ASCII-only mode a non-ASCII charset is replaced by the default.
`glyph_rain` | `true` / `false` | `false` | Scatter random glyphs, denser where it's brighter, instead of using `charset`.
`dither` | `true` / `false` | `false` | Ordered dithering between characters, for smoother gradients.
`palette` | object | `{"kind": "theme"}` | See [Palettes](#palettes).
`trail` | 0 to 0.98 | `0` | `0` is off. Otherwise how much brightness a cell keeps each frame.
`pulse` | 0 to 8 | `0` | `0` is off. Otherwise breaths per second.
`scanlines` | `true` / `false` | `false` | Darken every other row.
`glitch` | `true` / `false` | `false` | Occasionally tear a row sideways.
`sparkle` | 0 to 0.05 | `0` | Fraction of cells that twinkle each frame.
`seed` | whole number ≥ 0 | `0` | Offsets the animation clock, so two otherwise identical effects don't move in lockstep.

Each entry in `layers`, `warps` and `filters` is an object with a `kind` and
that kind's parameters. Missing parameters take their defaults; numbers
outside the allowed range are clamped. Layers after the first also take a
`blend` (default `average`).

## Palettes

`kind` | Extra fields | Meaning
--- | --- | ---
`theme` | | Follow the current theme. Recommended: the effect then works with every theme.
`rainbow` | `spread` (number), `drift` (number), `offset` (0 to 1) | Hue from brightness × `spread`, rotating by `drift` turns per second.
`duo` | `first`, `second` (hex colours like `"#ff00aa"`) | Black → `first` → `second` → white.
`angular` | | Hue from the angle around the centre of the screen.

## Reference

Generated from the code by `tools/gen_docs.py`; a test fails if it falls out of date.

<!-- reference:start -->

### Layers

**`grid`**: crossing sine waves

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`scale_y` | Scale (vertical) | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`

**`rings`**: concentric rings

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`shape` | Ring shape | one of `circle`, `diamond`, `square`, `star` | `circle`

**`spiral`**: rotating spiral arms

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`arms` | Arms | whole number, 1 to 12 | `4`

**`rays`**: light rays from the centre

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Twist | number, 0.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`arms` | Arms | whole number, 1 to 12 | `4`

**`checker`**: sliding checkerboard

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`scale_y` | Scale (vertical) | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`

**`moire`**: two interfering ring sets

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`

**`flow`**: liquid domain-warped waves

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`

**`blobs`**: merging metaballs

Key | Meaning | Values | Default
--- | --- | --- | ---
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`count` | Count | whole number, 2 to 9 | `4`

**`julia`**: the Julia fractal, breathing

Key | Meaning | Values | Default
--- | --- | --- | ---
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`c_real` | Shape (real) | number, -1.0 to 0.5 | `-0.6`
`c_imag` | Shape (imaginary) | number, -1.0 to 1.0 | `0.2`

**`mandelbrot`**: zooming into the Mandelbrot set

Key | Meaning | Values | Default
--- | --- | --- | ---
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`spot` | Zoom target | one of `seahorse`, `spiral`, `needle`, `elephant`, `bulb`, `tendril` | `seahorse`

**`voronoi`**: drifting cells

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`count` | Count | whole number, 2 to 9 | `4`
`style` | Style | one of `edges`, `distance`, `cells` | `edges`

**`hexagons`**: honeycomb interference

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`

**`lissajous`**: woven sine curves

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`x_waves` | Waves across | whole number, 1 to 9 | `3`
`y_waves` | Waves down | whole number, 1 to 12 | `4`

**`tunnel`**: flying down a twisted tunnel

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`arms` | Arms | whole number, 1 to 12 | `4`

**`sources`**: circling wave emitters

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`count` | Count | whole number, 2 to 9 | `4`

**`shape`**: outlines pulsing outwards

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`shape` | Shape | one of `box`, `cross`, `star`, `triangle`, `ring` | `ring`
`points` | Star points | whole number, 2 to 12 | `5`

**`noise`**: drifting cloudy noise

Key | Meaning | Values | Default
--- | --- | --- | ---
`scale` | Scale | number, 1.0 to 20.0 | `6.0`
`speed` | Motion | number, -3.0 to 3.0 | `1.0`
`seed` | Noise seed | whole number, 0 to 1048576 | `1`

### Warps

**`rotate`**: spin the whole pattern

Key | Meaning | Values | Default
--- | --- | --- | ---
`spin` | Spin | number, -1.5 to 1.5 | `0.2`

**`zoom`**: scale in and out, breathing

Key | Meaning | Values | Default
--- | --- | --- | ---
`zoom` | Zoom | number, 0.5 to 3.0 | `1.5`
`pulse` | Pulse | number, 0.0 to 0.8 | `0.3`
`pulse_rate` | Pulse rate | number, 0.1 to 3.0 | `0.8`

**`kaleidoscope`**: mirror into wedges around the centre

Key | Meaning | Values | Default
--- | --- | --- | ---
`segments` | Segments | whole number, 2 to 16 | `6`
`spin` | Spin | number, -1.0 to 1.0 | `0.2`

**`mirror`**: reflect across an axis

Key | Meaning | Values | Default
--- | --- | --- | ---
`axis` | Axis | one of `x`, `y`, `xy` | `xy`

**`tile`**: repeat in a drifting grid

Key | Meaning | Values | Default
--- | --- | --- | ---
`tiles` | Tiles | number, 1.0 to 6.0 | `2.0`
`drift_x` | Drift across | number, -1.0 to 1.0 | `0.2`
`drift_y` | Drift down | number, -1.0 to 1.0 | `0.1`

**`swirl`**: twist the middle like stirred paint

Key | Meaning | Values | Default
--- | --- | --- | ---
`twist` | Twist | number, -6.0 to 6.0 | `2.0`

**`wave`**: wobble sideways in waves

Key | Meaning | Values | Default
--- | --- | --- | ---
`strength` | Strength | number, 0.0 to 1.0 | `0.3`
`frequency` | Frequency | number, 0.5 to 10.0 | `3.0`

**`polar`**: unroll circles into lines

No parameters.

**`fold`**: fold space over on itself

Key | Meaning | Values | Default
--- | --- | --- | ---
`offset` | Offset | number, 0.0 to 1.0 | `0.3`
`angle` | Angle | number, 0.0 to 3.14 | `0.7`
`folds` | Folds | whole number, 1 to 4 | `2`

**`pixelate`**: chunky low-resolution blocks

Key | Meaning | Values | Default
--- | --- | --- | ---
`resolution` | Resolution | number, 2.0 to 24.0 | `8.0`

**`ripple`**: rings travelling out from the centre

Key | Meaning | Values | Default
--- | --- | --- | ---
`strength` | Strength | number, 0.0 to 1.0 | `0.3`
`frequency` | Frequency | number, 2.0 to 24.0 | `10.0`
`speed` | Speed | number, -6.0 to 6.0 | `2.0`

### Filters

**`gamma`**: darken or lift the midtones

Key | Meaning | Values | Default
--- | --- | --- | ---
`gamma` | Gamma | number, 0.3 to 3.0 | `1.2`

**`posterize`**: flatten into a few bands

Key | Meaning | Values | Default
--- | --- | --- | ---
`levels` | Levels | whole number, 2 to 12 | `4`

**`contour`**: draw lines along brightness levels

Key | Meaning | Values | Default
--- | --- | --- | ---
`lines` | Lines | whole number, 1 to 10 | `3`
`sharpness` | Sharpness | number, 0.3 to 3.0 | `1.0`

**`invert`**: swap dark and bright

No parameters.

**`cycle`**: slide brightness around over time

Key | Meaning | Values | Default
--- | --- | --- | ---
`speed` | Speed | number, -1.0 to 1.0 | `0.3`

**`pulse`**: fade in and out

Key | Meaning | Values | Default
--- | --- | --- | ---
`rate` | Rate | number, -1.0 to 1.0 | `0.3`

**`fold`**: brightest where it was mid-grey

No parameters.

**`sawtooth`**: repeat the brightness range

Key | Meaning | Values | Default
--- | --- | --- | ---
`repeats` | Repeats | whole number, 2 to 10 | `4`

### Blends

`average`, `multiply`, `lighten`, `darken`, `difference`, `screen`, `wrap`, `displace`

<!-- reference:end -->

## Errors

A file that can't be used is skipped with a message (in the app, and in
`staticfx doctor`) that names the file and every problem in it, for example:

```
skipped neon.sfx: unknown layer kind 'sprial'; spiral: arms must be a number
```

Other effects keep loading. A file written by a newer StaticFX says so
instead of guessing.

## StaticFX 1.x files

Version 2 files (from the 1.x Studio) and 1.x plugin files (`"format": "sfx"`,
which used to live in a hidden `plugins/` folder) are converted automatically.
The first time 2.x runs, it copies any old plugins into your effects folder;
the originals are left where they were.
