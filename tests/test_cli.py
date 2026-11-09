"""The command line, called in-process with captured output."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from staticfx.cli import main
from staticfx.cli.parser import translate


def run(capsys: pytest.CaptureFixture[str], tmp_path: Path, *args: str) -> tuple[int, str, str]:
    code = main([*args, "--data-dir", str(tmp_path)])
    out, err = capsys.readouterr()
    return code, out, err


def test_list_search_and_kinds(capsys, tmp_path: Path) -> None:
    code, out, _ = run(capsys, tmp_path, "list", "fire")
    assert code == 0 and "Fireworks" in out and "matrix" not in out
    _, out, _ = run(capsys, tmp_path, "list", "--kind", "gallery")
    assert len(out.splitlines()) == 47
    _, out, err = run(capsys, tmp_path, "list", "--favorites")
    assert out == "" and "No effects match" in err


def test_themes_and_looks(capsys, tmp_path: Path) -> None:
    _, out, _ = run(capsys, tmp_path, "themes")
    assert "cyberpunk" in out and "flashing" in out
    _, out, _ = run(capsys, tmp_path, "looks")
    assert "Synthwave" in out and "none yet" in out


def test_render_text_ansi_and_file(capsys, tmp_path: Path) -> None:
    code, out, _ = run(capsys, tmp_path, "render", "plasma", "--size", "30x5", "--seed", "1")
    assert code == 0 and len(out.splitlines()) == 5 and "\x1b" not in out
    _, again, _ = run(capsys, tmp_path, "render", "plasma", "--size", "30x5", "--seed", "1")
    assert again == out  # same seed, same picture
    _, out, _ = run(capsys, tmp_path, "render", "-e", "fire", "--ansi", "--256", "--size", "20x8")
    assert "\x1b[38;5;" in out
    target = tmp_path / "frame.txt"
    code, out, _ = run(capsys, tmp_path, "render", "galaxy", "--out", str(target), "--size", "20x4")
    assert code == 0 and out == "" and len(target.read_text().splitlines()) == 4


def test_render_with_look_theme_and_filters(capsys, tmp_path: Path) -> None:
    code, _, _ = run(capsys, tmp_path, "render", "--look", "Synthwave", "--crt", "--size", "20x5")
    assert code == 0
    code, _, err = run(capsys, tmp_path, "render", "--look", "Nope")
    assert code == 2 and "no look called" in err


def test_unknown_effect_and_theme_are_usage_errors(capsys, tmp_path: Path) -> None:
    code, _, err = run(capsys, tmp_path, "render", "nope")
    assert code == 2 and "staticfx list nope" in err
    with pytest.raises(SystemExit) as exit_info:
        main(["render", "--theme", "plaid"])
    assert exit_info.value.code == 2


def test_new_import_export_round_trip(capsys, tmp_path: Path) -> None:
    code, out, _ = run(capsys, tmp_path, "new", "Night Drive", "--seed", "5")
    assert code == 0 and "my_night_drive" in out
    shared = tmp_path / "shared.sfx"
    code, out, _ = run(capsys, tmp_path, "export", "my_night_drive", str(shared))
    assert code == 0 and json.loads(shared.read_text())["name"] == "Night Drive"
    code, out, _ = run(capsys, tmp_path, "import", str(shared))
    assert code == 0 and "my_night_drive_2" in out
    code, _, err = run(capsys, tmp_path, "export", "matrix", str(shared))
    assert code == 2 and "hand-written" in err
    code, _, _ = run(capsys, tmp_path, "export", "proc_042", str(tmp_path / "gen.sfx"))
    assert code == 0
    code, _, err = run(capsys, tmp_path, "import", str(tmp_path / "missing.sfx"))
    assert code == 1 and "import failed" in err


def test_read_only_commands_write_nothing(capsys, tmp_path: Path) -> None:
    for args in (["list"], ["looks"], ["render", "matrix", "--size", "10x3"], ["doctor"]):
        run(capsys, tmp_path, *args)
    assert list(tmp_path.iterdir()) == []


def test_doctor(capsys, tmp_path: Path) -> None:
    code, out, _ = run(capsys, tmp_path, "doctor")
    assert code == 0 and "self-test" in out and "FAILED" not in out


def test_play_needs_a_terminal(capsys, tmp_path: Path) -> None:
    code, _, err = run(capsys, tmp_path)
    assert code == 2 and "needs a terminal" in err


def test_version(capsys) -> None:
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "StaticFX 2." in capsys.readouterr().out


@pytest.mark.parametrize(
    ("old", "new"),
    [
        (["--list", "fire"], ["list", "fire"]),
        (["--favorites"], ["list", "--favorites"]),
        (["--themes"], ["themes"]),
        (["--presets"], ["looks"]),
        (["--new-effect", "X", "--seed", "3"], ["new", "X", "--seed", "3"]),
        (["--import", "a.sfx"], ["import", "a.sfx"]),
        (["--export", "e", "f"], ["export", "e", "f"]),
        (
            ["--frames", "9", "-e", "plasma", "--size", "8x2"],
            ["render", "--frames", "9", "-e", "plasma", "--size", "8x2"],
        ),
        (["--fetch", "neofetch"], ["fetch", "--tool", "neofetch"]),
        (["--smoke-test"], ["doctor"]),
        (
            ["--mode", "plasma", "--rainbow", "--preset", "Ocean"],
            ["--effect", "plasma", "--recolour", "--look", "Ocean"],
        ),
        (["--plugin-dir", "x", "--no-config", "--color256"], ["--no-save", "--256"]),
        (["-e", "plasma"], ["-e", "plasma"]),
    ],
)
def test_1x_flags_still_work(old: list[str], new: list[str]) -> None:
    assert translate(old) == new


def test_1x_frames_command_end_to_end(capsys, tmp_path: Path) -> None:
    code, out, _ = run(capsys, tmp_path, "--frames", "10", "-e", "galaxy", "--size", "30x6")
    assert code == 0 and len(out.splitlines()) == 6


def _stream_frames(raw: bytes) -> tuple[str, list[list[str]]]:
    lines = raw.decode("utf-8").split("\n")
    header = lines[0]
    height = int(header.split()[3])
    frames, i = [], 1
    while i < len(lines) and lines[i] == "F":
        frames.append(lines[i + 1 : i + 1 + height])
        i += 1 + height
    return header, frames


def test_stream_writes_frames(tmp_path: Path) -> None:
    import io

    from staticfx.app import session
    from staticfx.cli.commands import load_app
    from staticfx.cli.parser import build

    args = build().parse_args(
        ["stream", "plasma", "--size", "20x6", "--seed", "3", "--data-dir", str(tmp_path)]
    )
    app = load_app(args)
    app.play(app.registry.resolve("plasma"), announce=False)
    app.resize(20, 6)
    out = io.BytesIO()
    session.stream(app, out, 20, count=3)
    header, frames = _stream_frames(out.getvalue())
    assert header == "STATICFX-STREAM 1 20 6"
    assert len(frames) == 3
    for row in frames[0]:
        width = 0
        for run in row.split("\x1f"):
            if not run:
                continue
            if run.startswith("_"):
                width += int(run[1:])
            else:
                int(run[:6], 16)
                width += len(run) - 6
        assert width <= 20


def test_stream_row_encoding() -> None:
    from staticfx.app.session import encode_stream_row
    from staticfx.core.color import RGB
    from staticfx.core.frame import Cell

    row = [
        Cell(" "),
        Cell("#", RGB(255, 136, 0)),
        Cell("#", RGB(255, 136, 0)),
        Cell(" "),
        Cell("*", RGB(1, 2, 3)),
    ]
    assert encode_stream_row(row) == b"_1\x1fff8800##\x1f_1\x1f010203*\n"
    assert encode_stream_row([Cell(" ")] * 3) == b"\n"


def test_stream_command_and_tsv(capsys, tmp_path: Path) -> None:
    code, out, _ = run(capsys, tmp_path, "themes", "--tsv")
    assert code == 0
    assert out.splitlines()[0].split("\t")[0] == "matrix"
    code, out, _ = run(capsys, tmp_path, "list", "galaxy", "--tsv")
    assert code == 0
    assert all(len(line.split("\t")) == 3 for line in out.splitlines())
    code, out, _ = run(capsys, tmp_path, "looks", "--tsv")
    assert code == 0
    assert all(len(line.split("\t")) == 5 for line in out.splitlines())
