#!/usr/bin/env python3
"""W6 item 5 — the same ticket, the same defects, three languages, two coding styles.

One task ("a fourth order status was added to the type; make the four consumers
handle it"), expressed identically in Python, TypeScript and Rust. Seven candidate
answers per language, from "did nothing" to "correct". Two styles for the subject
code: `wildcard`, where every consumer has a catch-all arm, and `exhaustive`, where
none does and the language's exhaustiveness rule applies.

Each tree is run through four instruments: the syntax check, the type check, the
linter, the repository's own test suite, and the acceptance test. Ground truth is
by construction — every mutant except `m5_reference` fails the ticket, and
`m6_regression` is the one that fails it by breaking something that used to work.

Answers OQ-W6-9 (does the picture change where the type checker is the build) with
the language as the only variable.

Usage:  python mutants.py [--only py|ts|rs]
Writes: mutants-results.json next to this file. Trees go in ./trees (git-ignored).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
TREES = HERE / "trees"
TSC = HERE / "node_modules" / "typescript" / "bin" / "tsc"

# ── the seven candidate answers ────────────────────────────────────────────────
# sites: which of the four consumers got the new arm.
# extra: an additional defect layered on top of a complete change.
MUTANTS = [
    ("m0_empty", (), None, "no change at all"),
    ("m1_one_site", (1,), None, "1 of 4 consumers handled"),
    ("m2_three_sites", (1, 2, 3), None, "3 of 4 consumers handled"),
    ("m3_wrong_semantics", (1, 2, 3, 4), "semantics", "all 4 touched, is_terminal wrong"),
    ("m4_wrong_type", (1, 2, 3, 4), "type", "all 4 touched, bucket returns a bool"),
    ("m5_reference", (1, 2, 3, 4), None, "correct"),
    ("m6_regression", (1, 2, 3, 4), "regression", "correct for DISPUTED, breaks REFUNDED"),
]
# By construction: everything but m5 fails the ticket. m6 is the only one whose
# damage is visible to the pre-existing suite.
CORRECT = {"m5_reference"}
REGRESSION = {"m6_regression"}


# ── Python ─────────────────────────────────────────────────────────────────────
def py_tree(style: str, sites: tuple[int, ...], extra: str | None) -> dict[str, str]:
    wild = style == "wildcard"
    arm1_val = "True" if extra == "type" else '"held"'
    arm1 = f"        case Status.DISPUTED:\n            return {arm1_val}\n" if 1 in sites else ""
    arm2_val = "False" if extra == "semantics" else "True"
    arm2 = f"        case Status.DISPUTED:\n            return {arm2_val}\n" if 2 in sites else ""
    arm3 = '        case Status.DISPUTED:\n            return "Disputed"\n' if 3 in sites else ""
    arm4 = "        case Status.DISPUTED:\n            return True\n" if 4 in sites else ""
    refunded_terminal = "False" if extra == "regression" else "True"
    tail = "" if wild else "    assert_never(status)\n"
    tail_o = "" if wild else "    assert_never(order.status)\n"
    w = (lambda body: f"        case _:\n            return {body}\n") if wild else (lambda body: "")
    imports = "" if wild else "from typing import assert_never\n"

    lib = f'''"""Order lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
{imports}

class Status(Enum):
    NEW = "new"
    PAID = "paid"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


@dataclass(frozen=True)
class Order:
    ident: str
    status: Status
    amount_p: int


def bucket(order: Order) -> str:
    """Which dashboard bucket the order is counted in."""
    match order.status:
        case Status.NEW:
            return "queued"
        case Status.PAID:
            return "done"
        case Status.REFUNDED:
            return "done"
{arm1}{w('"other"')}{tail_o}

def is_terminal(status: Status) -> bool:
    """True when no further transition is possible."""
    match status:
        case Status.NEW:
            return False
        case Status.PAID:
            return False
        case Status.REFUNDED:
            return {refunded_terminal}
{arm2}{w("False")}{tail}

def label(status: Status) -> str:
    """Human-readable name for the console."""
    match status:
        case Status.NEW:
            return "New"
        case Status.PAID:
            return "Paid"
        case Status.REFUNDED:
            return "Refunded"
{arm3}{w('"Unknown"')}{tail}

def needs_followup(order: Order) -> bool:
    """True when a human has to look at this order."""
    match order.status:
        case Status.NEW:
            return False
        case Status.PAID:
            return False
        case Status.REFUNDED:
            return False
{arm4}{w("False")}{tail_o}'''

    repo_tests = '''from orders import Order, Status, bucket, is_terminal, label, needs_followup


def _o(status: Status) -> Order:
    return Order("o1", status, 500)


