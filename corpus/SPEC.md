# ABCC 2.0 corpus format — v1 (frozen)

`schema = 1`. Frozen 2026-08-08. **This file, not `research/W8-corpus-format.md`, is what the importer
codes against.** The research doc carries the reasoning and the evidence; this carries the contract.

Basis: R1–R8 of `research/W8-corpus-format.md`, approved by David 2026-08-08 with five amendments
(§14). R6 was approved separately on the same date. Every "because" below traces to a finding
(F1–F21) in `research/W8-corpus-format.md`, `research/W8-hardest-30.md` or
`research/W8-gate-step1-all90.md`; findings are cited, not restated.

**Changing v1.** Anything that makes a previously-valid corpus invalid, or changes what a field means,
bumps `schema` to 2 and needs David. Adding an optional field with a defined default does not. The
loader rejects `schema` values it does not know rather than guessing.

---

## 1. The three concepts (R1)

| Concept | Is | Varies | Lives in |
|---|---|---|---|
| **Task** | fixture + turns + verifier | never, once frozen | `suites/<suite>/tasks/<id>/` |
| **Variant** | permission config + operator track | per experiment | `suite.toml`, overridable per task |
| **Subject** | binary + adapter + declared capabilities | per run | `subjects/<id>.toml` |

A result cell is `(task, variant, subject)`. The `control` variant reproduces the donor's conditions;
intervention variants add an operator track against **the same fixture and the same verifier**, so a
difference between cells is attributable to the intervention and to nothing else.

Task content never changes when a variant is added. That is why variants are not in `task.toml`.

## 2. Layout (R2)

```
corpus/
  SPEC.md                          this file
  subjects/
    claudette-fc1ea22.toml         one per subject under test — this one predates [delivery]
    claudette-af3f804.toml         the same subject one commit later, and the current one
  suites/
    u100/
      suite.toml                   suite metadata, caveats, aggregate rule, default variants
      tasks/
        fix_sql_inject/
          task.toml                required
          prompt.txt               required if any turn uses send_file
          fixture/                 required; copied fresh into the workdir per task run
          verify.sh                required unless [verify].kind = "none"
          refsol/                  optional; gate point 2 only, never visible to the subject
          sham/                    optional; gate point 3 only, never visible to the subject
          stub/                    optional; overrides the generated stub for gate point 1
          variants.toml            optional; overrides or extends the suite defaults
    q56/                           Claudette's battery (step 5)
    k/                             new operator-control tasks, authored after this freeze
```

TOML because the harness is Rust (`toml` is already a Claudette dependency,
`crates/claudette/Cargo.toml:64`) and because it takes comments — the donor TSV manifest cannot say
*why* a timeout is what it is.

`refsol/`, `sham/` and `stub/` are gate-time only. The runner must never copy them into a workdir the
subject can see; a loader that cannot guarantee that must refuse to run.

## 3. `task.toml`

```toml
schema = 1
id        = "fix_sql_inject"      # must equal the directory name
title     = "parameterise the user lookup query"
lang      = "python"
kind      = "bugfix"
timeout_s = 300

# The unit of measurement is a session. A list, even when it has one element.
[[turn]]
send_file = "prompt.txt"          # exactly one of send_file / send_text

[verify]
kind   = "script"                 # script | none
script = "verify.sh"              # contract in §8

[disposition]                     # §10 — amendment 2
verifiable = "full"               # full | presence_only | none
quarantine = "none"               # none | with_baseline

[selection]                       # amendment 2; `gate3` is R9's rename of `hardest`
gate3      = true
gate3_rank = 9

[gate]                            # §9 — amendment 2; recorded, not asserted at run time
point1 = "sound"
point2 = "sound"
point3 = "broken"

[[gate.evidence]]
point    = 1
tier     = "stub"                 # stub | absent | donor_fixture | refsol | sham
verdict  = "FAIL"                 # PASS | FAIL | INVALID
detail   = "AssertionError"
verifier = "rewritten"            # rewritten | donor
run      = "<script>, <platform>, <date>"

[provenance]
donor        = "abcc-u100"
donor_id     = "fix_sql_inject"
donor_commit = "d5528ea"
donor_path   = "scripts/ultimate-100-task-test.js"
imported_at  = "2026-08-08"
verbatim     = ["fixture", "kind", "complexity"]
rewritten    = ["prompt", "verify"]
synthesized  = ["timeout_s", "refsol", "sham", "variants", "turn"]
caveats      = ["..."]

[donor_tags]                      # donor-scoped, no cross-suite meaning
complexity = 7
section    = "4B"
```

