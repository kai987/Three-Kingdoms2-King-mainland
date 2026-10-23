/* Pure route choices: merge mode aliases without enabling unknown sea routes. */
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 else root.GameRouteOptions=api;
})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 const knownModes=Object.freeze(['fastest','land','special','sea','river']);
 const valid=quote=>quote!==null&&typeof quote==='object';
 const number=value=>typeof value==='number'&&Number.isFinite(value)?value:Infinity;
 const stable=value=>Array.isArray(value)?value.map(stable):value!==null&&typeof value==='object'?
  Object.fromEntries(Object.keys(value).sort().map(key=>[key,stable(value[key])])):value;
 // Route identity is directional and ordered. The same cities can have both
 // ordinary roads and a distinct pass, so city paths alone cannot identify it.
 const identity=quote=>JSON.stringify([
  quote.path||[],
  (quote.routes||[]).map(leg=>[leg.id,leg.from,leg.to,leg.mode,leg.special,leg.terrain,
   leg.days,leg.distance_km,leg.land_km,leg.sea_km,leg.river_km,leg.flow,
   stable(leg.river_segments),leg.base_days,stable(leg.hazard)]),
  [quote.days,quote.turns,quote.distance_km,quote.river_km,quote.grain_per_officer]
 ]);
 function kind(quote){
  let land=(quote.modes||[]).includes('land'),sea=(quote.modes||[]).includes('sea'),
   river=(quote.modes||[]).includes('river')||quote.river_km>0;
  for(const leg of quote.routes||[]){
   land=land||leg.mode==='land'||leg.land_km>0;
   sea=sea||leg.mode==='sea'||leg.sea_km>0;
   river=river||leg.mode==='river'||leg.river_km>0;
  }
  return river?(sea?'river_sea':'river'):land&&sea?'mixed':sea?'sea':'land';
 }
 function decorate(groups){
  const counts={land:0,sea:0,mixed:0,river:0,river_sea:0},indexes={land:0,sea:0,mixed:0,river:0,river_sea:0};
  for(const group of groups)counts[kind(group.quote)]++;
  const shortest=groups.length?number(groups[0].quote.days):Infinity;
  return groups.map(group=>{
   const type=kind(group.quote);
   return {...group,kind:type,shortest:number(group.quote.days)===shortest,
    indexWithinKind:++indexes[type],kindCount:counts[type]};
  });
 }
 function build(quotesByMode,{preferred='fastest',exploring=false}={}){
  const quotes=quotesByMode||{},groups=[],byRoute=new Map();
  for(const mode of knownModes){
   const quote=quotes[mode];if(!valid(quote))continue;
   const key=identity(quote),existing=byRoute.get(key);
   if(existing){existing.aliases.push(mode);continue;}
   const group={mode,aliases:[mode],quote};groups.push(group);byRoute.set(key,group);
  }
  groups.sort((a,b)=>number(a.quote.days)-number(b.quote.days)||
   number(a.quote.distance_km)-number(b.quote.distance_km)||knownModes.indexOf(a.mode)-knownModes.indexOf(b.mode));
  const canExplore=valid(quotes.explore),active=exploring===true&&canExplore;
  const options=decorate(active?[{mode:'explore',aliases:['explore'],quote:quotes.explore}]:groups);
  const selected=options.find(option=>option.aliases.includes(preferred))||options[0];
  return {options,value:selected?.mode||'',knownCount:groups.length,canExplore,exploring:active};
 }
 return Object.freeze({build});
});
