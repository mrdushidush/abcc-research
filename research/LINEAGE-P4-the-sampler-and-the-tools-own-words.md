# LINEAGE P4 — the sampler nobody set, and the words no event kept

**Status: F712 CLOSED on the operator's ruling, F713 SHIPPED, and the parked sampling item is
CLOSED and turned out to have a second half nobody had measured.** `abcc` `213ee66` →
**`223ae3a`**, four commits, **615 tests** (was 601), 19 ignored, fmt and `clippy --all-targets -D
warnings` clean, all four pushed to `origin`. Probed on `qwen3.6-35b-a3b-mtp@iq3_s` at `-c 40960
--parallel 1`, 70 live calls. Findings **F714–F717, next free F718.**

🚨 **The engine sent no sampling parameters at all, and five identical requests are five different
answers.** `max_tokens` was the only field. So every rate this project has ever quoted — 5.3% over
95 attempts, `apply_patch` at 31 of 66, F657's *4 of 5 versus 1 of 5* — was taken at whatever the
server defaulted to, unseeded, with nothing on the log saying so. **F657 was not a finding about the
model. It is arm one of this probe, and it reproduces in ten seconds.**

🚨 **And a seed does not fix it, which is the half the ruling did not know.** MTP speculative
decoding flips draft-acceptance state on **every** call, seeded or not, and when the accepted count
changes the sampler's draws land differently. Seven of eight seeds pinned the output; one
alternated between two answers in exact step with the draft counts. `temperature: 0` was
deterministic in every arm, because an argmax does not draw. ▶ So a seeded sortie is
**attributable**, not reproducible, and that is the sentence to use.

🎉 **A tool's output is on the log** (F713), written from the same binding that feeds the model's
context so the two cannot drift — and its cost is **not** the one the finding assumed. *Output is
already capped so size is not the objection* was written without measuring it. It quadruples the
log.

⚠ **Three claims in the shipped docs are refuted by the code** (F714), and the one that matters is
that the art is *"carried across unchanged"* while `git ls-files` finds zero art files. 🚨 **The
packaging decision behind that was already put to the operator on 2026-09-07 and answered — wait —
and this session's own queue restated its precondition as met.** The write-up that recorded the
deferral says in terms: *nobody should re-ask it or start it*.

---

## 1. F712 — the redactor stopped rewriting this repository

The ruling was the recommended one: **drop `(?i)` on the name half only.** It is narrower than it
looks, because the value half contains no letters at all — case-sensitivity binds the name half
alone, and removing the flag from the whole pattern *is* the name-half fix.

The sweep is the interesting part, and it was run before the change rather than quoted from P3:

| | files altered of 132 | `Assignment` hits |
|---|---|---|
| `213ee66` | 14 | 51 |
| after | 4 | **2** |

Both survivors are deliberate fixtures — `DATABASE_PASSWORD=hunter2hunter2` in the redactor's own
tests and `ABCC_MODEL_API_KEY=` in the engine's. **On `crates/*/src` the count is zero.** The four
files still altered are all test files holding a planted secret, plus `redact.rs`, whose two
remaining hits are doc comments quoting an `Authorization: Bearer` header — where the rule is
right, and the only collateral is a closing backtick.

⚠ **P3's 14-of-132 reproduced exactly, and the instrument counted itself.** The sweep file contains
a lowercase `secrets` assignment of its own, which matched. Excluding it, the pre-existing figure is
13 of 131 — so P3's number was 13 real files plus its own probe. The count was right about the
defect and one too high about the repository.

▶ **The regression test is the sweep, not the six lines the sweep found.** A case list asserts the
shapes somebody already thought of; this one walks `crates/*/src` and would catch a false positive
in a file nobody has considered. It asserts on `Kind::Assignment` alone, for the reason above. The
**cost** is asserted too — a lowercase YAML `password:` is no longer caught — so `(?i)` cannot come
back without reading what it costs, and the note beside the pattern says what has to move first:
the value half's greed, not the name half's case.

🚨 **The negative control is a finding about the old suite.** With `(?i)` restored the three new
tests fail and **the pre-existing eleven pass.** That is why this shipped: nothing in a well-written
redaction suite was asking whether the redactor ate its own repository.

---

## 2. F713 — a tool's words are on the log, and the oracle is the provider

