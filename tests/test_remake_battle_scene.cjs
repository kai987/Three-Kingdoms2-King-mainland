/* Current command receipts and explicit legacy display-schema examples drive
 * a pure consumer. Aggregate display examples are not current damage rules;
 * persistent soldier contact is covered by test_remake_soldier_scene.cjs. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const officerChoices=require('../game/officer-choice.js');
const ROOT=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(ROOT,'game/battle-scene.js'),'utf8');
const actual=JSON.parse(execFileSync(process.env.PYTHON||'python3',['-B','-c',String.raw`
import json,sys
from copy import deepcopy
sys.path[:0]=['source','tests']
from remake.campaign import Campaign,SeedRng
from remake.campaign_expansion import TACTICS
from remake import battle_grid
from remake.tactical_ai import tactic_reason
from test_remake_tactical_ai import battle,actors,successful_rng
from test_remake_generated_officers import GeneratedOfficerTests

def thin(value):
 c=value['catalog'];g=value['game']
 return dict(revision=value['revision'],presentation=value.get('presentation'),game={k:g[k] for k in ('battle','officers','player','seed','phase','rng')},catalog=dict(scenario_id=c.get('scenario_id',c.get('id','controlled-scene')),**{k:c[k] for k in ('names','cities','tactics','battle_tactical')}))
rows=[]
def scene_battle(terrain='plain',three_enemies=True):
 # An explicitly experienced historical strategist exercises every original
 # learned tactic. This is an isolated renderer fixture, not an opening claim.
 game=battle(terrain,three_enemies=three_enemies);b=game.state.battle
 old=b['attackers'][0];ident=game.catalog.ids['san14-candidate-0440'];officer=game.state.officers[ident]
 officer.experience=10000
 from remake.officers import experience_tier
 officer.tier=experience_tier(officer.experience)
 replacement=next((u for u in b['defenders'] if u['id']==ident),None)
 old_point=b['extended']['tactical']['positions'][str(old['id'])]
 if replacement:
  source,target=game.state.cities[b['source']],game.state.cities[b['target']]
  source.roster.officer_ids.remove(old['id']);source.roster.officer_ids.append(ident)
  target.roster.officer_ids.remove(ident);target.roster.officer_ids.append(old['id'])
  game.state.officers[old['id']].faction_id=target.owner;officer.faction_id=source.owner
  b['defenders'][b['defenders'].index(replacement)]=old
  b['extended']['tactical']['positions'][str(old['id'])]=b['extended']['tactical']['positions'][str(ident)]
 else:
  replacement=dict(id=ident,troops=officer.troops,start=officer.troops,martial=officer.profile.martial_strength)
  del b['extended']['support'][str(old['id'])]
  b['extended']['support'][str(ident)]=dict(health=officer.health,energy=18,stunned=0,guard=0,morale=70)
  del b['extended']['tactical']['positions'][str(old['id'])]
 b['attackers'][0]=replacement;b['extended']['tactical']['positions'][str(ident)]=old_point
 return game
def arrange(game,tid=None):
 # Isolated presentation fixtures use explicit legal contact cells. They do
 # not claim that armies naturally marched to these cells in campaign play.
 b=game.state.battle
 if tid==8:
  # The current command correctly rejects rulers. A non-ruler opponent is the
  # legal target for this isolated renderer's real conversion receipt.
  b['defenders'].sort(key=lambda unit:unit['id']in game.state.extension['leaders'].values())
 a=b['attackers'][0];t=b['defenders'][0]
 tactical=b['extended']['tactical'];field=battle_grid._field(b)
 tactical['points']={'attackers':20,'defenders':20}
 cells=[(x,y) for y in range(19) for x in range(31)]
 for tx,ty in cells:
  for ax,ay in ((tx-1,ty),(tx,ty-1),(tx+1,ty),(tx,ty+1)):
   if not (0<=ax<31 and 0<=ay<19):continue
   placed={str(a['id']):dict(x=ax,y=ay),str(t['id']):dict(x=tx,y=ty)}
   occupied={(ax,ay),(tx,ty)}
   nearby=[p for p in ((tx-1,ty),(tx,ty-1),(tx+1,ty),(tx,ty+1))
           if 0<=p[0]<31 and 0<=p[1]<19 and p not in occupied]
   for unit in b['defenders'][1:]:
    candidates=nearby+[p for p in cells if p not in occupied]
    point=next(p for p in candidates if p not in occupied)
    placed[str(unit['id'])]=dict(x=point[0],y=point[1]);occupied.add(point)
   for unit in b['attackers'][1:]:
    point=next(p for p in cells if p not in occupied)
    placed[str(unit['id'])]=dict(x=point[0],y=point[1]);occupied.add(point)
   tactical['positions']=placed
   if tid is None or not tactic_reason(game.state,b,a,t,'attackers','defenders','plain',TACTICS[tid]):return
 raise AssertionError('No legal isolated presentation placement for tactic '+str(tid))
def action(game,kind,payload,key):
 before=thin(game.view());response=game.command(kind,payload,game.revision)
 rows.append(dict(key=key,kind=kind,payload=payload,before=before,after=thin(response)))
def legacy_contact_display(game,payload,key):
 # Pure presentation-schema compatibility samples: explicit small deltas are
 # unrelated to the current soldier damage kernel. No command or campaign RNG
 # is run to manufacture an obsolete instantaneous contact in playable rules.
 before=thin(game.view());after=deepcopy(before);after['revision']+=1
 b=after['game']['battle'];own='attackers';foe='defenders'
 actor=next(unit for unit in b[own]if unit['id']==payload['actor'])
 target=next(unit for unit in b[foe]if unit['id']==payload['target'])
 def snapshot():
  return dict(round=b['round'],outcome=b['outcome'],duel=None,
   units=[dict(id=unit['id'],side=side,troops=unit['troops'],
    **{field:b['extended']['support'][str(unit['id'])][field]for field in ('health','energy','guard','stunned')})
    for side in ('attackers','defenders')for unit in b[side]])
 scenes=[]
 def receipt(kind,who,other,side,change,*,counter=False,skipped=False,tactic=None,effect=None):
  start=snapshot();change();end=snapshot()
  scenes.append(dict(kind=kind,battle_id=b['id'],actor=who['id'],target=other['id'],own=side,
   counter=counter,tactic=tactic,effect=effect,success=not skipped,skipped=skipped,
   move=None,reply=None,before=start,after=end))
 if key=='ambush':
  receipt('ambush',target,actor,foe,lambda:actor.update(troops=max(1,actor['troops']-7)),
   counter=True,tactic=11,effect='ambush')
 if key=='stunned':
  receipt('attack',actor,target,own,lambda:b['extended']['support'][str(actor['id'])].update(stunned=0),skipped=True)
 else:
  def hit():
   target['troops']=max(0,target['troops']-(5 if key=='attack_guard'else 11))
   if key=='attack_guard':b['extended']['support'][str(target['id'])]['guard']-=1
  receipt('attack',actor,target,own,hit)
  if target['troops']:
   receipt('attack',target,actor,foe,lambda:actor.update(troops=max(0,actor['troops']-7)),counter=True)
 after['presentation']=dict(schema='tk2-battle-presentation-v1',revision=after['revision'],scenes=scenes)
 rows.append(dict(key=key,kind='attack',payload=payload,before=before,after=after,
  source='explicit-aggregate-renderer-schema-example; not current gameplay or damage arithmetic'))
for tid,(_,cost,effect,_) in enumerate(TACTICS):
 terrain='water' if effect in {'water','chain','flood'} else 'mountain' if effect=='rock' else 'plain'
 game=scene_battle(terrain);arrange(game,tid);b,a,t,*_=actors(game);successful_rng(game.state)
 action(game,'tactic',dict(battle_id=b['id'],actor=a['id'],target=t['id'],tactic=tid),'tactic:'+effect)
for key in ('attack','attack_guard','attack_defeat','ambush','stunned','failure','retreat','duel'):
 game=scene_battle(three_enemies=False);arrange(game);b,a,t,*_=actors(game)
 if key=='attack_guard':b['extended']['support'][str(t['id'])]['guard']=2
 if key=='attack_defeat':t['troops']=1
 if key=='ambush':b['extended']['ambush']=dict(actor=t['id'])
 if key=='stunned':b['extended']['support'][str(a['id'])]['stunned']=1
 if key=='failure':
  arrange(game,0)
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
 legacy_contact_display(game,dict(battle_id=b['id'],actor=a['id'],target=t['id']),key)
# Ending the whole side lets the real enemy move/attack with the same rules.
game=scene_battle(three_enemies=False);arrange(game);successful_rng(game.state)
# Start separated so the handoff includes an actual move/tactic receipt before
# the new persistent-contact page. Adjacent contact itself is not an aggregate
# damage receipt and is covered by the soldier scene regression.
b,a,t,*_=actors(game)
b['extended']['tactical']['positions'][str(a['id'])]=dict(x=10,y=10)
b['extended']['tactical']['positions'][str(t['id'])]=dict(x=12,y=10)
action(game,'battle_wait',dict(battle_id=game.state.battle['id']),'side_handoff')
# Two real public movement commands provide authoritative paths and saves;
# they are also combined below only as an isolated renderer sequence fixture.
game=scene_battle(three_enemies=False);arrange(game)
b,a,*_=actors(game)
options=game.view()['catalog']['battle_tactical']['actors'][str(a['id'])]['reachable']
choice=next(p for p in options if 3<=p['cost']<=12 and len(battle_grid.move_quote(game,game.state,b,a,p['x'],p['y'])['path'])>=3)
origin=dict(b['extended']['tactical']['positions'][str(a['id'])])
action(game,'battle_move',dict(battle_id=b['id'],actor=a['id'],x=choice['x'],y=choice['y']),'move_first')
action(game,'battle_move',dict(battle_id=b['id'],actor=a['id'],**origin),'move_second')
# Real committed desperate attacks, separately covering success, self-injury,
# and a low-health opponent choosing the same move from its ordinary AI pool.
for key,wanted,reply_only in [('duel_desperate_success',True,False),('duel_desperate_failure',False,False),('duel_desperate_reply',None,True)]:
 game=scene_battle(three_enemies=False);arrange(game);b,a,t,*_=actors(game);successful_rng(game.state)
 game.command('duel_start',dict(battle_id=b['id'],actor=a['id'],target=t['id']),game.revision)
 b=game.state.battle
 for seed in range(1,1000):
  r=SeedRng(seed);reply=r.next()%3;quality=r.next()%100
  if reply_only and reply==0 or not reply_only and (quality<30)==wanted:break
 game.state.rng=SeedRng(seed)
 if reply_only:b['extended']['support'][str(t['id'])]['health']=30
 action(game,'duel_action',dict(battle_id=b['id'],move='guard' if reply_only else 'desperate'),key)
game,ident=GeneratedOfficerTests().new()
game.command('allocate',dict(city='nanjun',officer=ident,troops=1000),game.revision)
game._complete_turn(game.state);game._reconcile_factions(game.state)
game._start_expanded_battle(game.state,game.state.cities['nanjun'],game.state.cities['jiangxia'],[ident])
arrange(game)
legacy_contact_display(game,dict(battle_id=game.state.battle['id'],actor=ident,target=game.state.battle['defenders'][0]['id']),'mixed')
print(json.dumps(dict(rows=rows,tactics=[dict(id=i,effect=t[2]) for i,t in enumerate(TACTICS)]),ensure_ascii=False,separators=(',',':')))
`],{cwd:ROOT,encoding:'utf8',maxBuffer:8*1024*1024,env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}}));
const clone=value=>JSON.parse(JSON.stringify(value));
function freeze(value){if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
function environment({manifest=null,enhancedManifest=null,duelAppearance=null,battlefields=null,failedPaths=[],badDimensions=[],reduced=false,missingRAF=false,missingContext=false}={}){
 const rafs=new Map(),timers=new Map(),listeners=new Map(),requests=[],imageRequests=[],cancels=[],observers=[],texts=[],draws=[],rectangles=[],transforms=[],scales=[],matrixStack=[];let next=0,matrix=[1,0,0,1,0,0];
 const doc={hidden:false,addEventListener(type,fn){if(!listeners.has(type))listeners.set(type,new Set());listeners.get(type).add(fn);},removeEventListener(type,fn){listeners.get(type)?.delete(fn);},emit(type,event={}){for(const fn of [...listeners.get(type)||[]])fn(event);},createElement(){return canvas();}};
 const context={setTransform(...args){transforms.push(args);matrix=[...args];},fillRect(x,y,w,h){rectangles.push({x,y,w,h,color:this.fillStyle});},fillText(text,x,y){texts.push({text:String(text),x,y});},save(){matrixStack.push([...matrix]);},restore(){matrix=matrixStack.pop()||matrix;},drawImage(image,...args){draws.push({src:image?.src,args,matrix:[...matrix]});},translate(x,y){matrix[4]+=matrix[0]*x+matrix[2]*y;matrix[5]+=matrix[1]*x+matrix[3]*y;},scale(...args){scales.push(args);matrix[0]*=args[0];matrix[1]*=args[0];matrix[2]*=args[1];matrix[3]*=args[1];},getImageData(){return{data:new Uint8ClampedArray(256*160*4)};}};
 function canvas(){return{style:{},width:256,height:240,getContext:()=>missingContext?null:context,getBoundingClientRect(){return{left:0,top:0,width:parseFloat(this.style.width)||256,height:parseFloat(this.style.height)||240};}};}
 const surface=canvas(),nodes={'.nes-battle-viewport':{clientWidth:512,clientHeight:480},'[data-battle-canvas]':surface};
 for(const name of ['[data-battle-skip]','[data-battle-scene-title]','[data-battle-caption]','[data-battle-description]'])nodes[name]={hidden:true,textContent:'',addEventListener(type,fn){this[type]=fn;}};
 nodes['[data-duel-loadouts]']={hidden:true,innerHTML:'',querySelector:()=>null};
 const host={isConnected:true,dataset:{},querySelector:selector=>nodes[selector]||null};
 const i18n={locale:'zh-Hant',t:(value,lang)=>lang==='ja'?'日:'+value:value};
 const sandbox={module:{exports:{}},document:doc,console,AbortController,Uint8ClampedArray,Math:Object.assign(Object.create(Math),{random(){throw Error('Scene sampled randomness');}}),GameI18n:i18n,GameOfficerChoices:officerChoices,GameDuelAppearance:duelAppearance,GameBattlefields:battlefields,
  matchMedia:()=>({matches:reduced}),setTimeout(fn){const id=++next;timers.set(id,fn);return id;},clearTimeout(id){timers.delete(id);},
  requestAnimationFrame:missingRAF?undefined:fn=>{const id=++next;rafs.set(id,fn);return id;},cancelAnimationFrame:id=>{cancels.push(id);rafs.delete(id);},
  fetch:async url=>{requests.push(url);assert(['/assets/battle-original/index.json','/assets/battle-enhanced/index.json','/assets/siege-original/index.json'].includes(url),'Playback may fetch artwork, never gameplay');const data=url.includes('siege-original')?null:url.includes('battle-enhanced')?enhancedManifest:manifest;return data?{ok:true,json:async()=>data}:{ok:false};},
  ResizeObserver:class{constructor(fn){this.fn=fn;this.disconnects=0;observers.push(this);}observe(){}disconnect(){this.disconnects++;}},
  Image:class{constructor(){this.width=16;this.height=16;}set src(value){this._src=value;if(value.startsWith('/assets/battlefields/')){this.width=496;this.height=304;if(badDimensions.includes(value))this.width--;}const atlas=Object.values(enhancedManifest?.soldiers?.types||{}).flatMap(type=>[type.friendly,type.enemy]).find(row=>row?.path===value);if(atlas){this.width=atlas.width;this.height=atlas.height;if(badDimensions.includes(value))this.width--;}imageRequests.push(value);queueMicrotask(()=>failedPaths.includes(value)?this.onerror?.():this.onload?.());}get src(){return this._src;}}};
 sandbox.window=sandbox;vm.runInNewContext(source,sandbox,{filename:'game/battle-scene.js'});
 return{api:sandbox.module.exports,doc,host,surface,nodes,i18n,requests,imageRequests,cancels,observers,texts,draws,rectangles,transforms,scales,rafs,timers,setReduced(value){reduced=value;},
  step(time){const entries=[...rafs];rafs.clear();for(const [,fn]of entries)fn(time);},
  drain(){for(let i=0;rafs.size&&i<100;i++)this.step(i*1200);assert.equal(rafs.size,0,'RAF queue must terminate');},
  listenerCount(){return[...listeners.values()].reduce((n,set)=>n+set.size,0);}};
}
const standalone=environment().api;
const normalize=value=>JSON.parse(JSON.stringify(value));
function scenesFor(row){return standalone.receiptScenes(row.after.presentation,row.after.game.battle.id,row.after.revision);}
function soldierLibrary(){
 const actions=['idle','march','ready','attack','guard','hit','retreat','defeat'];
 return{schema:'tk2-soldier-actions-v1',scale:4,actions,types:Object.fromEntries(Object.entries({infantry:16,archer:16,cavalry:24}).map(([type,size])=>[type,Object.fromEntries(['friendly','enemy'].map(side=>[side,{path:`/assets/battle-enhanced/soldiers-${type}-${side}.png`,facing:'right',width:size*4*8,height:size*4,logical_width:size,logical_height:size,frames:actions.map((action,i)=>({action,source_rect:[i*size*4,0,size*4,size*4]}))}]))]))};
}
function enhancedSoldiers(native,soldiers=soldierLibrary()){
 const sprites=Object.fromEntries(['attack_formation','attack_formation_enemy'].map(kind=>[kind,{frames:native.sprites[kind].frames.map((f,i)=>({path:`/assets/battle-enhanced/${kind}-${i}.png`,width:512,height:640,logical_width:128,logical_height:160}))}]));
 return{schema:'tk2-battle-enhanced-v1',scale:4,backgrounds:{},sprites,duelists:{},soldiers};
}
const watchdog=setTimeout(()=>{console.error('Battle scene playback did not resolve within 20 seconds');process.exitCode=1;},20000);
(async()=>{
 const accepted=new Map(actual.rows.map(row=>[row.key,scenesFor(row)]));
 for(const tactic of actual.tactics){const row=actual.rows.find(r=>r.key==='tactic:'+tactic.effect),scenes=accepted.get(row.key);assert(scenes.length,`Actual tactic ${tactic.id}/${tactic.effect} must not be discarded`);assert.equal(scenes[0].tactic,tactic.id);assert.equal(scenes[0].effect,tactic.effect);}
 assert.equal(actual.tactics.length,16);assert(accepted.get('tactic:strike').length,'要撃 uses strike');
 const attack=accepted.get('attack');assert.equal(attack[0].kind,'attack');assert.equal(attack.length,2,'A surviving ordinary target immediately returns a blow in the same exchange');
 assert.equal(attack[1].kind,'attack');assert.equal(attack[1].counter,true);assert.equal(attack[1].actor,attack[0].target);assert.equal(attack[1].target,attack[0].actor);assert.deepEqual(normalize(attack[1].before),normalize(attack[0].after));
 assert(accepted.get('side_handoff').some(s=>s.counter),'A real whole-side handoff retains authoritative enemy action scenes');
 const chain=accepted.get('ambush');assert.equal(chain[0].kind,'ambush');assert.equal(chain[1].kind,'attack');assert.deepEqual(normalize(chain[0].after),normalize(chain[1].before),'Ambush damage must not be replayed as attack damage');
 assert(accepted.get('retreat').length,'Actual retreat permits null actor/target');
 assert.equal(accepted.get('stunned')[0].skipped,true);assert.equal(accepted.get('failure')[0].success,false);
 assert.equal(typeof accepted.get('mixed')[0].actor,'string');
 assert.equal(accepted.get('duel_desperate_success')[0].move,'desperate');assert.equal(accepted.get('duel_desperate_success')[0].success,true);
 assert.equal(accepted.get('duel_desperate_failure')[0].success,false);assert.equal(accepted.get('duel_desperate_reply')[0].reply,'desperate');
 for(const row of actual.rows){
  const original=JSON.stringify(row),scenes=accepted.get(row.key);assert(scenes.length,row.key);
  for(const scene of scenes){
   const deltas=standalone.changes(scene);
   for(const delta of deltas){const before=scene.before.units.find(u=>u.id===delta.id),after=scene.after.units.find(u=>u.id===delta.id);for(const field of ['troops','health','energy','guard','stunned'])assert.equal(delta[field],after[field]-before[field]);}
  }
  assert.equal(JSON.stringify(row),original,'Receipt validation and differences are read-only');
 }
 const first=actual.rows.find(r=>r.key==='attack'),bid=first.after.game.battle.id,revision=first.after.revision;
 // Same-family markers use canonical names, within each army independently.
 {
  const names=['刘备','劉表','张飞','張郃','诸葛亮','諸葛瑾','公孙瓒','公孫度','司马懿','司馬昭','夏侯惇','夏侯渊','夏侯恩','夏承','司宏','张','𠮷野','趙雲'];
  const attackerIds=new Set([0,1,2,3,10,11,12,13,15,17]);
  const units=names.map((_,id)=>({id,side:attackerIds.has(id)?'attackers':'defenders'})),expected=['备','表','飞','郃','亮','瑾','瓒','度','懿','昭','惇','渊','恩','夏','司','张','𠮷','趙'];
  const original=JSON.stringify(units),markers=standalone.markerLabels(units,id=>names[id]);
  assert.deepEqual(Array.from(markers.values()),expected,'Shared surname uses final full Unicode character; compound surnames are not confused with single-character families');
  const localized=['劉備','劉表','張飛','張郃','諸葛亮','諸葛瑾','公孫瓚','公孫度','司馬懿','司馬昭','夏侯惇','夏侯淵','夏侯恩','夏承','司宏','張','𠮷野','趙雲'];
  const japanese=standalone.markerLabels(units,id=>names[id],id=>localized[id]);
  assert.equal(japanese.get(0),'備');assert.equal(japanese.get(2),'飛');assert.equal(japanese.get(11),'淵');
  assert.equal(japanese.get(13),'夏','A lone夏 is not grouped with夏侯');assert.equal(japanese.get(14),'司','A lone司 is not grouped with司馬');
  assert.equal(JSON.stringify(units),original,'Marker labels are read-only');
  assert.equal(standalone.familyName(' 皇甫嵩 '),'皇甫');assert.equal(standalone.familyName('公仇称'),'公仇');
  const gongNames=['公仇称','公孙瓒','公孫度'];assert.deepEqual(Array.from(standalone.markerLabels(gongNames.map((_,id)=>({id,side:'attackers'})),id=>gongNames[id]).values()),['公','瓒','度'],'公仇 stays distinct from the 公孫 family');
 assert.equal(standalone.familyName('毌丘俭'),'毌丘');
  const zhongNames=['钟离牧','鍾離斐','钟会'];assert.deepEqual(Array.from(standalone.markerLabels(zhongNames.map((_,id)=>({id,side:'attackers'})),id=>zhongNames[id]).values()),['牧','斐','钟'],'鍾離 and単姓鍾 remain distinct families');
 }
 {
  const names=['张飞','張遼','張郃','张绣'],a='attackers',d='defenders';
  for(const [sides,expected]of [
   [[a,d],['张','張']],
   [[a,d,a],['飞','張','郃']],
   [[a,d,d],['张','遼','郃']],
   [[a,d,a,d],['飞','遼','郃','绣']]
  ]){
   const units=sides.map((side,id)=>({id,side,troops:300})),original=JSON.stringify(units);
   assert.deepEqual(Array.from(standalone.markerLabels(units,id=>names[id]).values()),expected,'Only same-side surname duplicates change that army’s markers');
   assert.equal(JSON.stringify(units),original,'Same-side grouping preserves the unit state');
  }
  const routed=[{id:0,side:a,troops:300},{id:1,side:d,troops:300},{id:2,side:a,troops:0}];
  assert.deepEqual(Array.from(standalone.markerLabels(routed,id=>names[id]).values()),['飞','張','郃'],'Routed teammates still have flags and remain part of their own surname group');
  const compound=['诸葛亮','諸葛瑾','諸葛誕'],mixed=[{id:0,side:a},{id:1,side:d},{id:2,side:a}];
  assert.deepEqual(Array.from(standalone.markerLabels(mixed,id=>compound[id],id=>['諸葛亮','諸葛瑾','諸葛誕'][id]).values()),['亮','諸','誕'],'Canonical compound surnames are grouped per side before localized display');
  assert.deepEqual(Array.from(standalone.markerLabels([{id:0,side:a},{id:1,side:a}],id=>['劉𠮷','刘表'][id]).values()),['𠮷','表'],'Final markers retain full Unicode characters');
 }
 // A visible normal strike has distinct approach, contact, recoil and result
 // stages, using no random sampling and resolving damage from the receipt only.
 {
  assert.equal(standalone.duration(accepted.get('attack')[0]),2200);
  assert.equal(standalone.attackStage(0).phase,'approach');assert.equal(standalone.attackStage(.15).shift,20);
  assert.equal(standalone.attackStage(.4).phase,'clash');assert.equal(standalone.attackStage(.4).resolved,false);
  assert.equal(standalone.attackStage(.6).resolved,true);assert.equal(standalone.attackStage(.75).phase,'recoil');
  assert.equal(standalone.attackStage(1).phase,'result');assert.equal(standalone.attackStage(1).shift,0);
  assert.equal(standalone.attackStage(.4,true).phase,'result');assert.equal(standalone.attackStage(.4,true).shift,0);
 }
 // Movement receipts contain the server's full legal path, not an invented
 // straight line between two final coordinates. A unit visibly leaves its
 // source before reaching the committed destination; cancelling the replay
 // restores the same final state without another API command or RNG draw.
 {
  const row=actual.rows.find(r=>r.key==='move_first'),movement=accepted.get('move_first')[0],path=movement.move.path;
  assert.equal(movement.kind,'move');assert.equal(movement.target,null);assert(path.length>=3);assert(standalone.validMovement(movement.move));
  assert.deepEqual(normalize(path[0]),row.before.game.battle.extended.tactical.positions[String(movement.actor)]);
  assert.deepEqual(normalize(path.at(-1)),row.after.game.battle.extended.tactical.positions[String(movement.actor)]);
  assert.deepEqual(normalize(movement.before),normalize(movement.after),'Moving flags alone does not alter soldier snapshots');
  assert.equal(row.before.game.rng.draws,row.after.game.rng.draws);
  const initial=standalone.movementStage(movement,0),last=standalone.movementStage(movement,1);
  assert.equal(initial.x,path[0].x*16+8);assert.equal(last.x,path.at(-1).x*16+8);assert.equal(last.index,path.length-1);
  for(const mutate of [m=>m.path[1].x=31,m=>m.path[1].y=.5,m=>m.path[1]={...m.path[0]},m=>m.path[1]={x:30,y:18},m=>m.cost=0,m=>m.cost=61,m=>m.map_id='other',m=>m.path[0].run='execute']){
   const bad=clone(row.after.presentation);mutate(bad.scenes[0].move);assert.equal(standalone.receiptScenes(bad,row.after.game.battle.id,row.after.revision).length,0);
  }
  const original=JSON.stringify(row),env=environment(),navigated=[],scene=env.api.create({onNavigate:(...p)=>navigated.push(p)});
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after,{actor:movement.actor});const play=scene.play();env.step(0);
  assert.equal(env.host.dataset.battleSceneMode,'movement');assert.equal(env.surface.width,1984);assert.equal(env.surface.height,1536);
  assert.equal(Number(env.host.dataset.battleMoveX),initial.x);assert.equal(Number(env.host.dataset.battleMoveY),initial.y);
  env.step(standalone.duration(movement)*.37);const middle=[env.host.dataset.battleMoveX,env.host.dataset.battleMoveY];
  assert.notDeepEqual(middle,[String(initial.x),String(initial.y)]);assert.notDeepEqual(middle,[String(last.x),String(last.y)]);
  env.doc.emit('game-language-change');assert.deepEqual([env.host.dataset.battleMoveX,env.host.dataset.battleMoveY],middle,'Changing language does not restart movement');
  env.surface.onkeydown({key:'ArrowRight',preventDefault(){throw Error('Active movement cannot accept a second command');}});assert.equal(navigated.length,0);
  scene.skip();await play;assert.equal(env.host.dataset.battleSceneMode,'tactical');assert.equal(env.host.dataset.battleMoveActor,'');assert.equal(scene.playing,false);assert.equal(env.rafs.size,0);
  assert.equal(JSON.stringify(row),original);scene.observe(row.kind,row.payload,row.before,row.after);assert.equal(scene.state().queued,0);scene.dispose();
  // A single AI action may move the same officer several times. Concatenate
  // these two independently genuine command receipts as a renderer-only
  // sequence fixture and verify that the second starts at the first endpoint.
  const second=actual.rows.find(r=>r.key==='move_second'),combined=clone(second.after);
  combined.presentation.scenes=[...clone(row.after.presentation.scenes),...clone(second.after.presentation.scenes)];
  const env2=environment(),sequence=env2.api.create(),frozen=JSON.stringify(combined);
  sequence.observe('battle_wait',{},row.before,combined);sequence.mount(env2.host,combined,{actor:movement.actor});const twice=sequence.play();env2.step(0);
  assert.equal(Number(env2.host.dataset.battleMoveX),initial.x,'Rewind uses both authoritative moves rather than the final coordinate');
  const firstDuration=standalone.duration(movement);env2.step(firstDuration+1);env2.step(firstDuration+2);
  assert.equal(Number(env2.host.dataset.battleMoveX),last.x);assert.equal(Number(env2.host.dataset.battleMoveY),last.y);
  env2.drain();await twice;assert.equal(env2.host.dataset.battleSceneMode,'tactical');assert.equal(JSON.stringify(combined),frozen);sequence.dispose();
  for(const mode of ['hidden','reduced','missingRAF','reset','leave','dispose']){
   const e=environment({reduced:mode==='reduced',missingRAF:mode==='missingRAF'}),s=e.api.create();if(mode==='hidden')e.doc.hidden=true;
   s.observe(row.kind,row.payload,row.before,row.after);s.mount(e.host,row.after);const p=s.play();
   if(['reset','leave','dispose'].includes(mode)){e.step(0);s[mode]();}await p;assert.equal(s.playing,false);assert.equal(e.rafs.size,0);s.dispose();
  }
  const malformedView=clone(row.after);malformedView.game.battle.extended.tactical.positions[String(movement.actor)]={...path[0]};
  const failed=environment(),invalid=failed.api.create();invalid.observe(row.kind,row.payload,row.before,malformedView);invalid.mount(failed.host,malformedView);assert.equal(invalid.state().queued,0,'A path whose endpoint disagrees with the committed position cannot animate');invalid.dispose();
 }
 // A congested AI command can legitimately contain many movements and
 // exchanges. This renderer-only overload sequence repeats real scene
 // records to exercise its hard wall-clock bound, without replaying any of
 // their combat results or claiming another actual gameplay command.
 {
  const overloaded=clone(first.after);overloaded.presentation.scenes=Array.from({length:40},()=>clone(accepted.get('attack'))).flat();
  const frozen=JSON.stringify(overloaded),env=environment(),scene=env.api.create();scene.observe('battle_wait',{},first.before,overloaded);scene.mount(env.host,overloaded);await scene.load();const play=scene.play();env.step(0);assert(scene.playing);env.step(16000);await play;
  assert.equal(scene.playing,false);assert.equal(scene.state().queued,0);assert.equal(env.rafs.size,0);assert.equal(env.host.dataset.battleSceneMode,'tactical');assert.equal(JSON.stringify(overloaded),frozen,'The replay budget drops only visual frames, never gameplay');scene.dispose();
 }

 //4× means4× each backing dimension, with the logical/CSS footprint unchanged.
 {const env=environment(),selected=[],scene=env.api.create({onSelect:(side,id)=>selected.push({side,id})}),row=clone(first.before),id=first.payload.actor;
  row.catalog.names[String(id)]='𠮷野';
  scene.mount(env.host,row,{actor:id});
  assert.equal(env.surface.width,1984);assert.equal(env.surface.height,1536);
  assert.equal(env.surface.style.width,'512px');assert.equal(env.surface.style.height,'396px');
  assert(env.transforms.some(t=>t.join(',')==='4,0,0,4,0,0'));
  const flags=env.texts.filter(t=>t.y<304);
  const markers=JSON.parse(env.host.dataset.battleMarkers),marker=markers.find(unit=>unit.id===id),point=standalone.unitPosition(row,id);
  assert(markers.every(unit=>['平','山','水'].includes(unit.type)&&unit.teams===Math.ceil(unit.troops/100)&&unit.teams<=10));
  assert(flags.some(t=>t.x===point.x*16+4&&t.y===point.y*16+3&&t.text===marker.type),'The flag shows the original affinity type in its top half');
  assert(flags.some(t=>t.x===point.x*16+4&&t.y===point.y*16+9&&t.text===String(marker.teams)),'The flag shows its actual number of hundred-person teams below the type');
  assert(!flags.some(t=>t.text==='𠮷'),'Names remain in the HUD rather than replacing tactical type/team markers');
  assert(scene.html().includes('width="1024" height="960"'));
  const rect=env.surface.getBoundingClientRect();env.surface.onclick({clientX:(point.x*16+8)*rect.width/496,clientY:(point.y*16+8)*rect.height/384});
  assert.deepEqual(selected,[{side:'actor',id}],'Pointer hit testing stays inCSS/logical coordinates after4× rendering');
  scene.dispose();
 }

 // Real tactical flags depend on affinity and current soldiers, never names
 // or which army the human controls. Keep routed zero-team flags and verify
 // the original saved positions, frozen view and campaign RNG are untouched.
 {
  const row=clone(actual.rows.find(r=>r.key==='tactic:fire').before),b=row.game.battle;
  assert(b.attackers.length===1&&b.defenders.length>=3,'Fixture must contain one attacker and several defenders');
  row.catalog.names[String(b.attackers[0].id)]='张飞';
  for(const [i,name]of ['張遼','张郃','趙雲'].entries())row.catalog.names[String(b.defenders[i].id)]=name;
  b.defenders[1].troops=0;
  for(const player of [b.attacker,b.defender]){
   const view=clone(row);view.game.player=player;freeze(view);const original=JSON.stringify(view);
   const env=environment(),scene=env.api.create();scene.mount(env.host,view);
   const flagText=(id,offset)=>{const p=standalone.unitPosition(view,id);return env.texts.find(t=>t.x===p.x*16+4&&t.y===p.y*16+offset)?.text;};
   for(const marker of JSON.parse(env.host.dataset.battleMarkers)){
    assert.equal(flagText(marker.id,3),marker.type);assert.equal(flagText(marker.id,9),String(marker.teams));
   }
   assert.equal(flagText(b.defenders[1].id,9),'0','A routed unit retains its location with an accurate zero-team flag');
   assert.equal(JSON.stringify(view),original,'Drawing flags preserves the entire campaign view and RNG');scene.dispose();
  }
 }

 for(const key of ['attack','mixed']){
  const row=actual.rows.find(r=>r.key===key),view=clone(row.after),id=row.payload.actor,foe=row.payload.target;
  view.game.extension={leaders:{current:id,ended:null}};view.game.officers[String(id)].loyalty=100;
  const env=environment(),scene=env.api.create(),selected={actor:id,target:foe};
  for(const locale of ['zh-Hant','ja']){
   env.i18n.locale=locale;const before=JSON.stringify(view);env.texts.length=0;scene.mount(env.host,view,selected);
   assert(env.texts.some(t=>t.x===184&&t.y===335&&t.text==='忠 --'),key+' current ruler HUD must display the literal --');
   const trainingLabel=(locale==='ja'?'練度':'訓練度')+' '+(view.game.battle.extended.support[String(id)].morale??70);
   assert(env.texts.some(t=>t.x===184&&t.y===346&&t.text===trainingLabel),key+' HUD labels the actual training value');
   assert.equal(JSON.stringify(view),before,'Battle HUD preserves current-ruler loyalty sentinel and RNG');
  }
  view.game.extension.leaders.current=foe;env.texts.length=0;scene.mount(env.host,view,selected);
  assert(env.texts.some(t=>t.x===184&&t.y===335&&t.text==='忠 100'),key+' ordinary officer with100 loyalty is not masked');scene.dispose();
 }
 for(const mutate of [r=>r.schema='unknown',r=>r.revision++,r=>r.scenes.push(...Array(193).fill(r.scenes[0])),r=>r.scenes[0].battle_id='another-battle',r=>r.scenes[0].kind='execute-command',r=>r.scenes[0].actor=true,r=>r.scenes[0].counter=1,r=>r.scenes[0].effect='invented',r=>r.scenes[0].before.units[0]=null,r=>r.scenes[0].before.units[0].troops=-1,r=>r.scenes[0].after.units[0].health=100,r=>r.scenes[0].after.units[0].energy=19,r=>r.scenes[0].after.units[1].id=r.scenes[0].after.units[0].id]){
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
  const manifests=['/assets/battle-original/index.json','/assets/battle-enhanced/index.json',...(row.after.game.battle.extended.siege?['/assets/siege-original/index.json']:[])];
  assert.equal(JSON.stringify(row),original,'Drawing and language changes cannot alter campaign, RNG or receipt');assert.deepEqual(env.requests,manifests,'Only the cached artwork manifests needed by the actual pending scene are permitted');
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
 // New soldier poses read only committed snapshots; they do not infer a new
 // saved troop class or create another damage/randomness calculation.
 {
  const strike=accepted.get('attack')[0],actor=strike.actor,target=strike.target;
  for(const [p,pose]of [[.1,'march'],[.33,'ready'],[.45,'attack'],[.8,'retreat'],[.99,'idle']])assert.equal(standalone.soldierActionPose(strike,actor,p),pose);
  assert.equal(standalone.soldierActionPose(strike,target,.45),'ready');assert.equal(standalone.soldierActionPose(strike,target,.6),'hit');
  const guarded=accepted.get('attack_guard')[0];assert.equal(standalone.soldierActionPose(guarded,guarded.target,.45),'guard');
  const defeated=accepted.get('attack_defeat')[0];assert.equal(standalone.soldierActionPose(defeated,defeated.target,.6),'defeat');
  const stunned=accepted.get('stunned')[0];assert.equal(standalone.soldierActionPose(stunned,stunned.actor,.45),'idle');
  const crossbow=accepted.get('tactic:crossbow')[0];assert.equal(standalone.soldierActionPose(crossbow,crossbow.actor,.4),'attack');
  const guard=accepted.get('tactic:guard')[0];assert.equal(standalone.soldierActionPose(guard,guard.actor,.4),'guard');
  const retreat=accepted.get('retreat')[0],own=retreat.before.units.find(u=>u.side===retreat.own),foe=retreat.before.units.find(u=>u.side!==retreat.own);
  assert.equal(standalone.soldierActionPose(retreat,own.id,.5),'retreat');assert.equal(standalone.soldierActionPose(retreat,foe.id,.5),'idle');
  assert.equal(standalone.soldierActionPose(null,actor,.4),'idle');
  for(const row of actual.rows){const before=JSON.stringify(row);for(const s of scenesFor(row))for(const u of s.before.units)for(const p of [0,.33,.45,.6,.8,1])assert(standalone.SOLDIER_ACTIONS.includes(standalone.soldierActionPose(freeze(s),u.id,p)));assert.equal(JSON.stringify(row),before);}
 }
 {
  const good=soldierLibrary();assert(standalone.validSoldierLibrary(good));
  for(const alter of [s=>s.scale=2,s=>s.actions.reverse(),s=>delete s.types.archer,s=>s.types.infantry.friendly.width--,s=>s.types.cavalry.enemy.facing='left',s=>s.types.archer.enemy.path='/assets/battle-enhanced/../escape.png',s=>s.types.infantry.friendly.frames[3].source_rect[0]++,s=>s.types.infantry.friendly.frames[3].action='unknown']){
   const bad=clone(good);alter(bad);assert.equal(standalone.validSoldierLibrary(bad),false,'Malformed soldier component must fail closed');
   const env=environment({manifest:nativeManifest,enhancedManifest:enhancedSoldiers(nativeManifest,bad)}),scene=env.api.create(),row=actual.rows.find(r=>r.key==='attack');
   scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);assert(await scene.load(),'Optional invalid soldier component must retain old enhanced artwork');const play=scene.play();for(let i=0;i<15;i++)await Promise.resolve();env.step(0);
   assert(!env.imageRequests.some(p=>p.includes('/soldiers-')));assert(env.draws.some(d=>d.src.startsWith('/assets/battle-enhanced/attack_formation')));scene.skip();await play;scene.dispose();
  }
 }
 for(const key of ['attack','attack_guard','attack_defeat','tactic:crossbow','tactic:guard','retreat']){
  const row=actual.rows.find(r=>r.key===key),before=JSON.stringify(row),hd=enhancedSoldiers(nativeManifest),env=environment({manifest:nativeManifest,enhancedManifest:hd}),scene=env.api.create();
  scene.observe(row.kind,row.payload,freeze(row.before),freeze(row.after));scene.mount(env.host,row.after);await scene.load();assert(!env.imageRequests.some(p=>p.includes('/soldiers-')),'Tactical view must not preload soldier atlases');
  const play=scene.play();for(let i=0;i<15;i++)await Promise.resolve();assert(scene.playing);env.step(0);assert.equal(new Set(env.imageRequests.filter(p=>p.includes('/soldiers-'))).size,6);assert(!env.imageRequests.some(p=>p.includes('/duel-actions-')));
  const first=scenesFor(row)[0],duration=env.api.duration(first);
  for(const p of [.33,.45,.6,.8,.95]){
   env.draws.length=0;env.scales.length=0;env.step(duration*p);
   const sprites=env.draws.filter(d=>d.src.includes('/soldiers-'));assert.equal(sprites.length,20,'Each army retains the mixed native-style ten-position composition');
   for(const type of ['infantry','archer','cavalry'])for(const palette of ['friendly','enemy']){
    const atlas=hd.soldiers.types[type][palette],unit=first.before.units.find(u=>u.id===(palette==='friendly'?(first.own==='attackers'?first.actor:first.target):(first.own==='attackers'?first.target:first.actor)))||first.before.units.find(u=>u.side===(palette==='friendly'?'attackers':'defenders'));
    let pose=standalone.soldierActionPose(first,unit.id,p);if(first.effect==='crossbow'&&unit.id===first.actor&&pose==='attack'&&type!=='archer')pose='ready';
    const draws=sprites.filter(d=>d.src===atlas.path);assert.equal(draws.length,type==='cavalry'?2:4,'Original composition is4 infantry,4 archers and2 cavalry per army');
    for(const d of draws){assert.deepEqual(d.args.slice(0,4),atlas.frames.find(f=>f.action===pose).source_rect);assert.equal(d.args.length,8,'Crop original4× source pixels directly without an intermediate tiny canvas');assert.deepEqual(d.args.slice(-2),[atlas.logical_width,atlas.logical_height]);}
   }
   assert.equal(env.scales.filter(s=>s[0]===-1&&s[1]===1).length,10,'Only the right-facing army is mirrored');
   const boxes=sprites.map(d=>{const[x,y,w,h]=d.args.slice(4),[a,b,c,e,tx,ty]=d.matrix,xx=[(a*x+c*y+tx)/4,(a*(x+w)+c*(y+h)+tx)/4],yy=[(b*x+e*y+ty)/4,(b*(x+w)+e*(y+h)+ty)/4];return{src:d.src,left:Math.min(...xx),right:Math.max(...xx),top:Math.min(...yy),bottom:Math.max(...yy)};});
   const friendly=boxes.filter(b=>b.src.endsWith('-friendly.png')),enemy=boxes.filter(b=>b.src.endsWith('-enemy.png'));assert.equal(friendly.length,10);assert.equal(enemy.length,10);
   const friendlyType=type=>friendly.filter(b=>b.src.includes('/soldiers-'+type+'-'));
   assert.deepEqual(friendlyType('infantry').map(b=>b.bottom),[32,48,64,80]);assert.deepEqual(friendlyType('archer').map(b=>b.bottom),[96,96,112,128]);assert.deepEqual(friendlyType('cavalry').map(b=>b.bottom),[160,160],'The original rear pair are cavalry, not archers');
   for(const a of friendly)for(const b of enemy)assert(a.right+8<=b.left,'Every opposing soldier image box remains separated by at least8logical pixels');
   if(key!=='retreat')for(const box of boxes)assert(box.left>=0&&box.right<=256&&box.top>=0&&box.bottom<=160,'Approaching soldiers remain within the original battle arena');
   if(key==='attack'&&p===.45){assert.equal(Math.max(...friendlyType('archer').map(b=>b.right)),108,'Archer approach remains capped at28');assert.equal(Math.max(...friendlyType('cavalry').map(b=>b.right)),124,'Wider rear cavalry stop at24 to retain the center gap');assert.equal(Math.max(...friendlyType('infantry').map(b=>b.right)),64+standalone.attackStage(p).shift,'Infantry retain the original full contact shift');}
   if(key==='retreat'){assert.equal(Math.max(...friendlyType('archer').map(b=>b.right)),80-Math.round(p*38));assert.equal(Math.max(...friendlyType('cavalry').map(b=>b.right)),100-Math.round(p*38),'Negative withdrawal retains the full outward distance');}
  }
  scene.skip();await play;scene.dispose();assert.equal(JSON.stringify(row),before,'Soldier playback cannot mutate authoritative views or RNG');assert.equal(env.rafs.size,0);assert.equal(env.timers.size,0);
 }
 for(const fallback of ['atlas','physical-size','native-formation','single-soldier']){
  const hd=enhancedSoldiers(nativeManifest),paths=Object.values(hd.soldiers.types).flatMap(t=>[t.friendly.path,t.enemy.path]),failed=fallback==='physical-size'?[]:[...paths];
  if(['native-formation','single-soldier'].includes(fallback))failed.push(...Object.values(hd.sprites).flatMap(r=>r.frames.map(f=>f.path)));
  if(fallback==='single-soldier')failed.push(...['attack_formation','attack_formation_enemy'].flatMap(k=>nativeManifest.sprites[k].frames.map(f=>f.path)));
  const env=environment({manifest:nativeManifest,enhancedManifest:hd,failedPaths:failed,badDimensions:fallback==='physical-size'?paths:[]}),scene=env.api.create(),row=actual.rows.find(r=>r.key==='attack');
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);await scene.load();const play=scene.play();for(let i=0;i<15;i++)await Promise.resolve();env.step(0);
  assert(!env.draws.some(d=>d.src.includes('/soldiers-')),'Failed or physically malformed soldier atlases are not rendered');
  assert(env.draws.some(d=>fallback==='single-soldier'?/\/(infantry|cavalry)-/.test(d.src):d.src.startsWith(`/assets/battle-${fallback==='native-formation'?'original':'enhanced'}/attack_formation`)),fallback+' retains the next original artwork layer');
  scene.skip();await play;scene.dispose();assert.equal(env.rafs.size,0);
 }
 {
  const row=actual.rows.find(r=>r.key==='attack'),env=environment({manifest:nativeManifest,enhancedManifest:enhancedSoldiers(nativeManifest),reduced:true}),scene=env.api.create();scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);await scene.load();await scene.play();assert(!env.imageRequests.some(p=>p.includes('/soldiers-')),'Reduced motion settles without waiting for additional artwork');assert.equal(env.rafs.size,0);assert.equal(scene.state().queued,0);scene.dispose();
 }
 // A real ordinary-attack receipt visibly renders both original soldier lines,
 // advances to contact, resolves authoritative losses, and returns without re-execution.
 for(const useEnhanced of [false,true]){
  const row=actual.rows.find(r=>r.key==='attack'),original=JSON.stringify(row),native=clone(nativeManifest);
  const makeFrame=(path)=>({path,logical_width:128,logical_height:160,width:512,height:640});
  const hd={schema:'tk2-battle-enhanced-v1',scale:4,backgrounds:{},duelists:{},sprites:{
   attack_formation:{frames:[makeFrame('/assets/battle-enhanced/formation-left-00.png'),makeFrame('/assets/battle-enhanced/formation-left-01.png')]},
   attack_formation_enemy:{frames:[makeFrame('/assets/battle-enhanced/formation-right-00.png'),makeFrame('/assets/battle-enhanced/formation-right-01.png')]}}};
  const env=environment({manifest:native,enhancedManifest:useEnhanced?hd:null}),scene=env.api.create();
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);await scene.load();const playback=scene.play();env.step(0);
  const wanted=side=>new Set(((useEnhanced?hd:native).sprites[side]?.frames||[]).map(f=>f.path));
  const left=wanted('attack_formation'),right=wanted('attack_formation_enemy');assert(left.size&&right.size,'Original attack formations must be available');
  env.draws.length=0;env.step(330);
  let l=env.draws.find(d=>left.has(d.src)),r=env.draws.find(d=>right.has(d.src));assert(l&&r,'Both opposing soldier formations are visible in the same frame');
  assert.deepEqual(l.args,[20,0,128,160]);assert.deepEqual(r.args,[108,0,128,160]);
  env.draws.length=0;env.step(880);l=env.draws.find(d=>left.has(d.src));r=env.draws.find(d=>right.has(d.src));
  assert(l&&r);assert(l.args[0]>=39&&l.args[0]<=41);assert(r.args[0]>=87&&r.args[0]<=89,'Opposed troops meet during the clash');
  env.draws.length=0;env.step(2090);l=env.draws.find(d=>left.has(d.src));r=env.draws.find(d=>right.has(d.src));assert.equal(l.args[0],0);assert.equal(r.args[0],128,'Surviving formations withdraw to native positions');
  scene.skip();await playback;assert.equal(scene.state().queued,0);assert.equal(env.rafs.size,0);assert.equal(JSON.stringify(row),original,'Attack animation is presentation only');
  scene.observe(row.kind,row.payload,row.before,row.after);assert.equal(scene.state().queued,0,'Skip cannot replay the same committed attack');scene.dispose();
 }
 // Starting the first attack during asynchronous artwork loading waits for
 // the original formations instead of spending the whole action on placeholders.
 {
  const env=environment({manifest:nativeManifest}),scene=env.api.create(),row=actual.rows.find(r=>r.key==='attack');
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);const playback=scene.play();
  assert.equal(scene.state().assetStatus,'loading');assert.equal(env.rafs.size,0);assert.equal(scene.playing,false);
  await scene.load();await Promise.resolve();assert(scene.playing);env.step(0);
  assert.equal(env.nodes['[data-battle-scene-title]'].textContent,'部隊對陣');
  assert(env.draws.some(d=>/attack_formation/.test(d.src)),'Artwork is present before the first timed frame');
  scene.skip();await playback;scene.dispose();assert.equal(env.timers.size,0);assert.equal(env.rafs.size,0);
 }
 // Visibility/reduced-motion can change while the first artwork fetch is
 // pending. Settle instead of scheduling a background RAF after that await.
 for(const mode of ['hidden','reduced']){
  const env=environment({manifest:nativeManifest}),sounds=[],settled=[],outcomes=[],scene=env.api.create({onSound:s=>sounds.push(s),onSettled:()=>settled.push(true),onOutcome:cue=>outcomes.push(cue)}),row=actual.rows.find(r=>r.key==='attack');
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);scene.deferOutcome('committed');const playback=scene.play();assert.equal(scene.state().assetStatus,'loading');
  if(mode==='hidden'){env.doc.hidden=true;env.doc.emit('visibilitychange');}else env.setReduced(true);
  await scene.load();await playback;assert.equal(env.rafs.size,0);assert.equal(scene.playing,false);assert.equal(scene.state().queued,0);assert.deepEqual(outcomes,['committed']);
  assert.equal(sounds.length,mode==='hidden'?0:1);assert.equal(settled.length,mode==='hidden'?0:1);scene.dispose();assert.equal(env.timers.size,0);
 }
 // Failure of the new formation images still leaves native unit sprites and
 // the already-committed result available, without a second command or roll.
 {
  const rows=['attack_formation','attack_formation_enemy'].flatMap(k=>nativeManifest.sprites[k].frames),env=environment({manifest:nativeManifest,failedPaths:rows.map(f=>f.path)}),scene=env.api.create(),row=actual.rows.find(r=>r.key==='attack');
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);await scene.load();env.draws.length=0;
  const playback=scene.play();env.step(0);assert(env.draws.some(d=>/\/(infantry|cavalry)-/.test(d.src)),'Missing formation falls back to retained original soldier cutouts');
  scene.skip();await playback;scene.dispose();assert.equal(env.rafs.size,0);assert.equal(env.timers.size,0);
 }
 // Enhanced sprites use their logical dimensions, prefer actual4× source pixels,
 // bind both participants separately, and fall back to the original same scene.
 {
  const row=actual.rows.find(r=>r.key==='duel_start');assert(row.after.game.battle.extended.duel);
  const ids=row.after.game.battle.extended.duel;
  const frame=(path,w,h)=>({path,width:w*4,height:h*4,logical_width:w,logical_height:h,anchor:{x:w/2,y:h}});
  const aPath='/assets/battle-enhanced/dual_swords-white.png',tPath='/assets/battle-enhanced/spear-black.png';
  const enhanced={schema:'tk2-battle-enhanced-v1',scale:4,backgrounds:{plain:frame('/assets/battle-enhanced/plain.png',256,160)},sprites:{},duelists:{dual_swords:{white:{frames:[frame(aPath,96,96)]}},spear:{black:{frames:[frame(tPath,96,96)]}}}};
  const profiles={
   [ids.actor]:{weapon:'dual_swords',horse:'white',weapon_label:{'zh-Hant':'雙股劍',ja:'双股剣'},horse_label:{'zh-Hant':'的盧',ja:'的盧'}},
   [ids.target]:{weapon:'spear',horse:'black',weapon_label:{'zh-Hant':'長槍',ja:'長槍'},horse_label:{'zh-Hant':'黑馬',ja:'黒馬'}}
  };
  for(const failed of [false,true]){
   let loaded=0;const env=environment({manifest:nativeManifest,enhancedManifest:enhanced,duelAppearance:{load:async()=>loaded++,profile:(catalog,id)=>profiles[id]},failedPaths:failed?[aPath,tPath]:[]}),scene=env.api.create(),before=JSON.stringify(row.after);
   scene.mount(env.host,row.after);assert(await scene.load());assert.equal(loaded,1);env.draws.length=0;env.texts.length=0;
   env.doc.emit('game-language-change');
   if(!failed){
    assert(env.texts.some(t=>t.y===50&&t.text==='雙股劍'));assert(env.texts.some(t=>t.y===57&&t.text==='的盧'));
    assert(env.texts.some(t=>t.y===50&&t.text==='長槍'));assert(env.texts.some(t=>t.y===57&&t.text==='黑馬'));
    assert(env.nodes['[data-battle-description]'].textContent.includes('雙股劍 的盧'),'Equipment remains available to screen readers');
   }else{
    assert.equal(env.texts.filter(t=>t.y===50&&t.text==='原版備用圖').length,2);assert(!env.texts.some(t=>t.y===50&&['雙股劍','長槍'].includes(t.text)));
    assert(!env.nodes['[data-battle-description]'].textContent.includes('雙股劍'),'Fallback cannot describe mismatched native equipment as the iconic set');
    assert(env.nodes['[data-battle-description]'].textContent.includes('原版備用圖 通用騎將'));
   }
   if(!failed){assert(env.draws.some(d=>d.src===aPath));assert(env.draws.some(d=>d.src===tPath));assert(env.draws.filter(d=>[aPath,tPath].includes(d.src)).every(d=>d.args.slice(-2).join(',')==='96,96'));}
   else{assert(!env.draws.some(d=>[aPath,tPath].includes(d.src)));assert(env.draws.some(d=>/battle-original\/duelist/.test(d.src)),'Missing enhanced riders retain original mounted artwork');}
   env.i18n.locale='ja';env.texts.length=0;env.doc.emit('game-language-change');if(!failed){assert(env.texts.some(t=>t.y===50&&t.text==='双股剣'));assert(env.texts.some(t=>t.y===57&&t.text==='黒馬'));}else assert.equal(env.texts.filter(t=>t.y===50&&t.text==='原作予備画像').length,2);
   assert.equal(JSON.stringify(row.after),before,'Equipment and high resolution rendering cannot change state, stats or RNG');
   scene.dispose();assert.equal(env.timers.size,0);assert.equal(env.rafs.size,0);
  }
 }
 // Each fighter follows its own authoritative move/reply. Hurt and defeat
 // poses come only from actual health/roster deltas, never an animation roll.
 {
  const base=clone(accepted.get('duel_action')[0]),moves=['strike','guard','feint','desperate'];
  for(const move of moves)for(const reply of moves){
   const s=clone(base);s.move=move;s.reply=reply;s.after=clone(s.before);
   assert.equal(standalone.duelActionPose(s,s.actor,.35),move);
   assert.equal(standalone.duelActionPose(s,s.target,.35),reply);
   assert.equal(standalone.duelActionPose(s,s.actor,.05),'idle');
   s.after.units.find(u=>u.id===s.target).health-=3;
   assert.equal(standalone.duelActionPose(s,s.target,.65),'hit');
   assert.equal(standalone.duelActionPose(s,s.actor,.65),move,'A hit against the target cannot change the actor pose');
   s.after.units.find(u=>u.id===s.target).health=0;
   assert.equal(standalone.duelActionPose(s,s.target,.75),'defeat');
  }
  const s=clone(base);s.move='withdraw';s.reply=null;s.after=clone(s.before);
  assert.equal(standalone.duelActionPose(s,s.actor,.4),'withdraw');assert.equal(standalone.duelActionPose(s,s.target,.4),'idle');
  assert.equal(standalone.duelMotion('guard',.5),0);assert(standalone.duelMotion('withdraw',.5)<0);
  assert(standalone.duelMotion('strike',.5)>standalone.duelMotion('strike',.5,true),'A bow fires from its position instead of charging into melee');
  assert(standalone.duelMotion('desperate',.5)>standalone.duelMotion('strike',.5));
 }
 // Complete eight-action atlases are lazy: the cartesian library stays on the
 // server, while the two selected riders alone fetch their4096×384 source.
 {
  const row=actual.rows.find(r=>r.key==='duel_guard'),ids=row.before.game.battle.extended.duel,appearance=require('../game/duel-appearance.js');
  const labels=value=>({'zh-Hant':value,ja:'日'+value}),atlas=name=>({path:'/assets/battle-enhanced/atlas-'+name+'.png',width:4096,height:384,logical_width:128,logical_height:96,anchor:{x:64,y:96},frames:standalone.DUEL_ACTIONS.map((action,i)=>({action,source_rect:[i*512,0,512,384]}))});
  const a=atlas('spear-white'),t=atlas('dual-ji-black'),bow=atlas('bow-white'),blackBow=atlas('bow-black'),unused=atlas('guding-chestnut');
  const enhanced={schema:'tk2-battle-enhanced-v1',scale:4,backgrounds:{plain:{path:'/assets/battle-enhanced/plain.png',width:1024,height:640,logical_width:256,logical_height:160}},sprites:{},duelists:{},action_atlases:{spear:{white:a},'dual-ji':{black:t},bow:{white:bow,black:blackBow},'guding-dao':{chestnut:unused}}};
  assert(standalone.validActionAtlas(a));
  for(const mutate of [r=>r.path='../file.png',r=>r.width=384,r=>r.anchor.x=-1,r=>r.frames.pop(),r=>r.frames[2].action='strike',r=>r.frames[0].source_rect=[3072,0,384,384]]){const bad=clone(a);mutate(bad);assert(!standalone.validActionAtlas(bad));}
  const profiles=appearance.validate({schema:'tk2-duel-appearances-v1',profiles:{'actor-art':{name:'甲',weapon:'spear',horse:'white',weapon_variants:[{key:'bow',label:labels('弓')}],horse_variants:[{key:'black',label:labels('黑馬')}]},'target-art':{name:'乙',weapon:'dual-ji',horse:'black'}}});
  const appearances={load:async()=>true,profile:(catalog,id,choice)=>appearance.select(profiles[id===ids.actor?'actor-art':'target-art'],choice)},env=environment({manifest:nativeManifest,enhancedManifest:enhanced,duelAppearance:appearances}),scene=env.api.create(),original=JSON.stringify(row);
  scene.mount(env.host,row.before);await scene.load();await Promise.resolve();
  assert.deepEqual([...new Set(env.imageRequests.filter(p=>p.includes('/atlas-')))].sort(),[a.path,t.path].sort(),'Only both current default rider atlases load');
  assert(!env.nodes['[data-duel-loadouts]'].hidden);assert(env.nodes['[data-duel-loadouts]'].innerHTML.includes('data-duel-field="weapon"'));
  assert(!scene.chooseDuelAppearance(ids.target,{weapon:'bow'}),'Another rider cannot borrow a globally valid weapon');
  assert(!scene.chooseDuelAppearance(999999,{horse:'black'}));
  assert(scene.chooseDuelAppearance(ids.actor,{weapon:'bow'}));await Promise.resolve();await Promise.resolve();
  assert(env.imageRequests.includes(bow.path));assert(!env.imageRequests.includes(blackBow.path));assert(!env.imageRequests.includes(unused.path));
  env.nodes['[data-duel-loadouts]'].onchange({target:{dataset:{duelPerson:String(ids.actor),duelField:'horse'},value:'black'}});await Promise.resolve();await Promise.resolve();
  assert(env.imageRequests.includes(blackBow.path),'The cosmetic selector changes just the chosen rider');
  env.i18n.locale='ja';env.doc.emit('game-language-change');assert(env.nodes['[data-duel-loadouts]'].innerHTML.includes('value="black" selected'),'Language changes retain the selected loadout');
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);const playback=scene.play();await Promise.resolve();await Promise.resolve();
  assert(scene.playing);assert(!scene.chooseDuelAppearance(ids.actor,{horse:'white'}),'Do not swap art while a committed exchange is playing');
  env.step(0);env.draws.length=0;env.step(350);
  const action=accepted.get('duel_guard')[0],leftPose=standalone.duelActionPose(action,ids.actor,.35),rightPose=standalone.duelActionPose(action,ids.target,.35);
  const ad=env.draws.find(d=>d.src===blackBow.path),td=env.draws.find(d=>d.src===t.path);assert(ad&&td,'Both selected action atlases draw');
  assert.equal(ad.args[0],standalone.DUEL_ACTIONS.indexOf(leftPose)*512);assert.equal(td.args[0],standalone.DUEL_ACTIONS.indexOf(rightPose)*512);
  assert.deepEqual(ad.args.slice(1,4),[0,512,384]);assert.deepEqual(ad.args.slice(-2),[128,96]);
  scene.skip();await playback;assert.equal(JSON.stringify(row),original,'Selectors, language, atlas playback and skip never change the save or RNG');
  const shot=actual.rows.find(r=>r.key==='duel_action'),shotState=JSON.stringify(shot);scene.observe(shot.kind,shot.payload,shot.before,shot.after);scene.mount(env.host,shot.after);
  const firing=scene.play();await Promise.resolve();env.step(0);env.rectangles.length=0;env.draws.length=0;env.step(400);
  assert(env.rectangles.some(r=>r.color==='#fff0b0'),'An actual bow strike releases a visible arrow');
  assert(env.draws.some(d=>d.src===blackBow.path&&d.args[0]===512),'Bow release selects its strike picture, not a sword or idle frame');
  scene.skip();await firing;assert.equal(JSON.stringify(shot),shotState,'Bow release cannot add a damage roll or an engine command');
  scene.reset();scene.mount(env.host,row.before);await Promise.resolve();assert(env.nodes['[data-duel-loadouts]'].innerHTML.includes('value="spear" selected'),'New/load reset clears cosmetic choices');scene.dispose();
  assert.equal(env.timers.size,0);assert.equal(env.rafs.size,0);
  // A failed new atlas keeps the older exact weapon/mount two-pose artwork.
  const legacyPath='/assets/battle-enhanced/legacy-spear-white.png',fallback=clone(enhanced);fallback.duelists.spear={white:{frames:[{path:legacyPath,width:384,height:384,logical_width:96,logical_height:96,anchor:{x:48,y:96}}]}};
  const failed=environment({manifest:nativeManifest,enhancedManifest:fallback,duelAppearance:appearances,failedPaths:[a.path]}),kept=failed.api.create();kept.mount(failed.host,row.before);await kept.load();for(let i=0;i<8;i++)await Promise.resolve();
  assert(failed.draws.some(d=>d.src===legacyPath),'Missing action atlas retains the matching previous rider instead of blocking the duel');kept.dispose();assert.equal(failed.timers.size,0);
 }
 for(const p of ['/assets/battle-enhanced/dual_swords-white.png','/assets/battle-enhanced/tactical.png'])assert(standalone.validEnhancedAssetPath(p));
 for(const p of ['/assets/battle-enhanced/../escape.png','/assets/battle-enhanced/sub/file.png','https://example.com/a.png','/assets/battle-original/duelist.png','/assets/battle-enhanced/a.png?x=1'])assert(!standalone.validEnhancedAssetPath(p));

 for(const key of ['attack','tactic:strike','retreat']){
  const row=actual.rows.find(r=>r.key===key),env=environment({manifest:nativeManifest}),scene=env.api.create();
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);assert(await scene.load());
  const playback=scene.play();env.step(0);env.draws.length=0;env.texts.length=0;env.rectangles.length=0;env.step(env.api.duration(accepted.get(key)[0])*.6);
  const armyPaths=new Set(['infantry','infantry_enemy','cavalry','attack_formation','attack_formation_enemy'].flatMap(kind=>(nativeManifest.sprites[kind]?.frames||[]).map(f=>f.path)));
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
 // Full recovered city maps retain native coordinates while close-ups keep
 // their original layout. Use shipped ROM-derived metadata, not a fake map.
 {
  const library=JSON.parse(fs.readFileSync(path.join(ROOT,'game/assets/battlefields/index.json'),'utf8')),
   bindings=JSON.parse(fs.readFileSync(path.join(ROOT,'game/config/battlefield-city-bindings.json'),'utf8')),
   selector=require('../game/battlefields.js'),selected=(city)=>selector.select(city,library,bindings),
   fields={load:async()=>library,resolve:selected,label:(city,locale)=>{const row=selected(city);return locale==='ja'?row.label_ja:row.label_tc;}};
  const row=actual.rows.find(r=>r.key==='attack'),original=JSON.stringify(row),chosen=selected(row.before.game.battle.target),
   env=environment({manifest:nativeManifest,battlefields:fields}),calls=[],scene=env.api.create({onSelect:(...args)=>calls.push(args)});
  scene.mount(env.host,row.before);await scene.load();for(let i=0;i<5;i++)await Promise.resolve();
  assert.equal(env.surface.width,1984);assert.equal(env.surface.height,1536);
  assert.deepEqual(env.imageRequests.filter(p=>p.startsWith('/assets/battlefields/')),[chosen.field.path],'Only the chosen city image is fetched');
  env.rectangles.length=0;scene.mount(env.host,row.before);
  const flags=env.rectangles.filter(r=>r.w===12&&r.h===12&&r.color==='#000000');
  const units=[...row.before.game.battle.attackers,...row.before.game.battle.defenders];assert.equal(flags.length,units.length);
  const cells=flags.map(r=>[Math.floor((r.x+6)/16),Math.floor((r.y+6)/16)]);
  assert.equal(new Set(cells.map(p=>p.join(':'))).size,units.length,'Deployment does not overlap');
  for(const[index,[x,y]]of cells.entries()){assert(x>=0&&x<31&&y>=0&&y<19);assert.deepEqual([x,y],Object.values(standalone.unitPosition(row.before,units[index].id)),'Flag cells come only from the authoritative saved positions');}
  const own=row.before.game.battle.attacker===row.before.game.player?'attackers':'defenders',id=row.before.game.battle[own].find(u=>u.troops>0).id,
   index=units.findIndex(u=>u.id===id),flag=flags[index],rect=env.surface.getBoundingClientRect();
  env.surface.onclick({clientX:(flag.x+6)*rect.width/496,clientY:(flag.y+6)*rect.height/384});assert.deepEqual(calls,[['actor',id]],'Full-map clicks use native map coordinates');
  env.surface.onclick({clientX:rect.width/2,clientY:rect.height*330/384});assert.equal(calls.length,1,'HUD clicks never select a unit');
  env.i18n.locale='ja';env.doc.emit('game-language-change');assert.equal(env.surface.width,1984);
  scene.observe(row.kind,row.payload,row.before,row.after);scene.mount(env.host,row.after);const playback=scene.play();await Promise.resolve();env.step(0);
  assert.equal(env.surface.width,1024);assert.equal(env.surface.height,960,'Attack cutscenes keep the native256x240 scene');
  scene.skip();await playback;assert.equal(env.surface.width,1984);assert.equal(env.surface.height,1536,'Skipping returns to the full city map');
  assert.equal(JSON.stringify(row),original,'Maps, deployment, selection, language and playback never change the save/RNG');scene.dispose();assert.equal(env.timers.size,0);
  const missing=environment({manifest:nativeManifest,battlefields:fields,failedPaths:[chosen.field.path]}),fallback=missing.api.create();fallback.mount(missing.host,row.before);await fallback.load();for(let i=0;i<5;i++)await Promise.resolve();
  assert.equal(missing.surface.width,1984);assert.equal(missing.surface.height,1536,'A missing bitmap retains the authoritative31x19 coordinate system');fallback.dispose();
 }
 // A routed flag releases its cell and cannot cover or intercept a live unit.
 {
  const value=clone(first.before),b=value.game.battle,actor=b.attackers[0].id,dead=b.defenders[0].id,p=b.extended.tactical.positions[actor];
  b.defenders[0].troops=0;b.extended.support[dead].health=0;b.extended.tactical.positions[dead]={...p};
  const env=environment(),selections=[],cells=[],directions=[],confirmed=[],scene=env.api.create({onSelect:(...args)=>selections.push(args),onCell:p=>cells.push(p),onNavigate:(...args)=>directions.push(args),onConfirmMove:()=>confirmed.push(true)}),before=JSON.stringify(value);
  scene.mount(env.host,value,{actor});const bodies=env.rectangles.filter(r=>r.w===10&&r.h===10&&r.x===p.x*16+3&&r.y===p.y*16+3);
  assert.deepEqual(bodies.map(r=>r.color),['#888888','#ffffff'],'Routed flags paint before live flags at the same saved cell');
  const rect=env.surface.getBoundingClientRect();env.surface.onclick({clientX:(p.x*16+8)*rect.width/496,clientY:(p.y*16+8)*rect.height/384});assert.deepEqual(selections,[['actor',actor]]);
  env.surface.onclick({clientX:30.5*16*rect.width/496,clientY:18.5*16*rect.height/384});assert.equal(cells.length,1,'An empty whole cell sends only a preview intent');
  env.surface.onkeydown({key:'ArrowRight',preventDefault(){}});env.surface.onkeydown({key:'Enter',preventDefault(){}});assert.deepEqual(directions,[[1,0]]);assert.equal(confirmed.length,1);
  assert.equal(JSON.stringify(value),before,'Grid selection and keyboard intents cannot mutate the campaign or sample RNG');scene.dispose();
 }
 for(const manifest of [null,{schema:'wrong',backgrounds:{},sprites:{}},{schema:'tk2-battle-original-v1',backgrounds:{plain:{path:'/assets/battle-original/../escape.png'}},sprites:{}}]){
  const env=environment({manifest}),scene=env.api.create();assert.equal(await scene.load(),false);assert.equal(scene.state().assetStatus,'unavailable');assert.equal(env.rafs.size,0);assert.equal(env.timers.size,0);scene.dispose();
 }
 console.log(`battle scenes: ${actual.rows.filter(row=>!row.source).length} real current command receipts plus ${actual.rows.filter(row=>row.source).length} explicit aggregate display-schema compatibility samples; all16effects, troop/team flags, strict schema/assets, read-only playback, revision/baseline lifecycle, skip/cancel/hidden/reduced-motion and RAF cleanup passed`);
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>clearTimeout(watchdog));
