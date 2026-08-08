# `w8-corpus` — the loader for a `corpus/SPEC.md` v1 corpus

The first piece of step 3. `w8-import` (step 2) only *writes* the corpus; nothing in Rust could
read it back. This crate is the port of `research/spikes/w8-corpus-v1/validate.py`, which
implements SPEC §13's ten rejection rules, the §5 variant merge and the §10 aggregate arithmetic,
and is numbered to match the spec — so it is a reference to port, not a shape to guess at.

```bash
cargo run -p w8-corpus -- ../corpus --subject claudette-fc1ea22   # human report
cargo run -p w8-corpus -- ../corpus --facts                       # a sorted fact stream
cargo test -p w8-corpus                                           # 53 tests
```

On the current corpus: **90 tasks · 54 full / 24 presence-only / 12 quarantined-with-baseline ·
aggregate denominator 78 · 271 cells against `claudette-fc1ea22`, 0 n/a · ACCEPTED.**

The workspace's **first third-party dependency**, and SPEC §2 anticipated it — the corpus is TOML
because `toml` is already a Claudette dep. It is used for *parsing only*; the model is walked by
hand rather than derived, because a rejection has to name the rule it violates and a derive's
"missing field `quarantine`" cannot.

## The cross-check, which is the point

A port whose reference is a script nobody re-ran is a port that agrees by assertion. Both
implementations grew a `--facts` mode emitting the same sorted lines — one per subject, suite,
task and merged variant, carrying disposition, gate triple, aggregate membership, variant origin,
permission mode, `requires`, rule count and `default`:

```bash
python research/spikes/w8-corpus-v1/validate.py corpus --facts > py.txt
harness/target/debug/w8-corpus corpus --facts > rs.txt
diff py.txt rs.txt          # normalise newlines first — see below
```

**364 facts, 0 differing.** Including all 271 `(task, variant)` cells and both quarantined tasks.

Normalise line endings before diffing: Python's `print` emits CRLF on this host and Rust's emits
LF, so a raw `diff` reports every line as changed while the content is identical. That is the
third time CRLF has produced a difference that looks like a finding and is not (cf. F21, F22).

## Three ways it is stricter than `validate.py`, all deliberate

Recorded because a silent divergence between an implementation and its reference is the exact
defect class this project keeps finding.

1. **A task with any rejection does not enter the model.** `validate.py` reports the violation and
   still counts the task as loaded. SPEC §13 says the loader *rejects the corpus*, so a half-valid
   task has no business reaching a runner. The two therefore agree exactly on an accepted corpus
   and differ in the task count on a rejected one.
2. **Gate evidence is checked against §9's vocabulary** — `tier`, `verdict` and `verifier` — under
   rule 7. Measured first: all 172 evidence blocks in `u100` already conform, so this rejects
   nothing that exists today.
3. **`expected_tasks` is checked against the tree.** A silently missing task directory is the
   failure that flatters a run: fewer tasks, same pass rate. `u100` declares 90 and holds 90.

Rule 2 is also applied to suite directories and subject filenames, not only task directories.
Both hold today.

## What building it found

**A loader that read SPEC §4 literally would have found zero suite caveats.** §4's prose says
"suite-level `caveats`", but §4's own example — and `suites/u100/suite.toml` — place the key
*after* the `[provenance]` header, which under TOML scoping makes it `provenance.caveats`. Same
for `expected_tasks`. The first version of this loader read the top level, reported **0 caveats**
and never fired the `expected_tasks` guard, and nothing anywhere said so. Silent, and in the
flattering direction: a suite that records no caveats looks cleaner than it is. Both keys are now
read from `[provenance]` first and the top level second, since only a parser can see the
difference.

**Two fixtures are not empty and the suite says they are.** `suite.toml`'s caveat reads "78 of the
90 tasks generate their artifact from nothing and so have an EMPTY `fixture/`, holding only a
`.gitkeep`". Measured: **76 fixtures are empty; 14 hold files** — the 10 section-4B `fix_*` buggy
fixtures plus the 4 dependency fixtures reconstructed for F23. `node_server_main` and
`py_server_main` carry a `.gitkeep` *beside* four real files each, because the importer wrote the
placeholder before the reconstruction stage added the files. Harmless at run time — dotfiles are
skipped — but the caveat is a claim about the tree and it is off by two.

