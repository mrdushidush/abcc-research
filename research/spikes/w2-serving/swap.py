"""Model-swap cost: the per-gate price of a second-opinion reviewer (W1/F68 -> W6).

Co-residency is impossible on this card, so W6's "second local model" reviewer costs
a full unload+load every time a gate fires. This measures that, both directions,
with repeats -- a single reading is worthless for a number a design decision hangs on.

Reports unload and load separately: they are different mechanisms (unload is a free,
load is a 12.7 GiB read from NVMe with --no-mmap) and only load scales with model size.
"""

import json
import statistics
import subprocess
import sys
import time

CHAMPION = "qwen3.6-35b-a3b-mtp@iq3_s"
REVIEWER = "openai/gpt-oss-20b"
REPS = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def run(args):
    return subprocess.run(args, capture_output=True, text=True, shell=False)


def unload():
    t = time.perf_counter()
    run(["lms", "unload", "--all"])
    return time.perf_counter() - t


def load(model, ctx):
    t = time.perf_counter()
    r = run(["lms", "load", model, "-c", str(ctx), "--gpu", "max",
             "--parallel", "1", "-y"])
    dt = time.perf_counter() - t
    if r.returncode != 0:
        print(f"  !! load failed: {r.stderr[:200]}", file=sys.stderr)
    return dt


results = {"to_reviewer": [], "to_champion": []}
for i in range(REPS):
    u1 = unload()
    l1 = load(REVIEWER, 32768)
    results["to_reviewer"].append({"unload_s": round(u1, 3), "load_s": round(l1, 3),
                                   "total_s": round(u1 + l1, 3)})
    print(f"rep{i+1} -> reviewer : unload {u1:6.2f}s  load {l1:6.2f}s  total {u1+l1:6.2f}s",
          flush=True)

    u2 = unload()
    l2 = load(CHAMPION, 65536)
    results["to_champion"].append({"unload_s": round(u2, 3), "load_s": round(l2, 3),
                                   "total_s": round(u2 + l2, 3)})
    print(f"rep{i+1} -> champion : unload {u2:6.2f}s  load {l2:6.2f}s  total {u2+l2:6.2f}s",
          flush=True)

print()
for k, v in results.items():
    tot = [x["total_s"] for x in v]
    print(f"{k}: median {statistics.median(tot):.2f}s  min {min(tot):.2f}  max {max(tot):.2f}")
rt = statistics.median([x["total_s"] for x in results["to_reviewer"]])
ct = statistics.median([x["total_s"] for x in results["to_champion"]])
print(f"\nROUND TRIP (one gate firing): {rt + ct:.2f}s median")
print(json.dumps(results))
