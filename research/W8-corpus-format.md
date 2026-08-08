# W8 - The corpus format

Sub-deliverable 1 of W8, and the decision every other part of W8 sits on. This is the schema plus
two worked import examples, for David's approval **before any new task content is written**.

Status: proposal. Nothing below has been committed to as a build decision yet.

---

## Question

What is the on-disk format of an ABCC 2.0 evaluation task, given that:

1. the harness is new and imports ABCC's 100-task suite and Claudette's Q56 battery as corpora
   rather than extending either (decided 2026-08-08, brief §14 item 1);
2. the unit of measurement has to be **a session with interventions in it**, not one invocation
   against a fixture, because operator control is the axis 2.0 differentiates on;
3. Claudette at `fc1ea22` (v0.17.0) is the stand-in subject, producing a **baseline** rather than a
   proxy (brief §11 W8).

The schema must carry, per task: the fixture, the permission configuration, the scripted
interventions, and the verifier.

## Method

Read the two donor corpora at source and drove the stand-in subject for real. Specifically:

- Read ABCC's suite definition and execution engine (`scripts/ultimate-100-task-test.js` at
  `d5528ea`, 3,521 lines) rather than the dossier's description of it.
- Read Claudette's battery manifest, runner, gate and verifiers on the unmerged
  `battery/q50-quality-corpus` branch at `43d6b34`.
- Traced Claudette's permission gate from the prompter to the two entry points that do and do not
  construct it, because the doc comment on that path carries a build decision.
- **Ran a throwaway spike** that drives `claudette` v0.17.0 over pipes against a live local model,
  to settle four mechanical premises by measurement instead of by reading. Driver and transcript in
  `research/spikes/w8-pipe-drive/`.
- **Ran the proposed import gate** against one real ABCC task, including an adversarial case.

Retrieval date for every claim below: **2026-08-08**.

---

## Inherited

### From Claudette's Q56 battery (`43d6b34`, `runs/eval-2026-05-29/battery/`)

Nearly all of the good structure comes from here, and the format below keeps it:

| Inherited | Where | Kept as |
|---|---|---|
| Fresh fixture copied per task | `run_battery.sh` per-task `rm -rf work; cp -r fixtures/$fixture` | `fixture/`, unchanged |
| Verifier contract `RESULT: PASS\|FAIL <msg>` on stdout | `run_battery.sh` status parse; `verify/*.sh` | unchanged, plus `INVALID` |
| Verifier receives **workdir and transcript** | `bash verify/$id.sh "$work" "$log"` | unchanged - transcript-reading verifiers matter |
| Hidden tests injected at grade time | `verify/Q08.sh` writes `tests/hidden_gate.rs` then `cargo test` | unchanged |
| Test-first authoring gate | `gate_q50.sh`: fixture must FAIL, refsol must PASS | kept and **extended to three points** |
| Reference solution outside the fixture | `refsol/<id>/`, gate-only | unchanged |
| Per-task timeout, with a documented retry-once-on-124 rule | `manifest-q50.tsv` col 5; `run_battery.sh` | `timeout_s` |
| Optional per-task setup hook | `setup/<id>.sh` (only J1-J4 use it) | `setup.sh`, optional |
| Recording the config a run was **actually** measured under | `probe_runtime_config.sh` -> `RUNMETA.tsv` | required, not optional |

The battery's own README states the limit this workstream exists to fix: it "cannot measure context
compaction, prefix-cache behaviour, model escalation, or permission handling - `run_battery.sh` sets
`CLAUDETTE_AUTO_APPROVE=1`, so those paths are never exercised."

### From ABCC's 100-task suite (`d5528ea`, `scripts/ultimate-100-task-test.js`)

Less structure, but two things worth carrying:

- **Deterministic per-task verifiers with no LLM judge** (`validation` + `validationLang`, one per
  task). Honest from the start, same principle as Q56.
- **Decomposition as a measured variable** (`CTO_BRIEFS`, `ctoGenerated`, `retriesSaved`) - the only
  place in the family where a plan-then-execute path is scored. Out of scope for v1 of the format,
  but the schema should not make it impossible later.

### Not inherited, deliberately

- ABCC's shared cumulative workspace (below).
- ABCC's tool-name-coupled prompts (below).
- Claudette's TSV manifest as the primary definition. A TSV row cannot express an intervention
  track, and it cannot carry a comment saying why Q12's timeout is 900 rather than 600.

---

## Findings

### F1. One-shot mode has no permission prompter at all. The harness must drive the REPL.

