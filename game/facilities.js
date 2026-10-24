/* Facility visits and prevention use committed server quotes, never preview RNG. */
'use strict';
(function(root){
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const choose=(locale,tc,ja)=>locale==='ja'?ja:tc;
 const defaults=Object.freeze({enabled:false,gold_budget:200,gold_floor:100,grain_floor:200,grain_target:2000,target_preparedness:70,heal_below:60,auto_prevent:true,auto_treat:true,auto_develop:false,auto_study:false,auto_trade:false,auto_equip:false});
 const limits=Object.freeze({gold_budget:[0,1000000],gold_floor:[0,100000000],grain_floor:[0,100000000],grain_target:[0,100000000],target_preparedness:[0,99],heal_below:[1,99]});
 const services=Object.freeze({hospital:['醫館','医館'],market:['市場','市場'],school:['學問所','学問所'],armory:['武器屋','武器屋']});
 const bounded=(value,max,min=0)=>Math.max(min,Math.min(max,Number.isFinite(Number(value))?Math.trunc(Number(value)):min));
 function ref(value){
  if(root.GameOfficerChoices?.ref)return root.GameOfficerChoices.ref(value);
  if(typeof value==='number')return Number.isSafeInteger(value)&&value>=0&&value<=65534?value:null;
  if(typeof value!=='string')return null;
  if(/^clerk-[0-9]{6,12}$/.test(value)){const n=Number(value.slice(6));return n>=1&&n<=1000000&&value===`clerk-${String(n).padStart(6,'0')}`?value:null;}
  return /^(?:0|[1-9][0-9]*)$/.test(value)&&Number.isSafeInteger(Number(value))&&Number(value)<=65534?Number(value):null;
 }
 const data=view=>view?.catalog?.facilities||null,city=(view,id)=>data(view)?.cities?.[id]||null;
 const same=(a,b)=>String(a)===String(b);
 const person=(view,id)=>view?.game?.officers?.[id];
 const name=(view,id)=>view?.catalog?.names?.[String(id)]||view?.catalog?.library?.find(p=>same(p.id,id))?.name||String(id??'');
 const stable=(a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true});
 function sortActors(ids,view){return [...new Map((ids||[]).map(id=>[String(ref(id)),ref(id)]).filter(([,id])=>id!==null)).values()].sort((a,b)=>{
  for(const key of ['intellect','virtue','martial_strength','health','experience','troops']){const first=['health','experience','troops'].includes(key)?person(view,a)?.[key]:person(view,a)?.profile?.[key],second=['health','experience','troops'].includes(key)?person(view,b)?.[key]:person(view,b)?.profile?.[key],diff=(second??-1)-(first??-1);if(diff)return diff;}
  return stable(a,b);
 });}
 function attributes(view,id,locale='zh-Hant'){
  const officer=person(view,id),p=officer?.profile||{},shown=value=>Number.isFinite(value)?String(value):'—',ruler=root.GameOfficerChoices?.isRuler?.(id,view?.game?.extension?.leaders)===true,loyalty=ruler?'--':shown(officer?.loyalty),experience=root.GameOfficerChoices?.experience?.(officer?.experience)??'—';
  return choose(locale,`兵${shown(officer?.troops)} · 武${shown(p.martial_strength)} · 知${shown(p.intellect)} · 德${shown(p.virtue)} · 忠${loyalty} · 體${shown(officer?.health)} · 經${experience}`,`兵${shown(officer?.troops)}・武${shown(p.martial_strength)}・知${shown(p.intellect)}・徳${shown(p.virtue)}・忠${loyalty}・体力${shown(officer?.health)}・経${experience}`);
 }
 function normalizePolicy(value={}){const result={...defaults};for(const key of Object.keys(defaults))if(typeof defaults[key]==='boolean')result[key]=value[key]===undefined?defaults[key]:value[key]===true;for(const[key,[min,max]]of Object.entries(limits))result[key]=bounded(value[key]??defaults[key],max,min);result.grain_target=Math.max(result.grain_floor,result.grain_target);return result;}
 function sortEquipment(ids,view){return sortActors(ids,view).sort((a,b)=>{for(const key of ['martial_strength','intellect','virtue','health','experience','troops']){const first=['health','experience','troops'].includes(key)?person(view,a)?.[key]:person(view,a)?.profile?.[key],second=['health','experience','troops'].includes(key)?person(view,b)?.[key]:person(view,b)?.profile?.[key],diff=(second??-1)-(first??-1);if(diff)return diff;}return stable(a,b);});}
 const shown=value=>Number.isFinite(value)?String(value):'—';
 const range=(min,max)=>Number.isFinite(min)&&Number.isFinite(max)?min===max?String(min):`${min}–${max}`:'—';
 function summary(view,id,{locale='zh-Hant',bilingual=true}={}){
  const row=city(view,id);if(!row)return '';
  if(bilingual)return ['zh-Hant','ja'].map(language=>`<div data-locale-only="${language}" data-l10n-native="${language}">${summary(view,id,{locale:language,bilingual:false})}</div>`).join('');
  const tc=`城町發展 ${row.town}/3 · 防災 ${row.preparedness}/99 · 災害損傷 ${row.damage}/50`,ja=`都市発展 ${row.town}/3・防災 ${row.preparedness}/99・災害損傷 ${row.damage}/50`;
  return `<p class="small facility-city-summary" data-l10n-native="${locale}" data-city-facilities="${escape(id)}">${escape(choose(locale,tc,ja))}</p>`;
 }
 function create(options={}){
  const doc=options.document||root.document,dialog=options.dialog||doc?.querySelector?.('#dialog'),i18n=options.i18n||root.GameI18n,getView=options.getView||(()=>null),cityName=options.cityName||(id=>id),openDialog=options.openDialog,command=options.command,isBusy=options.isBusy||(()=>false),isPreview=options.isPreview||(()=>false);
  let active=null,pending=false,disposed=false;
  const locale=()=>i18n?.locale==='ja'?'ja':'zh-Hant',text=(tc,ja)=>choose(locale(),tc,ja),label=value=>i18n?.t?i18n.t(String(value??''),locale()):String(value??'');
  const query=selector=>dialog?.querySelector?.(selector),row=()=>city(getView(),active?.city);
  const identity=()=>{const v=getView();return JSON.stringify([v?.catalog?.scenario_id,v?.game?.player,v?.game?.seed,v?.game?.turn]);};
  const showing=()=>!!active&&dialog?.open!==false&&!!query('[data-facilities-dialog]');
  const matches=token=>!disposed&&active===token&&identity()===token.identity&&getView()?.game?.player===token.faction&&getView()?.game?.cities?.[token.city]?.owner===token.faction&&row()?.owner===token.faction;
  const canWrite=()=>!!active&&matches(active)&&!isBusy()&&!isPreview()&&!pending&&getView()?.game?.phase==='city'&&row()?.can_manage===true;
  const actors=()=>sortActors(row()?.eligible_actors,getView());
  const actorReady=()=>actors().some(id=>same(id,active.actor));
  const record=()=>getView()?.game?.cities?.[active?.city];
  const affordable=gold=>Number.isSafeInteger(gold)&&gold>=0&&(record()?.gold??-1)>=gold;
  const tradeMaximum=()=>{const quote=row()?.trade?.[active.direction];if(!quote||!Number.isSafeInteger(quote.rate)||quote.rate<1||!Number.isSafeInteger(quote.batch_grain)||quote.batch_grain<1)return 0;return Math.max(0,Math.min(quote.max_batches??0,active.direction==='buy'?Math.floor((record()?.gold??0)/quote.rate):Math.floor((record()?.grain??0)/quote.batch_grain),active.direction==='buy'?Math.floor((100000000-(record()?.grain??100000000))/quote.batch_grain):Math.floor((100000000-(record()?.gold??100000000))/quote.rate)));};
  const canAct=()=>canWrite()&&actorReady()&&row()?.can_act===true&&getView()?.game?.cities?.[active.city]?.action_used!==true;
  const officerLabel=id=>`${label(name(getView(),id))} · ${attributes(getView(),id,locale())}`;
  const select=(id,caption,value,choices)=>`<label class="field">${caption}<select id="${id}">${choices.map(([key,title])=>`<option value="${escape(key??'')}" ${same(value??'',key??'')?'selected':''}>${escape(title)}</option>`).join('')||`<option value="">${text('沒有可選項目','選択できる項目がありません')}</option>`}</select></label>`;
  const number=(id,caption,value,max,min=0)=>`<label class="field">${caption}<input id="${id}" type="number" min="${min}" max="${max}" step="1" value="${value===''?'':bounded(value,max,min)}"></label>`;
  const check=(id,caption,value)=>`<label class="domestic-toggle"><input id="${id}" type="checkbox" ${value?'checked':''}>${caption}</label>`;
  function reconcile(){
   const source=row(),available=actors(),availableServices=(source.services||[]).filter(id=>Object.hasOwn(services,id));
   if(!available.some(id=>same(id,active.actor)))active.actor=available[0]??null;
   if(!availableServices.includes(active.service))active.service=availableServices[0]??null;
   const pick=(field,rows,key='id')=>{if(!rows.some(p=>same(p[key],active[field])))active[field]=(rows.find(p=>p.can_treat===true||p.can_study===true)||rows[0])?.[key]??null;};
   pick('patient',[...(source.patients||[])].sort((a,b)=>a.before-b.before||stable(a.id,b.id)));pick('student',[...(source.students||[])].sort((a,b)=>b.before-a.before||stable(a.id,b.id)));
   const equipment=sortEquipment(source.equipment_targets,getView());if(!equipment.some(id=>same(id,active.equipmentOfficer)))active.equipmentOfficer=equipment[0]??null;
   const stock=source.stock?.[active.slot]||[];if(!stock.some(p=>same(p.id,active.item)))active.item=(stock.find(p=>(p.eligible_targets||[]).some(id=>same(id,active.equipmentOfficer)))||stock[0])?.id??null;
   const quote=source.trade?.[active.direction];if(active.batches!=='')active.batches=bounded(active.batches,tradeMaximum(),tradeMaximum()>0?1:0);
  }
  const targetQuote=(kind,id)=>(row()?.[kind]||[]).find(p=>same(p.id,id));
  const equipmentQuote=()=>(row()?.stock?.[active.slot]||[]).find(p=>same(p.id,active.item));
  const equipmentPreview=()=>equipmentQuote()?.preview_by_officer?.[String(active.equipmentOfficer)];
  const equipmentAllowed=()=>equipmentQuote()?.can_buy===true&&equipmentPreview()?.eligible!==false&&(equipmentQuote()?.eligible_targets||[]).some(id=>same(id,active.equipmentOfficer));
  const ownedOffers=()=>{const person=root.GameEquipment?.row?.(getView(),active.equipmentOfficer);return (person?.owned||[]).filter(item=>item.slot===active.slot&&item.item!==person?.[active.slot]?.id);};
  const ownedAllowed=()=>ownedOffers().some(item=>same(item.item,active.ownedItem))&&(row()?.equipment_targets||[]).some(id=>same(id,active.equipmentOfficer));
  const preventionQuote=()=>row()?.prevention_quotes?.[String(active.actor)];
  function boundary(){
   if(!matches(active)||isPreview())return text('目前無法操作這座城池。','現在、この都市では操作できません。');
   if(getView()?.game?.phase!=='city')return text('請在戰略階段操作。','戦略段階で操作してください。');
   if(getView()?.game?.cities?.[active.city]?.action_used)return text('本城本旬已行動；仍可查看設施與調整自動方針。','この都市は今旬、行動済みです。施設の確認と自動方針の変更はできます。');
   if(!actors().length)return text('本城沒有健康、已付薪且尚未行動的在場執行者。','この都市に健康・俸給支給済み・未行動の実行武将がいません。');
   return '';
  }
  function update(){
   if(!showing())return;
   const source=row(),ready=canAct(),set=(id,disabled)=>{const el=query('#'+id);if(el)el.disabled=disabled;};
   set('facility-develop',!ready||!source?.develop?.can_develop||!affordable(source?.develop?.gold));
   const patient=targetQuote('patients',active.patient),student=targetQuote('students',active.student),equipment=equipmentQuote(),prevent=preventionQuote(),trade=source?.trade?.[active.direction];
   set('facility-treat',!ready||!source?.services?.includes('hospital')||!patient?.can_treat||!affordable(patient?.gold));
   set('facility-study',!ready||!source?.services?.includes('school')||!student?.can_study||!affordable(student?.gold));
   set('facility-equipment-buy',!ready||!source?.services?.includes('armory')||!equipmentAllowed()||!affordable(equipment?.price));
   set('facility-equip-owned',!ready||!source?.services?.includes('armory')||!ownedAllowed());
   set('facility-prevent',!ready||!prevent?.can_prevent||!affordable(prevent?.gold_max));set('facility-save-policy',!canWrite());
   if(active.batches!=='')active.batches=bounded(active.batches,tradeMaximum(),tradeMaximum()>0?1:0);
   const amount=query('#facility-trade-batches');if(amount){amount.max=String(tradeMaximum());amount.min=String(tradeMaximum()>0?1:0);amount.value=String(active.batches);}
   set('facility-trade-max',pending||!trade||tradeMaximum()<1);
   set('facility-trade',!ready||!source?.services?.includes('market')||active.batches<1||active.batches>tradeMaximum());
   const tradePreview=query('#facility-trade-preview');if(tradePreview)tradePreview.textContent=trade?text(`${active.direction==='buy'?'購入':'出售'}兵糧 ${active.batches*trade.batch_grain}，${active.direction==='buy'?'花費':'收入'}金錢 ${active.batches*trade.rate}。`,`兵糧${active.batches*trade.batch_grain}を${active.direction==='buy'?'購入':'売却'}し、資金${active.batches*trade.rate}を${active.direction==='buy'?'支出':'取得'}します。`):text('目前沒有可交易的報價。','現在、取引できる見積りがありません。');
   const prevention=query('#facility-prevention-preview');if(prevention)prevention.textContent=prevent?text(`費用：金${range(prevent.gold_min,prevent.gold_max)}；防災 +${range(prevent.gain_min,prevent.gain_max)} → ${range(prevent.preparedness_min,prevent.preparedness_max)}；損傷 → ${range(prevent.damage_min,prevent.damage_max)}。`,`費用：資金${range(prevent.gold_min,prevent.gold_max)}。防災+${range(prevent.gain_min,prevent.gain_max)} → ${range(prevent.preparedness_min,prevent.preparedness_max)}、損傷 → ${range(prevent.damage_min,prevent.damage_max)}。`):text('請選擇可執行防災的武將。','防災を実行できる武将を選択してください。');
   const actorSummary=query('#facility-actor-summary');if(actorSummary)actorSummary.textContent=active.actor===null?'':officerLabel(active.actor);
   const status=query('#facility-boundary');if(status)status.textContent=boundary();
   i18n?.apply?.();
  }
  function serviceBody(){
   const source=row();
   if(active.service==='hospital'){
    const quote=targetQuote('patients',active.patient);
    return `<fieldset><legend>${text('醫館診療','医館での治療')}</legend>${select('facility-patient',text('受診武將（體力低者優先）','治療対象（体力の低い順）'),active.patient,[...(source.patients||[])].sort((a,b)=>a.before-b.before||stable(a.id,b.id)).map(p=>[p.id,officerLabel(p.id)]))}<p class="small" id="facility-treat-preview">${quote?text(`花費金${shown(quote.gold)}；體力 ${shown(quote.before)} → ${range(quote.after_min,quote.after_max)}（回復${range(quote.heal_min,quote.heal_max)}，不超過上限）。`,`資金${shown(quote.gold)}を使い、体力${shown(quote.before)} → ${range(quote.after_min,quote.after_max)}（回復${range(quote.heal_min,quote.heal_max)}、上限まで）。`):text('本城沒有可受診的武將。','この都市に治療できる武将はいません。')}</p><button id="facility-treat" class="primary" data-facility-confirm>${text('確認診療','治療を確定')}</button></fieldset>`;
   }
   if(active.service==='school'){
    const quote=targetQuote('students',active.student);
    return `<fieldset><legend>${text('學問所求學','学問所で学ぶ')}</legend>${select('facility-student',text('求學武將','学ぶ武将'),active.student,[...(source.students||[])].sort((a,b)=>b.before-a.before||stable(a.id,b.id)).map(p=>[p.id,officerLabel(p.id)]))}<p class="small" id="facility-study-preview">${quote?text(`花費金${shown(quote.gold)}；知 ${shown(quote.before)} → ${range(quote.after_min,quote.after_max)}（增加${range(quote.gain_min,quote.gain_max)}）。知80以上不能再求學。`,`資金${shown(quote.gold)}を使い、知${shown(quote.before)} → ${range(quote.after_min,quote.after_max)}（+${range(quote.gain_min,quote.gain_max)}）。知80以上は学べません。`):text('本城沒有可求學的武將。','この都市に学べる武将はいません。')}</p><button id="facility-study" class="primary" data-facility-confirm>${text('確認求學','学習を確定')}</button></fieldset>`;
   }
   if(active.service==='market'){
    const quote=source.trade?.[active.direction];
    return `<fieldset><legend>${text('市場兵糧買賣','市場で兵糧を売買')}</legend>${select('facility-trade-direction',text('交易方向','取引の種類'),active.direction,[['buy',text('買進兵糧','兵糧を購入')],['sell',text('出售兵糧','兵糧を売却')]])}<p class="small">${quote?text(`每批兵糧${shown(quote.batch_grain)}，金錢${shown(quote.rate)}。`,`1口は兵糧${shown(quote.batch_grain)}、資金${shown(quote.rate)}です。`):''}</p><div class="facility-amount">${number('facility-trade-batches',text('交易批數','取引口数'),active.batches,tradeMaximum(),tradeMaximum()>0?1:0)}<button type="button" id="facility-trade-max">${text('最大值','最大')}</button></div><p id="facility-trade-preview" role="status" aria-live="polite"></p><button id="facility-trade" class="primary" data-facility-confirm>${text('確認交易','取引を確定')}</button></fieldset>`;
   }
   if(active.service==='armory'){
    const quote=equipmentQuote(),stock=source.stock?.[active.slot]||[];
    const owned=ownedOffers();if(!owned.some(item=>same(item.item,active.ownedItem)))active.ownedItem=owned[0]?.item??null;
    const current=root.GameEquipment?.summary?.(getView(),active.equipmentOfficer,{locale:locale(),bilingual:false})||'';
    const comparison=root.GameEquipment?.comparison?.(getView(),active.equipmentOfficer,quote,{locale:locale(),bilingual:false})||'';
    const ownedBody=owned.length?`<fieldset><legend>${text('本人持有的備用裝備','本人が持つ予備の装備')}</legend>${select('facility-owned-equipment',text('選擇備用裝備','予備の装備を選択'),active.ownedItem,owned.map(item=>[item.item,`${locale()==='ja'?item.name_ja:item.name_tc} · ${text('強度','強さ')}${item.power} · ${text('重量','重さ')}${item.weight}`]))}<p class="small">${text('只能重新裝備本人的持有物，不收購置金錢；仍使用本城及武將的本旬行動。','本人の所持品だけを再装備できます。購入代金は不要ですが、都市と武将の今旬の行動を使います。')}</p><button id="facility-equip-owned" data-facility-confirm>${text('確認重新裝備','再装備を確定')}</button></fieldset>`:'';
    return `<fieldset><legend>${text('武器屋購置裝備','武器屋で装備を購入')}</legend>${select('facility-equipment-officer',text('裝備武將','装備する武将'),active.equipmentOfficer,sortEquipment(source.equipment_targets,getView()).map(id=>[id,officerLabel(id)]))}${current}${select('facility-equipment-slot',text('裝備部位','装備部位'),active.slot,[['weapon',text('兵器','武器')],['armor',text('防具','防具')]])}${select('facility-equipment-item',text('出售裝備','販売装備'),active.item,stock.map(p=>[p.id,`${locale()==='ja'?p.name_ja:p.name_tc} · ${text('金','資金')}${p.price} · ${text('強度','強さ')}${p.power} · ${text('重量','重さ')}${p.weight}`]))}<p class="small" id="facility-equipment-preview">${quote?text(`花費金${shown(quote.price)}；購買後替換本部位現有裝備，不退回舊裝備價款。`,`資金${shown(quote.price)}を使い、この部位の装備を交換します。以前の装備代は払い戻しません。`):text('本城目前沒有可購買的裝備。','現在、この都市で購入できる装備はありません。')}</p>${comparison}<p class="small" data-facility-appearance-note>${text('兵器演出對應目前實際裝備；坐騎外觀獨立設定。名將的初始專屬兵器也登記為實際裝備。','武器の演出は現在の実装備に対応し、騎馬の外見は別に設定します。名将の初期専用武器も実際の装備として記録します。')}</p><button id="facility-equipment-buy" class="primary" data-facility-confirm>${text('確認購買','購入を確定')}</button>${ownedBody}${root.GameEquipment?.acquisition?.(getView(),{locale:locale(),bilingual:false,open:active.equipmentGuideOpen})||''}</fieldset>`;
   }
   return `<p class="small">${text('目前沒有可訪問的設施。','現在、訪問できる施設がありません。')}</p>`;
  }
  function policyBody(){
   const p=active.policy,labels={gold_budget:['全勢力每旬預算','勢力全体・1旬の予算'],gold_floor:['各城保留金錢','各都市に残す資金'],grain_floor:['各城保留兵糧','各都市に残す兵糧'],grain_target:['各城兵糧目標','各都市の兵糧目標'],target_preparedness:['目標防災值','防災の目標'],heal_below:['低於此體力時受診','この体力未満で治療']},jobs={auto_prevent:['自動防災／修復','自動防災・復旧'],auto_treat:['自動診療','自動治療'],auto_trade:['自動兵糧買賣','自動で兵糧を売買'],auto_equip:['自動購置裝備','自動で装備を購入'],auto_develop:['自動發展城町','自動で町を発展'],auto_study:['自動求學','自動で学習']};
   return `<details class="facility-policy" ${active.policyOpen?'open':''}><summary>${text('全勢力自動設施與防災方針','勢力全体の施設・防災方針')}</summary><fieldset><legend>${text('自動方針','自動方針')}</legend>${check('facility-policy-enabled',text('啟用全勢力自動執行','勢力全体の自動実行を有効にする'),p.enabled)}<div class="domestic-input-grid">${Object.entries(labels).map(([key,captions])=>number('facility-policy-'+key,text(...captions),p[key],limits[key][1],limits[key][0])).join('')}</div>${Object.entries(jobs).map(([key,captions])=>check('facility-policy-'+key,text(...captions),p[key])).join('')}<p class="small">${text('金錢預算為全勢力每旬合計。依防災／修復、診療、兵糧交易、裝備、發展、求學的順序，使用尚未行動的城池與武將。玩家和AI共用實際費用與行動限制。','資金予算は勢力全体の1旬の合計です。防災・復旧、治療、兵糧取引、装備、都市発展、学習の順に、未行動の都市と武将が実行します。プレイヤーとAIは同じ費用と行動制限を使います。')}</p><button id="facility-save-policy" data-facility-confirm>${text('儲存自動方針','自動方針を保存')}</button></fieldset></details>`;
  }
  function feedback(){return active.error?`<p class="staff-command-error" role="alert">${text('操作未完成，請核對最新資源、設施與武將後重試。','操作を完了できませんでした。最新の資源・施設・武将を確認して再度お試しください。')}</p>`:active.saved?`<p class="domestic-saved" role="status">${text('操作已完成，預覽已更新。返回戰役可查看圖文事件。','操作が完了し、予測を更新しました。戦役に戻ると画像付きイベントを確認できます。')}</p>`:'';}
  function render(){
   if(!active||!matches(active)||!row()||typeof openDialog!=='function')return false;
   const existingPolicy=query('.facility-policy');if(existingPolicy)active.policyOpen=existingPolicy.open===true;
   const existingGuide=query('[data-equipment-guide]');if(existingGuide)active.equipmentGuideOpen=existingGuide.open===true;
   reconcile();const source=row(),availableServices=(source.services||[]).filter(id=>Object.hasOwn(services,id)),develop=source.develop;
   const body=`<div class="facilities-panel" data-facilities-dialog data-facilities-city="${escape(active.city)}" data-l10n-native="${locale()}">${summary(getView(),active.city,{locale:locale(),bilingual:false})}<p id="facility-boundary" class="small" role="status"></p>${feedback()}${select('facility-actor',text('執行武將（知較高者優先）','実行武将（知の高い順）'),active.actor,actors().map(id=>[id,officerLabel(id)]))}<p class="small" id="facility-actor-summary"></p><fieldset><legend>${text('城町發展','町の発展')}</legend><p class="small">${develop&&develop.from_town===develop.to_town?text('已達最高城町等級3。醫館、市場、學問所與武器屋均已開放。','町の発展段階は上限の3です。医館・市場・学問所・武器屋を利用できます。'):develop?text(`發展 ${shown(develop.from_town)} → ${shown(develop.to_town)}，花費金${shown(develop.gold)}。醫館與市場為基礎服務；發展後開放學問所與武器屋，最高級提供進階商品。`,`発展${shown(develop.from_town)} → ${shown(develop.to_town)}、費用は資金${shown(develop.gold)}。医館・市場は基本施設で、発展すると学問所・武器屋を利用でき、最高段階では上級商品が並びます。`):''}</p><button id="facility-develop" data-facility-confirm>${text('確認城町發展','都市発展を確定')}</button></fieldset>${select('facility-service',text('訪問設施','訪問する施設'),active.service,availableServices.map(id=>[id,text(...services[id])]))}${serviceBody()}<fieldset><legend>${text('防災與災後修復','防災と被災後の復旧')}</legend><p class="small" id="facility-prevention-preview"></p><button id="facility-prevent" class="primary" data-facility-confirm>${text('確認防災整備','防災整備を確定')}</button><p class="small">${text('防災值最多99、損傷最低0。費用與效果會在確認後，依顯示的參考範圍決定。','防災は99まで、損傷は0までです。費用と効果は、表示した参考範囲から確定時に決まります。')}</p></fieldset><p class="small">${text('發展、設施訪問和防災各使用本城與執行武將的本旬行動；診療、求學與購裝備也會登記受益武將行動。醫館仍可為體力0或已行動者治療。查看、取消與切換語言不扣資源、不改人物資料。','発展・施設訪問・防災は都市と実行武将の今旬の行動を使い、治療・学習・装備購入では対象武将の行動も記録します。医館では体力0・行動済みの武将も治療できます。閲覧・取消・言語切替では資源や人物情報は変わりません。')}</p>${policyBody()}</div>`;
   if(openDialog(text(`設施與防災 · ${label(cityName(active.city))}`,`施設と防災・${label(cityName(active.city))}`),body,`<button data-cancel>${text('返回戰役','戦役へ戻る')}</button>`)===undefined)return false;
   const rerender=()=>{const scroll=dialog.scrollTop;render();dialog.scrollTop=scroll;};
   query('#facility-actor').onchange=()=>{if(!pending){active.actor=ref(query('#facility-actor').value);update();}};
   query('#facility-service').onchange=()=>{if(!pending){active.service=query('#facility-service').value;rerender();}};
   query('#facility-develop').onclick=()=>submit('develop_town',()=>({city:active.city,actor:ref(active.actor)}),()=>row()?.develop?.can_develop===true&&affordable(row()?.develop?.gold));
   if(query('#facility-patient'))query('#facility-patient').onchange=()=>{if(!pending){active.patient=ref(query('#facility-patient').value);rerender();}};
   if(query('#facility-treat'))query('#facility-treat').onclick=()=>submit('treat_officer',()=>({city:active.city,actor:ref(active.actor),officer:ref(active.patient)}),()=>row()?.services?.includes('hospital')&&targetQuote('patients',active.patient)?.can_treat===true&&affordable(targetQuote('patients',active.patient)?.gold));
   if(query('#facility-student'))query('#facility-student').onchange=()=>{if(!pending){active.student=ref(query('#facility-student').value);rerender();}};
   if(query('#facility-study'))query('#facility-study').onclick=()=>submit('study_officer',()=>({city:active.city,actor:ref(active.actor),officer:ref(active.student)}),()=>row()?.services?.includes('school')&&targetQuote('students',active.student)?.can_study===true&&affordable(targetQuote('students',active.student)?.gold));
   if(query('#facility-trade-direction'))query('#facility-trade-direction').onchange=()=>{if(!pending){active.direction=query('#facility-trade-direction').value==='sell'?'sell':'buy';rerender();}};
   if(query('#facility-trade-batches')){const input=query('#facility-trade-batches');input.oninput=()=>{if(!pending){active.batches=input.value;update();}};input.onchange=input.onblur=()=>{if(!pending){active.batches=input.value===''?(tradeMaximum()>0?1:0):input.value;update();}};}
   if(query('#facility-trade-max'))query('#facility-trade-max').onclick=()=>{if(!pending){active.batches=tradeMaximum();update();}};
   if(query('#facility-trade'))query('#facility-trade').onclick=()=>submit('trade_grain',()=>({city:active.city,actor:ref(active.actor),direction:active.direction,batches:active.batches}),()=>row()?.services?.includes('market')&&active.batches>=1&&active.batches<=tradeMaximum());
   for(const[id,field,parse]of [['facility-equipment-officer','equipmentOfficer',ref],['facility-equipment-slot','slot',value=>value==='armor'?'armor':'weapon'],['facility-equipment-item','item',value=>Number(value)]])if(query('#'+id))query('#'+id).onchange=()=>{if(!pending){active[field]=parse(query('#'+id).value);rerender();}};
   if(query('#facility-equipment-buy'))query('#facility-equipment-buy').onclick=()=>submit('buy_equipment',()=>({city:active.city,actor:ref(active.actor),officer:ref(active.equipmentOfficer),slot:active.slot,item:active.item}),()=>row()?.services?.includes('armory')&&equipmentAllowed()&&affordable(equipmentQuote()?.price));
   if(query('#facility-owned-equipment'))query('#facility-owned-equipment').onchange=()=>{if(!pending){active.ownedItem=Number(query('#facility-owned-equipment').value);update();}};
   if(query('#facility-equip-owned'))query('#facility-equip-owned').onclick=()=>submit('equip_owned',()=>({city:active.city,actor:ref(active.actor),officer:ref(active.equipmentOfficer),slot:active.slot,item:active.ownedItem}),()=>row()?.services?.includes('armory')&&ownedAllowed());
   query('#facility-prevent').onclick=()=>submit('improve_prevention',()=>({city:active.city,actor:ref(active.actor)}),()=>preventionQuote()?.can_prevent===true&&affordable(preventionQuote()?.gold_max));
   for(const key of Object.keys(defaults)){const input=query('#facility-policy-'+key);if(!input)continue;if(typeof defaults[key]==='boolean')input.onchange=()=>{if(!pending)active.policy[key]=input.checked;};else input.oninput=input.onchange=input.onblur=()=>{if(!pending){active.policy[key]=bounded(input.value,limits[key][1],limits[key][0]);active.policy=normalizePolicy(active.policy);for(const field of Object.keys(limits))if(query('#facility-policy-'+field))query('#facility-policy-'+field).value=String(active.policy[field]);}};}
   query('#facility-save-policy').onclick=()=>submit('set_facility_policy',()=>({faction:active.faction,policy:normalizePolicy(active.policy)}),()=>true,{management:true});
   update();return true;
  }
  async function submit(kind,payload,guard,{management=false}={}){
   if(!canWrite())return false;update();if(!(management?canWrite():canAct())||!guard())return false;
   const token=active,request=payload();pending=true;
   for(const button of dialog?.querySelectorAll?.('[data-facility-confirm]')||[])button.disabled=true;
   let success=false;try{success=await command(kind,request)!==false;}catch{success=false;}finally{pending=false;}
   if(!matches(token)||!showing())return success;
   token.error=!success;token.saved=success;
   if(success&&kind==='set_facility_policy')token.policy=normalizePolicy(data(getView())?.factions?.[token.faction]?.policy);
   const scroll=dialog.scrollTop;render();dialog.scrollTop=scroll;return success;
  }
  function refresh(){if(!disposed&&!pending&&showing()&&matches(active)){const scroll=dialog.scrollTop;render();dialog.scrollTop=scroll;}}
  function open(id){
   const view=getView(),record=view?.game?.cities?.[id],source=city(view,id);
   if(disposed||pending||isBusy()||isPreview()||view?.game?.phase!=='city'||!record||record.owner!==view.game.player||!source?.can_manage)return false;
   active={city:id,faction:view.game.player,identity:identity(),actor:null,service:null,patient:null,student:null,equipmentOfficer:null,slot:'weapon',item:null,direction:'buy',batches:1,policy:normalizePolicy(data(view)?.factions?.[view.game.player]?.policy)};
   const opened=render();if(opened)dialog.scrollTop=0;return opened;
  }
  doc?.addEventListener?.('game-language-change',refresh);
  return {open,refresh,dispose(){disposed=true;active=null;doc?.removeEventListener?.('game-language-change',refresh);}};
 }
 const api=Object.freeze({create,data,city,summary,attributes,sortActors,sortEquipment,normalizePolicy,bounded,ref,range});
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.GameFacilities=api;
})(typeof window!=='undefined'?window:globalThis);
