//! W11 item 3 probe harness — the five handoff artifacts as Rust types.
//!
//!   artifacts schemas <outdir>        emit each wire type's JSON Schema
//!   artifacts check <kind> <file>     deserialise a model payload into it
//!   artifacts ground <root> <file>    brief: check every path against a tree
//!   artifacts evolve                  append-only log vs. a changed type
//!   artifacts bcf-parse <file>        BCF's critique parser, ported verbatim

mod checked;
mod emit;
mod wire;

use std::path::Path;

/// `schema_for!` as a plain `Value`, before `emit::apply` fixes the order.
pub fn schema_json<T: schemars::JsonSchema>() -> serde_json::Value {
    serde_json::to_value(schemars::schema_for!(T)).unwrap()
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let cmd = args.first().map(String::as_str).unwrap_or("help");
    match cmd {
        "schemas" => schemas(args.get(1).map(String::as_str).unwrap_or(".")),
        "check" => check(&args[1], &args[2]),
        "ground" => ground(&args[1], &args[2]),
        "evolve" => evolve(),
        "bcf-parse" => bcf_parse(&args[1]),
        _ => eprintln!("{}", include_str!("main.rs").lines().take(8).collect::<Vec<_>>().join("\n")),
    }
}

// ── schemas ──────────────────────────────────────────────────────────

fn schemas(outdir: &str) {
    std::fs::create_dir_all(outdir).unwrap();
    let mut out = |name: &str, mut v: serde_json::Value| {
        let raw_first = v["properties"]
            .as_object()
            .and_then(|o| o.keys().next().cloned())
            .unwrap_or_default();
        emit::apply(&mut v, name);
        let emitted_first = v["properties"]
            .as_object()
            .and_then(|o| o.keys().next().cloned())
            .unwrap_or_default();
        let text = serde_json::to_string_pretty(&v).unwrap();
        std::fs::write(Path::new(outdir).join(format!("{name}.json")), &text).unwrap();
        println!(
            "{:<12} {:>5}B  $defs={:<2} $ref={:<5} nullable={:<5} \
             schemars_first={:<12} emitted_first={:<12}{}",
            name,
            text.len(),
            v.get("$defs").and_then(|d| d.as_object()).map_or(0, |o| o.len()),
            text.contains("\"$ref\""),
            text.contains("null"),
            raw_first,
            emitted_first,
            match emit::decision_key(name) {
                Some(d) if raw_first == d => "   <- schemars put the decision first",
                _ => "",
            },
        );
    };
    out("brief", schema_json::<wire::BriefWire>());
    out("task_set", schema_json::<wire::TaskSetWire>());
    out("change_note", schema_json::<wire::ChangeNoteWire>());
    out("verdict", schema_json::<wire::VerdictWire>());
}

// ── check ────────────────────────────────────────────────────────────

fn check(kind: &str, file: &str) {
    let text = std::fs::read_to_string(file).unwrap_or_default();
    let r = match kind {
        "brief" => serde_json::from_str::<wire::BriefWire>(&text).map(|v| format!("{v:?}")),
        "task_set" => serde_json::from_str::<wire::TaskSetWire>(&text).map(|v| format!("{v:?}")),
        "change_note" => serde_json::from_str::<wire::ChangeNoteWire>(&text).map(|v| format!("{v:?}")),
        "verdict" => serde_json::from_str::<wire::VerdictWire>(&text).map(|v| format!("{v:?}")),
        other => {
            eprintln!("unknown kind: {other}");
            return;
        }
    };
    match r {
        Ok(v) => println!("PARSE ok    {kind}  {} chars  {}", text.len(), &v[..v.len().min(120)]),
        Err(e) => println!("PARSE FAIL  {kind}  {e}"),
    }
}

// ── ground: the half a schema cannot do ──────────────────────────────

fn ground(root: &str, file: &str) {
    let root = Path::new(root);
    let text = std::fs::read_to_string(file).unwrap_or_default();
    // Try a brief first, then a task set: the grounding question is the same.
    let paths: Vec<String> = if let Ok(b) = serde_json::from_str::<wire::BriefWire>(&text) {
        b.sites.iter().map(|s| s.path.clone()).collect()
    } else if let Ok(t) = serde_json::from_str::<wire::TaskSetWire>(&text) {
        t.tasks.iter().flat_map(|t| t.touches.clone()).collect()
    } else {
        println!("GROUND  n/a  payload did not parse as brief or task_set");
        return;
    };
    let mut ok = 0usize;
    for p in &paths {
        match checked::RepoPath::check(root, p) {
            Ok(_) => {
                ok += 1;
                println!("  exists    {p}");
            }
            Err(why) => println!("  UNGROUND  {p}   {why:?}"),
        }
    }
    println!("GROUND  {ok}/{} paths exist under {}", paths.len(), root.display());
}

// ── evolve: what append-only does to a typed payload ─────────────────

/// `verdict.v1` — what the log already holds.
#[derive(Debug, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct VerdictV1 {
    call: wire::Call,
    rationale: String,
    defects: Vec<wire::DefectWire>,
}

