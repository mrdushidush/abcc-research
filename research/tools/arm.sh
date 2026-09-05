#!/bin/bash
# arm.sh <model-path> <ctx> <label> [bench_lines]
SP="/c/Users/david/AppData/Local/Temp/claude/D--dev-ABCC-20-powerd-by-claudette/17e0c9f7-5f2f-4d6c-aa81-5139ae20b765/scratchpad"
MODEL="$1"; CTX="$2"; LABEL="$3"; LINES="${4:-250}"
lms unload --all >/dev/null 2>&1; sleep 3
T0=$(date +%s)
if ! lms load "$MODEL" -c "$CTX" --parallel 1 --identifier probe >/dev/null 2>&1; then
  echo "LOAD FAILED: $LABEL @ $CTX"; exit 1
fi
T1=$(date +%s)
SMI=$(nvidia-smi --query-gpu=memory.used --format=csv,noheader | tr -d ' MiB')
MEM=$(powershell -NoProfile -ExecutionPolicy Bypass -File "$(cygpath -w "$SP/gpumem.ps1")" 2>&1)
DED=$(echo "$MEM" | grep Dedicated | tr -dc '0-9,' | tr -d ',')
SHR=$(echo "$MEM" | grep Shared    | tr -dc '0-9,' | tr -d ',')
echo "### $LABEL  ctx=$CTX  load=$((T1-T0))s  smi_used=${SMI}MiB  dedicated=${DED}MiB  shared=${SHR}MiB"
timeout 400 python "$SP/bench.py" probe "$LABEL @ctx$CTX" "$LINES" 150 2>&1 | python -c "
import sys,json
raw=sys.stdin.read()
try:
    d=json.loads(raw[raw.index('{'):raw.rindex('}')+1])
except Exception:
    print('    BENCH: no parseable result (timeout/hang) ->', raw.strip()[:120]); raise SystemExit
if not d.get('completion_tokens'):
    print('    BENCH: ZERO TOKENS in %.1fs -- HUNG, not a rate' % d.get('total_s',0)); raise SystemExit
print('    prompt=%(prompt_tokens)s ttft=%(ttft_s)ss prefill=%(prefill_tok_s)s tok/s decode=%(decode_tok_s)s tok/s' % d)
"
