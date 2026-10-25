/* Web Audio lifecycle, original scores, bounded voices and optional storage. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const{create,STORAGE_KEY}=require('../game/audio.js');
class Param{
 constructor(){this.events=[];}
 setValueAtTime(value,time){assert(Number.isFinite(value));assert(Number.isFinite(time));this.events.push(['set',value,time]);}
 linearRampToValueAtTime(value,time){assert(Number.isFinite(value));assert(Number.isFinite(time));this.events.push(['ramp',value,time]);}
}
class Node{
 constructor(){this.connections=[];this.disconnected=false;this.gain=new Param();}
 connect(target){this.connections.push(target);}
 disconnect(){this.disconnected=true;}
}
class Osc extends Node{
 constructor(ctx){super();this.ctx=ctx;this.frequency=new Param();this.stops=[];}
 start(time){this.started=time;}
 stop(time){this.stops.push(time);if(time<=this.ctx.currentTime)this.onended?.();}
}
class Context{
 static instances=[];
 constructor(){this.currentTime=0;this.state='suspended';this.destination={};this.nodes=[];this.oscillators=[];Context.instances.push(this);}
 createGain(){const node=new Node();this.nodes.push(node);return node;}
 createDynamicsCompressor(){const node=new Node();for(const key of ['threshold','knee','ratio','attack','release'])node[key]=new Param();this.nodes.push(node);return node;}
 createOscillator(){const node=new Osc(this);this.oscillators.push(node);return node;}
 async resume(){this.state='running';}
 async suspend(){this.state='suspended';}
 async close(){this.state='closed';}
}
function fixture(saved,options={}){
 const events=new Map(),doc={hidden:false,addEventListener:(key,fn)=>events.set(key,fn),removeEventListener:(key,fn)=>{if(events.get(key)===fn)events.delete(key);}};
 const store=new Map(saved?[[STORAGE_KEY,JSON.stringify(saved)]]:[]),storage={getItem:key=>store.get(key),setItem:(key,value)=>store.set(key,value)};
 let next=0;const timers=new Map();
 const audio=create({AudioContext:Context,document:doc,storage,setInterval:fn=>{timers.set(++next,fn);return next;},clearInterval:key=>timers.delete(key),...options});
 return{audio,events,doc,store,timers};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 const f=fixture(),{audio,timers}=f;
 assert.equal(Context.instances.length,0,'Loading the page must not create or start AudioContext');
 assert.equal(audio.play('click'),false);
 audio.setScene('strategy');assert.equal(Context.instances.length,0);assert.equal(timers.size,0);
 assert(await audio.unlock());const ctx=Context.instances.at(-1);
 assert.equal(ctx.state,'running');assert.equal(timers.size,1);assert(audio.getStatus().activeVoices>0);
 assert.equal(audio.getStatus().scene,'strategy');
 assert.equal(ctx.oscillators[0].frequency.events[0][1],440*Math.pow(2,(64-69)/12));
 assert.equal(ctx.oscillators[0].type,'square');assert(ctx.oscillators.some(node=>node.type==='triangle'));
 for(const node of ctx.oscillators){assert(node.started>=0);assert(node.stops[0]>node.started);}
 const firstMusic=[...ctx.oscillators];
 assert(await audio.unlock());assert.equal(Context.instances.length,1);assert.equal(timers.size,1);
 assert(audio.play('confirm'));const effectVoices=audio.getStatus().activeVoices-firstMusic.length;
 assert.equal(effectVoices,2);
 audio.setScene('battle');assert.equal(timers.size,1);
 assert(firstMusic.every(node=>node.disconnected),'Switching scenes must stop/disconnect all scheduled music');
 assert(ctx.oscillators.slice(firstMusic.length,firstMusic.length+2).every(node=>!node.disconnected),'Brief feedback may finish across scene changes');
 for(const value of ['menu','duel','strategy','battle']){
  audio.setScene(value);assert.equal(timers.size,1);assert.equal(audio.getStatus().scene,value);
 }
 audio.setScene('__proto__');assert.equal(audio.getStatus().scene,'battle');assert.equal(audio.play('__proto__'),false);
 // Clock jumps enqueue a small current window rather than old, missed notes.
 const beforeJump=ctx.oscillators.length;ctx.currentTime=600;[...timers.values()][0]();
 assert(ctx.oscillators.length-beforeJump<10);assert(ctx.oscillators.at(-1).started>=600);
 for(const effect of ['click','confirm','cancel','error','march','attack','tactic','victory','defeat','turn'])assert(audio.play(effect));
 for(let i=0;i<200;i++)audio.play('click');
 assert(audio.getStatus().activeVoices<45,'Repeated interaction sounds must remain bounded');
 const config=audio.configure({bgmVolume:5,sfxVolume:-1});assert.equal(config.bgmVolume,1);assert.equal(config.sfxVolume,0);
 assert.equal(audio.play('click'),false);config.bgmVolume=.42;assert.equal(audio.getSettings().bgmVolume,1,'Settings must return a copy');
 assert.deepEqual(JSON.parse(f.store.get(STORAGE_KEY)),{muted:false,bgmVolume:1,sfxVolume:0});
 audio.configure({bgmVolume:NaN,sfxVolume:Infinity});assert.equal(audio.getSettings().bgmVolume,1);assert.equal(audio.getSettings().sfxVolume,0);
 audio.configure({muted:true});assert.equal(timers.size,0);assert.equal(audio.getStatus().activeVoices,0);assert.equal(audio.play('click'),false);
 assert(ctx.oscillators.every(node=>node.disconnected));
 audio.configure({muted:false,sfxVolume:.5});assert.equal(timers.size,1);
 audio.configure({bgmVolume:0});assert.equal(timers.size,0);assert(audio.play('click'),'Effects remain available with music volume zero');
 audio.configure({bgmVolume:.3});assert.equal(timers.size,1);
 f.doc.hidden=true;f.events.get('visibilitychange')();await settle();
 assert.equal(timers.size,0);assert.equal(audio.getStatus().activeVoices,0);assert.equal(ctx.state,'suspended');assert.equal(audio.play('click'),false);
 f.doc.hidden=false;f.events.get('visibilitychange')();await settle();assert.equal(ctx.state,'running');assert.equal(timers.size,1);
 // Ended sources release their gain/oscillator references, without a scene change.
 const live=ctx.oscillators.filter(node=>!node.disconnected);for(const node of live)node.onended?.();
 assert.equal(audio.getStatus().activeVoices,0);assert(live.every(node=>node.disconnected));
 audio.play('victory');audio.dispose();await settle();assert.equal(timers.size,0);assert.equal(f.events.size,0);
 assert.equal(ctx.state,'closed');assert.equal(audio.getStatus().activeVoices,0);assert.equal(await audio.unlock(),false);
 assert.equal(audio.play('click'),false);audio.setScene('duel');audio.dispose();
 const persisted=fixture({muted:true,bgmVolume:.2,sfxVolume:.8});assert.deepEqual(persisted.audio.getSettings(),{muted:true,bgmVolume:.2,sfxVolume:.8});
 assert(await persisted.audio.unlock());assert.equal(persisted.timers.size,0);persisted.audio.dispose();
 const absent=create({AudioContext:null,document:null,storage:{getItem(){throw Error('private');},setItem(){throw Error('private');}}});
 assert.equal(absent.getStatus().supported,false);assert.equal(await absent.unlock(),false);assert.equal(absent.play('click'),false);
 assert.doesNotThrow(()=>absent.configure({muted:true}));absent.dispose();
 const broken=create({AudioContext:class{constructor(){throw Error('disabled');}},document:null,storage:null});
 assert.equal(await broken.unlock(),false);assert.equal(broken.play('click'),false);broken.dispose();
 // Original recordings replace the authored fallback only after real decoding.
 class BufferContext extends Context{
  async decodeAudioData(data){assert(data instanceof ArrayBuffer);return{duration:10};}
  createBufferSource(){const source=new Osc(this);source.start=(time,offset)=>{source.started=time;source.offset=offset;};this.oscillators.push(source);return source;}
 }
 const requests=[],track=slug=>({path:'/assets/audio/original/'+slug+'.mp3',kind:'original_rom_capture',loop_start:0,loop_end:2});
 const manifest={schema:'tk2-original-audio-v1',tracks:{menu:track('title'),strategy:track('strategy'),battle:{...track('battle'),path:'https://other.invalid/music.mp3'}}};
 const original=fixture(null,{AudioContext:BufferContext,fetch:async path=>{requests.push(path);return path.endsWith('.json')?{ok:true,json:async()=>manifest}:{ok:true,arrayBuffer:async()=>new ArrayBuffer(8)};}});
 assert.equal(requests.length,0,'Original assets also wait for the first audio unlock');
 assert(await original.audio.unlock());await settle();
 assert.deepEqual(requests,['/assets/audio/effects.json','/assets/audio/index.json','/assets/audio/original/title.mp3']);
 assert.equal(original.audio.getStatus().musicSource,'original');assert.equal(original.timers.size,0);
 const bc=Context.instances.at(-1),titleSource=bc.oscillators.at(-1);
 assert.equal(titleSource.loop,true);assert.equal(titleSource.loopStart,0);assert.equal(titleSource.loopEnd,2);assert.equal(titleSource.offset,0);
 original.audio.setScene('strategy');await settle();assert(titleSource.disconnected);
 assert.equal(original.audio.getStatus().musicSource,'original');assert.equal(original.audio.getStatus().originalTracks,2);
 bc.currentTime=1.5;
 original.audio.configure({muted:true});assert.equal(original.audio.getStatus().activeVoices,0);assert.equal(original.audio.getStatus().playing,false);
 original.audio.configure({muted:false});assert.equal(original.audio.getStatus().musicSource,'original');
 assert(Math.abs(bc.oscillators.at(-1).offset-1.49)<1e-8,'Unmuting an original track resumes its playhead');
 original.audio.setScene('battle');await settle();assert.equal(original.audio.getStatus().musicSource,'synthesized');
 assert(!requests.some(path=>path.startsWith('https:')),'Original media paths must remain within the pinned asset directory');
 original.audio.setScene('menu');assert.equal(original.audio.getStatus().musicSource,'original');assert.equal(requests.filter(path=>path.endsWith('title.mp3')).length,1);
 original.audio.dispose();assert.equal(original.audio.getStatus().activeVoices,0);assert.equal(original.timers.size,0);
 const unavailable=fixture(null,{AudioContext:BufferContext,fetch:async()=>({ok:false})});await unavailable.audio.unlock();await settle();
 assert.equal(unavailable.audio.getStatus().musicSource,'synthesized');unavailable.audio.dispose();
 let release;
 const late=fixture(null,{AudioContext:BufferContext,fetch:async path=>path.endsWith('.json')?{ok:true,json:async()=>manifest}:{ok:true,arrayBuffer:()=>new Promise(resolve=>{release=resolve;})}});
 await late.audio.unlock();await settle();late.audio.dispose();release(new ArrayBuffer(8));await settle();
 assert.equal(late.audio.getStatus().activeVoices,0);assert.equal(late.timers.size,0,'Late decoding must not restart disposed music');
 // Original one-shots take priority, share decoded assets across aliases and never loop.
 const effectRow=(cue,id)=>({kind:'original_rom_capture',path:'/assets/audio/original/effects/seq-'+cue+'.wav',request:{id}});
 const effects={schema:'tk2-original-effects-v1',effects:{click:effectRow('60',0x60),confirm:effectRow('62',0x62),cancel:effectRow('61',0x61),duel_withdraw:effectRow('61',0x61),tactic_88:effectRow('88',0x88),duel_strike:effectRow('68',0x68),error:{...effectRow('60',0x60),path:'https://other.invalid/error.wav'}}};
 const fetched=[],heard=[];
 const fetchEffects=async url=>{fetched.push(url);return url==='/assets/audio/effects.json'?{ok:true,json:async()=>effects}:url==='/assets/audio/index.json'?{ok:true,json:async()=>manifest}:{ok:true,arrayBuffer:async()=>new ArrayBuffer(8)};};
 const fx=fixture(null,{AudioContext:BufferContext,fetch:fetchEffects,onEffect:row=>heard.push(row)});
 await fx.audio.unlock();await settle();
 for(const id of ['click','confirm','cancel','duel_withdraw','tactic_88','duel_strike']){
  assert(fx.audio.play(id));assert.equal(fx.audio.getStatus().lastEffect.id,id);assert.equal(fx.audio.getStatus().lastEffect.source,'original');
  assert.equal(Context.instances.at(-1).oscillators.at(-1).loop,false);
 }
 assert.equal(fetched.filter(path=>path.endsWith('seq-61.wav')).length,1,'Aliases reuse one decoded original asset');
 assert.equal(fx.audio.getStatus().effectCounts.original,6);assert.equal(heard.length,6);
 fx.audio.play('turn');assert.equal(fx.audio.getStatus().lastEffect.source,'synthesized','New game interactions can use authored additions');
 fx.audio.play('error');await settle();assert.equal(fx.audio.getStatus().lastEffect.source,'synthesized');assert(!fetched.some(path=>path.startsWith('https:')));
 const originalCount=fx.audio.getStatus().effectCounts.original;fx.audio.configure({muted:true});assert.equal(fx.audio.play('confirm'),false);assert.equal(fx.audio.getStatus().effectCounts.original,originalCount);
 fx.audio.dispose();
 // A slow first recording uses one prompt fallback, never a delayed second sound.
 let resolveWave;const deadlines=new Map();let nextDeadline=0;
 const slow=fixture(null,{AudioContext:BufferContext,setTimeout:fn=>{deadlines.set(++nextDeadline,fn);return nextDeadline;},clearTimeout:key=>deadlines.delete(key),fetch:async url=>url==='/assets/audio/effects.json'?{ok:true,json:async()=>({schema:effects.schema,effects:{confirm:effects.effects.confirm}})}:url==='/assets/audio/index.json'?{ok:false}:{ok:true,arrayBuffer:()=>new Promise(resolve=>{resolveWave=resolve;})}});
 await slow.audio.unlock();await settle();assert(slow.audio.play('confirm'));assert.equal(slow.audio.getStatus().pendingEffects,1);
 [...deadlines.values()][0]();assert.equal(slow.audio.getStatus().lastEffect.source,'synthesized');assert.equal(slow.audio.getStatus().lastEffect.sequence,1);
 resolveWave(new ArrayBuffer(8));await settle();assert.equal(slow.audio.getStatus().lastEffect.sequence,1,'Late decode must not double-play the interaction');
 slow.audio.play('confirm');assert.equal(slow.audio.getStatus().lastEffect.source,'original');assert.equal(slow.audio.getStatus().lastEffect.sequence,2);slow.audio.dispose();
 // Muting while a decode is pending cancels the queued interaction permanently.
 let finishWave;const pending=fixture(null,{AudioContext:BufferContext,fetch:async url=>url==='/assets/audio/effects.json'?{ok:true,json:async()=>({schema:effects.schema,effects:{confirm:effects.effects.confirm}})}:url==='/assets/audio/index.json'?{ok:false}:{ok:true,arrayBuffer:()=>new Promise(resolve=>{finishWave=resolve;})}});
 await pending.audio.unlock();await settle();pending.audio.play('confirm');pending.audio.configure({sfxVolume:0});assert.equal(pending.audio.getStatus().pendingEffects,0);
 finishWave(new ArrayBuffer(8));await settle();assert.equal(pending.audio.getStatus().lastEffect,null);pending.audio.dispose();
 // A cover holds the title cue while rendering continues to request later scenes.
 const held=fixture(null,{fetch:null});held.audio.setScene('strategy');held.audio.setCoverActive(true);
 assert.equal(held.audio.getStatus().scene,'menu');assert.equal(held.audio.getStatus().requestedScene,'strategy');
 assert.equal(held.audio.getStatus().coverActive,true);assert.equal(held.audio.getStatus().unlocked,false);
 await held.audio.unlock();const heldContext=Context.instances.at(-1),voiceCount=heldContext.oscillators.length;
 assert.equal(heldContext.oscillators[0].frequency.events[0][1],440*Math.pow(2,(67-69)/12),'The cover plays the menu score, not the underlying strategy score');
 held.audio.setScene('battle');held.audio.setScene('duel');held.audio.setScene('__proto__');held.audio.setCoverActive(true);
 assert.equal(held.audio.getStatus().scene,'menu');assert.equal(held.audio.getStatus().requestedScene,'duel');
 assert.equal(heldContext.oscillators.length,voiceCount,'Repeated cover activation and background renders must not restart the title');assert.equal(held.timers.size,1);
 held.audio.setCoverActive(false);assert.equal(held.audio.getStatus().scene,'duel');assert.equal(held.audio.getStatus().coverActive,false);assert.equal(held.timers.size,1);
 held.audio.setCoverActive(true);held.audio.configure({muted:true});held.audio.setScene('battle');held.audio.setCoverActive(false);
 assert.equal(held.audio.getStatus().scene,'battle');assert.equal(held.audio.getStatus().playing,false,'Releasing the cover must preserve the user mute setting');
 held.audio.configure({muted:false});assert.equal(held.audio.getStatus().playing,true);assert.equal(held.audio.getStatus().scene,'battle');
 held.audio.dispose();held.audio.setCoverActive(true);assert.equal(held.audio.getStatus().coverActive,false);
 // Available original title recordings retain priority while cover requests are held.
 const coverRequests=[],coverManifest={...manifest,tracks:{menu:track('title'),strategy:track('strategy'),battle:track('battle'),duel:track('duel')}};
 const recordedCover=fixture(null,{AudioContext:BufferContext,fetch:async path=>{
  coverRequests.push(path);return path==='/assets/audio/effects.json'?{ok:true,json:async()=>({schema:effects.schema,effects:{}})}:path.endsWith('.json')?{ok:true,json:async()=>coverManifest}:{ok:true,arrayBuffer:async()=>new ArrayBuffer(8)};
 }});
 recordedCover.audio.setCoverActive(true);recordedCover.audio.setScene('strategy');await recordedCover.audio.unlock();await settle();
 assert.equal(recordedCover.audio.getStatus().scene,'menu');assert.equal(recordedCover.audio.getStatus().musicSource,'original');
 assert(coverRequests.includes('/assets/audio/original/title.mp3'));assert(!coverRequests.includes('/assets/audio/original/strategy.mp3'));
 recordedCover.audio.setScene('duel');recordedCover.audio.setScene('battle');
 assert.equal(recordedCover.audio.getStatus().scene,'menu');assert.equal(recordedCover.audio.getStatus().requestedScene,'battle');
 recordedCover.audio.setCoverActive(false);await settle();assert.equal(recordedCover.audio.getStatus().scene,'battle');
 assert.equal(recordedCover.audio.getStatus().musicSource,'original');assert(coverRequests.includes('/assets/audio/original/battle.mp3'));
 assert(!coverRequests.includes('/assets/audio/original/duel.mp3'),'An overwritten scene request must not start a second background track');recordedCover.audio.dispose();
 // Evaluate the browser branch: the cover and app obtain the exact same object,
 // while callers explicitly using create(options) keep an independent lifecycle.
 const listeners=new Set(),pageTimers=new Map();let pageTimer=0;
 const browser={AudioContext:Context,fetch:null,document:{hidden:false,addEventListener:(event,fn)=>listeners.add(fn),removeEventListener:(event,fn)=>listeners.delete(fn)},
  localStorage:{getItem:()=>null,setItem(){}},setInterval:fn=>{pageTimers.set(++pageTimer,fn);return pageTimer;},clearInterval:key=>pageTimers.delete(key),setTimeout,clearTimeout};
 const sandbox={window:browser};vm.createContext(sandbox);vm.runInContext(fs.readFileSync(require.resolve('../game/audio.js'),'utf8'),sandbox);
 const browserApi=browser.GameAudio,contextsBefore=Context.instances.length,coverAudio=browserApi.page(),appAudio=browserApi.page();
 assert.strictEqual(coverAudio,appAudio);assert.equal(listeners.size,1);assert.equal(Context.instances.length,contextsBefore,'Getting the shared page instance must not bypass autoplay policy');
 coverAudio.setCoverActive(true);appAudio.setScene('strategy');assert.equal(appAudio.getStatus().scene,'menu');
 const separate=browserApi.create();assert.notStrictEqual(separate,appAudio);separate.setScene('duel');assert.equal(appAudio.getStatus().requestedScene,'strategy');
 await coverAudio.unlock();await appAudio.unlock();assert.equal(Context.instances.length,contextsBefore+1);assert.equal(pageTimers.size,1,'The two UI owners share one context and scheduler');
 coverAudio.setCoverActive(false);assert.equal(appAudio.getStatus().scene,'strategy');assert.strictEqual(browserApi.page(),appAudio);
 coverAudio.dispose();separate.dispose();assert.equal(listeners.size,0);assert.equal(pageTimers.size,0);
 assert.match(fs.readFileSync(require.resolve('../game/app.js'),'utf8'),/const gameAudio=GameAudio\.page\(\);/);
 console.log('audio: shared page mixer and cover/title scene hold, original music and one-shots, bounded loading, alias caching, fallback, mute/disposal and diagnostics passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
