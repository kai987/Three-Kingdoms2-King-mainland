/* Confirm the actual faction-book price before sending a player command.
 * This overlay never sends a request, changes the campaign or spends a book. */
'use strict';
(function(root){
 const ACTIONS=Object.freeze({
  recruit:['徵募預備兵','予備兵の徴募'],allocate:['編兵','兵の編制'],
  recruit_officer:['登用武將','武将の登用'],persuade_officer:['勸誘武將','武将の勧誘'],
  staff_recruit:['招募地方文吏','地方文吏の採用'],hire_staff:['錄用地方文吏','地方文吏の採用'],
  depart:['出陣','出陣'],transfer:['調動武將','武将の移動'],dispatch_transport:['派遣運輸隊','輸送隊の派遣'],
  resupply_march:['補給在途部隊','行軍中の部隊への補給'],transport_treasure:['運送寶物','宝の輸送'],
  search_treasure:['探索寶物','宝の探索'],reward_officer:['賞賜武將','武将への褒美'],sell_treasure:['出售寶物','宝の売却'],
  develop_town:['開發町設施','町の開発'],treat_officer:['治療武將','武将の治療'],study_officer:['武將進修','武将の学習'],
  trade_grain:['交易兵糧','兵糧の取引'],buy_equipment:['購買裝備','装備の購入'],equip_owned:['更換裝備','装備の変更'],
  improve_prevention:['加強防災','防災の強化']
 });
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const choose=(locale,tc,ja)=>locale==='ja'?ja:tc;
 function quote(view,kind,payload={},options={}){
  const amount=options.books?.cost(view,kind,payload);
  if(amount===null||amount===undefined){
   if(ACTIONS[kind])throw Error(choose(options.locale,'命令書費用尚未就緒，請重新載入後再試。','命令書の必要枚数を読み込めません。再読込してください。'));
   return null;
  }
  if(!Number.isSafeInteger(amount)||amount<0||amount>13)throw Error('Invalid command-book confirmation price');
  const locale=options.locale||'zh-Hant',labels=ACTIONS[kind];
  if(amount>0&&!labels)throw Error('Unknown command-book confirmation action');
  const cities=view?.game?.cities||{},id=[payload.city,payload.source].find(value=>typeof value==='string'&&Object.hasOwn(cities,value))||null;
  const raw=id?(options.cityName?.(id)||id):choose(locale,'本勢力','自勢力');
  const city=options.translate?.(raw,locale)||raw,action=labels?.[locale==='ja'?1:0]||kind;
  return{kind,amount,city_id:id,city,action,message:choose(locale,
   `將消耗${amount}張命令書，在「${city}」執行「${action}」。是否確定？`,
   `命令書${amount}枚を使い、「${city}」で「${action}」を実行します。よろしいですか？`)};
 }
 function create({document:doc,books,getView,cityName,i18n,onSound=()=>{}}){
  const dialog=doc?.getElementById('order-confirm-dialog');
  let pending=null,disposed=false;
  const priced=(view,kind,payload,locale)=>quote(view,kind,payload,{books,cityName,locale,translate:(value,language)=>i18n?.t?.(value,language)||value});
  const identity=view=>JSON.stringify([view?.revision,view?.catalog?.scenario_id,view?.game?.turn,view?.game?.player]);
  function finish(accepted){
   const current=pending;if(!current)return;
   pending=null;
   let valid=false;
   try{const view=getView(),fresh=priced(view,current.kind,current.payload,i18n?.locale);valid=accepted&&identity(view)===current.identity&&fresh?.amount===current.amount&&fresh?.city_id===current.city;}catch{}
   if(dialog?.open)dialog.close();
   try{if(current.focus?.isConnected!==false)current.focus?.focus?.({preventScroll:true});}catch{}
   try{onSound(valid?'confirm':'cancel');}catch{}
   current.resolve(!!valid);
  }
  function cancel(event){event?.preventDefault?.();finish(false);}
  function closed(){if(!dialog.open)finish(false);}
  function hidden(){if(doc.visibilityState==='hidden')finish(false);}
  dialog?.addEventListener('cancel',cancel);
  dialog?.addEventListener('close',closed);
  doc?.addEventListener('visibilitychange',hidden);
  function ask(kind,payload={}){
   if(disposed||pending)return Promise.resolve(false);
   const view=getView(),price=priced(view,kind,payload,i18n?.locale);
   if(!price||price.amount===0)return Promise.resolve(true);
   if(!dialog?.showModal)throw Error(choose(i18n?.locale,'無法開啟命令書確認，請重新載入遊戲。','命令書の確認を開けません。ゲームを再読込してください。'));
   const copied=JSON.parse(JSON.stringify(payload)),locale=i18n?.locale||'zh-Hant';
   const both=(tc,ja)=>['zh-Hant','ja'].map(language=>`<span data-locale-only="${language}" data-l10n-native="${language}"${locale===language?'':' hidden'}>${escape(choose(language,tc,ja))}</span>`).join('');
   const tc=priced(view,kind,copied,'zh-Hant'),ja=priced(view,kind,copied,'ja');
   dialog.innerHTML=`<div class="dialog-heading"><h2 id="order-confirm-title">${both('確認命令','命令の確認')}</h2><label class="language-picker">${both('語言','言語')}<select id="order-confirm-language" data-language-picker aria-label="語言 / 言語"><option value="zh-Hant">繁體中文</option><option value="ja">日本語</option></select></label></div><p id="order-confirm-message">${both(tc.message,ja.message)}</p><p class="small">${both('取消不會消耗命令書或資源。','取消しても命令書や資源は消費しません。')}</p><div class="dialog-actions"><button type="button" id="order-confirm-cancel">${both('取消','取消')}</button><button type="button" id="order-confirm-accept" class="primary">${both('確定執行','実行する')}</button></div>`;
   dialog.dataset.commandBookKind=kind;dialog.dataset.commandBookCost=String(price.amount);
   return new Promise(resolve=>{
    pending={resolve,kind,payload:copied,amount:price.amount,city:price.city_id,identity:identity(view),focus:doc.activeElement};
    dialog.querySelector('#order-confirm-cancel').onclick=()=>finish(false);
    dialog.querySelector('#order-confirm-accept').onclick=()=>finish(true);
    try{dialog.showModal();i18n?.apply?.();dialog.querySelector('#order-confirm-accept').focus();}
    catch(error){finish(false);throw error;}
   });
  }
  return{ask,cancel:()=>finish(false),get pending(){return!!pending;},dispose(){finish(false);disposed=true;dialog?.removeEventListener('cancel',cancel);dialog?.removeEventListener('close',closed);doc?.removeEventListener('visibilitychange',hidden);}};
 }
 const api=Object.freeze({ACTIONS,quote,create});
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root)root.GameOrderConfirmation=api;
})(typeof window==='object'?window:globalThis);
