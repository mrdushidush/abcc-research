# W10 — Fleet topology and game modes

**Status: COMPLETE — session 10 of the 14-session landing budget, 2026-08-28.** **Line budget:
≤ 400.** §13's ten sections once. **Findings F464–F474**; next free number is **F475**. The second
deliverable — the one §16 names — is `research/W10-mode-matrix.md`.

The four brief items are `RESEARCH_BRIEF.md:935-945`; the modes themselves are §9, `:447-515`.
Cross-references W2 and W3 rather than duplicating them, per the brief's own instruction.

**What this workstream changes for anyone reading only one thing.** Every one of the four items
turns out to be blocked on something that is *already on this disk and already the wrong shape*,
and in three cases the donor code says so in its own comments:

1. **Multiplayer's mechanism is not installed.** `--rpc` parses on the shipped `llama-server` and
   then fails, because the flag lives in `llama-common.dll` and the backend that implements it
   does not ship in any of the **eight** llama.cpp runtimes on this machine (F464).
2. **The transport that *does* work is loopback-only and unauthenticated** — LM Studio's
   OpenAI-compat port answers `HTTP 200` to a request with no key and to a request with a wrong
   key, and its exposure control has two documented positions: loopback, or *every* interface
   (F474). Tailscale is an interface, not a filter.
3. **The provider abstraction exists and has never been proven** — one production implementation
   out of eighteen, pinned to a concrete type at every production call site, with a signature
   (`&mut self`, returns a `Vec`, blocking `reqwest`) that makes co-op's headline requirement —
   async escalation that does not stall the local pipeline — *unrepresentable* (F466–F468).
4. **Egress is guarded on the tools and not on the model call**, which is the one path a co-op
   payload actually leaves by; and redaction, which W7 already measured as leaking 6 of 13
   shapes, is wired to six log and transcript sites and to nothing on the wire (F469–F471).

And the mesh the brief calls the proof rig is real but mostly *absent*: three nodes, two offline,
the test target a family laptop last seen a day ago (F465). So item 4's first requirement is not
discovery — it is the behaviour when a registered rig simply is not there.

---

## Question

**(a)** Does **one** provider abstraction cover a local model server, a cloud API and a remote rig,
or does one of the three not fit — and what does the donor's existing abstraction already prove or
disprove about that? **(b)** Can a run start in co-op and finish in single player, and what is the
unit of that transition — a config value, a run property, or an event? **(c)** What does the co-op
egress policy engine have to build versus inherit, given a donor that ships an `egress.rs` and a
`redact.rs`? **(d)** Is the rig registration, health and scheduling protocol testable against the
laptop over Tailscale *today*, and if not, what exactly is missing? **(e)** The §16 deliverable:
what is available in each mode, and what happens on a mid-run downgrade.

## Method

**Local-first and binary-first, because every question above is decided by something already
installed.** Four kinds of evidence, all gathered on the desktop on **2026-08-28**:

- **Shipped binaries.** All eight `~/.lmstudio/extensions/backends/llama.cpp-*` runtimes
  (2.13.0 → 2.27.1; CPU-AVX2, CUDA 12, Vulkan) enumerated for `ggml-*.dll` membership, and their
  DLLs read for strings.
- **Live network state.** `tailscale status --json`; `Get-NetTCPConnection -State Listen`;
  `~/.lmstudio/.internal/http-server-config.json`; `lms server start --help`; and an
  unauthenticated `curl` against the running server.
- **Donor source.** `D:\dev\claudette` HEAD, `crates/claudette/src/**` — 93 files — read for the
  provider trait, its implementations, the egress guard's call sites, the redaction call sites,
  `brain_selector.rs` and `hw.rs`.
- **Inherited findings**, quoted rather than re-measured: F79, F275, F462, F463, W7's redaction
  measurement, W3's lifecycle. **No spike was run** — the standing rule for the five cut docs.

