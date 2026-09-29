#!/usr/bin/env bash
# The Q56 control (TOOL-S6, F847), approved by David 2026-09-29 ("run it now").
#
# S6 scored Q56 48 on abcc dc57bde at temperature 0; A3 scored 50 on e5eef90 at the server's
# temperature. The ten Q56 tasks that moved or still fail are run here on dc57bde both ways:
# three passes at the server's temperature (abcc-dc57bde-tserver = `--temperature server`) and
# one more at T = 0 (abcc-dc57bde, the S6 subject). Reading:
#   Q20 Q26 Q39 Q51 pass at the server's temperature -> the Q56 drop is the price of T = 0;
#   they still fail -> the code since e5eef90 moved them.
# ~45 min. Launched outside Claude Code's process tree (its low-memory reaper killed night 1).
# By hand, from PowerShell:
#   & "C:\Program Files\Git\bin\bash.exe" D:/dev/ABCC_20_powerd_by_claudette/harness/s6-q56-control.sh
# `touch harness/runs/s6q/STOP` ends it between cells. Progress: harness/runs/s6q/driver.log.
cd /d/dev/ABCC_20_powerd_by_claudette/harness || exit 1
OUT=runs/s6q
MODEL=qwen3.6-35b-a3b-mtp@iq3_s
CTX=40960
mkdir -p "$OUT"
log() { echo "$(date -Iseconds) $*" | tee -a "$OUT/driver.log"; }

# The model: loaded at 40960, or loaded here; loaded at another size is refused, not replaced.
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

TASKS=()
for t in Q03 Q04 Q05 Q20 Q25 Q26 Q29 Q39 Q46 Q51; do TASKS+=(--task "$t"); done

one() {  # name subject
  if [ -f "$OUT/STOP" ]; then log "STOP file present, not starting $1"; touch "$OUT/DONE"; exit 0; fi
  log "start $1"
  target/release/w8-run.exe ../corpus --subject "$2" --suite q56 "${TASKS[@]}" --variant control \
    --model "$MODEL" --num-ctx "$CTX" --verify-timeout-s 1200 \
    > "$OUT/$1.log" 2>&1
  local rc=$?
  log "end $1 exit=$rc run=$(grep -o 'runs.w8-[0-9]*' "$OUT/$1.log" | tail -1)"
}
one tserver-p1 abcc-dc57bde-tserver
one tserver-p2 abcc-dc57bde-tserver
one tserver-p3 abcc-dc57bde-tserver
one t0-p1      abcc-dc57bde
log "all cells done"
touch "$OUT/DONE"
