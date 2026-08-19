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

M3 scope: the read-only BOARD, the live feed and its mtime poll, and VERDICTS mode -- the
ONE thing this application writes. A verdict is written by shelling out to the engine's own
`qa_ledger.py curate`, one process per keypress, one observation per process (ADR-033): the
TUI never opens the ledger for writing and never builds a curation record, so it cannot
drift from the record shape the engine owns. It records a judgement; it does not promote,
does not rerun, and never moves DONE (INV-TOP-03).

M4 scope (phase 2, ADR-037): `d` opens a READ-ONLY spec↔code drift pane over `spec_diff`, the
advisory record `qa_ledger.py spec-drift` already left in the ledger -- it measures nothing and
runs nothing; with no recorded run the pane says so instead of showing a clean board. `o` reruns
the command THE HUMAN supplied at launch (`--rerun-cmd`, ADR-008 style: the tool never guesses a
test command) and then lets the engine's own `snapshot` ingest whatever the run produced -- so the
board still moves only on measured evidence, and the TUI still writes nothing itself. Three spawns
exist BEYOND THE READ BOUNDARY and no more: `curate` (a verdict), `snapshot` (the ingest) and the
human's own command, one per keypress, none inside a loop. The read boundary itself -- the one
`top --json` call in `load_state` -- is a fourth `subprocess.run` in this module and always was;
counting it among the three read as a false claim to anyone who grepped (1.91.0 blind review), so
the sentence now says which side of the boundary it counts. Four call sites total, no fifth.

Stdlib only. Python 3.8+. Runnable directly or via `python -m uscha_top`.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import unicodedata

DEFAULT_LEDGER = "QA-LEDGER.json"
FALLBACK_SIZE = (100, 32)

# Lines the board always spends on chrome: the title, 3 rules, 4 KPI lines, the table
# header, the feed label and the key hint. Everything else is table rows + feed.
CHROME_LINES = 11
FEED_MAX = 8            # = the engine's events_tail length; a short terminal shows fewer
BURNUP_MAX = 24
MIN_REFRESH = 0.5       # a poll faster than this is a busy loop, not a refresh

MODE_BOARD = "board"
MODE_VERDICTS = "verdicts"
MODE_DIFF = "diff"
# DIFF geometry: title, rule, the measurement line, the rule under it, the table header, the
# rule above the status line, the status line, the key hint. The rest is drift rows.
DIFF_CHROME = 8
DIFF_HINT = "advisory (ADR-005) -- a stale spec is a conversation, never a gate"
# VERDICTS geometry: title, rule, the pending line, the rule under the list, the rule under
# the pane, the status line, the key hint. Everything else is queue rows + the detail pane.
VERDICT_CHROME = 7
VERDICT_LIST_MAX = 9    # [1]..[9]: exactly the observations a single keypress can select
SIDE_BY_SIDE_MIN = 100  # narrower than this, candidate and evidence stack instead of pairing
# The three verdicts `curate` accepts, and nothing else: the vocabulary belongs to ADR-013.
VERDICTS = {"p": "preserve", "f": "fix", "u": "undefined"}
CURATE_NOTE = "recorded via uscha top"
VERDICT_HINT = "the only write is a verdict, recorded by `qa_ledger.py curate`"
# A held key repeats. Because the queue ADVANCES after every write, repeat number two would
# land on an observation the human never read -- N verdicts from one glance, which is the
# batch INV-CURATION-01 forbids arriving one legitimate call at a time. Two guards: the input
# buffer is drained after a write (`drain_keys`), and for this long a verdict key is refused
# outright, saying so instead of swallowing it.
VERDICT_COOLDOWN = 0.25
VERDICT_COOLDOWN_MSG = ("verdict recorded -- release the key (the queue advanced; the next "
                        "observation is a new judgement)")

# `o` (ADR-037, option B). The command is NEVER guessed and never read from config: it is the
# shell string the human passed at launch, the same discipline `cleanroom --run` follows
# (ADR-008). Without it the key is inert and says why.
RERUN_MISSING_MSG = "no rerun command given -- pass --rerun-cmd"
# The same courtesy a refused verdict key gets: a held `o` is one rerun, and the presses the
# cooldown eats must SAY they were eaten. A keypress that vanishes silently reads as a dropped
# input, and the next reflex is to press it again -- the repeat the cooldown exists to stop.
RERUN_COOLDOWN_MSG = ("rerun in progress or just finished -- release the key (the board "
                      "reloaded; press `o` again to run it once more)")
RERUN_FROZEN_MSG = "--state is a frozen snapshot -- a rerun needs a live ledger"
RERUN_NO_REPO_MSG = "no repo configured in this ledger -- nothing to rerun and nothing to ingest"

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

# Feed levels: one letter and one colour each. The LETTER carries the level on the plain
# path (golden frames, pipes, CI) and the colour only decorates that same letter on a real
# terminal -- so both paths have identical geometry and a snapshot compares text, never
# terminal control codes. `info` is deliberately uncoloured: it is the level an unclassified
# step falls back to, and it must not look like a verdict.
FEED_LEVELS = {
    "pass": ("P", "32"),
    "fail": ("F", "31"),
    "human": ("H", "33"),
    "unmeasured": ("U", "90"),
    "info": ("I", ""),
}

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
def _dw(text):
    """Display width in TERMINAL COLUMNS, not codepoints.

    `len()` counts codepoints, and the frame's whole contract is columns: a CJK project name
    or a full-width event text takes two columns per codepoint, so a line `len()` called
    exactly `cols` wide draws twice that and the frame every golden pins stops being a frame
    (1.86.1 fresh review, LOW, deferred until a fixture existed -- `state-wide.json` is it).

    Three classes, and no font metric anywhere: East Asian Wide and Fullwidth cost 2, a
    combining mark costs 0 (it draws on the previous cell), everything else costs 1. East
    Asian *Ambiguous* deliberately counts 1 -- that is the class the renderer's own glyphs
    fall into (`…`, `·`, `─`, `│`, `▁`, `—`), so on an ASCII state `_dw` is `len` and every
    frame captured before this function existed stays byte-identical."""
    width = 0
    for ch in str(text):
        if unicodedata.combining(ch):
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def _cut(text, width):
    """The longest PREFIX of `text` that fits in `width` columns, whole characters only.

    A wide character is never split: half a glyph is not half a column, it is a cell the
    terminal fills however it likes and a frame nobody can snapshot."""
    if width <= 0:
        return ""
    out, used = [], 0
    for ch in str(text):
        w = 0 if unicodedata.combining(ch) else (
            2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1)
        if used + w > width:
            break
        out.append(ch)
        used += w
    return "".join(out)


