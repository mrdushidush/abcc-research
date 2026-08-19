#!/usr/bin/env python3
"""W3 item 3 - durability spike: what does one durable state transition cost?

Answers three questions the durability design turns on:

  1. Can the event log absorb a heartbeat per token batch (OQ-W3-3)?
  2. What do SQLite's two durability knobs actually cost on this machine?
  3. Is boot-as-replay (rebuild the projection from the log) affordable, or
     does it need a snapshot?

Plus a control: the mechanism the family uses today - a whole-file JSON
rewrite of a mutable status document (Claudette `run/research.rs:731`,
BCF `db.rs:29`) - measured at the same update rate.

Stdlib only (`sqlite3`, `json`, `time`), same house style as the W2 spike.

CAVEAT, stated up front: this measures SQLite and the filesystem through
CPython, not through rusqlite. Per-call interpreter overhead inflates the
cheap configurations and is invisible in the expensive ones, which are
fsync-bound. Read the ratios, not the absolute rates; the ratios are disk
behaviour and carry over.

Usage:  python append_bench.py [--dir DIR] [--n N] [--replay-n N]
"""

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
import time

SCHEMA = """
CREATE TABLE event (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id    TEXT    NOT NULL,
    attempt_id TEXT,
    kind       TEXT    NOT NULL,
    payload    TEXT    NOT NULL,
    at_unix_ms INTEGER NOT NULL
);
CREATE TABLE task_status (
    task_id   TEXT    PRIMARY KEY,
    state     TEXT    NOT NULL,
    since_seq INTEGER NOT NULL,
    evidence  TEXT
);
CREATE INDEX event_task ON event(task_id, seq);
"""

# A representative event payload: a tool-call observation, ~200 bytes, which is
# what the ExecutionLog row shape (ABCC) actually carries per step.
PAYLOAD = json.dumps({
    "thought": "reading the assigner to find the claim path",
    "action": "read_file",
    "input": {"path": "packages/api/src/services/taskAssigner.ts", "lines": [40, 90]},
    "elapsed_ms": 143,
})


def fresh_db(path, journal, sync):
    if os.path.exists(path):
        os.remove(path)
    for suffix in ("-wal", "-shm", "-journal"):
        if os.path.exists(path + suffix):
            os.remove(path + suffix)
    conn = sqlite3.connect(path, isolation_level=None)
    conn.execute("PRAGMA journal_mode=" + journal)
    conn.execute("PRAGMA synchronous=" + sync)
    conn.executescript(SCHEMA)
    return conn


def bench_append(conn, n, per_tx, with_status):
    """Append `n` events. `per_tx` events per transaction. `with_status` also
    upserts the status projection row inside the same transaction - the
    `apply()` write path from W3 item 1 section 3."""
    now = int(time.time() * 1000)
    t0 = time.perf_counter()
    i = 0
    while i < n:
        conn.execute("BEGIN IMMEDIATE")
        for _ in range(min(per_tx, n - i)):
            conn.execute(
                "INSERT INTO event(task_id, attempt_id, kind, payload, at_unix_ms)"
                " VALUES (?,?,?,?,?)",
                ("task-%d" % (i % 8), "attempt-%d-1" % (i % 8), "tool_call", PAYLOAD, now + i),
            )
            if with_status:
                conn.execute(
                    "INSERT INTO task_status(task_id, state, since_seq, evidence)"
                    " VALUES (?,?,last_insert_rowid(),?)"
                    " ON CONFLICT(task_id) DO UPDATE SET"
                    " state=excluded.state, since_seq=excluded.since_seq,"
                    " evidence=excluded.evidence",
                    ("task-%d" % (i % 8), "Engaged", "attempt-%d-1" % (i % 8)),
                )
            i += 1
        conn.execute("COMMIT")
    return time.perf_counter() - t0


