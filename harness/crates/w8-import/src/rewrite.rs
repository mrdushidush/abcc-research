//! Stage 2 — rewrite. Turns a `DonorTask` into the corpus task SPEC v1 describes.
//!
//! Every edit made here is recorded on the task as a caveat, and every corpus field lands in
//! exactly one of `verbatim` / `rewritten` / `synthesized` (SPEC §3 rule 10). That is the whole
//! mechanism by which "importing rather than extending means comparability must be argued"
//! becomes a per-field record instead of a paragraph someone has to remember to write.

use crate::donor::DonorTask;
use crate::verify_sh;
use std::collections::BTreeMap;

/// How much a donor verifier actually establishes. Mirrors `rank.py`'s `verifier_class`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VClass {
    /// Imports or requires the produced artifact and asserts on behaviour.
    Exec,
    /// Reads the produced file and asserts substrings are present.
    StrMatch,
    /// `validation: null`; the donor scored the agent-execution success flag (F13).
    None,
}

impl VClass {
    /// SPEC §10. The mapping is the whole of the disposition decision for `verifiable`.
    pub fn verifiable(self) -> &'static str {
        match self {
            VClass::Exec => "full",
            VClass::StrMatch => "presence_only",
            VClass::None => "none",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VerifyLang {
    Python,
    Node,
}

#[derive(Debug, Clone)]
pub struct Task {
    pub id: String,
    pub title: String,
    pub lang: &'static str,
    pub kind: String,
    pub timeout_s: u32,
    pub vclass: VClass,
    /// The donor path the prompt dictates, e.g. `tasks/security_fixes/sql_inject.py`.
    pub artifact_donor: String,
    /// Its basename, which is where it lives in the work dir.
    pub artifact: String,
    pub prompt: String,
    /// `None` when `vclass == None`, i.e. `[verify].kind = "none"`.
    pub verify: Option<Verify>,
    /// Files copied fresh into the work dir per run: donor fixture bodies and reconstructed
    /// cross-task dependencies. Empty for the 78 tasks that generate from nothing.
    pub fixture: BTreeMap<String, String>,
    /// Flat filenames the verifier reaches for that are *not* the artifact.
    pub deps: Vec<String>,
    pub gate3_rank: Option<usize>,
    /// The artifact body the donor's own prompt dictates, where it dictates one (60 of the 90).
    /// This is a reference solution by construction, which is what makes a positive control
    /// possible without authoring anything: see `--selftest`.
    pub dictated: Option<String>,
    pub caveats: Vec<String>,
    pub donor: DonorTask,
    /// Set when the fixture body came from the donor's `BUGGY_FILES` rather than being
    /// reconstructed; decides whether `fixture` is verbatim or synthesized.
    pub fixture_is_donor: bool,
}

#[derive(Debug, Clone)]
pub struct Verify {
    pub lang: VerifyLang,
    /// The donor assertion body after the recorded rewrites, executed verbatim by `verify.sh`.
    pub body: String,
    /// The full text of `verify.sh`.
    pub script: String,
}

// ---------------------------------------------------------------------------------------------
// The frozen gate3 selection (R9/R10)
// ---------------------------------------------------------------------------------------------

/// The 30 tasks that get the three-point gate, in rank order.
///
/// This is a **decision, not a computation**: David approved R10's set on 2026-08-08 after R9
/// settled that "hardest" means *where a sham is most likely to pass*, tie-broken by verifier
/// exposure. `research/spikes/w8-hardest-30/rank.py` is the code that produced it, and the
/// order below is that script's output. It is embedded rather than re-derived because
/// re-deriving an approved selection from a results TSV is a way for the set to drift silently
/// between the approval and the corpus.
pub const GATE3: [&str; 30] = [
    "fix_insecure_random",
    "fix_missing_validation",
    "fix_weak_hash",
    "fix_xss_reflect",
    "sec_xss_filter",
    "fix_path_traversal",
    "fix_hardcoded_secret",
    "fix_open_redirect",
    "fix_sql_inject",
    "fix_type_confusion",
    "fix_info_leak",
    "sec_brute_force",
    "sec_csp_builder",
    "sec_csrf_token",
    "sec_input_validator",
    "sec_jwt_simple",
    "sec_password_hash",
    "sec_rate_limit",
    "sec_sanitize_html",
    "sec_sanitize_sql",
    "py_rate_limiter",
    "py_text_pipeline",
    "node_router",
    "py_router",
    "node_query_parser",
    "node_server_main",
    "py_server_main",
    "mini_markdown",
    "tm_utils",
    "mini_todo_cli",
];

/// The donor's global task timeout: `TASK_TIMEOUT_MS = 5 * 60 * 1000`. There is no per-task
/// value, and the clean runs' 307 s `fetch failed` rows are this firing rather than infra
/// noise (F12).
pub const TIMEOUT_S: u32 = 300;

// ---------------------------------------------------------------------------------------------
// Small text helpers (no regex crate: these patterns are all delimiter scans)
// ---------------------------------------------------------------------------------------------

fn is_path_byte(c: u8) -> bool {
    c.is_ascii_alphanumeric() || matches!(c, b'.' | b'_' | b'/' | b'-')
}

fn is_mod_byte(c: u8) -> bool {
    c.is_ascii_alphanumeric() || matches!(c, b'.' | b'_')
}

/// Is `at` the start of a `tasks/` or `tasks.` token rather than the tail of a longer name?
///
/// Only identifier characters disqualify it, so `subtasks/x` is skipped while `./tasks/x` and
/// `/app/workspace/tasks/x` are not. Treating `/` and `.` as disqualifying was the first version
/// of this function and it silently left every node `require('./tasks/...')` unflattened — the
/// 17 node verifiers would have shipped pointing at paths that do not exist in the work dir.
fn boundary_before(s: &str, at: usize) -> bool {
    if at == 0 {
        return true;
    }
    let p = s.as_bytes()[at - 1];
    !(p.is_ascii_alphanumeric() || matches!(p, b'_' | b'-'))
}

/// Every `tasks/...` token in `text`, longest-first so replacement is unambiguous.
fn donor_path_tokens(text: &str) -> Vec<String> {
    let b = text.as_bytes();
    let mut out: Vec<String> = Vec::new();
    let mut i = 0;
    while let Some(rel) = text[i..].find("tasks/") {
        let at = i + rel;
        i = at + 6;
        if !boundary_before(text, at) {
            continue;
        }
        let mut j = at;
        while j < b.len() && is_path_byte(b[j]) {
            j += 1;
        }
        let tok = text[at..j].trim_end_matches(['.', '/']).to_string();
        if tok.contains('/') && !out.contains(&tok) {
            out.push(tok);
        }
    }
    out.sort_by_key(|t| std::cmp::Reverse(t.len()));
    out
}

fn basename(p: &str) -> String {
    p.rsplit('/').next().unwrap_or(p).to_string()
}

/// Strip the container prefix and flatten every `tasks/<dir>/<file>` to `<file>`.
///
/// Flattening is safe as a blanket rule: all 107 donor paths sit at exactly one directory of
/// depth, every task dictates exactly one artifact, and flattening the basenames collides in
/// **zero** of the 90 tasks. Measured before this rule was written, not assumed.
fn flatten_paths(text: &str) -> String {
    let mut out = text.replace("/app/workspace/", "");
    for tok in donor_path_tokens(&out) {
        out = out.replace(&tok, &basename(&tok));
    }
    out
}

/// `tasks.<dir>.<mod>` -> `<mod>`, for python's dotted import form.
fn flatten_py_modules(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let b = text.as_bytes();
    let mut i = 0;
    while i < text.len() {
        if text[i..].starts_with("tasks.") && boundary_before(text, i) {
            let mut j = i;
            while j < b.len() && is_mod_byte(b[j]) {
                j += 1;
            }
            let tok = text[i..j].trim_end_matches('.');
            out.push_str(tok.rsplit('.').next().unwrap_or(tok));
            i = j;
            continue;
        }
        let ch = text[i..].chars().next().unwrap();
        out.push(ch);
        i += ch.len_utf8();
    }
    out
}

/// `from .router import Router` -> `from router import Router`.
///
/// A relative import needs a package, and the flattened work dir is not one. Exactly one donor
/// prompt dictates relative imports (`py_server_main`), and left alone it tells the subject to
/// write a file that cannot import under the layout this corpus runs — the positive control
/// caught it as `ImportError: attempted relative import with no known parent package`. This is
/// a mechanical consequence of the flatten decision, not a new one.
fn flatten_relative_imports(text: &str) -> String {
    let mut out = String::with_capacity(text.len());
    let mut rest = text;
    while let Some(i) = rest.find("from .") {
        let after = &rest[i + 6..];
        let keeps_dot = !after
            .chars()
            .next()
            .is_some_and(|c| c.is_ascii_alphanumeric() || c == '_');
        out.push_str(&rest[..i]);
        out.push_str(if keeps_dot { "from ." } else { "from " });
        rest = &rest[i + 6..];
    }
    out.push_str(rest);
    out
}

/// Flat filenames a dictated artifact body reaches for — as opposed to what the *verifier*
/// reaches for. Both matter, and only looking at the verifier misses the case where the
/// artifact itself imports a module another donor task was supposed to create.
fn body_deps(body: &str, lang: VerifyLang) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut push = |s: String| {
        if !out.contains(&s) {
            out.push(s);
        }
    };
    match lang {
        VerifyLang::Python => {
            for line in body.lines() {
                let l = line.trim_start();
                if let Some(r) = l.strip_prefix("from ") {
                    let name: String = r
                        .trim_start_matches('.')
                        .chars()
                        .take_while(|c| c.is_ascii_alphanumeric() || *c == '_')
                        .collect();
                    if !name.is_empty() {
                        push(format!("{name}.py"));
                    }
                }
            }
        }
        VerifyLang::Node => {
            let mut i = 0;
            while let Some(rel) = body[i..].find("require('./") {
                let at = i + rel + 11;
                i = at;
                if let Some(end) = body[at..].find('\'') {
                    let n = &body[at..at + end];
                    push(if n.ends_with(".js") {
                        n.to_string()
                    } else {
                        format!("{n}.js")
                    });
                }
            }
        }
    }
    out
}

/// Everything the verifier reaches for, as flat work-dir filenames.
fn verifier_targets(validation: &str, lang: VerifyLang) -> Vec<String> {
    let mut out: Vec<String> = Vec::new();
    let mut push = |s: String| {
        if !s.is_empty() && !out.contains(&s) {
            out.push(s);
        }
    };
    match lang {
        VerifyLang::Python => {
            // `from tasks.<dir>.<mod> import` -> <mod>.py
            let mut i = 0;
            while let Some(rel) = validation[i..].find("from ") {
                let at = i + rel + 5;
                i = at;
                let b = validation.as_bytes();
                let mut j = at;
                while j < b.len() && is_mod_byte(b[j]) {
                    j += 1;
                }
                let tok = validation[at..j].trim_end_matches('.');
                if let Some(last) = tok.rsplit('.').next() {
                    if tok.starts_with("tasks.") {
                        push(format!("{last}.py"));
                    }
                }
            }
            // `open('<path>'` -> basename
            let mut i = 0;
            while let Some(rel) = validation[i..].find("open('") {
                let at = i + rel + 6;
                i = at;
                if let Some(end) = validation[at..].find('\'') {
                    let p = &validation[at..at + end];
                    push(basename(&p.replace("/app/workspace/", "")));
                }
            }
        }
        VerifyLang::Node => {
            let mut i = 0;
            while let Some(rel) = validation[i..].find("require('") {
                let at = i + rel + 9;
                i = at;
                if let Some(end) = validation[at..].find('\'') {
                    let p = &validation[at..at + end];
                    let flat = basename(&p.replace("/app/workspace/", ""));
                    if flat.starts_with('.') || flat.is_empty() {
                        continue; // a bare node builtin, e.g. require('fs')
                    }
                    // Only paths the donor points into its own tree are artifacts.
                    if p.contains("tasks/") {
                        push(if flat.ends_with(".js") {
                            flat
                        } else {
                            format!("{flat}.js")
                        });
                    }
                }
            }
        }
    }
    out
}

/// The artifact: the file the prompt tells the agent to create, or to read and fix.
fn artifact_of(desc: &str) -> Option<String> {
    for pat in ["file_write to create ", "file_write to save "] {
        if let Some(i) = desc.find(pat) {
            let rest = &desc[i + pat.len()..];
            let b = rest.as_bytes();
            let mut j = 0;
            while j < b.len() && is_path_byte(b[j]) {
                j += 1;
            }
            let tok = rest[..j].trim_end_matches(['.', '/']);
            if tok.starts_with("tasks/") {
                return Some(tok.to_string());
            }
        }
    }
    if let Some(i) = desc.find("Read the file ") {
        let rest = &desc[i + 14..];
        let b = rest.as_bytes();
        let mut j = 0;
        while j < b.len() && is_path_byte(b[j]) {
            j += 1;
        }
        let tok = rest[..j].trim_end_matches(['.', '/']);
        if !tok.is_empty() {
            return Some(tok.to_string());
        }
    }
    None
}

/// The body the donor's prompt dictates verbatim, for the 60 tasks that spell out the whole
/// file. Used only to reconstruct a cross-task dependency, never as a fixture for the task's
/// own artifact — that would hand the subject the answer.
fn dictated_body(desc: &str) -> Option<String> {
    let i = desc.find("with this content:\n")? + 19;
    let rest = &desc[i..];
    let end = ["\n\nStep ", "\n\nDO NOT"]
        .iter()
        .filter_map(|m| rest.find(m))
        .min()
        .unwrap_or(rest.len());
    let body = rest[..end].trim_end();
    if body.is_empty() {
        None
    } else {
        Some(format!("{body}\n"))
    }
}

/// SPEC §3's `lang` vocabulary, from the artifact's extension.
///
/// This is the artifact's language, not the verifier's: 25 tasks produce html/css/jsx while
/// their verifier is python (it opens the file and string-matches it), so the donor's
/// `validationLang` is the wrong field to read. `.css` maps to `html` because the vocabulary
/// has no `css` and a stylesheet is a web-page asset; recorded in the suite caveats.
fn lang_of(artifact: &str) -> &'static str {
    match artifact.rsplit('.').next().unwrap_or("") {
        "py" => "python",
        "js" | "jsx" => "node",
        "ts" | "tsx" => "typescript",
        "go" => "go",
        "html" | "css" => "html",
        _ => "mixed",
    }
}

