/* Pure presentation rules for officer choices. No game state or RNG writes. */
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 else root.GameOfficerChoices=api;
})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 const orders=Object.freeze({
  martial_strength:Object.freeze(['martial_strength','intellect','virtue','health','experience','troops']),
  virtue:Object.freeze(['virtue','intellect','martial_strength','health','experience','troops'])
 });
 const numeric=value=>typeof value==='number'&&Number.isFinite(value)?value:-1;
 const display=value=>typeof value==='number'&&Number.isFinite(value)?String(value):'—';
 const stat=(officer,key)=>numeric(['health','experience','troops'].includes(key)?officer?.[key]:officer?.profile?.[key]);
 // The original information screen shows the raw experience counter / 50.
 const experience=value=>Number.isInteger(value)&&value>=0&&value<=49999?Math.floor(value/50):'—';
 function stableId(a,b){
  const first=Number(a),second=Number(b);
  if(Number.isSafeInteger(first)&&Number.isSafeInteger(second)&&first!==second)return first-second;
  return String(a)<String(b)?-1:String(a)>String(b)?1:0;
 }
 function sort(ids,getOfficer,primary='martial_strength'){
  if(!Object.hasOwn(orders,primary))throw new RangeError('Unsupported officer choice order');
  if(typeof getOfficer!=='function')throw new TypeError('Officer resolver is required');
  // Snapshot once per ID so every comparison reads the same displayed values.
  const fields=orders[primary];
  return [...ids].map(id=>{const officer=getOfficer(id);return{id,values:fields.map(field=>stat(officer,field))};}).sort((a,b)=>{
   for(let index=0;index<fields.length;index++){
    const difference=b.values[index]-a.values[index];
    if(difference)return difference;
   }
   return stableId(a.id,b.id);
  }).map(row=>row.id);
 }
 // Returns plain text. The rendering caller escapes it when inserting HTML.
 function label(name,officer,{troops=officer?.troops,health=officer?.health,loyalty=false}={}){
  const profile=officer?.profile;
  return `${name} · ${display(troops)}兵 · 武${display(profile?.martial_strength)} · 知${display(profile?.intellect)} · 德${display(profile?.virtue)} · 体力${display(health)} · 经验${experience(officer?.experience)}${loyalty?` · 忠誠${display(officer?.loyalty)}`:''}`;
 }
 return Object.freeze({label,sort,experience});
});
