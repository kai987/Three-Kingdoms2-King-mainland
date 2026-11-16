#!/usr/bin/env bash
set -euo pipefail

project=$1
variant=$2
case $project in desktop-chromium|touch-chromium) ;; *) exit 2;; esac
case $variant in baseline|optimized) ;; *) exit 2;; esac
experiment=.github/experiments/soldier-opening-view
source=tests/browser_soldier_ui.spec.mjs
core=tools/browser-tests/node_modules/playwright-core
output="$PWD/build/soldier-opening-view/$project-$variant"
mkdir -p "$output"

git diff --exit-code "$OPTIMIZED_TEST" -- "$source"
original_core=$(mktemp)
cp "$core/lib/coreBundle.js" "$original_core"
restore() {
  cp "$original_core" "$core/lib/coreBundle.js"
  rm "$original_core"
  git restore -- "$source"
}
trap restore EXIT
if [[ $variant == baseline ]]; then
  git show "$FROZEN_SOURCE:$source" > "$source"
  git diff --exit-code "$FROZEN_SOURCE" -- "$source"
fi
python -B "$experiment/instrument-case.py" "$variant"
python -B "$experiment/instrument.py" "$core"
node --check "$source"
node --check "$core/lib/coreBundle.js"

target=$(node -e "
  const {grep}=require('./tools/browser-tests/case-shards.cjs');
  const cases=require('./tools/browser-tests/cases.json').cases.filter(row=>row.id==='soldier-orders');
  if(cases.length!==1)throw Error('Expected exactly one registered soldier-orders case');
  process.stdout.write(grep(cases));
")
export PLAYWRIGHT_JSON_OUTPUT_FILE="$output/playwright.json"
test_status=0
node tools/browser-tests/node_modules/@playwright/test/cli.js test \
  --config tools/browser-tests/playwright.config.mjs --project "$project" \
  --fully-parallel --grep "$target" --reporter=list,json || test_status=$?

find build/browser-results -type f \( -name 'actual-soldier-orders-events-and-rng.json' -o -name 'soldier-opening-view.json' \) -exec cp {} "$output/" \;
if [[ $test_status != 0 ]]; then exit "$test_status"; fi

node -e "
  const report=require(process.env.PLAYWRIGHT_JSON_OUTPUT_FILE);
  const {expected,unexpected,skipped,flaky}=report.stats;
  if(expected!==1||unexpected||skipped||flaky)throw Error('Expected one passing focused case');
"
test -s "$output/actual-soldier-orders-events-and-rng.json"
test -s "$output/soldier-opening-view.json"
restore
trap - EXIT
git diff --exit-code "$OPTIMIZED_TEST" -- "$source"
