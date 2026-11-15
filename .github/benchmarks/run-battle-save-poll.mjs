import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import scope from '../../tools/browser-tests/scope.cjs';
import shards from '../../tools/browser-tests/case-shards.cjs';

const [project] = process.argv.slice(2);
assert(shards.PROJECTS.includes(project));
const ids = ['battle-movement', 'battle-layout'];
const cases = scope.CASE_REGISTRY.cases.filter(row => ids.includes(row.id));
assert.equal(cases.length, ids.length);
const result = spawnSync(process.execPath, [
  'tools/browser-tests/node_modules/@playwright/test/cli.js', 'test',
  '--config', 'tools/browser-tests/playwright.config.mjs', '--project', project,
  '--workers', '1', '--grep', shards.grep(cases),
  '--reporter', 'line', '--output', `build/profile-playwright/${project}`,
], { stdio: 'inherit' });
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
