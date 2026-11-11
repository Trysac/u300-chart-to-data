"""
Recover numbers from raster bar and line chart images by pixel analysis: linear axis calibration,
series color matching, bar edges, line sampling and dominant colors
"""

from __future__ import annotations

from chart_to_data.__main__ import (
    Bar,
    Calibration,
    ChartError,
    RgbImage,
    dominant_colors,
    extract_bars,
    extract_line,
    load_image,
)

__all__ = [
    "Bar",
    "Calibration",
    "ChartError",
    "RgbImage",
    "__version__",
    "dominant_colors",
    "extract_bars",
    "extract_line",
    "load_image",
]

__version__ = "0.1.0"
