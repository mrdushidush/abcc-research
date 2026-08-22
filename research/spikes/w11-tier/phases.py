"""What a PHASE TRANSITION costs, and whether a model swap survives it.

W11 item 2 asks for a phase-to-tier mapping backed by W1/W2 measurements. Two of
those measurements do not exist yet:

  1. W2 F81 measured that ONE token changed at the FRONT of a prompt annihilates
     the prefix cache (11.399 s vs 11.549 s cold, 0.99x). It measured that with a
     single-token edit. The pipeline question is different: each phase wants its
     own system prompt and its own tool policy, which is a WHOLE DIFFERENT HEAD,
     and the phases alternate. Does the server keep more than one prefix? If it
     does, per-phase heads are free and F81's warning is narrower than it looks.
     If it does not, every phase transition is a full cold prefill.

  2. F79 measured a model swap at 23.77 s round trip. That is the load cost. It
     does not say what the swap does to the prefix cache -- i.e. whether the true
     price of a tier change is 23.77 s or 23.77 s + a cold prefill.

Arms, champion at -c 65536 --parallel 1, ~18k-token shared body (F81 used 18,470
so the numbers are directly comparable):

  HEAD-VARYING -- each phase carries its own system prompt + tool array
    1  A1  head A (Recon tools),   cold
    2  A2  head A again            -> warm baseline for this prefix
    3  B1  head B (Builders tools) -> the transition cost
    4  A3  head A again            -> does A's prefix survive B? (multi-prompt cache)

  HEAD-FROZEN -- one system prompt with the union tool set, phase instruction at
  the TAIL (F81's benign case D)
    5  S1  shared head, tail = Localize   cold (new prefix)
    6  S2  shared head, tail = Change     -> transition cost, frozen head
    7  S3  shared head, tail = Judge      -> transition cost, frozen head
    8  S4  shared head, tail = Localize   -> back to the first phase

  SWAP  (run with `python phases.py --replay` after an unload/load cycle)
    9  S1 again -> is the prefix still cached after the weights are reloaded?

Usage:
  python phases.py                 # steps 1-8
  python phases.py --replay        # step 9 only, same prompts, after a reload
"""

import json
import sys
import time
import urllib.request
import pathlib

BASE = "http://localhost:1234"
MODEL = "qwen3.6-35b-a3b-mtp@iq3_s"
TARGET = 18000  # tokens of shared body, to sit next to F81's 18,470

REPO = pathlib.Path(r"D:/dev/ABCC_20_powerd_by_claudette")
corpus = "\n\n".join(
    p.read_text(encoding="utf-8", errors="replace")
    for p in sorted(REPO.glob("prestudy/*.md")) + sorted(REPO.glob("research/*.md"))
)
while len(corpus) < TARGET * 3.3:
    corpus += corpus
BODY = corpus[: int(TARGET * 3.3)]

# ── the two per-phase heads. Realistic: a role line plus a tool array, which is
# what a chat template renders ahead of the messages. ~250 tokens each.

TOOLS_RECON = [
    {"name": "read_file", "description": "Read a file from the workspace.",
     "parameters": {"path": "string", "start_line": "integer", "end_line": "integer"}},
    {"name": "grep", "description": "Search the workspace with a regular expression.",
     "parameters": {"pattern": "string", "glob": "string", "context_lines": "integer"}},
    {"name": "list_dir", "description": "List the entries of a directory.",
     "parameters": {"path": "string", "depth": "integer"}},
]
TOOLS_BUILDERS = [
    {"name": "read_file", "description": "Read a file from the workspace.",
     "parameters": {"path": "string", "start_line": "integer", "end_line": "integer"}},
    {"name": "write_file", "description": "Write the whole contents of a file.",
     "parameters": {"path": "string", "content": "string"}},
    {"name": "apply_patch", "description": "Apply a unified diff to the workspace.",
     "parameters": {"diff": "string"}},
    {"name": "run_command", "description": "Run a shell command in the workspace.",
     "parameters": {"command": "string", "timeout_s": "integer"}},
]
TOOLS_UNION = TOOLS_RECON + TOOLS_BUILDERS[1:]


