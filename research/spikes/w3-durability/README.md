# W3 durability spike — what one durable state transition costs

The reproducible half of `research/W3-orchestration.md` item 3 (F169, F170). One script, stdlib
only — same house style as the W2 spike, so there is nothing to install and nothing to drift.

**All measurements: 2026-08-19**, this machine, scratch database on the project drive (D:, NVMe).
CPython 3.14's `sqlite3`. Two repeat runs, every row within 2%.

## What it answers

The durability design turns on three numbers that nobody in the family ever measured, because
nobody in the family ever used a database in the orchestration path:

1. **Can the log absorb the write rate?** — and specifically, what do SQLite's two durability
   knobs actually cost, so `synchronous=NORMAL` versus `FULL` is a measured choice rather than an
   inherited convention.
2. **Is boot-as-replay affordable**, or does the design need a snapshot mechanism?
3. **How does it compare to what the family does today** — a mutable status document rewritten
   whole on every update (Claudette `run/research.rs:731`, `runtime/session.rs:96`; BCF
   `db.rs:30`)?

The benchmark's unit is the real `apply()` write path from item 1 §3: an event row appended **and**
the status projection row upserted, in one transaction. Not a bare insert.

## Running it

```bash
python append_bench.py                          # scratch dir in %TEMP%, cleaned up after
python append_bench.py --dir D:/dev/.w3-scratch  # pin the drive — the answer is disk-dependent
python append_bench.py --n 5000 --replay-n 500000
```

`--dir` matters. The interesting rows are fsync-bound, so measuring on a different device measures
a different machine.

## Results, 2026-08-19

```
configuration                                          events/s   us/event
--------------------------------------------------------------------------
DELETE + synchronous=FULL  (SQLite default; recall.rs)      293     3409.6
WAL    + synchronous=FULL                                  1076      929.0
WAL    + synchronous=NORMAL                               11197       89.3
WAL    + NORMAL, event only (no status upsert)            14443       69.2
WAL    + NORMAL, 16 events per transaction                54637       18.3

control: whole-file JSON rewrite                      updates/s   us/update
--------------------------------------------------------------------------
  document holding 10 task rows (1 KiB)                    3224      310.2
  document holding 200 task rows (24 KiB)                   597     1674.2
  document holding 2000 task rows (247 KiB)                  68    14707.7

boot = replay
--------------------------------------------------------------------------
  log built:        100,000 events in 0.66 s (151,556/s, 500 per tx)
  on disk:          25.1 MiB (263 bytes/event)
  full replay:      94 ms for 100,000 events -> 8 task projection rows
  replay rate:      1,059,017 events/s
```

## What it proved

- **`FULL` is affordable, so take it.** 929 µs per fully-ACID transition — ~7% of a single decoded
  token (13–14 ms, W1 F80), and the log is written at action granularity, where one event covers a
  tool call's worth of generation (W5 F123). The usual advice to accept `NORMAL`'s power-loss window
  is optimising a resource this design has orders of magnitude to spare of.
- **WAL is not optional.** SQLite's default journal mode costs 3.7× — and it is what
  `recall.rs:240` opens with today, so 2.0's store must set the pragma rather than inherit the
  family's habit.
- **No snapshot mechanism is needed.** 100k events replay in 94 ms. The one-second threshold is
  ~1M events (~265 MiB), which is also the number OQ-W5-9's retention question turns on.
- **The family's mechanism is the only one that gets worse as the run grows.** 10 → 2000 rows costs
  the whole-file rewrite 47×, because it is O(everything) per O(1) change. The append is flat.

## What it does not prove

It measures SQLite and the filesystem **through CPython, not `rusqlite`**. Interpreter overhead
inflates the cheap configurations and is invisible in the fsync-bound ones. Read the ratios — those
are disk behaviour and carry over; treat the absolute rates as a floor. Re-run through `rusqlite`
once the 2.0 crate exists.

It also says nothing about torn writes, which are argued from the source rather than simulated:
`std::fs::write` truncates before writing, and three of the family's four persistence sites treat a
malformed file as a hard error rather than falling back to the last good state (F168).
