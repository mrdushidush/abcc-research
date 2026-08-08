//! Negative controls for every SPEC §13 rule, plus the §5 merge and the §10 arithmetic.
//!
//! A validator is one-sided in the same way the import gate is: a loader that accepted nothing
//! would pass "the corpus is rejected" for every rule and look rigorous. So every rule here is
//! tested twice — the valid corpus below must load, and the one mutation must reject *with that
//! rule's number*. Asserting only "some rejection happened" would let a rule fire for the wrong
//! reason and still read green.

use std::fs;
use std::path::{Path, PathBuf};

use w8_corpus::{Corpus, Lang, Quarantine, RuleId, Support, Verifiable, VariantOrigin};

// ---------------------------------------------------------------------------
// A minimal valid corpus, built from scratch rather than copied out of corpus/.
// Two reasons: the tests do not move when the U100 import changes, and a corpus
// that is not U100 proves the loader reads the *format* and not one donor.
// ---------------------------------------------------------------------------

const SUBJECT: &str = r#"
schema = 1
id = "subj"
version = "0.1.0"
bin = "sub"
drive = "repl-pipe"
capabilities = ["tool_gate"]
[markers]
gate = "Allow? [y/N"
turn_end = "^turn iter="
"#;

const SUITE: &str = r#"
schema = 1
id = "s1"
title = "a suite"
[aggregate]
include_verifiable = ["full", "presence_only"]
exclude_quarantined = true
[[variant]]
id = "control"
permissions = { mode = "allow" }
operator = []
"#;

const TASK: &str = r#"
schema = 1
id = "t1"
title = "a task"
lang = "python"
kind = "bugfix"
timeout_s = 300
[[turn]]
send_file = "prompt.txt"
[verify]
kind = "script"
script = "verify.sh"
[disposition]
verifiable = "full"
quarantine = "none"
[gate]
point1 = "sound"
point2 = "not_run"
point3 = "not_run"
[provenance]
donor = "k-series"
verbatim = []
rewritten = []
synthesized = ["id", "title", "lang", "kind", "timeout_s", "turn", "prompt", "fixture",
               "verify", "refsol", "sham", "variants", "disposition", "selection", "gate",
               "donor_tags"]
"#;

/// Anchored on the whole `[verify]` block: a mutation that silently fails to apply would leave
/// the task valid and the negative control would pass for the wrong reason.
const VERIFY_SCRIPT: &str = "[verify]\nkind = \"script\"\nscript = \"verify.sh\"";
const VERIFY_NONE: &str = "[verify]\nkind = \"none\"";

struct Tmp {
    root: PathBuf,
}

impl Tmp {
    /// A corpus with one subject, one suite and one task, all valid.
    fn new(name: &str) -> Tmp {
        let root = std::env::temp_dir().join(format!("w8-corpus-test-{name}"));
        let _ = fs::remove_dir_all(&root);
        fs::create_dir_all(root.join("subjects")).unwrap();
        fs::create_dir_all(root.join("suites/s1/tasks")).unwrap();
        let t = Tmp { root };
        t.write("subjects/subj.toml", SUBJECT);
        t.write("suites/s1/suite.toml", SUITE);
        t.task("t1", TASK);
        t
    }

    fn write(&self, rel: &str, body: &str) {
        let p = self.root.join(rel);
        fs::create_dir_all(p.parent().unwrap()).unwrap();
        fs::write(p, body).unwrap();
    }

    /// A task directory with everything SPEC §2 requires alongside its `task.toml`.
    fn task(&self, id: &str, toml: &str) {
        let d = self.root.join("suites/s1/tasks").join(id);
        fs::create_dir_all(d.join("fixture")).unwrap();
        fs::write(d.join("fixture/.gitkeep"), "").unwrap();
        fs::write(d.join("prompt.txt"), "do the thing").unwrap();
        fs::write(d.join("verify.sh"), "echo 'RESULT: FAIL nothing'\n").unwrap();
        fs::write(d.join("task.toml"), toml).unwrap();
    }

    fn task_dir(&self, id: &str) -> PathBuf {
        self.root.join("suites/s1/tasks").join(id)
    }

    fn load(&self) -> Result<Corpus, Vec<w8_corpus::Rejection>> {
        Corpus::load(&self.root)
    }

    /// The rejection list, asserting that at least one was produced.
    fn rejections(&self) -> Vec<w8_corpus::Rejection> {
        match self.load() {
            Ok(_) => panic!("expected the corpus to be rejected, but it loaded"),
            Err(r) => r,
        }
    }
}

