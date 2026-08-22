"""What a diff scanner sees, when the linter and the type checker see nothing.

The ladder's rungs all read the tree as a program. This reads it as a *change*:
which files the attempt added, deleted and modified, and whether any of that
separates a tree the suite verifier accepts from one it rejects.

Three candidate vetoes, all deterministic, all costing one directory walk:

  * **residue**   — a file the attempt left behind that the repository never had
                    and the ticket never asked for (`_analyze_tmp.py`).
  * **test edit** — the attempt modified a test that judges it.
  * **breadth**   — how many source files the change touched, against how many
                    the reference solution touched. F290 asked for a coverage
                    fraction; this is the cheapest possible one, computed with no
                    model and no criterion.

    python residue.py
"""

import json

import common as C

OUT = C.HERE / "residue-results.json"
SKIP_PARTS = ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")


def tree(root):
    out = {}
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if any(s in rel for s in SKIP_PARTS):
            continue
        try:
            body = p.read_bytes().replace(b"\r\n", b"\n")
        except OSError:
            continue
        out[rel] = body
    return out


def classify(rel):
    return "test" if rel.startswith("tests/") or "/tests/" in rel else "source"


def main():
    truth = {}
    for r in json.loads((C.HERE / "results-k.json").read_text(encoding="utf-8")):
        truth[r["id"]] = r["truth"]["verdict"]

    fixtures = {t: tree(C.K_TASKS / t / "fixture") for t in C.k_task_ids()}
    refsol_touch = {}
    for t in C.k_task_ids():
        n = 0
        for p in (C.K_TASKS / t / "refsol").rglob("*"):
            if p.is_file():
                n += 1
        refsol_touch[t] = n

    rows = []
    for d in C.cells(suite="k"):
        if not d["_wd"]:
            continue
        base = fixtures[d["task"]]
        cur = tree(d["_wd"])
        added = sorted(set(cur) - set(base))
        deleted = sorted(set(base) - set(cur))
        modified = sorted(k for k in set(cur) & set(base) if cur[k] != base[k])
        row = {
            "id": d["_id"],
            "task": d["task"],
            "status": d["status"],
            "truth": truth.get(d["_id"], "-"),
            "added": added,
            "deleted": deleted,
            "modified": modified,
            "src_modified": [m for m in modified if classify(m) == "source"],
            "test_modified": [m for m in modified if classify(m) == "test"],
            "src_added": [a for a in added if classify(a) == "source"],
            "test_added": [a for a in added if classify(a) == "test"],
            "refsol_files": refsol_touch[d["task"]],
        }
        rows.append(row)
        print(
            "%-52s %-5s +%d -%d ~%d  src~%d test~%d  refsol touched %d"
            % (row["id"], row["truth"], len(added), len(deleted), len(modified),
               len(row["src_modified"]), len(row["test_modified"]), row["refsol_files"]),
            flush=True,
        )
    OUT.write_text(json.dumps(rows, indent=1), encoding="utf-8")

    def rate(pred, label):
        f = [r for r in rows if r["truth"] == "FAIL"]
        p = [r for r in rows if r["truth"] == "PASS"]
        print("%-38s fires on %2d/%-2d FAIL   %2d/%-2d PASS"
              % (label, sum(1 for r in f if pred(r)), len(f),
                 sum(1 for r in p if pred(r)), len(p)))

    print()
    rate(lambda r: bool(r["src_added"]), "residue: a new source file")
    rate(lambda r: bool(r["test_modified"]), "the change edited an existing test")
    rate(lambda r: not r["test_added"] and not r["test_modified"],
         "no test was added or changed at all")
    rate(lambda r: len(r["src_modified"]) < r["refsol_files"],
         "touched fewer files than the refsol does")
    rate(lambda r: len(r["src_modified"]) == 0, "touched no source file at all")


if __name__ == "__main__":
    main()
