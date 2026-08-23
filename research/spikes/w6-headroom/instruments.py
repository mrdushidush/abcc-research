"""The rungs of the ladder, and what each one costs.

Every instrument takes a workdir and returns

    {"verdict": "green" | "red" | "error", "ms": int, "detail": str, "n": int}

`green` means the instrument would let the change through, `red` means it would
stop it, `error` means the instrument could not run (which is not a verdict — it
is the `Uncertain(why)` W6 item 2 requires, and it is counted separately).

`n` is the instrument's finding count where it has one, so a *delta* against the
same tree before the change can be computed later: an absolute lint gate is
useless on a repository that is already red, but a delta gate is not, and the
difference is measurable rather than arguable.
"""

import pathlib
import re

import common as C

# ── python ───────────────────────────────────────────────────────────

PY_SKIP = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def py_files(work):
    out = []
    for p in sorted(pathlib.Path(work).rglob("*.py")):
        rel = p.relative_to(work)
        if any(part in PY_SKIP for part in rel.parts):
            continue
        out.append(p)
    return out


def inst_syntax(work):
    """v1's rung: `python3 -m py_compile` over the tree (its ValidateSyntaxTool)."""
    files = py_files(work)
    if not files:
        return {"verdict": "error", "ms": 0, "detail": "no .py files", "n": 0}
    args = [C.REAL_PYTHON, "-m", "py_compile"] + [str(f) for f in files]
    code, out, ms = C.run(args, work, timeout=120)
    bad = [l for l in out.splitlines() if l.strip()]
    return {
        "verdict": "green" if code == 0 else "red",
        "ms": ms,
        "detail": " | ".join(bad[:3])[:300],
        "n": 0 if code == 0 else max(1, len(bad)),
    }


RUFF_LINE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+): (?P<code>[A-Z]+\d+)")


def _ruff(work, extra):
    code, out, ms = C.run(
        [C.REAL_PYTHON, "-m", "ruff", "check", "--no-cache", "--output-format",
         "concise"] + extra + ["."],
        work, timeout=180,
    )
    hits = []
    for l in out.splitlines():
        m = RUFF_LINE.match(l.strip())
        if m:
            hits.append(f"{m.group('file').replace(chr(92), '/')}::{m.group('code')}")
    if code not in (0, 1):
        return {"verdict": "error", "ms": ms, "detail": out.strip()[:300], "n": 0,
                "hits": []}
    return {
        "verdict": "green" if not hits else "red",
        "ms": ms,
        "detail": "; ".join(sorted({h.split("::")[1] for h in hits}))[:300],
        "n": len(hits),
        "hits": sorted(hits),
    }


def inst_ruff(work):
    return _ruff(work, [])


def inst_ruff_all(work):
    return _ruff(work, ["--select", "ALL"])


MYPY_LINE = re.compile(r"^(?P<file>[^:]+):(?P<line>\d+): error: (?P<msg>.*?)(\s+\[(?P<code>[a-z-]+)\])?$")


def _mypy(work, extra):
    code, out, ms = C.run(
        [C.REAL_PYTHON, "-m", "mypy", "--no-incremental", "--cache-dir",
         "/dev/null" if C.os.name != "nt" else "nul"] + extra + ["."],
        work, timeout=300,
    )
    hits = []
    for l in out.splitlines():
        m = MYPY_LINE.match(l.strip())
        if m:
            hits.append(f"{m.group('file').replace(chr(92), '/')}::{m.group('code') or '?'}")
    if code not in (0, 1) and "error:" not in out:
        return {"verdict": "error", "ms": ms, "detail": out.strip()[:300], "n": 0,
                "hits": []}
    return {
        "verdict": "green" if not hits else "red",
        "ms": ms,
        "detail": "; ".join(sorted({h.split("::")[1] for h in hits}))[:300],
        "n": len(hits),
        "hits": sorted(hits),
    }


def inst_mypy(work):
    return _mypy(work, [])


def inst_mypy_strict(work):
    return _mypy(work, ["--strict"])


