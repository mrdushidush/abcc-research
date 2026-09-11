# POSTURE P1 — the five open rows, and the four that stay admissions

**Status: the milestone's exit criterion is met.** All eleven threat-model rows now carry a shipped
control or a written, dated admission. 🚨 The session's largest finding is that **this repository had
no CI at all** against 297 crates until today — so ADR-0014 §5's *"one const **with a CI test**"* had
the const and the test and nowhere that ran them, for three milestones. 🎉 Row 11, **the one control
no donor in the family has**, is shipped and was driven against the real champion: it pins
`3fb1abe61135`, the digest `sha256sum` independently reports for the same 12.67 GiB. Two of the
brief's own claims were wrong and are corrected below — **there are nine tools, not seven**, and
**egress is not closed by absence**. Findings **F686–F692**; next free number is **F693**. Built
2026-09-11 against `D:\dev\abcc` from `38763a6` to `a6bb2ad`, five commits, **575 tests** (was 550),
19 ignored, `cargo fmt` and `cargo clippy --all-targets -D warnings` clean, `cargo deny check` and
`cargo audit` clean with zero warnings.

---

## 1. What was open, and what the recon got wrong

The milestone began from a recon that said six rows were shipped and five were open. The six were
shipped. Two of the five were mis-stated, and both errors ran in the *reassuring* direction, which is
the direction that matters for a threat model.

**The verification the brief itself demanded was the one thing it was right to demand.** ADR-0014 §7
merges the donor's two destructive-git guards into one table, and W7's F422 says the donor's guard
missed the shell path. Checked: `not_destructive` is called at `workspace.rs:668` on `bash`'s command
string and at `workspace.rs:697` on the `git` tool's joined argv, the classifier scans every token
rather than the first word, and `tests/exec.rs` drives both. Row 1 is what it says it is.

**F690 — 🚨 there are NINE tools, not seven, and the two nobody counted are the two that matter.**
Every prior statement of the tool set in this project's memory reads *"`read_file`, `list_files`,
`write_file`, `apply_patch`, `bash`, `run_tests`, `diagnostics`"*. `TOOLS` in
`abcc-engine/src/tools.rs` has nine entries: those seven plus **`search`** and **`git`**. `search` is
harmless — `Reach::Inspects`. `git` is `Reach::SpawnsChild`, and it is the second half of row 1's
"both paths". So the list that was being quoted omitted one of the two tools the destructive-git
table exists for, while the table itself was correct. ⚠ *A count repeated across three memory files
is not a measurement; it is the first person's count, quoted.*

**F691 — 🚨 "egress is closed by absence" is half true, and the half that is false is the operative
half.** The claim was that there is no `web_fetch` and no tool touches the network. The first clause
is true. The second does not follow: **three of the nine tools spawn children** (`bash`, `run_tests`,
`diagnostics`, plus `git`), the environment allowlist carries `PATH`, and a child with `PATH` reaches
`curl`. So egress is closed for every role capped below `Tier::Exec` — Engineering, Recon and
Commandos — and **open for Builders**, which is precisely the role that writes code.

⚠ And the thing that looks like the missing control is not one. `ProviderClass::leaves_the_machine`
exists, is well documented, and **has no caller anywhere in the workspace** — `Mode::SinglePlayer` is
a policy about which *provider* may be admitted, and a provider is where the model runs. It says
nothing about what a tool child does and cannot be read as an air gap. ADR-0014 §5's `--offline` for
unattended roles is the leg that would close row 8, and it is not built.

Row 8 is therefore recorded as **partly shipped with a dated admission**, not as closed.

---

## 2. Rows 4 and 9 — redaction, and why it is a type

`redact` had appeared in this workspace only in two doc comments (`provider.rs:79`, `:428`). ADR-0014
§5 asks for redaction *"at the tool-result boundary, as a property of the result type, applied once"*,
and the phrase is load-bearing in all three of its parts.

**Applied once.** A tool's output reaches three sinks — the durable log, the console that projects
that log, and the model's own context. The donor redacted the two disk sinks and neither of the
others (F418). Scrubbing at each sink would be three denylists that agree until one is edited, so the
scrub happens at one seam, `TurnLoop::tool_round`, and all three read from that one string.