This is the single most consequential finding and it changes how the subject is driven.

`crates/claudette/src/run.rs:186` - the single-shot path constructs
`let mut no_prompter: Option<&mut dyn PermissionPrompter> = None;` and passes it to the turn. The
doc comment at `run.rs:216-221` states the consequence directly: auto-approve is "the only way
one-shot (`claudette "fix the bug"`) can apply an edit, since one-shot has no prompter to answer."
Only the REPL constructs one (`run/repl.rs:56`, passed as `Some` on every turn at `:169-170`).

So `CLAUDETTE_AUTO_APPROVE=1` in the Q56 battery is not a convenience setting that happened to
suppress the gate. **It is forced**: without it, a one-shot run cannot edit a file at all, because
every `DangerFullAccess` tool is denied with nobody to ask. Q56 could not have measured permission
handling regardless of intent.

Consequence for W8: the harness drives `claudette` with **no arguments** (REPL) over pipes, and must
never set `CLAUDETTE_AUTO_APPROVE`.

### F2. The REPL degrades cleanly to piped stdin, so no PTY is needed on the path that has the gate.

The earlier "no PTY needed" conclusion was sourced from the gate's own fall-through
(`run/cli_prompter.rs:89-96`). That citation covers the gate but not the REPL's main input loop,
which is the part that would actually have forced a PTY. Checked separately:

`run/line_editor.rs:337` sets `interactive = io::stdin().is_terminal() && io::stderr().is_terminal()`,
and `read_line` at `:369-376` degrades to a plain `io::stdin().read_line` returning `Eof` on zero
bytes. `run/repl.rs:100-102` documents the intent: "Degrades to a plain `read_line` when
stdin/stderr isn't a terminal, so piped input, CI, and the eval battery behave exactly as before."

**Verified by running it** (see F5). The conclusion stands, now on the right evidence.

### F3. stdout and stderr carry different event classes and must be captured as separate pipes.

- Model text deltas go to **stdout**, flushed per delta: `api.rs:36-52`, `stdout_text_callback`
  does `write_all` then `flush` on every delta.
- The permission gate goes to **stderr**: `run/cli_prompter.rs:52-53` locks `io::stderr()`, and the
  prompt itself is written at `:84`.

Claudette's own `run_battery.sh` merges them (`>> "$log" 2>&1`), which is right for a log and wrong
for an instrument: merged, a harness cannot tell a gate prompt from model output. Capture separately.

Two mechanical details that follow:

- The gate prompt has **no trailing newline** (`write!`, not `writeln!`, at `:84`). A line-buffered
  reader blocks forever waiting for one. The reader must be byte-level, or match on the prompt
  suffix. This cost the spike its first design and is worth stating plainly.
- `theme` honours `NO_COLOR` / `CLICOLOR` (`theme.rs:6`), so setting `NO_COLOR=1` gives plain-text
  matching with no ANSI stripping. Non-ASCII glyphs remain, so the harness must be UTF-8 tolerant.

### F4. The turn-boundary marker exists, is unconditional, and carries real token counts.

`run/repl.rs:205-214` prints, after every REPL turn, to stderr:

```
⚡ turn iter=5 in=21106 out=505 ctx ~485/32k (1%)
```

This gives the harness three things for free and requires **no patch to the stand-in**:

1. **A turn-boundary marker.** Needed, because in piped mode the REPL never echoes its `❯` prompt -
   `line_editor.rs:370-376` ignores the prompt argument entirely on the non-interactive path. Without
   this line there would be no way to know a turn had ended.
2. **`in=` / `out=` token totals** from `summary.usage`, i.e. the API's reported usage rather than an
   estimate. **This makes cost per task reachable on the stand-in.** That metric has never been
   measurable anywhere in this family: ABCC's `execution_logs.input_tokens` is 0/5,977 populated.
   **The accounting is session-cumulative, not per-turn - see F9, which settles it.**
3. **`iter=`**, the iteration depth Q56's README reports as p50=4 / p90=8, now available per task.

The trailing `ctx ~485/32k` is the *estimated* session-token gauge and is a different, weaker number
than `in=`/`out=`; do not confuse them.

### F5. The spike: all four mechanical premises hold, measured end to end.

Driver: `research/spikes/w8-pipe-drive/`. Subject `claudette 0.17.0`, ctx 32768, `NO_COLOR=1`,
**no** `CLAUDETTE_AUTO_APPROVE`. Workspace: one `calc.py` whose `subtract()` adds. Prompt: fix it by
editing the file. Scripted operator track: on the first gate, send a redirect.