**The subject's `commit` was parsed by nothing.** Found while building the runner (step 3b), not
here: `subjects/claudette-fc1ea22.toml` carries `commit = "fc1ea22"`, `Subject` had no field for it,
and SPEC §11 lists subject commit among RUNMETA's required fields — so the first RUNMETA row wrote an
empty string for a required field and said nothing. Now `Subject::commit: Option<String>`; optional
because SPEC §7's example does not show the key. **The `--facts` stream is deliberately unchanged**,
so the 364-fact cross-check above still covers exactly what it covered before; a field a runner reads
and the cross-check does not is the residual risk, and it is smaller than re-baselining the diff.

**A negative control whose mutation does not apply is vacuous.** Two rule tests here were written
against a mis-transcribed anchor; the `str::replace` matched nothing and both tests exercised an
unmodified valid corpus. The rejection cases failed loudly, but the *acceptance* case passed for
entirely the wrong reason. Every template mutation now goes through a `mutate()` that asserts the
anchor exists.

## SPEC §2's isolation guarantee, made structural

> `refsol/`, `sham/` and `stub/` are gate-time only. The runner must never copy them into a
> workdir the subject can see; a loader that cannot guarantee that must refuse to run.

Both halves are implemented rather than commented:

- **Load time.** `fixture/` must exist; a symlink anywhere under it is a rejection (it could
  resolve to `../refsol`, so the guarantee cannot be made by inspecting names); a nested directory
  named `refsol`/`sham`/`stub` is a rejection.
- **Run time.** `WorkdirPlan` is the only thing in the crate that yields copyable paths and it is
  built from `fixture/` alone. `Task` reports `has_refsol()` / `has_sham()` / `has_stub()` as
  booleans and **never hands out their paths at all** — a runner that cannot name the directory
  cannot copy it by accident. Gate execution belongs to `w8-import` and to step 4, neither of
  which goes through this loader.

Dotfiles are skipped, which is measured rather than tidy: 76 U100 fixtures hold only a `.gitkeep`,
and copying it would put a file in a work dir the donor's runs did not have.

## Rule 8 is not a load rejection

SPEC §13 says so explicitly — a variant whose `requires` names a capability no subject declares is
a property of the *pair*, so it is answered by `Suite::plan(&subject)`, which returns
`Support::NotSupported { capability }` per cell. That prints as `n/a` and is arithmetically
distinct from zero, because §7's column is exactly where 2.0's differentiator has to appear and it
must never round to nothing.

## SPEC amendments 6 and 7 — both additive, `schema` stays `1`

- **`[delivery]` on the subject descriptor** (§7): `open` / `close` sentinels naming the lines that
  bracket a multi-line prompt the subject reassembles into one turn. Optional, but **both keys are
  required once the table is present** and they may not be identical — a half-declared pair would
  wrap a prompt in something the subject never closes on, and that failure lands as a *timeout*,
  which reads as a slow subject rather than as a bad descriptor.
- **`expect.gate_fires_after_deny`** (§5): gates strictly after the first delivered `deny`. F36 —
  `gate_fires = { min = 2 }` was satisfied by four exploratory `bash` gates while the denial was the
  session's last gate, so the bound passed and the question went unanswered.

A descriptor with no `[delivery]` and a variant with no `gate_fires_after_deny` load exactly as
before, which is why the integer did not move.

**A fourth deliberate strictening over `validate.py`, now matched on both sides: an unknown `expect`
key is rejected, not ignored.** An `expect` that checks nothing always holds, so
`gate_fires_after_denial` would have turned a variant's whole question into a silent pass — in the
direction that flatters the subject. Same shape as F28's zero caveats.

## Tests

53, in two files. `tests/rules.rs` builds a minimal valid corpus from scratch — not a copy of
`u100`, so the tests neither move when the import changes nor prove only that one donor parses —
and mutates one thing per test. Every negative control asserts the rejection **carries that rule's
number**; "some rejection happened" would let a rule fire for the wrong reason and still read
green. The valid baseline is asserted to load first, or every negative control below it is
vacuous. Two tests read the real corpus and restate the import's own numbers from an independent
reader.
