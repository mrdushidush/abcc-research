"""What output budget does one Judge call need on the champion?

W11 item 1 put A4 Judge at ONE model call, no tools, seeing A3's measurements, and
item 2 owes the per-phase runtime profile a number for its output budget.

Two donor facts make this worth measuring rather than guessing:

  * BCF's `premium` preset caps every judging role at max_predict 1024 --
    security, critique and cto (`src/model_config.rs:174-179`). That number was
    chosen for qwen2.5-coder, a non-reasoning model.
  * W2 F82 measured that on THIS model a max_tokens of 300 returns
    `finish_reason: "length"` with `content: ""` -- HTTP 200, empty payload,
    because the reasoning trace is unconstrained and is spent FIRST. At 3,000 it
    answered correctly. So a budget that is too small does not truncate the
    verdict; it deletes it.

The gap between 1024 and 3000 is where BCF's number lands, and nobody has run it.

Arms: a realistic Judge prompt (brief + diff + measurement set), a strict
json_schema verdict, max_tokens swept over the donor's number and its neighbours,
with and without the `/no_think` prefix BCF puts on its own router prompt
(`src/router.rs:327`) -- which is a Qwen-family control token, so whether it works
here is a measurement, not a documentation question.

Records for each cell: finish_reason, reasoning tokens, payload bytes, whether the
JSON parses, and wall clock.
"""

import json
import time
import urllib.request

BASE = "http://localhost:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"

BRIEF = """\
TASK: `usage.rs` double-counts tokens when a turn is resumed from a saved session.
ACCEPTANCE CRITERION: `cargo test -p claudette-core usage::` passes.
LOCALIZED TO: crates/core/src/usage.rs (UsageTracker::record), crates/core/src/conversation.rs:287.
NOTE FROM RECON: `record` only ever `+=`, and the tracker is seeded from the session
on resume, so a resumed session starts with the previous session's totals already in it.
"""

DIFF = """\
--- a/crates/core/src/usage.rs
+++ b/crates/core/src/usage.rs
@@ -38,12 +38,22 @@ pub struct UsageTracker {
     input_tokens: u64,
     output_tokens: u64,
+    /// Totals carried in from a resumed session, subtracted out of every report.
+    seeded: Option<Usage>,
 }

 impl UsageTracker {
-    pub fn record(&mut self, usage: &Usage) {
+    pub fn record(&mut self, usage: &Usage) {
         self.input_tokens += usage.input_tokens;
         self.output_tokens += usage.output_tokens;
     }
+
+    pub fn seed(&mut self, prior: Usage) {
+        self.seeded = Some(prior);
+    }
+
+    pub fn turn_totals(&self) -> Usage {
+        let base = self.seeded.unwrap_or_default();
+        Usage {
+            input_tokens: self.input_tokens - base.input_tokens,
+            output_tokens: self.output_tokens - base.output_tokens,
+        }
+    }
 }
--- a/crates/core/src/conversation.rs
+++ b/crates/core/src/conversation.rs
@@ -284,7 +284,8 @@ impl Conversation {
     pub fn resume(path: &Path) -> Result<Self> {
         let saved = Session::load(path)?;
         let mut tracker = UsageTracker::default();
-        tracker.record(&saved.usage);
+        tracker.record(&saved.usage);
+        tracker.seed(saved.usage);
         Ok(Self { tracker, ..Default::default() })
     }
"""

MEASUREMENTS = """\
MEASUREMENT SET (phase A3, no model involved):
  build            Measured(ok)            cargo build --workspace, 41.2s
  typecheck        Measured(ok)            cargo clippy -D warnings, 0 warnings
  project suite    Measured(fail)          cargo test --workspace: 312 passed, 1 FAILED
                                           usage::resumed_session_reports_turn_only
                                           panicked at 'attempt to subtract with overflow'
  criterion        Measured(fail)          cargo test -p claudette-core usage:: -> exit 101
  diff scan        Measured(ok)            no secrets, no new deps, 2 files, +21 -3
"""

SYSTEM = """\
You are the Judge. You are one model call with no tools. You see the brief, the diff \
and the measurement set. You do not run anything and you do not edit anything.

Score the attempt out of 10 and list every defect you can support from what you were \
given. A measurement that says fail is a fact, not an opinion: it cannot be argued with, \
and a verdict of pass while a required measurement failed is itself a defect.
"""

USER = f"{BRIEF}\n{DIFF}\n{MEASUREMENTS}\nReturn your verdict."

SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "verdict",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["pass", "fail"]},
                "score": {"type": "integer", "minimum": 0, "maximum": 10},
                "defects": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "file": {"type": "string"},
                            "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                            "description": {"type": "string"},
                        },
                        "required": ["file", "severity", "description"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["verdict", "score", "defects"],
            "additionalProperties": False,
        },
    },
}


def judge(label, max_tokens, no_think=False, schema=True):
    system = ("/no_think\n" + SYSTEM) if no_think else SYSTEM
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": USER}],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    if schema:
        body["response_format"] = SCHEMA
    req = urllib.request.Request(BASE + "/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    content, reasoning, finish, usage = "", "", None, None
    with urllib.request.urlopen(req, timeout=1800) as resp:
        for raw in resp:
            line = raw.decode("utf-8", errors="replace").strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                obj = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if obj.get("usage"):
                usage = obj["usage"]
            for ch in obj.get("choices") or []:
                d = ch.get("delta") or {}
                content += d.get("content") or ""
                reasoning += d.get("reasoning_content") or ""
                if ch.get("finish_reason"):
                    finish = ch["finish_reason"]
    wall = time.perf_counter() - t0
    ok = False
    parsed = None
    try:
        parsed = json.loads(content)
        ok = True
    except Exception:
        pass
    ct = (usage or {}).get("completion_tokens")
    print(f"{label:<30} finish={str(finish):<6} completion_tok={str(ct):>5} "
          f"reasoning_chars={len(reasoning):>5} payload_chars={len(content):>5} "
          f"json={'OK ' if ok else 'NO '} {wall:6.1f}s", flush=True)
    if ok:
        print(f"{'':<30}   -> verdict={parsed.get('verdict')} score={parsed.get('score')} "
              f"defects={len(parsed.get('defects') or [])}", flush=True)
    return {"label": label, "finish": finish, "completion_tokens": ct,
            "reasoning_chars": len(reasoning), "payload_chars": len(content),
            "json_ok": ok, "wall_s": round(wall, 2),
            "verdict": (parsed or {}).get("verdict"), "score": (parsed or {}).get("score")}


def main():
    rows = []
    print("-- schema-constrained verdict, thinking left on (the default) --")
    for mt in (256, 512, 1024, 2048, 4096, 8192):
        rows.append(judge(f"schema  max_tokens={mt}", mt))

    print("\n-- same, with BCF's /no_think prefix --")
    for mt in (256, 512, 1024, 2048, 4096):
        rows.append(judge(f"/no_think  max_tokens={mt}", mt, no_think=True))

    print("\n-- no schema, prompt-and-pray (v1 and BCF's actual mechanism) --")
    for mt in (1024, 4096):
        rows.append(judge(f"no schema  max_tokens={mt}", mt, schema=False))

    with open("verdict-results.json", "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1)
    print("\nwrote verdict-results.json")


if __name__ == "__main__":
    main()
