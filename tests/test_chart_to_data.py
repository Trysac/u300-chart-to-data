"""Tests for chart_to_data."""

from __future__ import annotations

import pytest

from chart_to_data import (
    Bar,
    Calibration,
    ChartError,
    RgbImage,
    dominant_colors,
    extract_bars,
    extract_line,
    load_image,
)


def _make_p3(width: int, height: int, pixels: list[tuple[int, int, int]]) -> bytes:
    """Create P3 PNM bytes from list of RGB tuples."""
    header = f"P3\n{width} {height}\n255\n"
    body = "\n".join(" ".join(map(str, rgb)) for rgb in pixels)
    return (header + body + "\n").encode("ascii")


def _make_p6(width: int, height: int, pixels: bytes) -> bytes:
    """Create P6 PNM bytes from raw RGB bytes."""
    header = f"P6\n{width} {height}\n255\n".encode("ascii")
    return header + pixels


def _make_white_image(width: int = 100, height: int = 100) -> RgbImage:
    pixels = [(255, 255, 255)] * (width * height)
    return load_image(_make_p3(width, height, pixels))


def _set_pixel(img: RgbImage, x: int, y: int, color: tuple[int, int, int]) -> RgbImage:
    """Return a new RgbImage with one pixel changed."""
    pixels = bytearray(img.pixels)
    idx = (y * img.width + x) * 3
    pixels[idx : idx + 3] = bytes(color)
    return RgbImage(img.width, img.height, bytes(pixels))


def _draw_vertical_bar(
    img: RgbImage, left: int, right: int, top: int, bottom: int, color: tuple[int, int, int]
) -> RgbImage:
    """Draw a solid vertical bar by setting pixels."""
    result = img
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            result = _set_pixel(result, x, y, color)
    return result


def test_calibration_exact() -> None:
    cal = Calibration.from_points((90, 0.0), (10, 100.0))
    assert cal.value(50) == 50.0
    assert cal.pixel(75.0) == 30
    with pytest.raises(ChartError) as exc_info:
        Calibration.from_points((90, 0.0), (90, 100.0))
    assert exc_info.value.code == "invalid_calibration"


def test_extract_bars_acceptance() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (31, 119, 180)
    # Draw three bars
    img = _draw_vertical_bar(img, 20, 29, 50, 89, color)
    img = _draw_vertical_bar(img, 40, 49, 30, 89, color)
    img = _draw_vertical_bar(img, 60, 69, 70, 89, color)
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    bars = extract_bars(img, area, y_cal, color)
    assert bars == [
        Bar(left=20, right=29, value=50.0),
        Bar(left=40, right=49, value=75.0),
        Bar(left=60, right=69, value=25.0),
    ]


def test_extract_bars_tolerance_and_min_width() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (35, 115, 185)
    # Draw a bar with default tolerance (30), should be found
    img = _draw_vertical_bar(img, 20, 29, 50, 89, color)
    # Draw gray gridlines (200,200,200) which should be ignored
    for x in range(20, 30):
        img = _set_pixel(img, x, 70, (200, 200, 200))
    # Draw a 1-pixel-wide column that should be ignored with min_bar_width=2
    img = _draw_vertical_bar(img, 40, 40, 60, 79, color)
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    bars = extract_bars(img, area, y_cal, color)
    assert len(bars) == 1
    assert bars[0].left == 20 and bars[0].right == 29


def test_negative_bar() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (0, 0, 255)
    # y_cal: (50,0) and (10,100) => zero row at 50
    y_cal = Calibration.from_points((50, 0.0), (10, 100.0))
    # Bar fills rows 50-69 (below zero)
    img = _draw_vertical_bar(img, 30, 39, 50, 69, color)
    bars = extract_bars(img, area, y_cal, color)
    assert bars == [Bar(left=30, right=39, value=-50.0)]


def test_extract_line_basic() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (214, 39, 40)
    # Draw line: row = 90 - (x - 10) for x from 10 to 90
    for x in range(10, 91):
        y = 90 - (x - 10)
        img = _set_pixel(img, x, y, color)
    x_cal = Calibration.from_points((10, 0.0), (90, 8.0))
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    values = extract_line(img, area, x_cal, y_cal, color, xs=[0.0, 4.0, 8.0])
    assert values == [0.0, 50.0, 100.0]
    # x=8.5 gives column 95 outside area -> None
    values2 = extract_line(img, area, x_cal, y_cal, color, xs=[8.5])
    assert values2 == [None]


