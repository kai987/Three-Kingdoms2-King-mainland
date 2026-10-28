/* Read-only original-map selection. Art provenance never changes combat state. */
'use strict';
(function(root){
 const LIBRARY_SCHEMA='tk2-original-battlefields-v1',BINDINGS_SCHEMA='tk2-battlefield-city-bindings-v1';
 const INDEX='/assets/battlefields/index.json',BINDINGS='/config/battlefield-city-bindings.json';
 const WIDTH=496,HEIGHT=304,COLUMNS=31,ROWS=19,TILE=16,MAX_TEXT=2_000_000;
 const KINDS=new Set(['direct_original','same_label_association','regional_reuse']);
 const STATUSES=new Set(['city_or_commandery_label','regional_label','unresolved_source_label','rom_name_verified']);
 const record=value=>!!value&&typeof value==='object'&&!Array.isArray(value)&&(Object.getPrototypeOf(value)===Object.prototype||Object.getPrototypeOf(value)===null);
 const text=(value,max)=>typeof value==='string'&&value.length>0&&value.length<=max;
 const mapId=value=>typeof value==='string'&&/^original-(?:[0-2][0-9])$/.test(value);
 const cityId=value=>typeof value==='string'&&/^[a-z][a-z0-9_-]{0,47}$/.test(value);
 const hash=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
 const number=(value,max)=>Number.isInteger(value)&&value>=0&&value<=max;
 function grid(value){return record(value)&&value.columns===COLUMNS&&value.rows===ROWS&&value.tile_size===TILE&&value.width===WIDTH&&value.height===HEIGHT;}
 function matrix(value,max){return Array.isArray(value)&&value.length===ROWS&&value.every(row=>Array.isArray(row)&&row.length===COLUMNS&&row.every(cell=>number(cell,max)));}
 function positions(value){return Array.isArray(value)&&value.length<=32&&value.every(row=>record(row)&&number(row.x,COLUMNS-1)&&number(row.y,ROWS-1));}
 function validateLibrary(value){
  if(!record(value)||value.schema!==LIBRARY_SCHEMA||!grid(value.grid)||!record(value.maps)||Object.keys(value.maps).length!==30)return false;
  return Array.from({length:30},(_,index)=>{
   const id='original-'+String(index).padStart(2,'0'),row=value.maps[id];
   return record(row)&&row.id===id&&row.original_city_index===index&&text(row.source_city_label,80)
    &&row.path==='/assets/battlefields/'+id+'.png'&&row.width===WIDTH&&row.height===HEIGHT&&hash(row.sha256)
    &&matrix(row.tiles,127)&&matrix(row.classes,5)
    &&(row.camps===undefined||positions(row.camps))&&(row.markers===undefined||positions(row.markers));
  }).every(Boolean);
 }
 function validateBindings(value){
  if(!record(value)||value.schema!==BINDINGS_SCHEMA||value.library_schema!==LIBRARY_SCHEMA
    ||!record(value.templates)||Object.keys(value.templates).length!==30||!record(value.cities)
    ||!number(value.city_count,512)||value.city_count<1||Object.keys(value.cities).length!==value.city_count
    ||value.original_map_count!==30)return false;
  for(let index=0;index<30;index++){
   const id='original-'+String(index).padStart(2,'0'),row=value.templates[id];
   if(!record(row)||row.original_city_index!==index||!text(row.source_city_label,80)
     ||!text(row.display_tc,80)||!text(row.display_ja,80)||!STATUSES.has(row.identity_status)
     ||row.identity_status==='rom_name_verified'&&!text(row.identity_evidence,1200))return false;
  }
  return Object.entries(value.cities).every(([id,row])=>cityId(id)&&record(row)&&mapId(row.map_id)&&KINDS.has(row.kind)
    &&text(row.reason_tc,1200)&&text(row.reason_ja,1200)
    &&(row.kind!=='direct_original'||value.templates[row.map_id].identity_status==='rom_name_verified'));
 }
 function matching(library,bindings){
  return Object.entries(bindings.templates).every(([id,row])=>row.source_city_label===library.maps[id].source_city_label);
 }
 function freeze(value){
  if(value&&typeof value==='object'&&!Object.isFrozen(value)){Object.freeze(value);for(const child of Object.values(value))freeze(child);}
  return value;
 }
 function copied(value){return JSON.parse(JSON.stringify(value));}
 function selected(city,library,bindings){
  const binding=bindings.cities[city];if(!binding)return null;
  const field=library.maps[binding.map_id],template=bindings.templates[binding.map_id];
  const original_tc=(template.display_tc.startsWith('原版')?'':'原版')+template.display_tc+'戰場';
  const original_ja=(template.display_ja.startsWith('原作')?'':'原作')+template.display_ja+'の戦場';
  const label_tc=binding.kind==='direct_original'?original_tc:(binding.kind==='same_label_association'?'同名參照・':'區域沿用・')+original_tc;
  const label_ja=binding.kind==='direct_original'?original_ja:(binding.kind==='same_label_association'?'同名参照・':'地域共用・')+original_ja;
  return Object.freeze({field,binding,grid:library.grid,city_id:city,label_tc,label_ja,
   description_tc:binding.reason_tc,description_ja:binding.reason_ja});
 }
 function select(city,library,bindings){
  if(!cityId(city)||!validateLibrary(library)||!validateBindings(bindings)||!matching(library,bindings))return null;
  try{return freeze(copied(selected(city,library,bindings)));}catch{return null;}
 }
 function create(options={}){
  const fetcher=options.fetch||(typeof root?.fetch==='function'?root.fetch.bind(root):null),asset=options.asset||(value=>root?.GamePaths?.asset(value)||value);
  const timeout=Number.isInteger(options.timeoutMs)&&options.timeoutMs>0?Math.min(options.timeoutMs,6000):6000;
  let library=null,bindings=null,pending=null,status='idle';const resolved=new Map();
  async function read(path){
   if(!fetcher)throw Error('No manifest reader');
   let timer;const controller=typeof AbortController==='function'?new AbortController():null;
   try{
    const request=(async()=>{
     const response=await fetcher(asset(path),{credentials:'same-origin',cache:'no-cache',...(controller?{signal:controller.signal}:{})});
     if(!response?.ok)throw Error('Unavailable battlefield metadata');
     const raw=await response.text();if(typeof raw!=='string'||raw.length>MAX_TEXT)throw Error('Oversized battlefield metadata');
     return JSON.parse(raw);
    })();
    return await Promise.race([request,new Promise((_,reject)=>{timer=setTimeout(()=>{controller?.abort();reject(Error('Battlefield metadata timeout'));},timeout);})]);
   }finally{clearTimeout(timer);}
  }
  function load(){
   if(pending)return pending;
   status='loading';pending=(async()=>{
    try{
     const [maps,choices]=await Promise.all([read(INDEX),read(BINDINGS)]);
     if(!validateLibrary(maps)||!validateBindings(choices)||!matching(maps,choices))throw Error('Invalid battlefield metadata');
     library=freeze(copied(maps));bindings=freeze(copied(choices));status='ready';return library;
    }catch{status='unavailable';library=bindings=null;resolved.clear();return null;}
   })();return pending;
  }
  function resolve(city){
   if(!cityId(city)||status!=='ready'||!Object.hasOwn(bindings.cities,city))return null;
   if(!resolved.has(city))resolved.set(city,selected(city,library,bindings));return resolved.get(city);
  }
  function resolveMap(id){
   if(!mapId(id)||status!=='ready')return null;
   const field=library.maps[id],template=bindings.templates[id];
   return Object.freeze({field,grid:library.grid,label_tc:'原版'+template.display_tc.replace(/^原版/,'')+'戰場',label_ja:'原作'+template.display_ja.replace(/^原作/,'')+'の戦場'});
  }
  const client={load,resolve,resolveMap,label(city,locale='zh-Hant'){const row=resolve(city);return row?(locale==='ja'?row.label_ja:row.label_tc):'';},
   description(city,locale='zh-Hant'){const row=resolve(city);return row?(locale==='ja'?row.description_ja:row.description_tc):'';},
   get status(){return status;},get library(){return library;},get bindings(){return bindings;}};
  return Object.freeze(client);
 }
 const client=create(),api={LIBRARY_SCHEMA,BINDINGS_SCHEMA,INDEX,BINDINGS,WIDTH,HEIGHT,COLUMNS,ROWS,TILE,
  validateLibrary,validateBindings,select,create,load:client.load,resolve:client.resolve,resolveMap:client.resolveMap,label:client.label,description:client.description,
  get status(){return client.status;},get library(){return client.library;},get bindings(){return client.bindings;}};
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root)root.GameBattlefields=Object.freeze(api);
})(typeof window==='object'?window:null);
