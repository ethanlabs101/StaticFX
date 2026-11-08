"""The Effect Studio: edit a recipe with a live preview, undo, and save to My Effects.

The panel's rows are generated from the recipe and from each kind's
parameter schema, so a new layer kind shows up here with no Studio changes.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from staticfx.core.color import hsv, hue_of
from staticfx.effects.engine import EngineEffect, Recipe, generate
from staticfx.effects.engine.filters import BLENDS, FILTERS
from staticfx.effects.engine.layers import LAYERS
from staticfx.effects.engine.recipe import (
    CHARSETS,
    MAX_FILTERS,
    MAX_LAYERS,
    MAX_WARPS,
    PALETTES,
    Stage,
)
from staticfx.effects.engine.schema import Kind, Param
from staticfx.effects.engine.warps import WARPS
from staticfx.effects.spec import USER
from staticfx.library.effects import UserEffect
from staticfx.ui.dialogs import Confirm, Prompt
from staticfx.ui.screen import Screen
from staticfx.ui.widgets import Canvas, Cursor, fit

if TYPE_CHECKING:
    from staticfx.app.app import App

OFF = "off"
UNDO_LIMIT = 200
PANEL_WIDTH = 50
FOOTER = "s save  a copy  r random  u undo  Esc close"

# Ranges for the recipe-wide settings (layer, warp and filter params carry their own).
SPEED = Param("speed", "Speed", 1.0, 0.05, 6.0, 0.05)
SPREAD = Param("spread", "Spread", 1.0, 0.1, 3.0, 0.1)
DRIFT = Param("drift", "Drift", 0.0, -1.0, 1.0, 0.05)
HUE = Param("hue", "Hue", 0.0, 0.0, 0.99, 0.03)
TRAIL = Param("trail", "Trail", 0.0, 0.0, 0.98, 0.04)
PULSE = Param("pulse", "Pulse", 0.0, 0.0, 8.0, 0.25)
SPARKLE = Param("sparkle", "Sparkle", 0.0, 0.0, 0.03, 0.002)


@dataclass
class Row:
    label: str
    value: Callable[[], str] = str
    change: Callable[[int], None] | None = None  # called with -1 or +1
    hint: str = ""
    heading: bool = False
    on_enter: Callable[[], None] | None = None


def constant(text: str) -> Callable[[], str]:
    return lambda: text


def cycle(options: list[Any], current: Any, step: int) -> Any:
    index = options.index(current) if current in options else 0
    return options[(index + step) % len(options)]


class Studio(Screen):
    help = (
        ("↑ ↓", "choose a setting"),
        ("← →", "change it"),
        ("PgUp PgDn", "jump between sections"),
        ("Enter", "rename (on the Name row)"),
        ("s", "save to My Effects"),
        ("a", "save as a new copy"),
        ("r", "randomise everything"),
        ("u", "undo"),
        ("t", "try the next theme"),
        ("p", "pause the preview"),
        ("Esc", "close (asks before discarding changes)"),
    )

    def __init__(
        self, app: App, recipe: Recipe, name: str = "", effect_id: str | None = None
    ) -> None:
        super().__init__(app)
        self.recipe = recipe
        self.name = name
        self.effect_id = effect_id  # set once saved: later saves overwrite the same file
        self.saved_key: str | None = None
        self.history: list[dict[str, Any]] = []
        self.cursor = Cursor()  # over editable rows
        self.view = Cursor()  # over every row, for scrolling
        self.rows: list[Row] = []
        self.visible_rows = 10
        self.preview = EngineEffect(app.rng, recipe=recipe)
        self.preview.ascii_only = app.ascii_only
        self.preview.adaptive = app.player.adaptive
        self.preview.resize(app.width, app.height)
        app.player.override = self.preview
        self.was_paused = app.player.paused
        self.clean = self._state()
        self.rebuild()

    def _state(self) -> tuple[str, dict[str, Any]]:
        return self.name, self.recipe.to_dict()

    @property
    def dirty(self) -> bool:
        return self.clean != self._state()

    def _replace(self, recipe: Recipe) -> None:
        self.recipe = recipe
        self.preview.recipe = recipe
        self.rebuild()

    def edit(self, change: Callable[[], None]) -> None:
        """Apply ``change`` to the recipe, remembering the previous state for undo."""
        before = self.recipe.to_dict()
        change()
        if self.recipe.to_dict() != before:
            self.history.append(before)
            del self.history[:-UNDO_LIMIT]
        self.rebuild()

    def undo(self) -> None:
        if self.history:
            self._replace(Recipe.from_dict(self.history.pop()))
        else:
            self.app.toast("Nothing to undo")

    def randomise(self) -> None:
        self.history.append(self.recipe.to_dict())
        self._replace(generate(self.app.rng.randrange(10**6, 10**7))[0])
        self.app.toast("Randomised (U undoes)")

    def number(
        self,
        label: str,
        param: Param,
        get: Callable[[], Any],
        put: Callable[[Any], None],
        hint: str = "",
    ) -> Row:
        def change(step: int) -> None:
            self.edit(lambda: put(param.nudge(get(), step)))

        return Row(label, lambda: param.format(get()), change, hint)

    def param_row(self, params: dict[str, Any], param: Param, hint: str) -> Row:
        def put(value: Any) -> None:
            params[param.name] = value

        return self.number(param.label, param, lambda: params[param.name], put, hint)

    def attr_number(self, label: str, obj: object, attr: str, param: Param, hint: str = "") -> Row:
        return self.number(
            label, param, lambda: getattr(obj, attr), lambda v: setattr(obj, attr, v), hint
        )

    def attr_toggle(self, label: str, obj: object, attr: str, hint: str = "") -> Row:
        def flip(_step: int) -> None:
            self.edit(lambda: setattr(obj, attr, not getattr(obj, attr)))

        return Row(label, lambda: "on" if getattr(obj, attr) else "off", flip, hint)

    def attr_choice(
        self, label: str, obj: object, attr: str, options: list[str], hint: str = ""
    ) -> Row:
        def change(step: int) -> None:
            self.edit(lambda: setattr(obj, attr, cycle(options, getattr(obj, attr), step)))

        return Row(label, lambda: str(getattr(obj, attr)), change, hint)

    def rebuild(self) -> None:
        r = self.recipe
        rows = [
            Row("Effect", heading=True),
            Row(
                "Name",
                lambda: self.name or "(unnamed)",
                hint="Enter to rename",
                on_enter=self.rename,
            ),
            self.attr_number("Speed", r, "speed", SPEED, "how fast everything moves"),
        ]
        rows += self.stage_rows("Layer", r.layers, LAYERS, MAX_LAYERS, required=1)
        rows += self.stage_rows("Warp", r.warps, WARPS, MAX_WARPS)
        rows += self.stage_rows("Filter", r.filters, FILTERS, MAX_FILTERS)
        rows += self.look_rows()
        rows += self.extra_rows()
        self.rows = rows
        self.cursor.clamp(len(self.selectable()))

    def stage_rows(
        self, title: str, stages: list[Stage], kinds: dict[str, Kind], limit: int, required: int = 0
    ) -> list[Row]:
        """Rows for each layer, warp or filter, plus one empty slot to add another."""
        rows = []
        for index in range(min(limit, len(stages) + 1)):
            stage = stages[index] if index < len(stages) else None
            options = list(kinds) if index < required else [OFF, *kinds]

            def change_kind(step: int, index: int = index, options: list[str] = options) -> None:
                current = stages[index].kind if index < len(stages) else OFF
                kind = cycle(options, current, step)

                def apply() -> None:
                    if kind == OFF:
                        del stages[index:]  # later slots would shift up; drop them too
                    elif index < len(stages):
                        stages[index] = Stage(kind, kinds[kind].defaults(), stages[index].blend)
                    else:
                        stages.append(Stage(kind, kinds[kind].defaults()))

                self.edit(apply)

            rows.append(Row(f"{title} {index + 1}", heading=True))
            label = "Pattern" if title == "Layer" else "Kind"
            if stage is None:
                rows.append(
                    Row(label, lambda: OFF, change_kind, f"pick one to add a {title.lower()}")
                )
                continue
            kind = kinds[stage.kind]
            rows.append(Row(label, constant(kind.label), change_kind, kind.summary))
            if title == "Layer" and index > 0:
                rows.append(
                    self.attr_choice(
                        "Blend",
                        stage,
                        "blend",
                        list(BLENDS),
                        "how it combines with the layers above",
                    )
                )
            for param in kind.params:
                rows.append(self.param_row(stage.params, param, f"{kind.label}: {kind.summary}"))
        return rows

    def look_rows(self) -> list[Row]:
        r, pal = self.recipe, self.recipe.palette
        chars = self.attr_choice("Characters", r, "charset", list(CHARSETS), "dark to bright")
        chars.value = lambda: fit(r.charset.lstrip(), 16)
        rows = [
            Row("Look", heading=True),
            chars,
            self.attr_toggle("Glyph rain", r, "glyph_rain", "random glyphs instead of shading"),
            self.attr_toggle("Dither", r, "dither", "smoother gradients"),
            self.attr_choice(
                "Colours", pal, "kind", list(PALETTES), "theme = follow the theme (T)"
            ),
        ]
        if pal.kind == "rainbow":
            rows.append(self.attr_number("Spread", pal, "spread", SPREAD))
            rows.append(self.attr_number("Drift", pal, "drift", DRIFT))
        elif pal.kind == "duo":
            rows.append(
                self.number(
                    "First hue",
                    HUE,
                    lambda: round(hue_of(pal.first), 2),
                    lambda v: setattr(pal, "first", hsv(v)),
                )
            )
            rows.append(
                self.number(
                    "Second hue",
                    HUE,
                    lambda: round(hue_of(pal.second), 2),
                    lambda v: setattr(pal, "second", hsv(v, 0.9)),
                )
            )
        return rows

    def extra_rows(self) -> list[Row]:
        r = self.recipe
        return [
            Row("Extras", heading=True),
            self.attr_number("Trail", r, "trail", TRAIL, "bright cells fade slowly; 0 is off"),
            self.attr_number("Pulse", r, "pulse", PULSE, "breathing brightness; 0 is off"),
            self.attr_number("Sparkle", r, "sparkle", SPARKLE, "random twinkles; 0 is off"),
            self.attr_toggle("Scanlines", r, "scanlines"),
            self.attr_toggle("Glitch", r, "glitch"),
        ]

    def selectable(self) -> list[Row]:
        return [row for row in self.rows if not row.heading]

    @property
    def current(self) -> Row:
        return self.selectable()[self.cursor.index]

    def handle(self, key: str) -> None:
        lower = key.lower() if len(key) == 1 else key
        row = self.current
        if key in ("escape", "ctrl-c"):
            self.request_close()
        elif key in ("pageup", "pagedown"):
            self.jump_section(-1 if key == "pageup" else 1)
        elif self.cursor.handle(key, len(self.selectable()), self.visible_rows):
            pass
        elif key in ("left", "right") and row.change is not None:
            row.change(-1 if key == "left" else 1)
        elif key == "enter" and row.on_enter is not None:
            row.on_enter()
        elif lower == "s":
            self.save()
        elif lower == "a":
            self.save(as_copy=True)
        elif lower == "r":
            self.randomise()
        elif lower == "u":
            self.undo()
        elif lower == "t":
            self.app.set_theme(cycle(self.app.theme_names(), self.app.player.theme_name, 1))
            self.app.toast(f"Theme: {self.app.player.theme().label}")
        elif lower == "p":
            self.app.player.paused = not self.app.player.paused

    def jump_section(self, step: int) -> None:
        """Move to the first row of the next (or previous) section."""
        starts, editable, after_heading = [], 0, False
        for row in self.rows:
            if row.heading:
                after_heading = True
                continue
            if after_heading:
                starts.append(editable)
            after_heading = False
            editable += 1
        here = self.cursor.index
        if step > 0:
            self.cursor.index = next((s for s in starts if s > here), starts[-1])
        else:
            self.cursor.index = next((s for s in reversed(starts) if s < here), 0)

    def rename(self) -> None:
        self.app.push(Prompt(self.app, "Name your effect", self._set_name, self.name))

    def _set_name(self, name: str) -> None:
        self.name = name

    def save(self, as_copy: bool = False) -> None:
        if as_copy or not self.name:
            title = "Save a copy as" if as_copy else "Name your effect"
            self.app.push(Prompt(self.app, title, lambda name: self._write(name, as_copy)))
        else:
            self._write(self.name, as_copy=False)

    def _write(self, name: str, as_copy: bool) -> None:
        app = self.app
        if app.library is None:
            app.toast("Can't save: StaticFX is running without a data folder")
            return
        ident = self.effect_id if self.effect_id and not as_copy else app.library.unique_id(name)
        effect = UserEffect(ident, name, self.recipe.copy())
        if app.save_effect(effect):
            self.name, self.effect_id, self.saved_key = name, ident, effect.key
            self.clean = self._state()
            app.toast(f"Saved '{name}' to My Effects")

    def request_close(self) -> None:
        if not self.dirty:
            self.close()
            return
        lines = ["You have unsaved changes.", "Close the Studio and lose them?"]
        self.app.push(Confirm(self.app, "Discard changes?", lines, self.close))

    def on_close(self) -> None:
        app = self.app
        app.player.override = None
        app.player.paused = self.was_paused
        if self.saved_key:
            app.play(self.saved_key)

    def update(self, dt: float) -> None:
        if (self.preview.width, self.preview.height) != (self.app.width, self.app.height):
            self.preview.resize(self.app.width, self.app.height)

    def draw(self, canvas: Canvas) -> None:
        c, s = canvas.chrome, canvas.style
        w, h = min(canvas.width - 2, PANEL_WIDTH), canvas.height - 2
        x, y = 1, 1
        title = f"Studio: {self.name or 'new effect'}{' *' if self.dirty else ''}"
        canvas.box(x, y, w, h, title)
        self.visible_rows = h - 5
        current = self.current
        self.view.index = self.rows.index(current)
        for line, i in enumerate(self.view.window(self.visible_rows, len(self.rows)), y + 1):
            row = self.rows[i]
            if row.heading:
                canvas.text(x + 2, line, f"{c.h * 2} {row.label} ", s.dim, w - 4)
                continue
            selected = row is current
            value = row.value()
            if selected and row.change is not None:
                value = f"{c.arrow_left} {value} {c.arrow_right}"
            colour = s.selected if selected else s.text
            value_width = min(len(value), w - 22)
            label = f"{c.cursor if selected else ' '} {row.label}"
            canvas.text(x + 2, line, label, colour, w - 6 - value_width)
            canvas.text(
                x + w - 3 - value_width, line, value, colour if selected else s.dim, value_width
            )
        canvas.scrollbar(x + w - 2, y + 1, self.visible_rows, self.view.first, len(self.rows))
        canvas.rule(x, y + h - 4, w)
        canvas.text(x + 2, y + h - 3, current.hint, s.text, w - 4)
        canvas.text(x + 2, y + h - 2, FOOTER, s.dim, w - 4)


def open_studio(app: App, key: str | None) -> None:
    """Open the Studio on a new random effect (``key`` is None) or an existing one.

    Your own effects are edited in place; generated ones are copied, so the
    original stays as it was.
    """
    if key is None:
        recipe, _ = generate(app.rng.randrange(10**6, 10**7))
        app.push(Studio(app, recipe))
        app.toast("New effect: change settings with ← →, S saves", 4.0)
        return
    spec = app.registry[key]
    if spec.recipe is None:
        new = app.keymap.label("new_effect", app.ascii_only)
        app.toast(f"Hand-written built-ins can't be edited; press {new} for a new effect", 3.5)
        return
    if spec.kind == USER:
        app.push(Studio(app, spec.recipe.copy(), spec.label, key.removeprefix("my_")))
    else:
        app.push(Studio(app, spec.recipe.copy(), f"{spec.label} remix"))
