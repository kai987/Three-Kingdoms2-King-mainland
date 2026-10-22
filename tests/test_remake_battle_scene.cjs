/* Real server receipts drive a pure scene consumer; playback never executes gameplay. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const ROOT=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(ROOT,'game/battle-scene.js'),'utf8');
const actual=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B','-c',String.raw`
import json,sys
sys.path[:0]=['source','tests']
from remake.campaign import Campaign,SeedRng
from remake.campaign_expansion import TACTICS
from test_remake_tactical_ai import battle,actors,successful_rng
from test_remake_generated_officers import GeneratedOfficerTests

def thin(value):
 c=value['catalog'];g=value['game']
 return dict(revision=value['revision'],presentation=value.get('presentation'),game={k:g[k] for k in ('battle','officers','player','seed','phase','rng')},catalog=dict(scenario_id=c.get('scenario_id',c.get('id','controlled-scene')),**{k:c[k] for k in ('names','cities','tactics')}))
rows=[]
def action(game,kind,payload,key):
 before=thin(game.view());response=game.command(kind,payload,game.revision)
 rows.append(dict(key=key,kind=kind,payload=payload,before=before,after=thin(response)))
for tid,(_,cost,effect,_) in enumerate(TACTICS):
 terrain='water' if effect in {'water','chain','flood'} else 'mountain' if effect=='rock' else 'plain'
 game=battle(terrain);b,a,t,*_=actors(game);successful_rng(game.state)
 action(game,'tactic',dict(battle_id=b['id'],actor=a['id'],target=t['id'],tactic=tid),'tactic:'+effect)
for key in ('attack','ambush','stunned','failure','retreat','duel'):
 game=battle(three_enemies=False);b,a,t,*_=actors(game)
 if key=='ambush':b['extended']['ambush']=dict(actor=t['id'])
 if key=='stunned':b['extended']['support'][str(a['id'])]['stunned']=1
 if key=='failure':
  game.state.rng=SeedRng(next(i for i in range(1,10000) if SeedRng(i).next()%100>=95))
  action(game,'tactic',dict(battle_id=b['id'],actor=a['id'],target=t['id'],tactic=0),'failure');continue
 if key=='retreat':action(game,'retreat',dict(battle_id=b['id']),'retreat');continue
 if key=='duel':
  successful_rng(game.state)
  action(game,'duel_start',dict(battle_id=b['id'],actor=a['id'],target=t['id']),'duel_start')
  action(game,'duel_action',dict(battle_id=b['id'],move='strike'),'duel_action')
  action(game,'duel_action',dict(battle_id=b['id'],move='guard'),'duel_guard')
  action(game,'duel_action',dict(battle_id=b['id'],move='feint'),'duel_feint')
  action(game,'duel_action',dict(battle_id=b['id'],move='withdraw'),'duel_withdraw');continue
 action(game,'attack',dict(battle_id=b['id'],actor=a['id'],target=t['id']),key)
game,ident=GeneratedOfficerTests().new()
game.command('allocate',dict(city='nanjun',officer=ident,troops=999),game.revision)
game._complete_turn(game.state);game._reconcile_factions(game.state)
game._start_expanded_battle(game.state,game.state.cities['nanjun'],game.state.cities['jiangxia'],[ident])
action(game,'attack',dict(battle_id=game.state.battle['id'],actor=ident,target=game.state.battle['defenders'][0]['id']),'mixed')
print(json.dumps(dict(rows=rows,tactics=[dict(id=i,effect=t[2]) for i,t in enumerate(TACTICS)]),ensure_ascii=False,separators=(',',':')))
`],{cwd:ROOT,encoding:'utf8',maxBuffer:8*1024*1024,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}}));
const clone=value=>JSON.parse(JSON.stringify(value));
function freeze(value){if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
function environment({manifest=null,reduced=false,missingRAF=false,missingContext=false}={}){
 const rafs=new Map(),timers=new Map(),listeners=new Map(),requests=[],cancels=[],observers=[],texts=[],draws=[],rectangles=[];let next=0;
 const doc={hidden:false,addEventListener(type,fn){if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn);},removeEventListener(type,fn){listeners.get(type)?.delete(fn);},emit(type,event={}){for(const fn of [...listeners.get(type)||[]])fn(event);},createElement(){return canvas();}};
 const context={fillRect(x,y,w,h){rectangles.push({x,y,w,h,color:this.fillStyle});},fillText(text,x,y){texts.push({text:String(text),x,y});},save(){},restore(){},drawImage(image,...args){draws.push({src:image?.src,args});},translate(){},scale(){},getImageData(){return{data:new Uint8ClampedArray(256*160*4)};}};
 function canvas(){return{style:{},width:256,height:240,getContext:()=>missingContext?null:context,getBoundingClientRect(){return{left:0,top:0,width:parseFloat(this.style.width)||256,height:parseFloat(this.style.height)||240};}};}
 const surface=canvas(),nodes={'.nes-battle-viewport':{clientWidth:512,clientHeight:480},'[data-battle-canvas]':surface};
 for(const name of ['[data-battle-skip]','[data-battle-scene-title]','[data-battle-caption]','[data-battle-description]'])nodes[name]={hidden:true,textContent:'',addEventListener(type,fn){this[type]=fn;}};
 const host={isConnected:true,dataset:{},querySelector:selector=>nodes[selector]||null};
 const i18n={locale:'zh-Hant',t:(value,lang)=>lang==='ja'?'日:'+value:value};
 const sandbox={module:{exports:{}},document:doc,console,AbortController,Uint8ClampedArray,Math:Object.assign(Object.create(Math),{random(){throw Error('Scene sampled randomness');}}),GameI18n:i18n,
  matchMedia:()=>({matches:reduced}),setTimeout(fn){const id=++next;timers.set(id,fn);return id;},clearTimeout(id){timers.delete(id);},
  requestAnimationFrame:missingRAF?undefined:fn=>{const id=++next;rafs.set(id,fn);return id;},cancelAnimationFrame:id=>{cancels.push(id);rafs.delete(id);},
  fetch:async url=>{requests.push(url);assert.equal(url,'/assets/battle-original/index.json','Playback may fetch artwork, never gameplay');return manifest?{ok:true,json:async()=>manifest}:{ok:false};},
  ResizeObserver:class{constructor(fn){this.fn=fn;this.disconnects=0;observers.push(this);}observe(){}disconnect(){this.disconnects++;}},
  Image:class{constructor(){this.width=16;this.height=16;}set src(value){this._src=value;queueMicrotask(()=>this.onload?.());}get src(){return this._src;}}};
 sandbox.window=sandbox;vm.runInNewContext(source,sandbox,{filename:'game/battle-scene.js'});
 return{api:sandbox.module.exports,doc,host,surface,nodes,i18n,requests,cancels,observers,texts,draws,rectangles,rafs,timers,
  step(time){const entries=[...rafs];rafs.clear();for(const [,fn]of entries)fn(time);},
  drain(){for(let i=0;rafs.size&&i<100;i++)this.step(i*1200);assert.equal(rafs.size,0,'RAF queue must terminate');},
  listenerCount(){return[...listeners.values()].reduce((n,set)=>n+set.size,0);}};
}
const standalone=environment().api;
const normalize=value=>JSON.parse(JSON.stringify(value));
function scenesFor(row){return standalone.receiptScenes(row.after.presentation,row.after.game.battle.id,row.after.revision);}
const watchdog=setTimeout(()=>{console.error('Battle scene playback did not resolve within 20 seconds');process.exitCode=1;},20000);
(async()=>{
 const accepted=new Map(actual.rows.map(row=>[row.key,scenesFor(row)]));
 for(const tactic of actual.tactics){const row=actual.rows.find(r=>r.key==='tactic:'+tactic.effect),scenes=accepted.get(row.key);assert(scenes.length,`Actual tactic ${tactic.id}/${tactic.effect} must not be discarded`);assert.equal(scenes[0].tactic,tactic.id);assert.equal(scenes[0].effect,tactic.effect);}
 assert.equal(actual.tactics.length,16);assert(accepted.get('tactic:strike').length,'要撃 uses strike');
 const attack=accepted.get('attack');assert.equal(attack[0].kind,'attack');assert(attack.some(s=>s.counter),'Actual AI response is part of the receipt');
 const chain=accepted.get('ambush');assert.equal(chain[0].kind,'ambush');assert.equal(chain[1].kind,'attack');assert.deepEqual(normalize(chain[0].after),normalize(chain[1].before),'Ambush damage must not be replayed as attack damage');
 assert(accepted.get('retreat').length,'Actual retreat permits null actor/target');
 assert.equal(accepted.get('stunned')[0].skipped,true);assert.equal(accepted.get('failure')[0].success,false);
 assert.equal(typeof accepted.get('mixed')[0].actor,'string');
 for(const row of actual.rows){
  const original=JSON.stringify(row),scenes=accepted.get(row.key);assert(scenes.length,row.key);
  for(const scene of scenes){
   const deltas=standalone.changes(scene);
   for(const delta of deltas){const before=scene.before.units.find(u=>u.id===delta.id),after=scene.after.units.find(u=>u.id===delta.id);for(const field of ['troops','health','energy','guard','stunned'])assert.equal(delta[field],after[field]-before[field]);}
  }
  assert.equal(JSON.stringify(row),original,'Receipt validation and differences are read-only');
 }
 const first=actual.rows.find(r=>r.key==='attack'),bid=first.after.game.battle.id,revision=first.after.revision;
 for(const mutate of [r=>r.schema='unknown',r=>r.revision++,r=>r.scenes.push(...Array(25).fill(r.scenes[0])),r=>r.scenes[0].battle_id='another-battle',r=>r.scenes[0].kind='execute-command',r=>r.scenes[0].actor=true,r=>r.scenes[0].counter=1,r=>r.scenes[0].effect='invented',r=>r.scenes[0].before.units[0]=null,r=>r.scenes[0].before.units[0].troops=-1,r=>r.scenes[0].after.units[0].health=100,r=>r.scenes[0].after.units[0].energy=19,r=>r.scenes[0].after.units[1].id=r.scenes[0].after.units[0].id]){
  const malformed=clone(first.after.presentation);mutate(malformed);assert.equal(standalone.receiptScenes(malformed,bid,revision).length,0,'Malformed receipt must be ignored');
 }
 // Identity and shape failures must also be rejected before reaching drawing.
 for(const mutate of [r=>r.scenes[0].actor=987654321,r=>r.scenes[0].target=null,r=>delete r.scenes[0].success,r=>delete r.scenes[0].before.outcome,r=>r.scenes[0].after.units[0].id='clerk-000000',r=>r.scenes[0].after.units[0].side='defenders',r=>r.scenes[0].before.duel={actor:r.scenes[0].actor,target:r.scenes[0].actor,round:1}]){
  const malformed=clone(first.after.presentation);mutate(malformed);assert.equal(standalone.receiptScenes(malformed,bid,revision).length,0,'Unknown actors, missing fields and divergent snapshot identities must be ignored');
 }
 for(const p of ['/assets/battle-original/plain.png','/assets/battle-original/frames/duel_01.png'])assert(standalone.validAssetPath(p));
 for(const p of ['../plain.png','/assets/battle-original/../plain.png','https://example.com/plain.png','data:image/png,a','/assets/battle-original/plain.svg','/assets/battle-original/plain.png?x=1','/assets/battle-original/%2e%2e/plain.png'])assert(!standalone.validAssetPath(p));
 for(const row of actual.rows){
  freeze(row);const env=environment(),sounds=[],settled=[],scene=env.api.create({onSound:value=>sounds.push(value),onSettled:()=>settled.push(true)}),original=JSON.stringify(row),selected={actor:row.payload.actor??row.after.game.battle.attackers[0]?.id,target:row.payload.target??row.after.game.battle.defenders[0]?.id};
  scene.observe(row.kind,row.payload,row.before,row.after);assert.equal(scene.state().queued,accepted.get(row.key).length,row.key);
  assert(scene.mount(env.host,row.after,selected));await scene.load();
  const playback=scene.play();assert(scene.playing);assert.equal(env.rafs.size,1);env.step(0);assert.equal(scene.state().scene,accepted.get(row.key)[0].kind);
  env.doc.emit('game-language-change');env.i18n.locale='ja';env.doc.emit('game-language-change');assert(scene.playing,'Language change must not cancel/restart an action');
  env.drain();await playback;assert(!scene.playing);assert.equal(scene.state().queued,0);assert(env.nodes['[data-battle-skip]'].hidden);assert.equal(env.rafs.size,0);
  assert.deepEqual(normalize(sounds),normalize(accepted.get(row.key)),row.key+' must play each authoritative scene once and in order');assert.equal(settled.length,1);
  assert.equal(JSON.stringify(row),original,'Drawing and language changes cannot alter campaign, RNG or receipt');assert.deepEqual(env.requests,['/assets/battle-original/index.json'],'Only the one cached artwork manifest request is permitted');
  scene.observe(row.kind,row.payload,row.before,row.after);assert.equal(scene.state().queued,0,'Same revision must not replay');
  scene.dispose();assert.equal(env.listenerCount(),0);assert.equal(env.rafs.size,0);assert(env.observers.every(o=>o.disconnects>0));assert.equal(env.timers.size,0);
 }
 // Explicit baseline reset/new/leave and every early-exit path release playback.
 for(const mode of ['skip','escape','hidden','disconnected','reset','leave','dispose']){
  const env=environment(),outcomes=[],scene=env.api.create({onOutcome:value=>outcomes.push(value)}),before=JSON.stringify(first.after);scene.observe(first.kind,first.payload,first.before,first.after);scene.mount(env.host,first.after);await scene.load();scene.deferOutcome({key:mode});const playback=scene.play();env.step(0);
  if(mode==='skip')scene.skip();else if(mode==='escape'){let prevented=false;env.doc.emit('keydown',{key:'Escape',preventDefault(){prevented=true;}});assert(prevented);}else if(mode==='hidden'){env.doc.hidden=true;env.doc.emit('visibilitychange');}else if(mode==='disconnected'){env.host.isConnected=false;env.step(20);}else scene[mode]();
  await playback;assert.equal(env.rafs.size,0,mode+' RAF');assert(!scene.playing,mode);assert.equal(scene.state().queued,0,mode+' queue');assert.equal(outcomes.length,['reset','leave','dispose'].includes(mode)?0:1,mode+' deferred outcome lifecycle');assert.equal(JSON.stringify(first.after),before,mode+' cannot mutate authoritative state');scene.dispose();
 }
 for(const mode of ['hidden','reduced','missingRAF']){
  const env=environment({reduced:mode==='reduced',missingRAF:mode==='missingRAF'}),scene=env.api.create();if(mode==='hidden')env.doc.hidden=true;
  scene.observe(first.kind,first.payload,first.before,first.after);scene.mount(env.host,first.after);await scene.load();await scene.play();assert(!scene.playing);assert.equal(scene.state().queued,0);assert.equal(env.rafs.size,0);scene.dispose();
 }
 // Canvas failure and accessibility skips still settle the already committed result exactly once.
 for(const mode of ['normal','skip','hidden','reduced','missingRAF','missingContext','empty']){
  const env=environment({reduced:mode==='reduced',missingRAF:mode==='missingRAF',missingContext:mode==='missingContext'}),outcomes=[],settled=[],sounds=[];
  const scene=env.api.create({onOutcome:value=>outcomes.push(value),onSettled:()=>settled.push(true),onSound:value=>sounds.push(value)}),cue=freeze({key:'authoritative-result'});
  if(mode==='hidden')env.doc.hidden=true;
  if(mode!=='empty')scene.observe(first.kind,first.payload,first.before,first.after);
  scene.mount(env.host,first.after);await scene.load();scene.deferOutcome(cue);const playback=scene.play();
  if(mode==='normal')env.drain();else if(mode==='skip'){env.step(0);scene.skip();}
  await playback;assert.deepEqual(outcomes,[cue],mode+' must deliver the final outcome once');
  assert.equal(settled.length,['normal','skip','reduced','missingRAF'].includes(mode)?1:0,mode+' restores the final scene after visible playback');
  assert.equal(sounds.length,mode==='normal'?accepted.get('attack').length:['skip','reduced','missingRAF'].includes(mode)?1:0,mode+' sound follows playback accessibility policy');
  scene.skip();await scene.play();assert.equal(outcomes.length,1,mode+' must not repeat outcome cue');assert.equal(env.rafs.size,0);scene.dispose();
 }
 // An accessibility skip must restore battle music after the last duel sound, before the result cue.
 for(const mode of ['reduced','missingRAF']){
  const row=actual.rows.find(r=>r.key==='duel_withdraw'),env=environment({reduced:mode==='reduced',missingRAF:mode==='missingRAF'}),order=[];let music=null;
  assert(row.before.game.battle.extended.duel);assert.equal(row.after.game.battle.extended.duel,null);
  const scene=env.api.create({onSound:value=>{music=value.kind.startsWith('duel')?'duel':'battle';order.push(music);},onSettled:()=>{music=row.after.game.battle.extended.duel?'duel':'battle';order.push(music);},onOutcome:()=>order.push('outcome')});
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);await scene.load();scene.deferOutcome('test-result');await scene.play();
  assert.equal(music,'battle',mode+' cannot leave a completed duel BGM active');assert.deepEqual(order,['duel','battle','outcome']);assert.equal(env.rafs.size,0);scene.dispose();
 }
 // Native artwork must remain on screen for actor-less retreat, and strike must actually render an impact.
 const nativeManifest=JSON.parse(fs.readFileSync(path.join(ROOT,'game/assets/battle-original/index.json'),'utf8'));
 for(const key of ['attack','tactic:strike','retreat']){
  const row=actual.rows.find(r=>r.key===key),env=environment({manifest:nativeManifest}),scene=env.api.create();
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);assert(await scene.load());
  const playback=scene.play();env.step(0);env.draws.length=0;env.texts.length=0;env.rectangles.length=0;env.step(env.api.duration(accepted.get(key)[0])*.6);
  const armyPaths=new Set(['infantry','infantry_enemy','cavalry'].flatMap(kind=>(nativeManifest.sprites[kind]?.frames||[]).map(f=>f.path)));
  assert(env.draws.some(d=>armyPaths.has(d.src)),key+' must draw real unit artwork');assert(env.texts.length>0,key+' must retain its unit HUD');
  if(key!=='retreat'){
   const impactPaths=new Set((nativeManifest.sprites.impact?.frames||[]).map(f=>f.path));
   assert(impactPaths.size?env.draws.some(d=>impactPaths.has(d.src)):env.rectangles.some(r=>r.color==='#d82000'),key+' must draw impact at actual hit time');
  }
  scene.skip();await playback;assert.equal(env.rafs.size,0);scene.dispose();assert.equal(env.timers.size,0);
 }
 {
  const env=environment(),scene=env.api.create();scene.observe(first.kind,first.payload,first.before,first.after);scene.mount(env.host,first.after);await scene.load();const playback=scene.play();env.step(0);scene.reset();await playback;
  const baseline=clone(first.after);delete baseline.presentation;scene.observe('load',{},first.after,baseline);assert.equal(scene.state().queued,0,'Loading a baseline must not replay old receipt');scene.mount(env.host,baseline);assert(!scene.playing);
  scene.observe('new',{},baseline,{...baseline,game:{...baseline.game,seed:999}});assert.equal(scene.state().queued,0);scene.dispose();
 }
 for(const manifest of [null,{schema:'wrong',backgrounds:{},sprites:{}},{schema:'tk2-battle-original-v1',backgrounds:{plain:{path:'/assets/battle-original/../escape.png'}},sprites:{}}]){
  const env=environment({manifest}),scene=env.api.create();assert.equal(await scene.load(),false);assert.equal(scene.state().assetStatus,'unavailable');assert.equal(env.rafs.size,0);assert.equal(env.timers.size,0);scene.dispose();
 }
 console.log(`battle scenes: ${actual.rows.length} real command receipts, all16effects, authoritative damage/counters/mixed IDs, strict schema/assets, read-only playback, revision/baseline lifecycle, skip/cancel/hidden/reduced-motion and RAF cleanup passed`);
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>clearTimeout(watchdog));