def test_extract_line_gap_interpolation() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (214, 39, 40)
    # Draw line but erase in columns 45-55
    for x in range(10, 91):
        y = 90 - (x - 10)
        if x < 45 or x > 55:
            img = _set_pixel(img, x, y, color)
    x_cal = Calibration.from_points((10, 0.0), (90, 8.0))
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    # x=4.0 -> column 50, gap width 11 > max_gap_px=3 -> None
    values = extract_line(img, area, x_cal, y_cal, color, xs=[4.0], max_gap_px=3)
    assert values == [None]
    # x=8.0 -> column 90, still data
    values2 = extract_line(img, area, x_cal, y_cal, color, xs=[8.0], max_gap_px=3)
    assert values2 == [100.0]


def test_dominant_colors() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (31, 119, 180)
    # Fill area with color, then add some white background
    # Actually area is white initially; we draw bars of color, then test
    img = _draw_vertical_bar(img, 20, 29, 50, 89, color)
    img = _draw_vertical_bar(img, 40, 49, 30, 89, color)
    img = _draw_vertical_bar(img, 60, 69, 70, 89, color)
    colors = dominant_colors(img, area)
    # Most frequent is white (background), excluded; second is color with count sum
    count_total = (
        (29 - 20 + 1) * (89 - 50 + 1)
        + (49 - 40 + 1) * (89 - 30 + 1)
        + (69 - 60 + 1) * (89 - 70 + 1)
    )
    assert colors == [((31, 119, 180), count_total)]


def test_load_image_errors() -> None:
    # Unsupported maxval
    p3_unsupported = b"P3\n1 1\n65535\n0 0 0\n"
    with pytest.raises(ChartError) as exc_info:
        load_image(p3_unsupported)
    assert exc_info.value.code == "unsupported_image"
    # Too many pixels
    p3_large = b"P3\n10000 10000\n255\n" + b"0 " * (
        10000 * 10000 * 3
    )  # huge, likely memory error, but we check limit before
    with pytest.raises(ChartError) as exc_info:
        load_image(p3_large)
    assert exc_info.value.code == "image_too_large"
    # Truncated data
    p6_truncated = b"P6\n2 2\n255\n" + b"\x00" * 5  # only 5 bytes, need 12
    with pytest.raises(ChartError) as exc_info:
        load_image(p6_truncated)
    assert exc_info.value.code == "invalid_image"


def test_invalid_area() -> None:
    img = _make_white_image()
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    with pytest.raises(ChartError) as exc_info:
        extract_bars(img, (10, 10, 200, 90), y_cal, (0, 0, 0))
    assert exc_info.value.code == "invalid_area"


def test_two_adjacent_bars_separated_by_one_column() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (10, 20, 30)
    # Bar 1 columns 20-29, gap column 30, bar 2 columns 31-40
    img = _draw_vertical_bar(img, 20, 29, 50, 89, color)
    img = _draw_vertical_bar(img, 31, 40, 50, 89, color)
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    bars = extract_bars(img, area, y_cal, color)
    assert len(bars) == 2
    assert bars[0].left == 20 and bars[0].right == 29
    assert bars[1].left == 31 and bars[1].right == 40


def test_bar_touching_area_edge() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (1, 2, 3)
    # Bar touches left edge of area: columns 10-19
    img = _draw_vertical_bar(img, 10, 19, 50, 89, color)
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    bars = extract_bars(img, area, y_cal, color)
    assert bars == [Bar(left=10, right=19, value=50.0)]


def test_anti_aliased_edge_outside_tolerance() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (100, 100, 100)
    # Draw bar with color, but add anti-aliased pixel with difference > tolerance
    img = _draw_vertical_bar(img, 20, 29, 50, 89, color)
    # Add a pixel at top edge with color (150,150,150), diff 50 > tolerance 30
    img = _set_pixel(img, 20, 49, (150, 150, 150))
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    bars = extract_bars(img, area, y_cal, color, tolerance=30)
    # Should still find bar with top at 50 (ignoring the anti-aliased pixel)
    assert bars == [Bar(left=20, right=29, value=50.0)]


