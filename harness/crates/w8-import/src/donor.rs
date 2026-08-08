//! Stage 1 — extract. Reads the donor's `scripts/ultimate-100-task-test.js` and pulls out the
//! task objects and the `BUGGY_FILES` map.
//!
//! Why a string walker and not a pattern match: `validation` is a template literal that spans
//! lines for some tasks and contains quote characters, so the field has to be scanned with
//! something that tracks delimiters. This is a port of the throwaway spike's
//! `extract_tasks.py`, which is the code that found F21.
//!
//! The scanners work on bytes. That is safe for UTF-8 input because every delimiter they stop
//! on is ASCII, and UTF-8 continuation bytes are all >= 0x80, so no index can land inside a
//! multi-byte character.

use std::collections::BTreeMap;
use std::path::Path;

/// Read the donor source and normalise its line endings to LF.
///
/// **The donor file is entirely CRLF** — measured: 3,521 `\r\n` and zero bare `\n`. Every
/// multi-line template literal in it therefore carries `\r\n`, and normalising is not cosmetic:
///
///   * `dictated_body` looks for `"with this content:\n"`, which never matches under CRLF, so
///     the two cross-task dependency fixtures came out **empty**. Their verifiers then crashed
///     on the missing module before reaching any assertion — and a crash is a FAIL, which is
///     the verdict a *sound* verifier gives. Gate point 1 read `sound` for two tasks that had
///     measured nothing at all. Silent, and flattering.
///   * every emitted `prompt.txt` carried CRLF, and the two multi-line verifier bodies carried
///     `\r` inside a raw python string nested in a bash heredoc.
///
/// One normalisation at the point of reading, so no later stage has to remember.
pub fn read(path: &Path) -> std::io::Result<String> {
    Ok(std::fs::read_to_string(path)?.replace("\r\n", "\n"))
}

/// Categories that are not part of the stable 90 (F11): a CTO-decomposition experiment whose
/// task content changed between the only two runs it appeared in, so there is nothing stable
/// to import.
pub const UNSTABLE_CATEGORIES: [&str; 2] = ["react_cto", "cto_decomposed"];

#[derive(Debug, Clone, Default)]
pub struct DonorTask {
    pub name: String,
    /// `None` when the donor wrote `validation: null` — ten tasks do (F13).
    pub validation: Option<String>,
    pub section: String,
    pub complexity: String,
    pub category: String,
    pub validation_lang: String,
    pub dir: String,
    pub files: String,
    pub description: String,
}

// ---------------------------------------------------------------------------------------------
// JS string escapes
// ---------------------------------------------------------------------------------------------

/// Resolve JS string escapes to the value the donor actually passes to the runner.
///
/// This function is F21. `extract_tasks.py` originally captured `\x` pairs verbatim so the
/// closing delimiter could not be misread, and then forgot to unescape, so `tasks.json` carried
/// `\\n` where the donor passes `\n`. One verifier was affected (`py_csv_transform`): the CSV
/// arrived as a single row and the verifier FAILed for a reason that had nothing to do with the
/// artifact — that is, it failed in the direction that reads as *"the verifier is sound"*.
/// A silent, one-directional, flattering error is exactly the kind that needs a test rather
/// than a comment, so see the tests at the bottom of this file.
pub fn js_unescape(s: &str) -> String {
    let b = s.as_bytes();
    let mut out: Vec<u8> = Vec::with_capacity(b.len());
    let mut i = 0;
    while i < b.len() {
        if b[i] != b'\\' || i + 1 >= b.len() {
            out.push(b[i]);
            i += 1;
            continue;
        }
        let n = b[i + 1];
        // \uXXXX
        if n == b'u' && i + 6 <= b.len() {
            if let Some(c) = hex_char(&b[i + 2..i + 6]) {
                push_char(&mut out, c);
                i += 6;
                continue;
            }
        }
        // \xXX
        if n == b'x' && i + 4 <= b.len() {
            if let Some(c) = hex_char(&b[i + 2..i + 4]) {
                push_char(&mut out, c);
                i += 4;
                continue;
            }
        }
        out.push(match n {
            b'n' => b'\n',
            b't' => b'\t',
            b'r' => b'\r',
            b'b' => 0x08,
            b'f' => 0x0c,
            b'v' => 0x0b,
            b'0' => 0x00,
            // Unknown escapes resolve to the escaped character itself, as JS does. This is the
            // branch that carries `\\` -> `\`, and so the branch F21 turned on.
            other => other,
        });
        i += 2;
    }
    String::from_utf8(out).unwrap_or_else(|e| String::from_utf8_lossy(e.as_bytes()).into_owned())
}

