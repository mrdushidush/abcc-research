#!/usr/bin/env python3
"""W6 item 5 — v1's two language-aware surfaces, executed rather than read.

Both are ports, verbatim except where noted, of ABCC v1 at `d5528ea`:

  A. `ValidateSyntaxTool._run` — `packages/agents/src/tools/code_validation.py:16-89`.
     A five-entry table mapping a *model-supplied* language string to an extension
     and a checker command. The only edit is dropping the `ActionHistory` loop hook
     (`monitoring`), which does not touch the validator.

  B. the `/run-validation` handler — `packages/agents/src/main.py:524-576`. Decides
     how to execute the task's `validationCommand`: if the first word is one of six
     binaries it is split and run; otherwise it is wrapped in the language's
     `-c`/`-e`/`-r` flag. The success rule is `returncode == 0 and "PASS" in stdout`.

The question this item asks of both: what happens when the language is not Python?

Writes v1-channel-results.json next to this file.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent


# ── A. ValidateSyntaxTool._run, verbatim (minus the ActionHistory hook) ────────
def validate_syntax(code: str, language: str) -> str:
    try:
        language = language.lower()

        # Map language to file extension and validator command
        validators = {
            'python': ('.py', ['python3', '-m', 'py_compile']),
            'javascript': ('.js', ['node', '--check']),
            'typescript': ('.ts', ['npx', '-y', 'tsx', '--help']),  # tsx doesn't have --check, fallback
            'go': ('.go', ['gofmt', '-e']),
            'php': ('.php', ['php', '-l'])
        }

        if language not in validators:
            return f"Unsupported language: {language}. Supported: {', '.join(validators.keys())}"

        ext, cmd = validators[language]

        with tempfile.NamedTemporaryFile(mode='w', suffix=ext, delete=False, encoding='utf-8') as f:
            f.write(code)
            temp_path = f.name

        try:
            if language == 'typescript':
                result = subprocess.run(
                    ['node', '--input-type=module', '--check'],
                    input=code,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    cmd + [temp_path],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

            if result.returncode == 0:
                return "OK"
            else:
                error = result.stderr or result.stdout
                error = error.replace(temp_path, f"<temp>{ext}")
                return f"Syntax error:\n{error.strip()}"

        except subprocess.TimeoutExpired:
            return "Validation timeout (code too complex?)"
        except Exception as e:
            return f"Validation failed: {str(e)}"
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    except Exception as e:
        return f"Error during validation: {str(e)}"


# ── B. /run-validation, verbatim (the dispatch and the success rule) ──────────
def run_validation(command: str, language: str, cwd: Path, timeout: int = 20) -> dict:
    command = command.strip()
    first_word = command.split()[0] if command else ""
    full_command_prefixes = ("go", "php", "python", "python3", "node", "tsx")

    if first_word in full_command_prefixes:
        cmd = shlex.split(command)
    else:
        lang = language.lower()
        if lang == "python":
            cmd = ["python3", "-c", command]
        elif lang in ("javascript", "js"):
            cmd = ["node", "-e", command]
        elif lang in ("typescript", "ts"):
            cmd = ["tsx", "-e", command]
        elif lang == "php":
            cmd = ["php", "-r", command]
        elif lang == "go":
            cmd = ["go", "run", command]
        else:
            return {"success": False, "output": f"Unsupported language: {language}",
                    "exit_code": -1, "argv": None}

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                                cwd=str(cwd), encoding="utf-8", errors="replace")
        output = result.stdout
        if result.stderr:
            output += ("\n" if output else "") + result.stderr
        success = result.returncode == 0 and "PASS" in result.stdout
        return {"success": success, "output": output.strip()[:5000],
                "exit_code": result.returncode, "argv": cmd}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": f"Validation timed out after {timeout}s",
                "exit_code": -1, "argv": cmd}
    except Exception as e:
        return {"success": False, "output": f"Validation error: {e}", "exit_code": -1, "argv": cmd}


# ── the samples ───────────────────────────────────────────────────────────────
VALID = {
    "python": "def add(a, b):\n    return a + b\n",
    "javascript": "export function add(a, b) {\n  return a + b;\n}\n",
    # Valid TypeScript, and deliberately typed: annotations are the thing a
    # TS-aware checker has to accept and a JS parser cannot.
    "typescript": "export function add(a: number, b: number): number {\n  return a + b;\n}\n",
    "go": "package main\n\nfunc add(a int, b int) int {\n\treturn a + b\n}\n",
    "php": "<?php\nfunction add($a, $b) {\n    return $a + $b;\n}\n",
    "rust": "pub fn add(a: i64, b: i64) -> i64 {\n    a + b\n}\n",
}
INVALID = {
    "python": "def add(a, b)\n    return a + b\n",
    "javascript": "export function add(a, b) {\n  return a + b;\n",
    "typescript": "export function add(a: number, b: number): number {\n  return a + b;\n",
    "go": "package main\n\nfunc add(a int, b int) int {\n\treturn a + b\n",
    "php": "<?php\nfunction add($a, $b) {\n    return $a + $b;\n",
    "rust": "pub fn add(a: i64, b: i64) -> i64 {\n    a + b\n",
}

# Validation commands a real ticket in each ecosystem would carry. The last two
# are the shape v1's own coder persona teaches (`coder.py:57`).
COMMANDS = [
    ("pytest -q", "python"),
    ("python3 -m pytest -q", "python"),
    ("ruff check .", "python"),
    ("mypy .", "python"),
    # With a `LANG=` prefix the language is whatever the ticket said; without
    # one, `extractLanguageFromCommand` (asyncValidationService.ts:476-483)
    # defaults to python. Both paths are measured.
    ("cargo test", "rust"),
    ("cargo test", "python"),
    ("npm test", "python"),
    ("npm test", "javascript"),
    ("node --test", "javascript"),
    ("go test ./...", "go"),
    ("tsc --noEmit", "typescript"),
    ('python -c "from calc import add; assert add(2,3)==5; print(\'PASS\')"', "python"),
    ('python -c "from calc import add; assert add(2,3)==5"', "python"),
]


def node_check_matrix() -> list[dict]:
    """Why v1's JavaScript rung passes broken code: the extension it picks.

    `validate_syntax` writes the model's code to a `.js` temp file and runs
    `node --check`. On node 24.15.0 that combination is silent about a file that
    contains ESM syntax *and* a syntax error — the same bytes in a `.mjs` file
    are rejected.
    """
    cases = [
        ("cjs-broken", ".js", "function add(a, b) {\n  return a + b;\n"),
        ("esm-broken", ".js", "export function add(a, b) {\n  return a + b;\n"),
        ("esm-broken", ".mjs", "export function add(a, b) {\n  return a + b;\n"),
        ("esm-broken-token", ".js", 'import x from "y";\nconst q = ;;;\n'),
        ("esm-broken-token", ".mjs", 'import x from "y";\nconst q = ;;;\n'),
        ("esm-ok", ".js", "export function add(a, b) {\n  return a + b;\n}\n"),
    ]
    rows = []
    for name, ext, code in cases:
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, encoding="utf-8") as f:
            f.write(code)
            p = f.name
        r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
        os.remove(p)
        rows.append({"case": name, "extension": ext, "exit_code": r.returncode,
                     "reads_as_ok": r.returncode == 0})
        print(f"node --check     {name:18} {ext:5} -> exit {r.returncode} "
              f"{'(reads as OK)' if r.returncode == 0 else ''}")
    return rows


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out: dict = {"validate_syntax": [], "run_validation": [], "node_check": [],
                 "node_version": subprocess.run(["node", "--version"], capture_output=True,
                                                text=True).stdout.strip()}

    for lang in ["python", "javascript", "typescript", "go", "php", "rust"]:
        for kind, table in (("valid", VALID), ("invalid", INVALID)):
            verdict = validate_syntax(table[lang], lang)
            out["validate_syntax"].append({
                "language": lang,
                "sample": kind,
                "verdict_first_line": verdict.splitlines()[0] if verdict else "",
                "verdict": verdict[:400],
                "reads_as_ok": verdict == "OK",
            })
            print(f"validate_syntax  {lang:11} {kind:8} -> {verdict.splitlines()[0][:90]}")

    print()
    out["node_check"] = node_check_matrix()

    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        # A workspace that is not empty: one module and one green test, so a
        # command that really runs has something correct to find.
        (ws / "calc.py").write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")
        (ws / "test_calc.py").write_text(
            "from calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8")
        print()
        for command, lang in COMMANDS:
            r = run_validation(command, lang, ws)
            r["command"] = command
            r["language"] = lang
            out["run_validation"].append(r)
            argv = " ".join(r["argv"]) if r["argv"] else "(none)"
            first = (r["output"].splitlines() or [""])[0][:70]
            print(f"run_validation   {command:52} -> argv[{argv[:56]:56}] "
                  f"exit={r['exit_code']!s:>5} success={r['success']!s:5} {first}")

    # On this host `python3` is the Microsoft Store alias, so the wrapped
    # commands above die at the interpreter rather than inside it. Repeat the
    # wrapper with the interpreter that works, so the finding is about the
    # wrapper and not about this machine.
    print()
    out["wrapper_on_a_working_interpreter"] = []
    for c in ["pytest -q", "cargo test", "npm test", "ruff check ."]:
        r = subprocess.run([sys.executable, "-c", c], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        first = [ln for ln in (r.stderr or "").splitlines() if ln.strip()][-1:] or [""]
        out["wrapper_on_a_working_interpreter"].append(
            {"command": c, "exit_code": r.returncode, "error": first[0][:200]})
        print(f"python -c {c:20} -> exit {r.returncode}  {first[0][:80]}")

    (HERE / "v1-channel-results.json").write_bytes(
        json.dumps(out, indent=1).encode("utf-8"))
    print(f"\nwrote {HERE / 'v1-channel-results.json'}")


if __name__ == "__main__":
    sys.exit(main())
