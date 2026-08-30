# FLEET closes — a ceiling per slot, a breaker with a real pulse, and the bill, measured

**Status: FLEET's four remaining items are done and its exit clause is met.** Findings
**F550–F556**; next free number is **F557**. Built 2026-08-30 against `D:\dev\abcc` at `8cd9681`,
landed as `ac02ff5` (the slot ceiling) and `6fbaf4f` (the breaker). **368 tests passing, 10 ignored,
clippy clean under `-D warnings`, rustfmt clean.** The measurement is four `hw-probe` arms on the
champion, `qwen3.6-35b-a3b-mtp@iq3_s` at `PARALLEL 1`, context 65536.

Two of the four items were verification rather than construction, and **checking first was worth
it**: the frozen head set was already built and tested, and the falsifier the plan wrote for the
slot ceiling rests on a premise that is false in the shipped code (F551). Building on that premise
would have shipped a foot-gun.

▶ **And the retry budget was spent for real, on the GPU, for the first time.** The first measured
sortie flew two attempts on one task — `Fresh`, then `Retry`, then `AwaitingOrders` — which is
exactly ADR-0022. F548's fix is the reason that is now possible from anywhere in the system, and
this is it happening rather than being argued about.

---

## 1. ⚠ The frozen tool-head set (ADR-0011 §2) — already built. Struck, not rebuilt.

Verified by reading the code and running the tests, not the plan. `Head::policy()` was a `const fn`
over a compile-time `TOOLS` registry with no runtime path, and `tests/heads.rs` + `tests/policy.rs`
carried 23 tests including `a_prefix_is_byte_identical_on_a_second_rendering` — which is the freeze
itself, `ptr::eq` and not just equality.

**The one candidate gap turned out to be the interesting part.** `PLAN.md` §3 asks for the set
*frozen **per attempt***, and the code froze it for the life of the process — stronger than asked,
which made the qualifier vacuous. Item 2 is what makes it exact: the ceiling in force is operator
configuration fixed for a sortie, so *per attempt* is now precisely the scope over which the prefix
cannot move. **The plan's wording was right and the code had overshot it.**

---

## 2. A tool policy per slot — and the two things building it found

The ceiling was per **role** (`Policy { role, max_tier }`) and `Fleet` had no policy field at all.
The slot's half is ADR-0014 §4's other half: **the effective ceiling is the narrower of the role's
and the slot's**. 🚨 It is a `Tier` and never a tool-name list — W7 proved four times, with four
mechanisms across three authors, that an argument check binds only the tool that has an argument.
`Reach` is the property every tool declares and `Tier::Exec` *is* the class.

`Fleet::ceiling` → `Driver::ceiling` → `TurnLoop::ceiling`, plus
`--ceiling no-tools|read|write|exec` on `abcc fleet` and `abcc run`. Default `Tier::Exec`, so a
caller that sets nothing sees no change. Both commands print the ceiling in force, because a capped
slot is otherwise invisible until a role is refused something.

### 🚨 F551 — `Why::Denied` is classified `HardFailure`/`Stop`, and nothing can reach that arm

The plan's falsifier for this item reads: *a slot capped at `Read` must make `Builders` refuse
`run_tests`, and the refusal must be `Why::Denied`, which is a **HardFailure** and
`NextAction::Stop`. ⚠ Check that is the ending you want before shipping it.*

**It is not the ending, and it never was.** `abcc-drive`'s `outcome_from` maps `Why::Denied` to
`HardFailure` and `next_after` maps it to `Stop`, and **no denial can arrive at either**:

| where `Why::Denied` is built | what it becomes |
|---|---|
| `turn.rs::tool_round`, the policy refusing a call | `ToolCallEnded.unmeasured`, a **log field** |
| `turn.rs::NoTools::run` | `ToolResult.unmeasured`, which becomes the same field |
| anywhere at all | **no** `Ending::Unmeasured(Why::Denied)` exists — `grep` returns nothing |

A denied call increments `report.denials`, puts the refusal in the model's own transcript, and **the
round loop continues**. `tests/turn_loop.rs::a_denied_tool_is_refused_on_the_log_and_in_the_transcript`
has asserted that since Skeleton: the scripted model asks for `bash`, is refused, and the phase goes
on to answer.

▶ **This is the same shape as F548, running the other way.** F548 was a recommendation nothing could
receive; this is a classification nothing can produce. Both are two values, each correct alone, that
had never been read together — and this one had already produced a wrong sentence in a planning
document written from the table rather than from the path.

