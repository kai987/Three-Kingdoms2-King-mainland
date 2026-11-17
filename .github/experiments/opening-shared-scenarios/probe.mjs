import {createHash} from 'node:crypto';
import {writeFile} from 'node:fs/promises';
import {prepareWorkerProbe} from './opening-shared-worker-cdp.mjs';

export async function installOpeningTrial(page,testInfo) {
  const shared = process.env.TK2_OPENING_SHARED_MODE === 'shared';
  await page.addInitScript(({shared}) => {
    const optIn = 'scenarios-v1|';
    const hex = /^[a-f0-9]{64}$/;
    const rows=[];
    const responseRows=new WeakMap();
    const decodedRows=new WeakMap();
    const encoder = new TextEncoder();
    const callbacks=[];
    let held = true, receiving, index = 0;
    const NativeWorker=window.Worker;
    const NativeResponse=window.Response;

    window.Worker = new Proxy(NativeWorker,{
      construct(target,args,newTarget) {
        const worker = Reflect.construct(target,args,newTarget);
        if (!new URL(args[0],location.href).pathname.endsWith('/browser-engine-worker.js')) return worker;
        const pending=new Map();
        const send=worker.postMessage;
        worker.addEventListener('message',({data})=>{
          if (data?.type!=='response' || !pending.has(data.id)) return;
          const row=pending.get(data.id);
          pending.delete(data.id);
          row.received=performance.now();
          row.status=data.status;
          row.raw=data.body;
          receiving=row;
        });
        worker.postMessage=function(message,...args) {
          if (message?.type!=='request') return Reflect.apply(send,this,[message,...args]);
          const input=message.path==='/api/command' ? JSON.parse(message.body) : null;
          const scenario=input?.kind==='new' ? input.payload.scenario : null;
          if (scenario) {
            // Hold the campaign identity constant across the paired runs.
            input.payload.campaign_id=(++index).toString(16).padStart(32,'0');
            message={...message,body:JSON.stringify(input)};
          }
          const start=()=>{
            if (scenario || message.path==='/api/state') {
              const row={scenario,input,id:message.id,sent:performance.now()};
              rows.push(row);
              pending.set(message.id,row);
            }
            return Reflect.apply(send,this,[message,...args]);
          };
          if (held) callbacks.push(start);
          else return start();
        };
        return worker;
      },
    });

    window.Response = new Proxy(NativeResponse,{
      construct(target,args,newTarget) {
        const response=Reflect.construct(target,args,newTarget);
        if (receiving && args[0]===receiving.raw) {
          responseRows.set(response,receiving);
          receiving=null;
        }
        return response;
      },
    });
    const json=NativeResponse.prototype.json;
    NativeResponse.prototype.json=function(...args) {
      const row=responseRows.get(this);
      const done=Reflect.apply(json,this,args);
      if (!row) return done;
      return done.then(data=>{
        if (data && typeof data==='object') decodedRows.set(data,row);
        return data;
      });
    };

    function canonical(value) {
      return JSON.stringify(value,(_,item)=>
        item && typeof item==='object' && !Array.isArray(item)
          ? Object.fromEntries(Object.entries(item).sort(([a],[b])=>a<b?-1:a>b?1:0))
          : item);
    }
    function proof(value) {
      return crypto.subtle.digest('SHA-256',encoder.encode(canonical(value)))
        .then(bytes=>Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join(''));
    }

    let api;
    Object.defineProperty(window,'GameViewCache',{
      configurable:true,
      get:()=>api,
      set(original) {
        api={...original, create(...args) {
          const cache=original.create(...args);
          let scenarios;
          return {
            token() {
              const base=cache.token();
              return shared ? optIn+base+'|'+(scenarios?.token ?? '') : base;
            },
            hydrate(data) {
              const tracked=decodedRows.get(data);
              const start=performance.now();
              let value=cache.hydrate(data);
              if (shared && data.transport==='tk2-view-v1') {
                const token=data.scenarios_token;
                if (!hex.test(token)) throw Error('Missing shared scenarios identity');
                if ('shared_scenarios' in data) {
                  if (!Array.isArray(data.shared_scenarios)) throw Error('Invalid shared scenarios');
                  scenarios={token, data:data.shared_scenarios};
                }
                if (scenarios?.token!==token) throw Error('Shared scenarios cache miss without payload');
                value={...value,catalog:{...value.catalog,scenarios:structuredClone(scenarios.data)}};
              }
              if (tracked && tracked.status===200) {
                tracked.hydrateMs=performance.now()-start;
                tracked.sharedToken=data.scenarios_token ?? null;
                tracked.sharedSent='shared_scenarios' in data;
                tracked.viewProof=proof(value);
              }
              return value;
            },
            clear() { cache.clear(); scenarios=undefined; },
          };
        }};
      },
    });
    window.__openingObserver={
      release() { held=false; for (const send of callbacks.splice(0)) send(); },
      async capture(scenario) {
        const row=rows.find(entry=>entry.scenario===scenario && entry.raw!==undefined);
        if (!row || !row.viewProof) throw Error('Missing captured opening response');
        const result={...row,bodyBytes:encoder.encode(row.raw).byteLength,viewProof:await row.viewProof};
        delete result.raw;
        delete row.raw;
        return result;
      },
    };
  },{shared});
  let worker, setup;
  const views=[], saves=[];
  return {
    async attach() {
      worker=await page.waitForEvent('worker',{predicate:w=>new URL(w.url()).pathname.endsWith('/browser-engine-worker.js')});
      setup=await prepareWorkerProbe(worker.url());
      page.once('close',()=>setup.close());
      await page.evaluate(()=>window.__openingObserver.release());
      await setup.ready;
    },
    async capture(scenario) {
      views.push(await page.evaluate(scenario=>window.__openingObserver.capture(scenario),scenario));
    },
    save(scenario,cities,text) {
      saves.push({scenario,cities,digest:createHash('sha256').update(text).digest('hex')});
    },
    async finish() {
      const workerRows=JSON.parse(await worker.evaluate(()=>self.__openingPythonProfile()));
      await writeFile(testInfo.outputPath('opening-shared-trial.json'),JSON.stringify({shared,views,saves,workerRows},null,2));
      setup.close();
    },
  };
}
