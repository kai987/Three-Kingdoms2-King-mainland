/* Presentation adapter; the server remains authoritative for commands/saves. */
'use strict';
(function(root){
 const geometryKey=view=>view.catalog.travel_rules.geometry_sha256||'';
 const stateKey=view=>view?.game&&view.catalog?.travel_rules?JSON.stringify([view.catalog.scenario_id,geometryKey(view),view.revision,view.game.player]):null;
 function createMarchCore({workerFactory=()=>new Worker(root.GamePaths?.asset('/march-worker.js')||'/march-worker.js'),fetcher=(...args)=>fetch(...args),timeout=30000}={}){
  let worker=null,failed=false,sequence=0,key=null,quotes=null,pendingUpdate=null,engine='idle',lastError=null;
  const requests=new Map(),contexts=new Map(),subscribers=new Set();
  function stop(error){
   failed=true;engine='fallback';lastError=String(error?.message||error);quotes=null;
   worker?.terminate();worker=null;
   for(const request of requests.values()){clearTimeout(request.timer);request.reject(error);}
   requests.clear();
  }
  function call(request){
   if(failed)return Promise.reject(new Error(lastError||'March worker unavailable'));
   try{
    if(!worker){
     worker=workerFactory();
     worker.onmessage=event=>{
      const result=event.data||{},pending=requests.get(result.id);if(!pending)return;
      requests.delete(result.id);clearTimeout(pending.timer);
      if(result.ok===true)pending.resolve(result.value);else pending.reject(new Error(result.error||'March calculation failed'));
     };
     worker.onerror=()=>stop(new Error('March worker unavailable'));
     worker.onmessageerror=()=>stop(new Error('March worker message failed'));
    }
    return new Promise((resolve,reject)=>{
     const id=++sequence,timer=setTimeout(()=>stop(new Error('March calculation timed out')),timeout);
     requests.set(id,{resolve,reject,timer});
     try{worker.postMessage({id,request});}catch(error){stop(error);}
    });
   }catch(error){stop(error);return Promise.reject(error);}
  }
  function context(scenario,geometry){
   const graphKey=JSON.stringify([scenario,geometry]);
   if(contexts.has(graphKey)){
    const cached=contexts.get(graphKey);contexts.delete(graphKey);contexts.set(graphKey,cached);return cached;
   }
   let pending;
   pending=(async()=>{
    const response=await fetcher('/api/march-config?scenario='+encodeURIComponent(scenario));
    if(!response.ok)throw new Error('March configuration unavailable');
    const configuration=await response.json();
    if(contexts.get(graphKey)!==pending)return null;
    return call({op:'register',data:configuration.data||configuration});
   })();
   contexts.set(graphKey,pending);
   // A campaign browser may visit many scenarios. Retain eight immutable
   // graphs. Evicted fetches skip registration; registrations already sent
   // release their own ID even if the scenario has since been opened again.
   while(contexts.size>8){
    const oldest=contexts.keys().next().value,retired=contexts.get(oldest);contexts.delete(oldest);
    retired.then(id=>id===null?null:call({op:'unregister',context:id})).catch(()=>{});
   }
   return pending;
  }
  function update(view){
   const next=stateKey(view);
   if(next===key)return pendingUpdate||Promise.resolve();
   key=next;quotes=null;
   if(!next){engine=failed?'fallback':'idle';return Promise.resolve();}
   if(failed)return Promise.resolve();
   engine='loading';
   const snapshot={scenario:view.catalog.scenario_id,geometry:geometryKey(view),cities:Object.values(view.game.cities).map(({id,owner})=>({id,owner})),month:view.game.month,discovered:[...(view.game.extension?.travel?.discovered||[])],player:view.game.player};
   pendingUpdate=(async()=>{
    try{
     const contextId=await context(snapshot.scenario,snapshot.geometry);
     if(key!==next)return;
     const result=await call({op:'batch',context:contextId,cities:snapshot.cities,month:snapshot.month,discovered:snapshot.discovered,player:snapshot.player});
     if(key!==next)return;
     quotes=result;engine='wasm';
     for(const notify of subscribers)notify();
    }catch(error){stop(error);}
   })();
   return pendingUpdate;
  }
  async function survivalPreview(view,quote,troops){
   const current=stateKey(view);
   if(!quote||failed||current!==key||quotes===null)return null;
   try{
    const result=await call({op:'survival_preview',quote,troops:[...troops]});
    return key===current?result:null;
   }catch(error){stop(error);return null;}
  }
  return {update,quotesFor:view=>stateKey(view)===key?quotes:null,survivalPreview,subscribe:notify=>{subscribers.add(notify);return()=>subscribers.delete(notify);},get status(){return{engine,key,error:lastError,contexts:contexts.size};}};
 }
 if(typeof module==='object'&&module.exports)module.exports={createMarchCore,stateKey};
 else root.MarchCore=createMarchCore();
})(typeof window==='object'?window:globalThis);
