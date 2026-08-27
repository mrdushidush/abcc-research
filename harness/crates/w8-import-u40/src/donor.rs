//! Stage 1 — read the donor and take it apart.
//!
//! The donor is one flat `const TASKS = [ … ];` of 40 object literals with five keys each, so the
//! multi-line-template-literal byte-walker in `w8-import/src/donor.rs` is not needed and is not
//! reused: bending a walker built for `ultimate-100-task-test.js` around a strictly simpler file
//! would make both harder to read. What IS reused is its discipline — a string- and comment-aware
//! scan rather than a line regex, because `code:` values contain `{`, `}` and `//` inside strings
//! (`f'Hello, {name}!'`, `token in '+-*/'`).
//!
//! 🚨 The field this importer sends to the model is `description`, **not** the `fullDescription`
//! that `createTask` (`ollama-stress-test-40.js:372-380`) builds. That one interpolates
//! `task.code` — the reference solution — into the prompt, but it is posted to the task DB record
//! and never reaches the model: `executeTask(:412)` sends `task.description`, and the agents
//! service uses `request.task_description` verbatim (`packages/agents/src/main.py:325`). The
//! 17 tasks whose two paths disagree are the independent proof — see `path_disagreements`.

use std::collections::BTreeSet;
use std::process::Command;

#[derive(Debug, Clone)]
pub struct DonorTask {
    pub complexity: u8,
    /// The donor's own `name` key. Not the id: 17 of 40 disagree with the artifact path.
    pub name: String,
    /// The prompt the model actually received, verbatim.
    pub description: String,
    /// The reference solution. NEVER emitted into `prompt.txt`; it is the answer key and the
    /// refsol tier of the gate.
    pub code: String,
    /// The assertion body, executed unchanged.
    pub validation: String,
    /// `tasks/c5_flatten.py`, parsed out of `description`.
    pub artifact: String,
    /// `c5_flatten` — the artifact's stem, the module the verifier imports, and the task id.
    pub id: String,
    /// `c5_flatten_list` — the stem `createTask` would have named. Recorded, never used.
    pub db_stem: String,
    /// The names the verifier imports out of the module.
    pub symbols: Vec<String>,
}

/// One task's line in a recorded donor run.
#[derive(Debug, Clone)]
pub struct Recorded {
    pub status: String,
    pub duration_s: u32,
}

pub fn read_donor(repo: &str, commit: &str, path: &str) -> Result<String, String> {
    let out = Command::new("git")
        .arg("-C")
        .arg(repo)
        .arg("show")
        .arg(format!("{commit}:{path}"))
        .output()
        .map_err(|e| format!("git show {commit}:{path}: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "git show {commit}:{path} failed: {}",
            String::from_utf8_lossy(&out.stderr).trim()
        ));
    }
    // CRLF normalised on read, as `w8-import/src/donor.rs` does: the 100-task donor was entirely
    // CRLF and it silently emptied two fixtures before anyone noticed.
    Ok(String::from_utf8_lossy(&out.stdout).replace("\r\n", "\n"))
}

// ---------------------------------------------------------------------------------------------
// The scanner
// ---------------------------------------------------------------------------------------------

/// Walk `src` from `start`, returning the byte ranges of the top-level `{ … }` objects inside the
/// array that opens there. String- and comment-aware, so a brace inside `f'Hello, {name}!'` or a
/// `//` inside `'+-*/'` cannot move the depth.
fn object_ranges(src: &str, start: usize) -> Result<Vec<(usize, usize)>, String> {
    let b = src.as_bytes();
    let mut i = start;
    let mut depth = 0usize;
    let mut obj_start = 0usize;
    let mut out = Vec::new();
    let mut array_open = false;

    while i < b.len() {
        let c = b[i];
        match c {
            b'/' if i + 1 < b.len() && b[i + 1] == b'/' => {
                while i < b.len() && b[i] != b'\n' {
                    i += 1;
                }
            }
            b'/' if i + 1 < b.len() && b[i + 1] == b'*' => {
                i += 2;
                while i + 1 < b.len() && !(b[i] == b'*' && b[i + 1] == b'/') {
                    i += 1;
                }
                i += 2;
            }
            b'"' | b'\'' | b'`' => {
                let quote = c;
                i += 1;
                while i < b.len() {
                    if b[i] == b'\\' {
                        i += 2;
                        continue;
                    }
                    if b[i] == quote {
                        break;
                    }
                    i += 1;
                }
                i += 1;
            }
            b'[' if !array_open => {
                array_open = true;
                i += 1;
            }
            b']' if array_open && depth == 0 => return Ok(out),
            b'{' => {
                if depth == 0 {
                    obj_start = i;
                }
                depth += 1;
                i += 1;
            }
            b'}' => {
                depth = depth
                    .checked_sub(1)
                    .ok_or_else(|| format!("unbalanced `}}` at byte {i}"))?;
                if depth == 0 {
                    out.push((obj_start, i + 1));
                }
                i += 1;
            }
            _ => i += 1,
        }
    }
    Err("reached end of file before the TASKS array closed".to_string())
}

