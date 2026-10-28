/* City treasure and faction rewards. Inspection and drafts never write game state or RNG. */
'use strict';
(function(root){
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const choose=(locale,tc,ja)=>locale==='ja'?ja:tc;
 const defaults=Object.freeze({enabled:false,target_loyalty:90,gold_budget:100,gold_floor:100,treasure_floor:1,prefer:'gold'});
 const policyLimits=Object.freeze({target_loyalty:[1,100],gold_budget:[0,1000000],gold_floor:[0,100000000],treasure_floor:[0,99]});
 function bounded(value,max,min=0){const n=Number(value);return Math.max(min,Math.min(max,Number.isFinite(n)?Math.trunc(n):min));}
 function ref(value){
  if(root.GameOfficerChoices?.ref)return root.GameOfficerChoices.ref(value);
  if(typeof value==='number')return Number.isSafeInteger(value)&&value>=0&&value<=65534?value:null;
  if(typeof value!=='string')return null;
  if(/^clerk-[0-9]{6,12}$/.test(value)){const n=Number(value.slice(6));return n>=1&&n<=1000000&&value===`clerk-${String(n).padStart(6,'0')}`?value:null;}
  return /^(?:0|[1-9][0-9]*)$/.test(value)&&Number.isSafeInteger(Number(value))&&Number(value)<=65534?Number(value):null;
 }
 const data=view=>view?.catalog?.treasury||null;
 const city=(view,id)=>data(view)?.cities?.[id]||null;
 const count=(view,id)=>bounded(view?.game?.extension?.treasury?.cities?.[id]?.treasure??city(view,id)?.treasure??0,99);
 const person=(view,id)=>view?.game?.officers?.[id];
 const ruler=(view,id)=>root.GameOfficerChoices?.isRuler?.(id,view?.game?.extension?.leaders)===true;
 const name=(view,id)=>view?.catalog?.names?.[String(id)]||view?.catalog?.library?.find(p=>String(p.id)===String(id))?.name||String(id??'');
 const translated=(value,locale)=>root.GameI18n?.t?root.GameI18n.t(String(value??''),locale):String(value??'');
 const shown=value=>Number.isFinite(value)?String(value):'—';
 function attributes(view,id,locale='zh-Hant'){
  const officer=person(view,id),p=officer?.profile||{},loyalty=ruler(view,id)?'--':shown(officer?.loyalty);
  const experience=root.GameOfficerChoices?.experience?.(officer?.experience)??'—';
  return choose(locale,`兵${shown(officer?.troops)} · 武${shown(p.martial_strength)} · 知${shown(p.intellect)} · 德${shown(p.virtue)} · 忠${loyalty} · 體${shown(officer?.health)} · 經${experience}`,`兵${shown(officer?.troops)}・武${shown(p.martial_strength)}・知${shown(p.intellect)}・徳${shown(p.virtue)}・忠${loyalty}・体力${shown(officer?.health)}・経${experience}`);
 }
 function stable(a,b){return String(a).localeCompare(String(b),undefined,{numeric:true});}
 function sortActors(ids,view){return [...new Map((ids||[]).map(id=>[String(ref(id)),ref(id)]).filter(([,id])=>id!==null)).values()].sort((a,b)=>{
  for(const key of ['virtue','intellect','martial_strength']){const diff=(person(view,b)?.profile?.[key]??-1)-(person(view,a)?.profile?.[key]??-1);if(diff)return diff;}
  return stable(a,b);
 });}
 function sortTargets(targets,view){return [...(targets||[])].filter(p=>ref(p.id)!==null&&!ruler(view,p.id)).sort((a,b)=>(a.loyalty??101)-(b.loyalty??101)||(person(view,b.id)?.profile?.virtue??-1)-(person(view,a.id)?.profile?.virtue??-1)||stable(a.id,b.id));}
 function normalizePolicy(value={}){
  const policy={...defaults,enabled:value.enabled===true,prefer:value.prefer==='treasure'?'treasure':'gold'};
  for(const[key,[min,max]]of Object.entries(policyLimits))policy[key]=bounded(value[key]??defaults[key],max,min);
  return policy;
 }
 function rewardPreview(view,id,target,kind,amount){
  const row=city(view,id),candidate=row?.reward_targets?.find(p=>String(p.id)===String(target)),record=view?.game?.cities?.[id];
  let max=0,quote;
  if(candidate&&!ruler(view,target)&&candidate.loyalty<100){
   if(kind==='gold')max=Math.min(100,bounded(candidate.gold_max??0,100),bounded(record?.gold??0,100000000));
   else if(kind==='treasure'&&candidate.treasure_reward?.amount===1)max=Math.min(1,bounded(candidate.treasure_max??0,1),count(view,id));
  }
  const value=bounded(amount,max,max?1:0);
  if(value>0&&kind==='gold')quote=candidate?.gold_rewards?.find(q=>value>=q.min&&value<=q.max);
  else if(value===1&&kind==='treasure')quote=candidate?.treasure_reward;
  const valid=!!quote&&Number.isInteger(quote.gain)&&quote.gain>0&&Number.isInteger(quote.loyalty)&&quote.loyalty<=100&&quote.loyalty>candidate.loyalty;
  return {max,amount:value,gain:valid?quote.gain:0,loyalty:valid?quote.loyalty:candidate?.loyalty??null,valid};
 }
 function summary(view,id,{locale='zh-Hant',bilingual=true}={}){
  if(!city(view,id)&&!view?.game?.extension?.treasury?.cities?.[id])return '';
  if(bilingual)return ['zh-Hant','ja'].map(language=>`<div data-locale-only="${language}" data-l10n-native="${language}">${summary(view,id,{locale:language,bilingual:false})}</div>`).join('');
  const current=city(view,id),governor=current?current.governor:view?.game?.extension?.treasury?.cities?.[id]?.governor;
  return `<p class="small treasury-city-summary" data-l10n-native="${locale}">${choose(locale,'寶','宝')} <strong data-city-treasure="${escape(id)}">${count(view,id)}</strong>/99 · ${choose(locale,'太守','太守')} ${escape(governor===null||governor===undefined?choose(locale,'尚無適任者','該当者なし'):translated(name(view,governor),locale))}</p>`;
 }
 function create(options={}){
  const doc=options.document||root.document,dialog=options.dialog||doc?.querySelector?.('#dialog'),i18n=options.i18n||root.GameI18n;
  const getView=options.getView||(()=>null),cityName=options.cityName||(id=>id),openDialog=options.openDialog,command=options.command,isBusy=options.isBusy||(()=>false),isPreview=options.isPreview||(()=>false);
  let active=null,pending=false,disposed=false;
  const locale=()=>i18n?.locale==='ja'?'ja':'zh-Hant',text=(tc,ja)=>choose(locale(),tc,ja),label=value=>i18n?.t?i18n.t(String(value??''),locale()):String(value??'');
  const query=selector=>dialog?.querySelector?.(selector),row=()=>city(getView(),active?.city);
  const identity=()=>{const view=getView();return JSON.stringify([view?.catalog?.scenario_id,view?.game?.player,view?.game?.seed,view?.game?.turn]);};
  const showing=()=>!!active&&dialog?.open!==false&&!!query('[data-treasury-dialog]');
  const matches=token=>!disposed&&active===token&&identity()===token.identity&&getView()?.game?.cities?.[token.city]?.owner===token.faction&&getView()?.game?.player===token.faction;
  const canWrite=()=>!!active&&matches(active)&&!isPreview()&&!isBusy()&&!pending&&getView()?.game?.phase==='city'&&row()?.can_manage===true;
  const bookReady=kind=>root.GameCommandBooks?.can(getView(),kind)===true;
  const bookHint=kind=>root.GameCommandBooks?.html(getView(),{kind,locale:locale()})||'';
  const officerLabel=id=>`${label(name(getView(),id))} · ${attributes(getView(),id,locale())}`;
  const select=(id,caption,value,choices)=>`<label class="field">${caption}<select id="${id}">${choices.map(([key,title])=>`<option value="${escape(key??'')}" ${String(value??'')===String(key??'')?'selected':''}>${escape(title)}</option>`).join('')||`<option value="">${text('沒有可選武將','選択できる武将がいません')}</option>`}</select></label>`;
  const number=(id,caption,value,max,min=0)=>`<label class="field">${caption}<input id="${id}" type="number" min="${min}" max="${max}" step="1" value="${bounded(value,max,min)}"></label>`;
  const targets=()=>sortTargets(row()?.reward_targets,getView());
  const actors=()=>sortActors(row()?.eligible_actors,getView());
  function reconcile(){
   const source=row(),available=actors(),candidates=sortActors(source?.governor_candidates,getView()),eligible=targets();
   if(!available.some(id=>String(id)===String(active.actor)))active.actor=available[0]??null;
   if(active.governor!==null&&!candidates.some(id=>String(id)===String(active.governor)))active.governor=null;
   if(!eligible.some(p=>String(p.id)===String(active.target)))active.target=eligible[0]?.id??null;
  }
  function reason(){
   if(!matches(active)||isPreview())return text('目前無法操作這座城池。','現在、この都市では操作できません。');
   if(getView()?.game?.phase!=='city')return text('請在戰略階段操作。','戦略段階で操作してください。');
   if(!root.GameCommandBooks?.can(getView(),'search_treasure'))return root.GameCommandBooks?.reason(getView(),'search_treasure',locale())||text('命令書資料尚未就緒。','命令書の情報を読み込めません。');
   return '';
  }
  function update(){
   if(!active||!showing())return;
   const source=row(),view=getView(),writable=canWrite(),available=actors(),selected=ref(active.actor),eligible=available.some(id=>id===selected),stock=count(view,active.city),saleMax=Math.min(stock,bounded(source?.sell_max??0,99));
   const sale=query('#treasury-sell-amount');if(sale){active.sale=bounded(active.sale,saleMax,saleMax?1:0);sale.max=String(saleMax);sale.min=String(saleMax?1:0);sale.value=String(active.sale);}
   const quote=rewardPreview(view,active.city,active.target,active.kind,active.amounts[active.kind]),amount=query('#treasury-reward-amount');
   active.amounts[active.kind]=quote.amount;
   if(amount){amount.max=String(quote.max);amount.min=String(quote.max?1:0);amount.value=String(quote.amount);}
   const set=(id,disabled)=>{const button=query('#'+id);if(button)button.disabled=disabled;};
   set('treasury-search',!writable||!bookReady('search_treasure')||!source?.can_search||!eligible||stock>=99||(view?.game?.cities?.[active.city]?.gold??0)<(source?.search_fee??20));
   set('treasury-sell',!writable||!bookReady('sell_treasure')||!source?.can_sell||!eligible||active.sale<1||saleMax<1);
   set('treasury-sell-max',pending||saleMax<1);
   set('treasury-reward',!writable||!bookReady('reward_officer')||!source?.can_reward||!quote.valid);
   set('treasury-reward-max',pending||quote.max<1);
   set('treasury-set-governor',!writable);
   set('treasury-save-policy',!writable);
   const actorSummary=query('#treasury-actor-summary');if(actorSummary)actorSummary.textContent=selected===null?'':officerLabel(selected);
   const chance=source?.search_chances?.[String(selected)],searchPreview=query('#treasury-search-preview');
   if(searchPreview)searchPreview.textContent=text(`尋寶花費${source?.search_fee??20}金，成功率${Number.isInteger(chance)?chance:'—'}%；成功增加1件寶。`,`探索費は資金${source?.search_fee??20}、成功率${Number.isInteger(chance)?chance:'—'}%。成功すると宝が1個増えます。`);
   const salePreview=query('#treasury-sell-preview');if(salePreview)salePreview.textContent=text(`出售${active.sale}件寶，收入${active.sale*(data(view)?.rules?.sell_gold_per_treasure??100)}金。`,`宝${active.sale}個を売却し、資金${active.sale*(data(view)?.rules?.sell_gold_per_treasure??100)}を得ます。`);
   const preview=query('#treasury-reward-preview');if(preview){preview.textContent=quote.valid?text(`賞賜後忠誠 ${quote.loyalty}（+${quote.gain}）。`,`褒美後の忠誠 ${quote.loyalty}（+${quote.gain}）。`):text('目前沒有可執行的賞賜預覽。','現在、実行できる褒美の予測がありません。');preview.dataset.gain=String(quote.gain);preview.dataset.loyalty=String(quote.loyalty??'');}
   const boundary=query('#treasury-boundary');if(boundary)boundary.textContent=reason();
   i18n?.apply?.();
  }
  function feedback(){return active.error?`<p class="staff-command-error" role="alert">${text('操作未完成，請核對最新庫存、太守與武將後重試。','操作を完了できませんでした。最新の在庫・太守・武将を確認して再度お試しください。')}</p>`:active.saved?`<p class="domestic-saved" role="status">${text('操作已完成。庫存與預覽已更新；返回戰役可查看戰報與圖文事件。','操作が完了しました。在庫と予測を更新しました。戦役へ戻ると報告と画像付きイベントを確認できます。')}</p>`:'';}
  function render(){
   if(!active||!matches(active)||!row()||typeof openDialog!=='function')return false;
   reconcile();const source=row(),view=getView(),p=active.policy,candidates=sortActors(source.governor_candidates,view),available=actors(),eligible=targets(),governor=source.governor;
   const maxSale=Math.min(count(view,active.city),bounded(source.sell_max??0,99));
   const body=`<div class="treasury-panel" data-treasury-dialog data-treasury-city="${escape(active.city)}" data-l10n-native="${locale()}">${summary(view,active.city,{locale:locale(),bilingual:false})}${bookHint()}<p class="small" id="treasury-boundary" role="status"></p>${feedback()}
    <fieldset><legend>${text('太守任命','太守の任命')}</legend><p class="small" data-treasury-governor>${text('目前太守','現在の太守')}：${governor===null||governor===undefined?text('尚無適任者','該当者なし'):escape(officerLabel(governor))} · ${source.governor_mode==='manual'?text('指定','指定'):text('自動','自動')}</p>${select('treasury-governor',text('指定太守','太守を指定'),active.governor,[[null,text('自動：本城君主優先，其餘按德排序','自動：この都市の君主を優先、他は徳順')],...candidates.map(id=>[id,officerLabel(id)])])}<button id="treasury-set-governor" data-treasury-confirm>${text('確認太守任命','太守の任命を確定')}</button></fieldset>
    <fieldset><legend>${text('尋寶與出售','宝の探索と売却')}</legend>${select('treasury-actor',text('執行武將','実行武将'),active.actor,available.map(id=>[id,officerLabel(id)]))}<p class="small" id="treasury-actor-summary"></p><p class="small" id="treasury-search-preview"></p>${bookHint('search_treasure')}<button id="treasury-search" data-treasury-confirm>${text('確認尋寶','宝の探索を確定')}</button><div class="treasury-amount">${number('treasury-sell-amount',text('出售寶物數量','売却する宝の数'),active.sale,maxSale,maxSale?1:0)}<button id="treasury-sell-max" data-treasury-max>${text('最大值','最大')}</button></div><p class="small" id="treasury-sell-preview"></p>${bookHint('sell_treasure')}<button id="treasury-sell" data-treasury-confirm>${text('確認出售','売却を確定')}</button><p class="small">${text('尋寶與出售使用全勢力共用命令書，可連續投入同一城。每城最多99件寶。','探索・売却は勢力共通の命令書を使い、同じ都市で続けて実行できます。各都市の宝は99個までです。')}</p></fieldset>
    <fieldset><legend>${text('賞賜武將','武将に褒美を与える')}</legend><p class="small">${text('由已生效的太守經辦；勢力可賞賜太守本人，目前君主不列為賞賜目標。使用全勢力共用命令書。','保存済みの太守が担当します。勢力から太守自身への褒美も可能ですが、現在の君主は対象外です。勢力共通の命令書を使います。')}</p>${select('treasury-reward-officer',text('賞賜對象（忠誠低者優先）','対象（忠誠の低い順）'),active.target,eligible.map(target=>[target.id,officerLabel(target.id)]))}${select('treasury-reward-kind',text('賞賜種類','褒美の種類'),active.kind,[['gold',text('金錢（每次最多100金）','資金（1回100まで）')],['treasure',text('寶物（每次1件）','宝（1回1個）')]])}<div class="treasury-amount">${number('treasury-reward-amount',text('賞賜數量','与える数'),active.amounts[active.kind],100)}<button id="treasury-reward-max" data-treasury-max>${text('最大值','最大')}</button></div><p id="treasury-reward-preview" role="status" aria-live="polite"></p>${bookHint('reward_officer')}<button id="treasury-reward" class="primary" data-treasury-confirm>${text('確認賞賜','褒美を確定')}</button><p class="small">${text('以下預覽依本作太守德值與賞賜規則計算，忠誠最高100；不是已還原的原版ROM公式。未確認不扣資源、不抽取事件。','予測は本作の太守の徳と褒美のルールで計算し、忠誠の上限は100です。原作ROMから復元した計算式ではありません。確定前に資源消費や抽選は起こりません。')}</p></fieldset>
    <fieldset><legend>${text('全勢力自動賞賜方針','勢力全体の自動褒美方針')}</legend><label class="domestic-toggle"><input id="treasury-policy-enabled" type="checkbox" ${p.enabled?'checked':''}>${text('啟用自動賞賜','自動褒美を有効にする')}</label><div class="domestic-input-grid">${number('treasury-policy-target',text('目標忠誠','忠誠の目標'),p.target_loyalty,100,1)}${number('treasury-policy-budget',text('全勢力每旬金錢預算','勢力全体・1旬の資金予算'),p.gold_budget,1000000)}${number('treasury-policy-gold-floor',text('各城保留金錢','各都市に残す資金'),p.gold_floor,100000000)}${number('treasury-policy-treasure-floor',text('各城保留寶物','各都市に残す宝'),p.treasure_floor,99)}</div>${select('treasury-policy-prefer',text('優先賞賜種類','優先する褒美'),p.prefer,[['gold',text('優先金錢','資金を優先')],['treasure',text('優先寶物','宝を優先')]])}<p class="small">${text('儲存後由各城太守依行動與庫存條件執行。目標忠誠是自動方針，不限制手動賞賜；玩家與AI使用相同規則。','保存後、各都市の太守が行動・在庫の条件に従って実行します。忠誠目標は自動方針であり、手動の褒美の上限ではありません。プレイヤーとAIは同じルールです。')}</p><button id="treasury-save-policy" data-treasury-confirm>${text('儲存自動賞賜方針','自動褒美方針を保存')}</button></fieldset></div>`;
   if(openDialog(text(`寶物與賞賜 · ${label(cityName(active.city))}`,`宝と褒美・${label(cityName(active.city))}`),body,`<button data-cancel>${text('返回戰役','戦役へ戻る')}</button>`)===undefined)return false;
   query('#treasury-actor').onchange=()=>{if(!pending){active.actor=ref(query('#treasury-actor').value);update();}};
   query('#treasury-governor').onchange=()=>{if(!pending)active.governor=query('#treasury-governor').value===''?null:ref(query('#treasury-governor').value);};
   query('#treasury-reward-officer').onchange=()=>{if(!pending){active.target=ref(query('#treasury-reward-officer').value);update();}};
   query('#treasury-reward-kind').onchange=()=>{if(!pending){active.kind=query('#treasury-reward-kind').value==='treasure'?'treasure':'gold';update();}};
   for(const[id,apply]of [['treasury-sell-amount',input=>{active.sale=input.value;}],['treasury-reward-amount',input=>{active.amounts[active.kind]=input.value;}]]){const input=query('#'+id);input.oninput=input.onchange=input.onblur=()=>{if(!pending){apply(input);update();}};}
   query('#treasury-sell-max').onclick=()=>{if(!pending){active.sale=Math.min(count(getView(),active.city),bounded(row()?.sell_max??0,99));update();}};
   query('#treasury-reward-max').onclick=()=>{if(!pending){active.amounts[active.kind]=rewardPreview(getView(),active.city,active.target,active.kind,active.amounts[active.kind]).max;update();}};
   query('#treasury-search').onclick=()=>submit('search_treasure',()=>({city:active.city,actor:ref(active.actor)}),()=>row()?.can_search===true&&count(getView(),active.city)<99&&(getView()?.game?.cities?.[active.city]?.gold??0)>=(row()?.search_fee??20)&&actors().includes(ref(active.actor)));
   query('#treasury-sell').onclick=()=>submit('sell_treasure',()=>({city:active.city,actor:ref(active.actor),amount:active.sale}),()=>row()?.can_sell===true&&actors().includes(ref(active.actor))&&active.sale>=1&&active.sale<=Math.min(count(getView(),active.city),bounded(row()?.sell_max??0,99)));
   query('#treasury-reward').onclick=()=>submit('reward_officer',()=>({city:active.city,officer:ref(active.target),kind:active.kind,amount:active.amounts[active.kind]}),()=>row()?.can_reward===true&&rewardPreview(getView(),active.city,active.target,active.kind,active.amounts[active.kind]).valid);
   query('#treasury-set-governor').onclick=()=>submit('set_governor',()=>({city:active.city,officer:active.governor}),()=>active.governor===null||sortActors(row()?.governor_candidates,getView()).includes(ref(active.governor)));
   query('#treasury-save-policy').onclick=()=>submit('set_treasury_policy',()=>({faction:active.faction,policy:normalizePolicy(active.policy)}));
   for(const[id,key]of [['target','target_loyalty'],['budget','gold_budget'],['gold-floor','gold_floor'],['treasure-floor','treasure_floor']]){const input=query('#treasury-policy-'+id),[min,max]=policyLimits[key];input.oninput=input.onchange=input.onblur=()=>{if(!pending){input.value=String(bounded(input.value,max,min));active.policy[key]=Number(input.value);}};}
   query('#treasury-policy-enabled').onchange=()=>{if(!pending)active.policy.enabled=query('#treasury-policy-enabled').checked;};
   query('#treasury-policy-prefer').onchange=()=>{if(!pending)active.policy.prefer=query('#treasury-policy-prefer').value==='treasure'?'treasure':'gold';};
   update();return true;
  }
  async function submit(kind,payload,guard=()=>true){
   if(!canWrite())return false;update();if(!canWrite()||!bookReady(kind)||!guard())return false;
   const token=active,request=payload();pending=true;
   for(const id of ['treasury-search','treasury-sell','treasury-reward','treasury-set-governor','treasury-save-policy']){const button=query('#'+id);if(button)button.disabled=true;}
   let success=false;try{success=await command(kind,request)!==false;}catch{success=false;}finally{pending=false;}
   if(!matches(token)||!showing())return success;
   token.error=!success;token.saved=success;
   if(success){const source=row();if(kind==='set_treasury_policy')token.policy=normalizePolicy(data(getView())?.factions?.[token.faction]?.policy);if(kind==='set_governor')token.governor=source?.governor_mode==='manual'?ref(source.governor):null;}
   const scroll=dialog.scrollTop;render();dialog.scrollTop=scroll;return success;
  }
  function refresh(){if(!disposed&&!pending&&showing()&&matches(active)){const scroll=dialog.scrollTop;render();dialog.scrollTop=scroll;}}
  function open(id){
   const view=getView(),record=view?.game?.cities?.[id],source=city(view,id);
   if(disposed||pending||isBusy()||isPreview()||view?.game?.phase!=='city'||!record||record.owner!==view.game.player||!source?.can_manage)return false;
   active={city:id,faction:view.game.player,identity:identity(),actor:null,target:null,kind:'gold',amounts:{gold:100,treasure:1},sale:1,governor:source.governor_mode==='manual'?ref(source.governor):null,policy:normalizePolicy(data(view)?.factions?.[view.game.player]?.policy)};
   const opened=render();if(opened)dialog.scrollTop=0;return opened;
  }
  doc?.addEventListener?.('game-language-change',refresh);
  return {open,refresh,dispose(){disposed=true;active=null;doc?.removeEventListener?.('game-language-change',refresh);}};
 }
 const api=Object.freeze({create,data,city,count,summary,attributes,sortActors,sortTargets,rewardPreview,normalizePolicy,bounded,ref});
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.GameTreasury=api;
})(typeof window!=='undefined'?window:globalThis);
