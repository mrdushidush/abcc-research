"""W11 item 4 — who plays the reviewer, measured in the regime where it matters.

Four artifacts, all GREEN on the acceptance criterion the ticket implies, three
of them wrong by the K-suite's own four-consumer verifier (`build.py`). The Judge
is shown the ticket, the tree, the specification the ticket names, the brief, a
body, and the measurement set. The only thing that changes between arms is who
is reviewing and what body they see:

  A  artifact       fresh call, same weights, shown the unified diff
  B  narration      fresh call, same weights, shown the author's own completion
                    report instead of the diff — v1's shape (F232)
  C  self-history   the author's own conversation, continued: system = the
                    builder head, the diff is the assistant's own previous turn,
                    and the judge instruction is appended as the next user turn
  D  swap           arm A on a second model (`swap.py`, after a load)

Every arm uses the verdict schema item 3 shipped, verbatim: `rationale`,
`defects`, `call`, in that order, because F263 measured the order as causal.

Scored two ways per call: the binary against ground truth, and the recall of the
three sites the artifact actually left broken.
"""

import json
import pathlib
import sys

import common as C

HERE = C.HERE
GT = {r["id"]: r for r in json.loads((HERE / "ground-truth.json").read_text("utf-8"))}
NARR_PATH = HERE / "narrations.json"

SITES = {
    "jobs/summary.py": ("summary", "bucket", "counts"),
    "jobs/charges.py": ("charges", "chargeable", "billing", "bill"),
    "jobs/retry.py": ("retry", "requeue", "should_retry"),
}


# ── the author's turn ────────────────────────────────────────────────


def builder_user(a):
    return f"""\
{C.context_block()}

{C.BRIEF}
Make the change."""


def narration_for(a, model=C.CHAMPION):
    """The completion report the model writes for its own change, generated once
    and cached. Its words, not the probe author's — arm B is only worth running
    if the story is the model's."""
    cache = json.loads(NARR_PATH.read_text("utf-8")) if NARR_PATH.exists() else {}
    if a["id"] in cache:
        return cache[a["id"]]
    msgs = [
        {"role": "system", "content": C.HEAD_BUILDER},
        {"role": "user", "content": builder_user(a)},
        {
            "role": "user",
            "content": f"""You made this change:

{a['diff']}
Write the completion report you would hand back, in the first person, at most six \
lines, no code. Say what you changed and why it is done.""",
        },
    ]
    r = C.call(model, msgs)
    text = (r["content"] or "").strip()
    # The model's reasoning trace is not part of the report.
    if "</think>" in text:
        text = text.split("</think>", 1)[1].strip()
    cache[a["id"]] = text
    NARR_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    print(f"   narration[{a['id']}] {r['wall_s']}s, {len(text)} chars")
    return text


# ── the arms ─────────────────────────────────────────────────────────


def messages_for(arm, a, narration):
    g = GT[a["id"]]
    meas = C.measurement_block(g["criterion_exit"], g["criterion_out"])
    if arm == "A-artifact":
        return [
            {"role": "system", "content": C.HEAD_JUDGE},
            {"role": "user", "content": C.user_judge(a, meas, C.diff_body(a))},
        ]
    if arm == "B-narration":
        return [
            {"role": "system", "content": C.HEAD_JUDGE},
            {
                "role": "user",
                "content": C.user_judge(a, meas, C.narration_body(narration)),
            },
        ]
    if arm == "E-both":
        # The realistic pipeline question, once B is known to be bad: is the
        # narration merely insufficient, or is it poison when the diff is there
        # too? A pipeline that carries a completion report has to know.
        return [
            {"role": "system", "content": C.HEAD_JUDGE},
            {
                "role": "user",
                "content": C.user_judge(
                    a, meas, C.narration_body(narration) + "\n\n" + C.diff_body(a)
                ),
            },
        ]
    if arm == "C-selfhistory":
        return [
            {"role": "system", "content": C.HEAD_BUILDER},
            {"role": "user", "content": builder_user(a)},
            {
                "role": "assistant",
                "content": f"{narration}\n\n```diff\n{a['diff']}```",
            },
            {
                "role": "user",
                "content": f"""{C.HEAD_JUDGE}
{meas}
Judge the change you just made. Return your verdict.""",
            },
        ]
    raise ValueError(arm)