**As a property of the type.** `Scrubbed` has a private field and one constructor, and both sinks take
one: `Event::ToolCallEnded::arguments` and `Message::tool_result`. A second path to either **does not
compile**. That shape was chosen against a specific defect: the donor's denylist was a good one hung
off `validate_read_path`, and `bash` never called it. *A check that is not on the path is not a check.*

The type change touched three call sites in the whole workspace, which is the cheap evidence that the
seam was in the right place.

**F692 — ⚠ the log carries more free text than the memory said it did.** The standing note is that
*"the log does not persist tool arguments — `tool_call_started` carries only kind/attempt/tool/tier"*.
True of that event. `ToolCallEnded` carries `arguments: Option<String>` **on every refusal** (F505),
which is a refused `bash` command line or a refused `write_file`'s entire content, verbatim, on disk.
So row 9's surface was larger than the row's own description, and that field is now the one place in
`Event` that takes a `Scrubbed` rather than a `String`.

### 2.1 Two defects the tests found in their own subject

🚨 **Scrubbing twice re-reported a removal it had not made.** `Authorization: Bearer [redacted]`
matches the authorization rule — correctly; the pattern is right and the rewrite is empty. The naive
fix is a fifth pattern that matches the marker, which is a fifth thing to keep in step with the other
four. The shipped fix is structural: **a rewrite that produces exactly what it matched removed
nothing, so it is not counted.** Idempotence then holds for every shape and for shapes added later.

⚠ **A seam test passed against a mutation that deleted half the denylist.** The first version put the
secret in `ABCC_MODEL_API_KEY=...` and `Authorization: Bearer ...` — both of which the *shape* half
catches, so dropping the *literal* half changed nothing. A third occurrence in plain prose is what
makes the mutation visible. *A test whose subject is caught by two mechanisms measures neither.*

Seven mutations, none survived.

---

## 3. Rows 5 and 10 — the gate, and the CI that was never there

**F687 — 🚨 there was no CI in this repository at all**, and it had been quietly load-bearing in two
places. There is no `.github/`, so:

- ADR-0014 §5 says adopt `env_clear()` + allowlist *"as data in one const with a CI test"*. The const
  is `ENV_ALLOWLIST`; the test is `abcc-engine/tests/child.rs`; **nothing ran it anywhere but a
  developer's box**, and row 5 has been recorded as shipped since Skeleton on that basis.
- W7's F419 called *300+ transitive crates with no supply-chain gate* a contradiction for a
  security-positioned project. At 297 crates, it stayed one for three milestones.

The gate is the donor's, copied per ADR-0014 §6 with the update procedure — the procedure being the
part that stops the policy rotting into a pile of `ignore` entries. Three places the copy is
deliberately not verbatim, each because a measurement said so rather than because it was inconvenient:

| what | why | what was done instead of loosening |
|---|---|---|
| `wildcards = "deny"` fired on nine path deps | the donor is **one** crate; a `{ path = ... }` dep correctly has no version requirement | declared the workspace `publish = false` — true today, no release pipeline — which is the procedure's own *fix the tree* branch |
| five licenses in the allow-list matched nothing | the list claims to be the minimum satisfying the tree | removed them. The one that mattered is **MPL-2.0**: weak copyleft, allowed by the donor, earned by nothing in these 297 crates |
| the skip list named the donor's duplicates | this tree's are different | re-derived from `cargo tree -d`: `hashbrown`, `miniz_oxide`, `syn`, `windows-sys`, each with the two upstreams that disagree named |

⚠ **Every one of the seven job commands was run locally and exits 0**; the Linux half of each matrix
is unverified until the workflow first runs, and the commit says so. The `needs:` gate the ADR asks
for sits in front of `cargo publish` in the donor and this workspace publishes nothing, so the same
shape guards the branch as **one derived required check** — a job that `needs:` every other job, with
`if: always()` and an explicit per-result test, because a `needs:` job whose dependency was *skipped*
succeeds by default and *not failed* is not the same predicate as *passed*.

---

## 4. Row 11 — the weights, and the two numbers that designed it

The one control no donor has. Two measurements came before any design, and both changed it.

