# LINEAGE P3 — what the model was shown, and the file it was shown with holes in it

**Status: F708 is CLOSED for the brief and CONFIRMED LIVE. Two new alarms came out of closing
it.** `abcc` `082567b` → **`213ee66`**, one commit, **601 tests** (was 593), 19 ignored, fmt and
`clippy --all-targets -D warnings` clean. Flown on `qwen3.6-35b-a3b-mtp@iq3_s` at `-c 40960
--parallel 1`, two attempts on one task, **4 of 4 phases have their brief on the log**. Findings
**F711–F713, next free F714.**

🎉 **The question F700 exists for is now a SQL query.** `a11138` was a retry standing on a tree the
veto rung had refused, and `json_extract(body,'$.text')` over `kind = 'brief_recorded'` returns the
paragraph that told it so, with the compiler's own output inside it. Under `082567b` that fact was
derivable from a code path and from nothing else.

🚨 **F712 — the redactor rewrites this repository's own source, and hands the model broken Rust.**
14 of 132 files are altered before a model sees them. `pub fn secrets(mut self, secrets: Secrets)
-> Driver<'a>` arrives as `pub fn secrets(mut self, secrets: [redacted] -> Driver<'a>`: the type is
gone and so is the closing paren, because the shape half's name pattern is case-insensitive and
matches the English word *secrets*. It has never fired before — **2 of 95 attempts on this log, both
today** — because no attempt had yet had a reason to read those files. **That is exactly what
SELF-HOST changes.**

🚨 **F713 — and whether that is what broke this attempt is the one thing the log still cannot
say.** A tool's output text reaches the model's context and no event carries it, so the question
*was this model shown a mangled file* can only be answered by re-running the scrubber by hand —
which is the re-derivation F708 says is not evidence. The finding F708 closed and the finding it did
not close met on the same attempt, an hour apart.

---

## 1. What F708 was

Thirty event kinds and **not one carried a prompt body**. `ModelCallStarted` records the provider,
the model, the head's key, the ceiling and the budget — every fact about the call except the one the
call was made of.

So *was the model told X* has always been answered by reading a code path and a precondition, never
by reading the log. That is true of every prompt-surface arm this project has flown: F655's rescue
prose, ruling 2's `summary` line, F700's refusal paragraph, F531's rung view. In each case the
evidence that the change reached the model is **a test** — true of the build the test ran in, and
unreadable from the log of the sortie that was actually flown.

⚠ It is worth being exact about how weak that is. A test says *this build would tell it*. An arm
asks *was it told*. The two differ whenever the code path has a precondition — and F707 is the
demonstration: `refusal_under` had a passing test and **fired zero times in nine live attempts**,
because the precondition it keyed on was the wrong one. Nine attempts went by with a feature that
did not exist, and the log of those attempts cannot distinguish them from nine where it did.

## 2. What shipped — `Event::BriefRecorded`

One event, written in `Driver::phase` beside the `AttemptPhaseEntered` that says which phase it
opened. The phase is deliberately **not** repeated on it, which is `PhaseEnded`'s own rule: it is
the `attempt_phase_entered` above, and a second copy is a second thing that can disagree.

▶ **`phase` now takes the brief as text and builds the `Body` itself, and that is what makes the
record honest rather than merely present.** Nothing inside that function could tell an opening body
from a used one, so a record of *whatever body it was handed* would have been a true statement about
the argument and not about the prompt. Built there, the text logged and the text sent are one
expression. There is no way around it: `Driver::phase` is the only caller of `TurnLoop::run` in the
workspace.

▶ **The test compares the log against what the provider actually received**, never against
`brief::localize`. Re-deriving the expectation from the function under test is an oracle comparing a
thing with itself: it agrees however wrong both halves are, and the failure it has to catch is the
log describing a prompt other than the one that was sent. Both negative controls were run — logging
a truncated brief fails it, and sending unscrubbed while logging scrubbed fails the redaction test.

