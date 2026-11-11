# chart-to-data

[![PyPI version](https://img.shields.io/pypi/v/trysac-chart-to-data)](https://pypi.org/project/trysac-chart-to-data/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-chart-to-data)](LICENSE)
[![CI](https://github.com/Trysac/u300-chart-to-data/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u300-chart-to-data/actions/workflows/ci.yml)

Recover numbers from raster bar and line chart images by pixel analysis: linear axis calibration, series color matching, bar edges, line sampling and dominant colors

## Problem

Data often survives only as a chart image in a report or slide, and retyping it by hand is slow and error-prone, while vision models return plausible but unverifiable numbers. When the axis scale and series color are known, the values can be measured from pixels exactly and reproducibly. This library calibrates linear axes from two reference points, finds bars and line series by color inside the plot area and converts pixel positions back to data values.

## Install

```sh
pip install trysac-chart-to-data
# or
uv add trysac-chart-to-data
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

Input must be a PNM image (P2, P3, P5 or P6 with maxval 255). Convert PNG or JPEG files to PNM first; decoders for those formats are deliberately out of scope.

```python
from chart_to_data import Calibration, extract_bars, load_image

img = load_image(open("chart.ppm", "rb").read())
y_cal = Calibration.from_points((90, 0.0), (10, 100.0))
bars = extract_bars(img, (10, 10, 90, 90), y_cal, (31, 119, 180))
for bar in bars:
    print(bar.left, bar.right, bar.value)
```

### Public API

- `load_image(data: bytes, *, max_pixels: int = 25_000_000) -> RgbImage` parses P2, P3, P5 and P6 with maxval exactly 255. P2 and P5 are expanded to RGB by repeating the gray value. `RgbImage` is frozen with `width`, `height` and `pixels` (3 bytes per pixel, row-major, row 0 at top).
- `Calibration.from_points((pixel, value), (pixel, value)) -> Calibration` builds a linear axis. `value(pixel)` converts a pixel position to a data value; `pixel(value)` converts a data value to the nearest pixel using round half to even. Identical calibration pixels raise `ChartError` with code `invalid_calibration`.
- `extract_bars(img, area, y_cal, color, *, tolerance: int = 30, min_bar_width: int = 2) -> list[Bar]` finds vertical bars inside an inclusive `(left, top, right, bottom)` area. Bars are sorted by `left`. A bar at or below the zero row is negative and is measured at its bottom edge; otherwise it is measured at its top edge. `Bar` is frozen with `left`, `right` and `value`.
- `extract_line(img, area, x_cal, y_cal, color, *, xs: Sequence[float], tolerance: int = 30, max_gap_px: int = 3) -> list[float | None]` samples the mean row of matching pixels per column. A missing column is linearly interpolated from the nearest data columns on both sides when they are at most `max_gap_px` apart; otherwise the result is `None`.
- `dominant_colors(img, area, *, top: int = 5) -> list[tuple[tuple[int, int, int], int]]` counts exact colors inside the area, excludes the most frequent color (treated as background) and returns the next colors by count, with ties by color tuple.
- `ChartError` carries a machine-readable `code` in `unsupported_image`, `image_too_large`, `invalid_image`, `invalid_area`, `invalid_calibration` or `invalid_argument`, and truncates its message to 200 characters. Version: `chart_to_data.__version__ == '0.1.0'`.

Limits and options: areas must be inclusive and inside the image; `max_pixels` defaults to 25,000,000; `tolerance` must be non-negative; `min_bar_width` and `max_gap_px` must be at least 1; `top` must be at least 1. Numeric results are rounded to 6 decimal places.

### Command line

```sh
python -m chart_to_data chart.ppm --area 10,10,90,90 --y 90:0,10:100 --color 1f77b4 --bars
```

Bar mode prints the CSV header `left,right,value` followed by one line per bar. Line mode uses `--line --x 10:0,90:8 --xs 0,4,8` and prints the header `x,value`; missing values are printed as empty cells. The exit code is 0 when values were found, 1 when nothing was found and 2 for usage, IO or invalid image errors.

Out of scope: logarithmic or date axes, horizontal and stacked bars, pie charts, axis label OCR, PNG and JPEG decoding, and automatic calibration.

## Why not vision-model extraction

Vision-model extraction returns plausible numbers that cannot be traced to exact pixel positions and can change between runs. This utility has no model and no training data: the same image, area, calibration and color produce the same values, each derived from row and column coordinates.

## Documentation

- [Project record](docs/PROJECT.md): objective, scope and out-of-scope
- [Architecture](docs/ARCHITECTURE.md): package shape and public API
- [Security policy](docs/SECURITY.md): threat model and limits
- [Testing](docs/TESTING.md): test module and coverage
- [Stack](docs/STACK.md): tools used and discarded

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
