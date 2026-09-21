# PILOT P13 — the lead that was not there, and the control that fired on the first run

**Status: the inherited lead is FALSIFIED, and the control run falsified it twice over — once by
being absent from 100 calls, and once by firing on call 101 through a completely different
mechanism.**

Session 17 opened with a note saying every claudette attempt *"died against the 24-round budget
while spending 74-90% of output on reasoning trace, and claudette's own PR #225 already root-caused
exactly that."* Three separate claims, and the log disagrees with all three.

🚨🚨 **PR #225's mechanism is not abcc's.** PR #225 fixed a claudette bug where the chain-of-thought
spends the `num_predict` budget and the turn ends with `finish_reason: length` and no content. abcc
is not blind to that — it parses `reasoning_content` and `finish_reason`, counts the trace, and its
budget is already **16384**, the value claudette's own mitigation pins. Over the four pre-existing
attempts, **93 model calls, zero `length`**.

🚨🚨 **Then the control run hit the cap on its third Change turn — with 184 reasoning tokens and the
trace CLOSED.** What consumed 16,200 of 16,384 tokens was **one `apply_patch` argument**, and it
arrived with **`argument_chars: 0`**. That is F511 and F515, exactly, on a second repository: the
overrun is not the trace, it is one tool call's arguments, and a call cut mid-argument never becomes
a call. The attempt changed **no file** and was scored `Uncertain`. Finding **F798**.

🚨 **What eats the rounds is re-reading.** **89.4%** of claudette's `read_file` calls return bytes the
model was already shown in the same attempt, and every attempt read exactly **one** distinct path.
Finding **F800**, which extends F774 to a second repository.

Findings **F798-F802**; next free is **F803**.

---

## 1. Five attempts, and what actually ended each one

`qwen3.6-35b-a3b-mtp@iq3_s`, `-c 40960`, `max_tokens: 16384`, default `--rounds 24`. Every figure is
read from `C:/Users/david/AppData/Local/abcc/claudette-92490a1b1de94eca/log.sqlite`, not from a doc.

| attempt | task | how it ended | calls | finish reasons | max completion |
|---|---|---|---|---|---|
| `a10`  | `t2`   | Uncertain / **BudgetExhausted** | 36 | 33 tool_calls, 3 stop | 7,615 |
| `a209` | `t201` | Uncertain / **BudgetExhausted** | 27 | 23 tool_calls, 4 stop | 8,559 |
| `a364` | `t201` | **Refused by acceptance** | 13 | 9 tool_calls, 4 stop | 8,941 |
| `a478` | `t201` | killed by the operator | 17 | 15 tool_calls, 2 stop | 3,188 |
| `a577` | `t201` | Uncertain / **TruncatedAtCap** | 8 | 6 tool_calls, 1 stop, **1 length** | **16,384** |

⚠ **"All 3 attempts died on the 24-round budget" is wrong three ways**: there are five attempts, only
**two** died on the round budget, and the newest died on the token cap instead.

Over all **101** calls the finish reasons are **84 `tool_calls`, 16 `stop`, 1 `length`**.

## 2. 🚨🚨 F798 — the one call that hit the cap, and why it is not PR #225

`a577` seq 640, the Change phase's third turn, read straight off the log:

| field | value |
|---|---|
| `prompt_tokens` | 6,806 |
| `completion_tokens` | **16,384** — exactly the cap |
| `reasoning_tokens` | **184** |
| answer tokens | 16,200 |
| `finish` | **`length`** |
| composition | `text 293 chars, trace 731 chars, calls [(apply_patch, 0)]` |
| the rung | `structural exit 1 — the attempt changed no file the repository tracks` |

**The trace was `Closed` and 731 characters long.** PR #225's mechanism requires the reasoning to be
what exhausts the budget; here the reasoning is 1.1% of it. The budget went into a single
`apply_patch` diff, and `argument_chars` came back **0** — the server buffers a tool call's arguments
whole and emits nothing when the cut lands mid-argument, so there is no partial diff to recover and
nothing to retry from. The whole attempt produced no file change.

▶ **This matters for what to fix.** PR #225's repair is *escalate the output ceiling and retry on an
empty turn*. Applied here it would double 16,384 to 32,768 and buy one more oversized diff — against
a 40,960-token window, where the prompt then has 8,192 tokens to live in. The lever that fits this
failure is not a bigger ceiling; it is **not asking for a 16,000-token diff in the first place**,
which is F511/F515's standing conclusion and is now confirmed off abcc's own tree.