def head(role, tools):
    return (
        f"You are {role}. You are one unit of an ABCC 2.0 attempt.\n"
        f"Available tools:\n{json.dumps(tools, indent=1)}\n"
        "Use only the tools listed. Report findings against the workspace below.\n\n"
    )


HEAD_A = head("Recon", TOOLS_RECON)
HEAD_B = head("Builders", TOOLS_BUILDERS)
HEAD_S = head("a unit of the attempt pipeline", TOOLS_UNION)

TAIL_LOCALIZE = ("PHASE: Localize. Produce a grounded brief naming the files and the "
                 "single most load-bearing measurement above.")
TAIL_CHANGE = ("PHASE: Change. Name the one edit you would make first and the file it "
               "belongs in. Do not write the diff yet.")
TAIL_JUDGE = ("PHASE: Judge. You see the brief and the measurements. Name the one claim "
              "above you would refuse to sign off on.")


def ttft(label, system, user, max_tokens=40):
    body = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    first = None
    usage = None
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
                if (d.get("content") or d.get("reasoning_content")) and first is None:
                    first = time.perf_counter() - t0
    pt = (usage or {}).get("prompt_tokens")
    rate = round(pt / first, 1) if pt and first else None
    print(f"{label:<34} ttft {first:7.3f}s   prompt_tokens {pt:>6}   apparent prefill {rate} tok/s",
          flush=True)
    return first, pt


REPLAY = "--replay" in sys.argv

if REPLAY:
    print(f"REPLAY after reload -- body ~{TARGET} tokens, model {MODEL}\n")
    s1r, _ = ttft("9  S1 shared head (after reload)", HEAD_S + BODY, TAIL_LOCALIZE)
    print("\ncompare against step 5 (cold) and steps 6-8 (warm) of the main run.")
    sys.exit(0)

print(f"body ~{TARGET} tokens, model {MODEL}\n")
print("-- head-varying: each phase brings its own system prompt and tools --")
a1, pt_a = ttft("1  A1 head Recon      cold", HEAD_A + BODY, TAIL_LOCALIZE)
a2, _ = ttft("2  A2 head Recon      repeat", HEAD_A + BODY, TAIL_JUDGE)
b1, pt_b = ttft("3  B1 head Builders   transition", HEAD_B + BODY, TAIL_CHANGE)
a3, _ = ttft("4  A3 head Recon      back again", HEAD_A + BODY, TAIL_LOCALIZE)

print("\n-- head-frozen: one system prompt, phase at the tail --")
s1, pt_s = ttft("5  S1 frozen head    Localize (cold)", HEAD_S + BODY, TAIL_LOCALIZE)
s2, _ = ttft("6  S2 frozen head    -> Change", HEAD_S + BODY, TAIL_CHANGE)
s3, _ = ttft("7  S3 frozen head    -> Judge", HEAD_S + BODY, TAIL_JUDGE)
s4, _ = ttft("8  S4 frozen head    -> Localize", HEAD_S + BODY, TAIL_LOCALIZE)

print()
print(f"head-varying: repeat of the same head   {a2:6.3f}s   ({a2/a1:5.2f}x of cold)")
print(f"head-varying: PHASE TRANSITION          {b1:6.3f}s   ({b1/a1:5.2f}x of cold)")
print(f"head-varying: return to a used head     {a3:6.3f}s   ({a3/a1:5.2f}x of cold)")
print(f"head-frozen:  cold                      {s1:6.3f}s")
print(f"head-frozen:  PHASE TRANSITIONS         {s2:6.3f}s {s3:6.3f}s {s4:6.3f}s")
print()
print(f"cost of a per-phase head, per transition: {b1 - s2:+.3f}s "
      f"({b1/s2:.2f}x) at ~{pt_s} prompt tokens")
