"""The effect browser: groups on the left, effects on the right, live preview behind."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from staticfx.effects.builtin import CATEGORIES
from staticfx.effects.registry import GENERATED_CATEGORY, USER_CATEGORY
from staticfx.effects.spec import USER, EffectSpec
from staticfx.ui.dialogs import Confirm
from staticfx.ui.screen import Screen
from staticfx.ui.studio import open_studio
from staticfx.ui.widgets import Canvas, Cursor, fit

if TYPE_CHECKING:
    from staticfx.app.app import App

GROUP_WIDTH = 19


@dataclass
class Group:
    name: str
    effects: Callable[[], list[EffectSpec]]
    empty: str = "Nothing here yet"


def rank(spec: EffectSpec, query: str) -> int:
    """Lower is better: exact name, name prefix, name contains, anything else."""
    label = spec.label.lower()
    if query in (label, spec.key):
        return 0
    if label.startswith(query):
        return 1
    return 2 if query in label else 3


class Browser(Screen):
    help = (
        ("↑ ↓  PgUp PgDn", "move"),
        ("← →", "switch between groups and effects"),
        ("Tab", "next group"),
        ("Enter", "play the highlighted effect"),
        ("/", "search the selected group (Enter plays, Esc clears)"),
        ("f", "add to / remove from favourites"),
        ("e", "open in the Studio (generated and your own effects)"),
        ("n", "new effect"),
        ("d  Del", "delete one of your effects"),
        ("Esc  q", "close"),
    )

    def __init__(self, app: App) -> None:
        super().__init__(app)
        registry = app.registry
        specs = registry.specs

        def by_keys(keys: list[str] | tuple[str, ...]) -> list[EffectSpec]:
            return [registry[k] for k in keys if k in registry]

        def by_category(name: str) -> Callable[[], list[EffectSpec]]:
            return lambda: [s for s in specs() if s.category == name]

        new_key = app.keymap.label("new_effect", app.ascii_only)
        fav_key = app.keymap.label("favorite", app.ascii_only)
        self.groups = [
            Group("All", specs),
            Group(
                "Favourites",
                lambda: by_keys(app.settings.favorites),
                f"None yet: press {fav_key} on an effect here or while it plays",
            ),
            Group("Recent", lambda: by_keys(app.settings.recent), "Nothing played yet"),
            Group(
                USER_CATEGORY, by_category(USER_CATEGORY), f"None yet: press {new_key} to make one"
            ),
            Group("Gallery", lambda: by_keys(registry.gallery)),
            *(Group(name, by_category(name)) for name in CATEGORIES),
            Group(GENERATED_CATEGORY, by_category(GENERATED_CATEGORY)),
        ]
        self.search_text = {s.key: s.search_text() for s in specs()}
        self.group = Cursor()
        self.cursor = Cursor()
        self.focus = "list"  # "list", "groups" or "search"
        self.query = ""
        self.items: list[EffectSpec] = []
        self.counts: list[int] = []
        self.rows = 10
        self.refresh(keep=app.player.key)

    @property
    def current(self) -> EffectSpec | None:
        return self.items[self.cursor.index] if self.items else None

    def refresh(self, keep: str | None = None) -> None:
        """Recompute the visible list, keeping the cursor on ``keep`` if it's still there."""
        if keep is None and self.current is not None:
            keep = self.current.key
        items = self.groups[self.group.index].effects()
        tokens = self.query.lower().split()
        if tokens:
            items = [s for s in items if all(t in self.search_text.get(s.key, "") for t in tokens)]
            phrase = " ".join(tokens)
            items.sort(key=lambda s: rank(s, phrase))
        self.items = items
        self.counts = [len(g.effects()) for g in self.groups]
        keys = [s.key for s in items]
        self.cursor.index = keys.index(keep) if keep in keys else 0
        self.preview()

    def preview(self) -> None:
        self.app.player.preview(self.current.key if self.current else None)

    def on_close(self) -> None:
        self.app.player.preview(None)

    def handle(self, key: str) -> None:
        if self.focus == "search":
            self.handle_search(key)
            return
        app, current = self.app, self.current
        if key in ("escape", "ctrl-c", "q"):
            self.close()
        elif key == "/":
            self.focus = "search"
        elif key == "left":
            self.focus = "groups"
        elif key == "right":
            self.focus = "list"
        elif key in ("tab", "shift-tab"):
            self.select_group(self.group.index + (1 if key == "tab" else -1))
        elif self.focus == "groups" and self.group.handle(key, len(self.groups), 5):
            self.select_group(self.group.index)
        elif self.cursor.handle(key, len(self.items), self.rows):
            self.preview()
        elif key == "enter":
            if self.focus == "groups":
                self.focus = "list"
            else:
                self.play()
        elif key == "n":
            self.close()
            open_studio(app, None)
        elif current is None:
            return
        elif key == "f":
            added = app.toggle_favorite(current.key)
            app.toast(f"{'Added to' if added else 'Removed from'} favourites: {current.label}")
            self.refresh()
        elif key == "e":
            self.edit(current)
        elif key in ("d", "delete"):
            self.delete(current)

    def handle_search(self, key: str) -> None:
        """Typing goes into the search; arrows still move through the results."""
        if key in ("escape", "ctrl-c"):
            self.query = ""
            self.focus = "list"
            self.refresh()
        elif key == "enter":
            self.play()
        elif key in ("tab", "shift-tab"):
            self.focus = "list"
        elif self.cursor.handle(key, len(self.items), self.rows):
            self.preview()
        elif key == "backspace":
            if not self.query:
                self.focus = "list"
            self.query = self.query[:-1]
            self.refresh()
        elif key == "space" or (len(key) == 1 and key.isprintable()):
            self.query += " " if key == "space" else key
            self.refresh()

    def play(self) -> None:
        if self.current is not None:
            self.close()
            self.app.play(self.current.key)

    def select_group(self, index: int) -> None:
        self.group.index = index % len(self.groups)
        self.cursor.first = 0
        self.refresh()

    def edit(self, spec: EffectSpec) -> None:
        if not spec.editable:
            self.app.toast("Hand-written built-ins can't be edited; try a Generated effect")
            return
        self.close()
        open_studio(self.app, spec.key)

    def delete(self, spec: EffectSpec) -> None:
        if spec.kind != USER:
            self.app.toast("Only your own effects can be deleted")
            return

        def confirmed() -> None:
            self.app.delete_effect(spec.key)
            self.app.toast(f"Deleted {spec.label}")
            self.refresh()

        lines = [f"Delete '{spec.label}'?", "Its .sfx file will be removed."]
        self.app.push(Confirm(self.app, "Delete effect", lines, confirmed))

    def draw(self, canvas: Canvas) -> None:
        app, c, s = self.app, canvas.chrome, canvas.style
        w = canvas.width - 2 if canvas.width < 90 else min(84, max(64, canvas.width * 3 // 5))
        h = canvas.height - 2
        x, y = 1, 1
        group = self.groups[self.group.index]
        canvas.box(
            x, y, w, h, "Effects", f"{len(self.items):,} of {self.counts[self.group.index]:,}"
        )

        if self.focus == "search":
            canvas.text(x + 2, y + 1, f"Search: {self.query}_", s.selected, w - 4)
        elif self.query:
            canvas.text(x + 2, y + 1, f"Search: {self.query}   (/ to change)", s.text, w - 4)
        else:
            canvas.text(x + 2, y + 1, "Press / to search", s.dim, w - 4)
        split = GROUP_WIDTH + 1
        canvas.rule(x, y + 2, w, split, c.top_tee)
        body_top, body_bottom = y + 3, y + h - 4
        self.rows = max(1, body_bottom - body_top)
        canvas.column(x + split, body_top, body_bottom)
        canvas.rule(x, body_bottom, w, split, c.bottom_tee)

        # groups
        for row, i in enumerate(self.group.window(self.rows, len(self.groups)), body_top):
            g = self.groups[i]
            marker = c.cursor if i == self.group.index else " "
            focused = i == self.group.index and self.focus == "groups"
            colour = s.selected if focused else s.text if i == self.group.index else s.dim
            label = f"{marker} {fit(g.name, GROUP_WIDTH - 7, c.ellipsis)}"
            canvas.text(x + 1, row, label, colour, GROUP_WIDTH - 4)
            canvas.text(x + split - 5, row, f"{self.counts[i]:>4}", s.dim)

        # effects
        lx, lw = x + split + 2, w - split - 4
        if not self.items:
            canvas.text(lx, body_top, "No matches" if self.query else group.empty, s.dim, lw)
        for row, index in enumerate(self.cursor.window(self.rows, len(self.items))):
            spec = self.items[index]
            selected = index == self.cursor.index
            star = c.star if app.is_favorite(spec.key) else " "
            marker = c.cursor if selected else " "
            tag = "" if group.name == spec.category else spec.category
            name = fit(spec.label, lw - len(tag) - 5, c.ellipsis)
            colour = s.selected if selected and self.focus == "list" else s.text
            canvas.text(lx, body_top + row, f"{marker}{star} {name}", colour, lw - len(tag))
            canvas.text(lx + lw - len(tag), body_top + row, tag, s.dim)
        canvas.scrollbar(x + w - 2, body_top, self.rows, self.cursor.first, len(self.items))

        # description and keys
        current = self.current
        if current is not None:
            canvas.text(x + 2, body_bottom + 1, current.description, s.text, w - 4)
        if self.focus == "search":
            keys = ["type to search", "Enter play", "↑↓ move", "Esc clear"]
        else:
            keys = ["Enter play", "/ search", "f favourite"]
            if current is not None and current.editable:
                keys.append("e edit")
            if current is not None and current.kind == USER:
                keys.append("d delete")
            keys += ["n new", "Esc close"]
        canvas.text(x + 2, body_bottom + 2, f"  {c.dot}  ".join(keys), s.dim, w - 4)