> ⚠ **This run used `qwen3.5-4b`, so it is mechanism-only: it proves the plumbing, and its timings
> are not measurements.** The champion is `qwen3.6-35b-a3b-mtp@iq3_s` and every number anyone might
> cite must come from it (F9, F10, both re-run on the champion). The four premises below are
> model-independent; the millisecond figures in the transcript are not, and on the champion the same
> shape of work took 72 s to reach the gate rather than 26 s.

Measured transcript, abridged:

```
[   1506ms] IN   turn-1 prompt: 'There is a bug in calc.py: subtract() adds instead of subtracting...'
[  25902ms] ERR    ⚠ apply_diff wants to run (415 chars):
[  25904ms] ERR      -     return a + b
[  25904ms] ERR      +     return a - b
[  25905ms] ERR  *** GATE OBSERVED ON ERR *** '  Allow? [y/N · or type a redirect] '
[  25905ms] IN   scripted REDIRECT: 'actually just tell me the one-line fix, do not edit anything'
[  31623ms] *** FIRST BYTE ON STDOUT (TTFT sample) ***
[  32106ms] OUT  Change `return a + b` to `return a - b` on line 5 in the subtract() function.
[  32107ms] ERR  ⚡ turn iter=5 in=21106 out=505 ctx ~485/32k (1%)
[  32642ms] process exited rc=0
```

- **P1 REPL-over-pipe reaches a live gate: YES.** The gate fired on `apply_diff`, unprompted by any
  TTY.
- **P2 gate observable on stderr, separately: YES.** Including a full diff preview, which is itself
  a scriptable event (the harness can match on the tool name).
- **P3 TTFT samplable during the run: YES**, 31,623 ms.
- **P4 turn boundary and token counts: YES**, parsed `in=21106 out=505`.

And the redirect worked **semantically**, not just mechanically: `calc.py` was left byte-unchanged
(`subtract` still returns `a + b`) while the model obeyed the typed instruction and answered in
text. Deny-plus-forward is real behaviour, now confirmed by observation rather than by reading
`gate_line_decision`.

### F6. "Time to first visible output" is not first-byte-on-stdout, and the spike proves it.

In that run the operator saw something at **25,902 ms** - the gate preview on stderr. The first model
text on stdout arrived at **31,623 ms**. A TTFT defined on stdout alone overstates the felt latency
by 5.7 s here, and by the entire tool-call phase in general, which on an agentic task is most of it.

The brief asks for "the latency the operator actually feels". So:

- `ttfvo_ms` (**the headline metric**) = first byte on **either** stream after the turn is sent.
- `ttft_stdout_ms` = first model text, kept as a diagnostic.

This distinction only appeared by running it, and it would have quietly biased every latency number.

### F7. The two donors disagree about workspace isolation, and it is not a detail.

Claudette copies a fresh fixture per task (`run_battery.sh`). ABCC wipes its 14 task directories
**once at the start of a run** (`ultimate-100-task-test.js:2642-2653`) and then lets all 100 tasks
share the workspace cumulatively; `RESET_EVERY_N_TASKS` resets *agent memory*, not the filesystem.
Section 4B's ten buggy files are seeded once, before the section, into that shared tree
(`seedBuggyFiles()`, `:2662-2686`).

So an imported ABCC task run under per-task isolation is **not** running the experiment the 7
recorded runs ran. Isolation is the better science and it breaks byte-comparability. The format
records this rather than papering over it.

### F8. ABCC's `fix_sql_inject` verifier passes a solution with the injection fully intact.

Found while building the worked import example, by running the donor's own verifier against an
adversarial input.

The donor assertion (`ultimate-100-task-test.js:1726`) is an OR-chain:

```python
q = r.get('query',''); assert "'" not in q or '?' in q or ':' in q or '%s' in q
```

Any query containing a `?` anywhere short-circuits the check. Ran it:

```
--- gate step 1: untouched fixture must FAIL ---
RESULT: FAIL AttributeError: 'NoneType' object has no attribute 'execute'
--- gate step 2: fixture + refsol must PASS ---
RESULT: PASS donor assertions held
--- adversarial: injection intact, does the donor verifier catch it? ---
RESULT: PASS donor assertions held
actual query returned: SELECT * FROM users WHERE name = 'admin' OR 1=1 --' -- ?
```

That last line is textbook SQL injection and the verdict is PASS. Two things follow:

1. **Claudette's two-point gate would not have caught this.** The fixture FAILs and the refsol
   PASSes, so the task gates clean while the verifier fails to verify. The gate needs a third point.
