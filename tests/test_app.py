"""The app without a terminal: startup, playing, favourites, looks, keys, saving."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from conftest import AppFactory, press, screen

from staticfx.app.app import App
from staticfx.app.keymap import ACTIONS, DEFAULT_KEYS, RESERVED, Keymap
from staticfx.library import config
from staticfx.library.looks import Look
from staticfx.ui.help import help_lines
from staticfx.ui.play import PlayScreen

FIXTURES = Path(__file__).parent / "fixtures"


def test_starts_on_the_saved_effect(make_app: AppFactory) -> None:
    app = make_app(effect="plasma", theme="ocean")
    assert app.player.key == "plasma" and app.player.theme_name == "ocean"
    assert app.notes == []


def test_a_missing_effect_falls_back_instead_of_refusing_to_start(make_app: AppFactory) -> None:
    app = make_app(effect="my_deleted_effect")
    assert app.player.key == "matrix"
    assert "no longer exists" in app.notes[0]


def test_strobe_needs_permission(make_app: AppFactory) -> None:
    assert make_app(theme="strobe").player.theme_name == "matrix"
    assert make_app(theme="strobe", allow_flashing=True).player.theme_name == "strobe"
    assert "strobe" not in make_app().theme_names()


def test_1x_data_folder_upgrades_cleanly(tmp_path: Path) -> None:
    shutil.copy(FIXTURES / "v1_config.json", tmp_path / "config.json")
    shutil.copy(FIXTURES / "v1_looks.json", tmp_path / "looks.json")
    (tmp_path / "effects").mkdir()
    shutil.copy(FIXTURES / "v1_studio_effect.sfx", tmp_path / "effects" / "old_studio_effect.sfx")
    (tmp_path / "plugins").mkdir()
    shutil.copy(FIXTURES / "v1_plugin.sfx", tmp_path / "plugins" / "wavy.sfx")

    settings, warnings = config.load(tmp_path / "config.json")
    app = App(settings, tmp_path)
    app.start()
    assert warnings == []
    assert app.player.key == "proc_042"
    assert app.settings.favorites == ["matrix", "plasma"]  # gen_007 no longer exists
    assert "my_old_studio_effect" in app.registry and "my_wavy_plugin" in app.registry
    assert app.keymap.action("y") == "crt"
    assert [look.name for look in app.looks.looks] == ["My Cyber"]
    saved = json.loads((tmp_path / "config.json").read_text())
    assert saved["imported_plugins"] is True  # recorded straight away, so it never repeats

    App(config.load(tmp_path / "config.json")[0], tmp_path).start()
    assert len(list((tmp_path / "effects").glob("*.sfx"))) == 2  # not imported twice


def test_next_previous_random_and_back(app: App) -> None:
    keys = app.registry.keys()
    press(app, "right")
    assert app.player.key == keys[1]
    press(app, "left", "left")
    assert app.player.key == keys[-1]
    press(app, "b")
    assert app.player.key == keys[0]
    press(app, "x")
    assert app.player.key in app.auto_pool()


def test_auto_cycle_changes_effect_and_pauses_in_menus(app: App) -> None:
    app.settings.auto_seconds = 1.0
    press(app, "a")
    start = app.player.key
    press(app, "m")
    for _ in range(60):
        app.update(1 / 30)
    assert app.player.key == start  # a menu is open
    press(app, "escape")
    for _ in range(40):
        app.update(1 / 30)
    assert app.player.key != start


def test_auto_pool_prefers_favourites(app: App) -> None:
    assert "proc_940" in app.auto_pool() and "matrix" in app.auto_pool()
    press(app, "f", "right", "f")
    assert sorted(app.auto_pool()) == sorted(app.registry.keys()[:2])


def test_filters_speed_pause_and_theme(app: App) -> None:
    press(app, "v", "g", "w", "up", "up", "p", "c")
    post = app.player.post
    assert post.crt and post.glitch and post.recolour
    assert app.player.speed > 1.4 and app.player.paused
    assert app.player.theme_name == "cyberpunk"
    press(app, "down", "down", "down", "p")
    assert app.player.speed < 1.0 and not app.player.paused


def test_letters_work_with_shift_or_caps_lock(app: App) -> None:
    press(app, "M")
    assert len(app.screens) == 2
    press(app, "escape", "V")
    assert app.player.post.crt


def test_quitting(app: App) -> None:
    press(app, "escape")
    assert app.running  # first Esc only warns
    press(app, "escape")
    assert not app.running


def test_q_and_ctrl_c_quit_at_once(make_app: AppFactory) -> None:
    for key in ("q", "ctrl-c"):
        app = make_app()
        press(app, key)
        assert not app.running


def test_ctrl_z_asks_the_session_to_suspend(app: App) -> None:
    press(app, "ctrl-z")
    assert app.suspend_requested and app.running


def test_welcome_card_shows_once(make_app: AppFactory) -> None:
    app = make_app(seen_welcome=False)
    assert "Welcome to StaticFX" in screen(app)
    press(app, "right")  # dismisses; doesn't act
    assert app.player.key == "matrix" and app.settings.seen_welcome
    assert "Welcome" not in screen(app)


def test_status_bar(app: App) -> None:
    press(app, "i")
    assert "Matrix Rain" in screen(app).splitlines()[-1]


def test_tiny_terminal_shows_a_message(make_app: AppFactory) -> None:
    app = make_app(width=30, height=8)
    assert "Terminal too small" in screen(app)
    press(app, "q")
    assert not app.running


def test_apply_look(app: App) -> None:
    app.apply_look(Look("x", "fire", "inferno", 2.0, crt=True))
    assert (app.player.key, app.player.theme_name, app.player.speed) == ("fire", "inferno", 2.0)
    assert app.player.post.crt
    app.apply_look(Look("y", "gone", "ocean"))
    assert app.player.key == "fire"  # missing effect: nothing changes
    app.apply_look(Look("z", "plasma", "strobe"))
    assert app.player.theme_name == "inferno"  # strobe not allowed


def test_every_action_has_a_default_key() -> None:
    keymap = Keymap()
    for action in ACTIONS:
        assert keymap.keys_for(action), f"{action} has no default key"
    for key, action in DEFAULT_KEYS.items():
        assert action in ACTIONS and key not in RESERVED


def test_play_screen_handles_every_action(app: App) -> None:
    play = app.screens[0]
    assert isinstance(play, PlayScreen)
    assert set(play.actions) == set(ACTIONS)


def test_rebinding_is_saved_as_changes_only(app: App, tmp_path: Path) -> None:
    lost = app.keymap.bind("v", "glitch")
    assert lost == "crt"
    app.dirty = True
    app.save_settings()
    saved = json.loads((tmp_path / "config.json").read_text())
    assert saved["keybinds"] == {"v": "glitch"}


def test_help_reflects_current_bindings(app: App) -> None:
    app.keymap.bind("y", "crt")
    rows = {text: keys for kind, keys, text in help_lines(app) if kind == "row"}
    assert "y" in rows[ACTIONS["crt"][1]].split()


def test_invalid_saved_bindings_become_notes(make_app: AppFactory) -> None:
    app = make_app(keybinds={"y": "explode", "escape": "crt"})
    assert len(app.notes) == 2
    assert app.keymap.action("escape") is None


def test_settings_are_saved_only_when_changed(app: App, tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    app.dirty = False
    app.save_settings()
    assert not path.exists()
    press(app, "right")
    app.save_settings()
    assert json.loads(path.read_text())["effect"] == app.player.key


def test_no_save_mode_writes_nothing(tmp_path: Path) -> None:
    app = App(None, tmp_path, persist_settings=False)
    app.start()
    press(app, "right", "v")
    app.save_settings()
    assert list(tmp_path.iterdir()) == []


def test_command_line_overrides_are_not_saved(app: App, tmp_path: Path) -> None:
    app.override("fps", 60)
    app.override("characters", "ascii")
    app.apply_characters()
    assert app.ascii_only
    app.dirty = True
    app.save_settings()
    saved = json.loads((tmp_path / "config.json").read_text())
    assert saved["fps"] == 30 and saved["characters"] == "auto"
    app.keep("fps")  # changed in Settings during the session: now it sticks
    app.dirty = True
    app.save_settings()
    assert json.loads((tmp_path / "config.json").read_text())["fps"] == 60


def test_system_info_key_is_easy_to_find(make_app: AppFactory) -> None:
    app = make_app(seen_welcome=False)
    assert "y        your system info" in screen(app)
    app = make_app()
    assert "y sysinfo" in screen(app)
    top = [keys for kind, keys, _ in help_lines(app)[:16] if kind == "row"]
    assert "y" in top, "the help screen should show it without scrolling"
