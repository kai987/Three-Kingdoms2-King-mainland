/* Checked-list limits are presentation state only; no campaign or RNG writes. */
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 else root.GameOfficerSelection=api;
})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 const limitOf=value=>Number.isFinite(Number(value))?Math.max(0,Math.min(Number.MAX_SAFE_INTEGER,Math.floor(Number(value)))):0;
 function bind(inputs,{limit=inputs.length,onChange=()=>{},isEligible=()=>true}={}){
  const rows=[...inputs],permanent=new Set(rows.filter(input=>input.disabled));
  let maximum=limitOf(limit),order=[],lastSignature=null,notifying=false,pendingNotification=false;
  const eligible=input=>!permanent.has(input)&&!!isEligible(input);
  const id=input=>Number(input.value);
  const selectedIds=()=>rows.filter(input=>input.checked&&eligible(input)).map(id);
  const state=trimmed=>{const ids=selectedIds();return{ids,count:ids.length,limit:maximum,trimmedIds:[...trimmed]};};
  function notify(snapshot,signature){
   if(signature===lastSignature)return;
   lastSignature=signature;
   if(notifying){pendingNotification=true;return;}
   notifying=true;
   try{
    onChange(snapshot);
    // A destination change inside a callback may adjust the limit again. Notify
    // once more with the settled state, never recurse for an unchanged update.
    while(pendingNotification){pendingNotification=false;onChange(state([]));}
   }finally{notifying=false;}
  }
  function update(changed=null){
   const trimmed=[];
   for(const input of rows)if(input.checked&&!eligible(input)){input.checked=false;trimmed.push(id(input));}
   order=order.filter(input=>input.checked&&eligible(input));
   for(const input of rows)if(input!==changed&&input.checked&&eligible(input)&&!order.includes(input))order.push(input);
   if(changed?.checked&&eligible(changed)&&!order.includes(changed))order.push(changed);
   while(order.length>maximum){const input=order.pop();input.checked=false;trimmed.push(id(input));}
   const atLimit=order.length>=maximum;
   for(const input of rows)input.disabled=!eligible(input)||(!input.checked&&atLimit);
   const snapshot=state(trimmed),signature=JSON.stringify([snapshot.ids,maximum,rows.map(input=>input.disabled)]);
   notify(snapshot,signature);
   return snapshot;
  }
  for(const input of rows)input.addEventListener('change',()=>update(input));
  const controller={selectedIds,setLimit(value){maximum=limitOf(value);return update();},update:()=>update(),refresh:()=>update()};
  update();
  return Object.freeze(controller);
 }
 return Object.freeze({bind});
});
