#!/usr/bin/env python3
"""W8 spike (THROWAWAY): is the per-turn `in=/out=` line per-TURN or
session-CUMULATIVE?

Code says cumulative (usage.rs:44-50 only ever +=; conversation.rs:858 hands
back cumulative_usage()). This runs a multi-turn session to confirm, because a
single-turn session cannot tell the two apart.

If cumulative: in=/out= strictly increase across turns, and per-turn cost is the
DIFFERENCE between consecutive lines.
"""
import os, subprocess, sys, threading, time, queue, re

WS = sys.argv[1]
MODEL = sys.argv[2] if len(sys.argv) > 2 else "qwen3.5-4b"
TIMEOUT = float(sys.argv[3]) if len(sys.argv) > 3 else 300.0

TURNS = os.environ.get("PROBE_TURNS", "").split("|||") if os.environ.get("PROBE_TURNS") else [
    "Say exactly: hello",
    "Say exactly: goodbye",
    "Say exactly: three",
]

env = dict(os.environ)
env.update({
    "NO_COLOR": "1",
    "CLAUDETTE_OPENAI_COMPAT": "1",
    "OLLAMA_HOST": "http://localhost:1234",
    "CLAUDETTE_SKIP_OLLAMA_PROBE": "1",
    "CLAUDETTE_MODEL": MODEL,
    "CLAUDETTE_CODER_MODEL": MODEL,
    "CLAUDETTE_NUM_CTX": "32768",
    "CLAUDETTE_CODER_NUM_CTX": "32768",
    "CLAUDETTE_WORKSPACE": WS,
})
env.pop("CLAUDETTE_AUTO_APPROVE", None)

t0 = time.monotonic()
def ts(): return round((time.monotonic() - t0) * 1000)

q = queue.Queue()
p = subprocess.Popen(["claudette"], cwd=WS, env=env,
                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE, bufsize=0)

def pump(stream, name):
    buf = b""
    while True:
        b = stream.read(1)
        if not b:
            q.put((name, "EOF", "")); return
        buf += b
        if b == b"\n":
            q.put((name, "LINE", buf.decode("utf8", "replace").rstrip("\r\n"))); buf = b""
        elif buf.endswith(b"or type a redirect] "):
            q.put((name, "GATE", buf.decode("utf8", "replace"))); buf = b""

threading.Thread(target=pump, args=(p.stdout, "OUT"), daemon=True).start()
threading.Thread(target=pump, args=(p.stderr, "ERR"), daemon=True).start()

def send(line, why):
    print(f"[{ts():>7}ms] IN   {why}: {line!r}", flush=True)
    p.stdin.write((line + "\n").encode()); p.stdin.flush()

TURN_RE = re.compile(r"turn iter=(\d+) in=(\d+) out=(\d+)")
rows = []
idx = 0

time.sleep(1.5)
send(TURNS[idx], f"turn-{idx+1}")

deadline = time.monotonic() + TIMEOUT
while time.monotonic() < deadline:
    try:
        name, kind, payload = q.get(timeout=0.5)
    except queue.Empty:
        if p.poll() is not None: break
        continue
    if kind == "EOF":
        continue
    if kind == "GATE":
        send("y", "approve")
        continue
    txt = payload
    if txt.strip():
        print(f"[{ts():>7}ms] {name}  {txt}", flush=True)
    m = TURN_RE.search(txt)
    if m:
        it, tin, tout = int(m.group(1)), int(m.group(2)), int(m.group(3))
        rows.append((idx + 1, it, tin, tout))
        idx += 1
        if idx < len(TURNS):
            send(TURNS[idx], f"turn-{idx+1}")
        else:
            send("exit", "end session")
            deadline = min(deadline, time.monotonic() + 10)

try: p.stdin.close()
except Exception: pass
try: p.wait(timeout=10)
except Exception: p.kill()

print("\n=============== USAGE ACCOUNTING ===============")
print(f"{'turn':>4} {'iter':>5} {'in=':>9} {'out=':>7} {'d(in)':>9} {'d(out)':>8}")
pin = pout = 0
for (t, it, tin, tout) in rows:
    print(f"{t:>4} {it:>5} {tin:>9} {tout:>7} {tin-pin:>9} {tout-pout:>8}")
    pin, pout = tin, tout
if len(rows) >= 2:
    mono_in = all(rows[i][2] >= rows[i-1][2] for i in range(1, len(rows)))
    mono_out = all(rows[i][3] >= rows[i-1][3] for i in range(1, len(rows)))
    print(f"\nstrictly non-decreasing across turns: in={mono_in} out={mono_out}")
    print("VERDICT:", "SESSION-CUMULATIVE (per-turn cost = the delta column)"
          if mono_in and mono_out else "PER-TURN")