/// `verdict.v2` — one field added, six months later. No `#[serde(default)]`,
/// because item 1 §6 forbids a default on a gate input.
#[derive(Debug, serde::Serialize, serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct VerdictV2 {
    call: wire::Call,
    rationale: String,
    defects: Vec<wire::DefectWire>,
    /// The new field: which measurement the Judge leaned on.
    decisive_check: String,
}

/// The same field, added the way serde's documentation suggests.
#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct VerdictV2Lenient {
    call: wire::Call,
    rationale: String,
    defects: Vec<wire::DefectWire>,
    #[serde(default)]
    decisive_check: String,
}

fn evolve() {
    let v1 = VerdictV1 {
        call: wire::Call::Fail,
        rationale: "criterion failed".into(),
        defects: vec![],
    };
    let old_event = serde_json::to_string(&v1).unwrap();
    let v2 = VerdictV2 {
        call: wire::Call::Fail,
        rationale: "criterion failed".into(),
        defects: vec![],
        decisive_check: "criterion".into(),
    };
    let new_event = serde_json::to_string(&v2).unwrap();

    println!("old event on the log : {old_event}");
    println!("new event on the log : {new_event}");
    println!();
    println!("-- today's reader against yesterday's event --");
    match serde_json::from_str::<VerdictV2>(&old_event) {
        Ok(v) => println!("  strict   v2 <- v1  OK   {v:?}"),
        Err(e) => println!("  strict   v2 <- v1  FAIL {e}"),
    }
    match serde_json::from_str::<VerdictV2Lenient>(&old_event) {
        Ok(v) => println!(
            "  default  v2 <- v1  OK   decisive_check={:?}  <- the forbidden fix",
            v.decisive_check
        ),
        Err(e) => println!("  default  v2 <- v1  FAIL {e}"),
    }
    println!();
    println!("-- yesterday's reader against today's event (replay after a downgrade) --");
    match serde_json::from_str::<VerdictV1>(&new_event) {
        Ok(v) => println!("  strict   v1 <- v2  OK   {v:?}"),
        Err(e) => println!("  strict   v1 <- v2  FAIL {e}"),
    }
    #[derive(serde::Deserialize, Debug)]
    struct VerdictV1Open {
        call: wire::Call,
        #[allow(dead_code)]
        rationale: String,
    }
    match serde_json::from_str::<VerdictV1Open>(&new_event) {
        Ok(v) => println!("  open     v1 <- v2  OK   {v:?}  <- unknown field silently dropped"),
        Err(e) => println!("  open     v1 <- v2  FAIL {e}"),
    }
}

// ── BCF's critique parser, ported verbatim ───────────────────────────

/// Line-for-line port of `battle-command-forge:src/mission.rs:1654-1687`.
/// Same initialisation (`5.0`), same `find(prefix)`, same "first number 0-10
/// on the line" scan from the start of the line, same `|` split for defects.
fn bcf_critique_parse(response: &str) -> (Vec<f32>, Vec<String>) {
    let mut scores = vec![5.0f32; 5];
    let mut details = vec![String::new(); 5];
    let prefixes = ["DEV", "ARCH", "TEST", "SEC", "DOCS"];

    for line in response.lines() {
        let stripped: String = line.chars().filter(|c| *c != '*' && *c != '#').collect();
        let upper = stripped.to_uppercase();
        for (i, prefix) in prefixes.iter().enumerate() {
            if let Some(pos) = upper.find(prefix) {
                let after = &upper[pos + prefix.len()..];
                if after.starts_with(':') || after.starts_with(' ') || after.starts_with('=') {
                    for word in stripped.split_whitespace() {
                        let cleaned = word.trim_matches(|c: char| !c.is_numeric() && c != '.');
                        if let Ok(n) = cleaned.parse::<f32>() {
                            if (0.0..=10.0).contains(&n) {
                                scores[i] = n;
                                break;
                            }
                        }
                    }
                    if let Some(defect_part) = line.split('|').nth(1) {
                        details[i] = defect_part.trim().to_string();
                    }
                }
            }
        }
    }
    (scores, details)
}

fn bcf_parse(file: &str) {
    let text = std::fs::read_to_string(file).unwrap_or_default();
    // Blank line separates cases; first line of each case is its label.
    // Normalise line endings first: this model emits CRLF, and splitting a
    // CRLF file on "\n\n" silently yields ONE case rather than an error.
    let text = text.replace("\r\n", "\n");
    for case in text.split("\n\n") {
        let case = case.trim_end();
        if case.is_empty() {
            continue;
        }
        let (label, body) = case.split_once('\n').unwrap_or((case, ""));
        let (scores, details) = bcf_critique_parse(body);
        let avg: f32 = scores.iter().sum::<f32>() / 5.0;
        let all_default = scores.iter().all(|&s| s == 5.0);
        println!(
            "{:<34} scores={:?} avg={:.2}{}  details_found={}",
            label.trim(),
            scores,
            avg,
            if all_default { "  <- all-default (BCF warns)" } else { "" },
            details.iter().filter(|d| !d.is_empty()).count(),
        );
    }
}
