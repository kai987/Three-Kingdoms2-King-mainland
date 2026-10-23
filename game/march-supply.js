/* Read-only counterpart of source/remake/march_supply.py. */
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameMarchSupply=api;
})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 function requiredGrain(troops,officers,days,reserves=0){
  if([troops,officers,days,reserves].some(n=>!Number.isSafeInteger(n)||n<0))throw new TypeError('Invalid march supply');
  const units=troops+100*officers+reserves,value=units*days;
  if(!Number.isSafeInteger(value+999))throw new RangeError('March supply too large');
  return Math.floor((value+999)/1000);
 }
 function estimate(people,ids,quote,reserves=0){
  return requiredGrain(ids.reduce((sum,id)=>sum+(people[id]?.troops||0),0),ids.length,quote.days,reserves);
 }
 return Object.freeze({requiredGrain,estimate});
});
