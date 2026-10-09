# ABCC 2.0 — the research record

This is the research behind [**abcc**](https://github.com/mrdushidush/abcc), a Rust
command center for running local model workers against real repository tasks.
abcc's source comments cite this repository by finding id (`F146`), by
workstream (`W3`) and by decision record (`ADR-0004`); this is where those
citations resolve.

It holds **849 numbered findings (F1–F849)**, **25 architecture decision
records**, the benchmark corpora, and the harness that ran them. Most of the
prose was written by Claude Code sessions executing a research brief for David,
who made the rulings; a ruling is dated where it was made.

## Where to start

| If you want | Read |
|---|---|
| the architecture, in two pages | [`research/SUMMARY.md`](research/SUMMARY.md) |
| why each decision was taken, and what would overturn it | [`research/decisions/`](research/decisions/) — ADR-0001 to ADR-0025 |
| the plan the code was built from | [`PLAN.md`](PLAN.md) |
| the current plan, and the verdict on the agent loop | [`PLAN-TOOL.md`](PLAN-TOOL.md) |
| the newest measurement | [`research/TOOL-S6-the-ship-bench.md`](research/TOOL-S6-the-ship-bench.md) |
| the brief that started it | [`RESEARCH_BRIEF.md`](RESEARCH_BRIEF.md) |
| one finding, by number | `python research/tools/fledger.py build` once, then `python research/tools/fledger.py show F847` |

## How a finding works

A finding is defined once, in the prose of the document that measured it.
`research/findings.sqlite` is an index **derived** from the Markdown by
`research/tools/fledger.py build` (with `fparse.py`). It is not committed;
build it once after cloning, with Python 3 and nothing else.

Nothing here is rewritten after the fact. When a later measurement corrects an
earlier one, the correction is itself a new finding, and the relation between
the two — `refines`, `supersedes`, `answers` or `retracts` — is recorded with
the sentence that proves it in
[`research/findings-authored.tsv`](research/findings-authored.tsv), the one
authored input to the ledger. So an old document can say something that is no
longer true: **before quoting a finding, ask the ledger whether a later one
corrected it** (`fledger.py show` and `fledger.py chain`).

## What is where

| Path | What |
|---|---|
| `research/` | the workstream documents (W1–W13 from Phase 1; CONSOLE, GATE, FLEET, LINEAGE, SELFHOST, PILOT, DEBUG and TOOL from building it), the ADRs, the ledger |
| `research/spikes/` | the probes behind the findings, with their raw results |
| `research/tools/` | the scripts that read runs, logs and the ledger |
| `corpus/suites/` | the benchmarks: `q56` (claudette's hidden-test battery), `u40` and `u100` (ABCC v1's), `k`, `od`, and `r` — fourteen real defects in claudette at a pinned commit, each graded by its author's hidden test |
| `corpus/subjects/` | the binaries a run measured, pinned by commit |
| `harness/` | `w8-run`, the Rust runner that turns a corpus and a subject into graded cells, and the overnight scripts |
| `prestudy/` | Phase 0: dossiers on the predecessors, and datasets extracted from them, including ABCC v1's last database dump |
| `runs/` | a deliberate sliver of raw run output — the hardware probe, the run manifests, one fleet probe. The rest (3.8 GB) is not in git |

## Read it with these in mind

- **One machine.** Every measurement this research took was on one Windows 11
  box with one RTX 5060 Ti 16 GB, serving through LM Studio, mostly with
  `qwen3.6-35b-a3b-mtp@iq3_s`. The predecessors' datasets in `prestudy/` came
  from their own hardware, which each dossier names.
- **Attributable, not reproducible.** A run records its seed and its
  configuration, so a number can be traced to what produced it. A seed does not
  make this serving stack deterministic, so re-running is not guaranteed to give
  the same number. The documents say *attributable*, and mean it.
- **The paths are the author's.** Scripts, subjects and fixtures name absolute
  paths such as `D:/dev/claudette`. To run anything here, those need pointing at
  your own checkouts.
- **Some text here is hostile on purpose.** The W7 spikes carry prompt-injection
  probes and fabricated credential shapes; none is a live secret. The R suite's
  security cards (`edit_10`, `sec_04`, `sec_06`) describe defects in claudette
  that were fixed in claudette 0.18.1 before this repository was published.

## Related repositories

- [`abcc`](https://github.com/mrdushidush/abcc) — the tool this research built.
- [`claudette`](https://github.com/mrdushidush/claudette) — the predecessor
  agent, the source of Q56 and the R suite's subject.
- [`agent-battle-command-center`](https://github.com/mrdushidush/agent-battle-command-center)
  — ABCC v1, the source of the `u40` and `u100` suites.

## Licence

- **Code** — everything under `corpus/` and `harness/`, and every source file
  anywhere (`*.py`, `*.rs`, `*.sh`, `*.ps1`, `*.js`, `*.mjs`, `*.ts`): `MIT OR
  Apache-2.0`, at your option ([`LICENSE-MIT`](LICENSE-MIT),
  [`LICENSE-APACHE`](LICENSE-APACHE)). The R suite's fixtures and patches are
  claudette's code, which carries the same licence.
- **Prose and data** — the Markdown documents and the data files outside
  `corpus/` (`*.tsv`, `*.csv`, `*.json`, `*.jsonl`, `*.txt`, `*.log`,
  `*.sql.gz`): [CC BY 4.0](LICENSE-CC-BY-4.0). Reuse them, and say where they came from.