▶ **Scrubbed once, before the send, so both sinks take the same bytes** (ADR-0014 §5). A record of
a prompt that is not the prompt is the failure this event exists to end. Most of a brief is our own
prose, but it also carries the output of a check that ran over a tree the model itself wrote (F700)
— and an exemption for the strings we wrote is the first of the exemptions. ⚠ **This has a cost and
F712 is it**; see §5.

▶ **The shape is pinned by a test, because the value is in the readback.** `Scrubbed` is
`serde(transparent)`, so the text is a plain string at `$.text` and the query is one line. Wrap it
in a struct and every arm's readback starts answering `null` with nothing anywhere failing — the
instrument-that-reports-its-own-failure shape this archive keeps finding.

```sql
select seq, attempt, json_extract(body, '$.text')
  from event where kind = 'brief_recorded' order by seq;
```

## 3. The other half — the head, as a digest

`head` and `ceiling` name one of nine compile-time constants **within a build**. Edit a charter, or
a tool's one-line `summary` — which is exactly what ruling 2 is — and every field on
`ModelCallStarted` reads as it did before. So *were these two arms shown the same head* was not a
question the record could answer either (F711).

`head_digest` is the first 16 hex of the SHA-256 of the prefix, computed once per process beside the
prefix itself, `#[serde(default)]` so every log already written still replays.

⚠ **A digest here and the text there, and the asymmetry is the point.** A body is composed at run
time from the task, the tree and the operator, and exists nowhere else — so it goes on the log
whole. A prefix is a constant whose text is in the source at the commit the run was made from — so
what the log owes is *this differs from that*, and 16 characters says it. The nine measured, for the
record: Recon at read 2,678 bytes `2d7ac53218f2e381`; Builders at exec 4,133 bytes
`9d491d116cf78300`; Commandos at no-tools 2,267 bytes `05227dc3fedbaf78`.

⚠ **The test recomputes the digest from the prefix rather than asserting a property of it.** A
digest taken of the *key* instead would be nine distinct, stable values that pass every obvious
check and answer nothing, because it would be identical across a build that rewrote every charter.

## 4. Flown — and the cost, measured

One task, two attempts, `a10967` (fresh) and `a11138` (a retry, through `abcc take` +
`abcc release`, which is still the only route back onto the board — F703 is still open).

| | `a10967` | `a11138` |
|---|---|---|
| cause | `Fresh` | `Retry { of: a10967 }` |
| opened on | the checkout, `7b6058d4` | the operator's hand-back, `51a09b03` |
| `brief_recorded` | 2 — 596 and 2,723 chars | 2 — 1,493 and 3,438 chars |
| told what refused its tree | n/a | **yes, and the log says so** |
| ending | `Uncertain{BudgetExhausted 24}` | `Uncertain{TruncatedAtCap 16384}` |
| gate | structural ok, **veto REFUSED** | **structural refused** — changed no file |

🎉 **4 of 4 briefs are on the log**, the first attempt's two carrying no refusal heading (nothing was
under it) and the retry's two carrying the veto's own output verbatim: *the tree does not build —
error[E0308]: mismatched types … `Secrets::from("0".repeat(12))` … expected `Scrubbed`, found
`Secrets`*. ⚠ The Judge was not asked in either attempt, so there is no third brief — correct, and
the log says why in a `note`.

**What it costs.** Over the live log's 195 phases before today, a phase's first call is 1,260 prompt
tokens at the median for Localize, 2,917 for Change and 1,905 for Judge, against heads of 2,678,
4,133 and 2,267 bytes. So the briefs are roughly **740 KB against 2.66 MB of event bodies — about a
quarter more log**, for the thing every arm is about. ⚠ That is an estimate from token counts and
head sizes, not a measurement of the new rows; the four real rows are 596 to 3,438 characters.

