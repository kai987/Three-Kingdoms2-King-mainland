/* Optional three-turn guidance. Observes committed results; never sends commands. */
'use strict';
(function(root){
 const KEY='three-kingdoms-tutorial-choice';
 const MESSAGES={
  'tutorial.title':{'zh-Hant':'最初三旬操作指引',ja:'最初の3旬・操作ガイド'},
  'tutorial.offer':{'zh-Hant':'依實際操作了解編兵、內政與行軍。可隨時結束，不代替你執行命令。',ja:'編制・内政・行軍を実際の操作に沿って案内します。いつでも終了でき、命令を自動実行しません。'},
  'tutorial.start':{'zh-Hant':'開始指引',ja:'ガイドを開始'},
  'tutorial.short':{'zh-Hant':'指引',ja:'ガイド'},
  'tutorial.later':{'zh-Hant':'稍後再說',ja:'あとで'},
  'tutorial.end':{'zh-Hant':'結束指引',ja:'ガイドを終了'},
  'tutorial.focus':{'zh-Hant':'顯示操作位置',ja:'操作する場所を表示'},
  'tutorial.progress':{'zh-Hant':'步驟 {current}／{total}・已經過 {turns}／3旬',ja:'手順 {current}／{total}・経過 {turns}／3旬'},
  'tutorial.city':{'zh-Hant':'選擇本方都市',ja:'自分の都市を選ぶ'},
  'tutorial.city.detail':{'zh-Hant':'在地圖上點選本方城池，確認資金、兵糧與預備兵。',ja:'地図で自勢力の都市を選び、資金・兵糧・予備兵を確認します。'},
  'tutorial.allocate':{'zh-Hant':'確認一次編兵',ja:'兵の編制を確定する'},
  'tutorial.allocate.detail':{'zh-Hant':'進入「軍務 → 編兵」，設定目標兵數並確認。切換下一名武將不消耗額外命令書；完成後結束編兵。',ja:'「軍務 → 編制」で目標兵数を入力し、確定します。次の武将への切替で命令書は追加消費しません。配分後は編制を終了します。'},
  'tutorial.domestic':{'zh-Hant':'委任兩名勢力內政官',ja:'勢力の内政官を2人任命する'},
  'tutorial.domestic.detail':{'zh-Hant':'在勢力內政委任民政官與軍備官，兩人管理全勢力都市。先查看政策與費用；人數不足時可考慮登用地方文吏，或先結束指引。',ja:'勢力の内政で民政官と軍備官を任命し、方針と費用を確認します。2人が全都市を担当します。人数不足なら地方文吏の登用を検討するか、ガイドを終了できます。'},
  'tutorial.route':{'zh-Hant':'查看行軍估算',ja:'行軍の見積りを確認する'},
  'tutorial.route.detail':{'zh-Hant':'在「軍務 → 出陣」選擇目的城與武將，查看日數、兵糧及減員風險。查看或取消不出陣，不必為指引派兵。',ja:'「軍務 → 出陣」で目的地と武将を選び、日数・兵糧・損耗の危険を確認します。見積りの確認だけでよく、出陣する必要はありません。'},
  'tutorial.turn':{'zh-Hant':'推進最初三旬',ja:'最初の3旬を進める'},
  'tutorial.turn.detail':{'zh-Hant':'確認本旬命令與物資，再結束本旬。每旬10日；觀察行軍、收入與內政工作，經過三旬後結束指引。',ja:'今旬の命令と物資を確認して旬を終了します。1旬は10日です。行軍・収入・内政の結果を確認しながら3旬を進めます。'},
  'tutorial.complete':{'zh-Hant':'操作指引完成。可在「更多 → 操作指引」重新開始。',ja:'操作ガイドが完了しました。「その他 → 操作ガイド」から再開できます。'},
  'tutorial.expired':{'zh-Hant':'三旬的指引期間已結束。尚未完成的操作可在「更多 → 操作指引」重新練習。',ja:'3旬の案内期間が終了しました。未確認の操作は「その他 → 操作ガイド」から練習できます。'},
 };
 const STEPS=Object.freeze(['city','allocate','domestic','route','turn']);
 const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function identity(view){const g=view?.game;return g?[view.catalog?.scenario_id,g.player,g.seed].join(':'):'';}
 function createModel(){
  let key='',startTurn=0,status='inactive',done=new Set();
  const step=()=>STEPS.find(name=>!done.has(name));
  function begin(view,offer=false){if(!view?.game)return false;key=identity(view);startTurn=view.game.turn;done=new Set();status=offer?'offer':'active';return true;}
  function observe(view,selectedCity){
   if(identity(view)!==key||!view?.game){status='inactive';return;}
   if(!['active','offer'].includes(status))return;
   const g=view.game,elapsed=g.turn-startTurn;
   if(elapsed<0){status='inactive';return;}
   if(status==='active'){
    if(step()==='city'&&selectedCity&&g.cities?.[selectedCity]?.owner===g.player)done.add('city');
    const posts=g.extension?.domestic?.factions?.[g.player];
    if(step()==='domestic'&&posts?.civil!==null&&posts?.civil!==undefined&&posts?.military!==null&&posts?.military!==undefined)done.add('domestic');
    if(step()==='turn'&&elapsed>=3)done.add('turn');
   }
   if(done.size===STEPS.length)status='complete';
   else if(elapsed>=3)status=status==='offer'?'inactive':'expired';
  }
  function command(kind,payload,before,after){
   if(status!=='active'||identity(after)!==key)return;
   if(kind==='allocate'&&step()==='allocate'&&after.revision>before.revision)done.add('allocate');
   observe(after);
  }
  return {begin,observe,command,routePreview(){if(status==='active'&&step()==='route')done.add('route');},dismiss(){status='inactive';},
   state:()=>({status,key,startTurn,step:step()||null,completed:[...done]})};
 }
 function create(options={}){
  const doc=options.document||root.document,i18n=options.i18n||root.GameI18n,model=createModel();
  const getView=options.getView||(()=>null),getSelection=options.getSelection||(()=>null);
  const compact=root.matchMedia?.('(max-width:1000px), (max-height:540px)');
  i18n?.registerMessages?.(MESSAGES);
  let node=null,signature='',highlight=null;
  const text=(id,values={})=>i18n?.message?i18n.message(id,values):Object.entries(values).reduce((s,[key,value])=>s.replaceAll('{'+key+'}',String(value)),MESSAGES[id][i18n?.locale==='ja'?'ja':'zh-Hant']);
  function preference(){try{return (options.storage||root.localStorage)?.getItem(KEY)||'';}catch{return '';}}
  function remember(value){try{(options.storage||root.localStorage)?.setItem(KEY,value);}catch{}}
  function clearHighlight(){highlight?.classList?.remove('game-tutorial-target');highlight=null;}
  function target(){
   const step=model.state().step,view=getView();
   if(step==='city'){
    const id=Object.values(view?.game?.cities||{}).find(c=>c.owner===view.game.player)?.id;
    return id?doc.querySelector(`#world-map .city-hit[data-city="${id}"]`):null;
   }
   if(step==='allocate'||step==='route'){
    const control=doc.querySelector(step==='allocate'?'#allocate':'#depart');
    if(control&&!control.closest('[hidden]'))return control;
    return doc.querySelector('#city-command-tab-army');
   }
   return doc.querySelector(step==='domestic'?'#faction-domestic':'#end-turn');
  }
  function focusTarget(){
   clearHighlight();const control=target();if(!control)return;
   const details=control.closest?.('details');if(details)details.open=true;
   control.scrollIntoView?.({block:'nearest',behavior:'instant'});control.focus?.({preventScroll:true});
   control.classList?.add('game-tutorial-target');highlight=control;
  }
  function start(){
   if(options.isBusy?.())return;
   remember('started');
   const toggle=doc?.querySelector?.('#inspector-toggle');
   if(compact?.matches&&toggle?.getAttribute('aria-expanded')==='false')toggle.click();
   model.begin(getView());observe(getView());
  }
  function render(){
   const state=model.state(),inspector=doc?.querySelector?.('#inspector');
   // Keep the invitation in the compact bar's own flow. A heading below that
   // sticky bar can be fully covered when the longer command panel is scrolled.
   const offerHost=compact?.matches&&doc?.querySelector?.('.mobile-inspector-bar');
   const host=state.status==='offer'?(offerHost||inspector?.querySelector?.('.inspector-heading')||inspector):inspector;
   if(state.status==='inactive'||!host||getView()?.game?.phase!=='city'){node?.remove?.();signature='';clearHighlight();return;}
   if(!node){node=doc.createElement('section');node.id='game-tutorial';node.className='game-tutorial';node.setAttribute('aria-labelledby','tutorial-title');}
   if(node.parentElement!==host){if(state.status==='offer')host.append(node);else host.prepend(node);}
   const turns=Math.max(0,Math.min(3,(getView()?.game?.turn||state.startTurn)-state.startTurn));
   const next=JSON.stringify([state,i18n?.locale,turns]);if(next===signature)return;signature=next;clearHighlight();
   node.setAttribute('data-l10n-native',i18n?.locale==='ja'?'ja':'zh-Hant');
   node.className='game-tutorial'+(state.status==='offer'?' game-tutorial-offer':'');
   const button=(id,label)=>`<button type="button" id="${id}">${escape(text(label))}</button>`;
   let body;
   if(state.status==='offer')body=`<button type="button" id="tutorial-start" title="${escape(text('tutorial.offer'))}" aria-label="${escape(text('tutorial.start'))}">${escape(text('tutorial.short'))}</button>`;
   else if(state.status==='complete'||state.status==='expired')body=`<p role="status">${escape(text('tutorial.'+state.status))}</p>${button('tutorial-close','tutorial.end')}`;
   else body=`<p class="game-tutorial-progress">${escape(text('tutorial.progress',{current:state.completed.length+1,total:STEPS.length,turns}))}</p><strong>${escape(text('tutorial.'+state.step))}</strong><p>${escape(text('tutorial.'+state.step+'.detail'))}</p><div class="game-tutorial-actions">${button('tutorial-focus','tutorial.focus')}${button('tutorial-end','tutorial.end')}</div>`;
   if(state.status==='offer'){node.removeAttribute('aria-labelledby');node.setAttribute('aria-label',text('tutorial.title'));node.innerHTML=body;}
   else{node.removeAttribute('aria-label');node.setAttribute('aria-labelledby','tutorial-title');node.innerHTML=`<h3 id="tutorial-title">${escape(text('tutorial.title'))}</h3>${body}`;}
   node.querySelector('#tutorial-start')?.addEventListener('click',start);
   for(const id of ['tutorial-end','tutorial-later','tutorial-close'])node.querySelector('#'+id)?.addEventListener('click',()=>{remember('dismissed');model.dismiss();render();});
   node.querySelector('#tutorial-focus')?.addEventListener('click',focusTarget);
   if(state.status==='complete')remember('completed');
  }
  function observe(view){model.observe(view,getSelection());render();}
  const language=()=>{signature='';render();};doc?.addEventListener?.('game-language-change',language);
  compact?.addEventListener?.('change',render);
  return {observe,start,
   command(kind,payload,before,after){if(kind==='new'){model.dismiss();if(!preference())model.begin(after,true);}else model.command(kind,payload,before,after);observe(after);},
   routePreview(){model.routePreview();render();},loaded(){model.dismiss();render();},state:model.state,
   dispose(){model.dismiss();render();doc?.removeEventListener?.('game-language-change',language);compact?.removeEventListener?.('change',render);}};
 }
 const api={KEY,STEPS,MESSAGES,createModel,create};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameTutorial=api;
})(typeof window==='object'?window:globalThis);
