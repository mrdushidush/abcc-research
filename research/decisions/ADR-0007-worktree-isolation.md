# ADR-0007 — Isolation is a git worktree at a temp-index snapshot sha, written to a ref

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** Claude Code (W6 item 6 probes), ratified with `research/SUMMARY.md`
- **Sources:** W6 F325–F335 (probes on four real repositories, this machine) · W11 F249 (corrected)
  · W2 F83 · W5 F95, F125
- **Answers:** OQ-W3-12 (checkpoint identity) and OQ-W6-11, as a **composition** rather than a choice

## Context

Three questions were open at once — what a checkpoint *is*, how two attempts avoid each other, and
what parallel isolation costs on a 32 GB box — and the probes answered them as one mechanism.

🚨 **The marker is free and the working directory is not.** A worktree costs **0.08–0.66 s and
0.8–63.7 MB** against **6–136 s and 1.7–25.5 GB** to copy the same tree (F327). The difference is
not the mechanism, it is **what git ignores**: a worktree contains the repository and none of the
toolchain — 0.8–64 MB of tracked tree against 1.7–25.5 GB of ignored environment (F334).

Two donor facts frame the rest. **No donor ever runs two agents against one tree**, and v1's
parallel endpoint has no caller; its three file-locking surfaces all exclude the one agent that
writes code (F326). And **`git status` clean is not a claim about content**: 241 of 539 tracked
files in the v1 donor differ from their blobs while the tree reports clean, because `status` answers
from a stat cache (F328).

W11 F249 had assumed isolation costs a cold build per attempt. **Corrected (F331): 56.6 s cold,
24.7 s for a worktree created after the cache is warm, 0.4 s for one that is warm**, when
`CARGO_TARGET_DIR` is shared — and a copied tree with no `.git` gets the same.

## Decision

**A checkpoint is a commit sha produced by a temp-index snapshot and written to a ref. Isolation is
a worktree at that sha. The change list is the diff between two snapshots.**

```
GIT_INDEX_FILE=<scratch>  git read-tree HEAD
GIT_INDEX_FILE=<scratch>  git add -A
GIT_INDEX_FILE=<scratch>  git write-tree                           -> tree
GIT_INDEX_FILE=<scratch>  git commit-tree <tree> -p HEAD -m "..."  -> the identifier
                          git update-ref refs/abcc/checkpoints/<mission>/<seq> <sha>
```

Measured **0.16 s** on a 495-file tree, 0.31 s on a 1,079-file one. It touches neither the index nor
the working tree, and **it captures the files the agent created — which `git stash create` cannot**
(F329).

🚨 **The last line is not optional: an unreferenced snapshot does not survive `git gc --prune=now`**
(F330). This is the ref that makes ADR-0004's `Holding { checkpoint }` and every fork-from-checkpoint
promise real rather than aspirational.

The full cycle, measured (F330): **take 0.16 s · diff 0.024 s** (exactly the six paths the agent
touched, ignored build output excluded by construction) **· hand to an isolated attempt 0.25 s ·
restore 0.06 s**, byte-exact up to the repository's text attributes.

### The five rules that come with it

1. **One shared build directory, set per repository, never per attempt.** `CARGO_TARGET_DIR` is the
   Rust instance of a general rule: the toolchain profile gains one field — *where this toolchain's
   build cache lives*. It saves 2.90 GB per attempt and turns the first build from 57 s into 24.7 s.
2. 🚨 **Isolate the workspaces; serialize the gate.** Holding N isolated attempts is cheap; building
   two at once is not — **110.8 s against 113–135 s in sequence, and 2.3 GB of free RAM left on a
   31.9 GB box with no model loaded** (F333). The build/test rung is a **single-flight resource**
   behind a permit. W2's cap of two is about the model server, where the second sequence is worth
   +69%; at the build the second job is worth **at best a sixth** of the wall clock.
