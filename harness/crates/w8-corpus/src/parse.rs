//! TOML → model, accumulating SPEC §13 rejections.
//!
//! Two deliberate properties:
//!
//! **It accumulates, it does not fail fast.** A corpus of 90 tasks fixed one rejection per run is
//! a 90-round loop. Every rule is evaluated for every task and the whole list comes back at once.
//!
//! **A task with any rejection does not enter the model.** SPEC §13 says the loader *rejects the
//! corpus*, so a half-valid task has no business reaching a runner. This is the one place the
//! Rust loader is stricter than `research/spikes/w8-corpus-v1/validate.py`, which reports rule
//! violations but still counts the task as loaded — noted because the two are cross-checked and a
//! silent difference between an implementation and its reference is the exact defect class this
//! project keeps finding.

use std::collections::BTreeMap;
use std::path::Path;

use toml::{Table, Value};

use crate::model::*;
use crate::{RuleId, Rejections, workdir};

pub(crate) const SCHEMA: i64 = 1;

// ---------------------------------------------------------------------------
// Field accessors. Each one records its own rejection rather than returning an
// error a caller has to remember to attribute to a rule.
// ---------------------------------------------------------------------------

fn req_str<'a>(t: &'a Table, key: &str, at: &str, rej: &mut Rejections) -> Option<&'a str> {
    match t.get(key) {
        Some(Value::String(s)) => Some(s),
        Some(v) => {
            rej.add(RuleId::Field, at, format!("`{key}` is {}, expected a string", type_of(v)));
            None
        }
        None => {
            rej.add(RuleId::Field, at, format!("`{key}` is missing"));
            None
        }
    }
}

fn req_int(t: &Table, key: &str, at: &str, rej: &mut Rejections) -> Option<i64> {
    match t.get(key) {
        Some(Value::Integer(i)) => Some(*i),
        Some(v) => {
            rej.add(RuleId::Field, at, format!("`{key}` is {}, expected an integer", type_of(v)));
            None
        }
        None => {
            rej.add(RuleId::Field, at, format!("`{key}` is missing"));
            None
        }
    }
}

fn opt_str<'a>(t: &'a Table, key: &str) -> Option<&'a str> {
    t.get(key).and_then(Value::as_str)
}

fn str_list(t: &Table, key: &str) -> Vec<String> {
    t.get(key)
        .and_then(Value::as_array)
        .map(|a| a.iter().filter_map(|v| v.as_str().map(str::to_owned)).collect())
        .unwrap_or_default()
}

fn table<'a>(t: &'a Table, key: &str) -> Option<&'a Table> {
    t.get(key).and_then(Value::as_table)
}

fn type_of(v: &Value) -> &'static str {
    match v {
        Value::String(_) => "a string",
        Value::Integer(_) => "an integer",
        Value::Float(_) => "a float",
        Value::Boolean(_) => "a boolean",
        Value::Datetime(_) => "a datetime",
        Value::Array(_) => "an array",
        Value::Table(_) => "a table",
    }
}

/// Read a value out of a closed vocabulary, or reject naming the whole vocabulary. The message
/// matters: "not in [full, none, presence_only]" tells an author what to write; "invalid value"
/// sends them back to the spec.
fn vocab_str<T>(
    t: &Table,
    key: &str,
    rule: RuleId,
    at: &str,
    rej: &mut Rejections,
    parse: fn(&str) -> Option<T>,
    allowed: &[&str],
) -> Option<T> {
    let raw = match t.get(key) {
        Some(Value::String(s)) => s,
        Some(v) => {
            rej.add(rule, at, format!("`{key}` is {}, expected a string", type_of(v)));
            return None;
        }
        None => {
            rej.add(rule, at, format!("`{key}` is missing; expected one of [{}]", allowed.join(", ")));
            return None;
        }
    };
    match parse(raw) {
        Some(v) => Some(v),
        None => {
            rej.add(rule, at, format!("`{key}` = {raw:?} is not one of [{}]", allowed.join(", ")));
            None
        }
    }
}

