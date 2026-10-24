'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const ROOT=path.resolve(__dirname,'..'),api=require('../game/duel-appearance.js');
const registry=JSON.parse(fs.readFileSync(path.join(ROOT,'game/config/duel-appearances.json')));
const clone=x=>JSON.parse(JSON.stringify(x)),freeze=x=>{if(x&&typeof x==='object'){Object.freeze(x);for(const v of Object.values(x))freeze(v);}return x;};
(async()=>{
 const profiles=api.validate(registry);assert.equal(Object.keys(profiles).length,27);assert.equal(api.WEAPONS.length,12);assert.equal(api.HORSES.length,13);
 const liu=Object.entries(registry.profiles).find(([,p])=>p.name==='劉備'),guan=Object.entries(registry.profiles).find(([,p])=>p.name==='關羽');
 assert(liu&&guan);assert.equal(profiles[liu[0]].weapon,'dual-swords');assert.equal(profiles[liu[0]].horse,'dilu');assert.equal(profiles[guan[0]].horse,'red-hare');
 const pan=profiles['san14-candidate-0785'];assert.equal(pan.weapon,'axe');assert.equal(pan.horse,'chestnut');
 let calls=0;const lookup=api.create({fetch:async url=>{assert.equal(url,api.INDEX);calls++;return{ok:true,json:async()=>registry};}});
 const catalog=freeze({library:Object.entries(registry.profiles).map(([person_id,p],id)=>({id,person_id,name:p.name})),names:{999:'劉備'}}),before=JSON.stringify(catalog);
 assert.deepEqual(await Promise.all([lookup.load(),lookup.load()]),[true,true]);assert.equal(calls,1);assert.equal(lookup.status,'ready');
 for(const p of catalog.library){const a=lookup.profile(catalog,p.id),b=registry.profiles[p.person_id];assert.equal(a.person_id,p.person_id);assert.equal(a.weapon,b.weapon);assert.equal(a.horse,b.horse);assert.equal(a.documented,true);assert(Object.isFrozen(a));for(const key of ['weapon_label','horse_label'])for(const lang of ['zh-Hant','ja'])assert.equal(a[key][lang],b[key][lang]);}
 const runtime=catalog.library.find(p=>p.person_id===liu[0]).id;assert.equal(lookup.profile(catalog,String(runtime)).horse,'dilu');
 const cao=catalog.library.find(p=>p.name==='曹操'),huang=catalog.library.find(p=>p.name==='黃忠'),quan=catalog.library.find(p=>p.name==='孫權');
 assert.equal(lookup.profile(catalog,cao.id,{horse:'zhuahuang-feidian'}).horse,'zhuahuang-feidian');
 assert.equal(lookup.profile(catalog,cao.id,{horse:'jueying'}).horse,'jueying');
 assert.equal(lookup.profile(catalog,huang.id,{weapon:'bow'}).weapon,'bow');
 assert.equal(lookup.profile(catalog,huang.id,{weapon:'guandao'}).weapon,'guandao');
 assert.equal(lookup.profile(catalog,quan.id,{horse:'jingfan'}).horse,'jingfan');
 for(const selection of [{horse:'red-hare'},{weapon:'bow'},{horse:'../file'},{horse:'jueying',arbitrary:true},[]])assert.throws(()=>lookup.profile(catalog,cao.id,selection),'Only this person\'s documented variants may be selected');
 assert.equal(lookup.profile(catalog,cao.id).horse,registry.profiles[cao.person_id].horse,'Cosmetic choices never change the default binding');
 assert(Object.isFrozen(lookup.profile(catalog,cao.id).horse_variants));assert(Object.isFrozen(lookup.profile(catalog,cao.id).horse_variants[0].label));
 const other=freeze({library:[{id:runtime,person_id:'other-identity',name:'劉備'}]});assert.equal(lookup.profile(other,runtime).documented,false,'Equal runtime IDs or names cannot borrow another stable identity');assert.equal(lookup.profile(catalog,999).documented,false,'No name or substring fallback');
 for(const id of ['clerk-000001','clerk-000002',null,0,1199]){const a=lookup.profile({},id),b=lookup.profile(null,id);assert.deepEqual(a,b);assert(api.WEAPONS.includes(a.weapon));assert(['chestnut','white','black'].includes(a.horse));assert.equal(a.documented,false);}
 assert.equal(JSON.stringify(catalog),before,'The art registry is read-only');
 for(const mutate of [r=>r.schema='bad',r=>r.profiles=[],r=>r.profiles[liu[0]].weapon='../file',r=>r.profiles[liu[0]].horse='mythical',r=>r.profiles[liu[0]].weapon_label.ja=32,r=>r.profiles[liu[0]].horse_variants={},r=>r.profiles[liu[0]].horse_variants=[{key:'jueying',label:{'zh-Hant':'絕影',ja:'絶影'}},{key:'jueying',label:{'zh-Hant':'重複',ja:'重複'}}],r=>r.profiles[liu[0]].weapon_variants=[{key:'escape',label:{'zh-Hant':'越界',ja:'越界'}}],r=>r.profiles[liu[0]].horse_variants=[{key:'black',label:{'zh-Hant':'黑馬'}}]]){const bad=clone(registry);mutate(bad);assert.throws(()=>api.validate(bad));}
 for(const fetcher of [async()=>{throw Error('offline');},async()=>({ok:false}),async()=>({ok:true,json:async()=>({schema:'bad'})}),async()=>({ok:true,json:async()=>new Promise(()=>{})})]){
  const failed=api.create({fetch:fetcher,timeoutMs:5});assert.equal(await failed.load(),false);assert.equal(failed.status,'unavailable');assert.equal(failed.profile(catalog,runtime).documented,false,'Registry failure still leaves a deterministic generic sprite');
 }
 const sandbox={window:null,fetch:async()=>({ok:true,json:async()=>registry}),setTimeout,clearTimeout,AbortController,Math:Object.assign(Object.create(Math),{random(){throw Error('Art must not consume RNG');}})};sandbox.window=sandbox;
 vm.runInNewContext(fs.readFileSync(path.join(ROOT,'game/duel-appearance.js'),'utf8'),sandbox);await sandbox.GameDuelAppearance.load();assert.equal(sandbox.GameDuelAppearance.profile(catalog,runtime).horse,'dilu');for(let i=0;i<1100;i++)sandbox.GameDuelAppearance.profile({},i);
 console.log('duel appearance:27 stable-ID profiles,12 weapon/13 horse keys, per-person cosmetic variants, bilingual labels, generic determinism, no RNG/state writes, strict registry and bounded missing-asset fallback passed');
})().catch(error=>{console.error(error);process.exitCode=1;});

