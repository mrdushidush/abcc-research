//! `w8-run` — drive a subject over the REPL pipe and produce one measured cell per
//! `(task, variant, subject)`.
//!
//! Step 3b of the W8 plan, and where W8 stops being verifier archaeology. `w8-corpus` (step 3a)
//! reads the corpus and refuses it when it is wrong; this crate is what turns an accepted corpus
//! into numbers.
//!
//! The modules are ordered by how much trouble each one turned out to be:
//!
//! - [`env`] — the held constants. Bigger than it looks, because Claudette loads
//!   `~/.claudette/.env` non-overridingly at startup, so **a constant this runner does not set is
//!   not held, it is inherited from David's daily-driver config**.
//! - [`driver`] — three pipes, a newline-less gate prompt, and one stdin two readers take turns
//!   owning.
//! - [`delivery`] — how a prompt becomes a turn. `claudette-fc1ea22` had no path that delivered a
//!   multi-line prompt as one turn and 69 of the 90 U100 prompts are multi-line; `af3f804` added
//!   the sentinel block, which the subject declares and this module never hard-codes.
//! - [`endpoint`] — confirming which model actually answered, because LM Studio silently serves a
//!   request that names a model it does not have.
//! - [`verify`] — SPEC §8's contract, and interpreters probed by executing.
//! - [`result`] — SPEC §11's metrics and RUNMETA.
//!
//! It is a library as well as a binary so the driver can be exercised against
//! `src/bin/fake_subject.rs` from `tests/`, with no model in the loop.

pub mod delivery;
pub mod driver;
pub mod endpoint;
pub mod env;
pub mod result;
pub mod verify;