⚠ **The retry was told and still produced nothing, and that is n = 1.** Its Change phase made one
`apply_patch` call whose arguments were cut at the 16,384 cap with **0 argument characters
recorded** — F506 and F511's known failure — and the structural rung refused it for changing no
file. Do not read it as evidence about F700 either way (F575, F657).

## 5. 🚨 F712 — the denylist rewrites this repository's own source

The shape half's assignment pattern is
`(?i)\b[A-Z0-9_]*(?:API[_-]?KEY|SECRET|…)[A-Z0-9_]*\s*[:=]\s*["']?[^\s"'#]{8,}["']?`. Its doc
comment says *`SOMETHING_SECRET=value`, in the shape an env file or a shell export has*. It is
case-insensitive, it accepts `:` as well as `=`, and it is anchored to nothing — so in Rust it
matches a field, a parameter and a path:

```
crates/abcc-drive/src/lib.rs, as the model is shown it
      secrets: [redacted]
      pub fn secrets(mut self, secrets: [redacted] -> Driver<'a> {
          self.secrets = [redacted]
crates/abcc-core/src/redact.rs, as the model is shown it
  /// Text that has been through [`Secrets:[redacted]
```

🚨 **The type is gone and so is the closing paren.** The value half is greedy over non-space
characters, which is right for an env value and wrong for `Secrets::default(),`, so the erasure eats
trailing syntax. A model asked to write Rust is handed Rust that does not parse. And in `redact.rs`
the doc comment that explains the type is truncated **exactly where it would have named
`Secrets::scrub`** — the one thing a reader needs, because `Scrubbed` has a private field and one
constructor on purpose.

**14 of 132 `.rs`/`.md`/`.toml` files in this workspace are altered**, `abcc-drive/src/lib.rs`,
`abcc-engine/src/turn.rs`, `abcc-fleet/src/lib.rs`, `abcc-core/src/redact.rs` and
`abcc-tui/tests/lines.rs` among them. 27 assignment-shaped and 6 authorization-header matches were
removed across today's two attempts.

🚨 **And it has never fired before.** 20 redaction notes on a 11,000-event log, all 20 from today:
**2 of 95 attempts**. Not because the shape changed — it did not — but because no attempt had yet
had a reason to read those files. Every arm this project has flown worked on
`crates/abcc/src/cli.rs` and `main.rs`, which contain none of these shapes. **SELF-HOST is the
milestone where the subject becomes the whole of `abcc`**, and this is waiting in it.

⚠ **The brief now inherits the same false positives**, which is the price of scrubbing once for both
sinks (§2). `a11138`'s Change brief is on the log carrying
`text: Secrets:[redacted]0".repeat(12)).text,` — Recon had correctly reported that `Scrubbed` has
no public constructor, and the example of the defect it was quoting was redacted on the way to
Builders. ▶ That is an argument for fixing the
shape, not for exempting the brief: the other two arrangements are *put a secret in the task prompt
onto the log* and *log a prompt other than the one that was sent*, and the second is F708 again.

⏸ **Three candidate fixes, and this is the operator's call, not a rung's.** (1) Drop `(?i)` on the
name half only — an env var is `SECRET_KEY`, and this kills all 27 of today's hits while keeping
every real env-file shape; it loses lowercase `password: …` in YAML. (2) Anchor to `=` and to a line
start with an optional `export`, which is what the doc comment describes; it loses a secret pasted
mid-line. (3) Reject values containing `::` or `(`, which is a Rust special case in a general
denylist and will not generalise. ▶ **Recommended: (1).** It is the smallest change that makes the
regex mean what its own doc comment says, and `redact`'s module docs already say this half is a
heuristic and *not the control*.

## 6. ⏸ What is still not on the log

▶ **A tool's output text.** It reaches the model's context, and `ToolCallEnded` keeps the exit
status and the arguments-only-when-refused (F505). So `apply_patch`'s F649 sentence — one of the
four surfaces F708 named — is still a prompt the record cannot read back, and so is every file the
model read. **F713 is the case that prices it**: the question §5 raises is *was this model shown a
file with its syntax removed*, and the honest answer today is *probably, and the log cannot say*.

