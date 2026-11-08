"""The application: settings, the user's library, the player and the screen stack.

Nothing here touches the terminal (see ``session.py``), so the whole app can
be driven key by key in tests.
"""

from __future__ import annotations

import dataclasses
import random
from pathlib import Path
from typing import Any

from staticfx import themes
from staticfx.app.keymap import Keymap
from staticfx.app.player import Player
from staticfx.core.frame import Frame
from staticfx.effects.engine import describe
from staticfx.effects.registry import BUILTIN, USER, USER_CATEGORY, Registry
from staticfx.effects.spec import EffectSpec, recipe_spec
from staticfx.library import config
from staticfx.library.config import Settings
from staticfx.library.effects import EffectLibrary, UserEffect
from staticfx.library.looks import Look, LookStore
from staticfx.sysinfo import SystemInfo, overlay
from staticfx.ui.play import PlayScreen
from staticfx.ui.screen import Screen
from staticfx.ui.widgets import ASCII, UNICODE, Canvas, Style, fit

DEFAULT_EFFECT = "matrix"
RECENT_LIMIT = 30
MIN_WIDTH, MIN_HEIGHT = 40, 12


class App:
    def __init__(
        self,
        settings: Settings | None = None,
        data_dir: Path | None = None,
        *,
        utf8: bool = True,
        persist_settings: bool = True,
        registry: Registry | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.settings = settings or Settings()
        self.data_dir = data_dir
        # False for one-off commands and --no-save: nothing writes config.json or
        # runs one-time migrations, so those only happen in a real session.
        self.persist_settings = persist_settings and data_dir is not None
        self.utf8 = utf8  # can the terminal show non-ASCII characters at all?
        self.ascii_only, unicode = self._characters()
        self.chrome = ASCII if self.ascii_only else UNICODE
        self.rng = rng or random.Random()
        self.registry = registry or Registry()
        self.library = EffectLibrary(data_dir / "effects") if data_dir else None
        self.looks = LookStore(data_dir / "looks.json" if data_dir else None)
        self.keymap = Keymap()
        self.notes: list[str] = []  # problems found while loading, shown once at startup
        self._session_only: dict[str, Any] = {}  # setting -> value to save instead

        self.player = Player(self.registry, self.rng, unicode=unicode, ascii_only=self.ascii_only)
        self.player.speed = self.settings.speed
        self.player.post.crt = self.settings.crt
        self.player.post.glitch = self.settings.glitch
        self.player.post.recolour = self.settings.recolour

        self.screens: list[Screen] = []
        self.running = True
        self.suspend_requested = False
        self.dirty = False  # settings changed since the last save
        self.toast_text = ""
        self.toast_time = 0.0
        self.auto = False
        self.auto_timer = 0.0
        self.show_status = False
        self.info = SystemInfo()
        self.width, self.height = 80, 24

    def start(self) -> None:
        """Load the user's things and pick the first effect. Call once, before running."""
        self.notes += self.keymap.apply_changes(self.settings.keybinds)
        self.notes += self.looks.load()
        if self.library is not None and self.data_dir is not None:
            if self.persist_settings and not self.settings.imported_plugins:
                self._import_plugins(self.library, self.data_dir / "plugins")
            effects, problems = self.library.load()
            self.notes += [f"skipped {problem}" for problem in problems]
            for effect in effects:
                self.registry.put_user(self.user_spec(effect))

        self.settings.favorites = [k for k in self.settings.favorites if k in self.registry]
        self.settings.recent = [k for k in self.settings.recent if k in self.registry]
        if self.settings.theme == "strobe" and not self.settings.allow_flashing:
            self.settings.theme = themes.DEFAULT
        self.player.set_theme(self.settings.theme)

        try:
            self.play(self.registry.resolve(self.settings.effect), announce=False)
        except KeyError:
            self.notes.append(f"'{self.settings.effect}' no longer exists; playing Matrix Rain")
            self.play(DEFAULT_EFFECT, announce=False)
        self.screens = [PlayScreen(self)]

    def override(self, name: str, value: Any) -> None:
        """Change a setting for this session only, as command-line options do."""
        self._session_only.setdefault(name, getattr(self.settings, name))
        setattr(self.settings, name, value)

    def keep(self, name: str) -> None:
        """Make a session-only setting permanent (the user changed it in Settings)."""
        self._session_only.pop(name, None)

    def _import_plugins(self, library: EffectLibrary, folder: Path) -> None:
        """One-time copy of 1.x plugin files into My Effects."""
        self.settings.imported_plugins = True
        self.dirty = True
        if not folder.is_dir():
            return
        count, problems = library.import_legacy_plugins(folder)
        self.notes += problems
        if count:
            self.notes.append(f"Copied {count} effect(s) from the old plugins folder to My Effects")
        self.save_settings()  # record it now, so a crash can't make it copy them twice

    def _characters(self) -> tuple[bool, bool]:
        """(ascii_only, katakana) from the setting and what the terminal supports."""
        ascii_only = self.settings.characters == "ascii" or not self.utf8
        return ascii_only, self.settings.characters == "katakana" and not ascii_only

    def apply_characters(self) -> None:
        """Rebuild what's on screen after the Characters setting changed."""
        self.ascii_only, unicode = self._characters()
        self.chrome = ASCII if self.ascii_only else UNICODE
        self.player.ascii_only, self.player.unicode = self.ascii_only, unicode
        self.player.reload()

    def user_spec(self, effect: UserEffect) -> EffectSpec:
        description = effect.description or describe(effect.recipe)
        return recipe_spec(effect.key, effect.name, description, USER_CATEGORY, USER, effect.recipe)

    @property
    def top(self) -> Screen:
        return self.screens[-1]

    def push(self, screen: Screen) -> None:
        self.screens.append(screen)

    def pop(self, screen: Screen | None = None) -> None:
        """Remove ``screen`` (default: the top one). The play screen can't be removed."""
        screen = screen or self.top
        if screen in self.screens[1:]:
            self.screens.remove(screen)
            screen.on_close()

    def handle_key(self, key: str) -> None:
        if key == "ctrl-z":
            self.suspend_requested = True
        elif self.too_small and key in ("q", "ctrl-c"):
            self.running = False
        else:
            self.top.handle(key)

    @property
    def too_small(self) -> bool:
        return self.width < MIN_WIDTH or self.height < MIN_HEIGHT

    def play(self, key: str, announce: bool = True) -> None:
        self.player.play(key)
        self.settings.effect = key
        recent = self.settings.recent
        if key in recent:
            recent.remove(key)
        recent.insert(0, key)
        del recent[RECENT_LIMIT:]
        self.dirty = True
        self.auto_timer = self.settings.auto_seconds
        if announce:
            self.toast(self.registry[key].label)

    def step(self, delta: int) -> None:
        keys = self.registry.keys()
        index = keys.index(self.player.key) if self.player.key in keys else 0
        self.play(keys[(index + delta) % len(keys)])

    def play_random(self) -> None:
        choices = [k for k in self.auto_pool() if k != self.player.key and k in self.registry]
        if choices:
            self.play(self.rng.choice(choices))
        else:
            self.step(1)

    def play_previous(self) -> None:
        if len(self.settings.recent) < 2:
            self.toast("Nothing to go back to yet")
        else:
            self.play(self.settings.recent[1])

    def auto_pool(self) -> list[str]:
        """What auto-cycle and random pick from: favourites if you have a few,
        otherwise the built-ins plus the Gallery of the best generated effects."""
        if len(self.settings.favorites) >= 2:
            return list(self.settings.favorites)
        builtins = [s.key for s in self.registry.specs() if s.kind == BUILTIN]
        return builtins + list(self.registry.gallery)

    def toggle_auto(self) -> None:
        self.auto = not self.auto
        self.auto_timer = self.settings.auto_seconds
        source = "favourites" if len(self.settings.favorites) >= 2 else "built-ins and Gallery"
        state = f"every {self.settings.auto_seconds:g}s from {source}" if self.auto else "off"
        self.toast(f"Auto-cycle {state}")

    def toggle_info(self) -> None:
        self.info.toggle()
        if self.info.visible and self.info.loading:
            self.toast("Loading system info...")

    def is_favorite(self, key: str) -> bool:
        return key in self.settings.favorites

    def toggle_favorite(self, key: str) -> bool:
        """Returns True if ``key`` is now a favourite."""
        favorites = self.settings.favorites
        added = key not in favorites
        if added:
            favorites.append(key)
        else:
            favorites.remove(key)
        self.dirty = True
        return added

    def set_theme(self, name: str) -> None:
        self.player.set_theme(name)
        self.settings.theme = self.player.theme_name
        self.dirty = True

    def theme_names(self) -> list[str]:
        return themes.names(self.settings.allow_flashing)

    def current_look(self, name: str) -> Look:
        post = self.player.post
        return Look(
            name=name,
            effect=self.player.key,
            theme=self.player.theme_name,
            speed=round(self.player.speed, 2),
            crt=post.crt,
            glitch=post.glitch,
            recolour=post.recolour,
        )

    def apply_look(self, look: Look) -> None:
        if look.effect not in self.registry:
            self.toast(f"'{look.name}' uses an effect that no longer exists")
            return
        if look.theme == "strobe" and not self.settings.allow_flashing:
            settings = self.keymap.label("settings", self.ascii_only)
            self.toast(f"That look uses Strobe; allow flashing in Settings ({settings}) first")
            return
        self.set_theme(look.theme)
        self.player.speed = look.speed
        post = self.player.post
        post.crt, post.glitch, post.recolour = look.crt, look.glitch, look.recolour
        self.play(look.effect, announce=False)
        self.toast(f"Look: {look.name}")

    def save_effect(self, effect: UserEffect) -> bool:
        if self.library is None:
            self.toast("Can't save: StaticFX is running without a data folder")
            return False
        try:
            self.library.save(effect)
        except OSError as exc:
            self.toast(f"Couldn't save: {exc.strerror or exc}")
            return False
        self.registry.put_user(self.user_spec(effect))
        return True

    def delete_effect(self, key: str) -> None:
        if self.library is not None:
            self.library.delete(key.removeprefix("my_"))
        self.registry.remove_user(key)
        for keys in (self.settings.favorites, self.settings.recent):
            if key in keys:
                keys.remove(key)
        self.dirty = True
        if self.player.key == key:
            self.play(DEFAULT_EFFECT, announce=False)

    def toast(self, text: str, seconds: float = 2.0) -> None:
        self.toast_text, self.toast_time = text, seconds

    def resize(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        self.player.resize(width, height)

    def update(self, dt: float) -> None:
        self.player.update(dt)
        for screen in self.screens:
            screen.update(dt)
        self.toast_time = max(0.0, self.toast_time - dt)
        if self.info.visible and self.info.error:
            self.info.visible = False
            self.toast(f"No system info: {self.info.error}", 5.0)
        if self.auto and len(self.screens) == 1:
            self.auto_timer -= dt
            if self.auto_timer <= 0:
                self.play_random()

    def draw(self, frame: Frame) -> None:
        theme = self.player.draw(frame)
        canvas = Canvas(frame, self.chrome, Style.from_theme(theme))
        if self.too_small:
            self._draw_too_small(canvas)
            return
        if self.info.visible and self.info.text:
            overlay(frame, theme, self.info.text)
        for screen in self.screens:
            screen.draw(canvas)
        if self.toast_time > 0 and self.toast_text:
            text = f" {fit(self.toast_text, frame.width - 4, self.chrome.ellipsis)} "
            canvas.text(frame.width - len(text) - 1, frame.height - 1, text, canvas.style.accent)

    def _draw_too_small(self, canvas: Canvas) -> None:
        lines = ["Terminal too small", f"need {MIN_WIDTH}x{MIN_HEIGHT}", "(q quits)"]
        top = max(0, canvas.height // 2 - 1)
        for i, line in enumerate(lines):
            line = fit(line, canvas.width, "")
            canvas.text(max(0, (canvas.width - len(line)) // 2), top + i, line, canvas.style.title)

    def save_settings(self) -> None:
        """Write ``config.json`` if anything changed. Failures are reported, not raised."""
        if not self.dirty:
            return
        self.dirty = False
        settings = self.settings
        post = self.player.post
        settings.speed = round(self.player.speed, 2)
        settings.crt, settings.glitch, settings.recolour = post.crt, post.glitch, post.recolour
        settings.keybinds = self.keymap.changes()
        if self.persist_settings and self.data_dir is not None:
            try:
                saved = dataclasses.replace(settings, **self._session_only)
                config.save(saved, self.data_dir / "config.json")
            except OSError as exc:
                self.toast(f"Couldn't save settings: {exc.strerror or exc}")
