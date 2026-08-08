#!/usr/bin/env python3
"""Gate step 1 across all 90 stable ABCC tasks: can each verifier report a wrong answer?

Generalises gate_step1_section4b.py from 10 tasks to all 90. Section 4B was easy because
the donor ships a real buggy fixture for it (BUGGY_FILES). The other 80 tasks generate from
nothing, so there is no fixture to be wrong - the wrong answer has to be synthesised, and
the only synthesis that needs no per-task authoring is a *null implementation*.

Four tiers. Every one of them is a wrong answer, so every one MUST FAIL. A verifier that
PASSes any tier cannot report that answer as wrong.

  absent   all 80+10  nothing exists. The artifact was never produced.
  stub     all 80+10  the artifact exists and imports cleanly, and does nothing:
                      every symbol is a no-op returning None.
  sham     24 strmatch  a file whose entire content is a comment holding every substring
                      the verifier searches for. Generated, not authored - possible only
                      because all 24 assertions are positive presence checks.
  fixture  10 sec-4B  the donor's own buggy file, i.e. the original F16 tier, re-run here
                      so all four tiers appear in one table.

Why `absent` alone is not enough, and why `stub` is the tier that matters: a py verifier
whose import fails raises before reaching any assertion, so `absent` only proves the
verifier notices *total absence*. `fix_path_traversal` (F15) FAILs `absent` for that reason
and PASSes `stub` - the defect is invisible to the weaker tier.

Fidelity. Both donor validation paths run the same source (`task.validation`) as
`python3 -c` / `node -e` with cwd=/app/workspace, and score `exit 0 AND "PASS" in stdout`:
  - local     ultimate-100-task-test.js:2788-2814 (runValidationLocal, docker exec)
  - server    packages/agents/src/main.py:524-589  (/run-validation), reached via
              packages/api/src/services/asyncValidationService.ts:432; the script sends the
              same string with a LANG= prefix (ultimate-100-task-test.js:2695-2709)
This script reproduces that contract, substituting a temp dir for /app/workspace. It runs on
the host, not in the abcc-agents container, so every FAIL is classified and any failure that
could be platform noise rather than detection is reported as INCONCLUSIVE - a spurious FAIL
would otherwise read as "this verifier is sound", which is the one direction that hides a
defect.

Donor: agent-battle-command-center @ d5528ea.
Run: python gate_step1_all90.py [path-to-abcc-repo]
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from extract_tasks import js_unescape

HERE = Path(__file__).parent
DEFAULT_REPO = Path(r"D:\dev\agent-battle-command-center")
CTO = {"react_cto", "cto_decomposed"}
TIMEOUT_S = 30

PY_FROM = re.compile(r"from\s+([\w.]+)\s+import")
PY_OPEN = re.compile(r"open\(\s*'([^']+)'")
NODE_REQ = re.compile(r"require\(\s*'([^']+)'")
IN_H = re.compile(r"'([^']*)'\s+in\s+h")
COUNT_H = re.compile(r"\.count\('([^']*)'\)")

# A module that imports cleanly and implements nothing. Dunders must still raise, or the
# import machinery reads a stub __path__ and treats the module as a package.
STUB_PY = '''\
def __getattr__(name):
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(name)
    def _stub(*a, **k):
        return None
    return _stub
'''

# Same idea for node: every export resolves to a no-op. Symbols stay undefined so the
# module does not accidentally look thenable or iterable to the runtime.
STUB_NODE = (
    "module.exports = new Proxy({}, { get: (t, k) => "
    "(typeof k === 'symbol' ? undefined : function () { return undefined; }) });\n"
)

COMMENT = {
    ".html": ("<!--", "-->"),
    ".css": ("/*", "*/"),
    ".js": ("/*", "*/"),
    ".jsx": ("/*", "*/"),
}

# Errors that mean the harness or the platform got in the way, not that the verifier
# detected anything. Any FAIL attributed to one of these is reported INCONCLUSIVE.
PLATFORM_ERRORS = ("WinError", "UnicodeDecodeError", "UnicodeEncodeError", "PermissionError")


def load_tasks():
    tasks = [t for t in json.loads((HERE / "tasks.json").read_text("utf-8"))
             if t.get("category") not in CTO]
    assert len(tasks) == 90, f"expected 90 stable tasks, got {len(tasks)}"
    return tasks


def buggy_files(repo):
    """Parse BUGGY_FILES (ultimate-100-task-test.js:1706-1717) out of the donor source."""
    src = (repo / "scripts" / "ultimate-100-task-test.js").read_text(encoding="utf-8")
    start = src.index("const BUGGY_FILES = {")
    end = src.index("\n};", start)
    block = src[start:end]
    return {m.group(1): js_unescape(m.group(2))
            for m in re.finditer(r"'([\w.]+)':\s*`((?:[^`\\]|\\.)*)`", block)}


def targets(task):
    """What the verifier reaches for: py modules, files opened, node modules."""
    v = task["validation"]
    return {
        "py_mods": PY_FROM.findall(v),
        "opens": PY_OPEN.findall(v),
        "node_mods": NODE_REQ.findall(v),
    }


def shape(task, tg):
    if task.get("validationLang") == "node":
        return "node-require"
    return "py-import" if tg["py_mods"] else "py-open"


def sham_tokens(v):
    """Every substring the verifier looks for. Sound only because all 24 strmatch
    assertions are positive presence checks - verified: no `not in` anywhere."""
    return list(dict.fromkeys(IN_H.findall(v) + COUNT_H.findall(v)))


def write_stub_py(work, dotted):
    parts = dotted.split(".")
    p = work
    for d in parts[:-1]:
        p = p / d
        p.mkdir(exist_ok=True)
        (p / "__init__.py").write_text("", encoding="utf-8")
    (p / f"{parts[-1]}.py").write_text(STUB_PY, encoding="utf-8")


def rel_from_workspace(path):
    """'/app/workspace/tasks/x/y.html' or './tasks/x/y' -> 'tasks/x/y.html'."""
    return path.replace("/app/workspace/", "").lstrip("./")


def build(work, task, tg, tier, fixtures):
    """Materialise the workspace for one tier. Returns None, or a skip reason."""
    if tier == "absent":
        return None

    if tier == "fixture":
        dotted = tg["py_mods"][0]
        fname = f"{dotted.split('.')[-1]}.py"
        if fname not in fixtures:
            return f"no BUGGY_FILES entry for {fname}"
        parts = dotted.split(".")
        p = work
        for d in parts[:-1]:
            p = p / d
            p.mkdir(exist_ok=True)
            (p / "__init__.py").write_text("", encoding="utf-8")
        (p / fname).write_text(fixtures[fname], encoding="utf-8")
        return None

    if tier == "stub":
        for dotted in tg["py_mods"]:
            write_stub_py(work, dotted)
        for rq in tg["node_mods"]:
            rel = rel_from_workspace(rq)
            f = work / (rel if rel.endswith(".js") else rel + ".js")
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(STUB_NODE, encoding="utf-8")
        for op in tg["opens"]:
            f = work / rel_from_workspace(op)
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("", encoding="utf-8")  # exists, empty
        return None

    if tier == "sham":
        toks = sham_tokens(task["validation"])
        if not toks:
            return "no tokens extracted"
        for op in tg["opens"]:
            f = work / rel_from_workspace(op)
            f.parent.mkdir(parents=True, exist_ok=True)
            o, c = COMMENT.get(f.suffix, ("<!--", "-->"))
            # Repeat each token so any count>=N threshold is met; max observed is >=3.
            body = " ".join(t for t in toks for _ in range(5))
            f.write_text(f"{o} {body} {c}\n", encoding="utf-8")
        return None

    raise ValueError(tier)


def run_verifier(task, work):
    """Run the verifier the way the donor does. Returns (verdict, detail)."""
    code = task["validation"].replace("/app/workspace", work.as_posix())
    # fix_path_traversal is the only verifier naming a real filesystem path outside the
    # workspace: it probes a base dir and reaches out of it for /etc/passwd.
    if "'/tmp'" in code:
        base = work / "base"
        base.mkdir(exist_ok=True)
        (work / "etc").mkdir(exist_ok=True)
        (work / "etc" / "passwd").write_text("root:x:0:0:root:/root:/bin/sh\n", encoding="utf-8")
        code = code.replace("'/tmp'", repr(base.as_posix()))

    cmd = ([sys.executable, "-c", code] if task.get("validationLang") != "node"
           else ["node", "-e", code])
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=work,
                           timeout=TIMEOUT_S, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return "FAIL", "TIMEOUT"

    if p.returncode == 0 and "PASS" in (p.stdout or ""):
        return "PASS", ""
    return "FAIL", why_failed(p, task.get("validationLang") == "node")[:78]


# Anchored at line start, because both runtimes print the exception that way and node also
# echoes the offending source line. Unanchored, an identifier like `handleError` inside that
# echo matches first and node_error_handler's failure gets attributed to its own source text.
# The name may carry a module prefix (json.decoder.JSONDecodeError) and Python prints a bare
# `AssertionError` with no colon, so neither a prefix nor a colon can be required.
ERR_LINE = re.compile(r"^(?:[A-Za-z_][\w.]*\.)?[A-Za-z_]*(?:Error|Exception)\b")


def why_failed(p, is_node):
    """The line that says what went wrong.

    Direction matters: a Python traceback ends with the exception, while node prints the
    error near the top and closes with a `Node.js vX` version banner. Taking the last line
    for both attributes 15 node failures to a version string, which says nothing about
    whether the verifier detected anything.
    """
    lines = [l.strip() for l in (p.stderr or "").splitlines() if l.strip()]
    hits = [l for l in lines if ERR_LINE.search(l)]
    if hits:
        return hits[0] if is_node else hits[-1]
    if lines:
        return lines[0] if is_node else lines[-1]
    # The node verifiers reject by calling process.exit(1) rather than throwing, so a
    # non-zero exit with no stderr is the verifier's own reject path, not a silent crash.
    if p.returncode != 0:
        return f"exit {p.returncode}, no stderr (process.exit reject path)"
    return "no PASS on stdout"


def inconclusive(detail):
    return any(e in detail for e in PLATFORM_ERRORS)


# Positive control. Every tier above expects FAIL, so a harness that silently never loads
# the artifact would report all 80 verifiers sound. Two things rule that out. First, the
# error class changes between tiers - absent gives ModuleNotFoundError / "Cannot find
# module", stub gives AssertionError / TypeError - which only happens if the stub really was
# imported. Second, this: a hand-written correct artifact must PASS, one per language, which
# is gate step 2 for two tasks and proves the harness can produce a PASS at all.
SELFTEST = {
    "py_json_response": ("tasks/py_api_server/json_helpers.py", '''\
import json
def json_response(data, status=200):
    return {'status': status, 'body': json.dumps(data)}
def error_response(message, status=400):
    return {'status': status, 'body': json.dumps({'error': message})}
'''),
    "node_json_response": ("tasks/node_api_server/jsonResponse.js", '''\
function jsonResponse(data, statusCode = 200) {
  return { statusCode, body: JSON.stringify(data) };
}
function errorResponse(message, statusCode = 400) {
  return { statusCode, body: JSON.stringify({ error: message }) };
}
module.exports = { jsonResponse, errorResponse };
'''),
}


def selftest(tasks):
    print("Harness positive control - a correct artifact must PASS\n")
    ok = True
    by_name = {t["name"]: t for t in tasks}
    for name, (rel, body) in SELFTEST.items():
        t = by_name[name]
        work = Path(tempfile.mkdtemp(prefix="w8g1_pc_"))
        try:
            f = work / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(body, encoding="utf-8")
            # py needs the package markers its verifier imports through
            if rel.endswith(".py"):
                p = work
                for part in Path(rel).parent.parts:
                    p = p / part
                    (p / "__init__.py").write_text("", encoding="utf-8")
            verdict, detail = run_verifier(t, work)
            print(f"  {name:<22} {t.get('validationLang'):<5} {verdict:<5} {detail}")
            ok &= verdict == "PASS"
        finally:
            shutil.rmtree(work, ignore_errors=True)
    print(f"\n  positive control: {'PASS - the harness can produce a PASS on both languages' if ok else 'FAILED - results below are not trustworthy'}\n")
    return ok


def main():
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPO
    tasks = load_tasks()
    fixtures = buggy_files(repo)
    if not shutil.which("node"):
        print("WARNING: node not found; the 17 node verifiers will be skipped\n")
    if not selftest(tasks):
        print("Aborting: the positive control failed, so a FAIL cannot be attributed to")
        print("the verifier rather than to this harness.")
        return 1

    rows = []
    for t in tasks:
        v = (t.get("validation") or "").strip()
        if v in ("", "null"):
            rows.append({"name": t["name"], "cat": t.get("category"), "shape": "none",
                         "tiers": {}, "step1": "NO VERIFIER", "step1_passing": [],
                         "step3": "n/a", "step3_passing": []})
            continue
        tg = targets(t)
        sh = shape(t, tg)
        tiers = ["absent", "stub"]
        if sh == "py-open":
            tiers.append("sham")
        if tg["py_mods"] and f"{tg['py_mods'][0].split('.')[-1]}.py" in fixtures:
            tiers.append("fixture")

        results = {}
        for tier in tiers:
            work = Path(tempfile.mkdtemp(prefix="w8g1_"))
            try:
                skip = build(work, t, tg, tier, fixtures)
                if skip:
                    results[tier] = ("SKIP", skip)
                    continue
                results[tier] = run_verifier(t, work)
            finally:
                shutil.rmtree(work, ignore_errors=True)

        # Two different gate points, kept apart. absent/stub/fixture are all step 1: the
        # verifier must reject an artifact that is missing, inert, or unfixed. The sham
        # tier is step 3 - a wrong answer that satisfies the letter of the verifier - and
        # rolling it into one verdict would report 24 step-3 failures as step-1 failures.
        S1 = ("absent", "stub", "fixture")

        def judge(tiers_):
            got = {k: v for k, v in results.items() if k in tiers_ and v[0] != "SKIP"}
            if not got:
                return "n/a", []
            passing_ = [k for k, (verdict_, _) in got.items() if verdict_ == "PASS"]
            if passing_:
                return "BROKEN", passing_
            if any(inconclusive(d) for _, (verdict_, d) in got.items()):
                return "INCONCLUSIVE", []
            return "SOUND", []

        v1, p1 = judge(S1)
        v3, p3 = judge(("sham",))
        rows.append({"name": t["name"], "cat": t.get("category"), "shape": sh,
                     "tiers": {k: {"verdict": a, "detail": b} for k, (a, b) in results.items()},
                     "step1": v1, "step1_passing": p1, "step3": v3, "step3_passing": p3})

    # ---- report ----
    print("Every tier below is a wrong answer, so every tier MUST FAIL.")
    print("step1 = absent/stub/fixture (missing, inert, or unfixed artifact)")
    print("step3 = sham (a wrong answer that satisfies the letter of the verifier)\n")
    hdr = (f"  {'task':<24} {'cat':<9} {'shape':<12} {'absent':<7} {'stub':<7} "
           f"{'fixture':<8} {'sham':<6} {'step1':<13} step3")
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))
    for r in rows:
        cells = ["-" if t not in r["tiers"] else r["tiers"][t]["verdict"]
                 for t in ("absent", "stub", "fixture", "sham")]
        s3 = "" if r["step3"] == "n/a" else r["step3"]
        print(f"  {r['name']:<24} {r['cat']:<9} {r['shape']:<12} "
              f"{cells[0]:<7} {cells[1]:<7} {cells[2]:<8} {cells[3]:<6} {r['step1']:<13} {s3}")

    live = [r for r in rows if r["step1"] != "NO VERIFIER"]
    b1 = [r for r in live if r["step1"] == "BROKEN"]
    i1 = [r for r in live if r["step1"] == "INCONCLUSIVE"]
    s3live = [r for r in live if r["step3"] != "n/a"]
    b3 = [r for r in s3live if r["step3"] == "BROKEN"]

    print(f"\n  {len(live)} of {len(rows)} tasks have a verifier to exercise; "
          f"{len(rows) - len(live)} have none (F13).")
    print(f"\n  GATE STEP 1 - n={len(live)}: "
          f"SOUND={len(live) - len(b1) - len(i1)}  BROKEN={len(b1)}  INCONCLUSIVE={len(i1)}")
    for r in b1:
        print(f"      {r['name']:<24} passes: {', '.join(r['step1_passing'])}")
    print(f"\n  GATE STEP 3, mechanical sham - n={len(s3live)} "
          f"(the {len(s3live)} strmatch tasks only; exec shams need authoring): "
          f"SOUND={len(s3live) - len(b3)}  BROKEN={len(b3)}")

    print("\n  by tier:")
    for tier in ("absent", "stub", "fixture", "sham"):
        c = Counter(r["tiers"][tier]["verdict"] for r in live if tier in r["tiers"])
        n = sum(c.values())
        if n:
            print(f"    {tier:<8} n={n:<3} " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))

    print("\n  step 1 by shape:")
    for sh in ("py-import", "node-require", "py-open", "none"):
        sub = [r for r in rows if r["shape"] == sh]
        if sub:
            c = Counter(r["step1"] for r in sub)
            print(f"    {sh:<13} n={len(sub):<3} " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))

    print("\n  Why step-1 SOUND is necessary and not sufficient: fix_sql_inject is SOUND")
    print("  here - it rejects absence, inertness and its own unfixed fixture - and F8")
    print("  still showed it passing a solution with the SQL injection fully intact. Step 1")
    print("  bounds the defect rate from below; only an authored sham closes it.")

    out = HERE / "gate_step1_all90.json"
    out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(f"\n  wrote {out.name}")


if __name__ == "__main__":
    sys.exit(main() or 0)
