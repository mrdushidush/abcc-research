# LEDGER P1 — the index is derived, and supersession is the field that is written down

**Built 2026-09-08 against the archive at `85f80a0`.** The design was settled before this session
and is not re-derived here: markdown stays the source of truth, SQLite is a derived index
regenerable from the prose, and supersession is the one field that is authored. What this document
records is the build, the five things measuring the corpus taught us while doing it, and the one
number nobody should quote as complete.

Instruments: `research/tools/fparse.py` (the grammar), `research/tools/fledger.py` (the index and
its queries), `research/tools/fread.py` (the coverage probe, unchanged in behaviour). The authored
half is `research/findings-supersession.tsv`. The index itself, `research/findings.sqlite`, is
gitignored — it is rebuilt in 3.9 s and committing it would make it a second copy of something.

---

## 1. What was built

Three files, one grammar between them.

`fparse.py` holds the six definition shapes and nothing else. They were extracted verbatim out of
`fread.py`, which now imports them, and **the probe's TSV is byte-identical before and after the
extraction** — checked, because F668–F670 quote that probe's coverage block and a change there
would be a regression rather than a tidy-up. The shapes are expensive: the heading-with-a-section-
number shape was worth 58 findings on its own and took the parse from 15% to 88.5%.

`fledger.py build` walks the same 137 documents, picks one canonical definition per finding, dates
it by `git blame`, loads the authored edges, derives everything else, and writes a SQLite file with
seven tables. Then `show`, `search`, `chain`, `gaps`, `contested`, `candidates` and `next` read it.

The state machine is derived and never authored, because an authored state and an authored edge
are two things that can disagree. Precedence, strongest claim first: `retracted` → `superseded` →
`answered` → `live`. A `refines` edge deliberately leaves its target `live` — that is the point of
having the kind at all.

---

## 2. The findings

### F680 — the corpus restates itself 1.5×, and the FIRST statement is the definition

**1,020 parsed definitions for 667 distinct findings**, counted at `85f80a0` and so not including
this document's own six. 390 numbers are defined exactly once; 277
carry between two and six. The extra copies are not scattered — 227 of them come from five memory
files, and the rest from documents *about* the archive: `DEBUG-P6`, the `CONSOLE-P*` series, the
ADRs. This is F670's trap at scale, and position alone cannot resolve it.

**Date and length can, in that order.** The rule is: lowest source class wins (research →
decisions → memory), then the **earliest** statement, then the fullest, then document order. Date
first because a finding is defined when it is first written down and everything after is a
restatement.

⚠ **Length alone gets `F83` wrong by ten characters.** `DEBUG-P6`'s 272-character *description of a
parse bug* beats `W2-serving.md`'s 262-character definition, and the description is the one about
the archive rather than about the world. With the date in front, `F83` resolves to
`W2-serving.md:131`, 2026-08-16, correctly. Length still decides between same-day rivals and where
no date exists, which is where it earns its keep: `F531` is 497 characters in `ACCEPTANCE-C` and 40
in `DEBUG-P6`, quoted there as an example of prose arguing in the negative.

Together they leave **9 contested picks** — a human read of nine rows rather than a
redesign. `fledger.py contested` lists them, and seven are the same benign shape: `W8-hardest-30`
work written up twice, once as a research doc and once as a spike README.

### F681 — 40 findings exist ONLY in a memory file, and 12 only in an ADR

A ledger scoped to `research/**` would have silently dropped **52 findings**, 40 of them from the
early F22–F52 band that survives nowhere else. The memory directory is not a summary of the
archive here; for those 40 it *is* the archive. That settles a question the design left open by
implication: the reader must scan the memory directory, even though `MEMORY.md` itself stays out
of the database.

⚠ It also has a cost. The memory directory lives under `~/.claude` and is **not a git repository**,
so those 40 findings carry no date and no commit. That is recorded as NULL, not papered over.

### F682 — requiring the number to be the OBJECT of a correction verb raises precision by ~6×

Two detectors were run over the same prose:

| detector | proposes | real edges | precision |
|---|---|---|---|
| co-occurrence — a retraction word in the block × every finding it cites | 79 pairs | ~6 | **~8%** |
| directed — the number must be the object of a correction verb, or the subject of a correction predicate, within one line | 34 hits | 18 | **~53%** |

The co-occurrence rule is the one F669 measured at +76% over the truth, and the mechanism is
visible in its worst row: `F290` cites nine other findings as its supporting evidence and the rule
reads all nine as corrections. The directed rule declines that row entirely.

