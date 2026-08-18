#!/usr/bin/env python3
"""
uscha_top.py — the terminal projection of the QA ledger (`uscha top`, ADR-031/034).

It DERIVES NOTHING. Every state, cardinality, median and percentage on screen is read from
one read-only engine call, `qa_ledger.py top --json` (ADR-032), and `render()` is a pure
function of that object: same JSON + same size -> byte-identical lines, no clock, no files,
no subprocess, no environment. That purity is what lets the golden frames under
tests/fixtures/uscha-top/golden/ be the oracle: a renderer that quietly shows 100% while a
criterion is unmeasured fails a snapshot, not a code review (ADR-034).

Truth-pass (INV-TOP-05): a field the engine emits as null renders as an em dash, never as a
zero and never as a guess. In v0.1 that is ETA, every AGE, drift, and the trace column --
each with its deferred wiring recorded in ADR-035.

M1 scope: the read-only BOARD. The live feed (M2) and VERDICTS mode (M3) are not wired; the
panes that will hold them are labelled as such rather than faked.

Stdlib only. Python 3.8+. Runnable directly or via `python -m uscha_top`.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

DEFAULT_LEDGER = "QA-LEDGER.json"
FALLBACK_SIZE = (100, 32)

# Lines the board always spends on chrome: the title, 3 rules, 4 KPI lines, the table
# header, the feed label and the key hint. Everything else is table rows + feed.
CHROME_LINES = 11
FEED_MAX = 3
BURNUP_MAX = 24

# ANSI SGR by obligation state. TRACED and TAGGED deliberately share the UNMEASURED gray:
# the v0.1 engine has no source for either rung (ADR-032), so they must read as "not
# measured", never as PASS (INV-TOP-02, AC-T-08).
PALETTE = {
    "MEASURED_PASS": "32",
    "MEASURED_FAIL": "31",
    "QUARANTINE": "33",
    "UNMEASURED": "90",
    "TRACED": "90",
    "TAGGED": "90",
}
RESET = "\x1b[0m"
DASH = "—"          # the honest "no source" marker (INV-TOP-05)
MID = "·"
RULE = "─"
BLOCKS = "▁▂▃▄▅▆▇█"

# What the reader is expected to DO about a row. Presentation, not a KPI: no number here.
ACTIONS = {
    "MEASURED_PASS": DASH,
    "MEASURED_FAIL": "machine: fix, then rerun",
    "QUARANTINE": "you: record a verdict",
    "UNMEASURED": "you: tag a test",
    "TRACED": "you: tag a test",
    "TAGGED": "machine: run the case",
}


# --------------------------------------------------------------------------- #
# pure rendering                                                              #
# --------------------------------------------------------------------------- #
def _fit(text, cols):
    """One line, never wider than the terminal. Wrapping would break the frame's row
    accounting, so an over-long line is cut and marked."""
    if cols <= 0:
        return ""
    if len(text) <= cols:
        return text
    return text[:cols - 1] + "…" if cols > 1 else text[:cols]


def _spread(left, right, cols):
    """left ... right on one line, right-aligned, degrading to just `left` when tight."""
    if len(left) + len(right) + 1 > cols:
        return _fit(left, cols)
    return left + " " * (cols - len(left) - len(right)) + right


def _num(value):
    """A number the engine emitted, or the em dash when it emitted null."""
    return DASH if value is None else str(value)


def _pct_line(terminado):
    """INV-TOP-01: the DONE bar carries an explicit `N unmeasured` suffix whenever anything
    is unmeasured, and the engine has already capped the percentage below 100 while any
    obligation sits outside MEASURED_PASS -- the renderer republishes that fact, it never
    recomputes it (AC-T-01, AC-T-04, AC-T-23)."""
    done = terminado.get("done")
    total = terminado.get("total")
    pct = terminado.get("pct")
    unm = terminado.get("unmeasured") or 0
    line = "DONE %s/%s (%s%%)" % (_num(done), _num(total), _num(pct))
    if unm:
        line += " %s %d unmeasured" % (MID, unm)
    return line


def _burnup_line(burnup, cols):
    """The score trend, labelled as a score trend. v0.1 has no obligation-count history
    (ADR-035/2), so calling this a burn-up of closed obligations would be a lie the label
    exists to prevent."""
    points = [p for p in (burnup or {}).get("weeks") or [] if isinstance(p, (int, float))]
    label = "score trend  "
    note = "  (readiness score, not closed obligations)"
    if not points:
        return label + DASH + "  (no `readiness --record` history yet)"
    room = max(4, min(BURNUP_MAX, cols - len(label) - len(note)))
    bars = "".join(BLOCKS[min(len(BLOCKS) - 1, max(0, int(p) * len(BLOCKS) // 101))]
                   for p in points[-room:])
    return label + bars + note


def _spec_pin_text(spec_pin):
    """git HEAD, labelled for what it is. There is no pinned-spec concept in the engine yet
    (ADR-035/4): an unverified sha must SAY it is unverified, and a non-git tree shows the
    em dash rather than a fabricated pin (AC-T-06, INV-TOP-05)."""
    if not spec_pin or not spec_pin.get("sha"):
        return "spec_pin " + DASH
    mark = ("clean-room verified" if spec_pin.get("clean_room_verified")
            else "not clean-room verified")
    return "spec_pin %s (%s)" % (spec_pin["sha"], mark)


def _cases_text(ob):
    total = ob.get("cases_total") or 0
    if not total:
        return DASH               # no ingested case names this criterion: no count to show
    return "%s/%s" % (_num(ob.get("cases_pass")), total)


def _row(ob, selected):
    gutter = "> " if selected else "  "
    return "%s%-8s%-9s%-15s%7s%5s  %s" % (
        gutter, str(ob.get("id") or "?")[:8], str(ob.get("gate") or DASH)[:8],
        str(ob.get("state") or "?")[:14], _cases_text(ob),
        _num(ob.get("age_hours")), ACTIONS.get(ob.get("state"), DASH))


def _colorize(line, state):
    code = PALETTE.get(state)
    if not code or state not in line:
        return line
    return line.replace(state, "\x1b[%sm%s%s" % (code, state, RESET), 1)


def render(state, size, sel=0, plain=True):
    """The whole board as a list of exactly `rows` lines, none wider than `cols`.

    PURE (ADR-034): no I/O, no clock, no randomness, no environment. `state` is the parsed
    `qa_ledger.py top --json` object; `size` is (cols, rows); `sel` is the highlighted row.
    plain=True emits no escape sequences at all -- the mode `--once`, CI and the golden
    frames use, so a snapshot compares text and not terminal control codes.
    """
    cols, rows = size
    cols = max(20, int(cols))
    rows = max(CHROME_LINES + 1, int(rows))
    obligations = state.get("obligations") or []
    terminado = state.get("terminado") or {}
    debtors = state.get("debtors") or {}
    honesty = state.get("honesty") or {}

    out = []
    out.append(_spread("uscha top %s %s" % (MID, state.get("project") or "(unnamed project)"),
                       "step #%s" % _num(state.get("step")), cols))
    out.append(RULE * cols)
    out.append(_pct_line(terminado))
    out.append("machine owes %s %s you owe %s %s untagged %s %s ETA %s"
               % (_num(debtors.get("machine")), MID, _num(debtors.get("you")), MID,
                  _num(debtors.get("untagged")), MID, _num(state.get("eta_min"))))
    # honesty travels BESIDE done on purpose (INV-TOP-04): a thin denominator has to be
    # visible at the same glance as the number it flatters.
    out.append("honesty %s/%s (%s%%) measured %s %s"
               % (_num(honesty.get("measured")), _num(honesty.get("total")),
                  _num(honesty.get("pct")), MID, _spec_pin_text(state.get("spec_pin"))))
    out.append(_burnup_line(state.get("burnup"), cols))
    out.append(RULE * cols)
    out.append("  %-8s%-9s%-15s%7s%5s  %s"
               % ("ID", "GATE", "STATE", "CASES", "AGE", "ACTION"))

    # Budget: the table is served FIRST and the feed gets only what is left over, so a short
    # terminal shortens the feed and never the board (AC-T-21).
    avail = rows - CHROME_LINES
    want = len(obligations) or 1
    feed_n = min(FEED_MAX, max(0, avail - want))
    table_n = max(1, min(want, avail - feed_n))
    body = table_n - 1 if len(obligations) > table_n else table_n
    body = max(1, body)
    top = 0
    if sel >= body:
        top = min(sel - body + 1, max(0, len(obligations) - body))
    top = max(0, top)

    table = []
    for i, ob in enumerate(obligations[top:top + body], start=top):
        line = _fit(_row(ob, i == sel), cols)
        table.append(line if plain else _colorize(line, ob.get("state")))
    hidden = len(obligations) - len(table)
    if hidden > 0:
        table.append(_fit("  %s %d more obligation(s) not shown (j/k to move)"
                          % (DASH, hidden), cols))
    if not obligations:
        table.append(_fit("  no tagged criterion in the acceptance file "
                          "(nothing to measure yet)", cols))
    out.extend(table[:max(1, table_n)])

    pad = avail - len(table[:max(1, table_n)]) - feed_n
    out.extend([""] * max(0, pad))
    out.append(RULE * cols)
    events = state.get("events_tail") or []
    out.append("feed %s the live event tail is M2; nothing is invented here" % MID)
    for i in range(feed_n):
        if i < len(events):
            ev = events[i]
            out.append(_fit("  %s  %s" % (ev.get("ts") or DASH, ev.get("text") or ""), cols))
        else:
            out.append("")
    out.append("[j/k] move %s [r] reload %s [q] quit %s [v] verdicts (M3) %s "
               "[d]/[o] phase 2" % (MID, MID, MID, MID))
    out = [_fit(line, cols) for line in out]
    # exactly `rows` lines: a frame that drifts in height is a frame no snapshot can pin
    out = out[:rows] + [""] * max(0, rows - len(out))
    return out


# --------------------------------------------------------------------------- #
# state loading (the ONE read boundary -- it shells out, it never re-derives)  #
# --------------------------------------------------------------------------- #
def engine_path():
    """qa_ledger.py inside this kit, in either skill-tree layout -- the same both-layouts
    resolution `install-uscha.py` uses for the mirador renderer."""
    here = os.path.dirname(os.path.realpath(__file__))
    local = os.path.join(here, "qa_ledger.py")
    if os.path.isfile(local):
        return local
    kit = os.path.realpath(os.path.join(here, "..", "..", ".."))
    for rel in (("skills", "uscha-devloop", "qa_ledger.py"),
                (".claude", "skills", "uscha-devloop", "qa_ledger.py")):
        cand = os.path.join(kit, *rel)
        if os.path.isfile(cand):
            return cand
    return None


def load_state(state_path=None, ledger=DEFAULT_LEDGER, engine=None):
    """The board's state: either a FROZEN `top --json` object (a file -- what the golden
    frames render from, no engine call) or one read-only engine call. Raises RuntimeError
    with the engine's own message rather than inventing an empty board."""
    if state_path:
        with open(state_path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    if not os.path.isfile(ledger):
        raise RuntimeError("ledger '%s' not found here -- run the dev loop first, or pass "
                           "--ledger" % ledger)
    eng = engine or engine_path()
    if not eng:
        raise RuntimeError("qa_ledger.py not found next to uscha_top.py")
    proc = subprocess.run([sys.executable, eng, "top", "--json", "--ledger", ledger],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or b"").decode("utf-8", "replace").strip()
                           or "qa_ledger.py top failed")
    return json.loads(proc.stdout.decode("utf-8"))


