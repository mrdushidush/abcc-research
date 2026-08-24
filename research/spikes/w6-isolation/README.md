# w6-isolation — worktrees, checkpoints and what parallel work costs

Probes run 2026-08-24 for **W6 item 6 (worktrees / per-task isolation)**. Findings **F325–F335** in
`research/W6-verification.md`.

§11's scope for the item: *"Git worktrees or per-task isolation for parallel work. Compare overhead,
and check RAM cost against the 32GB ceiling."* Plus two inherited questions:

- **OQ-W3-12** — the workspace checkpoint marker: git worktree, git stash object, or a copied
  pre-image tree. W3 item 4's requirement is narrow and exact: *the checkpoint row must carry an
  identifier that can restore the workspace, and `Holding`/fork must refuse to promise resumability
  without one.*
- **OQ-W6-11** — where the toolchain profile lives, and who writes it for a repository 2.0 has
  never seen.

Six probes. Everything is measured on the four real repositories on this machine — the three
donors and this one — rather than on a synthetic tree, because the numbers that decide the question
are the sizes of the directories git ignores.

| probe | what it does | output |
|---|---|---|
| `mechanisms.py` | prices `git worktree add`/`remove`, `git checkout-index`, `git stash create`, the temp-index snapshot and a full `robocopy` of the working directory, per repo, n=3 | `mechanisms-results.json` |
| `stale.py` | hashes every tracked file in every repo and compares with the index — is `git status` clean a claim about content? | `stale-results.json` |
| `checkpoint.py` | the whole checkpoint cycle in a throwaway clone: snapshot, an agent's edits, snapshot, change list, a worktree **at** the snapshot, restore, and whether the snapshot survives `git gc --prune=now` | `checkpoint-results.json` |
| `buildcache.py` | seven cargo phases on the real Rust workspace: private vs shared `CARGO_TARGET_DIR`, cold vs warm vs cross-worktree, two attempts at once on one build dir and on two, with RAM sampled throughout | `buildcache-results.json` |
| `freshwt.py` | the case `buildcache.py` cannot see — a worktree created *after* the cache is warm (so every source file is newer than every artifact), a copied tree with no `.git`, and two cold builds at once | `freshwt-results.json` |
| `toolchain.py` | what a fresh worktree does *not* contain: the ignored entries and their size, the toolchain profile resolved in both trees, and one executed command per repo | `toolchain-results.json` |

## Safety

`mechanisms.py` and `toolchain.py` run against David's real repositories. They add a worktree and
remove it, and they write objects with `git stash create` / `commit-tree`, which touch neither the
index, the working tree nor any ref. Every repo's `git status` is asserted clean before and after,
and the one file each probe edits is restored byte for byte.

One trap this cost an hour, recorded in `stale.py`'s docstring and in the finding: **picking that
file by name is not safe.** In the v1 donor 241 of 539 tracked files differ from their blobs while
`git status` reports the tree clean, because the index stat cache matches; touching one — even
writing back the identical bytes — makes git re-hash it and report a whole-file modification. The
probe now picks a file whose bytes actually hash to its index entry.

`checkpoint.py` and `buildcache.py` work in `scratch/w6-isolation/` (gitignored) on throwaway
clones and worktrees.

## Running them

```
cd research/spikes/w6-isolation
python stale.py                      # ~20 s
python mechanisms.py --quick         # ~30 s, everything except the full copies
python mechanisms.py                 # adds the robocopy rows: ~25 min, and writes ~35 GB.
                                     # NOTE: the v1 row must use /XJ and the abcc20 row must
                                     # write outside the repo — see F327 for both reasons
python checkpoint.py                 # ~30 s
python buildcache.py                 # ~12 min, three cold cargo builds
python freshwt.py                    # ~8 min, three more; the last phase takes the box
                                     # to ~2 GB free — do not run it with a model loaded
python toolchain.py                  # ~5 min
```

`scratch/w6-isolation/` should be empty when they finish; each probe removes its worktrees and
temporary trees. `git worktree list` in each donor is the check.
