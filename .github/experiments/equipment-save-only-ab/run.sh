#!/usr/bin/env bash
set -euo pipefail

device=$1
variant=$2
case "$device" in desktop-chromium|touch-chromium) ;; *) exit 2;; esac
case "$variant" in baseline|save-only) ;; *) exit 2;; esac
profile="$RUNNER_TEMP/equipment-save-only-ab"
out="$PWD/build/equipment-save-only-ab/$device-$variant"
mkdir -p "$out"
test "$(git rev-parse HEAD)" = "$FROZEN_SOURCE"
git diff --exit-code
trap 'git restore -- tests/browser_ui.spec.mjs' EXIT
if [[ $variant == save-only ]]; then
  git apply "$profile/save-only.patch"
fi
EQUIPMENT_VARIANT=$variant python -B "$profile/patch.py"
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