fn hex_char(digits: &[u8]) -> Option<char> {
    if !digits.iter().all(|d| d.is_ascii_hexdigit()) {
        return None;
    }
    let s = std::str::from_utf8(digits).ok()?;
    char::from_u32(u32::from_str_radix(s, 16).ok()?)
}

fn push_char(out: &mut Vec<u8>, c: char) {
    let mut buf = [0u8; 4];
    out.extend_from_slice(c.encode_utf8(&mut buf).as_bytes());
}

// ---------------------------------------------------------------------------------------------
// Scanners
// ---------------------------------------------------------------------------------------------

fn skip_ws(b: &[u8], mut i: usize) -> usize {
    while i < b.len() && matches!(b[i], b' ' | b'\t' | b'\n' | b'\r') {
        i += 1;
    }
    i
}

/// `b[i]` is the opening delimiter. Returns the raw body (escape pairs kept verbatim so the
/// closing delimiter cannot be misread) and the index after the closing delimiter.
fn read_delimited(b: &[u8], mut i: usize) -> Option<(String, usize)> {
    let q = b[i];
    i += 1;
    let mut out: Vec<u8> = Vec::new();
    while i < b.len() {
        if b[i] == b'\\' && i + 1 < b.len() {
            out.push(b[i]);
            out.push(b[i + 1]);
            i += 2;
            continue;
        }
        if b[i] == q {
            return Some((String::from_utf8_lossy(&out).into_owned(), i + 1));
        }
        out.push(b[i]);
        i += 1;
    }
    None
}

/// Read a JS value starting at `i`: template literal, quoted string, or a bare token.
/// Strings are unescaped; bare tokens (numbers, `null`) are returned trimmed.
fn read_value(b: &[u8], i: usize) -> (String, usize) {
    let i = skip_ws(b, i);
    if i >= b.len() {
        return (String::new(), i);
    }
    if matches!(b[i], b'`' | b'\'' | b'"') {
        if let Some((raw, j)) = read_delimited(b, i) {
            return (js_unescape(&raw), j);
        }
    }
    let mut j = i;
    while j < b.len() && !matches!(b[j], b',' | b'\n' | b'}') {
        j += 1;
    }
    (
        String::from_utf8_lossy(&b[i..j]).trim().to_string(),
        j,
    )
}

fn is_word_byte(c: u8) -> bool {
    c.is_ascii_alphanumeric() || c == b'_'
}

/// Find `<field>:` in `block` at a word boundary. Returns the index just after the colon.
fn find_field(block: &[u8], field: &str) -> Option<usize> {
    let needle = format!("{field}:").into_bytes();
    let mut from = 0;
    while let Some(rel) = find_sub(&block[from..], &needle) {
        let at = from + rel;
        let boundary_ok = at == 0 || !is_word_byte(block[at - 1]);
        if boundary_ok {
            return Some(at + needle.len());
        }
        from = at + 1;
    }
    None
}

fn find_sub(hay: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || hay.len() < needle.len() {
        return None;
    }
    hay.windows(needle.len()).position(|w| w == needle)
}

// ---------------------------------------------------------------------------------------------
// Extraction
// ---------------------------------------------------------------------------------------------