⚠ **The honest caveat on the cap's rate.** One `length` in 101 calls is an exact count, not a rate
worth quoting — it fired on the first control run after 93 calls without it, which is precisely how
much the count can move. What is established is the **mechanism**, not its frequency.

## 3. F799 — the rounds are spent on work, not on waste

The "74-90% reasoning" figure is real as an aggregate and is not a cause. Counting every call that
produced **no tool call and under 40 answer tokens** — the turns a nudge has to pay for:

    9 of 101 calls, 20,600 completion tokens = 16% of all completion in the log

and they sit mostly in **Recon**, not in the phase that ran out of rounds. Both round-exhausted
attempts look like this:

| attempt | Change-phase calls | tool calls emitted | Change completion |
|---|---|---|---|
| `a10`  | **24 of 24** | 23 | 6,443 |
| `a209` | **24 of 24** | 22 | 6,023 |

A Change turn averages **~250 completion tokens** against a 16,384 cap. The model is not thinking
itself to death in the phase that dies — it makes one small tool call per round and runs out of
rounds. **The 24-round ceiling binds on work.** Finding **F799**, refines F774.

## 4. 🚨 F800 — what the rounds actually buy: bytes the model has already seen

`read_file` reports `<path> lines A-B of N`, so every read's path and range is recoverable. Each read
classified against the reads before it **in the same attempt**:

| | claudette | abcc's own log |
|---|---|---|
| reads with a recoverable path+range | 47 | 337 |
| first read of a path | 5 (**10.6%**) | 103 (30.6%) |
| same path, new range | 30 (63.8%) | 159 (47.2%) |
| ...of those, **overlapping** a range already read | **30 of 30** | **156 of 159** |
| **byte-identical repeat** | 12 (**25.5%**) | 75 (22.3%) |

**89.4% of claudette's reads, and 69.4% of abcc's, return bytes already shown in that attempt.** A
quarter are byte-for-byte repeats of a call already made.

Every claudette attempt read **exactly one distinct path**. `a10` read
`crates/claudette/src/run/research.rs` **22 times**; `a209` read `json.rs` 7 times in 24 rounds.

▶ This is F774's 65.1% measured again on a second repository, higher, and with the overlap
decomposed: the "new range" reads are not exploration, they are 30-of-30 re-cuts of covered ground.
F774 and F775 already proposed the repair — **carry Recon's reads into the Change phase under a
cap** — and this is evidence it is the right one and that it generalises off abcc's own tree.
Finding **F800**, refines F774.

## 5. What happens when `apply_patch` is refused

`apply_patch` in the claudette log: **1 applied of 7** — 3 hunk-context mismatches, 2 diffs carrying
the model's own `<tool_call>` markup, 1 malformed (`---` with no `+++`).

🚨 **Do NOT quote that as a claudette-vs-abcc contrast.** abcc's own log over its *measurable* window
is 20 of 61 = 32.8%, and Fisher against 1-of-7 gives **p = 0.423**. At n = 7 the rates are
indistinguishable. The measurable window matters: **233 of abcc's 294 `apply_patch` calls have
`output IS NULL`**, from before the success path logged anything. Counting those as successes
inflates the rate to 86%, and that is the first thing I got wrong this session.

What *is* visible in both logs is the shape of the recovery. After a refusal the model often abandons
the structured editor and splices files through `bash`:

    a209: refused once, then 15 bash calls and no further patch attempt --
          sed -i, cat -n | grep, sed -n, then head -172 json.rs > /tmp/part1.txt
    a10:  after its second refusal -- head -n 2869 research.rs > /tmp/x && cat >> /tmp/x << TEST_EOF
    abcc's own log does it too: a13308, a15057, a12423 and a12691 all end in bash runs of 4-6 calls

Each such edit costs 3-5 rounds and often leaves the file wrong. Both round-exhausted attempts died
inside this fallback.

⚠ **A tempting contrast that does NOT survive.** Pooled, claudette retries `apply_patch` after a
refusal in 1 of 4 full six-call windows against abcc's 27 of 32 — Fisher **p = 0.0278**, which looks
like a result. Decomposed by refusal type it evaporates: claudette's four windows are 2 hunk
mismatches, 1 malformed, 1 markup, **no cell above n = 2**. And the obvious explanation — that the
markup refusal says *"stop patching and use `write_file`"* — is falsified by abcc, where that same
message is followed by a retry **6 times in 8**. Recorded so the next session does not re-derive it:
**the retry-rate contrast is not established.**

