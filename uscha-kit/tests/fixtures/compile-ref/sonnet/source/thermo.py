"""Celsius <-> Fahrenheit conversion.

Two pure functions, symmetric input validation, plain floats in and out.
"""

_NUMERIC_TYPES = (int, float)


def _reject_non_numeric(value, label):
    # bool is a subclass of int in Python; treat it as non-numeric on purpose
    # (see unresolved_intent) so True/False can't silently pass as 1/0.
    if isinstance(value, bool) or not isinstance(value, _NUMERIC_TYPES):
        raise TypeError(
            "{} must be an int or float, got {}".format(label, type(value).__name__)
        )


def celsius_to_fahrenheit(celsius):
    """Convert a Celsius temperature to Fahrenheit.

    Raises TypeError if celsius is not an int or float (bool included).
    """
    _reject_non_numeric(celsius, "celsius")
    return celsius * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(fahrenheit):
    """Convert a Fahrenheit temperature to Celsius.

    Raises TypeError if fahrenheit is not an int or float (bool included).
    """
    _reject_non_numeric(fahrenheit, "fahrenheit")
    return (fahrenheit - 32.0) * 5.0 / 9.0
