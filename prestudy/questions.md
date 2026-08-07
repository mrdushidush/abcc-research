# Open Questions for Phase 1

Per brief 4.5: everything Phase 0 noticed that the research phase needs to answer, including
things not currently in section 11. **Not answered here deliberately.**

Ordered by what unblocks the most work.

---

## 0. Questions Phase 0 already closed - do not spend Phase 1 on these

The most useful thing this document can do is stop the research phase re-deriving what three
working repos already answered. Each of these is an open question in the brief that Phase 0 found
already settled.

| Brief asks | Already answered by | Answer |
|---|---|---|
| W2: "how does the Rust orchestrator talk to llama.cpp? HTTP server, in-process bindings, or something else" | Claudette `api.rs` | HTTP, two dialects (Ollama-native `/api/chat` and OpenAI-compatible). No FFI. Reached LM Studio, `llama-server` and Ollama across 131 configs, `--jinja` parity proven. |
| §17 Q5: console shape | David, 2026-08-07 | Full isometric C&C-style web UI. |
| §17 Q1: what BCF is | Phase 0 | Public, Apache-2.0, sole-authored, greenfield POC. Section 3.3 was broadly right. |
| §17 Q4: Claudette's relationship | Phase 0 | `claudette-forge` is the self-edit sandbox, `claudette-research-control` is the Q56 runner. Both are working roles, not stale copies. |
| W4: "assess whether a fine-tuned router or worker is worth it. Expect no" | `CHAMPION-DOSSIER.md` §8 | NO, with four structural blockers and written trigger conditions for reopening. |
| W1: NVFP4 / MXFP4 | May 2026 benchmark + champion campaign | Null-to-negative on both backends. Blackwell FP4 does not pay on a bandwidth-bound workload. Closed. |
| W8: does an eval harness exist | Q56 | 56 tasks, per-task shell verifiers, no LLM judge, 131 configurations, frozen core. |
| W5: SQLite versus Postgres | Claudette `~/.claudette/` | A serious daily-driver agent needs no database server. Files plus one SQLite. |

**But see section 1 below** - one thing the brief treats as settled is *not*, and it is load-bearing.

---

## 1. The one settled decision that needs reopening

**The hardware constraint framing in section 5 describes a configuration that was superseded on
2026-07-11.**

The brief says "32GB system RAM is the ceiling, not 16GB VRAM. MoE under llama.cpp with
`--n-cpu-moe`, mmap off." Every residency and concurrency question in W1, W2 and W11 inherits it.
`CHAMPION-DOSSIER.md` records:

- `--cpu-moe` measured at 1.16x, "worse than fit-target packing", verdict "don't use".
- The crowned config runs **zero CPU experts, fully resident**, 15.4 of 16.3 GiB.
- "Residency is ~90% of the win; MTP in LMS is a small bonus."

Questions this raises:

1. **Should W1 and W2 be reframed from "survive expert offload into 32 GB" to "stay resident in
   16 GB"?** These are different research questions with different answers.
2. **Does the 32 GB versus 64 GB question (§17 Q9) still matter?** On the crowned configuration
   system RAM is barely involved. David has answered 32 GB fixed, so this is now about whether
   that constraint even binds.
3. **Does quantizer lineage become a first-class W1 variable?** byteshape ShapeLearn at 3.06 bpw
   tied unsloth's 4-bit on quality using 4.1 GB less. That is a bigger lever than model choice and
   the brief does not mention it.
4. **What is the concurrency answer when the model is fully resident?** The brief assumes RAM
   pressure bounds builder fan-out. If nothing spills, the bound is VRAM and KV cache instead.
   Entirely different formula, and W11's fan-out number depends on it.
5. **Does 2.0 pin a quant, or ship a chooser?** Q56 has the harness to answer "which quant for
   your card" for any user. That is a shippable feature, not just an internal decision.

David has confirmed Q56 reproduction is scheduled and expects the numbers to hold. The reframing
question stands regardless of the outcome.

---

## 2. Questions for David

Decisions only he can make. Several gate specific workstreams.

1. **`BMORE.md`** in the public battle-command-forge repo is a full commercial product
   specification (SaaS product-data management for SMB computing retailers, with revenue targets).
   Demo mission input, or a real business document that should come out of a public repo?
2. **Licensing.** ABCC is MIT, Claudette is MIT-OR-Apache dual, BCF is Apache-2.0. Sole authorship
   is confirmed so relicensing is available. What does 2.0 ship as? (Gates W12.)
3. **Repo and naming** (§17 Q3, still open). New repo, or a major version of ABCC? Still called
   Agent Battle Command Center? Gates W12 entirely.
4. **Frontier API spend ceiling** (§17 Q7, still open). W4 needs an objective to optimize routing
   against.
5. **RTS framing depth** (§17 Q8, still open). Presentation layer only, or into the Rust domain
   model? Note this is now sharper than when the brief was written: Claudette's `forge/types.rs`
   states the principle "role naming is about what the model is doing, not which weights are
   loaded", which is a *functional* naming scheme. Military naming would replace it. Rust enums
   make the choice sticky.