3. **Never diff a snapshot against `HEAD`** (v1's tree would report 241 phantom files, F329) **and
   never ask `git status` what changed** (F328).
4. **When the subject has no git, copy the file plan, never the directory.** 0 of this project's
   1,383-cell corpus is a git repository (F334); the destination lives **outside** the tree being
   copied, and cleanup uses the `\\?\` extended-length form, because a copy can contain a name
   Windows will not delete (F327).
5. **In a worktree `.git` is a file, not a directory.** Ask `git rev-parse --git-common-dir` and
   treat "this is a worktree" as the normal case — under this decision it *is* the normal case.
   Claudette met this and chose to degrade silently, landing its mission marker in the PR instead of
   `.git/info/exclude` (`missions.rs:428-441`).

### The restore contract, stated honestly

**Restore is exact *up to the repository's own text attributes*.** The round trip normalises line
endings the way `.gitattributes` says (219 CRLF in, 0 out, F330), and the repository with no such
rule accumulated 241 divergent files without noticing (F328). **2.0 must never claim a byte-exactness
it does not have**, and the honest claim is the one git itself makes.

## Consequences

- **The change list is the gate's free structural rung** (ADR-0008). It is the diff between two
  snapshots — 0.024 s — and `.gitignore` is the repository's own answer to *is this a source file*,
  which is the deny-list question the toolchain item left open.
- **Undo becomes a button rather than an apology.** A checkpoint sha is a save game at 0.16 s; the
  restore is 0.06 s and the operator can be shown, before pressing, exactly which paths will change.
  W5 asked for undo as a first-class verb; this is what makes it honest.
- **The FLEET milestone's RAM ceiling is a build question, not a model question.** Two cold builds
  alone leave 2.3 GB free, which is why the gate serializes and why the milestone measures with a
  real build rather than an idle probe.
- **BCF's mechanism is kept and its wiring is not** (F325): it never calls `git worktree remove` or
  `prune` — neither appears anywhere in that repository — so metadata accumulates, and it falls back
  to a full clone when `worktree add` fails.

## Alternatives rejected

- **Copy the working directory per attempt** — 6–136 s and 1.7–25.5 GB. It also follows pnpm's 2,859
  junctions until killed, copies its own destination when the scratch directory is inside the tree,
  and can leave a directory Windows refuses to delete by name (F327). It survives in exactly one
  role: a subject with no git, where the file plan is ~8 KB.
- **A private `target/` per attempt** — 2.90 GB and 57–68 s each, and two at once take the box to
  2.3 GB free for at best a sixth of the wall clock (F331, F333). ⚠ Note a private build directory
  **does not remove the serialization**: what serializes two attempts is cargo's package-cache lock
  (F332). A shared build directory costs one lock message.
- **`git stash` for the pre-image** — `create` cannot see the files the agent wrote (F329), and
  `push -u` gets them by mutating the working tree, which is the one thing a checkpoint must not do.
- **More attempts in parallel because the box is idle** — it is not: the model saturates at two
  sequences (F83) and one cargo build already saturates six physical cores.
- **Lock files, like v1** — three surfaces, none reachable from the agent that writes (F326).
  Isolation has to be enforced where the path is resolved, and a worktree does exactly that.
- **Require the subject to be a git repository** — 0 of 1,383 measured cells is one (F334).
- **A container per attempt** — daemons were already ruled out for 2.0's runtime (F95/F125), W3 put
  the isolation boundary at the tool child, and the expensive part of an attempt is the build cache,
  which a container would have to share anyway.

## What would falsify this

**A subject repository where the temp-index snapshot is not cheap** — the cost is `add -A`
re-hashing, and it already shows up as 0.39 s on v1's tree because 241 files were divergent. A very
large or pathologically dirty tree would push the checkpoint out of "free", at which point the
snapshot becomes incremental or checkpoints become less frequent — **but the identifier stays a
commit sha and the ref stays mandatory**.
