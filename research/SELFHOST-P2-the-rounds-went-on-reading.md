# SELF-HOST P2 — the rounds went on reading, and two assumptions died on the way

**Status: Block A of the two-session plan is done, at the desk, with no GPU and nothing flown.
It set out to confirm a chain this project has been telling itself — *`apply_patch` refuses, the
round is gone, the budget runs out* — and the log refuses it: tool refusals cost **8.8%** of the
rounds in a `budget_exhausted` attempt, median 2 of 30. What actually spends the budget is
**reading**, and 65% of the reads whose path is readable are re-reads of a file the same attempt
has already read — 47% of a file *Recon* read, in the phase whose brief tells the model to check
Recon's claims. The second result is a split rather than a casualty: **27 of the 36 attempts that
ran out of rounds were never shown a cut prompt and died with a median 16,057 tokens of headroom**,
while **9 of 36 were cut**, some by more than 27,000 tokens. So the obvious repair — carry Recon's
bytes forward — is affordable for three attempts in four and would make the fourth worse, which is
a design constraint rather than a blocker.** Findings **F771–F776**;
next free number is **F777**. Read-only against
`abcc-1ae35b6091a63e2c/log.sqlite` (108 attempts, 13,048 events) and `D:\dev\abcc` at `71f6aa8`.

---

## 1. The instrument, before anything rested on it

🚨 **F771 — `apply_patch`'s success path wrote nothing to the log until `1cfe1ac`, so every
`applied` count before it is zero for a reason that is not about the tool.** The field is F713's
`output` on `ToolCallEnded`, added 2026-09-12; `unmeasured` has carried refusals since Skeleton
(`afc3555`). Read naively, the log says `apply_patch` applied **0** patches in 95 attempts and 9
in the next 13, which reads as a tool that was broken and got fixed.

**The control says otherwise, and it is not a subtle one.** In the pre-`F713` era `output` is
absent for **all nine tools** — including **1,179 `read_file` calls**, 296 `bash` and 193
`search`, every one of which plainly worked, since the model went on using what they returned.
The absence is a property of the schema, not of any tool. ▶ So a pre-`F713` row carrying *neither*
field is a success, and cutting on **which binary flew** rather than on the calendar:

| binary era | attempts | applied | refused | applied rate |
|---|---|---|---|---|
| pre-`F713` | 95 | **86** (inferred from the control) | 147 | **36.9%** |
| `F713`-era | 13 | 9 | 16 | **36.0%** |

🎉 **The two eras agree to within 0.9 points.** `apply_patch` applies about **36%** of what it is
handed and always has — 95 of 258 calls over the whole log, readable for the first time here.
⚠ **Cut on the date instead and you get a different answer**, because attempt `11138` ran on an
old binary *after* 09-12; that is P12's error in miniature, caught this time by the field rather
than the clock. 🚨 **The standing `31 ok / 35 refused of 66` in this project's memory is a
narrower window and is not what the whole log says.** It is not wrong; it is not the aggregate.

---

## 2. What actually exhausts the round budget — and it is not refusals

The chain SELFHOST-P1 §2 proposed was: a refused `apply_patch` costs a round, and 24 rounds run
out. The first clause is true — `for round in 0..self.limits.rounds` (`turn.rs:487`) is one model
call per round whatever the tool did. **The second does not follow, and the log says so.**

🚨🚨 **F773 — over the 36 `budget_exhausted` attempts, 97 of 1,098 rounds ended in a refused tool
call: 8.8%, median 2 rounds of a median 30.** Across all 108 attempts it is 172 of 2,194, 7.8%.
▶ **Tool refusals are a real cost and they are not the mechanism.** A repair aimed at them buys
back about two rounds in thirty. ⚠ *This kills a hypothesis this file's own author wrote down two
hours earlier, and it is recorded because the next reader will otherwise re-derive it.*

**Where the rounds go instead**, over the same 36 attempts, by phase:

