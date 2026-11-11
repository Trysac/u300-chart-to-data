# Testing

## Running

```sh
uv run pytest --cov=chart_to_data   # tests with coverage report
uv run python scripts/check.py      # every gate, as CI and the factory run it
```

## Policy

- Tests exercise the public API (`import chart_to_data`) and assert return values, raised `ChartError` codes and command line output.
- Tests are deterministic: they build PNM images in memory and require no network, wall clock or fixture files.
- Each bug fix starts with a failing test that reproduces it.

## Tiers

There is one test tier in the supplied code: `tests/test_chart_to_data.py`, run locally and in CI. No external-tool conformance marker or download step is present in the supplied test module.

## Layout

`tests/test_chart_to_data.py` is the test module. It defines helpers `_make_p3`, `_make_p6`, `_make_white_image`, `_set_pixel` and `_draw_vertical_bar`, imports `Bar`, `Calibration`, `ChartError`, `RgbImage`, `dominant_colors`, `extract_bars`, `extract_line` and `load_image`, and contains `test_calibration_exact`. The suite covers linear calibration including `invalid_calibration`, bar extraction on synthetic images, line extraction including out-of-area samples and gaps, dominant color counting, PNM loading and error codes (`unsupported_image`, `image_too_large`, `invalid_image`, `invalid_area`), and command line output and exit codes.
