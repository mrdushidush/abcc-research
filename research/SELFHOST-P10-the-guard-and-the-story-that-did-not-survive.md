# SELF-HOST P10 — wave 4: one green, three that said nothing, and a story I had to withdraw

**Status: the champion flew four attempts. `t14581` `Seq::forward` went GREEN and is landable.
The `review` guard F796 asked for failed three times out of three, and is now written by hand and
verified green — `research/patches/review-guard-verified-green.patch`, 690 tests, all four gate
commands exit 0.**
🚨🚨 **AND F797 IS A RETRACTION OF MY OWN HEADLINE.** After the first two attempts I told David the
green task and the failed one differed by **15× in bytes read** and that this was *"the whole
difference"*. Then a **byte-identical** prompt was run again and read **202,460 bytes** where its
twin read **45,964** — **4.4× apart with the prompt held fixed**. Reading volume is not controlled
by the prompt at this n, so the attribution is withdrawn: the contrast is real as an observation and
its cause is **not established**. Finding **F797**; next free is **F798**.

---

## 1. What flew, and what came back

Four attempts, one model load, `--rounds 36` rather than the default 24.

| attempt | task | ended | phase | completion | of which reasoning |
|---|---|---|---|---|---|
| `a14589` | `t14580` guard, prompt v1 | `said_nothing` | Recon | 95 | 90 |
| `a14698` | `t14581` `Seq::forward` | 🎉 **success** | — | — | — |
| `a14795` | `t14787` guard, prompt v2 | `said_nothing` | Recon | 6,234 | **6,233** |
| `a14862` | `t14854` guard, **v2 identical** | `said_nothing` | **Builders** | 79 | 72 |

🎉 **`t14581` is landable** — 4 rungs, 691/691 tests, one file, and the Judge reported no findings.
It applies cleanly to `fb15aa1`, and so does the `--version` patch **on top of it**: tested in a
throwaway worktree, both apply in sequence with no collision.

✅ **And it called `diagnostics`** — 36.5 s, 8,521 bytes back. That is F792's lever working a fourth
time, on the attempt that went green.

---

## 2. 🚨🚨 F797 — the reading-list story is withdrawn by its own re-run

### What I claimed

After `a14589` and `a14698` the table looked decisive:

| | `t14581` green | `t14580` said nothing |
|---|---|---|
| `read_file` | 2 calls, **10,666 bytes** | 13 calls, **160,802 bytes** |
| prompts cut by the server | 0 | **9 of 18**, ≥26,752 tokens gone |

and the v1 prompt did name five files totalling **143,927 bytes** against a 40,960-token window. So
I re-authored the prompt with every type quoted inline and **no file named but the one being
edited**, and reported the reading list as the cause.

### What the control did to it

| attempt | prompt sha | `read_file` bytes | cut | ended |
|---|---|---|---|---|
| `a14589` | v1 `f68ba03e` | 160,802 | 9 | `said_nothing` / Recon |
| `a14795` | v2 `a7a4b554` | **45,964** | 0 | `said_nothing` / Recon |
| `a14862` | v2 `a7a4b554` — **the same prompt** | **202,460** | 0 | `said_nothing` / Builders |

▶ **Two runs of one prompt, 4.4× apart, and the larger one read more than v1 did.** A quantity that
swings that far with the input held fixed cannot carry the explanation I hung on it.

🚨 **What may NOT be said:** that the reading list caused the failure; that inlining the types fixed
the reading; that `t14580` and `t14581` differ *because* of how many files their prompts named.
✅ **What may:** that the v1 prompt named 143,927 bytes of reading against a 40,960-token window,
which is a fact about the prompt; that `a14589` was cut 9 times and `a14795` and `a14862` were not;
and that all three guard attempts ended `said_nothing`.

⚠ **This is the fourth time on this project that a tempting single-cause story has been killed by
the control** — F769, F777, F789, F794 — and the third time **I published it before running the
control.** The lesson is already in the standing list and did not stick: *run the control that
could kill your result first.*

---

## 3. ⏹ Three of three, and the rule that was declared before the third

`said_nothing` is **not rare on this log: 16 of 122 ended attempts, 13.1%**, and Recon accounts for
**11 of the 16**. That matters twice over. It means one failure is unremarkable — and it means
F782's *do not iterate on the wording* does **not** forbid re-running an unchanged prompt, because
that is sampling rather than iterating.

▶ **So the rule was written down before the third attempt ran:** re-run the byte-identical prompt
once; green means the first two were sampling; a third `said_nothing` means the task is the common
factor, and I stop prompting and write the guard by hand.

⚠ **It fired.** Three of three, at two different phases. Three consecutive `said_nothing` against a
13.1% background is p ≈ 0.002 **if the attempts were independent draws, which they are not** — they
are three draws on one task, which is exactly why the task is the thing implicated. The failure did
move forward through the pipeline each time (Recon cut → Recon reasoning → Builders, with Change
actually running), but **that is a description and not a mechanism**, and it is not offered as one.

---

## 4. ✅ The guard, written by hand and verified

`research/patches/review-guard-verified-green.patch` — **3 files, +167 / −10.**

`ops::review` now resolves its argument before it appends anything:

