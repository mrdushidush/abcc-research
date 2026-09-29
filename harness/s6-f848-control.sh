#!/usr/bin/env bash
# The F848 control (TOOL-S6), approved by David 2026-09-29. Chained behind the Q56 control: it
# waits for harness/runs/s6q/DONE before touching the model.
#
# F848: main passes finish_the_cancelled_status by applying the fix Recon wrote; chat (Builders
# alone) turns the `other` bucket into `cancelled`, 3/3. Two things differ and were not separated:
# the Recon section of the brief, and chat's framing. This runs `abcc chat` (abcc-dc57bde-chat,
# T = 0) on a scratch corpus, harness/runs/f848/corpus (gitignored), with two copies of the card:
#   finish_the_cancelled_status        the card as it is (fixture now free of the stray
#                                      __pycache__, which changes what list_files shows, so the
#                                      S6 chat result is re-measured here as the baseline)
#   finish_the_cancelled_status_recon  the same card, its prompt followed by main's Recon report
#                                      verbatim (copy: research/s6/f848-recon-prompt.txt)
# Reading: _recon passes and the baseline fails -> the Recon section is the lever and chat's
# framing does not break it. _recon fails too -> the framing (or chat itself) matters.
# ~20 min. `touch harness/runs/f848/STOP` ends it between cells. Progress: runs/f848/driver.log.
cd /d/dev/ABCC_20_powerd_by_claudette/harness || exit 1
OUT=runs/f848
CORPUS=runs/f848/corpus
MODEL=qwen3.6-35b-a3b-mtp@iq3_s
CTX=40960
mkdir -p "$OUT"
log() { echo "$(date -Iseconds) $*" | tee -a "$OUT/driver.log"; }

log "waiting for runs/s6q/DONE"
for _ in $(seq 1 180); do
  [ -f runs/s6q/DONE ] && break
  sleep 60
done
if [ ! -f runs/s6q/DONE ]; then log "REFUSED: the Q56 control never finished (3 h)"; exit 1; fi

loaded="$(lms ps 2>/dev/null | grep -F "$MODEL")"
if [ -z "$loaded" ]; then
  log "$MODEL is not loaded; loading it at $CTX (no TTL)"
  lms load "$MODEL" -c "$CTX" --parallel 1 -y > /dev/null 2>&1
  loaded="$(lms ps 2>/dev/null | grep -F "$MODEL")"
fi
if ! printf '%s\n' "$loaded" | grep -qw "$CTX"; then
  log "REFUSED: $MODEL is not loaded at $CTX. lms ps says: ${loaded:-nothing}"
  exit 1
fi
log "$MODEL loaded at $CTX"

one() {  # name task
  if [ -f "$OUT/STOP" ]; then log "STOP file present, not starting $1"; touch "$OUT/DONE"; exit 0; fi
  log "start $1"
  target/release/w8-run.exe "$CORPUS" --subject abcc-dc57bde-chat --suite k --task "$2" \
    --variant control --model "$MODEL" --num-ctx "$CTX" --verify-timeout-s 1200 \
    > "$OUT/$1.log" 2>&1
  local rc=$?
  log "end $1 exit=$rc run=$(grep -o 'runs.w8-[0-9]*' "$OUT/$1.log" | tail -1)"
}
one recon-p1 finish_the_cancelled_status_recon
one base-p1  finish_the_cancelled_status
one recon-p2 finish_the_cancelled_status_recon
one recon-p3 finish_the_cancelled_status_recon
log "all cells done"
touch "$OUT/DONE"
