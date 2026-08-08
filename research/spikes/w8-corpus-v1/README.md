# Spike: checking `corpus/` against SPEC v1 (THROWAWAY)

Run 2026-08-08, when the corpus format was frozen as v1. **Throwaway code**, kept as evidence.
The real loader is Rust and is step 2 of the W8 plan; nothing here is a proposal for it.

It exists because a schema whose only example has never been checked against it is a schema that
is *approximately* right — and the entire argument for the provenance block is that approximately
right is not good enough when comparability is the thing being claimed.

## `validate.py` — the ten rejection rules

Implements SPEC.md §13, plus the §5 variant merge and the §10 aggregate arithmetic. Rules are
numbered to match the spec, so a rule that changes there and not here shows up as a numbering gap
rather than as silence.

```
$ python validate.py corpus

  subj claudette-fc1ea22: drive='repl-pipe' caps=['tool_gate', 'redirect', 'undo', 'resume']
  var  u100/fix_sql_inject: control              suite
  var  u100/fix_sql_inject: gated                suite
  var  u100/fix_sql_inject: redirect-first-edit  task-override
  var  u100/fix_sql_inject: deny-first-edit      task-new

  1 task(s) loaded
    fix_sql_inject       verifiable=full  quarantine=with_baseline  in aggregate: NO

  ACCEPTED — every §13 rule holds
```

The four variant lines are the §5 merge working: `control` and `gated` inherited from the suite,
`redirect-first-edit` replaced by the task's own, `deny-first-edit` appended. This is what stops
the importer emitting 90 near-identical `variants.toml` files.

## The negative control

A validator that only ever accepts proves nothing. Four defects injected into a copy, one per
rule class, and each was caught by the rule that should catch it:

| Injected | Caught by |
|---|---|
| `permissions.mode = "prompt"` | rule 3, with the derived-`Ord` reason in the message |
| `prompt` in two provenance lists, `sham` in none | rule 10, both halves separately |
| a `broken` gate point on a task marked `quarantine = "none"` | rule 7 |
| `send_file` naming a file that is not there | rule 4 |

## `gate_example.sh` — the three-point gate against the on-disk task

The gate evidence in `task.toml` was **re-measured against the rewritten verifier**, not copied
from the sweep. This matters: the sweep ran the donor's verifier with its package path, and v1's
verifier imports flat.

```
gate point 1 — every pre-state is a wrong answer and MUST FAIL
  absent    RESULT: FAIL ModuleNotFoundError: No module named 'sql_inject'
  stub      RESULT: FAIL AssertionError:
  fixture   RESULT: FAIL AttributeError: 'NoneType' object has no attribute 'execute'
gate point 2 — fixture + refsol MUST PASS
  refsol    RESULT: PASS donor assertions held
gate point 3 — fixture + sham MUST FAIL
  sham      RESULT: PASS donor assertions held        <-- F8, and why the task is quarantined
```

Verdicts agree with `gate_step1_all90.py` on every tier. The one difference is the absent-tier
error string — `No module named 'tasks'` there, `'sql_inject'` here — which is the flat path
rewrite and not a change in detection. Both are recorded in `task.toml`'s gate evidence, with
`verifier = "rewritten"` marked as the authoritative column.

Same platform caveat as the sweep: Windows host, not the `abcc-agents` container. A Linux re-run
is still the cheap unspent confirmation.

## Reproducing

```bash
cd D:/dev/ABCC_20_powerd_by_claudette
PYTHONUTF8=1 python research/spikes/w8-corpus-v1/validate.py corpus
bash research/spikes/w8-corpus-v1/gate_example.sh
```

`PYTHONUTF8=1` is needed on Windows: the output carries `§` and `—`, and the default cp1252
console encoding mangles them.
