# PILOT P16 — the window abcc already has and throws away, and the read it never charges for

**Status: `SHELL-06` was driven as a real card, twice, under David's instruction that the next card
be ONE change instead of `SHELL-04`'s three. It did not land — but for the first time neither
attempt died the way the last two did, and the two deaths were different from each other. The
first filled the server's context window with tool output; the second, after a one-line control
removed that, reasoned itself to the output cap. Diagnosing them found that abcc receives the
context window on every single run and discards it, that 41.7% of every `read_file` byte it has
ever served was a byte-identical repeat, and that the barren-turn rule P15 proposed is now 4 for 4.
▶ **Then `SHELL-10` — one line, in the same 180-line file `SHELL-04` died in twice — landed
on the first attempt, 4 of 4 rungs green, as `a450e00`.** Every landing this pilot has had is a
one-change card; no multi-part card has landed in four attempts (Fisher p = 0.0476, n = 10).**

Every number below is read from `claudette-92490a1b1de94eca/log.sqlite` and
`abcc-1ae35b6091a63e2c/log.sqlite`, from the source at `b09bcdf`, or from a live probe of the
serving stack recorded inline.

---

## 0. The card, and the reference solution that proved it solvable

`SHELL-06` [V] HIGH — *`semantic_grep` follows symlinks with unbounded recursion*.
`crates/claudette/src/tools/semantic.rs`, 427 lines. `fn walk` at lines 172–194 is a hand-rolled
recursion over `std::fs::read_dir` that tests `path.is_dir()` — which follows symlinks — with no
depth limit and no visited set. claudette is built with `panic = "abort"`
(`D:/dev/claudette/Cargo.toml:23`), so one self-referential directory link is the process.

The same 23 lines carry a second defect: `collect_chunks` returns `false` at `semantic.rs:151`
once `files_scanned` reaches `MAX_FILES` (1500), and `walk` returns from the **current directory
frame only**, so every parent frame keeps iterating and the cap never ends the walk.

✅ **Verified open by grep before any GPU was spent** — no `WalkBuilder` and no `follow_links` in
the file; `read_dir` at `:173`, `is_dir()` at `:185`.

✅ **Reference solution written by hand and verified, the way the standing discipline requires.**
The whole fix is *rewrite `walk`'s body on `ignore::WalkBuilder`* — `ignore = "0.4"` is already a
dependency (`crates/claudette/Cargo.toml`), and three siblings already do exactly it
(`repomap.rs:151`, `repomap.rs:314`, `search.rs:328`; the card says two — grep, never quote the
card). One function, one file. All three rungs green: `cargo test` **1164 + 32 + 4 + 2 + 3 pass,
0 fail**, `cargo fmt --check -- --color=never` exit 0, `cargo clippy --all-targets -- -D warnings`
exit 0. Saved at `research/patches/SHELL-06-reference-solution.patch`.

✅ **Both new tests proved red against the unfixed source**, with the predicted failure text:
`walk_stops_the_whole_walk_when_the_callback_returns_false` reports **`got 3 callbacks`** — exactly
one per sibling directory, which is the `MAX_FILES` bug stated as an assertion — and
`walk_respects_gitignore` reports that a git-ignored file was scanned.

🚨 **The portability trap, settled before queueing and worth keeping.** The headline defect is a
symlink loop, but a test that builds one is **not portable**: a Windows symlink needs
`SeCreateSymbolicLinkPrivilege`, so such a test fails on this box and on `windows-latest`
regardless of the fix. Both tests above assert properties the same rewrite delivers that need no
privilege. ⚠ Settled by probe, not assumption: `ignore`'s `require_git` defaults to true, so the
gitignore test creates an empty `.git` directory in its temp tree — which works.

---

## 1. Attempt one: the conversation filled the window

