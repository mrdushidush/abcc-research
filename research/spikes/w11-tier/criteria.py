"""Do M1 Plan's acceptance criteria actually fail on the unfixed tree?

plan.py measured that the model emits a task set of the right SIZE -- one task for
a one-task mission, three for a three-task mission. What it printed alongside that
was harder to read past: several of the acceptance commands look like they would
pass on the tree as it stands. `cargo check -p claudette` compiles a repository
that already compiles. `cargo test --lib <name of a test that does not exist yet>`
matches nothing -- and cargo exits 0 when a filter matches nothing.

A criterion that passes before the change is F231's defect one level up: not an
ABSENT gate reporting pass, but a PRESENT gate that never had an opinion. So run
every emitted criterion against the unfixed clone and sort them into three:

  PASSES-TODAY   exit 0 on the unfixed tree -- worthless as a gate
  UNCERTAIN      non-zero, but because the command could not run (binary not on
                 PATH, `jq` absent) -- F218's Uncertain, not a measurement
  DISCRIMINATES  non-zero for the reason the task is about

The third column is the only one that is a criterion.
"""

import json
import pathlib
import subprocess

CLONE = pathlib.Path(
    r"C:/Users/david/AppData/Local/Temp/claude/D--dev-ABCC-20-powerd-by-claudette"
    r"/42b00185-4a5a-4806-9e97-33bd4fcebc29/scratchpad/w11-integrate/claudette"
)

rows = json.loads(pathlib.Path(__file__).with_name("plan-results.json").read_text(encoding="utf-8"))

NOT_FOUND = ("command not found", "is not recognized", "No such file")

out = []
for r in rows:
    for t in (r["tasks"] or []):
        cmd = t["acceptance_command"]
        p = subprocess.run(cmd, cwd=str(CLONE), shell=True, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=1800)
        err = (p.stderr or "") + (p.stdout or "")
        if p.returncode == 0:
            verdict = "PASSES-TODAY"
        elif any(s in err for s in NOT_FOUND):
            verdict = "UNCERTAIN"
        else:
            verdict = "DISCRIMINATES"
        first_err = next((l for l in err.splitlines() if l.strip()), "")[:70]
        first_err = first_err.encode("ascii", "replace").decode("ascii")
        print(f"{r['label']:<10} exit={p.returncode:<4} {verdict:<14} {cmd[:58]:<58} {first_err}",
              flush=True)
        out.append({"call": r["label"], "cmd": cmd, "exit": p.returncode,
                    "verdict": verdict, "stderr_head": first_err})

print()
for v in ("PASSES-TODAY", "UNCERTAIN", "DISCRIMINATES"):
    n = sum(1 for o in out if o["verdict"] == v)
    print(f"{v:<14} {n}/{len(out)}")

pathlib.Path(__file__).with_name("criteria-results.json").write_text(
    json.dumps(out, indent=1), encoding="utf-8")
print("\nwrote criteria-results.json")