⚠ **One method finding, recorded because it produced a false result that survived two tool calls.**
The binary scan was first run with `strings`, which **is not installed in this shell**. Every
lookup returned `0` — including three positive controls — and `grep -c` on a binary counts *lines*,
not matches, so it under-reports too. Redone as `tr -c '[:print:]' '\n' | grep`, with
`ggml_backend_dev → 16` in `ggml-base.dll` as the control that proves the method finds positives.
**Item 44 of the standing rule, a second time: a zero from an unvalidated instrument is not a
measurement.** Every count below was taken with a control in the same command.

## Inherited

| What | Where | Verdict |
|---|---|---|
| `ApiClient`, the provider seam | `runtime/conversation.rs:141` | **KEEP the seam, replace the signature** — F466, F468 |
| `OllamaApiClient`, the one real provider | `api.rs:585` | KEEP as the local case; it is the only proven one |
| `egress.rs` offline mode | 621 lines, 28 referencing files | **KEEP the three shapes, not the policy** — F470 |
| `redact.rs` | 6 call sites, all logs and transcripts | **DO NOT extend** — wrong side of the wire, F471 |
| `brain_selector.rs` tiered fallback | 789 lines | **KEEP the machinery, invert polarity and latch** — F472 |
| `hw.rs` VRAM detection + `VramSource` | 208 lines | KEEP `VramSource`; the payload is 1 of 5 fields — F473 |
| `scheduler.rs` | 1,271 lines | **NOT a work scheduler** — wall-clock cron over `schedule.jsonl` |
| llama.cpp RPC backend | not installed | **F464** — the mechanism §9 names does not exist here |

## Findings

### 🚨 F464 — `--rpc` ships, the RPC backend does not, and the failure strings ship with it

Across all **eight** llama.cpp runtimes installed under `~/.lmstudio/extensions/backends`
(`win-x86_64-avx2-2.13.0`, `nvidia-cuda12-avx2` 2.13.0 / 2.14.0 / 2.24.0 / 2.25.2 / 2.27.1,
`nvidia-cuda-avx2-2.13.0`, `vulkan-avx2-2.13.0`) the ggml backend libraries are exactly
`ggml_llamacpp.dll`, `ggml-base.dll`, `ggml-cpu.dll` and one accelerator (`ggml-cuda.dll` or
`ggml-vulkan.dll`). **There is no `ggml-rpc.dll` and no `rpc-server.exe` anywhere under
`~/.lmstudio`.** Yet `llama-common.dll` carries the entire argument surface — `--rpc`,
`LLAMA_ARG_RPC`, `ggml_backend_rpc_add_server`, `comma-separated list of RPC servers (host:port)` —
and `llama.dll` exports `llama_supports_rpc`. The strings that settle it are the *failure* paths
shipped beside them: **`failed to find RPC backend`** and **`failed to find RPC add server
function`**, which upstream prints when the named backend cannot be resolved at run time. And LM
Studio's own layer — `llm_engine.dll`, `llm_engine_cuda12.node`, `liblmstudio_bindings_cuda12.node`
— contains **zero** `rpc` strings, so nothing in `lms load`'s config surface could pass the flag
even if the library appeared. ▶ Multiplayer's mechanism is not "shipped but insecure", which is how
W9's F462 left it; on this machine it is **absent**, and the *server* half was never built at all.
Item 4 therefore opens a **W2 serving-runtime decision**, not a W10 protocol decision.

### 🚨 F465 — the mesh is real, two of its three nodes are offline, and the test target is a family laptop

`tailscale status --json`, desktop, 2026-08-28, client **1.102.2**, tailnet `tail8dfa6e.ts.net`,
MagicDNS on: `100.79.86.45 david` (self, online, owner and admin), `100.100.9.101 david-pub`
— **offline, last seen 63 days** — and `100.86.64.47 laptop-kids` — **offline, last seen 1 day**.
Health reports two DNS-configuration failures. ▶ §9's *"there is a real second node on a real
Tailscale mesh, so the protocol can be tested end to end"* is right about existence and wrong about
availability. The single test target is a shared household machine whose uptime nobody controls,
and the third node has been dead two months. **The first thing the protocol must handle is not
discovery or capability matching — it is a registered rig that is simply not there**, which §9
lists last, under failure handling. It also means every latency, tokens/sec and drain measurement
item 4 wants is gated on someone switching a laptop on, so the protocol has to be *provable
offline*, against a loopback second instance, or it will not be proved at all.

