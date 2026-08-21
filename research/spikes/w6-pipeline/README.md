# W6 item 2 — the build/test gate's plumbing

**Question this spike exists to settle:** item 2 ends by recommending that 2.0 inherit Claudette's
deterministic build+test gate (`tools/quality.rs:344`, driven by `test_runner.rs:39`) in place of
BCF's LLM-scored stages. Before inheriting a mechanism, run it. The reading said Claudette's runner
was correct — it drains its pipes on threads and its module doc names the exact bug BCF has. Ten
minutes of probing says the runner is correct **except on the path it takes when a test suite
overruns**, which is precisely the path a verification gate exists to handle.

Run 2026-08-21, two runs agreeing exactly. Raw output: `gate-pipe-results.txt`.

## How to run

```
python gate_pipe_probe.py tmp
```

stdlib only; cell 4 is Windows-specific via `ctypes` and is skipped elsewhere.

## Results

**1 — F202 reproduces, by execution.** BCF's shape (`sandbox.rs:126-134`: pipe both streams, wait
for the child, *then* `read_to_string`) deadlocks on a child that writes 512 KiB — a small `cargo
test` run. `wait()` consumed the whole 8 s budget and the child only finished once the parent
drained. F202 was a reading; it is now a measurement.

```
[1] read-after-exit, child writes 512 KiB: DEADLOCKED - wait() used the whole 8.0 s budget;
    the child only finished once the parent drained (512 KiB recovered)
```

BCF's timeout arm then returns `stdout: String::new()` (`sandbox.rs:146-150`), so the run is
recorded as a timeout **with no output at all** — the verifier gets neither the pass count nor the
failure text.

**2 — Claudette's fix holds on the normal path.** The same child, drained on two reader threads
(`test_runner.rs:64-65`), completes in **0.03 s** with all 512 KiB captured.

**3 — 🚨 but the timeout path hangs, after it has announced the timeout.** Claudette's timeout arm
kills the direct child (`test_runner.rs:82`) and then **joins the reader threads** (`:87-88`),
under a comment that states the assumption: *"Reader threads exit cleanly once the kill closes the
pipe ends."* They do not, when the child had a child of its own. W3 item 7 (F206–F212) measured
that `child.kill()` orphans grandchildren; a grandchild also inherited the **write end of the
pipe**, so the reader never sees EOF:

```
[3/plain] kill at timeout, grandchild pid 16220 STILL RUNNING: reader join STILL BLOCKED
          after 11.01 s (budget 10 s)
```

The join outlived a 10 s budget, twice. This is not a contrived shape: `cargo test` compiles and
then **spawns the test binaries** as separate processes, and Claudette's own `bash` tool runs
`powershell -NoProfile -NonInteractive -Command <cmd>` (`tools/shell.rs:207-221`), a wrapper by
construction. The failure is worse than the one it replaced — BCF returns a wrong answer, this
returns no answer at all.

**4 — W3 item 7's job object closes this too.** With the child assigned to a Windows Job Object
carrying `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, closing the handle kills the tree, the grandchild
dies, the pipe's last write end closes, and the reader join returns **immediately**:

```
[3/job] kill at timeout, grandchild pid 15972 dead: reader join RETURNED after 0.00 s
```

The job object was already costed by the topology spike at **0.04 ms** to create. One mechanism
fixes an orphaned workspace (W3 item 7) and a hung verification gate (this), which is the argument
for putting it in the seam rather than at either call site.

## What this settles for 2.0

1. **Drain concurrently** — never read after wait. Non-negotiable, and cheap.
2. **A timeout must kill the tree, not the handle you happen to hold.** Job object on Windows,
   process group + `killpg` on Unix.
3. **Never join a reader you have not closed.** Even with the tree killed, the join must be
   bounded; an unbounded join inside a timeout handler converts a bounded failure into a hang.
4. **A verification gate's failure modes are its interface.** `Uncertain(timeout)` is a legitimate
   verdict (F161, F218); *no verdict ever* is not, and that is what the inherited code produces.

Recorded as **F220** in `research/W6-verification.md`, item 2.

## Scope and honesty

Measured on Windows 11 only. The pipe-buffer deadlock (cell 1) and the drain fix (cell 2) are
portable and would reproduce on Linux; the orphan-holds-the-pipe result (cell 3) reproduces
anywhere a killed parent's children survive, which is the default on Unix too — but the *fix* in
cell 4 is Windows-specific and its Unix equivalent (process groups) is **not measured here**. The
probe uses Python subprocesses rather than the Rust code itself: it reproduces the shape and the OS
semantics, not the donors' exact binaries. What it proves is that the OS behaves the way the
finding claims; the line-level match to `test_runner.rs:82-88` and `sandbox.rs:126-150` is from
reading.
