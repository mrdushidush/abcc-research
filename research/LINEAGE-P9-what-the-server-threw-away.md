# LINEAGE P9 — what the server was throwing away, and the malformation it left behind

Session 10, 2026-09-13. `abcc` `6e1cbaa` → **`79d7b20`**, `abcc-research` at `4bbb099`, both trees
clean. Findings **F748–F757**. ▶ The queue's first item was *F744's repair*, and the repair itself is
a trade the operator rules on. What was buildable without that ruling is everything underneath it:
**F744's own rate, re-counted against the right denominator; why nothing in the workspace could see
the cut; a detector that can; what the server actually discards; and what that costs.**

🚨 **Three of this session's ten findings correct the session that produced them.** F744's rate was
overstated fourteenfold, its headline example is not a truncation at all, and the thing that ends the
attempt is not the cut — it is the **malformation the cut leaves behind**, which silences the model
at a size that fits comfortably.

---

## 1. 🚨 F748 — the unit of monotonicity is the PHASE, and the count was keyed on the attempt

F744's argument is exactly right and it is worth restating, because everything below rests on it:
`Body`'s only mutation is `append` — no `insert`, no `prepend`, no indexed write — so `prompt_tokens`,
the server's own measurement of that object, **cannot fall**. A non-monotone measurement of a
monotone object means the object was cut before it was measured.

▶ **But the object is not the attempt's body. It is the phase's.** `abcc-drive/src/lib.rs:703`
builds `Body::opening(brief)` *inside* `phase()`, once per phase, and `phase()` is the only caller of
`TurnLoop::run` in the workspace. Localize, Change and the Judge each get a **fresh body** — the
Judge's freshness is a documented design decision (F280–F282: same model, fresh call, and nothing the
author wrote in prose). So a fall at a phase boundary is not a truncation. **It is the design
working.**

The archive's instrument, reproduced exactly and then segmented:

| | falls > 1,000 tokens | attempts |
|---|---|---|
| **as published, keyed on the attempt** | **117** | **86 of 98** |
| of which: at a phase boundary — a fresh body | **103** | — |
| of which: `localize` → `change` | 84 | — |
| of which: `change` → `judge` | 19 | — |
| **within one phase — the truncation** | **14** | **6 of 98** |

▶ **The rate is 6% of attempts, not 88%.** The reproduction is exact — the same query keyed on the
attempt returns 117 and 86, the published pair — so this is the same instrument re-read and not a
different one. 🚨 **F744's phenomenon stands and F745's external measurement is untouched.** What is
corrected is its size: **the count was 8.4× the truncations, and 14× on the attempt.**

⚠ **The shape of the error is worth more than the number.** 204 phase segments over 98 attempts means
**106 body resets in the archive**, and 103 of them landed in a bucket labelled *the server cut the
prompt*. A denominator that is one level too wide does not add noise — here it added **7 times the
signal**, all of it in the direction that made the finding look bigger.

---

## 2. F750 — the deepest drop in F744 is the Judge opening its own body

The published headline is *largest single drop **38,006 tokens** (`a8007`: peak 40,087, last call
2,081)*. Those two numbers are the **last call of `change`** and the **only call of `judge`**:

```
a8007  [change]  ... 39,584 → 39,981 → 40,087     the window, nearly full
a8007  [judge]   2,081                            a fresh body: the task, the diff, the rungs
```

▶ **Nothing was discarded there.** `abcc-drive:1059` builds that call's body from `judge::Dossier`,
and 2,081 tokens is what a task, a diff and four rung results weigh. 🚨 **Do not quote 38,006 as a
truncation.** The largest real cut is **27,041** (§3), and the largest thing this number measures is
how much cheaper the Judge is than the phase it reviews.

---

## 3. F749 — the number the work is spent on is CUT CALLS, not falls

A fall counts a *transition*. What an attempt pays for is every call **shown** a cut prompt — and
after the first cut every later call in the phase is also cut, because the body keeps growing and the
window does not. The test for *this call was cut* is therefore **below the phase's running maximum**,
not *below the previous call*, and it needs no threshold at all: any amount is impossible.

| | |
|---|---|
| model calls in the archive | **1,977** |
| calls shown a cut prompt | **74 — 3.7%** |
| falls, at any size | **23** |
| phases carrying at least one | **12 of 204** |
| attempts carrying at least one | **12 of 98** |
| deepest cut | **27,041** — `a9480` `change`, 40,832 already measured, 13,791 reported |

