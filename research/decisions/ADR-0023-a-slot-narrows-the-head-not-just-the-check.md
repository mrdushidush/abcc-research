# ADR-0023 — A slot's ceiling narrows the head itself, not just the check underneath it

- **Status:** ✅ Accepted
- **Date:** 2026-08-30
- **Deciders:** Claude Code, building FLEET's *"one slot with a resident model and a tool policy"*;
  the ceiling-on-the-role half is **ADR-0014 §4**, and the *deny the class* rule underneath both is
  **W7's**, ratified with `research/SUMMARY.md`
- **Sources:** W7 **F404–F422** (an argument check binds only the tool that has an argument, four
  times) · **F551**, **F552** (both new, `research/FLEET-P3-the-slot-the-breaker-and-the-bill.md`) ·
  **F81** (the prefix cache saves 79.7% of TTFT) · **F392** (two mechanisms sharing one integer)
- **Extends:** ADR-0014 §4 · ADR-0011 §2

## Context

ADR-0014 §4 put a tool ceiling on the **role** and said so as code: `Policy { role, max_tier }`,
with `Head::max_tier()` giving Recon `Read`, Builders `Exec` and the Judge `NoTools`. FLEET's
milestone list asks for a slot that has *"a resident model **and a tool policy**"*, and `Fleet` had
no policy field at all. The two halves needed joining, and the effective ceiling is obviously the
narrower of them — `min(head.max_tier, slot.max_tier)`.

What was not obvious is **where the cap has to be applied**, and the plan's own falsifier assumed
the wrong answer.

## Decision

### 1. The cap is a `Tier`, and never a list of tool names

W7 proved four times, with four mechanisms across three authors, that an argument check binds only
the tool that has an argument — a shell walks past it. `Reach` is a property every registry entry
declares and `Tier::Exec` **is** the class. A slot ceiling that named tools would be the same defect
one level out.

### 2. 🚨 The cap narrows the head, because the advertised and enforced surfaces are one list

Enforcement alone is the obvious build and it is a trap. A `Builders` capped at `Read` whose prompt
still advertised `run_tests` would ask for it, be refused, and be told — **on every attempt,
forever** — spending a tool round to learn something the prompt could have said. `head.rs`'s own
rule already said the advertised surface and the enforced surface are one list; a cap that reached
only the check would make them two lists that had agreed until the day a slot capped something.

**So a `Head` alone can no longer answer *what tools do I have*.** The unit is
`Posting { head, ceiling }`, normalised at construction so a ceiling above the head's own is
unrepresentable, and `Head::policy/tools/prefix` no longer exist — `Head::posted(slot)` is the only
route to any of the three. Three renderings read the posting and there is nothing else for them to
read: the prompt's tool section, the OpenAI wire `tools` array, and `Policy::admits`.

### 3. The enumeration is nine, and the affordability argument is unchanged

ADR-0011 §2's bill is *one cold prefill and ~473 MiB of warm state per head*. The compile-time table
goes from four to **nine**, not sixteen, because a posting's ceiling can never exceed its head's.
⚠ And what is warm at once does not move at all: **a slot's ceiling is operator configuration fixed
for a sortie**, so one column of the table is live in any session — four heads, the same bill.

▶ This is also what makes ADR-0011's *"frozen **per attempt**"* an exact statement. The prefix used
to be frozen for the life of the process, which is stronger than the plan asked for and made the
qualifier vacuous. Now there is a thing that could vary between sorties and cannot vary inside one.

### 4. The ceiling in force goes on the log

`Event::ModelCallStarted` carries `ceiling` (`#[serde(default)]` for logs written before it
existed). Without it a capped run and an uncapped one differ **only in the prompt** and agree in
every event, and status is a projection of the log alone.

### 5. One dial, not one per role

The ceiling belongs to the fleet, the way a toolchain profile does (ADR-0008 calls that operator
configuration), and it is one value rather than one per role — the role already has its own, and two
dials on one quantity is F392's shape.

## What it changes about the falsifier

`PLAN.md` wrote the falsifier as: *a slot capped at `Read` must make `Builders` refuse `run_tests`,
and the refusal must be `Why::Denied`, which is a `HardFailure` and `NextAction::Stop`.*

🚨 **F551: no denial can reach that classification.** `outcome_from` and `next_after` do map
`Why::Denied` that way, and the only producers of `Why::Denied` put it on
`ToolCallEnded.unmeasured` — a log field. No `Ending::Unmeasured(Why::Denied)` is constructed
anywhere. A denied call is a normal outcome **inside** a phase: the counter increments, the model is
told in its own transcript, and the round loop continues, which
`tests/turn_loop.rs::a_denied_tool_is_refused_on_the_log_and_in_the_transcript` has asserted since
Skeleton.

Had the premise been true, a capped slot would have been a foot-gun — one wrong setting killing
every attempt at its first tool call. **The falsifier as shipped is the real behaviour**: the cap
narrows what the role is told it has, and the refusal underneath is the backstop for a model that
asks anyway.

## Consequences

- `--ceiling no-tools|read|write|exec` on `abcc fleet` and `abcc run`, defaulting to `Tier::Exec`,
  so a caller that sets nothing sees no change at all. Both commands print the ceiling in force,
  because a capped slot is otherwise invisible until a role is refused something.
- A slot can only ever take capability away. `Head::posted` takes the minimum, so no setting
  anywhere can hand a role something its own ceiling refuses — which is what makes the flag safe to
  expose. `a_slot_narrows_a_role_and_can_never_widen_one` checks that over all sixteen products.
- `Tier::narrower` is a `const` discriminant comparison so that `Head::posted` can be `const` and
  `Posting::ALL` a const array. ⚠ That equivalence holds only while the variants stay in order, so
  it is checked against `Ord` over all sixteen pairs rather than assumed.
- The Judge is unreachable from any slot setting: `Commandos.posted(slot).ceiling()` is `NoTools`
  for all four, so *A4 has no tools* stays a fact about the call.

## What would overturn it

- **A confinement primitive appears on this platform.** ADR-0014's own falsifier. A real OS boundary
  would make the ceiling one control among two rather than the only one, and `Confinement` already
  has the arm to say so.
- **A slot ceiling is wanted per phase rather than per sortie.** That would make the prefix a dial
  and reopen ADR-0011's affordability argument, since more than one column of the table would be
  warm at once. Nothing wants it today.
- **A denial becomes a phase ending.** Then F551's dead arm comes alive and the *check that is the
  ending you want* question from `PLAN.md` becomes real, and has to be answered before a cap is
  anything but advisory.