### 🚨 F466 — the provider trait exists and has one production implementation out of eighteen

`crates/claudette/src/runtime/conversation.rs:141` —
`pub trait ApiClient { fn stream(&mut self, request: &ApiRequest<'_>) -> Result<Vec<AssistantEvent>, RuntimeError>; }`
— one method. The whole 93-file crate declares **five** traits (`Clock`, `Embedder`, `ApiClient`,
`ToolExecutor`, `PermissionPrompter`). `grep -rn 'impl ApiClient'` returns **18** implementations:
**one production** (`api.rs:585`, `OllamaApiClient`) and **seventeen test doubles**, every one of
them inside `conversation.rs`'s own test module (`ScriptedApiClient`, `QueuedApi`, `CapSpiralApi`,
`GitSpiralApi`, …). ▶ The abstraction was extracted **for testability, not for provider
polymorphism**, and it has never been exercised against a second real backend. W10 item 1 does not
inherit a working provider abstraction. It inherits a seam — and a seam that has only ever had
fakes on the other side of it is an untested hypothesis about where the boundary goes.

### F467 — and production pins the concrete type, so the seam is not actually open

`brain_selector.rs:39` — `type AgentRuntime = ConversationRuntime<OllamaApiClient, AgentToolExecutor>;`
The runtime is generic over the client, but every production path **monomorphises it to the
concrete `OllamaApiClient`**: there is no `dyn ApiClient` and no `Box<dyn ApiClient>` anywhere in
the crate. So the cost of a second provider is not "write an `impl`" — it is threading a second type
parameter, or introducing dynamic dispatch and with it a boxing decision on a hot streaming path,
through `run/runtime_build.rs`, `run/forge_run.rs`, `brain_selector.rs` and every builder that names
the alias. ▶ This is exactly the brief's stated reason for asking the question early — *"expensive
to change later"* — and it is already mildly expensive now.

### 🚨 F468 — the inherited signature makes co-op's headline requirement unrepresentable

