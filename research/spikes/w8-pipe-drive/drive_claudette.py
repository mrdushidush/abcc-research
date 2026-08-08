#!/usr/bin/env python3
"""W8 spike (THROWAWAY): can a piped harness drive Claudette's REPL,
observe the [y/N] gate on stderr, inject a redirect, and see the turn end?

Proves or disproves the four mechanical premises of the W8 corpus design:
  P1  REPL over a pipe reaches a live permission gate (one-shot cannot).
  P2  Gate prompt is observable on stderr, separately from model text.
  P3  TTFT is samplable as first-byte-on-stdout, during the run.
  P4  The post-turn line on stderr is a usable turn-boundary marker AND
      carries real in=/out= token counts (i.e. cost per task is reachable).
"""
import os, subprocess, sys, threading, time, queue, re

WS = sys.argv[1]
MODEL = sys.argv[2] if len(sys.argv) > 2 else "qwen3.5-4b"
TIMEOUT = float(sys.argv[3]) if len(sys.argv) > 3 else 300.0

env = dict(os.environ)
env.update({
    "NO_COLOR": "1",                     # theme.rs honours this -> plain-text matching
    "CLAUDETTE_OPENAI_COMPAT": "1",
    "OLLAMA_HOST": "http://localhost:1234",
    "CLAUDETTE_SKIP_OLLAMA_PROBE": "1",
    "CLAUDETTE_MODEL": MODEL,
    "CLAUDETTE_CODER_MODEL": MODEL,
    "CLAUDETTE_NUM_CTX": "32768",
    "CLAUDETTE_CODER_NUM_CTX": "32768",
    "CLAUDETTE_WORKSPACE": WS,
})
# DELIBERATELY NOT SET: CLAUDETTE_AUTO_APPROVE. That flag is what the Q56
# battery sets, and it is exactly what makes the gate unobservable.
env.pop("CLAUDETTE_AUTO_APPROVE", None)

t0 = time.monotonic()
def ts():
    return round((time.monotonic() - t0) * 1000)

events = []          # (ms, stream, kind, text)
q = queue.Queue()

p = subprocess.Popen(
    ["claudette"], cwd=WS, env=env,
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    bufsize=0,
)

def pump(stream, name):
    """Byte-level pump: the gate prompt has NO trailing newline, so a
    line-buffered reader would block forever waiting for one."""
    buf = b""
    while True:
        b = stream.read(1)
        if not b:
            q.put((name, "EOF", ""))
            return
        buf += b
        q.put((name, "BYTE", b))
        if b == b"\n":
            q.put((name, "LINE", buf.decode("utf8", "replace").rstrip("\r\n")))
            buf = b""
        elif buf.endswith(b"Allow? [y/N \xc2\xb7 or type a redirect] ") or buf.endswith(b"or type a redirect] "):
            q.put((name, "GATE", buf.decode("utf8", "replace")))
            buf = b""

threading.Thread(target=pump, args=(p.stdout, "OUT"), daemon=True).start()
threading.Thread(target=pump, args=(p.stderr, "ERR"), daemon=True).start()

def send(line, why):
    events.append((ts(), "IN", why, line))
    print(f"[{ts():>7}ms] IN   {why}: {line!r}", flush=True)
    p.stdin.write((line + "\n").encode())
    p.stdin.flush()

PROMPT = ("There is a bug in calc.py: subtract() adds instead of subtracting. "
          "Fix it by editing the file.")

ttft = None
first_out_byte = None
gates = 0
turn_line = None
sent_prompt = False
state = "boot"

# Give the REPL a moment to finish its banner, then send the task.
time.sleep(1.5)
send(PROMPT, "turn-1 prompt")
sent_prompt = True

deadline = time.monotonic() + TIMEOUT
while time.monotonic() < deadline:
    try:
        name, kind, payload = q.get(timeout=0.5)
    except queue.Empty:
        if p.poll() is not None:
            print(f"[{ts():>7}ms] process exited rc={p.returncode}", flush=True)
            break
        continue

    if kind == "BYTE":
        if name == "OUT" and first_out_byte is None:
            first_out_byte = ts()
            ttft = first_out_byte
            print(f"[{ttft:>7}ms] *** P3: FIRST BYTE ON STDOUT (TTFT sample) ***", flush=True)
        continue

    if kind == "EOF":
        print(f"[{ts():>7}ms] {name}  EOF", flush=True)
        continue

    if kind == "GATE":
        gates += 1
        print(f"[{ts():>7}ms] {name}  *** P1+P2: GATE OBSERVED ON {name} *** {payload!r}", flush=True)
        events.append((ts(), name, "GATE", payload))
        if gates == 1:
            send("actually just tell me the one-line fix, do not edit anything",
                 "scripted REDIRECT (non-y/n text)")
        else:
            send("n", "scripted DENY")
        continue

    # LINE
    txt = payload
    if txt.strip():
        print(f"[{ts():>7}ms] {name}  {txt}", flush=True)
    events.append((ts(), name, "LINE", txt))
    if "turn iter=" in txt:
        turn_line = txt
        print(f"[{ts():>7}ms] *** P4: TURN-BOUNDARY MARKER *** {txt!r}", flush=True)
        send("exit", "end session")
        # drain briefly then stop
        deadline = min(deadline, time.monotonic() + 10)

try:
    p.stdin.close()
except Exception:
    pass
try:
    p.wait(timeout=10)
except Exception:
    p.kill()

print("\n================ SPIKE RESULT ================")
print(f"P1 REPL-over-pipe reached a live gate : {'YES' if gates else 'NO'}  (gates={gates})")
print(f"P2 gate observable on stderr          : {'YES' if any(e[1]=='ERR' and e[2]=='GATE' for e in events) else 'NO'}")
print(f"P3 TTFT samplable during the run      : {str(ttft)+' ms' if ttft is not None else 'NO'}")
print(f"P4 turn-boundary marker + token counts: {turn_line!r}")
if turn_line:
    m = re.search(r"in=(\d+)\s+out=(\d+)", turn_line)
    print(f"   parsed usage: in={m.group(1)} out={m.group(2)}" if m else "   parsed usage: NONE")
print(f"exit rc={p.returncode}")
