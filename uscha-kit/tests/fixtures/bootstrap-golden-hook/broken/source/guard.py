"""Deliberately broken guard fixture: always ALLOW. Fails every block case -- used only to
prove bootstrap-oracle's failure path (exit 1, names the divergences). NOT a compilation."""
import sys
def main():
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