Two properties of `fn stream(&mut self, …) -> Result<Vec<AssistantEvent>, RuntimeError>`: it is
**blocking** — `api.rs` uses `reqwest::blocking` throughout and says so (*"Reqwest's blocking
Response implements Read, so we can wrap it in a BufReader"*) — and it takes **`&mut self`**, which
makes two concurrent calls on one client impossible *at the type level*. §9's co-op section asks for
*"async escalation so a pending cloud call does not stall the local pipeline, plus retry and
fallback."* **That is not unimplemented in the donor; it is unrepresentable in the donor's trait.**
Returning a `Vec` at the end also means the caller cannot see the first token until the last one
arrives, which is the opposite of what W5's live console needs. ▶ Item 1's trait must take `&self`
and hand back a stream or a handle, or co-op's availability bullet is dead on arrival — and this is
the single change that most justifies doing the trait work before Phase 2 code exists.

### 🚨 F469 — egress is guarded on the tools and not on the model call, which is co-op's only egress path

`egress.rs` is **621 lines** and `grep -rln 'egress::'` matches **28 files**. `guard` and
`guard_subprocess` fire in `google_auth.rs` (×4), `telegram_mode.rs`, `tools/calendar.rs`,
`tools/facts.rs` (×2), `tools/git.rs` (×2), `tools/github.rs`, `tools/gmail.rs`,
`tools/mission.rs` (×2) and `tools/registry.rs` (×2). **`api.rs` calls no guard at all.** Its only
two uses of the module are `egress::local_http_builder()` at lines 236 and 515, which is the whole
of `reqwest::blocking::Client::builder().no_proxy()` (`egress.rs:278-280`). `firstrun.rs:62` states
the rule in a comment: *"no `egress::guard()` here because the target is the local backend."* ▶ The
inherited control is a **tool-egress** control. Co-op's egress is **model-egress** — a disjoint
surface with zero coverage — so attaching a cloud arm to `ApiClient` creates an unguarded egress
path *by construction*, and `NET_TOOLS`' maintenance contract cannot catch it, because a provider is
not a tool. This is W7's ruling arriving from a new direction: the control has to bind the thing
that actually has the argument.

### 🚨 F470 — what does exist is a switch, not a policy engine — but its three shapes are the ones to keep

`egress.rs`'s allow-list is *the resolved local backend host, plus loopback*; everything else is
hard-blocked with one uniform message; and the whole thing is driven by one boolean (`--offline` /
`CLAUDETTE_OFFLINE=1`). There are **no per-repo rules, no content rules, no destination classes and
no payload log**. §9 asks for *"explicit per-repo rules for what may cross to a cloud provider, a
redaction step before egress, and an audit log of every payload sent"* — the donor supplies **none
of the three**. What it *does* supply is three structural ideas worth copying verbatim: **(1)** one
registry (`NET_TOOLS`) as the single source of truth, with a written maintenance contract; **(2)** a
CI test that drives every listed item through the real dispatcher and asserts the refusal, *"turning
the air-gap from a documented posture into a CI-proven guarantee"*; **(3)** a startup preflight
(`preflight_offline_proxy`) that refuses to start when a proxy variable is set, because a proxy
would route even loopback traffic off-box and the banner would then be a lie. ▶ Inherit the
**shape** of the enforcement, and build the policy new.

### 🚨 F471 — redaction is a display filter: six call sites, none of them the wire

`grep -rn 'redact::'` over the crate, excluding the module itself, returns exactly six calls:
`runtime/session.rs:106` (the rendered prompt, for display), `tools/git.rs:227` and `:239` (args and
stderr), `tools/shell.rs:571` and `:712` (command and output), and `transcript.rs:164`. **Not
`api.rs`. Not `conversation.rs`.** Every secret `redact.rs` catches is caught on its way to a *log*;
nothing is caught on its way to a *model*. Stack that on W7's measurement — `redact.rs` leaks **6 of
13** shapes, including every credential this project itself uses, and the terminal and the model's
own context are unredacted sinks — and co-op's redaction step today is a function that is both too
weak and wired to the wrong side. ▶ Item 3 builds redaction **new, at the client boundary**, and
does not extend `redact.rs` outward; the existing function stays where it is, doing the log job it
already does.

### 🚨 F472 — the donor already does a mid-run model transition, with the opposite polarity and the opposite latch

`brain_selector.rs` is **789 lines** of exactly the machinery item 2 needs: snapshot the session
before the turn, run the primary, test three strict "stuck" signals (`Err("no content")` surviving
the retry nudge; zero assistant text blocks at or near `max_iterations`; **≥3** consecutive
`is_error` tool results), then build a fresh runtime around the fallback model *and the pre-turn
snapshot*, replay the same input, swap the caller's runtime pointer, and append a record to
`~/.claudette/fallback.jsonl`. Two properties decide item 2. It is **upward** (weak → strong) and it
is **per-turn reverting** — the module's own words, *"per-turn revert: the next turn goes back to
the primary."* Item 2 asks for a transition that is **downward** (co-op → single player) and
**sticky**: a spent budget or a dropped network does not un-drop. ▶ Same machinery, inverted on both
axes — and its cost comment, *"every fallback costs a ~5-10s model swap"*, is the donor's estimate,
where the measured swap on this hardware is **23.77 s** (F79). The JSONL record is the right
instinct, and becomes W3 event-log rows rather than a private file.

### F473 — the rig-registration payload is already written: one vendor, one field of five

`hw.rs` is **208 lines**: `detect_vram_gb()` parses `nvidia-smi` output, `resolve_vram_gb()` returns
a value **plus a `VramSource`** saying how it was learned, and `recommend_brain(vram_gb,
openai_compat)` maps the number to a model recommendation. §9 wants a rig to advertise **VRAM,
system RAM, resident models, measured tokens/sec and queue depth** — the donor computes **one of the
five**, by shelling out to an NVIDIA-only tool, so the 4 GB laptop and any AMD, Intel or Apple rig
advertise nothing at all. ▶ The idea to generalise is `VramSource`: **a capability claim that
carries its own provenance is the only kind that can be distrusted later**, which is §9's "behaviour
when a rig is slower than advertised" answered at the type instead of in the scheduler.
⚠ Naming trap for whoever reads the tree next: `scheduler.rs` (1,271 lines) is a **wall-clock**
scheduler over `~/.claudette/schedule.jsonl` — cron, not dispatch. **Nothing in the donor schedules
work across workers.**

### 🚨 F474 — the only working transport is unauthenticated, and its exposure switch is all-or-nothing

Measured on the desktop, 2026-08-28. `Get-NetTCPConnection -State Listen` shows LM Studio holding
exactly two sockets, **both on `127.0.0.1`**: `:1234`, the OpenAI-compat server, and `:41343`, the
bare server. `~/.lmstudio/.internal/http-server-config.json` reads `"networkInterface":
"127.0.0.1"`, `"port": 1234`, `"cors": false`, `"autoStartOnLaunch": true`,
`"justInTimeModelLoading": true` and **`"logSensitiveData": true`**. And the server has **no auth
whatsoever**: `GET /v1/models` with **no** `Authorization` header returns **HTTP 200** and the full
model list, and the same request with `Authorization: Bearer totally-wrong` also returns **HTTP
200**. The exposure control is `lms server start --bind <address>` (or `LMS_SERVER_HOST`), whose
help documents exactly two values — `127.0.0.1` for loopback and **`0.0.0.0` to "accept connections
from the local network"**. ▶ So the transport multiplayer would actually use today has a binary
switch whose "on" position publishes an **unauthenticated inference endpoint on every interface** —
the tailnet *and* the LAN, because **Tailscale is an interface, not a filter**. Nor does the overlay
narrow it: Tailscale's own documentation states that *"when you first create your tailnet, the
default tailnet policy file enables communication between all devices within the tailnet"* and that
*"in the absence of an `acls` section in the tailnet policy file, Tailscale applies the default
allow all policy"* (`https://tailscale.com/kb/1018/acls`, retrieved 2026-08-28), so `laptop-kids`
would reach the port too. The narrow control is `--bind 100.79.86.45`, the
tailnet address specifically, which the help does not document but the parameter accepts. Compare
F464's RPC warning, *"never run the RPC server on an open network"* — the *unauthenticated* half of
that warning is already true of the port that is in use right now.

## Options compared — item 1's provider abstraction

Criteria: does it represent async escalation (§9); the cost of adding the second provider today;
traceability of which provider served a call; honesty about RPC's actual semantics (F462 — RPC
splits one model's weights and KV across devices, so a rig makes one model *bigger*, never two
workers); and effort before Phase 2 code exists.

