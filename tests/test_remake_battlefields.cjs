'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const api=require('../game/battlefields.js');
const root=path.resolve(__dirname,'..'),bindings=JSON.parse(fs.readFileSync(path.join(root,'game/config/battlefield-city-bindings.json')));
const clone=value=>JSON.parse(JSON.stringify(value));
function library(){
 return {schema:api.LIBRARY_SCHEMA,grid:{columns:31,rows:19,tile_size:16,width:496,height:304},
  maps:Object.fromEntries(Object.entries(bindings.templates).map(([id,template])=>[id,{id,
   original_city_index:template.original_city_index,source_city_label:template.source_city_label,
   path:'/assets/battlefields/'+id+'.png',width:496,height:304,sha256:'a'.repeat(64),
   tiles:Array.from({length:19},(_,y)=>Array.from({length:31},(_,x)=>(x+y)%128)),
   classes:Array.from({length:19},(_,y)=>Array.from({length:31},(_,x)=>(x+y)%6)),
   provenance:{scope:'Synthetic selector test data; not original pixels'}}]))};
}
const response=value=>({ok:true,text:async()=>JSON.stringify(value)});
(async()=>{
 const maps=library(),before=JSON.stringify({maps,bindings});
 assert(api.validateLibrary(maps));assert(api.validateBindings(bindings));
 for(const [city,binding]of Object.entries(bindings.cities)){
  const result=api.select(city,maps,bindings);assert(result);assert.equal(result.field.id,binding.map_id);
  assert.equal(result.binding.kind,binding.kind);assert.equal(result.city_id,city);
  assert(result.label_tc&&result.label_ja);assert(Object.isFrozen(result.field.classes[0]));
  assert.throws(()=>{result.field.classes[0][0]=99;},TypeError);
 }
 assert.equal(JSON.stringify({maps,bindings}),before,'Selection must not write source data');
 assert.equal(api.select('unknown-city',maps,bindings),null);assert.equal(api.select('__proto__',maps,bindings),null);
 for(const change of [
  data=>{data.maps['original-00'].path='https://foreign.example/map.png';},
  data=>{data.maps['original-00'].path='/assets/battlefields/../private.png';},
  data=>{data.maps['original-00'].path+="?token=untrusted";},
  data=>{data.maps['original-00'].width=256;},
  data=>{data.maps['original-00'].tiles[0].pop();},
  data=>{data.maps['original-00'].classes[0][0]=6;},
  data=>{data.maps['original-00'].camps=[{x:-1,y:2}];},
  data=>{data.maps['original-00'].markers=[{x:2,y:19}];},
  data=>{data.maps['original-00'].sha256='z'.repeat(64);},
  data=>{data.maps['original-00'].original_city_index=1;},
  data=>{delete data.maps['original-29'];},
 ]){const bad=clone(maps);change(bad);assert.equal(api.validateLibrary(bad),false);assert.equal(api.select('liaodong',bad,bindings),null);}
 for(const change of [
  data=>{data.city_count++;},
  data=>{data.cities.liaodong.map_id='original-30';},
  data=>{data.cities.liaodong.kind='certified_historical_map';},
  data=>{data.cities.xihe.kind='direct_original';},
  data=>{data.cities.shujun.kind='direct_original';},
  data=>{data.templates['original-26'].identity_status='rom_name_verified';},
  data=>{delete data.cities.liaodong.reason_ja;},
  data=>{delete data.templates['original-29'];},
 ]){const bad=clone(bindings);change(bad);assert.equal(api.validateBindings(bad),false);assert.equal(api.select('liaodong',maps,bad),null);}
 const wrongLabel=clone(maps);wrongLabel.maps['original-27'].source_city_label='unverified correction';
 assert.equal(api.select('fuling',wrongLabel,bindings),null,'A label mismatch cannot silently certify a city association');
 const certified=clone(bindings);certified.templates['original-26'].identity_status='rom_name_verified';
 certified.templates['original-26'].identity_evidence='Synthetic reviewed-identity fixture, not production source evidence';
 certified.cities.shujun.kind='direct_original';assert.match(api.select('shujun',maps,certified).label_tc,/^原版成都戰場$/);
 const calls=[],client=api.create({asset:value=>'/project'+value,fetch:async(url,options)=>{
  calls.push({url,options});return response(url.endsWith('/index.json')?maps:bindings);
 }});
 assert.equal(client.status,'idle');assert.equal(client.resolve('wuling'),null);
 const first=client.load(),again=client.load();assert.strictEqual(first,again);assert.equal(calls.length,2,'Both metadata reads start together');
 await first;assert.equal(client.status,'ready');assert.equal(calls.length,2);
 for(let i=0;i<30;i++){const id='original-'+String(i).padStart(2,'0'),field=client.resolveMap(id);assert.equal(field.field.id,id);assert(Object.isFrozen(field));assert.equal(field.grid.columns,31);}
 assert.equal(client.resolveMap('original-30'),null);assert.equal(client.resolveMap('../original-01'),null);
 assert.deepEqual(calls.map(row=>row.url).sort(),['/project'+api.INDEX,'/project'+api.BINDINGS].sort());
 assert(calls.every(row=>row.options.credentials==='same-origin'&&row.options.cache==='no-cache'));
 assert(!calls.some(row=>row.url.endsWith('.png')),'Loading the registry must not preload 30 maps');
 const originalRandom=Math.random;Math.random=()=>{throw Error('Map selection must not sample random state');};
 try{
  const view={game:{battle:{target:'wuling',attackers:[{id:1}]},rng:{state:2026,draws:0}}};
  let snapshot=JSON.stringify(view),selected=client.resolve(view.game.battle.target);assert(selected);
  assert.equal(JSON.stringify(view),snapshot);
  view.game.battle.attackers.push({id:'clerk-000001'});snapshot=JSON.stringify(view);
  assert.strictEqual(client.resolve(view.game.battle.target),selected,'Adding a clerk cannot change the city map');
  assert.equal(JSON.stringify(view),snapshot);
  assert.match(client.label('wuling','zh-Hant'),/區域沿用/);assert.match(client.label('wuling','ja'),/地域共用/);
  assert.match(client.label('shujun','zh-Hant'),/同名參照/);assert.match(client.label('shujun','ja'),/同名参照/);
  assert(!client.label('xihe').includes('西安阳'),'Unresolved guide labels use city-number badges');
  assert.equal(client.label('missing'),'');assert.equal(client.description('missing'),'');
  assert.deepEqual(view.game.rng,{state:2026,draws:0});
 }finally{Math.random=originalRandom;}
 maps.maps['original-00'].classes[0][0]=5;
 assert.equal(client.resolve('liaodong').field.classes[0][0],0,'Validated state owns a frozen copy');
 assert.equal(calls.length,2,'Locale and selection changes never reload images or metadata');
 for(const mode of ['http','json','size','shape','label']){
  const requests=[];const broken=api.create({fetch:async url=>{
   requests.push(url);
   if(mode==='http')return {ok:false,text:async()=>''};
   if(mode==='json')return {ok:true,text:async()=>'{broken'};
   if(mode==='size')return {ok:true,text:async()=>' '.repeat(2_000_001)};
   const value=url===api.INDEX?library():clone(bindings);
   if(mode==='shape'&&url===api.INDEX)value.grid.columns=16;
   if(mode==='label'&&url===api.INDEX)value.maps['original-00'].source_city_label='different';
   return response(value);
  }});
  assert.equal(await broken.load(),null);assert.equal(broken.status,'unavailable');assert.equal(broken.resolve('liaodong'),null);
  assert.equal(await broken.load(),null);assert.equal(requests.length,2,'Failure keeps a bounded single load without retry storms');
 }
 const signals=[],stalled=api.create({timeoutMs:10,fetch:(_url,options)=>{signals.push(options.signal);return new Promise(()=>{});}});
 assert.equal(await stalled.load(),null,'A stalled network must release battle playback to the retained fallback');
 assert.equal(stalled.status,'unavailable');
 await new Promise(resolve=>setTimeout(resolve,15));
 assert(signals.every(signal=>signal?.aborted),'Timed-out metadata requests must be aborted');
 console.log('battlefield bindings:115 explicit city choices, honest source labels, full-grid/path validation, immutable deterministic selection, two metadata reads/no image preload, bilingual labels and bounded failure passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
