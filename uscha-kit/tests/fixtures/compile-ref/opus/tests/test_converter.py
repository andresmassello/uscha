"""Behavioral tests for the reference compilation (model: opus)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "source"))
from converter import celsius_to_fahrenheit, fahrenheit_to_celsius  # noqa: E402


def test_freezing_point():          # AC-TC-01
    assert celsius_to_fahrenheit(0) == 32.0


def test_boiling_point():           # AC-TC-02
    assert celsius_to_fahrenheit(100) == 212.0


def test_inverse():                 # AC-TC-03, INV-TC-ROUNDTRIP-01
    for c in (-40.0, 0.0, 37.0, 100.0):
        assert abs(fahrenheit_to_celsius(celsius_to_fahrenheit(c)) - c) < 1e-9


def test_non_numeric_raises():      # AC-TC-04
    with pytest.raises(TypeError):
        celsius_to_fahrenheit("hot")
    with pytest.raises(TypeError):
        fahrenheit_to_celsius(None)
