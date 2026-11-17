#!/usr/bin/env bash
set -euo pipefail

device=$1
case "$device" in desktop-chromium|touch-chromium) ;; *) exit 2;; esac
profile="$RUNNER_TEMP/equipment-read-profile"
out="$PWD/build/equipment-read-profile/$device"
mkdir -p "$out"
test "$(git rev-parse HEAD)" = "$FROZEN_SOURCE"
git diff --exit-code
trap 'git restore -- tests/browser_ui.spec.mjs' EXIT
python -B "$profile/patch.py"
node --check tests/browser_ui.spec.mjs
title=$(node - <<'JS'
const rows=require('./tools/browser-tests/cases.json').cases.filter(c=>c.id==='equipment');
if(rows.length!==1)throw Error('Expected exactly one registered equipment case');
process.stdout.write(rows[0].title+'$');
JS
)
export PLAYWRIGHT_JSON_OUTPUT_FILE="$out/playwright.json"
status=0
node tools/browser-tests/node_modules/@playwright/test/cli.js test \
  --config tools/browser-tests/playwright.config.mjs --project "$device" \
  --grep "$title" --reporter=list,json || status=$?
find build/browser-results -type f -name 'equipment-profile.json' -exec cp {} "$out/" \;
if ((status)); then exit "$status"; fi
test -s "$out/equipment-profile.json"
