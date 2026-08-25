# W6 item 8 — honest failure reporting

Everything behind item 8 of `research/W6-verification.md`: §11's *"**Honest failure
reporting**, which V1 got badly wrong when an agent claimed two passing tests on a run
that executed zero. Rust's error handling makes it possible to do this properly. Design
for it explicitly."*

Three halves, because the brief has three clauses.

## 1. The donor, executed rather than read

v1 has a written fix for this class of defect — `docs/FIX_FALSE_POSITIVE_COMPLETIONS.md`,
*"Status: IMPLEMENTED (Feb 12, 2026) — All 3 verification tests pass"* — and the module
that carries it opens with *"Prevents agents from hallucinating test success."* So the
question is not what the code says. It is what the code returns.

`v1_parser.py` executes pytest and `python -m unittest` in a scratch tree, in the six
states a run can end in, and feeds the **real bytes and the real exit status** to v1's own
`parse_test_output`. `v1_output.py` imports v1's `_parse_from_execution_logs` and
`parse_agent_output` at `d5528ea` and reads back the `status` and `confidence` a task
record would have carried. `v1_safety_net.mjs` ports `taskExecutor.ts`'s
`handleTaskCompletion` guard and `detectTestFailures` byte-for-byte and runs them over the
records the two probes upstream produced.

## 2. The corpus this project already has

1,369 preserved cells, of which 266 are Q56 **Rust** cells whose work dirs are still on
disk. Two independent readings of each:

* **Did a test actually run?** A subject that runs the crate's own tests leaves a test
  binary in `target/*/deps` that the verifier's `cargo test --test hidden_gate` never
  builds. `control.py` establishes that discriminator by executing all four commands on a
  fresh fixture; **run it before quoting any number from `ran.py`.**
* **What did the subject say?** `ran.py` classifies the subject's own prose by rule, keeps
  the sentence every rule fired on, and joins the two readings to the verifier's recorded
  verdict.

`visible.py` then answers the next question — *was the claim true?* — by re-running the
suite the subject could see on the tree it actually delivered, in a scratch copy with the
verifier's hidden gate removed.

## 3. The type, compiled

`report/` is the design, written as a Rust crate so its properties are assertions rather
than prose. It reads the same captured bytes as the donor probes (`captured/`, written by
`v1_parser.py`) and turns the eight real run-endings into outcomes.

## The probes

| file | what it does | output |
|---|---|---|
| `control.py` | establishes the forensic discriminator: four cargo commands on a fresh Q01 fixture, and which of them leaves a crate-named test binary | `control-results.json` |
| `ran.py` | 266 Rust cells: what the subject said about tests, whether one ran, and whether it ran *before* the last edit | `ran-results.json`, `ran-out.txt` |
| `visible.py` | re-runs the visible suite on every clean-arm delivered tree, hidden gate removed | `visible-results.json`, `visible-out.txt` |
| `v1_parser.py` | real pytest / unittest output in six ending states, fed to v1's `parse_test_output` | `v1_parser-results.json`, `captured/` |
| `v1_output.py` | v1's `_parse_from_execution_logs` and `parse_agent_output`, imported and called | `v1_output-results.json` |
| `v1_safety_net.mjs` | v1's `handleTaskCompletion` safety net, ported verbatim, over those records | `v1_safety_net-results.json` |
| `shared_target.py` | a green `cargo test` that measured nothing: two trees, one package name, one shared `CARGO_TARGET_DIR` | `shared_target-results.json` |
| `report/` | the 2.0 outcome type, 11 tests, run against `captured/` | `cargo test` |

## Running them

The donor probes need `pydantic` (v1's schemas) and `pytest` (to produce the output), and
neither is a project dependency, so they are installed into a scratch directory and put on
`PYTHONPATH` rather than into the host interpreter:

```
python -m pip install --target <scratch>/pylibs pydantic pytest
PYTHONIOENCODING=utf-8 PYTHONPATH=<scratch>/pylibs python v1_parser.py <scratch>/parser
PYTHONIOENCODING=utf-8 PYTHONPATH=<scratch>/pylibs python v1_output.py > v1_output-results.json
node v1_safety_net.mjs > v1_safety_net-results.json
```

`PYTHONIOENCODING=utf-8` is not optional: v1 prints `⚠️` on its log-fetch fallback path and
the host console is cp1252, so without it the donor's own error handler raises
`UnicodeEncodeError` and takes the probe down with it.

The corpus probes need nothing but the repository and a `cargo`:

```
python control.py <scratch>/ctl > control-results.json     # run this first
python ran.py > ran-results.json 2> ran-out.txt
python visible.py <scratch>/visible > visible-results.json 2> visible-out.txt
python shared_target.py <scratch>/shared > shared_target-results.json
cd report && cargo test
```

## Traps this spike walked into, all of them recorded in the code

* **`cargo test --lib` is not "the suite the subject could see."** The first draft of
  `visible.py` used it and read five honest claims as unbacked, because the subject had
  written its own `tests/ring_buffer_tests.rs`.
* **One shared `CARGO_TARGET_DIR` across two trees of the same package silently runs the
  wrong binary.** The second draft of `visible.py` shared one to save the rebuilds — item
  6 F331's saving — and cargo reported `ok. 0 passed` on a tree with eleven tests, exit 0,
  printing `Fresh`. `shared_target.py` is the minimal reproduction, and it is a hazard for
  the shared build cache item 6 recommends.
* **The honest classifier invented a count on its first run.** `counts_from` read
  unittest's `FAILED (failures=2)` as no failures — the number is inside a `key=value`
  token, not a `<n> <word>` pair — and reported two passes on a run where both tests
  failed. Caught by running it; there is now a test named after it.
* **A pooled rate would have invented a finding here too.** Seven cells assert that tests
  pass with no test run, and all seven are in the `deny-first-edit` and
  `redirect-first-edit` arms, where the sentence is a prediction about a patch the harness
  would not let the subject apply. Stratify by arm before quoting anything.
