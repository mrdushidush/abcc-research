"""W11 item 5 — does ABCC v1's abort endpoint stay reachable during an execution?

v1 declares `async def execute_task(...)` (packages/agents/src/main.py:236) and calls
the synchronous `crew.kickoff()` inside it (:381). `/execute/abort` (:592) and
`/health` (:657) are also `async def`. If a blocking call in an `async def` handler
occupies the event loop, no other request is served while a task runs — which would
make the only abort path in the system unreachable exactly when it is needed.

This reproduces the shape with the smallest possible program: one `async def` handler
that blocks (as `crew.kickoff()` does), one that does not, and a control where the
blocking handler is `def` instead (FastAPI's threadpool path).

Run:  python fastapi_blocking_probe.py
"""
import subprocess, sys, time, threading, urllib.request, json, os, textwrap, socket

APP = textwrap.dedent('''
    import time
    from fastapi import FastAPI
    app = FastAPI()

    @app.get("/block_async")          # v1's shape: blocking call inside async def
    async def block_async():
        time.sleep(6)
        return {"done": True}

    @app.get("/block_sync")           # control: plain def -> FastAPI threadpool
    def block_sync():
        time.sleep(6)
        return {"done": True}

    @app.get("/abort")                # v1's abort/health shape
    async def abort():
        return {"aborted": True}
''')

def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p

def get(url, timeout=15):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read()
        return time.perf_counter() - t0, None
    except Exception as e:
        return time.perf_counter() - t0, type(e).__name__

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(here, "_probe_app.py")
    open(app_path, "w", encoding="utf-8").write(APP)
    port = free_port()
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "_probe_app:app",
                             "--port", str(port), "--log-level", "warning"],
                            cwd=here, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(80):
            if get(base + "/abort", timeout=1)[1] is None: break
            time.sleep(0.25)
        else:
            print("server never came up"); return

        print(f"baseline /abort while idle: {get(base + '/abort')[0]*1000:.0f} ms\n")
        for path in ("/block_async", "/block_sync"):
            res = {}
            t = threading.Thread(target=lambda: res.update(zip(("dt", "err"), get(base + path, 30))))
            t.start(); time.sleep(1.0)          # let the blocking request take hold
            dt, err = get(base + "/abort", timeout=20)
            t.join()
            label = "async def (v1's shape)" if path == "/block_async" else "plain def (threadpool)"
            print(f"{label:26} blocking handler sleeps 6 s")
            print(f"    /abort answered in {dt*1000:8.0f} ms  err={err}")
            print(f"    -> abort endpoint was {'BLOCKED for the whole task' if dt > 3 else 'reachable'}\n")
    finally:
        proc.terminate()
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired: proc.kill()
        try: os.remove(app_path)
        except OSError: pass

main()
