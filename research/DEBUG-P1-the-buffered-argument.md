# DEBUG P1 — the buffered argument, and a liveness instrument that reports after the silence

**2026-09-05.** F606 left two candidate causes with opposite fixes and said *one live run
separates them*. It did, on the first attempt. The run cost about six minutes of GPU; what it
found reaches further than F606 asked, because the same measurement falsifies the premise of
F537's fix and puts a hard ceiling on how large an `apply_patch` this stack can deliver.

Findings **F622–F626**. Instrument `research/tools/ssecapture.py`, raw captures in
`research/spikes/f606-sse/`.

---

## 1. What was asked

F606: on every full-cap truncation the composition accounts for 1.4–1.9% of the tokens billed
and the single `apply_patch` call's `argument_chars` is **zero**. Two candidates survived the
fold and it could not separate them:

1. **The argument deltas were streamed and the in-flight counter never accumulated them** — our
   instrument is broken and the fix is in `abcc-engine`.
2. **The tokens never crossed the socket** — our instrument is correct and the fix, if there is
   one, is in how we ask.

They have opposite fixes, so the question had to be settled at the wire rather than in our own
parser. `ssecapture.py` posts to the same endpoint `abcc` uses — `http://127.0.0.1:1234`, the
LM Studio API port — with `abcc`'s own `apply_patch` schema
(`crates/abcc-engine/src/tools.rs:245`), and writes **every SSE line with a millisecond offset**
to disk before anything interprets it.

## 2. Three arms

Champion `qwen3.6-35b-a3b-mtp@iq3_s`, `-c 40960`, `--parallel 1`, `temperature 0`.

| arm | prompt | `max_tokens` | finish | completion tokens | wire argument chars | **argument deltas** |
|---|---|---|---|---|---|---|
| `cap8192` | large module | 8,192 | **`length`** | 8,192 | **0** | **0** |
| `complete_small` | small module | 16,384 | `tool_calls` | 559 | 231 | **1** |
| `bigarg` | large module | 24,576 | `tool_calls` | 9,743 | **33,962** | **1** |

`cap8192` reproduces the field shape exactly: `finish_reason: length` at the cap, one
`apply_patch`, zero argument characters.

## 3. F622 — the server buffers the whole tool call and delivers it in one delta, at the end

This is the finding everything else follows from, and the two completing arms prove it across
two orders of magnitude of argument size:

| arm | argument chars | deltas | first delta at | last delta at | call ended at |
|---|---|---|---|---|---|
| `complete_small` | 231 | **1** | 6,243 ms | 6,243 ms | 6,244 ms |
| `bigarg` | **33,962** | **1** | 226,377 ms | 226,377 ms | 226,381 ms |

**33,962 characters arrive in a single delta in the last 4 milliseconds of a 226-second call.**
Size changes nothing: there is no incremental delivery of tool-call arguments at any size.

🎉 **The control is in the same responses.** `reasoning_content` streams token by token
throughout — `cap8192` put 4,986 chunks and 20,049 characters of trace on the wire before the
call began. So this is not a buffering proxy or a client artefact: the same connection delivers
one field continuously and holds the other back.

**What the wire actually carries**, `cap8192`:

```
+54,743 ms   {"delta":{"tool_calls":[{"index":0,"id":"...","type":"function",
              "function":{"name":"apply_patch","arguments":""}}]}}
             <-- 28.5 SECONDS OF NOTHING -->
+83,272 ms   {"delta":{},"finish_reason":"length"}
+83,272 ms   {"usage":{"completion_tokens":8192,...,"reasoning_tokens":4982}}
```

The server announces the call's **name** the moment it starts one, with `arguments: ""`, and
then says nothing at all until the call parses.

## 4. F623 — cut at the cap, the arguments never leave the server. **F606 is answered**

In `cap8192` the model was billed 8,192 completion tokens, of which 4,982 are reasoning. The
remaining **3,210 tokens — 39% of the budget — went into the tool call and produced zero bytes
on the socket.** At the 4.02 chars/token this arm's trace measures, that is roughly 12,900
characters of `apply_patch` diff, generated at full speed and discarded server-side because the
parser never reached a complete call.

🚨 **So F606's candidate 1 is dead and the instrument is exonerated.** `argument_chars: 0` in
the log is a **true reading**, not a counter that failed to accumulate. Nothing in `abcc` needs
fixing for the count to be right — it was right, and the thing it was reporting is that the
tokens genuinely never arrived.

⚠ **The share differs from the field cases and the mechanism does not.** The three logged
truncations accounted for 1.4–1.9% because their traces were tiny (344–468 chars); this
reproduction accounts for 61% because the prompt provoked a 20,049-character trace. What is
identical is the part that matters: an `apply_patch` whose arguments are billed and never sent.

## 5. F624 — `Delta::ToolCallProgress` reports *after* the silence, and the field log already said so

F537 built `Delta::ToolCallProgress` because *"a model writing one large tool call delivers bytes
continuously while producing no delta at all"* (`provider.rs`, the delta's own doc comment). The
measurement above falsifies the premise: **the server does not deliver bytes continuously.** It
delivers nothing until the call parses, and then delivers everything.

