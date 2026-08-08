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
//! ## How it was resolved: the subject gained the missing path
//!
//! David's call, 2026-08-08: fix the subject rather than rewrite 69 prompts. Claudette's piped
//! branch now accepts a **sentinel-delimited block** — a line reading exactly `<<<CLAUDETTE-PROMPT`
//! opens it, a line reading exactly `CLAUDETTE-PROMPT>>>` closes it, and everything between arrives
//! as one turn with its newlines and blank lines intact. Confirmed by running it, not by reading it:
//! a 6-line body containing a bare `exit` line ran as **one** turn against the champion, while the
//! same body without sentinels ran as two turns and then ended the session at `exit`.
//!
//! **The sentinels are declared by the subject descriptor, never hard-coded here** — a different
//! subject will have a different way in, or none, and the runner must not assume Claudette's.
//!
//! So [`Mode::Verbatim`] no longer means "single-line only". It means what it always said: the
//! subject receives exactly these bytes as one turn. Whether that needs a wrapper is a transport
//! detail, recorded per cell as [`Transport`]. A subject that declares no block delivery still gets
//! the refusal, with the citation.
//!
//! [`Mode::EscapeNewlines`] is kept, unapproved and unused, because it is the fallback for any
//! future subject in the position Claudette was in this morning.

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

/// The sentinel pair a subject declares for delivering a block as one turn. Borrowed from the
/// descriptor so this module never learns any particular subject's strings.
#[derive(Debug, Clone, Copy)]
pub struct Sentinel<'a> {
    pub open: &'a str,
    pub close: &'a str,
}

/// How the bytes reached the subject. Orthogonal to [`Mode`]: both transports are faithful under
/// `verbatim`, and a reader of a cell still needs to know which one carried it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Transport {
    /// One line, written as-is. What every single-line prompt uses.
    Line,
    /// Wrapped in the subject's declared sentinels and written as several lines that the subject
    /// reassembles into one turn.
    Sentinel,
}

impl Transport {
    pub fn as_str(self) -> &'static str {
        match self {
            Transport::Line => "line",
            Transport::Sentinel => "sentinel",
        }
    }
}

impl fmt::Display for Transport {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.as_str())
    }
}

