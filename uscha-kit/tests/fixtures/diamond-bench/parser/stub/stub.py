"""Degenerate parser stub: gives up on everything (always ERROR). Passes only the error cases;
proves the oracle DISCRIMINATES (a stub cannot score like a real evaluator). NOT a compilation."""
import sys


def main():
    sys.stdin.read()
    print("ERROR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