`ToolCallEnded` carried `attempt, tool, exit, elapsed_ms, unmeasured, arguments` and no event of
the 23 kinds carried a tool's output text. It is the mirror of F505 and **deliberately the opposite
rule**, because the two have opposite second copies: a successful call's arguments are recoverable
from the tree, which is why the log declines to be a second workspace, but its *words* went into
the context and nowhere else.

▶ **`output` is written from the same binding that feeds the body, two lines apart.** That is the
whole claim — *what the record says the model was shown* and *what the model was shown* cannot
drift — and it is what the test asserts: against the `Role::Tool` message the scripted provider
**actually received**, never against `secrets.scrub`. Re-deriving the expectation from the function
under test is an oracle comparing a thing with itself, and it agrees however wrong both halves are.

A denial's refusal text is recorded the same way. `Why::Denied` already carries the role, the tool
and the ceiling — but *the class was denied* and *this is the sentence the model read* are different
facts, and deriving the second from the first is precisely what F708 was.

🚨 **Two negative controls, and the second is the one that earned the test its shape.** Blanked, all
three new tests fail. Fed instead from a **second `scrub` call** on the way to the log — the
arrangement ADR-0014 §5 exists to forbid, three lines that look like tidying — two of the three
still pass, and only the byte-equality catches it. With the key on disk.

---

## 3. F717 — what F713 actually costs, which F713 did not measure

*Output is already bounded (64 KiB a read, 16 KiB a stream), so size is not the objection.* That
sentence was written twice into a memory index and never checked. The bound is real; the multiplier
is what matters.

There is no output on the log to measure, so it is measured indirectly: across each window between
two `model_call_ended` events inside one attempt, the growth in `prompt_tokens` minus what the
assistant itself contributed, divided by the tool calls in that window.

| | tokens per tool result |
|---|---|
| median | **244** |
| mean | **984** — the tail is file reads |
| p90 / p99 | 3,168 / 7,228 |

Over 1,136 windows and 2,147 tool calls that is **6.6–8.6 MiB against 2.7 MiB of event bodies
today** — bracketed because whether reasoning tokens are resent changes the subtraction, and they
are half of all completion tokens on this log. **The log roughly quadruples: 3.9 MiB becomes about
12 MiB for five active days.** Cheap in absolute terms, and the honest form of the sentence is a
multiplier rather than a reassurance.

▶ **No cap is applied on the way to the log, on purpose.** The text is already bounded to what the
model itself is held to; truncating again here would put a *different* text on the record from the
one that was sent, which is the defect the field exists to end.

---

## 4. F714 — three claims in the shipped docs that the code refutes

**"It never says `Accomplished`."** It has said it five times. The sentence predates the Gate
milestone, which made the word reachable: `Driver` runs the gate over the snapshot pair and a
`Green` headline lands `Landing::Accomplished` (`abcc-drive/src/lib.rs:895`), and the live log holds
five `task_transitioned` rows saying so. The rule the sentence reached for is still true and now
says what it is — only a *measurement* says it, never the model.

**"488 numbered findings."** 713, per `fledger.py next`.

**"The art, the audio and the identity are David's own and are carried across unchanged."** True of
the provenance, false of the packaging, and a reader takes it as the second. `git ls-files` finds
**0** art files and **0** audio files; `corpus_root` has no default and refuses without `--sprites`
or `ABCC_SPRITES`. `CREDITS.md` said it in the same words.

🚨 **This does not reopen the packaging decision, and the way it nearly did is the lesson.** The
session queue carried it as *the `rust-embed` item deferred 2026-09-07 whose precondition is now
met*. `CONSOLE-P9` §8 records what actually happened: it was put to the operator **with these
numbers**, three options were priced, he chose **wait until the art settles**, and the write-up
closes *"the queue item is deferred, not open: it comes back when new art arrives, and until then
nobody should re-ask it or start it."* The corpus files are still dated February. ▶ **A deferred
decision's precondition was restated as met by a later session that had not read the deferral** —
and the restating was confident, numbered, and marked 🚨 three times.

Re-measured rather than quoted: 28 files, 16 distinct, and the admission filter draws **4**. Every
one of the twelve distinct PNGs is refused — ten on coherence, four on a caption burnt into the top
edge, overlapping. ▶ **The cheap megabyte is the half that draws nothing**, and the four that draw
are 34.3 MB of the corpus's 35.

