#!/usr/bin/env bash
set -euo pipefail

project=$1
variant=$2
case $project in desktop-chromium|touch-chromium) ;; *) exit 2;; esac
case $variant in baseline|warm) ;; *) exit 2;; esac
experiment="$RUNNER_TEMP/allocation-revision-ab"
output="$PWD/build/allocation-revision-ab/$project-$variant"
test_file=tests/browser_ui.spec.mjs
mkdir -p "$output"
test "$(git rev-parse HEAD)" = "$FROZEN_SOURCE"
git diff --exit-code "$FROZEN_SOURCE" -- "$test_file"

restore() {
  git restore -- "$test_file"
}
trap restore EXIT
if [[ $variant == warm ]]; then
  git apply "$experiment/warm.patch"
fi
REVISION_VARIANT=$variant python -B "$experiment/patch.py"
node --check "$test_file"

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
find build/browser-results -type f \( -name 'paid-allocation-raw-save.json' -o -name 'paid-allocation-three-officer-ledgers.json' -o -name 'allocation-revision-ab.json' \) -exec cp {} "$output/" \;
if ((status)); then exit "$status"; fi
node -e "
  const {expected,unexpected,skipped,flaky}=require(process.env.PLAYWRIGHT_JSON_OUTPUT_FILE).stats;
  if(expected!==1||unexpected||skipped||flaky)throw Error('Expected one passing allocation case');
"
test -s "$output/paid-allocation-raw-save.json"
test -s "$output/paid-allocation-three-officer-ledgers.json"
test -s "$output/allocation-revision-ab.json"
restore
trap - EXIT
git diff --exit-code "$FROZEN_SOURCE" -- "$test_file"
