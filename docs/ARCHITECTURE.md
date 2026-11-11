# Architecture

## Purpose

`trysac-chart-to-data` is a small, dependency-free Python library that recovers numbers from raster bar and line chart images by pixel analysis. It parses PNM images, calibrates linear axes, finds vertical bars and line series by color inside a plot area, and counts dominant colors.

## Shape

```text
src/chart_to_data/__init__.py  -> re-exports the public names
src/chart_to_data/__main__.py  -> implementation and command line entry point
tests/test_chart_to_data.py    -> in-memory PNM tests
```

- **Public API**: the names in `__all__` of `src/chart_to_data/__init__.py`: `Bar`, `Calibration`, `ChartError`, `RgbImage`, `dominant_colors`, `extract_bars`, `extract_line`, `load_image` and `__version__`.
- **Implementation**: `src/chart_to_data/__main__.py` contains the frozen dataclasses, PNM parsing, color matching, bar and line extraction, dominant color counting and `main`.
- **Errors**: invalid input raises `ChartError` with a `code` and a message at most 200 characters. Library functions do not print or exit.
- **Side effects**: the library functions perform no file or network I/O and have no global mutable state. The module logger uses `logging.getLogger(__name__)` with a `NullHandler`.
- **Command line**: `main(argv)` reads exactly one local file path, parses the flags described in the README and prints CSV to stdout. It returns 0 when values were found, 1 when nothing was found and 2 for usage, IO or invalid image errors.

## Quality contract

`scripts/check.py` is the single definition of the gates; `fabrica.json` tells the factory and CI how to run it. See [TESTING.md](TESTING.md).

## Decisions

No numbered ADR files are present in the supplied tree. The module docstrings and this page describe the implemented design.
