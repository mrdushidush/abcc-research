# Spike: driving Claudette's REPL over pipes (THROWAWAY)

Run 2026-08-08. Supports `research/W8-corpus-format.md`. **This is throwaway code**, kept only as
evidence for the findings it produced. None of it is a proposal for the real harness, which is Rust.

## What it proved

`drive_claudette.py` spawns `claudette` v0.17.0 with no arguments (REPL), stdin/stdout/stderr as
three separate pipes, **no `CLAUDETTE_AUTO_APPROVE`**, against `qwen3.5-4b` on LM Studio at
`localhost:1234`. Workspace: one `calc.py` whose `subtract()` adds. It sends the task, waits for the
permission gate, and injects a redirect.

```
[   1506ms] IN   turn-1 prompt: 'There is a bug in calc.py: subtract() adds instead of subtracting...'
[  25902ms] ERR    ⚠ apply_diff wants to run (415 chars):
[  25904ms] ERR      -     return a + b
[  25904ms] ERR      +     return a - b
[  25905ms] ERR  *** GATE OBSERVED ON ERR *** '  Allow? [y/N · or type a redirect] '
[  25905ms] IN   scripted REDIRECT: 'actually just tell me the one-line fix, do not edit anything'
[  31623ms] *** FIRST BYTE ON STDOUT (TTFT sample) ***
[  32106ms] OUT  Change `return a + b` to `return a - b` on line 5 in the subtract() function.
[  32107ms] ERR  ⚡ turn iter=5 in=21106 out=505 ctx ~485/32k (1%)
[  32642ms] process exited rc=0

P1 REPL-over-pipe reached a live gate : YES  (gates=1)
P2 gate observable on stderr          : YES
P3 TTFT samplable during the run      : 31623 ms
P4 turn-boundary marker + token counts: '⚡ turn iter=5 in=21106 out=505 ctx ~485/32k (1%)'
   parsed usage: in=21106 out=505
```

After the run `calc.py` was **byte-unchanged** (`subtract` still returns `a + b`) while the model
obeyed the typed instruction in text. Deny-plus-forward confirmed behaviourally, not just by reading
`gate_line_decision`.

Findings that came out of it and are written up in `W8-corpus-format.md`: F2 (REPL degrades to piped
stdin, so no PTY on the path that has the gate), F3 (stdout and stderr carry different event classes;
the gate prompt has no trailing newline, so a line-buffered reader hangs), F4 (the post-turn stderr
line is a usable turn boundary **and** carries real token counts, making cost per task reachable),
F6 (first visible output was 25,902 ms on stderr vs 31,623 ms on stdout - a TTFT defined on stdout
alone overstates felt latency by the whole tool-call phase).

## Reproducing

```bash
mkdir ws && printf 'def subtract(a, b):\n    return a + b\n' > ws/calc.py
PYTHONUTF8=1 python drive_claudette.py "$PWD/ws" qwen3.5-4b 240
```

Needs `claudette` on PATH and an OpenAI-compatible server on `localhost:1234`. `PYTHONUTF8=1` is
required on Windows: the subject emits non-ASCII glyphs even under `NO_COLOR=1`, and the default
cp1252 console encoding raises on them.

> ⚠ **The transcript above is `qwen3.5-4b` and is mechanism-only**: it proves the plumbing, and its
> timings are not measurements. The champion is `qwen3.6-35b-a3b-mtp@iq3_s` and every citable number
> must come from it. On the champion the same shape of work took 72 s to reach the gate, not 26 s.

## `multi_turn_probe.py` - the usage-accounting probe

Answers "is the per-turn `in=/out=` line per-turn or session-cumulative?", which a single-turn
session cannot distinguish. Run on the champion:

```
# three text-only turns, iter=1 each
turn  iter       in=    out=     d(in)   d(out)
   1     1      4885      63      4885       63
   2     1      9785      80      4900       17
   3     1     14701      94      4916       14

# two tool-using turns, both edits applied after a scripted approve
   1     3     15464     322     15464      322
   2     2     26631     573     11167      251

VERDICT: SESSION-CUMULATIVE (per-turn cost = the delta column)
```

That is W8 finding F9. The same three text turns on `qwen3.5-4b` gave **byte-identical** `in=`
counts and different `out=` counts, which is how we know the ~4.9k per-turn preamble belongs to
Claudette's system prompt plus tool schemas rather than to the model.

Wall clock on the champion also produced F10: turn 1 took **169.7 s** against 4.1 s and 3.7 s for
turns 2 and 3. That is the JIT model load, not task difficulty, and it is why the harness needs a
warmup turn before the first measured task.

```bash
PYTHONUTF8=1 python multi_turn_probe.py "$PWD/ws" "qwen3.6-35b-a3b-mtp@iq3_s" 600
PROBE_TURNS='first turn|||second turn' PYTHONUTF8=1 python multi_turn_probe.py ...
```

## The gate script

`gate_fix_sql_inject.py` is the verifier half of the ABCC import example, used to run the proposed
three-point gate against ABCC's `fix_sql_inject`. No model needed.

```
fixture (buggy)      -> RESULT: FAIL AttributeError: 'NoneType' object has no attribute 'execute'
fixture + refsol     -> RESULT: PASS
fixture + sham       -> RESULT: PASS     <-- the finding
```

The sham returns `SELECT * FROM users WHERE name = 'admin' OR 1=1 --' -- ?`, i.e. the injection fully
intact, and the donor's verifier passes it. Its assertion is an OR-chain
(`"'" not in q or '?' in q or ...`) that short-circuits on any `?`. This is F8, and it is why the
import gate gets a third point.
