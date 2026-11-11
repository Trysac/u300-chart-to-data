# Exact pixel analysis over vision models

Status: accepted (generated, pending human review)

## Context

The task requires recovering numeric values from chart images when the axis scale and series color are known. Vision models provide plausible but unverifiable numbers; exact pixel analysis is reproducible and traceable.

## Decision

Implement deterministic pixel analysis: parse PNM images, calibrate linear axes from two points, extract bars and lines by color matching with tolerance, and count dominant colors. Use median statistics for edge detection and linear interpolation for gaps.

## Consequences

Values are exact and reproducible, but the approach is limited to linear axes, vertical bars, line series, and PNM images (PNG/JPEG must be converted first). Calibration must be supplied manually. Error handling is strict with typed codes.
