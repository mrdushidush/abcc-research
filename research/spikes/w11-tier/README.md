# w11-tier — what a phase change costs, and what a phase actually needs

Five probes run 2026-08-22 for **W11 item 2 (phase-to-tier mapping)**. Findings
**F238–F251** in `research/W11-stages.md`.

Held constants for every GPU probe: champion `qwen3.6-35b-a3b-mtp@iq3_s` loaded with
`lms load … -c 65536 --gpu max --parallel 1 -y`, nothing else resident, LM Studio on
`:1234`. The `llama-server` command line was captured per F86's rule and is byte-identical
to the one recorded in W2 F86 — in particular it carries **no `--cache-ram` and no
`--slot-save-path`**, which matters for F240: the multi-prompt cache is a backend default,
not a configured feature. Backend `llama.cpp-win-x86_64-nvidia-cuda12-avx2-2.27.1`.
CPU probes ran with no model call in flight.

| script | question | raw output |
|---|---|---|
| `phases.py` | does a phase transition cost a prefill? | `phases-run1.txt` |
| `heads.py` | how many distinct prompt heads stay warm, and does a reload survive? | `heads-run1.txt`, `heads-run2-after-reload.txt` |
| `verdict.py` | what output budget does one Judge call need? | `verdict-run1.txt`, `verdict-results.json` |
| `repeat.py` | fair prompt-and-pray arm + score reproducibility | `repeat-run1.txt`, `repeat-results.json` |
| `integrate.py` | what does M2 Integrate cost (OQ-W11-1)? | `integrate-run1.txt`, `integrate-run2-rust.txt`, `integrate-results.json` |
| `plan.py` | what does M1 Plan cost, and does it inflate (OQ-W11-2)? | `plan-run1.txt`, `plan-results.json` |
| `criteria.py` | do Plan's acceptance criteria fail on the unfixed tree? | `criteria-run1.txt`, `criteria-results.json` |

## What came out

**1. A phase transition costs a cold prefill if and only if it rewrites the prompt head.**
At ~16.9k prompt tokens: a repeat of the same head 2.398 s, a *new* head 10.857 s against a
10.944 s cold — 0.99× of cold, so the cache is annihilated exactly as W2 F81 found for a
single token. With the head frozen and the phase instruction moved to the tail, three
consecutive phase transitions cost 2.362 / 2.377 / 2.364 s. **+8.5 s per transition, 4.60×.**

**2. The server keeps at least twelve distinct heads warm, and nobody asked it to.**
Twelve heads × ~16.9k tokens: every one cold on first sight (~10.7 s), every one warm on
second (2.53–2.60 s), no eviction. Host RSS of `llama-server` went 988 MiB → 2,879 MiB across
four cached states = **473 MiB per state, ~28.7 KiB per token**. This is llama.cpp's RAM
prompt cache at its default budget; the command line does not mention it.

**3. A model load wipes it.** A head warm at 2.626 s came back at 10.584 s after an
unload/load of the *same* model. That round trip was **9.20 s** (unload 0.87 + load 8.33)
against F79's 23.77 s for a true model change — the difference is the OS page cache, since
nothing else displaced the weights.

**4. The donor's output cap for a judging role returns nothing at all.** BCF caps security,
critique and cto at `max_predict` 1024. On the champion, with a 745-token Judge prompt and a
strict verdict schema: 256 / 512 / 1024 / 2048 all returned `finish_reason: length` with
**zero payload bytes** and 938 / 1,990 / 4,107 / 8,599 characters of reasoning. First payload
at 4096. BCF's own workaround — the `/no_think` prefix it puts on its router prompt — had no
measurable effect on trace length here.

**5. And 4096 is not safe either.** Five identical calls at `max_tokens` 4096, temperature 0:
four returned a verdict, **one burned 16,564 characters of trace and returned empty**. Trace
length on identical input varied 9,942–16,564 chars. Verdicts: `fail` 4/4. Scores: 0, 2, 0, 2.
**The binary is reproducible and the number is not.**

**6. Prompt-and-pray parsed 3/3** once the format was actually asked for in the prompt, which
is what the donors do. The first run's no-schema arm had not been told to emit JSON, so it was
not a fair comparison; corrected here. The schema's case is the guarantee, not the hit rate.

**7. Integrate costs what the target project costs.** K-suite Python fixture: criterion 0.06–0.17 s,
pytest 1.17 s cold / 0.48 s warm. Claudette (real Rust workspace, ~300 deps): **104.2 s** from a
fresh clone (fetch 17.5 + cold build 57.1 + test compile 19.7 + test run 9.8), **6.1 s** with
nothing changed, **22.3 s** after touching one library source file — which is the case M2 actually
faces. A fresh workspace per attempt costs ~4.7× the incremental number.

**8. Plan does not inflate, and its criteria do not bind.** Told explicitly not to pad, the model
emitted 1, 1, 1 tasks for a one-task mission and 3, 2, 3 for a many-task mission, at 36–62 s per
call (prompt 1,534 tokens, completion 2,442–4,301). But of the **11 acceptance commands it
emitted, 6 exit 0 on the unfixed tree** — `cargo check` on a repo that compiles, and
`cargo test --lib <a test that does not exist yet>`, which matches nothing and **exits 0**. Three
more could not run at all (`./target/debug/…` under cmd.exe, and `jq`, which is not installed).
The one that failed for the right reason ran `claudette` from `PATH`, which resolves to
`C:\Users\david\.cargo\bin\claudette.exe` — the installed daily driver, not the tree under test.

## Reproducing

```powershell
lms load qwen3.6-35b-a3b-mtp@iq3_s -c 65536 --gpu max --parallel 1 -y
(Get-CimInstance Win32_Process -Filter "Name='llama-server.exe'").CommandLine   # record it
python phases.py ; python heads.py 12 ; python verdict.py ; python repeat.py ; python plan.py
python integrate.py            # CPU only; run with no model call in flight
python criteria.py             # needs plan.py's output and integrate.py's clone
```

`integrate.py` clones Claudette into the session scratchpad with `--no-hardlinks` (a `--local`
clone across volumes fails on Windows with `Improper link`) and never touches the donor. Both
drives on this box are SSD with over 900 GB free, so the C:/D: split is not a confound.

⚠ **`integrate.py`, `plan.py` and `criteria.py` hardcode the scratchpad path of the session that
wrote them** (`…/42b00185-4a5a-4806-9e97-33bd4fcebc29/scratchpad/w11-integrate`), which will not
exist in a later session. Point `SCRATCH` / `TREE_ROOT` / `CLONE` at the new session's scratchpad
before re-running, and run `integrate.py` first — `plan.py` reads the clone's file tree and
`criteria.py` runs the emitted commands inside it.
