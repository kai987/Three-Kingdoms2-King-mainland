/* Presentation-only boot cover. Real controls, not artwork or timers, end it. */
'use strict';
(function(root){
 const doc=root.document;if(!doc)return;
 const copy={
  'zh-Hant':{subtitle:'大陸戰役',scenario:'184年・黃巾之亂',description:'正在整備兵馬，準備進入戰役。',manifest:'讀取遊戲版本清單……',loading:'下載遊戲資料並準備執行環境……',initializing:'準備戰役畫面……',failed:'遊戲載入失敗。請檢查連線，再重試載入。',runtime:'執行環境',working:'準備中',done:'已就緒',bytes:'遊戲資料已讀取',excludes:'不含執行環境'},
  ja:{subtitle:'大陸戦役',scenario:'184年・黄巾の乱',description:'兵馬を整え、戦役の開始を準備しています。',manifest:'ゲームのバージョン情報を確認しています……',loading:'ゲームデータのダウンロードと実行環境の準備中です……',initializing:'戦役画面を準備しています……',failed:'ゲームを読み込めません。接続を確認して、もう一度お試しください。',runtime:'実行環境',working:'準備中',done:'準備完了',bytes:'ゲームデータの読み込み量',excludes:'実行環境を除く'}
 };
 const state={phase:'manifest',receivedBytes:0,runtimeReady:false,failed:false,ready:false,canRetry:false};
 let cover,subtitle,scenario,description,message,slot,observer,attached,home,pendingPanel,dismissed=false,motion;
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
  cover.setAttribute('data-phase',state.failed?'failed':state.ready?'initializing':state.phase);
  subtitle.textContent=words.subtitle;scenario.textContent=words.scenario;description.textContent=words.description;
  let text=state.failed?words.failed:words[state.ready?'initializing':state.phase]||words.loading;
  if(!state.failed&&!state.ready&&state.phase==='loading'){
   text+='\n'+words.runtime+'：'+(state.runtimeReady?words.done:words.working);
   if(state.receivedBytes>0)text+=' · '+words.bytes+' '+(state.receivedBytes/1024).toFixed(1)+' KiB（'+words.excludes+'）';
  }
  message.textContent=text;message.hidden=!!attached&&!attached.hidden;
 }
 function motionChanged(){if(cover&&!dismissed)cover.setAttribute('data-motion',motion?.matches?'still':'animated');}
 function releaseStatus(){
  if(!attached||attached.parentNode!==slot)return;
  if(home?.parent&&home.parent.isConnected!==false)home.parent.insertBefore(attached,home.next?.parentNode===home.parent?home.next:null);
  else doc.querySelector('#notice')?.insertAdjacentElement('afterend',attached);
 }
 function checkReady(){
  if(dismissed||!cover)return;
  const inspector=doc.querySelector('#inspector');if(!inspector)return;
  const controls=[inspector.querySelector('#begin'),inspector.querySelector('#allocate')];
  const notice=doc.querySelector('#notice'),appError=/(?:^|\s)error(?:\s|$)/.test(notice?.className||'')&&(!root.GameBrowserEngine||root.GameBrowserEngine.ready);
  if(!controls.some(node=>node&&!node.disabled&&!node.hidden)&&!appError)return;
  dismissed=true;cover.hidden=true;cover.setAttribute('aria-hidden','true');
  releaseStatus();observer?.disconnect();observer=null;
  doc.removeEventListener('game-language-change',render);doc.removeEventListener('error',imageError,true);
  motion?.removeEventListener?.('change',motionChanged);
 }
 function attachStatus(panel){
  if(!panel||panel.id!=='game-engine-status'||dismissed)return false;
  if(!cover){pendingPanel=panel;return false;}
  if(attached!==panel){releaseStatus();attached=panel;home={parent:panel.parentNode,next:panel.nextSibling};}
  if(panel.parentNode!==slot)slot.append(panel);
  render();return true;
 }
 function update(next={}){
  if(!next||typeof next!=='object'||dismissed)return;
  if(['manifest','loading','initializing'].includes(next.phase))state.phase=next.phase;
  if(Number.isSafeInteger(next.receivedBytes)&&next.receivedBytes>=0)state.receivedBytes=next.receivedBytes;
  for(const key of ['runtimeReady','failed','ready','canRetry'])if(typeof next[key]==='boolean')state[key]=next[key];
  render();checkReady();
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
  footer.append(message,slot);shell.append(heading,stage,footer);cover.append(shell);doc.body.append(cover);
  try{motion=root.matchMedia?.('(prefers-reduced-motion: reduce)');}catch{}
  motionChanged();motion?.addEventListener?.('change',motionChanged);
  doc.addEventListener('game-language-change',render);doc.addEventListener('error',imageError,true);
  if(typeof root.MutationObserver==='function'){
   observer=new root.MutationObserver(checkReady);
   observer.observe(doc.documentElement,{childList:true,subtree:true,attributes:true,attributeFilter:['disabled','hidden','class']});
  }
  if(pendingPanel){attachStatus(pendingPanel);pendingPanel=null;}
  render();checkReady();
 }
 root.GameLoadingCover=Object.freeze({update,attachStatus});
 if(doc.readyState==='loading')doc.addEventListener('DOMContentLoaded',start,{once:true});else start();
})(window);
