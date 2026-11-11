"""Behavior tests for the public API of chart_to_data."""

from __future__ import annotations

import pytest

import chart_to_data


def test_normalize_trims_and_lowercases() -> None:
    assert chart_to_data.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        chart_to_data.normalize(value)


def test_version_is_semver() -> None:
    parts = chart_to_data.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
