# W8 - The Q56 import direction (donor 2)

Step 5 of the five-step W8 plan, and as of 2026-08-08 it is the **critical path** rather than the
last item: David answered F38 with *front-load donor 2*, which makes Claudette's Q56 battery the
corpus that carries operator control. This document is the survey that decides whether it can, and
the import plan that follows if it does.

Status: **survey complete, all of it measured against the donor tree rather than read off its
prose.** Findings F39-F46 below. Two things want David's word before the importer is written; both
are at the end and neither blocks starting.

> **Read `research/W8-corpus-format.md` §A first** - the `Q08` worked import is already authored
> there and approved, and this document does not repeat it. The mapping it gives (prompt, fixture,
> `verify.sh`, `refsol/` all *verbatim*; `[[turn]]` and `variants` synthesized) survives this survey
> intact.

---

## Where the donor is

Claudette repo, branch **`battery/q50-quality-corpus`** at **`43d6b34`**, path
**`runs/eval-2026-05-29/battery/`**. It is not on `main`, which carries a different, older A-K
battery. Everything below was read with `git show 43d6b34:<path>` - **nothing was merged, checked
out, or edited**, per the standing instruction.

56 tasks in `manifest-q50.tsv` (`id`, `lang`, `kind`, `fixture`, `timeout_s`):

| axis | distribution |
|---|---|
| lang | python 15, rust 14, js 10, ts 9, shell 8 |
| kind | implement-spec 18, boundary 7, bugfix 6, api-misuse 6, error-handling 5, refactor 4, perf 4, multi-file 4, concurrency 2 |
| `timeout_s` | 600 x45, 700 x7, 900 x4 |

The same directory also holds the older A-K core battery and four `T01`-`T04` tasks. **Only
`Q01`-`Q56` are in scope**; the manifest is the boundary, not the directory listing.

---

## Why this donor answers F38, and the correction that makes it true

F38 said `write_file` requires `WorkspaceWrite` and therefore "passes through silently - no gate", so
a task finishable by creating a file can never fire one. **The first half is wrong**, and it was
wrong in the flattering direction: it made the gate look narrower than it is.

**F39. `write_file` onto a path that already exists is `DangerFullAccess` and gates.** F38 was read
at `run/runtime_build.rs:471`, which does carry `with_tool_requirement("write_file", WorkspaceWrite)`
- but the tier that actually governs a call is computed in a *different file*,
`runtime/permissions.rs:236-252`, and it overrides that base:

```rust
if crate::tools::file_ops::existing_write_target(path_str).is_some() {
    PermissionMode::DangerFullAccess
} else {
    base
}
```

The comment above it names the reason (roast EDIT-04: the only tool that can replace a whole file was
the only one that never prompted). `file_ops.rs:440`,
`existing_write_target_distinguishes_create_from_overwrite`, is a unit test for exactly this.
`authorize` calls `effective_required_mode`, not `required_mode_for` (`permissions.rs:262`).

**The corrected rule is about the target, not the tool: creating a new file never gates; touching a
file that already exists gates, whichever of `write_file` / `apply_diff` / `edit_file` /
`apply_patch` the model reaches for.**

F38's *conclusion* is unaffected - the ~14-task bound on U100 follows from 76 of 90 tasks shipping an
empty fixture (F29), not from the tool - so David's decision stands on the same ground it was made
on. What changes is the **selection criterion for donor 2**, which should read *"the task must
require modifying a file that already exists"* rather than *"un-finishable by `write_file` alone"*.
The second is now false and would have excluded nothing.

> ⚠ Still to confirm by execution. Source + unit test agree, and F30 recorded a `write_file` call
> that produced a gate on `fix_sql_inject` (whose fixture ships an existing file), which is
> consistent - but that run cannot separate a `write_file` gate from a `bash` one. **A three-minute
> probe settles it and must be run before this finding is quoted**: an existing file in the work dir,
> a prompt that invites a full rewrite, `gate_fires` on the resulting cell. It is deferred only
> because the GPU is busy with the n=5 repeats and a second session against the endpoint would
> corrupt their timings.

---

## What the survey measured

**F40. Not one of the 56 tasks ships an empty fixture.** 109 fixture files across the 56, minimum 1
(seven tasks: `Q43`-`Q48`, `Q50`), mean 2. This is the precise inverse of U100, where 76 of 90 are
empty. Under F39's corrected rule **all 56 are gate-capable**, and they are gate-capable
*structurally* rather than by luck of tool choice - there is no path to a passing answer that does
not touch a file that is already there. F30's tool lottery stops being a threat to the measurement.

