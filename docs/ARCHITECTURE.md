# Architecture

StaticFX is about 9,000 lines of Python (nearly half of it the effects themselves) with no
dependencies. This page is
the map: what lives where, what happens every frame, and why it's built the
way it is.

## Layers

```
cli/            parse the command line, run a subcommand
  │
app/            the interactive app: settings, player, screen stack, run loop
  │   ui/       screens (browser, Studio, settings, ...) and drawing helpers
  │
effects/        what can be drawn: built-ins, the procedural engine, the registry
library/        what the user saves: settings, .sfx effects, looks
  │
core/           terminal plumbing: colour, frames, rendering, keys, terminal modes
```

Imports only point down this list. `core` knows nothing about effects;
`effects` knows nothing about the app; screens reach the app only through
the `App` object they're given. The one upward reference, `App` creating the
first `PlayScreen`, is deliberate: the app owns its screen stack.

## Modules

Path | What it does
--- | ---
`core/color.py` | `RGB` and the few colour operations effects need.
`core/frame.py` | `Frame`: a grid of `(char, colour)` cells. Spaces are transparent.
`core/renderer.py` | Encodes a frame as ANSI, writing only rows that changed since the last frame.
`core/keys.py` | Turns raw terminal bytes into key names (`up`, `ctrl-e`, `a`).
`core/terminal.py` | Takes over the terminal (alternate screen, raw-ish input) and always gives it back: on exit, exceptions, `SIGTERM`, and around `Ctrl-Z`.
`core/clock.py` | Frame pacing.
`themes.py` | Colour themes as 256-entry ramps, plus the animated Rainbow and Strobe.
`postfx.py` | The CRT, glitch and recolour filters applied to finished frames.
`sysinfo.py` | Runs fastfetch or neofetch and draws its output over a frame, for `staticfx fetch`.
`effects/base.py` | The `Effect` base class and its contract.
`effects/builtin/` | The 50 hand-written effects, and `CATALOGUE`, which names and groups them.
`effects/engine/` | The procedural engine: `schema.py` (parameter descriptions), `layers.py`, `warps.py`, `filters.py`, `recipe.py` (the data model and its JSON form), `generate.py` (seed → recipe), `effect.py` (drawing a recipe).
`effects/registry.py` | Every playable effect in a stable order, and name lookup.
`effects/curated.py` | Which generated effects are excluded, and the Gallery.
`library/config.py` | `Settings` and a loader that never fails.
`library/effects.py` | Reading and writing `.sfx` files.
`library/legacy.py` | Converting StaticFX 1.x files.
`library/looks.py` | Saved looks and the built-in ones.
`app/app.py` | `App`: settings, library, player, screen stack, toasts, saving.
`app/player.py` | What's on screen: the effect, theme, speed, filters, and previews.
`app/keymap.py` | Main-view actions and their keys.
`app/session.py` | The real-terminal loop, and headless rendering.
`ui/screen.py` | The `Screen` base class.
`ui/widgets.py` | Box characters, colours, panels, scrolling lists.
`ui/play.py`, `browser.py`, `pickers.py`, `studio.py`, `settings.py`, `help.py`, `dialogs.py` | One file per screen.
`cli/parser.py`, `cli/commands.py` | Arguments, and one function per subcommand.

## One frame

`session.run` loops:

1. **Input.** `KeyReader` collects pending keys. `App.handle_key` gives each
   one to the screen on top of the stack. `Ctrl-Z` is the exception: the app
   asks the session to suspend.
2. **Resize.** If the terminal changed size, the frame, the player and every
   effect are resized and the screen is redrawn from scratch.
3. **Update.** `App.update(dt)` advances the player (which advances the
   effect, scaled by speed), every screen, the toast timer and auto-cycle.
4. **Draw.** `App.draw(frame)` asks the player to draw the effect and apply
   filters, then draws each screen from the bottom up.
5. **Output.** `Renderer.diff` encodes the rows that changed; one `write`.
6. **Save.** If settings changed, they're written, at most once a second.
7. **Wait** for the next frame.