def _pad(text, width):
    """`str.ljust` measured in columns. Padding by codepoints puts a wide cell's second
    column inside the next field and every column after it walks."""
    return str(text) + " " * max(0, width - _dw(text))


def _rjust(text, width):
    """`str.rjust` measured in columns -- `_pad`'s mirror, for the numeric columns."""
    return " " * max(0, width - _dw(text)) + str(text)


def _fit(text, cols):
    """One line, never wider than the terminal. Wrapping would break the frame's row
    accounting, so an over-long line is cut and marked.

    Measured and cut in COLUMNS (`_dw`/`_cut`): cutting by codepoints was the bug. Note the
    cut may leave one column short rather than land exactly on `cols - 1` -- when the
    character at the boundary is wide it is dropped whole, and a frame one column narrow is
    correct where a frame one column wide is not."""
    if cols <= 0:
        return ""
    if _dw(text) <= cols:
        return text
    return _cut(text, cols - 1) + "…" if cols > 1 else _cut(text, cols)


def _spread(left, right, cols):
    """left ... right on one line, right-aligned, degrading to just `left` when tight."""
    if _dw(left) + _dw(right) + 1 > cols:
        return _fit(left, cols)
    return left + " " * (cols - _dw(left) - _dw(right)) + right


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
    room = max(4, min(BURNUP_MAX, cols - _dw(label) - _dw(note)))
    bars = "".join(BLOCKS[min(len(BLOCKS) - 1, max(0, int(p) * len(BLOCKS) // 101))]
                   for p in points[-room:])
    return label + bars + note


def _spec_pin_text(spec_pin):
    """git HEAD, labelled for what it is. There is no pinned-spec concept in the engine yet
    (ADR-035/4): an unverified sha must SAY it is unverified, and a non-git tree shows the
    em dash rather than a fabricated pin (AC-T-06, INV-TOP-05).

    The sha is state-supplied text like any other, so it goes through `_safe`: it shares a
    line with no colour of its own, but a frozen state carrying an escape here would put one
    in the header, and the header is the one line every frame has."""
    if not spec_pin or not spec_pin.get("sha"):
        return "spec_pin " + DASH
    mark = ("clean-room verified" if spec_pin.get("clean_room_verified")
            else "not clean-room verified")
    return "spec_pin %s (%s)" % (_safe(spec_pin["sha"]), mark)


def _cases_text(ob):
    total = ob.get("cases_total") or 0
    if not total:
        return DASH               # no ingested case names this criterion: no count to show
    return "%s/%s" % (_num(ob.get("cases_pass")), total)


def _row(ob, selected):
    # the three left columns are cut and padded in COLUMNS: an id or state carrying wide
    # characters used to eat its neighbour's field and walk every column after it.
    gutter = "> " if selected else "  "
    return "%s%s%s%s%7s%5s  %s" % (
        gutter, _pad(_cut(_safe(ob.get("id") or "?"), 8), 8),
        _pad(_cut(_safe(ob.get("gate") or DASH), 8), 9),
        _pad(_cut(_safe(ob.get("state") or "?"), 14), 15), _cases_text(ob),
        _num(ob.get("age_hours")), ACTIONS.get(ob.get("state"), DASH))


def _safe(text):
    """No control character reaches the terminal through the feed. The engine already
    strips them where the text is derived (`_top_event_text`); this is the second guard on
    the same surface, because the renderer also accepts a frozen state file a human wrote,
    and one ESC in it would be a control sequence the board obeys instead of prints.

    Dropped (1.90.0), matching the engine's `_top_clean` exactly: C0 and DEL, the C1 range
    U+0080-U+009F (a terminal reading the stream as latin-1 takes those for CSI/OSC), and
    every Unicode format character (category `Cf`) -- U+200B costs a codepoint and no column,
    U+202E reverses everything after it. A character that cannot be seen must not be able to
    move what is."""
    out = []
    for ch in str(text or ""):
        code = ord(ch)
        if code < 32 or code == 127 or 0x80 <= code <= 0x9F:
            continue
        if unicodedata.category(ch) == "Cf":
            continue
        out.append(ch)
    return "".join(out)


def _feed_line(ev, cols, plain):
    """`HH:MM:SS  L  text` -- the level letter is the level, the colour only decorates it,
    so the plain frame carries exactly the same information as the coloured one."""
    letter, sgr = FEED_LEVELS.get(ev.get("level"), FEED_LEVELS["info"])
    line = _fit("  %s  %s  %s" % (_safe(ev.get("ts")) or DASH, letter,
                                  _safe(ev.get("text"))), cols)
    if plain or not sgr:
        return line
    return line.replace("  %s  " % letter, "  \x1b[%sm%s%s  " % (sgr, letter, RESET), 1)


def _colorize(line, state):
    code = PALETTE.get(state)
    if not code or state not in line:
        return line
    return line.replace(state, "\x1b[%sm%s%s" % (code, state, RESET), 1)


def render(state, size, sel=0, plain=True, mode=MODE_BOARD, status=""):
    """One frame: exactly `rows` lines, none wider than `cols`.

    PURE (ADR-034): no I/O, no clock, no randomness, no environment. `state` is the parsed
    `qa_ledger.py top --json` object; `size` is (cols, rows); `sel` is the highlighted row of
    the ACTIVE mode; `mode` picks the board or the verdicts queue; `status` is the last line
    the write path produced (a parameter, not a global, so the frame stays a pure function of
    its inputs and the golden frames stay reproducible). plain=True emits no escape sequences
    at all -- the mode `--once`, CI and the golden frames use, so a snapshot compares text and
    not terminal control codes.
    """
    if mode == MODE_VERDICTS:
        return _render_verdicts(state, size, sel, plain, status)
    if mode == MODE_DIFF:
        return _render_diff(state, size, sel, plain, status)
    return _render_board(state, size, sel, plain, status)


def _render_board(state, size, sel, plain, status=""):
    cols, rows = size
    cols = max(20, int(cols))
    rows = max(CHROME_LINES + 1, int(rows))
    obligations = state.get("obligations") or []
    terminado = state.get("terminado") or {}
    debtors = state.get("debtors") or {}
    honesty = state.get("honesty") or {}

    # every string the STATE supplies goes through _safe on its way into a line (project,
    # spec_pin, the row cells, the feed): after that the only escapes in a frame are the
    # ones this renderer put there, which is what lets the final width pass leave coloured
    # lines alone without a state file being able to smuggle one in (or widen a line).
    out = []
    out.append(_spread("uscha top %s %s"
                       % (MID, _safe(state.get("project")) or "(unnamed project)"),
                       "step #%s" % _safe(_num(state.get("step"))), cols))
    out.append(RULE * cols)
    out.append(_pct_line(terminado))
    out.append("machine owes %s %s you owe %s %s untagged %s %s ETA %s"
               % (_num(debtors.get("machine")), MID, _num(debtors.get("you")), MID,
                  _num(debtors.get("untagged")), MID, _num(state.get("eta_min"))))
    # honesty travels BESIDE done on purpose (INV-TOP-04): a thin denominator has to be
    # visible at the same glance as the number it flatters.
    # fitted HERE, at construction, not only by the pass at the end: this line carries the
    # longest state-supplied string of the header, and the end pass skips coloured lines.
    out.append(_fit("honesty %s/%s (%s%%) measured %s %s"
                    % (_num(honesty.get("measured")), _num(honesty.get("total")),
                       _num(honesty.get("pct")), MID,
                       _spec_pin_text(state.get("spec_pin"))), cols))
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
    events = [e for e in (state.get("events_tail") or []) if isinstance(e, dict)]
    shown = events[:feed_n]
    if not events:
        # honest empty label: a ledger with no steps has nothing to feed, and saying so is
        # not the same statement as an idle feed with the lines scrolled away (INV-TOP-05).
        out.append("feed %s no ledger step recorded yet (nothing to show)" % MID)
    elif not shown:
        # the board is served first (AC-T-21), so at the 80x24 floor with a long table the
        # feed can lose every line. It says so; it does not pretend the ledger is quiet.
        out.append("feed %s 0/%d %s no room at this size (the board is served first)"
                   % (MID, len(events), MID))
    else:
        # `3/8` says out loud that the pane is showing three of the eight steps the engine
        # sent: a feed that silently drops lines is a feed that can hide the red one.
        out.append("feed %s %d/%d %s newest first %s P/F/H/U/I = pass/fail/human/"
                   "unmeasured/info" % (MID, len(shown), len(events), MID, MID))
    if status:
        # the LAST verdict of a queue empties it and drops the reader back here, so the
        # engine's own confirmation would otherwise vanish with the mode that showed it. It
        # takes the feed's label line for exactly one frame (the next keypress clears it) --
        # the feed's own `N/M` count returns with it. `status` is empty on every other path,
        # which is why the golden frames never see this line.
        out[-1] = _fit("status %s %s" % (MID, _safe(status)), cols)
    for i in range(feed_n):
        out.append(_feed_line(shown[i], cols, plain) if i < len(shown) else "")
    # every key on this line WORKS as of 1.91.0: `[v]` lost its `(M3)` marker when verdicts
    # shipped, and `[d]/[o]` lose their `phase 2` marker here for the same reason. A hint that
    # labels a live key as future is the same class of stale claim the frames exist to catch --
    # and one that labels a dead key as live is the worse half of it.
    out.append("[j/k] move %s [r] reload %s [q] quit %s [v] verdicts %s [d]iff %s [o] rerun"
               % (MID, MID, MID, MID, MID))
    # a coloured line was already fitted BEFORE its escape bytes went in (table rows and
    # feed lines both), and re-fitting it here would count those bytes as visible width --
    # cutting the coloured frame ~9 characters shorter than the plain one it is supposed to
    # match. Fit only what carries no escapes; the golden frames are that path exactly.
    out = [line if "\x1b" in line else _fit(line, cols) for line in out]
    # exactly `rows` lines: a frame that drifts in height is a frame no snapshot can pin
    out = out[:rows] + [""] * max(0, rows - len(out))
    return out


# --------------------------------------------------------------------------- #
# VERDICTS mode -- the queue, the detail pane, and the keymap that writes      #
# --------------------------------------------------------------------------- #
def verdict_queue(state):
    """The pending queue is EXACTLY what the engine emitted. `observations[]` already holds
    only uncurated observations, in the order `cmd_top` fixed (the anchored criterion first,
    then the id). The TUI filters nothing and sorts nothing -- a second place that decides
    what is pending is a second place that can disagree with the ledger (ADR-032)."""
    return [o for o in (state.get("observations") or []) if isinstance(o, dict)]


def _wrap(text, width):
    """Whole words onto as many lines as they need.

    The pane must never cut a claim in half: a claim the reader cannot finish is a verdict
    recorded on half the evidence (AC-T-14). A single token wider than the pane is hard-split
    and CONTINUES on the next line, so nothing is dropped either way."""
    width = max(8, int(width))
    out, line = [], ""
    for word in _safe(text).split():
        if not line:
            line = word
        elif _dw(line) + 1 + _dw(word) <= width:
            line += " " + word
        else:
            out.append(line)
            line = word
        # the hard split is measured in columns too, and `_cut` never breaks a wide
        # character in half -- so a wide token continues on the next line, whole.
        while _dw(line) > width:
            head = _cut(line, width)
            out.append(head)
            line = line[len(head):]
    if line:
        out.append(line)
    return out or [""]


def _obs_row(i, ob, selected, cols):
    """One queue line: `[n] OBS-id  title  · AC-x · pending`. The TITLE is the engine's
    capped head of the claim; the whole claim lives in the pane below, never here."""
    gutter = "> " if selected else "  "
    idx = "[%d]" % (i + 1) if i < VERDICT_LIST_MAX else "   "
    tail = " %s %s %s pending" % (MID, _safe(ob.get("ac")) or ("AC " + DASH), MID)
    head = "%s%-4s%s" % (gutter, idx, _pad(_cut(_safe(ob.get("id")), 18), 18))
    room = max(4, cols - _dw(head) - _dw(tail))
    title = _fit(_safe(ob.get("title")) or DASH, room)
    return head + _pad(title, room) + tail


def _column_widths(cols):
    """`  <left> │ <right>` spends 2 on the gutter and 3 on the divider."""
    left = (cols - 5) // 2
    return left, cols - 5 - left


def _pane(ob, cols, height):
    """The detail of the selected observation, in exactly `height` lines.

    Side by side while there is room, stacked below `SIDE_BY_SIDE_MIN` columns -- a
    40-character column is not a pane, it is a word per line. Content that still does not fit
    is NOT silently cut: the last line says how many lines are missing, which is the same
    discipline the feed's `5/7` label follows."""
    if height <= 0:
        return []
    if not ob:
        body = ["  no observation selected %s the queue is empty ([t] returns to the board)"
                % MID]
    else:
        head = ["  %s %s %s %s repo %s" % (_safe(ob.get("id")) or "?", MID,
                                           _safe(ob.get("ac")) or ("AC " + DASH), MID,
                                           _safe(ob.get("repo")) or DASH), ""]
        def block(key, width):
            return [ln for x in (ob.get(key) or []) for ln in _wrap(x, width)]

        if cols >= SIDE_BY_SIDE_MIN:
            lw, rw = _column_widths(cols)
            left = ["CANDIDATE"] + block("candidate", lw)
            right = ["EVIDENCE"] + block("evidence", rw)
            pad = max(len(left), len(right))
            left += [""] * (pad - len(left))
            right += [""] * (pad - len(right))
            body = head + [("  %s │ %s" % (_pad(l, lw), r)).rstrip()
                           for l, r in zip(left, right)]
        else:
            body = (head + ["  CANDIDATE"] + ["  " + ln for ln in block("candidate", cols - 2)]
                    + [""] + ["  EVIDENCE"] + ["  " + ln for ln in block("evidence", cols - 2)])
    if len(body) > height:
        body = body[:height - 1] + ["  %s %d more line(s) of this observation do not fit at "
                                    "this size" % (DASH, len(body) - (height - 1))]
    return [_fit(ln, cols) for ln in body] + [""] * max(0, height - len(body))


def _render_verdicts(state, size, sel, plain, status):
    """The verdicts queue. Read-only like every other frame -- the write happens in the
    dispatch, never in the renderer (ADR-034: `render` performs no I/O at all).

    `plain` is accepted and not used: this frame carries no colour of its own (the `>` gutter
    marks the selection, and a state colour here would decorate a claim rather than a
    verdict), so the coloured and plain paths are the same lines. Keeping the parameter keeps
    one render signature, and keeps the golden frames comparing the frame the terminal draws."""
    cols, rows = size
    cols = max(20, int(cols))
    rows = max(VERDICT_CHROME + 4, int(rows))
    queue = verdict_queue(state)
    debtors = state.get("debtors") or {}
    sel = max(0, min(int(sel), max(0, len(queue) - 1)))

    out = [_spread("uscha top %s %s %s verdicts"
                   % (MID, _safe(state.get("project")) or "(unnamed project)", MID),
                   "step #%s" % _safe(_num(state.get("step"))), cols),
           RULE * cols,
           # the two numbers are DIFFERENT facts and both are named: `pending` counts
           # uncurated observations, `you owe` counts the criteria they hold in quarantine.
           # One observation can name no criterion at all, so conflating them would inflate
           # whichever is shown alone.
           _fit("pending %d %s you owe %s %s a verdict never moves DONE (INV-TOP-03)"
                % (len(queue), MID, _num(debtors.get("you")), MID), cols)]

    avail = rows - VERDICT_CHROME
    want = len(queue) or 1
    list_n = max(1, min(VERDICT_LIST_MAX, want, avail - 3))
    body = list_n - 1 if len(queue) > list_n else list_n
    body = max(1, body)
    top = 0
    if sel >= body:
        top = min(sel - body + 1, max(0, len(queue) - body))
    rowsout = [_fit(_obs_row(i, ob, i == sel, cols), cols)
               for i, ob in enumerate(queue[top:top + body], start=top)]
    if len(queue) > len(rowsout):
        rowsout.append(_fit("  %s %d more observation(s) not shown (j/k to move)"
                            % (DASH, len(queue) - len(rowsout)), cols))
    if not queue:
        rowsout = [_fit("  nothing uncurated %s every observation carries a verdict "
                        "(`promote` is a human step, not this one)" % MID, cols)]
    out.extend(rowsout[:list_n])
    out.extend([""] * max(0, list_n - len(rowsout)))

    out.append(RULE * cols)
    out.extend(_pane(queue[sel] if queue else None, cols, avail - list_n))
    out.append(RULE * cols)
    out.append(_fit("status %s %s" % (MID, _safe(status) or VERDICT_HINT), cols))
    # every key this mode answers to is on the line, `[r]` included: the queue is re-read from
    # a ledger another process can move, and a reload the reader cannot find is a reload that
    # does not exist. Abbreviated to fit the 80-column floor without the `…` cut.
    out.append(_fit("[jk/1-9] move %s [p]reserve %s [f]ix %s [u]ndefined %s [r]eload %s "
                    "[t] back %s [q]uit" % (MID, MID, MID, MID, MID, MID), cols))
    out = [line if "\x1b" in line else _fit(line, cols) for line in out]
    return out[:rows] + [""] * max(0, rows - len(out))


# --------------------------------------------------------------------------- #
# DIFF mode -- spec <-> code drift, read-only (ADR-037 phase 2)                 #
# --------------------------------------------------------------------------- #
def first_repo(state):
    """The repo this session acts on: the FIRST configured one, which is the same repo
    `spec_pin` already labels the board with (ADR-032). Returns (name, path) or (None, None).

    The choice is the engine's, not the TUI's -- `repos[]` arrives in configuration order and
    this only takes the head of it. A multi-repo project therefore reruns and ingests ONE
    repo, the first, and every line that depends on the choice says which repo it picked
    rather than leaving the reader to assume it was all of them."""
    repos = [r for r in (state.get("repos") or []) if isinstance(r, dict) and r.get("name")]
    if not repos:
        return None, None
    return _safe(repos[0]["name"]), _safe(repos[0].get("path") or ".")


def _lag_text(value):
    """A lag in days, or the em dash when the record carries none. `%g` so a whole number of
    days reads as `60` and a fractional one keeps its tenth -- the record rounds to one
    decimal and this neither adds precision nor drops it."""
    if not isinstance(value, (int, float)):
        return DASH
    return "%g" % value


def _cut_tail(text, width):
    """The longest SUFFIX of `text` that fits in `width` columns, whole characters only.
    `_cut` read backwards -- same no-split-a-wide-glyph rule, same column arithmetic."""
    if width <= 0:
        return ""
    out, used = [], 0
    for ch in reversed(str(text)):
        w = 0 if unicodedata.combining(ch) else (
            2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1)
        if used + w > width:
            break
        out.append(ch)
        used += w
    return "".join(reversed(out))


def _fit_tail(text, cols):
    """Like `_fit`, but it keeps the END of the string. Used only for paths: a governed file
    cut at the front still shows the file that moved, cut at the back it shows a directory.

    Measured and cut in COLUMNS (`_dw`/`_cut_tail`), like `_fit`: `len()` and slicing count
    codepoints, and a CJK path component draws two columns per codepoint -- the DIFF pane was
    the one surface still measuring itself in codepoints after 1.90.0 fixed the board. As
    with `_fit`, the cut may land one column short rather than exactly on `cols - 1` when the
    character at the boundary is wide: one column narrow keeps the frame, one column wide
    does not."""
    text = _safe(text)
    if cols <= 0:
        return ""
    if _dw(text) <= cols:
        return text
    return "…" + _cut_tail(text, cols - 1) if cols > 1 else _cut_tail(text, cols)


def _diff_widths(cols):
    """`  <doc>  <lag>  <code ref>` -- 2 for the gutter, 2+2 for the separators, 6 for LAG."""
    lag = 6
    code = max(10, (cols - 4 - lag - 2) // 2)
    doc = max(10, cols - 4 - lag - 2 - code)
    return doc, lag, code


def _diff_head(diff, state):
    """The one line that says WHEN this was measured, or that nobody measured it.

    The honest empty case is the whole point of the pane: with no `spec-drift` record the
    board must not read as "no drift" -- it says there is no run and names the command that
    would produce one (INV-TOP-05, the same rule the feed's empty label follows)."""
    if not diff:
        repo, _path = first_repo(state)
        return ("no spec-drift run recorded -- run `qa_ledger.py spec-drift --repo %s`"
                % (repo or "<repo>"))
    stale = [s for s in (diff.get("stale") or []) if isinstance(s, dict)]
    lag = diff.get("max_lag_days")
    # the COUNT sits before the timestamp on purpose: at the 80-column floor this line is the
    # one that gets cut, and "2 of 4 stale" is the fact the reader came for.
    return ("spec %s code drift %s advisory %s %d of %d doc(s) stale (lag > %s d) %s "
            "measured %s" % ("↔", MID, MID, len(stale), diff.get("docs_total") or 0,
                             _num(lag), MID, _safe(diff.get("measured_at")) or DASH))


def _render_diff(state, size, sel, plain, status):
    """The spec↔code drift pane: `spec_diff` drawn, nothing derived and nothing run.

    Read-only twice over. `d` never invokes `spec-drift` (that command walks git and WRITES
    its latest-state record; this pane is a projection of that record, ADR-037), and `render`
    performs no I/O at all (ADR-034). What is on screen is what the last real run measured,
    with its own timestamp beside it so an old measurement cannot pass for a fresh one.

    `sel` and `plain` are accepted and unused: this pane has no cursor (v1 shows the worst
    lags first and NAMES the shortfall rather than scrolling) and no colour of its own -- a
    green/red here would read as a gate, and ADR-005 drift never gates."""
    cols, rows = size
    cols = max(20, int(cols))
    rows = max(DIFF_CHROME + 1, int(rows))
    diff = state.get("spec_diff") if isinstance(state.get("spec_diff"), dict) else None
    doc_w, lag_w, code_w = _diff_widths(cols)

    out = [_spread("uscha top %s %s %s spec drift"
                   % (MID, _safe(state.get("project")) or "(unnamed project)", MID),
                   "step #%s" % _safe(_num(state.get("step"))), cols),
           RULE * cols,
           _fit(_diff_head(diff, state), cols),
           RULE * cols,
           "  %s  %s  %s" % (_pad("DOC", doc_w), _rjust("LAG/d", lag_w),
                             "A NEWER GOVERNED FILE")]

    body = []
    stale = [s for s in ((diff or {}).get("stale") or []) if isinstance(s, dict)]
    for s in stale:
        ref = _fit_tail(s.get("code_ref") or DASH, code_w)
        more = s.get("newer_files_total")
        if isinstance(more, int) and more > 1:
            # the row shows ONE file of the N that outran the doc, and says so: a single
            # path with no cardinality beside it reads as "one file changed".
            ref = _fit(ref + " (1 of %d)" % more, code_w)
        body.append("  %s  %s  %s" % (_pad(_fit(_safe(s.get("doc")) or "?", doc_w), doc_w),
                                      _rjust(_lag_text(s.get("lag_days")), lag_w), ref))
    if not diff:
        body = ["  nothing to show until a spec-drift run is recorded %s `d` reads that "
                "record, it never runs it" % MID]
    elif not stale:
        body = ["  no spec document is stale at this lag %s every one reads CLEAN, unmapped "
                "or untracked" % MID]

    avail = rows - DIFF_CHROME
    if len(body) > avail:
        body = body[:max(0, avail - 1)] + ["  %s %d more stale doc(s) do not fit at this size "
                                           "(worst lag first)" % (DASH, len(body) - avail + 1)]
    out.extend(body[:avail])
    out.extend([""] * max(0, avail - len(body)))
    out.append(RULE * cols)
    out.append(_fit("status %s %s" % (MID, _safe(status) or DIFF_HINT), cols))
    out.append(_fit("[t]/[Esc] back %s [r] reload %s [q] quit" % (MID, MID), cols))
    out = [line if "\x1b" in line else _fit(line, cols) for line in out]
    return out[:rows] + [""] * max(0, rows - len(out))


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


def wait_key(timeout):
    """One keypress, or "" when `timeout` seconds pass first. This is what makes the poll
    possible without a busy loop AND without a key that waits for the next tick to be seen:
    POSIX blocks in `select` (raw mode held for the whole window, so a single byte is
    readable the instant it arrives), Windows walks `msvcrt.kbhit` in short slices."""
    if os.name == "nt":
        import msvcrt
        deadline = time.time() + max(0.0, timeout)
        while True:
            if msvcrt.kbhit():
                return read_key()
            if time.time() >= deadline:
                return ""
            time.sleep(0.03)
    import select
    import termios
    import tty
    fd = sys.stdin.fileno()
    try:
        saved = termios.tcgetattr(fd)
    except Exception:
        return ""                                    # no terminal to read: never block
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([sys.stdin], [], [], max(0.0, timeout))
        return sys.stdin.read(1) if ready else ""
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)


DRAIN_MAX = 256          # a terminal that never stops reporting input is not drained forever


def drain_keys():
    """Throw away whatever is ALREADY in the input buffer, and say how much it threw.

    Called right after a verdict. `wait_key` reads one byte per turn of the loop, so a held
    key (or a fast repeat, or a paste) leaves N keypresses queued -- and because the queue
    advances after every write, keypress two would judge the observation that just moved into
    the cursor's place. Draining is what makes "one keypress, one verdict" true of the
    KEYBOARD and not only of the dispatch (ADR-033, INV-CURATION-01).

    Same family as `read_key`/`wait_key` and isolated for the same reason: the driver is not
    what the suite tests, so it must be replaceable. Without a terminal it drops nothing and
    returns 0 rather than raising -- a pipe has no held key to drain."""
    dropped = 0
    if os.name == "nt":
        try:
            import msvcrt
            while dropped < DRAIN_MAX and msvcrt.kbhit():
                msvcrt.getch()
                dropped += 1
        except Exception:
            return dropped                           # no console: nothing was buffered
        return dropped
    import select
    import termios
    import tty
    fd = sys.stdin.fileno()
    try:
        saved = termios.tcgetattr(fd)
    except Exception:
        return 0                                     # no terminal: nothing to drain
    try:
        tty.setraw(fd)
        while dropped < DRAIN_MAX and select.select([sys.stdin], [], [], 0)[0]:
            if not sys.stdin.read(1):
                break                                # EOF reads ready forever: stop
            dropped += 1
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
    return dropped


def _changed(paths, seen):
    """(changed?, new snapshot) for a set of files, by (mtime, size).

    The whole of the M2 poll: no server, no watcher, no thread (ADR-031). Kept as a small
    pure-ish function on purpose -- it is the piece the suite can actually drive (AC-T-12),
    while a real TTY session is not. A path that cannot be stat'ed records None instead of
    raising: a ledger deleted under the app is a CHANGE, not a crash."""
    now = {}
    for path in paths or []:
        if not path:
            continue
        try:
            st = os.stat(path)
            now[path] = (st.st_mtime, st.st_size)
        except OSError:
            now[path] = None
    return now != (seen if seen is not None else {}), now


def watch_paths(args):
    """What the poll watches: the frozen state file when one is given, otherwise the ledger
    the engine reads. Nothing else -- `discovery/CANDIDATE-DELTA.json` is NOT watched in
    v0.1 (the state carries no path to it), so a `discover` run that leaves the ledger
    untouched is seen on the next `r`, not on the next tick. Under-claim, then wire."""
    return [args.state] if getattr(args, "state", None) else [getattr(args, "ledger", None)]


def resolve_human(explicit=None):
    """Who is at the keyboard. The person recording the verdict is its author, so the TUI
    passes the name EXPLICITLY (ADR-033) instead of letting the engine guess in a different
    process -- an SSH or multi-user session would otherwise attribute the judgement to
    whoever owns the environment. It never invents one: with nothing to resolve this returns
    None, `--human` is left off the call, and `curate`'s own default stands."""
    return explicit or os.environ.get("USERNAME") or os.environ.get("USER") or None


def _curate_call(engine, ledger, repo, obs_id, verdict, human=None, note=CURATE_NOTE):
    """THE single write of this application (ADR-033): one process, one observation, one
    verdict. The TUI never opens the ledger for writing and never constructs a curation
    record -- the record shape belongs to `curate` (ADR-013), which is exactly what the
    byte-equal fixture (AC-T-17) measures.

    It is one function on purpose: it is the boundary the suite replaces to assert the argv
    and the ONE call per keypress without writing anything (AC-T-15).

    Returns (returncode, the engine's own last line)."""
    argv = [sys.executable, engine, "curate", "--ledger", ledger, "--repo", repo,
            "--obs", obs_id, "--verdict", verdict]
    if human:
        argv += ["--human", human]
    argv += ["--note", note]
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    said = ((proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
            or (proc.stdout or b"").decode("utf-8", "replace").strip().splitlines())
    return proc.returncode, (said[-1] if said else "")


def apply_verdict(ob, verdict, args, engine=None):
    """One keypress -> one `curate` call, synchronously, for the ONE selected observation.

    A refusal by the engine (an unknown OBS, a malformed delta, a batch-looking id) comes
    back as the engine's OWN line and is surfaced: the selection does not advance and nothing
    is retried. A retry loop over a refusal is how a batch gets written one call at a time,
    which is the thing INV-CURATION-01 exists to make impossible.

    Returns (recorded?, the line the status bar shows)."""
    if getattr(args, "state", None):
        # `--state` renders a FROZEN snapshot: the ledger on disk is not the one on screen (it
        # may be another project's, or none at all). A verdict recorded from it would judge an
        # observation the reader is not looking at -- refused, and named.
        return False, "--state is a frozen snapshot -- verdicts need a live ledger"
    if not ob or not ob.get("id"):
        return False, "no observation selected: nothing to record"
    if not ob.get("repo"):
        return False, ("%s carries no repo in `top --json` -- curate needs one (--repo)"
                       % ob.get("id"))
    eng = engine or engine_path()
    if not eng:
        return False, "qa_ledger.py not found next to uscha_top.py"
    rc, said = _curate_call(eng, args.ledger, ob["repo"], ob["id"], verdict,
                            getattr(args, "human", None))
    if rc == 0:
        return True, said or ("%s = %s recorded" % (ob["id"], verdict))
    return False, said or ("curate exited %s -- nothing was recorded" % rc)


def _rerun_call(cmd, cwd):
    """The human's OWN command, run in the tracked repo's directory (ADR-037, option B).

    `shell=True` is the decision, not an oversight: what arrives here is the shell string the
    human typed after `--rerun-cmd` (`pytest -q && npm test`), exactly the way `cleanroom
    --run` and `golden-coverage --harness` take theirs -- the engine never decides what to
    run, and neither does this TUI (ADR-008). The trust boundary is the human's own shell,
    which ADR-037 states rather than pretends to mitigate: a misspelt flag runs whatever the
    shell makes of it, in that directory, the same as typing it there.

    Output is NOT captured: a test suite writes to the terminal the human is watching, and
    swallowing it would replace measured output with a spinner. One function on purpose --
    it is the boundary the suite replaces to assert the command and the ONE call per keypress
    without running anything (AC-T-26). Returns the exit code."""
    return subprocess.run(cmd, shell=True, cwd=cwd).returncode


def _snapshot_call(engine, ledger, repo):
    """The INGEST, made by the engine's own `snapshot` -- the same subcommand the dev loop
    runs at every pass close. This is what makes `o` honest: the board moves on ingested
    evidence or it does not move at all, and the TUI still builds no record of its own
    (ADR-033's rule, one more engine subcommand under it -- ADR-037).

    Returns (returncode, the engine's own last line)."""
    argv = [sys.executable, engine, "snapshot", "--ledger", ledger, "--repo", repo]
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    said = ((proc.stderr or b"").decode("utf-8", "replace").strip().splitlines()
            or (proc.stdout or b"").decode("utf-8", "replace").strip().splitlines())
    return proc.returncode, (said[-1] if said else "")


def rerun_banner(cmd, repo):
    """What the board says WHILE the command runs. Pure, so the frame that carries it stays
    a pure function of its inputs; the loop draws it before it blocks."""
    return ("rerun: %s %s running in %s (first configured repo) %s verdict keys locked"
            % (_safe(cmd), MID, _safe(repo), MID))


def run_rerun(state, args, engine=None):
    """One keypress -> the human's command, then the engine's ingest, then a reload upstream.
    Returns (ran?, the line the status bar shows).

    The order is the decision: the snapshot runs **whether or not the command exited 0**. A
    red suite is evidence too, and the whole point of `o` is that what lands on the board is
    what a report says, never what an exit code narrated -- refusing to ingest a red run
    would leave the board showing the previous, greener measurement (measured red beats
    narrated green, kit 1.48.1). What a non-zero exit changes is the STATUS LINE, which names
    it, and nothing else.

    Three refusals come first, none of which spawns anything: no `--rerun-cmd` (the command
    is the human's to supply, ADR-008), a `--state` frozen snapshot (the ledger on disk is
    not the one on screen -- the same refusal a verdict gets), and a ledger with no configured
    repo (there is no cwd to run in and no repo to ingest for)."""
    cmd = getattr(args, "rerun_cmd", None)
    if not cmd:
        return False, RERUN_MISSING_MSG
    if getattr(args, "state", None):
        return False, RERUN_FROZEN_MSG
    repo, path = first_repo(state)
    if not repo:
        return False, RERUN_NO_REPO_MSG
    eng = engine or engine_path()
    if not eng:
        return False, "qa_ledger.py not found next to uscha_top.py"
    cwd = os.path.join(os.path.dirname(os.path.realpath(args.ledger)) or ".", path or ".")
    if not os.path.isdir(cwd):
        return False, "repo path '%s' does not exist -- nothing was run" % path
    code = _rerun_call(cmd, cwd)
    rc, said = _snapshot_call(eng, args.ledger, repo)
    tail = said or ("snapshot exited %s" % rc)
    if rc != 0:
        return True, ("rerun exit %s %s snapshot FAILED (%s) -- nothing was ingested"
                      % (code, MID, tail))
    if code != 0:
        # a red run is still a measurement: it is ingested, and the line says both facts.
        return True, "rerun exit %s (red) %s ingested: %s" % (code, MID, tail)
    return True, "rerun exit 0 %s ingested: %s" % (MID, tail)


def after_verdict(sel, count):
    """Where the cursor lands once the queue has been re-read: (selection, mode).

    The observation just judged is GONE from `observations[]` (the engine emits only
    uncurated ones), so the next pending observation has taken its index -- the selection
    stays put and only clamps at the end. An empty queue is the signal to go back to the
    board: there is nothing left to judge, and a verdicts pane over an empty queue invites a
    second verdict on nothing."""
    if count <= 0:
        return 0, MODE_BOARD
    return max(0, min(sel, count - 1)), MODE_VERDICTS


def is_rerun_key(key, mode, cooling=False, rerunning=False):
    """Is this keypress a rerun request (ADR-037)? A pure predicate, and deliberately NOT a
    sixth member of `dispatch_mode`'s tuple: that shape is what M3 measured, and widening a
    measured contract so it can carry a second action is how a keymap grows a second write
    path nobody counted. The caller spends a True on exactly one `_rerun_call` + one
    `_snapshot_call`, never a loop (AC-T-29).

    `o` answers on the BOARD only -- the verdicts queue and the drift pane have their own
    jobs -- and it is refused while a rerun is in flight or while the 250 ms cooldown after
    one is still running, so a HELD `o` is one rerun and not a queue of them (the same guard
    a held verdict key gets, ADR-033)."""
    return key in ("o", "O") and mode == MODE_BOARD and not cooling and not rerunning


# `rerunning=True` is never passed by `_loop`, and that is not an oversight: the rerun is
# SYNCHRONOUS (the spawn blocks the loop, and `drain_keys` throws away whatever was typed
# meanwhile), so the sync block plus the drain IS the lock -- the flag would have nothing to
# guard against. It exists as a MEASURED contract: the predicate is what a future async rerun
# would have to honour, and AC-T-27 pins it as a pure function rather than racing a terminal.
def dispatch_mode(key, mode, sel, count, cooling=False, rerunning=False):
    """The mode machine: key + current mode -> (mode, selection, quit?, reload?, verdict).

    Pure, and the ONE place a keypress becomes a write decision -- `verdict` is a string the
    caller then spends on exactly one `curate` call, never a loop. The BOARD keymap is
    `dispatch` below, unchanged and still measured on its own, so nothing about the board's
    keys moved when this was layered on top. `sel` belongs to the ACTIVE mode; a mode change
    hands back 0 and the caller keeps the other mode's cursor.

    `cooling` is the caller's answer to "is a verdict still echoing?" (it owns the clock; this
    stays pure). While it is true, `p`/`f`/`u` produce NO verdict: a key held down repeats,
    and the second repeat would judge the observation that just took the cursor's place. Every
    other key keeps working -- the cooldown blocks writes, not the reader."""
    if mode == MODE_DIFF:
        # a read-only pane with a read-only keymap: leave, re-read, or quit. No cursor (the
        # pane names what does not fit instead of scrolling) and no write of any kind.
        if key in ("q", "Q", "\x03"):
            return mode, sel, True, False, None
        if key in ("t", "T", "\x1b", "d", "D"):
            return MODE_BOARD, 0, False, False, None
        if key == "r":
            return mode, sel, False, True, None
        return mode, sel, False, False, None
    if mode != MODE_VERDICTS:
        if key in ("v", "V"):
            return MODE_VERDICTS, 0, False, False, None
        if key in ("d", "D"):
            return MODE_DIFF, 0, False, False, None
        sel, quit_now, reload_now = dispatch(key, sel, count)
        return MODE_BOARD, sel, quit_now, reload_now, None
    if key in ("q", "Q", "\x03"):
        return mode, sel, True, False, None
    if key in ("t", "T", "\x1b"):
        return MODE_BOARD, 0, False, False, None
    if key == "j":
        return mode, min(sel + 1, max(0, count - 1)), False, False, None
    if key == "k":
        return mode, max(0, sel - 1), False, False, None
    if key == "r":
        return mode, sel, False, True, None
    if key in VERDICTS:
        # an empty queue produces NO verdict: there is nothing selected to judge, and a
        # keypress that writes anyway would be a verdict the human never aimed at an OBS.
        # Neither does a queue still cooling from the last one.
        # `rerunning` is the same refusal for a different reason (ADR-037): while a rerun is
        # in flight the queue on screen was read BEFORE it, and a verdict recorded against a
        # queue the ingest is about to move is a judgement aimed at the wrong observation.
        return mode, sel, False, False, (VERDICTS[key] if (count and not cooling
                                                           and not rerunning) else None)
    if len(str(key)) == 1 and key in "123456789":
        n = int(key) - 1
        return mode, (n if n < count else sel), False, False, None
    return mode, sel, False, False, None


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


def _reload(state, args):
    """Re-read, or keep what is on screen. A poll that catches the ledger MID-WRITE reads a
    truncated file; the last good board plus a retry next tick is honest, a traceback over
    a working terminal is not."""
    try:
        return load_state(args.state, args.ledger)
    except (OSError, ValueError, RuntimeError):
        return state


def _apply_and_advance(state, args, queue, cur, verdict):
    """ONE keypress -> ONE curate process -> re-read. Returns (state, sel, mode, status, wrote?).

    This lives in a function of its own, and not as four lines inside the key loop, for a
    reason the suite asserts structurally (AC-T-15): the module's single call to
    `apply_verdict` must have no `for` or `while` above it, so no later edit can quietly turn
    one keypress into a pass over the queue. The re-read afterwards is a READ -- the verdict
    left the queue and the board behind it did not move (INV-TOP-03); nothing reruns.

    The input buffer is drained whether the write landed or not: a held key queues repeats
    either way, and a refusal followed by three buffered `p`s is the same hazard as a success
    followed by three."""
    ok, status = apply_verdict(queue[cur] if cur < len(queue) else None, verdict, args)
    drain_keys()
    if not ok:
        return state, cur, MODE_VERDICTS, status, False
    state = _reload(state, args)
    cur, mode = after_verdict(cur, len(verdict_queue(state)))
    return state, cur, mode, status, True


def _rerun_and_reload(state, args):
    """ONE keypress -> ONE command -> ONE `snapshot` -> re-read. Returns (state, status).

    A function of its own for the same structural reason `_apply_and_advance` is one, and the
    suite asserts it the same way (AC-T-29): the module's single call to `run_rerun` must have
    no `for`/`while` above it, so no later edit can quietly turn one keypress into a pass over
    the repos. The re-read afterwards is what makes the new measurement visible; DONE moves
    here or nowhere, because the ingest is the only thing that can move it (INV-TOP-03).

    The input buffer is drained whether anything ran or not: a suite that takes a minute is
    exactly when a human types, and those keystrokes belong to the terminal they were typed
    into, not to the board that comes back."""
    ran, status = run_rerun(state, args)
    drain_keys()
    if not ran:
        return state, status
    return _reload(state, args), status


def _loop(state, args):
    sel = 0                       # the board's cursor
    vsel = 0                      # the verdict queue's cursor, kept apart from it
    mode = MODE_BOARD
    status = ""
    cooldown_until = 0.0
    interval = max(MIN_REFRESH, float(args.refresh or 0))
    paths = watch_paths(args)
    _seed, seen = _changed(paths, {})          # the first frame is already current
    dirty = True
    sys.stdout.write("\x1b[?25l")
    try:
        while True:
            if dirty:
                frame = render(state, terminal_size(args.cols, args.rows),
                               sel=(vsel if mode == MODE_VERDICTS else sel), plain=False,
                               mode=mode, status=status)
                sys.stdout.write("\x1b[H\x1b[2J" + "\n".join(frame))
                sys.stdout.flush()
                dirty = False
            # one wait serves both jobs: a key answers immediately, and the deadline is the
            # `--refresh` tick that re-reads only when a watched file actually moved.
            key = wait_key(interval)
            if key:
                queue = verdict_queue(state)
                if mode == MODE_VERDICTS:
                    cur, count = vsel, len(queue)
                else:
                    cur, count = sel, len(state.get("obligations") or [])
                # the last write's line lives exactly one frame: the next keypress clears it,
                # so a stale confirmation never sits over a board that has moved on.
                status = ""
                cooling = time.time() < cooldown_until
                new_mode, cur, quit_now, reload_now, verdict = dispatch_mode(
                    key, mode, cur, count, cooling=cooling)
                if quit_now:
                    return 0
                if verdict:
                    state, cur, new_mode, status, wrote = _apply_and_advance(
                        state, args, queue, cur, verdict)
                    cooldown_until = time.time() + VERDICT_COOLDOWN
                    if wrote:
                        _fresh, seen = _changed(paths, seen)
                elif is_rerun_key(key, mode, cooling=cooling):
                    if getattr(args, "rerun_cmd", None):
                        # the frame the human watches WHILE the command runs, drawn before
                        # the spawn because the spawn blocks this loop until it returns.
                        # That synchronous shape is also why the verdict lock is measured on
                        # `dispatch_mode(..., rerunning=True)` and not raced against a
                        # terminal (AC-T-27): while the suite runs, no key is read at all --
                        # what is typed lands in the buffer and the drain throws it away.
                        sys.stdout.write("\x1b[H\x1b[2J" + "\n".join(render(
                            state, terminal_size(args.cols, args.rows), sel=sel, plain=False,
                            mode=mode, status=rerun_banner(args.rerun_cmd,
                                                           first_repo(state)[0] or "?"))))
                        sys.stdout.flush()
                    state, status = _rerun_and_reload(state, args)
                    # the same 250 ms a verdict gets, for the same reason: a held `o` must be
                    # one rerun, not a queue of them.
                    cooldown_until = time.time() + VERDICT_COOLDOWN
                    _fresh, seen = _changed(paths, seen)
                elif key in ("o", "O") and cooling and mode == MODE_BOARD:
                    status = RERUN_COOLDOWN_MSG
                elif key in VERDICTS and cooling:
                    # the key WAS a verdict and it was refused: say why. A keypress that
                    # vanishes silently reads as a dropped input, and the next reflex is to
                    # press it again -- which is the repeat this cooldown exists to stop.
                    status = VERDICT_COOLDOWN_MSG
                elif reload_now:
                    state = _reload(state, args)
                    _fresh, seen = _changed(paths, seen)
                # each mode keeps its OWN cursor: coming back from a verdict must not move
                # the row the reader left highlighted on the board.
                if new_mode == MODE_VERDICTS:
                    vsel = cur
                elif mode == MODE_BOARD:
                    sel = cur
                mode = new_mode
                dirty = True
                continue
            moved, seen = _changed(paths, seen)
            if moved:
                state = _reload(state, args)
                dirty = True
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
                        help="seconds between mtime polls of the ledger (default: 2, "
                             "floor %.1f); `r` still forces a re-read" % MIN_REFRESH)
    parser.add_argument("--human", default=None,
                        help="who is at the keyboard: the name recorded on every verdict "
                             "this session writes (default: $USERNAME/$USER; with neither "
                             "set, `curate`'s own default applies). The person pressing the "
                             "key is the author of the judgement -- the TUI never invents a "
                             "name for it")
    parser.add_argument("--rerun-cmd", default=None,
                        help="the shell command `o` reruns, in the first configured repo's "
                             "directory (e.g. \"pytest -q\"). The tool NEVER guesses it and "
                             "never reads it from config (ADR-008/037): without this flag "
                             "`o` is inert and says so. After the command, the engine's own "
                             "`snapshot` ingests the report -- on a red run too, because a "
                             "red measurement is still a measurement")
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
    args.human = resolve_human(args.human)
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