| Option | Async | Cost of 2nd provider | Traceable | Honest about rigs | Verdict |
|---|---|---|---|---|---|
| **A.** Keep `ApiClient` as is, add impls | ❌ excluded by `&mut self` + `Vec` | low to write, high to wire (F467) | caller only | ❌ models a rig as a peer | **reject** |
| **B.** New `Provider`, `&self` + stream handle, **two** cases (local, cloud); a rig is a *device* on the local case | ✅ | one type parameter at build sites | provider id on every event | ✅ matches F462 | **ADOPT** |
| **C.** Three-case trait including `RemoteRig` | ✅ | as B, plus a third impl | ✅ | ❌ the third case has no wire protocol of its own | reject |
| **D.** Concrete enum, no trait | ✅ possible | edit one enum | ✅ | neutral | reject — discards the 17 existing test doubles |
| **E.** External gateway process (OpenAI-compat fan-out) | ✅ | zero Rust change | ❌ one opaque hop | ✅ | reject — makes F469's blind spot permanent |

## Recommendation

### 1. `Provider` takes `&self` and returns a stream, and there are two cases, not three

```rust
pub trait Provider: Send + Sync {
    fn id(&self) -> ProviderId;               // on every event; W3's log, not the caller's memory
    fn class(&self) -> ProviderClass;         // Local | Cloud — the egress-relevant fact
    fn start(&self, req: &ApiRequest<'_>) -> Result<Box<dyn TurnStream>, ProviderError>;
}
```

