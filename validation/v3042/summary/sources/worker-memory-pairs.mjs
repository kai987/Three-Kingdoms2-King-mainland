import {createRequire} from 'node:module';
import path from 'node:path';

const require=createRequire(path.resolve('tools/browser-tests/package.json'));
const {chromium,expect}=require('@playwright/test');
const url=process.argv[2];
const browser=await chromium.launch({channel:'chromium'});
let sequence=0;
async function sample(enabled){
 const page=await browser.newPage({viewport:{width:1280,height:800}});
 await page.goto(url);
 await expect(page.locator('#game-loading-start')).toBeEnabled({timeout:120000});
 await page.locator('#game-loading-start').click();
 await page.locator('#scenario').selectOption('mainland227-02');
 if(enabled)await page.locator('#infrastructure-option').check();
 await page.locator('input[name=faction][value=shu]').check();
 await page.locator('#begin').click();
 await expect(page.locator('#world-map .city-hit')).not.toHaveCount(0);
 await expect(page.locator('body')).not.toHaveClass(/\bbusy\b/);
 await expect(page.locator('[data-map-wharf]')).toHaveCount(enabled?6:0,{timeout:90000});
 const browserSession=await browser.newBrowserCDPSession();
 const {targetInfos}=await browserSession.send('Target.getTargets');
 const worker=targetInfos.find(t=>t.type==='worker'&&t.url.includes('/browser-engine-worker.js'));
 if(!worker)throw new Error('Dedicated game Worker is missing');
 const {sessionId}=await browserSession.send('Target.attachToTarget',{targetId:worker.targetId,flatten:false});
 async function workerRequest(method){
  const id=++sequence;
  const promise=new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>{
    browserSession.off('Target.receivedMessageFromTarget',listener);
    reject(new Error(method+' timed out'));
   },10000);
   const listener=row=>{
    if(row.sessionId!==sessionId)return;
    const message=JSON.parse(row.message);
    if(message.id!==id)return;
    clearTimeout(timer);
    browserSession.off('Target.receivedMessageFromTarget',listener);
    if(message.error)reject(new Error(message.error.message));
    else resolve(message.result);
   };
   browserSession.on('Target.receivedMessageFromTarget',listener);
  });
  await browserSession.send('Target.sendMessageToTarget',{sessionId,message:JSON.stringify({id,method})});
  return promise;
 }
 await workerRequest('HeapProfiler.collectGarbage');
 const memory=await workerRequest('Runtime.getHeapUsage');
 await page.close();
 await browserSession.detach();
 return {enabled,...memory};
}
try {
 const measurements=[];
 for(const enabled of [false,true,true,false])measurements.push(await sample(enabled));
 console.log(JSON.stringify({browser:browser.version(),scenario:'227-02',seed:2026,
  api:'Chrome Runtime.getHeapUsage after HeapProfiler.collectGarbage',measurements,units:'bytes'},null,2));
}finally{await browser.close();}
