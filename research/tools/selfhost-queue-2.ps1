# selfhost-queue-2.ps1 - wave 2, aimed at the two walls wave 1 actually hit.
#
# Wave 1 (t13051-t13055) landed one of five. The four losses were not the model
# failing at the work:
#
#   Seq::back              CORRECT, 681/681, refused at `standard` on a clippy lint
#   Outcome::is_unmeasured NEVER ATTEMPTED AN EDIT - read until the 16,384-token
#   Cause::name            completion cap cut it mid-write. Reading was 100% of
#                          the Change phase, which is F774 at full strength.
#   abcc --version         4 edits, then context_overflow at 40,828 of 40,960 -
#                          and that was the PROMPT's fault: four seams, three
#                          files, against the one-file envelope that works.
#
#   SO THESE THREE PROMPTS CHANGE TWO THINGS, DELIBERATELY, AND NO MEASUREMENT
# MAY BE CLAIMED FROM THE DIFFERENCE. `judge.rs` says it best about its own
# probe: "a probe that changes two things at once measures neither." The goal
# here is landable changes, not a reading, so both levers are pulled at once:
#
#   1. THE SURROUNDING CODE IS IN THE PROMPT, VERBATIM. Both truncated attempts
#      had a Recon brief that named the file and quoted the lines, and the Change
#      phase re-read anyway. A prompt that carries the bytes leaves less to fetch.
#      (This is P4's Proposal 1 done by hand, at the task level, for three tasks.
#      It is NOT the engine change - that is still David's to rule on.)
#   2. THE STANDARD IS NAMED. Ten of the twenty refusals on this log are one rung
#      from landing and ALL TEN refused at `standard`; a third are pure
#      formatting. F673's repair put fmt and clippy inside `diagnostics`, and F786
#      measured that the tool has never been called once under that summary. So
#      the prompt says the criterion out loud. W7 prices this weakly (39/50, then
#      0/50) and F782 at 1/33 - it is a cheap lever, not a fix.
#
# It only calls `abcc task`. It runs nothing, lands nothing, reviews nothing.
#
#   WARNING - POWERSHELL MANGLED THE THIRD PROMPT AND abcc PRINTED ITS USAGE.
# Tasks 1 and 2 were created; task 3 was rejected at the argument boundary, and
# the identical string handed to abcc from Python's subprocess, with no shell in
# the way, was accepted immediately (t13606). The prompt was never the problem.
# If a task here is refused, do not edit the prompt - pass it from Python:
#
#   subprocess.run([exe, 'task', prompt, '--title', title])
#
# A future wave should be authored in Python for this reason; every other tool
# in research/tools already is.
#   RUN IT FROM D:\dev\abcc.

$ErrorActionPreference = 'Stop'

$abcc = Join-Path (Get-Location) 'target\release\abcc.exe'
if (-not (Test-Path $abcc)) {
    throw "no binary at $abcc - run 'cargo build --release' from D:\dev\abcc first"
}
$writtenAgainst = 'a0054e7'
$head = (& git rev-parse --short HEAD).Trim()
if ($head -ne $writtenAgainst) {
    Write-Warning "these prompts quote source as of $writtenAgainst and HEAD is $head."
    Write-Warning 'the embedded snippets may be stale - check before trusting them.'
}

$standard = @'

Before you finish, check your own work with the `diagnostics` tool. It runs the
same commands the gate grades you with: `cargo check --all-targets`, then
`cargo fmt --check`, then `cargo clippy --all-targets -- -D warnings`. This
workspace denies `clippy::all` and warns `clippy::pedantic`, and the gate passes
`-D warnings`, so a pedantic lint fails the run. Formatting and lints are graded;
fix what the tool reports before you report done.
'@