**`verbatim` / `rewritten` / `synthesized` is load-bearing.** The accepted cost of importing rather
than extending is that comparability must be *argued*. These three lists turn that argument into a
mechanical per-field record instead of a paragraph someone has to remember to write.

The three lists must **partition** this fixed vocabulary — every name in exactly one list, no name
twice, nothing left out:

```
id  title  lang  kind  timeout_s  turn  prompt  fixture  verify
refsol  sham  variants  disposition  selection  gate  donor_tags
```

The loader checks it (§13 rule 10). It is checkable precisely because the vocabulary is closed;
adding a name to it is a `schema` bump.

### Field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema` | int | yes | must be `1` |
| `id` | string | yes | `[a-z0-9_]+`, equal to the directory name |
| `title` | string | yes | human-readable, not an identifier |
| `lang` | string | yes | `python` \| `node` \| `rust` \| `go` \| `typescript` \| `html` \| `shell` \| `mixed` (amendment 8) |
| `kind` | string | yes | free text; donor category maps straight in (`bugfix`, `security`, …) |
| `timeout_s` | int | yes | wall clock for the whole session, not per turn |
| `[[turn]]` | array | yes, ≥1 | ordered; `send_file` **xor** `send_text` |
| `[verify].kind` | string | yes | `script` \| `none` |
| `[verify].script` | string | if `kind="script"` | path relative to the task dir |
| `[disposition]` | table | yes | §10 |
| `[selection]` | table | no | absent ⇒ `gate3 = false` |
| `[gate]` | table | yes | §9; `not_run` is a legal value, silence is not |
| `[provenance]` | table | yes | authored tasks use `donor = "k-series"` and `verbatim = []` |
| `[donor_tags]` | table | no | arbitrary keys, never read by the aggregate |

`send_file` / `send_text` replaces R3's single `send` key, which could not be read unambiguously
(amendment 5).

## 4. `suite.toml`

```toml
schema = 1
id     = "u100"
title  = "ABCC's 100-task suite — the 90 stable tasks"

[provenance]
donor        = "agent-battle-command-center"
donor_commit = "d5528ea"
donor_path   = "scripts/ultimate-100-task-test.js"
imported_at  = "2026-08-08"

caveats = [ "..." ]      # suite-wide; per-task caveats live in the task's provenance

[aggregate]
include_verifiable  = ["full", "presence_only"]
exclude_quarantined = true

[[variant]]              # defaults, inherited by every task in the suite
...
```

Suite-level `caveats` exist so a fact true of all 90 tasks is stated once. The two that apply to
`u100` are F7 (the donor shared one cumulative workspace; per-task isolation is better science and
breaks byte-comparability with the 7 recorded runs) and F1 (the donor had no permission gate in the
path at all, so every U100 baseline is effectively `mode = "allow"`).

## 5. Variants (R4, amendment 4)

Variants are declared once in `suite.toml` and inherited by every task. A task overrides or extends
them with a `variants.toml` in its own directory. Merge is **by `id`**: a task-level variant with an
id that already exists replaces the suite one entirely (no field-level merge — partial merge of an
ordered rule list is not readable in a diff); a new id is appended.

Without this, the importer would emit 90 near-identical `variants.toml` files.