🚨 **The serving stack offers no digest.** Probed against LM Studio with the service up:
`/v1/models` returns `id`, `object`, `owned_by`. `/api/v0/models` adds `type`, `publisher`, `arch`,
`quantization`, `state`, `max_context_length`, `capabilities`. **Neither carries a digest, a length or
a path.** The API identifies a model by the name — which is the thing under suspicion. ADR-0014 says
*manifest digest* because ollama has one; this stack does not, so the digest has to be of the file.

🚨 **A full SHA-256 of the champion is 51.9 s** by `sha256sum` and **54 s** through the shipped module
— 12.67 GiB at ~250 MB/s. That single number is the whole design. A check costing most of a minute on
every `abcc run` is a check that gets turned off, so a start compares length and modification time and
re-reads only when one has moved.

**F688 — the two passing arms are not interchangeable, and that is F495's shape one asset over.** In
F495, keeping *the server says it is loaded* apart from *the server lists it* is what stopped a weaker
answer being read as a stronger one. Here `Verified` means the 54-second read happened and the bytes
hash to the pin; `Unchanged` means a directory entry matched and **the file was not read**. One is a
measurement of the bytes and the other of the metadata, and collapsing them would make every start
look like a full check.

⚠ **A mismatch does not re-pin.** Overwriting the pin at the mismatch would make the alarm fire exactly
once and then describe the substitute as the reference — *a control that disarms itself the first time
it is right*. `abcc weights --repin` is a separate word from `--verify` for the same reason.

### 4.1 Two defects, again found by the tests written for them

⚠ **`reads_the_file` predicted a read for a model with no file behind it**, so `abcc weights`
announced a 54-second pause and then reported `unchecked` instantly. Caught by the test that asserts
the predicate agrees with what `check` actually did on every arm — which exists because two functions
answering one question is F392's shape, and the defence is a test that fails when they disagree rather
than an expectation that they will not.

🚨 **The digest test passed a mutant that hashed only the first 8 MiB.** It hashed one file twice,
compared it with itself, and checked the hex was 64 characters — and the digest of *something* is
always 64 characters. The oracle is now two files sharing a whole chunk and differing after it.

Eight mutations, none survived.

---

## 5. The four admissions, and the one that was verified first

Rows 3, 6, 7 and 8 have no shipped control. They are written down because **a threat model with
silent rows is worse than one with honest gaps** — and because ADR-0014's exit criterion counts a
dated admission as an answer.

Rows 3 and 6 restate W7's own measurements: there is no OS-level confinement on this platform
(F408–F411), and no marking of untrusted file contents would hold — 39 of 50 for the family's best
wrapper, 0 of 50 for the best candidate (F412–F415).

**Row 7 was marked UNVERIFIED in the brief and was checked rather than assumed.** ADR-0014 §5 wants a
displaced task to be *"a verification failure, not a style issue"*. It is not one:

- The gate's `Veto` rung has **exactly one rule** — a tree whose checker could not reach a test is
  broken rather than unmeasured — and its own source says the security rule *"arrives with the Posture
  milestone"*. It has not arrived. Declaring it would be a name standing in for a specification, and
  a veto that cannot fire is one an operator trusts for the wrong reason.
- The **Judge does see it**: `judge::Dossier` carries the task's title and prompt beside the patch.
- 🚨 **And the Judge may never refuse.** `AttemptPhase::may_refuse` is `!uses_model()`, a model verdict
  is a `Claim`, and nothing in the workspace turns one into an `Outcome`.

⚠ **One claim was softened before it was quoted.** The first draft said the Judge had been *"observed
objecting on exactly those grounds"*. F536's case is a reviewer checking a change against *the scope
the ticket states* — on a change that did **too little**, not one that did **something else**. That is
a reason to think a displaced task would be noticed; it is not a measurement that one was.

So row 7 is: **visible to a reviewer, invisible to the gate, and terminal only through a person's
verb** — `abcc accept` is an operator's, and a working task reaches no terminal state without one.

---

## 6. What this cost the documentation, which had drifted

- `CLAUDE.md`'s closing section said **"`max_tier` does not exist yet. It arrives with the Posture
  milestone"**. It has existed since Skeleton (`head.rs:131`), so the file every agent reads has been
  telling them to describe shipped enforcement as intended.
- `CLAUDE.md`'s derived test list had drifted for the third time. Re-derived: **36 process-free targets
  of 49**, 412 tests; full suite 575.
