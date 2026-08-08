//! Confirming which model actually answered, over ~90 lines of HTTP/1.1.
//!
//! ## Why this module exists at all
//!
//! Measured 2026-08-08, and it invalidates the obvious way to record a held constant:
//!
//! ```text
//! POST /v1/chat/completions  {"model":"w8-bogus-model-id", ...}
//!   -> 200 OK  {"model":"qwen3.6-35b-a3b-mtp@iq3_s", ...}
//! ```
//!
//! **LM Studio serves a request that names a model it does not have, using whichever model is
//! loaded, and answers normally.** A `claudette` run with `CLAUDETTE_MODEL` set to a typo therefore
//! succeeds, produces plausible numbers, and reports nothing — the same run was tried through
//! Claudette itself and returned `in=1817 out=45` against a nonexistent id. So "RUNMETA says the
//! champion" is a claim about a string this harness wrote, not evidence about the model that ran.
//!
//! The response's own `model` field is the evidence, and it is the only place it appears. One probe
//! before the first measured cell turns the RUNMETA row from an assertion into a confirmation, and
//! makes [[always-test-on-the-champion-model]] enforceable rather than aspirational.
//!
//! No HTTP dependency: the endpoint is plain-text localhost, so there is no TLS to get wrong.

use std::io::{Read, Write};
use std::net::TcpStream;
use std::time::Duration;

#[derive(Debug)]
pub enum EndpointError {
    BadUrl(String),
    Io(std::io::Error),
    Status(u16, String),
    NoModelField(String),
}

impl std::fmt::Display for EndpointError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EndpointError::BadUrl(u) => write!(f, "cannot parse endpoint {u:?} as http://host:port"),
            EndpointError::Io(e) => write!(f, "{e}"),
            EndpointError::Status(c, b) => write!(f, "HTTP {c}: {}", b.trim()),
            EndpointError::NoModelField(b) => {
                write!(f, "response carried no \"model\" field: {}", truncate(b, 300))
            }
        }
    }
}

impl From<std::io::Error> for EndpointError {
    fn from(e: std::io::Error) -> Self {
        EndpointError::Io(e)
    }
}

fn truncate(s: &str, n: usize) -> String {
    if s.chars().count() <= n { s.to_string() } else { s.chars().take(n).collect::<String>() + "…" }
}

/// `http://host:port` (with or without a trailing slash) into a socket address.
fn host_port(endpoint: &str) -> Result<String, EndpointError> {
    let rest = endpoint
        .strip_prefix("http://")
        .ok_or_else(|| EndpointError::BadUrl(endpoint.to_string()))?;
    let authority = rest.split('/').next().unwrap_or("");
    if authority.is_empty() {
        return Err(EndpointError::BadUrl(endpoint.to_string()));
    }
    Ok(if authority.contains(':') { authority.to_string() } else { format!("{authority}:80") })
}

fn request(
    endpoint: &str,
    method: &str,
    path: &str,
    body: Option<&str>,
    timeout: Duration,
) -> Result<String, EndpointError> {
    let addr = host_port(endpoint)?;
    let mut stream = TcpStream::connect(&addr)?;
    stream.set_read_timeout(Some(timeout))?;
    stream.set_write_timeout(Some(timeout))?;

    let mut req = format!(
        "{method} {path} HTTP/1.1\r\nHost: {addr}\r\nAccept: application/json\r\n\
         Connection: close\r\n"
    );
    if let Some(b) = body {
        req.push_str("Content-Type: application/json\r\n");
        req.push_str(&format!("Content-Length: {}\r\n", b.len()));
    }
    req.push_str("\r\n");
    if let Some(b) = body {
        req.push_str(b);
    }
    stream.write_all(req.as_bytes())?;
    stream.flush()?;

    let mut raw = Vec::new();
    stream.read_to_end(&mut raw)?;
    let text = String::from_utf8_lossy(&raw).into_owned();
    parse_response(&text)
}

/// Split status line / headers / body, and de-chunk when the server used
/// `Transfer-Encoding: chunked` — which `Connection: close` does not prevent.
fn parse_response(text: &str) -> Result<String, EndpointError> {
    let (head, body) = match text.find("\r\n\r\n") {
        Some(i) => (&text[..i], &text[i + 4..]),
        None => (text, ""),
    };
    let mut lines = head.split("\r\n");
    let status_line = lines.next().unwrap_or("");
    let code: u16 = status_line.split(' ').nth(1).and_then(|c| c.parse().ok()).unwrap_or(0);
    let chunked = head.to_ascii_lowercase().contains("transfer-encoding: chunked");
    let body = if chunked { dechunk(body) } else { body.to_string() };
    if (200..300).contains(&code) { Ok(body) } else { Err(EndpointError::Status(code, body)) }
}

