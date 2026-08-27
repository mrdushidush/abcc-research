# W13 deliverable 2 — the proposed CLAUDE.md skeleton

Second half of W13's deliverable (`RESEARCH_BRIEF.md:1001`). The reasoning is in
`research/W13-codev.md`; this file is the artifact. **68 lines of skeleton**, against v1's 582 and
BCF's 388 — and the size is the point, not an accident: F425 measured 31% and 39% of those two
files sitting under headings the current guidance names on its exclude list
(<https://code.claude.com/docs/en/best-practices>, retrieved 2026-08-27).

`«angle brackets»` mark values Phase 2 fills in when the repository exists. Numbers shown are
Claudette's measured ladder (F427) and are placeholders for 2.0's own, taken the same way — warm,
on the named machine, with exit status asserted.

```markdown
# ABCC 2.0 — agent context

Rust workspace. RTS-framed agent command center: the operator runs a fleet of local model
workers against real repository tasks. Read `README.md` for what it is; this file is how to
work in it.

## Commands

The loop ladder, measured warm on «machine». Use the cheapest rung that answers the question.

| when | command | ~time |
|---|---|---|
| after every edit | `cargo check --workspace --all-targets` | 0.5 s |
| before proposing a change | `cargo clippy --all-targets -- -D warnings && cargo test --lib` | 12 s |
| once, before commit | `cargo test --workspace` | 47 s when test binaries relink |

Never run the full workspace suite in the edit loop — it is ~113× the inner loop and tells you
nothing `cargo check` did not. Run a single test by name (`cargo test <name>`) over a whole
module when you are iterating on one failure.

Formatting and the toolchain are pinned in `rust-toolchain.toml`. If `cargo fmt --all --check`
disagrees with CI, that is a bug in the pin — report it, do not reformat around it.

## Environment

- «required env vars, and which are needed only for the model-serving path»
- The model server is not started by the test suite. Tests that need one are `#[ignore]`d and
  named `*_live_*`; run them with `--ignored` after starting «serving command».
- `target/` is large (tens of GB). Do not clean it to free space without asking.

## Style rules that differ from defaults

- «RTS domain vocabulary is settled in W3 and is load-bearing: the type names are the game's
  words, not the framework's. Do not "correct" them toward functional naming.»
- Errors are typed per crate and never `anyhow` across a public boundary.
- «one or two more, added only when a real mistake happens twice»

## Architecture you cannot infer from one file

- A model verdict is a **report, never a gate**. Anything that reads like a review pass may
  annotate a task; only the deterministic gate changes its state.
- Task state transitions are append-only events in the durable log. Never mutate a task's state
  in place — emit the event and let the reducer move it.
- The isolation boundary is the tool child process, not the agent. A tool that spawns a shell
  is in the same class as one that runs code, regardless of its argument surface.

## Repository etiquette

- Conventional Commits. One logical change per commit.
- Work happens in a worktree, one per task. Never edit the operator's checkout directly.
- Agent-authored commits carry `Co-authored-by:` so authorship stays countable after squash.
- ADRs in `research/decisions/` are **append-only**. When reality diverges from an ADR, write a
  new one that supersedes it. Never edit an ADR to match what shipped.
- `plans/<campaign>/<task>.md` is written before the work, not after.

## CI

Eight jobs. Seven gate; `coverage` is `continue-on-error` and is the only advisory signal.
A red `coverage` is not a reason to stop. Any other red job is.

## What you cannot do, and why it is not a list here

Capabilities are removed, not requested. If an action is not available to your role, the tool
is absent from your set or the permission tier refuses it — there is no honour-system list of
forbidden commands in this file, because a sentence binds only as far as the model complies.

If you believe you need a capability you do not have, say so and stop. Do not route around it
with a different tool.
```

## What is deliberately absent, and which finding says so

| left out | why |
|---|---|
| Roadmap / phase status | F425 — v1 carries 103 lines of it, still marked "COMPLETED Feb 2026", in a file loaded every turn. Lives in `plans/`. |
| Benchmark results, model comparisons | F425 — 39% of BCF's file. Lives in `research/`; a number in an always-loaded file is a number that goes stale silently. |
| Module map / package structure | F425 and the guidance's *"File-by-file descriptions of the codebase"*. An agent reads the code faster than it reads a stale map. |
| A "never run X" denial list | F426 + W7's ruling. v1's `CLAUDETTE.md` is the best-written such list in the family and names two commands (`git clean`, `git stash drop`) the shipped guard does not catch. The content becomes `max_tier`; only the *pointer* stays. |
| A second `.claude.md`-style document | F424 — v1's is 500 lines, six months stale, and never loaded, because a leading dot makes it a different filename. |
| Anything only sometimes relevant | Guidance: use on-demand skills in `.claude/skills/` rather than growing the always-loaded file. |

## Two things this skeleton assumes that do not exist yet

1. **`rust-toolchain.toml`** — the "Formatting" paragraph makes a promise F430 shows the donors
   cannot keep. It is safe to write only because recommendation 3 pins the toolchain first. If
   the pin slips, delete that paragraph rather than shipping the promise.
2. **Capability removal per role** — the closing section is W7's ruling stated as a fact about
   the repository. Until `max_tier` exists, that section is aspirational and should say so
   rather than implying an enforcement that is not there.

**Maintenance rule.** Treat this file like code: when the agent makes a mistake this file should
have prevented, add a line; when the agent already does something right, delete the line telling
it to. Guidance's own test for every line — *"Would removing this cause Claude to make
mistakes?"* — and the failure signal is the opposite one: if the agent ignores a rule that is
written here, the file is probably too long.