| phase | tool calls | what they are |
|---|---|---|
| Localize | 326 | `read_file` 66.6% · `search` 20.2% · `list_files` 13.2% — **100% exploration** |
| Change | 927 | `read_file` **50.5%** · `bash` 27.2% · `apply_patch` 15.4% · `search` 4.7% |

🚨 **Half of the Change phase's tool calls are reading.** `run_tests` is 0.8% of them and
`diagnostics` is **1 call in 927** — F673's and F765's checker-avoidance seen from an angle
neither was looking from.

---

## 3. The reads are re-reads, and the brief asks for them

🚨🚨 **F774 — of the 189 `read_file` calls whose path the log can recover, 65.1% are re-reads.**
**89 of them (47.1%) re-read a file Recon already read in the same attempt**, 34 (18.0%) re-read a
file already read in the same phase, and only 66 (34.9%) are the first sight of that file.
Attempt `12881` — which ended `BudgetExhausted` — made **5 first reads and 24 re-reads**.

▶ **And the Change brief asks for exactly this.** `brief::change` says *"Recon's report is a claim
about the tree rather than a measurement of it, so check the part you are about to rely on before
you rely on it."* That is ADR-0009's honesty rule, it is correct, and **it is being paid for in
rounds**: the brief carries Recon's *sentence* and drops the *bytes* Recon read, so the only way
for the model to obey it is to fetch them again.

⚠ **n = 189 reads over 13 attempts** — the other 95 attempts' paths are unrecoverable for F771's
reason, so this is the `F713`-era population and not the whole log. It is the largest readable
sample there is, and the mechanism it names is checkable against the brief rather than only
against the count.

---

## 4. The window binds one attempt in four, and the obvious test for it is vacuous

🚨 **The first version of this section said *the window was never the constraint*, on the grounds
that zero of 2,194 model calls exceeded 40,960 tokens. That test cannot fail, and F748 already
says why:** `Body`'s only mutation is `append`, so `prompt_tokens` is a measurement of a monotone
object and **cannot fall** — a fall means the object was cut *before* it was measured. The server
truncates and then reports what survived, so *no call exceeded the window* is true by construction
and is evidence of nothing. ⚠ **The control that would have killed the claim was already in this
repository**, one directory away, and it was not run first.

🚨🚨 **F775 — run on F749's test instead (a call below its phase's running maximum), the
`budget_exhausted` population splits three-to-one, and only the smaller part is a window story.**

| of the 36 `budget_exhausted` attempts | n | last-call prompt, p50 | headroom, p50 |
|---|---|---|---|
| **never shown a cut prompt** | **27** | 24,903 | **16,057** |
| **shown a cut prompt** | **9** | 17,121 *(post-cut)* | — the body exceeded the window |

