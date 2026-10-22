/* Novel-based presentation only. This registry never grants equipment, changes
 * battle statistics, writes a save, or consumes the campaign random stream. */
'use strict';
(function(root){
 const INDEX='/config/duel-appearances.json';
 const WEAPONS=Object.freeze(['spear','serpent-spear','guandao','halberd','sword','dual-swords','axe','dual-axes','dual-ji']);
 const HORSES=Object.freeze(['chestnut','white','black','red-hare','dilu']);
 const LABELS=Object.freeze({
  spear:['長槍','槍'], 'serpent-spear':['丈八蛇矛','丈八蛇矛'], guandao:['大刀','大刀'], halberd:['方天畫戟','方天画戟'],
  sword:['劍','剣'], 'dual-swords':['雙劍','双剣'], axe:['大斧','大斧'], 'dual-axes':['雙斧','双斧'], 'dual-ji':['雙鐵戟','双鉄戟'],
  chestnut:['棗紅馬','栗毛'], white:['白馬','白馬'], black:['黑馬','黒馬'], 'red-hare':['赤兔馬','赤兎馬'], dilu:['的盧馬','的盧']
 });
 const labels=(value,key)=>Object.freeze({'zh-Hant':typeof value?.['zh-Hant']==='string'?value['zh-Hant']:LABELS[key][0],ja:typeof value?.ja==='string'?value.ja:LABELS[key][1]});
 const personPattern=/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
 function validate(data){
  if(!data||data.schema!=='tk2-duel-appearances-v1'||!data.profiles||typeof data.profiles!=='object'||Array.isArray(data.profiles)||Object.keys(data.profiles).length>1200)throw Error('Invalid duel appearance registry');
  const profiles=Object.create(null);
  for(const[id,row]of Object.entries(data.profiles)){
   if(!personPattern.test(id)||!row||!WEAPONS.includes(row.weapon)||!HORSES.includes(row.horse))throw Error('Invalid duel appearance profile');
   for(const field of ['weapon_label','horse_label'])if(row[field]&&['zh-Hant','ja'].some(lang=>typeof row[field][lang]!=='string'||row[field][lang].length>40))throw Error('Invalid duel appearance label');
   profiles[id]=Object.freeze({person_id:id,name:typeof row.name==='string'?row.name:'',weapon:row.weapon,horse:row.horse,weapon_label:labels(row.weapon_label,row.weapon),horse_label:labels(row.horse_label,row.horse),documented:true});
  }
  return Object.freeze(profiles);
 }
 // A stable identity hash is solely an art selector, not a new game RNG draw.
 function identityHash(value){let n=2166136261;for(const c of String(value)){n^=c.codePointAt(0);n=Math.imul(n,16777619)>>>0;}return n;}
 function create(options={}){
  const fetcher=options.fetch||root.fetch?.bind(root),maps=new WeakMap();let profiles=Object.create(null),pending=null,status='idle';
  const timeoutMs=Number.isFinite(options.timeoutMs)&&options.timeoutMs>0?options.timeoutMs:6000;
  function personId(catalog,id){
   if(typeof id==='string'&&/^clerk-[0-9]{6,12}$/.test(id))return id;
   if(!catalog||typeof catalog!=='object'||!Array.isArray(catalog.library))return null;
   let map=maps.get(catalog);if(!map){map=new Map(catalog.library.filter(p=>p&&personPattern.test(p.person_id||'')).map(p=>[String(p.id),p.person_id]));maps.set(catalog,map);}
   return map.get(String(id))||null;
  }
  function profile(catalog,id){
   const person=personId(catalog,id),known=person&&profiles[person];if(known)return known;
   const hash=identityHash(person||'runtime:'+String(id)),weapon=['spear','sword','axe','dual-axes'][hash%4],horse=['chestnut','white','black'][(hash>>>4)%3];
   return Object.freeze({person_id:person,name:'',weapon,horse,weapon_label:labels(null,weapon),horse_label:labels(null,horse),documented:false});
  }
  async function load(){
   if(pending)return pending;status='loading';
   pending=(async()=>{let timer;const controller=typeof AbortController==='function'?new AbortController():null;
    try{
     const read=(async()=>{const response=await fetcher(INDEX,controller?{signal:controller.signal}:{});if(!response.ok)throw Error('Appearance registry unavailable');return response.json();})();
     const data=await Promise.race([read,new Promise((_,reject)=>{timer=setTimeout(()=>{controller?.abort();reject(Error('timeout'));},timeoutMs);})]);
     profiles=validate(data);status='ready';
    }catch{status='unavailable';}finally{clearTimeout(timer);}return status==='ready';
   })();return pending;
  }
  return Object.freeze({load,profile,personId,get status(){return status;}});
 }
 const api={INDEX,WEAPONS,HORSES,validate,identityHash,create};
 if(typeof module==='object'&&module.exports)module.exports=api;
 else{const instance=create();root.GameDuelAppearance=Object.freeze({...api,load:instance.load,profile:instance.profile,personId:instance.personId,get status(){return instance.status;}});}
})(typeof window==='object'?window:globalThis);