`&self` rather than `&mut self` is the whole point: it permits a pending cloud turn and a running
local turn to coexist, which F468 shows the inherited trait forbids. `TurnStream` yields the
existing `AssistantEvent` values one at a time and is cancellable, which W3 already requires of an
attempt and W5 already requires of the console. **`ProviderClass` is two-valued on purpose** — it is
the predicate the egress guard binds to, and a value that is only ever read by a `match` asking
"does this leave the machine" must not have a third arm that answers "sort of".

### 2. A remote rig is a **device**, not a provider — the brief's key question, answered

§9 asks: *"is a remote rig just another provider behind the same interface as a cloud model, or does
it need its own plane? Argue it."* It is neither. llama.cpp's own RPC documentation
(`https://github.com/ggml-org/llama.cpp/blob/master/tools/rpc/README.md`, retrieved 2026-08-28 —
W9 F462/F463) says the runtime *"distributes model
weights and the KV cache across all available devices — both local and remote — in proportion to
each device's available memory."* **A rig therefore spreads one model thinner; it does not add a
second worker.** It buys parameters or context at LAN latency and buys **no parallelism at all**,
which compounds F275 (co-residency is arithmetically impossible on this card) and F79 (23.77 s to
swap). So a rig is configured *on the local provider*, as a device list, and it changes that
provider's **capability** — a bigger model, or a longer context, becomes resident — rather than
adding a routing target. Nothing above the provider ever names a rig. ⚠ And per F464 the device
backend is not installed, so this is a design that is currently **unrunnable**; see §5 below.

### 3. Mode is a per-run, one-way ratchet, and a downgrade is an **event**, not a config change

- **Mode is a property of a run**, fixed at admission and recorded as the run's first event. Two
  values matter at runtime — `SinglePlayer` and `CoOp` — because per F462 multiplayer changes a
  provider's capability rather than the run's topology, and because with **zero standing cloud
  spend** (`decisions` Q7) co-op's cloud arm is a configured-but-usually-absent provider.
- **Transitions are downward only, and sticky.** `CoOp → SinglePlayer` is permitted on a budget
  ceiling, an egress denial or a network failure, and it **latches for the rest of the run**. The
  reverse is **denied**: an upgrade mid-run would make the run's own egress record retroactively
  wrong, and W7's ruling is that the control that works is denying the class.
- **The transition is an event on the durable log** (W3), carrying reason, `Seq` and the provider
  that failed — so the console can show it, replay can reproduce it, and the *effective* mode at any
  point is a projection, exactly as W3 makes status a projection rather than a column.
- **In-flight work at the moment of downgrade:** an attempt with an outstanding cloud call is
  cancelled and tombstoned `HardFailure(egress_revoked)`; its task returns to `Queued` and is
  re-attempted locally. Attempts with no outstanding cloud call are untouched. That is F472's
  machinery with the polarity and the latch inverted, and it reuses W3's per-state contract table
  unchanged — **no new Task state is introduced by any of it**.

### 4. The egress engine binds the provider, not the tool — and it is a second guard, not an edit

Item 3 builds: **(a)** a per-repo policy resolved at run admission and frozen into the run, because
a policy that can change mid-run cannot be audited; **(b)** a redaction pass **at the
`Provider::start` boundary** for every `ProviderClass::Cloud` call — new code, not `redact.rs`
extended outward (F471); **(c)** an audit record per outbound payload — hash, byte count, policy
decision, redaction hits — as W3 event rows rather than `brain_selector`'s private JSONL (F472).
It inherits `egress.rs`'s three shapes from F470 verbatim: one registry with a maintenance contract,
a CI test that drives every entry through the real dispatcher and asserts the refusal, and a startup
preflight. **Single player is then a policy, not a code path** — zero `ProviderClass::Cloud`
providers admitted — which is the whole reason §9 can call it the primary mode rather than a
degraded fallback.

### 5. Rig registration: a claim that carries its provenance, and is absent by default

