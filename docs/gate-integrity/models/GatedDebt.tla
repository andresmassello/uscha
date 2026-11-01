---- MODULE GatedDebt ----
(***************************************************************************)
(* ADR-056 R2 (docs/gate-integrity/SPEC.md 3.3), the gated-finding debt,  *)
(* for ONE QA tool in ONE repo, as the SPEC describes it -- BEFORE 2.11.0  *)
(* writes it. The engine sees only what the ledger records: test-runs and  *)
(* log-steps, each stamped with the source and ISSUES-DEFERRED.md content  *)
(* at record time. Ground truth the engine cannot see: which code versions *)
(* hold a gated bug (Buggy) and which of them a QA tool has flagged.       *)
(*                                                                         *)
(* Rule the reader agrees to (NoFlaggedBugShips): pr-ready never holds on  *)
(* a code version the LEDGER knows a QA tool flagged, unless deferred.    *)
(*                                                                         *)
(* Anchor = TRUE adds the candidate fix: convergence also requires the     *)
(* latest QA step to have been logged at the source that is on disk now.  *)
(* Lies = TRUE lets the agent narrate counts no review produced.           *)
(* Witness = TRUE: the engine stamps the tree when a review STARTS, and a  *)
(* step carries the REVIEWED tree (a step with no recorded start is not   *)
(* evidence) -- the test-run principle of ADR-055 applied to QA reviews.  *)
(* Memory = TRUE: a clean step whose reviewed tree has the same content as *)
(* a tree the ledger already saw flagged contradicts the record: it counts *)
(* for nothing.                                                            *)
(* V211 = TRUE: the design as SHIPPED in 2.11.0 after the fresh review -- *)
(* the agent may also UNDO a deferral and log a gated step with no review *)
(* (both were outside the first model); an unwitnessed gated step opens a *)
(* debt on its logged state; Anchor also compares ISSUES-DEFERRED.md.     *)
(* DeferFix / MemoryFix = TRUE: the two fixes TLC forced on the shipped   *)
(* design (AC-GI-64, -65). Each `ci` teeth config sets one to FALSE and   *)
(* MUST break -- the bound still finds the hole it closes (ADR-059).      *)
(***************************************************************************)
EXTENDS Naturals, Sequences

CONSTANTS MaxLog, Anchor, Lies, Witness, Memory, V211, DeferFix, MemoryFix

Versions == 0..2
Buggy == {0}
NoReview == [src |-> 99, gated |-> 99, def |-> 99]

VARIABLES src, deferred, log, pending, flagged
vars == <<src, deferred, log, pending, flagged>>

Init ==
  /\ src = 0
  /\ deferred = 0
  /\ log = <<>>
  /\ pending = NoReview
  /\ flagged = {}

Rec(kind, g) == [kind |-> kind, src |-> src, def |-> deferred, gated |-> g, wit |-> FALSE]

\* the agent edits the code: a fix, an unrelated change, or a revert
Edit(v) ==
  /\ v /= src
  /\ src' = v
  /\ UNCHANGED <<deferred, log, pending, flagged>>

\* the agent adds an entry to ISSUES-DEFERRED.md
Defer ==
  /\ deferred = 0
  /\ deferred' = 1
  /\ UNCHANGED <<src, log, pending, flagged>>

\* test-run: the engine records a stamp of the tree
TestRun ==
  /\ Len(log) < MaxLog
  /\ log' = Append(log, Rec("run", 0))
  /\ UNCHANGED <<src, deferred, pending, flagged>>

\* a QA tool reviews the code on disk; its verdict waits to be logged
Review ==
  /\ pending = NoReview
  \* the deferral state is read when the review STARTS, as review-start reads it in the engine
  /\ pending' = [src |-> src, gated |-> IF src \in Buggy THEN 1 ELSE 0, def |-> deferred]
  /\ UNCHANGED <<src, deferred, log, flagged>>

\* log-step with the counts the review produced (the SKILL order: fix, test, log)
StepRec(g) == IF Witness THEN [kind |-> "step", src |-> pending.src,
                               def |-> IF V211 THEN pending.def ELSE deferred, gated |-> g,
                               wit |-> TRUE]
              ELSE Rec("step", g)