/// Read `key: <value>` out of one object literal. Values here are either a bare integer or a
/// double-quoted string; anything else is a donor shape this importer does not claim to handle,
/// and it says so rather than guessing.
fn field(obj: &str, key: &str) -> Result<String, String> {
    let pat = format!("{key}:");
    let mut from = 0usize;
    let at = loop {
        let rel = obj[from..]
            .find(&pat)
            .ok_or_else(|| format!("no `{key}:` in object literal"))?;
        let abs = from + rel;
        // A key is preceded by `{`, `,` or whitespace — never by an identifier character, so
        // `complexity:` cannot match inside `task.complexity:`.
        let ok = obj[..abs]
            .chars()
            .next_back()
            .is_none_or(|p| !p.is_alphanumeric() && p != '_' && p != '.');
        if ok {
            break abs + pat.len();
        }
        from = abs + pat.len();
    };
    let rest = obj[at..].trim_start();
    if let Some(body) = rest.strip_prefix('"') {
        let bytes = body.as_bytes();
        let mut i = 0usize;
        while i < bytes.len() {
            match bytes[i] {
                b'\\' => i += 2,
                b'"' => return unescape_js(&body[..i]),
                _ => i += 1,
            }
        }
        return Err(format!("`{key}:` string is not terminated"));
    }
    let end = rest
        .find([',', '\n', '}'])
        .ok_or_else(|| format!("`{key}:` value is not terminated"))?;
    Ok(rest[..end].trim().to_string())
}

/// The subset of JavaScript string escapes this donor uses, plus the ones that would silently
/// corrupt a value if they appeared: an unknown escape is an error, never a passed-through
/// backslash.
fn unescape_js(s: &str) -> Result<String, String> {
    let mut out = String::with_capacity(s.len());
    let mut it = s.chars();
    while let Some(c) = it.next() {
        if c != '\\' {
            out.push(c);
            continue;
        }
        match it.next().ok_or("string ends in a lone backslash")? {
            'n' => out.push('\n'),
            't' => out.push('\t'),
            'r' => out.push('\r'),
            '0' => out.push('\0'),
            '\\' => out.push('\\'),
            '\'' => out.push('\''),
            '"' => out.push('"'),
            '`' => out.push('`'),
            'u' => {
                let hex: String = it.by_ref().take(4).collect();
                let n = u32::from_str_radix(&hex, 16).map_err(|_| format!("bad \\u{hex}"))?;
                out.push(char::from_u32(n).ok_or_else(|| format!("bad \\u{hex}"))?);
            }
            other => return Err(format!("unhandled escape \\{other}")),
        }
    }
    Ok(out)
}

// ---------------------------------------------------------------------------------------------
// Parse
// ---------------------------------------------------------------------------------------------

pub fn parse(src: &str, expected: usize) -> Result<Vec<DonorTask>, String> {
    let start = src
        .find("const TASKS = [")
        .ok_or("no `const TASKS = [` in the donor")?;
    let ranges = object_ranges(src, start + "const TASKS =".len())?;
    let mut tasks = Vec::with_capacity(ranges.len());
    for (a, b) in ranges {
        let obj = &src[a..b];
        let complexity: u8 = field(obj, "complexity")?
            .parse()
            .map_err(|e| format!("complexity: {e}"))?;
        let name = field(obj, "name")?;
        let description = field(obj, "description")?;
        let code = field(obj, "code")?;
        let validation = field(obj, "validation")?;

        let artifact = artifact_of(&description)
            .ok_or_else(|| format!("{name}: no `tasks/<file>.py` in the description"))?;
        let id = artifact
            .rsplit('/')
            .next()
            .unwrap_or_default()
            .trim_end_matches(".py")
            .to_string();
        let (module, symbols) = import_of(&validation)
            .ok_or_else(|| format!("{name}: no `from tasks.<mod> import …` in the validation"))?;
        if module != format!("tasks.{id}") {
            return Err(format!(
                "{name}: the prompt names `{artifact}` and the verifier imports `{module}`; \
                 an import cannot reconcile those two and must not try"
            ));
        }
        // The verifier is executed inside a `r'''…'''` literal (see `verify_sh`), so these two
        // shapes would change its meaning. Neither occurs in the donor; the check is here so a
        // future donor edit fails loudly rather than emitting a verifier that lies.
        if validation.contains("'''") || validation.ends_with('\'') || validation.ends_with('\\') {
            return Err(format!("{name}: validation cannot be carried in a raw triple-quote"));
        }
        tasks.push(DonorTask {
            complexity,
            db_stem: format!("c{complexity}_{name}"),
            name,
            description,
            code,
            validation,
            artifact,
            id,
            symbols,
        });
    }

    if tasks.len() != expected {
        return Err(format!(
            "found {} task objects, expected {expected}. The count is the boundary of this \
             suite, so an import that found something else imports nothing",
            tasks.len()
        ));
    }
    let ids: BTreeSet<&str> = tasks.iter().map(|t| t.id.as_str()).collect();
    if ids.len() != tasks.len() {
        return Err("two tasks derive the same id from their artifact path".to_string());
    }
    Ok(tasks)
}

