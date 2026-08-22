"""Two follow-ups verdict.py's first run left owed.

1. FAIR PROMPT-AND-PRAY. verdict.py's no-schema arm was not told to emit JSON, so
   it measured "what the model does with no schema", which is not what v1 and BCF
   do -- they ask for JSON in the prompt. Re-run the unconstrained arm WITH format
   instructions, which is the real donor mechanism, so the comparison against
   `response_format` is a fair one.

2. SCORE REPRODUCIBILITY. Four successful verdicts on identical input in the first
   run returned verdict=fail 4/4 and score 2, 0, 2, 0. Temperature is 0.0, so that
   spread is the model, not the sampler (MoE routing + speculative decoding are not
   bit-reproducible). n=4 across four different max_tokens is not a measurement of
   it; five identical calls are.
"""

import json
import statistics
import verdict as V

FORMAT_INSTRUCTION = """

Reply with a single JSON object and nothing else. No prose, no markdown fence.
Shape:
{"verdict": "pass" | "fail", "score": <integer 0-10>,
 "defects": [{"file": "<path>", "severity": "low"|"medium"|"high",
              "description": "<one sentence>"}]}
"""

print("-- prompt-and-pray, format asked for in the prompt (the donors' mechanism) --")
V.SYSTEM = V.SYSTEM + FORMAT_INSTRUCTION
pray = [V.judge(f"asked-for JSON r{i+1}", 4096, schema=False) for i in range(3)]

print("\n-- five identical schema-constrained calls, max_tokens=4096, temperature 0 --")
V.SYSTEM = V.SYSTEM.replace(FORMAT_INSTRUCTION, "")
reps = [V.judge(f"repeat r{i+1}", 4096) for i in range(5)]

print()
ok = [r for r in reps if r["json_ok"]]
scores = [r["score"] for r in ok]
verdicts = {r["verdict"] for r in ok}
print(f"schema arm: {len(ok)}/5 parsed   verdicts {verdicts}   scores {scores}")
if len(scores) > 1:
    print(f"            score spread {min(scores)}-{max(scores)}, "
          f"stdev {statistics.stdev(scores):.2f}")
print(f"            completion tokens {[r['completion_tokens'] for r in reps]}")
print(f"            wall {[r['wall_s'] for r in reps]}")
print(f"prompt-and-pray: {sum(1 for r in pray if r['json_ok'])}/3 parsed, "
      f"payload_chars {[r['payload_chars'] for r in pray]}")

with open("repeat-results.json", "w", encoding="utf-8") as f:
    json.dump({"prompt_and_pray": pray, "repeats": reps}, f, indent=1)
print("\nwrote repeat-results.json")