pub(crate) fn parse_toml(path: &Path, rej: &mut Rejections) -> Option<Table> {
    let text = match std::fs::read_to_string(path) {
        Ok(t) => t,
        Err(e) => {
            rej.add(RuleId::Parse, path.display().to_string(), format!("cannot read: {e}"));
            return None;
        }
    };
    match text.parse::<Table>() {
        Ok(t) => Some(t),
        Err(e) => {
            rej.add(RuleId::Parse, path.display().to_string(), format!("does not parse: {e}"));
            None
        }
    }
}

/// Rule 1. Applied to every file that carries a `schema`, because "the loader rejects `schema`
/// values it does not know rather than guessing" is a property of the format and not of one file.
fn check_schema(t: &Table, at: &str, rej: &mut Rejections) {
    match t.get("schema") {
        Some(Value::Integer(n)) if *n == SCHEMA => {}
        Some(v) => rej.add(RuleId::R1Schema, at, format!("schema is {}, expected the integer {SCHEMA}", type_of(v))),
        None => rej.add(RuleId::R1Schema, at, "no `schema` key".to_string()),
    }
}

// ---------------------------------------------------------------------------
// Variants — SPEC §5
// ---------------------------------------------------------------------------

fn parse_action(v: &Value, at: &str, rej: &mut Rejections) -> Option<Action> {
    match v {
        Value::String(s) => match s.as_str() {
            "approve" => Some(Action::Approve),
            "deny" => Some(Action::Deny),
            other => {
                rej.add(
                    RuleId::OperatorGrammar,
                    at,
                    format!("do = {other:?} is not \"approve\" or \"deny\", and is not a redirect table"),
                );
                None
            }
        },
        Value::Table(t) => {
            let keys: Vec<&str> = t.keys().map(String::as_str).collect();
            if keys != ["redirect"] {
                rej.add(
                    RuleId::OperatorGrammar,
                    at,
                    format!("do table must have exactly the key `redirect`, got [{}]", keys.join(", ")),
                );
                return None;
            }
            match t.get("redirect").and_then(Value::as_str) {
                Some(s) => Some(Action::Redirect(s.to_owned())),
                None => {
                    rej.add(RuleId::OperatorGrammar, at, "do.redirect is not a string".to_string());
                    None
                }
            }
        }
        other => {
            rej.add(RuleId::OperatorGrammar, at, format!("do is {}, expected a string or a table", type_of(other)));
            None
        }
    }
}

fn parse_bound(v: &Value) -> Bound {
    let t = match v.as_table() {
        Some(t) => t,
        None => return Bound::default(),
    };
    Bound {
        min: t.get("min").and_then(Value::as_integer).map(|n| n as u32),
        max: t.get("max").and_then(Value::as_integer).map(|n| n as u32),
    }
}

/// SPEC §5's `expect` keys, and **nothing else**.
///
/// A misspelled key is refused rather than ignored. An `expect` that never checks anything always
/// holds, so a typo here converts a variant's whole question into a silent pass — the same
/// silent-and-flattering shape as F28's zero caveats and F22's `sound` verifier that never ran.
fn parse_expect(t: Option<&Table>, at: &str, rej: &mut Rejections) -> Expect {
    const KEYS: &[&str] =
        &["gate_fires", "gate_fires_after_deny", "interventions_delivered", "unscripted_gates"];

    let t = match t {
        Some(t) => t,
        None => return Expect::default(),
    };
    for k in t.keys() {
        if !KEYS.contains(&k.as_str()) {
            rej.add(
                RuleId::Field,
                at,
                format!("expect.{k} is not an expectation; SPEC §5 defines [{}]", KEYS.join(", ")),
            );
        }
    }
    Expect {
        gate_fires: t.get("gate_fires").map(parse_bound),
        gate_fires_after_deny: t.get("gate_fires_after_deny").map(parse_bound),
        interventions_delivered: t.get("interventions_delivered").and_then(Value::as_integer).map(|n| n as u32),
        unscripted_gates: t.get("unscripted_gates").map(parse_bound),
    }
}

