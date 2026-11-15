import { defineConfig } from '../../tools/browser-tests/node_modules/@playwright/test/index.mjs';
import base from '../../tools/browser-tests/playwright.config.mjs';
import { fileURLToPath } from 'node:url';

export default defineConfig({
  ...base,
  grep: undefined,
  testDir: fileURLToPath(new URL('.', import.meta.url)),
  testMatch: 'battle-step-edge.spec.mjs',
  reporter: 'line',
});