## 6. 🚨 F801 — the exec class is indivisible, so `diagnostics` costs you `bash`

`bash` is where the file-splicing spiral in section 5 happens. It cannot be taken away on its own.

`crates/abcc-engine/src/tools.rs` gives `bash`, `run_tests` and `diagnostics` all the same
`Reach::SpawnsChild`, which maps to `Tier::Exec`, and `tests/policy.rs` fails the moment any
`SpawnsChild` entry is admitted below `Tier::Exec`. `Posting::ALL` therefore offers Builders exactly
four ceilings, and the choice is binary:

| Builders ceiling | read_file | apply_patch / write_file | diagnostics | run_tests | **bash** |
|---|---|---|---|---|---|
| `write` | yes | yes | **no** | **no** | no |
| `exec`  | yes | yes | yes | yes | **yes** |

▶ **So `--ceiling write` is not an available intervention.** F792 names calling `diagnostics` as the
single strongest lever on whether a task lands (told: 5 of 6; untold: 0 of 44). Granting it
necessarily grants `bash`, and `bash` is a de facto unrestricted editor — `sed -i`, `cat > file` —
sitting *above* the write tier that is supposed to bound editing.

⚠ **This is not a bug in the tier ladder.** The ladder is a security control and "starts a child
process" is the right class for it. What is missing is an **orthogonal** control: the model has no
ceiling that says *you may measure but you may only edit through the structured editors.* Whether
that should exist is a decision, not a cleanup. Finding **F801**, refines F792.

## 7. F802 — an orphaned attempt cannot be recovered the way the notes say

The session-16 notes prescribed `abcc take t201 --repo D:/dev/claudette` then `abcc release t201`.
**`take` is refused on an `Engaged` task:**

    abcc: t201 is Engaged and the fleet is holding its workspace. Stop the attempt first --
    `halt t201` at the run or fleet desk -- and take it over once it has landed.

and `halt` exists only as a desk verb inside a live `run`/`fleet` process, which for an orphan is
exactly the process that no longer exists. The real path is `Store::boot`'s orphan sweep, which
tombstones the dead attempt and requeues the task — but **only `run` and `fleet` call `boot`**;
`board`, `replay`, `fun` and `paint` all deliberately open the log without booting it.

✅ **What worked**, and it is clean because `boot()` runs before `choose()`:

    abcc run --task t999999 --repo D:/dev/claudette
    -> boot  569 events replayed, 2 task(s)
             requeued t201 -- a slot-holding state with no worker behind it
    -> abcc: there is no t999999 on this board

The sweep is durable; the command then fails harmlessly on the bogus task id. `t201` went
`ENGAGING TARGET` -> `STANDING BY`. ⚠ Asking for a task that does not exist is a workaround, not an
interface — an operator who has lost a run has no command that says *sweep this log*. Finding
**F802**.

## 8. Where this leaves the pilot

* The instrument is **not** the thing to fix next. The gate bugs are fixed (`d26a3cf`, `605fd7d`),
  and the two mechanisms that actually ended attempts here — the argument overrun and the re-read
  spiral — are both already-named findings (F511/F515, F774/F775) that now have evidence off abcc's
  own tree.
* **The 4% must still not be quoted.** Nothing here measures a landing rate. Five attempts, four
  distinct endings, one of them the operator's own kill.
* The cheapest next control, unchanged from F774/F775: **carry Recon's reads into Change under a
  cap**, and see whether the Change phase stops spending its rounds re-reading one file.

---

# Part 2 — the same session, two more attempts, and the mechanism reproduced

## 9. 🚨🚨 F798 reproduced 2 of 2: every `length` in this log is an `apply_patch` runaway

After Part 1 was written I queued a task chosen to be as easy as this corpus gets, and **verified it
solvable before queueing it**: roast card `RUNTIME-11`, one file
(`crates/claudette/src/runtime/usage.rs`, **112 lines**), two tiny functions, an existing
`#[cfg(test)] mod tests` to put the test in. Reference solution: all three gate commands exit 0,
**1162 passed / 0 failed**, and the new test panics `attempt to add with overflow` on the unfixed
source. ✅ That 1162/0 is also independent confirmation that **the gate fix holds and the tree is
genuinely green** — the 58 failures charged to `a209` really were manufactured.

