# W3 item 7 — the process-topology probe

**Question this spike exists to settle:** the choice between one binary and a supervisor plus
workers is usually argued on cost and on safety. Both halves are measurable in ten minutes, and one
of them turns out to be a live defect in code both Rust donors already ship.

Run 2026-08-20, two runs agreeing exactly. Raw output: `topology-probe-results.txt`.

## How to run

```
python orphan_probe.py tmp
```

stdlib only; the Job Object half is Windows-specific via `ctypes` and is skipped elsewhere.

## Results

**1 — a process boundary costs nothing at this workload.** 2.4–2.5 ms to spawn a child, 10.5 ms for
a native binary to spawn, exit and be reaped (`cmd /c exit`), 26.5–27.8 ms for an interpreted one
(mostly interpreter startup). Against W1's measured **33.9 s** time-to-first-token at the daily
driver's context, the native figure is **0.03% of one turn**. Neither side of the topology argument
can be won on latency.

**2 — 🚨 the inherited kill orphans the work.** The probe reproduces the exact shape both donors
use — a wrapper process that launches the real worker and waits on it, then `child.kill()` on the
wrapper:

```
[2] plain child.kill(): grandchild pid 29444 - ticks 5 at kill, 13 two seconds later -> STILL RUNNING
```

That wrapper is the normal path, not a contrivance: Claudette's `bash` tool runs
`powershell -NoProfile -NonInteractive -Command <cmd>` (or `sh -c <cmd>`) with a **30 s** timeout
(`tools/shell.rs:207-221`, kill at `test_runner.rs:82`), and BCF kills `cargo` while the test binary
it spawned is a grandchild (`sandbox.rs:145`). Anything slower than the timeout ends with the
orchestrator believing it reclaimed a workspace that is still being written.

**3 — a Windows Job Object closes it for free.** `CreateJobObject` + `SetInformationJobObject` with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` costs **0.04 ms**; closing the handle killed the whole tree in
**1.8–1.9 ms**, grandchild included:

```
[3] closing the job handle killed the tree in 1.9 ms - grandchild 26192: ticks 5 -> 5 -> dead
```

## Caveats

- The Unix half is **not measured here**. The equivalent is `Command::process_group(0)` (safe std
  since Rust 1.64) plus a group kill, and the group kill is the part that needs `libc` or a crate.
- Both the job object and `killpg` are `unsafe` from Rust, which collides with the donor's
  crate-level `unsafe_code = "forbid"`. That trade-off is OQ-W3-24, handed to W7.
- The probe uses Python children, so the absolute spawn numbers are an upper bound for a Rust
  worker; the orphan and job-object results are properties of the OS and do not depend on the
  language.
