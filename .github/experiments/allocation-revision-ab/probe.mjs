import {writeFile} from 'node:fs/promises';

export async function prepareRevisionProbe(page,testInfo) {
  await page.addInitScript(()=>{
    const rows=[];
    let current=null;
    let armed=false;
    globalThis.__tk2AllocationRevisionProbe={
      request(fetchState) {
        if(current)throw Error('A revision read is already pending');
        current={};
        armed=true;
        try { return fetchState(); }
        finally { armed=false; }
      },
      parseStart() { current.parseStart=performance.now(); },
      parseEnd() { current.parseEnd=performance.now(); },
      finish(revision,body) {
        if(!Number.isSafeInteger(revision)||current.status!==200||!Number.isSafeInteger(current.bodyUtf16Units)){
          throw Error('Missing revision or dedicated Worker reply');
        }
        current.revision=revision;
        current.transport=body.transport??null;
        current.staticCatalog='static_catalog' in body;
        current.travelQuotes='travel_quotes' in (body.view||body).catalog;
        rows.push(current);
        current=null;
      },
      rows,
    };
    globalThis.Worker=new Proxy(globalThis.Worker,{
      construct(target,args,newTarget) {
        const worker=Reflect.construct(target,args,newTarget);
        if(!new URL(args[0],location.href).pathname.endsWith('/browser-engine-worker.js'))return worker;
        const pending=new Map();
        worker.addEventListener('message',({data})=>{
          if(data?.type!=='response'||!pending.has(data.id))return;
          const row=pending.get(data.id);
          pending.delete(data.id);
          row.received=performance.now();
          row.status=data.status;
          row.bodyUtf16Units=data.body?.length;
        });
        const postMessage=worker.postMessage;
        worker.postMessage=function(message,...rest) {
          if(armed&&message?.type==='request'&&message.method==='GET'&&message.path==='/api/state'){
            const row=current;
            if(row.id!==undefined)throw Error('More than one Worker request for a revision read');
            row.id=message.id;
            row.cacheToken=message.view_cache??null;
            pending.set(message.id,row);
            row.sent=performance.now();
          }
          return Reflect.apply(postMessage,this,[message,...rest]);
        };
        return worker;
      },
    });
  });
  return async ()=>{
    const rows=await page.evaluate(()=>globalThis.__tk2AllocationRevisionProbe.rows);
    if(rows.length!==8)throw Error('Expected eight independent revision replies');
    await writeFile(testInfo.outputPath('allocation-revision-ab.json'),JSON.stringify(rows));
  };
}
