#!/usr/bin/env bash
set -euo pipefail
variant=${1:?}
project=${2:?}
case "$variant" in
  baseline) ref=$BASELINE_SHA ;;
  response) ref=$RESPONSE_SHA ;;
  *) exit 2 ;;
esac
git show "${ref}:tests/browser_ui.spec.mjs" > tests/browser_ui.spec.mjs
python -B .github/benchmarks/instrument-battle-save-poll.py "$variant"
git diff --check
PROFILE_VARIANT="$variant" node .github/benchmarks/run-battle-save-poll.mjs "$project"
