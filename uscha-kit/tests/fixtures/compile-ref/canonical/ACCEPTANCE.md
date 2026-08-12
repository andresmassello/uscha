# ACCEPTANCE — temperature converter (Diamond M3 compiler-contract reference fixture)

A deliberately tiny, public canonical package. Its `ir-extract` output is the reference IR
that the M3 reference compilations target. Kept minimal on purpose: M3 proves the CONTRACT,
not a real system (that is M4).

- [ ] AC-TC-01 celsius_to_fahrenheit(0) returns 32.0
- [ ] AC-TC-02 celsius_to_fahrenheit(100) returns 212.0
- [ ] AC-TC-03 fahrenheit_to_celsius is the inverse of celsius_to_fahrenheit within 1e-9
- [ ] AC-TC-04 a non-numeric input to either function raises TypeError