def test_calibration_inverted_values() -> None:
    # Top pixel has smaller value: e.g., p1=(10, 100), p2=(90, 0)
    cal = Calibration.from_points((10, 100.0), (90, 0.0))
    assert cal.value(50) == 50.0
    assert cal.pixel(50.0) == 50
    # Use this calibration for a bar
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (0, 255, 0)
    img = _draw_vertical_bar(img, 20, 29, 50, 89, color)
    bars = extract_bars(img, area, cal, color)
    # zero_row = cal.pixel(0.0) = 90? because value 0 is at pixel 90
    # top=50 < zero_row=90, so positive bar value = cal.value(50) = 50.0
    assert bars == [Bar(left=20, right=29, value=50.0)]


def test_horizontal_line_constant_value() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (255, 0, 0)
    # Horizontal line at row 50 from column 10 to 90
    for x in range(10, 91):
        img = _set_pixel(img, x, 50, color)
    x_cal = Calibration.from_points((10, 0.0), (90, 8.0))
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    values = extract_line(img, area, x_cal, y_cal, color, xs=[0.0, 4.0, 8.0])
    # All columns have mean row 50, value = y_cal.value(50) = 50.0
    assert values == [50.0, 50.0, 50.0]


def test_load_image_p2_grayscale_to_rgb() -> None:
    # P2 image: 2x2 grayscale values 0, 64, 128, 255
    p2_data = b"P2\n2 2\n255\n0 64 128 255\n"
    img = load_image(p2_data)
    assert img.width == 2 and img.height == 2
    assert img.pixels == bytes([0, 0, 0, 64, 64, 64, 128, 128, 128, 255, 255, 255])


def test_load_image_p5_grayscale_to_rgb() -> None:
    p5_data = b"P5\n2 2\n255\n" + bytes([0, 64, 128, 255])
    img = load_image(p5_data)
    assert img.pixels == bytes([0, 0, 0, 64, 64, 64, 128, 128, 128, 255, 255, 255])


def test_load_image_comments() -> None:
    # Include comments in header
    p3_with_comments = (
        b"P3 # comment\n2 2\n255\n# another comment\n0 0 0 255 255 255 0 0 0 255 255 255\n"
    )
    img = load_image(p3_with_comments)
    assert img.width == 2 and img.height == 2
    # Check first pixel is black
    assert img.pixels[0:3] == b"\x00\x00\x00"


def test_even_width_bar_uses_lower_median_top() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (31, 119, 180)
    # Two-column bar whose topmost matching rows are 50 and 52.
    img = _draw_vertical_bar(img, 20, 20, 50, 89, color)
    img = _draw_vertical_bar(img, 21, 21, 52, 89, color)
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    bars = extract_bars(img, area, y_cal, color)
    assert bars == [Bar(left=20, right=21, value=y_cal.value(50))]


def test_gap_wider_than_max_gap_is_not_interpolated() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    color = (214, 39, 40)
    # Data only at columns 40 and 45: the gap between them is 4 columns.
    img = _set_pixel(img, 40, 60, color)
    img = _set_pixel(img, 45, 60, color)
    x_cal = Calibration.from_points((40, 0.0), (50, 10.0))
    y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
    # x=2.0 maps to column 42, inside the 4-column gap.
    values = extract_line(img, area, x_cal, y_cal, color, xs=[2.0], max_gap_px=3)
    assert values == [None]


def test_load_image_non_ascii_header() -> None:
    with pytest.raises(ChartError) as exc_info:
        load_image(b"P3\n1 \xff1\n255\n0 0 0")
    assert exc_info.value.code == "invalid_image"


def test_load_image_non_ascii_raster() -> None:
    with pytest.raises(ChartError) as exc_info:
        load_image(b"P3\n1 1\n255\n\xff 0 0")
    assert exc_info.value.code == "invalid_image"


def test_dominant_colors_ties() -> None:
    img = _make_white_image()
    area = (10, 10, 90, 90)
    # Create two colors with equal count, and more background
    color1 = (1, 0, 0)
    color2 = (0, 1, 0)
    # Draw 10 pixels of each
    for i in range(10):
        img = _set_pixel(img, 10 + i, 10, color1)
        img = _set_pixel(img, 20 + i, 10, color2)
    colors = dominant_colors(img, area)
    # Background is most frequent (white), then two colors tie with count 10
    # sorted by color tuple: (0,1,0) < (1,0,0)
    assert colors == [((0, 1, 0), 10), ((1, 0, 0), 10)]