/// Both the inline `operator = [ { ... } ]` form and the `[[variant.operator]]` block form land
/// here as the same array of tables, in declaration order. The loader does not distinguish them:
/// a TOML inline table cannot span lines, so a long redirect *must* use the block form, and a
/// format where the two syntaxes meant different things would be a trap.
fn parse_variant(v: &Table, origin: VariantOrigin, where_: &str, rej: &mut Rejections) -> Option<Variant> {
    let id = req_str(v, "id", where_, rej)?.to_owned();
    let at = format!("{where_}[{id}]");

    // Rule 3. `prompt` gets its own message because the enum variant reads as "prompt me" and
    // does the opposite; anyone who reasons correctly from the name arrives at the wrong answer.
    let perms = table(v, "permissions");
    let mode_raw = perms.and_then(|p| opt_str(p, "mode"));
    let mode = match mode_raw {
        Some("prompt") => {
            rej.add(
                RuleId::R3PermissionMode,
                &at,
                "permissions.mode = \"prompt\" is rejected: PermissionMode derives Ord at fc1ea22 \
                 (runtime/permissions.rs:5-11) with Prompt ranked above DangerFullAccess, so a \
                 Prompt session auto-approves everything. Use \"workspace_write\" to get a gate."
                    .to_string(),
            );
            None
        }
        Some(s) => match PermissionMode::parse(s) {
            Some(m) => Some(m),
            None => {
                rej.add(
                    RuleId::R3PermissionMode,
                    &at,
                    format!("permissions.mode = {s:?} is not one of [{}]", PermissionMode::allowed().join(", ")),
                );
                None
            }
        },
        None => {
            rej.add(RuleId::R3PermissionMode, &at, "no permissions.mode".to_string());
            None
        }
    };

    let mut operator = Vec::new();
    let mut operator_ok = true;
    if let Some(rules) = v.get("operator").and_then(Value::as_array) {
        for (i, r) in rules.iter().enumerate() {
            let rat = format!("{at}.operator[{i}]");
            let Some(rt) = r.as_table() else {
                rej.add(RuleId::OperatorGrammar, &rat, format!("rule is {}, expected a table", type_of(r)));
                operator_ok = false;
                continue;
            };
            let on = match rt.get("on").and_then(Value::as_table) {
                Some(on) => on,
                None => {
                    rej.add(RuleId::OperatorGrammar, &rat, "rule has no `on` matcher".to_string());
                    operator_ok = false;
                    continue;
                }
            };
            // v1 has exactly one event class. An `on` naming anything else matches nothing, and a
            // rule that can never fire is a typo the author wants to hear about.
            let Some(gate) = on.get("gate").and_then(Value::as_table) else {
                rej.add(RuleId::OperatorGrammar, &rat, "`on` has no `gate` matcher; it is the only event class in v1".to_string());
                operator_ok = false;
                continue;
            };
            let Some(action) = rt.get("do").map(|d| parse_action(d, &rat, rej)).unwrap_or_else(|| {
                rej.add(RuleId::OperatorGrammar, &rat, "rule has no `do` action".to_string());
                None
            }) else {
                operator_ok = false;
                continue;
            };
            operator.push(OperatorRule {
                on: Matcher {
                    gate: GateMatcher {
                        tool: gate.get("tool").and_then(Value::as_str).map(str::to_owned),
                        input_contains: gate.get("input_contains").and_then(Value::as_str).map(str::to_owned),
                    },
                },
                action,
                times: rt.get("times").and_then(Value::as_integer).map(|n| n as u32),
            });
        }
    }

    let default = match v.get("default") {
        Some(d) => parse_action(d, &at, rej),
        None => None,
    };
    // SPEC §5: `default` answers any gate no rule matched. Without it a stray gate blocks on
    // stdin until the timeout burns — a whole cell lost to a question nobody was listening for.
    if !operator.is_empty() && default.is_none() {
        rej.add(
            RuleId::NoDefault,
            &at,
            "has operator rules but no `default`: an unmatched gate would block on stdin until \
             the timeout burns"
                .to_string(),
        );
    }

    let mode = mode?;
    if !operator_ok {
        return None;
    }
    Some(Variant {
        id,
        mode,
        requires: str_list(v, "requires"),
        expect: parse_expect(table(v, "expect"), &at, rej),
        operator,
        default,
        origin,
    })
}

