# telemetry roll-up

Reads device telemetry as JSONL, filters it, applies per-device calibration,
buckets it into fixed windows and prints a per-channel summary.

```
python3 run.py data/samples.jsonl
```

## Stages

| Stage | Module | In → Out |
|---|---|---|
| ingest | `pipeline/ingest.py` | raw dicts → `Accepted` (samples + drop counters) |
| calibration | `pipeline/calibration.py` | `Accepted` → `Accepted` (values corrected) |
| windowing | `pipeline/windowing.py` | `Accepted` → `[Window]` |
| stats | `pipeline/stats.py` | `[Window]` → `Summary` |
| report | `pipeline/report.py` | `Summary` → text |

`pipeline/normalize.py` is a helper, not a stage. It is the **only** place that
knows how the wire format differs between firmware revisions, and every
comparison against a constant set has to go through it first — see
`docs/firmware_notes.md`.

Supporting modules: `alerts.py` (thresholds over window means), `retention.py`
(downsampling policy), `sinks.py` (json/csv output), `schema.py` (shape checks
used by the tests), `validate.py` (plausibility bounds), `transport.py` (file
reading).

## Design notes

- **A drop is always counted.** Every rejection in ingest increments a reason
  code, because the failure mode this pipeline fears most is losing data while
  continuing to produce a plausible-looking report.
- **Empty windows are emitted, not skipped.** `windowing.split` produces a
  window for every (reported channel, window start) pair in range, including
  ones that received nothing. A hole that is not emitted is a hole nobody can
  notice.
- **`STRICT_EMPTY_WINDOWS` is on.** A window with no usable samples is an error
  rather than a hole, because a silent zero is indistinguishable from a
  genuinely quiet period, and the two mean very different things to whoever is
  reading the graph.

## Known issues

- The fleet is mid-upgrade and runs two firmware revisions at once. See
  `docs/firmware_notes.md` before touching anything that compares a flag or a
  channel name against a literal.
- `retention.apply_policy` has never been run against real 30-day data.
