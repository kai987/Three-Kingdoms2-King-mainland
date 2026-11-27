import base from '../../tools/browser-tests/playwright.config.mjs';
const port='18941';
const address='http://127.0.0.1:'+port+'/Three-Kingdoms2-King-mainland/';
export default {...base,outputDir:'browser-rerun-verified',timeout:420_000,
 use:{...base.use,baseURL:address},webServer:{...base.webServer,url:address,env:{TK2_STATIC_TEST_PORT:port}}};