/// `str::replace` that will not silently do nothing.
///
/// This is not belt-and-braces: two of the negative controls below were written against a
/// mis-transcribed anchor, the mutation quietly applied to nothing, and both tests exercised an
/// unmodified valid corpus. The rejection cases failed loudly; the *acceptance* case passed for
/// entirely the wrong reason. A test whose setup can no-op is a test that reports on nothing.
trait Mutate {
    fn mutate(&self, from: &str, to: &str) -> String;
}

impl Mutate for str {
    #[track_caller]
    fn mutate(&self, from: &str, to: &str) -> String {
        assert!(self.contains(from), "mutation anchor not present, so this test would be vacuous: {from:?}");
        self.replace(from, to)
    }
}

#[track_caller]
fn assert_rejected_by(rejections: &[w8_corpus::Rejection], rule: RuleId) {
    assert!(
        rejections.iter().any(|r| r.rule == rule),
        "expected a [rule {}] rejection, got: {}",
        rule.code(),
        rejections.iter().map(|r| r.to_string()).collect::<Vec<_>>().join(" | ")
    );
}

// ---------------------------------------------------------------------------
// The positive control
// ---------------------------------------------------------------------------

#[test]
fn a_minimal_valid_corpus_loads() {
    let t = Tmp::new("valid");
    let c = t.load().expect("the baseline corpus must load, or every negative control below is vacuous");
    assert_eq!(c.suites.len(), 1);
    assert_eq!(c.suites[0].tasks.len(), 1);
    assert_eq!(c.subjects.len(), 1);
}

// ---------------------------------------------------------------------------
// Rules 1–10
// ---------------------------------------------------------------------------

#[test]
fn rule1_unknown_schema_is_rejected() {
    let t = Tmp::new("rule1");
    t.task("t1", &TASK.mutate("schema = 1", "schema = 2"));
    assert_rejected_by(&t.rejections(), RuleId::R1Schema);
}

