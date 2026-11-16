#!/usr/bin/env bash
set -euo pipefail

project=$1
variant=$2
case $project in desktop-chromium|touch-chromium) ;; *) exit 2;; esac
case $variant in control|profile) ;; *) exit 2;; esac
patch=.github/experiments/soldier-breakdown/timing.patch
output="$PWD/build/soldier-breakdown/$project-$variant"
mkdir -p "$output"

git diff --exit-code "$FROZEN_SOURCE" -- tests/browser_soldier_ui.spec.mjs
if [[ $variant == profile ]]; then
  git apply "$patch"
  trap 'git apply --reverse "$patch"' EXIT
fi

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

find build/browser-results -type f \( -name 'actual-soldier-orders-events-and-rng.json' -o -name 'soldier-orders-breakdown.json' \) -exec cp {} "$output/" \;
if [[ $test_status != 0 ]]; then exit "$test_status"; fi

node -e "
  const report=require(process.env.PLAYWRIGHT_JSON_OUTPUT_FILE);
  const {expected,unexpected,skipped,flaky}=report.stats;
  if(expected!==1||unexpected||skipped||flaky)throw Error('Expected one passing focused case');
"
test -s "$output/actual-soldier-orders-events-and-rng.json"
if [[ $variant == profile ]]; then
  test -s "$output/soldier-orders-breakdown.json"
  git apply --reverse "$patch"
  trap - EXIT
fi
git diff --exit-code "$FROZEN_SOURCE" -- tests/browser_soldier_ui.spec.mjs
