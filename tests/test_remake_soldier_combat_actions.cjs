/* Four-pose presentation only: source clips, facing and release/contact timing.
 * Controlled receipts exercise the consumer; real command receipts are also
 * exercised by the browser soldier tests. Nothing here computes game damage. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../game/battle-scene.js'),'utf8'),api=require('../game/battle-scene.js');
const clone=value=>JSON.parse(JSON.stringify(value));
const TYPES={infantry:['melee'],archer:['melee','ranged'],cavalry:['melee'],general:['melee']};
function library(){
 return {schema:'tk2-soldier-combat-actions-v1',scale:4,logical_size:[16,16],frame_size:[64,64],frames_per_action:4,
  types:Object.fromEntries(Object.entries(TYPES).map(([kind,actions])=>[kind,Object.fromEntries(actions.map(action=>[action,
   Object.fromEntries(['friendly','enemy'].map(palette=>[palette,{path:`/assets/soldier-combat-actions-v1/${kind}-${action}-${palette}.png`,width:256,height:64,facing:'right',anchor:{x:8,y:16},sha256:'a'.repeat(64),frames:api.SOLDIER_COMBAT_PHASES[action].map((phase,i)=>({phase,source_rect:[i*64,0,64,64]}))}]))]))]))};
}
const valid=library();assert(api.validSoldierCombatLibrary(valid));
const shipped=JSON.parse(fs.readFileSync(path.join(__dirname,'../game/assets/soldier-combat-actions-v1/index.json'),'utf8'));
assert(api.validSoldierCombatLibrary(shipped),'The shipped frozen manifest satisfies the actual runtime contract');
for(const mutate of [
 d=>d.scale=1,d=>d.frame_size=[16,16],d=>d.logical_size=[32,32],d=>d.frames_per_action=8,
 d=>delete d.types.general,d=>d.types.infantry.ranged=clone(d.types.archer.ranged),d=>d.types.archer.melee.other=clone(d.types.archer.melee.enemy),
 d=>d.types.archer.ranged.friendly.path='/assets/soldier-combat-actions-v1/../secret.png',
 d=>d.types.archer.ranged.friendly.path='https://example.com/atlas.png',d=>d.types.archer.ranged.friendly.path='/assets/soldier-combat-actions-v1/infantry-melee-friendly.png',
 d=>d.types.general.melee.enemy.width=128,d=>d.types.general.melee.enemy.height=256,d=>d.types.general.melee.enemy.anchor.x=16,
 d=>d.types.general.melee.enemy.facing='left',d=>d.types.general.melee.enemy.sha256='unknown',
 d=>d.types.general.melee.enemy.frames[1].phase='release',d=>d.types.general.melee.enemy.frames[1].source_rect=[0,0,64,64],
 d=>d.types.general.melee.enemy.frames[1].source_rect=[64,0,65,64],d=>d.types.general.melee.enemy.frames[1].source_rect[0]=true,
]){const bad=library();mutate(bad);assert.equal(api.validSoldierCombatLibrary(bad),false,'Unlisted paths, missing types and drifting geometry are rejected before loading images');}
for(const [kind,actions]of Object.entries(TYPES))for(const action of actions){
 const event=action==='ranged'?'arrow':'melee';
 for(const [p,index]of [[0,0],[.249,0],[.25,1],[.499,1],[.5,2],[.749,2],[.75,3],[1,3]]){
  const frame=api.soldierCombatFrame(kind,event,p);assert.equal(frame.index,index);assert.equal(frame.action,action);assert.equal(frame.phase,api.SOLDIER_COMBAT_PHASES[action][index]);assert.equal(frame.release,action==='ranged'&&p>=.5);assert.equal(frame.contact,p>=.65);
 }
}
for(const kind of ['general','cavalry','infantry','unknown'])assert.equal(api.soldierCombatFrame(kind,'arrow',.6),null,'Only archers display an actual ranged event');
assert.equal(api.soldierCombatFrame('archer','move',.6),null);assert.equal(api.soldierCombatFrame('archer','melee',.6).release,false);
assert.equal(api.soldierCombatFrame('archer','arrow',NaN).index,0);assert.equal(api.soldierCombatFrame('infantry','melee',-5).index,0);

function fixture(kind,eventKind,side){
 const actor=side==='attackers'?(kind==='general'?'a0':'a1'):(kind==='general'?'d0':'d1'),target=side==='attackers'?'d1':'a1';
 const row={schema:'tk2-siege-v1',mode:'field',actor:1,target:2,fort:null,map_id:'original-09',cell:{x:8,y:9},stage:'combat',round:1,events:[],units:[
  {id:'a0',side:'attackers',kind:'general',x:1,y:1,troops:0,health:80,withdrawn:false},
  {id:'a1',side:'attackers',kind:'infantry',x:7,y:5,troops:100,health:100,withdrawn:false},
  {id:'d0',side:'defenders',kind:'general',x:14,y:1,troops:0,health:80,withdrawn:false},
  {id:'d1',side:'defenders',kind:'infantry',x:8,y:5,troops:100,health:100,withdrawn:false},
 ]};
 const unit=row.units.find(u=>u.id===actor);unit.kind=kind;unit.x=side==='attackers'?7:8;unit.y=5;
 if(kind==='general')row.units.find(u=>u.side===side&&u.id!==actor).x=side==='attackers'?6:9;
 const victim=row.units.find(u=>u.id===target),after=clone(row);after.round=2;after.units.find(u=>u.id===target).troops=after.units.find(u=>u.id===target).health=80;
 after.events=[{kind:eventKind,actor,target,from:{x:unit.x,y:unit.y},to:{x:victim.x,y:victim.y},loss:20}];
 const macro=[{id:1,side:'attackers',troops:1000,health:80,energy:18,guard:0,stunned:0},{id:2,side:'defenders',troops:1000,health:80,energy:18,guard:0,stunned:0}],snapshot={round:1,outcome:null,duel:null,units:macro};
 const receipt={schema:'tk2-battle-presentation-v1',revision:2,scenes:[{kind:'soldier_step',battle_id:'controlled',actor:1,target:2,own:'attackers',counter:false,tactic:null,effect:null,success:true,skipped:false,move:null,reply:null,before:snapshot,after:clone(snapshot),soldiers:{before:row,after}}]};
 const view={revision:2,presentation:receipt,catalog:{scenario_id:'controlled',names:{1:'甲',2:'乙'}},game:{phase:'battle',player:'one',seed:1,officers:{1:{profile:{terrain_affinity:0}},2:{profile:{terrain_affinity:1}}},battle:{id:'controlled',attacker:'one',defender:'two',round:1,outcome:null,attackers:[{id:1,troops:1000}],defenders:[{id:2,troops:1000}],extended:{duel:null,siege:after,support:{1:{health:80,energy:18,guard:0,stunned:0},2:{health:80,energy:18,guard:0,stunned:0}}}}}};
 return {view,receipt,actor,event:after.events[0]};
}
function environment({combat=library(),failedPaths=[],badDimensions=[]}={}){
 const rafs=new Map(),requests=[],imageRequests=[],draws=[],scales=[],texts=[],textCalls=[],timers=new Map(),transforms=[],listeners=new Map();let serial=0,mirror=1,scaleX=1,scaleY=1;
 const ctx={setTransform(a,b,c,d){mirror=a<0?-1:1;scaleX=Math.abs(a);scaleY=Math.abs(d);},fillRect(){},fillText(value,x,y){texts.push(String(value));textCalls.push({text:String(value),x,y});},save(){transforms.push({mirror,scaleX,scaleY});},restore(){({mirror,scaleX,scaleY}=transforms.pop()??{mirror:1,scaleX:1,scaleY:1});},translate(){},scale(...args){scales.push(args);mirror*=args[0]<0?-1:1;scaleX*=Math.abs(args[0]);scaleY*=Math.abs(args[1]);},rotate(){},drawImage(image,...args){draws.push({path:image.src,args,mirror,scaleX,scaleY,smoothing:ctx.imageSmoothingEnabled});}};
 const canvas={style:{},width:1024,height:960,getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0,width:512,height:480})};
 const nodes={'.nes-battle-viewport':{clientWidth:512,clientHeight:480},'[data-battle-canvas]':canvas,'[data-duel-loadouts]':{hidden:true,innerHTML:'',querySelector:()=>null}};
 for(const key of ['[data-battle-skip]','[data-battle-scene-title]','[data-battle-caption]','[data-battle-description]','[data-battlefield-label]'])nodes[key]={hidden:true,textContent:'',addEventListener(){}};
 nodes['[data-soldier-label-toggle]']={hidden:true,textContent:'',attributes:{},setAttribute(name,value){this.attributes[name]=value;}};
 const host={isConnected:true,dataset:{},querySelector:key=>nodes[key]||null};
 const doc={hidden:false,modal:false,activeElement:null,querySelector:()=>doc.modal?{}:null,addEventListener(type,fn){if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn);},removeEventListener(type,fn){listeners.get(type)?.delete(fn);},emit(type,event={}){for(const fn of listeners.get(type)||[])fn(event);}};
 const i18n={locale:'zh-Hant'};
 const native={schema:'tk2-original-siege-assets-v1',assets:{}};
 for(const kind of Object.keys(TYPES))for(const palette of ['friendly','enemy'])native.assets[`sprite-${kind}-${palette}-0`]={path:`/assets/siege-original/sprite-${kind}-${palette}-0.png`,width:64,height:64};
 for(const effect of ['arrow','melee'])native.assets['effect-'+effect]={path:`/assets/siege-original/effect-${effect}.png`,width:effect==='arrow'?32:64,height:effect==='arrow'?32:64};
 const paths=new Map(Object.values(native.assets).map(row=>[row.path,row]));
 if(combat?.types)for(const type of Object.values(combat.types))for(const action of Object.values(type))for(const row of Object.values(action))paths.set(row.path,row);
 const sandbox={module:{exports:{}},console,AbortController,Math:Object.assign(Object.create(Math),{random(){throw Error('Presentation cannot sample RNG');}}),document:doc,GameI18n:i18n,
  setTimeout(fn){const id=++serial;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id),matchMedia:()=>({matches:false}),
  requestAnimationFrame:fn=>{const id=++serial;rafs.set(id,fn);return id;},cancelAnimationFrame:id=>rafs.delete(id),
  fetch:async url=>{requests.push(url);const value=url==='/assets/siege-original/index.json'?native:url==='/assets/soldier-combat-actions-v1/index.json'?combat:null;return value?{ok:true,json:async()=>value}:{ok:false};},
  Image:class{set src(value){imageRequests.push(value);this._src=value;const row=paths.get(value);this.width=row?.width||16;this.height=row?.height||16;if(badDimensions.includes(value))this.width--;queueMicrotask(()=>failedPaths.includes(value)?this.onerror?.():this.onload?.());}get src(){return this._src;}}
 };sandbox.window=sandbox;vm.runInNewContext(source,sandbox,{filename:'game/battle-scene.js'});
 return{api:sandbox.module.exports,host,nodes,doc,i18n,requests,imageRequests,draws,scales,texts,textCalls,rafs,timers,step(time){const pending=[...rafs];rafs.clear();for(const[,fn]of pending)fn(time);}};
}
(async()=>{
 let rendered=0;
 for(const [kind,actions]of Object.entries(TYPES))for(const action of actions)for(const side of ['attackers','defenders']){
  const eventKind=action==='ranged'?'arrow':'melee',data=fixture(kind,eventKind,side),before=JSON.stringify(data),env=environment(),scene=env.api.create();
  scene.observe('siege_step',{},null,data.view);scene.mount(env.host,data.view);await scene.load();const playback=scene.play();
  for(let i=0;i<10&&!scene.playing;i++)await new Promise(resolve=>setImmediate(resolve));assert(scene.playing);
  env.step(0);const duration=env.api.duration(data.receipt.scenes[0]);
  for(const [index,p]of [.125,.375,.6,.875].entries()){
   env.draws.length=0;env.scales.length=0;env.textCalls.length=0;env.step(duration*p);
   const palette=side==='attackers'?'friendly':'enemy',expected=`/assets/soldier-combat-actions-v1/${kind}-${action}-${palette}.png`;
   assert.equal(env.host.dataset.soldierCombatSource,'supplemental-4x');assert.equal(env.host.dataset.soldierCombatKind,kind);assert.equal(env.host.dataset.soldierCombatAction,action);assert.equal(env.host.dataset.soldierCombatFrame,String(index));
   const drawn=env.draws.filter(row=>row.path===expected);assert.equal(drawn.length,1);assert.deepEqual(Array.from(drawn[0].args.slice(0,4)),[index*64,0,64,64]);
   assert.equal(drawn[0].args[6]*drawn[0].scaleX,64,'A 64px source pose occupies 64 physical backing pixels, retaining source detail');assert.equal(drawn[0].args[7]*drawn[0].scaleY,64);assert.equal(drawn[0].smoothing,false);
   assert.equal(drawn[0].mirror,side==='defenders'?-1:1,'Attack direction follows the actual target vector');
   const arrow=env.draws.some(row=>row.path==='/assets/siege-original/effect-arrow.png');assert.equal(arrow,action==='ranged'&&p>=.5&&p<.65,'A projectile appears only after the bow release, before contact');
   const hit=env.draws.some(row=>row.path==='/assets/siege-original/effect-melee.png');assert.equal(hit,p>=.65,'Impact and loss display begin at the authoritative visual application point');
   const actor=data.receipt.scenes[0].soldiers.before.units.find(unit=>unit.id===data.actor);
   assert(!env.textCalls.some(call=>call.x===actor.x*16+1&&[actor.y*16,actor.y*16+11].includes(call.y)),'The current attack pose is not covered by its two in-cell labels');
   assert(env.textCalls.some(call=>call.y>=160),'The HUD remains visible while in-cell attack labels are temporarily cleared');
   assert.equal(JSON.stringify(data),before);rendered++;
  }
  env.textCalls.length=0;scene.skip();await playback;assert.equal(env.host.dataset.soldierCombatFrame,'');assert.equal(env.rafs.size,0);
  if(kind!=='general'){const actor=data.receipt.scenes[0].soldiers.after.units.find(unit=>unit.id===data.actor);assert(env.textCalls.some(call=>call.x===actor.x*16+1&&call.y===actor.y*16),'Final-state pieces immediately restore their labels');}
  scene.dispose();assert.equal(env.timers.size,0);
 }
 for(const mode of ['missing-manifest','invalid-manifest','invalid-path','missing-image','wrong-size']){
  const p='/assets/soldier-combat-actions-v1/infantry-melee-friendly.png',data=fixture('infantry','melee','attackers'),combat=library();if(mode==='invalid-manifest')combat.types.infantry.melee.friendly.width=128;
  if(mode==='invalid-path')combat.types.infantry.melee.friendly.path='https://example.com/untrusted-soldier.png';
  const env=environment({combat:mode==='missing-manifest'?null:combat,failedPaths:mode==='missing-image'?[p]:[],badDimensions:mode==='wrong-size'?[p]:[]}),scene=env.api.create(),before=JSON.stringify(data);
  scene.observe('siege_step',{},null,data.view);scene.mount(env.host,data.view);await scene.load();const playback=scene.play();for(let i=0;i<10&&!scene.playing;i++)await new Promise(resolve=>setImmediate(resolve));env.step(0);env.draws.length=0;env.step(160);
  assert.equal(env.host.dataset.soldierCombatSource,'native-fallback');assert(env.draws.some(row=>row.path==='/assets/siege-original/sprite-infantry-friendly-0.png'));assert.equal(JSON.stringify(data),before);
  if(mode==='invalid-manifest'||mode==='invalid-path')assert(!env.imageRequests.some(url=>url.startsWith('/assets/soldier-combat-actions-v1/')||url.startsWith('https://')),'Invalid dimensions or paths reject the whole optional library before image loading');
  scene.skip();await playback;scene.dispose();assert.equal(env.rafs.size,0);assert.equal(env.timers.size,0);
 }
 // Palette is attached to army identity; facing follows the actual horizontal
 // event vector even when a unit has advanced past the other army.
 for(const side of ['attackers','defenders'])for(const dx of [-1,1]){
  const data=fixture('infantry','melee',side),event=data.event,actorX=8,targetX=actorX+dx;
  for(const row of Object.values(data.receipt.scenes[0].soldiers)){row.units.find(unit=>unit.id===event.actor).x=actorX;row.units.find(unit=>unit.id===event.target).x=targetX;}
  event.from.x=actorX;event.to.x=targetX;
  let settled=0,outcomes=0;const env=environment({combat:shipped}),scene=env.api.create({onSettled:()=>settled++,onOutcome:()=>outcomes++}),before=JSON.stringify(data);
  scene.observe('siege_step',{},null,data.view);scene.mount(env.host,data.view);await scene.load();scene.deferOutcome({key:'committed'});const playback=scene.play();for(let i=0;i<10&&!scene.playing;i++)await new Promise(resolve=>setImmediate(resolve));env.step(0);env.draws.length=0;env.step(40);
  const palette=side==='attackers'?'friendly':'enemy',path=`/assets/soldier-combat-actions-v1/infantry-melee-${palette}.png`,pose=env.draws.find(row=>row.path===path);assert(pose);assert.equal(pose.mirror,dx<0?-1:1);
  const duration=env.api.duration(data.receipt.scenes[0]);env.step(duration*.649);assert(!env.draws.some(row=>row.path==='/assets/siege-original/effect-melee.png'),'No hit before .65');env.draws.length=0;env.step(duration*.65);assert(env.draws.some(row=>row.path==='/assets/siege-original/effect-melee.png'),'Hit begins at .65 of the unchanged bounded event duration');
  scene.skip();await playback;scene.skip();await scene.play();assert.equal(settled,1);assert.equal(outcomes,1,'Skip/replay cannot show or settle the committed outcome twice');assert.equal(JSON.stringify(data),before);scene.dispose();
 }
 // Both armies use the same one-line labels independently of player/AI side.
 // This state belongs to the scene controller and is not a campaign field.
 for(const player of ['one','two'])for(const locale of ['zh-Hant','ja']){
  const data=fixture('archer','melee','attackers');data.view.game.player=player;
  const before=JSON.stringify(data),env=environment(),scene=env.api.create({canInteract:()=>false}),button=env.nodes['[data-soldier-label-toggle]'];env.i18n.locale=locale;
  assert.match(scene.html(),/<button type="button" data-soldier-label-toggle aria-pressed="false" aria-keyshortcuts="V" hidden>/);
  scene.mount(env.host,data.view);await scene.load();
  const press=(patch={})=>{let prevented=false;env.doc.emit('keydown',{key:'v',preventDefault(){prevented=true;},...patch});return prevented;};
  const assertLabels=mode=>{
   env.textCalls.length=0;env.doc.emit('game-language-change');
   assert.equal(env.host.dataset.soldierLabelMode,mode);assert.equal(button.attributes['aria-pressed'],String(mode==='troops'));assert.equal(button.hidden,false);assert(button.textContent.includes('[V]'));assert(env.nodes['[data-battle-caption]'].textContent.includes(button.textContent));
   for(const unit of data.view.game.battle.extended.siege.units){
    const top=env.textCalls.filter(call=>call.x===unit.x*16+1&&call.y===unit.y*16),bottom=env.textCalls.filter(call=>call.x===unit.x*16+1&&call.y===unit.y*16+11);
    assert.equal(bottom.length,0,'There is no second line over the lower sprite');
    if(unit.kind==='general'){assert.equal(top.length,0,'The commander keeps the original unlabelled sprite');continue;}
    const kind={infantry:locale==='ja'?'歩':'步',archer:'弓',cavalry:'騎'}[unit.kind]+unit.id.slice(1),expected=mode==='troops'?String(unit.troops):kind;
    assert.deepEqual(top.map(call=>call.text),[expected],'Exactly the selected kind/number or current troop count is drawn');
   }
  };
  assertLabels('kind');button.onclick();assertLabels('troops');assert(press({key:'V'}));assertLabels('kind');assert(press());assertLabels('troops');
  for(const patch of [{key:'x'},{repeat:true},{defaultPrevented:true},{ctrlKey:true},{metaKey:true},{altKey:true},{shiftKey:true},{isComposing:true},{keyCode:229},{target:{isContentEditable:true}},...['input','select','textarea','contenteditable','role="textbox"','data-language-picker','nav','#utility-menu'].map(kind=>({target:{closest:selector=>selector.includes(kind)?{}:null}}))]){assert.equal(press(patch),false);assert.equal(scene.state().soldierLabelMode,'troops','Native/modified/composing/repeated input does not toggle');}
  env.doc.activeElement={isContentEditable:true};assert.equal(press(),false);env.doc.activeElement=null;
  env.doc.modal=true;assert.equal(press(),false);assert.equal(button.onclick(),false);env.doc.modal=false;assertLabels('troops');
  scene.mount(env.host,data.view);assertLabels('troops');
  // Pure display remains switchable during an authoritative replay, including
  // when the normal command controls are busy. Skipping keeps the selected mode.
  scene.observe('siege_step',{},null,data.view);const playback=scene.play();for(let i=0;i<10&&!scene.playing;i++)await new Promise(resolve=>setImmediate(resolve));assert(scene.playing);assert(press());assert.equal(scene.state().soldierLabelMode,'kind');button.onclick();scene.skip();await playback;assertLabels('troops');
  scene.leave();assert.equal(scene.state().soldierLabelMode,'kind');scene.mount(env.host,data.view);assertLabels('kind');assert.equal(JSON.stringify(data),before);scene.dispose();
 }
 for(const mode of ['tactical','duel']){
  const data=fixture('infantry','melee','attackers'),env=environment(),scene=env.api.create();
  if(mode==='tactical')data.view.game.battle.extended.siege=null;else data.view.game.battle.extended.duel={actor:1,target:2,round:1};
  scene.mount(env.host,data.view);await scene.load();const button=env.nodes['[data-soldier-label-toggle]'];assert(button.hidden,'The label toggle is only shown for the soldier sub-battle');let prevented=false;env.doc.emit('keydown',{key:'v',preventDefault(){prevented=true;}});assert.equal(prevented,false);assert.equal(scene.state().soldierLabelMode,'kind');scene.dispose();
 }
 console.log(`Soldier combat actions: ${rendered} actual canvas pose selections across all 4 classes/both palettes, strict 4× atlases, four phases, facing, release/contact timing, native fallbacks and immutable state/RNG passed`);
 console.log('Soldier labels: one-line kind/count modes for both armies, button/V parity, bilingual/ARIA hints, native/modifier/repeat/IME/modal guards, replay/skip persistence and controller reset passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
