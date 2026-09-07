import subprocess, sys, os
ABCC = r"D:\dev\abcc"
EXE = os.path.join(ABCC, "target", "release", "abcc.exe")

def prompt(task):
    out = subprocess.run([EXE, "replay", task], cwd=ABCC, capture_output=True, text=True, encoding="utf-8").stdout
    for line in out.splitlines():
        if line.startswith("  | "):
            return line[4:]
    raise SystemExit(f"no prompt line in replay {task}")

if __name__ == "__main__":
    ps = [prompt(t) for t in sys.argv[1:]]
    for t, p in zip(sys.argv[1:], ps):
        print(f"{t}: {len(p)} chars")
    if len(ps) > 1:
        for t, p in zip(sys.argv[2:], ps[1:]):
            assert ps[0] == p, f"not the same subject any more: {sys.argv[1]} vs {t}"
        print("byte-identical: OK")
