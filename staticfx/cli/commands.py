"""One function per subcommand. Each returns the process exit code."""

from __future__ import annotations

import argparse
import contextlib
import platform
import random
import sys
import time
from pathlib import Path

from staticfx import __version__, themes
from staticfx.app import session
from staticfx.app.app import App
from staticfx.core.frame import Frame
from staticfx.core.renderer import Renderer
from staticfx.core.terminal import is_interactive, supported, terminal_size
from staticfx.effects.engine import generate
from staticfx.effects.spec import BUILTIN, GENERATED, USER
from staticfx.integrations import overlay, system_info
from staticfx.library import config
from staticfx.library.effects import EffectLibrary, UserEffect, export
from staticfx.library.files import clean_name, default_data_dir, slugify
from staticfx.library.looks import BUILTIN_LOOKS, find_look

EXIT_OK, EXIT_ERROR, EXIT_USAGE = 0, 1, 2


def fail(message: str, code: int = EXIT_USAGE) -> int:
    print(f"staticfx: {message}", file=sys.stderr)
    return code


def data_dir(args: argparse.Namespace) -> Path:
    return Path(args.data_dir).expanduser() if args.data_dir else default_data_dir()


def load_app(args: argparse.Namespace, persist: bool = False) -> App:
    """The app with the user's settings and library loaded, and the command-line
    options from the "what to show" group applied on top."""
    folder = data_dir(args)
    settings, warnings = config.load(folder / "config.json")
    seed = getattr(args, "seed", None)
    app = App(
        settings,
        folder,
        utf8=session.supports_utf8(),
        persist_settings=persist,
        rng=random.Random(seed),
    )
    app.notes += warnings
    if getattr(args, "ascii", False):
        app.override("characters", "ascii")
    elif getattr(args, "katakana", False):
        app.override("characters", "katakana")
    app.apply_characters()
    app.start()
    return app


def apply_look_options(app: App, args: argparse.Namespace) -> str | None:
    """Apply --look, --effect, --theme, --speed and the filters. Returns an error, if any."""
    if args.look:
        look = find_look(args.look, app.looks)
        if look is None:
            names = ", ".join(look.name for look in (*app.looks.looks, *BUILTIN_LOOKS))
            return f"no look called '{args.look}' (try one of: {names})"
        app.settings.allow_flashing |= look.theme == "strobe" and args.theme == "strobe"
        app.apply_look(look)
    effect = getattr(args, "effect_name", None) or args.effect
    if effect:
        if effect.lower() == "random":
            app.play_random()
        else:
            try:
                app.play(app.registry.resolve(effect), announce=False)
            except KeyError:
                return f"unknown effect '{effect}' (search with: staticfx list {effect})"
    if args.theme:
        app.set_theme(args.theme)
    if args.speed:
        app.player.speed = min(5.0, max(0.1, args.speed))
    post = app.player.post
    for name in ("crt", "glitch", "recolour"):
        value = getattr(args, name)
        if value is not None:
            setattr(post, name, value)
    return None


def play(args: argparse.Namespace) -> int:
    if not supported():
        return fail("the interactive app needs Linux, macOS or WSL (try `staticfx render`)")
    if not is_interactive():
        return fail("the interactive app needs a terminal; for piped output use `staticfx render`")
    app = load_app(args, persist=not args.no_save)
    app.player.adaptive = True
    app.player.reload()
    if args.fps:
        app.override("fps", args.fps)
    if args.color256:
        app.override("colour", "256")
    error = apply_look_options(app, args)
    if error:
        return fail(error)
    if args.auto:
        low, high = config.AUTO_RANGE
        app.override("auto_seconds", min(high, max(low, args.auto)))
        app.auto = True
        app.auto_timer = app.settings.auto_seconds
    with contextlib.suppress(KeyboardInterrupt):  # SIGINT from outside; Ctrl-C is a key
        session.run(app, args.duration)
    for note in app.notes:
        print(f"staticfx: {note}", file=sys.stderr)
    return EXIT_OK


def render(args: argparse.Namespace) -> int:
    app = load_app(args)
    error = apply_look_options(app, args)
    if error:
        return fail(error)
    app.resize(*args.size)
    frame = session.render_frames(app, args.frames)
    text = (
        Renderer(truecolor=not args.color256).full(frame) if args.ansi else "\n".join(frame.lines())
    )
    if args.out:
        try:
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        except OSError as exc:
            return fail(f"can't write {args.out}: {exc.strerror}", EXIT_ERROR)
    else:
        print(text)
    return EXIT_OK


def fetch(args: argparse.Namespace) -> int:
    try:
        info = system_info(args.tool)
    except RuntimeError as exc:
        return fail(str(exc), EXIT_ERROR)
    app = load_app(args)
    error = apply_look_options(app, args)
    if error:
        return fail(error)
    width, height = terminal_size() if is_interactive() else (80, 24)
    app.resize(width, height - 1)
    frame = session.render_frames(app, 90)
    overlay(frame, app.player.theme(), info)
    print(Renderer(truecolor=session.wants_truecolor(app)).full(frame))
    return EXIT_OK


