"""The main view: the effect, full screen, driven by the key map."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from staticfx.app.keymap import key_label
from staticfx.ui.browser import Browser
from staticfx.ui.dialogs import ask_look_name
from staticfx.ui.help import HelpScreen
from staticfx.ui.pickers import LookPicker, ThemePicker
from staticfx.ui.screen import Screen
from staticfx.ui.settings import SettingsScreen
from staticfx.ui.studio import open_studio
from staticfx.ui.widgets import Canvas, fit

if TYPE_CHECKING:
    from staticfx.app.app import App

HINT_SECONDS = 6.0
QUIT_WINDOW = 2.0  # seconds within which a second Esc quits


class PlayScreen(Screen):
    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.hint_time = HINT_SECONDS
        self.quit_armed = 0.0
        self.actions: dict[str, Callable[[], None]] = {
            "next": lambda: app.step(1),
            "previous": lambda: app.step(-1),
            "random": app.play_random,
            "back": app.play_previous,
            "auto": app.toggle_auto,
            "browse": self.open_browser,
            "themes": self.open_themes,
            "looks": self.open_looks,
            "settings": self.open_settings,
            "help": self.open_help,
            "new_effect": lambda: self.open_studio(None),
            "edit_effect": lambda: self.open_studio(app.player.key),
            "favorite": self.favorite,
            "save_look": self.save_look,
            "next_theme": self.next_theme,
            "crt": lambda: self.toggle_filter("crt", "CRT scanlines"),
            "glitch": lambda: self.toggle_filter("glitch", "Glitch"),
            "recolour": lambda: self.toggle_filter("recolour", "Rainbow recolour"),
            "info": app.toggle_info,
            "pause": self.pause,
            "restart": self.restart,
            "faster": lambda: self.change_speed(app.player.faster),
            "slower": lambda: self.change_speed(app.player.slower),
            "status": self.toggle_status,
            "quit": self.quit,
        }

    def handle(self, key: str) -> None:
        app = self.app
        self.hint_time = 0.0
        if not app.settings.seen_welcome:
            app.settings.seen_welcome = True  # any key dismisses the welcome card
            app.dirty = True
            return
        if key == "ctrl-c":
            self.quit()
        elif key == "escape":
            if self.quit_armed > 0:
                self.quit()
            else:
                self.quit_armed = QUIT_WINDOW
                app.toast(f"Press Esc again to quit ({app.keymap.label('quit')} quits at once)")
        else:
            action = app.keymap.action(key)
            if action is not None:
                self.actions[action]()

    def update(self, dt: float) -> None:
        self.hint_time = max(0.0, self.hint_time - dt)
        self.quit_armed = max(0.0, self.quit_armed - dt)

    def quit(self) -> None:
        self.app.running = False

    def open_browser(self) -> None:
        self.app.push(Browser(self.app))

    def open_themes(self) -> None:
        self.app.push(ThemePicker(self.app))

    def open_looks(self) -> None:
        self.app.push(LookPicker(self.app))

    def open_settings(self) -> None:
        self.app.push(SettingsScreen(self.app))

    def open_help(self) -> None:
        self.app.push(HelpScreen(self.app))

    def open_studio(self, key: str | None) -> None:
        open_studio(self.app, key)

    def favorite(self) -> None:
        app = self.app
        key = app.player.key
        added = app.toggle_favorite(key)
        label = app.registry[key].label
        app.toast(f"Added {label} to favourites" if added else f"Removed {label} from favourites")

    def save_look(self) -> None:
        ask_look_name(self.app)

    def next_theme(self) -> None:
        app = self.app
        names = app.theme_names()
        current = app.player.theme_name
        index = names.index(current) if current in names else -1
        app.set_theme(names[(index + 1) % len(names)])
        app.toast(f"Theme: {app.player.theme().label}")

    def toggle_filter(self, name: str, label: str) -> None:
        post = self.app.player.post
        setattr(post, name, not getattr(post, name))
        self.app.dirty = True
        self.app.toast(f"{label} {'on' if getattr(post, name) else 'off'}")

    def restart(self) -> None:
        self.app.player.restart()
        self.app.toast("Restarted")

    def pause(self) -> None:
        player = self.app.player
        player.paused = not player.paused
        self.app.toast("Paused" if player.paused else "Playing")

    def change_speed(self, change: Callable[[], None]) -> None:
        change()
        self.app.dirty = True
        self.app.toast(f"Speed ×{self.app.player.speed:.2f}")

    def toggle_status(self) -> None:
        self.app.show_status = not self.app.show_status

    def draw(self, canvas: Canvas) -> None:
        if len(self.app.screens) > 1 and self.app.screens[-1] is not self:
            return
        if not self.app.settings.seen_welcome:
            self.draw_welcome(canvas)
        elif self.app.show_status:
            self.draw_status(canvas)
        elif self.hint_time > 0:
            self.draw_hint(canvas)

    def _key(self, action: str) -> str:
        return self.app.keymap.label(action, self.app.ascii_only)

    def draw_status(self, canvas: Canvas) -> None:
        app, c, s = self.app, canvas.chrome, canvas.style
        spec = app.registry[app.player.key]
        star = f"{c.star} " if app.is_favorite(spec.key) else ""
        flags = [*app.player.post.active()]
        if app.auto:
            flags.append("auto")
        if app.player.paused:
            flags.append("paused")
        parts = [spec.category, app.player.theme().label, f"×{app.player.speed:.1f}", *flags]
        left = f" {star}{spec.label}  {f' {c.dot} '.join(parts)}"
        right = f"{self._key('help')} help "
        y = canvas.height - 1
        canvas.frame.fill(0, y, canvas.width, 1)
        canvas.text(0, y, fit(left, canvas.width - len(right) - 1, c.ellipsis), s.text)
        canvas.text(canvas.width - len(right), y, right, s.dim)

    def draw_hint(self, canvas: Canvas) -> None:
        dot = f" {canvas.chrome.dot} "
        browse = (
            f"{key_label('left', self.app.ascii_only)}{key_label('right', self.app.ascii_only)}"
        )
        hint = dot.join(
            [
                f"{browse} next",
                f"{self._key('browse')} browse",
                f"{self._key('themes')} themes",
                f"{self._key('new_effect')} create",
                f"{self._key('info')} sysinfo",
                f"{self._key('help')} help",
                f"{self._key('quit')} quit",
            ]
        )
        hint = fit(hint, canvas.width - 2, canvas.chrome.ellipsis)
        canvas.text((canvas.width - len(hint)) // 2, canvas.height - 1, hint, canvas.style.dim)

    def draw_welcome(self, canvas: Canvas) -> None:
        app = self.app
        count = f"{len(app.registry):,}"
        arrows = f"{key_label('left', app.ascii_only)} {key_label('right', app.ascii_only)}"
        rows = [
            (arrows, "previous / next effect"),
            (self._key("browse"), f"browse and search all {count} effects"),
            (self._key("themes"), "change the colour theme"),
            (self._key("looks"), "ready-made looks"),
            (self._key("new_effect"), "make your own effect in the Studio"),
            (self._key("info"), "your system info over the effect"),
            (self._key("status"), "show what's playing"),
            (self._key("help"), "every key"),
        ]
        room = max(1, canvas.height - 6)
        if len(rows) > room:  # small terminal: drop rows, but always say where every key is
            rows = rows[: room - 1] + rows[-1:]
        width = min(canvas.width - 4, 52)
        height = len(rows) + 6
        x, y = (canvas.width - width) // 2, max(0, (canvas.height - height) // 2)
        canvas.box(x, y, width, height, "Welcome to StaticFX")
        s = canvas.style
        canvas.text(x + 3, y + 2, "Animated effects for your terminal.", s.text, width - 6)
        for i, (keys, what) in enumerate(rows):
            canvas.text(x + 3, y + 3 + i, keys, s.selected, 9)
            canvas.text(x + 12, y + 3 + i, what, s.text, width - 15)
        canvas.text(x + 3, y + height - 2, "Press any key to start", s.accent, width - 6)