`t649` ran on that task and died exactly as `a577` had:

| | `a577` (`t201`, json.rs, 358 lines) | `a657` (`t649`, usage.rs, **112 lines**) |
|---|---|---|
| `completion_tokens` | **16,384** | **16,384** |
| `reasoning_tokens` | 184 | **99** |
| trace chars | 731 | 342 |
| trace state | `Closed` | `Closed` |
| composition `calls` | `[(apply_patch, 0)]` | `[(apply_patch, 0)]` |
| tool_call events for it | **none** | **none** |
| rung | `structural exit 1 — changed no file` | `structural exit 1 — changed no file` |

🚨 **Those are the only two `length` finishes in the entire log, and they are the same event twice.**
Exactly the cap; reasoning under 200 tokens; the trace closed; one `apply_patch` whose arguments
arrive with **zero characters**; no `tool_call_started` at all, because a call cut mid-argument never
becomes a call (F515); and the attempt scored `Uncertain` having changed nothing.

▶ **The 112-line file is what makes this sharp.** A correct patch to `usage.rs` is about 40 lines and
~1,500 characters. The model spent **16,285 answer tokens** on it — an order of magnitude more than
the whole file. This is not a large patch hitting a small ceiling; it is the model **failing to
terminate inside the argument**, and the ceiling is merely where it stops.

⚠ **And the argument is unrecoverable by design.** F622: the server buffers a tool call's arguments
whole, so nothing partial reaches abcc and there is nothing to log, diff or retry from. Seeing what
the model actually emitted needs a raw SSE probe (`research/tools/ssecapture.py`), not the log.

## 10. Three levers, none of them a bigger ceiling — ▶ DAVID'S CALL

Stated as proposals, not changes. Nothing in abcc was edited this session.

**(a) Say which editor to use, in the tool summary.** `apply_patch`'s summary is
*"Apply a unified diff to the workspace."* and `write_file`'s is *"Write a file in the workspace,
creating it if it does not exist."* — neither says **when** to prefer which, so the model picks the
diff and, twice, failed to terminate inside it. ▶ There is precedent in this repository and it is
F673's: the `diagnostics` summary was rewritten because *"this sentence is the fix as much as the
code is"*. The same move is available here, and it costs one const.

**(b) On `TruncatedAtCap` with a cut `apply_patch`, retry the phase with a different TOOL, not a
bigger budget.** This is where PR #225's instinct is right and its remedy is wrong. Doubling 16,384
to 32,768 against a 40,960 window leaves the prompt 8,192 tokens and buys one more oversized diff.
Re-asking the same turn with *"send `write_file` with the whole file"* addresses what actually
happened. ⚠ abcc already knows enough to do this: it has the `Finish::Length`, the composition
showing `apply_patch` with `argument_chars: 0`, and `Why::TruncatedAtCap`.

**(c) Carry Recon's reads into Change under a cap** — F774 + F775, unchanged, now with the evidence
of §4 behind it and a second repository's worth of it.

⚠ **What NOT to do:** raise `max_tokens`. The overrun is not a patch that is slightly too big; on a
112-line file the model produced ten times the file in answer tokens. A bigger ceiling moves where it
stops, not whether it terminates.

## 11. Housekeeping done this session

* ✅ **`t201`'s orphan cleared** — and the prescribed `take` → `release` recipe does not work; see §7.
* ✅ **`MEMORY.md` was 26,811 bytes against a 24,985 limit, and 3 index rows were being silently
  truncated — so 3 memories were not loading at all.** Four index lines were carrying 4,089 / 2,746 /
  2,599 / 1,821 bytes against a ~200-character guideline. Compressed to **17,730 bytes**, all 43 rows
  and all 42 files still indexed, every link resolving.
* 🚨 **While doing it, the rule-5 heredoc hazard bit again and wrote a BEL into `MEMORY.md`.** A
  *quoted* heredoc still ate one of a doubled backslash, so Python saw an escape and produced 0x07.
  🎉 **The tell was free:** Python printed `SyntaxWarning: "\L" is an invalid escape sequence` on the
  same run — proof the source had been mangled, since a doubled backslash should never reach Python
  as a lone one. Caught by the post-write scan, at offset 7199. Written up as rules 7 and 8 in
  `back-up-memory-every-session.md`, with the second being: **never split frontmatter on `---`,
  because a description can contain one** — that mis-parse makes a healthy file look corrupt.