/// Rule 9: duplicate variant `id` **within** one file. Across files is the documented override
/// (SPEC §5), which is why this is per-file and not global.
fn parse_variant_list(
    file: &Table,
    origin: VariantOrigin,
    where_: &str,
    rej: &mut Rejections,
) -> Vec<Variant> {
    let mut out: Vec<Variant> = Vec::new();
    let Some(list) = file.get("variant").and_then(Value::as_array) else {
        return out;
    };
    for v in list {
        let Some(vt) = v.as_table() else {
            rej.add(RuleId::Field, where_, format!("[[variant]] is {}, expected a table", type_of(v)));
            continue;
        };
        if let Some(parsed) = parse_variant(vt, origin, where_, rej) {
            if out.iter().any(|e| e.id == parsed.id) {
                rej.add(RuleId::R9DuplicateVariant, where_, format!("duplicate variant id {:?} within one file", parsed.id));
                continue;
            }
            out.push(parsed);
        }
    }
    out
}

/// SPEC §5's merge: same id replaces the suite variant **entirely** and keeps its position; a new
/// id is appended. No field-level merge — a partial merge of an ordered rule list is not readable
/// in a diff, and the rule list is the whole content of an intervention.
fn merge_variants(suite: &[Variant], task: Vec<Variant>) -> Vec<Variant> {
    let mut merged: Vec<Variant> = suite.to_vec();
    for mut v in task {
        match merged.iter().position(|e| e.id == v.id) {
            Some(i) => {
                v.origin = VariantOrigin::TaskOverride;
                merged[i] = v;
            }
            None => {
                v.origin = VariantOrigin::TaskNew;
                merged.push(v);
            }
        }
    }
    merged
}

// ---------------------------------------------------------------------------
// Task
// ---------------------------------------------------------------------------