```toml
[[variant]]
id          = "control"                       # donor-faithful; reproduces the imported baseline
permissions = { mode = "allow" }
operator    = []

[[variant]]
id          = "gated"
permissions = { mode = "workspace_write" }
requires    = ["tool_gate"]
expect      = { gate_fires = { min = 1 } }
operator    = [ { on = { gate = {} }, do = "approve" } ]
default     = "deny"

[[variant]]
id          = "redirect-first-edit"
permissions = { mode = "workspace_write" }
requires    = ["tool_gate", "redirect"]
expect      = { gate_fires = { min = 1 }, interventions_delivered = 1 }
operator = [
  { on = { gate = { tool = "apply_diff" } }, do = { redirect = "..." }, times = 1 },
  { on = { gate = {} }, do = "approve" },
]
default = "deny"
```

**Two ways to write a rule, one parsed result.** The inline form above is R4's and reads well for
short rules. A TOML inline table **cannot span lines**, so any rule whose redirect text does not fit
on one line must use the array-of-tables form instead:

```toml
[[variant]]
id = "redirect-first-edit"
# ... scalar keys first; the operator blocks must follow, or they attach to the wrong variant

[[variant.operator]]
on    = { gate = { tool = "apply_diff" } }
do    = { redirect = "a long instruction that would not fit on one line" }
times = 1
```

Both produce the same array of rule tables in the same order. The loader does not distinguish them.

### Operator-track semantics

- **`on` matchers.** `{ gate = {} }` matches any permission gate. `gate.tool` narrows to a tool name.
  `gate.input_contains` narrows to a substring of the tool input as previewed on stderr — present so
  that "only redirect a `bash` running `cargo test`" is a K-series authoring question and not a
  schema change (open question 4).
- **`do`** is `"approve"`, `"deny"`, or `{ redirect = "<text>" }`.
- **Rules are event-triggered, never turn- or clock-triggered.** The subject decides when it calls a
  tool; nothing else is reliably schedulable.
- **First matching rule wins**, in declaration order. `times` caps how often a rule may fire (default
  unlimited); an exhausted rule stops matching and the next one is tried.
- **`default` answers any gate no rule matched**, and every use of it increments `unscripted_gates`.
  It exists so a stray gate cannot deadlock the session on stdin until the timeout burns.
- **The harness writes one line at a time and never pre-queues.** The REPL's line editor and the gate
  share one stdin and take turns owning it (`repl.rs:106-108`). A pre-queued next turn sitting in the
  pipe when a gate fires is consumed as the gate's answer — and since any non-`y`/`n` text is a
  redirect, it is silently absorbed as an instruction instead of running as a turn. This is the
  reason the track is reactive, and it is a real trap.
- **`requires` vs the subject's declared capabilities decides `n/a` mechanically** (§7). Nobody types
  "n/a" into a results table.
- **`expect` violations are `INVALID`, not `FAIL`.** A run where the gate never fired did not measure
  the thing; scoring it as a failure would be a lie in the direction that flatters 2.0.

`expect` keys: `gate_fires = { min, max }`, `gate_fires_after_deny = { min, max }`,
`interventions_delivered = <int>`, `unscripted_gates = { max }`.

### Why `gate_fires_after_deny` exists (F36, amendment 6)

**`gate_fires = { min = 2 }` cannot express "the subject re-proposed the edit after being denied",
and that is the question a deny variant is authored to ask.** Measured on `fix_sql_inject`'s own
`deny-first-edit`: the run fired **five** gates, four of them exploratory `bash` calls (`bash` is
`DangerFullAccess`, so it gates unconditionally), and the denial was the session's *last* gate. The
bound passed. Nothing was answered. A count that any amount of unrelated tool use can satisfy is a
bound on curiosity, not on persistence.

