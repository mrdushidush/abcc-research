# ADR-0015 — The idle gap is ours; a full window is not a fault; silence is not an artifact

- **Status:** ✅ Accepted
- **Date:** 2026-08-29
- **Deciders:** David (three rulings, 2026-08-29), written by Claude Code
- **Sources:** F493 (the idle gap), F496 + F498 (the window), F497 + F502 (the empty answer),
  F499–F501 (what the same two runs also showed) · the runs themselves are attempts `a8` and
  `a107` on the log at `%LOCALAPPDATA%\abcc\abcc-1ae35b6091a63e2c\log.sqlite`, 151 events
- **Supersedes in part:** ADR-0006 § *Timeouts, with the numbers on them*
- **Extends:** ADR-0009 (this is the enum that ADR says is the failure class)

## Context

Skeleton was built against scripted providers and one closed log. Then two attempts ran end to end
against the champion, and **each produced an ending the ratified record described wrongly**. All
three corrections below are the same mistake in three places: *a record that names the wrong cause
is worse than one that names none*, because the wrong cause is actionable and the action is futile.

### 1. The idle gap was bought, and the shop has closed (F493)

ADR-0006 rests on F198: that `RequestBuilder::timeout` on `reqwest::blocking` is a **per-read**
budget renewing on every chunk, so one number is both hang detector and TTFB bound. F198 flagged
its own risk — *the doc comment describes the opposite behaviour, so a design leaning on the
measured behaviour must own a test that pins it* — and made that pin the first of two not-optional
tests. **The test was written and it failed on its first run.** Re-measured against a socket that
writes on command, six lines 200 ms apart under a 500 ms budget, with a control that completes:

| version | F198 test A (1.2 s of body, 500 ms budget) | verdict |
|---|---|---|
| reqwest 0.12.28 | **fails at 0.502 s** | total duration |
| reqwest 0.13.4 | **fails at 0.509 s** | total duration |

F198's measurement was right for the version it ran; its reading of the mechanism was incomplete.
The per-read `wait::timeout` is still there byte-identical, but the blocking timeout now *also*
reaches the async layer as `RequestConfig<TotalTimeout>` wrapping the body. **A total-duration
timer ends every long turn as a transport failure**, which is the opposite of what the design
needs. The code already reflects this and ADR-0006 does not.

### 2. A full context window was recorded as an engine fault (F496)

Attempt `a8` died at **14,261 prompt + 2,123 completion = 16,384**, the loaded window exactly. The
loop appended that `finish: length` turn and asked again, which guaranteed the overflow; LM Studio
answered HTTP 500 with a generic HTML page — `<pre>Internal Server Error</pre>`, **carrying no
information about the cause at all** — and it was recorded `EngineError` → `HardFailure`, i.e.
*another attempt would repeat this unchanged*. It is the one thing that is not true of it: the same
body runs against a larger window.

🚨 **F498 — the window is observable, and the two token counts are what observe it.** A turn
finishing at `length` having spent *fewer* completion tokens than the `max_tokens` we sent was not
stopped by our cap; the only other thing that ends a chat completion early is the window, so
`prompt + completion` **is** the window. Run 1: 2,123 against a budget of 8,192. This needs no
string matching against an error page that says nothing, and it is knowable one turn *before* the
500 the loop currently provokes.

### 3. An empty answer was presented as an artifact (F497)

On the clean run `a107` **both `ClaimRecorded` events are zero characters** — Recon at completion
47 / reasoning 42, Builders at 582 / 577. The budget went into the reasoning trace and the few
tokens of answer never arrived, at `finish: stop`. A live positive control on the same server ruled
out the parser. `Answered { text: "" }` is an absence wearing an artifact's shape, and Localize's
empty answer became Change's *"What Recon reported"* input.

⚠ **F502 — ADR-0010 §7's `TraceSignal::OpenAt200` is the same condition, detected worse.** The
first answer token closes the trace, so `OpenAt200` is reachable only by a turn that reasoned and
then produced nothing — F497's shape, plus a floor of 200 completion tokens. On this run it would
have fired for Builders (582) and **missed Recon (47) entirely**. The signal was already watching
and recorded a number where the phase should have ended.

