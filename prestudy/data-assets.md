# Data Assets

**Purpose:** brief 4.2 — dump, characterize and recover every dataset the three source repos
produced, in a portable form, and say how usable each one actually is.

**Extracted to:** `prestudy/data/` (1.9 MB, 13 files, all plain TSV/CSV plus one verbatim
`pg_dump`). Nothing there needs tooling to read.

**Written:** 2026-08-07. Sources read at ABCC v1 `d5528ea` · Claudette `fc1ea22` and branch
`battery/q50-quality-corpus` `43d6b34` · battle-command-forge `d6c1601` · plus two archived repos
the brief does not know about (§6).

---

## 0. The verdict in one table

| Asset | Real? | Rows | Usable for | Verdict |
|---|---|---|---|---|
| **Q56 corpus + published results** | yes | 56 tasks / 36 runs / 16 models | W1, W2, W6, W8, W11 | **The load-bearing asset.** Everything else is supporting. |
| **Claudette battery telemetry** | yes, but nobody had aggregated it | 3,593 task runs | W1, W2, W11 | **Newly extracted here.** 117.6M prompt tokens of evidence. |
| **Battery per-task scores (all eras)** | yes | 1,869 | W6, W8 | Long-form now; was 84 loose TSVs. |
| **ABCC 100-task suite + results** | yes | 481 | W8 | **The brief does not mention this.** Closer to 2.0's workload than the 40. |
| **ABCC 40-task corpus + results** | yes | 40 + 40 | W8 (calibration floor only) | Recovered whole, including verifiers. Saturated. |
| **ABCC PostgreSQL** | **mostly not** | 218 tasks / 5,977 log rows | one real finding | **9 days, not months. Token and cost columns are 0% populated.** |
| **StealthForge mission corpus** | yes | 59 missions, 34 paired | **W6 — decisively** | **New source.** Measured gate inflation, one-directional. |

**If you read one thing:** §5.2. A self-scored LLM critic panel over-scored its own output on
**34 out of 34** paired missions, median **+3.65** points. Not once did the independent reviewer
score higher. That is the empirical answer to the sharpest open question in the inheritance map.

---

## 1. Q56 — Claudette's quality battery

The brief calls it "56 tasks across 11 surfaces and 12 task types, a shell verifier per task, no
LLM judge, 131 configurations, frozen core". That is right in spirit and wrong in several
specifics that matter for reproducing it.

### 1.1 Where it actually lives

**Not on `main`.** The entire Q-series corpus — 56 fixtures, 56 prompts, 56 hidden verifiers, 56
reference solutions, `manifest-q50.tsv`, and every `SCORES-q50-*.tsv` — lives only on the
unmerged branch **`battery/q50-quality-corpus`** (head `43d6b34`, pushed to `origin`).

`main` at `fc1ea22` carries a **different, older battery**: the A–K lettered core-50 plus the
8-task K extension (58 prompts, 58 verifiers, `manifest.tsv` + `manifest-ext.tsv`). That is the
battery the brief's "131 configs / `--jinja` parity" claims come from. The two are separate
instruments with separate manifests that happen to share one runner.

A further trap: `D:\dev\claudette\.git\info\exclude` contains `/runs/`, a **local-only, never
committed** exclusion. On `main` this makes `git status` report clean while 84 SCORES files and
132 log directories sit untracked in the working tree. Anyone auditing the repo from `git status`
alone will conclude the campaign artifacts do not exist. They do; they are on the branch.

**Consequence for Phase 1: to reproduce Q56 you must check out the branch.** A clone of `main` is
not enough and gives no error saying so.

### 1.2 What the corpus is

56 tasks, `manifest-q50.tsv`, extracted to `prestudy/data/q56-manifest.tsv`.

- Languages: rust 12, python 13, js 9, ts 8, shell 8. Deliberately scoped to what the author's box
  can actually build — go, java, kotlin, php, ruby and C++ were **dropped rather than faked via
  transcript-grep**, which is the single most important methodological decision in the whole
  family.
