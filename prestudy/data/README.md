# `prestudy/data/`

Extracted datasets for brief 4.2. **Read `../data-assets.md` first** — it says what each of these
is worth, which is not the same as what it contains.

Everything here is plain TSV/CSV except one verbatim `pg_dump`. No tooling required.

## Claudette / Q56

| File | What |
|---|---|
| `q56-manifest.tsv` | The frozen 56-task corpus definition. `task, lang, type, fixture, timeout_s`. |
| `q56-results.csv` | The published results table: 36 runs, 16 model/quant configurations, 34 in the ranking. Carries `engine`, `kv`, `ctx` and `vram_mib` per row — **only compare rows whose `kv` and `ctx` match**. |
| `q56-runmeta.tsv` | Per-run configuration provenance. The `provenance` column separates **measured** from **inferred**; never cite an inferred row as evidence. Its header comment is the best short list in the family of what silently invalidates a local-inference benchmark. |
| `battery-scores-long.tsv` | 84 `SCORES-*.tsv` files unpivoted. 1,869 rows spanning both batteries (A–K core-50 and Q01–Q56). Note `status` distinguishes `FAIL` from `FAIL(TIMEOUT)` from `INFRA` — do not collapse them. |
| `battery-telemetry.tsv` | **Derived here; exists nowhere else.** One row per task run, mined from the `⚡ iter=… in=… out=…` and `### EXIT=… ELAPSED=…` lines in 132 log directories. 3,593 rows, 3,150 with token counts. Blank `iters`/`in_tokens`/`out_tokens` mean the run predates that log line or died before emitting it. |

Source: `D:\dev\claudette`, branch **`battery/q50-quality-corpus`** (`43d6b34`) for the corpus and
published tables, working tree for the logs. Not on `main`.

## ABCC v1

| File | What |
|---|---|
| `abcc-40task-corpus.tsv` | The 40-task C1–C9 set, recovered from `ollama-stress-test-40.js`. `validation_command` is the deterministic per-task verifier. |
| `abcc-40task-results-2026-02-20.tsv` | 39/40, single failure `flatten_list` at C5. This is the "88%"/"39/40" figure the brief cites — a **pass rate**, not a routing rate. |
| `abcc-100task-results.tsv` | 7 runs of the 100-task suite, long form. `run` is the source file's timestamp. The `2026-02-26T11-04-01` run is an infrastructure collapse (72 errors, 0 genuine failures) — exclude it from any average. |
| `abcc-postgres-2026-02-14.sql.gz` | The last surviving `pg_dump`, verbatim. 12 tables. Scanned for credentials before committing. |
| `abcc-db-tasks-2026-02-14.csv` | 218 rows. `complexity` is 5.0 (the default) on 137 of 182 scored rows; `complexity_reasoning` is 18% populated. |
| `abcc-db-execution-logs-2026-02-14.csv` | 5,977 rows. `duration_ms` is real (89% populated, tool-execution latency). Token and `model_used` columns were dropped because they are 0% populated in the source. **10.5% of `action` values fall outside the 7-tool vocabulary** — see `../data-assets.md` §5.4. |
| `abcc-db-training-datasets-2026-02-14.csv` | 154 rows, but only 5 have a Claude side and none have tokens or quality scores. |

Source: `D:\dev\agent-battle-command-center` at `d5528ea`.

## StealthForge (archive repo)

| File | What |
|---|---|
| `stealthforge-mission-reports.tsv` | 59 completed missions. **34 carry both `gate_score` (self-scored critic panel) and `independence_score` (separate reviewer process).** The paired subset is the evidence for `../archive-repos.md` §2. |

Source: `D:\dev\_archive\abcc_projects\abcc_projects\stealthsambaV2\generated\`. See
`../archive-repos.md` §1.2 for the custody warning — that working tree has no git history.