---

## 5. F715 — the engine sent no sampling parameters

`payload` sent `model`, `messages`, `max_tokens`, `stream`, `stream_options`, `tools` and
`response_format`. **No temperature, no top_p, no seed, anywhere in the crate** — while
`abcc/src/pulse.rs:114` sends `"temperature": 0` on the health check. One place in this workspace
knew to pin the sampler, and it is the one place whose answer is discarded after a single token.

Four arms, five identical requests each, on the champion:

| arm | what was sent | distinct of 5 |
|---|---|---|
| **A** | **what `abcc` sent** — `max_tokens` only | **5** |
| B | `+ seed` | 1 |
| C | `+ temperature 0` | 1 |
| D | `+ temperature 0, top_p 1, seed` | 1 — byte-identical to C |

B's hash differs from C's, so the server's inherited default temperature is **not** 0. D matching C
confirms a seed is inert once temperature is, which cross-validates that both knobs reach the
sampler rather than being quietly ignored.

⚠ **The first pass of this probe compared four empty strings and produced a clean table doing it.**
All 120 tokens of a short answer go to `reasoning_content`; `content` came back empty and
`e3b0c442…` — the SHA of the empty string — was printed four times as *1 distinct of 5*. The
instrument could not observe the thing under test and said nothing about it.

▶ **The ruling: a per-call derived seed, recorded; temperature untouched.** Derived from the
attempt, the head's **digest** and the round index. Two rounds differ, two heads differ, and a retry
differs from its parent — which matters now that F701 has a retry opening on its parent's closing
tree. **A constant seed plus F701 would have made a retry a no-op.** The digest rather than the
head's name, so editing a charter re-seeds the calls made under it: two builds that disagree about
the prompt must not agree about the sampler and read as a replication.

`u32`, because the request is JSON and LM Studio parses it in TypeScript, where an integer past
2^53 is rounded silently. `u32::MAX` is llama.cpp's *pick one for me* sentinel and is the one value
the derivation will not return.

🚨 **Three negative controls, and the middle one is why the test asserts both directions.** A
constant seed fails the three difference tests. A **random** seed fails only the replay half — it
passes three of four. Dropping the field from the payload fails the wire test.

---

## 6. F716 — a seed does not pin this stack, and MTP is why

The streaming path was checked separately, because the engine streams and the probe did not.
Streaming turned out not to be the variable at all — and something else was.

| | distinct |
|---|---|
| `stream=false`, seed `3041887211` | **2 of 6** — `A B A B A B` |
| `stream=true`, same seed | **2 of 6** — the same two hashes, the same alternation |
| `stream=true`, seed + `temperature 0` | 1 of 6 |
| `stream=true`, `temperature 0` alone | 1 of 6 — the same hash as the line above |

The alternation is in **MTP speculative decoding**, and the draft counters say so in step:

```
seed 3041887211    596174ee   draft 72 accepted 65 rejected 7
                   1ff51234   draft 69 accepted 62 rejected 7     <- alternating
seed 42            350aa23a   draft 71 accepted 63 rejected 8
                   350aa23a   draft 70 accepted 63 rejected 7     <- also alternating
```

🚨 **The draft state alternates on every call for both seeds. Whether it reaches the output depends
on the seed.** When the accepted-draft count changes, the sampler's draws land on different tokens —
sometimes at the same argmax, sometimes not.

Over eight seeds at four runs each: **seven pinned the output completely, one alternated.** ⚠ **Four
runs is not proof that a seed holds — it is proof that one does not**, so 1 in 8 is a floor on the
rate and not an estimate of it. `temperature: 0` held in every arm tested, because an argmax makes
no draw.

▶ The champion is **MTP-on by default**, so this is the baseline rather than a configuration. ▶ And
it is why the claim is *attributable* and not *reproducible*: the log now names the seed that
produced an answer, which is strictly more than it could say yesterday, and it is not a guarantee
that re-flying it returns the same answer.

---

## 7. ⏸ What is left

* **K-series arms B and C** never ran, and are readable against arm A only while subject sha
  `877588415bedd40e` / llama.cpp `2.27.1` / `-c 40960` hold. ▶ **And they are now worth re-reading
  against F716**: a per-cell difference between two quantizations was measured unseeded, on an
  MTP-on server.
