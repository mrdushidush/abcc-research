# W6 item 7 — verifying the unrunnable

Everything behind item 7 of `research/W6-verification.md`: *"Verifying documentation
and review output where there is no test to run. LLM-as-judge reliability and its known
failure modes."*

The trap in that brief is that a population with no test also has no ground truth, so a
reliability number measured on it is an opinion about an opinion. Both halves here are
built to avoid it.

## The two populations, and why they have answer keys

**The 29.** F321 and F322 left OQ-W6-13 open: on the 280 Q56 cells where nothing
interfered with the agent, 29 attempts are real failures and no deterministic rung in
five languages fires on any of them. That is the unrunnable case *with* an answer key —
Q56 hides its reviewer tests at grade time on purpose (`Q03/task.toml`, caveat 3: *"the
fixture ships only happy-path visible tests on purpose: a PASS is possible only if the
subject handled an edge the prompt implies but does not state"*), so at the moment the
agent stopped, the visible suite was green and there was no test it could have run that
would have told it the truth.

**A real document.** `docs/status_lifecycle.md` from the K suite's
`finish_the_cancelled_status`, paired with the reference solution it describes — a
document that is true of its code sentence by sentence. Seven variants each carry
exactly one planted defect, applied as an anchored substitution so an edit cannot
silently miss.

## The probes

| file | what it does | output |
|---|---|---|
| `common.py` | assembles the 29 failures + 36 matched passes into 57 deduplicated trees, strips the verifier's residue, renders what a Judge is shown, and holds the backend call | — |
| `census.py` | dumps ticket, diff, reference solution and hidden assertions for every failing tree, for a hand classification | `census-out.txt` |
| `taxonomy.py` | the hand classification, with every `stated`/`signalled` quote asserted against the ticket | `taxonomy-results.json` |
| `judge.py` | the champion as reviewer over all 57 trees, two arms: `verdict` (pass/fail) and `edge` (name concrete cases) | `judge-verdict.json`, `judge-edge.json` |
| `check.py` | runs every case the `edge` arm named against the agent's tree and the reference solution | `check-results.json` |
| `citations.py` | the free rung for prose: findings, open questions, `file:line` addresses and code quotations over 44 authored documents | `citations-results.json` |
| `docgate.py` | planted defects in a real document; pointwise gate, position bias, verbosity bias | `docgate-results.json` |
| `v1_review.mjs` | v1's `getReviewDecision` and the router's type switch, ported verbatim from `d5528ea` and run | `v1-review-results.json` |
| `analyse.py` | reads the result files and prints the tables the workstream document quotes | `analyse-out.txt` |

Everything model-facing is resumable: re-running fills in missing keys only.

**Status: complete.** All four result files are full — `judge-verdict.json` and
`judge-edge.json` at 57 trees each, `check-results.json` at 20 cases, `docgate-results.json`
at 38 rows over four arms. `python analyse.py > analyse-out.txt` reproduces every table
quoted in F336–F345 of `research/W6-verification.md`.

## Held constants

Champion `qwen3.6-35b-a3b-mtp@iq3_s`, `lms load ... -c 65536 --gpu max --parallel 1 -y`,
LM Studio on `:1234`, temperature 0, `max_tokens` 8192, schema-constrained output with
the verdict schema W11 item 3 shipped (reasoning first, the decidable field last — F263).
The server's own command line for this session:

```
--ctx-size 65536 --n-gpu-layers 999999 --batch-size 2048 --ubatch-size 512
--parallel 1 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --kv-unified
--no-mmap --spec-type draft-mtp --spec-draft-n-max 2
```

Donor commits: v1 `d5528ea`, BCF `d6c1601`, Claudette `af3f804`.

## Six traps this spike walked into, all of them recorded in the code

1. **The checker's yield is a measurement of the checker.** `citations.py` reported 40
   dangling finding references, then 21, then 12, then 9, as it learned that this corpus
   defines a finding in **five** different ways (`### F158 —`, `### 🚨 F158 —`,
   `### F35.`, `## 4. F54 —`, `**F41.**`). Every one of the first 31 was its own.
2. **Attribution manufactures defects.** Attributing a fenced block to "the citation
   within three lines above" reported 12 documentation errors; 12 of them were the rule,
   not the document. Running the attribution backwards from the fence and requiring the
   language tag to match the cited file's extension leaves 7, and all 7 are paraphrase
   rather than falsehood.
3. **`subprocess.run(timeout=)` again.** One of the 29 trees does not terminate. Probing
   it with a plain `subprocess.run` hung the probe for the full tool timeout and left an
   orphaned `bash solution.sh` spinning whose recorded parent was already gone — so
   `taskkill /T` on the direct child could not reach it. F220 and F324, in one probe,
   ten minutes apart. Use `w6-headroom/common.py`'s `run`, which kills the tree.
4. **cp1252 truncates a census.** `python census.py > out.txt` died on the first em dash
   in a ticket and left a file that looked complete. `census.py` now opens its own output
   with `encoding="utf-8", newline="\n"`.
5. **The clean baseline was not clean, and the model under test found it.** `docgate.py`'s
   `faithful` document is a real spec written by a task author against real code, and every
   variant is planted against it — so it is the arm's control. It carries a claim the
   reference solution does not implement: rule 2 says a cancelled job's deadline no longer
   applies, and `sla.is_breached` still compares `finished_at` against it. The model raised
   it, at `high`, on three of the ten documents. It is left in place and recorded as
   `KNOWN_DISCREPANCY`, because a spec whose own implementation does not quite match it is
   the population 2.0 will be pointed at — but it means the `faithful` row is a **lower
   bound** on the false-positive rate and not a measurement of it.
6. **A rate conditioned on answering is not a rate.** The `edge` arm lost 17 of 57 calls to
   the token cap and named a case on 16 trees; scoring "did the reviewer's case discriminate"
   over those 16 gives 10 of 11, and over all 57 trees it gives 10 of 23. `analyse.py` prints
   the second. Item 26 and item 28 of the memory file, a third time.
