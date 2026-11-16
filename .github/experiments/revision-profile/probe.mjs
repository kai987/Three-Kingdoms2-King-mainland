import assert from 'node:assert/strict';
import {readFile,writeFile} from 'node:fs/promises';

const now = () => performance.timeOrigin + performance.now();

async function connectWorker(page) {
  const transport = await page.context().newCDPSession(page);
  const {targetInfo: parent} = await transport.send('Target.getTargetInfo');
  const {targetInfos} = await transport.send('Target.getTargets');
  const active = targetInfos.filter(item=>item.type==='worker'
    && (!item.parentId || item.parentId===parent.targetId)
    && new URL(item.url).pathname.endsWith('/browser-engine-worker.js'));
  assert.equal(active.length,1,'Expected the page campaign Worker');
  const {sessionId} = await transport.send('Target.attachToTarget',{targetId:active[0].targetId,flatten:false});
  const pending = new Map();
  let next = 0;
  let paused;
  transport.on('Target.receivedMessageFromTarget',event=>{
    if(event.sessionId!==sessionId)return;
    const packet=JSON.parse(event.message);
    if(packet.method==='Debugger.paused')paused?.(packet.params);
    if(!packet.id || !pending.has(packet.id))return;
    const request=pending.get(packet.id);
    pending.delete(packet.id);
    if(packet.error)request.reject(Error(packet.error.message));
    else request.resolve(packet.result);
  });
  return {
    async send(method,params={}) {
      const id=++next;
      let timer;
      try {
        const result = new Promise((resolve,reject)=>{
          timer=setTimeout(()=>reject(Error('Worker CDP timed out at '+method)),15_000);
          pending.set(id,{resolve,reject});
        });
        // A transport error can occur before the response awaits this promise.
        result.catch(()=>{});
        await transport.send('Target.sendMessageToTarget',{sessionId,message:JSON.stringify({id,method,params})});
        return await result;
      } finally {
        pending.delete(id);
        clearTimeout(timer);
      }
    },
    onPause(callback) { paused=callback; },
    async disconnect() {
      await transport.send('Target.detachFromTarget',{sessionId});
      await transport.detach();
    },
  };
}