/// Extract every task object: the ones carrying `name:` together with `validation:`.
///
/// The object's extent is "up to the next `name:`", which is what the spike did and what the
/// donor's flat array-of-objects layout allows. `validation: null` is preserved as `None`
/// rather than dropped, because those ten tasks have to be imported too (SPEC §8).
pub fn extract(js: &str) -> Vec<DonorTask> {
    let b = js.as_bytes();
    let mut tasks = Vec::new();
    let name_key = b"name:";
    let mut from = 0;

    while let Some(rel) = find_sub(&b[from..], name_key) {
        let at = from + rel;
        from = at + name_key.len();
        if at > 0 && is_word_byte(b[at - 1]) {
            continue; // e.g. `fileName:` — not a task's `name`
        }
        let after = skip_ws(b, at + name_key.len());
        if after >= b.len() || b[after] != b'\'' {
            continue; // the donor writes task names as single-quoted literals
        }
        let Some((raw_name, name_end)) = read_delimited(b, after) else {
            continue;
        };
        let name = js_unescape(&raw_name);

        // The object runs to the next `name:` — plain substring search, as the spike did.
        let block_end = find_sub(&b[name_end..], name_key)
            .map(|r| name_end + r)
            .unwrap_or(b.len());
        let block = &b[name_end..block_end];

        let Some(vi) = find_field(block, "validation") else {
            continue; // not a task object
        };
        let (validation, _) = read_value(block, vi);

        let mut t = DonorTask {
            name,
            validation: if validation.trim().is_empty() || validation.trim() == "null" {
                None
            } else {
                Some(validation)
            },
            ..Default::default()
        };
        for (field, slot) in [
            ("section", &mut t.section),
            ("complexity", &mut t.complexity),
            ("category", &mut t.category),
            ("validationLang", &mut t.validation_lang),
            ("dir", &mut t.dir),
            ("files", &mut t.files),
            ("description", &mut t.description),
        ] {
            if let Some(fi) = find_field(block, field) {
                *slot = read_value(block, fi).0;
            }
        }
        tasks.push(t);
    }
    tasks
}

/// The stable 90: everything outside the CTO-decomposition experiment (F11).
pub fn stable(tasks: Vec<DonorTask>) -> Vec<DonorTask> {
    tasks
        .into_iter()
        .filter(|t| !UNSTABLE_CATEGORIES.contains(&t.category.as_str()))
        .collect()
}

/// Parse `BUGGY_FILES` — the ten real buggy fixtures the donor ships for section 4B.
pub fn buggy_files(js: &str) -> BTreeMap<String, String> {
    let b = js.as_bytes();
    let mut out = BTreeMap::new();
    let Some(start) = find_sub(b, b"const BUGGY_FILES = {") else {
        return out;
    };
    let end = find_sub(&b[start..], b"\n};")
        .map(|r| start + r)
        .unwrap_or(b.len());
    let block = &b[start..end];

    // Entries are `'<name>': `<template literal>`,`
    let mut i = 0;
    while i < block.len() {
        if block[i] != b'\'' {
            i += 1;
            continue;
        }
        let Some((key, after_key)) = read_delimited(block, i) else {
            break;
        };
        let j = skip_ws(block, after_key);
        if j >= block.len() || block[j] != b':' {
            i = after_key;
            continue;
        }
        let k = skip_ws(block, j + 1);
        if k < block.len() && block[k] == b'`' {
            if let Some((raw, after_val)) = read_delimited(block, k) {
                out.insert(js_unescape(&key), js_unescape(&raw));
                i = after_val;
                continue;
            }
        }
        i = after_key;
    }
    out
}

