# OD-series — how to author a task here, and the constraint that shapes all of them

`suite.toml` carries why the suite exists. This carries how a task is built, and
the two properties that are easy to break without noticing.

## What a task has to be

```
prompt.txt   the ticket, in a user's voice
task.toml    lang, disposition, and the MEASURED gate evidence
verify.sh    the answer key — asserts behaviour, never presence
fixture/     a small real program that is already a wrong answer
refsol/      the right answer, as a partial overlay
sham/        the tempting wrong answer — required in this suite, not optional
```

Three shapes, eight tasks each. `donor_tags.shape` says which:

| shape | the sham | the question it asks |
|---|---|---|
| `outside_cover` | patches a **strict subset** of what `refsol` patches | does the reviewer notice what the change does not reach? |
| `outside_file` | patches a **different file** from `refsol` | does it notice the change is at the symptom? |
| `inside` | patches **the same file**, scope complete, logic wrong | 🚨 the control: does the reviewer fire here too? |

`donor_tags.scope_statement` is the second axis — `explicit` (the ticket states
the extent), `implied` (it points at a rule that does), `single_instance` (it
names one case of a general defect). Report a rate per cell of that 3 × 3 grid
or a ceiling will read as an effect.

## 🚨 The constraint that shapes every task in the suite

**The sham tree must be GREEN on the deterministic ladder.** If it is not, the
reviewer is shown a red rung, the ladder has already answered, and the tree
stops measuring what the tier was built for — the Judge as the only opinion
there is.

That has a consequence which is structural and not a trick, and it is worth
saying out loud because it looks like one when you meet it in the fourth task:
**the behaviour a sham changes cannot be pinned by a visible test.** A sham that
relaxes an integrity check breaks any test of that check raising. So the
fixture's suite covers the check on inputs it accepts and not on inputs it
refuses — which is how most real suites are written, and is why these defects
survive in real repositories. Each task's `caveats` says which absence it is
relying on. **A task whose sham fails `python -m pytest -q` is a bug in the
task**, and `gate-task.sh` refuses it.

## Authoring loop

```bash
# 1. write fixture/, refsol/, sham/, prompt.txt
# 2. predict the three outputs, then look
python harness/scripts/od_show.py corpus/suites/od/tasks/<id>

# 3. task.toml + verify.sh from a spec on stdin
python harness/scripts/od_new_task.py corpus/suites/od/tasks/<id> <<'JSON'
{ "title": ..., "reason": ..., "caveats": [...], "donor_tags": {...}, "verify": {...} }
JSON

# 4. measure SPEC.md §9's three points and write the block into task.toml
WRITE=1 bash harness/scripts/gate-task.sh corpus/suites/od/tasks/<id>
```

`gate-task.sh` was run against the K suite before it was trusted and reproduces
all three of K's recorded gate records. `od_new_task.py` writes
`point1 = "not_run"`, so **a task whose gate block still says `not_run` has not
been gated** — that is the intended reading, not an oversight.

## Building the trees, and running a probe over them

```
ABCC_CORPUS=D:\dev\ABCC_20_powerd_by_claudette\corpus  ABCC_CORPUS_SCRATCH=D:\ac \
ABCC_CORPUS_OUT=D:\dev\ABCC_20_powerd_by_claudette\research\corpus-run \
  cargo test -p abcc-gate --test corpus -- --ignored --nocapture      # no model call
./harness/scripts/scope-probe.sh both     # the arms; SAMPLE=b for a second sample
```

⚠ `ABCC_CORPUS_ONLY` takes a comma-separated list of task directory names, so a
single task can be rebuilt without the other 82 trees.

## 🚨 Reading a result from this suite

1. **Every probe owes a noise floor arm measured ON THIS SUITE.** Nothing in
   this stack samples at temperature zero. The corpus-wide figure — 27 of 121
   trees change when the identical question is asked twice — is q56+k's number
   and does not transfer.
2. **The `inside` third is the ruler, not filler.** A switch that moves
   `inside` shams as often as the other two thirds is producing volume.
3. **A finding on a `correct` tree is a candidate false positive**, and both
   briefs measured in GATE-P4 fabricated one identifier defect per 59 correct
   trees. Invention is the reviewer's; do not attribute it to a switch without
   the control saying so.
4. **Read the finding against the answer key by hand.** `verify.sh` grades a
   tree and a reviewer's prose is not a tree. A keyword count is not a finding
   count — F568.
