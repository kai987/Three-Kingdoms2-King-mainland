/* Original-ROM recordings where available; authored chiptunes/SFX as fallback. No game RNG. */
'use strict';
(function(root){
 const STORAGE_KEY='three-kingdoms-audio';
 const DEFAULTS=Object.freeze({muted:false,bgmVolume:.35,sfxVolume:.55});
 const TRACKS=Object.freeze({
  menu:{step:.215,lead:[
   67,0,69,72,74,72,69,67,64,0,67,69,67,64,62,0,
   60,62,64,67,69,67,64,62,60,0,62,64,67,0,64,0,
   67,69,72,74,76,74,72,69,67,0,69,72,74,72,69,67,
   64,67,69,67,64,62,60,62,64,0,62,0,60,0,0,0
  ],bass:[48,48,53,53,45,45,43,43,48,48,53,53,45,43,48,48],counter:[60,64,62,64,65,69,65,69,57,60,57,60,55,59,55,59]},
  strategy:{step:.245,lead:[
   64,0,67,69,67,64,62,0,60,62,64,0,62,60,57,0,
   60,0,62,64,67,64,62,60,57,0,60,62,64,0,62,0,
   64,67,69,72,69,67,64,0,62,64,67,69,67,64,62,0,
   60,62,64,67,64,62,60,57,55,0,57,60,62,0,60,0
  ],bass:[48,48,43,43,45,45,41,43,48,48,43,43,45,41,43,48],counter:[60,55,60,55,57,52,57,52,60,55,60,55,57,53,55,60]},
  battle:{step:.135,lead:[
   69,69,72,74,76,0,74,72,69,0,67,69,72,69,67,64,
   67,67,69,72,74,0,72,69,67,0,64,67,69,67,64,62,
   69,72,74,76,79,76,74,72,76,74,72,69,72,69,67,64,
   67,69,72,69,67,64,62,64,67,0,64,0,69,0,69,0
  ],bass:[45,45,45,43,43,43,43,40,45,45,45,43,43,40,43,45],counter:[57,64,57,64,55,62,55,62,57,64,57,64,55,52,55,57]},
  duel:{step:.155,lead:[
   62,0,62,65,67,0,69,67,65,0,62,60,62,0,57,0,
   60,0,60,62,65,0,67,65,62,0,60,57,60,0,57,0,
   62,65,67,69,74,0,72,69,67,0,69,67,65,62,60,0,
   62,0,65,62,60,57,55,57,60,0,57,0,62,0,0,0
  ],bass:[38,38,38,41,36,36,36,33,38,38,38,41,36,33,36,38],counter:[50,57,50,57,48,55,48,55,50,57,50,57,48,45,48,50]}
 });
 const EFFECTS=Object.freeze({
  click:[['square',76,0,.035,.38]],
  confirm:[['square',72,0,.06,.45],['square',79,.065,.11,.45]],
  cancel:[['triangle',67,0,.07,.6],['triangle',60,.07,.1,.6]],
  error:[['square',44,0,.08,.4],['square',43,.1,.13,.4]],
  march:[['triangle',48,0,.09,.7],['triangle',55,.1,.09,.7],['square',67,.2,.13,.35]],
  attack:[['square',52,0,.045,.48],['square',40,.045,.08,.45],['triangle',28,.08,.12,.8]],
  tactic:[['triangle',72,0,.06,.65],['triangle',76,.06,.06,.65],['triangle',79,.12,.06,.65],['square',84,.18,.18,.3]],
  victory:[['square',72,0,.12,.45],['square',76,.13,.12,.45],['square',79,.26,.12,.45],['square',84,.4,.34,.4],['triangle',60,.4,.34,.7]],
  defeat:[['triangle',64,0,.18,.7],['triangle',62,.2,.18,.7],['triangle',60,.4,.18,.7],['triangle',57,.6,.32,.7]],
  turn:[['triangle',60,0,.1,.7],['square',67,.12,.08,.35],['square',72,.22,.18,.4]]
 });
 const EFFECT_ALIASES=Object.freeze({attack_impact:'attack',tactic_prepare:'tactic',duel_start:'confirm',duel_refused:'cancel',duel_strike:'attack',duel_guard:'attack',duel_feint:'attack',duel_withdraw:'cancel',tactic_88:'tactic',tactic_8d:'tactic',tactic_91:'tactic',tactic_95:'tactic'});
 const effectIds=Object.freeze([...Object.keys(EFFECTS),...Object.keys(EFFECT_ALIASES)]);
 const volume=(value,fallback)=>typeof value==='number'&&Number.isFinite(value)?Math.min(1,Math.max(0,value)):fallback;
 function create(options={}){
  const doc=options.document===undefined?root.document:options.document;
  let storage=options.storage;
  if(storage===undefined){try{storage=root.localStorage;}catch{storage=null;}}
  const AudioCtor=options.AudioContext===undefined?(root.AudioContext||root.webkitAudioContext):options.AudioContext;
  const fetcher=options.fetch===undefined?root.fetch?.bind(root):options.fetch;
  const startInterval=options.setInterval||root.setInterval.bind(root);
  const stopInterval=options.clearInterval||root.clearInterval.bind(root);
  const later=options.setTimeout||root.setTimeout.bind(root),cancelLater=options.clearTimeout||root.clearTimeout.bind(root);
  let settings={...DEFAULTS};
  try{
   const saved=JSON.parse(storage?.getItem(STORAGE_KEY)||'null');
   if(saved&&typeof saved==='object')settings={muted:saved.muted===true,bgmVolume:volume(saved.bgmVolume,DEFAULTS.bgmVolume),sfxVolume:volume(saved.sfxVolume,DEFAULTS.sfxVolume)};
  }catch{/* Storage is optional, including private browsing. */}
  let context=null,musicBus=null,effectsBus=null,compressor=null,timer=null;
  let scene='menu',step=0,nextTime=0,unlocked=false,disposed=false,hidden=!!doc?.hidden,suspension=null;
  let manifestPromise=null,originalVoice=null,originalResume=null;
  let effectsManifestPromise=null,effectsManifest=null,effectsUnavailable=false,effectsPreloaded=false,effectSequence=0,effectRequestSequence=0,lastEffect=null;
  const effectBuffers=new Map(),effectLoads=new Map(),effectAssets=new Map(),pendingEffects=new Set(),effectCounts={original:0,synthesized:0};
  const originalBuffers=new Map(),originalLoads=new Map();
  const voices=new Set();
  const status=()=>({supported:typeof AudioCtor==='function',unlocked,scene,playing:timer!==null||originalVoice!==null,musicSource:originalVoice?'original':timer!==null?'synthesized':null,originalTracks:originalBuffers.size,originalEffects:effectBuffers.size,pendingEffects:pendingEffects.size,effectRequestSequence,lastEffect:lastEffect?{...lastEffect}:null,effectCounts:{...effectCounts},hidden,activeVoices:voices.size,disposed});
  function gains(){
   if(!context)return;
   musicBus.gain.setValueAtTime(settings.muted?0:settings.bgmVolume*.12,context.currentTime);
   effectsBus.gain.setValueAtTime(settings.muted?0:settings.sfxVolume*.15,context.currentTime);
  }
  function removeVoice(voice){
   if(!voices.delete(voice))return;
   if(voice===originalVoice)originalVoice=null;
   try{voice.osc.disconnect();voice.envelope.disconnect();}catch{/* Already disconnected. */}
  }
  function stopVoices(kind,preserveOriginal=false){
   for(const voice of [...voices])if(!kind||voice.kind===kind){
    if(preserveOriginal&&voice===originalVoice){
     const duration=voice.end-voice.start;
     originalResume={scene:voice.scene,offset:voice.start+(voice.offset-voice.start+Math.max(0,context.currentTime-voice.started))%duration};
    }
    try{voice.osc.stop(context.currentTime);}catch{/* An expired source may already be stopped. */}
    removeVoice(voice);
   }
  }
  function note(wave,midi,when,duration,level,kind){
   if(!midi||!context)return;
   const osc=context.createOscillator(),envelope=context.createGain();
   const voice={osc,envelope,kind};voices.add(voice);
   osc.type=wave;osc.frequency.setValueAtTime(440*Math.pow(2,(midi-69)/12),when);
   const end=when+duration,attack=Math.min(.006,duration/4),release=Math.min(.018,duration/4);
   envelope.gain.setValueAtTime(0,when);
   envelope.gain.linearRampToValueAtTime(level,when+attack);
   envelope.gain.setValueAtTime(level,end-release);
   envelope.gain.linearRampToValueAtTime(0,end);
   osc.connect(envelope);envelope.connect(kind==='music'?musicBus:effectsBus);
   osc.onended=()=>removeVoice(voice);
   osc.start(when);osc.stop(end+.002);
  }
  function pause(){
   if(timer!==null){stopInterval(timer);timer=null;}
   cancelPendingEffects();
   stopVoices(undefined,true);
  }
  function restartMusic(){
   if(timer!==null){stopInterval(timer);timer=null;}
   stopVoices('music');startMusic();
  }
  async function loadOriginal(value){
   if(!fetcher||!context||typeof context.decodeAudioData!=='function'||disposed)return;
   if(originalLoads.has(value))return originalLoads.get(value);
   const task=(async()=>{
    try{
     if(!manifestPromise)manifestPromise=(async()=>{
      const response=await fetcher('/assets/audio/index.json');
      if(!response.ok)throw Error('Audio index unavailable');
      const manifest=await response.json();
      if(manifest.schema!=='tk2-original-audio-v1'||!manifest.tracks||typeof manifest.tracks!=='object')throw Error('Invalid audio index');
      return manifest;
     })();
     const manifest=await manifestPromise,track=manifest.tracks[value];
     if(disposed||!track||track.kind!=='original_rom_capture'||!/^\/assets\/audio\/original\/[a-z-]+\.mp3$/.test(track.path)||!Number.isFinite(track.loop_start)||!Number.isFinite(track.loop_end)||track.loop_start<0||track.loop_end<=track.loop_start)return;
     const response=await fetcher(track.path);if(!response.ok)throw Error('Original audio unavailable');
     const buffer=await context.decodeAudioData(await response.arrayBuffer());
     if(disposed||!Number.isFinite(buffer.duration)||buffer.duration<track.loop_end-.05)return;
     originalBuffers.set(value,{buffer,start:track.loop_start,end:Math.min(track.loop_end,buffer.duration)});
     if(scene===value)restartMusic();
    }catch{/* Unavailable/unsupported recordings keep the authored fallback. */}
   })();
   originalLoads.set(value,task);return task;
  }
  function canLoadEffects(){return !!fetcher&&!!context&&typeof context.decodeAudioData==='function';}
  async function loadEffectsManifest(){
   if(!canLoadEffects()||disposed)return null;
   if(!effectsManifestPromise)effectsManifestPromise=(async()=>{
    try{
     const response=await fetcher('/assets/audio/effects.json');
     if(!response.ok)throw Error('Effects index unavailable');
     const value=await response.json();
     if(value.schema!=='tk2-original-effects-v1'||!value.effects||typeof value.effects!=='object')throw Error('Invalid effects index');
     effectsManifest=value;return value;
    }catch{effectsUnavailable=true;return null;}
   })();
   return effectsManifestPromise;
  }
  async function loadOriginalEffect(id){
   if(!canLoadEffects()||disposed)return null;
   if(effectLoads.has(id))return effectLoads.get(id);
   const task=(async()=>{
    try{
     const manifest=await loadEffectsManifest(),row=manifest?.effects[id];
     if(disposed||!row||row.kind!=='original_rom_capture'||!/^\/assets\/audio\/original\/effects\/[a-z0-9-]+\.wav$/.test(row.path))return null;
     if(!effectAssets.has(row.path))effectAssets.set(row.path,(async()=>{
      const response=await fetcher(row.path);if(!response.ok)throw Error('Original effect unavailable');
      const buffer=await context.decodeAudioData(await response.arrayBuffer());
      if(!Number.isFinite(buffer.duration)||buffer.duration<=0||buffer.duration>15)throw Error('Invalid original effect duration');
      return buffer;
     })());
     const buffer=await effectAssets.get(row.path);if(disposed)return null;
     const original={buffer,row};effectBuffers.set(id,original);return original;
    }catch{return null;}
   })();
   effectLoads.set(id,task);return task;
  }
  function prepareEffects(){
   if(!canLoadEffects()||disposed||effectsPreloaded)return;
   effectsPreloaded=true;
   void loadEffectsManifest().then(manifest=>{
    if(!manifest||disposed)return;
    for(const id of effectIds)if(Object.hasOwn(manifest.effects,id))void loadOriginalEffect(id);
   });
  }
  function cancelPendingEffects(){
   for(const pending of pendingEffects){pending.active=false;cancelLater(pending.timer);}
   pendingEffects.clear();
  }
  function recordEffect(id,source,row=null){
   lastEffect={sequence:++effectSequence,id,source,requestId:row?.request?.id??null,path:row?.path??null};
   effectCounts[source]++;
   try{options.onEffect?.({...lastEffect});}catch{/* Diagnostics never alter game interaction. */}
  }
  function canPlayEffect(){return unlocked&&context&&!disposed&&!hidden&&!settings.muted&&settings.sfxVolume>0&&context.state==='running';}
  function startEffect(id,original=null){
   if(!canPlayEffect())return false;
   if([...voices].filter(voice=>voice.kind==='effect').length>24)stopVoices('effect');
   if(original){
    const source=context.createBufferSource(),envelope=context.createGain();
    source.buffer=original.buffer;source.loop=false;
    const gain=Number.isFinite(original.row.playback_gain)?Math.max(.1,Math.min(4,original.row.playback_gain)):4;
    envelope.gain.setValueAtTime(gain,context.currentTime);source.connect(envelope);envelope.connect(effectsBus);
    const voice={osc:source,envelope,kind:'effect'};voices.add(voice);source.onended=()=>removeVoice(voice);
    source.start(context.currentTime+.005);recordEffect(id,'original',original.row);return true;
   }
   const notes=EFFECTS[EFFECT_ALIASES[id]||id];
   for(const[wave,midi,offset,duration,level]of notes)note(wave,midi,context.currentTime+.005+offset,duration,level,'effect');
   recordEffect(id,'synthesized');return true;
  }
  function schedule(){
   if(!context||disposed||hidden||settings.muted||settings.bgmVolume===0)return;
   const track=TRACKS[scene];
   // Resume after a throttled timer at the present bar; never enqueue a backlog.
   if(nextTime<context.currentTime-.1)nextTime=context.currentTime+.025;
   while(nextTime<context.currentTime+.2){
    note('square',track.lead[step],nextTime,track.step*.84,.52,'music');
    if(step%4===0)note('triangle',track.bass[step/4],nextTime,track.step*3.5,.65,'music');
    if(step%4===2)note('square',track.counter[Math.floor(step/4)],nextTime,track.step*1.5,.14,'music');
    step=(step+1)%track.lead.length;nextTime+=track.step;
   }
  }
  function startMusic(){
   if(!context||!unlocked||disposed||hidden||settings.muted||settings.bgmVolume===0||context.state==='suspended'||timer!==null||originalVoice)return;
   const original=originalBuffers.get(scene);
   if(original){
    const source=context.createBufferSource(),envelope=context.createGain();
    source.buffer=original.buffer;source.loop=true;source.loopStart=original.start;source.loopEnd=original.end;
    // Match the authored fallback's measured level, retaining ample mix headroom.
    envelope.gain.setValueAtTime(2.5,context.currentTime);source.connect(envelope);envelope.connect(musicBus);
    const offset=originalResume?.scene===scene?originalResume.offset:original.start;originalResume=null;
    originalVoice={osc:source,envelope,kind:'music',scene,offset,start:original.start,end:original.end,started:context.currentTime+.01};const voice=originalVoice;voices.add(voice);
    source.onended=()=>removeVoice(voice);source.start(voice.started,offset);return;
   }
   void loadOriginal(scene);
   nextTime=context.currentTime+.025;
   schedule();timer=startInterval(schedule,50);
  }
  async function unlock(){
   if(disposed||typeof AudioCtor!=='function')return false;
   try{
    if(!context){
     context=new AudioCtor();musicBus=context.createGain();effectsBus=context.createGain();compressor=context.createDynamicsCompressor();
     compressor.threshold.setValueAtTime(-12,context.currentTime);compressor.knee.setValueAtTime(12,context.currentTime);
     compressor.ratio.setValueAtTime(6,context.currentTime);compressor.attack.setValueAtTime(.003,context.currentTime);compressor.release.setValueAtTime(.12,context.currentTime);
     musicBus.connect(compressor);effectsBus.connect(compressor);compressor.connect(context.destination);gains();
    }
    if(suspension)await suspension;
    if(disposed||hidden)return false;
    if(context.state!=='running'&&context.state!=='closed')await context.resume();
    if(disposed||hidden){if(!disposed&&context.state==='running')void context.suspend().catch(()=>{});return false;}
    unlocked=context.state==='running';prepareEffects();startMusic();return unlocked;
   }catch{return false;}
  }
  function setScene(value){
   if(disposed||!Object.hasOwn(TRACKS,value)||scene===value)return;
   scene=value;step=0;originalResume=null;
   restartMusic();
  }
  function configure(value={}){
   if(disposed)return{...settings};
   if(typeof value.muted==='boolean')settings.muted=value.muted;
   settings.bgmVolume=volume(value.bgmVolume,settings.bgmVolume);
   settings.sfxVolume=volume(value.sfxVolume,settings.sfxVolume);
   try{storage?.setItem(STORAGE_KEY,JSON.stringify(settings));}catch{/* Optional storage. */}
   gains();
   if(settings.sfxVolume===0){cancelPendingEffects();stopVoices('effect');}
   if(settings.muted)pause();
   else if(settings.bgmVolume===0){if(timer!==null){stopInterval(timer);timer=null;}stopVoices('music',true);}
   else startMusic();
   return{...settings};
  }
  function play(effect){
   if(!canPlayEffect()||!effectIds.includes(effect))return false;
   effectRequestSequence++;
   if(effectBuffers.has(effect))return startEffect(effect,effectBuffers.get(effect));
   if(!canLoadEffects()||effectsUnavailable||effectsManifest&&!Object.hasOwn(effectsManifest.effects,effect))return startEffect(effect);
   // Keep the first gesture responsive without playing a fallback then the original twice.
   if(pendingEffects.size>=16){const oldest=pendingEffects.values().next().value;oldest.active=false;cancelLater(oldest.timer);pendingEffects.delete(oldest);}
   const pending={active:true,timer:null};pendingEffects.add(pending);
   const finish=original=>{if(!pending.active)return;pending.active=false;cancelLater(pending.timer);pendingEffects.delete(pending);startEffect(effect,original);};
   pending.timer=later(()=>finish(null),160);
   void loadOriginalEffect(effect).then(finish);
   return true;
  }
  function visibility(){
   hidden=!!doc?.hidden;
   if(hidden){
    pause();
    if(context?.state==='running')suspension=Promise.resolve(context.suspend()).catch(()=>{}).finally(()=>{suspension=null;});
   }
   else if(unlocked)void unlock();
  }
  doc?.addEventListener('visibilitychange',visibility);
  function dispose(){
   if(disposed)return;
   disposed=true;pause();doc?.removeEventListener('visibilitychange',visibility);
   if(context){
    try{musicBus.disconnect();effectsBus.disconnect();compressor.disconnect();}catch{/* Already closed. */}
    Promise.resolve(context.close()).catch(()=>{});
   }
  }
  return{unlock,setScene,play,configure,getSettings:()=>({...settings}),getStatus:status,dispose};
 }
 const api={create,STORAGE_KEY};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameAudio=api;
})(typeof window==='object'?window:globalThis);
