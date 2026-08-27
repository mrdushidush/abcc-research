# W7 — Security and sandboxing

**Status: IN PROGRESS — started 2026-08-27.** Sessions 3–5 of the 14-session landing budget, and
the one **undo-cost exception** in that budget: sandboxing shapes the execution model, so it is the
last workstream that is expensive to get wrong. **Line budget: ≤ 900.** §13's ten sections per
item, findings only where a decision turns on them, and no spike unless a decision is genuinely
blocked without one. Findings **F404–F411** so far; next free number is **F412**.

Planned items:

1. ✅ **The isolation boundary** (F404–F411) — §11's first bullet: *"executing model-generated code
   locally: minimum viable isolation and its performance cost… what are the options for a single
   Rust binary that is not shipping a container runtime?"* W3 handed W7 the tool child as *the*
   isolation boundary; `research/W8-u40-floor-check.md` F403 handed it the measurement saying a
   per-tool path check is not one. **Answered below, and it inverted the brief in two places.**
2. ⬜ **Prompt injection through the codebase itself** — a worker reading a file that contains
   hostile instructions. Item 1's execution sinks are this item's payload delivery.
3. ⬜ **Secrets in prompts, traces and the tool child's environment** — the console renders traces,
   so a leaked secret is persisted *and* displayed. BCF's env allowlist (F407) is the starting
   point; item 1 establishes that neither other donor strips anything.
4. ⬜ **Supply chain** — dependencies and model weights pulled at first run, `cargo audit` in CI.
5. ⬜ **Blast radius and the README** — what happens when a user points 2.0 at a repository they
   care about, and the **threat model table** the brief names as the deliverable.

**What item 1 changes for anyone reading only one thing.** The question was *path check per tool, or
a process the tool child runs inside*. Both halves moved. The path check is not the weak part of a
good design — it is a **well-built** control that is simply not in the path of the tools that
execute code, and all three donors have that property by three different mechanisms. And the
process boundary is not portable: on the platform this project is developed on there is **no
containment available without writing Win32 token code** (measured), the state of the art does not
attempt it, and the escape hatch that *is* available — WSL2 — hands any PE file back to the Windows
host to execute (reproduced). The cost that decides the design is **not process spawn**: a tool
child is cheap, and the workspace crossing a VM boundary is ~290× (measured).

---

# Item 1 — the isolation boundary

## Question

§11's first W7 bullet: *"Executing model-generated code locally: minimum viable isolation and its
performance cost. V1 relied on Docker, which is a starting point but not a boundary against hostile
code. What are the options for a single Rust binary that is not shipping a container runtime?"*

Sharpened by what the family already decided and measured:

- **W3 already chose the tool child as the isolation boundary** — the unit that 2.0 confines is the
  process a tool spawns, not the agent.
- **F403 measured that a per-tool path check is not a boundary**: unprompted, on 40 trivial
  greenfield tasks run twice, **30 of 80 attempts** answered a `write_file` refusal by calling
  `bash`, which has no path gate, and wrote outside the workspace anyway.
- **W6 item 6 already owns *filesystem* isolation** — a worktree at 0.25 s, 24.7 s for a warm-cache
  build in a fresh one (F325–F335). That answers *"how does each task get its own tree."* **This
  item answers the different question: what stops the code inside that tree from leaving it.**

So the question here is narrow and load-bearing: **is the boundary a path check per tool, or a
process the tool child runs inside — and what does each cost on the platforms 2.0 has to run on?**

## Method

Two halves, both cheap; no GPU, and no spike beyond four probes that each answer one yes/no.

**Read the three donors' execution surfaces against source, not against their dossiers.** Claudette
`tools.rs`, `tools/shell.rs`, `tools/quality.rs`, `runtime/permissions.rs`, `run/runtime_build.rs`,
`egress.rs`, `test_runner.rs` at `af3f804`; v1 `packages/agents/src/tools/shell.py`,
`docker-compose.yml`, `packages/*/Dockerfile`; BCF `src/sandbox.rs`, `src/verifier.rs`. Every tool
that can write or execute was enumerated and matched against the control that is supposed to bound
it, and — per F347/F367's lesson — **the readers of each control were grepped**, not just its
definition.