// Actual held weapons override old visual selections; the independent horse
// registry still controls a rider's documented mount and optional horse variant.
(async()=>{
 const lookup=api.create({fetch:async()=>({ok:true,json:async()=>registry})});assert.equal(await lookup.load(),true);
 const library=Object.entries(registry.profiles).map(([person_id,profile],id)=>({id,person_id,name:profile.name}));
 const lu=library.find(person=>person.name==='呂布'),cao=library.find(person=>person.name==='曹操'),liu=library.find(person=>person.name==='劉備');assert(lu&&cao&&liu);
 const halberd={id:21,name_tc:'方天畫戟',name_ja:'方天画戟',family:'spear',appearance:'halberd'};
 const sword={id:2,name_tc:'長劍',name_ja:'長剣',family:'sword',appearance:'sword'};
 const catalog=freeze({library,equipment:{officers:{[lu.id]:{weapon:halberd},[cao.id]:{weapon:sword},[liu.id]:{weapon:{id:24,name_tc:'雙股劍',name_ja:'双股剣',family:'sword',appearance:'dual-swords'}}}}});
 const before=JSON.stringify(catalog),physical=lookup.profile(catalog,lu.id);
 assert.equal(physical.weapon,'halberd');assert.equal(physical.weapon_label['zh-Hant'],'方天畫戟');assert.equal(physical.weapon_label.ja,'方天画戟');assert.equal(physical.physical_equipment,true);assert.equal(physical.horse,'red-hare');assert.equal(physical.weapon_variants.length,1);
 assert.equal(lookup.profile(catalog,lu.id,{weapon:'sword'}).weapon,'halberd','An old visual weapon choice cannot replace the actual held halberd');
 assert.equal(lookup.profile(catalog,lu.id,{weapon:'bow'}).weapon,'halberd','An unrelated legacy selection cannot create an unowned weapon');
 const purchased=clone(catalog);purchased.equipment.officers[lu.id].weapon=clone(sword);freeze(purchased);const purchasedBefore=JSON.stringify(purchased);
 const replacement=lookup.profile(purchased,lu.id,{weapon:'halberd'});assert.equal(replacement.weapon,'sword');assert.equal(replacement.weapon_label['zh-Hant'],'長劍');assert.equal(replacement.horse,'red-hare','Buying a normal sword changes only the actual weapon, keeping Lü Bu’s independent mount');
 assert.equal(lookup.profile(catalog,liu.id).weapon,'dual-swords');assert.equal(lookup.profile(catalog,liu.id).horse,'dilu');
 for(const horse of ['jueying','zhuahuang-feidian']){const variant=lookup.profile(catalog,cao.id,{weapon:'bow',horse});assert.equal(variant.weapon,'sword');assert.equal(variant.horse,horse,'Documented horse choices remain independent of actual equipment');}
 assert.equal(JSON.stringify(catalog),before);assert.equal(JSON.stringify(purchased),purchasedBefore);assert(Object.isFrozen(replacement));assert(Object.isFrozen(replacement.weapon_variants));
 console.log('actual duel equipment: Lü Bu’s real halberd, purchased sword replacement, independent famous horses, inert legacy weapon choices and immutable projection passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