$tasks = @(
    @{
        Title  = 'Outcome::is_unmeasured (wave 2)'
        Prompt = @'
In crates/abcc-core/src/outcome.rs, add a method `Outcome::is_unmeasured(&self) -> bool` to the existing `impl Outcome` block, after `is_red` and before `rung`. It answers whether this outcome is the `Outcome::Unmeasured` variant - the state that `is_green` and `is_red` both deliberately return false for. Give it a doc comment in the house style, and add a test.

Here is the whole of that impl block as it stands, so you do not need to read the file to place the method:

```rust
impl Outcome {
    /// Green means: a measurement exists, and it says nothing failed.
    #[must_use]
    pub fn is_green(&self) -> bool {
        match self {
            Outcome::Measured(m) => m.exit == 0,
            Outcome::Unmeasured { .. } => false,
        }
    }

    /// Red means: a measurement exists, and it says something failed. An absent
    /// measurement is not red either - that is the whole point of the type.
    #[must_use]
    pub fn is_red(&self) -> bool {
        match self {
            Outcome::Measured(m) => m.exit != 0,
            Outcome::Unmeasured { .. } => false,
        }
    }

    #[must_use]
    pub fn rung(&self) -> &str {
        match self {
            Outcome::Measured(m) => &m.rung,
            Outcome::Unmeasured { rung, .. } => rung,
        }
    }
```

The enum is `Outcome::Measured(Measurement)` and `Outcome::Unmeasured { rung: String, why: Why }`.

Make the edit with apply_patch early rather than reading more of the file first. The placement above is all you need.
'@
    },
    @{
        Title  = 'Cause::name (wave 2)'
        Prompt = @'
In crates/abcc-core/src/attempt.rs, add a method `Cause::name(&self) -> &'static str` to the existing `impl Cause` block, after `spends_retry_budget`. It returns the bare variant name: "fresh", "retry", "rescope", "edit", "replay". Give it a doc comment in the house style, and add a test covering all five variants.

Here is the enum and the whole of that impl block as it stands, so you do not need to read the file to place the method:

```rust
pub enum Cause {
    Fresh,
    Retry { of: AttemptId },
    Rescope { of: AttemptId },
    Edit { of: AttemptId },
    Replay { of: AttemptId },
}

impl Cause {
    /// The attempt this one forked from, if any.
    #[must_use]
    pub fn parent(&self) -> Option<AttemptId> {
        match self {
            Cause::Fresh => None,
            Cause::Retry { of }
            | Cause::Rescope { of }
            | Cause::Edit { of }
            | Cause::Replay { of } => Some(*of),
        }
    }

    /// Whether this attempt counts against the retry budget. ...
    #[must_use]
    pub fn spends_retry_budget(&self) -> bool {
        matches!(self, Cause::Retry { .. })
    }
}
```

`AttemptOutcome::name` further down the same file does exactly this job for the other enum; match its shape.

Make the edit with apply_patch early rather than reading more of the file first. The placement above is all you need.
'@
    },
    @{
        Title  = 'Seq::back (wave 2, lint named)'
        Prompt = @'
In crates/abcc-core/src/seq.rs, add a method `Seq::back(self, n: u64) -> Seq` to the existing `impl Seq` block, after `is_origin`. It moves a log position backwards by n and saturates at Seq::ORIGIN, so it never returns a position before the origin. Give it a doc comment in the house style, and add a test.

Here is the whole of that impl block as it stands, so you do not need to read the file to place the method:

```rust
impl Seq {
    /// The position before the first event. ...
    pub const ORIGIN: Seq = Seq(0);

    #[must_use]
    pub const fn new(raw: i64) -> Self {
        Self(raw)
    }

    #[must_use]
    pub const fn get(self) -> i64 {
        self.0
    }

    /// Returns true if this is [`Seq::ORIGIN`].
    #[must_use]
    pub const fn is_origin(self) -> bool {
        self.0 == Seq::ORIGIN.get()
    }
}
```

`Seq` is a newtype over `i64`: `pub struct Seq(i64)`, so the field is `self.0`.

Two things about the conversion, both of which have already cost an attempt on this task:

1. Saturation is the whole point. An `as` cast lets a value larger than i64::MAX turn into a negative and walk straight past the clamp, so convert with `i64::try_from(n)` and treat failure as "further back than the origin", which is ORIGIN.
2. `cargo clippy --all-targets -- -D warnings` rejects a `match` used purely to unwrap that conversion - `clippy::manual_let_else` - so write it as a let-else:

```rust
let Ok(n) = i64::try_from(n) else { return Seq::ORIGIN };
```

Make the edit with apply_patch early rather than reading more of the file first. The placement above is all you need.
'@
    }
)

Write-Host ''
Write-Host "Creating $($tasks.Count) wave-2 tasks." -ForegroundColor Cyan
foreach ($t in $tasks) {
    Write-Host "  $($t.Title)"
    & $abcc task ($t.Prompt + $standard) --title $t.Title
    if ($LASTEXITCODE -ne 0) { throw "abcc task failed for '$($t.Title)'" }
}
Write-Host ''
& $abcc board 2>&1 | Select-String -Pattern 'wave 2'
Write-Host ''
Write-Host 'Two levers were pulled at once on purpose. No measurement may be claimed' -ForegroundColor Yellow
Write-Host 'from the difference against wave 1 - the goal is landable changes.' -ForegroundColor Yellow
