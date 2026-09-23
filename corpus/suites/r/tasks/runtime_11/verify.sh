#!/usr/bin/env bash
# RUNTIME-11: the card's hidden test, the rest of the lib, fmt and clippy — see ../../lib/card_verify.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/../../lib/card_verify.sh" "${1:-}" "${2:-}" crates/claudette/src/runtime/usage.rs "$HERE/hidden.rs"