`t1494` / `a1502`, prompt 5,350 chars, pure ASCII (F817's trap avoided deliberately).

    ended     Uncertain { ContextOverflow { window: 40959, prompt_tokens: 40281 } }
    localize  3 turn(s), 4 tool call(s), 49931 in / 1126 out (683 reasoning), 74142 ms
    rung      REFUSED structural — the attempt changed no file the repository tracks

🚨 **This is not `SHELL-04`'s death and it is important that it is not.** `SHELL-04` spent 99.4% of
its completion tokens on reasoning across nine turns and emitted `text_chars` 0 on every one.
`a1502` spent **683 reasoning tokens in total**. The model was not wandering. It was working, and
the room ran out under it.

The four tool calls, with the bytes each returned:

| seq | tool | result | bytes |
|---|---|---|---|
| 1509 | `read_file` | `tools/semantic.rs` lines 1–427 of 427 | 14,017 |
| 1511 | `list_files` | 28 entries under `tools` to depth 1 | 1,121 |
| 1515 | `read_file` | **`tools/repomap.rs` lines 1–1517 of 1517** | **61,843** |
| 1517 | `read_file` | **`tools/search.rs` lines 1–1513 of 1513** | **62,313** |
|  |  | **total** | **139,294** |

**The prompt named `repomap.rs:151` and `search.rs:328` — with line numbers — and pasted the
sibling block verbatim. The model read all 1,517 and all 1,513 lines anyway.** `read_file`'s schema
offers `from_line` and `to_line` (`tools.rs:204`); nothing asked for them and nothing required them.

**The measured density for this attempt.** The conversation held 5,729 chars of brief
(`brief_recorded`, seq 1505), 139,294 chars of tool output and 3,796 chars of assistant output —
about 148,800 chars before the system prompt — against `prompt_tokens: 40281`. That is
**~3.75 chars per token**, consistent with F809's finding that the largest arguments ever delivered
run 2.77–3.82 and that the 2.55 median is the wrong statistic for large payloads.

---

## 2. F818 — abcc receives the context window on every run and throws it away

**`MAX_READ_BYTES` is `64 * 1024` (`crates/abcc-engine/src/workspace.rs:74`)** — a compile-time
constant, consulted by `read_file` at `workspace.rs:423` through `clamp`, with **no reference to
the context window anywhere.** At the 3.75 chars/token measured above, one call at that cap is
**~17,500 tokens, 42.7% of the 40,960-token window this run was served.** Two calls at the cap are
85% of it. That is not a hypothetical: `a1502`'s two large reads came back at 61,843 and 62,313
bytes, both within 6% of the cap.

🚨 **The window is available, from an endpoint abcc already calls, before the first model call.**
`confirm.rs` hits `/api/v0/models` on every run (`confirm.rs:389`, and it is first in the
fallback list at `:397`) — that is what prints *model confirmed: asked X, the server reports it has
loaded X*. A live probe of that endpoint with the champion loaded, run this session:

    "id": "qwen3.6-35b-a3b-mtp@iq3_s",
    "state": "loaded",
    "max_context_length": 262144,
    "loaded_context_length": 40960,

**And abcc parses exactly two fields out of it** (`confirm.rs:340`):

    #[derive(Deserialize)]
    struct Entry {
        id: String,
        state: Option<String>,
    }

serde drops the rest. So the only place abcc ever learns the window is `overflow_in`
(`openai.rs:549`), which scans the server's **error body** for `exceed_context_size_error` and
pulls `n_ctx` out of it — **after the request has already been refused.**

🚨 **This is structurally the same defect as F812.** F812 found ADR-0010 §7's one in-flight signal
is computed after the drain loop ends, so it could never be a stop. Here the one number that could
bound a conversation is learned only from the failure it could have prevented. A quantity that
arrives after the event cannot govern it.

⚠ **The trap for whoever fixes this, and it is one field away.** `max_context_length` is
**262,144** — the model's ceiling, **6.4× the real window**. Reading it instead of
`loaded_context_length` would budget against a number that is wrong in the dangerous direction and
would look correct in every test where the operator happened to load a large context. This is the
same join hazard Sweep B recorded: *join on `server.loaded_context_length`, never `held.num_ctx`*.

⚠ **What this finding does NOT say.** `context_overflow` is **3 of 159 attempts (1.9%)** across all
four logs — it is real but it is not the dominant death. Full outcome census, every attempt abcc
has ever recorded:

| outcome | why | n | share |
|---|---|---|---|
| uncertain | `budget_exhausted` | 49 | 30.8% |
| uncertain | `truncated_at_cap` | 32 | 20.1% |
| refused | — | 26 | 16.4% |
| uncertain | `said_nothing` | 21 | 13.2% |
| **success** | — | **18** | **11.3%** |
| hard_failure | `engine_error` | 4 | 2.5% |
| uncertain | `no_checker_for_artifact` | 4 | 2.5% |
| **uncertain** | **`context_overflow`** | **3** | **1.9%** |
| soft_failure | `timeout` | 2 | 1.3% |
| | **total** | **159** | |

---

## 3. F819 — 41.7% of every `read_file` byte abcc has ever served was a byte-identical repeat

Over all four logs there are **422** `read_file` results carrying a parseable
`<path> lines <a>-<b> of <n>` header. **224 of them (53.1%) are whole-file reads.** The
distribution is not alarming on its own — median **2,565** bytes, p90 **28,709** — but the tail
reaches the cap: **max 65,231 bytes**, 78 calls over 16 KiB, 9 over 32 KiB.

The tail is not the real cost. **Counting byte-identical repeats within a single attempt**, across
the 46 attempts that read anything:

    3,363,276 bytes of read_file output served
    1,401,291 of them byte-identical repeats within the same attempt   =  41.7%

Worst offenders, and they are not marginal:

| log | attempt | reads | bytes | duplicate | dup % |
|---|---|---|---|---|---|
| abcc | 11598 | 18 | 367,847 | 173,549 | 47.2% |
| abcc | 14162 | 24 | 231,134 | 145,722 | **63.0%** |
| abcc | 13308 | 14 | 135,937 | 94,505 | **69.5%** |
| abcc | 12423 | 11 | 129,578 | 87,450 | **67.5%** |
| claudette | 10 | 22 | 176,669 | 66,323 | 37.5% |

🚨 **Attempt 13308 is the second measurable `context_overflow`, and it died purely of re-reads.**
`crates/abcc/src/cli.rs` lines 1–663 came back at **28,709 bytes four separate times** (seq 13315,
13331, 13348, 13387); `lib.rs` twice; `main.rs` twice. 114,836 bytes of that attempt's 135,937 were
one file. It ended at `prompt_tokens: 40828` of a `40960` window.

**So the two measurable overflows are two different routes to the same wall.** `a1502` read three
*distinct* files and had **0%** duplication; `13308` read the same file four times and had 69.5%.
Nothing in abcc stops either: there is no cumulative accounting of tool output anywhere, and
`dedup` appears in the tree only in `outcome.rs`'s error-line folding and two test helpers.

⚠ **The third overflow is unmeasurable, not absent.** Attempt 1968 (`seq 2077`, window 32768) has
22 tool calls that all logged **0 bytes** of output — it predates `1cfe1ac`, when the success path
logged nothing (the same window F771 warns about). It cannot be attributed either way.

---

## 4. F820 — the control fired: one line removed the overflow, and moved the death

Per the standing rule that the control runs **before** the cause is published, `SHELL-06` was
re-queued as `t1533` with **exactly one change** to the prompt — a paragraph saying the sibling
block above is complete, not to open `repomap.rs` or `search.rs`, and that `read_file` takes
`from_line`/`to_line`. Everything else byte-identical.

| | `t1494` (v1) | `t1533` (v2, control) |
|---|---|---|
| tool calls | 4 | 3 |
| `read_file` bytes | **138,173** | **34,199** |
| large sibling reads | 2 (61,843 + 62,313) | **0** |
| prompt tokens at death | **40,281** of 40,959 | 33,718 |
| reasoning tokens | 683 | **21,861** |
| elapsed | 74.1 s | **389.8 s** |
| died of | `ContextOverflow` | `TruncatedAtCap { budget: 16384 }` |

✅ **The mechanism is confirmed and it is prompt-reachable.** One sentence cut `read_file` output
by **75%** and removed the overflow entirely. ⚠ **And it is honest to say the prompt invited the
overflow in the first place** — v1 named two large files by line number. `a1502` is therefore not
evidence that abcc overflows on ordinary work; it is evidence that **nothing in abcc bounds what a
prompt can invite**, which is the same finding stated without blaming the operator.

🚨 **The card still did not land, and the second wall is `SHELL-04`'s wall.** v2 reasoned 21,861
tokens across 4 turns and died at the output cap with nothing written.

---

## 5. F821 — the barren-turn rule is now 4 for 4, and the margin is unchanged

P15 proposed stopping a turn at **12,288 reasoning tokens with no text delta and no tool-call
delta yet seen**, measured 3 for 3 with zero false positives over 2,536 turns. `a1541`'s four turns
are a clean fourth trial, and all four turns are informative:

| turn | prompt | completion | reasoning | `text_chars` | calls | finish | elapsed |
|---|---|---|---|---|---|---|---|
| 1 | 2,707 | 178 | 142 | 0 | 1 | `tool_calls` | 6.1 s |
| 2 | 6,785 | 5,472 | 5,088 | 1,258 | 1 | `tool_calls` | 102.5 s |
| 3 | 11,204 | 288 | 251 | 0 | 1 | `tool_calls` | 11.4 s |
| **4** | 13,022 | **16,384** | **16,380** | **0** | **0** | **`length`, `content_empty`** | **269.8 s** |

✅ **Turn 4 is exactly the shape the rule describes** — 16,380 reasoning tokens, zero text, zero
tool calls, 269.8 seconds spent to emit nothing, at `prompt_tokens` of only 13,022 with a third of
the window still free. **The rule is now 4 for 4.**

✅ **And the three productive turns are the false-positive test: the highest reaches 5,088
reasoning tokens**, less than half the 12,288 threshold. P15 recorded the nearest productive turn
ever seen at 10,486, giving a margin of 1,802 tokens. **This attempt does not narrow it.** The
honest statement is still *n = 4 on the catch side, margin 1,802 tokens*.

⚠ **`a1541`'s trace is `OpenAt200`** — and per F813 that stays unwired. It inverts over 272 phases
(p = 0.4657) and here it is simply along for the ride; turn 4 is caught by the reasoning-token rule
and not by the trace state.

---

## 6. F822 — the re-read reproduces at n = 3, and the obvious fix is not free

`a1541` made three `read_file` calls and **two of them were the same file**:

    seq 1548  read_file  tools/semantic.rs lines 1-427 of 427    14,017 B
    seq 1562  read_file  tools/semantic.rs lines 1-427 of 427    14,017 B   <- byte-identical
    seq 1567  read_file  claudette/Cargo.toml lines 1-137 of 137  6,165 B

**14,017 of 34,199 bytes = 41.0% duplicate** — within rounding of the 41.7% whole-history figure,
in an attempt that made only three reads. The re-read came immediately after the turn that spent
5,088 reasoning tokens and wrote 1,258 characters of text: **the model reasoned about the file,
then asked for it again.**

🚨 **The obvious fix — answer a re-read with *you already have this* instead of the bytes — is NOT
unconditionally safe, and the hazard is recorded here so nobody wires it blind.** A back-reference
is only sound if the earlier copy is still in the conversation the server sees. The
`lmstudio-truncates-the-middle` mechanism keeps the system prompt and the first user message and
drops the middle, which is precisely where an earlier tool result lives.

⚠ **What is measured about that here, and what is not.** On the path abcc actually uses, all three
overflows came back as a **refusal carrying `exceed_context_size_error`, `n_ctx` and
`n_prompt_tokens`** — abcc could only parse those numbers because the server sent an error rather
than silently truncating. So middle-truncation is **not** observed on this path. That is an
observation about three events, not a guarantee about the policy, and a dedup that assumes it would
be betting the correctness of every re-read on it.

---

## 7. What to change, ranked — and what not to

1. ✅ **Read `loaded_context_length` in `confirm.rs` and carry it.** One field on one struct, from
   a response already in hand. Pure information; no behaviour change on its own. It is the
   prerequisite for everything below, and surfacing it in `abcc check` would have made `a1502`
   diagnosable in one glance. ⚠ **Not `max_context_length`** (F818).
2. ✅ **Wire the barren-turn stop** — 12,288 reasoning tokens, no text delta, no tool-call delta.
   4 for 4, zero false positives over 2,536 turns, and it would have ended `a1541`'s turn 4 about
   67 s early. ⚠ Quote both halves: margin 1,802 tokens, n = 4 on the catch side.
3. ⏸ **Budget `read_file` against the window rather than a 64 KiB constant.** Correct in
   principle, but the cap only bit twice in 422 calls and the honest denominator is 3 overflows in
   159 attempts. Worth doing after (1) makes the window available; not worth doing first.
4. 🚨 **Do NOT wire a re-read back-reference yet** (F822). The saving is the largest on offer —
   41.7% of all read bytes — and the failure mode is a pointer into bytes the server may have
   dropped. It needs the truncation policy settled first.
5. 🚨 **Do NOT wire `OpenAt200`** — F811–F814 stand, and `a1541` adds nothing that changes them.

---

## 8. F823 — PowerShell 5.1 splits a task prompt on its own double quotes, and abcc caught it

F817 recorded that `Get-Content -Raw` reads a BOM-less UTF-8 file as the ANSI codepage and
mangled nine em dashes with **nothing in abcc noticing**. This is its sibling one step later in the
same pipeline, and it has the opposite ending.

`SHELL-10`'s prompt is the first in this series to carry embedded double quotes — a Rust string
literal and a `starts_with("failed to spawn")` guard. Handing it to `abcc task` from PowerShell 5.1
produced:

    abcc: task takes a prompt and nothing else — quote it if it has spaces in it

Probed directly, the same 4,037-byte file against a program that prints its own `argv`:

    source chars: 4037
    argc = 5
    arg0 len = 1772
     extra arg: 'sys;'
     extra arg: 'sys.stdout.write(str(len(sys.stdin.read())));...'
     extra arg: 'to'
     extra arg: 'spawn)` and returns early...'

**The split points are exactly the embedded quoted segments.** PowerShell 5.1 passes an embedded
`"` to a native command's raw command line **without escaping it**, so it re-opens quoting and the
argument breaks at whitespace inside the quoted run. `arg0` stops at 1,772 characters — precisely
where `let body = "import sys; ...` begins.

⚠ **A small control does NOT reproduce it, and that is the trap inside the trap.** One balanced
pair with nothing structural after it is silently **stripped** instead of splitting: `"alpha
\"beta\" gamma"` arrives as a single argument reading `alpha beta gamma`. **Quote loss and
argument splitting are the same defect at two doses**, and testing the small one concludes it is
safe.

✅ **abcc caught this, and that is the half worth keeping.** `task`'s arity check refused rather
than filing a truncated prompt, and the message named the cause. F817's mojibake reached the model
because nothing checked it; this reached nothing because something did. That is the same shape as
the `apply_patch` guard in P14 §2 — a check that found a real defect and said how to recover.

▶ **The working recipe is Git Bash**, and it was verified rather than assumed:

    cd /d/dev/abcc && abcc task "$(cat prompt.txt)" --title "..." --repo D:/dev/claudette

The stored prompt was then read back out of `task_created` and compared to the source:
**4,036 chars stored against the 4,037-byte file whose trailing newline `$(cat)` drops, identical
otherwise.** ⚠ Check the stored prompt, not the command's exit code — F817's whole lesson is that
the corrupted version filed successfully.

---

## 9. F824 — a one-line card landed first try, and the ladder now has a control

`SHELL-06` was abandoned after two attempts rather than a third, per the standing rule that the n
which matters is **different cards**, not more attempts on one. The fallback named in the brief was
`UX-04`, and it was **rejected on reading the code rather than the card**: its headline is Ctrl+C
leaving the cursor hidden, which needs a **signal handler** — `ctrlc` and `signal-hook` are not
dependencies of this crate and *no new dependencies* is a hard gate constraint. A panic hook, the
`tui.rs:699` pattern the card points at, does not catch `SIGINT`. The card's own fix says *install
it once in `main`*, and `main.rs` is 1,486 lines. It fails the rig twice over.

▶ **`SHELL-10` was driven instead, and it landed on the first attempt** — `a1612`, **4 of 4 rungs
green**, landed as **`a450e00`** on `claudette`.

    localize  10 turn(s), 8 tool call(s), 81379 in / 10014 out (8262 reasoning), 138459 ms
    change     5 turn(s), 4 tool call(s), 43302 in /  2829 out (591 reasoning), 133341 ms
    gate      structural ok · acceptance ok · veto ok · standard ok

**What it wrote is the reference solution, independently derived** — `.stdin(Stdio::null())` on the
builder chain and a `stdin_is_null` test in the `mod tests` that was already there, reusing the
existing skip-if-absent guard verbatim. It asserted `stdout.trim() == "0"` where the reference
asserted `"0"`, which is marginally more robust. ✅ Re-verified by hand off the checkpoint: the
patch applies clean, passes the probe that caught the defect (**24 bytes → 0**), and the whole tree
is `fmt` 0, `clippy` 0, **1204 tests, 0 failures**.

🚨 **The comparison that carries the most weight is the same-file one.** `SHELL-04` and `SHELL-10`
are both `crates/claudette/src/test_runner.rs`, both 180 lines, both reached through the same
module and the same `python` test idiom. They differ in one thing — **how many parts the card
asks for**:

| card | file | parts asked | attempts | landed |
|---|---|---|---|---|
| `SHELL-04` | `test_runner.rs`, 180 | 3 (tree-kill, reader deadline, test) | 2 | **0** |
| `SHELL-10` | `test_runner.rs`, 180 | **1** (one line, one test) | 1 | **1** |

Across every card this pilot has driven, sorted the same way:

| shape | cards | attempts | landed |
|---|---|---|---|
| one change | `RUNTIME-11` (P14), `SHELL-10` | 6 | **5** |
| multi-part | `SHELL-04`, `SHELL-06` | 4 | **0** |

**Fisher exact, two-tailed: p = 0.0476** (one-tailed 0.0238).

⚠ **And here is what that number is NOT.** These cards were **chosen, not randomised**, and they
differ in more than part-count: the files run 112, 180 and 427 lines, and `SHELL-06`'s first death
was a context overflow this operator's own prompt invited (F820). n is **10 attempts across 4
cards**. The honest sentence is *every landing in this pilot has been a one-change card, and no
multi-part card has landed in four attempts* — a real pattern at p = 0.0476, on a sample small
enough that one more multi-part landing would take it past 0.05. ▶ **The cheap way to strengthen
it is another one-change card on a different file**, not another attempt on `SHELL-06`.

⚠ **A caveat the prompt carried on purpose, and it is a limit on the card, not on the model.**
Under `cargo test` the harness's own stdin is already at end-of-file, so the child inherits a
closed handle and reads zero bytes **whether or not the fix is applied**. `stdin_is_null` is a
regression guard, not a red-to-green proof, and the prompt said so explicitly so the model would
not spiral trying to make it fail. The defect was proved the only way it can be — by putting real
input on the parent's stdin, where the unfixed code read all 24 bytes of it. **So the gate's
`acceptance` rung green here means *nothing regressed*, not *the fix is proved*.** The proof is in
this document, not in the suite.

---

Findings **F818–F824**; next free is **F825**.
