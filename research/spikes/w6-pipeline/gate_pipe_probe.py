"""W6 item 2 - the build/test gate's plumbing, measured.

Item 2 recommends inheriting Claudette's deterministic build+test gate
(`tools/quality.rs:344`, driven by `test_runner.rs:39`) rather than BCF's
LLM-scored stages. Before inheriting a mechanism, run it. Four cells:

  1. Read-after-exit - BCF's shape (`sandbox.rs:126-134`): pipe stdout/stderr,
     wait for the child, THEN read. F202 says a child that outwrites the OS
     pipe buffer blocks forever and is recorded as a timeout. Does it?
  2. Drain-on-threads - Claudette's shape (`test_runner.rs:63`): concurrent
     reader threads. Same child. Does the fix hold?
  3. The composed defect. Claudette's timeout path kills the direct child
     (`test_runner.rs:82`) and then JOINS the reader threads. W3 item 7
     (F206-F212) measured that this kill orphans grandchildren. `cargo test`
     spawns test binaries as grandchildren, and they inherit the pipe write
     end. If the orphan holds it open, the reader never sees EOF and the join
     never returns - a gate that hangs AFTER announcing its timeout.
  4. Does the W3 item 7 fix (a Windows Job Object) close cell 3 too?

stdlib only. Cells 1-3 are portable; cell 4 is Windows-specific via ctypes
and is skipped elsewhere.

    python gate_pipe_probe.py [tmpdir]
"""
import ctypes
import os
import subprocess
import sys
import threading
import time

IS_WIN = sys.platform == "win32"

# How much the noisy child writes. The OS pipe buffer is ~64 KiB on both
# Windows and Linux; 512 KiB is a small `cargo test` run.
NOISY_BYTES = 512 * 1024

# Bounded waits. Every cell that can hang is given a budget and reports
# whether it used all of it, so the probe always terminates.
DEADLOCK_BUDGET = 8.0
JOIN_BUDGET = 10.0


def now():
    return time.monotonic()


# A child that writes NOISY_BYTES to stdout and exits. The shape of any test
# runner with a verbose suite.
NOISY = (
    "import sys\n"
    "n=int(sys.argv[1])\n"
    "chunk='x'*4096\n"
    "w=0\n"
    "while w<n:\n"
    "    sys.stdout.write(chunk); w+=len(chunk)\n"
    "sys.stdout.flush()\n"
)

# A grandchild that holds the inherited stdout handle open without writing,
# then exits. The shape of a test binary still running when its `cargo`
# parent is killed.
HOLDER = (
    "import time,sys,os\n"
    "open(sys.argv[1],'w').write(str(os.getpid()))\n"
    "time.sleep(float(sys.argv[2]))\n"
)


def wrapper_src(pidfile, hold_secs):
    """A wrapper that launches the holder and waits on it, inheriting stdout.

    `cargo test` / `sh -c "..."` / `powershell -Command "..."` all have this
    shape: the supervisor holds a handle to the wrapper, the work and the
    pipe's write end live in a process it does not know about.
    """
    return (
        "import subprocess,sys\n"
        "p=subprocess.Popen([sys.executable,'-c',%r,%r,%r])\n"
        "p.wait()\n" % (HOLDER, pidfile, str(hold_secs))
    )


def wait_for(path, secs=5.0):
    deadline = now() + secs
    while now() < deadline and not os.path.exists(path):
        time.sleep(0.05)
    return os.path.exists(path)


def pid_alive(pid):
    if IS_WIN:
        SYNCHRONIZE = 0x00100000
        h = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if not h:
            return False
        rc = ctypes.windll.kernel32.WaitForSingleObject(h, 0)
        ctypes.windll.kernel32.CloseHandle(h)
        return rc != 0  # WAIT_OBJECT_0 == 0 == exited
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def drain(pipe, out):
    """Claudette's `spawn_pipe_reader`: read to EOF on a dedicated thread."""
    try:
        out.append(pipe.read())
    except Exception:
        out.append(b"")


# 1. read-after-exit: BCF's shape ------------------------------------------

