"""Does LM Studio's OpenAI-compat surface honour constrained decoding?

W2 asks whether grammar/schema-constrained decoding is reachable from the Rust side.
llama-server supports GBNF and JSON-schema natively; the open question is whether
LM Studio's proxy on :1234 forwards it. Three probes, each a separate claim:

  1. response_format: {"type": "json_schema", ...}   — the OpenAI dialect
  2. response_format: {"type": "json_object"}        — the older/looser dialect
  3. a deliberately hostile prompt under (1)         — does the schema actually BIND,
     or is it merely accepted and ignored?

Probe 3 is the one that matters. An endpoint that accepts the field and ignores it
looks identical to a working one until a model decides to editorialise.
"""

import json
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:1234"
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen3.6-35b-a3b-mtp@iq3_s"

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "score": {"type": "integer"},
    },
    "required": ["verdict", "score"],
    "additionalProperties": False,
}


def call(label, extra, prompt, max_tokens=300):
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    body.update(extra)
    req = urllib.request.Request(
        BASE + "/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            obj = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:400]
        print(f"[{label}] HTTP {e.code}: {detail}")
        return None
    msg = (obj.get("choices") or [{}])[0].get("message") or {}
    content = msg.get("content")
    print(f"[{label}] finish={obj['choices'][0].get('finish_reason')} content={content!r:.400}")
    if content:
        try:
            json.loads(content)
            print(f"[{label}] -> parses as JSON: YES")
        except json.JSONDecodeError as e:
            print(f"[{label}] -> parses as JSON: NO ({e})")
    return content


print("=" * 70)
call(
    "1-json_schema",
    {
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "verdict", "strict": True, "schema": SCHEMA},
        }
    },
    "Grade this patch. Reply with the verdict and a score out of 10.",
)
print("=" * 70)
call("2-json_object", {"response_format": {"type": "json_object"}},
     "Grade this patch. Reply as JSON with a verdict and a score.")
print("=" * 70)
# The binding test: everything in this prompt pushes AWAY from the schema.
call(
    "3-hostile",
    {
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "verdict", "strict": True, "schema": SCHEMA},
        }
    },
    "Write a two-paragraph prose essay about the sea. Use no JSON, no braces, "
    "no quotes. Begin with the word 'The'. Do not mention verdicts or scores.",
)
print("=" * 70)