def test_buckets_for_the_original_three() -> None:
    assert bucket(_o(Status.NEW)) == "queued"
    assert bucket(_o(Status.PAID)) == "done"
    assert bucket(_o(Status.REFUNDED)) == "done"


def test_terminality_for_the_original_three() -> None:
    assert is_terminal(Status.NEW) is False
    assert is_terminal(Status.PAID) is False
    assert is_terminal(Status.REFUNDED) is True


def test_labels_for_the_original_three() -> None:
    assert label(Status.NEW) == "New"
    assert label(Status.PAID) == "Paid"
    assert label(Status.REFUNDED) == "Refunded"


def test_followup_for_the_original_three() -> None:
    assert needs_followup(_o(Status.NEW)) is False
    assert needs_followup(_o(Status.PAID)) is False
    assert needs_followup(_o(Status.REFUNDED)) is False
'''

    acceptance = '''from orders import Order, Status, bucket, is_terminal, label, needs_followup


def test_disputed_is_held() -> None:
    assert bucket(Order("o1", Status.DISPUTED, 500)) == "held"


def test_disputed_is_terminal() -> None:
    assert is_terminal(Status.DISPUTED) is True


def test_disputed_label() -> None:
    assert label(Status.DISPUTED) == "Disputed"


def test_disputed_needs_followup() -> None:
    assert needs_followup(Order("o1", Status.DISPUTED, 500)) is True
'''
    return {
        "orders.py": lib,
        "conftest.py": "",
        "tests_repo/test_orders.py": repo_tests,
        "acceptance/test_disputed.py": acceptance,
    }


# ── TypeScript ─────────────────────────────────────────────────────────────────
def ts_tree(style: str, sites: tuple[int, ...], extra: str | None) -> dict[str, str]:
    wild = style == "wildcard"
    arm1_val = "true" if extra == "type" else '"held"'
    arm1 = f'    case "disputed":\n      return {arm1_val};\n' if 1 in sites else ""
    arm2_val = "false" if extra == "semantics" else "true"
    arm2 = f'    case "disputed":\n      return {arm2_val};\n' if 2 in sites else ""
    arm3 = '    case "disputed":\n      return "Disputed";\n' if 3 in sites else ""
    arm4 = '    case "disputed":\n      return true;\n' if 4 in sites else ""
    refunded_terminal = "false" if extra == "regression" else "true"

    def close(default: str, expr: str) -> str:
        if wild:
            return f"    default:\n      return {default};\n  }}\n}}\n"
        return f"  }}\n  const unhandled: never = {expr};\n  return unhandled;\n}}\n"

    lib = f'''/** Order lifecycle helpers. */

// A string-literal union rather than a TS `enum`: node's type-stripping runtime
// rejects `enum` as non-erasable syntax, and the union is what the `never`
// exhaustiveness idiom is written against.
export type Status = "new" | "paid" | "refunded" | "disputed";

export interface Order {{
  ident: string;
  status: Status;
  amountP: number;
}}