**Four probes on this host** (Windows 11 Pro 26200, the machine 2.0 is developed on):

| probe | what it settles | instrument |
|---|---|---|
| spawn cost | is a per-call tool child affordable at all | `std::process::Command` + piped stdio + `wait`, the exact path `run_command_with_timeout` uses; 20 reps, median, **exit status checked** |
| workspace cost | what a boundary costs the *files*, not the process | 200 small writes + a read-back sweep, same script, ext4 inside WSL2 vs 9p out to the Windows drives; 7 reps, median, timed from Windows |
| Windows containment | what a single binary can confine without Win32 token code | a child under `runas /trustlevel:0x20000` reporting its integrity level, two writes, one outbound TCP connect |
| execution reachability | whether a fixed-argv test runner still executes model-written code | a `conftest.py` + `pytest.ini` in a scratch tree, `pytest` invoked with the tool's own argv, marker written outside the invocation directory |

⚠ **One row is deliberately absent.** `docker run` could not be measured: Docker Desktop is
installed but its daemon is stopped, and an early version of the spawn bench reported the container
row at 133 ms — which was **the cost of failing to connect to the daemon**, not a container start.
The bench now checks exit status and prints `FAILED`; the number is not quoted anywhere below.

## Inherited

Each donor built roughly one third of a boundary, by a different mechanism, and none of the three
mechanisms sits in front of the tools that actually execute code.

| what | where | verdict |
|---|---|---|
| **A well-built path check** — component-wise `Path::starts_with`, `.`/`..` resolved manually so it works on targets that do not exist yet, plus `reject_write_symlink_escape` against the nearest existing ancestor | Claudette `tools.rs:1002-1039`, `:943-960` | **KEEP the implementation, demote the claim.** This is the *correct* version of a path check and it still bounds nothing (F404) |
| **A string-prefix path check** — `str(full_path.resolve()).startswith(str(WORKSPACE_PATH.resolve()))` | v1 `tools/file_ops.py`, per the dossier §9.8 | **DISCARD** — the wrong primitive, and the dossier already says so |
| **Permission tiers keyed on tool name**, five modes, `WorkspaceWrite` active by default, plus a `max_tier` hard cap that denies before any prompter is consulted | Claudette `runtime/permissions.rs`, `run/runtime_build.rs:438-611` | **KEEP `max_tier` ONLY.** The ladder is inert in the mode 2.0 runs in; the cap is the one part that still holds (F404, F405) |
| **An argv allow/deny list plus 21 regex "dangerous patterns"** and four per-language inline-code validators | v1 `tools/shell.py:1-280` | **DISCARD** — 280 lines that an allowlisted interpreter walks past (F406) |
| **Docker Compose as the containment story** — three services, `USER appuser` in all three Dockerfiles, workspace bind-mounted read-write into all three | v1 `docker-compose.yml`, `packages/*/Dockerfile` | **DISCARD as a boundary, note the one good part.** Non-root is real; `cap_drop`, `security_opt`, `read_only`, `pids_limit` and any network restriction appear **nowhere** in the compose file |
| **An environment allowlist stripped before exec** — `env_clear()` then re-add ~30 named vars plus `LC_*` | BCF `src/sandbox.rs:10-105` | **KEEP, and it is the piece the other two lack entirely** (F407) |
| **Network denial on the one call that runs model-authored code** — `sandbox-exec` with `(deny network*)` around the test step | BCF `src/sandbox.rs:167-183`, called from `verifier.rs` ×5 | **KEEP the placement, FIX the silence** — macOS only, and it no-ops on every other platform with nothing in the result saying so (F407) |
| **A two-layer egress guard with a maintenance contract and a CI test** — HTTP layer + subprocess layer, one `NET_TOOLS` registry, `tests/offline_egress.rs` drives every listed tool and asserts refusal | Claudette `egress.rs`, `tests/offline_egress.rs` | **KEEP, and copy its *shape* to the execution class** — this is the model for what the missing control looks like (F404) |
| **The tool child's environment, inherited whole** | Claudette `test_runner.rs:39-50` (`Command::new`, no `env_clear`); v1 `shell.py:250-257` (`subprocess.run` with no `env=`) | **DISCARD both** — and v1's case is acute: the compose file puts `ANTHROPIC_API_KEY` and `XAI_API_KEY` in the environment of the service whose shell the model drives |

