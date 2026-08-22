//! Emission order — the part of an artifact schema that nothing in the derive
//! chain preserves, and that turns out to decide the answer.
//!
//! Measured (`order.py`, `enumbias.py`, `prefix.py`, 37 calls at temperature 0):
//! a Judge asked for `call` as the FIRST key of its object answered `pass`
//! against a failed acceptance criterion **14 times out of 14**, writing a
//! rationale in the same object that argued for `fail`. With any field that
//! carries the argument in front of it — `rationale`, `assessment`, `defects` —
//! it answered `fail` **17 times out of 17**. Reversing the enum's own value
//! order changed nothing in either direction, and a zero-information prefix
//! (`{"artifact_version":"v1"}`) did not help: 0/3.
//!
//! Two separate things destroy that order, and the first one is not the one it
//! looks like:
//!
//! 1. **`serde_json`'s default `Map` is a `BTreeMap`.** Without the
//!    `preserve_order` feature — which nothing on the dependency line mentions
//!    — every JSON object this crate builds is re-sorted alphabetically on
//!    serialisation, including the one it just carefully ordered. `schemars`
//!    is *not* the alphabetiser: with `preserve_order` on, `SiteWire` comes
//!    out `path, first_line, last_line, why` (declaration order) where
//!    alphabetical would be `first_line, last_line, path, why`. Turning the
//!    feature on is the whole fix for that layer, and there is no compile
//!    error and no warning if you never do.
//! 2. **The declaration order itself.** `VerdictWire` is declared
//!    `call, rationale, defects` because that is how a person writes down a
//!    verdict, which puts the decision first — 0/14. Declaration order is a
//!    prose habit; emission order is a measurement.
//!
//! So: one explicit emission order per artifact, one declared decision key per
//! artifact, and a test that refuses to let the decision key be first.

use serde_json::Value;

/// `(type, emission order, the key that records a decision)`.
///
/// The decision key is the field a gate reads. Everything before it in the
/// emission order is the model's working, and it is there to be read by the
/// model itself as it decodes.
pub const ARTIFACTS: &[(&str, &[&str], Option<&str>)] = &[
    (
        "brief",
        &["restatement", "sites", "risks", "approach"],
        None, // a brief records no decision
    ),
    (
        "task_set",
        &["tasks"],
        None,
    ),
    (
        "task",
        &["title", "intent", "touches", "depends_on", "criterion"],
        None,
    ),
    (
        "change_note",
        &["summary", "unresolved"],
        None,
    ),
    (
        "verdict",
        &["rationale", "defects", "call"],
        Some("call"),
    ),
];

fn order_for(ty: &str) -> Option<&'static [&'static str]> {
    ARTIFACTS.iter().find(|(t, _, _)| *t == ty).map(|(_, o, _)| *o)
}

pub fn decision_key(ty: &str) -> Option<&'static str> {
    ARTIFACTS.iter().find(|(t, _, _)| *t == ty).and_then(|(_, _, d)| *d)
}

/// Rewrite one object's `properties` (and `required`) into the declared
/// emission order. Keys not in the list keep their relative position at the
/// end — a new field is never silently promoted in front of a decision.
pub fn reorder_object(node: &mut Value, order: &[&str]) {
    let Some(obj) = node.as_object_mut() else { return };
    let Some(props) = obj.get("properties").and_then(Value::as_object).cloned() else {
        return;
    };
    let mut out = serde_json::Map::new();
    for k in order {
        if let Some(v) = props.get(*k) {
            out.insert((*k).to_string(), v.clone());
        }
    }
    for (k, v) in &props {
        if !out.contains_key(k) {
            out.insert(k.clone(), v.clone());
        }
    }
    let keys: Vec<Value> = out.keys().map(|k| Value::String(k.clone())).collect();
    obj.insert("properties".into(), Value::Object(out));
    // Every property required, in the same order. `schemars` leaves `Option`
    // fields out of `required`; OpenAI's strict mode forbids that, and a
    // nullable type expresses the same thing without the omission.
    obj.insert("required".into(), Value::Array(keys));
}

/// Apply the declared order to a whole schema: the root, plus any `$defs`
/// entry whose name matches an artifact name (case-insensitively, minus the
/// `Wire` suffix `schemars` derives from the Rust type).
pub fn apply(schema: &mut Value, root_ty: &str) {
    if let Some(order) = order_for(root_ty) {
        reorder_object(schema, order);
    }
    let defs: Vec<String> = schema
        .get("$defs")
        .and_then(Value::as_object)
        .map(|o| o.keys().cloned().collect())
        .unwrap_or_default();
    for name in defs {
        let key = name.trim_end_matches("Wire").to_lowercase();
        let order = order_for(&key).map(<[&str]>::to_vec);
        if let Some(node) = schema
            .get_mut("$defs")
            .and_then(|d| d.get_mut(&name))
        {
            if let Some(order) = order {
                reorder_object(node, &order);
            } else {
                // Still close the `required` gap for strict mode.
                if let Some(props) = node.get("properties").and_then(Value::as_object) {
                    let keys: Vec<Value> =
                        props.keys().map(|k| Value::String(k.clone())).collect();
                    node.as_object_mut()
                        .unwrap()
                        .insert("required".into(), Value::Array(keys));
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The rule the measurement bought. A decision key that is first in the
    /// emission order is a Judge that answers before it reasons, and this test
    /// is the only thing standing between that and a schema regenerated by
    /// `schema_for!`.
    #[test]
    fn a_decision_key_is_never_the_first_emitted_field() {
        for (ty, order, decision) in ARTIFACTS {
            let Some(d) = decision else { continue };
            assert!(
                order.contains(d),
                "{ty}: decision key `{d}` is not in the emission order"
            );
            assert_ne!(
                order.first().copied(),
                Some(*d),
                "{ty}: `{d}` is the first emitted field — measured 0/14 correct in that position"
            );
        }
    }

    /// `schema_for!` follows declaration order, and declaration order puts the
    /// decision first. The shipped schema must not.
    #[test]
    fn reorder_moves_the_decision_behind_its_reasoning() {
        let mut s = crate::schema_json::<crate::wire::VerdictWire>();
        let before: Vec<String> = s["properties"].as_object().unwrap().keys().cloned().collect();
        assert_eq!(before.first().map(String::as_str), Some("call"));
        apply(&mut s, "verdict");
        let after: Vec<String> = s["properties"].as_object().unwrap().keys().cloned().collect();
        assert_eq!(after, vec!["rationale", "defects", "call"]);
    }

    /// Every property in `required`, including the nullable ones.
    #[test]
    fn every_property_is_required_after_apply() {
        let mut s = crate::schema_json::<crate::wire::VerdictWire>();
        apply(&mut s, "verdict");
        let defect = &s["$defs"]["DefectWire"];
        let props: Vec<&String> = defect["properties"].as_object().unwrap().keys().collect();
        let req: Vec<&str> = defect["required"]
            .as_array()
            .unwrap()
            .iter()
            .map(|v| v.as_str().unwrap())
            .collect();
        assert_eq!(props.len(), req.len(), "`path` is nullable, not optional");
    }
}