def bench_json_rewrite(path, n, tasks):
    """The control: the family's current mechanism. A mutable status document
    rewritten whole on every update (`std::fs::write`, no temp+rename)."""
    doc = {
        "manifest_hash": "0" * 64,
        "started_unix": int(time.time()),
        "phase": "batches",
        "batches": [
            {"id": t, "state": "pending", "attempts": 0, "findings": 0, "wall_secs": 0}
            for t in range(tasks)
        ],
    }
    t0 = time.perf_counter()
    for i in range(n):
        doc["batches"][i % tasks]["attempts"] += 1
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2)
    return time.perf_counter() - t0


def bench_replay(conn, expect):
    """Boot = rebuild the projection from the log (W3 item 1 section 3)."""
    t0 = time.perf_counter()
    state = {}
    seen = 0
    for seq, task_id, kind in conn.execute(
        "SELECT seq, task_id, kind FROM event ORDER BY seq"
    ):
        state[task_id] = (kind, seq)
        seen += 1
    elapsed = time.perf_counter() - t0
    assert seen == expect, "replayed %d, expected %d" % (seen, expect)
    return elapsed, len(state)


def db_bytes(path):
    total = os.path.getsize(path)
    for suffix in ("-wal", "-shm"):
        if os.path.exists(path + suffix):
            total += os.path.getsize(path + suffix)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=None, help="where to put the scratch DB")
    ap.add_argument("--n", type=int, default=2000, help="appends per configuration")
    ap.add_argument("--replay-n", type=int, default=100000, help="events in the replay log")
    args = ap.parse_args()

    work = args.dir or tempfile.mkdtemp(prefix="w3-dur-")
    os.makedirs(work, exist_ok=True)
    db = os.path.join(work, "bench.sqlite")
    print("scratch dir: %s" % work)
    print("appends per configuration: %d\n" % args.n)

    configs = [
        ("DELETE + synchronous=FULL  (SQLite default; recall.rs)", "DELETE", "FULL", 1, True),
        ("WAL    + synchronous=FULL", "WAL", "FULL", 1, True),
        ("WAL    + synchronous=NORMAL", "WAL", "NORMAL", 1, True),
        ("WAL    + NORMAL, event only (no status upsert)", "WAL", "NORMAL", 1, False),
        ("WAL    + NORMAL, 16 events per transaction", "WAL", "NORMAL", 16, True),
    ]
    print("%-52s %10s %10s" % ("configuration", "events/s", "us/event"))
    print("-" * 74)
    for label, journal, sync, per_tx, with_status in configs:
        conn = fresh_db(db, journal, sync)
        elapsed = bench_append(conn, args.n, per_tx, with_status)
        conn.close()
        print("%-52s %10.0f %10.1f" % (label, args.n / elapsed, elapsed / args.n * 1e6))

    print()
    print("%-52s %10s %10s" % ("control: whole-file JSON rewrite", "updates/s", "us/update"))
    print("-" * 74)
    for tasks in (10, 200, 2000):
        jpath = os.path.join(work, "progress.json")
        n = min(args.n, 500 if tasks >= 2000 else args.n)
        elapsed = bench_json_rewrite(jpath, n, tasks)
        size = os.path.getsize(jpath)
        label = "  document holding %d task rows (%d KiB)" % (tasks, size // 1024)
        print("%-52s %10.0f %10.1f" % (label, n / elapsed, elapsed / n * 1e6))

    print()
    print("boot = replay: rebuild the projection from the log")
    print("-" * 74)
    conn = fresh_db(db, "WAL", "NORMAL")
    build = bench_append(conn, args.replay_n, 500, False)
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    elapsed, tasks = bench_replay(conn, args.replay_n)
    size = db_bytes(db)
    conn.close()
    print("  log built:        %s events in %.2f s (%s/s, 500 per tx)"
          % ("{:,}".format(args.replay_n), build, "{:,.0f}".format(args.replay_n / build)))
    print("  on disk:          %.1f MiB (%.0f bytes/event)"
          % (size / 1024 / 1024, size / args.replay_n))
    print("  full replay:      %.0f ms for %s events -> %d task projection rows"
          % (elapsed * 1000, "{:,}".format(args.replay_n), tasks))
    print("  replay rate:      %s events/s" % "{:,.0f}".format(args.replay_n / elapsed))

    if args.dir is None:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