- Types: implement-spec 12, boundary 7, bugfix 6, api-misuse 6, error-handling 5, refactor 4,
  multi-file 4, perf 4, concurrency 2.
- Method: each task is a small buildable fixture the model sees, a prompt in a real user's voice
  that states the goal and **does not enumerate edge cases**, and a verifier that **injects hidden
  reviewer tests at grade time** and runs them against the model's mutated copy. It grades what
  the model did to the code, never what it said.
- Authoring gate (`gate_q50.sh`): a task may not enter the manifest until the untouched fixture
  **fails** the verifier and fixture-plus-reference-solution **passes** it. Test-first, enforced.

### 1.3 What the results are

`prestudy/data/q56-results.csv` — 36 runs across 16 model/quant configurations, 34 in the ranking
table. Columns: model, params, quant, GiB, run_tag, date, score, tasks, wall_clock_s, engine,
vram_mib, ctx, kv, parallel, in_ranking_table, failed_tasks.

`prestudy/data/q56-runmeta.tsv` — 55 rows of per-run configuration provenance, with a
`provenance` column separating **measured** from **inferred**. This file exists because the KV
cache type silently flipped from q8_0 to f16 mid-campaign and runs were compared across it
without anyone knowing. Its header carries the lesson verbatim: *"A held-constant nobody measures
is not held."* Three uncontrolled variables were found this way — KV type, CPU/GPU expert split,
and the LM Studio llama.cpp runtime, which auto-updated itself to 2.27.1 at 01:21 on 2026-07-26
between two runs of the same model.

**That file is the most directly reusable artifact in the entire prestudy for W1 and W2.** It is a
list of the things that will silently invalidate a local-inference benchmark, written by someone
who got burned by each of them.

### 1.4 Three corrections the brief needs

1. **The champion changed, and the brief still names the old one.** As of `2a6acea`
   (2026-07-25/26), the crowned model is **`google/gemma-4-26b-a4b-qat`** — Q4_0, 13.45 GiB,
   median **55/56** over three runs (55/54/55). The previous champion,
   `qwen3.6-35b-a3b-mtp@iq3_s` (byteshape 3.06 bpw), sits at 48–52/56. Every reference in the
   brief and the dossiers to "the 35B-A3B base agent" describes a superseded configuration. The
   runner-up is `unsloth/gemma-4-26B-A4B-it` at 54/56.

2. **The "consistent failure set" does not exist, and the corpus documents its own retraction.**
   The frozen record named Q03/Q05/Q25/Q51/Q52 as stable champion failures. Over six full runs the
   aggregate was rock-stable (49, 50, 50, 50, 50, 50) but **the identity of the failing tasks
   rotates**: 12 distinct tasks failed at least once, 44 never failed, and only Q03 failed all
   six times. The stable-set reading was a 3-sample artifact and the subset screen built on it
   misfired twice. This is a model at a stable competence level with a pool of borderline tasks
   resolving stochastically — and it is a direct warning to W6 and W8 against any per-task claim
   drawn from a single run.

3. **Difficulty and discrimination are close to orthogonal.** Measured: a hardening batch that
   added difficulty to 16 tasks moved the champion 46 → **47**, i.e. nothing. Meanwhile the crown
   holder swept the genuinely hard tail (Q53–Q56) while its most reliable failure was a trivial
   empty-range guard. W8 should not try to build a harder corpus; it should build a
   **trap-denser** one.

### 1.5 Publication posture

Decided by David 2026-08-01, `HELDOUT-SPLIT.md`: publish everything, date the contamination.
**Contamination date 2026-07-25** — the branch has been publicly cloneable with all fixtures, all
hidden verifiers and all reference solutions since then. Every model in the table was released
before that date, so all 36 runs stand; any model released after it must be treated as
potentially contaminated. A sealed successor corpus (`T2.md`, tier 2) was started 2026-07-27 and
is being built private from the first commit.

