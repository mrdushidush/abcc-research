# job tracker

Loads a snapshot of jobs and prints the operational report: counts, SLA
breaches, charges, retry candidates, notifications.

```
python3 run.py data/jobs.json
```

`now` comes from the snapshot rather than the clock, so the report is
reproducible.

## Modules

| Module | Role |
|---|---|
| `jobs/status.py` | the status vocabulary, `TERMINAL`/`ACTIVE`, and `TRANSITIONS` |
| `jobs/model.py` | the `Job` record, durations and wait times |
| `jobs/queue.py` | the only place a status change happens; enforces `TRANSITIONS` |
| `jobs/validate.py` | record shape checks, run before anything branches |
| `jobs/sla.py` | is this job late? |
| `jobs/charges.py` | is this job billable, and for how much? |
| `jobs/summary.py` | which bucket does it count in, and the rates |
| `jobs/retry.py` | should the scheduler requeue it? |
| `jobs/notify.py` | does the customer hear about it? |
| `jobs/dashboard.py` | labels, colours, glyphs — presentation only |

## Status semantics

**`docs/status_lifecycle.md` is the specification.** Six modules in the table
above branch on status, and they all have to agree with it. The vocabulary lives
in one file; the *meaning* of each status is distributed across every consumer,
which is the structural weakness of this design and the reason that document
exists.

## History

- **4.2** added `cancelled`, with the console's cancel button. The constant, the
  transitions and the operator flow all shipped in that release.
- 4.1 added per-kind charge rates.
- 4.0 split `sla.py` out of `summary.py`.

## Known issues

- The unit tests cover each module in isolation and cover the status vocabulary
  thoroughly. Nothing asserts what a *consumer* does with a given status.
- `notify` has no delivery retry; a dropped message is dropped.
- `charges` uses floats for pence.