`gate_fires_after_deny` counts only gates that fired **strictly after the first `deny` the operator
track delivered**. `{ min = 1 }` therefore reads "having been refused once, the subject asked for
something again"; `{ max = 0 }` reads "the first refusal stopped it", which is the behaviour actually
observed on the second `fix_sql_inject` run — the subject stopped, left the fixture untouched, and
the verifier failed on the fixture's own `AttributeError`. **Both are results. Only the bound tells
a reader which one the variant was looking for**, and a violation is `INVALID` like every other
`expect`, because a run that did not reach a denial did not measure persistence either way.

Deliberately not counted: gates before the first denial, and the denied gate itself. A variant that
wants "at least one gate at all" already has `gate_fires`.

## 6. Permissions (R5)

`permissions.mode` accepts exactly: `read_only`, `workspace_write`, `danger_full_access`, `allow`.

**`prompt` is rejected at load time**, with the reason in the error message:

> `permissions.mode = "prompt"` is rejected: `PermissionMode` derives `Ord` at `fc1ea22`
> (`runtime/permissions.rs:5-11`) with `Prompt` ranked above `DangerFullAccess`, so a `Prompt` session
> auto-approves everything. Use `workspace_write` to get a gate.

The trap is that the enum variant reads as "prompt me" and does the opposite. Rejecting it at load,
with the reason attached, is the only way it cannot be re-entered by someone reading the enum and
reasoning correctly from its name.

## 7. Subject descriptor (R6, approved as-is)

```toml
schema  = 1
id      = "claudette-af3f804"
version = "0.17.0"
commit  = "af3f804"
bin     = "claudette"
drive   = "repl-pipe"            # NOT one-shot: one-shot has no prompter (run.rs:186)

capabilities = ["tool_gate", "redirect", "undo", "resume"]

[env]
NO_COLOR = "1"

[markers]
gate     = "Allow? [y/N"
turn_end = '^⚡ turn iter=(\d+) in=(\d+) out=(\d+)'

[delivery]                       # optional; how this subject receives a multi-line prompt
open  = "<<<CLAUDETTE-PROMPT"
close = "CLAUDETTE-PROMPT>>>"
```

**`[delivery]` is what makes a multi-line prompt deliverable at all (amendment 7).** A piped REPL
reads one line per turn, so a prompt containing newlines becomes several turns — and worse, a blank
line inside it is skipped and a line reading `exit` ends the session. **69 of the 90 U100 prompts are
multi-line**, up to 54 lines. The two sentinels name lines that open and close a block the subject
reassembles into one turn; each must be alone on its line and match exactly.

The table is **optional and both keys are required once it is present** — a half-declared pair would
wrap a prompt in something the subject never closes on, and that failure lands as a timeout rather
than as a bad descriptor. A subject that declares no `[delivery]` is valid; it simply cannot run the
tasks whose prompts are multi-line, and the runner must refuse those cells rather than flatten them.

**The runner reads the pair from here and never hard-codes it.** These strings are a fact about one
subject; a second subject will have different ones, or none.

A variant whose `requires` names a capability the subject does not declare yields `NotSupported`,
which prints as `n/a` and is arithmetically distinct from zero. That column is exactly where 2.0's
differentiator has to appear, so it must never round to nothing.

`CLAUDETTE_AUTO_APPROVE` is never set. Setting it is what blinded Q56 (F1).

## 8. The verifier contract

`verify.sh` is invoked as `bash verify.sh <workdir> <transcript>` and writes **one line** to stdout:

```
RESULT: PASS <msg>
RESULT: FAIL <msg>
RESULT: INVALID <msg>
```