2. Note *why* the fixture fails: `AttributeError` on a `None` db, i.e. it crashes rather than being
   detected as vulnerable. The donor verifier cannot distinguish "still vulnerable" from "crashed",
   which is the same class of defect the brief already records for BCF's verifier in W6.

This is one task of 100. It is evidence for gating the import, not for distrusting the whole suite.

### F9. `in=` / `out=` is session-cumulative and summed per iteration. Cost is the last line, not the sum of lines.

Settled 2026-08-08 by reading the accounting and then running it, because a single-turn session
cannot tell the two hypotheses apart - and the spike in F5 was single-turn, which is exactly the
coincidence that would have made a wrong reading look right.

**Code.** `runtime/usage.rs:44-50` - `UsageTracker::record()` only ever `+=`, and nothing resets it.
It is called once per **assistant message**, i.e. once per iteration, not once per turn
(`runtime/conversation.rs:577` and `:911`). `TurnSummary.usage` is handed the whole tracker
(`conversation.rs:858`, `usage: self.usage_tracker.cumulative_usage()`). And the tracker is seeded
from the restored session at construction (`conversation.rs:287`,
`UsageTracker::from_session(&session)`), so a `--resume`d session starts non-zero.

**Measured on the champion**, `qwen3.6-35b-a3b-mtp@iq3_s`. Three text-only turns, each `iter=1`:

```
turn  iter       in=    out=     d(in)   d(out)
   1     1      4885      63      4885       63
   2     1      9785      80      4900       17
   3     1     14701      94      4916       14
```

Two tool-using turns, `iter=3` then `iter=2`, both edits applied after a scripted approve (final
`calc.py` correct on both counts):

```
turn  iter       in=    out=     d(in)   d(out)
   1     3     15464     322     15464      322
   2     2     26631     573     11167      251
```

Per-iteration input rises with the conversation (5,155 then 5,584), consistent with each iteration
re-sending the whole grown context. That sum is the right number for cost: it is the true prefill
the machine actually did, not the final context size.

**One cross-model comparison worth keeping.** The same three text turns on `qwen3.5-4b` produced
**byte-identical** `in=` counts (4885 / 9785 / 14701) and different `out=` counts (39 / 88 / 127).
Both are Qwen-family and share a tokenizer, so this is expected - and it establishes that the
**~4.9k per-turn preamble is a property of Claudette's system prompt and tool schemas, not of the
model.** That makes it a fixed cost 2.0 can attack directly, and it means the preamble column is
comparable across any two Qwen subjects.

**Four consequences the harness must implement, all cheap and all silent failures if missed:**

1. **Cost per task = the final line of a fresh session.** Summing the per-turn lines multiply-counts;
   over the 3-turn session above, summing gives 29,371 against a true 14,701.
2. **Cost per turn = the delta between consecutive lines.**
3. **Sessions must start fresh**, or the `from_session` seed must be recorded and subtracted.
4. **The `ctx ~N/32k` gauge is not cost and must never be used as it.** It omits the system prompt
   and tool schemas by design (`cli_prompter.rs:27-29`). In turn 1 above the gauge read `~7` tokens
   while the real input was **4,885**.

**A fifth thing worth having as its own column.** The fixed per-turn overhead - system prompt plus
tool schemas, resent every turn - measures about **4.9k tokens** here. On short tasks that is the
overwhelming majority of input, and it is precisely the part 2.0 can attack (prefix caching against
the 27.8:1 prefill:decode workload, W2). Reporting `tokens_in` without separating it would credit or
blame the model for the harness's preamble.

**Minor defect in the stand-in, David's call, not W8's.** The line is labelled
`turn iter=N in=X out=Y`. It reads as this turn's cost and it is not; in a long REPL session `in=`
grows without bound. Either the label or the number is wrong. It does not block W8 - the harness
takes deltas - but a daily-driver user reading that line is being misled.

### F10. The first task of a run pays the model load, and it must not be charged to the task.

Appeared only on the champion, and it is large enough to invalidate a latency column on its own.

Same three text-only turns, `qwen3.6-35b-a3b-mtp@iq3_s`, one session:

| Turn | Wall clock |
|---|---|
| 1 | **169.7 s** |
| 2 | 4.1 s |
| 3 | 3.7 s |

Turn 1 is not 40x harder than turn 2. It is paying the JIT load of a 35B model. The same effect
shows on the tool-using probe: 71.9 s to the first gate, against 64 s for the second turn's gate
where no load is involved.

