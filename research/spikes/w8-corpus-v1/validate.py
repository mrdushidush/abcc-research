#!/usr/bin/env python3
"""Check `corpus/` against corpus/SPEC.md v1 (THROWAWAY).

The real loader is Rust and is step 2. This exists for one reason: a schema whose only example
has never been checked against it is a schema that is approximately right, and the whole point
of the provenance block is that approximately right is not good enough.

Implements SPEC.md §13's ten rejection rules, plus the §5 variant merge and the §10 aggregate
arithmetic. Every rule is numbered to match the spec, so a rule that changes there and not here
shows up as a numbering gap rather than as silence.

Run: python validate.py [corpus-root]
     python validate.py [corpus-root] --facts    a sorted fact stream

`--facts` was added when the Rust loader (harness/crates/w8-corpus) was ported from this file.
A port whose reference is a script nobody re-ran is a port that agrees by assertion. Both
implementations emit the same sorted lines, so `diff` is the check.

Run: python validate.py corpus --facts > /tmp/py.txt
     w8-corpus corpus --facts > /tmp/rs.txt && diff /tmp/py.txt /tmp/rs.txt
"""
import sys
import tomllib
from pathlib import Path

SCHEMA = 1
PERM_MODES = {"read_only", "workspace_write", "danger_full_access", "allow"}
VERIFIABLE = {"full", "presence_only", "none"}
QUARANTINE = {"none", "with_baseline"}
GATE_VERDICTS = {"sound", "broken", "inconclusive", "not_run"}
DO_STRINGS = {"approve", "deny"}

# SPEC.md §3. Closed by design: adding a name is a schema bump, and it is only because the
# vocabulary is closed that "the three lists partition it" is a checkable claim at all.
PARTITION = {
    "id", "title", "lang", "kind", "timeout_s", "turn", "prompt", "fixture", "verify",
    "refsol", "sham", "variants", "disposition", "selection", "gate", "donor_tags",
}

errors, notes, facts = [], [], []


def do_label(do):
    """The `do` action as one word, matching the Rust loader's Action::label()."""
    if isinstance(do, dict):
        return "redirect"
    return do if do in DO_STRINGS else "?"


def bad(rule, where, msg):
    errors.append(f"[rule {rule}] {where}: {msg}")


def load(p):
    try:
        return tomllib.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        bad(0, p.as_posix(), f"does not parse: {e}")
        return None


def check_variant(v, where, capabilities):
    """Rules 3 and 8, plus the operator-rule grammar of §5."""
    vid = v.get("id", "<no id>")
    mode = (v.get("permissions") or {}).get("mode")
    if mode == "prompt":
        bad(3, f"{where}[{vid}]",
            'permissions.mode = "prompt" is rejected: PermissionMode derives Ord at fc1ea22 '
            "with Prompt above DangerFullAccess, so a Prompt session auto-approves everything")
    elif mode not in PERM_MODES:
        bad(3, f"{where}[{vid}]", f"permissions.mode = {mode!r} not in {sorted(PERM_MODES)}")

    for cap in v.get("requires", []):
        if capabilities is not None and cap not in capabilities:
            notes.append(f"  n/a  {where}[{vid}] requires {cap!r}: NotSupported by the subject")

    for i, rule in enumerate(v.get("operator", [])):
        at = f"{where}[{vid}].operator[{i}]"
        if "on" not in rule:
            bad(5.1, at, "rule has no `on` matcher")
        do = rule.get("do")
        if isinstance(do, str):
            if do not in DO_STRINGS:
                bad(5.1, at, f"do = {do!r} not in {sorted(DO_STRINGS)} and is not a redirect")
        elif isinstance(do, dict):
            if set(do) != {"redirect"}:
                bad(5.1, at, f"do table must have exactly the key `redirect`, got {sorted(do)}")
        else:
            bad(5.1, at, "rule has no `do` action")
    if v.get("operator") and "default" not in v:
        bad(5.2, f"{where}[{vid}]",
            "no `default`: an unmatched gate would block on stdin until the timeout burns")


