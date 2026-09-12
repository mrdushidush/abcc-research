# W1 — the K-series subject was never at the server's own sampling, and a seed would add nothing

**Status: the prescription standing over K-series arms B and C is wrong on both halves, and this is
the measurement that says so.** Written 2026-09-12 (session 7) against `abcc` `1f2d5ff`. Findings
**F728–F729, next free F730** — ask `fledger.py next`, never this line. Probe:
`research/tools/tempzero.py`, 35 live calls, about four minutes on the loaded champion.

The queue said: *if arms B and C are ever run, each cell n ≥ 3 **at a recorded seed***. That
sentence was written from F715 and F716, which were measured on **`abcc`** — a different program
from the one the K-series flies. Checking the subject instead of inheriting the reasoning:

## 1. F728 — the subject sends `temperature: 0.0`, and at temperature 0 this stack pins itself

**F728 — the K-series subject is greedy, not unseeded.** `claudette`'s OpenAI-compat request body
(`crates/claudette/src/api.rs:783`, present at `af3f804`, the subject batch 2 and 3 were flown with)
is exactly:

```json
{ "model": …, "messages": …, "tools": …,
  "stream": true, "stream_options": {"include_usage": true},
  "temperature": 0.0, "max_tokens": … }
```

**No `seed`. No `top_p`. And `temperature: 0.0`, on every call this rig has ever made.** So the
cells were never *at the server's own sampling* the way `abcc`'s pre-`223ae3a` calls were — they
were at argmax, which is a much stronger position than the queue's note assumed.

Measured on the champion, `qwen3.6-35b-a3b-mtp@iq3_s` at `-c 40960 --parallel 1`, one 133-character
prompt, `max_tokens` 400 (every call hit the cap, so 400 tokens are compared each time):

| arm | what it sends | result |
|---|---|---|
| A | `temperature 0`, no seed — **what the subject sends** | **1 distinct of 5**, twice |
| B | `temperature 0`, `seed 424242` | **1 distinct of 5**, twice |
| C | `temperature 0.8`, no seed — **the control** | **5 distinct of 5**, twice |

🚨 **All 20 warm greedy calls returned one byte-identical answer** — the same digest
`33652eb5cada` across both passes **and across both arms**, so the seed changed nothing, which is
what argmax means. ▶ **10 of 10 at temperature 0.8 were distinct**, which is the control: the
instrument can see a difference and did.

⚠ **The instrument had to read `reasoning_content`.** `content` came back **empty on all 35 calls** —
the model spends a short answer's whole budget in the reasoning channel. A probe hashing `content`
alone would have compared 35 empty strings and reported *1 distinct* for every arm including the
control. That trap is a session-5 lesson and the tool now prints a 🚨 line whenever it fires.

⚠ **This refines F716; it does not contradict it.** F716 measured that MTP speculative decoding
flips draft-acceptance state on every call *regardless of the seed*, and that a seed therefore does
not pin this stack — true where the sampler is stochastic, and the temperature-0.8 arm above is that
same fact at n=10. **At temperature 0 the argmax survives whatever the draft state does**, and the
seed becomes irrelevant rather than insufficient.

## 2. ⚠ The one regime where greedy did vary: the first calls on an idle server

The very first pass of arm A, on a server that `lms ps` had just reported **IDLE**, gave **3 distinct
of 5** — calls 1 and 2 each unique, calls 3, 4 and 5 the settled digest. Every pass after that,
including one run immediately after five temperature-0.8 calls, gave 1 of 5.

▶ **State it as observed, not as a mechanism.** Prefix cache, MTP draft warm-up and slot allocation
would all produce this shape and nothing here separates them. What follows operationally is the same
either way: **the first calls after an idle period are not comparable to the ones after them.**

⚠ The K-series harness does warm up — `runmeta.json` carries
`warmup = {ran: true, prompt: "Reply with the single word: ready."}` — so its cells run in the warm
regime. **Whether one short warm-up call is enough was not measured**, and the observation above is
the reason to ask.

## 3. F729 — the run manifest records no sampler at all

**F729 — `runmeta.json` captures the model, the quantization, the context length, `num_predict`,
`max_iterations`, the corpus commit, the interpreters and even a `server_uncaptured` list naming
what it knows it missed — and the strings `temperature`, `top_p`, `seed` and `draft` appear in it
nowhere.** The one input F715 proved governs whether a run can be re-read is absent from the run's
own record, and the manifest has a field whose whole job is to admit such gaps.