The donor harness already carries scar tissue from this without naming it as a metric problem:
`run_battery.sh` retries once on exit code 124 because "the first attempt warms the model", and it
runs `probe_runtime_config.sh` at the **end** of a run because "the model JIT-loads on the first
task, so a probe at t=0 reports `na`".

**So the harness must run a warmup turn before the first measured task**, and record that it did.
Otherwise task 1's `ttfvo_ms` is a model-load measurement wearing a task's name, and since corpora
run in a fixed order, the same unlucky task eats it every time. Add `warmup` to the required RUNMETA
row alongside the held constants.

---

## Recommendation

### R1. Three concepts, not one

The format separates what the donors conflated:

| Concept | Is | Varies |
|---|---|---|
| **Task** | fixture + turns + verifier | never, once frozen |
| **Variant** | permission config + operator track | per experiment |
| **Subject** | binary + adapter + **declared capabilities** | per run |

A result cell is `(task, variant, subject)`. This is what makes the before/after honest: the
`control` variant reproduces the donor's conditions, and intervention variants add the operator
track **against the same fixture and the same verifier**, so a difference is attributable.

### R2. Layout: a directory per task, TOML manifest

```
corpus/
  suites/
    q56/          suite.toml, tasks/Q08/{task.toml, prompt.txt, fixture/, verify.sh, refsol/, sham/}
    u100/         suite.toml, tasks/fix_sql_inject/{...}
    k/            new operator-control tasks, written after this schema is approved
  subjects/
    claudette-fc1ea22.toml
```

TOML because the harness is Rust and `toml = "1"` is already a Claudette dependency
(`crates/claudette/Cargo.toml:64`), and because it takes comments - the Q56 manifest cannot say why a
timeout is what it is.

### R3. `task.toml`

```toml
schema = 1
id      = "Q08"
title   = "chained subtraction evaluates left-associatively"
lang    = "rust"
kind    = "bugfix"
timeout_s = 700

# The unit is a session. A list, even when it has one element.
[[turn]]
send = "prompt.txt"

[verify]
script = "verify.sh"            # RESULT: PASS|FAIL|INVALID <msg>, receives (workdir, transcript)

[provenance]
donor        = "claudette-q56"
donor_id     = "Q08"
donor_commit = "43d6b34"
donor_path   = "runs/eval-2026-05-29/battery"
imported_at  = "2026-08-08"
verbatim     = ["prompt", "fixture", "verify", "refsol", "timeout_s", "lang", "kind"]
rewritten    = []
synthesized  = ["variants"]
caveats      = [
  "donor ran one-shot with CLAUDETTE_AUTO_APPROVE=1; no gate could fire (run.rs:186)",
]
```

`verbatim` / `rewritten` / `synthesized` is the load-bearing idea. The accepted cost of importing is
that "comparability must be argued rather than assumed" - these three lists turn that argument into a
mechanical, per-field record instead of a paragraph someone has to remember to write.

### R4. Variants, and the operator track

```toml
# corpus/suites/q56/tasks/Q08/variants.toml

[[variant]]
id = "control"                  # donor-faithful: reproduces the imported baseline
permissions = { mode = "allow" }
operator = []

[[variant]]
id = "gated"
permissions = { mode = "workspace_write" }
requires = ["tool_gate"]
expect = { gate_fires = { min = 1 } }
operator = [
  { on = { gate = { tool = "apply_diff" } }, do = "approve", times = 1 },
]

[[variant]]
id = "redirect-first-edit"
permissions = { mode = "workspace_write" }
requires = ["tool_gate", "redirect"]
expect = { gate_fires = { min = 1 }, interventions_delivered = 1 }
operator = [
  { on = { gate = { tool = "apply_diff" } },
    do = { redirect = "Fix the operator precedence in eval.rs, not the lexer." }, times = 1 },
  { on = { gate = {} }, do = "approve" },
]
default = "deny"                # answers any gate no rule matched; counted as unscripted_gate
```

Semantics, each chosen because of something the code or the spike showed:

- **Rules are event-triggered, never turn- or clock-triggered.** The subject decides when it calls a
  tool; nothing else is reliably schedulable.
- **The harness writes one line at a time and never pre-queues.** The REPL's line editor and the gate
  share one stdin and take turns owning it (`repl.rs:106-108`). A pre-queued second turn sitting in
  the pipe when a gate fires would be consumed as the gate's answer - and because any non-y/n text is
  a redirect, it would be silently absorbed as an instruction instead of running as a turn. This is a
  real trap and the reason the track is reactive.
