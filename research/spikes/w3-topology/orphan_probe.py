"""W3 item 7 - process-boundary probe.

Three questions the topology decision turns on, all cheap to measure and all
answered by opinion in the family's code:

  1. What does spawning a worker PROCESS cost, against a 33.9 s TTFB?
  2. When the supervisor kills a tool child (`child.kill()`, the inherited
     mechanism at `test_runner.rs:82` / `sandbox.rs:145`), do the child's own
     children die with it - or does the work keep running unattended?
  3. Does a Windows Job Object close that gap, and what does it cost?

stdlib only. Windows-specific for #3 via ctypes; #1 and #2 are portable.
"""
import ctypes
import os
import subprocess
import sys
import time

IS_WIN = sys.platform == "win32"


def now():
    return time.monotonic()


# The grandchild: records its pid, then ticks a file every 250 ms. If it is
# still ticking after its parent was killed, it was orphaned.
GRANDCHILD = (
    "import time,sys,os\n"
    "open(sys.argv[1],'w').write(str(os.getpid()))\n"
    "for i in range(600):\n"
    "    f=open(sys.argv[2],'a'); f.write('tick\\n'); f.close()\n"
    "    time.sleep(0.25)\n"
)


def child_src(pidfile, tickfile):
    """A shell-shaped child: launches the grandchild and waits on it.

    This is the shape of `bash -c "cargo test"` or of BCF's
    `run_tool("cargo", ["test", "--quiet"])` - the supervisor holds a handle
    to the wrapper, not to the process doing the work.
    """
    return (
        "import subprocess,sys\n"
        "p=subprocess.Popen([sys.executable,'-c',%r,%r,%r])\n"
        "p.wait()\n" % (GRANDCHILD, pidfile, tickfile)
    )


# 1. process spawn cost -----------------------------------------------------

def spawn_cost(n=20):
    exe = sys.executable
    t0 = now()
    for _ in range(n):
        subprocess.run([exe, "-c", "pass"], capture_output=True)
    per = (now() - t0) / n
    print("[1] child spawn + exit + reap : %.1f ms mean over %d" % (per * 1000, n))

    procs = []
    t0 = now()
    for _ in range(n):
        procs.append(subprocess.Popen([exe, "-c", "import time; time.sleep(5)"],
                                      stdout=subprocess.DEVNULL))
    per = (now() - t0) / n
    print("[1] spawn only, no wait       : %.1f ms mean over %d" % (per * 1000, n))
    for p in procs:
        p.kill()
    for p in procs:
        p.wait()


# 2. the orphan question ----------------------------------------------------

def pid_alive(pid):
    if IS_WIN:
        PROCESS_QUERY_LIMITED = 0x1000
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(h)
        return code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def wait_for(path, secs=10):
    deadline = now() + secs
    while now() < deadline and not os.path.exists(path):
        time.sleep(0.05)
    return os.path.exists(path)


def count_lines(path):
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        return sum(1 for _ in f)


def orphan_test(tmp):
    exe = sys.executable
    pidfile = os.path.join(tmp, "gc_plain.pid")
    tickfile = os.path.join(tmp, "gc_plain.ticks")
    for f in (pidfile, tickfile):
        if os.path.exists(f):
            os.remove(f)

    child = subprocess.Popen([exe, "-c", child_src(pidfile, tickfile)])
    if not wait_for(pidfile):
        print("[2] grandchild never started - inconclusive")
        child.kill()
        return
    gc_pid = int(open(pidfile).read())
    time.sleep(1.0)
    at_kill = count_lines(tickfile)

    # The inherited kill: terminate the direct child only.
    child.kill()
    child.wait()
    time.sleep(2.0)

    after = count_lines(tickfile)
    alive = pid_alive(gc_pid)
    verdict = "STILL RUNNING" if (alive or after > at_kill) else "dead"
    print("[2] plain child.kill(): grandchild pid %d - ticks %d at kill, "
          "%d two seconds later -> %s" % (gc_pid, at_kill, after, verdict))
    if alive:
        try:
            os.kill(gc_pid, 9)
        except OSError:
            pass


# 3. Windows Job Object -----------------------------------------------------

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
    t0 = now()
    h = ctypes.windll.kernel32.CreateJobObjectW(None, None)
    info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    ctypes.windll.kernel32.SetInformationJobObject(
        h, JobObjectExtendedLimitInformation, ctypes.byref(info), ctypes.sizeof(info))
    print("[3] CreateJobObject + SetInformationJobObject: %.2f ms"
          % ((now() - t0) * 1000))
    return h


def assign_to_job(job, pid):
    PROCESS_SET_QUOTA, PROCESS_TERMINATE = 0x0100, 0x0001
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE,
                                           False, pid)
    ok = ctypes.windll.kernel32.AssignProcessToJobObject(job, h)
    ctypes.windll.kernel32.CloseHandle(h)
    print("[3] AssignProcessToJobObject: %s" % ("ok" if ok else "FAILED"))


def job_kill_test(tmp):
    exe = sys.executable
    pidfile = os.path.join(tmp, "gc_job.pid")
    tickfile = os.path.join(tmp, "gc_job.ticks")
    for f in (pidfile, tickfile):
        if os.path.exists(f):
            os.remove(f)

    job = make_job()
    child = subprocess.Popen([exe, "-c", child_src(pidfile, tickfile)])
    assign_to_job(job, child.pid)
    if not wait_for(pidfile):
        print("[3] grandchild never started - inconclusive")
        child.kill()
        return
    gc_pid = int(open(pidfile).read())
    time.sleep(1.0)
    at_kill = count_lines(tickfile)

    t0 = now()
    ctypes.windll.kernel32.CloseHandle(job)   # KILL_ON_JOB_CLOSE fires here
    child.wait()
    elapsed = now() - t0
    time.sleep(2.0)

    after = count_lines(tickfile)
    alive = pid_alive(gc_pid)
    verdict = "STILL RUNNING" if (alive or after > at_kill) else "dead"
    print("[3] closing the job handle killed the tree in %.1f ms - grandchild %d: "
          "ticks %d -> %d -> %s" % (elapsed * 1000, gc_pid, at_kill, after, verdict))
    if alive:
        try:
            os.kill(gc_pid, 9)
        except OSError:
            pass


if __name__ == "__main__":
    tmp = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(tmp, exist_ok=True)
    print("platform=%s python=%s" % (sys.platform, sys.version.split()[0]))
    spawn_cost()
    orphan_test(tmp)
    if IS_WIN:
        job_kill_test(tmp)