`fragment()` pushes a progress delta only `if pushed > 0`, i.e. only when a non-empty
`function.arguments` fragment arrives. On this server that happens **exactly once per call, in
its final milliseconds.** The instrument fires after the silence it exists to break.

🚨 **And the field log has been saying this since the day F537 landed.** Of 237 liveness marks,
22 carry F537's three-clause form; of those, three report a non-zero argument count — and
**every one of them is the terminal mark of its call**:

| call duration | mark at | argument chars |
|---|---|---|
| 10.234 s | +10.2 s | 62 |
| 29.071 s | +29.1 s | 3,096 |
| 27.738 s | +27.7 s | 6,752 |

In the 29-second call the mark at **+10.0 s reads 0** and the mark at the end reads 3,096: the
whole argument appeared between them, in one delta. **No call anywhere in the log shows the
argument count growing across two marks.** The trace count in those same marks grows smoothly —
2,254 → 4,941 → 8,326 → 11,220 — which is what genuine incremental streaming looks like, in the
same records, as a control. These runs are 2026-08-30, *after* F537.

▶ **This does not make F537 wrong about the diagnosis.** The 90-second "hang" it investigated
was real and the GPU really was at 75%. What it got wrong is *where the bytes were*: it assumed
they were arriving unnoticed, and they were not arriving.

## 6. F625 — a **successful** 33,962-character patch is 211 seconds of silence against a 90-second gap

`idle_gap` is the **per-read** budget (`provider.rs:261`) and it is **90 s** for the champion
(`turn.rs:173`). The largest unbroken silence in each arm:

| arm | largest silence | starts at | total call |
|---|---|---|---|
| `complete_small` | 0.7 s | +5.5 s | 6.2 s |
| `cap8192` | 28.5 s | +54.7 s | 83.3 s |
| **`bigarg`** | **211.2 s** | +15.2 s | 226.4 s |

🚨 **`bigarg` succeeded.** It returned `finish_reason: tool_calls` and a well-formed
33,962-character `apply_patch`. And `abcc` would have killed it at 90 seconds and recorded
`Why::Timeout`, because for 211 of its 226 seconds the socket carried nothing and
`ToolCallProgress` cannot fire until the end.

**So there is a ceiling on the size of patch this stack can accept, and it is set by the idle gap
rather than by the model or the token budget.** Argument generation measured 161 chars/s
(`bigarg`) and 331 chars/s (`complete_small`); 90 seconds of silence therefore buys roughly
**14,000–30,000 characters**. The largest `apply_patch` this stack has ever delivered intact is
**17,157 characters** (`Head::budget`'s doc comment) — which sits inside that band.

▶ **That record is very likely the gap's ceiling, not the model's.** It was read as evidence
about what fits through and used to size `Head::budget` at 16384 tokens; on this evidence it is
evidence about what survives 90 seconds of buffering.

## 7. F626 — the two `Timeout` failures have this shape, and the log cannot finish the sentence

Both `SoftFailure/Timeout` attempts among the twenty `MISSION FAILED` ended at **`after_ms:
90000` exactly**, each with a `model_call_started` ~96 s earlier and **no liveness mark between
them**:

| attempt | task | ended | what precedes it |
|---|---|---|---|
| 1642 | 1636 | 2026-08-29 12:29:35Z | `model_call_started` at −97.4 s, no marks |
| 2086 | 2080 | 2026-08-29 12:45:01Z | `model_call_started` at −96.2 s, no marks |

That is precisely the signature F625 predicts. ⚠ **It is not proof.** Both predate F537, so
`tool_call_chars` did not exist and nothing recorded what was in flight; a genuinely dead socket
produces the identical record. **The log cannot tell these apart, which is F592 again** — and it
is why the next `Timeout` should be caught with the raw stream beside it.

## 8. What this leaves

**Settled, and needs nothing:** the composition counter. It reads zero because zero arrived.

**Open, and David's, because it is the idle gap's semantics (ADR-0015 §1, amended by ADR-0021):**
the gap can no longer be justified as *a claim about whether the stream is delivering*, because
on this server a healthy stream stops delivering for the entire duration of a tool call. Three
shapes of repair, and they are not equivalent:

1. **Suspend the gap between the name and the call.** The server tells us a call has opened —
   `arguments: ""` is that announcement — so the state *waiting for a tool call to parse* is
   observable, and the gap could be widened or lifted only inside it. Narrow, and it uses a
   signal we already receive and currently discard.
2. **Raise `idle_gap` for the builders head.** Cheapest, and it degrades the hang detector
   exactly where hangs cost the most.
3. **Ask the server not to buffer.** Unknown whether LM Studio can be told to stream tool-call
   arguments; if it can, F537's premise becomes true and its instrument starts working. This is
   a probe, not a decision.

⚠ **Whatever is chosen, `Delta::ToolCallProgress`'s doc comment must stop asserting the premise
this session falsified** — F609's lesson, one document later: a rationale written in the present
tense expires, and this one expired the day it was written.

**Also owed:** `Head::budget`'s doc cites 17,157 characters as *the largest this stack has
delivered intact* and reasons from it. That number should carry F625's caveat, because it is
probably a measurement of the timeout.
