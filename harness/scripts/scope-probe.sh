#!/usr/bin/env bash
# F536's better lead, run as a measurement instead of a population of one.
#
# The 15-call probe that produced `RungView::Named` found something it was not
# looking for: the best answer of all 15 came from `Full`, and what made it best
# was not what it had been shown. It checked the change against THE SCOPE THE
# TICKET STATES -- "the task explicitly requires treating cancelled jobs
# correctly everywhere ... this diff only modifies one file and I do not have
# visibility into the other five consumers ... I cannot verify full spec
# compliance." That is one sentence in the brief, and it is now written down as
# `judge::SCOPE_SENTENCE` behind `ABCC_JUDGE_SCOPE=on`.
#
#   ./scope-probe.sh            both arms, control first
#   ./scope-probe.sh off        the control arm alone
#   ./scope-probe.sh on         the treatment arm alone
#
#   SUITE=od ./scope-probe.sh both            one tier only, 72 trees an arm
#   SUITE=od SAMPLE=b ./scope-probe.sh off    that tier's noise floor arm
#
# 🚨 SUITE IS HOW THE NOISE FLOOR STAYS HONEST. "27 of 121 trees change when
# nothing changes" is q56+k's number on q56+k's trees. A probe over a new tier
# owes a floor MEASURED ON THAT TIER, which means the control has to be asked
# twice over the same selection — `SUITE=od` on all three arms, or on none.
#
# 🚨 THE CONTROL RUNS FIRST AND IT IS NOT THE STORED 121-TREE RUN. Nothing here
# samples at temperature zero -- the engine sends no temperature, no top_p and
# no seed -- so `full+off` asked FRESH is the only thing `full+on` can be read
# against. Comparing against `reviews/` would confound the switch with the day.
#
# 🚨 IT IS MEASURED ON ALL THREE POPULATIONS, NOT THE 3 SHAMS. The original
# sketch was 3 shams x 2 samples, ~13 min, and it could not have seen the cost
# that matters. An instruction to look for what a change does NOT reach is an
# instruction that can manufacture incompleteness on a tree that is fine, and
# ADR-0008's falsifier is a reviewer whose findings cost minutes for nothing.
# The 59 `correct` trees are the arm that can refuse this change.
#
# 🚨 EACH ARM IS RESTARTABLE AND SKIPS WHAT IT ALREADY ANSWERED. A dossier whose
# review file exists is skipped, so an interrupted night resumes where it
# stopped -- re-run the same command. To force a re-ask, delete that one file.
#
# ⚠ THE MODEL MUST BE LOADED AT --parallel 1 AND ANSWERING. The rig runs
# sequentially against one slot because that is what it was measured on. F539:
# `/v1/models` answers normally while every completion returns nothing, so the
# preflight below asks for a real token and reads the TOKEN COUNT, not the
# answer text (F550 -- this champion puts everything in reasoning_content).
#
# 🚨 F566 -- `lms ps` SAYING "No models are currently loaded" IS NOT A GUARD.
# LM Studio JIT-loads on the first completion request: measured 2026-09-04, a
# one-token ping against a reportedly empty server returned in 9,106 ms and
# `lms ps` then showed the champion resident. So "I unloaded it" does not stop a
# run, and a preflight that PASSES may be reporting a LOAD rather than a warm
# server -- a warm pulse is ~1 s and this was 9.1.
#
# 🚨 F567 -- A JIT LOAD CARRIES A 20-MINUTE TTL THAT AN EXPLICIT LOAD DOES NOT,
# AND `lms load` ON AN ALREADY-RESIDENT MODEL DOES NOT REPLACE IT -- IT ADDS A
# SECOND INSTANCE under a `:2` identifier. Measured: two 13.61 GB instances
# resident at once on a 16 GB card, 15,631 MiB used, so the second was spilling
# to RAM [[lm-studio-vram-spill]]. The rig asks for the BARE identifier, so it
# would address the TTL'd copy and could lose it at any 20-minute idle gap --
# splitting the two arms across two different loads. That is why this script
# unloads everything first and asserts exactly one instance with no TTL.
#
# Budget: 121 trees x 2 arms = 242 calls. The 121-tree run's median was 60.5 s
# under `Full`, worst 191.9 s, so ~2 h an arm and ~4 h the pair. That is an
# estimate from another day's run and not a promise.
#
# ⚠ The corpus is 193 trees now — q56 112 (no shams), k 9, od 72 — so an arm is
# ~3.2 h at that median and the three-arm design is most of a day. `SUITE=od` is
# 72 trees: ~72 min an arm, ~3.6 h for control + treatment + control again.

set -u

ARMS="${1:-both}"

ABCC_REPO="${ABCC_REPO:-D:/dev/abcc}"
RESEARCH="${RESEARCH:-D:/dev/ABCC_20_powerd_by_claudette}"

