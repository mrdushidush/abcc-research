# ADR-0024 — A repository's declared standard is a conjunction of commands, and formatting is in the cargo one

- **Status:** ✅ Accepted — **David's ruling of 2026-08-30**
- **Date:** 2026-08-30
- **Deciders:** David (add it unconditionally), Claude Code (the conjunction, the ordering, the evidence)
- **Sources:** **F555** (the finding), **F557** (the colour), F512 and F516–F518 via ADR-0017
- **Amends:** ADR-0017 — the standard rung is unchanged in *purpose* and changed in *shape*

## Context

ADR-0017 put a fourth rung on the ladder: **the standard a repository declares for itself**, spelled
for cargo as `cargo clippy --all-targets -- -D warnings` and witnessed by `clippy.toml`. Its
criterion is *a correct tree is one that could land*, and F512 is the evidence — six working
implementations by the champion, all six refused by the linter, two of them with every test passing.

**F555 is the hole that criterion still had.** A gate run reached MISSION ACCOMPLISHED on a tree
`cargo fmt --check` refuses: all four rungs green, the Judge reporting no findings, and one function
whose single-line body rustfmt reformats — verified against checkpoint `69358eda`, with the rest of
the file passing as the positive control. **rustfmt was in none of the four rungs.** The tree could
not have landed in this repository, and the gate said it could.

⚠ It is the same shape as Skeleton's run 10 failing clippy by one line. **The pattern recurred one
rung lower**, which is what makes it a decision rather than a patch.

## Decision

### 1. A declared standard is a **list** of commands, and the first refusal ends the rung

`Standard.command` becomes `Standard.commands`. A repository's declared standard is not always one
program, so the field that holds it is not always one command. The rung walks them in order and
stops at the first that refuses; an `Unmeasured` ends the walk too, and is still not a refusal.

### 2. `cargo fmt --check` is in the cargo standard, unconditionally, and runs **first**

Unconditionally rather than witnessed on `rustfmt.toml` — **`abcc` does not have one**, so a
witnessed rung would be silently off in the very repository that produced the finding, which is the
exact shape of a check that measures nothing.

First because it is cheapest: formatting is a parse and a print, clippy is a compile, and an
operator waiting on a red wants the fast one to say so.

### 3. The rung says which command, both ways

* **A red names the command that refused.** `standard: exit 1` with clippy's name nowhere near it
  sends a reader to the compiler for a formatting refusal — F555 read backwards, and the same class
  as F492's *a non-zero exit from the wrong program looks exactly like the right one failing*.
* **A green names every command it passed.** The green is the sentence F555 caught lying, so it
  stands on named evidence rather than on a word.

### 4. 🚨 F557 — `--color=never`, and it is measured rather than tidy

**rustfmt colours its diff even when stdout is a plain file rather than a terminal.** Measured by
redirecting to a file and counting `ESC`: 5 lines carrying escapes on the one-line-body fixture,
zero with `--color=never`. That output is the evidence ADR-0019 keeps, so it is written to a durable
SQLite log and re-rendered in the TUI, and control characters in a durable log are a defect.

The command is `cargo fmt --check -- --color=never`. ⚠ **Clippy is left alone** — changing what it
prints is not what was ruled.

## Consequences

- **The gate accepts less than it did.** A tree that is correct, tested and lint-clean but
  unformatted is now refused. That is the point: ADR-0017's criterion is *could it land*, and here it
  could not.
- **Python is unaffected.** Its profile still declares no standard, for ADR-0017's reason — ruff,
  flake8, pylint and mypy are four opinions and choosing one is this tool having an opinion about
  somebody else's repository.
- **A cargo project without `clippy.toml` still has three rungs.** The witness governs the rung, and
  formatting joins the rung rather than becoming a fifth one. ⚠ This is a real edge: such a project
  gets no formatting check either. It is the price of not inventing a standard nobody declared, and
  it is stated rather than hidden.
- The ladder is still **four rungs**, and `Rung::LADDER` is untouched.

## Alternatives rejected

- **Witness it on `rustfmt.toml`** — symmetrical with clippy's witness and **off in this repository**,
  which has none. A rung that cannot fire in the tree that produced the finding is not a fix.
- **A fifth rung** — the ladder's four are named in the type, the report, the log and a dozen tests,
  and *the standard a repository declares* already covers both commands. A second rung would be a
  second answer to one question.
- **Leave it out; formatting is not correctness** — true, and beside the point. The rung is a
  **mergeability** check, which ADR-0017 already argued: *a tree that fails the repository's own
  declared standard cannot land there, whether or not it is correct.*

## What would falsify this

**The formatting rung refusing trees that a human reviewer would have landed** — a project whose
`rustfmt` defaults disagree with how it actually writes code, so the rung reports a fault nobody
considers one. The observable is the rung's own red rate against how often the refusal is overridden
by an operator who accepts anyway. If it fires, the answer is the witness after all, plus a
`rustfmt.toml` in this repository so that the witness is not vacuous here.
