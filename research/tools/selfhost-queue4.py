#!/usr/bin/env python3
r"""selfhost-queue4.py - wave 4: the first task real USE produced, and one re-run.

  WHY THESE TWO.
* `review` guard - F796. Four landings and four reviews on the live log and
  ZERO pairs that join, because `ops::review` appends whatever string it is
  handed. This is the first defect this project found by USING the thing rather
  than studying it, and feeding it back is the daily-driving loop closing.
* `Seq::forward` - t13055 went green at its own tree and now CONFLICTS with
  `fb15aa1`, because `t13606` took the slot it patches. Its collision is also
  GONE: `seq.rs` now HAS a `#[cfg(test)] mod tests`, so the E0428 that made
  t13055 and t13606 mutually exclusive cannot happen again.

  WHAT THESE PROMPTS DO AND DO NOT DO. They carry the surrounding source
VERBATIM and NAME THE STANDARD - the shape that went green three times in waves
2 and 3 - and they tell the model to call `diagnostics` with NO ARGUMENTS
(F791: the `selector` its schema invites is appended raw to `cargo check`, which
takes no positionals; F792: told to call it, 5 of 6 attempts did). They do NOT
contain the patch. Two levers moved at once, deliberately, so NOTHING HERE IS A
MEASUREMENT of the model against wave 1.

  ⚠ AUTHORED IN PYTHON ON PURPOSE. PowerShell mangled wave 2's third prompt and
`abcc` printed its usage; the identical string through `subprocess` was accepted.

Usage:
    selfhost-queue4.py            # create both tasks, print their ids
    selfhost-queue4.py --dry-run  # print the prompts and create nothing
"""

import argparse
import pathlib
import subprocess
import sys

REPO = r"D:\dev\abcc"
#   ABSOLUTE, and forward slashes. On Windows `subprocess` resolves the
# executable against the CALLING process's cwd, not the `cwd=` argument, so a
# relative path here is a FileNotFoundError that looks like a missing binary.
ABCC = REPO + "/target/release/abcc.exe"

#   The standard, named the same way in both prompts. F673: the model is graded
# on a criterion it cannot observe unless it runs the tool that checks it, and
# 4687405 put fmt+clippy INSIDE `diagnostics` for exactly this.
STANDARD = """
This repository grades the work with `cargo fmt --check` and then `cargo clippy \
--all-targets -- -D warnings`, and both must exit 0. `-D warnings` promotes \
clippy's pedantic lints to hard errors, so a style lint refuses the work the \
same way a type error would. Call the `diagnostics` tool before you finish, and \
call it WITH NO ARGUMENTS - it takes none that help here - because it runs the \
compiler and then both of those commands, which is exactly what you are graded \
on. Fix what it reports and call it again until it is clean."""

def block(path, first, last=None):
    r"""The source, READ FROM DISK rather than retyped.

      🚨 THE FIRST DRAFT TRANSCRIBED `impl Seq` BY HAND AND GOT A DOC
    COMMENT WRONG - `Returns true if` for `Returns true if this is`. A prompt
    that misquotes the tree teaches the model a pre-image that is not there, and
    the whole point of carrying the source verbatim is that it IS verbatim.
    Nothing here is typed twice.
    """
    text = (pathlib.Path(REPO) / path).read_text(encoding="utf-8")
    i = text.index(first)
    j = text.index(last, i) + len(last) if last else len(text)
    return text[i:j].rstrip()


#   `impl Seq` up to its closing brace, and `review` up to its own.
#   ⚠ NO BACKSLASH APPEARS ON THESE TWO LINES, and that is deliberate.
# The first version of them was written by a generator, and a backslash in
# this project's tooling gets eaten one layer at a time: memory rule 3 says
# a Windows path in a non-raw Python string is escape syntax, and here the
# GENERATOR's string ate it first, putting a BEL into the path and a real
# newline into a separator. Forward slashes and chr(10) cannot be eaten at
# any depth, so nothing here can be quietly rewritten again.
SEQ_SRC = block("crates/abcc-core/src/seq.rs", "impl Seq {", chr(10) + "}" + chr(10))
REVIEW_SRC = block("crates/abcc/src/ops.rs", "pub fn review(", chr(10) + "}" + chr(10))

GUARD = f"""In crates/abcc/src/ops.rs, make `abcc review` refuse a change the \
log does not know about.

Today it appends whatever string it is handed, so a review can name an attempt \
id or an abbreviated sha and the ladder's two halves silently fail to join. \
That is not hypothetical: on the live log there are four landings and four \
reviews and zero pairs that join.

The function as it stands:

{REVIEW_SRC}

Before it appends anything, it must resolve `change` against the changes the \
log says were landed:

  * collect every `change_landed` event's `change`, which is a full \
40-character commit sha;
  * if the argument matches one of them exactly, use it;
  * if the argument is a prefix of exactly one of them, use that full sha;
  * if the argument names a task that was landed, written either `t14016` or \
`14016`, use that landing's sha;
  * otherwise return `AppError::Refused` with a sentence saying the log has no \
such landed change, and append NOTHING.

The event must always be written with the FULL sha, never the abbreviation the \
operator typed, because `Reviewed::change` and `Landed::change` are compared as \
strings and two spellings of one commit are two rows.

This crate already reads the log this way, in crates/abcc/src/land.rs:

    let log = crate::fun::read_all(&store)?;
    let replay = Replay::over(&log);

and `replay.ladder.landings` is a `Vec<Landed>`, where `Landed` has the public \
fields `change: String`, `task: TaskId`, `attempt: AttemptId` and \
`rungs: usize`.

A review may NOT name a change that `abcc land` did not make. That is a ruling \
rather than a preference: the ladder is "of the changes abcc landed" and never \
"of the repository", so a commit merged by hand is deliberately outside it.

Add tests, and they must cover the REFUSAL as well as the resolution - a guard \
whose refusal has no test is a guard nobody has run.{STANDARD}"""

FORWARD = f"""In crates/abcc-core/src/seq.rs, add a method \
`Seq::forward(self, n: u64) -> Seq` to the existing `impl Seq` block, directly \
after `back`. It is the symmetric partner of `back`: it moves a log position \
forwards by `n` and saturates at `i64::MAX` instead of overflowing.

The block as it stands:

{SEQ_SRC}

Give it a doc comment in the house style shown above and `#[must_use]` like its \
neighbours.

Saturation is the whole of it. `Seq::new(i64::MAX).forward(1)` must be \
`Seq::new(i64::MAX)`, and an `n` larger than `i64::MAX` must saturate too \
rather than wrapping or panicking - note that `back` handles that case with \
`i64::try_from(n)` and you will need the same care in the other direction.

Add a test to the `#[cfg(test)] mod tests` that is ALREADY at the bottom of \
this file. It exists - do not add a second module.{STANDARD}"""

TASKS = [
    ("review resolves its argument or refuses (F796)", GUARD),
    ("Seq::forward saturating (wave 4, vs fb15aa1)", FORWARD),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for title, prompt in TASKS:
        if args.dry_run:
            print("=" * 78)
            print(title)
            print("=" * 78)
            print(prompt)
            print()
            continue
        #   The prompt goes as ONE argv element, straight from Python. No shell
        # is involved and none may be: see the module docstring.
        r = subprocess.run([ABCC, "task", prompt, "--title", title],
                           cwd=REPO, capture_output=True, text=True, errors="replace")
        print(f"{title}\n   {r.stdout.strip() or r.stderr.strip()}")
        if r.returncode != 0:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