**The design lesson, stated in the file and worth carrying into 2.0 verbatim:** decide the
publication posture before the first push, not after 36 runs. A public repo is public in every
branch.

---

## 2. Claudette battery telemetry — newly extracted

Every task log in the campaign ends with a line the harness never aggregated:

```
⚡ iter=7 in=38041 out=2137
### EXIT=0  ELAPSED=43s
```

3,593 task logs across **132 run tags** carry the exit/elapsed pair; **3,150** also carry
iterations and token counts. Nothing in any repo reads them. Mined into
`prestudy/data/battery-telemetry.tsv` (198 KB, one row per task run).

Headline numbers across the whole campaign:

| Measure | Value |
|---|---|
| Total prompt tokens | **117.6 M** |
| Total output tokens | **4.2 M** |
| **Prefill : decode ratio** | **27.8 : 1** |
| Iterations per task | median 5, p90 10, max 41 |
| Prompt tokens per task | median 26,938, p90 60,263, max 597,513 |
| Output tokens per task | median 828, p90 2,883, max 28,140 |
| Q-series subset | 2,079 runs, median 30,177 prompt tokens, median 5 iterations |

**Why this matters immediately.** `questions.md` §3.3 item 11 asks whether prefix caching is worth
exploiting and notes nothing in the family does. This dataset answers the sizing half of that
question without running anything: the workload is **28 parts prefill to 1 part decode**. On a
factory workload with four builders sharing a near-identical system prompt, prefill is not a
tuning detail — it is essentially the whole cost. That reframes W2's prefix-caching item from
"investigate" to "quantify the hit rate", and it sharpens the conflict flagged in the same item,
because Claudette's `tools` array is mutable per turn and a changed array invalidates the prefix.

The median of 5 iterations per task also gives W11 a real prior for fan-out sizing, and the
p90-of-10 / max-of-41 tail says the distribution is long — a scheduler that budgets on the mean
will be wrong.

**Caveat:** these are one-shot CLI runs of `claudette "<prompt>"` under a battery driver. They are
not interactive sessions, and 2.0's differentiator is interactive operation. Treat the ratio as a
strong prior, not a measurement of 2.0's workload.

---

## 3. Battery scores, long form

84 `SCORES-*.tsv` files spanning both eras (A–K core-50 and Q01–Q56) unpivoted into one table:
`prestudy/data/battery-scores-long.tsv`, 1,869 rows.

Columns: `run_tag, task, lang, type, status, elapsed_s, exit_code, verdict`.

Status distribution: PASS 1,480 · FAIL 343 · FAIL(TIMEOUT) 23 · INFRA 12 · PASS(TIMEOUT) 11.

The `INFRA` and `*(TIMEOUT)` statuses are worth noting for W8: the harness distinguishes *the
model failed* from *the harness failed* from *the model ran out of clock*, and 46 of 1,869 rows
(2.5%) are one of the latter two. Any successor harness that collapses those into FAIL will
mis-attribute about one run in forty.

---

## 4. ABCC v1 evaluation corpora

### 4.1 The 40-task set — recovered whole

Definition: `scripts/ollama-stress-test-40.js`. Extracted to
`prestudy/data/abcc-40task-corpus.tsv` — 40 rows of `complexity, task, description,
validation_command`.

The `validation_command` field is the important recovery. Each task ships a Python one-liner that
imports the generated module and asserts on it, e.g.

```
from tasks.c9_linked_list import SortedList; s=SortedList(); s.insert(3); s.insert(1);
s.insert(2); assert s.to_list()==[1,2,3]; assert s.length()==3; ...
```

That is a deterministic per-task verifier — the same idea Q56 later industrialised. **ABCC v1 had
no LLM judge either.** The dossier's framing of ABCC as architecturally casual is right about the
orchestration and wrong about the eval: its verification was honest from the start.

