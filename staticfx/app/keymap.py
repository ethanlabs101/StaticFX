"""Key bindings for the main view.

There is one table of actions (shown in this order in the help screen) and
one table of default keys. Only the user's changes are saved, so a future
release can change a default without old config files pinning the old one.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# action -> (group, description)
ACTIONS: dict[str, tuple[str, str]] = {
    "next": ("Browse", "Next effect"),
    "previous": ("Browse", "Previous effect"),
    "random": ("Browse", "Random effect"),
    "back": ("Browse", "Back to the last effect"),
    "auto": ("Browse", "Auto-cycle through effects"),
    "browse": ("Menus", "Browse and search effects"),
    "themes": ("Menus", "Choose a theme"),
    "looks": ("Menus", "Saved looks"),
    "settings": ("Menus", "Settings and key bindings"),
    "help": ("Menus", "All keys"),
    "new_effect": ("Create", "New effect in the Studio"),
    "edit_effect": ("Create", "Edit this effect in the Studio"),
    "favorite": ("Create", "Add to / remove from favourites"),
    "save_look": ("Create", "Save effect + theme + filters as a look"),
    "next_theme": ("Look", "Next theme"),
    "crt": ("Look", "CRT scanlines filter"),
    "glitch": ("Look", "Glitch filter"),
    "recolour": ("Look", "Rainbow recolour filter"),
    "pause": ("Playback", "Pause"),
    "restart": ("Playback", "Restart the effect"),
    "faster": ("Playback", "Faster"),
    "slower": ("Playback", "Slower"),
    "status": ("Playback", "Show or hide the status bar"),
    "quit": ("Playback", "Quit"),
}

DEFAULT_KEYS: dict[str, str] = {
    "right": "next",
    "space": "next",
    "left": "previous",
    "x": "random",
    "b": "back",
    "a": "auto",
    "m": "browse",
    "enter": "browse",
    "t": "themes",
    "l": "looks",
    "o": "settings",
    "?": "help",
    "h": "help",
    "n": "new_effect",
    "e": "edit_effect",
    "f": "favorite",
    "s": "save_look",
    "c": "next_theme",
    "v": "crt",
    "g": "glitch",
    "w": "recolour",
    "p": "pause",
    "z": "restart",
    "up": "faster",
    "+": "faster",
    "=": "faster",
    "down": "slower",
    "-": "slower",
    "i": "status",
    "q": "quit",
}

# Keys that always mean the same thing and can't be rebound: Esc and Ctrl-C
# back out of anything, Ctrl-Z suspends.
RESERVED = frozenset({"escape", "ctrl-c", "ctrl-z"})
UNBOUND = "none"

KEY_LABELS = {
    "left": "←",
    "right": "→",
    "up": "↑",
    "down": "↓",
    "space": "Space",
    "enter": "Enter",
    "tab": "Tab",
    "escape": "Esc",
    "backspace": "Backspace",
    "delete": "Del",
    "pageup": "PgUp",
    "pagedown": "PgDn",
    "home": "Home",
    "end": "End",
}
ASCII_ARROWS = {"left": "Left", "right": "Right", "up": "Up", "down": "Down"}


def key_label(key: str, ascii_only: bool = False) -> str:
    """How a key is written for people: ``→``, ``Ctrl-E``, ``f``.

    Letters are shown in lower case so nobody reaches for Shift.
    """
    if ascii_only and key in ASCII_ARROWS:
        return ASCII_ARROWS[key]
    if key in KEY_LABELS:
        return KEY_LABELS[key]
    if key.startswith("ctrl-"):
        return "Ctrl-" + key[5:].upper()
    return key


@dataclass
class Keymap:
    bindings: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_KEYS))

    def action(self, key: str) -> str | None:
        """The action for ``key``. Letters work with or without Shift (or Caps Lock)
        unless the upper-case letter has a binding of its own."""
        action = self.bindings.get(key)
        if action is None and len(key) == 1 and key.isupper():
            action = self.bindings.get(key.lower())
        return None if action in (None, UNBOUND) else action

    def keys_for(self, action: str) -> list[str]:
        """Keys bound to ``action``, defaults first so labels stay familiar."""
        order = list(DEFAULT_KEYS)
        keys = [k for k, a in self.bindings.items() if a == action]
        return sorted(keys, key=lambda k: order.index(k) if k in order else len(order))

    def label(self, action: str, ascii_only: bool = False) -> str:
        """The first key for ``action``, for hints like "press m to browse"."""
        keys = self.keys_for(action)
        return key_label(keys[0], ascii_only) if keys else "(unbound)"

    def bind(self, key: str, action: str) -> str | None:
        """Bind ``key`` to ``action``. Returns the action that lost the key, if any."""
        if key in RESERVED:
            raise ValueError(f"{key_label(key)} is reserved")
        if action != UNBOUND and action not in ACTIONS:
            raise ValueError(f"unknown action '{action}'")
        previous = self.action(key)
        self.bindings[key] = action
        return previous if previous not in (None, action) else None

    def unbind(self, action: str) -> None:
        for key in self.keys_for(action):
            self.bindings[key] = UNBOUND

    def reset(self) -> None:
        self.bindings = dict(DEFAULT_KEYS)

    def changes(self) -> dict[str, str]:
        """What differs from the defaults: all that gets saved."""
        return {k: a for k, a in self.bindings.items() if DEFAULT_KEYS.get(k, UNBOUND) != a}

    def apply_changes(self, changes: dict[str, str]) -> list[str]:
        """Apply saved changes; returns a warning for each one that was invalid."""
        warnings = []
        for key, action in changes.items():
            try:
                self.bind(key, action)
            except ValueError as exc:
                warnings.append(f"key binding '{key}': {exc}")
        return warnings
