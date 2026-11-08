"""Docs that are generated from code, or that describe it, must stay true."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from staticfx.app.keymap import ACTIONS, DEFAULT_KEYS, key_label
from staticfx.effects.builtin import CATALOGUE

ROOT = Path(__file__).resolve().parent.parent


def test_effect_format_reference_is_current() -> None:
    command = [sys.executable, str(ROOT / "tools" / "gen_docs.py"), "--check"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout


def test_usage_guide_lists_every_default_key() -> None:
    usage = (ROOT / "docs" / "USAGE.md").read_text()
    for _group, description in ACTIONS.values():
        assert description in usage, f"USAGE.md doesn't mention: {description}"
    for key in DEFAULT_KEYS:
        assert f"`{key_label(key)}`" in usage, f"USAGE.md doesn't show the {key_label(key)} key"


def test_readme_effect_count_matches() -> None:
    readme = (ROOT / "README.md").read_text()
    assert f"{len(CATALOGUE)} hand-written effects" in readme
    gallery = re.search(r"(\d+) hand-picked", readme)
    from staticfx.effects.curated import GALLERY

    assert gallery and int(gallery.group(1)) == len(GALLERY)


def test_example_effect_in_the_guide_works() -> None:
    """The example in WRITING_EFFECTS.md is real code: run it through the effect checks."""
    import random

    from staticfx.core.frame import Frame
    from staticfx.themes import STATIC_THEMES

    guide = (ROOT / "docs" / "WRITING_EFFECTS.md").read_text()
    code = re.search(r"```python\n(import math.*?)```", guide, re.S)
    assert code, "example not found"
    namespace: dict = {}
    exec(code.group(1), namespace)  # the guide's own code, nothing else
    effect = namespace["Raindrops"](random.Random(1))
    drawn = 0
    for width, height in [(1, 1), (80, 24), (200, 60)]:
        effect.resize(width, height)
        frame = Frame(width, height)
        for _ in range(30):
            effect.update(1 / 15)
            frame.clear()
            effect.draw(frame, STATIC_THEMES["matrix"])
        drawn += sum(ch != " " for line in frame.lines() for ch in line)
    assert drawn > 0


def test_examples_load() -> None:
    from staticfx.library.effects import parse

    examples = sorted((ROOT / "examples").glob("*.sfx"))
    assert examples
    for path in examples:
        effect = parse(path.read_text(), path.stem)
        assert effect.name and effect.description


def test_readme_theme_count_matches() -> None:
    from staticfx.themes import names

    readme = (ROOT / "README.md").read_text()
    assert f"**{len(names())} colour themes**" in readme
