# The Effect Studio

The Studio is where you make your own effects. Every generated effect is
built from the same parts, so you can start from scratch or remix one you
like.

- `n` starts a new effect from a random recipe.
- `e` on a generated effect opens a copy of it (called "... remix"); the
  original never changes.
- `e` on one of your own effects edits it in place.
- `e` and `n` do the same in the effect browser.

The settings are on the left and the effect plays live on the right. Every
change shows up on the next frame.

## Keys

Key | Action
--- | ---
`↑` `↓` | Choose a setting
`←` `→` | Change it
`PgUp` `PgDn` | Jump to the previous / next section
`Enter` | Rename (on the Name row)
`s` | Save. The first time, it asks for a name.
`a` | Save as a new copy
`r` | Randomise everything
`u` | Undo (as many steps as you like)
`t` | Try the next theme
`p` | Pause the preview
`Esc` / `Ctrl-C` | Close. If you have unsaved changes, it asks before throwing them away.

The title shows `*` while there are unsaved changes. Saved effects appear in
**My Effects** in the browser straight away, and play when you close the
Studio.

## What the parts do

An effect is a short pipeline: warp the coordinates, generate a pattern,
reshape its brightness, then turn brightness into characters and colours.

**Effect.** The name, and the overall *Speed*.

**Layers** (1 to 3) make the pattern: spirals, rings, fractals, Voronoi
cells, metaballs, noise and so on. Each has *Scale* (how big the features
are), *Motion* (how fast it moves; negative runs backwards) and a few knobs of
its own. Layers 2 and 3 have a *Blend* that decides how they combine with the
layers above: `average`, `multiply`, `lighten`, `darken`, `difference`,
`screen`, `wrap` (adds and wraps around, which makes bands) or `displace`
(uses the layers above to push this one around).

**Warps** (0 to 3) bend space before the layers are drawn: rotate, zoom,
kaleidoscope, mirror, tile, swirl, wave, polar, fold, pixelate, ripple. They
apply in order, so a kaleidoscope after a swirl looks different from a swirl
after a kaleidoscope.

**Filters** (0 to 3) reshape brightness after the layers: gamma, posterize
(flat bands), contour (lines along brightness levels), invert, cycle, pulse,
fold, sawtooth.

To add a layer, warp or filter, change the *Pattern* or *Kind* of the empty
slot at the end of its section from `off` to something. To remove one, set it
back to `off`; any after it go too, so remove from the end if you want to keep
the others.

**Look.**
- *Characters*: the set of characters, from dark to bright. Some use Unicode
  blocks; in ASCII-only mode those fall back to a plain set.
- *Glyph rain*: scatter random glyphs instead of shading.
- *Dither*: smoother gradients.
- *Colours*: `theme` follows whatever theme is on, which is usually what you
  want. `rainbow`, `duo` and `angular` set their own colours.

**Extras.** *Trail* makes bright cells fade slowly, *Pulse* makes the whole
effect breathe, *Sparkle* adds random twinkles, and *Scanlines* and *Glitch*
are built into the effect itself (separate from the CRT and glitch filters in
the main view).

## Tips

- Start from the Gallery. Open the browser (`m`), go to Gallery, pick one you
  like and press `e`.
- One layer with a kaleidoscope warp is often prettier than three layers.
- `posterize` with 3 or 4 levels and a two-character charset (`" #"`) gives a
  crisp poster look.
- If something looks muddy, check the blend: `screen` and `lighten` keep
  things bright, `multiply` and `darken` make them dark.
- `r` then `u` is a fine way to browse random ideas without losing your work.

## Sharing

```bash
staticfx export my_neon_sunrise neon.sfx   # write a file anyone can import
staticfx import neon.sfx                   # add someone else's
```

The file format is documented in [EFFECT_FORMAT.md](EFFECT_FORMAT.md); it's
small, readable JSON you can also write by hand. A few examples are in
[`examples/`](../examples).
