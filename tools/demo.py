"""Record the README's demo GIF by driving the app through a short tour.

    python tools/demo.py assets/demo.gif

Needs Pillow and ffmpeg. The tour is a list of (seconds, keys) steps below;
edit it to change the demo.
"""

from __future__ import annotations

import argparse
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from screenshot import load_font, to_image

from staticfx.app.app import App
from staticfx.core.frame import Frame
from staticfx.library.config import Settings

FPS = 12
SIZE = (96, 28)

# (seconds to show, keys to press first)
TOUR: list[tuple[float, list[str]]] = [
    (2.4, []),  # Matrix Rain
    (0.8, ["m"]),  # open the browser
    (1.2, ["/", *"galax"]),  # search
    (2.0, ["enter"]),  # play Galaxy
    (0.6, ["t"]),  # themes, previewed while scrolling
    (0.5, ["down"] * 4),
    (0.5, ["down"] * 4),
    (1.2, ["down"] * 5),
    (1.6, ["enter", "m", "tab", "tab", "tab", "tab"]),  # back in the browser: the Gallery
    (1.0, ["down"]),
    (1.0, ["down"]),
    (2.0, ["enter"]),
    (0.8, ["n"]),  # the Studio
    (0.6, ["down", "down"]),
    (0.6, ["right"]),
    (0.6, ["right"]),
    (1.4, ["right"]),
    (1.8, ["escape", "y", "l", *["down"] * 6]),  # looks
    (2.4, ["enter"]),  # Synthwave
]


def record(out: Path) -> None:
    font = load_font(13)
    data = Path(tempfile.mkdtemp())
    app = App(Settings(seen_welcome=True), data, rng=random.Random(3))
    app.start()
    app.resize(*SIZE)
    app.screens[0].hint_time = 0.0
    frames = Path(tempfile.mkdtemp())
    count = 0
    for seconds, keys in TOUR:
        for key in keys:
            app.handle_key(key)
            for _ in range(2):
                app.update(1 / 30)
        for _ in range(int(seconds * FPS)):
            app.update(1 / FPS)
            frame = Frame(*SIZE)
            app.draw(frame)
            to_image(frame, font).save(frames / f"{count:04d}.png")
            count += 1
    palette = frames / "palette.png"
    pattern = str(frames / "%04d.png")
    ffmpeg = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", pattern]
    make_palette = "palettegen=max_colors=128:stats_mode=diff"
    use_palette = "paletteuse=dither=none:diff_mode=rectangle"
    subprocess.run([*ffmpeg, "-vf", make_palette, str(palette)], check=True)
    subprocess.run(
        [*ffmpeg, "-i", str(palette), "-lavfi", use_palette, "-loop", "0", str(out)], check=True
    )
    shutil.rmtree(frames)
    shutil.rmtree(data)
    print(f"{out}: {count} frames, {out.stat().st_size / 1e6:.1f} MB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", type=Path)
    record(parser.parse_args().out)


if __name__ == "__main__":
    main()