**F41. All 56 verifiers grade the code. None greps the transcript.** Measured across the 56 scripts:
zero uses of `_lib.sh`'s `tc` / `tcre` / `tcount` transcript helpers. Those helpers exist and are
real, but they belong to the older A-K battery that shares the directory. So Q56 carries **none** of
U100's presence-only class (24 of 90, all of which pass an empty page - F20), and the
`verifiable = "presence_only"` disposition that decision 9 had to argue over is simply not needed
here: all 56 import as `full`.

> This corrects one line of `corpus/SPEC.md` §8, which tells the harness that "transcript-reading
> verifiers are inherited from Q56 and matter." They are inherited from the *battery directory*, and
> for Q56 proper there are none. The transcript argument is still passed - the contract requires it -
> but no Q56 verifier reads it. Worth an amendment when the spec is next touched; it changes nothing
> in code.

**F42. `refsol/` coverage is 56 of 56.** 55 tasks carry one overlay file, one carries two. **Gate
point 2 is free for the entire donor, with nothing authored** - compare U100, where point 2 was free
for 49 of 90 only by exploiting F25's dictated bodies, and where SPEC §9 otherwise records
`not_run`.

**F43. The verifier contract is already SPEC §8's, because §8 was taken from here.**
`verify/_lib.sh`: `verify/<id>.sh <WORKDIR> <TRANSCRIPT>`, print exactly one
`RESULT: PASS|FAIL - ...` line, always exit 0. Two mechanical deltas and nothing else:

1. **All 56 `source "$(dirname "$0")/_lib.sh"`.** A W8 task dir is self-contained, so the importer
   inlines the used part - `WORKDIR`/`TRANSCRIPT` binding plus `pass()`/`fail()`, five lines. The
   three transcript helpers are dropped as dead by F41.
2. **Interpreters are hardcoded** - `python` x15, `pytest` x23, `node` x39, `cargo` x14 - where SPEC
   §8 requires the `${PYTHON:-python3}` form so the same task runs on the host and in a container.
   Rewritten at import, and **probed by executing**: on this host `python3` is the Store alias shim
   (F27) while `python` works, which is exactly the trap §8 was written for.

The em dash in `pass()`/`fail()` needs no handling: the parser takes the word after `RESULT:` and
treats the rest as free-text message (`verify.rs:160-173`), so `PASS - ok` parses as `PASS`.

**F44. 55 of the 56 prompts are a single line**; one carries four. So 55 cells deliver on `line`
transport and one on `sentinel`. The delivery problem that consumed sessions 6-7 - 207 of 271 U100
cells needing block delivery - is almost absent here, and `af3f804` already covers the one case.

**F45. Q56's own authoring gate is W8's gate points 1 and 2.** `gate_q50.sh` refuses a task entry to
the manifest unless untouched fixture → verify FAIL **and** fixture + refsol → verify PASS. The
import gate is therefore pre-satisfied by construction. **Re-run it anyway rather than trusting it**:
U100 scored 79 of 80 sound at point 1 and F8 still found a verifier passing an intact SQL injection.
Point 1 bounds the rate from below; it does not certify a verifier.

**F46. Two comparability deltas, to be recorded as suite caveats rather than repaired.**

- **Held constants differ.** Every published Q56 row ran at ctx **32768**, KV `q8_0`, one parallel
  session, full offload. W8 runs at **61440** (David's daily driver, F31's `Held::default`). The 36
  recorded runs in `RESULTS-q56.csv` are therefore imported baselines whose comparability must be
  argued, not assumed - the same accepted cost as U100's 7 runs, with a sharper cause.
- **Contamination date 2026-07-25.** The corpus - fixtures, hidden verifiers *and* reference
  solutions - has been publicly cloneable since then, and the donor's own README says any model
  released after that date must be treated as potentially contaminated on these 56 tasks. **Whether
  the champion falls after that line decides whether every W8 number on this suite carries the
  caveat.** See the open questions.

---

## What hand-authoring the worked example found

`Q08` was imported by hand into `corpus/suites/q56/tasks/Q08/` plus a `q56/suite.toml`, exactly as
`fix_sql_inject` was for U100, and validated against the frozen SPEC before a line of importer Rust
was written. Both validators **ACCEPT** it - `validate.py` and the compiled `w8-corpus` loader - with
all four variants merging onto the task from the suite. Two things surfaced that a reading of the
donor could not have.

**F47. `lang = "shell"` is not in SPEC §3's vocabulary, and eight Q56 tasks are shell.** The
vocabulary is `python | node | rust | go | typescript | html | mixed`, and it is **closed in the
loader** (`w8-corpus/src/model.rs:37-40`, `vocab!(Lang {...})`), so a shell task is a load rejection
and a rejected task rejects the whole corpus. The other four map cleanly: `python`→`python`,
`rust`→`rust`, `js`→`node`, `ts`→`typescript`.

