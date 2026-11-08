# Contributing

Thanks for wanting to help. Bug reports, new effects and fixes are all
welcome.

## Setting up

```bash
git clone https://github.com/ethanlabs101/StaticFX && cd StaticFX
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
```

StaticFX itself has no dependencies; those three are only for development.
The scripts in `tools/` also need Pillow (and `tools/demo.py` needs ffmpeg).

## Before you open a pull request

```bash
pytest                       # everything, including real-terminal tests
ruff check . && ruff format --check .
mypy
```

CI runs the same on Linux and macOS with Python 3.10 to 3.13.

## Where things go

[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) maps the code. In short:

- A new hand-written effect: [docs/WRITING_EFFECTS.md](docs/WRITING_EFFECTS.md).
- A new layer, warp or filter for the engine: add a function and a `Kind`
  entry in `staticfx/effects/engine/layers.py` (or `warps.py`,
  `filters.py`), then run `python tools/gen_docs.py` to update the format
  reference. The Studio picks it up by itself.
- A new screen: subclass `Screen` in `staticfx/ui/`, give it a `help` tuple,
  and add a test in `tests/test_ui.py`. It gets drawn at the minimum terminal
  size and in ASCII mode automatically if you add it to `OPENERS` there.
- A new main-view key: add the action to `ACTIONS` and a default to
  `DEFAULT_KEYS` in `staticfx/app/keymap.py`, and its handler in
  `PlayScreen.actions`. A test checks the three agree, and another checks the
  usage guide mentions it.

## Things that need care

- **Generated effects must not change by accident.** `test_engine.py`
  fingerprints all 1,000 recipes. If you change `generate.py` or the
  maths behind an existing layer, warp or filter, the fingerprint changes and
  everyone's `proc_NNN` favourites point at different pictures. Do it only on
  purpose, update the fingerprint, rerun `python tools/curate.py`, and note it
  in the changelog.
- **Effect keys are forever.** They're stored in favourites, looks and
  scripts. Rename the label, never the key.
- **Saved files must stay readable.** If you change the `.sfx` format or
  `config.json`, bump the version and keep reading the old one (see
  `library/legacy.py` and `config._migrate`).
- **Nothing may stop the app from starting.** Bad files and values are
  reported and skipped, never raised.

## Style

`ruff format` decides formatting (100 columns). Beyond that: write code for
the next person to read, keep functions short, name things for what they
mean, and comment on *why*, not *what*. Docstrings on modules, classes and
anything non-obvious; not on every getter.

## Reporting a bug

Please include the output of `staticfx doctor`, your terminal and OS, and
what you pressed. If an effect looks wrong, `staticfx render EFFECT --ansi
--seed 1 --out frame.txt` captures it exactly.
