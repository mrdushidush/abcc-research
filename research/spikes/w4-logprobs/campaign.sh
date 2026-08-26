#!/usr/bin/env bash
# W4 item 4: generate the population.
#
# The 378 control cells already on disk have an answer key and no logprobs, so
# item 4 is the second GPU item.  Repeats of Q56 control, each behind its own
# recorder instance so that (task, variant) is a unique key inside one repeat
# file and no timing join is needed.
#
# Held exactly as the three recorded Q56 control runs (`runmeta.json`):
#   subject claudette-af3f804 · model qwen3.6-35b-a3b-mtp@iq3_s
#   num_ctx 61440 · num_predict 8192 · max_iterations 40 · verify-timeout 300
#   delivery verbatim · variant control
# Three things are DELIBERATELY different and the analysis must carry them:
#   endpoint  -> the recorder, i.e. bare llama-server instead of LM Studio :1234
#   streaming -> off (the bare server 400s on logprobs + tools + stream, F388)
#   MTP       -> off per request, without which the array is fabricated (F387)
# The run's own pass rate against the recorded 49/50/48 of 56 is the check on
# whether those three moved the subject.
#
#   REPS=3 bash campaign.sh                       # the population
#   ARM=keep-mtp TASKS="Q03 Q07" TAG=probe bash campaign.sh   # attribution probe
#
# Each repeat gets its OWN PORT: the first campaign killed the recorder and
# started the next one on the same port, which was still held, so the banner
# printed and the bind failed and four of five repeats died on "connection
# refused". The port is never reused and readiness is polled, not assumed.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
HARNESS="$HERE/../../../harness"
REPS="${REPS:-3}"
BASE_PORT="${BASE_PORT:-1240}"
ARM="${ARM:-spec-off}"
TASKS="${TASKS:-}"
TAG="${TAG:-lp}"

keep=""
[ "$ARM" = "keep-mtp" ] && keep="--keep-mtp"

task_args=""
for t in $TASKS; do task_args="$task_args --task $t"; done

for r in $(seq 1 "$REPS"); do
  port=$((BASE_PORT + r))
  out="$HERE/$TAG-rep$r.jsonl"
  rm -f "$out"
  echo "===== repeat $r starting $(date -Is) on :$port arm=$ARM ====="
  python "$HERE/recorder.py" --port "$port" --out "$out" $keep &
  rec=$!
  ready=0
  for _ in $(seq 1 30); do
    if curl -s -o /dev/null "http://localhost:$port/v1/models"; then ready=1; break; fi
    sleep 1
  done
  if [ "$ready" != 1 ]; then
    echo "!! recorder never answered on :$port — aborting repeat $r"
    kill "$rec" 2>/dev/null; wait "$rec" 2>/dev/null
    continue
  fi
  "$HARNESS/target/release/w8-run.exe" "$HARNESS/../corpus" \
    --subject claudette-af3f804 --suite q56 --variant control \
    --model qwen3.6-35b-a3b-mtp@iq3_s \
    --num-ctx 61440 --num-predict 8192 --max-iterations 40 \
    --verify-timeout-s 300 --delivery verbatim \
    $task_args \
    --endpoint "http://localhost:$port" \
    --bin D:/dev/claudette/target/release/claudette.exe \
    --out "$HARNESS/../runs/w4-$TAG-r$r"
  kill "$rec" 2>/dev/null
  wait "$rec" 2>/dev/null
  echo "===== repeat $r done $(date -Is), $(wc -l < "$out") calls recorded ====="
done
