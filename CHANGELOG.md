# Changelog

## 2.1.0 (2026-11-09)

- `staticfx stream` writes frames continuously in a small text format, so
  other programs can draw StaticFX animations (NeoWave uses it for its
  animated backgrounds). The format is in [docs/STREAM.md](docs/STREAM.md).
- `list`, `themes` and `looks` take `--tsv` for tab-separated output.

## 2.0.1 (2026-11-08)

- System info in the app: `y` lays your fastfetch or neofetch output over
  the running effect, which keeps animating. It's on the welcome card, the
  hint line and the help screen.
- `staticfx fetch` now opens the live app with the info showing. The old
  still frame is `staticfx fetch --once`, for shell startup files.
- Install notes for pipx on each platform, and for Android through Termux.
- Fixed a test that failed at random on macOS (the app itself was fine).

## 2.0.0 (2026-11-07)

A rewrite. Your settings, favourites, looks and Studio effects carry over
automatically.

### New

- An effect browser with groups (Favourites, Recent, My Effects, Gallery,
  seven built-in categories, Generated), search that ranks name matches first,
  and live preview beside the list.
- A Gallery of 47 of the best generated effects, picked by hand.
- A settings screen (`o`): frame rate, character set, colour mode,
  auto-cycle interval, and rebinding any key, with conflict warnings.
- A welcome card on first run, an optional status bar (`i`), and a key hint
  line on start-up.
- In the Studio, every control has a real name and range, with a one-line
  explanation of the selected setting; save as a copy (`a`); unlimited undo.
- Subcommands: `list`, `themes`, `looks`, `new`, `import`, `export`,
  `render`, `fetch`, `doctor`. The 1.x flags still work.
- `staticfx doctor` checks your terminal and saved files and renders
  every effect once.
- 26 themes, up from 13, including takes on Dracula, Nord, Gruvbox,
  Solarized, Catppuccin and Tokyo Night. The theme menu shows each palette.
- Plain keys everywhere: menus no longer need Ctrl combinations: in the
  browser `/` searches and `f`, `e`, `n`, `d` act on the highlighted effect.
  Letters work with or without Shift, and every menu closes with `q`.
- Built-in looks reworked into twelve, each with a description.
- Meteor Shower has a twinkling sky; Fireworks fill large terminals.
- Docs: usage guide, Studio guide, file format, writing effects, architecture.

### Changed

- One procedural engine: 1.x had two (`proc_*` and `gen_*`). The
  `gen_*` effects are gone; favourites pointing at them are dropped
  quietly. `proc_*` effects look the same as before.
- One `.sfx` format (version 3) with readable keys; 1.x Studio files
  (version 2) and 1.x plugins are converted when read; old plugins are copied
  into My Effects once.
- An automated quality gate removes 8 generated effects that were blank,
  frozen, or a solid wall.
- Strobe is hidden until you allow flashing in Settings, and the theme
  menu never previews it unless you have.
- The 1.x key that cycled rainbow and strobe is gone: Rainbow is a normal theme now. The old
  "rainbow" overlay is called **recolour** (`w`) and keeps the effect's
  shading.
- Presets and hacker scenes are merged into **looks**.
- The theme `monochrome` is now `mono` (the old name still works).
- Only rows that changed are redrawn each frame.

### Fixed

- A deleted effect or an unknown theme in `config.json` no longer stops
  StaticFX from starting; any bad setting is ignored with a message.
- Ctrl-C in the Studio asks before discarding your work instead of quitting.
- Ctrl-Z suspends cleanly and restores the screen on `fg`.
- A user effect named like a built-in (`plasma`) no longer hides the
  built-in on the command line.
- Plugin effects deleted in the menu came back on restart.
- Hand-edited config values of the wrong type were accepted silently.
- Below 40×12, a "terminal too small" message replaces menus that used to
  draw over each other.
- Glyphs outside the terminal's character set could appear in ASCII mode.

### Removed

- The `gen_*` engine and the hidden `--plugin-dir` option.

## 1.0.0

First release: 50 built-in effects, 2,000 procedural effects in two
families, themes, looks, the Effect Studio and `.sfx` sharing.