- **`default` exists so a stray gate cannot deadlock the session.** Otherwise an unmatched prompt
  blocks on stdin until the task timeout burns.
- **`requires` vs the subject's declared capabilities decides `n/a` mechanically.** Nobody types
  "n/a" into a results table.
- **`expect` violations are `INVALID`, not `FAIL`.** A run where the gate never fired did not measure
  the thing; scoring it as a failure would be a lie in the direction that flatters 2.0.

### R5. Never `PermissionMode::Prompt`

`ReadOnly, WorkspaceWrite, DangerFullAccess, Prompt, Allow` still derives `Ord` at `fc1ea22`
(`runtime/permissions.rs:5-11`), so `Prompt` outranks `DangerFullAccess` and a `Prompt` session
auto-approves everything. The schema's `permissions.mode` therefore accepts only `read_only`,
`workspace_write`, `danger_full_access`, `allow`. **`prompt` is rejected by the loader**, with the
reason in the error message, so the trap cannot be re-entered by someone reading the enum and
reasonably assuming it means "prompt me".

### R6. Subject descriptor: capabilities are declared, `n/a` is derived

```toml
# corpus/subjects/claudette-fc1ea22.toml
id      = "claudette-fc1ea22"
version = "0.17.0"
bin     = "claudette"
drive   = "repl-pipe"           # NOT one-shot: one-shot has no prompter (run.rs:186)

capabilities = ["tool_gate", "redirect", "undo", "resume"]
# absent, deliberately: "pause". No SIGINT handler for a running turn; ctrl_c only
# cancels an input line (run/line_editor.rs:663). The gate is the only synchronous
# interception point, so it stops the agent only when a tool happens to need permission.

[env]
NO_COLOR = "1"
CLAUDETTE_OPENAI_COMPAT = "1"
CLAUDETTE_SKIP_OLLAMA_PROBE = "1"
# CLAUDETTE_AUTO_APPROVE deliberately unset - setting it is what blinded Q56.

[markers]                       # what the adapter watches for, per F3/F4
gate      = "Allow? [y/N"       # stderr, no trailing newline
turn_end  = '^⚡ turn iter=(\d+) in=(\d+) out=(\d+)'
```

Any task variant requiring `pause` against this subject yields `NotSupported`, which prints as `n/a`
and is arithmetically distinct from zero. That column is exactly where 2.0's differentiator has to
appear, so it must never round to nothing.

### R7. Metric values are a three-way enum

```rust
enum Metric { Measured(f64), NotApplicable { reason: String }, NotSupported { capability: String } }
```

Collected per cell: `status`, `ttfvo_ms` (F6), `ttft_stdout_ms`, `wall_clock_s`, `tokens_in`,
`tokens_out`, `iterations`, `gate_fires`, `interventions_delivered`, `unscripted_gates`,
`peak_rss_mb`. Plus the RUNMETA row, which is **required**, not best-effort: a held constant nobody
measures is not held, and the Q56 campaign lost two nights to exactly that.

### R8. The import gate gets a third point

Claudette's gate is: fixture FAILs, refsol PASSes. F8 shows that is not enough. Add `sham/` - a
deliberately wrong solution that satisfies the letter of the verifier - which **must FAIL**:

```
gate(task) := verify(fixture) == FAIL
           && verify(fixture + refsol) == PASS
           && verify(fixture + sham)   == FAIL
```

A task with no plausible sham is fine; the field is optional and its absence is recorded. But for
every imported task where a sham is easy to write, writing it is the cheapest quality signal
available, and it is how `fix_sql_inject` gets caught.

---

## The two worked import examples

### A. Claudette Q56 `Q08` -> `corpus/suites/q56/tasks/Q08/`

The easy direction. The donor and the format agree on almost everything.

| Corpus field | Donor source | Transform |
|---|---|---|
| `id`, `lang`, `kind`, `timeout_s` | `manifest-q50.tsv` row `Q08 rust multi-file Q08 700` | verbatim |
| `prompt.txt` | `prompts/Q08.txt` | verbatim |
| `fixture/` | `fixtures/Q08/` | verbatim |
| `verify.sh` | `verify/Q08.sh` | verbatim; contract already matches |
| `refsol/` | `refsol/Q08/` | verbatim |
| `[[turn]]` | the single `claudette "<prompt>"` call | **synthesized**: one-turn session |
| `variants` | none | **synthesized**: `control` + gated + redirect |
| `sham/` | none | **synthesized**, or recorded absent |

