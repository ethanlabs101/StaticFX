"""Command-line arguments."""

from __future__ import annotations

import argparse

from staticfx import __version__, themes

COMMANDS = (
    "play",
    "list",
    "themes",
    "looks",
    "new",
    "import",
    "export",
    "render",
    "stream",
    "fetch",
    "doctor",
)

EPILOG = """\
In the app: arrows browse, m opens the effect browser, t themes, l looks,
n the Studio, o settings, ? every key.

examples:
  staticfx                         play (picks up where you left off)
  staticfx -e plasma -t ocean      start on an effect and theme
  staticfx --auto 20               screensaver: a new effect every 20 seconds
  staticfx list fire               search effects
  staticfx render galaxy --size 80x24 --ansi > galaxy.txt
  staticfx stream plasma --size 120x40 | my-program
"""


def size(text: str) -> tuple[int, int]:
    try:
        width, height = (int(part) for part in text.lower().split("x"))
    except ValueError:
        raise argparse.ArgumentTypeError("size must look like 80x24") from None
    if not (1 <= width <= 1000 and 1 <= height <= 500):
        raise argparse.ArgumentTypeError("size must be between 1x1 and 1000x500")
    return width, height


def positive(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text}") from None
    if value <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return value


def theme(text: str) -> str:
    try:
        return themes.normalize(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def build() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data-dir", metavar="DIR", help="where effects, looks and settings live")

    look = argparse.ArgumentParser(add_help=False)
    group = look.add_argument_group("what to show")
    group.add_argument("-e", "--effect", help="effect key, name, proc42-style number, or 'random'")
    group.add_argument("-t", "--theme", type=theme, help=f"one of: {', '.join(themes.LABELS)}")
    group.add_argument("--look", help="start from a saved or built-in look")
    group.add_argument("--speed", type=positive, help="animation speed (1.0 is normal)")
    group.add_argument("--crt", action=argparse.BooleanOptionalAction, help="CRT scanlines")
    group.add_argument("--glitch", action=argparse.BooleanOptionalAction, help="glitch filter")
    group.add_argument("--recolour", action=argparse.BooleanOptionalAction, help="rainbow recolour")
    group.add_argument("--seed", type=int, help="random seed, for reproducible output")
    group.add_argument("--ascii", action="store_true", help="plain ASCII only")
    group.add_argument("--katakana", action="store_true", help="katakana in the rain effects")

    interactive = argparse.ArgumentParser(add_help=False)
    interactive.add_argument(
        "--auto",
        type=positive,
        nargs="?",
        const=12.0,
        metavar="SECS",
        help="change effect every SECS seconds (default 12)",
    )
    interactive.add_argument(
        "--duration", type=positive, metavar="SECS", help="quit after SECS seconds"
    )
    interactive.add_argument(
        "--fps", type=int, choices=range(5, 61), metavar="5-60", help="frame rate"
    )
    interactive.add_argument(
        "--256", dest="color256", action="store_true", help="force 256 colours"
    )
    interactive.add_argument("--no-save", action="store_true", help="don't save settings on exit")

    parser = argparse.ArgumentParser(
        prog="staticfx",
        description="Animated ASCII effects for your terminal.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"StaticFX {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    sub.add_parser("play", parents=[common, look, interactive], help="run the app (the default)")

    lister = sub.add_parser("list", parents=[common], help="list or search effects")
    lister.add_argument("query", nargs="*", help="words to search for")
    lister.add_argument("--kind", choices=("builtin", "generated", "mine", "gallery"))
    lister.add_argument("--favorites", action="store_true", help="only your favourites")
    lister.add_argument("--tsv", action="store_true", help="tab-separated, for other programs")

    themer = sub.add_parser("themes", parents=[common], help="list themes")
    themer.add_argument("--tsv", action="store_true", help="tab-separated, for other programs")
    looker = sub.add_parser("looks", parents=[common], help="list saved and built-in looks")
    looker.add_argument("--tsv", action="store_true", help="tab-separated, for other programs")

    new = sub.add_parser("new", parents=[common], help="create a random effect in My Effects")
    new.add_argument("name")
    new.add_argument("--seed", type=int, help="pick the starting recipe")

    importer = sub.add_parser("import", parents=[common], help="add a .sfx file to My Effects")
    importer.add_argument("file")

    exporter = sub.add_parser("export", parents=[common], help="save an effect as a .sfx file")
    exporter.add_argument("effect", help="one of your effects, or a generated one (proc_NNN)")
    exporter.add_argument("file")

    render = sub.add_parser("render", parents=[common, look], help="print one frame and exit")
    render.add_argument("effect_name", nargs="?", metavar="EFFECT")
    render.add_argument("--size", type=size, default=(80, 24), metavar="WxH")
    render.add_argument(
        "--frames", type=int, default=60, metavar="N", help="frames to simulate first (default 60)"
    )
    render.add_argument("--ansi", action="store_true", help="keep colours (escape codes)")
    render.add_argument("--256", dest="color256", action="store_true", help="256-colour codes")
    render.add_argument("--out", metavar="FILE", help="write to FILE instead of the screen")

    streamer = sub.add_parser(
        "stream",
        parents=[common, look],
        help="write frames continuously for other programs to draw",
        description=(
            "Write animation frames to standard output in a simple text format "
            "(see docs/STREAM.md) until the reader goes away."
        ),
    )
    streamer.add_argument("effect_name", nargs="?", metavar="EFFECT")
    streamer.add_argument("--size", type=size, default=(80, 24), metavar="WxH")
    streamer.add_argument(
        "--fps", type=int, choices=range(1, 61), default=20, metavar="1-60", help="frame rate"
    )
    streamer.add_argument(
        "--count", type=int, metavar="N", help="stop after N frames (uses a fixed time step)"
    )

    fetch = sub.add_parser(
        "fetch", parents=[common, look, interactive], help="system info over an effect"
    )
    fetch.add_argument(
        "--tool", choices=("fastfetch", "neofetch"), help="default: whichever is installed"
    )
    fetch.add_argument(
        "--once", action="store_true", help="print one still frame and exit (for shell startup)"
    )

    sub.add_parser("doctor", parents=[common], help="check your setup and run a self-test")
    return parser


# StaticFX 1.x flags, mapped to the commands that replaced them.
LEGACY_COMMANDS = {
    "--list": "list",
    "--favorites": "list",
    "--themes": "themes",
    "--looks": "looks",
    "--presets": "looks",
    "--scenes": "looks",
    "--new-effect": "new",
    "--import": "import",
    "--export": "export",
    "--frames": "render",
    "--fetch": "fetch",
    "--smoke-test": "doctor",
    "--info": "doctor",
}
LEGACY_RENAMES = {
    "--mode": "--effect",
    "--rainbow": "--recolour",
    "--no-rainbow": "--no-recolour",
    "--unicode": "--katakana",
    "--color256": "--256",
    "--preset": "--look",
    "--scene": "--look",
    "--no-config": "--no-save",
}
LEGACY_KEPT = {"--favorites": "--favorites", "--fetch": "--tool", "--frames": "--frames"}
LEGACY_DROPPED = {"--no-unicode", "--no-katakana", "--no-256", "--no-color256", "--plugin-dir"}


def translate(argv: list[str]) -> list[str]:
    """Rewrite a 1.x command line (``--list fire``) into the new form (``list fire``)."""
    command = None
    out: list[str] = []
    args = iter(argv)
    for arg in args:
        if arg in LEGACY_DROPPED:
            if arg == "--plugin-dir":
                next(args, None)
        elif arg in LEGACY_COMMANDS:
            command = command or LEGACY_COMMANDS[arg]
            if arg in LEGACY_KEPT:  # these become the command *and* keep an option
                out.append(LEGACY_KEPT[arg])
        else:
            out.append(LEGACY_RENAMES.get(arg, arg))
    return [command, *out] if command else out
