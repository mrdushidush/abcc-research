# FLEET probe 1 — does the fleet need two slots at once, or will one after another do?

**Status: the measurement is done and it changed the milestone's premise.** Findings **F537–F547**;
next free number is **F548**. Run 2026-08-30 on the development box, champion
`qwen3.6-35b-a3b-mtp@iq3_s` at `--ctx-size 65536`, subject repository `D:\dev\abcc` at `1457ffc`.
Artifacts: `runs/fleet-p1/` — one `hw-probe` report and trace per rung, one `*-timing.txt` per arm,
one `abcc` event log per slot under `D:\dev\_fleet-p1\`.

✅ **BOTH CALLS TAKEN BY DAVID, 2026-08-30 — written up as ADR-0020 and ADR-0021.**

1. 🚨 **`--parallel 1`, ONE SLOT. Two slots are deferred, not cancelled** — *"dont need two
   slots for the time being — we will revise it in the future — right now parallel=1 is best."*
   FLEET is **descoped, not dropped**: admission, worktree isolation, the serialised gate, the
   frozen tool-head set and **retry budget 2 (enforced nowhere)** are all still owed, and with
   one slot the receiver of `Landed::next` is **a loop rather than a scheduler**.
2. 🚨 **The exit clause is replaced by *delta over a same-session baseline + `min_avail_mib` +
   the blind window*.** On the 32.83 GiB load figure below — *"that was because Chrome was
   opened during this session"* — which is F540 confirmed from the other side: the absolute
   moved with the desktop and **the delta did not**.

## The question, and why it splits in two

David asked whether FLEET requires two attempts **in flight at once** or whether they can be run
**one after another, the way every model run this project has ever made**. The milestone brief
answers neither: `PLAN.md`'s exit criterion measures only **memory**, while
`crates/abcc-gate/tests/corpus_review.rs` gives the reason nothing has ever run concurrently —
*"two turns in flight push each other past the 90 s idle gap"* — which had never been measured.

So the probe is two halves, and **only the second needs the GPU**:

1. **What the box costs.** Model resident, worktrees, and the gate's cold `cargo` build — measurable
   with no model call at all.
2. **What two turns in flight actually do to each other.** Two real `abcc run` attempts on one
   repository, one server, sequentially and concurrently.

⚠ **The probe runs one attempt per OS process, not per thread.** ADR-0006 rules that FLEET's slots
are threads inside one process; two processes each hold their own `Store`, their own `abcc`, and
their own `target/`. That makes every number here a **conservative bound** on the threaded design —
if two processes fit, two threads fit — and it keeps ADR-0005's *one writer* question out of a
measurement that is not about it.

---

## 🚨🚨 F537 — the idle gap was a CONTENT detector, and it was killing healthy turns

**The first sequential arm failed 2 of 2 with `SoftFailure { Timeout { after_ms: 90000 } }` — with
one turn in flight.** That alone retires the premise, but the reason is worse than the premise.

`hw-probe` was sampling the GPU at ~107 ms throughout. During both 90-second "silences":

| window | samples | GPU util median | ≥50% | power median |
|---|---|---|---|---|
| slot A, normal work | 466 | 61% | 86% | 92.1 W |
| **slot A, the 90 s "silence"** | 828 | **75%** | **100%** | **115.1 W** |
| slot B, normal work | 557 | 60% | 90% | 89.2 W |
| **slot B, the 90 s "silence"** | 828 | **75%** | **97%** | **115.3 W** |

**The server never stopped.** It was flatter out during the "hang" than during the work — power
pinned at 115 W ±3 W against 89 W swinging to 167 W, which is the signature of a uniform compute
loop rather than of a dead socket.

### The mechanism, and it is four lines of `openai.rs`

`OpenAiCompat::fragment` folds a tool-call argument fragment into its slot and **pushes no `Delta`**.
A `Delta::ToolCall` exists only once `finish_reason` arrives and `flush_calls` runs. So while a model
writes one large tool call — an `apply_patch` diff, which is the Builders phase's whole job — the
reader thread receives SSE bytes continuously and the consumer's `recv_timeout(idle_gap)` receives
**nothing at all**. The hang detector was measuring whether the model was producing *content*, not
whether the stream was *delivering*.

▶ **A stream delivering ~380 characters per second was called idle.**

### The falsifier is the existing test with one substitution

`tests/http.rs` already pins the property, for text:
*`a_turn_whose_body_outlasts_the_budget_completes_while_every_gap_stays_inside_it`* — six pieces
120 ms apart under a 400 ms budget must complete. Swap the text chunks for tool-call argument
fragments, change nothing else, and it fails:

```
the stream delivered a fragment every 120ms and was called idle after 400 ms
```

That test is now `a_turn_writing_only_tool_call_arguments_is_not_silent_and_must_not_read_as_a_hang`.
⚠ The existing `tool_calls_are_assembled_from_their_fragments` could never have caught this: every
one of its pauses is `Duration::ZERO`, so it asserts assembly and says nothing about time.

### The fix, and what it recovered

`Delta::ToolCallProgress { chars }` — emitted per fragment, carrying the count and nothing else,
because a half-written argument is not a request (F506) and the assembled call must still arrive
once. `Accumulator` folds it into a `tool_call_chars` total and the `LivenessMark` note now reports
it. **332 tests pass, clippy clean under `-D warnings`.**

Live, on the first run after the fix, the log tells the story every ten seconds:

```
+ 97.8s builders streaming: 0 chars of answer, 428 of trace,  1698 of tool-call arguments
+123.6s builders streaming: 112 chars of answer, 336 of trace,  3020 of tool-call arguments
+163.6s builders streaming: 112 chars of answer, 336 of trace, 19039 of tool-call arguments
+233.7s builders streaming: 112 chars of answer, 336 of trace, 44939 of tool-call arguments
```

**One turn: 45,583 argument characters, 16,384 completion tokens, 121.9 s** — and it *completed*,
ending honestly at `TruncatedAtCap { budget: 16384 }` instead of being killed at 90 s as a hang. The
longest turn of the whole session reached **213.7 s** and also completed. ⚠ **Before the fix, every
turn spending more than 90 s on one tool call was recorded as a hang, and there is no way to tell
from the log alone how many of this project's history that is.**

## F538 — a false hang and a true one look identical in the log, and the GPU tells them apart

The same session produced both, and the instrument that separates them is free:

| | GPU util median | ≥50% of samples | power median | verdict |
|---|---|---|---|---|
| pre-fix, `SEQ1` slots A and B | 75% | 97–100% | 115 W | **false — the server was working** |
| post-fix, `SEQ-F1` slot B | **0%** | **0%** | **29.1 W** | **true — the server was idle** |

Post-fix, slot B's liveness marks show the trace growing to 11,069 characters and 119 characters of
answer, then **90.3 s of genuine silence at 0% GPU.** That is the class the idle gap exists for, and
after the fix it is the only class that reaches it. ▶ **An idle-gap ending is not evidence of a hang
unless something outside the process says the server was idle.** The historic rate on this project's
own log is **2 timeouts in 27 attempts** and it is not knowable, retrospectively, which kind they
were.

## 🚨 F539 — a true hang wedges the server for every later attempt, and only a reload clears it

After `SEQ-F1` slot B's genuine stall, the next arm's **two attempts both received zero first bytes**
and died at 90 s having logged no turns, no tokens and no liveness marks at all. The GPU was at **0%
utilisation and 29.4 W for the entire 91 s**.

The server was not dead. `GET /v1/models` answered normally. `POST /v1/chat/completions` with
`max_tokens: 8` and a six-word prompt returned **nothing in 60 seconds**. `--parallel 2` gives it two
slots and *neither* was usable, so what is stuck is the server, not a slot. Only `lms load` recovered
it.

▶ **That arm (`PAR-F1`) is void and is reported as void.** It looked exactly like "two concurrent
attempts deadlock", which is the answer the milestone was looking for, and it was an artefact of the
previous arm. 🚨 **The arms now ping the server for one token before and after** —
`scratchpad/ping.sh`, recorded in every `*-timing.txt` as `PING before-<tag> ok 1s`. Without that
control a wedged server and a slow one are the same observation.

▶ **This is what FLEET's breaker is for, and it is a bigger threat to two slots than memory is:** one
hung generation costs the whole fleet, not one attempt, and nothing in `abcc` detects or reports it.

---

## The memory half — measured with no model call at all

Every row is this session, `hw-probe` with `--pid` on `llama-server`. ⚠ **The peak is a maximum over
samples and the blind window is printed beside it**; the host stream's floor is `typeperf`'s 1 s.

| rung | wall | peak commit | min available | peak VRAM | host blind window |
|---|---|---|---|---|---|
| R0 — idle, nothing loaded | 30.1 s | **17.58 GiB** | 17,562 MiB | 1,763 MiB | 1,012 ms |
| R1 — `lms load … --parallel 2 -c 65536` | 12.6 s | 32.83 GiB | 17,020 MiB | 15,613 MiB | 1,016 ms |
| R1b — resident, idle | 20.0 s | 32.82 GiB | 17,043 MiB | 15,806 MiB (96.9%) | 1,041 ms |
| R2 — **one** cold gate walk | 91.0 s | 38.03 GiB | 13,363 MiB | 15,890 MiB | 3,714 ms |
| R3 — **two concurrent** cold gate walks | 147.6 s | **42.14 GiB** | 14,315 MiB | 15,846 MiB | **19,640 ms** |

A gate walk is the three rungs `abcc-gate` declares for a cargo repository
(`workspace.rs:187-196`), cold, in a fresh worktree: `cargo check --all-targets`, `cargo test`,
`cargo clippy --all-targets -- -D warnings`.

### 🚨 F540 — the 28.03 GiB ceiling of record is not portable, and the exit clause has to say so

**This session's idle baseline is 17.58 GiB. Session 19's was 8.99 GiB** (ACCEPTANCE-B). Loading the
model reached **32.83 GiB before a single attempt ran** — 4.8 GiB past the "ceiling" the milestone
says the whole run must stay under.

Nothing is wrong. The *delta* reproduces: this session's load costs **15.24 GiB** over its own
baseline against session 19's **16.01 GiB** for the same serving configuration. What moved is what
else David had open. ▶ **F488 said quote a peak against its own session's baseline; the exit clause
then quotes an absolute from a different session, and the two cannot both be obeyed.** The clause
should read: *the workload's delta over a same-session baseline, plus `min_avail_mib`, plus the blind
window.* An absolute commit figure is a fact about the desktop, not about the fleet.

### F541 — `--parallel 2` costs 187 MiB, because `--kv-unified` pools the window

From `llama-server`'s own command line (F86 — the only complete witness): `--ctx-size 65536
--parallel 2 --kv-unified --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --spec-type
draft-mtp`. On-card, resident and idle: **14,472 MiB at `--parallel 2`** against **13.95 GiB
(14,285 MiB) at `--parallel 1`** in session 19's `resident-65k-idle`.

▶ **The second slot is 187 MiB.** F83's `Σ(active sequence lengths) ≤ ctx` holds: slots pool the
window rather than dividing it, so a second slot buys concurrency without buying KV. **The slot count
is not a memory decision.**

### F542 — the gate is the memory event, and serialising it is now a measured ruling

`PLAN.md` requires the gate serialised and gave no number for it. Two cold walks:

| | wall | peak commit | host blind window |
|---|---|---|---|
| serialised (2 × R2) | 182.0 s | 38.03 GiB | 3,714 ms |
| concurrent (R3) | **147.6 s** | **42.14 GiB** | **19,640 ms** |

▶ **Serialising the gate costs 34.4 s (23%) and buys 4.1 GiB of commit and a 5× better
responsiveness figure.** Concurrent builds are only 1.23× faster because they contend: each walk
slowed from 91 s to 147 s. ⚠ And R3's peak is a **lower bound with a 19.6 s blind window** — the true
peak is unknown and higher.

### F543 — `max_gap_ms` on the host stream is the responsiveness instrument the exit clause lacked

*"Box still responsive"* has never had a measurement. It has one for free: **the widest gap
`typeperf` itself experienced**, already printed beside every peak. Idle **1.0 s** · one cold build
**3.7 s** · two concurrent cold builds **19.6 s**. When a platform-built-in sampler asking for one
sample per second cannot get scheduled for nineteen seconds, the box is not responsive, and no
person had to be sitting in front of it to say so.

### F544 — `hw-probe`'s host source has no `warm_up`, and one arm was lost to it

`PAR-F2` completed and reported `peak_committed_b: null`: **the host source produced zero samples**
while the GPU source produced 854. F63 fixed exactly this for the GPU stream —
`GpuSource::warm_up` blocks until one real sample arrives and otherwise fails loudly — and the host
stream never got the same treatment. ✅ It reported `null` rather than `0`, so the `Reading` discipline
held and nothing false was written down; the cost was a re-run, not a wrong number.

---


## The concurrency half — six arms, two of them clean and matched

Every arm is the **same two real tasks** on `D:\dev\abcc`: *add a `--version` flag to the binary*
and *add a `--paths-only` flag to `abcc where`*. One slot each, fresh home and fresh queue per arm,
one `llama-server` at `--parallel 2` serving both. `seq` runs them one after another; `par` starts
them together and waits for both.

| arm | mode | wall | slot A | slot B | peak commit | min avail | max TTFB A / B | endings |
|---|---|---|---|---|---|---|---|---|
| `SEQ1` *(pre-fix)* | seq | 311 s | 143 s | 168 s | 35.07 GiB | 14,847 MiB | 3.3 / 4.4 s | **2 false timeouts** |
| `SEQ-F1` | seq | 393 s | 236 s | 156 s | 38.18 GiB | 12,004 MiB | 4.1 / 5.0 s | cap · **1 true hang** |
| `PAR-F1` | par | 91 s | 91 s | 91 s | — | — | — | 🚨 **VOID — wedged server** |
| `PAR-F2` | par | 378 s | 378 s | 282 s | *(null — F544)* | — | 5.2 / 9.2 s | cap · rounds |
| **`SEQ-F2`** | **seq** | **1,113 s** | 456 s | 656 s | **50.60 GiB** | **3,155 MiB** | 8.6 / **30.3 s** | rounds · **refused** |
| **`PAR-F3`** | **par** | **1,006 s** | 1,004 s | 866 s | **50.02 GiB** | **2,976 MiB** | 12.1 / 25.5 s | **refused** · rounds |

`SEQ-F2` and `PAR-F3` are the clean matched pair: same server, health-checked at both ends, host
counters present, no false timeouts.

### 🚨 F545 — two turns in flight do not approach the 90 s gap, and the worst wait of the session was SEQUENTIAL

**Max time to first byte, concurrent: 25.5 s. Max sequential: 30.3 s.** Across the four post-fix arms —
**171 model calls started, 170 ended, and the one that did not is the true hang of F538** — there is
not one timeout that concurrency caused, and the single worst
first-byte wait of the whole session happened with one turn in flight.

The variable is **prompt size, not slot count**. `SEQ-F2` slot B's 30.3 s wait is a ~30,000-token
prompt at the champion's measured prefill rate; the Builders phase reaches 24 rounds and its context
grows every round. ▶ **The premise in `corpus_review.rs` — *two turns in flight push each other past
the 90 s idle gap* — is retired. It was never measured, and it is false.** ⚠ What *can* reach the gap
is a single cold prefill of a very large prompt; at 65,536 tokens that is arithmetically within
reach, and it is a reason to watch the window rather than the slot count.

### 🚨🚨 F546 — the throughput question is NOT resolvable at this sample size, and the two pairs disagree in sign

Completion tokens per second of arm wall clock, which normalises over the fact that no two attempts
do the same amount of work:

| pair | sequential | concurrent | concurrent is |
|---|---|---|---|
| `SEQ-F1` vs `PAR-F2` | 26,148 tok / 393 s = **66.6 tok/s** | 31,227 tok / 378 s = **82.6 tok/s** | **+24%** |
| `SEQ-F2` vs `PAR-F3` | 38,799 tok / 1,113 s = **34.9 tok/s** | 29,063 tok / 1,006 s = **28.9 tok/s** | **−17%** |

**The two pairs point opposite ways, and the reason is visible in the same table:** the *same arm*
on the *same two tasks* ran **393 s and 1,113 s** (sequential, 2.8× apart) and **378 s and 1,006 s**
(concurrent, 2.7× apart). **Within-arm variance is 2.7–2.8×; the between-arm difference is 1.1×.**

▶ **A difference eight times smaller than the noise is not a measurement.** Nothing here samples at
temperature zero — the engine sends no `temperature`, no `top_p` and no `seed` — so an attempt takes
5 rounds or 24 depending on the sample, and wall clock follows. Settling this would need many
repetitions per arm, and **it is not worth them**, because the answer below does not depend on it.

### F547 — concurrency costs no measurable memory; the gate costs all of it

`SEQ-F2` **50.60 GiB peak commit, 3,155 MiB minimum available** against `PAR-F3` **50.02 GiB and
2,976 MiB**. The
two arms are **0.58 GiB apart, with the sequential one higher**, and the concurrent arm was the
*less* responsive-limited of the two (host blind window 5.2 s against 7.5 s).

▶ **Running two attempts at once did not cost memory. Running the gate did.** Both arms build; that
is the whole bill, and F542 already priced it. ⚠ **The floor is `min_avail_mib` ≈ **2,976 MiB** —
under 3 GiB of free physical RAM on a 31.92 GiB box, in *both* modes. That is the number the fleet
has to respect, and adding a slot does not move it.**

---

## What this settles for FLEET

**Both scenarios work.** Post-fix, four arms and eight attempts ran to honest endings with the server
healthy before and after: **2 `TruncatedAtCap`, 3 `BudgetExhausted { 24 rounds }`, 2 `Refused` at the
standard rung, 1 true hang.** No successes, and the two that got furthest are worth reading twice:

> `structural` exit 0 · `acceptance` exit 0, **333 of 333 and 334 of 334 tests passed** · `veto`
> nothing vetoed · `standard` **exit 101 — `this function has too many lines (102/100)`**

**Both were working code that passed the entire suite and was refused only by the repository's own
declared standard** — F512 reproducing exactly, now under both modes, with the Judge reporting after
each.

### The rulings this supports

1. ✅ **RULED: `--parallel 1`, one slot, revisit later (ADR-0020).** F546 says the wall-clock
   difference is unmeasurable against the noise; F545 says nothing *blocks* concurrency; F547 says
   nothing pays for it in memory. So the second slot had to be justified by what the operator sees
   rather than by a number, and David's answer is **not yet**. ⚠ **ADR-0003's own falsifier did
   NOT fire** — two slots plus two worktrees plus real builds *held* inside 31.92 GiB. The count
   drops for the opposite reason: the second slot bought nothing measurable.
2. ✅ **The gate stays serialised, and now for a measured reason** (F542): 34.4 s against 4.1 GiB and
   a 5× better responsiveness figure.
3. 🚨 **`Deployed`'s reaper is not enough — the fleet needs a server health check that is a real
   generation** (F539). A wedged server answers `/v1/models` normally and takes down every slot at
   once; `NextAction::Attempt` with retry budget 2 would spend both retries against a server that
   cannot answer. **The breaker's input is a one-token completion, not a liveness endpoint.**
4. ✅ **RULED: the exit criterion is rewritten (ADR-0020, `PLAN.md` § FLEET).** *Peak under
   28.03 GiB* was violated by loading the model in this session — **because Chrome was open, which
   is David's own account and is the point**: the absolute tracked the desktop while the delta
   reproduced to within 0.8 GiB. F488 forbids the cross-session comparison that would have made the
   old clause meaningful. It is now **delta over a same-session baseline + `min_avail_mib` + the
   blind window** (F540, F543).
5. ⏸ **The 120 s idle-gap candidate is answered and it is the wrong question.** The gap never fired
   because of concurrency; it fired because it was the wrong instrument (F537) and once because the
   server genuinely stopped (F538). **Raising 90 s to 120 s would have hidden the bug and kept the
   true hang undetected 30 s longer.** Leave it at 90 s.
6. ▶ **The dominant failure mode is not the fleet's.** Five of eight attempts ended at a budget —
   one tool call eating 16,384 tokens, or 24 rounds of context growth to half a million prompt
   tokens. **That is a Builders-phase problem and it is what FLEET's throughput would be spent on.**

### What was changed in `D:\dev\abcc`

`Delta::ToolCallProgress { chars }` in `provider.rs`, emitted from `OpenAiCompat::fragment` in
`openai.rs`, folded by `Accumulator` and reported in the `LivenessMark` note in `turn.rs`, plus the
falsifying test in `tests/http.rs`. **332 tests pass, 10 ignored, clippy clean under `-D warnings`,
rustfmt clean.**

### The `Retires` clause: retired, and barely

*"Two slots plus a worktree plus a real build cannot hold inside 31.92 GiB"* — **it held.** `PAR-F3`
ran two attempts, two worktrees and real `cargo` builds concurrently beside a resident 14 GiB model
and never ran out: **minimum available 2,976 MiB**, no failure attributable to memory, `typeperf`'s
widest blind window **5.2 s**. ⚠ **And "held" is doing work in that sentence**: peak commit reached
**50.02 GiB against 31.92 GiB of physical RAM**, so the box was paging, and 2.9 GiB of headroom on a
32 GiB machine is not comfort. The hypothesis is retired; the margin is not generous.

### Two loose ends this probe leaves

* ⏸ **`--parallel 1` versus `--parallel 2` was never compared under load.** Everything post-`R1` ran
  against one `--parallel 2` server, on the reasoning that a sequential arm on a two-slot server uses
  one slot and is therefore equivalent — which F541's 187 MiB supports but does not prove. The
  falsifier is one reload and one `SEQ` arm.
* ⏸ **The wedge has one occurrence and no cause.** It followed a genuine stall, it survived every
  request but `/v1/models`, and `lms load` cleared it. One event is one event; what it justifies now
  is the health check (F539), not a theory.
