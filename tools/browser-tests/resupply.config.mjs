import {defineConfig,devices} from '@playwright/test';
import {fileURLToPath} from 'node:url';

const root=fileURLToPath(new URL('../../',import.meta.url));
export default defineConfig({
 testDir:root+'tests',testMatch:'browser_resupply.spec.mjs',
 outputDir:root+'build/resupply-browser-results',timeout:90_000,
 expect:{timeout:15_000},fullyParallel:false,workers:1,retries:0,reporter:'list',
 use:{channel:'chromium',baseURL:'http://127.0.0.1:18919/',actionTimeout:15_000,trace:'retain-on-failure',screenshot:'only-on-failure'},
 projects:[
  {name:'desktop-resupply',use:{...devices['Desktop Chrome'],viewport:{width:1280,height:900}}},
  {name:'touch-resupply',use:{...devices['iPhone 13'],defaultBrowserType:'chromium',viewport:{width:390,height:844}}},
 ],
 webServer:{command:'python3 -B tests/browser_resupply_fixture.py --port 18919',cwd:root,
  url:'http://127.0.0.1:18919/',reuseExistingServer:false,timeout:15_000},
});
