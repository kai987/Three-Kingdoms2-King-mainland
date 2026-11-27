import base from '../../tools/browser-tests/playwright.config.mjs';
const port='18937';
const address='http://127.0.0.1:'+port+'/Three-Kingdoms2-King-mainland/';
export default {...base,outputDir:'build/transshipment-v304/verified/browser-full',
 use:{...base.use,baseURL:address},
 webServer:{...base.webServer,url:address,env:{TK2_STATIC_TEST_PORT:port}}};
