# w11-artifacts — the five handoff artifacts as Rust types, and what breaks between the type and the model

Probes run 2026-08-22 for **W11 item 3 (handoff artifact schemas)**. Findings **F252–F269** in
`research/W11-stages.md`.

Everything here is re-runnable from a clean checkout with no scratchpad clone: the fixture is
`corpus/suites/k/tasks/finish_the_cancelled_status`, which is in this repository — 16 files, ~9.4k
tokens, a real four-site bug, one correct decoy consumer, and a reference solution the suite's own
verifier accepts. (`w11-tier`'s probes hardcoded a scratchpad path from the session that made them;
this set deliberately does not.)

Held constants for every GPU probe, identical to W11 item 2: champion `qwen3.6-35b-a3b-mtp@iq3_s`,
loaded `-c 65536 --gpu max --parallel 1 -y`, nothing else resident, LM Studio on `:1234`,
temperature 0, `max_tokens` 8192.

## Layout

| path | what it is |
|---|---|
| `artifacts/` | Rust crate: the five artifact types, their JSON Schemas, and the tests holding the rules |
| `artifacts/src/wire.rs` | what a model is asked to emit — all strings, no provenance, no `Default` |
| `artifacts/src/checked.rs` | what the pipeline carries after the recorder confronts a wire value with the world |
| `artifacts/src/emit.rs` | the emission order per artifact, the decision key per artifact, and the test that refuses to let a decision come first |
| `schemas/*.json` | the shipped schemas, after `emit::apply` |
| `payloads/*.json` | what the model actually returned, per arm |

| script | question | raw output |
|---|---|---|
| `chain.py` | does a schemars-derived schema survive to the model and back into `serde`? | `chain-run1.txt`, `chain-results.json` |
| `order.py` | why did the constrained Judge contradict its own rationale? | `order-run1.txt`, `order-results.json` |
| `enumbias.py` | field order, or the enum's own value order? | `enumbias-run1.txt`, `enumbias-results.json` |
| `prefix.py` | does *any* field in front fix it, or only one that argues? | `prefix-run1.txt`, `prefix-results.json` |
| `criterion.py` | what does a generated acceptance criterion measure? (generation) | `criterion-run1.txt` |
| `reclassify.py` | the same criteria, through a runner with a self-test | `criterion-run2-reclassified.txt`, `criterion-results.json` |
| `convention.py` | does BCF's prose contract survive on this model? | `convention-run1.txt`, `convention-raw.txt` |
| `artifacts evolve` | append-only log vs. a type that gained a field | `evolve-run1.txt` |
| `artifacts bcf-parse` | BCF's critique parser, ported verbatim, over ten plausible formats | `bcf-cases.txt` → `bcf-parse-run1.txt`; real output → `bcf-parse-real.txt` |
| *(shipped-schema check)* | does the schema actually written to `schemas/verdict.json` get it right? | `shipped-run1.txt`, `shipped-results.json` |

```
cd artifacts && cargo test && cargo run -- schemas ../schemas   # types, rules, schemas
cd .. && python chain.py && python order.py && python enumbias.py && python prefix.py
python criterion.py && python reclassify.py && python convention.py
```

## What came out

**1. The chain holds.** `schemars` output sent verbatim at `strict: true` — `$defs`, `$ref`,
`type: ["string","null"]`, and `Option` fields omitted from `required` — is accepted by the backend,
constrains the output (proved with a control enum of `["affirmative","negative"]`, which came back),
and deserialises into the real Rust type under `deny_unknown_fields`. 6 of 6. §10's premise that
"Rust's type system should make these contracts enforceable" survives contact with a derived schema.

**2. 🚨 The emission order of a schema's fields decides the answer.** A Judge asked for `call` as the
first key of its object answered `pass` against a failed acceptance criterion **14 times out of 14**,
while writing a rationale in the same object that argued for `fail` — *"Therefore, the only valid
verdict is FAIL."* With any field that carries the argument in front of it, **17 out of 17** correct.
Both confounds ruled out: reversing the enum's own value order changed nothing either way, and a
zero-information prefix (`{"artifact_version":"v1"}`) did not help (0/3). A neutral list is unstable
(2/3). It is specifically the reasoning that has to come first.

**3. Two silent layers destroy that order, and the first is not `schemars`.** `serde_json`'s default
`Map` is a `BTreeMap`: without the `preserve_order` feature — invisible on the dependency line, no
warning, no compile error — every object is re-sorted alphabetically on serialisation. `schemars`
preserves declaration order; declaration order then puts the decision first anyway, because that is
how a person writes a verdict down. `emit.rs` fixes both and a test holds it.

**4. 🚨 Of 35 model-generated acceptance criteria, none binds honestly.** 22 exit 0 on the unfixed
tree; 8 are textual proxies (adding the single comment line `# CANCELLED is handled elsewhere` flips
one from red to green while the bug is untouched); 4 exit non-zero on an `ImportError` for a symbol
the model invented, which is *unrunnable*, never a fail; and the 1 behavioural one is still red
against the reference solution — it can only be satisfied by deleting the SLA feature. 14 of the 35
carry an explicit escape hatch: `||` branches that exit 0, negated greps for absent strings,
`getattr(mod, 'name', lambda s: True)`. One prints `All status decisions correctly handle CANCELLED.`
on a tree where none of them do.

**5. The prompt-only arm fails at the type, not at the JSON.** Two of three unconstrained arms
returned JSON that `json.loads` accepts and `serde_json::from_str` rejects — the model copied the
schema's own `$schema` and `title` keys into its answer. All three donors' tolerant parsers would
have read the payload happily and never mentioned it.

**6. Constrained output is 2–3× cheaper**, and the reasoning trace is **87–97%** of the completion
for every structured artifact. The output budget is not being spent on the artifact.

**7. Append-only and "no `Default`" collide.** Adding one required field breaks replay of every
older event; `#[serde(default)]` is `result.score || 5` in Rust; `deny_unknown_fields` blocks the
downgrade path and dropping it silently discards fields. Versioned `kind`s are the only discipline
that satisfies both.

**8. BCF's prose contract survives on this model 5/5** — the case for types is not that the model
will not comply. It is that when it does not, the failure is silent: a numbered list turns the five
scores into `1, 2, 3, 4, 5`, moves the average 7.70 → 3.00, extracts all five defect strings so the
output looks complete, and BCF's own all-5.0 detector cannot fire.

## Two probes that had to be thrown away first

Recorded because the numbers they produced were confident, complete, and wrong — and because the
distinction they got wrong (*cannot run* vs *fails*) is the same one item 2 recommendation 6 is
about.

- Run 1 of `criterion.py` shelled out with `shell=True`, so `python3` resolved to this host's
  Microsoft Store shim: exit 9009, "Python was not found", **every criterion classified `binds`**.
- Run 1 of `reclassify.py` called `bash`, which on this host is WSL's: `execvpe(/bin/bash) failed`,
  exit 1, **every criterion classified `unrunnable`**.

`reclassify.py` now names Git Bash explicitly, shims `python3` to the interpreter that exists, and
carries a seven-check `selftest()` that refuses to print a tally if the runner cannot tell exit 0
from exit 1, find the fixture, or run the fixture's own green suite.
