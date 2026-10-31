const seq = (s) => (s ? Object.keys(s).sort((a, b) => a - b).map((k) => s[k]) : []);
const steps = (v) => seq(v.log).filter((r) => r.kind === "step");
export const title = "ADR-056 R2 as specified: the gated-finding debt, one QA tool";
export const state = (v) => {
  const code = v.src === 0 ? "Code has the bug" : "Code fixed";
  const st = steps(v);
  const last = st.length ? st[st.length - 1] : null;
  const ledger = !last ? "nothing logged" : last.gated > 0 ? "gated finding logged" : "clean pass logged";
  return `${code}, ${ledger}`;
};
export const group = (v) => (v.src === 0 ? "bug" : "fixed");
export const colors = { bug: "orange", fixed: "teal" };
export const step = (action, from, to) => {
  if (action === "Edit") {
    if (from.src === 0) return "the agent fixes the code";
    if (to.src === 0) return "the agent reverts to the buggy code";
    return "the agent edits the fixed code";
  }
  return {
    Review: "the QA tool reviews the code",
    TestRun: "test-run measures the code",
    LogHonest: "the agent logs what the tool found",
    LogClaimClean: "the agent logs a clean pass",
    Defer: "the agent defers the finding",
  }[action] ?? null;
};