🚨 **The two readings differ by 3.2× and the larger one is the true one.** `a9480` is the case that
shows why: the *fall* from 19,496 to 13,791 is 5,705 tokens, and that same call is **27,041 below
what the server had already measured for this conversation** seven calls earlier. The fall
understates the damage by nearly five times.

⚠ **And it is concentrated, not spread.** Six attempts carry 68 of the 74 cut calls — 18, 17, 9, 9,
9, 6 — and six more carry one each. So *12 of 98* is the right rate and *a long attempt that fills
the window is nearly certain to be cut repeatedly* is the right sentence; **a rate quoted per attempt
hides that the tail is the whole cost.**

---

## 4. 🚨 F751 — every window detector in this workspace is a function of ONE turn

This is why nothing could see it, and it is structural rather than an oversight.

* **F498's detector** — `Turn::uncertain` — reads `finish == length` and `completion < budget` and
  concludes the window from `prompt + completion`. One turn's own numbers.
* **F747's detector** — the `HTTP 400` — is one request's own refusal.

Both loud paths **announce themselves inside the turn that suffers them.** The silent cut does not:
status `200`, `finish: tool_calls`, no header, no field, no warning, and a `prompt_tokens` that is
merely *smaller than one an operator saw several screens ago*. ▶ **A detector that sees one call can
never find it.** The only witness is the **sequence** — and the sequence's scope is the phase (F748),
which is exactly the scope the turn loop already runs in.

---

## 5. The build — `Event::PromptCut`, at `829e485`

F744 ends *nothing is logged, no event is emitted, and `abcc replay` cannot say it happened.* Now it
can. The loop compares each turn's `prompt_tokens` against the phase's high water and records
`PromptCut { attempt, reported, high_water }` when it comes in under it.

Four decisions worth keeping:

1. **The detection is returned from the fold.** `PhaseReport::count` updates the high water and
   answers *was this cut* in the same three lines, so the loop cannot read a stale one and cannot
   forget to ask.
2. **The high water lives on the phase's report**, which is what makes F748's error unrepresentable:
   a new phase is a new report.
3. **`high_water - reported` is a floor, never the amount.** Everything appended since the high-water
   call is missing from this prompt too, and nothing measures that part.
4. **Nothing acts on it.** `BudgetExhausted` is left naming the rounds and the cut count sits on the
   log beside it: copying one into the other would be two things that can disagree.

`abcc replay` prints the count and the deepest cut **only when there are some** — zero is *no cut
recorded*, which over the 1,977 calls logged before this detector means nobody was looking, and a
line reading `0 cuts` would turn that into a measurement. Seven tests; 636 passing at that commit.

---

## 6. 🚨 F753 — what the server discards is the MIDDLE, and the vendor's own type says so

F746 left this open: *whether this is llama.cpp's context shift, an LM Studio policy, or a server
setting this project can turn off — and what it discards.* Measured, with canaries: a code word in
the system message, one in the first user message, one in the middle, one in the last, and a system
instruction to report `MISSING` for anything it cannot find rather than guess.

| arm | messages | reported | system | first | middle | last |
|---|---|---|---|---|---|---|
| **control — fits the window** | 22 | 11,177 | FOUND | FOUND | FOUND | FOUND |
| **overflow — same shape** | 122 | **19,689** | **FOUND** | **FOUND** | **MISSING** | FOUND |

▶ **The system prompt and the first user message survive; the middle is gone.** And LM Studio's own
SDK names the policy that does exactly that — `@lmstudio/sdk/dist/index.d.ts:3456`:

> `truncateMiddle`: **Keep the system prompt and the first user message, truncate middle.**

🚨 **So it is an LM Studio policy and not llama.cpp's context shift**, and the discrimination against
the neighbouring value is clean: `rollingWindow` *truncates past messages*, which would have taken
the first user message with them, and it survived in every flight.

**What that means for abcc is worse than a size loss.** What survives is the **frozen head** and the
**opening brief** — the two things abcc could rebuild from the log in a second. What goes is the
middle of the transcript, which is **nothing but tool results**: the files the phase read, the
searches it ran, the diffs it was shown. ▶ **F743's 47.2% of re-read bytes is not the model being
wasteful — it is the model re-reading the only thing that was taken away from it.**

⚠ **One canary is unreliable and is not leaned on.** The *last* code word sits in the question
itself, and the model repeatedly reported it `MISSING` even in arms where it was plainly present —
apparently declining to count a word stated in the question as one it *was given*. The load-bearing
contrast is **first FOUND against middle MISSING**, which no reading of the instrument can invert.

