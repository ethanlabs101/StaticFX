"""Screens driven by key presses, and drawn at awkward sizes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import AppFactory, press, screen, type_text

from staticfx.app.app import App
from staticfx.ui.browser import Browser
from staticfx.ui.dialogs import Confirm, Prompt
from staticfx.ui.help import HelpScreen
from staticfx.ui.pickers import LookPicker, ThemePicker
from staticfx.ui.settings import SettingsScreen
from staticfx.ui.studio import Studio


def test_browser_search_ranks_name_matches_first(app: App) -> None:
    press(app, "m", "/")
    type_text(app, "plasma")
    browser = app.top
    assert isinstance(browser, Browser)
    assert browser.current is not None and browser.current.key == "plasma"
    assert app.player.preview_key == "plasma"  # live preview
    press(app, "enter")
    assert app.player.key == "plasma" and len(app.screens) == 1


def test_browser_escape_clears_search_then_closes(app: App) -> None:
    press(app, "m", "/")
    type_text(app, "zzzz")
    assert "No matches" in screen(app)
    press(app, "escape")
    assert isinstance(app.top, Browser) and app.top.query == "" and app.top.focus == "list"
    press(app, "escape")
    assert len(app.screens) == 1 and app.player.preview_key is None


def test_browser_groups(app: App) -> None:
    press(app, "m", "tab")  # All -> Favourites
    assert "None yet" in screen(app)
    press(app, "left", "down", "down", "down")  # Favourites -> Gallery
    browser = app.top
    assert isinstance(browser, Browser)
    assert browser.groups[browser.group.index].name == "Gallery"
    assert all(spec.key in app.registry.gallery for spec in browser.items)


def test_browser_favourite_edit_and_delete_guard(app: App) -> None:
    press(app, "m", "f")
    assert app.is_favorite("matrix")
    press(app, "d")
    assert "Only your own effects" in app.toast_text
    press(app, "e")
    assert "can't be edited" in app.toast_text and isinstance(app.top, Browser)


def test_browser_deletes_your_effect_after_confirming(app: App, tmp_path: Path) -> None:
    press(app, "n", "s")
    type_text(app, "Doomed")
    press(app, "enter", "escape")
    assert (tmp_path / "effects" / "doomed.sfx").exists()
    press(app, "m", "/")
    type_text(app, "doomed")
    press(app, "tab", "d")
    assert isinstance(app.top, Confirm)
    press(app, "n")
    assert (tmp_path / "effects" / "doomed.sfx").exists()
    press(app, "delete", "y")
    assert not (tmp_path / "effects" / "doomed.sfx").exists()
    assert "my_doomed" not in app.registry and app.player.key == "matrix"


def test_browser_search_plays_with_enter_and_keeps_filter_on_tab(app: App) -> None:
    press(app, "m", "/")
    type_text(app, "fire")
    browser = app.top
    assert isinstance(browser, Browser) and browser.focus == "search"
    press(app, "down")  # arrows move through results while typing
    press(app, "tab")
    assert browser.focus == "list" and browser.query == "fire"
    press(app, "f")  # a command again, not a letter in the search
    assert browser.query == "fire" and app.settings.favorites
    press(app, "/", "backspace", "backspace", "backspace", "backspace", "backspace")
    assert browser.query == "" and browser.focus == "list"
    press(app, "/", "enter")
    assert len(app.screens) == 1


def test_menus_close_with_q(app: App) -> None:
    for opener in ("m", "t", "l", "o"):
        press(app, opener, "q")
        assert len(app.screens) == 1 and app.running, opener


def test_studio_create_tweak_undo_and_save(app: App, tmp_path: Path) -> None:
    press(app, "n")
    studio = app.top
    assert isinstance(studio, Studio)
    assert app.player.showing is studio.preview
    before = studio.recipe.speed
    press(app, "down", "right", "right")  # Speed up twice
    assert studio.recipe.speed > before and studio.dirty
    press(app, "u")
    assert studio.recipe.speed > before  # undid one of two steps
    press(app, "s")
    assert isinstance(app.top, Prompt)
    type_text(app, "My Swirl")
    press(app, "enter")
    saved = json.loads((tmp_path / "effects" / "swirl.sfx").read_text())
    assert saved["name"] == "My Swirl" and saved["version"] == 3
    assert not studio.dirty
    press(app, "escape")
    assert len(app.screens) == 1 and app.player.key == "my_swirl"


def test_studio_edits_your_effect_in_place(app: App, tmp_path: Path) -> None:
    press(app, "n", "s")
    type_text(app, "Mine")
    press(app, "enter", "escape", "e")
    studio = app.top
    assert isinstance(studio, Studio) and studio.effect_id == "mine"
    press(app, "down", "right", "s")  # change speed, save: no prompt this time
    assert len(list((tmp_path / "effects").glob("*.sfx"))) == 1
    press(app, "a")
    type_text(app, "Copy")
    press(app, "enter")
    assert sorted(p.name for p in (tmp_path / "effects").glob("*.sfx")) == ["copy.sfx", "mine.sfx"]


def test_studio_remix_leaves_the_generated_effect_alone(app: App) -> None:
    app.play("proc_042")
    original = app.registry["proc_042"].recipe.to_dict()
    press(app, "e", "down", "right", "right")
    assert app.registry["proc_042"].recipe.to_dict() == original
    assert app.top.name.endswith("remix")


def test_studio_asks_before_discarding_and_ctrl_c_does_not_quit(app: App) -> None:
    press(app, "n", "down", "right", "ctrl-c")
    assert app.running and isinstance(app.top, Confirm)
    press(app, "n")
    assert isinstance(app.top, Studio)
    press(app, "escape", "y")
    assert len(app.screens) == 1 and app.player.override is None


def test_studio_unchanged_closes_without_asking(app: App) -> None:
    press(app, "n", "escape")
    assert len(app.screens) == 1


def test_studio_rows_follow_the_recipe(app: App) -> None:
    press(app, "n")
    studio = app.top
    assert isinstance(studio, Studio)
    pattern_rows = [r for r in studio.selectable() if r.label == "Pattern"]
    layers = len(studio.recipe.layers)
    assert len(pattern_rows) == min(3, layers + 1)  # each layer, plus an empty slot
    # turning layer 1's pattern through every kind never breaks the rows
    index = studio.selectable().index(pattern_rows[0])
    studio.cursor.index = index
    for _ in range(20):
        press(app, "right")
        assert studio.current.label == "Pattern"


def test_studio_sections_and_randomise(app: App) -> None:
    press(app, "n", "pagedown")
    studio = app.top
    assert isinstance(studio, Studio)
    assert studio.current.label == "Pattern"
    for _ in range(12):
        press(app, "pagedown")
    press(app, "pageup", "r")
    assert studio.history


def test_theme_picker_previews_and_restores(app: App) -> None:
    press(app, "t", "down")
    assert isinstance(app.top, ThemePicker)
    assert app.player.preview_theme == "cyberpunk"
    press(app, "escape")
    assert app.player.preview_theme is None and app.player.theme_name == "matrix"
    press(app, "t", "down", "down", "enter")
    assert app.player.theme_name == "ocean"


def test_look_picker_saves_and_applies(app: App) -> None:
    press(app, "l")
    assert isinstance(app.top, LookPicker)
    press(app, "s")
    type_text(app, "Mine")
    press(app, "enter", "right", "l")
    picker = app.top
    assert isinstance(picker, LookPicker)
    assert picker.current is not None and picker.current.label == "Mine"
    press(app, "enter")
    assert app.player.key == "matrix"


def test_settings_rebind_a_key(app: App) -> None:
    press(app, "o")
    settings = app.top
    assert isinstance(settings, SettingsScreen)
    rows = settings.selectable()
    settings.cursor.index = next(i for i, r in enumerate(rows) if r.action == "crt")
    press(app, "enter", "y")
    assert app.keymap.action("y") == "crt" and app.keymap.action("v") is None
    press(app, "enter", "escape")  # Esc cancels a capture
    assert app.keymap.action("y") == "crt"
    press(app, "backspace")
    assert app.keymap.keys_for("crt") == []


def test_settings_flashing_needs_confirmation(app: App) -> None:
    press(app, "o")
    settings = app.top
    assert isinstance(settings, SettingsScreen)
    settings.cursor.index = next(
        i for i, r in enumerate(settings.selectable()) if r.label == "Allow flashing"
    )
    press(app, "right")
    assert isinstance(app.top, Confirm) and not app.settings.allow_flashing
    press(app, "y")
    assert app.settings.allow_flashing and "strobe" in app.theme_names()


def test_settings_characters_switches_to_ascii(app: App) -> None:
    press(app, "o")
    settings = app.top
    assert isinstance(settings, SettingsScreen)
    settings.cursor.index = 1
    press(app, "right", "right")
    assert app.settings.characters == "ascii" and app.ascii_only
    assert screen(app).isascii()


def test_help_scrolls_and_closes(app: App) -> None:
    press(app, "?")
    assert isinstance(app.top, HelpScreen)
    press(app, "pagedown", "end", "home")
    assert isinstance(app.top, HelpScreen)
    press(app, "x")
    assert len(app.screens) == 1


OPENERS = {
    "play": [],
    "status": ["i"],
    "browser": ["m"],
    "browser-groups": ["m", "left"],
    "studio": ["n"],
    "themes": ["t"],
    "looks": ["l"],
    "settings": ["o"],
    "help": ["?"],
    "prompt": ["s"],
    "welcome": None,
}
SIZES = [(40, 12), (41, 13), (80, 24), (250, 70)]


@pytest.mark.parametrize("name", OPENERS)
@pytest.mark.parametrize("size", SIZES, ids=lambda s: f"{s[0]}x{s[1]}")
@pytest.mark.parametrize("utf8", [True, False], ids=["unicode", "ascii"])
def test_every_screen_draws_at_every_size(
    make_app: AppFactory, name: str, size: tuple[int, int], utf8: bool
) -> None:
    keys = OPENERS[name]
    app = make_app(*size, utf8=utf8, seen_welcome=keys is not None)
    press(app, *(keys or []))
    text = screen(app)
    if not utf8:
        assert text.isascii(), f"non-ASCII output in {name}"
    app.resize(size[0] + 7, size[1] + 3)  # and survives a resize while open
    screen(app)
