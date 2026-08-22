"""Arm D — the second-model arm, and what it costs to get it.

Holds the body constant (the unified diff, arm A's prompt exactly) and varies
the only thing left: the weights. Also times the round trip, because W1 F79's
23.77 s is a swap between two models and item 2 F241 established that the swap
also wipes the RAM prompt cache — so the price of one decorrelated gate is the
load out, the load back, and a cold prefill on both sides.

  python swap.py qwen3.8-27b 40960 3

The window differs from the champion's 65536 because a dense 27B does not fit at
65536 on a 16 GB card (W1). It does not affect this measurement: the prompt is
~1.7k tokens.
"""

import json
import subprocess
import sys
import time

import common as C
import independence as I


def lms(*args, timeout=900):
    t0 = time.perf_counter()
    # `lms` writes a progress bar to stderr with bytes cp1252 cannot decode, and
    # the default text mode kills the reader thread on it. Decode permissively.
    r = subprocess.run(
        ["lms", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        shell=True,
    )
    return round(time.perf_counter() - t0, 2), r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen3.8-27b"
    ctx = sys.argv[2] if len(sys.argv) > 2 else "40960"
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 3

    timings = {}
    print(f"-- unloading everything --")
    timings["unload_champion"], rc, out = lms("unload", "--all")
    print(f"   {timings['unload_champion']}s rc={rc} {out.strip()[:120]}")

    print(f"-- loading {model} at -c {ctx} --")
    timings["load_second"], rc, out = lms(
        "load", model, "--context-length", ctx, "--gpu", "max", "-y"
    )
    print(f"   {timings['load_second']}s rc={rc} {out.strip()[:200]}")
    if rc != 0:
        raise SystemExit("load failed")

    rows = []
    for a in C.ARTIFACTS:
        I.run("A-artifact", a, n, model, rows, tag="D ")

    print("\n-- restoring the champion --")
    timings["unload_second"], rc, out = lms("unload", "--all")
    print(f"   {timings['unload_second']}s rc={rc}")
    timings["load_champion"], rc, out = lms(
        "load", C.CHAMPION, "--context-length", "65536", "--gpu", "max", "-y"
    )
    print(f"   {timings['load_champion']}s rc={rc} {out.strip()[:200]}")

    rt = sum(timings.values())
    print(f"\nround trip (unload + load + unload + load): {rt:.1f}s")
    (C.HERE / "swap-results.json").write_text(
        json.dumps({"model": model, "ctx": ctx, "timings": timings,
                    "round_trip_s": round(rt, 1), "rows": rows}, indent=2),
        encoding="utf-8",
    )
    I.summarise(rows)


if __name__ == "__main__":
    main()
