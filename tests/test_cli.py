"""Tests for the command line interface."""

from __future__ import annotations

from pathlib import Path

import pytest

from chart_to_data.__main__ import main


def _write_p3(path: Path, width: int, height: int, pixels: list[tuple[int, int, int]]) -> None:
    header = f"P3\n{width} {height}\n255\n"
    body = "\n".join(" ".join(map(str, rgb)) for rgb in pixels)
    path.write_text(header + body + "\n", encoding="ascii")


def _make_test_image(path: Path) -> None:
    # Create a 100x100 white image with three bars as in acceptance test
    width, height = 100, 100
    pixels = [(255, 255, 255)] * (width * height)
    color = (31, 119, 180)
    bars = ((20, 30, 50), (40, 50, 30), (60, 70, 70))
    for left, right, top in bars:
        for y in range(top, 90):
            for x in range(left, right):
                pixels[y * width + x] = color
    _write_p3(path, width, height, pixels)


def test_cli_bars(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    img_path = tmp_path / "chart.ppm"
    _make_test_image(img_path)
    exit_code = main(
        [
            str(img_path),
            "--area",
            "10,10,90,90",
            "--y",
            "90:0,10:100",
            "--color",
            "1f77b4",
            "--bars",
        ]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == "left,right,value\n20,29,50.0\n40,49,75.0\n60,69,25.0\n"


def test_cli_bars_no_found(tmp_path: Path) -> None:
    img_path = tmp_path / "empty.ppm"
    _write_p3(img_path, 100, 100, [(255, 255, 255)] * 10000)
    exit_code = main(
        [
            str(img_path),
            "--area",
            "10,10,90,90",
            "--y",
            "90:0,10:100",
            "--color",
            "000000",
            "--bars",
        ]
    )
    assert exit_code == 1


def test_cli_malformed_y(tmp_path: Path) -> None:
    img_path = tmp_path / "chart.ppm"
    _make_test_image(img_path)
    exit_code = main(
        [
            str(img_path),
            "--area",
            "10,10,90,90",
            "--y",
            "badformat",
            "--color",
            "1f77b4",
            "--bars",
        ]
    )
    assert exit_code == 2


def test_cli_line(tmp_path: Path) -> None:
    # Create line image
    img_path = tmp_path / "line.ppm"
    width, height = 100, 100
    pixels = [(255, 255, 255)] * (width * height)
    color = (214, 39, 40)
    for x in range(10, 91):
        y = 90 - (x - 10)
        pixels[y * width + x] = color
    _write_p3(img_path, width, height, pixels)
    exit_code = main(
        [
            str(img_path),
            "--area",
            "10,10,90,90",
            "--x",
            "10:0,90:8",
            "--y",
            "90:0,10:100",
            "--color",
            "d62728",
            "--line",
            "--xs",
            "0,4,8",
        ]
    )
    assert exit_code == 0