pub(crate) fn parse_task(
    dir: &Path,
    suite_id: &str,
    suite_variants: &[Variant],
    rej: &mut Rejections,
) -> Option<Task> {
    let dir_name = dir.file_name()?.to_string_lossy().into_owned();
    let where_ = format!("{suite_id}/{dir_name}");
    let path = dir.join("task.toml");
    if !path.is_file() {
        rej.add(RuleId::Parse, &where_, "no task.toml".to_string());
        return None;
    }
    let t = parse_toml(&path, rej)?;
    let before = rej.len();

    check_schema(&t, &where_, rej); // rule 1

    // Rule 2.
    let id = req_str(&t, "id", &where_, rej).unwrap_or_default().to_owned();
    if !id.is_empty() && id != dir_name {
        rej.add(RuleId::R2IdMismatch, &where_, format!("id = {id:?} but the directory is {dir_name:?}"));
    }

    let title = req_str(&t, "title", &where_, rej).unwrap_or_default().to_owned();
    let lang = vocab_str(&t, "lang", RuleId::Field, &where_, rej, Lang::parse, Lang::allowed());
    let kind = req_str(&t, "kind", &where_, rej).unwrap_or_default().to_owned();
    let timeout_s = req_int(&t, "timeout_s", &where_, rej).unwrap_or(0) as u32;

    // Rule 4. The unit of measurement is a session, so a task with no turn measures nothing.
    let mut turns = Vec::new();
    match t.get("turn").and_then(Value::as_array) {
        None => rej.add(RuleId::R4Turn, &where_, "no [[turn]]; the unit of measurement is a session with at least one".to_string()),
        Some(list) if list.is_empty() => {
            rej.add(RuleId::R4Turn, &where_, "no [[turn]]; the unit of measurement is a session with at least one".to_string())
        }
        Some(list) => {
            for (i, turn) in list.iter().enumerate() {
                let tt = turn.as_table().cloned().unwrap_or_default();
                let file = opt_str(&tt, "send_file");
                let text = opt_str(&tt, "send_text");
                match (file, text) {
                    (Some(_), Some(_)) => rej.add(RuleId::R4Turn, &where_, format!("turn[{i}] has both send_file and send_text")),
                    (None, None) => rej.add(RuleId::R4Turn, &where_, format!("turn[{i}] has neither send_file nor send_text")),
                    (Some(f), None) => {
                        let p = dir.join(f);
                        if p.is_file() {
                            turns.push(Turn::SendFile(p));
                        } else {
                            rej.add(RuleId::R4Turn, &where_, format!("turn[{i}].send_file {f:?} does not resolve"));
                        }
                    }
                    (None, Some(s)) => turns.push(Turn::SendText(s.to_owned())),
                }
            }
        }
    }

    let disp_t = table(&t, "disposition");
    // Rule 6.
    let disposition = match disp_t {
        None => {
            rej.add(RuleId::R6Disposition, &where_, "no [disposition]".to_string());
            None
        }
        Some(d) => {
            let v = vocab_str(d, "verifiable", RuleId::R6Disposition, &where_, rej, Verifiable::parse, Verifiable::allowed());
            let q = vocab_str(d, "quarantine", RuleId::R6Disposition, &where_, rej, Quarantine::parse, Quarantine::allowed());
            match (v, q) {
                (Some(verifiable), Some(quarantine)) => Some(Disposition { verifiable, quarantine }),
                _ => None,
            }
        }
    };

    // Rule 5.
    let verify = match table(&t, "verify") {
        None => {
            rej.add(RuleId::R5Verify, &where_, "no [verify]".to_string());
            None
        }
        Some(v) => match opt_str(v, "kind") {
            Some("script") => match opt_str(v, "script") {
                Some(s) if dir.join(s).is_file() => Some(Verify::Script(s.to_owned())),
                Some(s) => {
                    rej.add(RuleId::R5Verify, &where_, format!("verify.script {s:?} does not resolve"));
                    None
                }
                None => {
                    rej.add(RuleId::R5Verify, &where_, "verify.kind = \"script\" with no verify.script".to_string());
                    None
                }
            },
            Some("none") => {
                if disposition.map(|d| d.verifiable) != Some(Verifiable::None) {
                    rej.add(RuleId::R5Verify, &where_, "verify.kind = \"none\" but disposition.verifiable != \"none\"".to_string());
                }
                Some(Verify::None)
            }
            other => {
                rej.add(RuleId::R5Verify, &where_, format!("verify.kind = {other:?}, expected \"script\" or \"none\""));
                None
            }
        },
    };

    // Rule 7. `not_run` is how you say "not yet"; silence is not.
    let gate = match table(&t, "gate") {
        None => {
            rej.add(RuleId::R7Gate, &where_, "no [gate]".to_string());
            None
        }
        Some(g) => {
            let p1 = vocab_str(g, "point1", RuleId::R7Gate, &where_, rej, GateVerdict::parse, GateVerdict::allowed());
            let p2 = vocab_str(g, "point2", RuleId::R7Gate, &where_, rej, GateVerdict::parse, GateVerdict::allowed());
            let p3 = vocab_str(g, "point3", RuleId::R7Gate, &where_, rej, GateVerdict::parse, GateVerdict::allowed());
            let mut evidence = Vec::new();
            for (i, e) in g.get("evidence").and_then(Value::as_array).unwrap_or(&Vec::new()).iter().enumerate() {
                let eat = format!("{where_}.gate.evidence[{i}]");
                let Some(et) = e.as_table() else {
                    rej.add(RuleId::R7Gate, &eat, format!("evidence is {}, expected a table", type_of(e)));
                    continue;
                };
                let point = req_int(et, "point", &eat, rej).unwrap_or(0) as u8;
                let tier = vocab_str(et, "tier", RuleId::R7Gate, &eat, rej, GateTier::parse, GateTier::allowed());
                let verdict = vocab_str(et, "verdict", RuleId::R7Gate, &eat, rej, RunVerdict::parse, RunVerdict::allowed());
                let verifier = vocab_str(et, "verifier", RuleId::R7Gate, &eat, rej, VerifierUnderTest::parse, VerifierUnderTest::allowed());
                if let (Some(tier), Some(verdict), Some(verifier)) = (tier, verdict, verifier) {
                    evidence.push(Evidence {
                        point,
                        tier,
                        verdict,
                        verifier,
                        detail: opt_str(et, "detail").unwrap_or_default().to_owned(),
                        run: opt_str(et, "run").unwrap_or_default().to_owned(),
                    });
                }
            }
            match (p1, p2, p3) {
                (Some(point1), Some(point2), Some(point3)) => Some(Gate { point1, point2, point3, evidence }),
                _ => None,
            }
        }
    };

    // A `broken` gate point and a clean disposition cannot both be true: `broken` means a wrong
    // answer was accepted, and the standing rule for anything that fails the gate is
    // quarantine-with-baseline (David, 2026-08-08).
    if let (Some(g), Some(d)) = (&gate, &disposition)
        && [g.point1, g.point2, g.point3].contains(&GateVerdict::Broken)
        && d.quarantine != Quarantine::WithBaseline
    {
        rej.add(RuleId::R7Gate, &where_, "a gate point is `broken` but the task is not quarantined".to_string());
    }

    // Rule 10 — the one that costs something to maintain, and the reason the provenance block
    // exists. An import whose provenance is approximately right is an import whose comparability
    // argument is approximately right.
    let provenance = match table(&t, "provenance") {
        None => {
            rej.add(RuleId::R10Partition, &where_, "no [provenance]".to_string());
            None
        }
        Some(p) => {
            let verbatim = str_list(p, "verbatim");
            let rewritten = str_list(p, "rewritten");
            let synthesized = str_list(p, "synthesized");
            let flat: Vec<&String> = verbatim.iter().chain(&rewritten).chain(&synthesized).collect();

            let mut dupes: Vec<&str> = flat.iter().filter(|f| flat.iter().filter(|g| g == f).count() > 1).map(|s| s.as_str()).collect();
            dupes.sort_unstable();
            dupes.dedup();
            let mut missing: Vec<&str> = PARTITION.iter().copied().filter(|f| !flat.iter().any(|g| g.as_str() == *f)).collect();
            missing.sort_unstable();
            let mut extra: Vec<&str> = flat.iter().map(|s| s.as_str()).filter(|f| !PARTITION.contains(f)).collect();
            extra.sort_unstable();
            extra.dedup();

            if !dupes.is_empty() {
                rej.add(RuleId::R10Partition, &where_, format!("field(s) in more than one provenance list: [{}]", dupes.join(", ")));
            }
            if !missing.is_empty() {
                rej.add(RuleId::R10Partition, &where_, format!("field(s) in no provenance list: [{}]", missing.join(", ")));
            }
            if !extra.is_empty() {
                rej.add(RuleId::R10Partition, &where_, format!("provenance names field(s) outside the closed vocabulary: [{}]", extra.join(", ")));
            }

            req_str(p, "donor", &where_, rej).map(|donor| Provenance {
                donor: donor.to_owned(),
                donor_id: opt_str(p, "donor_id").map(str::to_owned),
                donor_commit: opt_str(p, "donor_commit").map(str::to_owned),
                donor_path: opt_str(p, "donor_path").map(str::to_owned),
                imported_at: opt_str(p, "imported_at").map(str::to_owned),
                verbatim,
                rewritten,
                synthesized,
                caveats: str_list(p, "caveats"),
            })
        }
    };

    let selection = table(&t, "selection")
        .map(|s| Selection {
            gate3: s.get("gate3").and_then(Value::as_bool).unwrap_or(false),
            gate3_rank: s.get("gate3_rank").and_then(Value::as_integer).map(|n| n as u32),
        })
        .unwrap_or_default();

    let donor_tags: BTreeMap<String, String> = table(&t, "donor_tags")
        .map(|d| d.iter().map(|(k, v)| (k.clone(), scalar(v))).collect())
        .unwrap_or_default();

    // Task-level variants, then SPEC §5's merge.
    let task_variants = if dir.join("variants.toml").is_file() {
        match parse_toml(&dir.join("variants.toml"), rej) {
            Some(vt) => parse_variant_list(&vt, VariantOrigin::TaskNew, &where_, rej),
            None => Vec::new(),
        }
    } else {
        Vec::new()
    };
    let variants = merge_variants(suite_variants, task_variants);

    // SPEC §2's isolation guarantee. A fixture the loader cannot plan is a corpus it must refuse
    // to run, not a task to run with a best-effort copy.
    let workdir = match workdir::plan(dir) {
        Ok(p) => p,
        Err(e) => {
            rej.add(RuleId::Isolation, &where_, e.to_string());
            workdir::WorkdirPlan::default()
        }
    };

    if rej.len() != before {
        return None;
    }
    Some(Task {
        id,
        title,
        lang: lang?,
        kind,
        timeout_s,
        turns,
        verify: verify?,
        disposition: disposition?,
        selection,
        gate: gate?,
        provenance: provenance?,
        donor_tags,
        variants,
        workdir,
        gate_dirs: GateDirs::probe(dir),
        dir: dir.to_path_buf(),
    })
}