Twelve attempts of 108 were cut at all (F749's count over this log), and the deepest cuts are
**27,041 · 26,772 · 25,565 · 24,041** tokens — not trims, but most of a conversation.

▶ **So both readings were wrong.** *The window never binds* is false: it binds 9 of 36. *The
window is the story* is also false: 27 of 36 run out of rounds with ~16k of context unused.

🎉 **And this is the load-bearing consequence for the repair.** Carrying Recon's bytes into the
Change phase is affordable for **three attempts in four** — the headroom is measured and it is
there. For the fourth it is actively harmful, because that attempt is already losing the middle of
its conversation. ▶ **So the proposal is not *carry the bytes*, it is *carry the bytes under a
cap*, and the cap's job is to keep the cut cohort from growing.** That is Block C's business and
David's ruling, not this file's.

✅ **And `Event::PromptCut` is exonerated, by dates rather than by argument.** It has never fired,
and there were 74 cut calls for it to fire on — but **all twelve cut attempts predate it.** The
last one, `a11598`, ran at **11:45 on 2026-09-13**; `829e485` shipped the detector at **14:19 the
same day**, two and a half hours later. Ten attempts have run since and **none of them was cut**.
▶ **The detector is young, not blind** — untested rather than vindicated, and the distinction is
the one this project keeps having to make.

⚠ **One caveat on the cut count itself.** F749's test has no threshold, on the correct reasoning
that a fall in a monotone measurement is impossible at any size. But six of the twelve "cuts" are
falls of **3, 7, 19, 23 and 27 tokens**, which is the size of a re-tokenisation or a template
edge rather than of the server dropping conversation. **The six that are unambiguous are
16,394 · 12,303 · 25,565 · 24,041 · 27,041 · 26,772.** Nothing here rests on the small ones, and
whether they are cuts at all is a question worth someone's half hour.

---

## 5. The arm, costed before it was flown

🚨 **F772 — the discriminating arm cannot clear 0.05 more than about half the time at any n,
because its reference is frozen.** Against the post-pivot cohort as it stands (**1 of 24**), with
the new arm's true rate assumed to be the pre-pivot **24.4%**, simulated power is 0.36 at n = 20,
0.53 at n = 40 and **0.53 at n = 60** — it saturates near 0.55, and n cannot buy what the
reference's precision does not have. Flown balanced instead, both arms fresh: 0.32 at 20/arm,
0.68 at 40/arm, **0.79 at 50/arm — 100 attempts, 7.2–11.9 GPU hours** at the log's own p50–p90
attempt time. ▶ **This is the A4 overestimate stated in advance**: that arm projected p ≈ 0.03 and
delivered 0.091.

✅ **David ruled 2026-09-18: the deterministic discriminator, then a small descriptive arm.** See
SELFHOST-P1 §3 Block B. 🚨 **Descriptive means descriptive** — n = 10/arm is chosen knowing it
cannot clear 0.05, so no p-value from it may be published as a result.

---

## 6. The owed bound, discharged

✅ **F776 — `promptcuts.py --check` is bounded at `AS_OF = 11726`, and F764's debt is paid.**
Unbounded, the control reported DRIFT on three figures the moment anybody flew: the first three
read **128 / 95 / 114** today against a published **117 / 86 / 103**, and they read 123 / 90 / 109
when F764 was written. **Neither is a correction — both are the same instrument over a bigger
population**, which is precisely what a control with no bound cannot say.

🚨 **`PUBLISHED` was not moved**, per F764's rule: repair by adding what is missing. The bound is
the same constant `toolreach.py:69` carries, deliberately — two controls over one log that
disagree about when *now* was are two answers waiting to be quoted against each other. Verified by
search rather than chosen: all nine figures reproduce at every bound from **11726 to 11800** and
drift first at 11910. `--check` prints the bound it used and exits 0; the unbounded report is
unchanged and still reads the whole log.

---

## 7. What Block C now has to propose, and what it must not

**The proposal pack changes shape because the diagnosis did.** What the measurements support:

* ▶ **Carry Recon's reads into the Change phase, under a cap** (F774 + F775). The evidence is 47%
  and the headroom is 16k on 27 attempts of 36. **This is the one proposal the numbers point at**,
  and the cap is not a detail: 9 of 36 are already losing the middle of their conversation.
* ⏸ **The round budget (24).** F773 says refusals are not why it runs out, so raising it is a way
  of paying for more reading rather than less. Propose it only beside a measurement of what the
  extra rounds get spent on.
* ⏸ **The `apply_patch` markup fold.** 42 of 163 refusals, on a stable 36% apply rate — real, and
  worth about two rounds in thirty. **Not the headline it has been quoted as.**
* ⏸ **The window, for the cut quarter only.** Not a general context guard — 27 of 36 have room to
  spare — but the nine that do not are a distinct population and a cap is what they need.

⚠ **And one instrument gap worth its own line:** successful tool calls do not log their arguments
(F713's rule, deliberately), so **F774's 47% is recoverable only from `read_file`'s output text**
and only for the `F713` era. A repair that changes what the Change phase is handed will need that
number again afterwards, on the same instrument, or it will not be comparable.
