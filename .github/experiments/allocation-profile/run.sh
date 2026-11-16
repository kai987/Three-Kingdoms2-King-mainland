#!/usr/bin/env bash
set -euo pipefail

project=$1
variant=$2
case $project in desktop-chromium|touch-chromium) ;; *) exit 2;; esac
case $variant in control|profile) ;; *) exit 2;; esac
experiment="$RUNNER_TEMP/allocation-profile"
output="$PWD/build/allocation-profile/$project-$variant"
test_file=tests/browser_ui.spec.mjs
core=tools/browser-tests/node_modules/playwright-core/lib/coreBundle.js
mkdir -p "$output"
test "$(git rev-parse HEAD)" = "$FROZEN_SOURCE"
git diff --exit-code "$FROZEN_SOURCE" -- "$test_file"

if [[ $variant == profile ]]; then
  backup=$(mktemp)
  cp "$core" "$backup"
  restore() {
    cp "$backup" "$core"
    rm "$backup"
    git restore -- "$test_file"
  }
  trap restore EXIT
  python -B "$experiment/patch.py"
  node --check "$test_file"
  node --check "$core"
fi

target=$(node -e "
  const {grep}=require('./tools/browser-tests/case-shards.cjs');
  const cases=require('./tools/browser-tests/cases.json').cases.filter(row=>row.id==='order-confirmation-allocation');
  if(cases.length!==1)throw Error('Expected one registered allocation case');
  process.stdout.write(grep(cases));
")
export PLAYWRIGHT_JSON_OUTPUT_FILE="$output/playwright.json"
status=0
node tools/browser-tests/node_modules/@playwright/test/cli.js test \
  --config tools/browser-tests/playwright.config.mjs --project "$project" \
  --fully-parallel --grep "$target" --reporter=list,json || status=$?
find build/browser-results -type f \( -name 'paid-allocation-raw-save.json' -o -name 'paid-allocation-three-officer-ledgers.json' -o -name 'allocation-profile.json' \) -exec cp {} "$output/" \;
if ((status)); then exit "$status"; fi
node -e "
  const {expected,unexpected,skipped,flaky}=require(process.env.PLAYWRIGHT_JSON_OUTPUT_FILE).stats;
  if(expected!==1||unexpected||skipped||flaky)throw Error('Expected one passing allocation case');
"
test -s "$output/paid-allocation-raw-save.json"
test -s "$output/paid-allocation-three-officer-ledgers.json"
if [[ $variant == profile ]]; then
  test -s "$output/allocation-profile.json"
  restore
  trap - EXIT
fi
git diff --exit-code "$FROZEN_SOURCE" -- "$test_file"
