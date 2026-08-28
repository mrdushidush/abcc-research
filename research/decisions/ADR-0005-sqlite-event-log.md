# ADR-0005 — A SQLite event log, WAL + `synchronous=FULL`; status is a projection and boot is replay

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** Claude Code (W3 measurement), ratified by David with `research/SUMMARY.md`
- **Sources:** W3 F166, F167, F168, F169, F170, F171 · W5 F123, F125, F126 · W1 F80
- **Depends on:** ADR-0004 (the writer whose transaction this pragma set makes durable)

## Context

**The donors have three stores and none of them is one.** v1 has a real database and never used it
as one: 🚨 **`prisma.$transaction` occurs exactly once in the whole repository, and it is a read**
(F166, `packages/api/src/routes/tasks.ts:57`) — in a system whose recovery path mutates locks, slot,
status, execution rows and agent in eight steps. The Rust donors keep a JSON document and rewrite it
whole, where a crash inside the save costs the record (F168).

W3 measured the alternatives rather than reasoning about them. `append_bench.py`, this machine, log
on the project NVMe, 2,000 transitions per configuration, where a "transition" is the real `apply()`
shape — **an event row appended and the status projection upserted in the same transaction**:

| Configuration | transitions/s | µs each |
|---|---|---|
| `journal=DELETE`, `synchronous=FULL` — SQLite's default, and what `recall.rs:240` opens with | 293 | 3410 |
| **WAL, `synchronous=FULL`** | **1076** | **929** |
| WAL, `synchronous=NORMAL` | 11197 | 89 |
| WAL, `NORMAL`, 16 events per transaction | 54637 | 18 |

And the control — the family's own mechanism, a status document rewritten whole:

| Control: whole-file JSON rewrite | updates/s | µs each |
|---|---|---|
| 10 task rows (1 KiB) | 3224 | 310 |
| 200 task rows (24 KiB) | 597 | 1674 |
| 2000 task rows (247 KiB) | 68 | 14708 |

🚨 **The rewrite degrades with the run and the append does not** — ten rows to two thousand costs the
rewrite **47×**, because it is O(size of everything) per O(1) change. That is not a micro-optimisation
argument: 2.0's log is also the console's replay source (F123), so it is *designed* to grow.

## Decision

**One SQLite database, one writer process, an append-only `event` table whose `seq INTEGER PRIMARY
KEY AUTOINCREMENT` is the system's only ordering, and a status row that is its projection.**

### The pragmas, two of which are not defaults

```
PRAGMA journal_mode = WAL;          -- not the default; 3.7x on the measured write path
PRAGMA synchronous  = FULL;         -- not the WAL convention; power-loss durability for 929 us
PRAGMA foreign_keys = ON;           -- not the default either
PRAGMA busy_timeout = 5000;         -- readers (the console) must never see a bare SQLITE_BUSY
```

🚨 **`FULL` rather than the conventional `NORMAL` is the one place this overrides received
practice**, and the justification is arithmetic, not taste. SQLite's docs are explicit
(<https://www.sqlite.org/pragma.html>, retrieved 2026-08-19): `NORMAL` under WAL is *"durable across
application crashes"* but *"might roll back following a power loss"*, while `FULL` *"is atomic,
consistent, isolated, and durable (ACID) in WAL mode"*. **One decoded token costs ~13–14 ms**
(70.12–75.84 tok/s, F80), so a `FULL` transition is ~7% of a *single token* — and the log is written
at **action** granularity, not token granularity (F123), where one event covers hundreds of tokens
and seconds of wall clock. Against that unit `FULL` is well under a tenth of a percent. **The usual
tradeoff assumes the write rate is the bottleneck; here it is three orders of magnitude from being
one.**

⚠ Note that `recall.sqlite` runs today on *neither* pragma — `recall.rs:240` opens with SQLite's
defaults, i.e. rollback-journal at 293 transitions/s. 2.0's store is a new file and inherits none of
that.

### Status is a projection; boot is the same code as replay

**F170 measured it rather than assuming it.** A 100,000-event log: built in 0.66 s, **25.1 MiB on
disk at 263 bytes per event**, and **replayed in 94 ms — 1,059,017 events/s**.

- **No snapshot mechanism ships.** The projection rebuild at a scale far beyond anything W5 projects
  (months of real driving is ~16k action-granularity events) costs under a tenth of a second.
- **The crossover where replay reaches one second is ~1M events, ~265 MiB.** That is the number to
  watch, and it is the same number the retention question turns on (OQ-W3-11 / OQ-W5-9).
- **This settles the standard objection to log-primary state** — *you will need snapshots, and then
  you will need to keep them consistent with the log.* Not at this scale, and the threshold is
  measured rather than assumed. Until then a snapshot table is a cache with no cache miss.

### One integer, four roles

`seq` is the event id, the SSE `Last-Event-ID`, the paged-read cursor and the scrub position (F126,
ADR-0012) — **and** the `since:` in every lifecycle variant (ADR-0004), which is what makes *when*
and *where in the replay* the same fact.

## Consequences

- **Boot has one recovery path and it runs on every start, so it cannot rot.** v1's second recovery
  path was the one that had never run when it was needed.
- **The console is a reader.** Two readers or ten make no difference to a worker, which is what makes
  ADR-0006's runtime seam free.
- **Retention is a real open question**, not a deferred one: the log is the replay source, so it
  cannot simply be truncated (OQ-W3-11).
- **The measured rates are a floor, stated plainly.** The bench is CPython's `sqlite3`, not
  `rusqlite`; interpreter overhead inflates the cheap rows and is invisible in the fsync-bound ones.
  The ratios are disk behaviour and carry.
- **Sixteen direct dependencies, and `rusqlite` is already one of them** (bundled).

## Alternatives rejected

- **Port v1's Postgres with mutable rows and statements instead of transactions** — F166/F167 *are*
  this option's observed behaviour, and it needs a container.
- **The family's JSON-document-rewritten-whole** — F168: a crash in the save costs the record, it is
  O(n) with no transaction, and it cannot serve a paged read.
- **An embedded KV store — `redb` or `fjall`** — both alive and ACID, but range scans and secondary
  indexes get hand-rolled, and the one integer stops being a primary key.
- **`cqrs-es` + `sqlite-es`** — an aggregate model rather than per-state contracts, 621 downloads/90d,
  single maintainer, pulls `sqlx`.
- **`apalis` over SQLite** — it retries *jobs*, not lifecycles.
- **Restate, Temporal or DBOS** — every one needs a server process. ▶ W10 should still read Restate's
  journal-and-replay model before designing its own.
- **Adopting Langfuse for the run record** — six services, ~21.5 GiB on a 32 GB box. Take the
  vocabulary, own the store.
- **`tracing` as the run record** — `tracing` diagnoses the binary; the event log *is* the record.
  Mixing them produces two logs that disagree.

## What would falsify this

**The event volume reaches ~1M events, ~265 MiB, in a realistic driving period** — an order of
magnitude beyond W5's projection. Then replay crosses one second, boot stops being free, and a
snapshot table earns its keep. The pragma choice would still stand; only the boot path changes.