def cell1_read_after_exit():
    exe = sys.executable
    p = subprocess.Popen([exe, "-c", NOISY, str(NOISY_BYTES)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    t0 = now()
    hung = False
    try:
        p.wait(timeout=DEADLOCK_BUDGET)
    except subprocess.TimeoutExpired:
        hung = True
    waited = now() - t0
    if hung:
        # Recover: drain, which unblocks the child, then reap.
        got = p.stdout.read()
        p.wait()
        print("[1] read-after-exit, child writes %d KiB: DEADLOCKED - wait() "
              "used the whole %.1f s budget; the child only finished once the "
              "parent drained (%d KiB recovered)"
              % (NOISY_BYTES // 1024, waited, len(got) // 1024))
    else:
        got = p.stdout.read()
        print("[1] read-after-exit, child writes %d KiB: completed in %.2f s "
              "(%d KiB) - NO deadlock on this platform"
              % (NOISY_BYTES // 1024, waited, len(got) // 1024))
    p.stderr.close()
    return hung


# 2. drain-on-threads: Claudette's shape ------------------------------------

def cell2_drain_on_threads():
    exe = sys.executable
    p = subprocess.Popen([exe, "-c", NOISY, str(NOISY_BYTES)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = [], []
    t0 = now()
    to = threading.Thread(target=drain, args=(p.stdout, out))
    te = threading.Thread(target=drain, args=(p.stderr, err))
    to.start(); te.start()
    try:
        p.wait(timeout=DEADLOCK_BUDGET)
        hung = False
    except subprocess.TimeoutExpired:
        hung = True
    to.join(2.0); te.join(2.0)
    took = now() - t0
    print("[2] drain-on-threads, same child: %s in %.2f s (%d KiB captured)"
          % ("HUNG" if hung else "completed", took,
             (len(out[0]) if out else 0) // 1024))
    return not hung


# 3. timeout + kill while a grandchild holds the write end ------------------

def cell3_kill_with_holder(tmp, hold_secs=25.0, job=None):
    exe = sys.executable
    tag = "job" if job else "plain"
    pidfile = os.path.join(tmp, "holder_%s.pid" % tag)
    if os.path.exists(pidfile):
        os.remove(pidfile)

    p = subprocess.Popen([exe, "-c", wrapper_src(pidfile, hold_secs)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if job is not None:
        assign_to_job(job, p.pid)
    if not wait_for(pidfile):
        print("[3/%s] grandchild never started - inconclusive" % tag)
        p.kill()
        return None
    gc_pid = int(open(pidfile).read())

    out, err = [], []
    to = threading.Thread(target=drain, args=(p.stdout, out))
    te = threading.Thread(target=drain, args=(p.stderr, err))
    to.start(); te.start()

    time.sleep(2.0)  # the "timeout" fires here

    t0 = now()
    if job is not None:
        # W3 item 7's fix: closing the job handle kills the whole tree.
        ctypes.windll.kernel32.CloseHandle(job)
    else:
        p.kill()          # test_runner.rs:82 / sandbox.rs:145
    try:
        p.wait(timeout=5.0)
    except subprocess.TimeoutExpired:
        pass
    # Now the code joins its reader threads (test_runner.rs:85-86).
    to.join(JOIN_BUDGET)
    joined = not to.is_alive()
    te.join(1.0)
    took = now() - t0

    alive = pid_alive(gc_pid)
    print("[3/%s] kill at timeout, grandchild pid %d %s: reader join %s after "
          "%.2f s (budget %.0f s)"
          % (tag, gc_pid, "STILL RUNNING" if alive else "dead",
             "RETURNED" if joined else "STILL BLOCKED", took, JOIN_BUDGET))
    if alive:
        try:
            if IS_WIN:
                subprocess.run(["taskkill", "/F", "/PID", str(gc_pid)],
                               capture_output=True)
            else:
                os.kill(gc_pid, 9)
        except OSError:
            pass
    return joined


# 4. the job-object fix ------------------------------------------------------

class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64),
                ("PerJobUserTimeLimit", ctypes.c_int64),
                ("LimitFlags", ctypes.c_uint32),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", ctypes.c_uint32),
                ("Affinity", ctypes.c_size_t),
                ("PriorityClass", ctypes.c_uint32),
                ("SchedulingClass", ctypes.c_uint32)]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [("ReadOperationCount", ctypes.c_uint64),
                ("WriteOperationCount", ctypes.c_uint64),
                ("OtherOperationCount", ctypes.c_uint64),
                ("ReadTransferCount", ctypes.c_uint64),
                ("WriteTransferCount", ctypes.c_uint64),
                ("OtherTransferCount", ctypes.c_uint64)]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]


JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JobObjectExtendedLimitInformation = 9


def make_job():
    h = ctypes.windll.kernel32.CreateJobObjectW(None, None)
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ctypes.windll.kernel32.SetInformationJobObject(
        h, JobObjectExtendedLimitInformation, ctypes.byref(info),
        ctypes.sizeof(info))
    return h


def assign_to_job(job, pid):
    PROCESS_SET_QUOTA, PROCESS_TERMINATE = 0x0100, 0x0001
    h = ctypes.windll.kernel32.OpenProcess(
        PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
    ok = ctypes.windll.kernel32.AssignProcessToJobObject(job, h)
    ctypes.windll.kernel32.CloseHandle(h)
    if not ok:
        print("    (AssignProcessToJobObject FAILED)")


def main():
    tmp = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(tmp, exist_ok=True)
    print("W6 item 2 - build/test gate plumbing probe")
    print("platform=%s python=%s pipe payload=%d KiB"
          % (sys.platform, sys.version.split()[0], NOISY_BYTES // 1024))
    print()
    cell1_read_after_exit()
    cell2_drain_on_threads()
    cell3_kill_with_holder(tmp)
    if IS_WIN:
        cell3_kill_with_holder(tmp, job=make_job())
    else:
        print("[3/job] skipped - Windows-only")


if __name__ == "__main__":
    main()