* 🚨 **`review_recorded` is still 0 of 11,311** and `abcc review <sha> <minutes>` has never been
  run. Plumbed end to end. The cheapest unblock on the board and it costs one command.
* **`Command::OrdersGiven`'s fate** (F703) · a second arm for the `summary` lever · the four `paint`
  changes · row 8's other half · the 96 voices.
* ⏸ **The sprite corpus is deferred, not open** (F714). It returns when new art arrives.

---

## Findings

### F714 — three shipped-doc claims the code refutes, and a deferral restated as met

`README.md` said *it never says `Accomplished`* (five `task_transitioned` rows say otherwise, and
`abcc-drive/src/lib.rs:895` is the path), *488 numbered findings* (713), and — with `CREDITS.md`, in
the same words — that the art is *carried across unchanged*, while `git ls-files` finds **0** art
files and `corpus_root` refuses without `--sprites`. 🚨 **The packaging decision behind the third was
put to the operator on 2026-09-07 with the numbers and answered *wait*; `CONSOLE-P9` §8 says nobody
should re-ask or start it.** This session's queue carried it as *precondition now met*. The
precondition is *when the art settles*; the corpus files are still dated February. ▶ **A deferred
decision is not an open one, and the confident restatement of its precondition came from a session
that had not opened the deferral.** Re-measured: 28 files, 16 distinct, admission filter draws 4,
all twelve distinct PNGs refused, and the four that draw are 34.3 MB of 35.

### F715 — the engine sent no sampling parameters, so no rate it produced was repeatable

`max_tokens` was the only sampling field (`abcc-engine/src/openai.rs`). Five identical requests to
the champion: **5 distinct answers of 5** with what the engine sent; **1 of 5** with a seed added;
1 of 5 at `temperature 0`; and seed-plus-temperature byte-identical to temperature alone, which
proves both knobs reach the sampler. The server's inherited default temperature is not 0, since the
seeded and the greedy answers differ. 🚨 **F657's *4 of 5 versus 1 of 5 on a byte-identical prompt an
hour apart* is arm A of this probe**, so it was unfalsifiable by construction rather than merely
unreproduced. Fixed: a **per-call derived** seed — attempt, head digest, round — sent on the wire
and recorded on `ModelCallStarted`. Derived and not fixed because F701 has a retry opening on its
parent's tree, and a constant would have made the pair a no-op. `u32` because LM Studio parses JSON
in TypeScript; `u32::MAX` excluded because it is llama.cpp's *random* sentinel. ⚠ The first pass of
the probe compared four empty strings — the answer was all in `reasoning_content` — and returned a
clean *1 of 5* while measuring nothing.

### F716 — MTP alternates draft state on every call, so a seed does not pin this stack

Refines **F715**. Non-streaming and streaming behave identically, so the stream is not the variable.
For one seed the output alternated `A B A B A B` over six calls, and the MTP draft counters
alternated in exact step (72/65/7 then 69/62/7); for another seed the counters alternated too
(71/63/8 then 70/63/7) and the output did not. 🚨 **The draft-acceptance state flips on every call
regardless of the seed; whether it reaches the tokens depends on the seed.** Over eight seeds at
four runs each, **seven pinned the output and one did not** — a floor on the rate, not an estimate,
because four runs cannot prove a seed holds. `temperature: 0` was deterministic in every arm,
because an argmax makes no draw. The champion is MTP-on by default, so this is the baseline. ▶ Say a
seeded sortie is **attributable**, never *reproducible*.

### F717 — F713's cost is a quadrupling, and F713 said size was not the objection

Refines **F713**. *Output is already bounded, so size is not the objection* was asserted twice and
never measured. Measured from `prompt_tokens` growth across 1,136 inter-call windows on the live
log: a tool result is **244 tokens at the median and 984 at the mean**, p90 3,168, p99 7,228 — the
tail is file reads. Over 2,147 tool calls that is **6.6–8.6 MiB against 2.7 MiB of event bodies**,
so `log.sqlite` goes from **3.9 MiB to about 12 MiB** for five active days. The bound was real and
the multiplier is what the sentence should have carried. ⚠ No second cap is applied on the way to
the log: the text is already bounded to what the model is held to, and truncating again would put a
different text on the record from the one that was sent.
