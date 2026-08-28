# ADR-0014 — Deny the class via `max_tier`; the posture is blast radius, not a sandbox

- **Status:** ✅ Accepted
- **Date:** 2026-08-28
- **Deciders:** Claude Code (W7, measured on this machine), ratified with `research/SUMMARY.md`
- **Sources:** W7 F404–F422, esp. F404–F411 (the boundary), F412–F415 (injection), F416–F418
  (secrets), F419–F420 (supply chain), F421–F422 (README and the git guards) · W8 F403
- **Depends on:** ADR-0007 (the worktree is the blast-radius boundary), ADR-0013 (egress binds the
  provider)

## Context

The brief asked *path check per tool, or a process the tool child runs inside*. **Both halves
moved.**

🚨 **The path check is not the weak part of a good design — it is a well-built control that is simply
not in the path of the tools that execute code**, and all three donors have that property by three
different mechanisms. `write_file` is path-sandboxed and `bash` is not, so **`write_file` on a new
path plus `run_tests` is arbitrary code execution at the tier that never prompts** (F404–F406).

🚨 **And there is no process boundary to reach for on this platform.** Measured: a
`runas /trustlevel:0x20000` child **stays at Medium integrity, writes `$HOME` and opens TCP**; and
**WSL2's `binfmt_misc` hands any PE file back to the Windows host to execute** (reproduced). There is
**no containment on Windows without Win32 token code**, the state of the art does not attempt it, and
the most-resourced comparable product declines the platform outright (F408–F411). ⚠ The cost that
decides the design is **not process spawn** — a tool child is cheap; **the workspace crossing a VM
boundary is ~290×**.

**The obvious fix for prompt injection is the one that does not work.** The shipped system-prompt
sentence naming the untrusted-content tags is at **39/50 (78%) compliance with the injection**; the
best re-aimed configuration reaches **0/50, CI [0, 7.1]%** — a large effect in the right direction,
**and a prompt binds only as far as the model complies.**

## Decision

### 1. 🚨 Deny the class — a role that does not need a capability does not get it

**`max_tier` per role is the only enforcement that is real without an OS boundary.** The Planner and
the Judge get a policy capped below the exec class. It is free, it is testable, and the donor's own
`research_permission_policy` (`max_tier = ReadOnly`, with a test) is the shipped proof.

**Ten of the threat model's eleven rows close on this one control**, and it is not a check:

- **An argument check binds one tool and a shell walks past it** — demonstrated **four times, by four
  mechanisms, across three authors**.
- **A prompt binds only as far as the model complies** — 78% as shipped.
- **On this platform there is no OS boundary underneath either of them.**

### 2. Every tool that can execute code is one class, in one const, with a CI test

**Copy `egress.rs`'s shape exactly — registry, maintenance contract, integration test** — because
the donor already proved the pattern and already put these four tools in one class *for the other
control*. **The class is at minimum: any shell, any toolchain runner, any package manager, anything
that spawns a child.** `run_tests` and `diagnostics` join `bash` at the same tier, and **the CI test
fails when a new tool joins the class and is not gated.**

⚠ **Argument checks are kept and demoted.** They stop honest mistakes, and they are described as
*an argument check* — in the code and in the text the model is shown — **never as "the sandbox"**.

### 3. Confinement is a value the operator can see

`Confinement::{ None, Cwd, OsSandbox(kind) }` on the `ToolChild` result — **not a Boolean, and not an
argument silently ignored on the wrong platform**. 🚨 **A run whose every tool child reports `None` is
a fact the console must show**, because that is the true state of 2.0 on Windows today.

### 4. The stated posture is blast radius, not a boundary — in the README, in those words

**On Windows, do not build a native sandbox and do not claim one.** What ships instead: **a
disposable tree per task** (ADR-0007, 0.25 s), **an event log that records every child**, and a
README that says plainly that model-written code runs with the user's privileges. `README.md:104`
is rewritten in `:150`'s register — ⚠ **but correcting the sentence is not the fix; `max_tier` per
role is**, so the *role* rather than the tool name carries the ceiling, and **unattended modes ship
read-only and offline**, as `--research` already does.

### 5. Secrets, the child's environment, and the one leg of egress that closes

- **Redact at the tool-result boundary, as a property of the result type, applied once** — today both
  disk sinks are redacted and **the console and the model context are not**, and a good denylist
  hangs off `validate_read_path`, which `bash` never calls.
- **Adopt BCF's `env_clear()` + allowlist** — one donor of three strips anything — **as data in one
  const with a CI test.**
- **`--offline` for unattended roles is the only exfiltration leg that closes.** An SSRF guard is not
  an exfiltration control.
- **A displaced task is a verification failure, not a style issue** — injection that displaces the
  task persists into the rewritten file, and the Verifier is warned of none of it today (F415).

### 6. Supply chain: copy the gate verbatim, and add the pin no donor has

**Copy the dependency gate verbatim — `needs:` gate and update procedure included.** 🚨 **The
procedure is the part that matters**: it is what stops the policy rotting into a pile of `ignore`
entries.

**Then add what no donor in the family has: record the model manifest digest at first pull and
compare it on every start**, surfacing a mismatch as a **run-visible event**. The weights are the one
ungated input. An allowlist by name is redundant once a digest exists, and ⚠ **ollama has no signing
story** (OQ-W7-10).

### 7. The two git guards merge into one table, as a backstop

The destructive-git guard **exists twice, and neither copy covers the other** (F422). The careful one
recognises **three** operations — `reset --hard`, `checkout -f`, `switch -f` — so **`git push --force`
and `git branch -D` are blocked through the git tool and unrecognised through `bash`**, while
`git clean -fd` and `git stash drop` are caught by neither. It keys on `cmd_word != "git"`, so
**`sh -c "git reset --hard"` returns `None`**, and it **fails open** when `git` fails.

**One table, read by both paths, with both holes closed — and it is a backstop, never the control.**
The boundary is the worktree.

## Consequences

- **Every mode above `SinglePlayer` inherits the platform fact** (ADR-0013), which is why the mode
  matrix states it per mode rather than once in a footnote.
- **The threat model table's 11 rows are the POSTURE milestone's exit criterion**: each row has a
  shipped answer or **a written, dated admission that it does not**.
- **This is a risk, not a hypothesis** — SUMMARY.md's risk 1 is a *platform fact*. The milestone does
  not retire it; it makes the stated posture honest.
- **Two README sentences must change before any freeze**, and they are named in W7.

## Alternatives rejected

- **A per-tool argument check as the security control** — the shipped untrusted-content wrapper was
  *measured* not to work (39 of 50), and the path check is not on the path that executes.
- **Prompting harder** — the effect is real (78% → 0/50) and it is still a prompt. It ships as
  defence in depth, never as the control.
- **A native Windows sandbox** — F409: nothing to reach for without Win32 token code that nobody has
  shipped.
- **WSL2 as the boundary** — `binfmt_misc` hands PE files back to the host, and the workspace
  crossing costs ~290×.
- **A container per attempt** — ruled out for the runtime on independent grounds (ADR-0007), and it
  would still not be a boundary against a tool child that shares the workspace.
- **An allowlist of model names** — redundant once the manifest digest is pinned.

## What would falsify this

**A supported OS-level confinement primitive appears on this platform** — a shipped, maintained way
to drop a child below the user's own privileges without hand-written token code. Then
`Confinement::OsSandbox(kind)` stops being an enum arm that never occurs on Windows, the posture
sentence in the README changes, and the boundary moves from *blast radius* to a real one.
**`max_tier` survives either way** — it is policy, and it is the control that does not depend on the
platform being kind.
