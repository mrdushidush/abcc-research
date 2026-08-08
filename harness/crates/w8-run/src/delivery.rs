//! How a prompt becomes a turn — and the blocker this module exists to name rather than paper over.
//!
//! ## The subject cannot receive a multi-line prompt as one turn
//!
//! Established by reading three paths and running the fourth:
//!
//! | Path | What happens to a newline |
//! |---|---|
//! | piped REPL (the drive mode) | `io::stdin().read_line` (`line_editor.rs:370-376`) — **one line is one turn**, so a 20-line prompt is 20 turns |
//! | interactive REPL + paste | `Event::Paste` filters newlines **out of the buffer entirely** (`line_editor.rs:401-403`), so `foo\nbar` arrives as `foobar` — and bracketed paste is not even enabled outside the TUI (`tui.rs:712`) |
//! | one-shot (`claudette "…"`) | argv carries newlines fine, but one-shot passes `None` for its prompter (`run.rs:186`) so it can never show a gate (F1), and its system prompt is a different size — measured `in=1816` against the REPL's ~4,885, i.e. comparable to nothing |
//! | slash commands | none of them reads a file into a turn (`commands.rs:168-230`) |
//!
//! Blank lines are skipped by the REPL (`repl.rs:125-127`) and `exit`/`quit`/`:q` on a line of their
//! own end the session (`:129-131`), so a prompt containing either does more than split.
//!
//! **69 of the 90 U100 prompts are multi-line** (measured: 21 single-line, the rest up to 54 lines).
//! The 21 that are single-line are all 10 section-4B `fix_*` tasks plus 11 presence-only landing
//! pages, so the reachable-today set is not a random sample but it is the section carrying most of
//! the suite's measured difficulty.
//!
//! There is no lossless option, so the choice is David's and the mode is recorded on **every** cell
//! rather than assumed: [`Mode::Verbatim`] refuses a prompt it cannot deliver exactly, and any other
//! mode labels its own output so no number can be quoted without its delivery.

use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Deliver the prompt byte-for-byte, or refuse the cell. The only mode that measures the
    /// donor's task rather than a rewrite of it.
    Verbatim,
    /// Interior newlines become the two characters `\` `n`. **Not approved** — it is a semantic
    /// edit to the prompt on 69 of 90 tasks, and 50 of those prompts dictate an artifact body
    /// verbatim, so the subject has to un-escape code correctly to pass. This project has already
    /// been burned twice by `\n` handling (F21's double-escaped template literals, F24's eaten
    /// backslashes), which is a reason for suspicion rather than a proof of harm.
    EscapeNewlines,
}

impl Mode {
    pub fn parse(s: &str) -> Option<Mode> {
        match s {
            "verbatim" => Some(Mode::Verbatim),
            "escape-newlines" => Some(Mode::EscapeNewlines),
            _ => None,
        }
    }

    pub fn as_str(self) -> &'static str {
        match self {
            Mode::Verbatim => "verbatim",
            Mode::EscapeNewlines => "escape-newlines",
        }
    }

    pub fn is_faithful(self) -> bool {
        matches!(self, Mode::Verbatim)
    }
}

impl fmt::Display for Mode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

#[derive(Debug, Clone)]
pub struct Plan {
    /// Exactly what to write, one element per line written to the subject's stdin.
    pub line: String,
    pub mode: Mode,
    pub prompt_lines: usize,
    pub prompt_bytes: usize,
}

#[derive(Debug, Clone)]
pub struct Undeliverable {
    pub mode: Mode,
    pub prompt_lines: usize,
    pub reason: String,
}

impl fmt::Display for Undeliverable {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.reason)
    }
}

/// Turn one turn's text into the single line the REPL will read, or say why it cannot be done.
pub fn plan(text: &str, mode: Mode) -> Result<Plan, Undeliverable> {
    // A trailing newline is the file's terminator, not part of the prompt.
    let body = text.trim_end_matches(['\n', '\r']);
    let prompt_lines = body.lines().count().max(1);
    let prompt_bytes = body.len();
    let multiline = body.contains('\n') || body.contains('\r');

    match mode {
        Mode::Verbatim if multiline => Err(Undeliverable {
            mode,
            prompt_lines,
            reason: format!(
                "this prompt is {prompt_lines} lines and claudette-fc1ea22 has no path that \
                 delivers a multi-line prompt as one turn: the piped REPL reads one line per turn \
                 (line_editor.rs:370-376), Event::Paste strips newlines outright \
                 (line_editor.rs:401-403), and one-shot has no permission prompter (run.rs:186). \
                 Sending it as written would run {prompt_lines} separate turns. Choose a delivery \
                 mode deliberately — see delivery.rs"
            ),
        }),
        Mode::Verbatim => Ok(Plan { line: body.to_string(), mode, prompt_lines, prompt_bytes }),
        Mode::EscapeNewlines => {
            let line = body.replace("\r\n", "\n").replace('\r', "\n").replace('\n', "\\n");
            Ok(Plan { line, mode, prompt_lines, prompt_bytes })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_single_line_prompt_is_delivered_byte_for_byte() {
        // `fix_sql_inject`'s real prompt: one line, 306 bytes.
        let p = plan("SECURITY FIX: Read the file sql_inject.py …\n", Mode::Verbatim).unwrap();
        assert_eq!(p.line, "SECURITY FIX: Read the file sql_inject.py …");
        assert_eq!(p.prompt_lines, 1);
        assert!(p.mode.is_faithful());
    }

    #[test]
    fn a_multi_line_prompt_is_refused_with_the_citation_not_silently_flattened() {
        let e = plan("line one\nline two\n", Mode::Verbatim).expect_err("must refuse");
        assert_eq!(e.prompt_lines, 2);
        assert!(e.reason.contains("line_editor.rs:370-376"), "{}", e.reason);
    }

    #[test]
    fn crlf_prompts_count_as_multi_line() {
        // The donor source is entirely CRLF (F22, 3,521 \r\n and zero bare \n). A check anchored on
        // '\n' alone would call a CRLF prompt single-line and then split it at the REPL.
        assert!(plan("a\r\nb\r\n", Mode::Verbatim).is_err());
    }

    #[test]
    fn escape_mode_produces_one_line_and_normalises_crlf_first() {
        let p = plan("a\r\nb\nc", Mode::EscapeNewlines).unwrap();
        assert_eq!(p.line, "a\\nb\\nc");
        assert!(!p.line.contains('\n'));
        // The count still describes the ORIGINAL prompt, which is what a reader of the cell record
        // needs in order to judge the mode.
        assert_eq!(p.prompt_lines, 3);
        assert!(!p.mode.is_faithful());
    }

    #[test]
    fn a_trailing_newline_is_not_treated_as_multi_line() {
        let p = plan("just one line\n", Mode::Verbatim).unwrap();
        assert_eq!(p.prompt_lines, 1);
        assert_eq!(p.line, "just one line");
    }

    #[test]
    fn mode_names_round_trip() {
        for m in [Mode::Verbatim, Mode::EscapeNewlines] {
            assert_eq!(Mode::parse(m.as_str()), Some(m));
        }
        assert_eq!(Mode::parse("flatten"), None);
    }
}
