# ADR-0025 — A pulse is a measurement, so it may stop a preflight; the rate is a verdict, so it may not

- **Status:** ✅ Accepted — **David's ruling of 2026-08-30**
- **Date:** 2026-08-30
- **Deciders:** David (yes, a silent pulse refuses), Claude Code (the `NotTaken` exclusion, the scope)
- **Sources:** **F539** (the outage), **F550** (the instrument that was wrong), ADR-0008, ADR-0009 §4, ADR-0010 §4
- **Amends:** ADR-0010 §4 — *reports and never gates* is scoped to the rate, which is what it always meant

## Context

F539 is the only outage this project has had. One hung generation left `/v1/models` answering
normally — the id, the state, the whole listing — while **every completion returned nothing for
60 s**, and it took both slots down until `lms load`. The check the project had was a poll of that
listing, so **the check that existed was precisely the check that missed the only thing it exists to
catch**, and a run spent both attempts against a server that could not answer.

The pulse was built for that: one completion, `max_tokens: 1`, non-streaming. It shipped as a
**report** on the reading that ADR-0010 §4's *reports and never gates* covered it.

**That reading was wrong, and the reason is in what §4 is about.** It governs the **rate** — F374's
update rule over the log's population — and the reason a rate may not refuse is that it is a
*statistical verdict* which **cannot tell a hard task from a dead server**. ADR-0009 §4 draws the
same line from the other side: a rung may refuse because it is a *measurement*, and a measurement is
the host asking a question and watching what happened.

A pulse is the second thing, not the first. The host asked for a token and watched.

## Decision

### 1. A silent or unreachable pulse **refuses a preflight**

`run` and `fleet` both go through one `confirm_model`, and it now returns `Refused` when the pulse
did not decode a token. Nothing is spent against a server that cannot answer.

⚠ The model verdict is still checked first and keeps its own advice. Both are fatal; the unconfirmed
model is the more specific fault, and an operator sent to reload a wedged server when the real
problem is an unconfirmed model reloads the wrong thing.

### 2. 🚨 `Pulse::refuses()` is **not** `!answered()` — `NotTaken` never refuses

| variant | refuses | why |
|---|---|---|
| `Answered` | no | a token was decoded |
| `Silent` | **yes** | HTTP 200 and nothing decoded — F539's shape exactly |
| `Unreachable` | **yes** | the socket did not answer a completion the listing had answered |
| `NotTaken` | **no** | **an absence** — nobody asked, so nothing was measured |

Letting `NotTaken` refuse would read *nothing was measured* as *something failed*, which is the one
confusion `Outcome` exists to prevent (ADR-0009). It is the same rule the gate's ladder already
applies to an `Unmeasured` rung, one level out.

### 3. `abcc check` refuses too; `abcc breaker` still refuses nothing

`abcc check` already refused on the **weaker** fault of an unconfirmed model. A health command that
exits 0 about a server nothing can run against lies to whatever script asked it, and
`harness/scripts/ping.sh` exits 1 on the same condition — two health checks on one box disagreeing
is worse than either answer alone.

`abcc breaker` prints the pulse **beside the rate** and refuses nothing. That is ADR-0010 §4 intact:
the operator reads both and decides.

### 4. ⚠ The instrument had to be right first, and it very nearly was not

**F550: the first pulse called a loaded, idle, fingerprint-confirmed champion SILENT after 243 ms.**
It read `choices[0].message.content`, and at `max_tokens` of 1, 8 and 64 this reasoning model
returns `content: ""` and puts every token in `reasoning_content`. The instrument is
`usage.completion_tokens >= 1`.

Under this ADR that bug would have **stopped every run on this machine**. The order matters and is
worth stating: the measurement was corrected first, and only then given the power to refuse.

## Consequences

- **A wedged server costs one 20-second pulse instead of two full attempts.** That is the whole
  return, and F539 is the receipt.
- **A false silence blocks work that would have succeeded.** The failure mode is real and it is the
  case against; it is bounded by the pulse being a direct question with a 20 s timeout, sized against
  a 60 s wedge and a 243 ms healthy answer.
- **`Pulse` now has two predicates**, and a caller that reaches for `!answered()` where it means
  `refuses()` reintroduces the `NotTaken` bug. Both are documented at the definition, and the test
  that pins them asserts the *gap* rather than either one.
- ADR-0010 §4 is not weakened. It is **scoped**, and its sentence keeps its force where it was aimed.

## Alternatives rejected

- **Keep it a pure report** — F550 is the case for, and it is a good one: a health check can be
  confidently wrong about a healthy box. Rejected because the cost of a wrong report is *also*
  measured, and it is F539: two attempts, both spent, on a box that answered nothing for 60 s.
- **Refuse only after N consecutive silent pulses** — survives one transient wrong answer, and adds a
  tunable plus a delay to the refusal. Rejected for now: the pulse is a *direct* question, so a
  second one measures the same thing again rather than more. ⏸ It is the obvious repair if false
  silences turn out to happen at all.
- **Refuse in `abcc breaker` too** — it would put a refusal next to the rate and invite the reading
  that the rate refuses. The two halves of that command exist to be different.

## What would falsify this

**A silent pulse against a server that then works.** The observable is a preflight refusal followed
by a successful run on the same server without an intervening reload — the log carries the pulse note
before the refusal precisely so this is answerable after the fact. If it happens at all, the answer
is the N-consecutive rule above; if it happens often, the pulse is not the measurement it claims to
be and goes back to being a report.
