# chart-to-data

[![PyPI version](https://img.shields.io/pypi/v/trysac-chart-to-data)](https://pypi.org/project/trysac-chart-to-data/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-chart-to-data)](LICENSE)
[![CI](https://github.com/Trysac/u300-chart-to-data/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u300-chart-to-data/actions/workflows/ci.yml)

Recover numbers from raster bar and line chart images by pixel analysis: linear axis calibration, series color matching, bar edges, line sampling and dominant colors

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-chart-to-data
# or
uv add trysac-chart-to-data
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import chart_to_data

# normalize() trims surrounding whitespace and lower-cases the text.
print(chart_to_data.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    chart_to_data.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
