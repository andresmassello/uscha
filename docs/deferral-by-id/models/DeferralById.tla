---- MODULE DeferralById ----
(***************************************************************************)
(* ADR-060: a gated finding closes by deferral only through a CONFIRMED,   *)
(* PRESENT deferral of ITS id -- written BEFORE the code (repo rule 12).   *)
(* One QA tool, one repo, witnessed reviews and Anchor as shipped in       *)
(* 2.11.0 (ADR-056 R2'). New here: each gated step names its finding ids;  *)
(* ISSUES-DEFERRED.md holds `defers:` lines per id, which the AGENT adds    *)
(* and removes; a confirmation is a separate HUMAN act recorded in the     *)
(* ledger (confirm-deferral), which the agent cannot perform.              *)
(*                                                                         *)
(* Ground truth the engine cannot see: which findings a version holds.     *)
(* Rule (NoUnacceptedFindingShips): pr-ready never holds on a version with *)
(* a finding the LEDGER knows was flagged, unless that finding's deferral  *)
(* is confirmed by a human AND still present in the file.                  *)
(*                                                                         *)
(* ById = FALSE: the 2.11-2.13 rule (any change to a present file closes). *)
(* Confirm = FALSE: a `defers:` line alone closes (no human act).          *)
(* ReadNow = FALSE: the deferral is read at the clean review only.         *)
(* NoIds = TRUE: the agent may log a gated step without its ids.           *)
(* Lies = TRUE: the agent may log a clean verdict no review produced.      *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS MaxLog, Lies, NoIds, ById, Confirm, ReadNow, Partial

\* Partial = FALSE drops v1 (one finding of two fixed): the bounded `ci` tier; the deep tier has it
Versions == IF Partial THEN 0..2 ELSE {0, 2}
Ids == {1, 2}
\* v0 holds both findings, v1 only finding 1, v2 none
Findings(v) == IF v = 0 THEN {1, 2} ELSE IF v = 1 THEN {1} ELSE {}
NoReview == [src |-> 99, ids |-> {}, defs |-> {}]

VARIABLES src, defers, confirmed, log, pending, flagged
vars == <<src, defers, confirmed, log, pending, flagged>>

Init ==
  /\ src = 0
  /\ defers = {}
  /\ confirmed = {}
  /\ log = <<>>
  /\ pending = NoReview
  /\ flagged = {}

Edit(v) ==
  /\ v /= src
  /\ src' = v
  /\ UNCHANGED <<defers, confirmed, log, pending, flagged>>

\* the agent writes or deletes a `- defers: tool/id -- why` line
AddDefer(i) ==
  /\ i \notin defers
  /\ defers' = defers \cup {i}
  /\ UNCHANGED <<src, confirmed, log, pending, flagged>>

RemoveDefer(i) ==
  /\ i \in defers
  /\ defers' = defers \ {i}
  /\ UNCHANGED <<src, confirmed, log, pending, flagged>>

\* confirm-deferral: a HUMAN act, refused in the agent's shell; it confirms only an id some gated
\* step reported (ADR-060 3c) and that a `defers:` line names
Reported == UNION {log[k].ids : k \in {j \in 1..Len(log) : log[j].kind = "step"}}
HumanConfirm(i) ==
  /\ i \in defers
  /\ i \in Reported
  /\ i \notin confirmed
  /\ confirmed' = confirmed \cup {i}
  /\ UNCHANGED <<src, defers, log, pending, flagged>>

TestRun ==
  /\ Len(log) < MaxLog
  /\ log' = Append(log, [kind |-> "run", src |-> src, ids |-> {}, defs |-> {},
                         noids |-> FALSE])
  /\ UNCHANGED <<src, defers, confirmed, pending, flagged>>

\* review-start stamps the tree AND the deferral file the review starts on
Review ==
  /\ pending = NoReview
  /\ pending' = [src |-> src, ids |-> Findings(src), defs |-> defers]
  /\ UNCHANGED <<src, defers, confirmed, log, flagged>>

Step(ids, noids) == [kind |-> "step", src |-> pending.src, ids |-> ids, defs |-> pending.defs,
                     noids |-> noids]

\* log-step --gated-reported |ids| --gated-ids <ids>
LogHonest ==
  /\ pending /= NoReview
  /\ Len(log) < MaxLog
  /\ log' = Append(log, Step(pending.ids, FALSE))
  /\ pending' = NoReview
  /\ flagged' = flagged \cup {<<pending.src, i>> : i \in pending.ids}
  /\ UNCHANGED <<src, defers, confirmed>>

\* a gated step with the honest count but NO ids (2a: logged, never closable by deferral)
LogNoIds ==
  /\ NoIds
  /\ pending /= NoReview
  /\ pending.ids /= {}
  /\ Len(log) < MaxLog
  /\ log' = Append(log, Step(pending.ids, TRUE))
  /\ pending' = NoReview
  /\ flagged' = flagged \cup {<<pending.src, i>> : i \in pending.ids}
  /\ UNCHANGED <<src, defers, confirmed>>

\* narration: a clean verdict no review produced, on a witnessed review start
LogClaimClean ==
  /\ Lies
  /\ pending /= NoReview
  /\ Len(log) < MaxLog
  /\ log' = Append(log, Step({}, FALSE))
  /\ pending' = NoReview
  /\ UNCHANGED <<src, defers, confirmed, flagged>>

Next ==
  \/ \E v \in Versions : Edit(v)
  \/ \E i \in Ids : AddDefer(i) \/ RemoveDefer(i) \/ HumanConfirm(i)
  \/ TestRun \/ Review \/ LogHonest \/ LogNoIds \/ LogClaimClean

Spec == Init /\ [][Next]_vars

(* ---------------- what the ENGINE derives from the ledger ---------------- *)
IsStep(k) == log[k].kind = "step"
Steps == {k \in 1..Len(log) : IsStep(k)}
Runs == {k \in 1..Len(log) : log[k].kind = "run"}
Max(S) == CHOOSE m \in S : \A k \in S : k <= m

\* an id is accepted when its deferral is confirmed (or, with Confirm = FALSE, merely written) and
\* present -- in the file the clean review saw, and (ReadNow) in the file now
Accepted(i, c) ==
  /\ (Confirm => i \in confirmed)
  /\ i \in log[c].defs
  /\ (ReadNow => i \in defers)

\* the debt of gated step g closes at a later clean step c by a FIX (the reviewed source moved)
\* or by DEFERRAL: ById -- every id of g accepted (never for a step logged without ids);
\* not ById -- the 2.11 rule: the deferral file seen at c is present and differs from g's
ClosedAt(g, c) ==
  \/ log[c].src /= log[g].src
  \/ (ById /\ ~log[g].noids /\ \A i \in log[g].ids : Accepted(i, c))
  \/ (~ById /\ log[c].defs /= {} /\ log[c].defs /= log[g].defs)

DebtOpen(g) ==
  /\ IsStep(g)
  /\ log[g].ids /= {}
  /\ ~\E c \in (g + 1)..Len(log) : IsStep(c) /\ log[c].ids = {} /\ ClosedAt(g, c)

\* Memory: a clean verdict on the source an earlier step flagged, with its ids not all accepted
Contradicts(c) == \E g \in 1..(c - 1) :
  /\ IsStep(g) /\ log[g].ids /= {} /\ log[g].src = log[c].src
  /\ ~(ById /\ ~log[g].noids /\ \A i \in log[g].ids : Accepted(i, c))
  /\ ~(~ById /\ log[c].defs /= {} /\ log[c].defs /= log[g].defs)

Converged ==
  /\ Steps /= {}
  /\ log[Max(Steps)].ids = {}
  /\ ~\E g \in 1..Len(log) : DebtOpen(g)
  /\ log[Max(Steps)].src = src                      \* Anchor: the last review saw the source now
  /\ log[Max(Steps)].defs = defers                  \* ... and the deferral file now
  /\ ~Contradicts(Max(Steps))

TestsCurrent == Runs /= {} /\ log[Max(Runs)].src = src
PrReady == Converged /\ TestsCurrent

(* ---------------- the rule ---------------- *)
TypeOK ==
  /\ src \in Versions
  /\ defers \subseteq Ids
  /\ confirmed \subseteq Ids

NoUnacceptedFindingShips ==
  PrReady => \A i \in Ids : <<src, i>> \in flagged => (i \in confirmed /\ i \in defers)

\* vacuity: MUST break -- a confirmed, present deferral of a flagged finding still ships
NeverAcceptedAndReady == ~(PrReady /\ \E i \in Ids : <<src, i>> \in flagged)
\* vacuity: MUST break -- a real fix still ships
NeverFixedAndReady == ~(PrReady /\ src = 2 /\ flagged /= {})
====