- Exit status is ignored; the line is the verdict. **Output containing no `RESULT:` line is
  `INVALID`, not `FAIL`** — "the verifier did not run" and "the artifact is wrong" are different
  facts, and the donor conflated them (F8: an `AttributeError` on a `None` db read as "vulnerability
  detected"). This is not hypothetical: a misresolved interpreter makes a verifier print an unrelated
  message and exit 0 or 9009, and scoring that as `FAIL` would report a broken harness as a hard task.
- Both arguments are absolute paths. The transcript is passed even when unused; transcript-reading
  verifiers are inherited from Q56 and matter.
- Verifiers are POSIX `sh`/`bash`. **The reference platform is Linux.** Every gate result recorded so
  far was measured on the Windows host, not in a container; a Linux re-run is a cheap unspent
  confirmation and the `absent`/`stub` error-class transition is the thing to check if it disagrees.
- Interpreters resolve through the environment (`${PYTHON:-python3}`, `${NODE:-node}`) so the same
  task runs on the host and in a container. **The harness must probe by executing, not by looking.**
  Windows ships a Microsoft Store alias shim named `python3.exe`; it is on `PATH`, `command -v` finds
  it, and running it prints an advert instead of the code. `python3 -c ''` returning 0 is the test.

`[verify].kind = "none"` is legal and means the donor supplied no verifier (F13: ten U100 tasks carry
`validation: null` and are scored on the agent-execution success flag). Such a task **must** carry
`disposition.verifiable = "none"`.

## 9. The import gate (R8, amendment 1)

```
gate(task) := verify(pre_state)        == FAIL
           && verify(fixture + refsol) == PASS
           && verify(fixture + sham)   == FAIL
```

Every input is a wrong answer, so every one must be rejected. A verifier that accepts any of them
cannot report that answer as wrong.

### Point 1 — the pre-state must FAIL. The pre-state is a **null-implementation stub** (F19).

Not the absent artifact. Running a verifier against an empty workspace misses `fix_path_traversal`
entirely, because its import raises before reaching the swallowed `assert`; the stub makes the import
succeed and exposes the defect. Same cost, strictly stronger. **The cheap gate asks "does the verifier
notice a no-op", not "does it notice absence."**

The stub is **generated, not authored** — no per-task work:

- *Python*: a module whose `__getattr__` returns a no-op for every name, with dunders still raising
  `AttributeError` so the import machinery does not read a stub `__path__` and treat the module as a
  package.
- *Node*: `module.exports` is a `Proxy` whose every string key resolves to a function returning
  `undefined`; symbol keys stay undefined so the module does not look thenable or iterable.
- *Files the verifier only opens*: created empty.

A task may ship `stub/` to override the generated one. Where the donor also supplies a real buggy
fixture (the 10 section-4B tasks), that fixture is run as an **additional** point-1 input and must
also FAIL.

Point 1 runs at import time **on all 90 tasks**, not just the `gate3` 30 — it is mechanical.

### Points 2 and 3 need authored artifacts

`refsol/` and `sham/` are optional. Absent, the corresponding point records `not_run`; it is never
silently treated as passed. Points 2 and 3 are authored for the `gate3` 30 (R10) and the shams must be
written against the **rewritten** verifier, not the donor's — which is why authoring follows import.

The 24 `presence_only` shams are **generated, not authored** (F20): a file whose entire content is a
comment holding every substring the verifier searches for. This is sound only because all 24
assertions are positive presence checks, with no `not in` anywhere — the loader must re-verify that
before generating, and fall back to `not_run` if it does not hold.

### `[gate]` vocabulary

`sound` (the requirement held) · `broken` (a wrong answer was accepted) · `inconclusive` (the failure
could be platform noise rather than detection) · `not_run`.

**Evidence carries `verifier = "rewritten" | "donor"`, and `rewritten` is the authoritative column.**
A gate result measured against the donor's verifier does not describe the verifier this corpus runs.
The two normally agree; where they diverge the difference is itself worth recording, since a path or
contract rewrite that changes a verdict has changed the task.

**Step-1 `sound` is necessary, not sufficient, and the suite contains its own proof.**
`fix_sql_inject` is step-1 sound — it rejects absence, inertness and its own unfixed fixture — and F8
still showed it passing a solution with the SQL injection fully intact. Point 1 bounds the defect rate
**from below**. Only an authored sham closes it. A spec that let `point1 = "sound"` stand in for
"verified" would be reintroducing the defect it exists to catch.

### The importer never drops a task

A task that fails any gate point is imported with `quarantine = "with_baseline"`. Failing the gate
changes the disposition; it never changes whether the task is on disk (§10).

## 10. Disposition, and the aggregate rule

Two orthogonal fields. Both are always written.

| `verifiable` | Means | n |
|---|---|---|
| `full` | the verifier executes the artifact and asserts behaviour | 56 |
| `presence_only` | the verifier string-matches generated source; a PASS establishes presence, not correctness | 24 |
| `none` | no verifier; the donor scored the agent-execution success flag (F13) | 10 |

| `quarantine` | Means | n |
|---|---|---|
| `none` | enters aggregates subject to the suite's `include_verifiable` | 78 |
| `with_baseline` | the donor baseline is carried, the task runs, and it is excluded from every aggregate | 12 |

Expected `u100` import: **54 clean** (`full` + `none` quarantine), **24 presence-only**, **12
quarantined-with-baseline** (10 `none` + `fix_sql_inject` and `fix_path_traversal`, both `full` but
demonstrated not to reject a wrong answer). 56 − 2 = 54; 54 + 24 + 12 = 90.

**This is a field, not a fork, and that is the point.** All 90 import once. Which dispositions enter a
headline number is `suite.toml`'s `[aggregate]`, and flipping it re-scores without re-importing.

**The rule as set by David, 2026-08-08:** `include_verifiable = ["full", "presence_only"]`,
`exclude_quarantined = true`. So the 24 count, the denominator stays 90 − 12 = 78, and the fact that
section 2 verifies presence rather than correctness is recorded at suite level rather than
task-by-task. The reasoning (R9) is that a `landing` task has no ground truth to be wrong about, so
quarantining it would describe a property of the task genre as if it were a defect. The alternative —
applying the standing quarantine rule literally, taking the usable suite to 54 and dropping all 15 of
section 2 — was considered and rejected.

**Any published number must state the rule it was computed under.** A headline that does not say
whether presence-only tasks are in it is not interpretable.

## 11. Results: metrics and RUNMETA (R7, amendment 3)

```rust
enum Metric { Measured(f64), NotApplicable { reason: String }, NotSupported { capability: String } }
```

Per cell `(task, variant, subject)`:

| Metric | Notes |
|---|---|
| `status` | `pass` \| `fail` \| `invalid` \| `not_supported` \| `timeout` \| `error` |
| `ttfvo_ms` | **headline latency.** First byte on **either** stream after the turn is sent (F6) |
| `ttft_stdout_ms` | first model text on stdout; diagnostic only |
| `wall_clock_s` | |
| `tokens_in`, `tokens_out` | **the last `turn iter=` line of a fresh session, never the sum** (F9) |
| `tokens_in_preamble` | *derived*: `turns × RUNMETA.preamble_tokens_in` |
| `tokens_in_net` | *derived*: `tokens_in − tokens_in_preamble` |
| `iterations` | `iter=` from the same line |
| `gate_fires`, `gate_fires_after_deny`, `interventions_delivered`, `unscripted_gates` | `gate_fires_after_deny` counts only gates strictly after the first delivered `deny` (§5, F36) |
| `delivery.mode` / `delivery.transport` / `delivery.faithful` | the mode is `verbatim` or `escape-newlines`; the transport is `line` or `sentinel` (§7). **A wrapped block is still verbatim and still faithful** — the wrapper is how the bytes travelled, not an edit to them |
| `peak_prompt_tokens` | *derived*: the subject's own end-of-turn context estimate, MAXed over turns, plus `tokens_in_preamble`. A **floor**, never the peak — all four of its limits understate, and it is quantized to 1,024. A validity gate for context-pressure tasks, not a performance number |
| `subject_output_bytes`, `subject_last_output_ms` | what the subject put on the pipes, and when it last did (session clock, zero = spawn). The **only** metrics that survive a timeout, which is the case they exist for: a subject narrates file mutations but not reads, so a cell can work for 40 minutes in silence and every other metric goes `not_applicable` (F91). The timestamp is the decisive one — the banner alone means the byte count is never zero |
| `peak_rss_mb` | no probe exists yet (W1/W2 owns building it); the name is reserved |

**Three ways to get token accounting wrong, all silent (F9):**

1. `in=`/`out=` are **session-cumulative and summed per iteration**, not per turn. Cost per task is
   the final line; cost per turn is the delta. Summing the lines over a 3-turn session gave 29,371
   against a true 14,701.
2. Sessions must start fresh, or the `from_session` seed must be recorded and subtracted
   (`conversation.rs:287`).
3. **The `ctx ~N/32k` gauge is not cost.** It omits the system prompt and tool schemas by design; the
   gauge read `~7` while real input was 4,885.

**RUNMETA is required, not best-effort** — a held constant nobody measures is not held, and the Q56
campaign lost two nights to exactly that. The row carries the model id, context size, subject id,
subject commit, corpus commit, platform, and:

- `warmup` — whether a warmup turn ran before the first measured task. **It must.** On the champion,
  turn 1 took 169.7 s against 4.1 s and 3.7 s for turns 2–3; that is a 35B JIT load, and since corpora
  run in a fixed order the same unlucky task eats it every time (F10). The warmup turn replaces the
  donor's retry-once-on-124 rule, which was scar tissue from the same effect.
- `preamble_tokens_in` — the `in=` of the warmup turn. This is Claudette's fixed per-turn overhead
  (system prompt + tool schemas, ~4.9k) **plus** the fixed warmup prompt, so it is an upper bound on
  the preamble and is comparable across subjects only because the warmup prompt is held constant.
  It is worth its own number because it is the part 2.0 attacks directly (prefix caching, W2), and
  because reporting `tokens_in` without separating it credits or blames the model for the harness's
  preamble. Measured identical on `qwen3.5-4b` and the champion, so it is a property of Claudette and
  not of the model.

## 12. Driving the subject

Recorded here because it constrains the format, not as runner design (step 3):

- **REPL over pipes, never one-shot.** One-shot constructs `None` for its prompter (`run.rs:186`), so
  it cannot edit a file at all without `CLAUDETTE_AUTO_APPROVE`, and it can never show a gate (F1).
- **stdout and stderr are separate pipes.** Model text is stdout; the gate and the turn-end line are
  stderr. Merged, a harness cannot tell a gate prompt from model output (F3).
- **The gate prompt has no trailing newline** (`write!`, not `writeln!`, `cli_prompter.rs:84`). A
  line-buffered reader blocks on it forever. Read bytes, or match the prompt suffix.
- **The turn-end line is the only turn boundary**, because piped mode never echoes `❯`
  (`line_editor.rs:370-376`).
- **A multi-line prompt goes in as a sentinel-delimited block** (§7's `[delivery]`), written line by
  line before the turn starts. This is the **one** exception to §5's "never pre-queue": the subject
  consumes the whole block inside a single read, so no gate can fire part-way through and no line of
  it can be swallowed as a gate answer. The exception holds only because the block is *read*, not
  *run* — a pre-queued second **turn** is still the trap §5 describes.

## 13. Loader validation

The loader **rejects the corpus** — it does not warn — on:

1. `schema` missing or unknown.
2. `id` ≠ directory name.
3. `permissions.mode = "prompt"` (§6), with the reason in the message.
4. A `[[turn]]` with neither or both of `send_file` / `send_text`; a `send_file` that does not resolve.
5. `[verify].kind = "script"` with a missing script, or `= "none"` with `verifiable ≠ "none"`.
6. `[disposition]` missing, or a value outside the enums in §10.
7. `[gate]` missing a point. `not_run` is how you say "not yet"; silence is not.
8. A variant whose `requires` names a capability no subject declares — caught at run planning, not
   load, since it is a property of the pair.
9. Duplicate variant `id` **within** one file (across files is the documented override, §5).
10. A provenance partition that is not a partition: a field in two of
    `verbatim`/`rewritten`/`synthesized`, or in none.

Rule 10 is the one that costs something to maintain and is the reason the block exists. An import
whose provenance is approximately right is an import whose comparability argument is approximately
right.

## 14. Amendments to `research/W8-corpus-format.md`

The delta from the prose David read, so the change is visible rather than smuggled.

| # | Amends | Change | Because |
|---|---|---|---|
| 1 | R8 | Gate point 1 is a **null-implementation stub**, not the absent artifact; the donor's buggy fixture is an additional input where one exists | F19 — `absent` alone misses `fix_path_traversal` at identical cost |
| 2 | R3 | `task.toml` gains `[selection].gate3` (R9's rename of `hardest`), `[disposition]`, and `[gate]` with recorded evidence | R9; the F20 decision must be a field, not a fork; the sweep result should travel with the task |
| 3 | R7 | Metrics gain `tokens_in_preamble` / `tokens_in_net`; RUNMETA gains `warmup` and `preamble_tokens_in` | F9, F10 |
| 4 | R4 | Variants declared once in `suite.toml`, overridden per task by `id` | as written the importer would emit 90 near-identical `variants.toml` files |
| 5 | R3 | `send` split into `send_file` / `send_text` | a single key holding either a path or a prompt cannot be read unambiguously |
| 6 | §5 | `expect` gains `gate_fires_after_deny = { min, max }` | F36 — `gate_fires = { min = 2 }` was satisfied by four exploratory `bash` gates while the denial was the session's last gate, so the bound passed and the question went unanswered |
| 7 | §7 | Subject descriptor gains an optional `[delivery]` with `open` / `close` | 69 of 90 prompts are multi-line and no subject path delivered one as a turn; David's call (2026-08-08) was to fix the subject, so the format has to carry how each subject receives a block |
| 8 | §3 | `lang` gains `shell` | F47 — 8 of Q56's 56 tasks are shell, the vocabulary is closed, and a rejected task rejects the whole corpus, so those eight could not import at all. David's word, 2026-08-08 |

**All three are additive and `schema` stays `1`.** Every existing file remains valid: a descriptor
with no `[delivery]` and a variant with no `gate_fires_after_deny` load exactly as before, and no
task on disk uses `shell`. Bumping the integer would invalidate all 90 task files to express "two
optional keys and one accepted value appeared", which is the wrong trade — the amendment table is
the record of the change.

**Amendment 8 is not the bump §3 warns about.** That rule governs the `verbatim`/`rewritten`/
`synthesized` **partition list** — the field *names* — because the partition claim is only checkable
against a closed set. `lang`'s accepted *values* are a different vocabulary: widening it accepts
strictly more corpora and rejects none, so every existing task loads unchanged. The direction that
would break is an older loader reading a newer corpus, and both move together here.

Two smaller resolutions, recorded so they are not rediscovered as bugs:

- R2's tree and R4's example disagreed about where variants live. Resolved to a sibling
  `variants.toml`, because R1 says a task never varies once frozen and adding a variant must
  therefore not touch `task.toml`.
- The worked example in the research doc lists `fixture/__init__.py` for `fix_sql_inject`, carried
  over from the donor's package layout. The rewritten verifier imports flat (`from sql_inject import`),
  so v1 drops it. Recorded in that task's `rewritten` list.

## 15. The worked example

`suites/u100/tasks/fix_sql_inject/` is the reference implementation of everything above, and it is
deliberately a **quarantined** task: it exercises the disposition field, the three-point gate with a
recorded failure at point 3, and both prompt rewrites. `suites/u100/suite.toml` currently describes
the full 90-task import while the tree holds only this one task; step 2 emits the other 89.