fn classify(validation: Option<&String>) -> VClass {
    let Some(v) = validation else {
        return VClass::None;
    };
    // Same test as rank.py: does the verifier reach the artifact as code?
    for needle in [
        "from tasks.",
        "__import__",
        "subprocess",
        "exec(",
        "importlib",
        "require(",
    ] {
        if v.contains(needle) {
            return VClass::Exec;
        }
    }
    VClass::StrMatch
}

// ---------------------------------------------------------------------------------------------
// The prompt rewrite
// ---------------------------------------------------------------------------------------------

/// Two edits, both semantic, both recorded. There is no third.
///
/// 1. **The tool name.** All 90 donor prompts name `file_write`, a tool from ABCC's registry.
///    Claudette at `fc1ea22` exposes `read_file` / `write_file` / `list_dir` / `apply_diff` /
///    `edit_file` / `bash` (`tools/file_ops.rs:48-65`, `tools/shell.rs:75-89`,
///    `tools/fuzzy_apply.rs:47`), so `file_write` -> `write_file` is a 1:1 rename onto a tool
///    with the same contract. Left in, the prompt instructs the subject to call a tool that
///    does not exist. The ten `fix_*` prompts end by asking for the fixed file to be *saved*,
///    which is an edit rather than a create, so they take the worked example's wording instead.
/// 2. **The paths.** `tasks/<dir>/<file>` is a path inside ABCC's container layout; it becomes
///    the basename, relative to the work dir.
fn rewrite_prompt(desc: &str, caveats: &mut Vec<String>) -> String {
    let mut p = desc.to_string();

    let fix_tail = "Use file_write to save the fixed version.";
    if p.contains(fix_tail) {
        p = p.replace(fix_tail, "Edit the file to fix it.");
        caveats.push(format!(
            "PROMPT REWRITE, and the largest single threat to comparability in the whole \
             import: '{fix_tail}' names a tool from ABCC's registry. Claudette has \
             edit_file / apply_diff / write_file, so left in, the prompt instructs the subject \
             to call a tool that does not exist. Rewritten to 'Edit the file to fix it.' \
             This is a semantic edit to a donor prompt"
        ));
    }
    if p.contains("file_write") {
        p = p.replace("file_write", "write_file");
        caveats.push(
            "PROMPT REWRITE: every donor prompt names ABCC's `file_write` tool, which does not \
             exist in Claudette. Renamed to `write_file`, which is the same contract (path + \
             content) at tools/file_ops.rs:65. A 1:1 tool rename, but still an edit to a donor \
             prompt"
                .to_string(),
        );
    }

    let before_rel = p.clone();
    p = flatten_relative_imports(&p);
    if p != before_rel {
        caveats.push(
            "PROMPT REWRITE: the dictated body used relative imports (`from .router import`), \
             which need a package. The flattened work dir is not one, so the prompt would have \
             instructed the subject to write a file that cannot import — the positive control \
             caught exactly that, as `ImportError: attempted relative import with no known \
             parent package`. Made absolute. A mechanical consequence of the flatten rewrite \
             rather than a separate decision"
                .to_string(),
        );
    }

    let before = p.clone();
    p = flatten_paths(&p);
    if p != before {
        caveats.push(
            "PROMPT REWRITE: `tasks/<dir>/<file>` is a path inside ABCC's container layout. \
             Flattened to the basename, relative to the work dir. Safe as a blanket rule \
             because all 107 donor paths sit at one directory of depth and flattening the \
             basenames collides in zero of the 90 tasks"
                .to_string(),
        );
    }
    p
}

