# K-series — how to run a model comparison, and how to read one

The suite `suite.toml` carries the design rule. This file carries the operating
procedure, because a comparison run has three ways to produce a number that
means nothing, and all three are avoidable.

## What this suite is for

Deciding between two **base models** on the axis §W1 actually names — *agentic
multi-file work under context pressure* — rather than on a score column §11.0
bars for that purpose. The first live use is Qwen3.8-27B against the champion
`qwen3.6-35b-a3b-mtp@iq3_s`.

## Running a comparison

Both arms must be run at the **same context window**, with **neither model
spilling**, or the run measures which model fits rather than which model is
better. On this box (RTX 5060 Ti, 16,311 MiB) that means **`-c 40960`**:

| model | at `-c 65536` | at `-c 40960` |
|---|---|---|
| champion | 14,745 MiB (90.4%) | 14,318 MiB (87.8%) |
| qwen3.8-27b | **15,847 MiB (97.2%), 464 MiB spare** | 15,269 MiB (93.6%) |

```bash
# arm A
lms unload --all && lms load qwen3.6-35b-a3b-mtp@iq3_s -c 40960 --gpu max --parallel 1 -y
cargo run -q -p w8-run --bin w8-run -- ../corpus --suite k \
    --subject claudette-af3f804 --model qwen3.6-35b-a3b-mtp@iq3_s \
    --num-ctx 40000 --bin /path/to/claudette

# arm B — identical except --model, and the model actually loaded
lms unload --all && lms load qwen3.8-27b -c 40960 --gpu max --parallel 1 -y
cargo run -q -p w8-run --bin w8-run -- ../corpus --suite k \
    --subject claudette-af3f804 --model qwen3.8-27b \
    --num-ctx 40000 --bin /path/to/claudette
```

`--num-ctx 40000` under a 40,960 load is the deliberate cushion; the inequality
**LM Studio window ≥ `CLAUDETTE_NUM_CTX`** is not enforced on the wire, because
the OpenAI-compat dialect has no `num_ctx` field at all (`research/W2-serving.md`
F84). The dangerous direction is silent.

## The three ways to get a meaningless number

1. 🚨 **Comparing a spilling model against a comfortable one.** At `-c 65536`
   the 27B has 464 MiB of headroom and its prompt processing collapses. Measured
   at a matched 40,960 with neither spilling, the champion is still **2.25×
   faster on prefill and 2.54× on decode** — that is the honest speed gap, and
   any quality win has to be paid for out of it.

2. 🚨 **Not reporting `peak_prompt_tokens` per cell.** These tasks create
   pressure by requiring a subject to read across a codebase. A subject that
   greps instead of reading, or that evicts aggressively, may finish a task
   having never held 25k tokens. That is a legitimate strategy — but a cell that
   never entered the regime cannot be evidence about the regime, and a low score
   from a subject that never entered it looks identical to a low score from one
   that did.

3. 🚨 **Using the wrong binary.** `--bin` matters and `--version` will not save
   you: the subject descriptor pins commit `af3f804`, and a `claudette` built
   eighteen minutes before that commit reports the identical `0.17.0`. The
   delivery pre-flight catches it (it refuses rather than measuring against a
   prompt the subject never received whole), but only because someone wrote that
   check. Point `--bin` at a binary you rebuilt from the pinned commit, and
   confirm the rebuild actually happened — `cargo build` will report "Finished"
   without recompiling if it believes the target is fresh.

## Reading a result

The aggregate is `include_verifiable = ["full"]`, so only tasks whose verifier
executes the artifact count. Every K task's verifier is built to reject a
specific **local wrong answer** — the fix at the point of the symptom — so a
FAIL here is usually not "the model could not code". It is "the model patched
the symptom". Read the workdir diff before concluding anything else; the
distinction between those two failures is the whole reason this suite exists.

A PASS establishes that the subject traced a defect across the codebase to its
cause. It does not establish that it would do so on a codebase ten times the
size, and nothing here is calibrated against a human engineer (`suite.toml`
caveats).