The donor prompt needs no rewriting at all - it names no tools and no absolute paths:

> "This crate evaluates simple integer arithmetic expressions (see src/lib.rs, src/lexer.rs,
> src/eval.rs). There's a bug: chained subtraction comes out wrong. [...] The existing test must
> still pass."

`verbatim` is long, `rewritten` is empty, and the one caveat is F1: the donor's number was produced
one-shot under `Allow`, so it is comparable to the `control` variant and to nothing else.

### B. ABCC U100 `fix_sql_inject` -> `corpus/suites/u100/tasks/fix_sql_inject/`

The hard direction, and the one that justifies the provenance block. Chosen because section 4B is
the closest ABCC gets to repo work: the agent reads an existing buggy file rather than generating a
project from nothing.

| Corpus field | Donor source | Transform |
|---|---|---|
| `id`, `kind`, `lang` | `name`, `category: 'bugfix'`, inferred `py` | verbatim |
| `fixture/sql_inject.py` | `BUGGY_FILES['sql_inject.py']` (`:1707`) | **synthesized**: a string in a JS map becomes a per-task fixture dir |
| `fixture/__init__.py` | created by `seedBuggyFiles()` (`:2666`) | **synthesized** |
| `prompt.txt` | `description` (`:1725`) | **rewritten**, twice - see below |
| `verify.sh` | `validation` + `validationLang: 'py'` (`:1726-1727`) | **rewritten**: paths, contract, and execution model |
| `timeout_s` | none per task; global `TASK_TIMEOUT_MS` = 5 min | **synthesized**: 300 |
| `refsol/`, `sham/` | none | **synthesized** |
| `complexity = 7` | `complexity: 7` | kept as a donor-scoped tag with no cross-suite meaning |

**Two rewrites to the prompt, both consequential:**

1. `Use file_write to save the fixed version` names a tool from **ABCC's** registry. Claudette has
   `edit_file` / `apply_diff` / `write_file`. Left in, the prompt instructs the subject to call a
   tool that does not exist. Rewritten to "Edit the file to fix it." This is a semantic edit to a
   donor prompt and the largest single threat to comparability in the whole import.
2. `tasks/security_fixes/sql_inject.py` is a path inside ABCC's container layout. Rewritten to
   `sql_inject.py`, relative to the work dir.

**The verifier is rewritten three ways.** The donor snippet is base64'd and run as
`docker exec -w /app/workspace abcc-agents python3 -c ...` (`:2805-2806`), so it needs: absolute
`/app/workspace` paths rewritten to the work dir; the `docker exec` execution model dropped; and the
donor's `result.includes('PASS')` plus catch-all `return false` (`:2809-2813`) mapped onto
`RESULT: PASS|FAIL <msg>`. The catch-all is preserved rather than improved, because faithfulness to
the donor is the point of an import - **but the third gate point is what makes it safe to preserve.**

Gate result, run for real (F8): fixture FAIL, refsol PASS, **sham PASS - a fail**. So under R8 this
task **does not enter the corpus** until either its verifier is repaired (recorded as `rewritten`,
breaking comparability with the 7 donor runs) or it is imported as `quarantined` with its baseline
carried but excluded from any aggregate. That is a decision for the import pass, and the schema's job
is only to make it visible rather than silent.

**And the isolation caveat (F7) applies to the whole suite**, recorded once at suite level:

```toml
caveats = [
  "donor shared one cumulative workspace across all 100 tasks (ultimate-100-task-test.js:2642); \
   per-task isolation here is better science and breaks byte-comparability with the 7 recorded runs",
  "donor had no permission gate in the path at all; every U100 baseline is effectively mode=allow",
]
```

---

## Options compared

Scored against: expresses an intervention track / imports both donors without editing them /
readable by David in a diff / Rust-native / lets `n/a` be first-class.

| Option | Track | Imports | Diffable | Rust | `n/a` | Verdict |
|---|---|---|---|---|---|---|
| **Dir-per-task + TOML (R2)** | yes | yes | yes | yes | yes | **recommended** |
| Extend Q56's TSV manifest | no - a nested rule list will not fit a column | partly | yes | yes | no | rejected |
| One big JSON/YAML corpus file | yes | yes | poor - fixtures cannot live in it | yes | yes | rejected |
| Rust structs, corpus as code | yes | yes | no - recompile to add a task | yes | yes | rejected |
| Reuse ABCC's JS array shape | no | no | poor | no | no | rejected |

## Rejected alternatives and why