// ---------------------------------------------------------------------------------------------
// Building a task
// ---------------------------------------------------------------------------------------------

pub fn build(donor: &DonorTask, buggy: &BTreeMap<String, String>, siblings: &[DonorTask]) -> Task {
    let mut caveats: Vec<String> = Vec::new();
    let vclass = classify(donor.validation.as_ref());

    let artifact_donor = artifact_of(&donor.description).unwrap_or_else(|| {
        panic!(
            "task {}: no artifact path in the prompt; the importer cannot guess one",
            donor.name
        )
    });
    let artifact = basename(&artifact_donor);
    let prompt = rewrite_prompt(&donor.description, &mut caveats);

    let vlang = if donor.validation_lang == "node" {
        VerifyLang::Node
    } else {
        VerifyLang::Python
    };

    // The body the donor's own prompt dictates, under the flat layout this corpus runs.
    let dictated = dictated_body(&donor.description).map(|b| flatten_relative_imports(&b));

    let mut fixture: BTreeMap<String, String> = BTreeMap::new();
    let mut fixture_is_donor = false;

    // Section 4B ships a real buggy fixture: the file the subject has to fix.
    if let Some(body) = buggy.get(&artifact) {
        fixture.insert(artifact.clone(), body.clone());
        fixture_is_donor = true;
    }

    // Cross-task dependencies. Measured, not anticipated: two verifiers reach a module that a
    // *different* donor task was supposed to create, because the donor shared one cumulative
    // workspace across all 100 tasks (F7). Under v1's per-task isolation that module is simply
    // absent, so the verifier raises before reaching any assertion no matter what the subject
    // did — and it raises into a FAIL, which is the verdict a sound verifier gives, so the
    // task would have looked fine while measuring nothing.
    // Two sources, because looking at only one misses real cases: what the *verifier* reaches
    // for, and what the *artifact itself* imports. `py_server_main` has four dependencies that
    // appear nowhere in its verifier — its own dictated body imports them — and the positive
    // control is what surfaced that.
    let mut queue: Vec<String> = Vec::new();
    if let Some(v) = donor.validation.as_ref() {
        queue.extend(verifier_targets(v, vlang));
    }
    if let Some(b) = &dictated {
        queue.extend(body_deps(b, vlang));
    }

    // The artifact is seeded as already-seen so that a task's own dictated body can never be
    // written into its fixture. That would hand the subject the answer.
    let mut seen: Vec<String> = vec![artifact.clone()];
    let mut deps: Vec<String> = Vec::new();
    let mut cursor = 0;
    while cursor < queue.len() {
        let target = queue[cursor].clone();
        cursor += 1;
        if seen.contains(&target) {
            continue;
        }
        seen.push(target.clone());
        // Only a sibling task's artifact can be a dependency. A stdlib name (`json.py`) simply
        // resolves to no sibling and is not one.
        let Some(sib) = siblings.iter().find(|s| {
            artifact_of(&s.description)
                .map(|a| basename(&a) == target)
                .unwrap_or(false)
        }) else {
            continue;
        };
        deps.push(target.clone());
        match dictated_body(&sib.description) {
            Some(body) => {
                let body = flatten_relative_imports(&body);
                queue.extend(body_deps(&body, vlang));
                fixture.insert(target.clone(), body);
                caveats.push(format!(
                    "SYNTHESIZED FIXTURE `{target}`: this task reaches a module the donor task \
                     `{}` was supposed to create in the shared workspace (F7). Under per-task \
                     isolation it would be absent, the verifier would raise before any \
                     assertion, and the task would score FAIL regardless of the subject's work \
                     — a FAIL that reads exactly like a sound verifier rejecting a wrong \
                     answer. Reconstructed from that task's prompt, which dictates its whole \
                     body verbatim, so this restores the state the donor actually ran in rather \
                     than inventing one",
                    sib.name
                ));
            }
            None => caveats.push(format!(
                "UNRESOLVED DEPENDENCY: this task reaches `{target}`, which is neither its own \
                 artifact nor reconstructible from a sibling prompt. Imported anyway; the gate \
                 evidence records what the verifier actually did"
            )),
        }
    }
    deps.sort();

    let verify = donor.validation.as_ref().map(|v| {
        let body = rewrite_verifier_body(&donor.name, v, vlang, &mut caveats);
        let script = match vlang {
            VerifyLang::Python => verify_sh::python(&donor.name, &body, &artifact),
            VerifyLang::Node => verify_sh::node(&donor.name, &body),
        };
        Verify {
            lang: vlang,
            body,
            script,
        }
    });

    if verify.is_none() {
        caveats.push(
            "NO VERIFIER: the donor wrote `validation: null` and the runner fell back to \
             `passed = execSuccess`, the agent-execution endpoint's own success flag \
             (ultimate-100-task-test.js:3168). These tasks still counted toward the 95/100 \
             headline. The prompt also contains the finished file body. F13"
                .to_string(),
        );
    }

    let is_fix = artifact_donor.contains("security_fixes");
    Task {
        id: donor.name.clone(),
        title: format!("{} {artifact}", if is_fix { "fix" } else { "create" }),
        lang: lang_of(&artifact),
        kind: donor.category.clone(),
        timeout_s: TIMEOUT_S,
        vclass,
        artifact_donor,
        artifact,
        prompt,
        verify,
        fixture,
        deps,
        gate3_rank: GATE3.iter().position(|n| *n == donor.name).map(|i| i + 1),
        dictated,
        caveats,
        donor: donor.clone(),
        fixture_is_donor,
    }
}