def inst_pytest(work):
    """Sandboxed execution of the tests the repository already has."""
    if not (pathlib.Path(work) / "tests").is_dir():
        return {"verdict": "error", "ms": 0, "detail": "no tests/ directory", "n": 0}
    code, out, ms = C.run(
        [C.REAL_PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        work, timeout=300,
    )
    tail = [l for l in out.splitlines() if l.strip()][-1:] or [""]
    if code in (0, 1):
        return {
            "verdict": "green" if code == 0 else "red",
            "ms": ms,
            "detail": tail[0][:200],
            "n": 0 if code == 0 else 1,
        }
    return {"verdict": "error", "ms": ms, "detail": tail[0][:200], "n": 0}


ENTRY = re.compile(r"python3?\s+(run\.py\s+\S+)")


def entrypoint_command(task_id):
    """The command the ticket itself tells you to run, lifted from the ticket."""
    text = (C.K_TASKS / task_id / "prompt.txt").read_text(encoding="utf-8")
    m = ENTRY.search(text)
    return m.group(1) if m else None


def make_entrypoint(task_id):
    """Sandboxed execution, v1's shape: run it, and believe the exit code."""
    cmd = entrypoint_command(task_id)

    def inst(work):
        if not cmd:
            return {"verdict": "error", "ms": 0, "detail": "no command in the ticket",
                    "n": 0}
        code, out, ms = C.run([C.REAL_PYTHON] + cmd.split(), work, timeout=180)
        tail = ([l for l in out.splitlines() if l.strip()][-1:] or [""])[0]
        if code is None:
            return {"verdict": "error", "ms": ms, "detail": "<timeout>", "n": 0}
        return {
            "verdict": "green" if code == 0 else "red",
            "ms": ms,
            "detail": tail[:200],
            "n": 0 if code == 0 else 1,
            # the last line only. Comparing the *whole* stream against the
            # unfixed tree's looked like a free instrument and is not: a
            # traceback carries absolute paths, so two identical crashes differ.
            "tail": tail[:200],
        }

    return inst


PY_LADDER = [
    ("syntax", inst_syntax),
    ("ruff", inst_ruff),
    ("ruff_all", inst_ruff_all),
    ("mypy", inst_mypy),
    ("mypy_strict", inst_mypy_strict),
    ("pytest", inst_pytest),
]


def py_ladder(task_id):
    """The Python ladder for one task, with the ticket's own command appended."""
    return PY_LADDER + [("entrypoint", make_entrypoint(task_id))]


# ── rust ─────────────────────────────────────────────────────────────


def _cargo(work, args, timeout=300):
    env = C.shim_env()
    env["CARGO_TERM_COLOR"] = "never"
    return C.run(["cargo"] + args, work, timeout=timeout, env=env)


RS_WARN = re.compile(r"^(warning|error)(\[[A-Z0-9]+\])?: ")


def _rust_result(code, out, ms, kinds=("error",)):
    hits = [l for l in out.splitlines() if RS_WARN.match(l.strip())
            and l.strip().split("[")[0].split(":")[0] in kinds]
    if hits:
        detail = hits[0]
    else:
        tail = [l for l in out.splitlines() if l.strip()]
        detail = tail[-1] if tail else ""
    return {
        "verdict": "green" if code == 0 else "red",
        "ms": ms,
        "detail": detail[:200],
        "n": len(hits),
    }


def inst_cargo_check(work):
    code, out, ms = _cargo(work, ["check", "--offline", "--quiet"])
    if code is None:
        return {"verdict": "error", "ms": ms, "detail": "<timeout>", "n": 0}
    return _rust_result(code, out, ms)


def inst_cargo_clippy(work):
    code, out, ms = _cargo(
        work, ["clippy", "--offline", "--quiet", "--", "-D", "warnings"]
    )
    if code is None:
        return {"verdict": "error", "ms": ms, "detail": "<timeout>", "n": 0}
    return _rust_result(code, out, ms, kinds=("error", "warning"))


def inst_cargo_test(work):
    """The crate's own visible tests — `--lib` so the verifier's residue cannot count."""
    code, out, ms = _cargo(work, ["test", "--offline", "--quiet", "--lib"])
    if code is None:
        return {"verdict": "error", "ms": ms, "detail": "<timeout>", "n": 0}
    line = next((l for l in out.splitlines() if "test result:" in l), "")
    return {
        "verdict": "green" if code == 0 else "red",
        "ms": ms,
        "detail": line.strip()[:200] or out.strip()[-200:],
        "n": 0 if code == 0 else 1,
    }


RS_LADDER = [
    ("cargo_check", inst_cargo_check),
    ("cargo_clippy", inst_cargo_clippy),
    ("cargo_test", inst_cargo_test),
]


# ── Q56: five languages, and a verifier that leaves its answer key behind ──


def q56_lang(task_id):
    text = (C.Q56_TASKS / task_id / "task.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.strip().startswith("lang"):
            return line.split("=", 1)[1].strip().strip('"')
    return "?"


_RESIDUE = {}


def verifier_residue(task_id):
    """Paths the verifier CREATES in a workdir — its hidden tests.

    Measured, not guessed: the verifier is run against a pristine fixture copy
    and the tree is diffed. An instrument that runs those files is reading the
    answer key, which is how a post-hoc harness accidentally reports a perfect
    gate.
    """
    if task_id in _RESIDUE:
        return _RESIDUE[task_id]
    task = C.Q56_TASKS / task_id
    tmp = C.pathlib.Path(C.tempfile.mkdtemp(prefix="w6hr-res-"))
    try:
        work = C.copy_tree(task / "fixture", tmp / "work")
        before = {p.relative_to(work).as_posix()
                  for p in work.rglob("*") if p.is_file()}
        stub = tmp / "transcript.log"
        stub.write_text("", encoding="utf-8")
        C.verify(work, task / "verify.sh", transcript=stub, timeout=300)
        after = {p.relative_to(work).as_posix()
                 for p in work.rglob("*") if p.is_file()}
        _RESIDUE[task_id] = after - before
    finally:
        C.shutil.rmtree(tmp, ignore_errors=True)
    return _RESIDUE[task_id]


def fixture_tests(task_id):
    """The test files the fixture itself ships, by relative path."""
    fx = C.Q56_TASKS / task_id / "fixture"
    out = []
    for p in sorted(fx.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(fx).as_posix()
        if any(s in rel for s in PY_SKIP):
            continue
        name = p.name
        if name.startswith("test_") or name.endswith("_test.py") or "/tests/" in rel:
            out.append(rel)
    return out


def make_q56_pytest(task_id):
    """The tests the repository already had — never the verifier's."""
    wanted = fixture_tests(task_id)

    def inst(work):
        present = [w for w in wanted if (pathlib.Path(work) / w).is_file()]
        if not present:
            return {"verdict": "error", "ms": 0,
                    "detail": "the fixture ships no test file", "n": 0}
        code, out, ms = C.run(
            [C.REAL_PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + present,
            work, timeout=180,
        )
        tail = ([l for l in out.splitlines() if l.strip()][-1:] or [""])[0]
        if code in (0, 1):
            return {"verdict": "green" if code == 0 else "red", "ms": ms,
                    "detail": tail[:200], "n": 0 if code == 0 else 1,
                    "files": present}
        return {"verdict": "error", "ms": ms, "detail": tail[:200], "n": 0,
                "files": present}

    return inst



# ── node / typescript / shell — added by W6 item 5 (language generality) ─────
#
# Item 4 ran the rust and python halves of Q56 and left 351 preserved cells in
# the other three languages unmeasured, deliberately: `q56_ladder` returned an
# empty rung list and `ladder.py` skipped the cell. These are those rungs. The
# shape is item 4's unchanged — every rung answers green/red/error plus a wall
# clock, and nothing here reads the verifier's residue (`ladder.py` deletes it
# before any rung runs).
#
# What exists per language is itself a finding. Node has a syntax check and the
# fixture's own test and no type checker. TypeScript has a type checker and no
# separate syntax rung worth running (tsc is the parse). Shell has `bash -n` and
# nothing else — `shellcheck` is not installed on this host, and a shell fixture
# ships no test file at all.

TSC = C.REPO / "research/spikes/w6-language/node_modules/typescript/bin/tsc"


def _sources(work, suffix):
    return sorted(p for p in pathlib.Path(work).rglob(f"*{suffix}")
                  if "node_modules" not in p.parts and not p.name.startswith("hidden_gate"))


def inst_node_syntax(work):
    """`node --check` over the solution files — v1's javascript rung, on `.mjs`.

    The extension matters: the same content in a `.js` file is accepted by node
    24 when it contains ESM syntax and a syntax error (W6 item 5, F311). Q56's
    node fixtures are `.mjs`, so this is the rung working as intended.
    """
    files = [f for f in _sources(work, ".mjs") if not f.name.startswith("test_")]
    if not files:
        return {"verdict": "error", "ms": 0, "detail": "no .mjs files", "n": 0}
    worst = {"verdict": "green", "ms": 0, "detail": "", "n": 0}
    for f in files:
        code, out, ms = C.run(["node", "--check", str(f)], work, timeout=60)
        worst["ms"] += ms
        if code != 0:
            worst["verdict"] = "red"
            worst["n"] += 1
            worst["detail"] = worst["detail"] or " ".join(out.split())[:200]
    return worst


def inst_bash_syntax(work):
    """`bash -n` — the shell equivalent of `py_compile`, and the only free rung."""
    files = _sources(work, ".sh")
    if not files:
        return {"verdict": "error", "ms": 0, "detail": "no .sh files", "n": 0}
    worst = {"verdict": "green", "ms": 0, "detail": "", "n": 0}
    for f in files:
        code, out, ms = C.run([C.BASH, "-n", str(f)], work, timeout=60)
        worst["ms"] += ms
        if code != 0:
            worst["verdict"] = "red"
            worst["n"] += 1
            worst["detail"] = worst["detail"] or " ".join(out.split())[:200]
    return worst


def _tsc(work, extra):
    """`tsc --noEmit` over the tree, with flags rather than a tsconfig.

    The fixtures ship no tsconfig, which is itself the point: a project that has
    never been type-checked has no config file to detect, and Claudette's
    `detect_diag_tool` looks for exactly that file.
    """
    if not TSC.is_file():
        return {"verdict": "error", "ms": 0, "detail": "tsc not installed", "n": 0}
    files = [str(f) for f in _sources(work, ".ts")]
    if not files:
        return {"verdict": "error", "ms": 0, "detail": "no .ts files", "n": 0}
    # `--typeRoots` is not optional: the fixtures import `node:assert/strict`,
    # and without the spike's @types/node every tree is red with TS2307 before
    # anything about the change is looked at. (Caught by running the rung on the
    # pristine fixture AND the refsol first - both red, which is what a broken
    # instrument looks like.)
    types = C.REPO / "research/spikes/w6-language/node_modules/@types"
    code, out, ms = C.run(
        ["node", str(TSC), "--noEmit", "--target", "es2022",
         "--module", "nodenext", "--moduleResolution", "nodenext",
         "--allowImportingTsExtensions", "--skipLibCheck",
         "--typeRoots", str(types), "--types", "node"] + extra + files,
        work, timeout=180,
    )
    if code is None:
        return {"verdict": "error", "ms": ms, "detail": "<timeout>", "n": 0}
    errs = [l for l in out.splitlines() if ": error TS" in l]
    return {
        "verdict": "green" if code == 0 else "red",
        "ms": ms,
        "detail": (errs[0] if errs else out.strip()[-200:])[:200],
        "n": len(errs),
    }


def inst_tsc(work):
    """`tsc --noEmit`: the type check IS the build in this language.

    Flags rather than a tsconfig, because the fixtures do not ship one - which is
    itself the point: a project that has never been type-checked has no config to
    detect, and Claudette's `detect_diag_tool` looks for exactly that file.
    """
    return _tsc(work, [])


def inst_tsc_strict(work):
    """`--strict`, which is what a TypeScript project usually turns on.

    Item 4 measured plain `mypy` against `mypy --strict` and found the second red
    on every tree it saw; this is the same comparison in the language where the
    strict flag is the community default.
    """
    return _tsc(work, ["--strict"])


def make_node_test(task_id, suffix):
    """The test file the fixture already shipped — never the verifier's."""
    wanted = [t for t in fixture_tests_any(task_id) if t.endswith(suffix)]

    def inst(work):
        present = [w for w in wanted if (pathlib.Path(work) / w).is_file()]
        if not present:
            return {"verdict": "error", "ms": 0,
                    "detail": "the fixture ships no test file", "n": 0}
        worst = {"verdict": "green", "ms": 0, "detail": "", "n": 0, "files": present}
        for rel in present:
            code, out, ms = C.run(["node", rel], work, timeout=120)
            worst["ms"] += ms
            if code is None:
                return {"verdict": "error", "ms": worst["ms"], "detail": "<timeout>",
                        "n": 0, "files": present}
            if code != 0:
                worst["verdict"] = "red"
                worst["n"] += 1
                worst["detail"] = worst["detail"] or " ".join(out.split())[-200:]
        return worst

    return inst


def fixture_tests_any(task_id):
    """`fixture_tests` without the python-only naming rule."""
    fx = C.Q56_TASKS / task_id / "fixture"
    return [p.relative_to(fx).as_posix() for p in sorted(fx.rglob("*"))
            if p.is_file() and p.name.startswith("test_")]


def q56_ladder(task_id):
    """The rungs that exist for this task's language.

    Five languages, and the rung list is not the same length twice - which is
    W6 item 5's answer in one function.
    """
    lang = q56_lang(task_id)
    if lang == "rust":
        return lang, RS_LADDER
    if lang == "python":
        return lang, [
            ("syntax", inst_syntax),
            ("ruff", inst_ruff),
            ("mypy", inst_mypy),
            ("pytest_fixture", make_q56_pytest(task_id)),
        ]
    if lang == "node":
        return lang, [
            ("node_syntax", inst_node_syntax),
            ("node_fixture_test", make_node_test(task_id, ".mjs")),
        ]
    if lang == "typescript":
        return lang, [
            ("tsc", inst_tsc),
            ("tsc_strict", inst_tsc_strict),
            ("node_fixture_test", make_node_test(task_id, ".ts")),
        ]
    if lang == "shell":
        return lang, [
            ("bash_syntax", inst_bash_syntax),
        ]
    return lang, []