export async function prepareRevisionProfile(page,testInfo) {
  await page.addInitScript(()=>{
    const now=()=>performance.timeOrigin+performance.now();
    const diag=globalThis.__tk2RevisionPage={armed:null,rows:[]};
    globalThis.Worker=new Proxy(globalThis.Worker,{
      construct(target,args,newTarget) {
        const worker=Reflect.construct(target,args,newTarget);
        if(!new URL(args[0],location.href).pathname.endsWith('/browser-engine-worker.js'))return worker;
        const pending=new Map();
        worker.addEventListener('message',({data:message})=>{
          if(message?.type!=='response'||!pending.has(message.id))return;
          const row=pending.get(message.id);
          pending.delete(message.id);
          row.response=now();
          row.status=message.status;
        });
        const send=worker.postMessage;
        worker.postMessage=function(message,...rest) {
          if(diag.armed&&message?.type==='request'&&message.path==='/api/state'&&message.method==='GET'){
            const row=diag.armed;
            row.id=message.id;
            row.send=now();
            pending.set(message.id,row);
          }
          return Reflect.apply(send,this,[message,...rest]);
        };
        return worker;
      },
    });
  });
  let worker;
  const readings=[];
  let marchStatus;
  async function read(compact) {
    const enter=now();
    const revision=await page.evaluate(async compact=>{
      const now=()=>performance.timeOrigin+performance.now();
      const diag=globalThis.__tk2RevisionPage;
      const row={compact};
      diag.rows.push(row);
      let request;
      diag.armed=row;
      try {
        if(compact){
          const token=viewCache.token();
          if(!/^[a-f0-9]{64}:[a-f0-9]{64}$/.test(token))throw Error('Expected a warm catalog and quote cache');
          request=fetch('/api/state',{tk2ViewCache:token});
        } else {
          request=fetch('/api/state');
        }
      } finally {
        diag.armed=null;
      }
      const response=await request;
      if(!response.ok)throw Error('Revision inspection failed');
      row.parseStart=now();
      const body=await response.json();
      row.parseEnd=now();
      const revision=(body.view||body).revision;
      row.revision=revision;
      row.uiRevision=view.revision;
      if(compact)row.cache={schema:body.transport,staticCatalog:'static_catalog' in body,travelQuotes:'travel_quotes' in body.view.catalog};
      row.ready=now();
      return revision;
    },compact);
    readings.push({enter,exit:now(),revision,compact});
    return revision;
  }
  return {
    async attach() {
      worker=await connectWorker(page);
      const python=await readFile(new URL('./worker.py',import.meta.url),'utf8');
      const code=await readFile(new URL('./worker.js',import.meta.url),'utf8');
      await worker.send('Debugger.enable');
      const {breakpointId,locations}=await worker.send('Debugger.setBreakpointByUrl',{
        urlRegex:'/browser-engine-worker\\.js',
        lineNumber:113,
      });
      assert.ok(locations.length,'Pinned Worker breakpoint did not resolve');
      let timer;
      const paused=new Promise((resolve,reject)=>{
        timer=setTimeout(()=>reject(Error('Worker did not pause on the read-only handshake')),15_000);
        worker.onPause(resolve);
      });
      try {
        await page.evaluate(()=>{
          globalThis.__tk2RevisionPage.handshake=new Promise((resolve,reject)=>{
            setTimeout(async()=>{
              try {
                const response=await fetch('/api/march-status');
                if(!response.ok)throw Error('Worker inspection handshake failed');
                resolve(await response.json());
              } catch(error) { reject(error); }
            },0);
          });
        });
        const frame=(await paused).callFrames[0];
        const result=await worker.send('Debugger.evaluateOnCallFrame',{
          callFrameId:frame.callFrameId, expression:`(${code})(py,${JSON.stringify(python)})`,
          returnByValue:true,
        });
        assert.equal(result.result?.value,true,JSON.stringify(result.exceptionDetails ?? result));
        await worker.send('Debugger.removeBreakpoint',{breakpointId});
      } finally {
        clearTimeout(timer);
        worker.onPause(null);
        await worker.send('Debugger.resume').catch(()=>{});
        await worker.send('Debugger.disable');
      }
      marchStatus=await page.evaluate(()=>globalThis.__tk2RevisionPage.handshake);
    },
    revision:()=>read(false),
    async finish() {
      assert.equal(readings.length,8);
      const compact=await read(true);
      assert.equal(compact,readings[7].revision);
      const rows=await page.evaluate(()=>globalThis.__tk2RevisionPage.rows);
      const cdp=await worker.send('Runtime.evaluate',{expression:'globalThis.__tk2RevisionWorker()',returnByValue:true});
      assert.ok(cdp.result?.value,JSON.stringify(cdp.exceptionDetails ?? cdp));
      const {messages,python}=cdp.result.value;
      assert.equal(messages.length,python.length);
      assert.equal(rows.length,readings.length);
      const combined=rows.map((row,i)=>{
        const position=messages.findIndex(m=>m.id===row.id);
        assert.ok(position>=0,'Missing Worker-side read');
        const message=messages[position], phases=python[position];
        assert.equal(message.compact,row.compact);
        assert.equal(phases.compact,row.compact);
        assert.equal(message.status,row.status);
        assert.equal(row.status,200);
        assert.equal(readings[i].revision,row.revision);
        assert.ok(phases.viewMs>0&&phases.encodeMs>0,'Missing Python phase timings');
        assert.ok(message.received<=phases.pythonStart&&phases.pythonEnd<=message.postStart);
        return {...row,...readings[i],worker:message,python:phases};
      });
      await worker.disconnect();
      await writeFile(testInfo.outputPath('allocation-revision-profile.json'),JSON.stringify({reads:combined,marchStatus}));
    },
  };
}