- **Extend Claudette's TSV manifest.** Cheapest by far, and it is the format that already works. It
  fails on the one thing W8 exists to measure: an operator track is a nested, ordered list of
  event-action rules, and a TSV column cannot hold it without becoming an embedded mini-language.
  Rejected on the same reasoning that rejected extending the corpora in place.
- **A single JSON or YAML corpus document.** Fixtures are directories of real source files that must
  be copied, compiled and tested; they cannot live inside the manifest, so the format is
  file-tree-shaped whether or not the manifest admits it. YAML additionally makes embedded code
  indentation-sensitive.
- **Corpus as Rust code.** Type-safe and tempting given the harness is Rust, but adding a task would
  mean recompiling the harness, and it puts task content behind `cargo build` for a research phase
  whose whole point is to iterate on task content.
- **Keep ABCC's shape.** Fails every criterion; the suite is being imported *out* of it.

## Effect on fun

Positive, and not incidentally.

The operator track is the first time anything in this family can *express* "I grabbed the wheel
mid-run", which is the feeling ABCC 2.0 is being built to produce. Writing a K-series task is
literally writing down an interaction David wants to be good, then measuring whether it is. That is
the fun criterion becoming an artifact instead of a vibe.

The `n/a` column is the honest version of the same thing: the pause column reads `n/a` for the
stand-in today, and the first time it reads a number instead, that is 2.0 earning its existence in
one cell of a table.

One risk against fun: this is a corpus format, an importer and a gate - real engineering inside a
research phase, already accepted as a cost. Kept in check by not writing new task content until this
schema is approved, which is exactly why this document stops here.

## Open questions

1. ~~**Does `in=`/`out=` sum per-iteration usage correctly?**~~ **ANSWERED 2026-08-08 - see F9.**
   It is session-cumulative, summed per iteration. Cost per task is the last line of a fresh session,
   cost per turn is the delta, and the `ctx` gauge is not cost. F10 came out of the same runs: the
   first task pays the model load and needs a warmup turn.
2. ~~**`fix_sql_inject`: repair, quarantine, or import as-is?**~~ **DECIDED by David 2026-08-08:
   quarantine-with-baseline.** Its donor baseline is carried and it is excluded from any aggregate.
   The same disposition applies to any other task that fails the three-point gate, unless David says
   otherwise per task.
3. ~~**How many of ABCC's other 99 tasks survive the three-point gate?**~~ **SCOPED by David
   2026-08-08: author the three-point gate across the 30 hardest ABCC tasks only**, not all 100.
   The remaining 70 import on the two-point gate. **What "hardest" means is the first open question of
   the import pass** and is answerable from data already in the repo:
   `prestudy/data/abcc-100task-results.tsv` holds 481 rows across the 7 recorded runs, so hardest can
   be ranked by observed failure rate. Two wrinkles to handle when doing it: the 2026-02-26 run is an
   infrastructure collapse (72 errors, 0 genuine failures) and must be excluded, and the suite is
   saturating - the best run scored 95/100 - so failure rate alone will not separate 30 tasks. Expect
   to need a tie-break, most likely complexity band then category coverage, so the 30 are not all
   drawn from one section.
4. **Does the redirect need a per-tool granularity the gate does not offer?** The gate fires per tool
   call with the tool name and full input available on stderr, which is enough to match on. Whether
   matching on the *input* (e.g. only redirect a `bash` running `cargo test`) is needed is a K-series
   authoring question, not a schema one - the schema already allows it.
5. **Peak RSS / VRAM.** Nothing in the family has a probe; W1/W2 owns building it. The schema
   reserves the metric names so the column can appear without a format change.

## Confidence: high on mechanics, medium on the import

**High** that the harness can drive the stand-in as described: the four premises were measured, not
read, on the actual binary at the actual version against a live model, and the redirect was confirmed
behaviourally (file unchanged, instruction obeyed). F1, F3, F4 and F6 each corrected or sharpened
something a reading of the docs would have got wrong.

**Medium** on the import. The Q56 direction is close to mechanical. The ABCC direction needs a
semantic rewrite of every prompt that names `file_write`, and F8 shows at least one verifier that
does not verify. What would raise it: run the three-point gate across all 100 ABCC tasks and report
the survival rate (open question 3), which is a day's work and turns the whole U100 import from an
assumption into a number.

**Low, and flagged as such:** nothing here has been tested against a second subject. The subject
descriptor (R6) is designed for a future 2.0 that does not exist, so its capability vocabulary is a
prediction. It will need one revision when 2.0 first runs, and that is expected rather than a defect.
