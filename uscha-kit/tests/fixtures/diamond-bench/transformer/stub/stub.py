"""Degenerate transformer stub: always prints an empty array. Passes only the empty-input case;
proves the oracle DISCRIMINATES. NOT a compilation."""
import sys


def main():
    sys.stdin.read()
    print("[]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