⚠ **The arm is kept and now says so.** If a phase ever does end on a denial, `HardFailure`/`Stop` is
the right answer — a role reaching above its ceiling repeats next attempt unchanged. What was wrong
was reading the table as a description of behaviour.

### 🚨 F552 — a cap has to narrow the head, or it is a trap rather than a policy

Enforcement alone was the obvious build and it is the wrong one. A `Builders` whose prefix still
advertised `run_tests` would ask for it, be refused, and be told — **every attempt, forever**,
spending a tool round to learn something the prompt could have said. `head.rs`'s own rule already
said so: *the advertised surface and the enforced surface are one list*.

So a `Head` alone stopped being able to answer *what tools do I have*. The unit is now
**`Posting { head, ceiling }`**, normalised at construction so a ceiling above the head's own is
unrepresentable, and `Head::policy/tools/prefix` are gone — `Head::posted(slot)` is the only way to
any of the three. Three renderings read it and there is nothing else for them to read: the prompt's
tool section, the OpenAI wire `tools` array, and `Policy::admits`.

**The enumeration went from four to nine, not sixteen** — `Commandos` has one posting and `Builders`
has four — and the affordability argument is unchanged, because a slot's ceiling is fixed for a
sortie: **one column of the table is live in any session**, so the warm set on the server is still
four heads.

`a_capped_slot_stops_advertising_what_it_will_refuse` is the test that would have failed on the
enforcement-only build, and `a_capped_slot_reaches_the_request_the_provider_is_handed` drives the
whole thread — `Fleet` to the request the provider is actually handed, plus the `ceiling` now on
`ModelCallStarted`, because a capped run and an uncapped one otherwise differ in the prompt and
agree in every event, and status is a projection of the log alone.

---

## 3. The breaker — two inputs, and only one of them can see a dead server

Zero code existed. ADR-0010 §4 and F539 ask for a rate over recent attempts read **from the event
log**, a threshold **learned per population**, an input that is **a real one-token completion**, and
a thing that **reports and never gates**. All four, in `abcc_fleet::breaker` + `abcc::pulse`, behind
`abcc breaker`.