# --------------------------------------------------------------------------- #
# terminal plumbing (mockable, and NOT what the golden frames test)            #
# --------------------------------------------------------------------------- #
def enable_vt():
    """Windows is first-class (ADR-031): modern conhost and Windows Terminal handle VT, and
    legacy conhost needs ENABLE_VIRTUAL_TERMINAL_PROCESSING switched on through ctypes.
    Returns False when it cannot be enabled -- the caller then prints a plain frame instead
    of spraying raw escapes at a terminal that would show them literally (AC-T-22)."""
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)              # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


def read_key():
    """One keypress, per platform, detected at runtime. Isolated in one function so the
    dispatch above it can be driven by a scripted sequence in tests -- the driver itself is
    not what is under test (ADR-034)."""
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):                     # arrow keys arrive as a 2-byte pair
            return {b"H": "k", b"P": "j"}.get(msvcrt.getch(), "")
        return ch.decode("utf-8", "replace")
    import termios
    import tty
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def dispatch(key, sel, count):
    """Key -> (new selection, quit?, reload?). Pure, so the keymap is testable without a
    terminal: the driver below is not what is under test, this dispatch is (ADR-034)."""
    if key in ("q", "Q", "\x03", "\x1b"):
        return sel, True, False
    if key == "j":
        return min(sel + 1, max(0, count - 1)), False, False
    if key == "k":
        return max(0, sel - 1), False, False
    if key == "r":
        return sel, False, True
    return sel, False, False