export ABCC_CORPUS_OUT="${ABCC_CORPUS_OUT:-$RESEARCH/research/corpus-run}"
export ABCC_MODEL="${ABCC_MODEL:-qwen3.6-35b-a3b-mtp@iq3_s}"
export ABCC_URL="${ABCC_URL:-http://localhost:1234}"

LOGS="$RESEARCH/research/corpus-run/logs"
mkdir -p "$LOGS" || exit 1

if [ ! -d "$ABCC_CORPUS_OUT/dossiers" ]; then
  echo "no dossiers at $ABCC_CORPUS_OUT/dossiers -- run \`--test corpus\` first" >&2
  exit 1
fi

# --- preflight ----------------------------------------------------------------
#
# 🚨 A FAILED COMMAND EARLIER IN A CHAIN MAKES EVERYTHING AFTER IT PROVE
# NOTHING, so every step here exits rather than warning. An arm that runs
# against a wedged server writes 121 `unmeasured` rows that look like data.

if [ "${SKIP_LOAD:-}" != "1" ]; then
  # F567: unload first. `lms load` on a resident model ADDS a copy, and two
  # copies of a 13.61 GB model on a 16 GB card means one of them is in RAM.
  echo "=== clearing any resident instance (F567)"
  lms unload --all >/dev/null 2>&1

  echo "=== loading $ABCC_MODEL explicitly -- no --ttl, so no auto-unload (F567)"
  if ! lms load "$ABCC_MODEL" -c 65536 --parallel 1 -y; then
    echo "LOAD FAILED -- not starting." >&2
    exit 1
  fi
fi

# 🚨 Assert the shape the rig assumes, rather than trusting the load. Exactly
# one instance, PARALLEL 1, and no TTL -- a TTL here means the JIT path won and
# the model can vanish between the two arms.
echo "=== checking what is actually resident"
PS="$(lms ps 2>&1)"
echo "$PS"
INSTANCES="$(printf '%s\n' "$PS" | grep -c "$ABCC_MODEL")"
if [ "$INSTANCES" -ne 1 ]; then
  echo "EXPECTED EXACTLY ONE INSTANCE, SAW $INSTANCES -- not starting (F567)." >&2
  exit 1
fi
if printf '%s\n' "$PS" | grep -Eq '[0-9]+m */ *[0-9]+m'; then
  echo "THE RESIDENT INSTANCE HAS A TTL -- it can unload mid-run (F567)." >&2
  echo "Re-run without SKIP_LOAD=1 so it is loaded explicitly." >&2
  exit 1
fi

# F539/F550: one real token, and the count is the instrument, not the text.
# F566: this is now a WARM pulse, because the load above already happened -- a
# slow one here means something else is wrong, not that it is loading.
echo "=== preflight: asking $ABCC_MODEL at $ABCC_URL for one token"
if ! "$RESEARCH/harness/scripts/ping.sh" "$ABCC_MODEL" "$ABCC_URL"; then
  echo "PREFLIGHT FAILED -- not starting. Check \`lms ps\` and the port." >&2
  exit 1
fi

run_arm() {
  # $SAMPLE names the sample, so the SAME arm can be asked twice. That pair is
  # the noise floor, and without it a changed tree cannot be told from a re-ask.
  # The tag carries the suite, so a tier's arms cannot be mistaken for the whole
  # corpus's — they are different populations and their tables must not share a
  # filename.
  local scope="$1" tag="scope${SUITE:+-$SUITE}-$1-${SAMPLE:-a}"
  local log="$LOGS/$tag-$(date +%Y%m%d-%H%M%S).log"
  echo
  echo "=== ARM $scope -> reviews-$tag/  (log: $log)"
  echo "=== started $(date -Is)"
  (
    cd "$ABCC_REPO" || exit 1
    ABCC_JUDGE_SCOPE="$scope" ABCC_REVIEW_TAG="$tag" ABCC_REVIEW_SUITE="${SUITE:-}" \
      cargo test -p abcc-gate --test corpus_review -- --ignored --nocapture
  ) 2>&1 | tee "$log"
  local rc="${PIPESTATUS[0]}"
  echo "=== ARM $scope ended $(date -Is), exit $rc"
  return "$rc"
}

case "$ARMS" in
  off)  run_arm off ;;
  on)   run_arm on ;;
  both)
    # Control first, always. If it fails, the treatment has nothing to be read
    # against and running it anyway would only spend the GPU.
    run_arm off || { echo "control arm failed -- stopping" >&2; exit 1; }
    run_arm on
    ;;
  *) echo "usage: scope-probe.sh [off|on|both]" >&2; exit 1 ;;
esac

echo
echo "=== tables:"
ls -l "$ABCC_CORPUS_OUT"/reviews-scope-*.tsv 2>/dev/null