fn scalar(v: &Value) -> String {
    match v {
        Value::String(s) => s.clone(),
        Value::Integer(i) => i.to_string(),
        Value::Float(f) => f.to_string(),
        Value::Boolean(b) => b.to_string(),
        other => format!("{other:?}"),
    }
}

// ---------------------------------------------------------------------------
// Suite and subject
// ---------------------------------------------------------------------------

pub(crate) fn parse_suite(dir: &Path, rej: &mut Rejections) -> Option<(Suite, Vec<Variant>)> {
    let dir_name = dir.file_name()?.to_string_lossy().into_owned();
    let path = dir.join("suite.toml");
    let t = parse_toml(&path, rej)?;
    let where_ = format!("suites/{dir_name}");

    check_schema(&t, &where_, rej);
    let id = req_str(&t, "id", &where_, rej).unwrap_or_default().to_owned();
    if !id.is_empty() && id != dir_name {
        rej.add(RuleId::R2IdMismatch, &where_, format!("id = {id:?} but the directory is {dir_name:?}"));
    }

    let variants = parse_variant_list(&t, VariantOrigin::Suite, &format!("{dir_name}/<suite>"), rej);

    let aggregate = match table(&t, "aggregate") {
        None => {
            rej.add(RuleId::Field, &where_, "no [aggregate]; a suite with no aggregate rule cannot produce a headline number".to_string());
            AggregateRule { include_verifiable: Vec::new(), exclude_quarantined: true }
        }
        Some(a) => {
            let mut include = Vec::new();
            for v in a.get("include_verifiable").and_then(Value::as_array).unwrap_or(&Vec::new()) {
                match v.as_str().and_then(Verifiable::parse) {
                    Some(x) => include.push(x),
                    None => rej.add(RuleId::Field, &where_, format!("aggregate.include_verifiable holds {v:?}, not one of [{}]", Verifiable::allowed().join(", "))),
                }
            }
            AggregateRule {
                include_verifiable: include,
                exclude_quarantined: a.get("exclude_quarantined").and_then(Value::as_bool).unwrap_or(true),
            }
        }
    };

    // `caveats` and `expected_tasks` are read from `[provenance]` first and the top level second,
    // and that is not defensiveness — it is a defect the port found. SPEC §4's prose says
    // "suite-level `caveats`", but §4's own example places the key *after* `[provenance]`, which
    // under TOML scoping makes it `provenance.caveats`. `suites/u100/suite.toml` does the same.
    // A loader that reads only the top level therefore finds **zero caveats and no
    // expected_tasks**, silently, and in the flattering direction: a suite that records no
    // caveats looks cleaner than it is, and the guard against a silently missing task directory
    // never fires. Accept both, since only a parser can see the difference.
    let prov = table(&t, "provenance");
    let suite_key = |k: &str| prov.and_then(|p| p.get(k)).or_else(|| t.get(k));

    let suite = Suite {
        id: if id.is_empty() { dir_name } else { id },
        title: opt_str(&t, "title").unwrap_or_default().to_owned(),
        caveats: suite_key("caveats")
            .and_then(Value::as_array)
            .map(|a| a.iter().filter_map(|v| v.as_str().map(str::to_owned)).collect())
            .unwrap_or_default(),
        aggregate,
        retry_on_timeout: table(&t, "aggregate")
            .and_then(|a| a.get("retry_on_timeout"))
            .or_else(|| t.get("retry_on_timeout"))
            .and_then(Value::as_bool)
            .unwrap_or(false),
        expected_tasks: suite_key("expected_tasks").and_then(Value::as_integer).map(|n| n as usize),
        tasks: Vec::new(),
        dir: dir.to_path_buf(),
    };
    Some((suite, variants))
}