/// The three verifier rewrites of SPEC §8, and one task-specific fourth.
fn rewrite_verifier_body(
    name: &str,
    validation: &str,
    lang: VerifyLang,
    caveats: &mut Vec<String>,
) -> String {
    let mut body = validation.to_string();

    const PREAMBLE: &str = "import sys; sys.path.insert(0,'/app/workspace'); ";
    if let Some(stripped) = body.strip_prefix(PREAMBLE) {
        body = stripped.to_string();
    }

    // The donor's verdict channel: `exit 0 AND "PASS" in stdout`. For python the trailing print
    // is replaced by the RESULT: contract; for node it is left in place and scored in the shell,
    // because those verifiers reject by calling process.exit(1) rather than by throwing, so an
    // in-process try/catch would never see a rejection.
    if lang == VerifyLang::Python {
        for tail in ["; print('PASS')", "\nprint('PASS')", "print('PASS')"] {
            if let Some(stripped) = body.strip_suffix(tail) {
                body = stripped.trim_end().to_string();
                break;
            }
        }
    }

    body = flatten_py_modules(&body);
    body = flatten_paths(&body);

    // fix_path_traversal is the only verifier naming absolute filesystem paths outside the
    // workspace: it probes a base dir of '/tmp' and reaches out of it for /etc/passwd. Both
    // move inside the work dir, and verify.sh creates them.
    if body.contains("'/tmp'") {
        assert_eq!(
            name, "fix_path_traversal",
            "a second verifier names an absolute container path. verify.sh's containment setup \
             is task-specific and would have to be extended before this task could be imported"
        );
        body = body.replace("'/tmp'", "'base'");
        caveats.push(
            "VERIFIER REWRITE, task-specific: the donor probes a base dir of '/tmp' and reaches \
             out of it for '../etc/passwd', two absolute container paths. The base becomes \
             `base/` inside the work dir and verify.sh creates `base/` and `etc/passwd` there. \
             Without this the verifier measures the host filesystem instead of the artifact"
                .to_string(),
        );
    }

    caveats.push(format!(
        "VERIFIER REWRITE, three ways: the donor snippet is base64'd and run as `docker exec -w \
         /app/workspace abcc-agents {} -c ...` (ultimate-100-task-test.js:2805-2806). Absolute \
         /app/workspace paths become the work dir, the docker exec execution model is dropped, \
         and the donor's `result.includes('PASS')` plus catch-all `return false` (:2809-2813) \
         map onto RESULT: PASS|FAIL|INVALID. The assertion body itself is reproduced UNCHANGED \
         and executed rather than reformatted, defects and all, because faithfulness to the \
         donor is the point of an import",
        if lang == VerifyLang::Node { "node" } else { "python3" }
    ));
    caveats.push(
        "both donor validation paths run the same verifier string and score `exit 0 AND PASS in \
         stdout` — local runValidationLocal (:2788-2814) and server /run-validation \
         (packages/agents/src/main.py:524-589, the path the recorded runs actually used). There \
         is no second copy to reconcile"
            .to_string(),
    );
    body
}