## Findings

### 🚨 F404 — the permission tier is keyed on the tool name, and Claudette's own source already says the tool name does not bound what executes

Claudette has two controls over the same four tools and they classify them differently.

**The egress guard treats them as one class.** `egress.rs`'s `NET_TOOLS` registry doc-comment says
it in full: the list covers the network tools *"plus the raw-shell escape hatch (`bash` /
`bash_background`) and the build/test toolchain runners (`run_tests` / `diagnostics`), which are
**not** network-by-default but are refused wholesale because **their egress is unguardable**
(arbitrary shell / build-script / test-code execution)."* `quality.rs:154-166` repeats the reasoning
at the call site — *"cargo/npm/pytest/go … compile and execute arbitrary build scripts, test bodies,
and proc-macros … **the SAME unguardable egress vector `bash` is refused for** (the air-gap guard
cannot inspect what a build script does). The only honest offline posture is to refuse the whole
tool."*

**The permission guard treats them as two classes, two tiers apart** (`run/runtime_build.rs`):

| tool | egress class | permission tier | prompts in the default mode? |
|---|---|---|---|
| `bash` | unguardable execution | `DangerFullAccess` | yes |
| `bash_background` | unguardable execution | `DangerFullAccess` | yes |
| `run_tests` | unguardable execution | **`WorkspaceWrite`** | **no** |
| `diagnostics` | unguardable execution | **`WorkspaceWrite`** | **no** |

🚨 **And only one of the two controls has anything keeping it honest.** The egress side carries a
written *"MAINTENANCE CONTRACT"* in the registry's doc comment and a 166-line integration test
(`tests/offline_egress.rs`) that drives every listed tool through `dispatch_tool` and asserts the
refusal — *"turning the air-gap from a documented posture into a CI-proven guarantee."* The
execution side has no registry, no contract, and no test: `run/runtime_build.rs` contains exactly
**two** tests, and neither pins a tier. Nothing fails if the next exec-capable tool is registered at
`WorkspaceWrite`.

**This is not an oversight nobody noticed.** The equivalence is written down, in the source, twice.
It was applied to one control and not to its sibling — which is a more useful finding than a missed
case, because it says the classification is already known and only the *enforcement point* is wrong.

### 🚨 F405 — two auto-allowed calls are arbitrary code execution, demonstrated on this host, with the `bash` gate never consulted

The chain is three lines of policy:

1. `write_file` is registered `WorkspaceWrite` (`runtime_build.rs:471`). `effective_required_mode`
   (`permissions.rs:236-252`) bumps it to `DangerFullAccess` **only when the target already
   exists** — the reasoning is sound (replacing a whole file is an edit) and the consequence is
   that **a new path never prompts**.
2. `run_tests` is registered `WorkspaceWrite` (`runtime_build.rs:499`). Its argv is fixed — the
   model cannot supply a command; `invoke()` builds `cargo test` / `npm test` / `pytest` / `go test`
   itself.
3. `authorize` returns `Allow` when `current_mode >= required_mode`, and the default active mode is
   `WorkspaceWrite`. Both calls are `WorkspaceWrite`. Both pass in silence.

**A fixed argv does not bound what runs, because the code is in the repository, not the command
line.** Demonstrated: a scratch tree containing `pytest.ini` and a `conftest.py`, `pytest` invoked
with the tool's own argv. The `conftest.py` executed **at collection time** and wrote a marker into
`$HOME` — outside the directory `pytest` ran in, and outside anything `validate_write_path` would
have permitted `write_file` to touch. Output: `1 passed in 0.42s`, marker present.

🚨 **And the model can install the framework it then invokes.** `detect_framework`
(`quality.rs:136-152`) walks up looking for `Cargo.toml`, `package.json`, `pytest.ini` /
`pyproject.toml`, `go.mod`. Every one of those is a *new file at a new path*, so writing one is a
`WorkspaceWrite` call that never prompts. In a repository with no test framework at all, three
auto-allowed calls — marker, `conftest.py`, `run_tests` — reach arbitrary execution. The `cargo`
equivalent is one file (`build.rs`); the `npm` equivalent is one key in `package.json`.