---

## 7. F754 — the policy cannot be reached from the request, and there is no flag for it either

If the policy were `stopAtLimit` the cut would be loud, so the obvious question is whether abcc can
ask for that. Measured on the same overflowing conversation:

| request | reported | behaviour |
|---|---|---|
| no policy field | 19,689 | 200, middle gone |
| `"contextOverflowPolicy": "stopAtLimit"` | **19,689** | **200, middle gone — identical** |
| `"contextOverflowPolicy": "truncateMiddle"` | 19,689 | 200, middle gone |

▶ **The field is ignored.** `stopAtLimit` is the one value whose whole point is to refuse rather than
truncate, and it produced neither a refusal nor a different number. **`lms load` has no option for it
either** — the full option list carries context length, GPU ratio, parallelism, TTL, identifier and
the speculative-decoding family, and nothing about overflow. So the lever exists at the **SDK and GUI
level** (`LLMContextOverflowPolicy = "stopAtLimit" | "truncateMiddle" | "rollingWindow"`) and **not
at the HTTP one this project uses**. ⏸ **Not tested: setting it in the GUI**, which is the operator's
machine and the operator's call.

⚠ Two otherwise identical requests in that table returned 482 and 807 completion tokens at one seed.
That is F716 restated — **a seed makes a run attributable, not reproducible** — and it is the reason
the arms below are flown more than once.

---

## 8. 🚨 F752 — the loud door was recorded as a fault in this engine. Fixed at `79d7b20`

F747's 400 is reachable in ordinary work: a single 45k-token `read_file` result appended to a body is
**one oversized message**, which is the shape that takes the refusal path. Read off the wire today at
two sizes:

```
HTTP 400
{"error":"Engine protocol predict request returned 400: {\"error\":{\"code\":400,
\"message\":\"request (44477 tokens) exceeds the available context size (40960 tokens),
try increasing it\",\"type\":\"exceed_context_size_error\",
\"n_prompt_tokens\":44477,\"n_ctx\":40960}}"}
```

▶ **Today that becomes `ProviderError::Status` → `Why::EngineError` → `HardFailure`**, which asserts
*another attempt would repeat this unchanged* — the one thing that is not true of a window overflow.
🚨 **This is F496's correction re-entering through the status code**: F496 found the same
misclassification at the `length` door and fixed it there.

**And the repair buys more than a class name.** `Why::ContextOverflow` is the only `Why` in the
workspace whose `next_after` is **`HandToOperator`**, with `brief::overflowed` naming the window and
the number to beat. So the classification turns a task stopped as broken into a question with an
answer in it.

⚠ **The body's shape is the trap.** The outer `error` is a **string** holding a second JSON document,
so `body["error"]["type"]` reads nothing and a structured parse of the whole body finds no fields at
all. The scan is therefore a substring search for the marker and the first digits after each name,
escape-blind so it reads the nested form and a future plain one. **Both numbers or nothing:** a
renamed field keeps today's classification, which is the wrong class but the safe direction, because
inventing a window would put a fabricated measurement on the log.

⚠ **`brief::overflowed` had to be reworded**, and that is the small honest half of this: it said *the
reply was cut off part-way*, which did not happen at the new door — nothing was generated — and
*{prompt_tokens} of it was prompt*, which reads as nonsense when the prompt is **larger** than the
window it did not fit.

---

## 9. 🚨🚨 F755 — the cut is not what costs the answer. The ORPHANED TOOL RESULT is

The plain prose arm answered its question perfectly well **while truncated** (§6), which is the
observation that makes the next one necessary: abcc does not send prose. It sends
`assistant(tool_calls)` / `tool(result)` **pairs**, and `truncateMiddle` drops middle **messages**.

The same probe in abcc's own shape, seven flights over three seeds and two budgets:

| arm | prompt | reply text | finish |
|---|---|---|---|
| **tool pairs, fits** — 8 pairs | 7,373 | **answered, 5 of 5** (65–131 chars) | `stop` |
| **tool pairs, cut** — 70 pairs | 19,680 | **nothing, 7 of 7** | `length` ×6, `tool_calls` ×1 |

▶ **Six of the seven spent their entire completion budget and returned zero characters of text** —
4,975 to 18,981 characters of reasoning trace, and no answer. A budget of 6,000 bought 18,981
characters of trace and still no reply.