Nothing in `App` or the screens touches the terminal, which is why the test
suite can drive the whole app with key presses and inspect the frames.

## Decisions

**No curses.** `curses` would handle terminal modes, but it's not available
on every Python build, its colour support stops at 256 colours without
work, and it makes the app much harder to test. Writing ANSI directly is a
few hundred lines in `core/` and gives 24-bit colour everywhere.

**Signals off in the terminal.** The terminal is put in a mode where Ctrl-C
and Ctrl-Z arrive as keys rather than signals. Each screen decides what they
mean, so Ctrl-C in the Studio can ask before throwing away your work instead
of killing the program. Suspend is done by hand: restore the terminal, stop,
re-enter when resumed.

**Row-level diffing.** Only rows that changed since the last frame are
written. For busy effects that saves little (about 7% of bytes across the
built-ins, measured at 120×36), but a paused effect or a slow one costs
almost nothing to redraw. Cell-level diffing would save more on busy
effects, at the price of a cursor move per changed run and noticeably more
code in the hottest loop; it's the obvious next step if output volume ever
becomes the bottleneck.

**`RGB` is a `NamedTuple`.** Thousands of colours are created per frame;
tuples are the cheapest immutable, hashable value Python has.

**A screen stack.** Each mode (browser, Studio, a confirmation dialog) is a
`Screen` with `handle`, `update` and `draw`. The top one gets the keys.
Opening a dialog over the Studio is just a push; nothing else needs to know.
This replaced a single class with a long `if menu: ... elif studio: ...`
chain.

**One parameter schema.** Each layer, warp and filter kind declares its
parameters once (`Param` in `engine/schema.py`). That one description is used
to validate `.sfx` files, fill in defaults, build the Studio's controls and
generate the reference in `EFFECT_FORMAT.md`, so they can't drift apart.

**Generated effects never change.** `generate(seed)` draws its random values
in a fixed order, and a test fingerprints all 1,000 recipes. Favourites,
saved looks and scripts that say `proc_042` keep meaning the same picture.
Changing the generator on purpose means updating the fingerprint and saying
so in the changelog.

**A quality gate, not a hand filter.** `tools/curate.py` renders every
generated recipe and excludes the ones that are blank, frozen or a solid
wall. It's repeatable: rerun it after changing the engine. The Gallery, by
contrast, is picked by eye; taste doesn't automate well.

**Settings can't stop the app from starting.** Every value in `config.json`
is checked on its own; a bad one is replaced by its default with a message.
The same goes for `.sfx` files and looks: a broken file is skipped and
reported, never fatal. The last effect you played may have been deleted;
StaticFX says so and starts on Matrix Rain.

**Adaptive detail.** The engine samples the pattern on a grid of blocks
rather than every cell when the terminal is large, and in the interactive
app it also coarsens or refines that grid based on how long frames take.
Headless rendering (`staticfx render`) keeps full detail so output is
deterministic.

## Testing

`tests/` mirrors the layers:

File | Covers
--- | ---
`test_core.py` | Colours, frame clipping, renderer diffing, key decoding.
`test_engine.py` | The schema, recipe validation (including a fuzz test that corrupts real recipes), and the generated-effects fingerprint.
`test_effects.py` | Every built-in, and a sample of generated effects, at sizes from 1×1 to 250×70, with odd timesteps, in both character modes.
`test_library.py` | Settings, `.sfx` files, looks, and real files from StaticFX 1.x.
`test_app.py` | Startup, playing, favourites, looks, key bindings, saving.
`test_ui.py` | Every screen driven by key presses, and drawn at the minimum size and in ASCII mode.
`test_cli.py` | Every subcommand, and the 1.x flags.
`test_terminal.py` | The real program in a pseudo-terminal: quitting, Ctrl-C, Ctrl-Z, resizing, `SIGTERM`, a corrupt config.
`test_docs.py` | Generated docs are current and the README and guides match the code.
`test_details.py` | Filters, the fetch overlay, adaptive detail, name lookup, dialogs.