⚠ **F403's `bash` detour is the visible half of this, not the whole of it.** The detour was
measurable because it followed a refusal and cost 2–3× the work. This path produces no refusal, no
prompt and no `▸` line beyond the ordinary write log, so **the u40 run cannot tell us how often it
happened** — only that it was available on every one of the 80 attempts.

### 🚨 F406 — v1 has the same defect through a different mechanism, and its author found it and fixed it in exactly one of five languages

`shell.py` is 280 lines of argv filtering: a 23-command allowlist, a 13-command denylist, 21 regex
"dangerous patterns" applied to the raw string, and four per-language validators. `python`, `node`,
`tsx`, `go`, `php` and `pytest` are all **on the allowlist**.

Every one of the extra validators fires only on an **inline** program — `_validate_python_code`
returns immediately unless `args[1] == '-c'`, `_validate_node_code` unless `-e`, `_validate_php_code`
unless `-r`. `pytest` has no validator at all.

🚨 **`_validate_go_code` is the exception, and that is what makes this a finding rather than an
omission.** For `go run <file>` it **opens the source file and greps it** for `os/exec`, `syscall`,
`net`, `net/http`, `plugin`. So the file-based bypass was seen, and closed, for one language of
five. `python evil.py`, `node evil.js`, `php evil.php` and a bare `pytest` are unchecked — and
`file_write` is bounded only by the `startswith` prefix test.

