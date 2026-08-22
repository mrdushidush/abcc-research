"""W11 item 3: the convention arm, run for real.

BCF's critique artifact is not JSON. It is five lines of prose in a fixed
layout, requested by the system prompt at `mission.rs:1626-1638` and read back
by a hand-rolled line scanner at `:1654-1687` whose score array is initialised
to `5.0`. `artifacts bcf-parse` has already shown what that scanner does to ten
plausible formats. What it has not shown is which of those formats THIS model
actually produces — a donor's contract is a measurement about the donor's model
(the standing rule from `verify-claims-against-code-not-docs` item 23), and
BCF's was calibrated on qwen2.5-coder.

Five identical calls, BCF's system prompt verbatim (including its `/no_think`
prefix), over the fixture's most-defective module. Each response goes through
the ported parser.
"""

import json
import pathlib
import subprocess
import time
import urllib.request

BASE = "http://localhost:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
HERE = pathlib.Path(__file__).resolve().parent
BIN = HERE / "artifacts/target/debug/artifacts.exe"

import chain  # noqa: E402

# Verbatim from battle-command-forge/src/mission.rs:1626-1638.
SYSTEM = (
    "/no_think\nYou are 5 expert reviewers in one. Score this code 0-10 on each dimension.\n"
    "Output EXACTLY this format (one line per role, nothing else):\n"
    "DEV: X.X | defects: ...\n"
    "ARCH: X.X | defects: ...\n"
    "TEST: X.X | defects: ...\n"
    "SEC: X.X | defects: ...\n"
    "DOCS: X.X | defects: ...\n\n"
    "DEV = correctness, robustness\n"
    "ARCH = architecture, SOLID, maintainability\n"
    "TEST = test quality, coverage\n"
    "SEC = security, OWASP, secrets\n"
    "DOCS = documentation, readability"
)

CODE = (chain.FIXTURE / "jobs/sla.py").read_text(encoding="utf-8")
SPEC = (chain.FIXTURE / "docs/status_lifecycle.md").read_text(encoding="utf-8")
USER = f"Code:\n{CODE}\n\nSpec:\n{SPEC}"


def critique(label):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": USER},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
        "max_tokens": 8192,
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    content, usage = "", None
    with urllib.request.urlopen(req, timeout=1800) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            p = line[5:].strip()
            if p == "[DONE]":
                break
            try:
                obj = json.loads(p)
            except json.JSONDecodeError:
                continue
            if obj.get("usage"):
                usage = obj["usage"]
            for ch in obj.get("choices") or []:
                content += (ch.get("delta") or {}).get("content") or ""
    wall = time.perf_counter() - t0
    rt = ((usage or {}).get("completion_tokens_details") or {}).get("reasoning_tokens")
    return content, rt, wall


def main():
    cases = []
    for i in range(5):
        text, rt, wall = critique(f"run{i+1}")
        first = next((l for l in text.splitlines() if l.strip()), "")
        print(f"run{i+1}  reas_tok={str(rt):>5} {wall:5.1f}s  first line: {first[:80]}")
        cases.append((f"run{i+1}", text))

    blob = "\n\n".join(f"{name}\n{text.strip()}" for name, text in cases)
    (HERE / "convention-raw.txt").write_text(blob, encoding="utf-8")
    print()
    print("-- through BCF's own parser --")
    r = subprocess.run(
        [str(BIN), "bcf-parse", str(HERE / "convention-raw.txt")],
        capture_output=True,
        text=True,
    )
    print(r.stdout.rstrip())


if __name__ == "__main__":
    main()