6. **Existing V1 users** (§17 Q10, still open). Clean break with a migration story, or does
   something keep working?
7. **Does Claudette keep shipping?** The brief scopes out Claudette's roadmap but 2.0 reuses most
   of its engine. If both are live, is the shared code a crate, a fork, or a copy? This is
   §17 Q4 at the code level rather than the process level, and W3 needs it.
8. **Is the ABCC Postgres extraction wanted at all now?** David deferred it and named Q56 the real
   eval. W4's retrospective routing analysis is the only remaining consumer. Worth the dump, or
   drop the ambition?

---

## 3. New questions the brief does not have

Things Phase 0 surfaced that section 11 does not cover.

### 3.1 Architecture

1. **Async or not.** BCF is tokio-first. Claudette is deliberately sync and `decisions.md` AD-7
   rejects tokio with reasons ("no pipeline stage has concurrent I/O that async would help").
   2.0 wants parallel builders, a live WebSocket console and a fleet protocol - all of which
   postdate that decision. This is the largest unforced choice in W3 and it must not be inherited
   by accident from whichever file gets ported first.
2. **`panic = "abort"` versus a long-running orchestrator.** Both Rust repos use it. Claudette's
   comment is explicit that the agent loop does not survive a panicked turn. Acceptable for a CLI;
   is it acceptable for a supervisor holding a task graph and a WebSocket console?
3. **Does 2.0 keep the single-crate discipline?** Claudette is 60k lines in one crate and says so
   deliberately. BCF is 16k flat. 2.0 adds a console, a fleet protocol and a scheduler. At what
   point does a workspace become correct, and does `cargo check` latency (W13) drive that?
4. **Where does the tool registry live when there are multiple concurrent agents?** Claudette's
   `ToolRegistry` is one `Arc<Mutex<_>>` per runtime. Four parallel builders means four
   registries, or one shared. Not obvious, and it interacts with permissions.

### 3.2 Verification and stages

5. **Are gate scores comparable across complexity bands?** BCF's thresholds fall as complexity
   rises, so a 9.4 at C3 and an 8.1 at C9 are both passes and mean different things. Does 2.0 want
   one comparable scale or one calibrated bar? Affects every dashboard that charts quality.
6. **Recalibrating the gate for local-first.** BCF's ladder averaged 7.5 all-local; the successor
   chose a config-driven 8.0. What is the right number for a 35B-A3B doing repo work rather than
   greenfield? Needs measurement, not opinion.
7. **Decomposition: contradictory evidence inside the family.** BCF tried it and reverted
   ("caused duplicate projects"); ABCC shipped it for missions; Claudette's forge has an optional
   CTO decomposition. Different regimes (greenfield versus repo work, 7b-32b versus 35B-A3B). W11
   must test rather than assume, in either direction.
8. **Nine stages collapsed to five and stayed there.** BCF ran nine; the successor folded
   Security + Critique + CTO into one gate call, citing "single critique call > 5 parallel calls,
   Ollama is sequential anyway". Does W11's reconciliation start from five rather than nine?
9. **Verifier-as-JSON versus verifier-as-code.** Claudette's forge Verifier is a tool-less LLM
   turn emitting `{score, pass, feedback}`. BCF's verifier is deterministic code. The gate formula
   assumes the second. Which is the Gate stage in 2.0, and can both coexist?

### 3.3 Tools and context

10. **Does the `enable_tools` indirection survive a 35B-A3B?** It was built for token economy and
    nearly broke on a 3-bit q3. The fix (pre-enable the coding core) means a coding session
    already ships 2.2k tokens of schema. If the base agent handles the meta-call reliably, is the
    indirection still earning its keep, or is it complexity with no remaining payer?
11. **Prefix caching against a factory workload.** W2 raises it; nothing in the family exploits
    it. With four builders sharing a near-identical system prompt the savings could be large, and
    it interacts with the tool registry being *mutable* per turn (a changed `tools` array
    invalidates the prefix). Possible direct conflict between the two mechanisms.
12. **Grammar-constrained decoding.** Named in W2, unused anywhere in the family. Claudette gets
    parseable output by asking nicely and repairing. Is constrained decoding a bigger quality
    lever than model choice, as W2 suspects?

### 3.4 Console and operator control

