"""Recover numeric data from raster bar and line chart images.

This module provides exact, reproducible extraction of values from chart
images when the axis calibration and series color are known. It parses PNM
images, calibrates linear axes, finds vertical bars and line series by color
inside a plot area, and counts dominant colors.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "Bar",
    "Calibration",
    "ChartError",
    "RgbImage",
    "dominant_colors",
    "extract_bars",
    "extract_line",
    "load_image",
]

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _median_low(values: list[int]) -> int:
    """Return the lower median of a non-empty list of ints."""
    sorted_values = sorted(values)
    return sorted_values[(len(sorted_values) - 1) // 2]


def _round6(value: float) -> float:
    """Round a float to 6 decimal places."""
    return round(value, 6)


class ChartError(Exception):
    """Base error for all chart extraction failures.

    Attributes:
        code: Machine-readable error code.
        message: Human-readable description (max 200 chars, no secrets).
    """

    def __init__(
        self,
        code: Literal[
            "unsupported_image",
            "image_too_large",
            "invalid_image",
            "invalid_area",
            "invalid_calibration",
            "invalid_argument",
        ],
        message: str,
    ) -> None:
        truncated = message[:200]
        super().__init__(truncated)
        self.code = code
        self.message = truncated


@dataclass(frozen=True)
class RgbImage:
    """Frozen representation of an RGB image.

    Attributes:
        width: Image width in pixels.
        height: Image height in pixels.
        pixels: Raw RGB bytes, 3 bytes per pixel, row-major, row 0 at top.
    """

    width: int
    height: int
    pixels: bytes

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ChartError("invalid_image", "Image dimensions must be positive")
        expected_len = self.width * self.height * 3
        if len(self.pixels) != expected_len:
            raise ChartError(
                "invalid_image",
                f"Pixel data length {len(self.pixels)} does not match dimensions "
                f"({self.width}x{self.height}x3={expected_len})",
            )


@dataclass(frozen=True)
class Calibration:
    """Linear calibration between pixel coordinates and data values.

    Created from two points (pixel, value) that define a straight line.
    """

    p1: float
    v1: float
    p2: float
    v2: float

    @classmethod
    def from_points(cls, p1: tuple[int, float], p2: tuple[int, float]) -> Calibration:
        """Create a calibration from two points.

        Args:
            p1: First point as (pixel, value).
            p2: Second point as (pixel, value).

        Returns:
            A Calibration instance.

        Raises:
            ChartError: If the two pixels are identical (code
                'invalid_calibration').
        """
        (pix1, val1), (pix2, val2) = p1, p2
        if pix1 == pix2:
            raise ChartError(
                "invalid_calibration",
                f"Calibration pixels must differ, got {pix1} and {pix2}",
            )
        return cls(p1=float(pix1), v1=float(val1), p2=float(pix2), v2=float(val2))

    def value(self, pixel: float) -> float:
        """Convert a pixel position to a data value."""
        return self.v1 + (pixel - self.p1) * (self.v2 - self.v1) / (self.p2 - self.p1)

    def pixel(self, value: float) -> int:
        """Convert a data value to the nearest pixel position (round half to even)."""
        raw = self.p1 + (value - self.v1) * (self.p2 - self.p1) / (self.v2 - self.v1)
        # Python's round() uses banker's rounding (half to even)
        return round(raw)


@dataclass(frozen=True)
class Bar:
    """Represents a vertical bar found in the chart.

    Attributes:
        left: Leftmost pixel column of the bar (inclusive).
        right: Rightmost pixel column of the bar (inclusive).
        value: Data value corresponding to the top edge (or bottom edge for
            negative bars).
    """

    left: int
    right: int
    value: float


def _parse_pnm_header(data: bytes) -> tuple[str, int, int, bytes]:
    """Parse PNM header and return (magic, width, height, remainder bytes)."""
    idx = 0
    n = len(data)

    def skip_whitespace_and_comments() -> None:
        nonlocal idx
        while idx < n:
            c = data[idx]
            if c in b" \t\r\n":
                idx += 1
            elif c == ord("#"):
                # skip to end of line
                while idx < n and data[idx] not in b"\r\n":
                    idx += 1
            else:
                break

    def read_token() -> str:
        nonlocal idx
        skip_whitespace_and_comments()
        start = idx
        while idx < n and data[idx] not in b" \t\r\n#":
            idx += 1
        if start == idx:
            raise ChartError("invalid_image", "Unexpected end of header")
        try:
            return data[start:idx].decode("ascii")
        except UnicodeDecodeError as err:
            raise ChartError("invalid_image", "Non-ASCII byte in PNM header") from err

    magic = read_token()
    if magic not in ("P2", "P3", "P5", "P6"):
        raise ChartError("unsupported_image", f"Unsupported PNM magic {magic!r}")

    width_token = read_token()
    height_token = read_token()
    try:
        width = int(width_token)
        height = int(height_token)
    except ValueError as err:
        raise ChartError("invalid_image", "Invalid width or height in PNM header") from err

    maxval_token = read_token()
    try:
        maxval = int(maxval_token)
    except ValueError as err:
        raise ChartError("invalid_image", "Invalid maxval in PNM header") from err

    if maxval != 255:
        raise ChartError(
            "unsupported_image",
            f"Maxval {maxval} not supported, only 255 is allowed",
        )

    # After maxval, there must be a single whitespace character (or comment) before
    # raster data.
    if idx >= n:
        raise ChartError("invalid_image", "Missing raster data")
    # For ASCII formats, we need to skip exactly one whitespace; for binary, there
    # may be a single whitespace that we should skip.
    if data[idx] in b" \t\r\n":
        idx += 1
    elif data[idx] == ord("#"):
        # a comment is allowed here as well, skip to end of line
        while idx < n and data[idx] not in b"\r\n":
            idx += 1
        if idx < n:
            idx += 1  # skip newline
    else:
        raise ChartError("invalid_image", "Missing whitespace after header")

    return magic, width, height, data[idx:]


def load_image(data: bytes, *, max_pixels: int = 25_000_000) -> RgbImage:
    """Load a PNM image from bytes.

    Supports P2 (grayscale ASCII), P3 (RGB ASCII), P5 (grayscale binary),
    P6 (RGB binary) with maxval exactly 255. P2/P5 are expanded to RGB by
    replicating the gray value.

    Args:
        data: Raw PNM image bytes.
        max_pixels: Maximum allowed width*height. Defaults to 25,000,000.

    Returns:
        An RgbImage instance.

    Raises:
        ChartError: With code 'unsupported_image' for unsupported magic or
            maxval, 'image_too_large' if pixel count exceeds max_pixels,
            'invalid_image' for malformed or truncated data.
    """
    magic, width, height, raster = _parse_pnm_header(data)
    total_pixels = width * height
    if total_pixels > max_pixels:
        raise ChartError(
            "image_too_large",
            f"Image has {total_pixels} pixels, exceeding limit {max_pixels}",
        )

    if magic in ("P5", "P6"):
        channels = 1 if magic == "P5" else 3
        expected_bytes = total_pixels * channels
        if len(raster) < expected_bytes:
            raise ChartError("invalid_image", "Truncated raster data")
        pixel_data = raster[:expected_bytes]
        if channels == 1:
            # Expand grayscale to RGB
            rgb_bytes = bytearray()
            for gray in pixel_data:
                rgb_bytes.extend([gray, gray, gray])
            return RgbImage(width=width, height=height, pixels=bytes(rgb_bytes))
        else:
            return RgbImage(width=width, height=height, pixels=pixel_data)
    else:
        # ASCII formats P2 and P3
        channels = 1 if magic == "P2" else 3
        tokens = []
        idx = 0
        n = len(raster)
        while idx < n:
            # skip whitespace and comments
            while idx < n and raster[idx] in b" \t\r\n":
                idx += 1
            if idx < n and raster[idx] == ord("#"):
                while idx < n and raster[idx] not in b"\r\n":
                    idx += 1
                continue
            start = idx
            while idx < n and raster[idx] not in b" \t\r\n#":
                idx += 1
            if start == idx:
                break
            try:
                token_str = raster[start:idx].decode("ascii")
            except UnicodeDecodeError as err:
                raise ChartError("invalid_image", "Non-ASCII byte in ASCII data") from err
            try:
                value = int(token_str)
            except ValueError as err:
                raise ChartError("invalid_image", "Invalid pixel value in ASCII data") from err
            if value < 0 or value > 255:
                raise ChartError("invalid_image", "Pixel value out of range 0-255")
            tokens.append(value)
        expected_count = total_pixels * channels
        if len(tokens) != expected_count:
            raise ChartError(
                "invalid_image",
                f"Expected {expected_count} pixel values, got {len(tokens)}",
            )
        if channels == 1:
            rgb_bytes = bytearray()
            for gray in tokens:
                rgb_bytes.extend([gray, gray, gray])
            return RgbImage(width=width, height=height, pixels=bytes(rgb_bytes))
        else:
            rgb_bytes = bytearray()
            for i in range(0, len(tokens), 3):
                r, g, b = tokens[i], tokens[i + 1], tokens[i + 2]
                rgb_bytes.extend([r, g, b])
            return RgbImage(width=width, height=height, pixels=bytes(rgb_bytes))


def _validate_area(img: RgbImage, area: tuple[int, int, int, int]) -> None:
    """Validate that area is inside image bounds and non-empty."""
    left, top, right, bottom = area
    if not (0 <= left <= right < img.width and 0 <= top <= bottom < img.height):
        raise ChartError(
            "invalid_area",
            f"Area {area} outside image bounds {img.width}x{img.height}",
        )


def _color_match(
    img: RgbImage, x: int, y: int, color: tuple[int, int, int], tolerance: int
) -> bool:
    """Return True if pixel at (x,y) matches color within tolerance."""
    idx = (y * img.width + x) * 3
    r = img.pixels[idx]
    g = img.pixels[idx + 1]
    b = img.pixels[idx + 2]
    return (
        abs(r - color[0]) <= tolerance
        and abs(g - color[1]) <= tolerance
        and abs(b - color[2]) <= tolerance
    )


def extract_bars(
    img: RgbImage,
    area: tuple[int, int, int, int],
    y_cal: Calibration,
    color: tuple[int, int, int],
    *,
    tolerance: int = 30,
    min_bar_width: int = 2,
) -> list[Bar]:
    """Extract vertical bars from a plot area by color matching.

    Consecutive columns within the area that contain at least one matching
    pixel form a candidate run. Runs of length at least min_bar_width are
    considered bars. For each bar, the top row is the median (lower median)
    of the topmost matching row per column, and the bottom row is the median
    of the bottommost matching row per column. The zero data value is mapped
    to a pixel row via y_cal.pixel(0.0). If the bar's top edge is at or below
    the zero row, the bar is negative and its value is y_cal.value(bottom+1),
    otherwise the value is y_cal.value(top).

    Args:
        img: The RGB image.
        area: Plot area as (left, top, right, bottom) inclusive.
        y_cal: Calibration for the y-axis.
        color: The RGB color of the bars.
        tolerance: Maximum per-channel difference for color matching.
        min_bar_width: Minimum width in pixels for a bar.

    Returns:
        List of Bar objects sorted by left column.

    Raises:
        ChartError: If area is invalid, tolerance negative, or min_bar_width < 1.
    """
    if tolerance < 0:
        raise ChartError("invalid_argument", "tolerance must be non-negative")
    if min_bar_width < 1:
        raise ChartError("invalid_argument", "min_bar_width must be at least 1")
    _validate_area(img, area)
    left, top, right, bottom = area

    zero_row = y_cal.pixel(0.0)

    bars: list[Bar] = []
    col = left
    while col <= right:
        # Find start of a run (column with matches)
        if not any(_color_match(img, col, row, color, tolerance) for row in range(top, bottom + 1)):
            col += 1
            continue
        run_start = col
        top_rows: list[int] = []
        bottom_rows: list[int] = []
        while col <= right and any(
            _color_match(img, col, row, color, tolerance) for row in range(top, bottom + 1)
        ):
            # Find topmost and bottommost matching rows in this column
            topmost = None
            bottommost = None
            for row in range(top, bottom + 1):
                if _color_match(img, col, row, color, tolerance):
                    if topmost is None:
                        topmost = row
                    bottommost = row
            if topmost is not None and bottommost is not None:
                top_rows.append(topmost)
                bottom_rows.append(bottommost)
            col += 1
        run_end = col - 1
        run_width = run_end - run_start + 1
        if run_width >= min_bar_width:
            median_top = _median_low(top_rows)
            median_bottom = _median_low(bottom_rows)
            if median_top >= zero_row:
                # negative bar: measure at bottom edge
                value = y_cal.value(median_bottom + 1)
            else:
                value = y_cal.value(median_top)
            bars.append(Bar(left=run_start, right=run_end, value=_round6(value)))
        # continue after run
    bars.sort(key=lambda b: b.left)
    return bars


def extract_line(
    img: RgbImage,
    area: tuple[int, int, int, int],
    x_cal: Calibration,
    y_cal: Calibration,
    color: tuple[int, int, int],
    *,
    xs: Sequence[float],
    tolerance: int = 30,
    max_gap_px: int = 3,
) -> list[float | None]:
    """Extract y-values of a line series at given x positions.

    For each column in the area, the mean row of all matching pixels is
    computed. For each requested x, the corresponding column is
    x_cal.pixel(x). If that column is outside the area, the result is None.
    If the column has data, the y-value is y_cal.value(mean_row). If the
    column has no data, the nearest data columns on both sides within
    max_gap_px are used for linear interpolation; if either side is missing
    or farther, the result is None. Values are rounded to 6 decimal places.

    Args:
        img: The RGB image.
        area: Plot area as (left, top, right, bottom) inclusive.
        x_cal: Calibration for the x-axis.
        y_cal: Calibration for the y-axis.
        color: The RGB color of the line.
        xs: Sequence of x data values to sample.
        tolerance: Maximum per-channel difference for color matching.
        max_gap_px: Maximum gap in pixels between two data columns to allow
            interpolation.

    Returns:
        List of y-values (or None) in the same order as xs.

    Raises:
        ChartError: If area is invalid, tolerance negative, or max_gap_px < 1.
    """
    if tolerance < 0:
        raise ChartError("invalid_argument", "tolerance must be non-negative")
    if max_gap_px < 1:
        raise ChartError("invalid_argument", "max_gap_px must be at least 1")
    _validate_area(img, area)
    left, top, right, bottom = area

    # Precompute mean row per column (None if no data)
    column_means: dict[int, float] = {}
    for col in range(left, right + 1):
        rows = [
            row for row in range(top, bottom + 1) if _color_match(img, col, row, color, tolerance)
        ]
        if rows:
            column_means[col] = sum(rows) / len(rows)

    results: list[float | None] = []
    for x in xs:
        col = x_cal.pixel(x)
        if col < left or col > right:
            results.append(None)
            continue
        if col in column_means:
            results.append(_round6(y_cal.value(column_means[col])))
        else:
            # Find nearest data columns left and right within max_gap_px
            left_col = None
            for c in range(col - 1, col - max_gap_px - 1, -1):
                if c in column_means:
                    left_col = c
                    break
            right_col = None
            for c in range(col + 1, col + max_gap_px + 1):
                if c in column_means:
                    right_col = c
                    break
            if (
                left_col is not None
                and right_col is not None
                and right_col - left_col - 1 <= max_gap_px
            ):
                # Interpolate y values
                left_mean = column_means[left_col]
                right_mean = column_means[right_col]
                left_y = y_cal.value(left_mean)
                right_y = y_cal.value(right_mean)
                # Linear interpolation in column space
                if right_col != left_col:
                    t = (col - left_col) / (right_col - left_col)
                    interpolated_y = left_y + t * (right_y - left_y)
                else:
                    interpolated_y = left_y
                results.append(_round6(interpolated_y))
            else:
                results.append(None)
    return results


def dominant_colors(
    img: RgbImage,
    area: tuple[int, int, int, int],
    *,
    top: int = 5,
) -> list[tuple[tuple[int, int, int], int]]:
    """Count exact colors inside the area and return the most common ones.

    The most frequent color (presumed to be the background) is excluded.
    Ties are broken by the color tuple for deterministic output.

    Args:
        img: The RGB image.
        area: Plot area as (left, top, right, bottom) inclusive.
        top: Number of colors to return (after excluding background).

    Returns:
        List of (color, count) tuples sorted by count descending, then by
        color tuple ascending.

    Raises:
        ChartError: If area is invalid or top < 1.
    """
    if top < 1:
        raise ChartError("invalid_argument", "top must be at least 1")
    _validate_area(img, area)
    left, top_row, right, bottom = area
    counts: dict[tuple[int, int, int], int] = {}
    for y in range(top_row, bottom + 1):
        for x in range(left, right + 1):
            idx = (y * img.width + x) * 3
            color = (
                img.pixels[idx],
                img.pixels[idx + 1],
                img.pixels[idx + 2],
            )
            counts[color] = counts.get(color, 0) + 1
    if not counts:
        return []
    # Exclude most frequent (background)
    max_count = max(counts.values())
    filtered = [(c, n) for c, n in counts.items() if n != max_count]
    # Sort by count descending, then by color tuple
    filtered.sort(key=lambda item: (-item[1], item[0]))
    return filtered[:top]


def _parse_points(text: str) -> tuple[tuple[int, float], tuple[int, float]]:
    """Parse a ``pixel:value,pixel:value`` calibration string."""
    parts = text.split(",")
    if len(parts) != 2:
        raise ValueError("expected two calibration points")
    points: list[tuple[int, float]] = []
    for part in parts:
        bits = part.split(":")
        if len(bits) != 2:
            raise ValueError("expected pixel:value pairs")
        points.append((int(bits[0]), float(bits[1])))
    return points[0], points[1]


def _parse_color(text: str) -> tuple[int, int, int]:
    """Parse a ``rrggbb`` hex color string."""
    if len(text) != 6:
        raise ValueError("color must have 6 hex digits")
    try:
        return (
            int(text[0:2], 16),
            int(text[2:4], 16),
            int(text[4:6], 16),
        )
    except ValueError as err:
        raise ValueError("invalid hex color") from err


def main(argv: list[str] | None = None) -> int:
    """Run the chart-to-data command line interface.

    Args:
        argv: Argument list without the program name. Defaults to
            ``sys.argv[1:]``.

    Returns:
        Exit code: 0 when values were found, 1 when nothing was found,
        2 for usage, IO or invalid image errors.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        return 2
    path = args[0]
    area: tuple[int, int, int, int] | None = None
    y_text: str | None = None
    x_text: str | None = None
    color_text: str | None = None
    xs_text: str | None = None
    mode: str | None = None

    index = 1
    while index < len(args):
        argument = args[index]
        if argument == "--bars":
            mode = "bars"
            index += 1
        elif argument == "--line":
            mode = "line"
            index += 1
        elif argument in ("--area", "--y", "--x", "--color", "--xs"):
            if index + 1 >= len(args):
                return 2
            value = args[index + 1]
            if argument == "--area":
                try:
                    area_bits = [int(bit) for bit in value.split(",")]
                except ValueError:
                    return 2
                if len(area_bits) != 4:
                    return 2
                area = (area_bits[0], area_bits[1], area_bits[2], area_bits[3])
            elif argument == "--y":
                y_text = value
            elif argument == "--x":
                x_text = value
            elif argument == "--color":
                color_text = value
            else:
                xs_text = value
            index += 2
        else:
            return 2

    if area is None or y_text is None or color_text is None or mode is None:
        return 2

    try:
        y_cal = Calibration.from_points(*_parse_points(y_text))
        color = _parse_color(color_text)
    except (ValueError, ChartError):
        return 2

    x_cal: Calibration | None = None
    xs_values: list[float] = []
    if mode == "line":
        if x_text is None or xs_text is None:
            return 2
        try:
            x_cal = Calibration.from_points(*_parse_points(x_text))
            xs_values = [float(value) for value in xs_text.split(",")]
        except (ValueError, ChartError):
            return 2

    try:
        with open(path, "rb") as handle:
            data = handle.read()
    except OSError:
        return 2

    try:
        img = load_image(data)
    except ChartError:
        return 2

    if mode == "bars":
        try:
            found_bars = extract_bars(img, area, y_cal, color)
        except ChartError:
            return 2
        if not found_bars:
            return 1
        print("left,right,value")
        for bar in found_bars:
            print(f"{bar.left},{bar.right},{bar.value}")
        return 0

    if x_cal is None:
        return 2
    try:
        values = extract_line(
            img,
            area,
            x_cal,
            y_cal,
            color,
            xs=xs_values,
        )
    except ChartError:
        return 2
    if all(value is None for value in values):
        return 1
    print("x,value")
    for x_value, y_value in zip(xs_values, values, strict=True):
        cell = "" if y_value is None else str(y_value)
        print(f"{x_value},{cell}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
