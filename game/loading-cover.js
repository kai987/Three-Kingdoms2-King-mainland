/* Presentation-only title screen. Real controls enable an explicit start. */
'use strict';
(function(root){
 const doc=root.document;if(!doc)return;
 const copy={
  'zh-Hant':{subtitle:'大陸戰役',scenario:'184年・黃巾之亂',description:'正在整備兵馬，準備進入戰役。',manifest:'讀取遊戲版本清單……',loading:'下載遊戲資料並準備執行環境……',initializing:'準備戰役畫面……',ready:'兵馬已整備，請開始遊戲。',start:'開始遊戲',failed:'遊戲載入失敗。請檢查連線，再重試載入。',runtime:'執行環境',working:'準備中',done:'已就緒',bytes:'遊戲資料已讀取',excludes:'不含執行環境',playMusic:'播放音樂',musicOn:'音樂：開',musicOff:'音樂：關',gesture:'點擊畫面或按鍵，即可播放原版標題音樂。',musicHint:'音量與遊戲內設定共用；切換分頁時暫停播放。',noAudio:'此瀏覽器不支援音訊播放。'},
  ja:{subtitle:'大陸戦役',scenario:'184年・黄巾の乱',description:'兵馬を整え、戦役の開始を準備しています。',manifest:'ゲームのバージョン情報を確認しています……',loading:'ゲームデータのダウンロードと実行環境の準備中です……',initializing:'戦役画面を準備しています……',ready:'準備が整いました。ゲームを開始してください。',start:'ゲーム開始',failed:'ゲームを読み込めません。接続を確認して、もう一度お試しください。',runtime:'実行環境',working:'準備中',done:'準備完了',bytes:'ゲームデータの読み込み量',excludes:'実行環境を除く',playMusic:'音楽を再生',musicOn:'音楽：入',musicOff:'音楽：切',gesture:'画面のクリック・タッチかキー操作で、原版のタイトル曲を再生します。',musicHint:'音量はゲーム内設定と共通です。別のタブでは再生を一時停止します。',noAudio:'このブラウザーでは音声を再生できません。'}
 };
 const state={phase:'manifest',receivedBytes:0,runtimeReady:false,failed:false,ready:false,canRetry:false};
 let cover,subtitle,scenario,description,message,slot,observer,attached,home,pendingPanel,dismissed=false,motion;
 let startButton,soundButton,audioNote,audio,openingReady=false;
 const background=new Map();
 let resolveEntered;const entered=new Promise(resolve=>{resolveEntered=resolve;});
 function locale(){
  if(root.GameI18n?.locale==='ja'||root.GameI18n?.locale==='zh-Hant')return root.GameI18n.locale;
  try{return root.localStorage?.getItem('three-kingdoms-language')==='ja'?'ja':'zh-Hant';}catch{return 'zh-Hant';}
 }
 function asset(value){
  if(typeof root.GamePaths?.asset==='function')return root.GamePaths.asset(value);
  try{return new URL(value.slice(1),doc.baseURI).href;}catch{return value;}
 }
 function element(tag,className,text){
  const node=doc.createElement(tag);if(className)node.className=className;if(text)node.textContent=text;return node;
 }
 function image(path,className){
  const node=element('img',className);node.src=asset(path);node.alt='';node.draggable=false;node.setAttribute('aria-hidden','true');return node;
 }
 function figure(type){
  const node=element('span','loading-cover-figure loading-cover-'+type);
  for(const frame of ['00','01'])node.append(image('/assets/battle-enhanced/native-'+(type==='rider'?'duelist':'infantry')+'-'+frame+'.png','loading-cover-frame'));
  return node;
 }
 function render(){
  if(!cover||dismissed)return;
  const language=locale(),words=copy[language];
  cover.setAttribute('data-l10n-native',language);cover.setAttribute('lang',language);
  cover.setAttribute('data-phase',state.failed?'failed':openingReady?'ready':state.ready?'initializing':state.phase);
  subtitle.textContent=words.subtitle;scenario.textContent=words.scenario;description.textContent=words.description;
  let text=state.failed?words.failed:openingReady?words.ready:words[state.ready?'initializing':state.phase]||words.loading;
  if(!state.failed&&!state.ready&&state.phase==='loading'){
   text+='\n'+words.runtime+'：'+(state.runtimeReady?words.done:words.working);
   if(state.receivedBytes>0)text+=' · '+words.bytes+' '+(state.receivedBytes/1024).toFixed(1)+' KiB（'+words.excludes+'）';
  }
  message.textContent=text;message.hidden=!openingReady&&!!attached&&!attached.hidden;
  startButton.textContent=words.start;startButton.hidden=!openingReady||state.failed;startButton.disabled=!openingReady||state.failed;
  renderAudio();
 }
 function prepareAudio(){
  if(!audio&&typeof root.GameAudio?.page==='function'){audio=root.GameAudio.page();audio.setCoverActive(true);}
  return audio;
 }
 function renderAudio(){
  if(!soundButton||dismissed)return;
  const words=copy[locale()],player=prepareAudio(),settings=player?.getSettings(),status=player?.getStatus();
  const supported=!!status?.supported,on=!!status?.unlocked&&!settings?.muted&&settings?.bgmVolume>0;
  soundButton.hidden=!supported;soundButton.setAttribute('aria-pressed',String(on));
  soundButton.textContent=on?words.musicOn:settings?.muted||settings?.bgmVolume===0?words.musicOff:words.playMusic;
  audioNote.textContent=!supported?words.noAudio:status.unlocked||settings?.muted||settings?.bgmVolume===0?words.musicHint:words.gesture;
 }
 function unlockMusic(event){
  if(!event?.isTrusted||dismissed||!cover||event.type==='pointerdown'&&!cover.contains(event.target))return;
  // Button handlers finish the gesture before updating text or layout. In
  // particular, title-audio hints must not move Start between touch down/up.
  for(let node=event.target;node&&node!==cover;node=node.parentNode)if(node.tagName==='BUTTON')return;
  void prepareAudio()?.unlock().then(renderAudio);
 }
 function toggleMusic(){
  const player=prepareAudio();if(!player)return;
  const enable=soundButton.getAttribute('aria-pressed')!=='true',settings=player.getSettings();
  player.configure({muted:!enable,...(enable&&settings.bgmVolume===0?{bgmVolume:.35}:{})});
  if(enable)void player.unlock().then(renderAudio);else renderAudio();
 }
 function blockBackground(){
  for(const node of doc.body.children){
   if(node===cover||node.tagName==='SCRIPT'||node.tagName==='STYLE')continue;
   if(!background.has(node))background.set(node,node.getAttribute('inert'));
   node.setAttribute('inert','');
  }
 }
 function restoreNode(node){
  if(!background.has(node))return;
  const value=background.get(node);if(value===null)node.removeAttribute('inert');else node.setAttribute('inert',value);
  background.delete(node);
 }
 function motionChanged(){if(cover&&!dismissed)cover.setAttribute('data-motion',motion?.matches?'still':'animated');}
 function releaseStatus(){
  if(!attached||attached.parentNode!==slot)return;
  if(home?.parent&&home.parent.isConnected!==false)home.parent.insertBefore(attached,home.next?.parentNode===home.parent?home.next:null);
  else doc.querySelector('#notice')?.insertAdjacentElement('afterend',attached);
 }
 function dismiss(){
  if(dismissed||!cover)return;
  dismissed=true;cover.hidden=true;cover.setAttribute('aria-hidden','true');
  for(const node of [...background.keys()])restoreNode(node);
  releaseStatus();observer?.disconnect();observer=null;
  audio?.setCoverActive(false);
  resolveEntered();
  doc.removeEventListener('game-language-change',render);doc.removeEventListener('error',imageError,true);
  doc.removeEventListener('pointerdown',unlockMusic,true);doc.removeEventListener('keydown',unlockMusic,true);
  motion?.removeEventListener?.('change',motionChanged);
 }
 function enterGame(){
  checkReady();if(!openingReady||state.failed||dismissed)return;
  void audio?.unlock();audio?.play('confirm');dismiss();
  (doc.querySelector('#scenario')||doc.querySelector('#begin')||doc.querySelector('#allocate'))?.focus?.({preventScroll:true});
 }
 function checkReady(){
  if(dismissed||!cover)return;
  blockBackground();
  const inspector=doc.querySelector('#inspector');if(!inspector)return;
  const controls=[inspector.querySelector('#begin'),inspector.querySelector('#allocate')];
  const notice=doc.querySelector('#notice'),appError=/(?:^|\s)error(?:\s|$)/.test(notice?.className||'')&&(!root.GameBrowserEngine||root.GameBrowserEngine.ready);
  if(appError){dismiss();return;}
  const wasReady=openingReady;
  openingReady=!state.failed&&controls.some(node=>node&&!node.disabled&&!node.hidden);
  if(openingReady!==wasReady){
   render();
   if(openingReady&&(!doc.activeElement||doc.activeElement===doc.body||!cover.contains(doc.activeElement)))startButton.focus?.({preventScroll:true});
  }
 }
 function attachStatus(panel){
  if(!panel||panel.id!=='game-engine-status'||dismissed)return false;
  if(!cover){pendingPanel=panel;return false;}
  if(attached!==panel){releaseStatus();attached=panel;home={parent:panel.parentNode,next:panel.nextSibling};}
  restoreNode(panel);if(panel.parentNode!==slot)slot.append(panel);
  render();return true;
 }
 function update(next={}){
  if(!next||typeof next!=='object'||dismissed)return;
  if(['manifest','loading','initializing'].includes(next.phase))state.phase=next.phase;
  if(Number.isSafeInteger(next.receivedBytes)&&next.receivedBytes>=0)state.receivedBytes=next.receivedBytes;
  for(const key of ['runtimeReady','failed','ready','canRetry'])if(typeof next[key]==='boolean')state[key]=next[key];
  checkReady();render();
 }
 function imageError(event){
  const target=event?.target;if(!cover||!target||!cover.contains(target)||target.tagName!=='IMG')return;
  target.hidden=true;
  if(target.className==='loading-cover-art')cover.setAttribute('data-art-failed','true');
 }
 function start(){
  if(cover||!doc.body)return;
  cover=element('section','loading-cover');cover.id='game-loading-cover';cover.setAttribute('role','region');
  cover.setAttribute('aria-labelledby','game-loading-title');cover.setAttribute('aria-describedby','game-loading-description');
  const shell=element('div','loading-cover-shell'),heading=element('header','loading-cover-heading'),title=element('h1','loading-cover-title');title.id='game-loading-title';
  title.append(element('span','loading-cover-name','三國志'),element('span','loading-cover-number','Ⅱ'));
  subtitle=element('p','loading-cover-subtitle');scenario=element('p','loading-cover-scenario');
  description=element('p','loading-cover-description');description.id='game-loading-description';heading.append(title,subtitle,scenario,description);
  const stage=element('div','loading-cover-stage');stage.setAttribute('aria-hidden','true');
  const march=element('div','loading-cover-march');march.append(figure('rider'),figure('soldier'),figure('soldier'),figure('soldier'));
  stage.append(image('/assets/loading/cover.png','loading-cover-art'),element('div','loading-cover-ground'),march);
  const footer=element('footer','loading-cover-footer');message=element('p','loading-cover-message');message.setAttribute('role','status');message.setAttribute('aria-live','polite');slot=element('div','loading-cover-status-slot');
  startButton=element('button','loading-cover-start');startButton.id='game-loading-start';startButton.type='button';startButton.hidden=true;startButton.disabled=true;startButton.onclick=enterGame;
  const audioControls=element('div','loading-cover-audio');soundButton=element('button','loading-cover-sound');soundButton.id='game-loading-sound';soundButton.type='button';soundButton.onclick=toggleMusic;
  audioNote=element('p','loading-cover-audio-note');audioNote.id='game-loading-audio-note';soundButton.setAttribute('aria-describedby',audioNote.id);audioControls.append(soundButton,audioNote);
  footer.append(message,slot,startButton,audioControls);shell.append(heading,stage,footer);cover.append(shell);doc.body.append(cover);
  try{motion=root.matchMedia?.('(prefers-reduced-motion: reduce)');}catch{}
  motionChanged();motion?.addEventListener?.('change',motionChanged);
  doc.addEventListener('game-language-change',render);doc.addEventListener('error',imageError,true);
  doc.addEventListener('pointerdown',unlockMusic,true);doc.addEventListener('keydown',unlockMusic,true);
  if(typeof root.MutationObserver==='function'){
   observer=new root.MutationObserver(checkReady);
   observer.observe(doc.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['disabled','hidden','class']});
  }
  if(pendingPanel){attachStatus(pendingPanel);pendingPanel=null;}
  prepareAudio();render();checkReady();
 }
 root.GameLoadingCover=Object.freeze({update,attachStatus,whenEntered:()=>entered});
 if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',start,{once:true});else start();
})(window);
