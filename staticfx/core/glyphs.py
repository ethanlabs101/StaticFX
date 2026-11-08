"""Character pools shared by several effects."""

from __future__ import annotations

import string

TECH = string.ascii_uppercase + string.digits + "!@#$%^&*<>/\\|=+-_~"
KATAKANA = "".join(chr(code) for code in range(0xFF66, 0xFF9E)) + string.digits
BINARY = "01"
HEX = "0123456789ABCDEF"


def tech_glyphs(unicode: bool) -> str:
    """The "terminal noise" pool: half-width katakana when Unicode is enabled."""
    return KATAKANA if unicode else TECH