fn dechunk(body: &str) -> String {
    let mut out = String::new();
    let mut rest = body;
    while let Some(nl) = rest.find("\r\n") {
        let size_field = rest[..nl].split(';').next().unwrap_or("").trim();
        let Ok(size) = usize::from_str_radix(size_field, 16) else { break };
        if size == 0 {
            break;
        }
        let start = nl + 2;
        let end = start + size;
        if end > rest.len() {
            out.push_str(&rest[start..]);
            break;
        }
        out.push_str(&rest[start..end]);
        rest = rest[end..].strip_prefix("\r\n").unwrap_or("");
    }
    out
}

/// Every `"id": "..."` in `GET /v1/models`. A pre-flight only — see [`confirm_model`] for the
/// check that actually holds.
pub fn list_models(endpoint: &str) -> Result<Vec<String>, EndpointError> {
    let body = request(endpoint, "GET", "/v1/models", None, Duration::from_secs(10))?;
    Ok(json_strings_for_key(&body, "id"))
}

/// What the server says about the loaded model, from LM Studio's own `/api/v0/models`.
///
/// `/v1/models` (the OpenAI-compatible path) carries ids and nothing else. The `v0` path is where
/// the load-time state lives, and that state is measurement-critical in a way the ids are not:
/// **`loaded_context_length` is the real context window, and no environment variable the runner
/// sets can change it.** On the OpenAI-compat path Claudette never sends `num_ctx` at all
/// (`api.rs:757-785`, whose own comment reads "`num_ctx` has no analogue — context is set at
/// model-load time in LM Studio"); `CLAUDETTE_NUM_CTX` drives only Claudette's *client-side*
/// history truncator (`api.rs:1254`, at 4 chars/token). The two numbers are different quantities
/// that read like the same one.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ServerModel {
    pub id: String,
    pub state: String,
    pub quantization: String,
    pub arch: String,
    pub publisher: String,
    pub kind: String,
    pub compatibility_type: String,
    pub loaded_context_length: Option<u64>,
    pub max_context_length: Option<u64>,
    pub capabilities: Vec<String>,
}

/// The `/api/v0/models` entry whose `id` is `model`, or `None` when the server has no such entry.
///
/// `Ok(None)` and `Err(..)` are deliberately different: a server that is not LM Studio has no `v0`
/// path at all and answers 404, which is a *missing capture*, not a bad one.
pub fn server_model(endpoint: &str, model: &str) -> Result<Option<ServerModel>, EndpointError> {
    let body = request(endpoint, "GET", "/api/v0/models", None, Duration::from_secs(15))?;
    Ok(parse_server_model(&body, model))
}

fn parse_server_model(body: &str, model: &str) -> Option<ServerModel> {
    json_objects_in_array(body, "data")
        .into_iter()
        .find(|o| json_string_field(o, "id").as_deref() == Some(model))
        .map(|o| ServerModel {
            id: json_string_field(&o, "id").unwrap_or_default(),
            state: json_string_field(&o, "state").unwrap_or_default(),
            quantization: json_string_field(&o, "quantization").unwrap_or_default(),
            arch: json_string_field(&o, "arch").unwrap_or_default(),
            publisher: json_string_field(&o, "publisher").unwrap_or_default(),
            kind: json_string_field(&o, "type").unwrap_or_default(),
            compatibility_type: json_string_field(&o, "compatibility_type").unwrap_or_default(),
            loaded_context_length: json_u64_field(&o, "loaded_context_length"),
            max_context_length: json_u64_field(&o, "max_context_length"),
            capabilities: json_string_array_field(&o, "capabilities"),
        })
}

/// Ask the endpoint to answer one token as `model`, and return **the model id the server says it
/// used**. The caller compares; a mismatch is a run-abort, not a warning.
pub fn confirm_model(endpoint: &str, model: &str) -> Result<String, EndpointError> {
    let body = format!(
        "{{\"model\":{},\"messages\":[{{\"role\":\"user\",\"content\":\"ok\"}}],\
         \"max_tokens\":1,\"stream\":false}}",
        json_quote(model)
    );
    // Generous: this call is what JIT-loads a 35B if it is not resident, which is the same load the
    // warmup turn exists to absorb (F10).
    let resp = request(
        endpoint,
        "POST",
        "/v1/chat/completions",
        Some(&body),
        Duration::from_secs(600),
    )?;
    json_string_field(&resp, "model").ok_or(EndpointError::NoModelField(resp))
}

