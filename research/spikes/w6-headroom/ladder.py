"""Run every rung of the ladder over a population and record what each one said.

    python ladder.py constructed          # K fixtures: unfixed / refsol / sham
    python ladder.py k                    # every preserved K agent workdir
    python ladder.py q56 [limit]          # every preserved Q56 agent workdir

Ground truth is re-measured, never taken from the record: the suite verifier is
run here, on a separate copy of the same tree, so that a disagreement with what
the run recorded shows up as a disagreement rather than as silence.

Instruments run on a copy with the caches and `target/` stripped — and for Q56
also with `tests/`, which is where the verifier leaves its hidden tests. An
instrument reading those would be reading the answer key.
"""

import json
import pathlib
import shutil
import sys
import time

import common as C
import instruments as I

OUT = C.HERE


def measure(tree, ladder, truth_fn):
    row = {"instruments": {}}
    for name, fn in ladder:
        with C.Work(tree) as w:
            r = fn(w)
        r.pop("hits", None) if False else None
        row["instruments"][name] = r
    v, line, ms = truth_fn()
    row["truth"] = {"verdict": v, "line": line, "ms": ms}
    return row


def run_constructed():
    results = []
    for task_id in C.k_task_ids():
        task = C.K_TASKS / task_id
        for art_id, make in C.constructed(task_id):
            tmp = pathlib.Path(C.tempfile.mkdtemp(prefix="w6hr-c-"))
            try:
                work = make(tmp / "work")
                row = {"pop": "constructed", "task": task_id, "id": art_id,
                       "instruments": {}}
                for name, fn in I.py_ladder(task_id):
                    with C.Work(work) as w:
                        row["instruments"][name] = fn(w)
                with C.Work(work) as w:
                    v, line, ms = C.verify(w, task / "verify.sh")
                row["truth"] = {"verdict": v, "line": line, "ms": ms}
                results.append(row)
                print(f"{task_id:34} {art_id:8} truth={v:8} "
                      + " ".join(f"{n}={row['instruments'][n]['verdict'][0]}"
                                 for n in row["instruments"]), flush=True)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
    (OUT / "results-constructed.json").write_text(
        json.dumps(results, indent=1), encoding="utf-8")
    return results


def run_k():
    results = []
    for d in C.cells(suite="k"):
        if not d["_wd"]:
            continue
        task = C.K_TASKS / d["task"]
        row = {"pop": "k", "task": d["task"], "id": d["_id"],
               "run": d["_run"], "variant": d.get("variant"),
               "subject_model": (d.get("model") or d.get("subject")),
               "status": d["status"],
               "recorded": (d.get("verifier") or {}).get("verdict", "-"),
               "instruments": {}}
        for name, fn in I.py_ladder(d["task"]):
            with C.Work(d["_wd"]) as w:
                row["instruments"][name] = fn(w)
        with C.Work(d["_wd"]) as w:
            v, line, ms = C.verify(w, task / "verify.sh")
        row["truth"] = {"verdict": v, "line": line, "ms": ms}
        results.append(row)
        print(f"{row['id']:52} rec={row['recorded']:8} now={v:8} "
              + " ".join(f"{n}={row['instruments'][n]['verdict'][0]}"
                         for n in row["instruments"]), flush=True)
    (OUT / "results-k.json").write_text(json.dumps(results, indent=1),
                                        encoding="utf-8")
    return results


def run_q56(limit=None):
    # resumable: a run that is killed (or that hits a task whose solution spins)
    # should not throw away the cells it already measured
    results = []
    if (OUT / "results-q56.json").exists():
        results = json.loads((OUT / "results-q56.json").read_text(encoding="utf-8"))
    done = {r["id"] for r in results}
    t0 = time.time()
    for i, d in enumerate(C.cells(suite="q56")):
        if not d["_wd"]:
            continue
        if limit and len(results) >= limit:
            break
        task = C.Q56_TASKS / d["task"]
        vsh = task / "verify.sh"
        if not vsh.is_file() or d["_uid"] in done:
            continue
        lang, rungs = I.q56_ladder(d["task"])
        if not rungs:
            continue                      # node / typescript / shell: item 5's
        residue = I.verifier_residue(d["task"])
        row = {"pop": "q56", "task": d["task"], "id": d["_uid"], "run": d["_run"],
               "variant": d.get("variant"), "status": d["status"], "lang": lang,
               "recorded": (d.get("verifier") or {}).get("verdict", "-"),
               # recorded for the reader: the answer key the verifier left behind.
               # Build artefacts are dropped from the record (not from the
               # deletion) — `target/` never reaches an instrument anyway,
               # because Work() does not copy it.
               "residue": sorted(r for r in residue
                                 if not r.startswith(("target/", ".pytest_cache/",
                                                      "__pycache__/"))),
               "instruments": {}}
        for name, fn in rungs:
            with C.Work(d["_wd"]) as w:
                for rel in residue:       # never run the answer key
                    (w / rel).unlink(missing_ok=True)
                row["instruments"][name] = fn(w)
        tr = d.get("transcript", "")
        tr = (C.REPO / tr.replace("../", "").replace("\\", "/")) if tr else ""
        with C.Work(d["_wd"]) as w:
            for rel in residue:
                (w / rel).unlink(missing_ok=True)
            v, line, ms = C.verify(w, vsh, transcript=tr)
        row["truth"] = {"verdict": v, "line": line, "ms": ms}
        results.append(row)
        print(f"[{len(results):>4} {int(time.time()-t0):>5}s] {row['id']:46} "
              f"rec={row['recorded']:8} now={v:8} "
              + " ".join(f"{n.split('_')[-1]}={row['instruments'][n]['verdict'][0]}"
                         for n in row["instruments"]), flush=True)
        if len(results) % 25 == 0:
            (OUT / "results-q56.json").write_text(json.dumps(results, indent=1),
                                                  encoding="utf-8")
    (OUT / "results-q56.json").write_text(json.dumps(results, indent=1),
                                          encoding="utf-8")
    return results


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "constructed"
    if which == "constructed":
        run_constructed()
    elif which == "k":
        run_k()
    elif which == "q56":
        run_q56(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    else:
        sys.exit(f"unknown population {which}")
