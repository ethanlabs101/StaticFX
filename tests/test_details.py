"""Smaller pieces: filters, the fetch overlay, adaptive detail, name lookup, dialogs."""

from __future__ import annotations

import random
import subprocess
from pathlib import Path

import pytest
from conftest import press, screen, type_text

from staticfx import integrations
from staticfx.app.app import App
from staticfx.cli import main
from staticfx.core.color import RGB
from staticfx.core.frame import Frame
from staticfx.effects.engine import EngineEffect, Recipe, generate
from staticfx.effects.registry import Registry
from staticfx.library.legacy import recipe_from_plugin, recipe_from_v2
from staticfx.postfx import PostFX, recolour, scanlines, tear
from staticfx.themes import STATIC_THEMES, normalize
from staticfx.ui.dialogs import Prompt
from staticfx.ui.settings import SettingsScreen


def filled(width: int = 20, height: int = 6) -> Frame:
    frame = Frame(width, height)
    for y in range(height):
        frame.text(0, y, "#" * width, RGB(200, 100, 50))
    frame.put(0, 0, " ", RGB(0, 0, 0))
    return frame


def test_scanlines_darken_odd_rows() -> None:
    frame = filled()
    scanlines(frame)
    assert frame.cells[0][1].color == RGB(200, 100, 50)
    assert frame.cells[1][1].color == RGB(140, 70, 35)


def test_tear_shifts_rows_and_keeps_the_frame_size() -> None:
    for seed in range(20):
        frame = filled()
        tear(frame, random.Random(seed))
        assert all(len(line) == 20 for line in frame.lines())


def test_recolour_keeps_blanks_and_brightness() -> None:
    frame = filled()
    frame.put(1, 0, "#", RGB(20, 10, 5))
    recolour(frame, 0.0)
    assert frame.cells[0][0].char == " "
    assert max(frame.cells[0][1].color) < max(frame.cells[0][2].color)


def test_postfx_lists_what_is_on() -> None:
    post = PostFX(crt=True, recolour=True, rng=random.Random(1))
    post.update(0.5)
    post.apply(filled())
    assert post.active() == ["crt", "recolour"]


def test_overlay_colours_labels() -> None:
    frame = filled(40, 8)
    theme = STATIC_THEMES["ocean"]
    integrations.overlay(frame, theme, "user@box\nOS: Linux\nlong line without a label")
    row = frame.lines()[3]
    assert "OS: Linux" in row
    assert frame.cells[3][3].color == theme.accent


def test_system_info_reports_missing_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integrations.shutil, "which", lambda name: None)
    with pytest.raises(RuntimeError, match="not installed"):
        integrations.system_info()


def test_system_info_strips_colours(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(integrations.shutil, "which", lambda name: "/bin/" + name)

    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout="\x1b[31mOS\x1b[0m: Linux\t!")

    monkeypatch.setattr(integrations.subprocess, "run", fake_run)
    assert integrations.system_info("neofetch") == "OS: Linux       !"


def test_fetch_command(monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path) -> None:
    monkeypatch.setattr("staticfx.cli.commands.system_info", lambda tool: "OS: Testix")
    assert main(["fetch", "-e", "plasma", "--data-dir", str(tmp_path)]) == 0
    assert "Testix" in capsys.readouterr().out
    monkeypatch.setattr(
        "staticfx.cli.commands.system_info",
        lambda tool: (_ for _ in ()).throw(RuntimeError("fastfetch is not installed")),
    )
    assert main(["fetch", "--data-dir", str(tmp_path)]) == 1


def test_adaptive_mode_trades_detail_for_speed() -> None:
    effect = EngineEffect(random.Random(1), recipe=generate(5)[0])
    effect.adaptive = True
    effect.resize(80, 24)
    start = effect.level
    effect.cost = 1.0  # pretend every frame is slow
    for _ in range(60):
        effect.update(1 / 30)
    assert effect.level > start
    effect.cost = 0.0
    for _ in range(400):
        effect.update(1 / 30)
    assert effect.level == start


