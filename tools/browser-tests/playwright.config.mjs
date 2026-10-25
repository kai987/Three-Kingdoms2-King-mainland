import {defineConfig, devices} from '@playwright/test';
import {fileURLToPath} from 'node:url';
import browserScopes from './scope.cjs';

const root=fileURLToPath(new URL('../../',import.meta.url));
const selection=browserScopes.loadBrowserScope();
export default defineConfig({
 testDir:fileURLToPath(new URL('../../tests/',import.meta.url)),
 testMatch:'browser_ui.spec.mjs',
 grep:selection.grep,
 outputDir:root+'build/browser-results',
 timeout:240_000,
 expect:{timeout:30_000},
 fullyParallel:false,
 workers:1,
 retries:0,
 reporter:[['list'],['html',{outputFolder:root+'build/browser-report',open:'never'}]],
 use:{
  channel:'chromium',
  baseURL:'http://127.0.0.1:18917/Three-Kingdoms2-King-mainland/',
  actionTimeout:30_000,trace:'retain-on-failure',screenshot:'only-on-failure',video:'retain-on-failure',
 },
 projects:[
  {name:'desktop-chromium',use:{...devices['Desktop Chrome'],viewport:{width:1280,height:800}}},
  {name:'touch-chromium',use:{...devices['iPhone 13'],defaultBrowserType:'chromium',viewport:{width:390,height:844}}},
 ],
 webServer:{
  command:'node tests/browser_static_server.mjs build/web',cwd:root,
  url:'http://127.0.0.1:18917/Three-Kingdoms2-King-mainland/',
  reuseExistingServer:false,timeout:15_000,
 },
});