// ---------------------------------------------------------------------------
// Just enough JSON to read two string fields. A `serde_json` dependency for this
// would be a third crate for `"model": "..."`.
// ---------------------------------------------------------------------------

pub fn json_quote(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

/// The first string value for `"key"`. Scans rather than parses, so it is only safe for keys whose
/// name cannot appear as a *value* in the same document — `model` and `id` in these two responses.
pub fn json_string_field(body: &str, key: &str) -> Option<String> {
    json_strings_for_key(body, key).into_iter().next()
}

fn json_strings_for_key(body: &str, key: &str) -> Vec<String> {
    let needle = format!("\"{key}\"");
    let bytes: Vec<char> = body.chars().collect();
    let mut out = Vec::new();
    let mut i = 0usize;
    let n_chars: Vec<char> = needle.chars().collect();
    while i + n_chars.len() <= bytes.len() {
        if bytes[i..i + n_chars.len()] == n_chars[..] {
            let mut j = i + n_chars.len();
            while j < bytes.len() && bytes[j].is_whitespace() {
                j += 1;
            }
            if j < bytes.len() && bytes[j] == ':' {
                j += 1;
                while j < bytes.len() && bytes[j].is_whitespace() {
                    j += 1;
                }
                if j < bytes.len() && bytes[j] == '"' {
                    j += 1;
                    let mut val = String::new();
                    while j < bytes.len() {
                        match bytes[j] {
                            '\\' if j + 1 < bytes.len() => {
                                let e = bytes[j + 1];
                                val.push(match e {
                                    'n' => '\n',
                                    'r' => '\r',
                                    't' => '\t',
                                    other => other,
                                });
                                j += 2;
                            }
                            '"' => break,
                            c => {
                                val.push(c);
                                j += 1;
                            }
                        }
                    }
                    out.push(val);
                    i = j;
                    continue;
                }
            }
        }
        i += 1;
    }
    out
}

/// The objects that are direct elements of `"key": [ ... ]`, each as raw JSON text.
///
/// Brace-balanced and string-aware, unlike [`json_strings_for_key`]: the flat scan is only safe
/// when a key name cannot appear as a value, and here the objects must be split *before* their
/// fields are read or `json_string_field(body, "id")` returns whichever model the server happened
/// to list first — which on this machine is the champion only by luck of ordering.
fn json_objects_in_array(body: &str, key: &str) -> Vec<String> {
    let chars: Vec<char> = body.chars().collect();
    let Some(open) = find_array_for_key(&chars, key) else { return Vec::new() };

    let mut out = Vec::new();
    let (mut depth, mut start, mut in_str, mut esc) = (0usize, None, false, false);
    for i in open..chars.len() {
        let c = chars[i];
        if in_str {
            match c {
                _ if esc => esc = false,
                '\\' => esc = true,
                '"' => in_str = false,
                _ => {}
            }
            continue;
        }
        match c {
            '"' => in_str = true,
            '{' => {
                if depth == 0 {
                    start = Some(i);
                }
                depth += 1;
            }
            '}' => {
                depth = depth.saturating_sub(1);
                if depth == 0 {
                    if let Some(s) = start.take() {
                        out.push(chars[s..=i].iter().collect());
                    }
                }
            }
            // The array's own close, reached only outside any element object.
            ']' if depth == 0 => break,
            _ => {}
        }
    }
    out
}

/// Index of the `[` introducing `"key": [`, skipping whitespace around the colon.
fn find_array_for_key(chars: &[char], key: &str) -> Option<usize> {
    let needle: Vec<char> = format!("\"{key}\"").chars().collect();
    let mut i = 0usize;
    while i + needle.len() <= chars.len() {
        if chars[i..i + needle.len()] == needle[..] {
            let mut j = i + needle.len();
            while j < chars.len() && chars[j].is_whitespace() {
                j += 1;
            }
            if j < chars.len() && chars[j] == ':' {
                j += 1;
                while j < chars.len() && chars[j].is_whitespace() {
                    j += 1;
                }
                if j < chars.len() && chars[j] == '[' {
                    return Some(j);
                }
            }
        }
        i += 1;
    }
    None
}

/// The unsigned integer value for `"key"`. `None` when the key is absent or the value is not a
/// bare integer — `not-loaded` models carry no `loaded_context_length` at all, and that absence is
/// the honest record, not a zero.
fn json_u64_field(obj: &str, key: &str) -> Option<u64> {
    let chars: Vec<char> = obj.chars().collect();
    let needle: Vec<char> = format!("\"{key}\"").chars().collect();
    let mut i = 0usize;
    while i + needle.len() <= chars.len() {
        if chars[i..i + needle.len()] == needle[..] {
            let mut j = i + needle.len();
            while j < chars.len() && chars[j].is_whitespace() {
                j += 1;
            }
            if j < chars.len() && chars[j] == ':' {
                j += 1;
                while j < chars.len() && chars[j].is_whitespace() {
                    j += 1;
                }
                let digits: String = chars[j..].iter().take_while(|c| c.is_ascii_digit()).collect();
                return digits.parse().ok();
            }
        }
        i += 1;
    }
    None
}

/// The string elements of `"key": ["a", "b"]`.
fn json_string_array_field(obj: &str, key: &str) -> Vec<String> {
    let chars: Vec<char> = obj.chars().collect();
    let Some(open) = find_array_for_key(&chars, key) else { return Vec::new() };
    let mut close = chars.len();
    let (mut in_str, mut esc) = (false, false);
    for (i, &c) in chars.iter().enumerate().skip(open) {
        if in_str {
            match c {
                _ if esc => esc = false,
                '\\' => esc = true,
                '"' => in_str = false,
                _ => {}
            }
            continue;
        }
        match c {
            '"' => in_str = true,
            ']' => {
                close = i;
                break;
            }
            _ => {}
        }
    }
    let inner: String = chars[open..close].iter().collect();
    // Every string literal inside the slice; the array holds nothing else.
    let mut out = Vec::new();
    let (mut cur, mut in_s, mut es) = (String::new(), false, false);
    for c in inner.chars() {
        if in_s {
            match c {
                _ if es => {
                    cur.push(c);
                    es = false;
                }
                '\\' => es = true,
                '"' => {
                    out.push(std::mem::take(&mut cur));
                    in_s = false;
                }
                _ => cur.push(c),
            }
        } else if c == '"' {
            in_s = true;
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The real `GET /api/v0/models` body from 2026-08-08, trimmed to three entries. Kept verbatim
    /// so the parser is tested against bytes the server actually sent, not against a shape assumed
    /// from the docs.
    const REAL_V0_MODELS: &str = r#"{"data":[
      {"id":"qwen3.6-35b-a3b-mtp@iq3_s","object":"model","type":"llm","publisher":"byteshape",
       "arch":"qwen35moe","compatibility_type":"gguf","quantization":"IQ3_S","state":"loaded",
       "max_context_length":262144,"loaded_context_length":65536,"capabilities":["tool_use"]},
      {"id":"devstral-small-2-24b-instruct-2512","object":"model","type":"llm",
       "publisher":"unsloth","arch":"mistral3","compatibility_type":"gguf","quantization":"IQ4_XS",
       "state":"not-loaded","max_context_length":393216,"capabilities":["tool_use"]},
      {"id":"google/gemma-4-26b-a4b","object":"model","type":"vlm","publisher":"google",
       "arch":"gemma4","compatibility_type":"gguf","quantization":"Q4_K_M","state":"not-loaded",
       "max_context_length":262144}
    ],"object":"list"}"#;

    #[test]
    fn reads_the_loaded_model_out_of_the_real_v0_body() {
        let m = parse_server_model(REAL_V0_MODELS, "qwen3.6-35b-a3b-mtp@iq3_s").unwrap();
        assert_eq!(m.state, "loaded");
        assert_eq!(m.quantization, "IQ3_S");
        assert_eq!(m.arch, "qwen35moe");
        assert_eq!(m.kind, "llm", "`type` must not be read out of `compatibility_type`");
        assert_eq!(m.compatibility_type, "gguf");
        assert_eq!(m.loaded_context_length, Some(65536));
        assert_eq!(m.max_context_length, Some(262144));
        assert_eq!(m.capabilities, vec!["tool_use"]);
    }

    /// The bug this splitter exists to prevent: a flat scan for `"id"` over the whole body returns
    /// the first model listed, so every field would describe a model that is not the one measured.
    #[test]
    fn selects_by_id_rather_than_taking_the_first_entry() {
        let m = parse_server_model(REAL_V0_MODELS, "devstral-small-2-24b-instruct-2512").unwrap();
        assert_eq!(m.arch, "mistral3");
        assert_eq!(m.state, "not-loaded");
        // Absent for an unloaded model, and absence is recorded as absence rather than as 0.
        assert_eq!(m.loaded_context_length, None);
        assert_eq!(json_string_field(REAL_V0_MODELS, "id").unwrap(), "qwen3.6-35b-a3b-mtp@iq3_s");
    }

    #[test]
    fn an_id_containing_a_slash_is_still_matched() {
        let m = parse_server_model(REAL_V0_MODELS, "google/gemma-4-26b-a4b").unwrap();
        assert_eq!(m.publisher, "google");
        assert!(m.capabilities.is_empty(), "the key is absent on this entry");
    }

    #[test]
    fn a_model_the_server_does_not_list_is_none_not_a_default() {
        assert_eq!(parse_server_model(REAL_V0_MODELS, "w8-bogus-model-id"), None);
        // A server with no v0 path at all answers something without `data`.
        assert_eq!(parse_server_model(r#"{"error":"not found"}"#, "anything"), None);
    }

    /// A `}` inside a string value must not close the object early, or the following entries shift
    /// by one and the wrong model is reported with total confidence.
    #[test]
    fn a_brace_inside_a_string_value_does_not_split_an_object() {
        let body = r#"{"data":[{"id":"a}b","state":"loaded","loaded_context_length":8},
                               {"id":"c","state":"not-loaded"}]}"#;
        let m = parse_server_model(body, "a}b").unwrap();
        assert_eq!(m.loaded_context_length, Some(8));
        assert_eq!(parse_server_model(body, "c").unwrap().state, "not-loaded");
    }

    #[test]
    fn host_port_defaults_and_paths() {
        assert_eq!(host_port("http://localhost:1234").unwrap(), "localhost:1234");
        assert_eq!(host_port("http://localhost:1234/").unwrap(), "localhost:1234");
        assert_eq!(host_port("http://example.test").unwrap(), "example.test:80");
        assert!(host_port("https://localhost:1234").is_err());
        assert!(host_port("localhost:1234").is_err());
    }

    #[test]
    fn reads_the_model_field_lm_studio_actually_returns() {
        // The real body from the 2026-08-08 probe, trimmed. The request named
        // `w8-bogus-model-id`; this is what came back.
        let body = r#"{"id":"chatcmpl-x","object":"chat.completion","created":1786202597,
          "model":"qwen3.6-35b-a3b-mtp@iq3_s","choices":[{"index":0,"message":
          {"role":"assistant","content":""}}]}"#;
        assert_eq!(json_string_field(body, "model").unwrap(), "qwen3.6-35b-a3b-mtp@iq3_s");
    }

    #[test]
    fn lists_every_id_in_a_models_response() {
        let body = r#"{"data":[{"id":"a","object":"model"},{"id":"b/c","object":"model"}]}"#;
        assert_eq!(json_strings_for_key(body, "id"), vec!["a", "b/c"]);
    }

    #[test]
    fn escapes_round_trip_through_quote_and_read() {
        let s = "a\"b\\c\nd";
        let doc = format!("{{\"model\":{}}}", json_quote(s));
        assert_eq!(json_string_field(&doc, "model").unwrap(), s);
    }

    #[test]
    fn a_key_that_is_not_present_is_none_not_a_neighbouring_value() {
        let body = r#"{"object":"list","data":[]}"#;
        assert_eq!(json_string_field(body, "model"), None);
    }

    #[test]
    fn chunked_and_plain_bodies_both_parse() {
        let plain = "HTTP/1.1 200 OK\r\nContent-Length: 9\r\n\r\n{\"a\":\"b\"}";
        assert_eq!(parse_response(plain).unwrap(), "{\"a\":\"b\"}");

        let chunked = "HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n\
                       5\r\n{\"a\":\r\n4\r\n\"b\"}\r\n0\r\n\r\n";
        assert_eq!(parse_response(chunked).unwrap(), "{\"a\":\"b\"}");
    }

    #[test]
    fn a_non_2xx_is_an_error_carrying_the_body() {
        let r = parse_response("HTTP/1.1 404 Not Found\r\n\r\nno such model");
        match r {
            Err(EndpointError::Status(404, b)) => assert!(b.contains("no such model")),
            other => panic!("expected 404, got {other:?}"),
        }
    }
}