def terminal_size(cols=None, rows=None):
    if cols and rows:
        return int(cols), int(rows)
    size = shutil.get_terminal_size(FALLBACK_SIZE)
    return int(cols or size.columns), int(rows or size.lines)


def _print_frame(lines):
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def _loop(state, args):
    sel = 0
    sys.stdout.write("\x1b[?25l")
    try:
        while True:
            frame = render(state, terminal_size(args.cols, args.rows), sel=sel, plain=False)
            sys.stdout.write("\x1b[H\x1b[2J" + "\n".join(frame))
            sys.stdout.flush()
            sel, quit_now, reload_now = dispatch(
                read_key(), sel, len(state.get("obligations") or []))
            if quit_now:
                return 0
            if reload_now:
                state = load_state(args.state, args.ledger)
    except KeyboardInterrupt:
        return 0
    finally:
        sys.stdout.write("\x1b[?25h\x1b[0m\n")
        sys.stdout.flush()


def build_parser():
    parser = argparse.ArgumentParser(
        prog="uscha top",
        description="terminal projection of the QA ledger (read-only board, ADR-031/034)")
    parser.add_argument("--ledger", default=DEFAULT_LEDGER,
                        help="ledger the engine reads (default: %s)" % DEFAULT_LEDGER)
    parser.add_argument("--state", default=None,
                        help="render a FROZEN `top --json` file instead of calling the "
                             "engine (the golden-frame path)")
    parser.add_argument("--once", action="store_true",
                        help="print one plain frame and exit (implied without a TTY)")
    parser.add_argument("--plain", action="store_true",
                        help="never emit escape sequences")
    parser.add_argument("--refresh", type=float, default=2.0,
                        help="reserved for the M2 timed poll; M1 re-reads on the `r` key")
    parser.add_argument("--cols", type=int, default=None)
    parser.add_argument("--rows", type=int, default=None)
    return parser


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    args = build_parser().parse_args(argv)
    try:
        state = load_state(args.state, args.ledger)
    except (OSError, ValueError, RuntimeError) as exc:
        sys.stderr.write("[uscha top] %s\n" % exc)
        return 1
    size = terminal_size(args.cols, args.rows)
    # no TTY (pipe, CI, redirect) behaves as --once, and legacy conhost that refuses VT
    # degrades the same way rather than printing escapes nobody can read (AC-T-20/22).
    if args.once or args.plain or not sys.stdout.isatty() or not enable_vt():
        _print_frame(render(state, size, sel=0, plain=True))
        return 0
    return _loop(state, args)


if __name__ == "__main__":
    sys.exit(main())