Results: `prestudy/data/abcc-40task-results-2026-02-20.tsv`. **39/40 at 2026-02-20**, single
failure `flatten_list` at C5, total wall clock 1,307 s. Per-complexity: C1–C4 and C6–C9 all
perfect, C5 4/5.

**This confirms the brief's correction — 88% (later 39/40 = 98%) is a pass rate, not a routing
rate — and adds that the corpus is saturated.** Every band above C5 passes. It cannot rank
anything. Its remaining use is as a floor: if a 2.0 candidate cannot clear 39/40 here, stop.

### 4.2 The 100-task suite — the brief does not mention it

`scripts/ultimate-100-task-test.js`, 3,521 lines, with **seven recorded runs** in
`archive/ultimate-100-results-*.json`. Extracted long-form to
`prestudy/data/abcc-100task-results.tsv`, 481 rows.

| Run | Rows | Pass | Fail | Error | Rate |
|---|---|---|---|---|---|
| 2026-02-21T18:17 | 90 | 82 | 4 | 4 | 91% |
| 2026-02-22T00:06 | 90 | 86 | 4 | 0 | 96% |
| 2026-02-22T19:03 | 90 | 79 | 3 | 8 | 88% |
| **2026-02-24T18:14** | **100** | **95** | **5** | **0** | **95%** |
| 2026-02-24T20:09 | 1 | 0 | 0 | 0 | aborted |
| 2026-02-24T21:10 | 20 | 18 | 2 | 0 | 90% |
| 2026-02-26T11:04 | 90 | 18 | 0 | 72 | 20% (infra collapse) |

Structure — and this is why it matters:

- Section 1: React app (20) — 10 pre-decomposed, 10 CTO-decomposed
- Section 2: landing pages (15) — 3 sites × 5 pages
- Section 3: web servers (25) — 13 Python, 12 Node stdlib APIs
- Section 4: security (20) — 10 secure-coding, 10 bug fixes
- Section 5: bonus (20) — 5 TS, 5 Go, 5 Python data, 5 mini-projects

Categories carried per row: react, landing, py_api, node_api, security, bugfix, typescript, go,
py_data, mini. Complexity C5–C8. Rows carry a `taskId` UUID that joins to the Postgres `tasks`
table.

**This is the closest thing in the family to David's stated target workload.** §17 Q2 answered
"repository work plus legacy review plus general-purpose coding". The brief says the gap is total
— "ABCC's 40 tasks are self-contained algorithms, BCF's missions are greenfield generation, and
only Q56's I-series and J-series touch real repository work". The 100-task suite is multi-file,
multi-language, has a security and bug-fix section, and includes decomposition as a measured
variable (`ctoGenerated`, `retriesSaved`). W8 should start here, not from scratch.

**Caveat:** it is a *generation* suite, not a repo-work suite — it builds new projects rather than
modifying existing ones. And the 2026-02-26 run shows how fragile it is: 72 errors out of 90 with
zero genuine failures, i.e. total infrastructure collapse recorded as a benchmark result.

---

## 5. ABCC v1 PostgreSQL — the asset is not there

The brief asks for "months of real execution logs with per-tool-call timing, token usage and
cost, plus collected training data". Here is what survives.

### 5.1 Custody

**The live database is gone.** `docker volume ls` shows one volume on this machine and it belongs
to an Algorand node; `abcc-postgres` and its `postgres_data` volume no longer exist. No `.dump`,
no `.sql`, no data directory anywhere on disk.

What survives is `backups/daily/` — **19 gzipped `pg_dump` snapshots, all from a 66-hour window
between 2026-02-12 10:13 and 2026-02-14 15:26**. One (`20260212_124702`) is empty, a failed
backup. The last one, `20260214_152639`, is a strict superset of the other 18, so the whole
surviving dataset is one file.

Copied verbatim to `prestudy/data/abcc-postgres-2026-02-14.sql.gz` (556 KB). Scanned for
credentials before committing — the only `password` hits are source-code strings inside the tasks
themselves.