🚨 **So the malformation was built by hand, at a size that fits, with the cut out of the picture.**
Take the intact 8-pair conversation and remove four `assistant(tool_calls)` turns, leaving their
results behind; then the mirror image, removing four results and leaving their calls:

| arm | prompt | reply text | finish |
|---|---|---|---|
| intact pairs — the control | 7,373 | answered, 2 of 2 | `stop` |
| **orphaned tool RESULTS** — a result whose call is gone | 7,221 | **nothing, 0 of 2** | `length` |
| orphaned tool CALLS — a call whose result is gone | 3,980 | answered, 2 of 2 | `stop` |

▶ **One of the two malformations is fatal and the other is harmless.** A result with no call makes
the model reason to its cap and say nothing, at **7,221 tokens against a 40,960-token window** — the
window is not involved. A call with no result costs nothing at all.

**And `truncateMiddle` on abcc's body produces the fatal one by construction**: it keeps the system
prompt, the first user message and the tail, and the tail of an abcc body begins wherever the cut
landed — mid-pair, on a `tool` result whose `assistant` turn is above the cut.

🎉 **`turn.rs` had already guessed at this, and both of its guesses are wrong.** The comment above
`body.append(Message::assistant_calling(...))` says a tool result whose question is missing is *"a
message the OpenAI dialect rejects and a lenient template renders as an answer from nowhere."* It is
neither: this server returns **200 OK** and renders something the model cannot answer over at all.
⚠ The two arms are not size-matched — removing results removes most of the bytes — but the intact
control at 7,373 answers and the orphan-result arm at 7,221 does not, so size is not the variable.

---

## 10. F756 — so the ending abcc records for this names the wrong resource, again

Take the fatal arm through this workspace's own classification. `finish: length` with
`completion_tokens == budget` fails F498's first branch (`completion < budget`) and lands on
`Why::TruncatedAtCap { budget }` → `Uncertain` → a retry.

▶ **The record therefore says *stopped at the 1500-token cap*, and the cause is a prompt the server
cut and a conversation the truncation malformed.** That is F746's shape — *`BudgetExhausted { 24
rounds }` names the wrong resource* — one level down, and now measured on the shape rather than
argued from the archive. 🚨 **Neither reading is available from the ending alone**, which is the whole
case for `PromptCut` being on the log beside it (§5).

⏸ **A hypothesis this raises and does not settle:** F503's empty answers — *the closing answer missing
from 8 of 10 phases*, repaired by a nudge — were read as a model quirk. A cut prompt produces the
same signature. Whether any of those ten phases was over the window is answerable from the archive
and was not asked here.

---

## 11. F757 — the ruling any repair inherits: trim in PAIRS, and the pair to keep is the result

Every option on F744's repair list involves abcc deciding what its body may contain — a cap on what
enters it, an eviction of what has aged, a summary in place of a file. **All of them trim.** So the
constraint is worth writing down before the feature exists:

1. 🚨 **Never leave a `tool` result without its `assistant(tool_calls)` turn.** 0 of 2 answered.
2. **A call without its result is safe** — 2 of 2 — so a pair may be dropped whole, and if only one
   half can go, it is the *call* that must keep its result rather than the other way round.
3. ▶ **Trimming in pairs is strictly better than any byte budget**, because the failure it avoids is
   not gradual: the model does not answer worse, it stops answering.
4. ⚠ **And abcc itself has never built one.** `tool_round` appends the assistant turn *before* its
   results, unconditionally, so the orphan is made downstream — by the server, inside the window it
   never told us about.

---

## 12. What is owed next

1. 🚨 **F744's repair is still the operator's trade, and it is now a better-informed one.** Raising
   `-c` costs VRAM (the model's `max_context_length` is 262,144 against 40,960 loaded); capping the
   body costs evidence; and a third option has appeared — **`stopAtLimit` in the GUI**, which makes
   every overflow loud and, since `79d7b20`, correctly classified and handed to the operator.
2. ⏸ **Row 8's `--offline`** — unchanged and still owed; F740 narrows it to *name it, bind it,
   record it*.
3. ▶ **K-series arms B and C** — `n ≥ 3` repeats and NO seed (F728), hours of GPU, **ask first**.
4. ⏸ **The 96 voice lines**, still unblocked and untouched.
5. 🚨 **`review_recorded` is still 0**, and there are now **nine** unreviewed merges. The packet from
   last session is at `scratch/review-packet-session9.md`; the operator types `abcc review`.
6. ⏸ **Four decisions parked**: F721, F723, F727, F733.