#[derive(Debug, Clone)]
pub struct Plan {
    /// Exactly what to write, one element per line written to the subject's stdin. More than one
    /// element only under [`Transport::Sentinel`], where the subject consumes the whole block
    /// inside a single read and no gate can interleave.
    pub lines: Vec<String>,
    pub mode: Mode,
    pub transport: Transport,
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

/// Turn one turn's text into the lines the REPL will read, or say why it cannot be done.
///
/// `sentinel` is whatever the subject descriptor declared, and `None` means the subject has no way
/// to receive a block — which is a refusal under `verbatim`, not a silent flatten.
pub fn plan(text: &str, mode: Mode, sentinel: Option<Sentinel<'_>>) -> Result<Plan, Undeliverable> {
    // A trailing newline is the file's terminator, not part of the prompt.
    let body = text.trim_end_matches(['\n', '\r']);
    let prompt_lines = body.lines().count().max(1);
    let prompt_bytes = body.len();
    let multiline = body.contains('\n') || body.contains('\r');

    let refuse = |reason: String| {
        Err(Undeliverable {
            mode,
            prompt_lines,
            reason,
        })
    };

    match mode {
        Mode::Verbatim if !multiline => Ok(Plan {
            lines: vec![body.to_string()],
            mode,
            transport: Transport::Line,
            prompt_lines,
            prompt_bytes,
        }),
        Mode::Verbatim => {
            let Some(s) = sentinel else {
                return refuse(format!(
                    "this prompt is {prompt_lines} lines and the subject declares no block \
                     delivery, so it has no path that delivers a multi-line prompt as one turn: a \
                     piped REPL of Claudette's shape reads one line per turn \
                     (line_editor.rs:370-376), Event::Paste strips newlines outright \
                     (line_editor.rs:401-403), and one-shot has no permission prompter \
                     (run.rs:186). Sending it as written would run {prompt_lines} separate turns. \
                     Add [delivery] to the subject descriptor, or choose a delivery mode \
                     deliberately — see delivery.rs"
                ));
            };
            // Normalise first: the block is prompt content and the donor source is entirely CRLF
            // (F22), so a stray \r would ride into a dictated code body invisibly.
            let normalised = body.replace("\r\n", "\n").replace('\r', "\n");
            // A body line identical to either sentinel would end the block early and turn the rest
            // of the prompt into loose turns. Refuse rather than deliver a truncated prompt — the
            // same reason the subject errors on an unterminated block.
            if let Some(clash) =
                normalised.lines().find(|l| *l == s.open || *l == s.close)
            {
                return refuse(format!(
                    "this prompt contains a line identical to the subject's block sentinel \
                     ({clash:?}), so wrapping it would end the block early and deliver a truncated \
                     prompt. No faithful delivery exists for this task against this subject"
                ));
            }
            let mut lines = Vec::with_capacity(prompt_lines + 2);
            lines.push(s.open.to_string());
            lines.extend(normalised.lines().map(str::to_string));
            lines.push(s.close.to_string());
            Ok(Plan {
                lines,
                mode,
                transport: Transport::Sentinel,
                prompt_lines,
                prompt_bytes,
            })
        }
        Mode::EscapeNewlines => {
            let line = body.replace("\r\n", "\n").replace('\r', "\n").replace('\n', "\\n");
            Ok(Plan {
                lines: vec![line],
                mode,
                transport: Transport::Line,
                prompt_lines,
                prompt_bytes,
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Claudette's real pair, as `subjects/claudette-*.toml` declares it.
    const S: Sentinel<'static> =
        Sentinel { open: "<<<CLAUDETTE-PROMPT", close: "CLAUDETTE-PROMPT>>>" };

    #[test]
    fn a_single_line_prompt_is_delivered_byte_for_byte_and_unwrapped() {
        // `fix_sql_inject`'s real prompt: one line, 306 bytes.
        let p = plan("SECURITY FIX: Read the file sql_inject.py …\n", Mode::Verbatim, Some(S))
            .unwrap();
        assert_eq!(p.lines, vec!["SECURITY FIX: Read the file sql_inject.py …"]);
        assert_eq!(p.transport, Transport::Line, "no wrapper when none is needed");
        assert_eq!(p.prompt_lines, 1);
        assert!(p.mode.is_faithful());
    }

    #[test]
    fn a_multi_line_prompt_is_wrapped_in_the_subjects_sentinels() {
        let p = plan("line one\nline two\n", Mode::Verbatim, Some(S)).unwrap();
        assert_eq!(p.lines, vec![S.open, "line one", "line two", S.close]);
        assert_eq!(p.transport, Transport::Sentinel);
        assert_eq!(p.prompt_lines, 2, "the count describes the prompt, not the wrapper");
        assert!(p.mode.is_faithful(), "wrapping is transport, not a rewrite");
    }

    #[test]
    fn without_a_declared_sentinel_a_multi_line_prompt_is_still_refused_with_the_citation() {
        let e = plan("line one\nline two\n", Mode::Verbatim, None).expect_err("must refuse");
        assert_eq!(e.prompt_lines, 2);
        assert!(e.reason.contains("line_editor.rs:370-376"), "{}", e.reason);
    }

    #[test]
    fn crlf_is_normalised_inside_the_block_rather_than_riding_into_the_prompt() {
        // The donor source is entirely CRLF (F22, 3,521 \r\n and zero bare \n).
        let p = plan("a\r\nb\r\n", Mode::Verbatim, Some(S)).unwrap();
        assert_eq!(p.lines, vec![S.open, "a", "b", S.close]);
        assert!(p.lines.iter().all(|l| !l.contains('\r')), "no CR survives: {:?}", p.lines);
    }

    #[test]
    fn blank_lines_inside_a_prompt_are_preserved_as_blank_lines() {
        // The REPL loop skips a blank *line*; inside a block it is prompt content, and 50 of the
        // donor prompts dictate an artifact body where the blank lines matter (F25).
        let p = plan("head\n\ntail", Mode::Verbatim, Some(S)).unwrap();
        assert_eq!(p.lines, vec![S.open, "head", "", "tail", S.close]);
    }

    #[test]
    fn a_prompt_containing_the_sentinel_is_refused_rather_than_truncated() {
        let text = format!("first\n{}\nsecond", S.close);
        let e = plan(&text, Mode::Verbatim, Some(S)).expect_err("must refuse");
        assert!(e.reason.contains("end the block early"), "{}", e.reason);
    }

    #[test]
    fn escape_mode_produces_one_line_and_normalises_crlf_first() {
        let p = plan("a\r\nb\nc", Mode::EscapeNewlines, Some(S)).unwrap();
        assert_eq!(p.lines, vec!["a\\nb\\nc"]);
        assert!(!p.lines[0].contains('\n'));
        // The count still describes the ORIGINAL prompt, which is what a reader of the cell record
        // needs in order to judge the mode.
        assert_eq!(p.prompt_lines, 3);
        assert!(!p.mode.is_faithful());
        assert_eq!(p.transport, Transport::Line, "escaping never wraps");
    }

    #[test]
    fn a_trailing_newline_is_not_treated_as_multi_line() {
        let p = plan("just one line\n", Mode::Verbatim, Some(S)).unwrap();
        assert_eq!(p.prompt_lines, 1);
        assert_eq!(p.lines, vec!["just one line"]);
        assert_eq!(p.transport, Transport::Line);
    }

    #[test]
    fn mode_names_round_trip() {
        for m in [Mode::Verbatim, Mode::EscapeNewlines] {
            assert_eq!(Mode::parse(m.as_str()), Some(m));
        }
        assert_eq!(Mode::parse("flatten"), None);
    }
}