**This needs a one-word SPEC amendment - add `shell` - and that is David's call, not the importer's.**
The alternative, mapping shell onto `mixed`, is available and wrong: `mixed` describes a task with
several languages, and labelling 8 single-language tasks with it to dodge an amendment would put a
false value in a field the corpus is meant to make checkable. Nothing else in the import is blocked
by this; the other 48 tasks can land first.

**F48. A half-imported suite is not inert - it stops the whole corpus loading, and then it stops the
runner.** Two separate traps, both hit within a minute of each other while five measured
repetitions were in flight:

1. `expected_tasks = 56` beside one task directory is a **load rejection**
   (`w8-corpus/src/lib.rs:168-176`), and a rejection anywhere rejects the corpus - so a placeholder
   in the new suite would have aborted the runs measuring the *old* one. The key is therefore
   deliberately absent from `q56/suite.toml` until the importer emits all 56, with a comment saying
   why. **The guard is real, so it must not be armed against a state it is designed to reject.**
2. **A second suite makes `--suite` mandatory** (`w8-run/src/main.rs:174-183`), and any script that
   omitted it - including the repeat loop - starts failing the moment the new suite appears.

Neither is a defect; both are guards behaving correctly. But they mean **the q56 tree cannot live
under `corpus/` while runs are in flight against u100**, which is a sequencing constraint on the
import rather than a design question. It was staged outside the corpus for the duration, and the five
repetitions therefore ran against a byte-identical corpus - which is the point of running them.

---

## The import plan

`w8-import` gains a second donor direction. It is the easy one: extraction is a file copy, and four
of the six task fields are verbatim.

| W8 task file | Q56 source | transform |
|---|---|---|
| `task.toml` `id`,`lang`,`kind`,`timeout_s` | the `manifest-q50.tsv` row | verbatim |
| `prompt.txt` | `prompts/Q<nn>.txt` | verbatim (F44: one line, 55 of 56) |
| `fixture/` | `fixtures/Q<nn>/` | verbatim (F40: never empty) |
| `verify.sh` | `verify/Q<nn>.sh` | `_lib.sh` inlined, interpreters made overridable (F43) |
| `refsol/` | `refsol/Q<nn>/` | verbatim (F42: 56 of 56) |
| `[[turn]]` | the single `claudette "<prompt>"` call | synthesized: one-turn session |
| `variants` | none | synthesized in `suite.toml` - `control`, `gated`, `redirect-first-edit`, `deny-first-edit` |
| `disposition` | - | `verifiable = "full"`, `quarantine = "none"` for all 56 pending the gate |
| `sham/` | none | absent at import; step 4's question, not step 5's |

Four notes that will otherwise be rediscovered the hard way:

- **The variant set can be the full four on every task**, which is what F40 buys and what U100 could
  only give on ~14. `deny-first-edit` copies `fix_sql_inject`'s re-authored template - matcher
  `{ gate = {} }`, `gate_fires = { min = 1 }`, `gate_fires_after_deny` deliberately unbounded (F30,
  F36). Do not re-derive it; do not scope the matcher to a tool.
- **Rust fixtures carry an empty `[workspace]` table on purpose** - without it the parent repo's
  workspace captures the fixture and `cargo test` errors out. The copy must preserve it verbatim, and
  a work dir under `runs/` is safe today only because ABCC's root has no `Cargo.toml` (the workspace
  is in `harness/`). Worth an assertion rather than an assumption.
- **Toolchain scope is rust / python / js / ts / shell**, all five needed. A missing toolchain does
  not skip its tasks in the donor harness - it fails them. Under SPEC §8 the same thing must read as
  **INVALID, not FAIL** (F35), so the importer's probe has to cover `cargo`, `python`, `pytest` and
  `node` by executing each one.
- **Line endings.** Check before diffing anything. Four separate findings so far have been a CRLF
  artefact wearing a real difference's clothes (F21, F22, F29, and the `main.rs` normalisation).

---

## Three things for David, one of which gates 8 of the 56

1. **SPEC amendment: add `shell` to §3's `lang` vocabulary** (F47). One word, and without it the 8
   shell tasks cannot be imported at all - they are a load rejection, and a rejected task rejects the
   corpus. The other 48 do not wait on it. Mapping them to `mixed` instead is possible and is not
   recommended: it would put a value in the field that is not true.
2. **The champion's release date against the 2026-07-25 contamination line.** If
   `qwen3.6-35b-a3b-mtp@iq3_s` was released after it, every Q56 number W8 produces carries a
   contamination caveat and the suite-level record has to say so. This does not stop the import - it
   decides one caveat line and how the first numbers may be quoted.
3. **Confirmation that reading blobs out of `43d6b34` is the sanctioned route.** The standing
   instruction was that David says where Q56 lives, and not to propose merging the branch or editing
   Claudette's README. Reading with `git show` touches nothing and is what this survey did; the
   importer would do the same. Say if it should instead read from a copy, or from the public clone.