pub(crate) fn parse_subject(path: &Path, rej: &mut Rejections) -> Option<Subject> {
    let stem = path.file_stem()?.to_string_lossy().into_owned();
    let t = parse_toml(path, rej)?;
    let where_ = format!("subjects/{stem}");
    let before = rej.len();

    check_schema(&t, &where_, rej);
    let id = req_str(&t, "id", &where_, rej).unwrap_or_default().to_owned();
    if !id.is_empty() && id != stem {
        rej.add(RuleId::R2IdMismatch, &where_, format!("id = {id:?} but the file is {stem:?}.toml"));
    }
    let version = req_str(&t, "version", &where_, rej).unwrap_or_default().to_owned();
    let bin = req_str(&t, "bin", &where_, rej).unwrap_or_default().to_owned();
    let drive = req_str(&t, "drive", &where_, rej).unwrap_or_default().to_owned();

    let markers = table(&t, "markers")
        .map(|m| Markers {
            gate: opt_str(m, "gate").unwrap_or_default().to_owned(),
            turn_end: opt_str(m, "turn_end").unwrap_or_default().to_owned(),
        })
        .unwrap_or_default();

    // `[delivery]` is optional — a subject with no way to receive a multi-line prompt is a valid
    // subject, it just cannot run the tasks that need one. But a *partial* declaration is refused:
    // a half-declared sentinel pair would wrap a prompt in something the subject never closes on,
    // and the failure would land as a timeout rather than as a bad descriptor.
    let delivery = table(&t, "delivery").and_then(|d| {
        let open = opt_str(d, "open").unwrap_or_default().to_owned();
        let close = opt_str(d, "close").unwrap_or_default().to_owned();
        let where_d = format!("{where_}.delivery");
        if open.is_empty() || close.is_empty() {
            rej.add(
                RuleId::Field,
                &where_d,
                "both `open` and `close` are required once [delivery] is present".to_string(),
            );
            return None;
        }
        if open == close {
            rej.add(
                RuleId::Field,
                &where_d,
                format!("`open` and `close` are both {open:?}; a block that opens and closes on \
                         the same line can never carry content"),
            );
            return None;
        }
        Some(BlockDelivery { open, close })
    });

    if rej.len() != before {
        return None;
    }
    Some(Subject {
        id,
        version,
        commit: opt_str(&t, "commit").map(str::to_owned),
        bin,
        drive,
        capabilities: str_list(&t, "capabilities"),
        env: table(&t, "env").map(|e| e.iter().map(|(k, v)| (k.clone(), scalar(v))).collect()).unwrap_or_default(),
        markers,
        delivery,
        path: path.to_path_buf(),
    })
}