### 5.2 Contents

12 tables. Row counts in the final snapshot:

| Table | Rows |
|---|---|
| execution_logs | 5,977 |
| tasks | 218 |
| training_datasets | 154 |
| task_executions | 45 |
| agent_types / agents | 3 / 4 |
| code_reviews | 2 |
| chat_messages, conversations, events, file_locks, task_memories | **0** |

Timestamp range: **2026-02-06 19:12 → 2026-02-14 20:17. Nine days, not months.**

### 5.3 Field population — the columns exist, the data does not

| Column | Populated |
|---|---|
| `execution_logs.duration_ms` | 5,344 / 5,977 (89%) |
| `execution_logs.input_tokens` | **0 / 5,977 (0%)** |
| `execution_logs.output_tokens` | **0 / 5,977 (0%)** |
| `execution_logs.model_used` | **0 / 5,977 (0%)** |
| `execution_logs.thought` | **0 / 5,977 (0%)** |
| `tasks.api_credits_used` | 218 rows, **all 0.0000** |
| `tasks.time_spent_ms` | 218 rows, **all 0** |
| `tasks.complexity` | 182/218, but **137 of them are exactly 5.0** (the default) |
| `tasks.complexity_reasoning` | **39 / 218 (18%)** |
| `training_datasets.claude_output` | 5 / 154 (3%) |
| `training_datasets.claude_tokens` / `local_tokens` | **0 / 154** |
| `training_datasets.quality_score` | **0 / 154** |

**Per-tool-call token usage and cost were never written.** The schema has the columns; the writer
never filled them. The only real telemetry is `duration_ms` on tool calls — median 66 ms, p90
412 ms, max 6.9 s, summing to 0.3 h. That is tool-execution latency, not model latency.

Three consequences:

1. **W4 cannot recompute a routing rate from this database.** 75% of scored tasks carry the
   default complexity of 5.0, so complexity is not a measurement for most rows.
2. **`questions.md` §5 item 3's proposed remedy does not work.** It suggests recovering the
   router-versus-AI comparison by text-parsing `complexity_reasoning`. That column is 18%
   populated — 39 rows. Not enough to compare anything.
3. **`questions.md` §2 item 8 is now answered by circumstance.** "Is the ABCC Postgres extraction
   wanted at all?" — the extraction is done, it cost an afternoon, and it produced one finding
   (below) plus a schema worth reading. There is nothing further to extract because there is
   nothing further there. **Close the question; do not schedule the ambition.**

### 5.4 The one real finding: a measured tool-call malformation rate

`execution_logs.action` should be one of seven values: `file_read, file_write, file_edit,
file_list, shell_run, code_search, find_file`. In 5,977 rows:

- **630 (10.5%) are outside that vocabulary.**
- 306 are the literal string `unknown`.
- **324 are prompt-template leakage** — the model emitted the *instruction text* as the action
  name. The most common, 239 times, is:
  `"the action to take, only one name of [file_read, file_write, file_edit, file_list, shell_run,
  code_search, find_file], just the name, exactly as it's written."`

This is a hard, dated measurement of ReAct-style tool calling on a 7B, and it is the single most
useful thing in the database. It quantifies exactly the gap the brief names as "the biggest gap in
ABCC v1 and the highest-value thing in Claudette": roughly **one tool call in ten was
unparseable**, and half of those failures were the model reading its own prompt back.

It also gives W2 and W11 a baseline. Any 2.0 tool-calling design should be able to state its
malformation rate against this 10.5% figure and the 8GB-era 7B that produced it.

### 5.5 What was extracted

- `abcc-postgres-2026-02-14.sql.gz` — the verbatim dump, 556 KB
- `abcc-db-tasks-2026-02-14.csv` — 218 rows, 14 columns
- `abcc-db-execution-logs-2026-02-14.csv` — 5,977 rows, 8 columns (blob columns dropped)
- `abcc-db-training-datasets-2026-02-14.csv` — 154 rows, 10 columns