def test_ascii_mode_replaces_unicode_charsets() -> None:
    recipe = Recipe.from_dict({"layers": [{"kind": "flow"}], "charset": " ░▒▓█"})
    effect = EngineEffect(random.Random(1), recipe=recipe)
    effect.ascii_only = True
    effect.resize(30, 8)
    frame = Frame(30, 8)
    effect.draw(frame, STATIC_THEMES["matrix"])
    assert "\n".join(frame.lines()).isascii()


@pytest.mark.parametrize("kind", ["theme", "rainbow", "duo", "angular"])
def test_every_palette_renders(kind: str) -> None:
    recipe = Recipe.from_dict({"layers": [{"kind": "rings"}], "palette": {"kind": kind}})
    effect = EngineEffect(random.Random(1), recipe=recipe)
    effect.resize(20, 6)
    frame = Frame(20, 6)
    effect.draw(frame, STATIC_THEMES["fire"])
    assert any(line.strip() for line in frame.lines())


def test_legacy_palettes_convert() -> None:
    base = {"layers": [["spiral", {}]], "ops": [], "tfs": [["kaleido", {}]], "posts": [["saw", {}]]}
    rainbow = recipe_from_v2({**base, "pal": ["rainbow", 1.0, 0.1, 0.5], "pulse": True})
    assert rainbow.palette.kind == "rainbow" and rainbow.pulse == 2.0
    assert rainbow.warps[0].kind == "kaleidoscope" and rainbow.filters[0].kind == "sawtooth"
    duo = recipe_from_v2({**base, "pal": ["duo", [255, 0, 0], [0, 0, 255]]})
    assert duo.palette.first == RGB(255, 0, 0)
    with pytest.raises(ValueError, match="1-3 layers"):
        recipe_from_v2({"layers": []})
    with pytest.raises(ValueError):
        recipe_from_v2({"layers": [["nonsense", {}]]})
    with pytest.raises(ValueError, match="unknown plugin generator"):
        recipe_from_plugin({"generator": "lasers"})


def test_registry_resolves_what_people_type(app: App) -> None:
    registry = Registry()
    assert registry.resolve("Matrix Rain") == "matrix"
    assert registry.resolve("proc7") == registry.resolve("proc_007") == "proc_007"
    assert registry.resolve("1") == registry.keys()[1]
    for bad in ("nothing", "proc_142", "proc9999", "99999"):  # 142 failed the quality gate
        with pytest.raises(KeyError):
            registry.resolve(bad)


def test_themes_accept_old_names() -> None:
    assert normalize(" Monochrome ") == "mono" and normalize("Arctic Blue") == "arctic"


def test_prompt_editing(app: App) -> None:
    results: list[str] = []
    app.push(Prompt(app, "Name", results.append, "abc"))
    press(app, "backspace", "enter")
    assert results == ["ab"]
    app.push(Prompt(app, "Name", results.append))
    press(app, "enter")
    assert "Type a name first" in screen(app)
    type_text(app, "  spaced   out ")
    press(app, "enter")
    assert results[-1] == "spaced out"
    app.push(Prompt(app, "Name", results.append))
    type_text(app, "x" * 60)
    press(app, "enter")
    assert results[-1] == "x" * 40


def test_settings_changes_apply_immediately(app: App) -> None:
    press(app, "o")
    settings = app.top
    assert isinstance(settings, SettingsScreen)
    rows = {row.label: i for i, row in enumerate(settings.selectable())}

    def adjust(label: str, *keys: str) -> None:
        settings.cursor.index = rows[label]
        press(app, *keys)

    adjust("Frame rate", "left", "left")
    adjust("Colours", "right")
    adjust("Auto-cycle every", "right")
    assert (app.settings.fps, app.settings.colour, app.settings.auto_seconds) == (
        20,
        "truecolor",
        20,
    )
    adjust("Next effect", "enter", "escape")  # Esc is reserved: cancels the capture
    assert app.keymap.action("right") == "next"
    adjust("Next effect", "enter", "ctrl-c")
    assert "reserved" in app.toast_text
    adjust("Reset all keys", "enter", "y")
    assert app.keymap.changes() == {}
