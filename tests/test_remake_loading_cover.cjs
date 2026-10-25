/* Boot presentation only: the shipped controls, progress and retry stay authoritative. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'../game/loading-cover.js'),'utf8');
const css=fs.readFileSync(path.join(__dirname,'../game/loading-cover.css'),'utf8');
function fixture({language='zh-Hant',storageThrows=false,loading=false,reduced=false,prefix='/Three-Kingdoms2-King-mainland/',paths=false,audio=null}={}){
 const listeners=new Map(),observers=[],timers=[],mediaListeners=new Set();
 class Element{
  constructor(tag){this.tagName=tag.toUpperCase();this.nodeType=1;this.children=[];this.attributes={};this.hidden=false;this.disabled=false;this.textContent='';this.parentNode=null;}
  get nextSibling(){const rows=this.parentNode?.children||[];return rows[rows.indexOf(this)+1]||null;}
  get isConnected(){for(let node=this;node;node=node.parentNode)if(node===html)return true;return false;}
  append(...nodes){for(const node of nodes){if(node.parentNode)node.parentNode.children.splice(node.parentNode.children.indexOf(node),1);node.parentNode=this;this.children.push(node);}}
  insertBefore(node,next){if(node.parentNode)node.parentNode.children.splice(node.parentNode.children.indexOf(node),1);const index=next?this.children.indexOf(next):-1;node.parentNode=this;this.children.splice(index<0?this.children.length:index,0,node);}
  insertAdjacentElement(where,node){assert.equal(where,'afterend');this.parentNode.insertBefore(node,this.nextSibling);}
  contains(value){return this===value||this.children.some(node=>node.contains(value));}
  setAttribute(name,value){this.attributes[name]=String(value);if(name==='id')this.id=String(value);}
  getAttribute(name){return name==='id'?this.id??null:this.attributes[name]??null;}
  removeAttribute(name){delete this.attributes[name];}
  focus(){document.activeElement=this;}
  querySelector(selector){assert(selector.startsWith('#'),'test fixture only queries stable IDs');return descendants(this).find(node=>node.id===selector.slice(1))||null;}
 }
 const descendants=node=>node.children.flatMap(child=>[child,...descendants(child)]);
 const html=new Element('html'),body=new Element('body'),notice=new Element('p'),inspector=new Element('aside');
 notice.id='notice';inspector.id='inspector';html.append(body);body.append(notice,inspector);
 const document={body:loading?null:body,documentElement:html,baseURI:'https://game.example'+prefix,readyState:loading?'loading':'interactive',
  createElement:tag=>new Element(tag),querySelector:selector=>html.querySelector(selector),
  addEventListener(type,fn,options){if(!listeners.has(type))listeners.set(type,[]);listeners.get(type).push({fn,options});},
  removeEventListener(type,fn){listeners.set(type,(listeners.get(type)||[]).filter(row=>row.fn!==fn));}
 };
 const emit=(type,extra={})=>{for(const row of [...listeners.get(type)||[]]){row.fn({type,...extra});if(row.options?.once)document.removeEventListener(type,row.fn);}};
 class MutationObserver{
  constructor(callback){this.callback=callback;this.connected=false;observers.push(this);}
  observe(target,options){this.target=target;this.options=options;this.connected=true;}
  disconnect(){this.connected=false;}
 }
 const media={matches:reduced,addEventListener(type,fn){assert.equal(type,'change');mediaListeners.add(fn);},removeEventListener(type,fn){assert.equal(type,'change');mediaListeners.delete(fn);}};
 const window={document,MutationObserver,localStorage:{getItem(key){assert.equal(key,'three-kingdoms-language');if(storageThrows)throw Error('blocked');return language;}},matchMedia:query=>{assert.equal(query,'(prefers-reduced-motion: reduce)');return media;}};
 if(audio)window.GameAudio={page:()=>audio};
 if(paths)window.GamePaths={asset:value=>prefix+value.slice(1)};
 vm.runInNewContext(source,{window,URL,console,setTimeout:(...args)=>timers.push(args)});
 return{window,document,body,notice,inspector,listeners,observers,timers,media,mediaListeners,all:()=>descendants(html),node:id=>document.querySelector('#'+id),
  mutate(){for(const observer of observers)if(observer.connected)observer.callback([]);},emit,
  domReady(){document.body=body;document.readyState='interactive';emit('DOMContentLoaded');},
  control(id,{disabled=false,outside=false,hidden=false}={}){const node=new Element('button');node.id=id;node.disabled=disabled;node.hidden=hidden;(outside?body:inspector).append(node);return node;},
  status(){const panel=new Element('p');panel.id='game-engine-status';panel.setAttribute('role','status');const button=new Element('button');button.textContent='Existing retry';panel.append(button);notice.insertAdjacentElement('afterend',panel);return{panel,button};},
  changeMotion(value){media.matches=value;for(const fn of mediaListeners)fn({matches:value});}
 };
}
const classNode=(f,name)=>f.all().find(node=>node.className===name);
const initial=fixture(),cover=initial.node('game-loading-cover');
assert(cover&&!cover.hidden,'The first parsed page has a visible cover without waiting for any artwork');
assert.equal(cover.getAttribute('role'),'region');assert.equal(cover.getAttribute('aria-labelledby'),'game-loading-title');
assert.equal(cover.getAttribute('data-phase'),'manifest');assert.equal(classNode(initial,'loading-cover-subtitle').textContent,'大陸戰役');
assert(initial.node('game-loading-start').hidden);assert(initial.node('game-loading-start').disabled);
assert.equal(initial.inspector.getAttribute('inert'),'','The covered application cannot receive pointer or keyboard actions');
initial.node('game-loading-start').onclick();assert(!cover.hidden,'An early start cannot bypass initialization');
assert.equal(classNode(initial,'loading-cover-scenario').textContent,'184年・黃巾之亂');
assert.equal(initial.node('game-loading-title').children.map(node=>node.textContent).join(''),'三國志Ⅱ');
assert(initial.all().filter(node=>node.tagName==='IMG').every(node=>node.alt===''&&node.getAttribute('aria-hidden')==='true'),'Decorative artwork does not compete with live boot status');
assert.equal(initial.timers.length,0,'No minimum duration, fake progress timer, or delayed dismissal is added');
assert.equal(initial.observers.length,1);assert(initial.observers[0].options.subtree);assert(initial.observers[0].options.childList);
assert.deepEqual([...initial.observers[0].options.attributeFilter],['disabled','hidden','class']);
initial.window.GameLoadingCover.update({phase:'loading',receivedBytes:2048,runtimeReady:false});
let message=classNode(initial,'loading-cover-message');assert(message.textContent.includes('2.0 KiB'));assert(message.textContent.includes('不含執行環境'));assert(!message.textContent.includes('%'));
initial.window.GameLoadingCover.update({receivedBytes:Infinity});assert(message.textContent.includes('2.0 KiB'),'Invalid byte reports cannot invent progress');
initial.window.GameLoadingCover.update({ready:true});assert(!cover.hidden,'Worker readiness alone does not hide an unrendered application');
assert.equal(cover.getAttribute('data-phase'),'initializing');assert(message.textContent.includes('準備戰役畫面'));
initial.control('begin',{outside:true});initial.mutate();assert(!cover.hidden,'Unrelated controls outside the inspector cannot dismiss the cover');
const begin=initial.control('begin',{disabled:true});initial.mutate();assert(!cover.hidden,'A disabled primary control is not a usable opening');
begin.disabled=false;begin.hidden=true;initial.mutate();assert(!cover.hidden);begin.hidden=false;initial.mutate();assert(!cover.hidden);
assert.equal(cover.getAttribute('data-phase'),'ready');assert(!initial.node('game-loading-start').hidden);assert(!initial.node('game-loading-start').disabled);
assert.equal(initial.node('game-loading-start').textContent,'開始遊戲');assert.equal(initial.document.activeElement,initial.node('game-loading-start'));
initial.mutate();assert(!cover.hidden,'A fully loaded cover remains until the player starts');
initial.node('game-loading-start').onclick();assert(cover.hidden);assert.equal(initial.inspector.getAttribute('inert'),null);
assert.equal(cover.getAttribute('aria-hidden'),'true');assert(!initial.observers[0].connected);assert.equal(initial.mediaListeners.size,0);
initial.window.GameLoadingCover.update({failed:true,ready:false});assert(cover.hidden,'A later campaign error never restarts the initial cover');
assert.equal((initial.listeners.get('game-language-change')||[]).length,0);

const japanese=fixture({language:'ja',prefix:'/nested/game/'});assert.equal(japanese.node('game-loading-cover').getAttribute('lang'),'ja');
assert.equal(classNode(japanese,'loading-cover-subtitle').textContent,'大陸戦役');assert.equal(classNode(japanese,'loading-cover-scenario').textContent,'184年・黄巾の乱');
assert.equal(classNode(japanese,'loading-cover-art').src,'https://game.example/nested/game/assets/loading/cover.png','Early boot assets honor the actual project subpath before paths.js is ready');
japanese.window.GameI18n={locale:'zh-Hant'};japanese.emit('game-language-change');assert.equal(classNode(japanese,'loading-cover-subtitle').textContent,'大陸戰役');
japanese.window.GameI18n.locale='ja';japanese.emit('game-language-change');japanese.window.GameLoadingCover.update({phase:'loading',receivedBytes:1024,runtimeReady:true});
assert(classNode(japanese,'loading-cover-message').textContent.includes('実行環境を除く'));assert(classNode(japanese,'loading-cover-message').textContent.includes('準備完了'));
const blocked=fixture({storageThrows:true,paths:true,prefix:'/nested/'});assert.equal(blocked.node('game-loading-cover').getAttribute('lang'),'zh-Hant');assert.equal(classNode(blocked,'loading-cover-art').src,'/nested/assets/loading/cover.png');

const retried=fixture(),{panel,button}=retried.status(),oldParent=panel.parentNode,oldNext=panel.nextSibling;
let retryCount=0;button.onclick=()=>{retryCount++;retried.window.GameLoadingCover.update({phase:'manifest',failed:false,ready:false});};
retried.mutate();assert.equal(panel.getAttribute('inert'),'');
assert(retried.window.GameLoadingCover.attachStatus(panel));assert.equal(panel.parentNode,classNode(retried,'loading-cover-status-slot'));
assert.equal(panel.getAttribute('inert'),null,'An existing retry remains operable after moving inside the cover');
assert(classNode(retried,'loading-cover-message').hidden,'The existing live status remains the sole message while it is visible');
retried.window.GameLoadingCover.update({failed:true,canRetry:true});assert(!retried.node('game-loading-cover').hidden);assert.equal(retried.node('game-loading-cover').getAttribute('data-phase'),'failed');
assert.equal(panel.children[0],button,'Retry uses the existing button and handler, never a replacement request');button.onclick();assert.equal(retryCount,1);assert.equal(retried.node('game-loading-cover').getAttribute('data-phase'),'manifest');
panel.hidden=true;retried.window.GameLoadingCover.update({ready:true,canRetry:false});assert(!classNode(retried,'loading-cover-message').hidden,'The cover still explains the gap between Worker readiness and rendered controls');
retried.control('allocate');retried.mutate();assert(!retried.node('game-loading-cover').hidden);retried.node('game-loading-start').onclick();assert(retried.node('game-loading-cover').hidden);assert.equal(panel.parentNode,oldParent);assert.equal(panel.nextSibling,oldNext,'The live status returns to its original document position after starting');
assert.equal(retried.window.GameLoadingCover.attachStatus(panel),false,'A post-ready engine error stays in the document instead of moving into a hidden cover');
panel.hidden=false;assert(!retried.node('game-loading-cover').contains(panel));

const images=fixture({reduced:true});assert.equal(images.node('game-loading-cover').getAttribute('data-motion'),'still');images.changeMotion(false);assert.equal(images.node('game-loading-cover').getAttribute('data-motion'),'animated');images.changeMotion(true);assert.equal(images.node('game-loading-cover').getAttribute('data-motion'),'still');
const art=classNode(images,'loading-cover-art');images.emit('error',{target:art});assert(art.hidden);assert.equal(images.node('game-loading-cover').getAttribute('data-art-failed'),'true');
for(const img of images.all().filter(node=>node.tagName==='IMG'))images.emit('error',{target:img});images.control('begin');images.mutate();assert(!images.node('game-loading-cover').hidden);assert(!images.node('game-loading-start').disabled);images.node('game-loading-start').onclick();assert(images.node('game-loading-cover').hidden,'Even failure of every decoration never blocks the explicit start');
assert(/@media\s*\(prefers-reduced-motion\s*:\s*reduce\)/.test(css));assert(/\[data-motion=still\].*animation:none/.test(css));assert(/#game-loading-cover\[hidden\]\{display:none\}/.test(css));
assert(/image-rendering:pixelated/.test(css));assert(!/transition:.*(?:opacity|visibility)/.test(css),'Dismissal has no forced fade delay');

const deferred=fixture({loading:true});assert.equal(deferred.node('game-loading-cover'),null);deferred.window.GameLoadingCover.update({phase:'loading',receivedBytes:4096});const queuedStatus=deferred.status().panel;assert.equal(deferred.window.GameLoadingCover.attachStatus(queuedStatus),false);deferred.domReady();assert(deferred.node('game-loading-cover'));assert.equal(queuedStatus.parentNode,classNode(deferred,'loading-cover-status-slot'));assert.equal(deferred.node('game-loading-cover').getAttribute('data-phase'),'loading');
const resumed=fixture({loading:true});resumed.control('allocate');resumed.domReady();assert(!resumed.node('game-loading-cover').hidden);assert(!resumed.node('game-loading-start').disabled);resumed.node('game-loading-start').onclick();assert(resumed.node('game-loading-cover').hidden,'Native or already-rendered campaign pages use the same explicit start without a Worker-ready dependency');
const originallyInert=fixture({loading:true});originallyInert.inspector.setAttribute('inert','retained');originallyInert.control('begin');originallyInert.domReady();originallyInert.node('game-loading-start').onclick();assert.equal(originallyInert.inspector.getAttribute('inert'),'retained','Starting restores original inert attributes instead of removing pre-existing UI boundaries');
const nativeError=fixture(),nativePanel=nativeError.status().panel;
nativeError.window.GameLoadingCover.attachStatus(nativePanel);nativeError.notice.className='error';nativeError.notice.textContent='An existing native startup error';nativeError.mutate();
assert(nativeError.node('game-loading-cover').hidden,'A native first-render error remains reachable without usable campaign controls');assert.equal(nativeError.notice.textContent,'An existing native startup error');assert.equal(nativePanel.parentNode,nativeError.body);
const bootError=fixture();bootError.window.GameBrowserEngine={ready:false};bootError.notice.className='error';bootError.window.GameLoadingCover.update({failed:true,canRetry:true});bootError.mutate();assert(!bootError.node('game-loading-cover').hidden,'Pre-ready Worker failure retains the cover and its existing retry');
bootError.window.GameBrowserEngine.ready=true;bootError.mutate();assert(bootError.node('game-loading-cover').hidden,'A first-render error after engine readiness exposes the original error instead of blocking forever');
for(const name of ['duelist','infantry'])for(const frame of ['00','01']){
 const file=path.join(__dirname,'../game/assets/battle-enhanced',`native-${name}-${frame}.png`),png=fs.readFileSync(file),size=name==='duelist'?384:64;
 assert.equal(png.subarray(0,8).toString('hex'),'89504e470d0a1a0a');assert.equal(png.readUInt32BE(16),size);assert.equal(png.readUInt32BE(20),size);
}
async function musicChecks(){
 const settings={muted:false,bgmVolume:.35},status={supported:true,unlocked:false,playing:false,coverActive:false},calls=[];
 const player={getSettings:()=>({...settings}),getStatus:()=>({...status}),setCoverActive(value){status.coverActive=value;calls.push(['cover',value]);},
  unlock(){status.unlocked=true;status.playing=!settings.muted&&settings.bgmVolume>0;calls.push(['unlock']);return Promise.resolve(true);},
  configure(value){Object.assign(settings,value);status.playing=status.unlocked&&!settings.muted&&settings.bgmVolume>0;calls.push(['configure',value]);},play(value){calls.push(['play',value]);}
 };
 const music=fixture({audio:player}),sound=music.node('game-loading-sound'),start=music.node('game-loading-start');
 assert(status.coverActive);assert.equal(sound.textContent,'播放音樂');assert.equal(sound.getAttribute('aria-pressed'),'false');
 music.emit('pointerdown',{target:sound,isTrusted:true});assert(!status.unlocked,'The music toggle owns its intent before other shared gesture listeners unlock');
 // The app's real capture listener may finish before click; the button must
 // still carry out its displayed "play" intent rather than toggling off.
 await player.unlock();sound.onclick();await Promise.resolve();assert(!settings.muted);assert(status.playing);assert.equal(sound.getAttribute('aria-pressed'),'true');
 sound.onclick();assert(settings.muted);assert(!status.playing);assert.equal(sound.textContent,'音樂：關');
 music.emit('pointerdown',{target:classNode(music,'loading-cover-art'),isTrusted:true});await Promise.resolve();assert(settings.muted,'Other cover gestures never override a saved mute preference');
 player.configure({bgmVolume:0});sound.onclick();await Promise.resolve();assert(!settings.muted);assert.equal(settings.bgmVolume,.35);assert(status.playing);
 music.control('begin');music.mutate();assert(!music.node('game-loading-cover').hidden);music.window.GameI18n={locale:'ja'};music.emit('game-language-change');assert.equal(start.textContent,'ゲーム開始');assert.equal(sound.textContent,'音楽：入');
 start.onclick();await Promise.resolve();assert(!status.coverActive);assert(calls.some(row=>row[0]==='play'&&row[1]==='confirm'));assert.equal((music.listeners.get('pointerdown')||[]).length,0);assert.equal((music.listeners.get('keydown')||[]).length,0);
 status.unlocked=false;status.playing=false;
 const direct=fixture({audio:player}),directStart=direct.node('game-loading-start'),note=classNode(direct,'loading-cover-audio-note');direct.control('begin');direct.mutate();
 let entered=false;direct.window.GameLoadingCover.whenEntered().then(()=>{entered=true;});await Promise.resolve();assert(!entered,'Startup dialogs can wait without covering or bypassing the title screen');
 const callsBefore=calls.length,textBefore=note.textContent;
 direct.emit('pointerdown',{target:directStart,isTrusted:true});await Promise.resolve();assert.equal(calls.length,callsBefore);assert.equal(note.textContent,textBefore,'First-touch Start must not move when the audio hint changes before pointerup');
 const retryPanel=direct.status();direct.window.GameLoadingCover.attachStatus(retryPanel.panel);direct.emit('pointerdown',{target:retryPanel.button,isTrusted:true});await Promise.resolve();assert.equal(calls.length,callsBefore,'The existing retry button is also protected from pointerdown layout changes');
 directStart.onclick();await Promise.resolve();assert(direct.node('game-loading-cover').hidden);assert(entered,'Deferred startup dialogs resume after the cover is dismissed');assert(status.unlocked,'Start still unlocks the shared audio once the click finishes');
 console.log('loading cover: explicit bilingual start, inert application, truthful progress, shared title music and mute, retained retry/errors, pixel artwork and reduced motion passed');
}
musicChecks().catch(error=>{console.error(error);process.exitCode=1;});
