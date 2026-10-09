# _jobs.sh -- opt-in parallel units for smoke-engine.sh (ADR-053). Sourced, never executed.
#
# The suite is the ruler every release is measured with, so this file has one job: make it
# faster WITHOUT changing what it measures. Parallelism is OFF unless USCHA_JOBS=N (N>1) asks
# for it. Off, `pj_unit NAME FN` calls FN in the current shell -- no subshell, no buffering, no
# background process -- so the suite runs exactly the commands it ran before this file existed,
# in the same order, with the same output. The ritual (tools/release.py) and CI stay serial.
#
# On, a unit runs in a background subshell with its counters reset to zero; it writes its
# delta ("PASS FAIL") to its own result file and its stdout+stderr to its own log, and
# `pj_collect` -- the barrier -- waits for every unit, replays the logs in LAUNCH order (so the
# log reads the same as a serial run) and sums the deltas. Collection is FAIL-CLOSED: a unit
# that left no result file, or an unreadable one, is one FAIL that names the unit, never a
# silently shorter sum.
#
# bash 3.2 only (the macOS CI cell): no `wait -n`, no associative arrays, no mapfile/readarray,
# no case-modifying expansions. The running set is counted from per-unit `.done` markers, and
# lists are space-separated strings, never arrays (an empty "${a[@]}" is unbound under set -u
# before bash 4.4). The functions also survive `set -e`, which the suite turns on at P0-A and
# never turns off: no bare test is ever the last word of a function here.
#
# Test-only, like _harness.py: package.json excludes uscha-kit/tests/ from the npm package.

PJ_JOBS=1
PJ_DIR=""
PJ_PIDS=""
PJ_PENDING=""
PJ_SEQ=0

# The effective job count, printed. 1 unless USCHA_JOBS is an integer above 1 AND coverage is
# off (USCHA_COVERAGE=1 forces serial: one coverage data set, one writer). Capped at the cores
# this machine reports -- nproc, then getconf (macOS has no nproc), then NUMBER_OF_PROCESSORS
# (git-bash), then 1 -- and never above what was asked for.
pj_resolve_jobs() {
  local want cores
  want="${USCHA_JOBS:-1}"
  case "$want" in ''|*[!0-9]*) echo 1; return 0;; esac
  want=$((10#$want))
  if [ "$want" -le 1 ] || [ "${USCHA_COVERAGE:-0}" = "1" ]; then echo 1; return 0; fi
  cores="$(nproc 2>/dev/null)" || cores=""
  case "$cores" in ''|*[!0-9]*) cores="$(getconf _NPROCESSORS_ONLN 2>/dev/null)" || cores="";; esac
  case "$cores" in ''|*[!0-9]*) cores="${NUMBER_OF_PROCESSORS:-}";; esac
  case "$cores" in ''|*[!0-9]*) cores=1;; esac
  cores=$((10#$cores))
  if [ "$cores" -lt 1 ]; then cores=1; fi
  if [ "$want" -gt "$cores" ]; then echo "$cores"; else echo "$want"; fi
  return 0
}

pj_init() {
  PJ_JOBS="$(pj_resolve_jobs)"
  if [ "$PJ_JOBS" -gt 1 ]; then
    PJ_DIR="$(mktemp -d 2>/dev/null || echo "${TMP:-/tmp}/uscha-pj-$$")"
    mkdir -p "$PJ_DIR"
  fi
  return 0
}

# How many launched units have not written their .done marker yet -> PJ_RUNNING. A global,
# not a command substitution: the throttle polls it, and a fork per poll is real time on Windows.
pj__count_running() {
  local t
  PJ_RUNNING=0
  for t in $PJ_PENDING; do
    if [ ! -f "$PJ_DIR/$t.done" ]; then PJ_RUNNING=$((PJ_RUNNING + 1)); fi
  done
  return 0
}

# pj_unit NAME FN -- run FN as one unit of the suite.
pj_unit() {
  local name="$1" fn="$2" tag flags
  if [ "$PJ_JOBS" -le 1 ]; then
    "$fn"
    return 0
  fi
  pj__count_running
  while [ "$PJ_RUNNING" -ge "$PJ_JOBS" ]; do
    sleep 0.1
    pj__count_running
  done
  PJ_SEQ=$((PJ_SEQ + 1))
  tag="$(printf '%03d' "$PJ_SEQ")-$name"
  # The unit keeps the -e state the serial suite would give it; the wrapper around it drops -e
  # so the .done marker is written however the unit ends (a unit that dies leaves no result
  # file and is counted red at collection, but it must never stall the throttle).
  flags="$-"
  {
    set +e
    (
      case "$flags" in *e*) set -e;; esac
      PASS=0; FAIL=0
      "$fn"
      printf '%s %s\n' "$PASS" "$FAIL" > "$PJ_DIR/$tag.res"
    ) > "$PJ_DIR/$tag.out" 2>&1
    : > "$PJ_DIR/$tag.done"
  } &
  PJ_PIDS="$PJ_PIDS $!"
  PJ_PENDING="$PJ_PENDING $tag"
  return 0
}

# pj_collect -- the barrier. Waits for every unit launched since the last barrier, replays
# their logs in launch order and adds their deltas to PASS/FAIL. A no-op when serial.
pj_collect() {
  local pid tag p f
  if [ "$PJ_JOBS" -le 1 ]; then return 0; fi
  for pid in $PJ_PIDS; do wait "$pid" || :; done
  for tag in $PJ_PENDING; do
    if [ -f "$PJ_DIR/$tag.out" ]; then cat "$PJ_DIR/$tag.out"; fi
    p=""; f=""
    if [ -f "$PJ_DIR/$tag.res" ]; then read -r p f < "$PJ_DIR/$tag.res" || :; fi
    case "$p:$f" in
      :*|*:|*[!0-9:]*)
        FAIL=$((FAIL + 1))
        echo "  FAIL parallel unit ${tag#*-} left no result -- it died before counting";;
      *)
        PASS=$((PASS + p)); FAIL=$((FAIL + f));;
    esac
  done
  PJ_PIDS=""
  PJ_PENDING=""
  return 0
}

# pj_finish -- drop the scratch directory once the last barrier has been crossed.
pj_finish() {
  if [ -n "$PJ_DIR" ]; then rm -rf "$PJ_DIR"; fi
  return 0
}