// ---------------------------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn flattens_container_paths() {
        assert_eq!(
            flatten_paths("open('/app/workspace/tasks/saas_landing/pricing.html')"),
            "open('pricing.html')"
        );
        assert_eq!(
            flatten_paths("require('./tasks/node_api_server/router')"),
            "require('./router')"
        );
        assert_eq!(
            flatten_paths("create tasks/py_api_server/todo_model.py with"),
            "create todo_model.py with"
        );
    }

    #[test]
    fn flattens_dotted_python_modules() {
        assert_eq!(
            flatten_py_modules("from tasks.security_fixes.sql_inject import get_user"),
            "from sql_inject import get_user"
        );
        // A dotted name that is not the donor's tree is left alone.
        assert_eq!(
            flatten_py_modules("import json.decoder"),
            "import json.decoder"
        );
    }

    #[test]
    fn finds_the_artifact_in_both_prompt_shapes() {
        assert_eq!(
            artifact_of("Step 1: Use file_write to create tasks/py_api_server/x.py with this")
                .unwrap(),
            "tasks/py_api_server/x.py"
        );
        assert_eq!(
            artifact_of("SECURITY FIX: Read the file tasks/security_fixes/sql_inject.py which")
                .unwrap(),
            "tasks/security_fixes/sql_inject.py"
        );
    }

    #[test]
    fn prompt_rewrite_reproduces_the_worked_example() {
        let donor = "SECURITY FIX: Read the file tasks/security_fixes/sql_inject.py which has a \
                     SQL injection vulnerability (f-string query interpolation). Fix it by using \
                     parameterized queries. The function get_user(db, username) should return a \
                     dict with 'query' and 'params' keys instead of calling db.execute directly. \
                     Use file_write to save the fixed version.";
        let mut c = Vec::new();
        let got = rewrite_prompt(donor, &mut c);
        assert!(got.ends_with("Edit the file to fix it."));
        assert!(got.contains("Read the file sql_inject.py which"));
        assert!(
            !got.contains("file_write"),
            "no emitted prompt may name a tool Claudette does not have"
        );
        assert!(!got.contains("tasks/"), "container paths must be gone");
    }

    #[test]
    fn create_prompts_get_the_one_to_one_tool_rename() {
        let donor = "IMPORTANT: You MUST use the file_write tool to create the file.\n\n\
                     Step 1: Use file_write to create tasks/react_taskmanager/utils.js with this \
                     content:\nvar a = 1;\n\nDO NOT just output the code - you MUST call \
                     file_write.";
        let mut c = Vec::new();
        let got = rewrite_prompt(donor, &mut c);
        assert!(!got.contains("file_write"));
        assert_eq!(got.matches("write_file").count(), 3);
        assert!(got.contains("create utils.js with this content"));
    }

    #[test]
    fn classifies_the_three_verifier_kinds() {
        assert_eq!(classify(None), VClass::None);
        assert_eq!(
            classify(Some(&"from tasks.a.b import c".to_string())),
            VClass::Exec
        );
        assert_eq!(
            classify(Some(&"var x=require('./tasks/a/b')".to_string())),
            VClass::Exec
        );
        assert_eq!(
            classify(Some(&"h=open('x.html').read(); assert 'a' in h".to_string())),
            VClass::StrMatch
        );
    }

    #[test]
    fn verifier_targets_separate_artifact_from_dependency() {
        let v = "import sys; sys.path.insert(0,'/app/workspace'); \
                 from tasks.py_api_server.todo_model import TodoStore; \
                 from tasks.py_api_server.todo_handlers import handle_list; print('PASS')";
        let t = verifier_targets(v, VerifyLang::Python);
        assert_eq!(t, vec!["todo_model.py", "todo_handlers.py"]);
    }

    #[test]
    fn dictated_body_stops_before_the_prompt_boilerplate() {
        let d = "IMPORTANT: You MUST use the file_write tool to create the file.\n\n\
                 Step 1: Use file_write to create tasks/x/y.py with this content:\n\
                 class A:\n    pass\n\n\
                 DO NOT just output the code - you MUST call file_write.";
        assert_eq!(dictated_body(d).unwrap(), "class A:\n    pass\n");
    }

    #[test]
    fn lang_comes_from_the_artifact_not_the_verifier() {
        assert_eq!(lang_of("sql_inject.py"), "python");
        assert_eq!(lang_of("utils.js"), "node");
        assert_eq!(lang_of("TaskItem.jsx"), "node");
        assert_eq!(lang_of("index.html"), "html");
        assert_eq!(lang_of("style.css"), "html");
        assert_eq!(lang_of("result.ts"), "typescript");
        assert_eq!(lang_of("slug.go"), "go");
    }

    #[test]
    fn gate3_is_the_approved_thirty_with_fix_sql_inject_at_nine() {
        assert_eq!(GATE3.len(), 30);
        assert_eq!(
            GATE3.iter().position(|n| *n == "fix_sql_inject").unwrap() + 1,
            9,
            "the worked example records gate3_rank = 9"
        );
        // R9 put ts_pipe out of the set.
        assert!(!GATE3.contains(&"ts_pipe"));
    }

    #[test]
    fn python_body_loses_the_preamble_and_the_pass_print() {
        let mut c = Vec::new();
        let got = rewrite_verifier_body(
            "demo",
            "import sys; sys.path.insert(0,'/app/workspace'); from tasks.a.b import f; \
             assert f(); print('PASS')",
            VerifyLang::Python,
            &mut c,
        );
        assert_eq!(got, "from b import f; assert f()");
        assert!(!got.contains("/app/workspace"));
    }

    #[test]
    fn node_body_keeps_its_own_pass_print() {
        let mut c = Vec::new();
        let got = rewrite_verifier_body(
            "demo",
            "var u=require('./tasks/a/b'); if(!u.f()) process.exit(1); console.log('PASS')",
            VerifyLang::Node,
            &mut c,
        );
        assert!(
            got.ends_with("console.log('PASS')"),
            "node is scored in the shell on the donor's own contract"
        );
        assert!(got.contains("require('./b')"));
    }
}