#[test]
fn rule2_id_must_equal_the_directory_name() {
    let t = Tmp::new("rule2");
    t.task("t1", &TASK.mutate(r#"id = "t1""#, r#"id = "somethingelse""#));
    assert_rejected_by(&t.rejections(), RuleId::R2IdMismatch);
}

#[test]
fn rule3_permission_mode_prompt_is_rejected_with_the_reason_attached() {
    let t = Tmp::new("rule3");
    t.write("suites/s1/suite.toml", &SUITE.mutate(r#"mode = "allow""#, r#"mode = "prompt""#));
    let r = t.rejections();
    assert_rejected_by(&r, RuleId::R3PermissionMode);
    // The reason has to travel with the rejection. Anyone who reads the enum and reasons
    // correctly from the name `Prompt` arrives at the wrong answer, so "invalid mode" would
    // send them straight back to re-deriving it.
    let msg = r.iter().find(|x| x.rule == RuleId::R3PermissionMode).unwrap().message.clone();
    assert!(msg.contains("Ord"), "message must say why: {msg}");
    assert!(msg.contains("DangerFullAccess"), "message must say why: {msg}");
}

#[test]
fn rule3_an_unknown_permission_mode_is_rejected() {
    let t = Tmp::new("rule3b");
    t.write("suites/s1/suite.toml", &SUITE.mutate(r#"mode = "allow""#, r#"mode = "yolo""#));
    assert_rejected_by(&t.rejections(), RuleId::R3PermissionMode);
}

#[test]
fn rule4_a_turn_with_both_send_keys_is_rejected() {
    let t = Tmp::new("rule4a");
    t.task("t1", &TASK.mutate(r#"send_file = "prompt.txt""#, "send_file = \"prompt.txt\"\nsend_text = \"hi\""));
    assert_rejected_by(&t.rejections(), RuleId::R4Turn);
}

#[test]
fn rule4_a_turn_with_neither_send_key_is_rejected() {
    let t = Tmp::new("rule4b");
    t.task("t1", &TASK.mutate(r#"send_file = "prompt.txt""#, "note = \"nothing to send\""));
    assert_rejected_by(&t.rejections(), RuleId::R4Turn);
}

#[test]
fn rule4_an_unresolvable_send_file_is_rejected() {
    let t = Tmp::new("rule4c");
    t.task("t1", &TASK.mutate(r#"send_file = "prompt.txt""#, r#"send_file = "missing.txt""#));
    assert_rejected_by(&t.rejections(), RuleId::R4Turn);
}

#[test]
fn rule4_no_turns_at_all_is_rejected() {
    let t = Tmp::new("rule4d");
    let stripped = TASK.mutate("[[turn]]\nsend_file = \"prompt.txt\"\n", "");
    t.task("t1", &stripped);
    assert_rejected_by(&t.rejections(), RuleId::R4Turn);
}

#[test]
fn rule5_a_missing_verifier_script_is_rejected() {
    let t = Tmp::new("rule5a");
    t.task("t1", &TASK.mutate(r#"script = "verify.sh""#, r#"script = "nope.sh""#));
    assert_rejected_by(&t.rejections(), RuleId::R5Verify);
}

#[test]
fn rule5_verify_none_demands_verifiable_none() {
    // The pairing matters: `kind = "none"` means the donor supplied no verifier (F13), and a
    // task claiming to be `full` while carrying nothing to verify with would enter the
    // aggregate on a promise it cannot keep.
    let t = Tmp::new("rule5b");
    t.task("t1", &TASK.mutate(VERIFY_SCRIPT, VERIFY_NONE));
    assert_rejected_by(&t.rejections(), RuleId::R5Verify);
}

#[test]
fn verify_none_with_verifiable_none_is_accepted() {
    let t = Tmp::new("rule5c");
    let toml = TASK
        .mutate(VERIFY_SCRIPT, VERIFY_NONE)
        .mutate(r#"verifiable = "full""#, r#"verifiable = "none""#);
    t.task("t1", &toml);
    let c = t.load().expect("a task with no verifier is legal when it says so");
    assert!(c.suites[0].tasks[0].verify_script().is_none());
}

#[test]
fn rule6_a_disposition_outside_the_enum_is_rejected() {
    let t = Tmp::new("rule6a");
    t.task("t1", &TASK.mutate(r#"verifiable = "full""#, r#"verifiable = "sort_of""#));
    assert_rejected_by(&t.rejections(), RuleId::R6Disposition);
}

#[test]
fn rule6_a_missing_disposition_is_rejected() {
    let t = Tmp::new("rule6b");
    let stripped = TASK.mutate("[disposition]\nverifiable = \"full\"\nquarantine = \"none\"\n", "");
    t.task("t1", &stripped);
    assert_rejected_by(&t.rejections(), RuleId::R6Disposition);
}

#[test]
fn rule7_a_missing_gate_point_is_rejected() {
    // `not_run` is how you say "not yet"; silence is not.
    let t = Tmp::new("rule7a");
    t.task("t1", &TASK.mutate("point3 = \"not_run\"\n", ""));
    assert_rejected_by(&t.rejections(), RuleId::R7Gate);
}

#[test]
fn rule7_a_broken_gate_point_demands_quarantine() {
    let t = Tmp::new("rule7b");
    t.task("t1", &TASK.mutate(r#"point1 = "sound""#, r#"point1 = "broken""#));
    assert_rejected_by(&t.rejections(), RuleId::R7Gate);
}

#[test]
fn a_broken_gate_point_with_quarantine_is_accepted() {
    // fix_sql_inject's shape: the task stays on disk, carries its donor baseline, and is out of
    // every aggregate. Failing the gate changes the disposition, never whether the task exists.
    let t = Tmp::new("rule7c");
    let toml = TASK
        .mutate(r#"point3 = "not_run""#, r#"point3 = "broken""#)
        .mutate(r#"quarantine = "none""#, r#"quarantine = "with_baseline""#);
    t.task("t1", &toml);
    let c = t.load().expect("quarantine-with-baseline is the disposition for a failed gate");
    let suite = &c.suites[0];
    assert_eq!(suite.tasks[0].disposition.quarantine, Quarantine::WithBaseline);
    assert_eq!(suite.aggregate().denominator, 0, "a quarantined task is in no aggregate");
}

#[test]
fn rule7_an_evidence_tier_outside_the_vocabulary_is_rejected() {
    let t = Tmp::new("rule7d");
    let toml = format!(
        "{TASK}\n[[gate.evidence]]\npoint = 1\ntier = \"vibes\"\nverdict = \"FAIL\"\nverifier = \"rewritten\"\nrun = \"x\"\n"
    );
    t.task("t1", &toml);
    assert_rejected_by(&t.rejections(), RuleId::R7Gate);
}

#[test]
fn rule9_a_duplicate_variant_id_within_one_file_is_rejected() {
    let t = Tmp::new("rule9");
    let dup = format!("{SUITE}\n[[variant]]\nid = \"control\"\npermissions = {{ mode = \"read_only\" }}\n");
    t.write("suites/s1/suite.toml", &dup);
    assert_rejected_by(&t.rejections(), RuleId::R9DuplicateVariant);
}

#[test]
fn rule10_a_field_in_two_provenance_lists_is_rejected() {
    let t = Tmp::new("rule10a");
    t.task("t1", &TASK.mutate(r#"verbatim = []"#, r#"verbatim = ["id"]"#));
    assert_rejected_by(&t.rejections(), RuleId::R10Partition);
}

#[test]
fn rule10_a_field_in_no_provenance_list_is_rejected() {
    let t = Tmp::new("rule10b");
    t.task("t1", &TASK.mutate(r#""donor_tags"]"#, "]"));
    assert_rejected_by(&t.rejections(), RuleId::R10Partition);
}

#[test]
fn rule10_a_field_outside_the_closed_vocabulary_is_rejected() {
    let t = Tmp::new("rule10c");
    t.task("t1", &TASK.mutate(r#"rewritten = []"#, r#"rewritten = ["vibes"]"#));
    assert_rejected_by(&t.rejections(), RuleId::R10Partition);
}

/// SPEC amendment 8, David's word on 2026-08-08. Without it, 8 of Q56's 56 tasks are a load
/// rejection — and a rejected task rejects the whole corpus, so those eight would have taken u100
/// down with them (F47, F48).
#[test]
fn a_shell_task_loads_since_amendment_8() {
    let t = Tmp::new("lang-shell");
    t.task("t1", &TASK.mutate(r#"lang = "python""#, r#"lang = "shell""#));
    let c = t.load().expect("`shell` is in the lang vocabulary as of SPEC amendment 8");
    assert_eq!(c.suites[0].tasks[0].lang, Lang::Shell);
}

/// The vocabulary is still closed, and it is only closed vocabularies that make `lang` a checkable
/// field at all. `bash` is the plausible near-miss: it is what someone would type for a shell task.
#[test]
fn the_lang_vocabulary_is_still_closed_after_amendment_8() {
    let t = Tmp::new("lang-bash");
    t.task("t1", &TASK.mutate(r#"lang = "python""#, r#"lang = "bash""#));
    assert_rejected_by(&t.rejections(), RuleId::Field);
}

// ---------------------------------------------------------------------------
// Rule 8 is NOT a load rejection — SPEC §13 says it is a property of the
// (variant, subject) pair, so it can only be answered at run planning.
// ---------------------------------------------------------------------------

#[test]
fn rule8_an_undeclared_capability_is_not_supported_rather_than_rejected() {
    let t = Tmp::new("rule8");
    let suite = format!(
        "{SUITE}\n[[variant]]\nid = \"redirecting\"\npermissions = {{ mode = \"workspace_write\" }}\n\
         requires = [\"redirect\"]\ndefault = \"deny\"\noperator = [ {{ on = {{ gate = {{}} }}, do = \"approve\" }} ]\n"
    );
    t.write("suites/s1/suite.toml", &suite);

    let c = t.load().expect("an unsatisfiable `requires` is not a malformed corpus");
    let subject = c.subject("subj").unwrap();
    let cells = c.suites[0].plan(subject);
    assert_eq!(cells.len(), 2);

    let na: Vec<&w8_corpus::Cell<'_>> = cells.iter().filter(|x| x.support != Support::Runnable).collect();
    assert_eq!(na.len(), 1, "the subject declares tool_gate but not redirect");
    assert_eq!(na[0].variant.id, "redirecting");
    assert_eq!(na[0].support, Support::NotSupported { capability: "redirect".into() });
}

// ---------------------------------------------------------------------------
// SPEC §5 — operator-rule grammar
// ---------------------------------------------------------------------------

#[test]
fn an_operator_rule_with_no_default_is_rejected() {
    // Without a `default`, an unmatched gate blocks on stdin until the timeout burns: a whole
    // cell lost to a question nobody was listening for.
    let t = Tmp::new("nodefault");
    let suite = format!(
        "{SUITE}\n[[variant]]\nid = \"gated\"\npermissions = {{ mode = \"workspace_write\" }}\n\
         operator = [ {{ on = {{ gate = {{}} }}, do = \"approve\" }} ]\n"
    );
    t.write("suites/s1/suite.toml", &suite);
    assert_rejected_by(&t.rejections(), RuleId::NoDefault);
}

#[test]
fn an_operator_rule_with_no_action_is_rejected() {
    let t = Tmp::new("noaction");
    let suite = format!(
        "{SUITE}\n[[variant]]\nid = \"gated\"\npermissions = {{ mode = \"workspace_write\" }}\n\
         default = \"deny\"\noperator = [ {{ on = {{ gate = {{}} }} }} ]\n"
    );
    t.write("suites/s1/suite.toml", &suite);
    assert_rejected_by(&t.rejections(), RuleId::OperatorGrammar);
}

#[test]
fn a_do_table_with_a_key_other_than_redirect_is_rejected() {
    let t = Tmp::new("baddo");
    let suite = format!(
        "{SUITE}\n[[variant]]\nid = \"gated\"\npermissions = {{ mode = \"workspace_write\" }}\n\
         default = \"deny\"\noperator = [ {{ on = {{ gate = {{}} }}, do = {{ shout = \"hi\" }} }} ]\n"
    );
    t.write("suites/s1/suite.toml", &suite);
    assert_rejected_by(&t.rejections(), RuleId::OperatorGrammar);
}

#[test]
fn the_inline_and_block_operator_forms_parse_identically() {
    // A TOML inline table cannot span lines, so a long redirect *must* use the block form. If
    // the two syntaxes parsed differently, the choice forced by line length would silently
    // change the experiment.
    let inline = format!(
        "{SUITE}\n[[variant]]\nid = \"r\"\npermissions = {{ mode = \"workspace_write\" }}\ndefault = \"deny\"\n\
         operator = [ {{ on = {{ gate = {{ tool = \"apply_diff\" }} }}, do = {{ redirect = \"stop\" }}, times = 1 }},\n\
                      {{ on = {{ gate = {{}} }}, do = \"approve\" }} ]\n"
    );
    let block = format!(
        "{SUITE}\n[[variant]]\nid = \"r\"\npermissions = {{ mode = \"workspace_write\" }}\ndefault = \"deny\"\n\
         [[variant.operator]]\non = {{ gate = {{ tool = \"apply_diff\" }} }}\ndo = {{ redirect = \"stop\" }}\ntimes = 1\n\
         [[variant.operator]]\non = {{ gate = {{}} }}\ndo = \"approve\"\n"
    );

    let mut seen = Vec::new();
    for (name, body) in [("inline", inline), ("block", block)] {
        let t = Tmp::new(&format!("form-{name}"));
        t.write("suites/s1/suite.toml", &body);
        let c = t.load().unwrap();
        let v = c.suites[0].tasks[0].variant("r").unwrap().clone();
        seen.push(format!("{:?}", (v.mode, v.operator.len(), v.operator[0].times, v.operator[0].action.clone(), v.default.clone())));
    }
    assert_eq!(seen[0], seen[1], "the two syntaxes must produce the same rule list");
}

#[test]
fn a_gate_matcher_narrows_by_tool_and_input() {
    let t = Tmp::new("matcher");
    let suite = format!(
        "{SUITE}\n[[variant]]\nid = \"r\"\npermissions = {{ mode = \"workspace_write\" }}\ndefault = \"deny\"\n\
         operator = [ {{ on = {{ gate = {{ tool = \"bash\", input_contains = \"cargo test\" }} }}, do = \"deny\" }} ]\n"
    );
    t.write("suites/s1/suite.toml", &suite);
    let c = t.load().unwrap();
    let m = &c.suites[0].tasks[0].variant("r").unwrap().operator[0].on.gate;
    assert!(m.matches("bash", "cargo test --offline"));
    assert!(!m.matches("bash", "cargo build"), "input_contains must narrow");
    assert!(!m.matches("apply_diff", "cargo test"), "tool must narrow");
}

// ---------------------------------------------------------------------------
// SPEC §5 — the merge
// ---------------------------------------------------------------------------

#[test]
fn a_task_variant_replaces_the_suite_one_by_id_and_a_new_one_is_appended() {
    let t = Tmp::new("merge");
    fs::write(
        t.task_dir("t1").join("variants.toml"),
        "[[variant]]\nid = \"control\"\npermissions = { mode = \"read_only\" }\n\n\
         [[variant]]\nid = \"extra\"\npermissions = { mode = \"workspace_write\" }\n",
    )
    .unwrap();

    let c = t.load().unwrap();
    let vs = &c.suites[0].tasks[0].variants;
    assert_eq!(vs.len(), 2);
    assert_eq!(vs[0].id, "control", "the overridden variant keeps its position");
    assert_eq!(vs[0].origin, VariantOrigin::TaskOverride);
    assert_eq!(vs[0].mode, w8_corpus::PermissionMode::ReadOnly, "override replaces entirely");
    assert_eq!(vs[1].id, "extra");
    assert_eq!(vs[1].origin, VariantOrigin::TaskNew);
}

#[test]
fn a_task_that_declares_no_variants_inherits_the_suite_defaults() {
    let c = Tmp::new("inherit").load().unwrap();
    let vs = &c.suites[0].tasks[0].variants;
    assert_eq!(vs.len(), 1);
    assert_eq!(vs[0].origin, VariantOrigin::Suite);
}

// ---------------------------------------------------------------------------
// SPEC §2 — the isolation guarantee
// ---------------------------------------------------------------------------

#[test]
fn a_missing_fixture_directory_is_rejected() {
    let t = Tmp::new("nofixture");
    fs::remove_dir_all(t.task_dir("t1").join("fixture")).unwrap();
    assert_rejected_by(&t.rejections(), RuleId::Isolation);
}

#[test]
fn a_gate_only_directory_nested_in_the_fixture_is_rejected() {
    let t = Tmp::new("leak");
    let d = t.task_dir("t1").join("fixture/refsol");
    fs::create_dir_all(&d).unwrap();
    fs::write(d.join("answer.py"), "the answer").unwrap();
    let r = t.rejections();
    assert_rejected_by(&r, RuleId::Isolation);
}

#[test]
fn the_workdir_plan_never_names_a_gate_only_directory() {
    // The structural half of the guarantee: `refsol/` exists on disk, is reported present, and
    // still cannot appear in the only list the runner is given.
    let t = Tmp::new("gateonly");
    let d = t.task_dir("t1");
    fs::create_dir_all(d.join("refsol")).unwrap();
    fs::write(d.join("refsol/answer.py"), "the answer").unwrap();
    fs::write(d.join("fixture/broken.py"), "bug").unwrap();

    let c = t.load().unwrap();
    let task = &c.suites[0].tasks[0];
    assert!(task.has_refsol());
    let dests: Vec<&str> = task.workdir.files().iter().map(|f| f.dest.as_str()).collect();
    assert_eq!(dests, ["broken.py"]);
}

#[test]
fn materializing_a_fixture_copies_the_files_and_not_the_dotfiles() {
    let t = Tmp::new("materialise");
    fs::write(t.task_dir("t1").join("fixture/broken.py"), "bug").unwrap();
    let c = t.load().unwrap();

    let work = t.root.join("work");
    fs::create_dir_all(&work).unwrap();
    c.suites[0].tasks[0].workdir.materialize(&work).unwrap();

    assert_eq!(fs::read_to_string(work.join("broken.py")).unwrap(), "bug");
    assert!(!work.join(".gitkeep").exists(), "78 U100 fixtures hold only a .gitkeep; copying it changes the work dir");
}

// ---------------------------------------------------------------------------
// SPEC §10 — the aggregate, and the suite's self-declared size
// ---------------------------------------------------------------------------

#[test]
fn the_aggregate_rule_decides_membership_and_travels_with_the_number() {
    let t = Tmp::new("aggregate");
    t.task("t2", &TASK.mutate(r#"id = "t1""#, r#"id = "t2""#).mutate(r#"verifiable = "full""#, r#"verifiable = "presence_only""#));
    t.task(
        "t3",
        &TASK
            .mutate(r#"id = "t1""#, r#"id = "t3""#)
            .mutate(r#"quarantine = "none""#, r#"quarantine = "with_baseline""#),
    );

    let c = t.load().unwrap();
    let agg = c.suites[0].aggregate();
    assert_eq!(agg.denominator, 2, "full + presence_only, quarantined excluded");
    assert_eq!(agg.excluded_quarantined, 1);
    assert!(agg.rule.contains("presence_only"), "the rule must be quotable alongside the number: {}", agg.rule);
}

#[test]
fn flipping_the_aggregate_rule_rescores_without_touching_a_task() {
    let t = Tmp::new("reaggregate");
    t.task("t2", &TASK.mutate(r#"id = "t1""#, r#"id = "t2""#).mutate(r#"verifiable = "full""#, r#"verifiable = "presence_only""#));
    assert_eq!(t.load().unwrap().suites[0].aggregate().denominator, 2);

    // This is what carrying disposition as a field rather than a fork buys.
    t.write("suites/s1/suite.toml", &SUITE.mutate(r#"["full", "presence_only"]"#, r#"["full"]"#));
    let c = t.load().unwrap();
    assert_eq!(c.suites[0].aggregate().denominator, 1);
    assert_eq!(c.suites[0].tasks.len(), 2, "no task changed");
}

#[test]
fn a_suite_that_declares_its_size_is_checked_against_the_tree() {
    // A silently missing task directory is the failure that flatters a run: fewer tasks, same
    // pass rate. `expected_tasks` exists to make that loud.
    let t = Tmp::new("expected");
    t.write("suites/s1/suite.toml", &SUITE.mutate("title = \"a suite\"", "title = \"a suite\"\n[provenance]\ndonor = \"k\"\nexpected_tasks = 2"));
    let r = t.rejections();
    assert!(r.iter().any(|x| x.message.contains("expected_tasks")), "got: {r:?}");
}

#[test]
fn suite_caveats_are_read_whether_they_sit_under_provenance_or_at_the_top_level() {
    // SPEC §4's prose says "suite-level caveats" while its example places the key after
    // [provenance], which TOML scoping makes provenance.caveats — and suites/u100/suite.toml
    // does the same. A loader that read only one of the two would silently find none.
    for body in [
        SUITE.mutate("title = \"a suite\"", "title = \"a suite\"\ncaveats = [\"one\"]"),
        SUITE.mutate("title = \"a suite\"", "title = \"a suite\"\n[provenance]\ndonor = \"k\"\ncaveats = [\"one\"]"),
    ] {
        let t = Tmp::new("caveats");
        t.write("suites/s1/suite.toml", &body);
        assert_eq!(t.load().unwrap().suites[0].caveats.len(), 1, "in: {body}");
    }
}

// ---------------------------------------------------------------------------
// Accumulation
// ---------------------------------------------------------------------------

#[test]
fn every_rejection_comes_back_at_once() {
    // Fixing a 90-task corpus one rejection per run is a 90-round loop.
    let t = Tmp::new("accumulate");
    t.task(
        "t1",
        &TASK
            .mutate("schema = 1", "schema = 7")
            .mutate(r#"id = "t1""#, r#"id = "wrong""#)
            .mutate(r#"verifiable = "full""#, r#"verifiable = "maybe""#),
    );
    let r = t.rejections();
    assert_rejected_by(&r, RuleId::R1Schema);
    assert_rejected_by(&r, RuleId::R2IdMismatch);
    assert_rejected_by(&r, RuleId::R6Disposition);
}

// ---------------------------------------------------------------------------
// The real corpus
// ---------------------------------------------------------------------------

fn corpus_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../../../corpus")
}

#[test]
fn the_u100_corpus_loads_and_reproduces_the_imports_own_numbers() {
    let root = corpus_root();
    if !root.is_dir() {
        eprintln!("skipping: no corpus at {}", root.display());
        return;
    }
    let c = Corpus::load(&root).unwrap_or_else(|r| {
        panic!("corpus rejected:\n{}", r.iter().map(|x| format!("  {x}")).collect::<Vec<_>>().join("\n"))
    });

    let suite = c.suite("u100").expect("the u100 suite");
    assert_eq!(suite.tasks.len(), 90, "the pool is 90, not 100 — F11");

    // The import's headline, restated by an independent reader of the same tree.
    let counts = suite.disposition_counts();
    assert_eq!(counts.full, 54);
    assert_eq!(counts.presence_only, 24);
    assert_eq!(counts.quarantined, 12);
    assert_eq!(suite.aggregate().denominator, 78);

    assert_eq!(suite.tasks.iter().filter(|t| t.selection.gate3).count(), 30, "R10's approved set");
    assert_eq!(
        suite.tasks.iter().filter(|t| t.disposition.verifiable == Verifiable::None).count(),
        10,
        "the ten tasks the donor scored on its agent-execution success flag — F13"
    );

    // SPEC §2's guarantee, over the whole real corpus rather than a constructed case.
    for t in &suite.tasks {
        for f in t.workdir.files() {
            assert!(f.src.starts_with(t.dir.join("fixture")), "{}: {} escapes fixture/", t.id, f.src.display());
            assert!(!f.dest.starts_with('.'), "{}: {} is a dotfile", t.id, f.dest);
        }
    }
}

// ---------------------------------------------------------------------------
// SPEC §7 `[delivery]` and SPEC §5 `gate_fires_after_deny` — amendments 6 and 7
// ---------------------------------------------------------------------------

#[test]
fn a_subject_with_no_delivery_table_is_valid_and_declares_no_block() {
    // Additive amendment: every descriptor written before this existed must still load.
    let t = Tmp::new("delivery-absent");
    t.write("subjects/subj.toml", SUBJECT);
    t.write("suites/s1/suite.toml", SUITE);
    t.task("t1", TASK);
    let c = t.load().expect("[delivery] is optional");
    assert!(c.subject("subj").unwrap().delivery.is_none());
}

#[test]
fn a_declared_delivery_pair_round_trips() {
    let t = Tmp::new("delivery-ok");
    t.write(
        "subjects/subj.toml",
        &SUBJECT.mutate(
            "[markers]",
            "[delivery]\nopen = \"<<<OPEN\"\nclose = \"CLOSE>>>\"\n[markers]",
        ),
    );
    t.write("suites/s1/suite.toml", SUITE);
    t.task("t1", TASK);
    let c = t.load().expect("a complete pair is valid");
    let d = c.subject("subj").unwrap().delivery.clone().expect("the pair");
    assert_eq!((d.open.as_str(), d.close.as_str()), ("<<<OPEN", "CLOSE>>>"));
}

#[test]
fn a_half_declared_delivery_pair_is_rejected_rather_than_half_used() {
    // A block opened with a sentinel the subject never closes on fails as a TIMEOUT, which reads
    // as a slow subject rather than as a bad descriptor.
    let t = Tmp::new("delivery-half");
    t.write("subjects/subj.toml", &SUBJECT.mutate("[markers]", "[delivery]\nopen = \"<<<OPEN\"\n[markers]"));
    t.write("suites/s1/suite.toml", SUITE);
    t.task("t1", TASK);
    assert_rejected_by(&t.rejections(), RuleId::Field);
}

#[test]
fn a_delivery_pair_whose_sentinels_are_identical_is_rejected() {
    let t = Tmp::new("delivery-same");
    t.write(
        "subjects/subj.toml",
        &SUBJECT.mutate("[markers]", "[delivery]\nopen = \"SAME\"\nclose = \"SAME\"\n[markers]"),
    );
    t.write("suites/s1/suite.toml", SUITE);
    t.task("t1", TASK);
    assert_rejected_by(&t.rejections(), RuleId::Field);
}

#[test]
fn gate_fires_after_deny_parses_as_a_bound_and_checks_independently_of_gate_fires() {
    use w8_corpus::Observed;

    let t = Tmp::new("after-deny");
    t.write("subjects/subj.toml", SUBJECT);
    t.write(
        "suites/s1/suite.toml",
        &SUITE.mutate(
            "id = \"control\"",
            "id = \"control\"\nexpect = { gate_fires = { min = 2 }, gate_fires_after_deny = { min = 1 } }",
        ),
    );
    t.task("t1", TASK);
    let c = t.load().expect("the new expect key is valid");
    let v = &c.suite("s1").unwrap().tasks[0].variants[0];
    assert_eq!(v.expect.gate_fires_after_deny.unwrap().min, Some(1));

    // F36 exactly: five gates, four of them exploratory `bash` before the denial, and the denial
    // last. `gate_fires` is satisfied and the question is not.
    let f36 = Observed {
        gate_fires: 5,
        gate_fires_after_deny: 0,
        interventions_delivered: 0,
        unscripted_gates: 0,
    };
    let why = v.expect.violation(f36).expect("the run that looked fine must now be INVALID");
    assert!(why.contains("gate_fires_after_deny"), "{why}");
    assert!(why.contains("of 5 gates in total"), "the message shows why the old bound passed: {why}");

    // Denied, then asked again — the behaviour the variant was written to catch.
    assert_eq!(v.expect.violation(Observed { gate_fires_after_deny: 1, ..f36 }), None);
}

#[test]
fn a_misspelled_expect_key_is_rejected_rather_than_ignored() {
    // The strictening that comes with amendment 6. An `expect` that checks nothing always holds,
    // so `gate_fires_after_denial` would convert the variant's whole question into a silent pass —
    // and it would pass in the direction that flatters the subject.
    let t = Tmp::new("expect-typo");
    t.write("subjects/subj.toml", SUBJECT);
    t.write(
        "suites/s1/suite.toml",
        &SUITE.mutate(
            "id = \"control\"",
            "id = \"control\"\nexpect = { gate_fires_after_denial = { min = 1 } }",
        ),
    );
    t.task("t1", TASK);
    let r = t.rejections();
    assert_rejected_by(&r, RuleId::Field);
    assert!(
        r.iter().any(|x| x.message.contains("gate_fires_after_denial")),
        "the message must name the offending key: {r:?}"
    );
}

#[test]
fn the_u100_corpus_plans_cells_against_the_claudette_subject() {
    let root = corpus_root();
    if !root.is_dir() {
        return;
    }
    let c = Corpus::load(&root).unwrap();
    let subject = c.subject("claudette-fc1ea22").expect("the stand-in subject");
    assert_eq!(subject.drive, "repl-pipe", "one-shot has no prompter (run.rs:186) — F1");

    let cells = c.suite("u100").unwrap().plan(subject);
    // 89 tasks inherit the suite's three variants; fix_sql_inject overrides one and adds one.
    assert_eq!(cells.len(), 89 * 3 + 4);
    assert!(cells.iter().all(|x| x.support == Support::Runnable), "the subject declares every capability the suite requires");
}
