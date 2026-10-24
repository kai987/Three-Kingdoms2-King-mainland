/* Horse art follows the novel registry; weapons follow authoritative equipment.
 * Rendering never grants items, changes a save or consumes campaign RNG. */
'use strict';
(function(root){
 const INDEX='/config/duel-appearances.json';
 const WEAPONS=Object.freeze(['spear','serpent-spear','guandao','halberd','sword','dual-swords','axe','dual-axes','dual-ji','guding-dao','ring-dao','bow']);
 const HORSES=Object.freeze(['chestnut','white','black','red-hare','dilu','jueying','zhuahuang-feidian','huiying','liaoyuanhuo','lifeisha','kuaihang','jingfan','zhaoye-yushizi']);
 const LABELS=Object.freeze({
  spear:['長槍','槍'], 'serpent-spear':['丈八蛇矛','丈八蛇矛'], guandao:['大刀','大刀'], halberd:['方天畫戟','方天画戟'],
  sword:['劍','剣'], 'dual-swords':['雙劍','双剣'], axe:['大斧','大斧'], 'dual-axes':['雙斧','双斧'], 'dual-ji':['雙鐵戟','双鉄戟'],
  'guding-dao':['古錠刀','古錠刀'],'ring-dao':['九環刀','九環刀'],bow:['二石鐵胎弓','二石鉄胎弓'],
  chestnut:['棗紅馬','栗毛'], white:['白馬','白馬'], black:['黑馬','黒馬'], 'red-hare':['赤兔馬','赤兎馬'], dilu:['的盧馬','的盧'],
  jueying:['絕影','絶影'],'zhuahuang-feidian':['爪黃飛電','爪黄飛電'],huiying:['灰影','灰影'],liaoyuanhuo:['燎原火','燎原火'],lifeisha:['里飛沙','里飛沙'],kuaihang:['快航','快航'],jingfan:['驚帆','驚帆'],'zhaoye-yushizi':['照夜玉獅子','照夜玉獅子']
 });
 const labels=(value,key)=>Object.freeze({'zh-Hant':typeof value?.['zh-Hant']==='string'?value['zh-Hant']:LABELS[key][0],ja:typeof value?.ja==='string'?value.ja:LABELS[key][1]});
 const personPattern=/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/;
 function variants(rows,key,label,allowed){
  if(rows!==undefined&&(!Array.isArray(rows)||rows.length>16))throw Error('Invalid duel appearance variants');
  const seen=new Set(),result=[Object.freeze({key,label})];
  for(const row of rows||[]){
   if(!row||!allowed.includes(row.key)||seen.has(row.key)||!row.label||['zh-Hant','ja'].some(lang=>typeof row.label[lang]!=='string'||!row.label[lang].length||row.label[lang].length>40))throw Error('Invalid duel appearance variant');
   seen.add(row.key);if(row.key!==key)result.push(Object.freeze({key:row.key,label:labels(row.label,row.key)}));
  }
  return Object.freeze(result);
 }
 function select(profile,selection){
  if(selection===undefined||selection===null)return profile;
  if(typeof selection!=='object'||Array.isArray(selection)||Object.keys(selection).some(k=>!['weapon','horse'].includes(k)))throw Error('Invalid duel appearance selection');
  const weapon=profile.weapon_variants.find(v=>v.key===(selection.weapon??profile.weapon)),horse=profile.horse_variants.find(v=>v.key===(selection.horse??profile.horse));
  if(!weapon||!horse)throw Error('Unavailable duel appearance variant');
  return Object.freeze({...profile,weapon:weapon.key,horse:horse.key,weapon_label:weapon.label,horse_label:horse.label});
 }
 function validate(data){
  if(!data||data.schema!=='tk2-duel-appearances-v1'||!data.profiles||typeof data.profiles!=='object'||Array.isArray(data.profiles)||Object.keys(data.profiles).length>1200)throw Error('Invalid duel appearance registry');
  const profiles=Object.create(null);
  for(const[id,row]of Object.entries(data.profiles)){
   if(!personPattern.test(id)||!row||!WEAPONS.includes(row.weapon)||!HORSES.includes(row.horse))throw Error('Invalid duel appearance profile');
   for(const field of ['weapon_label','horse_label'])if(row[field]&&['zh-Hant','ja'].some(lang=>typeof row[field][lang]!=='string'||row[field][lang].length>40))throw Error('Invalid duel appearance label');
   const weaponLabel=labels(row.weapon_label,row.weapon),horseLabel=labels(row.horse_label,row.horse);
   profiles[id]=Object.freeze({person_id:id,name:typeof row.name==='string'?row.name:'',weapon:row.weapon,horse:row.horse,weapon_label:weaponLabel,horse_label:horseLabel,weapon_variants:variants(row.weapon_variants,row.weapon,weaponLabel,WEAPONS),horse_variants:variants(row.horse_variants,row.horse,horseLabel,HORSES),documented:true});
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
  function profile(catalog,id,selection){
   const person=personId(catalog,id),known=person&&profiles[person];
   const hash=identityHash(person||'runtime:'+String(id)),weapon=['spear','sword','axe','dual-axes'][hash%4],horse=['chestnut','white','black'][(hash>>>4)%3];
   const weaponLabel=labels(null,weapon),horseLabel=labels(null,horse);
   const base=known||Object.freeze({person_id:person,name:'',weapon,horse,weapon_label:weaponLabel,horse_label:horseLabel,weapon_variants:variants(undefined,weapon,weaponLabel,WEAPONS),horse_variants:variants(undefined,horse,horseLabel,HORSES),documented:false});
   const actual=catalog?.equipment?.officers?.[String(id)]?.weapon;
   if(!actual)return select(base,selection);
   const kind=WEAPONS.includes(actual.appearance)?actual.appearance:actual.family==='sword'?'sword':actual.family==='blade'?'guandao':'spear';
   const actualLabel=Object.freeze({'zh-Hant':actual.name_tc,ja:actual.name_ja});
   const chosen=select(base,selection?{horse:selection.horse??base.horse}:undefined);
   return Object.freeze({...chosen,weapon:kind,weapon_label:actualLabel,weapon_variants:Object.freeze([Object.freeze({key:kind,label:actualLabel})]),physical_equipment:true});
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
 const api={INDEX,WEAPONS,HORSES,validate,select,identityHash,create};
 if(typeof module==='object'&&module.exports)module.exports=api;
 else{const instance=create();root.GameDuelAppearance=Object.freeze({...api,load:instance.load,profile:instance.profile,personId:instance.personId,get status(){return instance.status;}});}
})(typeof window==='object'?window:globalThis);
