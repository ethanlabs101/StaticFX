"""The ``staticfx`` command."""

from __future__ import annotations

import sys

from staticfx.cli.commands import HANDLERS
from staticfx.cli.parser import COMMANDS, build, translate


def main(argv: list[str] | None = None) -> int:
    args = translate(list(sys.argv[1:] if argv is None else argv))
    if not args or (args[0] not in COMMANDS and args[0] not in ("-h", "--help", "--version")):
        args = ["play", *args]  # plain `staticfx [options]` plays
    options = build().parse_args(args)
    # Output may be piped or the locale may be C; a glyph must never crash a listing.
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(errors="replace")
    return HANDLERS[options.command](options)