def list_effects(args: argparse.Namespace) -> int:
    app = load_app(args)
    specs = app.registry.specs()
    if args.kind == "gallery":
        specs = [app.registry[k] for k in app.registry.gallery]
    elif args.kind:
        kind = {"mine": USER, "generated": GENERATED}.get(args.kind, args.kind)
        specs = [s for s in specs if s.kind == kind]
    if args.favorites:
        specs = [s for s in specs if app.is_favorite(s.key)]
    words = [w.lower() for w in args.query]
    specs = [s for s in specs if all(w in s.search_text() for w in words)]
    for spec in specs:
        star = "*" if app.is_favorite(spec.key) else " "
        print(f"{star} {spec.key:<20} {spec.label:<30} {spec.category}")
    if not specs:
        print("No effects match.", file=sys.stderr)
    return EXIT_OK


def list_themes(args: argparse.Namespace) -> int:
    for key, label in themes.LABELS.items():
        note = "  (flashing: allow it in Settings first)" if key == "strobe" else ""
        print(f"{key:<10} {label}{note}")
    return EXIT_OK


def list_looks(args: argparse.Namespace) -> int:
    app = load_app(args)
    for heading, looks in (("Yours", app.looks.looks), ("Built in", BUILTIN_LOOKS)):
        print(f"{heading}:")
        if not looks:
            save = app.keymap.label("save_look", ascii_only=True)
            print(f"  (none yet: press {save} while an effect plays to save one)")
        for look in looks:
            print(f"  {look.name:<20} {look.effect:<18} {look.theme:<10} {look.note}")
    return EXIT_OK


def new_effect(args: argparse.Namespace) -> int:
    name = clean_name(args.name)
    if not name:
        return fail("the effect needs a name")
    library = EffectLibrary(data_dir(args) / "effects")
    seed = args.seed if args.seed is not None else random.randrange(10**6, 10**7)
    effect = UserEffect(library.unique_id(name), name, generate(seed)[0])
    try:
        path = library.save(effect)
    except OSError as exc:
        return fail(f"can't save: {exc.strerror}", EXIT_ERROR)
    print(f"Created '{name}' in {path}\nPlay it with:  staticfx -e {effect.key}")
    return EXIT_OK


def import_effect(args: argparse.Namespace) -> int:
    library = EffectLibrary(data_dir(args) / "effects")
    try:
        effect = library.import_file(Path(args.file))
    except (ValueError, OSError) as exc:
        return fail(f"import failed: {exc}", EXIT_ERROR)
    print(f"Imported '{effect.name}'. Play it with:  staticfx -e {effect.key}")
    return EXIT_OK


def export_effect(args: argparse.Namespace) -> int:
    app = load_app(args)
    try:
        spec = app.registry[app.registry.resolve(args.effect)]
    except KeyError:
        return fail(f"unknown effect '{args.effect}'")
    if spec.recipe is None:
        return fail(f"'{spec.label}' is hand-written; only Studio and generated effects export")
    effect = UserEffect(slugify(spec.label), spec.label, spec.recipe, spec.description)
    try:
        path = export(effect, Path(args.file))
    except OSError as exc:
        return fail(f"can't write {args.file}: {exc.strerror}", EXIT_ERROR)
    print(f"Exported '{spec.label}' to {path}")
    return EXIT_OK


def doctor(args: argparse.Namespace) -> int:
    """Report on the environment and saved files, then render every effect once."""
    folder = data_dir(args)
    print(f"StaticFX {__version__} on Python {platform.python_version()} ({platform.system()})")
    width, height = terminal_size()
    traits = [
        "interactive" if is_interactive() else "not a terminal",
        f"{width}x{height}",
        "UTF-8" if session.supports_utf8() else "ASCII only",
        "truecolor" if session.supports_truecolor() else "256 colours",
    ]
    print(f"terminal    {', '.join(traits)} (colour support is a best guess)")
    if not supported():
        print("            interactive mode is not supported here (needs Linux, macOS or WSL)")
    print(f"data folder {folder}")

    app = load_app(args)
    registry = app.registry
    counts = f"{registry.count(BUILTIN)} built in, {registry.count(GENERATED)} generated"
    print(f"effects     {len(registry)}: {counts}, {registry.count(USER)} yours")
    print(f"looks       {len(app.looks.looks)} saved, {len(BUILTIN_LOOKS)} built in")
    for note in app.notes:
        print(f"  warning   {note}")

    keys = [s.key for s in registry.specs() if s.kind != GENERATED]
    keys += [s.key for s in registry.specs() if s.kind == GENERATED][::20]
    print(f"self-test   rendering {len(keys)} effects...", end="", flush=True)
    failures, started = [], time.perf_counter()
    theme = themes.STATIC_THEMES[themes.DEFAULT]
    for key in keys:
        try:
            effect = registry.make(key, random.Random(1))
            effect.resize(80, 24)
            frame = Frame(80, 24)
            for _ in range(5):
                effect.update(1 / 30)
                effect.draw(frame, theme)
        except Exception as exc:  # report every broken effect rather than stopping at one
            failures.append(f"{key}: {exc.__class__.__name__}: {exc}")
    print(f" {len(keys) - len(failures)} ok in {time.perf_counter() - started:.1f}s")
    for failure in failures:
        print(f"  FAILED    {failure}")
    return EXIT_ERROR if failures else EXIT_OK


HANDLERS = {
    "play": play,
    "render": render,
    "fetch": fetch,
    "list": list_effects,
    "themes": list_themes,
    "looks": list_looks,
    "new": new_effect,
    "import": import_effect,
    "export": export_effect,
    "doctor": doctor,
}
