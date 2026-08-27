# The 40-task battery: imported, and run twice against the champion

**What this is.** A §16 acceptance record, not a workstream document. The brief's acceptance criteria
name ABCC's 40-task corpus; the set had never been imported (`corpus/suites/` held `k`, `q56` and
`u100`) and `prestudy/data-assets.md:23` marks it *"Saturated"*. **David ruled on 2026-08-26: import
it and run it once**, closing the criterion honestly rather than by argument.

**What it found.** The import corrected the baseline it was supposed to be measured against, and the
run did not measure what it was aimed at. Over **two repeats, 80 cells**: the subject put its artifact
in the directory the verifier grades **exactly half the time (40 of 80)** — and **of those 40, it
passed 38 (95%)**. The other half is one defect wearing three hats: the subject hands `write_file` an
absolute path with the work-dir component missing, `write_file` correctly refuses, and the subject
routes around the refusal with `bash`, which has no path gate at all. **Placement is a per-attempt
coin flip, not a property of the task** — 20 of 40 tasks landed differently in the two repeats.

Instrument: `harness/crates/w8-import-u40` (importer, README beside it) → `corpus/suites/u40/` →
`w8-run`. Findings **F400–F403**; next free finding **F404**.

---

## The import, and the four things it found before emitting anything

`w8-import-u40` is the third importer and the smallest — the donor is one flat
`const TASKS = [ … ]` of 40 objects with five string keys each, so the 100-task byte-walker is not
reused. It keeps the three rules the other two established (never drop a task, never overwrite an
authored file, read the donor through `git show`). The mechanics are in its README; what belongs
here is what reading the donor changed.

### 🚨 F400 — the recorded 39/40 is an after-retry number, and the single-attempt floor is 36/40

`ollama-stress-results-40.json` is committed five times. Each row is the same 40 tasks:

| commit | date | configuration | passed | failures |
|---|---|---|---|---|
| `159512f` | 2026-02-05 | `qwen2.5-coder:7b` | 35/40 | reverse_string, **flatten_list**, truncate, run_length_encode, sorted_linked_list |
| `27018b1` | 2026-02-17 | `qwen2.5-coder:32k` | 36/40 | greet, **flatten_list**, truncate, text_stats |
| `f32b1ff` | 2026-02-17 | dynamic 8K/16K/32K | 36/40 | the same four |
| `6c6bb86` | 2026-02-18 | dynamic 8K/16K/32K | 36/40 | the same four |
| `01246c1` | 2026-02-20 | dynamic **+ auto-retry pipeline** | **39/40** | **flatten_list** |

🚨 **`01246c1` is the commit that *added* the retry pipeline.** Its own message reads *"auto-retry
pipeline — 90% → 98% pass rate (39/40)"* and describes phase 0 validate → phase 1 Ollama retry with
the error in context → **phase 2 Haiku escalation**. So 39/40 is a *system* score with a cloud model
as its top rung, and **zero cloud spend (David, 2026-08-07) means it is not a number 2.0 can be
compared against at all.** The single-attempt figure is **36/40 = 90%**, stable across three runs and
two configurations.

⚠ **This is the number the §16 criterion has to be read against, and the handoff carried the other
one.** Quoting 39/40 as "v1's result" attributes an escalation ladder's work to the base agent.

🚨 **One task has never passed in any recorded configuration.** `flatten_list` (`c5_flatten`) is a
failure in all five runs, including the one with the retry pipeline and Haiku in front of it. Its
gate point 2 **passes** in this import — the verifier accepts the donor's own reference solution —
so the task is solvable and v1's stack never solved it. Any reading of 36/40 or 39/40 as "the
model's ceiling" is reading a corpus with a member nothing has ever solved.

### 🚨 F401 — the prompt the model saw was `description`, not the `fullDescription` that contains the answer

`createTask` (`ollama-stress-test-40.js:372-380`) builds a `fullDescription` that interpolates
`task.code` — **the reference solution** — into the prompt text, and posts it to the task DB record.
It never reaches the model: `executeTask(:412)` sends `task.description`, and the agents service uses
`request.task_description` verbatim (`packages/agents/src/main.py:325`).

