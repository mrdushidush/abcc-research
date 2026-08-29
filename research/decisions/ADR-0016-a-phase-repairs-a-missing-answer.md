# ADR-0016 — A phase asks again when the model says nothing, and a cut turn's tool calls are never run

- **Status:** ✅ Accepted
- **Date:** 2026-08-29
- **Deciders:** David (two rulings, 2026-08-29), written by Claude Code
- **Sources:** F503 (the population), F505 (the capture that diagnosed it), F506 (the cut turn),
  F507 (the nudge measured), F508 (the first working artifact) · F499 carried the ruling this
  applies · the runs are attempts `a8`–`a645` on
  `%LOCALAPPDATA%\abcc\abcc-1ae35b6091a63e2c\log.sqlite`
- **Extends:** ADR-0010 (a retry is this body with the failure appended), ADR-0015 (this is the
  observation its falsifier named)
- **Depends on:** ADR-0009 (`Unmeasured(Why)` is still where a phase ends)

## Context

ADR-0015 shipped `Why::SaidNothing` and wrote its own falsifier: *"an empty answer that is
reliably retryable in place would move `SaidNothing` from a phase ending to a within-phase
retry."* **It fired the same day**, and the ten runs that fired it are the whole of this record.

### The population, which is the only reason any of this is a decision

Ten attempts at **one task** — *"Add a `--version` flag to the abcc binary…"* — champion
`qwen3.6-35b-a3b-mtp@iq3_s`, 32,768 window, `--parallel 1`. ⚠ The 16,384 that killed the first
run was `numParallelSessions` dividing a 65,536 load by four; the window an operator loads is not
the window a conversation gets.

| | runs 1–7 (before) | runs 8–10 (after) |
|---|---|---|
| ended with no closing answer | **5 of 7** | **0 of 3** |
| Localize handed anything to Change | 3 of 7 | **3 of 3** |
| produced a change | 1 (incomplete) | **1 complete, verified** |

🚨 **F503 — the system's dominant failure was a missing closing sentence, not a missing
capability.** Four of seven runs never reached the Change phase, because Localize produced no
artifact to hand over. The turns that failed emitted **7, 5, 5 and 9 tokens** of non-reasoning
output: the model reasons to the end and treats the thinking as the deliverable.

✅ **The positive control is inside the experiment.** The same head, brief, server, model and code
path captured a **3,431**-character Recon claim on `a8` and **2,008** on `a162`. Nothing is lost
in transit — the model answers sometimes and not others, so **one absence is a sample, not a
verdict.** ⚠ F502: ADR-0010 §7's `OpenAt200` signal is the same condition detected worse — it
needs 200 completion tokens and would have missed Recon's 47 entirely.

### The other half: a cut turn is not a request

🚨 **F506 — both contentless HTTP 500s on this log are ours.** `a422` hit **our own 8,192 cap**
mid-tool-call; the fragment reached `apply_patch` with a **zero-character** argument string and
was recorded as the model failing its own schema; the malformed assistant turn went onto the body;
the next request came back `500` with a nine-line boilerplate page. **The window cannot explain
it: 8,209 + 8,192 = 16,401 against 32,768.** It fell through both guards — the overflow branch
needs `completion < budget` (exactly equal) and the cap branch needed `content_empty` (there was
content). ⚠ Diagnosed only because **F505** had started keeping a refused call's arguments, on its
first live run.

## Decision

🚨 **A phase repairs a missing answer before it ends, and never executes a fragment.**

1. **`Limits::nudges`, default 2.** A turn that finishes cleanly with an empty payload appends the
   empty turn and one sentence to the body, and the phase asks again. The sentence names the
   mechanism rather than scolding — *the reasoning is not visible and the reply is* — and it goes
   on the **end** of the body, never into the head, because one token changed at the front costs
   the whole 79.7% prefix-cache saving (F81).
2. **Exhausting the nudges still ends the phase `Why::SaidNothing`.** The falsifier is answered
   without reversing the ruling it questioned: the ending stays, and a repair happens first.
3. **`Event::PhaseNudged` puts it on the log.** A repair that fires on 8 of 10 phases and leaves
   no trace makes every later transcript a record of a conversation nobody can reconstruct.
4. **`Finish::Length` is uncertain always**, and `content_empty` selects the sentence rather than
   deciding whether there is one. A payload cut mid-token is a fragment and **a tool call cut
   mid-argument is not a request**, so the phase ends and none of its calls run — David's F499
   ruling, applied to the branch it had not reached.
5. **A failed tool call keeps its arguments on the log; a successful one does not**, and a
   *denied* one does not either — ADR-0014's control is the class, and recording the arguments of
   a tool a role may not have invites the argument-level reasoning W7 ruled against.

## Consequences

- ✅ **F507: five nudges, five recoveries, zero exhausted.** Every `PhaseNudged` reads `left: 1`,
  so the *first* one worked every time. Recon went silent on its first turn in 3 of 3 runs and
  answered after one nudge in 3 of 3. It is the highest-leverage line written in Phase 3.
- 🎉 **F508: the champion implemented the feature, and it works.** `a645`, checkpoint `491f07f2`,
  three files, +16/−3 — and it **found and fixed the exhaustive-match test its own change broke**.
  Verified by hand at that sha: compiles, **all 64 `abcc` tests pass**, `abcc --version` prints
  `0.1.0` and exits 0, rustfmt clean. ⚠ **It fails `clippy -D warnings` by one line** (`parse` is
  101 against a 100 limit) — the Gate demonstrated before the Gate exists, and precisely the shape
  ADR-0009 wants: correct work refused by a *deterministic* rung on a real rule.
- ⚠ **A phase can now cost three model calls where it cost one.** Bounded and small, and the
  measured price of the alternative is a phase that produces nothing 5 times in 7.
- ⚠ **`TruncatedAtCap` widens** to a cap-cut that carries content. Stated rather than hidden; the
  alternative was a known path that ends `HardFailure` on a 500 this project causes.
- **A complete tool call on a cut turn is discarded** (F499). On `a8` that was `apply_patch`
  succeeding with a real 6-line change. The trade is David's and he took the conservative side.

## Alternatives rejected

- **Rewrite the brief and change nothing else.** W7's standing lesson is that *a prompt binds only
  as far as the model complies* — shipped 39/50, best candidate 0/50. The nudge is a control that
  fires on the observed failure rather than a hope that it stops happening.
- **Schema-constrained decoding on the closing turn.** It works and is unused (W1/W2), and it
  would make an empty answer unrepresentable — but the same turn may legitimately still want a
  tool, and constraining it would deny that. Kept for the Gate's artifacts.
- **Move `SaidNothing` to a pure within-phase retry**, as ADR-0015's falsifier literally proposed.
  Rejected because a model that says nothing three times running is a real ending an operator
  needs to see, and deleting the class to add the repair would trade one honest sentence for none.
- **Stop on the `OpenAt200` signal.** F502: strictly weaker, and ADR-0010 §7 says it is a record.

## What would falsify this

- **A nudge rate that stops falling.** Five of five is a small population; if the recovered
  answers turn out to be worse than the ones that arrive unprompted — shorter, vaguer, or wrong —
  then the repair is buying a sentence rather than an artifact, and the brief is the fix after all.
- **A phase nudged into a loop**: an empty answer that repeats because the nudge itself is what
  the model cannot answer. `PhaseNudged` on the log is what makes that visible.
- **A `length` finish whose tool calls are complete and valuable often enough to matter** would
  reopen consequence 5 and F499 with it.
