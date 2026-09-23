#!/usr/bin/env bash
# SHELL-07: the card's hidden test, the rest of the lib, fmt and clippy — see ../../lib/card_verify.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
exec bash "$HERE/../../lib/card_verify.sh" "${1:-}" "${2:-}" crates/claudette/src/tools/search.rs "$HERE/hidden.rs"
