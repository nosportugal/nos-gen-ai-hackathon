#!/usr/bin/env bash
# Build the challenge brief: ./build.sh [--watch]
set -euo pipefail
cd "$(dirname "$0")"
TYPST="${TYPST:-$(command -v typst || echo "$HOME/Work/nos-hackathon-junctionx/.tools/typst")}"
mkdir -p build
CMD=compile; [[ "${1:-}" == "--watch" ]] && CMD=watch
exec "$TYPST" "$CMD" --font-path assets/fonts --root . main.typ build/nos-challenge-brief.pdf
