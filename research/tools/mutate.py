# -*- coding: utf-8 -*-
"""Apply one mutation, run the test that should catch it, put the file back.

Item 123 of verify-claims: `cargo test`'s own failure line is literally
`error: test failed`, so a harness that greps for `error:` calls every run a
build failure. Build failure is distinguished by `could not compile` / `error[E`
BEFORE the test binary runs, and by nothing else.
"""
import subprocess, sys, os
ABCC = r"D:\dev\abcc"

MUTATIONS = [
    ("the gate is asked only when the model answered",
     r"crates\abcc-drive\src\lib.rs",
     "(Some(closing), PhaseEnded::Answered { .. } | PhaseEnded::Unmeasured { .. }) => {",
     "(Some(closing), PhaseEnded::Answered { .. }) => {",
     "abcc-drive", "attempt", "an_ending_the_model_did_not_choose_is_measured_when_the_tree_changed"),

    ("a green ladder promotes an ending the model never chose",
     r"crates\abcc-drive\src\lib.rs",
     "        PhaseEnded::Unmeasured { why, .. } => {\n            let next = next_after(why, attempt);",
     "        PhaseEnded::Unmeasured { why, .. } => {\n"
     "            if matches!(gate.map(|g| &g.headline), Some(Headline::Green { .. })) {\n"
     "                return Ending {\n"
     "                    outcome: AttemptOutcome::Success,\n"
     "                    next: Some(NextAction::Stop),\n"
     "                    landing: Landing::Accomplished,\n"
     "                };\n"
     "            }\n"
     "            let next = next_after(why, attempt);",
     "abcc-drive", "attempt", "a_green_ladder_under_an_unchosen_ending_is_still_uncertain"),

    ("the Judge is widened with the gate",
     r"crates\abcc-drive\src\lib.rs",
     "            (Some(measured), Some(closing), PhaseEnded::Answered { .. }) => {",
     "            (Some(measured), Some(closing), _) => {",
     "abcc-drive", "attempt", "the_judge_is_not_asked_for_an_ending_the_model_did_not_choose"),

    ("the operator's stop is gated too",
     r"crates\abcc-drive\src\lib.rs",
     "            // An attempt the operator stopped is not ours to judge",
     "            (Some(closing), _) => Some(self.gate(attempt, &opened, closing)?),\n"
     "            // An attempt the operator stopped is not ours to judge",
     "abcc-drive", "attempt", "an_attempt_the_operator_halted_asks_no_rung"),

    ("the console asserts an absent artifact again",
     r"crates\abcc\src\run.rs",
     '"gate      not asked \u2014 the operator stopped this attempt"',
     '"gate      not asked \u2014 the attempt produced no artifact"',
     "abcc", None, "run::tests::an_unasked_gate_names_the_operator_and_never_asserts_an_absent_artifact"),
]

def run(pkg, test_target, name):
    cmd = ["cargo", "test", "-p", pkg]
    if test_target:
        cmd += ["--test", test_target]
    cmd += [name, "--", "--exact"]
    r = subprocess.run(cmd, cwd=ABCC, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    built = "could not compile" not in out and "error[E" not in out
    # 🚨 The trap this harness was rewritten for: `--exact` matches the
    # FULL path, so a bare name filters to zero tests, exits 0, and reads as a
    # surviving mutation. The only honest signal is that the named test RAN.
    ran = "running 1 test" in out
    return r.returncode, built, ran, out

survived = []
for label, rel, old, new, pkg, target, test in MUTATIONS:
    path = os.path.join(ABCC, rel)
    original = open(path, encoding="utf-8").read()
    assert old in original, "anchor missing for: %s" % label
    assert original.count(old) == 1, "anchor is not unique for: %s" % label
    open(path, "w", encoding="utf-8").write(original.replace(old, new, 1))
    try:
        code, built, ran, out = run(pkg, target, test)
    finally:
        open(path, "w", encoding="utf-8").write(original)
    if not built:
        verdict = "DID NOT COMPILE (still caught, but not by the test)"
    elif not ran:
        verdict = "*** THE TEST NEVER RAN — the harness is wrong, not the code ***"
        survived.append(label + " (unscored)")
    elif code != 0:
        verdict = "caught by %s" % test
    else:
        verdict = "*** SURVIVED ***"
        survived.append(label)
    print("%-52s %s" % (label, verdict))

print("\n%d of %d mutations caught; survivors: %s"
      % (len(MUTATIONS) - len(survived), len(MUTATIONS), survived or "none"))