Generalise `hw.rs`'s `VramSource` into every advertised field — VRAM, system RAM, resident models,
measured tokens/sec, queue depth — each carrying **how it was learned**: probed, self-reported,
configured or stale. §9's "behaviour when a rig is slower than advertised" then has somewhere to
live, and a self-reported number can be distrusted without a special case. **The default health
state is `Absent`, not `Unknown`** — F465 says two of three nodes are offline and the test target is
a household laptop, so absence is the common case, not the exception. ▶ **And none of this is built
in Phase 2 until F464 is resolved.** The honest order is (i) W2 re-opens the serving-runtime
question with "does it ship `ggml-rpc`?" as a new criterion; (ii) the registration record is
designed and proved against a **second local instance on loopback**; (iii) the laptop is a
confirmation, not a dependency. **No spike this session** — the Tailscale/RPC proof stays recorded
as **OQ-W9-5**, and when it is run it runs behind the overlay from the first attempt, never on the
LAN "just to see".

## Rejected alternatives and why

- **A third trait case for remote rigs.** Rejected by F462: a rig has no wire protocol distinct from
  the local server's — it is a device the local server enumerates. A third arm would be a case that
  never differs from the first, and every `match` would carry a redundant branch that a later reader
  would try to fill.
- **Extending `redact.rs` to cover the wire.** Rejected by F471 plus W7's 6-of-13 measurement: the
  function is too weak *and* on the wrong side. Reusing it would make a measured leak look guarded.
- **Reversible mode transitions.** Rejected: upgrading mid-run rewrites the meaning of every earlier
  event in the run's egress record. The cost of the ratchet is one abandoned run; the cost of
  reversibility is an unauditable one.
- **Binding the server to `0.0.0.0` behind Tailscale.** Rejected by F474: the switch exposes every
  interface, the endpoint has no auth, and a tailnet's default ACL is permissive between own nodes.
  Bind the tailnet address specifically, or do not expose it.
- **A gateway process (option E).** Rejected: it would route co-op's payloads through an opaque hop
  at exactly the place F469 says the project has no visibility today.

## Effect on fun

Single player being the *primary* mode is the fun-preserving decision, and it is now also the
truthful one: with zero standing cloud spend and no installed RPC backend, the machine on the desk
is the whole army, and the game has to be good with the network unplugged. That is a constraint that
makes the console better rather than worse — every unit on the field is one you own. The downgrade
ruling adds something genuinely playable: **losing air support mid-mission becomes an event on the
field**, with a reason and a timestamp, instead of a silent config change nobody sees. And
multiplayer keeps its best moment even after F462 demotes it from parallelism to capacity —
reinforcements arriving means the *big* brain becomes available, which is a better story than
"throughput went up 4%".

## Open questions

| ID | Question | Owner |
|---|---|---|
| OQ-W10-1 | Does 2.0 ship its own llama.cpp build with `GGML_RPC=ON`, or drop rigs until LM Studio ships one? | **W2**, re-opened by F464 |
| OQ-W10-2 | `Box<dyn TurnStream>` versus a generic associated stream — boxing cost on a per-token path is unmeasured | Phase 2, with a bench |
| OQ-W10-3 | Per-repo egress policy: a file in the repo, or in `~/.abcc`? In-repo is reviewable and also attacker-writable | W7 + W12 |
| OQ-W10-4 | Does a downgrade abandon the run's *completed* cloud work, or keep it and mark the run mixed-provenance? | David |
| OQ-W10-5 | `logSensitiveData: true` on the local server (F474) — leave it as a useful audit, or turn it off as a second unredacted sink? | David |
| OQ-W10-6 | Is `--bind <tailnet-ip>` stable across LM Studio upgrades, given the help documents only two values? | re-check per release |

## Confidence: high on the four findings that are binary facts, medium on the trait shape

**High** on F464, F465, F471 and F474 — each is a presence/absence or an HTTP status code measured
on this machine today, with a control in the same command. **High** on F466, F467, F469 and F472 —
counts over a checked-out tree, reproducible with the greps quoted. **Medium** on the `Provider`
signature: `&self` plus a stream is forced by F468, but the ownership of `TurnStream` and the boxing
question (OQ-W10-2) are unmeasured, and this is the one decision the brief itself flags as expensive
to change. **What would raise it:** implementing `Provider` with the existing `OllamaApiClient`
behind it and one loopback second instance standing in as the "rig", which also settles OQ-W10-2
with a number — roughly a day, and explicitly Phase 2's.
