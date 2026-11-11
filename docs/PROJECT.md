# Project record

## Objective

Recover numbers from raster bar and line chart images by pixel analysis: linear axis calibration, series color matching, bar edges, line sampling and dominant colors.

## Scope

- In scope: PNM input (P2, P3, P5, P6 with maxval 255); linear axis calibration from two points; vertical bar extraction by color with a minimum width and negative-bar handling; line extraction by color at requested x values with limited interpolation; dominant exact color counting; a command line interface that prints CSV and returns documented exit codes.
- Out of scope: logarithmic or date axes, horizontal and stacked bars, pie charts, axis label OCR, PNG and JPEG decoding, and automatic calibration.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 955127 / 63261 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.0879 |

## Factory run u300 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-11 | generation | deepseek-v4-pro | yes | 2048 | 17479 | 0 | 3328 | 0.0360 |
| 2026-11-11 | fix-1 | deepseek-flash | no | 21717 | 7759 | 0 | 277248 | 0.0087 |
| 2026-11-11 | fix-2 | deepseek-flash | no | 13609 | 1491 | 0 | 97536 | 0.0032 |
| 2026-11-11 | audit | deepseek-flash | no | 21800 | 24010 | 0 | 322432 | 0.0186 |
| 2026-11-11 | fix-3 | deepseek-flash | no | 13979 | 3179 | 0 | 105984 | 0.0043 |
| 2026-11-11 | docs | deepseek-flash | no | 75190 | 9343 | 0 | 256 | 0.0169 |

Total: $0.0879. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