/** Which dashboard bucket the order is counted in. */
export function bucket(order: Order): string {{
  switch (order.status) {{
    case "new":
      return "queued";
    case "paid":
      return "done";
    case "refunded":
      return "done";
{arm1}{close('"other"', "order.status")}
/** True when no further transition is possible. */
export function isTerminal(status: Status): boolean {{
  switch (status) {{
    case "new":
      return false;
    case "paid":
      return false;
    case "refunded":
      return {refunded_terminal};
{arm2}{close("false", "status")}
/** Human-readable name for the console. */
export function label(status: Status): string {{
  switch (status) {{
    case "new":
      return "New";
    case "paid":
      return "Paid";
    case "refunded":
      return "Refunded";
{arm3}{close('"Unknown"', "status")}
/** True when a human has to look at this order. */
export function needsFollowup(order: Order): boolean {{
  switch (order.status) {{
    case "new":
      return false;
    case "paid":
      return false;
    case "refunded":
      return false;
{arm4}{close("false", "order.status")}'''

    repo_tests = '''import { test } from "node:test";
import assert from "node:assert/strict";
import { type Order, type Status, bucket, isTerminal, label, needsFollowup } from "../orders.ts";

const o = (status: Status): Order => ({ ident: "o1", status, amountP: 500 });

test("buckets for the original three", () => {
  assert.equal(bucket(o("new")), "queued");
  assert.equal(bucket(o("paid")), "done");
  assert.equal(bucket(o("refunded")), "done");
});

test("terminality for the original three", () => {
  assert.equal(isTerminal("new"), false);
  assert.equal(isTerminal("paid"), false);
  assert.equal(isTerminal("refunded"), true);
});

test("labels for the original three", () => {
  assert.equal(label("new"), "New");
  assert.equal(label("paid"), "Paid");
  assert.equal(label("refunded"), "Refunded");
});

test("followup for the original three", () => {
  assert.equal(needsFollowup(o("new")), false);
  assert.equal(needsFollowup(o("paid")), false);
  assert.equal(needsFollowup(o("refunded")), false);
});
'''

    acceptance = '''import { test } from "node:test";
import assert from "node:assert/strict";
import { type Order, bucket, isTerminal, label, needsFollowup } from "../orders.ts";

const disputed: Order = { ident: "o1", status: "disputed", amountP: 500 };

test("disputed is held", () => {
  assert.equal(bucket(disputed), "held");
});

test("disputed is terminal", () => {
  assert.equal(isTerminal("disputed"), true);
});

test("disputed label", () => {
  assert.equal(label("disputed"), "Disputed");
});

test("disputed needs followup", () => {
  assert.equal(needsFollowup(disputed), true);
});
'''

    tsconfig = json.dumps(
        {
            "compilerOptions": {
                "target": "ES2022",
                "module": "nodenext",
                "moduleResolution": "nodenext",
                "allowImportingTsExtensions": True,
                "strict": True,
                "noEmit": True,
                "typeRoots": [str((HERE / "node_modules" / "@types").as_posix())],
                "types": ["node"],
                "skipLibCheck": True,
            },
            "include": ["orders.ts", "tests_repo/**/*.ts", "acceptance/**/*.ts"],
        },
        indent=2,
    )
    return {
        "orders.ts": lib,
        "tests_repo/orders.test.ts": repo_tests,
        "acceptance/disputed.test.ts": acceptance,
        "tsconfig.json": tsconfig,
    }


# ── Rust ───────────────────────────────────────────────────────────────────────
def rs_tree(style: str, sites: tuple[int, ...], extra: str | None) -> dict[str, str]:
    wild = style == "wildcard"
    arm1_val = "true" if extra == "type" else '"held"'
    arm1 = f"        Status::Disputed => {arm1_val},\n" if 1 in sites else ""
    arm2_val = "false" if extra == "semantics" else "true"
    arm2 = f"        Status::Disputed => {arm2_val},\n" if 2 in sites else ""
    arm3 = '        Status::Disputed => "Disputed",\n' if 3 in sites else ""
    arm4 = "        Status::Disputed => true,\n" if 4 in sites else ""
    refunded_terminal = "false" if extra == "regression" else "true"
    w = (lambda body: f"        _ => {body},\n") if wild else (lambda body: "")

    lib = f'''//! Order lifecycle helpers.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Status {{
    New,
    Paid,
    Refunded,
    Disputed,
}}

#[derive(Debug, Clone)]
pub struct Order {{
    pub ident: String,
    pub status: Status,
    pub amount_p: i64,
}}

/// Which dashboard bucket the order is counted in.
pub fn bucket(order: &Order) -> &'static str {{
    match order.status {{
        Status::New => "queued",
        Status::Paid => "done",
        Status::Refunded => "done",
{arm1}{w('"other"')}    }}
}}

/// True when no further transition is possible.
pub fn is_terminal(status: Status) -> bool {{
    match status {{
        Status::New => false,
        Status::Paid => false,
        Status::Refunded => {refunded_terminal},
{arm2}{w("false")}    }}
}}

/// Human-readable name for the console.
pub fn label(status: Status) -> &'static str {{
    match status {{
        Status::New => "New",
        Status::Paid => "Paid",
        Status::Refunded => "Refunded",
{arm3}{w('"Unknown"')}    }}
}}

/// True when a human has to look at this order.
pub fn needs_followup(order: &Order) -> bool {{
    match order.status {{
        Status::New => false,
        Status::Paid => false,
        Status::Refunded => false,
{arm4}{w("false")}    }}
}}

#[cfg(test)]
mod tests {{
    use super::*;

    fn o(status: Status) -> Order {{
        Order {{ ident: "o1".to_string(), status, amount_p: 500 }}
    }}

    #[test]
    fn buckets_for_the_original_three() {{
        assert_eq!(bucket(&o(Status::New)), "queued");
        assert_eq!(bucket(&o(Status::Paid)), "done");
        assert_eq!(bucket(&o(Status::Refunded)), "done");
    }}

    #[test]
    fn terminality_for_the_original_three() {{
        assert!(!is_terminal(Status::New));
        assert!(!is_terminal(Status::Paid));
        assert!(is_terminal(Status::Refunded));
    }}

    #[test]
    fn labels_for_the_original_three() {{
        assert_eq!(label(Status::New), "New");
        assert_eq!(label(Status::Paid), "Paid");
        assert_eq!(label(Status::Refunded), "Refunded");
    }}

    #[test]
    fn followup_for_the_original_three() {{
        assert!(!needs_followup(&o(Status::New)));
        assert!(!needs_followup(&o(Status::Paid)));
        assert!(!needs_followup(&o(Status::Refunded)));
    }}
}}
'''

    acceptance = '''use orders::{bucket, is_terminal, label, needs_followup, Order, Status};

fn disputed() -> Order {
    Order { ident: "o1".to_string(), status: Status::Disputed, amount_p: 500 }
}

#[test]
fn disputed_is_held() {
    assert_eq!(bucket(&disputed()), "held");
}

#[test]
fn disputed_is_terminal() {
    assert!(is_terminal(Status::Disputed));
}

#[test]
fn disputed_label() {
    assert_eq!(label(Status::Disputed), "Disputed");
}

#[test]
fn disputed_needs_followup() {
    assert!(needs_followup(&disputed()));
}
'''
    cargo = '[package]\nname = "orders"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n'
    return {
        "Cargo.toml": cargo,
        "src/lib.rs": lib,
        "tests/acceptance.rs": acceptance,
    }


BUILDERS = {"py": py_tree, "ts": ts_tree, "rs": rs_tree}


# ── running the instruments ────────────────────────────────────────────────────
def run(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[str, int, str]:
    """Return (verdict, ms, tail). verdict: green | red | error."""
    t0 = time.perf_counter()
    try:
        p = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
    except FileNotFoundError:
        return "error", int((time.perf_counter() - t0) * 1000), "binary not found"
    except subprocess.TimeoutExpired:
        return "error", int((time.perf_counter() - t0) * 1000), "timeout"
    ms = int((time.perf_counter() - t0) * 1000)
    out = ((p.stdout or "") + "\n" + (p.stderr or "")).strip()
    return ("green" if p.returncode == 0 else "red"), ms, out[-600:]


def instruments(lang: str, tree: Path) -> dict[str, tuple[str, int, str]]:
    py = sys.executable
    if lang == "py":
        return {
            "syntax": run([py, "-m", "py_compile", "orders.py"], tree),
            "typecheck": run([py, "-m", "mypy", "--no-incremental", "orders.py"], tree),
            "lint": run([py, "-m", "ruff", "check", "orders.py"], tree),
            "repo_tests": run([py, "-m", "pytest", "-q", "tests_repo"], tree),
            "acceptance": run([py, "-m", "pytest", "-q", "acceptance"], tree),
        }
    if lang == "ts":
        node = "node"
        return {
            # Node's own type-stripping parser is the closest thing TS has to a
            # syntax-only check: it parses and erases types without checking them.
            "syntax": run([node, "--experimental-strip-types", "-e",
                           "import('./orders.ts').then(()=>{},e=>{console.error(e.message);process.exit(1)})"], tree),
            "typecheck": run([node, str(TSC), "-p", "tsconfig.json"], tree),
            "lint": ("skipped", 0, "no linter installed for ts"),
            "repo_tests": run([node, "--test", "tests_repo/orders.test.ts"], tree),
            "acceptance": run([node, "--test", "acceptance/disputed.test.ts"], tree),
        }
    if lang == "rs":
        return {
            "syntax": run(["cargo", "check", "--lib", "--message-format=short"], tree),
            "typecheck": run(["cargo", "check", "--lib", "--message-format=short"], tree),
            "lint": run(["cargo", "clippy", "--lib", "--", "-D", "warnings"], tree),
            "repo_tests": run(["cargo", "test", "--lib"], tree),
            "acceptance": run(["cargo", "test", "--test", "acceptance"], tree),
        }
    raise ValueError(lang)


def main() -> None:
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1]
    if TREES.exists():
        shutil.rmtree(TREES, ignore_errors=True)
    results = []
    for lang in ["py", "ts", "rs"]:
        if only and lang != only:
            continue
        for style in ["wildcard", "exhaustive"]:
            for name, sites, extra, note in MUTANTS:
                tree = TREES / f"{lang}-{style}-{name}"
                for rel, content in BUILDERS[lang](style, sites, extra).items():
                    p = tree / rel
                    p.parent.mkdir(parents=True, exist_ok=True)
                    p.write_bytes(content.encode("utf-8"))
                res = instruments(lang, tree)
                row = {
                    "lang": lang, "style": style, "mutant": name, "note": note,
                    "correct": name in CORRECT,
                    "breaks_existing": name in REGRESSION,
                    **{k: {"verdict": v[0], "ms": v[1], "tail": v[2]} for k, v in res.items()},
                }
                results.append(row)
                print(
                    f"{lang:3} {style:11} {name:20} "
                    + " ".join(f"{k}={v[0]:>7}" for k, v in res.items()),
                    flush=True,
                )
    out = HERE / "mutants-results.json"
    out.write_bytes(json.dumps(results, indent=1).encode("utf-8"))
    print(f"\nwrote {out} ({len(results)} rows)")


if __name__ == "__main__":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    main()
