#!/usr/bin/env bash
# Ship plan, overnight bench (S6 night). One binary, abcc 9e0afcd, three arms:
#   main  = abcc-9e0afcd        (batch, temperature 0, (a') merged, eviction off)
#   evict = abcc-9e0afcd-evict  (the same with --evict)
#   chat  = abcc-9e0afcd-chat   (abcc chat --task, one conversation, /done after the first answer)
# Ordered by importance: pass 1 of every arm first, K before R, Q56 last. ~11 h if it all runs;
# whatever finishes by morning is usable. `touch runs/s6/STOP` ends it between cells.
cd /d/dev/ABCC_20_powerd_by_claudette/harness || exit 1
OUT=runs/s6
mkdir -p "$OUT"
log() { echo "$(date -Iseconds) $*" >> "$OUT/driver.log"; }
one() {  # name subject suite
  if [ -f "$OUT/STOP" ]; then log "STOP file present, not starting $1"; touch "$OUT/DONE"; exit 0; fi
  log "start $1"
  target/release/w8-run.exe ../corpus --subject "$2" --suite "$3" \
    --model qwen3.6-35b-a3b-mtp@iq3_s --num-ctx 40960 --verify-timeout-s 1200 \
    > "$OUT/$1.log" 2>&1
  local rc=$?
  log "end $1 exit=$rc run=$(grep -o 'runs.w8-[0-9]*' "$OUT/$1.log" | tail -1)"
}
M=abcc-9e0afcd; E=abcc-9e0afcd-evict; C=abcc-9e0afcd-chat
one main-k-p1  $M k
one chat-k-p1  $C k
one evict-k-p1 $E k
one main-r-p1  $M r
one chat-r-p1  $C r
one evict-r-p1 $E r
one main-k-p2  $M k
one chat-k-p2  $C k
one evict-k-p2 $E k
one main-r-p2  $M r
one chat-r-p2  $C r
one main-k-p3  $M k
one chat-k-p3  $C k
one evict-k-p3 $E k
one main-r-p3  $M r
one main-q56   $M q56
touch "$OUT/DONE"
