#!/usr/bin/env python3
"""selfhost-queue4b.py - the guard task, re-authored after MY prompt lost it.

  WHAT WENT WRONG THE FIRST TIME, AND IT WAS NOT THE MODEL. t14580's prompt
named five files: the one to edit, one to copy an idiom from, and three that
declare types it mentioned. Those five total 143,927 BYTES against a 40,960
token window. Recon read 160,802 bytes back in 13 `read_file` calls, the server
CUT 9 of the 18 prompts (at least 26,752 tokens gone at the worst of them, HTTP
200 every time), the reasoning trace grew to 88% of the composition, and Recon
then finished cleanly having emitted 95 tokens, 90 of them reasoning. Change
never ran. `SaidNothing`, and structural refused an empty tree.

  THE ONE CHANGE HERE IS THE READING LIST. Every type is quoted inline, and no
file is named except the one being edited. That is deliberate rather than
polite: W7 and F782 both measured that a prompt binds only as far as the model
complies - 39/50 at best, 1/33 at worst - so "do not read those files" is a
request, while NOT NAMING THEM removes the invitation. F781 priced the general
form of this: carrying Recon's reads costs p50 9,939 tokens against a median
headroom of 16,057, and this task's reading list was about 41,000.

  ⚠ AND THE CONTRAST IS INSIDE ONE WAVE. t14581 (`Seq::forward`) ran in the
same session, same model, same seed policy, same `--rounds 36`, same standard
paragraph, same author - one file, block quoted inline - and took 4 tool calls,
6 turns and went GREEN. n = 2, so it is an observation and not a result, but it
is the cleanest version of F774 this log has.
"""

import argparse
import importlib.util
import pathlib
import subprocess
import sys

#   `selfhost-queue4.py` is hyphenated, so it is not importable by name.
# Loading it by path keeps ONE copy of the standard paragraph and of the
# source-read-from-disk helper: a prompt that drifts from its sibling is two
# prompts pretending to be a wave.
_spec = importlib.util.spec_from_file_location(
    "queue4", pathlib.Path(__file__).with_name("selfhost-queue4.py"))
_q4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_q4)
ABCC, REPO = _q4.ABCC, _q4.REPO
REVIEW_SRC, STANDARD = _q4.REVIEW_SRC, _q4.STANDARD

GUARD2 = f"""In crates/abcc/src/ops.rs, make `abcc review` refuse a change the \
log does not know about.

EVERYTHING YOU NEED IS QUOTED IN THIS PROMPT. An earlier attempt at this task \
went looking for the files these types are declared in, read 160 KB of source, \
and ran out of context before it wrote anything. Nothing below needs to be \
looked up.

Today `review` appends whatever string it is handed, so a review can name an \
attempt id or an abbreviated sha and the ladder's two halves silently fail to \
join. That is not hypothetical: the live log has four landings, four reviews, \
and zero pairs that join.

The function, which is the only thing you need to change:

{REVIEW_SRC}

Before it appends anything, it must resolve `change` against the changes the \
log says were landed:

  * collect every `change_landed` event's `change`, which is a full \
40-character commit sha;
  * if the argument matches one of them exactly, use it;
  * if the argument is a prefix of exactly one of them, use that full sha;
  * if the argument names a task that was landed, written either `t14016` or \
`14016`, use that landing's sha;
  * otherwise return `AppError::Refused` with a sentence saying the log holds \
no such landed change, and append NOTHING.

The event must always be written with the FULL sha, never the abbreviation the \
operator typed, because the two halves of the ladder are compared as strings \
and two spellings of one commit are two rows.

Reading the log from inside this function is two lines:

    let log = crate::fun::read_all(&store)?;
    let replay = Replay::over(&log);

`Replay` needs one new import, `use abcc_core::replay::Replay;`. Then \
`replay.ladder.landings` is a `Vec<Landed>`, and this is the whole of that \
type:

    pub struct Landed {{
        pub change: String,   // the FULL 40-character sha `abcc land` made
        pub task: TaskId,
        pub attempt: AttemptId,
        pub from: String,
        pub to: String,
        pub rungs: usize,
        pub seq: Seq,
        pub at_ms: i64,
    }}

`TaskId` and `Seq` are already imported in this file. `TaskId` is `Copy`, it \
compares with `==`, and `TaskId::at(Seq::new(n))` builds one from a number - \
this same file already does exactly that, a few functions further down, where \
`accept` and `reject` turn a task argument into an id. `AppError::Refused` \
takes a `String` and this file already returns it in several places.

A review may NOT name a change that `abcc land` did not make. That is a ruling \
rather than a preference: the ladder is "of the changes abcc landed" and never \
"of the repository", so a commit merged by hand is deliberately outside it.

Add tests, and they must cover the REFUSAL as well as the resolution - a guard \
whose refusal has no test is a guard nobody has run.{STANDARD}"""

TITLE = "review resolves its argument or refuses (wave 4b, inlined)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.dry_run:
        print(GUARD2)
        print()
        print(f"--- {len(GUARD2)} chars, roughly {len(GUARD2) // 4} tokens ---")
        return 0
    r = subprocess.run([ABCC, "task", GUARD2, "--title", TITLE],
                       cwd=REPO, capture_output=True, text=True, errors="replace")
    print(r.stdout.strip() or r.stderr.strip())
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
