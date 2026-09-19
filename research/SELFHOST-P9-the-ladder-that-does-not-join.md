# SELF-HOST P9 — three more landings, and the ladder that counts four and joins none

**Status: the ruling of 2026-09-19 was carried out. Three changes landed, five tasks were rejected,
all by David's hand. `main` is at `fb15aa1`, clean.**
🚨🚨 **AND USING IT FOUND WHAT STUDYING IT DID NOT. F796 — W13's ladder now has four landings and
four reviews, and ZERO pairs that join.** `ChangeLanded.change` stores the **full 40-character
sha**, and its own doc says that is the only reason a landing names a sha at all: it is *"the string
`Event::ReviewRecorded`'s `change` takes"*. `ops::review` appends whatever string it is handed —
**no lookup, no validation, no resolution**. Of the four review rows, **three name an attempt id**
(`a14025`, `a13805`, `a13921`) and one names a **7-character abbreviation** (`a0054e7`). Exact join:
**0 of 4.** 🚨 **And both counters read 4**, so every count-based reading of this log says *four
landed, four reviewed* while the intersection is empty. ⚠ **It has been latent since the first
landing** — the celebrated `a0054e7` row of 2026-09-18 never joined either. Finding **F796**; next
free is **F797**.

---

## 1. ✅ What landed, and what it cost in the metric that matters

| change | task | attempt | rungs | review | `by` | boundary |
|---|---|---|---|---|---|---|
| `e86221c` | `t14016` | `a14025` | 4 | **2 min** | operator | false |
| `61012cf` | `t13604` | `a13805` | 4 | **1 min** | operator | false |
| `fb15aa1` | `t13606` | `a13921` | 4 | **1 min** | operator | false |
| *(09-18)* `a0054e7` | `t2131` | `a2137` | 4 | **2 min** | operator | false |

🎉 **Four changes, six minutes of human review, and the sequence behaved exactly as P8 said it
would** — three clean applies, no conflict, no `--3way` fallback, tree clean at the end.

✅ **Five tasks were rejected**, as ruled: `t13051`, `t13052`, `t13053`, `t13603` (each superseded by
a green landable twin) and `t13605` (a junk probe). ⚠ **The `INTERVENTION REQUIRED` count falls
from 14 to 10, not to 9** — `t13605` was `STANDING BY`, never `INTERVENTION REQUIRED`, so only four
of the five came out of that column. The ten left are **seven research arms** (`t11312`,
`t11726`–`t11731`) and the **three `--version` tasks** ruling (2) retired (`t13054`, `t14017`,
`t14411`).

---

## 2. 🚨🚨 F796 — four landings, four reviews, and nothing joins

### What the two rows actually hold

```
change_landed    change = 'a0054e7db2bcd6c5c82c94b6195c41677ca98e84'   (40 chars)
                 change = 'e86221c1f55fdbb5aa97ac0df062dde227966f3d'   (40)
                 change = '61012cf5de643d1d183aac83656dc8371f69d0c9'   (40)
                 change = 'fb15aa107ea056e1cc4419f469041c0973bb3f4b'   (40)

review_recorded  change = 'a0054e7'   (7)   120 s    <- an ABBREVIATION
                 change = 'a14025'    (6)   120 s    <- an ATTEMPT ID
                 change = 'a13805'    (6)    60 s    <- an ATTEMPT ID
                 change = 'a13921'    (6)    60 s    <- an ATTEMPT ID
```

| join | result |
|---|---|
| **exact string — the only join the log supports** | **0 of 4** |
| prefix (nothing in the code does this) | 1 of 4 |
| names an attempt instead of a change | **3 of 4** |

### Why it is a defect and not a loose field

`ReviewRecorded.change` is documented as *"What was reviewed — a commit sha, or a task id"*, which is
deliberately permissive. **But `ChangeLanded.change` is documented as the other half of a contract**
(`event.rs:551`):

> The commit this made on the operator's branch: **the string `Event::ReviewRecorded`'s `change`
> takes**, which is the only reason a landing has to name a sha at all.

and `ChangeLanded`'s own header says the point of the row is that *"`landed` and `reviewed` count one
population and the gap between them is readable."* **Neither sentence is true today.** An attempt id
is not a sha and not a task id, so the three new rows are outside even the permissive reading; and
the abbreviation is the *right kind* of thing that still fails to join.

🚨🚨 **AND THE HAZARD WAS FORESEEN AT THE DATA LAYER AND LEFT TO THE OPERATOR.**
`Landed::change` (`replay.rs:526`) carries its own warning:

