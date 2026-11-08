"""Render StaticFX frames to PNG images and GIFs (for the README and for reviewing changes).

    python tools/screenshot.py png plasma out.png --theme ocean
    python tools/screenshot.py gif matrix out.gif --seconds 4
    python tools/screenshot.py sheet sheet.png --keys proc_001 proc_002 ...

Needs Pillow (``pip install pillow``); StaticFX itself does not.
"""

from __future__ import annotations

import argparse
import random
import sys
from collections.abc import Callable
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from staticfx.app.app import App
from staticfx.core.frame import Frame
from staticfx.library.config import Settings

FONT_PATHS = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/Library/Fonts/Menlo.ttc",
    "C:/Windows/Fonts/consola.ttf",
)
BACKGROUND = (10, 10, 14)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_PATHS:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise SystemExit("no monospace font found; edit FONT_PATHS")


def to_image(frame: Frame, font: ImageFont.FreeTypeFont) -> Image.Image:
    left, top, right, bottom = font.getbbox("M")
    cell_w, cell_h = right - left, int((bottom - top) * 1.45)
    image = Image.new("RGB", (frame.width * cell_w, frame.height * cell_h), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for y, row in enumerate(frame.cells):
        for x, cell in enumerate(row):
            if cell.char != " ":
                draw.text((x * cell_w, y * cell_h), cell.char, fill=tuple(cell.color), font=font)
    return image


def make_app(width: int, height: int, seed: int) -> App:
    app = App(Settings(seen_welcome=True), None, rng=random.Random(seed))
    app.start()
    app.resize(width, height)
    app.screens[0].hint_time = 0.0  # no key hints in pictures
    return app


def capture(
    app: App, seconds: float, fps: int = 20, setup: Callable[[App], None] | None = None
) -> list[Frame]:
    frames = []
    if setup:
        setup(app)
    for _ in range(int(seconds * fps)):
        for _ in range(30 // fps):
            app.update(1 / 30)
        frame = Frame(app.width, app.height)
        app.draw(frame)
        frames.append(frame)
    return frames


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("mode", choices=("png", "gif", "sheet"))
    parser.add_argument("effect", nargs="?", default="matrix")
    parser.add_argument("out")
    parser.add_argument("--theme", default="matrix")
    parser.add_argument("--size", default="100x30")
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--font", type=int, default=14)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--keys", nargs="*", default=[])
    args = parser.parse_args()
    width, height = (int(v) for v in args.size.split("x"))
    font = load_font(args.font)

    if args.mode == "sheet":
        tiles = []
        for key in args.keys:
            app = make_app(width, height, args.seed)
            app.set_theme(args.theme)
            app.play(key, announce=False)
            frame = capture(app, 2.0, fps=10)[-1]
            frame.text(0, 0, f" {key} ", app.player.theme().bright)
            tiles.append(to_image(frame, font))
        columns = 4
        tile_w, tile_h = tiles[0].size
        rows = (len(tiles) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * (tile_w + 6), rows * (tile_h + 6)), (40, 40, 48))
        for i, tile in enumerate(tiles):
            sheet.paste(tile, ((i % columns) * (tile_w + 6), (i // columns) * (tile_h + 6)))
        sheet.save(args.out)
        return

    app = make_app(width, height, args.seed)
    app.set_theme(args.theme)
    app.play(args.effect, announce=False)
    if args.mode == "png":
        to_image(capture(app, args.seconds)[-1], font).save(args.out)
    else:
        images = [to_image(f, font) for f in capture(app, args.seconds)]
        images[0].save(args.out, save_all=True, append_images=images[1:], duration=50, loop=0)


if __name__ == "__main__":
    main()