**The rate** is F374's rule evaluated over this log: `P(pass at k+1 | first k failed) =
Σ p(1−p)^k / Σ (1−p)^k`. The tests build two populations with the *same* 80% headline rate — one
bimodal, one flat — and one failure takes the first to 0% and moves the second by nothing. **That
80-point spread between two populations that look identical from their headline is the whole reason
the ADR says ship the rule and not the number**, and it is W4's Q56-versus-U100 result reproduced in
arithmetic small enough to check by hand.

🚨 **An absence is not a failure, and this is where that matters most.** `Uncertain` is counted
apart and never inside the rate. F539's wedge ends every attempt `SaidNothing` or `Timeout`; count
those as failures and the rate collapses to **0% over a large sample**, and the breaker reports
*these tasks are impossible* about a server that is not answering at all — the one conclusion that
is certainly wrong, arrived at confidently. ▶ **A rate cannot tell a hard task from a dead server.
Only the pulse can.** That is what F539 was saying, and it is why both halves print together.

### 🚨🚨 F550 — the first pulse called a healthy champion dead

The pulse read `choices[0].message.content` and called an empty string silence. Against the
champion — **loaded, idle, correctly configured, answering `/v1/models` and confirmed by
fingerprint** — it reported `SILENT after 243 ms`.

A positive control in the same shell said why, at three caps:

| `max_tokens` | `message.content` | `reasoning_content` | `usage.completion_tokens` |
|---|---|---|---|
| 1 | `""` | `"Thinking"` | 1 |
| 8 | `""` | `"Thinking Process:\n\n1.  **"` | 8 |
| 64 | `""` | `"Thinking Process:\n\n1.  **Analyze the input:…"` | 64 |

The champion is a reasoning model. **A short completion never reaches the answer channel at all**,
so a health check that reads the answer text can only ever report a healthy server as dead.

▶ **The instrument is `usage.completion_tokens >= 1`.** Waiting for prose is not the fix: the trace
runs 9,942–16,564 characters on identical input (F246), so the probe that exists to be cheap becomes
the most expensive thing in the preflight. The channel the tokens came down is still reported,
because *the model generated* and *the model answered* are two different sentences (F497).
`tests/pulse.rs` pins the champion's verbatim body so this cannot regress.

⚠ **The general lesson is the one this project keeps paying for: a zero from an unvalidated
instrument is not a measurement.** What settled it was a positive control in the same command. Had
the pulse shipped as written, it would have reported an outage on every healthy run — and the
failure it exists to catch would have been indistinguishable from its own false alarm.

### Where it runs, and the one call it does not make

`abcc check` and the preflight of `abcc run` / `abcc fleet` both take a pulse now, and the preflight
writes it to the log before the budget is spent. ⚠ **It never gates.** No caller refuses on a silent
pulse and `abcc breaker`'s exit status does not depend on one.

▶ **One question for David.** ADR-0010 §4's *reports and never gates* is aimed at a **statistical
verdict**, and that is exactly right for the rate. The pulse is not one: the host asked for a token
and watched what happened, which is the shape ADR-0008 lets refuse. **Should a silent pulse refuse
the preflight?** F539 spent both retries against a server that could not answer, which is the case
for; a false alarm stopping a good run is the case against, and F550 is a live demonstration that a
health check can be confidently wrong. It ships as a report until ruled otherwise.

`harness/scripts/ping.sh` replaces the scratchpad copy that was lost — committed this time, with
F550's warning in its header and both arms exercised (healthy exit 0, dead port exit 1).

---

## 4. 🚨 The exit measurement — three numbers, and the box was paging

Four `hw-probe` arms, one session, 2026-08-30. **The sample counts were read before any number was
believed** (F544): every arm has 547–2,655 GPU samples and 58–260 host samples, and none is zero.

| arm | peak commit | `min_avail_mib` | `max_gap_ms` | host n | gpu n |
|---|---|---|---|---|---|
| baseline, **unloaded** | 18.20 GiB | 16,674 | 1,016 | 59 | 547 |
| baseline, loaded and idle | 34.06 GiB | 15,790 | 1,043 | 58 | 548 |
| sortie, gate never reached | 37.79 GiB | 11,984 | 1,051 | 212 | 1,995 |
| **sortie, with the gate's build** | **44.42 GiB** | **6,742** | **4,168** | 260 | 2,655 |

### 🚨 F553 — the three numbers ADR-0020 asks for

1. **Delta over a same-session baseline: 26.22 GiB.** Never the absolute — this session's *unloaded*
   baseline was **18.20 GiB**, against session 19's 8.99 and the probe session's 17.58, because the
   desktop is what moves that number (F540).
2. **`min_avail_mib` = 6,742 MiB** — the free-physical floor, which is what the box actually feels.
3. **The blind window `max_gap_ms` = 4,168 ms** — one cold `cargo` build, on the host stream.

**The model load reproduces for a third time.** 34.06 − 18.20 = **15.86 GiB**, against 15.24 and
16.01 in the two earlier sessions — three sessions, three different absolute baselines, and the
delta holds within 0.6 GiB. F540's ruling is now supported by three points rather than two.

**And the gate's build is the bill, quantified.** The attempt itself costs 3.74 GiB over a
loaded-idle box; the attempt *with* the gate's cold build costs 10.37 GiB. ▶ **The build is 6.63 of
those 10.37 GiB** — F542 said serialising the gate costs 34.4 s and buys 4.1 GiB, and this is the
same fact measured from the other side.

⚠ **The box was paging and that is said plainly.** 44.42 GiB of commit charge against **31.92 GiB
of physical RAM**. Nothing failed, no rung was lost, and the run ended `MISSION ACCOMPLISHED` with
all four rungs measured — but *held* is doing work in that sentence, exactly as it was in F547.

**Against two slots, and only where the comparison is legal.** F547's two-slot arm is a different
session, so its 50.02 GiB commit is **not** comparable to 44.42 — that is the whole of F540. What
*is* comparable is free physical RAM and scheduler latency, because neither is a cumulative counter:

| | two slots (F547) | **one slot (here)** |
|---|---|---|
| `min_avail_mib` | 2,976 | **6,742** (2.3× the headroom) |
| `max_gap_ms`, one cold build | 3.7 s / 19.6 s concurrent | **4.2 s** |

One slot leaves **2.3× the free-physical margin**, and its blind window matches the one-build figure
rather than the 19.6 s two concurrent builds produced. ADR-0020 was ruled on throughput evidence;
this is a second, independent reason for the same answer.

### ⚠ F554 — a peak working set is a process-lifetime high-water mark, not a per-window one

`focus_ws_peak_b_exact` for `llama-server` reads 0.96 → 4.77 → **7.37 GiB** across the three arms.
The last number is not what that window cost: the pid is the same process throughout, and the
kernel's high-water mark never resets. The per-window quantity is `focus_ws_rise_b` — **+3.41 GiB**
and **+2.08 GiB** respectively.

🚨 Read the *rise*, not the peak, unless the process was started inside the window. This is the same
trap as F488's — a counter is only comparable against its own baseline — wearing a field name that
says `EXACT`, which it is, about a question nobody asked.

### 🚨 F555 — the gate said MISSION ACCOMPLISHED about a tree `cargo fmt --check` refuses

The change the run produced is correct and green: four rungs measured, `structural`, `acceptance`,
`veto` and `standard` all exit 0, the Judge reported no findings. The change is one function and one
test in `crates/abcc-fleet/src/budget.rs`, and it is right.

It is also **unformatted**. `pub const fn retries() -> u32 { ATTEMPTS - 1 }` is a single-line body,
and `rustfmt --edition 2024 --check` refuses it — verified against the checkpoint blob
`69358eda`, with the rest of the file passing as the positive control.

The `standard` rung runs `cargo clippy --all-targets -- -D warnings`, witnessed by `clippy.toml`.
**`rustfmt` is in none of the four rungs.** So the gate is not wrong by its own contract — and
ADR-0017's criterion is *a correct tree is one that could land*, and this one cannot land here
without a reformat, because every session in this project ends on `cargo fmt --check`.

⚠ It is the same shape as Skeleton's run 10, which *"compiles and passes all 64 tests while failing
`clippy -D warnings` by one line — the Gate demonstrated before the Gate exists."* The Gate now
exists and catches clippy. The pattern recurred one rung lower.

▶ **David's call, and it is a small one either way.** Add `cargo fmt --check` to the cargo standard
unconditionally (rustfmt ships with the toolchain and has a default style, so there is always an
answer), or witness it on `rustfmt.toml` the way clippy is witnessed — which would not fire on this
repository, since it has none. **Not changed unilaterally: it moves what the gate accepts, and that
is the product.**

---

## 5. ⚠ F556 — two ADR dates disagree with the commits that added them

The brief flagged ADR-0018's `Date: 2026-08-31` against a GATE that closed 2026-08-29 and said to
find the evidence rather than correct it blind. **The evidence is the commit that added each file**,
and checking all twenty-two found **two** wrong, not one:

| | `Date:` field | commit that added it | out by |
|---|---|---|---|
| ADR-0017 | 2026-08-30 | `df6c55c`, **2026-08-29** 17:08:55 +0300 | 1 day |
| ADR-0018 | 2026-08-31 | `4f65779`, **2026-08-29** 18:09:30 +0300 | 2 days |

**The other twenty agree exactly.** Both wrong ones were written in the same session — the
GATE-closing one — and both are GATE rulings, which is what the brief suspected. Neither commit is
near midnight, so there is no ambiguity about which day it was.

This is the same trap that caught the following session, where everything written on 2026-08-30 was
first stamped 2026-08-31 and corrected in `8cd9681` + `a5d9d6e`. ▶ **The model's sense of "today"
and the box's clock are two different things, and only one of them is the fact.** The README's own
opening is why it matters: the ADRs are *"never backfilled with dates after the fact"*, which is a
claim about their dates being true. Both corrected, and the README's two mirrored sentences with
them.

---

## What FLEET has now, and what it owes

**Everything in `PLAN.md` §3's *exists at the end* list is built**, and the exit clause is measured:

- admission as a projection of the store — `Fleet::admit`, a fold over the log, no queue object;
- **one slot with a resident model and a tool policy** — ADR-0020's `N=1`, and §2 above;
- workspaces isolated and the gate serialized — one slot serialises it by construction, and the
  operator's checkout was untouched by both sorties (`git worktree list` back to one entry, and the
  work preserved on `refs/abcc/checkpoints/`);
- the tool-head set enumerated and frozen per attempt — §1, and now exactly rather than vacuously;
- `NextAction` with retry budget 2 and no pre-dispatch estimate — **spent for real on the GPU**;
- the breaker that reports and never gates, whose input is a real one-token completion — §3.

⏸ **Two things carried forward, both David's:** whether a silent pulse should refuse a preflight
(§3), and whether `cargo fmt --check` joins the cargo standard (F555). Neither blocks the milestone
and neither was decided here.