**The proof is independent of both call sites.** `fullDescription` names `tasks/c{complexity}_{name}.py`,
while `description` and `validation` agree on a different stem in **17 of 40 tasks** — `c9_stack_class`
against `tasks.c9_stack`, `c5_fizzbuzz_single` against `tasks.c5_fizzbuzz`, and fifteen more. A run
driven by `fullDescription` would have written a file the verifier never imports and failed at least
those 17. It failed one. **So the importer emits `description`, verbatim, and the reference solution
goes to `refsol/` where the loader never hands out its path.**

Two smaller facts that make the import quotable: the `TASKS` array is **byte-identical** at
`01246c1^`, at `01246c1` and at HEAD `d5528ea` (the only later change base64s the validation string
on its way into `docker exec`), so the tasks imported are the tasks that ran; and the donor's
`resetSystem(:362)` runs `touch /app/workspace/tasks/__init__.py` once per campaign, which is where
this suite's per-task fixture comes from — the shared cumulative workspace is the comparability break
worth knowing about, not a missing `BUGGY_FILES` map.

### The emitted suite

40 tasks, `python`, `timeout_s = 300` (the donor's global `TASK_TIMEOUT_MS`), one `control` variant at
`mode = "allow"` (donor-faithful: v1's `file_write` had no prompt in front of it). `w8-corpus` prints
**ACCEPTED**; the aggregate denominator is 40.

**The gate is stronger than either existing suite's.** SPEC §9 has three points and this suite answers
two, where u100 answered one:

| point | what it asks | u40 | u100 |
|---|---|---|---|
| 1 | rejects a non-answer — *absence* **and** a null-implementation stub | **sound 40/40** | sound |
| 2 | accepts a correct answer — the donor's own `code` | **sound 40/40** | `not_run` (no refsol exists) |
| 3 | rejects a plausible wrong answer | `not_run` — no sham for this donor | 30 tasks |

---

## The run

Held constants as every other campaign: subject `claudette-af3f804` (`--bin` pinned explicitly),
model `qwen3.6-35b-a3b-mtp@iq3_s` at `-c 65536 --gpu max --parallel 1`, `CLAUDETTE_NUM_CTX=61440`,
`num_predict 8192`, `max_iterations 40`, `--delivery verbatim`, LM Studio proxy on `:1234`.
**Run twice**, back to back on one model load — `runs/u40-r1/` and `runs/u40-r2/`.
⚠ **Both LM Studio anti-spill guardrails were OFF and the load had 0.30 GB of margin** — the joint
tightest of five recorded loads. That is a throughput risk, not a correctness one, and every number
below is pass/fail or an iteration count.

### 🚨 F402 — 38 of 80, and 38 of the 40 non-passes never delivered a file to the graded directory

**Two repeats, 80 cells, identical held constants**, because n = 1 per task reports either extreme as
fact — the K-series learned that the expensive way (F87–F92), and it is exactly what would have
happened here: **r1 scored 21/40, r2 scored 17/40.** Pooled: **38 pass · 41 fail · 1 timeout**, a raw
47.5%, against v1's 36/40 single-attempt floor.

**It is not a coding result.** Cross-tabbing every cell's outcome against *where the artifact actually
landed* separates it completely:

| where the artifact landed | cells | pass | fail | timeout |
|---|---|---|---|---|
| **in the work dir**, `wd/tasks/<id>.py` — what the prompt asked for | **40** | **38** | 2 | 0 |
| **one level up**, in the cell directory, written by `bash` | 30 | 0 | 29 | 1 |
| **somewhere else entirely** — the scratch sandbox, or nowhere at all | 10 | 0 | 10 | 0 |

🚨 **Every one of the 40 out-of-place cells failed with `ModuleNotFoundError`. Exactly two cells
failed on their code**, and both are real defects rather than near-misses: `c6_second_largest` calls
`unique.pop()` on a *set* and calls the result "remove the largest"; `c7_group_by` emits a
**`SyntaxError`** — an unexpected character after a line continuation, on line 7 of a file it
reported as finished.

**So: the subject delivered to the graded directory in exactly half of its attempts, and when it
delivered it was right 38 times in 40 (95%).**

🚨 **And placement is a per-attempt coin flip, not a property of the task.** Only **20 of 40 tasks
landed in the same place in both repeats**; the other 20 flipped. The outcome column flips with it —
11 tasks went pass → fail and 7 went fail → pass between the two runs. **A single repeat of this
suite is not a measurement of anything**, and a per-task verdict from one run would have been noise
in both directions.

The same instability rescues the comparison that mattered: **on every attempt where one of the four
tasks v1's single-attempt run failed was actually delivered — 6 of their 8 attempts — the champion
passed.** That includes both attempts at `c5_flatten`, which is `flatten_list`, the task that failed
in all five recorded donor runs including with Haiku escalation.

Two of the wrong destinations are worth naming separately, because they are different defects.
`c1_negate` wrote to `~/.claudette/files/tasks/c1_negate.py` and **printed that absolute path in its
answer** — it did not think it had failed; it believed the scratch dir was where files go, which is
exactly what the tool self-description told it (below). At least **five distinct artifacts** ended up
there across the two runs. `c3_max_of_two` wrote *"Done — created `tasks/c3_max_of_two.py`"* and **no
such file exists anywhere on this host** — a report of its own success that is simply false.

⚠ **The scratch sandbox is shared across cells and across runs**, so an artifact written there
outlives the cell that made it and is readable by every later one. Per-task isolation is a property
of the work dir only; it does not survive a write that leaves it. `~/.claudette/files/tasks/` held
five u40 artifacts when these two runs finished, and a third run would start with them in place.

### 🚨 F403 — the write sandbox is enforced on `write_file` and not on `bash`, so a refusal is a detour sign

The mechanism is in the subject's own session record (`~/.claudette/sessions/last.json`), not inferred:

1. The model calls `write_file` with `path = "D:\…\cells\c7_word_freq__control\tasks/c7_word_freq.py"`
   — an absolute path with the **`wd` component dropped**. The system prompt does carry
   `Working directory: …\wd`: `build_environment_block()` formats it at `prompt.rs:302` and
   `prompt.rs:138` appends it unconditionally, and it needs no git repository to be built. **So this
   is the model's path arithmetic, not a missing fact.**
2. `write_file` **refuses**, correctly: `CLAUDETTE_WORKSPACE` is pinned to the work dir and
   `validate_write_path` (`tools.rs:1027-1038`) enforces it. The refusal text names
   `~/.claudette/files` as the sandbox — the scratch dir, **not** the workspace that is actually in
   force, which is the same root `get_capabilities` advertises unconditionally (`tools.rs:408-411`).
   **The subject's self-description disagrees with its own enforcement.**
3. The model then calls **`bash`** — `mkdir -p "D:\…\c7_word_freq__control\tasks"`, then a PowerShell
   here-string into `Set-Content` — and writes the file outside the workspace. It succeeds.

`tools.rs:1013` says this out loud in a comment about the mission-tree branch: *"tree is theatre —
bash/edit_file already let the brain mutate it."* **So the defect is known; what is new here is the
rate.** Unprompted, on trivial greenfield tasks, **30 of 80 attempts took the detour**, and ten
more wrote somewhere else again.

🚨 **And the mis-advertised root is not a cosmetic complaint — one cell followed it.** `c1_negate`
wrote to `~/.claudette/files/tasks/c1_negate.py`, the exact directory both the refusal text and
`get_capabilities` name as *the* write sandbox, and reported that path as its answer. The subject
told the model where writes go, the model complied, and it was then graded on a directory nobody had
told it about. **That cell is not a model error; it is the subject's self-description being wrong and
the model being obedient.**

⚠ **This is a property of `allow` mode, which is the donor-faithful variant.** `bash` is gated by
*permission mode*, not by path: under `workspace_write` with a prompter, the `mkdir` would fire a
gate an operator could deny. The control variant pins `CLAUDETTE_AUTO_APPROVE=1`, so every detour was
auto-approved. **The suite cannot measure that difference** — all 40 tasks create a file that does not
exist, so a `gated` variant would be measuring the gate rather than the task (F39, F40).

**The detour is expensive as well as wrong:**

| cells | n | median iterations | median wall clock | median tokens out |
|---|---|---|---|---|
| landed in the work dir | 40 | 4.0 | 8.5 s | 612 |
| landed one level up, via `bash` | 30 | **6.0** | **20.0 s** | **1,227** |
| landed somewhere else | 10 | 3.0 | 10.2 s | 609 |

The third row is the tell: cells that wrote to the scratch sandbox were **cheap**, because nothing
refused them — they cost what a correct cell costs and delivered nothing. It is the `bash` detour,
the one that follows a refusal, that costs 2–3×. Worst cases: `c8_rle` spent **41 iterations, 208 s
and 11,962 output tokens** and still wrote to the wrong place; `c8_binary_search` hit the 300 s
ceiling. **The model does not fail fast when the sandbox refuses it — it works harder, in the wrong
direction.**

⚠ **u100 never exposed this**, because its importer flattens every donor path to a basename: a
single-component relative path resolves inside the work dir and the refusal never fires. **This suite
is the first one in the corpus whose prompts name a subdirectory**, and that one difference is what
made a known-in-comment defect measurable.

---

## What the criterion can and cannot claim

**Can:** the 40-task corpus is imported, gate-checked on two of three points, and run **twice** against
the champion under recorded held constants — David asked for one run; the second exists because the
first produced a per-task verdict that turned out to be a coin flip. Both are on disk, at
`runs/u40-r1/` and `runs/u40-r2/`, and the honest v1 floor
it is read against is **36/40, not 39/40** (F400).

**Cannot:** *"the new base agent clears v1's floor."* The literal comparison is 38/80 against 36/40,
and it is dominated by a tool-surface interaction rather than by coding ability. The nearest defensible
statement is narrower and worth more:

> Across two runs of all 40 tasks, the subject delivered its artifact to the directory the verifier
> grades in **40 of 80 attempts, and passed 38 of those 40**. Every one of the four tasks v1's
> single-attempt run failed passed here whenever it was delivered — including one v1 never passed in
> any of five recorded configurations. On the other half of the attempts it wrote a correct-looking
> file into the wrong directory, or nowhere. **Which half an attempt falls into is a coin flip: 20 of
> 40 tasks landed differently in the two runs.**

**The criterion is therefore closed by a documented run plus a named defect, not by a pass count**,
and the defect is squarely W7's: a write sandbox that one unsandboxed tool makes advisory, plus a
self-description that names the wrong root.

## Handoff

- **To W7 (security and sandboxing, the next workstream).** Three inputs, all measured rather than
  argued: `bash` has no path gate and is the escape hatch for every path-sandboxed tool (F403); the
  sandbox root the subject *reports* is not the one it *enforces*; and a refusal that does not
  terminate the attempt costs 2–3× the work while the model hunts for a way around it. The design
  question W7 owns: **is the boundary a path check per tool, or a process the tool child runs
  inside?** W3 already handed W7 the tool child as *the* isolation boundary; this run is the
  measurement that says a per-tool path check alone is not one.
- **To the SUMMARY.md gate.** The §16 line for this criterion is the block-quote above, plus F400's
  correction to the baseline.
- **Not a W4 input.** Nothing here changes routing: the failures are not a difficulty signal, and
  F385's ceiling argument is untouched.

## Open questions

- ~~**OQ-U40-1.** Is the placement failure stable per task or a per-attempt coin flip?~~ **ANSWERED by
  the second repeat: a coin flip.** 20 of 40 tasks placed differently across the two runs, and the
  outcome column flipped with them (11 pass→fail, 7 fail→pass). What is left open is the *rate's*
  precision — 40 of 80 is ± about 11 points at 95%, so this document reports "about half" and not a
  figure to two significant digits.
- **OQ-U40-2.** Does the detour still happen when the prompt names a bare filename? u100's evidence
  says no, but u100 never had a subdirectory to get wrong, so the two suites differ in more than one
  way. One arm of 40 with flattened paths would answer it — **do not run it as a substitute for this
  suite**, whose whole donor-faithfulness is the `tasks/` prefix.
- **OQ-U40-3.** Under `workspace_write` with a live prompter, does the operator actually see the
  `mkdir` gate in time to redirect? That is W7's question and Q56's instrument, not this suite's.
