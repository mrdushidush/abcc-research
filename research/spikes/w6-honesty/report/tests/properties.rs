//! The four properties item 8 asks the type to hold, each written as the donor
//! defect it exists to make unrepresentable.

use honest_report::{Claim, Counts, Headline, Measurement, Outcome, Report, Why};

/// v1: a task with files written and no test command is `SUCCESS` at confidence
/// 1.0 (`output.py`, the `elif has_meaningful_output:` branch, whose `else` arm
/// is commented *"No tests ran or all tests passed = SUCCESS"*).
#[test]
fn a_report_with_nothing_measured_is_not_a_pass() {
    let r = Report::new();
    assert!(!r.headline().is_pass());
    assert_eq!(r.headline(), Headline::Unverified { missing: vec![] });
    assert_eq!(r.measured_fraction(), (0, 0));
}

/// Claudette: `CheckOutcome::Skipped` carries "the feature is off", "we are
/// offline" and "there is no checker for a `.md` file" in one variant, and the
/// call site folds it into `Passed` (F348). Here the three are three values and
/// none of them is a pass.
#[test]
fn the_reasons_for_not_measuring_are_distinguishable_and_none_is_green() {
    let reasons = [
        Why::NoCheckerForArtifact {
            artifact: "docs/status_lifecycle.md".into(),
        },
        Why::CheckerNotOnHost {
            binary: "npm".into(),
        },
        Why::SpawnFailed {
            binary: "python3".into(),
            os_error: "exit 9009 (Store alias)".into(),
        },
        Why::NothingToRun {
            detail: "no tests ran in 0.23s".into(),
        },
        Why::FailedBeforeRunning {
            detail: "1 error in 0.39s".into(),
        },
        Why::Timeout { after_ms: 600_000 },
        Why::BudgetExhausted { which: "rounds" },
        Why::Cancelled {
            by: "operator".into(),
        },
    ];

    let mut rendered: Vec<String> = reasons.iter().map(ToString::to_string).collect();
    rendered.sort();
    rendered.dedup();
    assert_eq!(rendered.len(), reasons.len(), "two reasons render the same");

    for why in reasons {
        let o = Outcome::Unmeasured {
            rung: "tests",
            why: why.clone(),
        };
        assert!(!o.is_green(), "{why} counted as green");
        assert!(!o.is_red(), "{why} counted as red");

        let mut r = Report::new();
        r.record(o);
        let h = r.headline();
        assert!(!h.is_pass(), "{why} produced {h}");
        // The console line names the rung and the reason, which is the whole
        // requirement item 5 handed this item.
        let line = h.to_string();
        assert!(line.contains("tests"), "{line}");
        assert!(line.contains(&why.to_string()), "{line}");
    }
}

/// v1: `parse_agent_output` returns `AgentOutput(**data)` straight from the JSON
/// the model emitted whenever it carries `files_created` — the model's own
/// `status` and `confidence` become the task record. Here a claim is a different
/// type, and no amount of it moves the headline.
#[test]
fn what_the_model_said_never_becomes_what_the_host_saw() {
    let mut r = Report::new();
    for text in [
        "Done — both existing tests pass.",
        "Test passes clean, no warnings.",
        "All 6 hidden slug tests passed.",
    ] {
        r.note(Claim {
            by: "coder".into(),
            text: text.into(),
        });
    }
    assert_eq!(r.claims().len(), 3);
    assert!(!r.headline().is_pass());
    assert_eq!(r.measured_fraction(), (0, 0));

    // The claims survive for the operator to read; they are simply not evidence.
    assert!(r.claims().iter().any(|c| c.text.contains("tests pass")));
}

/// W11 F296's anti-pattern: a loop that exhausts its budget returning `Ok(())`.
/// The type has no `Ok(())` to return — exhaustion is a reason a rung produced
/// no measurement, and it is neither pass nor fail.
#[test]
fn exhaustion_is_classified_and_is_neither_pass_nor_fail() {
    let mut r = Report::new();
    r.record(Outcome::Measured(Measurement {
        rung: "structural",
        exit: 0,
        counts: None,
        detail: "3 source files changed".into(),
    }));
    r.record(Outcome::Unmeasured {
        rung: "tests",
        why: Why::BudgetExhausted { which: "rounds" },
    });

    let h = r.headline();
    assert!(!h.is_pass(), "{h}");
    assert!(matches!(h, Headline::Unverified { .. }), "{h}");
    assert_eq!(r.measured_fraction(), (1, 2));
    assert!(h.to_string().contains("rounds budget exhausted"), "{h}");
}

/// The first red wins and it names its rung, so a type error that takes the
/// suite down with it is one failure and not six (item 5 §8).
#[test]
fn the_first_red_is_the_headline_and_it_names_itself() {
    let mut r = Report::new();
    r.record(Outcome::Measured(Measurement {
        rung: "typecheck",
        exit: 101,
        counts: None,
        detail: "error[E0308]: mismatched types".into(),
    }));
    r.record(Outcome::Measured(Measurement {
        rung: "tests",
        exit: 101,
        counts: Some(Counts {
            run: 6,
            passed: 0,
            failed: 6,
        }),
        detail: "error: could not compile".into(),
    }));
    let h = r.headline();
    assert!(matches!(&h, Headline::Red { rung, .. } if *rung == "typecheck"), "{h}");
}
