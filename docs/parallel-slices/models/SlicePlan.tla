---- MODULE SlicePlan ----
(***************************************************************************)
(* ADR-063 (parallel slices), modelled BEFORE 2.17.0 writes it (repo rule  *)
(* 12). One change, one repo, three declared slices, three files.          *)
(* Amended after the first TLC run (2026-11-17): DropGuard (D1) and        *)
(* AncestryCheck (D2) added, the agent no longer assumed to obey `after`.  *)
(*                                                                         *)
(* The shape (operators below, not constants):                             *)
(*   s1  paths {f1}                                                        *)
(*   s2  paths {f2}, after s1   (content dependency, disjoint files)       *)
(*   s3  paths {f1}             (overlaps s1, no after edge)               *)
(*   lock  a file no slice declares (a lockfile, a generated file)         *)
(*                                                                         *)
(* Content is an opaque version: 0 is the base, each slice writes its own  *)
(* value (s1 -> 1, s2 -> 2, s3 -> 3), a merge that changes a file beyond   *)
(* the slice's diff writes 4 (a regenerated lockfile, a conflict resolved  *)
(* by hand), a fix on the change branch writes 5. 9 is "no stamp".         *)
(*                                                                         *)
(* A slice branch is its fork plus its own writes, and a slice writes only *)
(* its own value, so the branch is encoded by the SET of files it wrote    *)
(* (ed): its diff since the fork is exactly ed, every file of it holds     *)
(* Val(s). The fork snapshot itself is never read (a merge takes the       *)
(* slice's files and keeps the change branch elsewhere), so it is not      *)
(* stored: an exact re-encoding, not an abstraction.                       *)
(*                                                                         *)
(* The engine sees the ledgers: per slice the files stamped clean (rv) and *)
(* whether a slice test-run saw the current branch (sliceRun); in the main *)
(* ledger the integration stamps (irev, carried or reviewed) and whether   *)
(* an integration test-run saw the change branch as it is now (intRun,     *)
(* reset by every change; a branch that returns to an earlier tree reads   *)
(* untested, stricter than a hash compare). Ground truth it cannot see:    *)
(* which content of each file a real review ever saw (seen). The agent is *)
(* modelled as obeying slice-plan's DISJOINTNESS (decision 3; the ADR has  *)
(* no refusal for an overlap), but NOT its `after` column: it may fork a   *)
(* dependent slice at any time, because the engine refuses an `after` at   *)
(* the first review step, never at the start (it launches nothing).        *)
(*                                                                         *)
(* Flags (each one a rule of the ADR that can be switched off):            *)
(*   HashCarry        decision 6: a slice's clean pass carries into the    *)
(*                    integration only for files whose content equals the  *)
(*                    reviewed one. FALSE: it carries for every file the   *)
(*                    slice or its merge changed (the sum is believed).    *)
(*   DisjointCheck    decision 3: a slice starts only with declared paths  *)
(*                    disjoint from every running slice.                   *)
(*   AfterCheck       decision 4: a slice passes its first review step     *)
(*                    only with every `after` integrated.                  *)
(*   AncestryCheck    amendment D2: ... and only with every `after`'s      *)
(*                    merge an ancestor of the slice branch (in its fork). *)
(*   PathLeakCheck    decision 4: slice-integrate refuses a diff that      *)
(*                    leaves the declared paths.                           *)
(*   IntegrationSuite decision 6: pr-ready needs a test-run on the         *)
(*                    integration commit. FALSE: the slice runs count.     *)
(*   WholeDelivery    decision 7: pr-ready needs every declared slice      *)
(*                    integrated or dropped. FALSE: one integrated slice   *)
(*                    is enough.                                           *)
(*   DropGuard        amendment D1: slice-drop refuses a slice whose merge *)
(*                    is in the change branch (revert it first).           *)
(* Fixed ON: slice-integrate refuses a slice whose ledger has not          *)
(* converged, and one whose merge is not in the change branch.             *)
(*                                                                         *)
(* Bounds: MaxEdits caps slice writes plus change-branch fixes together;   *)
(* MaxSliceEdits caps the size of one slice's diff.                        *)
(***************************************************************************)
EXTENDS Naturals, FiniteSets

CONSTANTS MaxEdits, MaxSliceEdits, MaxPar,
          HashCarry, DisjointCheck, AfterCheck, AncestryCheck, PathLeakCheck, IntegrationSuite,
          WholeDelivery, DropGuard

Slices == {"s1", "s2", "s3"}
Files == {"f1", "f2", "lock"}
Paths(s) == IF s = "s1" THEN {"f1"} ELSE IF s = "s2" THEN {"f2"} ELSE {"f1"}
After(s) == IF s = "s2" THEN {"s1"} ELSE {}
Val(s) == IF s = "s1" THEN 1 ELSE IF s = "s2" THEN 2 ELSE 3
MergeVal == 4
FixVal == 5
NoVal == 9
Content == 0..5
Base == [f \in Files |-> 0]
NoTree == [f \in Files |-> NoVal]
\* a merge may change at most one file beyond what the slice brings
Merges == {{}} \cup {{g} : g \in Files}

\* ed[s]: the files the slice branch wrote since its fork (its diff); rv[s]: the files of it a clean
\* slice review stamped; forkOk[s]: every `after` of s was merged into the change branch when s
\* forked (git: each `after` merge is an ancestor of the slice branch); sliceRun[s]: a slice
\* test-run saw the slice branch as it is now
VARIABLES status, forkOk, ed, rv, merged, mf, chg, irev, seen, intRun, sliceRun, edits
vars == <<status, forkOk, ed, rv, merged, mf, chg, irev, seen, intRun, sliceRun, edits>>

Running == {s \in Slices : status[s] = "running"}
\* the slice's diff: what its branch changed since it forked from the change branch
Diff(s) == ed[s]
\* the slice ledger converged: every file of its diff reviewed clean at its current content
Converged(s) == Diff(s) /= {} /\ Diff(s) \subseteq rv[s]
AfterOk(s) == \A a \in After(s) : status[a] = "integrated"
\* the slice ledger carries at least one review stamp
Reviewed(s) == rv[s] /= {}
\* the integration's diff against the base
IntDiff == {f \in Files : chg[f] /= 0}

Init ==
  /\ status = [s \in Slices |-> "planned"]
  /\ forkOk = [s \in Slices |-> FALSE]
  /\ ed = [s \in Slices |-> {}]
  /\ rv = [s \in Slices |-> {}]
  /\ merged = [s \in Slices |-> FALSE]
  /\ mf = [s \in Slices |-> {}]
  /\ chg = Base
  /\ irev = NoTree
  /\ seen = [f \in Files |-> {}]
  /\ intRun = FALSE
  /\ sliceRun = [s \in Slices |-> FALSE]
  /\ edits = 0

\* the agent starts a slice: a worktree forked from the change branch. It obeys the plan's
\* disjointness and max_parallel, not its `after` column (the engine refuses that at review)
Start(s) ==
  /\ status[s] = "planned"
  /\ Cardinality(Running) < MaxPar
  /\ DisjointCheck => \A t \in Running : Paths(s) \cap Paths(t) = {}
  /\ status' = [status EXCEPT ![s] = "running"]
  /\ forkOk' = [forkOk EXCEPT ![s] = \A a \in After(s) : merged[a]]
  /\ UNCHANGED <<ed, rv, merged, mf, chg, irev, seen, intRun, sliceRun, edits>>

\* the slice's agent writes a file -- any file, inside or outside the declared paths
Edit(s, f) ==
  /\ status[s] = "running"
  /\ ~merged[s]
  /\ edits < MaxEdits
  /\ Cardinality(ed[s]) < MaxSliceEdits
  /\ f \notin ed[s]
  /\ ed' = [ed EXCEPT ![s] = ed[s] \cup {f}]
  /\ sliceRun' = [sliceRun EXCEPT ![s] = FALSE]
  /\ edits' = edits + 1
  /\ UNCHANGED <<status, forkOk, rv, merged, mf, chg, irev, seen, intRun>>

\* a clean review of the slice's diff stamps the content it saw (decision 4's refusal at
\* review-start / log-step: every after integrated; D2: and every after's merge in the fork)
Review(s) ==
  /\ status[s] = "running"
  /\ AfterCheck => AfterOk(s)
  /\ AncestryCheck => forkOk[s]
  /\ ~(ed[s] \subseteq rv[s])
  /\ rv' = [rv EXCEPT ![s] = rv[s] \cup ed[s]]
  /\ seen' = [f \in Files |-> IF f \in ed[s] THEN seen[f] \cup {Val(s)} ELSE seen[f]]
  /\ UNCHANGED <<status, forkOk, ed, merged, mf, chg, irev, intRun, sliceRun, edits>>

\* a test-run on the slice's branch. Only the IntegrationSuite = FALSE gate reads it, so with the
\* rule on it is disabled: a state reduction no invariant of an all-on config can tell apart
TestRunSlice(s) ==
  /\ ~IntegrationSuite
  /\ status[s] = "running"
  /\ ~sliceRun[s]
  /\ sliceRun' = [sliceRun EXCEPT ![s] = TRUE]
  /\ UNCHANGED <<status, forkOk, ed, rv, merged, mf, chg, irev, seen, intRun, edits>>

\* the agent merges the slice branch into the change branch. A file the slice changed takes the
\* slice's content (a textual conflict resolved in the slice's favour); the files in X are changed
\* by the merge itself (a regenerated lockfile, a conflict resolved by hand)
Merge(s, X) ==
  /\ status[s] = "running"
  /\ ~merged[s]
  /\ ed[s] /= {}
  /\ LET m == [f \in Files |-> IF f \in X THEN MergeVal
                               ELSE IF f \in ed[s] THEN Val(s) ELSE chg[f]]
     IN /\ chg' = m
        /\ intRun' = (intRun /\ m = chg)
        /\ mf' = [mf EXCEPT ![s] = {f \in Files : m[f] /= chg[f]}]
  /\ merged' = [merged EXCEPT ![s] = TRUE]
  /\ UNCHANGED <<status, forkOk, ed, rv, irev, seen, sliceRun, edits>>

\* what slice-integrate carries from the slice's ledger into the main ledger
Carry(s, f) == IF HashCarry THEN f \in rv[s] /\ chg[f] = Val(s)
               ELSE f \in Diff(s) \cup mf[s]

\* slice-integrate --slice S, with its three refusals
Integrate(s) ==
  /\ status[s] = "running"
  /\ merged[s]
  /\ Converged(s)
  /\ PathLeakCheck => Diff(s) \subseteq Paths(s)
  /\ status' = [status EXCEPT ![s] = "integrated"]
  /\ irev' = [f \in Files |-> IF Carry(s, f) THEN chg[f] ELSE irev[f]]
  /\ UNCHANGED <<forkOk, ed, rv, merged, mf, chg, seen, intRun, sliceRun, edits>>

\* slice-drop: a human act (decision 7). D1: refused for a slice whose merge is in the change
\* branch (the merge is reverted first; the model has no revert, so a merged slice stays)
Drop(s) ==
  /\ status[s] \in {"planned", "running"}
  /\ DropGuard => ~merged[s]
  /\ status' = [status EXCEPT ![s] = "dropped"]
  /\ UNCHANGED <<forkOk, ed, rv, merged, mf, chg, irev, seen, intRun, sliceRun, edits>>

\* the agent edits the change branch directly (a fix after the integration)
IntEdit(f) ==
  /\ edits < MaxEdits
  /\ chg[f] /= FixVal
  /\ chg' = [chg EXCEPT ![f] = FixVal]
  /\ intRun' = FALSE
  /\ edits' = edits + 1
  /\ UNCHANGED <<status, forkOk, ed, rv, merged, mf, irev, seen, sliceRun>>

\* a clean review of the integration's diff
IntReview ==
  /\ \E f \in IntDiff : irev[f] /= chg[f]
  /\ irev' = [f \in Files |-> IF f \in IntDiff THEN chg[f] ELSE irev[f]]
  /\ seen' = [f \in Files |-> IF f \in IntDiff THEN seen[f] \cup {chg[f]} ELSE seen[f]]
  /\ UNCHANGED <<status, forkOk, ed, rv, merged, mf, chg, intRun, sliceRun, edits>>

\* a test-run on the integration commit (Merge and IntEdit reset intRun when they change chg)
TestRunInt ==
  /\ ~intRun
  /\ intRun' = TRUE
  /\ UNCHANGED <<status, forkOk, ed, rv, merged, mf, chg, irev, seen, sliceRun, edits>>

Next ==
  \/ \E s \in Slices : Start(s) \/ Review(s) \/ TestRunSlice(s) \/ Integrate(s) \/ Drop(s)
  \/ \E s \in Slices : \E f \in Files : Edit(s, f)
  \/ \E s \in Slices : \E X \in Merges : Merge(s, X)
  \/ \E f \in Files : IntEdit(f)
  \/ IntReview \/ TestRunInt

Spec == Init /\ [][Next]_vars

(* ---------------- the pr-ready gate, as the engine reads it ---------------- *)
DeliveryOk == IF WholeDelivery THEN \A s \in Slices : status[s] \in {"integrated", "dropped"}
              ELSE \E s \in Slices : status[s] = "integrated"
SliceRunsOk ==
  /\ \E s \in Slices : status[s] = "integrated"
  /\ \A s \in Slices : status[s] = "integrated" => sliceRun[s]
TestsOk == IF IntegrationSuite THEN intRun ELSE SliceRunsOk
\* review_tiers: every file of the integration's diff carries a stamp of its current content
StampsOk == \A f \in IntDiff : irev[f] = chg[f]

PrReady == IntDiff /= {} /\ DeliveryOk /\ StampsOk /\ TestsOk

(* ---------------- the rules ---------------- *)
TypeOK ==
  /\ status \in [Slices -> {"planned", "running", "integrated", "dropped"}]
  /\ chg \in [Files -> Content]
  /\ \A s \in Slices : ed[s] \subseteq Files /\ rv[s] \subseteq ed[s]
  /\ merged \in [Slices -> BOOLEAN]
  /\ forkOk \in [Slices -> BOOLEAN]
  /\ sliceRun \in [Slices -> BOOLEAN]
  /\ edits \in 0..MaxEdits

\* 1. never pr-ready with a declared slice that is neither integrated nor dropped
WholeDelivered == PrReady => \A s \in Slices : status[s] \in {"integrated", "dropped"}
\* 2. never two overlapping slices running at once
NoOverlapRunning == \A s, t \in Running : s /= t => Paths(s) \cap Paths(t) = {}
\* 3. never a slice reviewed before every `after` is integrated (a stamp and integrated are both
\*    final, so this state invariant is the same as "at its first review step")
AfterRespected == \A s \in Slices : Reviewed(s) => AfterOk(s)
\* 4. never a gate pass with an integration file whose content no real review saw
ReviewedContent == PrReady => \A f \in IntDiff : chg[f] \in seen[f]
\* 5. never a gate pass without a test-run on the integration commit
IntegrationTested == PrReady => intRun
\* 6. never an integrated slice whose diff left its declared paths
NoLeakIntegrated == \A s \in Slices : status[s] = "integrated" => Diff(s) \subseteq Paths(s)
\* 7. (D2) never a slice reviewed that was not built on its `after` slices: each one's merge is
\*    in the slice's fork (an ancestor of the slice branch)
BuiltOnAfter == \A s \in Slices : Reviewed(s) => forkOk[s]
\* 8. (D1) never a gate pass shipping a merged slice's diff that left its declared paths
NoLeakShips == PrReady => \A s \in Slices : merged[s] => Diff(s) \subseteq Paths(s)
\* max_parallel, enforced by the plan
CapRespected == Cardinality(Running) <= MaxPar

\* vacuity control (everything on): MUST be violated -- the whole change reaches pr-ready with all
\* three slices integrated AND a file whose content a merge made (a regenerated lockfile, a conflict
\* resolved by hand) still in the change: the hash rule's re-review path is reachable, not a wall
Delivered ==
  /\ PrReady
  /\ \A s \in Slices : status[s] = "integrated"
  /\ \E f \in Files : chg[f] = MergeVal
NeverDeliveredThroughMerge == ~Delivered

\* reachability control for D3 (everything on): MUST be violated -- every slice dropped, and the
\* change still reaches pr-ready under the ordinary rules (a fix on the change branch, an
\* integration review, an integration test-run)
AllDroppedReady == PrReady /\ \A s \in Slices : status[s] = "dropped"
NeverAllDroppedReady == ~AllDroppedReady
====