> ⚠ Compared with [`Reviewed::change`] **as a string**, so an operator who reviews a landing
> **must name it the way the landing printed it**.

▶ So the fold knew the join was fragile and put the burden on the person typing — while `land`
prints the sha **two different ways on two consecutive lines**, and nothing between the warning and
the keyboard enforces it. **A comment is not a guard.**

🚨 **`ops::review` (`ops.rs:338`) is eleven lines and does not read the log.** It opens the store,
appends `change: change.to_owned()`, and prints. There is no place in the function where a wrong
value could be noticed.

### Why nobody saw it

* **Both counters agree.** `Ladder::recordings` counts events walked and the landings vector counts
  landings; both are 4. The trap is the mirror image of the standing rule that *a zero is exact as a
  count and weak as a rate* — **a non-zero count said the measurement existed, and the measurement
  never joined.**
* **The ladder has no CLI surface.** `abcc fun` is ADR-0012 §5's six queries and does not touch it;
  the only reader is `abcc-tui` (`line.rs:269`, `view.rs:242`). Nothing an operator runs after a
  landing would have shown the gap.
* ⚠ **And the handoff invited it.** `land`'s first output line is
  `landed <short-sha>  <attempt>  from <sha7> (4 rung(s) green)` — **three identifiers on one
  line** — and the correct full sha is on the *second* line. The instruction it was carried out
  from said *"review `<sha it prints>`"* without saying which line. **That is my defect, not
  David's.**

---

## 3. ▶ THE REPAIR, IN TWO PARTS THAT MUST HAPPEN IN THIS ORDER

### (a) The verb, so it cannot be mistyped again

▶ **Spec, and it is deliberately a single-file change.** In `crates/abcc/src/ops.rs`, `review`
already opens the log. Before appending, resolve `change` against the `ChangeLanded` rows:

* an **exact 40-char sha** that a landing names → use it;
* a **unique abbreviation** of one → resolve to the full sha and use that;
* a **task id** (`t14016` or `14016`) whose task was landed → resolve to that landing's sha;
* **anything else → refuse**, naming what it does know, the way every other refusal in this
  codebase does.

⚠ **One judgement call for David:** whether a review may still be recorded for a change `abcc land`
did not make — a hand-applied commit, for instance, which is exactly what `--version` is about to
become. **If yes, the refusal needs an escape hatch; if no, hand-applied work is permanently outside
the ladder.** F727's caution already says the ladder is *of the changes abcc landed* and never *of
the repository*, which argues for **refuse, and keep the ladder narrow and honest.**

### (b) The data, only after (a)

Four corrected rows, in David's hand, against the full shas. The minutes are already known, so
nothing is re-measured — this re-files a measurement that was taken, not a new one:

```
.\target\release\abcc.exe review a0054e7db2bcd6c5c82c94b6195c41677ca98e84 2
.\target\release\abcc.exe review e86221c1f55fdbb5aa97ac0df062dde227966f3d 2
.\target\release\abcc.exe review 61012cf5de643d1d183aac83656dc8371f69d0c9 1
.\target\release\abcc.exe review fb15aa107ea056e1cc4419f469041c0973bb3f4b 1
```

⚠ **The log is append-only, so the four wrong rows stay.** After this the ladder holds **8
recordings over 4 changes**, four of them orphans. `Ladder::recordings` is documented as *"passes,
not changes"*, so that is a legible state rather than a corrupt one — **but it must be written down,
because the next person to read `recordings` will read 8 and mean 4.**

---

## 4. ⏭ What the landings unblocked, and what they broke

| | state |
|---|---|
| **`--version` patch** | ✅ **still applies cleanly to `fb15aa1`** — `git apply --check` passes. One command away. |
| **`t13055` `Seq::forward`** | 🚨 **now CONFLICTS** — `patch failed: crates/abcc-core/src/seq.rs:43`, exactly as P7 predicted when `t13606` took that slot. Its four rungs are still green *at its own tree*, so `land` would take it and git would refuse it. **It needs a re-run, which needs the GPU.** |
| **the board** | **10** `INTERVENTION REQUIRED` — 7 research arms, 3 retired `--version` tasks |

---

## 5. 🎉 The part worth saying out loud

**F796 is the first defect this project found by *using* the thing rather than by studying it.**
Every finding before it came from an arm, a fold or a desk test. This one came from four landings and
six minutes of review — and it is a defect in the measurement the whole milestone is defined in,
sitting in an eleven-line function, latent since the first landing.

▶ **That is what daily driving is supposed to produce, and the loop closes by feeding it back**: the
`review` guard in §3(a) is a single-file change with a written spec and a testable refusal — which
F794 says is the shape that lands.