def check_task(tdir, suite, suite_variants, capabilities):
    tt = tdir / "task.toml"
    if not tt.exists():
        return bad(0, tdir.as_posix(), "no task.toml")
    t = load(tt)
    if t is None:
        return

    where = f"{tdir.parent.parent.name}/{tdir.name}"

    if t.get("schema") != SCHEMA:                                            # rule 1
        bad(1, where, f"schema = {t.get('schema')!r}, expected {SCHEMA}")
    if t.get("id") != tdir.name:                                             # rule 2
        bad(2, where, f"id = {t.get('id')!r} but the directory is {tdir.name!r}")

    turns = t.get("turn") or []                                              # rule 4
    if not turns:
        bad(4, where, "no [[turn]]; the unit of measurement is a session with at least one")
    for i, turn in enumerate(turns):
        has = {k for k in ("send_file", "send_text") if k in turn}
        if len(has) != 1:
            bad(4, where, f"turn[{i}] has {sorted(has) or 'neither'} of send_file/send_text")
        elif "send_file" in turn and not (tdir / turn["send_file"]).exists():
            bad(4, where, f"turn[{i}].send_file {turn['send_file']!r} does not resolve")

    verify = t.get("verify") or {}                                           # rule 5
    disp = t.get("disposition") or {}
    if verify.get("kind") == "script":
        if not (tdir / verify.get("script", "")).exists():
            bad(5, where, f"verify.script {verify.get('script')!r} does not resolve")
    elif verify.get("kind") == "none":
        if disp.get("verifiable") != "none":
            bad(5, where, 'verify.kind = "none" but verifiable != "none"')
    else:
        bad(5, where, f"verify.kind = {verify.get('kind')!r}, expected script|none")

    if not disp:                                                             # rule 6
        bad(6, where, "no [disposition]")
    else:
        if disp.get("verifiable") not in VERIFIABLE:
            bad(6, where, f"verifiable = {disp.get('verifiable')!r} not in {sorted(VERIFIABLE)}")
        if disp.get("quarantine") not in QUARANTINE:
            bad(6, where, f"quarantine = {disp.get('quarantine')!r} not in {sorted(QUARANTINE)}")

    gate = t.get("gate") or {}                                               # rule 7
    for pt in ("point1", "point2", "point3"):
        if pt not in gate:
            bad(7, where, f"[gate].{pt} missing; `not_run` is how you say 'not yet'")
        elif gate[pt] not in GATE_VERDICTS:
            bad(7, where, f"[gate].{pt} = {gate[pt]!r} not in {sorted(GATE_VERDICTS)}")
    # A broken gate point and a clean disposition cannot both be true.
    if "broken" in [gate.get(p) for p in ("point1", "point2", "point3")]:
        if disp.get("quarantine") != "with_baseline":
            bad(7, where, "a gate point is `broken` but the task is not quarantined")

    tv = tdir / "variants.toml"                                              # rules 9 and 5
    merged = {v["id"]: ("suite", v) for v in suite_variants}
    if tv.exists():
        tvd = load(tv) or {}
        seen = set()
        for v in tvd.get("variant", []):
            if v.get("id") in seen:
                bad(9, where, f"duplicate variant id {v.get('id')!r} within variants.toml")
            seen.add(v.get("id"))
            merged[v["id"]] = ("task-override" if v["id"] in merged else "task-new", v)
    for vid, (origin, v) in merged.items():
        check_variant(v, where, capabilities)
        notes.append(f"  var  {where}: {vid:<20} {origin}")
        facts.append(
            f"variant {where} {vid} origin={origin} "
            f"mode={(v.get('permissions') or {}).get('mode')} "
            f"requires={'|'.join(v.get('requires', []))} "
            f"operator={len(v.get('operator', []))} "
            f"default={do_label(v['default']) if 'default' in v else 'none'}"
        )

    agg = suite.get("aggregate") or {}
    counted = (disp.get("verifiable") in agg.get("include_verifiable", [])
               and not (agg.get("exclude_quarantined") and disp.get("quarantine") != "none"))
    facts.append(
        f"task {where} verifiable={disp.get('verifiable')} quarantine={disp.get('quarantine')} "
        f"gate={gate.get('point1')}|{gate.get('point2')}|{gate.get('point3')} "
        f"counted={'yes' if counted else 'no'}"
    )

    prov = t.get("provenance") or {}                                         # rule 10
    lists = {k: prov.get(k, []) for k in ("verbatim", "rewritten", "synthesized")}
    flat = [f for l in lists.values() for f in l]
    dupes = {f for f in flat if flat.count(f) > 1}
    missing = PARTITION - set(flat)
    extra = set(flat) - PARTITION
    if dupes:
        bad(10, where, f"field(s) in more than one provenance list: {sorted(dupes)}")
    if missing:
        bad(10, where, f"field(s) in no provenance list: {sorted(missing)}")
    if extra:
        bad(10, where, f"provenance names field(s) outside the closed vocabulary: {sorted(extra)}")

    return t


