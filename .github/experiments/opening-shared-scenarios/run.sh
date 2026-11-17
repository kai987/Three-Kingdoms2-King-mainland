#!/usr/bin/env bash
set -euo pipefail

device=$1
mode=$2
case "$mode" in baseline|shared) ;; *) exit 2;; esac
export TK2_OPENING_SHARED_MODE="$mode"
case "$device" in desktop-chromium|touch-chromium) ;; *) exit 2;; esac
profile="$RUNNER_TEMP/opening-shared-scenarios"
out="$PWD/build/opening-shared-scenarios/$device-$mode"
mkdir -p "$out"
test "$(git rev-parse HEAD)" = "$FROZEN_SOURCE"
test -z "$(git status --porcelain)"
spec=tests/opening-shared-profile.spec.mjs
probe=tests/opening-shared-probe.mjs
worker=tests/opening-shared-worker-cdp.mjs
python=tests/opening-shared-worker.py
config=tools/browser-tests/opening-shared-scenarios.config.mjs
for file in "$spec" "$probe" "$worker" "$python" "$config"; do test ! -e "$file"; done
trap 'rm -f -- "$spec" "$probe" "$worker" "$python" "$config"' EXIT
cp "$profile/probe.mjs" "$probe"
cp "$profile/worker-cdp.mjs" "$worker"
cp "$profile/worker-profile.py" "$python"
python -B "$profile/generate.py"
node --check "$spec"
cat > "$config" <<'CONFIG'
import standard from './playwright.config.mjs';
export default {...standard, testMatch:['opening-shared-profile.spec.mjs'],
 use:{...standard.use,launchOptions:{args:['--remote-debugging-port=18928']}}};
CONFIG
title=$(node - <<'JS'
const [row]=require('./tools/browser-tests/cases.json').cases.filter(c=>c.id==='opening-catalog-first');
process.stdout.write(row.title+'$');
JS
)
export PLAYWRIGHT_JSON_OUTPUT_FILE="$out/playwright.json"
status=0
node tools/browser-tests/node_modules/@playwright/test/cli.js test \
  --config "$config" --project "$device" --grep "$title" --reporter=list,json || status=$?
find build/browser-results -type f -name 'opening-shared-trial.json' -exec cp {} "$out/" \;
if ((status)); then exit "$status"; fi
test -s "$out/opening-shared-trial.json"