⚠ **The child also inherits the parent's whole environment.** `subprocess.run(parts, shell=False,
cwd=settings.WORKSPACE_PATH, …)` passes no `env=`, and `docker-compose.yml:129-130` puts
`ANTHROPIC_API_KEY` and `XAI_API_KEY` into the environment of the `agents` service — the same
process whose shell the model drives. `os.environ` is two auto-allowed tool calls away, and the
result lands in a trace that Postgres stores and the console renders.

### F407 — the three donors hold one third of the boundary each, and the missing thirds are not the same third

Laid against the three things a tool child can carry out of its sandbox — **files**, **the
environment it inherits**, and **the network** — the family covers each exactly once:

| | files | environment | network |
|---|---|---|---|
| **v1** | `startswith` prefix, on file tools only | **inherited whole** | container has no restriction; egress open |
| **Claudette** | correct path check, on 4 mutating tools only | **inherited whole** (`Command::new`, no `env_clear`) | `egress.rs`, two layers, registry + CI test — **the strongest control in the family** |
| **BCF** | none | **`env_clear()` + a ~30-name allowlist** | `(deny network*)`, on the right call, **macOS only** |

**BCF's env allowlist is the piece to take, and its doc comment carries the lesson:** it replaced a
substring *blocklist* that *"missed several real leak surfaces (`OLLAMA_HOST`, `DATABASE_URL`,
`KUBECONFIG`, `AWS_ACCESS_KEY_ID`, `SSH_AUTH_SOCK`, …); allowlist semantics close the class."*
That is the same allowlist-beats-denylist result F406 shows v1 learning the hard way.

🚨 **BCF's network denial has the right placement and a silent failure.** `run_tool_sandboxed` is
called at five sites in `verifier.rs`, all of them the step that executes model-authored code —
exactly where it belongs. But `src/sandbox.rs:176-178` returns the unsandboxed path when
`!deny_network || !cfg!(target_os = "macos") || !tool_exists("sandbox-exec")`, and **`ToolResult`
carries no field saying which branch ran.** On Windows and Linux the argument `deny_network: true`
is accepted and does nothing, and no caller can tell. ⚠ One line earlier, `verifier.rs:495` runs
`npm install --silent` **unsandboxed** immediately before the sandboxed `npm test` — so the
dependency install, with its postinstall scripts and its full network access, happens outside the
boundary the test then runs inside.

This is the same shape as F403's mis-advertised sandbox root and W6's silently-degrading checks:
**a control that is absent reports nothing.** It is the recurring family failure mode, and it is
the requirement that has to survive into 2.0's type — a sandbox result must say which boundary
actually applied.

### F408 — the tool child is cheap; the workspace crossing a boundary is not, and that is what decides the design

**Spawn cost, this host, `std::process::Command` + piped stdio, 20 reps, median, exit status
checked** (`scratchpad/spawnbench`):

| what | median | note |
|---|---|---|
| `cmd /c exit` | **10.3 ms** | the Win32 `CreateProcess` floor |
| `git --version` | 15.7 ms | a real small tool |
| `powershell -NoProfile -NonInteractive -Command` | **121.7 ms** | **what `bash` costs today on Windows** (`shell.rs:210-211`) |
| `wsl -- true` (warm VM) | **78.5 ms** | a hop into a Landlock-capable kernel |
| `docker run --rm alpine true` | *not measured* | daemon stopped; see Method |

🚨 **Moving the tool child into a Linux VM is 36% *cheaper* than the shell the tool already
spawns.** At the u40 run's median of 4 iterations per delivered cell, per-call isolation is a ~0.3 s tax on an
8.5 s task. **Process isolation is affordable.** That half of the brief's "performance cost"
question has a comfortable answer, and it is not the half that matters.

**Filesystem cost, 200 small writes + a read-back sweep, same script, 7 reps, median, timed from
Windows** (floor = `wsl -- true`, 113 ms in this batch):

| where the files live | total | workload |
|---|---|---|
| ext4, inside the VM (`/dev/sdd`, verified by `df -T`) | 116 ms | **~3 ms** |
| 9p → Windows `C:` | 894 ms | ~781 ms |
| 9p → Windows `D:` — **the drive the workspace is on** | 990 ms | **~877 ms** |

🚨 **~290×.** The boundary is nearly free to *enter* and enormous to *work across*. So the design
question is not "sandbox or not" — it is **whether the whole workspace lives on the sandbox's side
of the filesystem**, and the honest cost of a VM-based answer on Windows is that the repository has
to move into the VM, not be mounted into it.

⚠ Both numbers are one host, one batch. The ordering is not close enough for that to matter; the
ratio is.

### 🚨 F409 — on Windows, the containment a single binary can get without writing Win32 token code is zero, and the state of the art does not attempt it

**Measured.** A child launched under `runas /trustlevel:0x20000` — the "Restricted" trust level,
the strongest containment reachable from a shipped Windows binary without `CreateRestrictedToken`
plumbing — reported:

```
WROTE   C:\Users\david\w7-probe-home.txt
WROTE   D:\dev\ABCC_20_powerd_by_claudette\scratch\w7-probe-ws.txt
integrity: Mandatory Label\Medium Mandatory Level   S-1-16-8192
net egress: OPEN (True)
```

Still **Medium** integrity, still writing `$HOME`, still opening outbound TCP. Nothing relevant is
contained. Windows *does* have primitives — integrity levels, restricted tokens, AppContainer, job
objects — but they are **identity-and-ACL** shaped, not path shaped: to say *"this child may write
exactly this one tree"* you must relabel everything else, and job objects bound CPU, memory and
process count while binding neither the filesystem nor the network.

**The state of the art agrees, in writing.** Claude Code's sandbox documentation: *"The sandbox is
built into Claude Code and runs on macOS, Linux, and WSL2. **Native Windows is not supported.** On
Windows, run Claude Code inside a WSL2 distribution."* It uses Seatbelt on macOS and
`bubblewrap` + `socat` on Linux/WSL2 — **two external packages**, plus an optional seccomp filter
shipped separately — with network egress routed through a proxy that runs *outside* the sandbox.
(<https://code.claude.com/docs/en/sandboxing>, retrieved 2026-08-27.)

⚠ **That is also the answer to "a single Rust binary that is not shipping a container runtime."**
The most-resourced comparable product does not ship one either: it requires `bubblewrap` and
`socat` from the distribution, and it declines the platform 2.0 is developed on.

### 🚨 F410 — WSL2 gives you a Landlock kernel and a documented hole straight back to the Windows host, and the hole reproduces here

**The kernel is capable.** On this host, `/sys/kernel/security/lsm` reads
`capability,landlock,yama,safesetid,selinux` and `/proc/config.gz` has
`CONFIG_SECURITY_LANDLOCK=y`, `CONFIG_SECCOMP_FILTER=y`, with
`CONFIG_LSM="landlock,lockdown,yama,loadpin,safesetid,integrity,selinux,apparmor,tomoyo"`. Kernel
`6.6.114.1-microsoft-standard-WSL2`. **Landlock is present and active in the kernel WSL2 ships.**

**And it does not contain a Windows binary.** `/proc/sys/fs/binfmt_misc/WSLInterop` is registered
and `enabled`, with `interpreter /init` and `magic 4d5a` — the `MZ` header of a PE file. Reproduced:

```
$ wsl -- /mnt/host/c/Windows/System32/cmd.exe /c "echo ESCAPED-TO-WINDOWS-HOST"
ESCAPED-TO-WINDOWS-HOST
rc=0
```

A process inside the VM executed a binary **on the Windows host**, outside every Linux boundary the
VM could have set up. Claude Code's docs describe the same mechanism and say what it costs to close:
*"WSL hands a launch of a Windows binary such as `cmd.exe`, `powershell.exe`, or anything under
`/mnt/c/` to the Windows host over a Unix socket, so whether a sandboxed command can launch one
follows the sandbox's Unix-socket settings: **the optional seccomp filter has to be installed to
block the socket in the first place**."*

🚨 **So on Windows the boundary is not one layer, it is three**: a VM, a filesystem sandbox inside
it, and a syscall filter to stop the VM's own interop bridge from handing execution back. A
filesystem sandbox alone — which is what "confine the tool child to the workspace" means to most
people — leaves the escape one `exec` away, and **the model's own workspace is a place it can put a
`.exe`.**

⚠ **Not verified**: whether this WSL2 kernel's Landlock ABI includes the TCP access rights.
Network restriction arrived in **ABI 4** (<https://docs.kernel.org/userspace-api/landlock.html>,
retrieved 2026-08-27) and this kernel's ABI level was not probed — the distro present here is
Docker Desktop's internal one, which has no compiler. Treat filesystem restriction as available and
network restriction as unconfirmed on this host.

### F411 — there is no maintained, permissively-licensed, cross-platform embeddable sandbox crate in Rust

All retrieved 2026-08-27:

| crate | latest | released | recent downloads | platforms | licence |
|---|---|---|---|---|---|
| [`landlock`](https://crates.io/crates/landlock) | 0.4.7 | **2026-07-27** | 4,820,712 | Linux only | MIT |
| [`birdcage`](https://crates.io/crates/birdcage) | 0.8.1 | 2024-04-19 | 32,915 | cross-platform | **GPL-3.0-or-later** |
| [`extrasafe`](https://crates.io/crates/extrasafe) | 0.5.1 | 2024-04-16 | 6,379 | Linux only | MIT |

🚨 **`birdcage` — the only crate that claims "cross-platform embeddable sandbox" — is ARCHIVED**
(<https://github.com/phylum-dev/birdcage>, archived, retrieved 2026-08-27). It is disqualified
**twice over**: unmaintained, and **GPL-3.0-or-later** against 2.0's dual MIT/Apache-2.0 (W12, and
all three donors are MIT or Apache-2.0). `extrasafe` is Linux-only and small. The one healthy crate
is `landlock`, and it is a binding to a Linux kernel feature.

**So "a single Rust binary that sandboxes on every platform" does not exist as a dependency, and
would have to be written — three times, one per OS, with the Windows one being the one nobody has
shipped.**

## Options compared

Criteria, in the order they bind: **(a)** does it bound code the model wrote; **(b)** does it work
on Windows, where 2.0 is developed; **(c)** what does it cost to build and to run; **(d)** does it
fail loudly when it does not apply.

| option | bounds executed code | Windows | cost | fails loudly | verdict |
|---|---|---|---|---|---|
| **1. Per-tool path check (status quo)** | **no** — F404/F405/F406; not in the path of `bash`, `run_tests`, `diagnostics`, or an allowlisted interpreter | n/a | free | refusal text is wrong (F403) | **not a boundary** |
| **2. Path check + prompt on every exec tool** | partially — until the operator says yes | n/a | free to build; 30–60 prompts per task | yes | **fails the workload** — a fleet cannot prompt, and `Allow` mode makes the whole ladder inert |
| **3. `max_tier` cap: forbid the exec class outright for a role** | **yes**, absolutely — the tool is denied before any prompter | yes, it is pure policy | free | yes, structured deny | **KEEP** — the one inherited control that survives |
| **4. OS sandbox on the tool child** (Landlock/seccomp, Seatbelt, AppContainer) | yes, at the kernel | **no** — F409; three separate implementations, the Windows one unshipped anywhere | high build cost; 10–80 ms/call | only if built to | **right answer, wrong platform, not now** |
| **5. Container per task** | yes | via a VM only; daemon is a dependency, not a binary | unmeasured here; contradicts "no container runtime" | yes | **rejected for Phase 2**, revisit for a server deployment |
| **6. Run everything inside WSL2 / a VM** | yes, if the workspace moves too **and** the interop bridge is blocked | yes, with three layers (F410) | +78 ms/call, or **~290×** if the workspace stays on the Windows drive (F408) | no — interop is silent | **the only real boundary available on Windows, and it is not one layer** |
| **7. Blast-radius design: no boundary, cheap recovery** — disposable tree, everything the child does is recorded and revertible | **no** | yes | ~free (W6 item 6: 0.25 s/worktree) | n/a | **the honest Phase 2 posture, if it is *stated* rather than implied** |

## Recommendation

**Five rulings. The first is the one that changes the architecture.**

1. 🚨 **Isolation is a property of the tool child's *launcher*, never of a tool's argument
   validation.** 2.0 gets exactly one place that spawns a process — a `ToolChild` builder that
   owns cwd, environment, timeout, and whatever OS confinement is available — and **no tool calls
   `Command::new` directly**. Claudette already has one such chokepoint by accident
   (`run_command_with_timeout`, used by `bash` and by `quality.rs`); 2.0 makes it the only door and
   gives it the parts BCF has and Claudette does not (`env_clear` + allowlist) and the part nobody
   has (a stated confinement level). Path checks stay — they are good ergonomics and they catch
   honest mistakes — but **they are demoted from "the sandbox" to "an argument check", in the code
   and in the text the model is shown.**

2. 🚨 **Every tool that can execute code is one class, enumerated in one const, with a CI test that
   fails when a new tool joins it and is not gated.** Copy `egress.rs`'s shape exactly — registry,
   maintenance contract, integration test — because Claudette already proved the pattern works and
   already put these four tools in one class *for the other control* (F404). The class is at
   minimum: any shell, any toolchain runner, any package manager, anything that spawns a child.
   `run_tests` and `diagnostics` join `bash` at the same tier.

3. **The only enforcement that is real without an OS boundary is `max_tier` — a role that cannot
   execute is expressed by denying the class, not by prompting about it.** The Planner and the Judge
   get a policy capped below the exec class. This is free, it is testable, and Claudette's
   `research_permission_policy` already demonstrates it (`max_tier = ReadOnly`, with a test).

4. **The `ToolChild` result carries what actually confined it, as a value, and the operator can see
   it.** `Confinement::{ None, Cwd, OsSandbox(kind) }` — not a Boolean, not an argument that is
   silently ignored on the wrong platform (F407). **A run whose every tool child reports `None` is
   a fact the console must show**, because that is the true state of 2.0 on Windows today and
   pretending otherwise is what F403's refusal text did.

5. **On Windows, do not build a native sandbox, and do not claim one.** F409 measured that there is
   nothing to reach for without Win32 token work that nobody has shipped, and the most-resourced
   comparable product declines the platform outright. **The stated Phase 2 posture on Windows is
   option 7 — blast radius, not boundary**: a disposable tree per task (W6 item 6, 0.25 s), an event
   log that records every child, and a README that says plainly that model-written code runs with
   the user's own privileges. **When 2.0 runs on Linux or macOS, the `ToolChild` launcher acquires a
   real confinement and says so.** ⚠ This is a place where the honest answer is worse than the
   answer the brief hoped for, and it must be stated to David that way rather than softened.

**Deferred, deliberately.** Landlock/Seatbelt implementations are Phase 2 work behind the
`ToolChild` seam, not Phase 1 spikes; the seam is what has to exist first, and the seam is cheap.

## Rejected alternatives and why

- **Extending the path check to `bash` by parsing its command.** This is v1's 280 lines
  (F406), and it loses to `python file.py`. Argv is not where the code is.
- **`birdcage` as the cross-platform dependency.** Archived, and GPL-3.0-or-later against a dual
  MIT/Apache-2.0 project (F411). Two independent disqualifications; neither is close.
- **Docker per task, as v1 did.** §11 names it *"a starting point but not a boundary"* and v1's own
  compose file has no `cap_drop`, no `security_opt`, no `read_only` and no network restriction. It
  also contradicts the single-binary goal, and on Windows it is a VM wearing a daemon.
- **Prompting per exec call.** The mode 2.0 actually runs in is `Allow` / `CLAUDETTE_AUTO_APPROVE=1`
  (F403's control variant), where `authorize` returns `Allow` unconditionally. A control that only
  exists in a mode the product does not use is the same category as W4's documented-but-dead
  escalation ladder (F347/F367).
- **Mounting the workspace into WSL2 and leaving it on `D:`.** F408: ~290× on the file operations
  that are the entire job. If the tool child moves into the VM, the repository moves with it.
- **Deferring the whole question to Phase 2.** Rejected because ruling 1 changes the *shape* of the
  tool layer, and that is exactly the undo cost the budget carved out three sessions to avoid.

## Effect on fun

**Positive, and by subtraction.** F403 measured what a boundary the model can argue with costs the
operator: a refusal that does not end the attempt produced a median 6 iterations / 20.0 s / 1,227
output tokens against 4.0 / 8.5 s / 612 for cells that were not refused — the model *works harder,
in the wrong direction*, and the worst case burned 41 iterations and 208 s. A boundary the model
cannot route around is **cheaper to watch** than one it can.

It also matches what W5 already ruled: the agency is in the terminal, and the system earns trust by
showing its work. `Confinement::None`, printed, is a system telling the truth about itself.
`"writes are sandboxed to ~/.claudette/files"` — printed while a completely different root was in
force, to a model that then obeyed it (F403) — is the opposite, and it is the specific thing ruling
4 exists to prevent.

⚠ **The honest cost to fun**: on Windows the answer is "no boundary, cheap recovery", and a user
who wanted a safety story gets a warning label instead. That is a worse feeling than a green
padlock. It is also true, and the alternative on offer is a padlock that F409 measured as decorative.

## Open questions

- **OQ-W7-1.** Does this WSL2 kernel's Landlock ABI include the TCP access rights (ABI 4+)? Needs a
  one-file syscall probe in a distro with a compiler; decides whether network confinement on Windows
  needs the proxy shape Claude Code uses or comes free with the filesystem ruleset.
- **OQ-W7-2.** What does a container start actually cost here? Unmeasured (Method). It does not
  change ruling 5, but it does price option 5 for a future server deployment, and it needs David to
  start the daemon.
- **OQ-W7-3.** Does the `ToolChild` launcher own `run_tests`' *toolchain* discovery too? W6 item 5's
  toolchain profile (OQ-W6-11, answered in F335) and this item's exec class describe the same
  subprocess from two directions, and they should not end up as two mechanisms.
- **OQ-W7-4.** How often did F405's silent path actually fire in the u40 corpus? It leaves no
  refusal to grep for, so answering it means replaying the preserved cells looking for a write to a
  framework marker followed by a `run_tests`. Cheap, and it converts an availability argument into a
  rate.

## Confidence: high on the defect, high on the platform result, medium on the cost ratio

- **High on F404/F405/F406.** Every claim is a line of the donors' source read this session, and
  F405's execution path was demonstrated rather than argued. The strongest evidence is that
  Claudette's own comments state the equivalence — this item did not have to infer it.
- **High on F409 and F410.** Both are reproductions on this host with the output quoted, and both
  are independently corroborated by primary vendor documentation retrieved the same day.
- **Medium on F408's ratio.** One host, one batch, medians of 7. The ordering is not close
  (~290×) so the conclusion survives being off by a large factor, but the figure is not a benchmark.
- **The thing this item does not establish**: that an OS sandbox would be *sufficient*. It
  establishes that a per-tool path check is not a boundary and that no portable sandbox exists to
  buy. Whether Landlock plus a network rule is enough for a hostile repository is item 2's question,
  and item 2 supplies the payload this item only supplied the sinks for.
