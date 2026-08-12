import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "source"))

import pytest

from thermo import celsius_to_fahrenheit, fahrenheit_to_celsius

TOLERANCE = 1e-9


def test_freezing_point_celsius_to_fahrenheit():
    # AC-TC-01
    assert celsius_to_fahrenheit(0) == 32.0


def test_boiling_point_celsius_to_fahrenheit():
    # AC-TC-02
    assert celsius_to_fahrenheit(100) == 212.0


@pytest.mark.parametrize("celsius", [-40, 0, 37, 100, 212.5, -273.15])
def test_fahrenheit_to_celsius_is_inverse(celsius):
    # AC-TC-03
    fahrenheit = celsius_to_fahrenheit(celsius)
    assert abs(fahrenheit_to_celsius(fahrenheit) - celsius) < TOLERANCE


@pytest.mark.parametrize("bad_value", ["20", None, [20], {}, object()])
def test_celsius_to_fahrenheit_rejects_non_numeric(bad_value):
    # AC-TC-04
    with pytest.raises(TypeError):
        celsius_to_fahrenheit(bad_value)


@pytest.mark.parametrize("bad_value", ["68", None, [68], {}, object()])
def test_fahrenheit_to_celsius_rejects_non_numeric(bad_value):
    # AC-TC-04
    with pytest.raises(TypeError):
        fahrenheit_to_celsius(bad_value)


@pytest.mark.parametrize("celsius", [-459.67, -40, 0, 21.5, 100, 999.999])
def test_roundtrip_preserves_original_value(celsius):
    # INV-TC-ROUNDTRIP-01
    roundtripped = fahrenheit_to_celsius(celsius_to_fahrenheit(celsius))
    assert abs(roundtripped - celsius) < TOLERANCE