def main():
    argv = [a for a in sys.argv[1:] if a != "--facts"]
    want_facts = "--facts" in sys.argv[1:]
    root = Path(argv[0] if argv else "corpus")
    if not root.is_dir():
        print(f"no corpus at {root}")
        return 1

    caps = set()
    for sp in sorted((root / "subjects").glob("*.toml")):
        s = load(sp) or {}
        caps |= set(s.get("capabilities", []))
        notes.append(f"  subj {sp.stem}: drive={s.get('drive')!r} caps={s.get('capabilities')}")
        facts.append(f"subject {s.get('id')} drive={s.get('drive')} "
                     f"caps={'|'.join(s.get('capabilities', []))}")

    tasks = []
    for suite_toml in sorted(root.glob("suites/*/suite.toml")):
        s = load(suite_toml) or {}
        sv = s.get("variant", [])
        ids = [v.get("id") for v in sv]
        if len(ids) != len(set(ids)):
            bad(9, suite_toml.as_posix(), f"duplicate variant id among suite defaults: {ids}")
        for v in sv:
            check_variant(v, suite_toml.parent.name + "/<suite>", caps)

        agg = s.get("aggregate") or {}
        for val in agg.get("include_verifiable", []):
            if val not in VERIFIABLE:
                bad(10, suite_toml.as_posix(), f"aggregate includes unknown {val!r}")

        # `expected_tasks` sits under [provenance] in suites/u100/suite.toml, because SPEC §4's
        # example places the key after the [provenance] header and TOML scoping does the rest.
        # Read both, exactly as the Rust loader does, or the two disagree over a parsing detail
        # rather than over the corpus.
        expected = (s.get("provenance") or {}).get("expected_tasks", s.get("expected_tasks"))
        facts.append(
            f"suite {s.get('id')} include={'|'.join(agg.get('include_verifiable', []))} "
            f"exclude_quarantined={str(agg.get('exclude_quarantined', True)).lower()} "
            f"expected={expected if expected is not None else '-'}"
        )

        for tdir in sorted((suite_toml.parent / "tasks").iterdir()):
            if tdir.is_dir():
                t = check_task(tdir, s, sv, caps)
                if t:
                    tasks.append((s, t))

    if want_facts:
        for f in sorted(facts):
            print(f)
        print(f"verdict {'ACCEPTED' if not errors else 'REJECTED'} "
              f"rejections={len(errors)} tasks={len(tasks)}")
        return 0 if not errors else 1

    print("corpus/SPEC.md v1 — loader check\n")
    for n in notes:
        print(n)

    print(f"\n  {len(tasks)} task(s) loaded")
    for s, t in tasks:
        d = t["disposition"]
        agg = s.get("aggregate", {})
        counted = (d["verifiable"] in agg.get("include_verifiable", [])
                   and not (agg.get("exclude_quarantined") and d["quarantine"] != "none"))
        print(f"    {t['id']:<20} verifiable={d['verifiable']:<14} "
              f"quarantine={d['quarantine']:<14} in aggregate: {'yes' if counted else 'NO'}")

    if errors:
        print(f"\n  REJECTED — {len(errors)} violation(s):")
        for e in errors:
            print(f"    {e}")
        return 1
    print("\n  ACCEPTED — every §13 rule holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