▶ It has never produced a wrong number, because the value has been `0.0` for every cell ever flown.
▶ **It would produce one the first time anybody changed it**, and a manifest that cannot say what
the sampler was is a manifest that cannot date itself against that change. This is the same class as
F718 and F724: a fact that governs the result, with nothing writing it down.

## 4. ▶ What arms B and C actually need

1. **Not a seed.** Measured inert at temperature 0 on this stack, 20 of 20. Sending one would make
   the record look more controlled than it is.
2. **n ≥ 3 repeats, as before** — not because the sampler wanders but because batch 1 already
   caught the champion passing a task in two repeats and failing it in the third. **n = 1 would have
   reported either extreme as fact**, and that reason is independent of sampling.
3. **The sampler written into `runmeta.json`** — `temperature`, `top_p`, `seed`, and whether the
   loaded build is speculating — so a future reader can tell a re-run from a re-read.
4. ⚠ **And the honest claim stays *attributable*, never *reproducible*.** One short completion
   repeating 20 times is not a 40-iteration agentic trajectory repeating: a single differing token
   anywhere diverges everything after it, and nothing here measures that.

⏸ **Arms B and C are still unrun and still gated on David** — batch 2's two 27B arms took 11,202 s
and 6,615 s for nine cells each, so two arms at n ≥ 3 is a multi-hour GPU session. Valid only while
subject `af3f804` / llama.cpp `2.27.1` / `-c 40960` hold, and the two traps in `W1-batch3-residency-probe.md`
still bind: `justInTimeModelLoading` is TRUE and `confirm_model` compares **names**.

## 5. What shipped for F729, and the control that caught a blind test

`runmeta.json` gains **`warmup.tokens_out`** — the warmup turn's `out=`, which the harness had
already matched out of the turn-end line and thrown away. The warmup prompt is held constant across
every run this harness has ever made, so two manifests that disagree about that number disagree
about something. ⚠ **A fingerprint, not a proof**: equal counts do not mean equal text. It
falsifies, it does not certify.

`server_uncaptured` grows from **one name to eight** — `kv_cache_type` joined by `temperature`,
`top_p`, `top_k`, `min_p`, `repeat_penalty`, `seed` and `speculative_decoding`. That field's own
doc says *"state that neither source reports, named rather than left silent"*, and the sampler is
exactly that: **unrecordable here, not merely unrecorded.**

The match that dropped the number is now `warmup_measurement`, its own function so a test can reach
it, and it **refuses a marker reporting `out=0`**. The prompt is *"Reply with the single word:
ready."*; a completed turn that decoded nothing is the harness failing to read the count, and the
zero it would write is indistinguishable from the honest zero a dry run writes — F721's shape, in a
new field, caught before it shipped rather than after.

🚨 **The control that mattered.** The first version of the test asserted one `(tokens_in,
tokens_out)` pair — and **replacing the field with the literal `71` passed it**. One expected value
cannot distinguish *reads the field* from *happens to equal the fixture*; two markers with
different counts can. That is item 161's lesson (*a test where the two quantities agree pins
neither*) reappearing four days later in a different file, found by running the control instead of
assuming it.

| control | what it breaks | result |
|---|---|---|
| drop the `out=0` guard | the refusal | the test fails |
| return the literal `71` instead of the field | reading the count at all | the test fails **only after the second marker was added** |

**238 harness tests pass**, `w8-run` is `clippy --all-targets -D warnings` clean.

⚠ **Two things deliberately left alone.** The harness workspace is **not** rustfmt-clean — a
`cargo fmt --all` rewrites **35 files across six crates**, which is not this change — and
`w8-import-u40` carries **5 pre-existing clippy errors**. Neither was touched, and neither is
`w8-run`'s.

⚠ **What is not covered: the wiring.** There is no end-to-end harness test that produces a
`runmeta.json`, so nothing asserts that the number reaching the manifest is the one the subject
printed. The `out=0` refusal is what stands in for it: it makes `"ran": true` with
`"tokens_out": 0` impossible, which is the failure a silent wiring break would produce.
