---- MODULE ReviewPace ----
(***************************************************************************)
(* ADR-062 decisions 1-2 (review tiers, diff-scoped re-review), modelled   *)
(* BEFORE 2.16.0 writes them. Started from a copy of                       *)
(* docs/gate-integrity/models/GatedDebt.tla at commit a9ea294; the 2.15.1  *)
(* rules GatedDebt switches with V211, DeferFix and MemoryFix are fixed    *)
(* ON here, as shipped.                                                    *)
(*                                                                         *)
(* The engine sees only the ledger: test-runs and log-steps, each with the *)
(* tool, the files it reviewed (scope), the reviewed tree and the deferral *)
(* state. Ground truth it cannot see: which file content holds a gated bug *)
(* and what the ledger has been told is flagged (flagged).                 *)
(*                                                                         *)
(* Rule (NoFlaggedBugShips): pr-ready never holds while the files a gated  *)
(* step covered carry exactly the content that step flagged, unless the    *)
(* finding is deferred. With one file and one tool it is GatedDebt's rule. *)
(*                                                                         *)
(* Kept from GatedDebt with the same meaning: Witness, Anchor, Lies,       *)
(* Memory. New constants; with Wide, Tiers, DiffScope, CoverFix, Locate    *)
(* FALSE, NTools = 1, RaiseTo = 0 and Defers TRUE the module IS GatedDebt  *)
(* (ci-baseline: the same 2,936,010 distinct states).                      *)
(*   Wide      two files: a (holds the bug, touched by every fix) and b    *)
(*             (never buggy, the unrelated file), each with contents 0..1. *)
(*             FALSE: GatedDebt's single file, contents 0..2.              *)
(*   NTools    tool 1 may flag; tool 2 (NTools = 2) never flags.           *)
(*   Tiers     decision 1: the tier is the highest glob tier of the files  *)
(*             the change touches (a -> quick, b -> GlobB) or the tier the *)
(*             agent raised it to (up to RaiseTo). quick = {tool 1};       *)
(*             standard = deep = every tool. FALSE: every change is deep.  *)
(*   TierHighWater  the tier is the highest the change ever reached: an    *)
(*             edit that touches a higher-glob file raises `raised` too,   *)
(*             so reverting it does not lower the tier. FALSE: the tier is *)
(*             computed from the files touched NOW (a revert lowers it).   *)
(*   DiffScope decision 2: a review may cover any non-empty subset of the  *)
(*             files (the agent picks; the engine only reads the log). In  *)
(*             quick/standard convergence is C1 /\ C2; in deep it is       *)
(*             today's rule plus "each tool's last review was whole".      *)
(*             FALSE: every review covers every file.                      *)
(*   Rereview  clause C2 of decision 2.                                    *)
(*   SameTool  C2's re-review must come from the tool whose clean pass the *)
(*             change outdated. FALSE: "by at least one agent tool", as    *)
(*             the ADR first worded it.                                    *)
(*   TierTools C2's re-review and the latest step Anchor reads count only  *)
(*             tools of the tier. FALSE: any tool.                         *)
(*   WholeFirstPass  in quick/standard every tool of the tier must have a  *)
(*             witnessed review whose scope was the whole change.          *)
(*   CoverFix  the fix TLC forced (README): a gated step's debt and Memory *)
(*             read the files it covers -- a clean step closes the debt    *)
(*             only if it covered them and they moved, and contradicts the *)
(*             gated step if it covered them unchanged.                    *)
(*             FALSE: whole-tree, as 2.15.1.                               *)
(*   Locate    a gated step records the files its findings are in (the id  *)
(*             carries the path) and covers only those. FALSE: it covers   *)
(*             its whole scope.                                            *)
(*   Defers    the agent may add / remove a deferral (2.11.0's moves).     *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS MaxLog, Anchor, Lies, Witness, Memory,
          Wide, NTools, Tiers, GlobB, RaiseTo, DiffScope, Rereview, SameTool, CoverFix, Locate,
          Defers, TierHighWater, TierTools, WholeFirstPass

Files == IF Wide THEN {"a", "b"} ELSE {"a"}
Tools == 1..NTools
Range(f) == IF Wide THEN 0..1 ELSE 0..2
Trees == IF Wide THEN [a : 0..1, b : 0..1] ELSE [a : 0..2]
T0 == IF Wide THEN [a |-> 0, b |-> 0] ELSE [a |-> 0]
\* ground truth: content 0 of file a holds the gated bug
Bug(f, v) == f = "a" /\ v = 0
\* tiers: 0 quick, 1 standard, 2 deep
Glob(f) == IF f = "a" THEN 0 ELSE GlobB
ToolsOf(k) == IF k = 0 THEN {1} ELSE Tools

NoReview == [tool |-> 0, scope |-> {}, tree |-> T0, gated |-> 99, def |-> 99]

VARIABLES tree, deferred, log, pending, flagged, raised
vars == <<tree, deferred, log, pending, flagged, raised>>

MaxOf(S) == CHOOSE m \in S : \A k \in S : k <= m
TouchedIn(t) == {"a"} \cup {f \in Files : t[f] /= T0[f]}
GlobTier(t) == MaxOf({Glob(f) : f \in TouchedIn(t)})
Tier == IF Tiers THEN MaxOf({GlobTier(tree), raised}) ELSE 2
DiffMode == DiffScope /\ Tier < 2

Init ==
  /\ tree = T0
  /\ deferred = 0
  /\ log = <<>>
  /\ pending = NoReview
  /\ flagged = {}
  /\ raised = 0

Rec(kind, t, s, g) == [kind |-> kind, tool |-> t, scope |-> s, tree |-> tree,
                       def |-> deferred, gated |-> g, wit |-> FALSE]

\* the files a gated record covers (Locate: only the files its findings are in)
FS(r) == IF Locate THEN {f \in r.scope : Bug(f, r.tree[f])} ELSE r.scope
Know(r) == [files |-> FS(r), tree |-> r.tree]
Match(k, t) == \A f \in k.files : t[f] = k.tree[f]

\* the agent edits one file: a fix, an unrelated change, or a revert
Edit(f, v) ==
  /\ v /= tree[f]
  /\ tree' = [tree EXCEPT ![f] = v]
  \* TierHighWater: the highest tier the change reached stays (only a human lowers it)
  /\ raised' = IF Tiers /\ TierHighWater THEN MaxOf({raised, GlobTier(tree')}) ELSE raised
  /\ UNCHANGED <<deferred, log, pending, flagged>>

\* decision 1: the agent may raise the tier, never lower it
Raise(k) ==
  /\ Tiers
  /\ k > raised
  /\ raised' = k
  /\ UNCHANGED <<tree, deferred, log, pending, flagged>>

\* the agent adds an entry to ISSUES-DEFERRED.md
Defer ==
  /\ Defers
  /\ deferred = 0
  /\ deferred' = 1
  /\ UNCHANGED <<tree, log, pending, flagged, raised>>

\* test-run: the engine records a stamp of the tree
TestRun ==
  /\ Len(log) < MaxLog
  /\ log' = Append(log, Rec("run", 0, {}, 0))
  /\ UNCHANGED <<tree, deferred, pending, flagged, raised>>

\* a tool reviews the files it is given; its verdict waits to be logged. The agent picks the
\* tool and, with DiffScope, the files: the engine does not stop it, it only reads the log.
Review(t, s) ==
  /\ pending = NoReview
  /\ s /= {}
  /\ DiffScope \/ s = Files
  /\ pending' = [tool |-> t, scope |-> s, tree |-> tree,
                 gated |-> IF t = 1 /\ \E f \in s : Bug(f, tree[f]) THEN 1 ELSE 0,
                 def |-> deferred]
  /\ UNCHANGED <<tree, deferred, log, flagged, raised>>

\* log-step with the counts the review produced
StepRec(g) == IF Witness THEN [kind |-> "step", tool |-> pending.tool, scope |-> pending.scope,
                               tree |-> pending.tree, def |-> pending.def, gated |-> g,
                               wit |-> TRUE]
              ELSE Rec("step", pending.tool, pending.scope, g)

LogHonest ==
  /\ pending /= NoReview
  /\ Len(log) < MaxLog
  /\ log' = Append(log, StepRec(pending.gated))
  /\ pending' = NoReview
  \* the ledger now KNOWS the reviewed files hold a gated finding
  /\ flagged' = IF pending.gated > 0 THEN flagged \cup {Know(pending)} ELSE flagged
  /\ UNCHANGED <<tree, deferred, raised>>

\* narration: a clean step no review produced
LogClaimClean ==
  /\ Lies
  /\ Len(log) < MaxLog
  /\ \/ /\ pending /= NoReview
        /\ log' = Append(log, StepRec(0))
     \/ /\ ~Witness /\ pending = NoReview
        /\ \E t \in Tools : log' = Append(log, Rec("step", t, Files, 0))
  /\ pending' = NoReview
  /\ UNCHANGED <<tree, deferred, flagged, raised>>

\* the agent removes a deferral it added (2.11.0)
Undefer ==
  /\ deferred = 1
  /\ deferred' = 0
  /\ UNCHANGED <<tree, log, pending, flagged, raised>>

\* a gated step logged with NO review (2.11.0): the ledger knows the logged tree is flagged
LogUnwitnessedGated ==
  /\ \E f \in Files : Bug(f, tree[f])
  /\ Len(log) < MaxLog
  /\ log' = Append(log, Rec("step", 1, Files, 1))
  /\ flagged' = flagged \cup {Know(Rec("step", 1, Files, 1))}
  /\ UNCHANGED <<tree, deferred, pending, raised>>

Next ==
  \/ \E f \in Files : \E v \in Range(f) : Edit(f, v)
  \/ \E k \in 1..RaiseTo : Raise(k)
  \/ \E t \in Tools : \E s \in SUBSET Files : Review(t, s)
  \/ Defer \/ TestRun \/ LogHonest \/ LogClaimClean
  \/ Undefer \/ LogUnwitnessedGated

Spec == Init /\ [][Next]_vars

(* ---------------- what the ENGINE derives from the ledger ---------------- *)
IsStep(i) == log[i].kind = "step"
Steps == {i \in 1..Len(log) : IsStep(i)}
Runs == {i \in 1..Len(log) : log[i].kind = "run"}
Max(S) == CHOOSE m \in S : \A k \in S : k <= m
StepsOf(t) == {i \in Steps : log[i].tool = t}
HasStep(t) == StepsOf(t) /= {}
Last(t) == Max(StepsOf(t))
Clean(i) == log[i].gated = 0 /\ log[i].wit

\* the baseline of a gated step (GatedDebt): witnessed -> its reviewed tree; else its logged one
Base(i) == IF Witness THEN i ELSE IF i > 1 THEN i - 1 ELSE i
Origin(i) == log[IF ~log[i].wit THEN i ELSE Base(i)]

\* the files whose movement can close step i's debt
DebtFiles(i) == IF CoverFix THEN FS(log[i]) ELSE Files
Moved(i, c) ==
  \/ \E f \in DebtFiles(i) : Origin(i).tree[f] /= log[c].tree[f]
  \* a deferral closes a debt only when the clean review SAW one (DeferFix, 2.11.0)
  \/ (Origin(i).def /= log[c].def /\ log[c].def /= 0)
Covers(i, c) == CoverFix => FS(log[i]) \subseteq log[c].scope

\* per tool, as the engine's _review_verdicts
DebtOpen(i) ==
  /\ IsStep(i)
  /\ log[i].gated > 0
  /\ ~\E c \in (i + 1)..Len(log) :
        IsStep(c) /\ log[c].tool = log[i].tool /\ Clean(c) /\ Covers(i, c) /\ Moved(i, c)

SameContent(i, c) ==
  IF CoverFix THEN FS(log[i]) \subseteq log[c].scope
                   /\ \A f \in FS(log[i]) : log[i].tree[f] = log[c].tree[f]
  ELSE log[i].tree = log[c].tree

\* a clean step that contradicts an earlier gated verdict of the same tool on the same content
Contradicts(c) == \E i \in 1..(c - 1) :
  IsStep(i) /\ log[i].tool = log[c].tool /\ log[i].gated > 0 /\ SameContent(i, c)
  /\ (log[i].def = log[c].def \/ log[c].def = 0)          \* MemoryFix, 2.11.0

\* decision 2, quick/standard. C1: every tool of the tier had one clean pass (any scope) ...
C1 == \A t \in ToolsOf(Tier) : \E c \in StepsOf(t) : Clean(c)
\* ... C2: every file changed after a tool's clean pass was reviewed clean again, after it, at
\* its current content, by at least one agent tool (SameTool: by that same tool)
C2 == \A c \in Steps :
        (Clean(c) /\ log[c].tool \in ToolsOf(Tier)) =>
          \A f \in Files : tree[f] /= log[c].tree[f] =>
            \E d \in Steps : d > c /\ Clean(d) /\ f \in log[d].scope
                             /\ log[d].tree[f] = tree[f]
                             /\ (SameTool => log[d].tool = log[c].tool)
                             /\ (TierTools => log[d].tool \in ToolsOf(Tier))

\* WholeFirstPass: every tool of the tier had a witnessed review of the whole change
WholePass == \A t \in ToolsOf(Tier) : \E c \in StepsOf(t) : log[c].wit /\ log[c].scope = Files
\* the step Anchor reads (TierTools: the latest step of a tool of the tier)
AnchorSteps == IF TierTools THEN {i \in Steps : log[i].tool \in ToolsOf(Tier)} ELSE Steps

\* Anchor and the 2.11.0 clauses, on one step
LatestOk(L) == L.gated = 0 /\ L.wit /\ L.def = deferred /\ (Anchor => L.tree = tree)

Converged ==
  /\ Steps /= {}
  /\ ~\E i \in 1..Len(log) : DebtOpen(i)
  /\ (Memory => \A t \in Tools : HasStep(t) => ~(Clean(Last(t)) /\ Contradicts(Last(t))))
  /\ IF DiffMode
       \* the latest step stands for the latest cycle (Anchor reads the tools of the cycle)
       THEN /\ AnchorSteps /= {}
            /\ LatestOk(log[Max(AnchorSteps)])
            /\ C1
            /\ (WholeFirstPass => WholePass)
            /\ (Rereview => C2)
       \* today's rule: the last step of every tool of the tier is clean, on the tree on disk
       ELSE \A t \in ToolsOf(Tier) :
              /\ HasStep(t)
              /\ LatestOk(log[Last(t)])
              /\ (DiffScope => log[Last(t)].scope = Files)

TestsCurrent == Runs /= {} /\ log[Max(Runs)].tree = tree

PrReady == Converged /\ TestsCurrent

(* ---------------- the rule ---------------- *)
TypeOK ==
  /\ tree \in Trees
  /\ deferred \in {0, 1}
  /\ raised \in 0..2
  /\ \A k \in flagged : k.files \subseteq Files

NoFlaggedBugShips == PrReady => ~(deferred = 0 /\ \E k \in flagged : Match(k, tree))
\* vacuity control: this MUST be violated -- a legitimate fix still reaches pr-ready, and with
\* tiers and diff scope on, in the quick tier and through a diff-scoped review
NeverFixedAndReady == ~(PrReady /\ flagged /= {}
                        /\ (Tiers => Tier = 0)
                        /\ (DiffScope => \E i \in Steps : log[i].scope /= Files))
\* lowering control (GlobB = 2): MUST be violated -- the change touched the deep file b, the agent
\* reverted it, and a known finding was legitimately fixed to pr-ready
NeverRevertedAndReady == ~(PrReady /\ flagged /= {} /\ tree["b"] = T0["b"]
                           /\ \E i \in 1..Len(log) : log[i].tree["b"] /= T0["b"])
\* TierHighWater's property (GlobB = 2): a change that once touched the deep file b converges only
\* on the deep rule -- never on the quick tool list after a revert
LoweredNeverReady == (PrReady /\ \E i \in 1..Len(log) : log[i].tree["b"] /= T0["b"]) => Tier = GlobB
\* TierTools's property: in quick/standard at pr-ready, the latest step of a tool OF THE TIER saw
\* the tree on disk (a step of a tool outside the tier does not stand in for it)
TierAnchored == (PrReady /\ DiffMode) =>
                  LET A == {i \in Steps : log[i].tool \in ToolsOf(Tier)}
                  IN A /= {} /\ log[Max(A)].tree = tree
\* WholeFirstPass's property: at pr-ready every tool of the tier has reviewed every file
EveryFileReviewed == PrReady => \A t \in ToolsOf(Tier) : \A f \in Files :
                       \E i \in StepsOf(t) : log[i].wit /\ f \in log[i].scope
\* the same, in the standard tier and with a step of the second tool (two-tool configs)
NeverFixedAndReadyStandard == ~(PrReady /\ flagged /= {} /\ Tier = 1
                                /\ \E i \in Steps : log[i].tool = 2)
====