// ---------------------------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    /// F21, as a test rather than a comment. The donor source writes `\\n` inside a template
    /// literal; JS resolves that to a two-character `\n`, which Python then parses as a newline
    /// *inside* the verifier's string literal. Both neighbouring mistakes are silent:
    ///
    ///   - stopping too early leaves `\\n`, so python sees a literal backslash-n, the CSV
    ///     parses as one row, and the verifier FAILs for the wrong reason;
    ///   - going too far produces a real newline, which is a SyntaxError inside a
    ///     single-quoted python literal.
    ///
    /// So the correct answer is one backslash followed by `n`, and it is the only answer this
    /// test accepts.
    #[test]
    fn f21_backslash_n_survives_as_two_characters() {
        let donor_source = r"'name,age\\nAlice,30\\nBob,25'";
        // Strip the surrounding quotes the way the scanner does, then unescape once.
        let raw = &donor_source[1..donor_source.len() - 1];
        let got = js_unescape(raw);
        assert_eq!(got, r"name,age\nAlice,30\nBob,25");
        assert!(got.contains('\\'), "the backslash must survive");
        assert!(!got.contains('\n'), "it must NOT become a real newline");
        assert!(!got.contains(r"\\"), "and it must not stay double-escaped");
    }

    #[test]
    fn js_unescape_handles_the_rest_of_the_table() {
        assert_eq!(js_unescape(r"a\nb"), "a\nb");
        assert_eq!(js_unescape(r"a\tb"), "a\tb");
        assert_eq!(js_unescape(r"it\'s"), "it's");
        assert_eq!(js_unescape(r"a\`b"), "a`b");
        assert_eq!(js_unescape(r"a\$b"), "a$b");
        assert_eq!(js_unescape(r"\x41\x42"), "AB");
        assert_eq!(js_unescape(r"é"), "é");
        // An unknown escape resolves to the character itself.
        assert_eq!(js_unescape(r"a\qb"), "aqb");
        // A trailing lone backslash is kept rather than dropped.
        assert_eq!(js_unescape(r"ab\"), r"ab\");
    }

    #[test]
    fn read_value_reads_all_three_forms() {
        assert_eq!(read_value(b"'hi'", 0).0, "hi");
        assert_eq!(read_value(b"`hi there`", 0).0, "hi there");
        assert_eq!(read_value(b"  7,", 0).0, "7");
        assert_eq!(read_value(b" null,", 0).0, "null");
        // A quote inside a template literal must not close it.
        assert_eq!(read_value(b"`it's fine`", 0).0, "it's fine");
    }

    #[test]
    fn find_field_respects_word_boundaries() {
        // `validation:` must not be found inside `validationLang:`.
        let block = b"validationLang: 'py', validation: 'code'";
        let i = find_field(block, "validation").unwrap();
        assert_eq!(read_value(block, i).0, "code");
        // and the narrower field is still reachable
        let j = find_field(block, "validationLang").unwrap();
        assert_eq!(read_value(block, j).0, "py");
    }

    #[test]
    fn extract_reads_a_task_object() {
        let js = r#"
        const tasks = [
          { name: 'demo_one', section: '3', complexity: 7, category: 'py_api',
            validationLang: 'py', dir: 'py_api_server', files: 1,
            description: `Step 1: Use file_write to create tasks/py_api_server/x.py`,
            validation: `import sys; from tasks.py_api_server.x import f; assert f(); print('PASS')` },
          { name: 'demo_null', section: '5', complexity: 6, category: 'go',
            validationLang: 'go', dir: 'go_basics', files: 1,
            description: `whatever`, validation: null },
        ];
        "#;
        let ts = extract(js);
        assert_eq!(ts.len(), 2);
        assert_eq!(ts[0].name, "demo_one");
        assert_eq!(ts[0].category, "py_api");
        assert_eq!(ts[0].complexity, "7");
        assert!(ts[0].validation.as_ref().unwrap().contains("from tasks."));
        assert_eq!(ts[1].name, "demo_null");
        assert!(
            ts[1].validation.is_none(),
            "`validation: null` must survive as None, not as the string \"null\""
        );
    }

    /// The donor is entirely CRLF, so anything anchored on `\n` silently misses. This is the
    /// test for the normalisation that fixes it; without it the two cross-task dependency
    /// fixtures come out empty and their gate point 1 reads `sound` while measuring nothing.
    #[test]
    fn crlf_normalisation_makes_newline_anchored_matches_work() {
        let crlf = "Step 1: Use file_write to create tasks/x/y.py with this content:\r\n\
                    class A:\r\n    pass\r\n\r\nDO NOT just output the code.";
        assert!(
            !crlf.contains("with this content:\n"),
            "the raw CRLF form must NOT match, or this test proves nothing"
        );
        let lf = crlf.replace("\r\n", "\n");
        assert!(lf.contains("with this content:\n"));
        assert!(!lf.contains('\r'));
    }

    #[test]
    fn buggy_files_parses_a_template_literal_map() {
        let js = "const BUGGY_FILES = {\n  'x.py': `def f():\\n    return 1`,\n  'y.js': `var a = 1;`,\n};\n";
        let m = buggy_files(js);
        assert_eq!(m.len(), 2);
        assert_eq!(m["x.py"], "def f():\n    return 1");
        assert_eq!(m["y.js"], "var a = 1;");
    }
}