| what was typed | what happens |
|---|---|
| the full 40-char sha of a landing | used |
| an **unambiguous** abbreviation (≥ 4 chars) | resolved to the full sha |
| `t14016` or `14016`, a landed task | resolved to that landing's sha |
| **anything else** | **`AppError::Refused`, and nothing is appended** |

Run against a **copy** of the live log — the real one was never at risk:

```
a14025                                    REFUSED: no change `abcc land` made here is called
                                          a14025 ... The log holds 4 landing(s).
e86221c                                   recorded  e86221c1f55fdbb5aa97ac0df062dde227966f3d
e86221c1f55fdbb5aa97ac0df062dde227966f3d  recorded  e86221c1f55fdbb5aa97ac0df062dde227966f3d
t14016                                    recorded  e86221c1f55fdbb5aa97ac0df062dde227966f3d
14016                                     recorded  e86221c1f55fdbb5aa97ac0df062dde227966f3d
deadbeef                                  REFUSED
```

🎉 **`a14025` is the exact string that broke the ladder tonight, and it is now a refusal.**

### 🚨 And four of the workspace's own tests were encoding the broken behaviour

The guard did not compile against the existing suite, and **that is the finding, not an
inconvenience**: `operator.rs`'s one review test and **all three** of `replay.rs`'s ladder-arithmetic
tests recorded reviews for changes **nothing had landed**. The contract stated in `event.rs:551` was
enforced nowhere — not in the verb, and not in the tests written to exercise the fold that depends
on it. All four now land what they review.

⚠ **One bug of mine, caught by the ladder itself.** The test helper padded short names to sha width
with `0`, which makes `sha1` and `sha10` **the same forty characters** — ten changes folded into
nine and one grew a second pass. `Ladder`'s own *per change, never per recording* arithmetic is what
surfaced it. Padded with a non-digit now.

| the gate, on the guard | |
|---|---|
| `cargo check --all-targets` · `cargo test` · `cargo fmt --check` · `cargo clippy -D warnings` | **all exit 0** |
| tests | **690 passed** |

⚠ It also paid the pedantic tax `--version` pays: the natural nested `if let` is
`clippy::collapsible_if`, flattened with `and_then`.

---

## 5. ✅ CARRIED OUT THE SAME EVENING — and F796 bit once more on the way

**`t14581` landed as `c741d1f`** (David's hand), and **the guard was applied and committed as
`498b963`** (mine, at his instruction). The gate was re-run on the real tree rather than trusted
from the worktree, because `HEAD` had moved: **all four commands exit 0, 693 tests.**

🚨🚨 **And the fifth review named `a14698` — the attempt id again.** F796
caught a fifth victim between being written up and being fixed, which is the strongest argument
the finding could have made for itself. The shipped binary now refuses that exact string:

```
a14698    REFUSED: no change `abcc land` made here is called a14698 ... 5 landing(s).
t14581    recorded  c741d1fcd52ca8cb6a636b0e5f1327d818b66a5d  2.0 min
c741d1f   recorded  c741d1fcd52ca8cb6a636b0e5f1327d818b66a5d  2.0 min
```

🚨🚨 **THE LADDER IS STILL 0 OF 5, AND THE GUARD DOES NOT REPAIR IT.** It stops
the next mistake; it cannot rewrite an append-only log. **Five landings, five reviews, zero
joins**, and until the five are re-recorded M1 has no computable rate — only counts.

✅ **Re-recording is now one word per change, because the guard resolves a task id.** The
minutes below are the ones already measured, re-filed rather than re-taken; each review row is
paired to its landing **by attempt id**, not by order:

| type | it re-files | orphan row |
|---|---|---|
| `abcc review t2131 2` | `a0054e7db2b…` | `a0054e7`, 120 s |
| `abcc review t14016 2` | `e86221c1f55…` | `a14025`, 120 s |
| `abcc review t13604 1` | `61012cf5de6…` | `a13805`, 60 s |
| `abcc review t13606 1` | `fb15aa107ea…` | `a13921`, 60 s |
| `abcc review t14581 2` | `c741d1fcd52…` | `a14698`, 120 s |

⚠ **Afterwards the ladder holds 10 recordings over 5 changes**, five of them orphans.
`Ladder::recordings` is documented as *passes, not changes*, so that is legible rather than
corrupt — **but it will read 10 and mean 5.**

---

## 6. ▶ What is still waiting for David

```
.\target\release\abcc.exe land 14581
.\target\release\abcc.exe review <the FULL sha on land's SECOND line> 1
```

then, in either order, the two hand-applied changes — neither takes a ladder row, because neither
has a green attempt behind it:

```
git apply --index <research>/patches/review-guard-verified-green.patch
git commit -m "fix(abcc): a review names a change the log landed, or is refused"

git apply --index <research>/patches/version-verified-green.patch
git commit -m "feat(abcc): --version, through cli::parse rather than around it"
```

▶ **Land the guard before re-recording the four reviews** — that is P9 §3's ordering and it still
holds. Afterwards the ladder carries **8 recordings over 4 changes**, four of them orphans, and
`Ladder::recordings` will read 8 and mean 4.

⏸ **The board is 13 `INTERVENTION REQUIRED`** — the ten from P9 plus `t14580`, `t14787` and
`t14854`. The three guard attempts are spent and their work is superseded by the patch.

⏸ **The champion is still loaded** (13.61 GB). Nothing needs it.
