/* Read-only counterpart of source/remake/march_supply.py. */
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameMarchSupply=api;
})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 const RATION_DENOMINATOR=50,OFFICER_UNITS=100;
 function requiredGrain(troops,officers,days,reserves=0,denominator=RATION_DENOMINATOR){
  if([troops,officers,days,reserves].some(n=>!Number.isSafeInteger(n)||n<0))throw new TypeError('Invalid march supply');
  const units=troops+OFFICER_UNITS*officers+reserves,value=units*days;
  if(!Number.isSafeInteger(value+denominator-1))throw new RangeError('March supply too large');
  return Math.floor((value+denominator-1)/denominator);
 }
 const troopCount=(people,ids)=>ids.reduce((sum,id)=>sum+(people[id]?.troops||0),0);
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
 function estimate(people,ids,quote,reserves=0,cities=null,owner=null,denominator=RATION_DENOMINATOR){
  return quote.logistics?.initial_grain??requiredGrain(troopCount(people,ids),ids.length,initialDays(quote,cities,owner),reserves,denominator);
 }
 function refillForecast(people,ids,quote,loaded,cities,owner,denominator=RATION_DENOMINATOR){
  if(!ids.length||!Array.isArray(quote?.routes)||!Array.isArray(quote?.path))return [];
  if(quote.logistics?.refills)return quote.logistics.refills;
  const stops=[{city:quote.path[0],day:0}];
  let day=0;
  for(const [index,leg] of quote.routes.entries()){
   day+=leg.days;
   const city=quote.path[index+1];
   if(cities[city]?.owner===owner||index===quote.routes.length-1)stops.push({city,day});
  }
  const units=troopCount(people,ids)+OFFICER_UNITS*ids.length;
  const rows=[];
  let available=loaded*denominator,conditional=false;
  for(let index=0;index<stops.length-1;index++){
   const here=stops[index],destination=stops[index+1],days=destination.day-here.day,needed=units*days;
   if(index>0){
    const required=Math.max(0,Math.ceil((needed-available)/denominator));
    const stock=cities[here.city].grain,shortfall=Math.max(0,required-stock);
    rows.push({city:here.city,next:destination.city,days,stock,required,shortfall,conditional});
    // Later stops remain useful as a forecast once earlier gaps are covered.
    available+=required*denominator;
    conditional=conditional||shortfall>0;
   }
   // Grain and the engine's fractional credit share this scaled balance.
   available-=needed;
  }
  return rows;
 }
 function position(quote,routeDays=0){
  const path=quote?.path||[],routes=quote?.routes||[],total=quote?.days||0;
  let elapsed=Math.max(0,Math.min(total,Number.isFinite(routeDays)?routeDays:0));
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
 return Object.freeze({requiredGrain,initialDays,estimate,refillForecast,position,nextStop});
});
