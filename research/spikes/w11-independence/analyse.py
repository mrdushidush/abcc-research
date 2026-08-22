"""One table per question, over whatever result files exist."""

import json
import pathlib
import statistics as S

import common as C

HERE = C.HERE
FILES = [
    "independence-results.json",
    "armE-results.json",
    "swap-results.json",
]


def load():
    rows = []
    for f in FILES:
        p = HERE / f
        if not p.exists():
            continue
        data = json.loads(p.read_text("utf-8"))
        rows += data["rows"] if isinstance(data, dict) else data
    return rows


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(S.median(xs), 1) if xs else None


def main():
    rows = load()
    if not rows:
        raise SystemExit("no results yet")
    arms = list(dict.fromkeys(r["arm"] + " @ " + r["model"] for r in rows))

    print(
        f"{'arm':<32} {'correct':>8} {'false-pass':>11} {'false-fail':>11} "
        f"{'sites(def)':>11} {'sites(any)':>11} {'decoy':>6} {'med s':>6} {'med comp':>9}"
    )
    for key in arms:
        arm, model = key.split(" @ ")
        sub = [r for r in rows if r["arm"] == arm and r["model"] == model]
        bad = [r for r in sub if r["truth"] == "FAIL"]
        good = [r for r in sub if r["truth"] == "PASS"]
        ok = sum(1 for r in sub if r["correct"])
        fp = sum(1 for r in bad if r["call"] != "fail")
        fn = sum(1 for r in good if r["call"] != "pass")
        ts = sum(r["sites_missing"] for r in bad)
        gd = sum(len(r["sites_named"]) for r in bad)
        ga = sum(len(r["sites_named_any"]) for r in bad)
        dc = sum(1 for r in sub if r["decoy_named"])
        print(
            f"{key:<32} {ok:>4}/{len(sub):<3} {fp:>6}/{len(bad):<4} {fn:>6}/{len(good):<4} "
            f"{gd:>6}/{ts:<4} {ga:>6}/{ts:<4} {dc:>3}/{len(sub):<2} "
            f"{med([r['wall_s'] for r in sub]):>6} {str(med([r['completion_tokens'] for r in sub])):>9}"
        )

    print("\nper artifact (call, per rep):")
    for aid in [a["id"] for a in C.ARTIFACTS]:
        print(f"  {aid:<9} truth={[r for r in rows if r['artifact'] == aid][0]['truth']}")
        for key in arms:
            arm, model = key.split(" @ ")
            sub = [r for r in rows if r["artifact"] == aid and r["arm"] == arm
                   and r["model"] == model]
            if sub:
                print(f"    {key:<32} {' '.join(str(r['call']) for r in sub)}")

    bad_rows = [r for r in rows if r["call"] not in ("pass", "fail")]
    if bad_rows:
        print("\nnon-verdicts:")
        for r in bad_rows:
            print(
                f"  {r['arm']:<14} {r['artifact']:<8} rep{r['rep']} "
                f"finish={r['finish_reason']} comp={r['completion_tokens']} "
                f"reas={r['reasoning_tokens']} err={str(r['error'])[:60]} "
                f"raw={r['raw'][:60]!r}"
            )


if __name__ == "__main__":
    main()
