# selfhost-queue.ps1 - put SELFHOST-P7's five tasks on the board.
#
# Every premise in these prompts was checked against the tree at a0054e7; see
# research/SELFHOST-P7-the-next-five-tasks.md for what was verified and what was
# rejected. Each prompt names the FILE, the EXACT signature and a REAL neighbour
# to copy, because 50.5% of the Change phase's tool calls are read_file and 65%
# of those are re-reads (F774) - anything the prompt settles is a round saved.
#
# This script only calls `abcc task`. It runs no attempt, lands nothing, records
# no review, and never touches the GPU.
#
#   RUN IT FROM D:\dev\abcc. A different working directory gets a different,
# empty log and no error.

$ErrorActionPreference = 'Stop'

$abcc = Join-Path (Get-Location) 'target\release\abcc.exe'
if (-not (Test-Path $abcc)) {
    throw "no binary at $abcc - run 'cargo build --release' from D:\dev\abcc first"
}

# The tree these prompts were written against. If HEAD has moved, the line
# numbers below may have too, and a prompt that names a line that moved is the
# t2598 defect again.
$writtenAgainst = 'a0054e7'
$head = (& git rev-parse --short HEAD).Trim()
if ($head -ne $writtenAgainst) {
    Write-Warning "these prompts were written against $writtenAgainst and HEAD is $head."
    Write-Warning 'check the line numbers each prompt cites before trusting them.'
}

$tasks = @(
    @{
        Title  = 'Seq::back saturating'
        Prompt = @'
In crates/abcc-core/src/seq.rs, add a method `Seq::back(self, n: u64) -> Seq` to the existing `impl Seq` block, beside `is_origin`. It moves a log position backwards by n and saturates at Seq::ORIGIN, so it never returns a position before the origin. Give it a doc comment in the house style and add a test.

The saturation is the whole point of the method and it is easy to get wrong: converting n with an `as` cast lets a negative position turn into a large positive one and walk straight past the clamp. crates/abcc-tui/src/reader.rs line 172 writes this calculation out by hand today, which is the behaviour to match.

Follow the conventions already in seq.rs.
'@
    },
    @{
        Title  = 'Outcome::is_unmeasured'
        Prompt = @'
In crates/abcc-core/src/outcome.rs, add a method `Outcome::is_unmeasured(&self) -> bool` to the existing `impl Outcome` block, beside `is_green` and `is_red`. It answers whether this outcome is the `Outcome::Unmeasured` variant - the state that `is_green` and `is_red` both deliberately return false for. Give it a doc comment in the house style and add a test.

Follow `is_green` and `is_red` directly above it, including the `#[must_use]`.
'@
    },
    @{
        Title  = 'Cause::name'
        Prompt = @'
In crates/abcc-core/src/attempt.rs, add a method `Cause::name(&self) -> &'static str` to the existing `impl Cause` block. It returns the bare variant name: "fresh", "retry", "rescope", "edit", "replay". Give it a doc comment in the house style and add a test covering all five variants.

`AttemptOutcome::name` in the same file does exactly this for the other enum - follow it, including the `#[must_use]` and the `&'static str` return.

Add the method only. Do not change any existing caller.
'@
    },
    @{
        Title  = 'abcc --version via CliError'
        Prompt = @'
Add a --version flag to the abcc binary, through the argument surface rather than around it. `--help` is already done this way and is the pattern to follow. There are four seams and all four are needed:

1. crates/abcc/src/cli.rs, the `CliError` enum (around line 200): add a third variant `Version` beside `Help` and `Usage`. It needs its own thiserror `#[error(...)]` attribute like the two above it.
2. crates/abcc/src/cli.rs, `parse()` (around line 307): return `Err(CliError::Version)` when an argument is `--version`, beside the existing `--help` check.
3. crates/abcc/src/lib.rs, `AppError::exit_code()` (around line 100): map it to 0, the way `CliError::Help` is. --version is not a failure.
4. crates/abcc/src/main.rs, the match in `main()` (around line 16): print `abcc` and the version from `env!("CARGO_PKG_VERSION")` to `out`, and return `ExitCode::SUCCESS`.

Do not read `std::env::args()` inside `main` - `parse` is the one place that reads the argument surface.

Seams 3 and 4 both have a catch-all arm, so leaving either one out still COMPILES and still passes the tests while the flag is broken: it would print to stderr and exit 1. So the test you add must assert the exit code is 0 and that the version is written to the output, not just that `parse` returns the new variant.
'@
    },
    @{
        Title  = 'Seq::forward saturating'
        Prompt = @'
In crates/abcc-core/src/seq.rs, add a method `Seq::forward(self, n: u64) -> Seq` to the existing `impl Seq` block, as the symmetric partner of `back`. It moves a log position forwards by n and saturates at i64::MAX rather than overflowing. Give it a doc comment in the house style and add a test.

crates/abcc-tui/src/feed.rs computes this by hand at line 110, `Seq::new(self.head().get() + 1)`, which is the behaviour to match for n = 1.

Name it `forward`. It must not be called `next`: clippy::should_implement_trait fires on a method named `next`, and this workspace is graded by `cargo clippy --all-targets -- -D warnings`.
'@
    }
)

Write-Host ''
Write-Host "Creating $($tasks.Count) tasks on the board." -ForegroundColor Cyan
Write-Host ''
foreach ($t in $tasks) {
    Write-Host "  $($t.Title)"
    & $abcc task $t.Prompt --title $t.Title
    if ($LASTEXITCODE -ne 0) { throw "abcc task failed for '$($t.Title)'" }
}

Write-Host ''
Write-Host 'On the board now:' -ForegroundColor Cyan
& $abcc board
Write-Host ''
Write-Host 'Task 5 (Seq::forward) shares the impl Seq block with task 1 - land task 1 first.' -ForegroundColor Yellow
Write-Host 'land and review are the operator''s. An agent running review fabricates the measurement.' -ForegroundColor Yellow