LogHonest ==
  /\ pending /= NoReview
  /\ Len(log) < MaxLog
  /\ log' = Append(log, StepRec(pending.gated))
  /\ pending' = NoReview
  \* the ledger now KNOWS the reviewed version holds a gated finding
  /\ flagged' = IF pending.gated > 0 THEN flagged \cup {pending.src} ELSE flagged
  /\ UNCHANGED <<src, deferred>>

\* narration: a clean step no review produced (the audit's A-F2 re-log)
LogClaimClean ==
  /\ Lies
  /\ Witness => pending /= NoReview      \* witnessed: a step needs a recorded review start
  /\ Len(log) < MaxLog
  /\ log' = Append(log, StepRec(0))
  /\ pending' = NoReview
  /\ UNCHANGED <<src, deferred, flagged>>

\* V211: the agent removes a deferral it added
Undefer ==
  /\ V211
  /\ deferred = 1
  /\ deferred' = 0
  /\ UNCHANGED <<src, log, pending, flagged>>

\* V211: a gated step logged with NO review (honest count, no review-start): the ledger knows the
\* logged version is flagged
LogUnwitnessedGated ==
  /\ V211
  /\ src \in Buggy
  /\ Len(log) < MaxLog
  /\ log' = Append(log, Rec("step", 1))
  /\ flagged' = flagged \cup {src}
  /\ UNCHANGED <<src, deferred, pending>>

Next ==
  \/ \E v \in Versions : Edit(v)
  \/ Defer \/ TestRun \/ Review \/ LogHonest \/ LogClaimClean
  \/ Undefer \/ LogUnwitnessedGated

Spec == Init /\ [][Next]_vars

(* ---------------- what the ENGINE derives from the ledger ---------------- *)
IsStep(i) == log[i].kind = "step"
Steps == {i \in 1..Len(log) : IsStep(i)}
Runs == {i \in 1..Len(log) : log[i].kind = "run"}
Max(S) == CHOOSE m \in S : \A k \in S : k <= m

\* the baseline of a gated step: the newest stamp recorded before it; none -> the step itself
Base(i) == IF Witness THEN i ELSE IF i > 1 THEN i - 1 ELSE i   \* witnessed: the reviewed tree IS the before
\* V211: a changed deferral file closes a debt only when the clean review SAW a deferral --
\* removing one is not a deferral (TLC found the removal path: Defer, log gated, Undefer, clean)
Moved(a, b) == a.src /= b.src \/ (a.def /= b.def /\ ((V211 /\ DeferFix) => b.def /= 0))

DebtOpen(i) ==
  /\ IsStep(i)
  /\ log[i].gated > 0
  /\ ~\E c \in (i + 1)..Len(log) :
        IsStep(c) /\ log[c].gated = 0 /\ (V211 => log[c].wit)
        /\ Moved(log[IF V211 /\ ~log[i].wit THEN i ELSE Base(i)], log[c])

\* a clean step that contradicts an earlier gated verdict on the same content
Contradicts(c) == \E i \in 1..(c - 1) :
  IsStep(i) /\ log[i].gated > 0 /\ log[i].src = log[c].src
  \* V211: with no deferral on disk the clean verdict is on the same content as ANY earlier
  \* gated verdict on that source -- removing a deferral does not make it new content
  /\ (log[i].def = log[c].def \/ (V211 /\ MemoryFix /\ log[c].def = 0))

Converged ==
  /\ Steps /= {}
  /\ log[Max(Steps)].gated = 0
  /\ ~\E i \in 1..Len(log) : DebtOpen(i)
  /\ (Anchor => log[Max(Steps)].src = src)
  /\ (V211 => log[Max(Steps)].wit /\ log[Max(Steps)].def = deferred)
  /\ (Memory => ~Contradicts(Max(Steps)))

TestsCurrent == Runs /= {} /\ log[Max(Runs)].src = src

PrReady == Converged /\ TestsCurrent

(* ---------------- the rule ---------------- *)
TypeOK ==
  /\ src \in Versions
  /\ deferred \in {0, 1}
  /\ flagged \subseteq Versions

NoFlaggedBugShips == PrReady => ~(src \in flagged /\ deferred = 0)
\* vacuity control: this MUST be violated -- a legitimate fix still reaches pr-ready
NeverFixedAndReady == ~(PrReady /\ flagged /= {})
====
