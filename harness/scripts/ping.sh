#!/usr/bin/env bash
# One real completion out of the serving stack, and the only health check that
# would have caught F539.
#
# The wedge of 2026-08-30 left `/v1/models` answering normally -- the id, the
# state, the whole listing -- while every completion returned nothing for 60 s,
# and it took both slots down until `lms load`. So this asks for a token.
#
# The durable version of this is `abcc breaker` (and `abcc check`, which now
# takes a pulse of its own). This exists for the case where the binary will not
# build, or where a shell is all there is. The previous scratchpad copy was lost
# with the scratchpad; this one is committed.
#
#   ./ping.sh [model] [base-url]
#
# Defaults come from $ABCC_MODEL and $ABCC_MODEL_BASE_URL, and the bearer token
# from $ABCC_MODEL_API_KEY when it is set.
#
# 🚨 F550 -- READ THE TOKEN COUNT, NOT THE ANSWER TEXT. The champion is a
# reasoning model: at max_tokens of 1, 8 and 64 it returns content:"" every time
# and puts every token in reasoning_content, with usage.completion_tokens equal
# to the cap. A check that reads `.choices[0].message.content` calls a healthy,
# idle, correctly loaded server dead. Measured on this box, three caps, one
# session.

set -uo pipefail

MODEL="${1:-${ABCC_MODEL:-}}"
BASE="${2:-${ABCC_MODEL_BASE_URL:-http://127.0.0.1:1234}}"

if [ -z "$MODEL" ]; then
  echo "ping: no model named. Pass one, or set ABCC_MODEL." >&2
  echo "      There is no default: a check whose model was guessed is a check" >&2
  echo "      about something nobody chose." >&2
  exit 2
fi

# Accept any of the four spellings of the base url.
ROOT="${BASE%/}"
ROOT="${ROOT%/v1/chat/completions}"
ROOT="${ROOT%/api/v0/models}"
ROOT="${ROOT%/v1/models}"
ROOT="${ROOT%/v1}"
URL="$ROOT/v1/chat/completions"

AUTH=()
if [ -n "${ABCC_MODEL_API_KEY:-}" ]; then
  AUTH=(-H "Authorization: Bearer ${ABCC_MODEL_API_KEY}")
fi

BODY=$(printf '{"model":"%s","messages":[{"role":"user","content":"Reply with one word: ready."}],"max_tokens":1,"stream":false,"temperature":0}' "$MODEL")

START=$(date +%s%3N)
OUT=$(curl -sS --max-time 20 -X POST "$URL" \
  -H "Content-Type: application/json" "${AUTH[@]}" \
  -d "$BODY" 2>&1)
RC=$?
END=$(date +%s%3N)
MS=$((END - START))

if [ $RC -ne 0 ]; then
  echo "pulse  UNREACHABLE after ${MS} ms -- $OUT"
  exit 1
fi

# The instrument. Everything else in the body is decoration.
TOKENS=$(printf '%s' "$OUT" | python -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(0); sys.exit()
u = d.get("usage") or {}
n = u.get("completion_tokens") or 0
m = ((d.get("choices") or [{}])[0].get("message")) or {}
text = (m.get("content") or "").strip() or (m.get("reasoning_content") or "").strip()
# Text with no counter still counts: the absence of a counter is not the
# absence of generation.
print(n if n else (1 if text else 0))
' 2>/dev/null || echo 0)

CHANNEL=$(printf '%s' "$OUT" | python -c '
import json, sys
try:
    m = ((json.load(sys.stdin).get("choices") or [{}])[0].get("message")) or {}
except Exception:
    m = {}
if (m.get("content") or "").strip():
    print("answer: " + (m["content"].strip()[:40]))
elif (m.get("reasoning_content") or "").strip():
    print("reasoning only: " + (m["reasoning_content"].strip()[:40]))
else:
    print("no text, the count only")
' 2>/dev/null || echo "unparsed")

if [ "${TOKENS:-0}" -gt 0 ]; then
  echo "pulse  ${TOKENS} token(s) in ${MS} ms -- ${CHANNEL}"
  exit 0
fi

echo "pulse  SILENT after ${MS} ms -- HTTP 200 and nothing decoded"
echo "       A model listing answering is NOT this check (F539)."
printf '%s\n' "$OUT" | head -c 400
echo
exit 1