- `README.md` promised `SECURITY.md` *"when it lands with the Posture milestone"*. It has landed: 243
  lines, eleven rows, seven controls and four admissions, each dated.

---

## 7. Findings

**F686** — 🚨 **A denylist has two unequal halves and only one of them works.** The literals a process
holds are matched exactly and have no false-positive story; the shapes are heuristics that catch the
well-known formats and miss a credential that looks like prose. They are counted separately because a
record saying *a vendor token was removed* about the one value whose identity is known exactly is a
worse record than one that says which. ⚠ Two properties fell out of testing it: **scrubbing twice must
change nothing**, which is structural — a rewrite producing exactly what it matched removed nothing,
so it is not counted — and **the default must be ON**, because a redactor configured off by an omitted
builder call protects only the paths somebody remembered, which is F416 one layer up.

**F687** — 🚨 **There was no CI in this repository at all**, against 297 crates, through Skeleton, Gate,
Fleet and Console. ADR-0014 §5's *"one const with a CI test"* had a const and a test and no runner, and
row 5 had been counted as shipped on that basis since Skeleton. ⚠ The generalisation: *a control whose
evidence is a test is only as shipped as the thing that runs the test.* ⚠ Also measured while copying
the donor's gate: its license allow-list carries five licenses this tree does not use, **MPL-2.0 among
them** — an allowance nothing matches is a permission granted in advance.

**F688** — 🚨 **A weights check has two passing answers and they are not the same claim.** A full
SHA-256 of the champion is **51.9 s** (`sha256sum`) and **54 s** (shipped module) over 12.67 GiB, and
🚨 **neither model-listing endpoint carries a digest, a length or a path** — `/v1/models` and
`/api/v0/models` both identify a model by the name, which is the thing under suspicion. So the digest
is of the file, a start compares metadata, and `Verified` / `Unchanged` are separate arms: F495's
*loaded versus listed*, one asset over. ⚠ And a mismatch must **not** re-pin — a control that adopts
the substitute as its reference disarms itself the first time it is right.

**F689** — ⚠ **A displaced task is visible to a reviewer and invisible to the gate**, verified rather
than assumed. The `Veto` rung has exactly one rule and its own source says the security rule *"arrives
with the Posture milestone"*; `judge::Dossier` does carry the task's title and prompt beside the patch,
so the Judge can see it; and `AttemptPhase::may_refuse` is `!uses_model()`, so it may never act on it.
⚠ The nearest evidence, F536, is a reviewer checking a change against *the scope the ticket states* on
a change that did **too little** — a reason to think a displaced task would be noticed, not a
measurement that one was.

**F690** — 🚨 **There are nine tools, not seven.** `TOOLS` carries `search` (`Reach::Inspects`) and
`git` (`Reach::SpawnsChild`) beside the seven every memory file lists. The omitted `git` is one of the
two paths the destructive-git table is read from, so the count being quoted left out a tool the row it
described depends on. The table was right; the summary of it was not.

**F691** — 🚨 **Egress is not closed by absence.** There is no `web_fetch` and that is true and
insufficient: three of nine tools spawn children, `PATH` is on the environment allowlist, and a child
with `PATH` reaches `curl`. Egress is closed for every role below `Tier::Exec` and **open for
Builders**. ⚠ `ProviderClass::leaves_the_machine` **has no caller in the workspace** and is about
where the model runs; it is not an air gap and must not be quoted as one.

**F692** — ⚠ **`ToolCallEnded` keeps a refused call's arguments verbatim** (F505), so *the log does not
persist tool arguments* is true only of `tool_call_started`. A refused `write_file`'s entire content
and a refused `bash` line both land on disk unmodified. Row 9's surface was larger than the row said.

---

## 8. What is owed after this

- ⏸ **Row 8's other half.** `--offline` for unattended roles, which is the only leg that closes
  exfiltration, and `ProviderClass::leaves_the_machine` acquiring a caller or an explanation of why it
  has none.
- ⏸ **The Linux half of CI**, unverified until the workflow first runs on a push.
- ⏸ **The four `paint` changes**, specified in CONSOLE and deferred behind this milestone.
- ⏸ **The eleven arms**, recommended REJECT by three agents, still awaiting David's word.
- 🚨 **`review_recorded` is still 0**, so SELF-HOST's exit is measured in an event never once written.
  That is the next milestone's first problem, not this one's.
