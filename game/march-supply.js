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
 function initialDays(quote,cities=null,owner=null){
  if(!quote||!Number.isSafeInteger(quote.days)||quote.days<0)throw new TypeError('Invalid march duration');
  if(!cities||owner===null||!Array.isArray(quote.routes)||!Array.isArray(quote.path))return quote.days;
  let days=0;
  for(let index=0;index<quote.routes.length;index++){
   const leg=quote.routes[index];
   if(!Number.isSafeInteger(leg.days)||leg.days<0)throw new TypeError('Invalid march leg');
   days+=leg.days;
   if(cities[quote.path[index+1]]?.owner===owner)return days;
  }
  return quote.days;
 }
 function estimate(people,ids,quote,reserves=0,cities=null,owner=null){
  return requiredGrain(ids.reduce((sum,id)=>sum+(people[id]?.troops||0),0),ids.length,initialDays(quote,cities,owner),reserves);
 }
 function position(quote,routeDays=0){
  const path=quote?.path||[],routes=quote?.routes||[],total=quote?.days||0;
  let elapsed=Math.max(0,Math.min(total,Number.isSafeInteger(routeDays)?routeDays:0));
  if(!routes.length||!path.length)return {city:null,from:null,to:null,progress_days:elapsed,leg_days:total,arrived:elapsed>=total};
  if(elapsed===0)return {city:path[0],from:path[0],to:path[1]??null,progress_days:0,leg_days:routes[0].days,arrived:false};
  for(let index=0;index<routes.length;index++){
   const days=routes[index].days;
   if(elapsed<days)return {city:null,from:path[index],to:path[index+1],progress_days:elapsed,leg_days:days,arrived:false};
   elapsed-=days;
   if(elapsed===0)return {city:path[index+1],from:path[index+1],to:path[index+2]??null,progress_days:0,leg_days:routes[index+1]?.days??0,arrived:index===routes.length-1};
  }
  return {city:path.at(-1),from:path.at(-1),to:null,progress_days:0,leg_days:0,arrived:true};
 }
 function nextStop(quote,routeDays=0,cities=null,owner=null){
  if(!cities||owner===null||!Array.isArray(quote?.routes)||!Array.isArray(quote?.path))return null;
  let days=0;
  for(let index=0;index<quote.routes.length;index++){
   days+=quote.routes[index].days;
   const city=quote.path[index+1];
   if(days>=routeDays&&cities[city]?.owner===owner)return {city,days:Math.max(0,days-routeDays)};
  }
  return null;
 }
 return Object.freeze({requiredGrain,initialDays,estimate,position,nextStop});
});