▶ **Neither is ever written to `edge`.** Both are stored in `edge_candidate` with the shape that
proposed them, and `fledger.py candidates` prints the unresolved ones as a worklist. They are
reading prompts.

### F683 — the archive's dominant correction verb is *answers*, not *supersedes*

Of the 18 authored edges: **8 refine, 6 answer, 4 supersede, 0 retract.** A ledger offering only
supersede-and-retract would have mis-typed 14 of 18, and in the damaging direction — it would have
marked as *dead* eleven findings that are alive and merely qualified. The corpus says it plainly
and often: *"F606 is answered"*, *"F637 is ANSWERED"*, *"F38 IS ANSWERED"*, *"F625 IS REPAIRED"*.

🚨 The most valuable rows in the authored file are the **12 non-edges** — corrections the prose
considered and refused. *"This does not retract F531"*, *"`abcc take` DOES NOT CLOSE F585's gap"*,
and the three `F83 →` rows that exist only because `DEBUG-P6` quoted a sentence and a reader
recorded the quotation as a definition. Without somewhere to *store a refusal*, every future
automated pass re-asserts all of it. That is why the file is authored and not merely cached.

### F684 — 627 of 667 findings can be dated from git, and the 40 that cannot are exactly the memory-only ones

`git blame --line-porcelain` over the 96 tracked documents dates the canonical definition line of
**627 findings** at a cost of 3.9 s for the whole build. The 40 undated ones are precisely F681's
set, so the archive gains a time axis it never had and the axis is honest about where it stops.

▶ The date then does a second job it was not built for: it is the **primary tie-break** for the
canonical definition (F680), because the first statement of a claim is the definition and every
later one is a restatement.

### F685 — this document asserted a false edge from its own example block, on the first build

🚨 Section 4 below shows the new convention by printing `Supersedes: F649 (...)` inside a fenced
code block. The first build after writing it reported **1 inline edge** and moved `F649` from
`live` to `superseded` — an edge nobody authored, produced by the document whose section 2 warns
that a corpus containing documents about the corpus cannot be read by position.

The fix is one line: **a fenced block is an example, not an assertion**, so the inline and directed
detectors now skip fenced regions. Definition parsing was deliberately left alone, because
`fread.py`'s output is a fixed point that F668–F670 quote.

▶ The general form, and it is F667's family again: **the instrument that reads the archive is
itself in the archive.** Every detector added here has to be tested against the document that
describes it, because that document is the first thing it will read.

---

## 3. What is NOT claimed

⚠ **The edge count is not the archive's total.** F669 counted **38** correction edges in the prose
by hand. This file's first pass holds **18** — the ones a directed search surfaced *and* a human
then read and evidenced with the sentence that proves them. The other twenty are not denied; they
are **unread**. `research/findings-supersession.tsv` says so in its own header, `fledger.py build`
prints it as `edge_recall: UNKNOWN`, and the worklist is `fledger.py candidates`.

⏸ Two things are David's, not the tool's:

* the **nine contested canonical picks** — nine rows, one read each, seven of them the same
  benign shape;
* the **remaining ~20 edges** — the back-fill F669 already described as a human read done once.

---

## 4. The convention that makes this cheap going forward

A finding that corrects another should **say so on its own line**, exactly:

```
Supersedes: F649 (the door was taken with nobody offering it)
```

`Retracts:`, `Refines:`, `Answers:` and `Not-an-edge:` parse the same way, anywhere inside the
definition block, and land in `edge` with `authored_in = inline`. It is still authored — a person
wrote the sentence — it just lives next to the claim instead of in the sidecar. Nothing needs
back-filling into the 116 existing documents; the convention is for new writing.

One more, small and load-bearing: **`fledger.py next` is now the answer to "what is the next free
finding number".** It is `F680`. The memory index carried `F679`, which is defined, and a number
issued twice is the one failure the archive cannot repair after the fact.

---

## 5. Reproducing it

```bash
python research/tools/fledger.py build      # 3.9 s, rewrites the index whole
python research/tools/fledger.py show F655
python research/tools/fledger.py chain F38
python research/tools/fledger.py candidates # the unread worklist
python research/tools/fread.py . <memory-dir> out.tsv   # the coverage probe
```

Both tools take `--root` and `--memory`; `fledger.py` also takes `--out` and `--edges`. The build
deletes and rewrites the database rather than migrating it, which is the derived-only rule made
structural: there is no schema version to get wrong, and no state in the file that the markdown
cannot produce again.
