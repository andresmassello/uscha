// INV-GOLDEN-01 for pi (Earendil) — the golden-write guard, as a pi `tool_call` extension.
//
// It is the portable twin of the Claude PreToolUse hook (uscha-kit/hooks/block-approved-writes.py):
// the agent may NOT create, edit, or rename an `.approved` golden fixture. The approved file is
// field truth a HUMAN signs off; the agent emits a `.received` and stops. This blocks the write
// BEFORE the tool runs by returning `{ block: true, reason }`.
//
// Ships precompiled (plain JS, no build step) to respect the kit's stdlib-only limit. Wire it as
// a pi extension so the guard is MECHANICAL rather than advisory. Until it is loaded by a real pi
// run, `install-uscha.py doctor --target pi` reports `golden_guard: advisory` — the kit does not
// claim enforcement it has not measured.

const REASON =
  "BLOCKED by INV-GOLDEN-01: the agent may not write or rename an .approved golden. " +
  "The .approved is field truth — a human approves it. Emit a .received instead and stop.";

// A tool call touches a golden when a write-shaped tool targets a path containing `.approved`,
// or a shell command references one. Plain substring test -- BYTE-IDENTICAL semantics to the
// Python hook (`if ".approved" not in target`), so the two guards can never disagree.
function touchesGolden(name, input) {
  input = input || {};
  const n = String(name).toLowerCase();
  if (["write", "edit", "multiedit", "notebookedit"].includes(n)) {
    return String(input.file_path || input.path || "").includes(".approved");
  }
  if (n === "bash" || n === "shell") {
    return String(input.command || "").includes(".approved");
  }
  return false;
}

export default function register(pi) {
  pi.on("tool_call", (event) => {
    if (touchesGolden(event && event.tool_name, event && event.tool_input)) {
      return { block: true, reason: REASON };
    }
  });
}
