#!/usr/bin/env python3
r"""selfhost-queue3.py - wave 3, and the queue tool is Python this time.

  THE LANGUAGE IS THE FIRST FIX. Wave 2 was authored in PowerShell and it
mangled the third prompt: `abcc` printed its usage and the task was never
created, while the byte-identical string handed to `abcc` through
`subprocess.run` with no shell in the way was accepted immediately (t13606).
A shell between you and a 2,000-character argument is a suspect, and every
other tool in research/tools is already Python.

  WAVE 3 IS TWO TASKS AND BOTH ARE REPAIRS OF SOMETHING I GOT WRONG.

1. `Outcome::is_unmeasured` - wave 2's only loss (t13603). It made the edit,
   and `clippy::manual_string_new` refused it: three `"".into()` in the test it
   wrote, wanting `String::new()`. Wave 2 proved the shape of the repair -
   t13606 went green after the prompt quoted the exact lint form wave 1 had
   refused on - so this prompt quotes this one.

2. `abcc --version`, SPLIT. Wave 1's version named four seams across three
   files and overflowed the context at 40,828 of 40,960. That was the prompt's
   defect and the repair is decomposition, not more instruction: this task is
   `cli.rs` ONLY. It compiles and is testable on its own, because the two
   downstream matches (`AppError::exit_code`'s `_ => 1` and `main`'s `Err(e)`)
   both have catch-all arms. ⚠ THAT IS ALSO WHY A SECOND TASK IS NEEDED - the
   catch-alls mean a half-done flag exits 1 and prints to stderr while every
   rung stays green. The second half is NOT queued here: it has to be written
   against the tree the first half lands on.

Read-only with respect to the repository and the GPU: it creates tasks and
nothing else. It never runs an attempt, never lands and never reviews.

Usage:
    selfhost-queue3.py [--dry-run]
"""

import argparse
import pathlib
import subprocess
import sys

REPO = pathlib.Path(r"D:\dev\abcc")
EXE = REPO / "target" / "release" / "abcc.exe"
WRITTEN_AGAINST = "a0054e7"

# Appended to every prompt. The standard is named because ten of the twenty
# refusals on this log are one rung from landing and ALL TEN refused at
# `standard`. ⚠ F791: `diagnostics` takes a selector it cannot honour - a path
# becomes a positional argument and `cargo check` has none - so the prompt says
# to call it with NO arguments until that is fixed.
STANDARD = """

Before you report done, check your own work with the `diagnostics` tool, and call
it with no arguments. It runs the same commands the gate grades you with:
`cargo check --all-targets`, then `cargo fmt --check`, then
`cargo clippy --all-targets -- -D warnings`. This workspace denies `clippy::all`
and warns `clippy::pedantic`, and the gate passes `-D warnings`, so a pedantic
lint fails the run. Fix what the tool reports before you report done.
"""

TASKS = [
    (
        "Outcome::is_unmeasured (wave 3, lint named)",
        """In crates/abcc-core/src/outcome.rs, add a method `Outcome::is_unmeasured(&self) -> bool` to the existing `impl Outcome` block, after `is_red` and before `rung`. It answers whether this outcome is the `Outcome::Unmeasured` variant - the state `is_green` and `is_red` both deliberately return false for. Give it a doc comment in the house style, and add a test.

Here is the impl block as it stands, so you do not need to read the file to place the method:

```rust
impl Outcome {
    /// Green means: a measurement exists, and it says nothing failed.
    #[must_use]
    pub fn is_green(&self) -> bool {
        match self {
            Outcome::Measured(m) => m.exit == 0,
            Outcome::Unmeasured { .. } => false,
        }
    }

    /// Red means: a measurement exists, and it says something failed.
    #[must_use]
    pub fn is_red(&self) -> bool {
        match self {
            Outcome::Measured(m) => m.exit != 0,
            Outcome::Unmeasured { .. } => false,
        }
    }

    #[must_use]
    pub fn rung(&self) -> &str {
        match self {
            Outcome::Measured(m) => &m.rung,
            Outcome::Unmeasured { rung, .. } => rung,
        }
    }
}
```

The two variants are `Outcome::Measured(Measurement)` and `Outcome::Unmeasured { rung: String, why: Why }`.

One thing about the test, which has already cost an attempt on this exact task: `cargo clippy --all-targets -- -D warnings` rejects `"".into()` for an empty String - `clippy::manual_string_new` - so write `String::new()` instead. A previous attempt used `"".into()` three times in its test and the gate refused the whole change for it.

Make the edit with apply_patch early rather than reading more of the file first. The placement above is all you need.""",
    ),
    (
        "CliError::Version, cli.rs only (wave 3)",
        """In crates/abcc/src/cli.rs only, add the `--version` flag to the argument surface. Do not change any other file in this task.

Two edits, both in cli.rs:

1. The `CliError` enum, around line 200, currently has two variants. Add a third, `Version`, beside them. It needs its own thiserror `#[error(...)]` attribute like the two above it - the crate version is available as `env!("CARGO_PKG_VERSION")`.

```rust
#[derive(Debug, Clone, PartialEq, Eq, thiserror::Error)]
pub enum CliError {
    /// `--help`, or no arguments at all. Not a failure.
    #[error("{USAGE}")]
    Help,
    #[error("{0}\\n\\n{USAGE}")]
    Usage(String),
}
```

2. `parse()`, around line 307, begins like this. Return `Err(CliError::Version)` when an argument is `--version`, beside the existing `--help` check:

```rust
pub fn parse<I: IntoIterator<Item = String>>(args: I) -> Result<Invocation, CliError> {
    let mut args: Vec<String> = args.into_iter().collect();
    if args.iter().any(|a| a == "--help" || a == "-h") {
        return Err(CliError::Help);
    }
    if args.is_empty() {
        return Err(CliError::Help);
    }
```

Add a test beside the existing `parse` tests asserting that `--version` yields `CliError::Version`.

This task deliberately stops at cli.rs. Printing the version and exiting zero is a separate change against a separate file and is not yours to make here; leave `lib.rs` and `main.rs` alone.

Two clippy lints have already refused an attempt at this flag, so avoid both: `clippy::uninlined_format_args` - put the variable inside the braces, `format!("{x}")` and not `format!("{}", x)` - and `clippy::match_same_arms`, which refuses two match arms with identical bodies, so do not give `Version` a body that duplicates `Help`'s.""",
    ),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not EXE.exists():
        sys.exit(f"no binary at {EXE} - build it from {REPO} first")
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    if head != WRITTEN_AGAINST:
        print(f"  WARNING: these prompts quote source as of {WRITTEN_AGAINST} "
              f"and HEAD is {head}.")
        print("  The embedded snippets and line numbers may be stale - a prompt that")
        print("  names a neighbour that moved is the t2598 defect again.")

    for title, body in TASKS:
        prompt = body + STANDARD
        print(f"\n{title}  ({len(prompt)} chars)")
        if args.dry_run:
            continue
        r = subprocess.run([str(EXE), "task", prompt, "--title", title],
                           cwd=REPO, capture_output=True, text=True, errors="replace")
        if r.returncode != 0:
            sys.exit(f"abcc task failed: {r.stdout}\n{r.stderr}")
        print("  " + (r.stdout or "").strip().splitlines()[0])

    print()
    print("Queued. `land` and `review` remain the operator's - `by` defaults to")
    print("operator(), so an agent running review fabricates the measurement")
    print("SELF-HOST is judged on.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