---

## 6. StealthForge — a data asset the brief does not know exists

While extracting, David pointed at two archived repos in
`D:\dev\_archive\abcc_projects\abcc_projects\`. Both are Rust, neither is a git checkout, and
together they sit in the family timeline **between BCF and Claudette**. The architectural
assessment is in `prestudy/archive-repos.md`; what follows is the data.

`stealthsambaV2/` — internally **StealthForge V1.2.2**, a 10-stage pipeline, 10,889 lines —
contains `generated/` with **64 completed missions, 59 carrying a `pipeline-report.json`**, and
**34 of those carrying an `independence-verdict.json`** from a *separate reviewer binary* run
over the same artifact.

Extracted to `prestudy/data/stealthforge-mission-reports.tsv`, 59 rows:
`output_slug, mission_id, mission, total_rounds, gate_passed, gate_score, compile_passed,
autofix_count, independence_score, independence_grade`.

### 6.1 The paired measurement

Computed from the 34 paired rows:

| Measure | Value |
|---|---|
| Mean inflation (internal gate − independent review) | **+5.63** |
| Median inflation | **+3.65** |
| Range | +1.08 to +9.84 |
| Missions where inflation > 2.0 | **32 / 34** |
| Missions where inflation > 4.0 | 16 / 34 |
| **Missions where the independent reviewer scored *higher*** | **0 / 34** |
| Independent grades | D 9 · C+ 8 · B− 8 · C 3 · B 3 · C− 1 · F 1 · A− 1 |

The repo's own `BENCHMARK.md` shows the same effect on the curated M1–M13 regression suite, where
the self-scored gate passed **13/13 at a mean 9.5/10** while the independent static reviewer graded
the same artifacts C+, C−, D and F — including **M11 at gate 9.8 / independent F (3.3)**, where the
tests did not compile at all.

**Zero of thirty-four is the number that matters.** A one-directional bias of that size is not
noise and cannot be tuned away by moving a threshold. It is what a critic panel scoring its own
output does.

### 6.2 Why this lands squarely on the inheritance map

`inheritance-map.md` §12 lists five genuinely open pieces. Number four is *"gate independence in
single player — ABCC dodged it with different providers, Q56 dodged it with hand-written
verifiers, BCF's formula reduces but does not remove it. Still the sharpest problem in the
design."*

This dataset is a measured answer to that exact question, from the same author, on the same class
of workload, using the same models. It says: the reduction BCF's formula achieves is not enough,
and the size of the residual bias is about **+3.7 points on a 10-point scale**.

It also explains the whole family's trajectory. StealthForge measured its own gate as inflated;
Q56 was then built with deterministic shell verifiers and **no LLM judge at all**. That is not a
stylistic preference. It is a conclusion someone reached by measuring.

### 6.3 The caveats, stated plainly

- The reviewer is itself partly an LLM. `independencev1` clamps LLM scores by static analysis, so
  it is *more* grounded, not *ground truth*.
- `independencev1`'s own calibration study (10 projects, cross-checked against Claude Opus 4.6
  reviews) reports **70% pass/fail agreement, 100% agreement on FAILs, mean absolute delta 0.68**,
  and documents its own failure mode: a **7.0 floor** where the LLM defaults to 7.0 when uncertain
  (Test Quality scored exactly 7.0 on 8 of 10 projects). So the reviewer under-discriminates in the
  middle of the range.
- Both effects push the same way: the reviewer is conservative and clusters at 7.0, the internal
  gate clusters at 9.5. The *direction* of the finding is safe. The exact magnitude is not.
- Sample is 34 missions from one author, one pipeline, one model family, April 2026.

---

## 7. What was extracted — `prestudy/data/`

| File | Rows | Size | Source |
|---|---|---|---|
| `q56-manifest.tsv` | 56 | 1.6 K | claudette `battery/q50-quality-corpus` |
| `q56-results.csv` | 36 | 6.1 K | same, `RESULTS-q56.csv` |
| `q56-runmeta.tsv` | 55 | 16.4 K | same, `RUNMETA.tsv` |
| `battery-scores-long.tsv` | 1,869 | 198.7 K | 84 `SCORES-*.tsv`, unpivoted |
| `battery-telemetry.tsv` | 3,593 | 198.0 K | **mined from 132 log dirs; new** |
| `abcc-40task-corpus.tsv` | 40 | 11.7 K | `ollama-stress-test-40.js` |
| `abcc-40task-results-2026-02-20.tsv` | 40 | 1.0 K | `ollama-stress-results-40.json` |
| `abcc-100task-results.tsv` | 481 | 39.4 K | 7 `ultimate-100-results-*.json` |
| `abcc-postgres-2026-02-14.sql.gz` | — | 555.7 K | last surviving backup, verbatim |
| `abcc-db-tasks-2026-02-14.csv` | 218 | 38.8 K | parsed from the dump |
| `abcc-db-execution-logs-2026-02-14.csv` | 5,977 | 774.6 K | parsed from the dump |
| `abcc-db-training-datasets-2026-02-14.csv` | 154 | 17.2 K | parsed from the dump |
| `stealthforge-mission-reports.tsv` | 59 | 12.2 K | **archive repo; new** |

Total 1.9 MB. Regeneration scripts are not committed — every file is either a verbatim copy or
was produced by a throwaway parse whose output is the artifact. The two non-trivial derivations
(battery telemetry, StealthForge pairing) are described precisely enough above to redo.

---

## 8. Corrections this document makes to the brief and the dossiers

1. **The Q56 champion is `google/gemma-4-26b-a4b-qat` at 55/56, not the 35B-A3B.** Crowned
   2026-07-25/26, confirmed over three runs. Every "35B-A3B base agent" reference is stale.
2. **Q56 is not on `main`.** It is on `battery/q50-quality-corpus`. `main` carries a different,
   older battery. A local-only `.git/info/exclude` hides the artifacts from `git status`.
3. **ABCC's Postgres holds 9 days, not months, and its token and cost columns are empty.**
   Brief §4.2's premise does not hold.
4. **ABCC has a 100-task suite with 7 recorded runs that the brief does not mention**, and it is
   closer to 2.0's stated target workload than the 40-task set the brief does mention.
5. **ABCC's 40-task set has deterministic per-task verifiers.** ABCC never used an LLM judge
   either — the family has *never* shipped one that survived measurement.
6. **The family has two more members**, `independencev1` and StealthForge (`stealthsambaV2`),
   dating from April 2026, between BCF and Claudette. See `prestudy/archive-repos.md`.
7. **`questions.md` §5 item 3 is not actionable.** `complexity_reasoning` is 18% populated.
8. **`questions.md` §2 item 8 is closed.** The Postgres extraction is done and there is no more
   there.

---

## 9. Confidence

**High** on everything counted: row counts, field population, token sums, score deltas. All of it
came from parsing the files rather than reading claims about them, and the parses are simple.

**High** on the custody findings — the missing docker volume, the branch-only corpus, the
`.git/info/exclude` entry. Each was checked directly.

**Medium** on the StealthForge inflation magnitude. The pairing is real and the direction is
unambiguous (34/34), but the reviewer has a documented 7.0 floor, so the +5.63 mean is an upper
bound on a real effect rather than a calibrated number.

**Medium** on the 100-task suite's fitness for W8. I read its structure and results; I did not run
it, and its most recent recorded run was an infrastructure collapse.

**Low** on anything about how the Q56 numbers would move under 2.0's orchestrator rather than
Claudette's CLI. That is `questions.md` §4 item 5 and it needs a run, not a read. No model was
loaded and no battery was reproduced for this document.
