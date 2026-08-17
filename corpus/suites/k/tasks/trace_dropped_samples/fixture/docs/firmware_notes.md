# Device firmware notes

Field notes on what the sensor units actually put on the wire. Kept here because
the wire format has drifted twice and both drifts cost us a week of bad data.

## Revision A (units `dev-a1`, `dev-a2`)

The original format. Fields:

```json
{"t_ms": 0, "channel": "temp_c", "value": 21.5, "flag": "ok", "device": "dev-a1"}
```

- Quality flags are **lower-case**: `ok`, `warn`, `fault`.
- Channel names are lower-case, except vibration, which rev A calls `vib_mm_s`.
- `fault` readings are emitted rather than suppressed, on the reasoning that the
  roll-up should be the thing that decides to discard them.

## Revision B (units `dev-b1`, `dev-b2`)

Shipped with the 2.3 firmware. Two changes, both of which have bitten us:

1. **Quality flags are UPPER-CASE**: `OK`, `WARN`, `FAULT`. The vendor considers
   this a cosmetic change. It is not — anything comparing a flag against a
   literal set has to fold case first.
2. Several field names were shortened on the wire to save bytes:
   `t_ms` → `ts_ms`, `channel` → `chan`, `value` → `val`, `flag` → `quality`,
   `device` → `dev_id`.

`pipeline/normalize.py` is the single place that reconciles all of this.
`canonical_flag()` folds case; `canonical_record()` resolves the field aliases;
`canonical_channel()` folds case and maps `vib_mm_s`.

> **The rule that follows from this, and it is the one we keep re-learning:**
> any comparison against `constants.VALID_FLAGS` or `constants.KNOWN_CHANNELS`
> must happen on a value that has already been through the matching
> `normalize.canonical_*` helper. Those constant sets are written in
> revision A's spelling. Comparing a raw rev-B value against them does not
> raise — it simply never matches, and the sample is dropped as unusable.

## Revision C

Not shipped. Expected to keep rev B's casing and revert the field names.

## Deployment

As of the current run, the fleet is mixed: `dev-a1` and `dev-a2` are still on
rev A, `dev-b1` and `dev-b2` were upgraded to rev B. A roll-up that quietly
loses one revision therefore loses roughly half the fleet, and the remaining
half still produces a plausible-looking report.