13. **What is the unit of operator control?** Pause a task, a stage, a builder, or the whole run?
    Nothing in the family has working pause (ABCC's abort endpoint is a no-op), so there is no
    precedent to inherit and the answer shapes the domain model.
14. **How does take-over work concretely?** The operator edits a prompt mid-run, or takes the
    keyboard, or hand-writes the diff. Each implies different state machinery. This is the
    single most-cited 2.0 feature and the least specified.
15. **Does the isometric console render live state or replay?** Replay is much easier and W5's
    "replay a run" requirement may make it the primary mode with live as a special case.
16. **Is there a headless mode?** Claudette is a CLI, ABCC is a browser app. A developer on SSH
    cannot open an isometric web console. Does 2.0 need a TUI fallback, and does that make the
    inherited Ratatui work relevant after all?

### 3.5 Evaluation

17. **How do you measure fun without asking the user to score it?** W8 wants a log rather than a
    vibe. Candidate signals: does David open it unprompted, session length, does he finish runs or
    abandon them, intervention rate. None are in any harness today.
18. **How does the C8-C9 import preserve frozen-core comparability?** They must land as a
    K-series-style extension. Does the extension get its own score column, or does "Q56" become
    "Q66" and break every historical row?
19. **What replaces Q56's one-shot shape?** Every Q56 task is `claudette "<prompt>"` and exits.
    2.0's differentiator is interactive operation, which no existing task measures.

### 3.6 Security and distribution

20. **How does the air gap survive co-op mode?** Claudette's guarantee is structural: no cloud
    code is compiled in by default. 2.0 needs cloud escalation on purpose. Does the guarantee
    become a feature flag (weaker), a runtime policy (weaker still), or does 2.0 ship two binaries?
21. **Egress policy per repo.** W10 wants per-repo rules plus redaction plus an audit log.
    Claudette has the enforcement primitive (`egress.rs`) but no policy layer and no per-repo
    notion. That is new work.
22. **Prompt injection through the codebase.** W7 names it; nothing in any repo mitigates it.
    Claudette's `<email>` provenance wrapping for Gmail bodies is the only related precedent, and
    it does not extend to file contents a builder reads.

### 3.7 Process

23. **How do agent-authored commits and community PRs coexist?** W13 asks. ABCC's recent history
    is Claudette-authored commits on a public repo with real contributors, so there is live
    experience to mine that the brief does not know about.
24. **What stops ADRs going stale?** Claudette's `decisions.md` needed a warning banner declaring
    itself "fiction relative to the shipped product". A supersession marker, or a test that fails
    when an ADR contradicts the code?

---

## 4. Questions that need a measurement before they can be answered

Flagged for the benchmark plan.

1. Peak system RAM and VRAM for N concurrent builders on the crowned configuration. The brief
   wants a hard limit reported, not a tuning suggestion.
2. Model swap cost with mmap off from NVMe over PCIe 3.0 x8. Decides whether swapping is viable
   or one resident model is the whole design.
3. Prefill and decode throughput per candidate, plus quality per quantization level.
4. Prefix-cache hit rate and token savings on a factory workload.
5. Does the Q56 pass rate change when the same model runs behind 2.0's orchestrator rather than
   Claudette's CLI? This is the honest regression test for the port.
6. `cargo check` and full-test-run latency for the 2.0 workspace. Claudette's 14.76 s is the bar
   and agent loop latency is bounded by it.
7. The isometric console's frame budget with a live task graph at 2.0's event volume. ABCC's R3F
   battlefield was built for three agents.
8. Whether repairing the CodeX-7 prompt (the numbered list starting at item 2) measurably changes
   anything. Free experiment with a known-damaged baseline.

---

## 5. Corrections that Phase 1 should carry forward

Errors found in the brief during Phase 0 that change what Phase 1 does. The full lists are in the
three dossiers; these are the ones with research consequences.

1. **88 percent is a pass rate, not a routing rate.** ABCC's routing-rate claim is unverified and
   needs the database. W4 should not cite 88 percent as a routing baseline.
2. **Haiku was never an execution tier** in ABCC. The real ladder is C1-C6 local 16K, C7-C9
   remote-or-local 32K, C10 Sonnet. W4's escalation baseline is wrong in the brief.
3. **ABCC's complexity fields were collapsed** by the 2026-02-01 migration. Router-versus-AI
   comparison post-February needs a text parse of `complexity_reasoning`. BCF's `RoutingResult`
   shows the typed fix.
4. **BCF is not Python-only.** Project tests run for Python, Rust, Go and TS/JS. W6's scoping
   question is in better shape than the brief assumes.
5. **ABCC has a second, 2D isometric renderer** the brief does not mention. W5 starts there, not
   from the React Three Fiber work.
6. **ABCC was tuned on an RTX 3060 Ti 8GB.** Every V1 model choice, context size and pass rate is
   an 8GB result and none of it transfers to the 5060 Ti without re-measurement.
7. **Q56 supersedes the 40-task corpus** per David, and the frozen core must stay frozen.

---

## 6. Meta

Two observations about the research plan itself.

1. **Phase 1 is smaller than the brief expects.** The inheritance map has 48 REUSE rows and only
   5 REWRITE rows. Most of section 11 is integration and measurement rather than open research.
   The workstreams that are genuinely open are W5 (console and fun), W10 (fleet and the provider
   trait), the operator-control half of W3, and the recalibration half of W6. W9's prior-art scan
   may be the highest-value remaining pure-research item, precisely because "this already exists,
   use it" is now the likely finding for several workstreams.
2. **The sequencing in section 14 should be revisited.** It puts W1 and W2 first because
   "everything depends on what the hardware can actually do". Much of that is already measured. If
   the residency reframing in section 1 holds, W1 and W2 shrink to a confirmation run plus the
   concurrency and prefix-caching questions, which frees the schedule for W5 - the workstream the
   brief itself says deserves more than a week and which carries the project's identity.
