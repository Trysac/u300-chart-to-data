# Security notes

## Threat model

`trysac-chart-to-data` parses local PNM bytes and does pixel analysis. The library functions do not open files, use the network, evaluate code or deserialize objects. The command line interface reads exactly one file path supplied by the caller.

### Defended

- **Unsupported or malformed PNM input**: `load_image` accepts only P2, P3, P5 and P6 with maxval exactly 255. Unsupported magic or maxval raises `ChartError` with code `unsupported_image`; truncated, non-ASCII, out-of-range or inconsistent data raises `invalid_image`.
- **Oversized raster data**: `load_image` enforces `max_pixels`, default 25,000,000, and raises `image_too_large` before processing the raster.
- **Invalid plot areas and arguments**: `extract_bars`, `extract_line` and `dominant_colors` reject areas outside the image with `invalid_area`; negative `tolerance`, `min_bar_width` below 1, `max_gap_px` below 1 and `top` below 1 raise `invalid_argument`.
- **Invalid calibration**: `Calibration.from_points` rejects identical pixel coordinates with `invalid_calibration`.
- **Message size**: `ChartError` truncates messages to 200 characters.

### Not defended

- **PNG and JPEG decoding**: not provided. Callers must convert images to PNM first.
- **Hostile local image files**: the CLI opens the path it is given. Work is bounded by `max_pixels`, but a file within that limit can still consume proportional CPU and memory.
- **Semantic correctness**: color matching uses the requested RGB color and tolerance. Similar colors, anti-aliased pixels outside the tolerance or a wrong calibration will produce wrong values without an error.
- **Secrets and untrusted text**: the utility does not handle credentials, does not evaluate expressions and does not deserialize data. Error messages contain no secrets by design, but callers should still avoid passing sensitive text through `ChartError` messages.
- **Automatic calibration and label OCR**: not implemented, so axis values and series colors must be supplied by the caller.

## Publishing

Releases are published to PyPI with trusted publishing (OIDC) when available, never with a long-lived token stored in the repository.

To report a vulnerability, see [SECURITY.md](../SECURITY.md).
