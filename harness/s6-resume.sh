#!/usr/bin/env bash
# Ship plan, the rest of the S6 bench, run by David from his OWN terminal (ruled 2026-09-28), so
# Claude Code's low-memory reaper cannot kill it the way it killed s6-night.sh at ~23:37 on
# 2026-09-27. Same binary and subjects as s6-night.sh (abcc dc57bde).
#
# What s6-night.sh already has (harness/runs/s6/driver.log): main-k-p1, chat-k-p1, evict-k-p1,
# chat-r-p1. main-r-p1 is JUNK (13 cells could not start a process during the memory crunch,
# 0xC0000142) and is run again here as main-r-p1r.
# David's rulings of 2026-09-28: no evict arm (eviction fired once in 17 finished task logs and the
# tier never, so the arm tells nothing on K/R); main R first, because the (a') merge rule needs
# main R x3; then chat, then main K, Q56 last. ~8 h. Dogfood by day, bench by night.
#
# Start it from PowerShell in a window you leave open:
#   & "C:\Program Files\Git\bin\bash.exe" D:/dev/ABCC_20_powerd_by_claudette/harness/s6-resume.sh
# `touch harness/runs/s6/STOP` ends it between cells. Progress: harness/runs/s6/driver.log.
cd /d/dev/ABCC_20_powerd_by_claudette/harness || exit 1
OUT=runs/s6
MODEL=qwen3.6-35b-a3b-mtp@iq3_s
CTX=40960
mkdir -p "$OUT"
log() { echo "$(date -Iseconds) $*" | tee -a "$OUT/driver.log"; }

# Last night's markers would stop this before its first cell. Kept, renamed, not deleted.
for f in STOP DONE; do
  if [ -f "$OUT/$f" ]; then
    mv "$OUT/$f" "$OUT/$f.s6-night" && log "resume: moved last night's $f aside to $f.s6-night"
  fi
done

# The model: loaded at 40960, or loaded here; loaded at another size is refused, not replaced.
loaded="$(lms ps 2>/dev/null | grep -F "$MODEL")"
if [ -z "$loaded" ]; then
  log "resume: $MODEL is not loaded; loading it at $CTX (no TTL)"
  lms load "$MODEL" -c "$CTX" --parallel 1 -y > /dev/null 2>&1
  loaded="$(lms ps 2>/dev/null | grep -F "$MODEL")"
fi
if ! printf '%s\n' "$loaded" | grep -qw "$CTX"; then
  log "resume: REFUSED: $MODEL is not loaded at $CTX. lms ps says: ${loaded:-nothing}"
  exit 1
fi
log "resume: $MODEL loaded at $CTX"

one() {  # name subject suite
  if [ -f "$OUT/STOP" ]; then log "STOP file present, not starting $1"; touch "$OUT/DONE"; exit 0; fi
  log "start $1"
  target/release/w8-run.exe ../corpus --subject "$2" --suite "$3" \
    --model "$MODEL" --num-ctx "$CTX" --verify-timeout-s 1200 \
    > "$OUT/$1.log" 2>&1
  local rc=$?
  log "end $1 exit=$rc run=$(grep -o 'runs.w8-[0-9]*' "$OUT/$1.log" | tail -1)"
}
M=abcc-dc57bde; C=abcc-dc57bde-chat
one main-r-p1r $M r
one main-r-p2  $M r
one main-r-p3  $M r
one chat-k-p2  $C k
one chat-r-p2  $C r
one chat-k-p3  $C k
one main-k-p2  $M k
one main-k-p3  $M k
one main-q56   $M q56
log "resume: all cells done"
touch "$OUT/DONE"