## Decision

🚨 **Two new `Why` variants, and the idle gap is stated as ours.**

1. **`Why::SaidNothing { by, completion_tokens, reasoning_tokens }`** — the phase ends `Unmeasured`
   and **no claim is written**. *"The model said nothing"* and *"nothing measured what the model
   said"* are two different sentences and the operator was being shown the second.
   `reasoning_tokens` is `Option`, because not-reported is not zero and here the difference is the
   whole explanation.
2. **`Why::ContextOverflow { window, prompt_tokens }`** — classified apart from an engine fault,
   with the window carried on it, detected by F498's inequality. It is `Uncertain`, and it is the
   **one `Why` whose next action is `HandToOperator`**: retrying repeats it, stopping discards work
   that is one setting away from running, and only a person can load a larger window.
3. **The idle gap is this project's, implemented in `TurnStream::next_delta` as
   `recv_timeout(idle_gap)`** over the channel the reader thread feeds; the HTTP client is built
   with `timeout(None)` deliberately, against a blocking-builder default of 30 s.

▶ **Deferred, explicitly: bounding the request body against the window.** That is token accounting,
it belongs to Gate or Fleet, and nothing here does it. The window is *recorded when observed*, not
predicted.

## Consequences

- **`HardFailure` regains its meaning.** It now asserts only what it says — a retry changes nothing
  — and the two endings that violated it have left. `classify` stays exhaustive with no wildcard,
  which is what forced this decision to be made rather than defaulted.
- **A doomed request is no longer sent.** The overflow is detected on the turn that reveals it, so
  the contentless 500 stops being provoked at all.
- **`Landing` now follows `NextAction`** in the `Unmeasured` arm rather than being asserted beside
  it, so a `HandToOperator` cannot land as `Failed`. They were already documented as one judgement.
- ⚠ **A complete tool call on an overflowing turn is now discarded** (F499). On `a8` that turn
  carried two: `apply_patch`, which **succeeded and landed a real 6-line change**, and `write_file`,
  whose arguments arrived empty — cut mid-JSON by the window and recorded as the model's schema
  failure. Ending the phase first follows the existing precedent (`TruncatedAtCap` skips tool calls
  too) and is the conservative half of a genuine trade-off. **Open, and David's.**
- **F500 corrects the reading of the run, not the code.** `a8` produced correct, house-style code —
  a doc comment, a `VERSION` const, a `--version` branch — before the window killed it mid-task.
  Only `a107` did nothing. The population is n=2 and split, which is why *run more tasks* is the
  standing answer and not *change the model*.

## Alternatives rejected

- **Reuse an existing variant for either ending.** `TruncatedAtCap` names our own cap and would be
  a lie about the window; `NoCheckerForArtifact` is honest about the *gate's* absence and says
  nothing about a model that produced no artifact to check.
- **Detect the overflow from the error body.** The recorded body is nine lines of boilerplate HTML
  with `Internal Server Error` in it. There is nothing to match on, and a matcher would bind this
  code to one server's error page.
- **Let `OpenAt200` carry F497.** F502: it misses every empty answer under 200 completion tokens,
  which on the only run available is half of them.
- **Bound the body against the window now.** Deferred above. It needs a tokenizer this workspace
  does not have, and it would be predicting a number the server already reports.

## What would falsify this

- **A server that ends a completion at `length` below `max_tokens` for a third reason** — a stop
  sequence, a per-response cap we did not send — makes F498's inequality unsound, and
  `ContextOverflow` would then be naming a cause it cannot know. One counter-example is enough.
- **An empty answer that is reliably retryable in place** would move `SaidNothing` from a phase
  ending to a within-phase retry, the way ADR-0010 handles a failed tool call.
- **A `reqwest` release restoring a per-read budget on the blocking client**, pinned by the test
  F493 wrote, would let the idle gap go back to the library — and ADR-0006 would be right again.
