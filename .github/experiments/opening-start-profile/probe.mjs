import {writeFile} from 'node:fs/promises';
import {prepareWorkerProbe} from './opening-start-worker-cdp.mjs';

export async function installStartProfile(page,testInfo) {
  await page.addInitScript(() => {
    let active;
    window.__openingProbe = {
      arm(scenario) { active = {scenario, renders:[], eventOpens:[], eventCloses:[]}; },
      end() { const row=active; active = null; return row; },
    };
    document.addEventListener('click',event => {
      if (active && event.target.closest?.('#begin')) active.click = performance.now();
    },true);
    window.Worker = new Proxy(window.Worker, {
      construct(target,args,newTarget) {
        const worker = Reflect.construct(target,args,newTarget);
        if (!new URL(args[0],location.href).pathname.endsWith('/browser-engine-worker.js')) return worker;
        const send = worker.postMessage;
        worker.postMessage = function(message,...rest) {
          if (active && message?.type === 'request' && message.path === '/api/command') {
            const data = JSON.parse(message.body);
            if (data.kind === 'new' && data.payload.scenario === active.scenario) {
              active.id = message.id;
              active.sent = performance.now();
            }
          }
          return Reflect.apply(send,this,[message,...rest]);
        };
        worker.addEventListener('message',({data}) => {
          if (active && data?.type === 'response' && data.id === active.id) {
            active.received = performance.now();
            active.status = data.status;
          }
        });
        return worker;
      },
    });
  });

  let worker, setup, pageCDP;
  const rows=[];
  async function metrics() {
    const {metrics} = await pageCDP.send('Performance.getMetrics');
    return Object.fromEntries(metrics.filter(row => ['RecalcStyleDuration','LayoutDuration'].includes(row.name))
      .map(row => [row.name,row.value]));
  }
  return {
    async attach() {
      [worker] = page.workers().filter(w=>new URL(w.url()).pathname.endsWith('/browser-engine-worker.js'));
      if (!worker) throw Error('Shipped game Worker missing');
      pageCDP = await page.context().newCDPSession(page);
      await pageCDP.send('Performance.enable');
      await page.evaluate(() => {
        const probe = window.__openingProbe;
        const render = window.render;
        if (typeof render !== 'function') throw Error('Game renderer is unavailable');
        window.render = function(...args) {
          const start = performance.now();
          try { return Reflect.apply(render,this,args); }
          finally { probe.captureRender(start,performance.now()); }
        };
        const arm = probe.arm, end=probe.end;
        let row;
        probe.arm = scenario => { arm(scenario); row={renders:[],eventOpens:[],eventCloses:[]}; };
        probe.end = () => { const result=Object.assign(end(),row); row=null; return result; };
        probe.captureRender = (start,end) => { row?.renders.push({start,end}); };
        const modal = document.querySelector('#event-dialog');
        if (!modal) throw Error('Game event dialog missing');
        const show=modal.showModal, close=modal.close;
        modal.showModal = function(...args) {
          const result=Reflect.apply(show,this,args);
          row?.eventOpens.push(performance.now());
          return result;
        };
        modal.close = function(...args) {
          const result=Reflect.apply(close,this,args);
          row?.eventCloses.push(performance.now());
          return result;
        };
        new MutationObserver(() => {
          if (!row) return;
          const busy=document.body.classList.contains('busy');
          if (busy) row.sawBusy=true;
          else if (row.sawBusy && row.busyCleared === undefined) row.busyCleared=performance.now();
        }).observe(document.body,{attributes:true,attributeFilter:['class']});
      });
      await worker.evaluate(() => {
        const receive=self.onmessage, send=self.postMessage, pending=new Map(), complete=[];
        self.onmessage=function(event) {
          const message=event.data;
          if (message?.type==='request' && message.path==='/api/command' && JSON.parse(message.body).kind==='new') pending.set(message.id,performance.now());
          return Reflect.apply(receive,this,[event]);
        };
        self.postMessage=function(message,...rest) {
          if (message?.type==='response' && pending.has(message.id)) {
            const started=pending.get(message.id);
            complete.push({id:message.id, ms:performance.now()-started, status:message.status});
            pending.delete(message.id);
          }
          return Reflect.apply(send,this,[message,...rest]);
        };
        self.__openingWorkerStarts=()=>complete;
      });
      setup=await prepareWorkerProbe(worker.url());
      page.once('close',()=>setup.close());
    },
    async arm(scenario) {
      await setup.ready;
      await page.evaluate(scenario=>window.__openingProbe.arm(scenario),scenario);
      return metrics();
    },
    async scenario(row, before) {
      const browser=await page.evaluate(()=>window.__openingProbe.end());
      const after=await metrics();
      rows.push({...row,browser,layoutMs:(after.LayoutDuration-before.LayoutDuration)*1000,
        styleMs:(after.RecalcStyleDuration-before.RecalcStyleDuration)*1000});
    },
    async finish() {
      const {workerRows, python} = await worker.evaluate(()=>({
        workerRows:self.__openingWorkerStarts(),python:JSON.parse(self.__openingPythonProfile()),
      }));
      await writeFile(testInfo.outputPath('opening-start-profile.json'),JSON.stringify({rows,workerRows,python},null,2));
      setup.close();
    },
  };
}