⚠ It is a decision about what a log is for and it is not an oversight. Tool output is bounded
already — 64 KiB a read, 16 KiB a stream — so an attempt's whole output is at most a few hundred
kilobytes and a fraction of a git snapshot. What it reverses is F505's rule, *keep the text exactly
when the log is the only copy of it*, which was written about arguments. For output the log **is**
the only copy: a successful tool's effect is in the tree, its words are nowhere.

▶ **The nudge sentence and the head text** are constants and are identified rather than carried —
`PhaseNudged` says a nudge happened, `head_digest` says which head. That is the same call as §3 and
it is sound while they stay constants.

⏸ Unchanged and still owed: `Command::OrdersGiven`'s fate (F703) · a second arm for the `summary`
lever, still the only way to score ruling 2 · the four `paint` changes · row 8's other half · the 96
voice lines.

---

## Findings

### F711 — the log named which head and never which build's head

`ModelCallStarted` has always carried the head's key and its ceiling, which together name one of
nine compile-time constants **within a build**. Edit a charter or a tool's one-line `summary` —
ruling 2 is exactly that — and every field on the event reads as it did before, so *were these two
arms shown the same head* is unanswerable from the record. `head_digest` is the first 16 hex of the
SHA-256 of the prefix. ⚠ A digest rather than the text, deliberately: the prefix is a constant whose
text is in the source at that commit, where a brief is composed at run time and exists nowhere else.
⚠ **A digest of the key would pass every obvious test and answer nothing** — nine distinct stable
values, identical across a build that rewrote every charter — so the test recomputes it from the
prefix.

### F712 — the shape half of the denylist rewrites this repository's own source into Rust that does not parse

The assignment pattern is case-insensitive, accepts `:` as well as `=`, and is anchored to nothing,
so it matches the English word *secrets* in ordinary Rust. **`pub fn secrets(mut self, secrets:
Secrets) -> Driver<'a>` reaches the model as `pub fn secrets(mut self, secrets: [redacted] ->
Driver<'a>`** — the type gone, and the closing paren eaten with it, because the value half is greedy
over non-space characters. **14 of 132 files in this workspace are altered before a model sees
them**, `redact.rs` among them, where the doc comment is truncated exactly where it would have named
the one public constructor. 🚨 **It has never fired before today — 20 redaction notes on an
11,000-event log, all from 2 of 95 attempts** — not because anything changed, but because no attempt
had yet read those files. Every previous arm worked on `cli.rs` and `main.rs`, which contain none of
these shapes. **SELF-HOST is where the subject becomes the whole repository.** ⚠ The brief inherits
it too, now that the brief is scrubbed for both sinks: `a11138`'s Change brief carries
`Secrets:[redacted]` at the exact line the task was about. ▶ The fix is to the shape and not to the
boundary; recommended is dropping `(?i)` on the name half, which kills 27 of 27 of today's hits.

### F713 — tool output is the prompt surface the log still cannot read back, and F712 is what that costs

A tool's output text reaches the model's context and no event carries it: `ToolCallEnded` keeps the
exit status and the arguments only when the call was refused (F505). So F649's `write_file` sentence
— one of the four surfaces F708 named — and every file the model read are prompts the record cannot
reproduce. 🚨 **The price is exact and it was paid the same day**: whether `a10967` wrote
`Secrets::from(…)` after being shown a file with `Secrets::default()` redacted out of it is
answerable only by re-running the scrubber by hand, which is the re-derivation from a code path that
F708 says is not evidence. ⚠ Output is already bounded — 64 KiB a read, 16 KiB a stream — so the
objection is not size. What it reverses is F505's rule as written for *arguments*; for output the
log is the only copy, because a successful tool's effect is in the tree and its words are nowhere.