def score(a, parsed):
    """Two recalls, deliberately. The defect list is the field the pipeline
    carries and the console renders; the rationale is prose nothing downstream
    reads. Scoring only the first would understate what the model knew, and
    scoring only the second would overstate what the gate gets."""
    g = GT[a["id"]]
    call = (parsed or {}).get("call")
    correct = None
    if call in ("pass", "fail"):
        correct = (call == "pass") == (g["truth"] == "PASS")
    defects = (parsed or {}).get("defects") or []
    dblob = " ".join(
        f"{d.get('path') or ''} {d.get('description') or ''}" for d in defects
    ).lower()
    ablob = dblob + " " + ((parsed or {}).get("rationale") or "").lower()
    named = [s for s in a["missing"] if any(w in dblob for w in SITES[s])]
    named_any = [s for s in a["missing"] if any(w in ablob for w in SITES[s])]
    # jobs/dashboard.py already handles `cancelled` correctly — the suite's
    # deliberate decoy. Naming it as a site to fix is a false positive.
    decoy = "dashboard" in ablob
    return call, correct, named, named_any, decoy, len(defects)


def run(arm, a, n, model, rows, tag=""):
    narration = narration_for(a) if arm != "A-artifact" else ""
    for i in range(n):
        r = C.call(model, messages_for(arm, a, narration), schema=C.VERDICT_SCHEMA)
        parsed, first_key = None, None
        try:
            parsed = json.loads(r["content"])
            first_key = next(iter(parsed))
        except Exception:  # noqa: BLE001
            pass
        call, correct, named, named_any, decoy, ndef = score(a, parsed)
        rows.append(
            {
                "arm": arm,
                "artifact": a["id"],
                "model": model,
                "rep": i + 1,
                "truth": GT[a["id"]]["truth"],
                "call": call,
                "correct": correct,
                "sites_missing": len(a["missing"]),
                "sites_named": named,
                "sites_named_any": named_any,
                "decoy_named": decoy,
                "n_defects": ndef,
                "first_key": first_key,
                "rationale": (parsed or {}).get("rationale", "")[:600],
                "finish_reason": r["finish_reason"],
                "completion_tokens": r["usage"].get("completion_tokens"),
                "reasoning_tokens": (
                    r["usage"].get("completion_tokens_details") or {}
                ).get("reasoning_tokens"),
                "prompt_tokens": r["usage"].get("prompt_tokens"),
                "wall_s": r["wall_s"],
                "error": r["error"],
                "raw": (r["content"] or "")[:1500],
            }
        )
        mark = "ok " if correct else "MISS"
        print(
            f"{tag}{arm:<14} {a['id']:<8} rep{i+1} truth={GT[a['id']]['truth']:<4} "
            f"call={str(call):<5} [{mark}] sites={len(named)}/{len(named_any)}"
            f"/{len(a['missing'])} def={ndef}{' decoy' if decoy else ''} "
            f"{r['wall_s']:5.1f}s",
            flush=True,
        )


def summarise(rows):
    print("\n-- by arm --")
    arms = []
    for arm in dict.fromkeys(r["arm"] for r in rows):
        sub = [r for r in rows if r["arm"] == arm]
        ok = sum(1 for r in sub if r["correct"])
        bad = [r for r in sub if r["truth"] == "FAIL"]
        fp = sum(1 for r in bad if r["call"] == "pass")
        good = [r for r in sub if r["truth"] == "PASS"]
        fn = sum(1 for r in good if r["call"] == "fail")
        tot_sites = sum(r["sites_missing"] for r in bad)
        got_sites = sum(len(r["sites_named"]) for r in bad)
        got_any = sum(len(r["sites_named_any"]) for r in bad)
        decoys = sum(1 for r in sub if r["decoy_named"])
        arms.append((arm, ok, len(sub), fp, len(bad), fn, len(good), got_sites, tot_sites))
        print(
            f"{arm:<14} correct {ok}/{len(sub)}   false-pass {fp}/{len(bad)}   "
            f"false-fail {fn}/{len(good)}   sites(defects) {got_sites}/{tot_sites}   "
            f"sites(any) {got_any}/{tot_sites}   decoy {decoys}/{len(sub)}"
        )
    print("\n-- by artifact --")
    for aid in dict.fromkeys(r["artifact"] for r in rows):
        sub = [r for r in rows if r["artifact"] == aid]
        line = "  ".join(
            f"{r['arm'].split('-')[0]}:{r['call']}" for r in sub
        )
        print(f"{aid:<9} truth={GT[aid]['truth']:<5} {line}")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    rows = []
    print("-- narrations (cached) --")
    for a in C.ARTIFACTS:
        narration_for(a)
    print()
    for arm in ("A-artifact", "B-narration", "C-selfhistory"):
        print(f"-- {arm} --")
        for a in C.ARTIFACTS:
            run(arm, a, n, C.CHAMPION, rows)
        print()
    (HERE / "independence-results.json").write_text(
        json.dumps(rows, indent=2), encoding="utf-8"
    )
    summarise(rows)


if __name__ == "__main__":
    main()