fn artifact_of(description: &str) -> Option<String> {
    let at = description.find("tasks/")?;
    let rest = &description[at..];
    let end = rest.find(".py")? + ".py".len();
    Some(rest[..end].to_string())
}

fn import_of(validation: &str) -> Option<(String, Vec<String>)> {
    let at = validation.find("from ")?;
    let rest = &validation[at + "from ".len()..];
    let sp = rest.find(" import ")?;
    let module = rest[..sp].trim().to_string();
    let tail = &rest[sp + " import ".len()..];
    let end = tail.find(';').unwrap_or(tail.len());
    let symbols = tail[..end]
        .split(',')
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .collect();
    Some((module, symbols))
}

/// The 17 tasks whose DB-record stem (`c{complexity}_{name}`) is not the stem the prompt and the
/// verifier agree on. Each one would have written a file the verifier never imports, so their
/// existence is what proves `fullDescription` never reached the model.
pub fn path_disagreements(tasks: &[DonorTask]) -> Vec<&DonorTask> {
    tasks.iter().filter(|t| t.db_stem != t.id).collect()
}

// ---------------------------------------------------------------------------------------------
// The recorded baselines
// ---------------------------------------------------------------------------------------------

/// Scan one `ollama-stress-results-40.json` `details` array. The shape is fixed and machine-
/// written by the donor itself (`:571-576`), so a scanner is honest here; a JSON dependency
/// would be the only third-party crate in three importers.
pub fn parse_results(src: &str) -> Result<Vec<(String, Recorded)>, String> {
    let mut out = Vec::new();
    let at = src.find("\"details\"").ok_or("no `details` in the results JSON")?;
    let mut rest = &src[at..];
    while let Some(t) = rest.find("\"task\":") {
        rest = &rest[t + "\"task\":".len()..];
        let q = rest.find('"').ok_or("malformed details entry")?;
        let end = rest[q + 1..].find('"').ok_or("malformed details entry")? + q + 1;
        let task = rest[q + 1..end].to_string();
        let status = json_string_after(rest, "\"status\":").ok_or("no status")?;
        let duration_s = json_number_after(rest, "\"duration\":").unwrap_or(0);
        out.push((task, Recorded { status, duration_s }));
        rest = &rest[end..];
    }
    if out.is_empty() {
        return Err("the results JSON has no task entries".to_string());
    }
    Ok(out)
}

fn json_string_after(src: &str, key: &str) -> Option<String> {
    let at = src.find(key)? + key.len();
    let rest = &src[at..];
    let q = rest.find('"')?;
    let end = rest[q + 1..].find('"')? + q + 1;
    Some(rest[q + 1..end].to_string())
}

fn json_number_after(src: &str, key: &str) -> Option<u32> {
    let at = src.find(key)? + key.len();
    let rest = src[at..].trim_start();
    let end = rest.find(|c: char| !c.is_ascii_digit()).unwrap_or(rest.len());
    rest[..end].parse().ok()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_brace_inside_a_string_does_not_move_the_depth() {
        let src = "const TASKS = [\n{ complexity: 2, name: \"greet\", \
                   description: \"Create tasks/c2_greet.py with a greeting\", \
                   code: \"def greet(name):\\n    return f'Hello, {name}!'\", \
                   validation: \"from tasks.c2_greet import greet; print('PASS')\" }\n];";
        let t = parse(src, 1).expect("parses");
        assert_eq!(t[0].id, "c2_greet");
        assert_eq!(t[0].artifact, "tasks/c2_greet.py");
        assert_eq!(t[0].symbols, vec!["greet"]);
        assert!(t[0].code.contains("{name}"));
    }

    #[test]
    fn a_comment_marker_inside_a_string_is_not_a_comment() {
        let src = "const TASKS = [\n{ complexity: 9, name: \"rpn\", \
                   description: \"Create tasks/c9_rpn.py with rpn_calc\", \
                   code: \"if token in '+-*/':\\n    pass\", \
                   validation: \"from tasks.c9_rpn import rpn_calc; print('PASS')\" }\n];";
        let t = parse(src, 1).expect("parses");
        assert_eq!(t[0].code, "if token in '+-*/':\n    pass");
    }

    #[test]
    fn a_prompt_and_a_verifier_that_disagree_abort_the_import() {
        let src = "const TASKS = [\n{ complexity: 1, name: \"x\", \
                   description: \"Create tasks/c1_a.py\", code: \"pass\", \
                   validation: \"from tasks.c1_b import a; print('PASS')\" }\n];";
        assert!(parse(src, 1).is_err());
    }

    #[test]
    fn the_count_is_the_boundary() {
        let src = "const TASKS = [\n{ complexity: 1, name: \"x\", \
                   description: \"Create tasks/c1_a.py\", code: \"pass\", \
                   validation: \"from tasks.c1_a import a; print('PASS')\" }\n];";
        assert!(parse(src, 40).is_err());
    }
}
