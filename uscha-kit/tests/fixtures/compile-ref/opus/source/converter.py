"""Temperature converter — reference compilation (model: opus).

Compiled from the M3 reference IR (temperature converter canonical package). Each public
function traces to the acceptance/invariant nodes it implements; see COMPILATION.json.
"""


def celsius_to_fahrenheit(celsius):
    """C -> F. Implements AC-TC-01, AC-TC-02, AC-TC-04."""
    if isinstance(celsius, bool) or not isinstance(celsius, (int, float)):
        raise TypeError("celsius must be a number")
    return celsius * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(fahrenheit):
    """F -> C, the inverse of celsius_to_fahrenheit. Implements AC-TC-03, AC-TC-04,
    INV-TC-ROUNDTRIP-01."""
    if isinstance(fahrenheit, bool) or not isinstance(fahrenheit, (int, float)):
        raise TypeError("fahrenheit must be a number")
    return (fahrenheit - 32.0) * 5.0 / 9.0
