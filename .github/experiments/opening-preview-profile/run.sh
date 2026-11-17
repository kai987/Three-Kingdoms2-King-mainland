#!/usr/bin/env bash
set -euo pipefail

device=$1
case "$device" in desktop-chromium|touch-chromium) ;; *) exit 2;; esac
profile="$RUNNER_TEMP/opening-preview-profile"
out="$PWD/build/opening-preview-profile/$device"
mkdir -p "$out"
test "$(git rev-parse HEAD)" = "$FROZEN_SOURCE"
test -z "$(git status --porcelain)"
spec=tests/opening-profile.spec.mjs
probe=tests/opening-profile-probe.mjs
config=tools/browser-tests/opening-profile.config.mjs
for file in "$spec" "$probe" "$config"; do test ! -e "$file"; done
trap 'rm -f -- "$spec" "$probe" "$config"' EXIT
cp "$profile/probe.mjs" "$probe"
python -B "$profile/generate.py"
node --check "$spec"
cat > "$config" <<'CONFIG'
import standard from './playwright.config.mjs';
export default {...standard, testMatch:['opening-profile.spec.mjs']};
CONFIG
title=$(node - <<'JS'
const rows=require('./tools/browser-tests/cases.json').cases.filter(c=>c.id==='opening-catalog-first');
if(rows.length!==1)throw Error('Expected one registered first opening batch');
process.stdout.write(rows[0].title+'$');
JS
)
export PLAYWRIGHT_JSON_OUTPUT_FILE="$out/playwright.json"
status=0
node tools/browser-tests/node_modules/@playwright/test/cli.js test \
  --config "$config" --project "$device" --grep "$title" --reporter=list,json || status=$?
find build/browser-results -type f -name 'opening-profile.json' -exec cp {} "$out/" \;
if ((status)); then exit "$status"; fi
test -s "$out/opening-profile.json"
