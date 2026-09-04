# Units in the barometer pipeline

Sensors report **hectopascals**. Everything downstream of `baro.ingest` is in
**centi-kilopascals** — kPa × 100 — so the alert bounds can be quoted to two
decimals with no float in the pipeline.

    1 hPa = 0.1 kPa = 10 cKPa

**`baro.ingest` is the unit boundary and it is the only one.** A reading that
comes out of `ingest.readings` is already in cKPa. Nothing after it converts
again — a second conversion is not a rounding difference, it is a factor of ten,
and a factor of ten puts every reading in the batch outside the instrument's
range at once.

The bench offsets in `data/offsets.json` are quoted in hPa, because the bench
report gives hPa. They are the one value in `calibrate` that still needs
converting.

## The alert bounds

90.00 to 110.00 kPa — 9000 to 11000 cKPa — is the instrument's operating range.
It is a property of the hardware, not a tuning knob: a barometer that reads
outside it is broken or is not reading pressure.

`MAX_ALERTS` is a circuit breaker. If a whole batch is out of range then the
batch is wrong, not the world.
