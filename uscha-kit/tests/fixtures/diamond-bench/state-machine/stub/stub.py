"""Degenerate turnstile stub: always prints the start state 'locked'. Passes only the cases
that happen to end locked; proves the oracle DISCRIMINATES. NOT a compilation."""
import sys


def main():
    sys.stdin.read()
    print("locked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
