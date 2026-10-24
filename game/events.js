/* Read-only event playback. Acknowledgements never become campaign commands. */
'use strict';
(function(root){
 const KINDS=Object.freeze({
  campaign_start:['戰役揭幕','戦役の開幕'],officer_appeared:['武將登場','武将の登場'],
  recruit_success:['登用成功','登用に成功'],recruit_failure:['登用未果','登用を断られました'],
  defection:['武將轉屬','武将の移籍'],officer_death:['武將逝世','武将の死去'],
  succession:['主將繼任','君主の継承'],faction_ended:['勢力滅亡','勢力の滅亡'],
  city_founded:['新城建置','新都市の開設'],city_captured:['城池易主','都市の陥落'],
  city_upgraded:['都市擴建','都市の発展'],city_renamed:['城名顯示變更','都市名表示の変更'],
  battle_started:['戰鬥開始','戦闘開始'],battle_result:['戰果揭曉','戦闘の結果'],
  duel_started:['單挑交鋒','一騎討ち開始'],duel_result:['單挑結果','一騎討ちの結果'],
  tactic:['計略發動','計略の発動'],march_weather:['行軍遇險','行軍中の災害'],
  route_discovered:['發現新航路','新航路の発見'],march_arrived:['部隊抵達','部隊の到着'],
  march_resupplied:['行軍補給到達','行軍部隊への補給'],march_starvation:['行軍兵糧短缺','行軍中の兵糧不足'],march_retreat:['部隊自動撤退','部隊の自動撤退'],
  march_returned:['部隊折返','部隊の帰還'],new_year:['新年更始','新年の到来'],
  campaign_victory:['天下歸一','天下統一'],campaign_defeat:['戰役結束','戦役の終了'],
  ai_campaign:['敵軍動向','敵軍の動向'],
  treasure_found:['尋得寶物','宝の発見'],treasure_search_failed:['尋寶未果','宝の探索結果'],treasure_sold:['寶物出售','宝の売却'],officer_rewarded:['賞賜武將','武将への褒美'],governor_assigned:['太守任命','太守の任命'],
  staff_candidate:['地方文吏推薦','在地文官の推薦'],staff_hired:['文吏受聘','文官の雇用'],
  staff_declined:['婉拒文吏','文官の採用見送り'],staff_expired:['文吏候選撤回','文官候補の取り下げ'],
  staff_salary:['文吏月俸與成果','文官の俸給と業務成果'],staff_allegiance:['文吏留任','文官の留任'],
  domestic_report:['內政執行摘要','内政の実行報告'],transport_departed:['運輸隊出發','輸送隊の出発'],transport_arrived:['運輸隊抵達','輸送隊の到着'],transport_returned:['運輸隊折返','輸送隊の帰還'],transport_weather:['運輸途中遇險','輸送中の災害']
 });
 const STAFF=new Set(['staff_candidate','staff_hired','staff_declined','staff_expired','staff_salary','staff_allegiance']);
 const OPERATIONS=new Set(['domestic_report','transport_departed','transport_arrived','transport_returned','transport_weather']);
 const TREASURY=new Set(['treasure_found','treasure_search_failed','treasure_sold','officer_rewarded','governor_assigned']);
 const SUPPLY=new Set(['march_resupplied','march_starvation','march_retreat']);
 const SUPPLY_REASONS=new Set(['city','convoy','cargo','shortage','route_blocked','no_friendly_city','origin_changed','target_changed','completed']);
 const BATCH=new Set(['officer_appeared','officer_death','recruit_success','recruit_failure','march_arrived','march_returned']);
 const WORLD=new Set(['campaign_start','officer_appeared','officer_death','succession','faction_ended','city_founded','city_upgraded','city_renamed','city_captured','new_year','campaign_victory','campaign_defeat']);
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const clone=value=>JSON.parse(JSON.stringify(value));
 function validEvent(row){
  return !!row&&Number.isSafeInteger(row.id)&&row.id>0&&Object.hasOwn(KINDS,row.kind)&&['player','world'].includes(row.audience)&&
   Number.isSafeInteger(row.year)&&row.year>0&&Number.isInteger(row.month)&&row.month>=1&&row.month<=12&&[1,11,21].includes(row.day)&&Number.isSafeInteger(row.turn)&&row.turn>0&&
   ['person_ids','city_ids','factions'].every(key=>Array.isArray(row[key])&&row[key].every(id=>typeof id==='string'&&id.length<=128))&&
   !!row.details&&typeof row.details==='object'&&!Array.isArray(row.details)&&(!STAFF.has(row.kind)||validStaffEvent(row))&&(!TREASURY.has(row.kind)||validTreasuryEvent(row))&&(!OPERATIONS.has(row.kind)||validOperationEvent(row))&&(!SUPPLY.has(row.kind)||validSupplyEvent(row))&&(row.kind!=='city_upgraded'||validSizeEvent(row))&&(row.kind!=='city_renamed'||validNameEvent(row));
 }
 function validTreasuryEvent(row){
  const d=row.details,k=row.kind,keys={treasure_found:['actor','amount','chance','gold'],treasure_search_failed:['actor','amount','chance','gold'],treasure_sold:['actor','amount','gold'],officer_rewarded:['actor','target','kind','amount','gain','loyalty_before','loyalty_after'],governor_assigned:['governor','mode']}[k];
  if(row.audience!=='player'||row.factions.length!==1||row.city_ids.length!==1||Object.keys(d).sort().join(',')!==keys.sort().join(','))return false;
  const num=(key,min,max)=>Number.isSafeInteger(d[key])&&d[key]>=min&&d[key]<=max;
  if(k==='governor_assigned')return ['auto','manual'].includes(d.mode)&&(d.mode!=='manual'||d.governor!==null)&&JSON.stringify(row.person_ids)===JSON.stringify(d.governor===null?[]:[d.governor]);
  if(k==='officer_rewarded')return JSON.stringify(row.person_ids)===JSON.stringify([...new Set([d.actor,d.target])])&&['gold','treasure'].includes(d.kind)&&num('amount',1,d.kind==='gold'?100:1)&&num('gain',1,9)&&num('loyalty_before',0,99)&&num('loyalty_after',1,100)&&d.loyalty_after-d.loyalty_before===d.gain;
  if(JSON.stringify(row.person_ids)!==JSON.stringify([d.actor]))return false;
  return k==='treasure_sold'?num('amount',1,99)&&d.gold===d.amount*100:num('chance',15,80)&&d.amount===(k==='treasure_found'?1:0)&&d.gold===20;
 }
 function validNameEvent(row){
  const d=row.details;
  return row.audience==='world'&&row.day===1&&!row.person_ids.length&&row.city_ids.length===1&&row.factions.length===1&&
   Object.keys(d).sort().join(',')==='from_name,to_name'&&
   ['from_name','to_name'].every(key=>typeof d[key]==='string'&&d[key].trim().length>0&&d[key].length<=40&&!/[\u0000-\u001f\u007f]/u.test(d[key]))&&d.from_name!==d.to_name;
 }
 function validSupplyEvent(row){
  const d=row.details;
  if(Object.keys(d).sort().join(',')!=='grain,lost,reason,shortage_days,unit_id,unit_kind'||
   !['march','convoy'].includes(d.unit_kind)||!SUPPLY_REASONS.has(d.reason)||row.audience!=='player'||
   row.factions.length!==1||row.city_ids.length<1||row.city_ids.length>2||
   new Set(row.city_ids).size!==row.city_ids.length||row.person_ids.length>99||
   new Set(row.person_ids).size!==row.person_ids.length)return false;
  for(const [key,min,max]of [['unit_id',1,1000000],['grain',0,100000000],['lost',0,100000000],['shortage_days',0,10000000]])
   if(!Number.isSafeInteger(d[key])||d[key]<min||d[key]>max)return false;
  return row.kind==='march_resupplied'?d.grain>0&&d.lost===0:row.kind==='march_starvation'?d.grain===0&&d.shortage_days>0:d.grain===0&&d.lost===0;
 }
 function validSizeEvent(row){
  const d=row.details,tiers=['normal','large','giant'];
  return row.audience==='world'&&row.day===1&&!row.person_ids.length&&row.city_ids.length===1&&row.factions.length===1&&
   Object.keys(d).sort().join(',')==='from_tier,income,to_tier'&&tiers.includes(d.from_tier)&&tiers.includes(d.to_tier)&&d.from_tier!==d.to_tier&&
   !!d.income&&typeof d.income==='object'&&!Array.isArray(d.income)&&Object.keys(d.income).sort().join(',')==='gold,grain,reserves'&&
   Object.values(d.income).every(value=>Number.isSafeInteger(value)&&value>=0&&value<=100000000);
 }
 function validOperationEvent(row){
  const d=row.details,domestic=row.kind==='domestic_report',fields=domestic?['gold','grain','reserves','morale','cities','reason']:['convoy_id','gold','grain','reserves','treasure','lost','reason'];
  if(Object.keys(d).some(key=>!fields.includes(key))||fields.some(key=>!Object.hasOwn(d,key))||typeof d.reason!=='string'||!/^[a-z_]{1,80}$/.test(d.reason))return false;
  for(const key of fields)if(key!=='reason'&&(!Number.isInteger(d[key])||d[key]<0||d[key]>100000000))return false;
  return domestic?['turn','month'].includes(d.reason)&&d.morale<=11500&&d.cities>=1&&d.cities<=115:d.convoy_id>=1&&d.treasure<=99;
 }
 function validStaffEvent(row){
  const d=row.details,allowed=['staff_id','name','portrait','reason','amount','paid','bonus','counts'];
  if(row.person_ids.length||row.city_ids.length!==1||row.factions.length<1||row.factions.length>2||Object.keys(d).some(k=>!allowed.includes(k)))return false;
  const required=row.kind==='staff_salary'?['amount','paid','bonus','counts']:['staff_id','name','portrait','reason'];
  if(required.some(k=>!Object.hasOwn(d,k)))return false;
  if(Object.hasOwn(d,'staff_id')&&(typeof d.staff_id!=='string'||!/^clerk-[0-9]{6,12}$/.test(d.staff_id)||Number(d.staff_id.slice(6))<1))return false;
  if(Object.hasOwn(d,'name')&&(typeof d.name!=='string'||!d.name.trim()||d.name.length>40||/[\u0000-\u001f\u007f]/u.test(d.name)))return false;
  if(Object.hasOwn(d,'portrait')&&!['clerk-1','clerk-2','clerk-3'].includes(d.portrait))return false;
  if(Object.hasOwn(d,'reason')&&(typeof d.reason!=='string'||!/^[a-z_]{1,80}$/.test(d.reason)))return false;
  for(const k of ['amount','paid'])if(Object.hasOwn(d,k)&&(!Number.isInteger(d[k])||d[k]<0||d[k]>100000000))return false;
  if(Object.hasOwn(d,'bonus')&&(!d.bonus||typeof d.bonus!=='object'||Array.isArray(d.bonus)||Object.keys(d.bonus).sort().join(',')!=='gold,grain,reserves'||Object.values(d.bonus).some(n=>!Number.isInteger(n)||n<0||n>100000000)))return false;
  if(Object.hasOwn(d,'counts')&&(!d.counts||typeof d.counts!=='object'||Array.isArray(d.counts)||Object.keys(d.counts).sort().join(',')!=='cities,staff,total_unpaid'||!Number.isInteger(d.counts.staff)||d.counts.staff<1||d.counts.staff>11385||!Number.isInteger(d.counts.cities)||d.counts.cities<1||d.counts.cities>115||d.counts.staff<d.counts.cities||d.counts.staff>d.counts.cities*99||!Number.isInteger(d.counts.total_unpaid)||d.counts.total_unpaid<0||d.counts.total_unpaid>d.counts.staff))return false;
  return row.kind!=='staff_salary'||d.paid<=d.amount&&d.amount===d.counts.staff*5&&d.paid%5===0&&d.counts.total_unpaid===d.counts.staff-d.paid/5;
 }
 function campaignKey(view){return view?.game?JSON.stringify([view.catalog?.scenario_id||view.catalog?.title||'',view.game.seed,view.game.player]):null;}
 function eventRows(view){const rows=view?.game?.extension?.events?.items;return Array.isArray(rows)?rows.filter(validEvent).sort((a,b)=>a.id-b.id):[];}
 function automatic(row,player){return STAFF.has(row.kind)||OPERATIONS.has(row.kind)||SUPPLY.has(row.kind)||TREASURY.has(row.kind)?row.factions.includes(player):row.audience==='player'||WORLD.has(row.kind)||row.factions.includes(player);}
 function groupRows(rows){
  const groups=[],staffGroups=new Map();
  for(const row of rows){
   if(STAFF.has(row.kind)||OPERATIONS.has(row.kind)||SUPPLY.has(row.kind)||TREASURY.has(row.kind)){const key=row.turn+':'+row.kind;if(staffGroups.has(key))staffGroups.get(key).push(row);else{const group=[row];groups.push(group);staffGroups.set(key,group);}continue;}
   const last=groups.at(-1);if(last&&BATCH.has(row.kind)&&last[0].kind===row.kind&&last[0].turn===row.turn)last.push(row);else groups.push([row]);
  }
  return groups;
 }
 function create(options={}){
  const doc=options.document||root.document,modal=options.modal||doc?.querySelector('#event-dialog'),parent=options.parentDialog||doc?.querySelector('#dialog');
  const i18n=options.i18n||root.GameI18n,portraits=options.portraits||root.GamePortraits;
  const schedule=options.schedule||(fn=>root.setTimeout(fn,0)),getView=options.getView||(()=>null),isBusy=options.isBusy||(()=>false),isPreview=options.isPreview||(()=>false);
  let key=null,cursor=0,queue=[],active=null,historyMode=false,view=null,scheduled=false,portraitAttempted=false,shown=0,total=0,disposed=false;
  const locale=()=>i18n?.locale==='ja'?'ja':'zh-Hant',text=(tc,ja)=>locale()==='ja'?ja:tc;
  const label=value=>i18n?.t?i18n.t(String(value??''),locale()):String(value??'');
  function refreshHistoryLabel(){const button=doc?.querySelector?.('#event-history');if(button){button.textContent=text('事件回顧','出来事の記録');button.setAttribute('data-l10n-native',locale());}}
  function names(row){
   const catalog=view?.catalog||{},people=new Map((catalog.library||[]).map(p=>[p.person_id,p.name]));
   const personName=id=>{const current=Object.entries(view?.game?.officers||{}).find(([,person])=>person.person_id===id);return people.get(id)||(current&&catalog.names?.[current[0]])||text('未具名武將','名前未設定の武将');};
   return {people:row.person_ids.map(id=>label(personName(id))),cities:row.city_ids.map(id=>label(catalog.cities?.find(c=>c.id===id)?.name||text('未知城池','不明な都市'))),
    factions:row.factions.map(id=>label(catalog.factions?.find(f=>f.id===id)?.name||(id==='neutral'?text('無主','空白都市'):text('未具名勢力','名前未設定の勢力'))))};
  }
  function description(row){
   const n=names(row),p=n.people.join(text('、','・'))||text('武將','武将'),c=n.cities.join(' → ')||text('戰役地圖','戦役地図'),f=n.factions.at(-1)||text('本方','自軍'),d=row.details;
   switch(row.kind){
    case 'treasure_found':return text(`${p}在${c}尋得寶1件，已入本城寶庫。本次花費20金，搜尋成功率${d.chance}%。`,`${p}が${c}で宝を1個発見し、都市の宝庫に収めました。探索費用は資金20、成功率は${d.chance}%でした。`);
    case 'treasure_search_failed':return text(`${p}在${c}尋寶未果。本次花費20金，成功率${d.chance}%；已使用本城與執行武將的本旬行動。`,`${p}は${c}で宝を発見できませんでした。費用は資金20、成功率は${d.chance}%。都市と実行武将の今旬の行動を使用しました。`);
    case 'treasure_sold':return text(`${c}出售寶${d.amount}件，取得金${d.gold}，款項已入本城。`,`${c}で宝${d.amount}個を売却し、資金${d.gold}を都市に収めました。`);
    case 'officer_rewarded':{
     const recipient=names({...row,person_ids:[d.target]}).people[0],gift=d.kind==='gold'?text(`金${d.amount}`,`資金${d.amount}`):text(`寶${d.amount}件`,`宝${d.amount}個`);
     return text(`${c}賞賜${recipient}${gift}，忠誠${d.loyalty_before} → ${d.loyalty_after}（+${d.gain}）。費用已扣除，依太守德值與本作規則結算。`,`${c}で${recipient}に${gift}を与え、忠誠が${d.loyalty_before} → ${d.loyalty_after}（+${d.gain}）になりました。費用は差し引き済みで、太守の徳と本作のルールに従って精算しました。`);
    }
    case 'governor_assigned':return text(`${c}太守：${d.governor?p:'尚無適任者'}（${d.mode==='auto'?'自動選任':'指定'}）。任命不消耗城池行動；兩名全勢力內政官的委任另行管理。`,`${c}の太守は${d.governor?p:'該当者なし'}（${d.mode==='auto'?'自動選任':'指定'}）です。任命では都市行動を使いません。勢力全体の内政担当2名は別に管理します。`);
    case 'campaign_start':return text(`${f}展開新的戰役。每旬10日，請安排人事、兵力與行軍。`,`${f}による新たな戦役が始まります。1旬10日、人事・兵力・行軍を整えましょう。`);
    case 'officer_appeared':return text(`${p}已到登場年代，在${c}待訪。`,`${p}が登場年を迎え、${c}で仕官先を待っています。`);
    case 'recruit_success':return text(`${p}接受登用，加入${f}。`,`${p}が登用に応じ、${f}へ加わりました。`);
    case 'recruit_failure':return text(`${p}此次未接受登用。尋訪費用已按規則結算。`,`${p}は今回の登用を断りました。訪問費用は規則どおり精算されています。`);
    case 'defection':return text(`${p}的所屬已變更，現歸${f}。`,`${p}の所属が変わり、現在は${f}に仕えています。`);
    case 'officer_death':return text(`${p}離世。兵員與主將繼任依當前戰局結算。`,`${p}が死去しました。兵力と君主の継承は現在の戦況に従い処理されます。`);
    case 'succession':return text(`${p}接任${f}主將，勢力繼續行動。`,`${p}が${f}の君主を継承し、勢力の活動を続けます。`);
    case 'faction_ended':return text(`${f}失去繼續作戰的條件，退出戰役。`,`${f}は戦いを続けられなくなり、戦役から退場しました。`);
    case 'city_founded':{const founded=n.cities[0]||c,parent=n.cities[1];return text(`${founded}依年代建置，承接${parent||'原城'}目前歸屬及部分資源。`,`${founded}が設定年代に開設され、${parent||'元の都市'}の現在の所属と一部の資源を引き継ぎました。`);}
    case 'city_renamed':return text(`${row.year}年${row.month}月起，本作節點的顯示城名由${label(d.from_name)}切換為${label(d.to_name)}。目前歸屬、武將、兵數與庫存保持實際戰局狀態。`,`${row.year}年${row.month}月から、本作の拠点表示名が${label(d.from_name)}から${label(d.to_name)}へ切り替わりました。現在の支配・武将・兵力・在庫は実際の戦況を引き継ぎます。`);
    case 'city_upgraded':{
     const tiers={normal:text('通常都市','通常都市'),large:text('大都市','大都市'),giant:text('巨大都市','巨大都市')},income=d.income||{};
     return text(`${c}於${row.year}年${row.month}月由${tiers[d.from_tier]||'大都市'}升為${tiers[d.to_tier]||'巨大都市'}。今後每月收入：金${income.gold??0}、糧${income.grain??0}、預備兵${income.reserves??0}。這是本作的都市規模設定。`,`${row.year}年${row.month}月、${c}が${tiers[d.from_tier]||'大都市'}から${tiers[d.to_tier]||'巨大都市'}へ発展しました。以後の月収は資金${income.gold??0}・兵糧${income.grain??0}・予備兵${income.reserves??0}です。本作独自の都市規模設定です。`);
    }
    case 'city_captured':{const owner=n.factions[0]||f;return text(`${c}的歸屬改為${owner}。駐軍及資源已結算。`,`${c}は${owner}の支配下となりました。守備隊と資源は精算済みです。`);}
    case 'battle_started':return text(`${c}發生交戰。請依兵力、地形與敵軍狀態選擇行動。`,`${c}で戦闘が始まります。兵力・地形・敵の状態を見て行動を選びましょう。`);
    case 'battle_result':{
     const outcome={victory:text('攻方獲勝','攻撃側の勝利'),defeat:text('守方獲勝','防御側の勝利'),retreat:text('攻方退卻','攻撃側の撤退')}[d.outcome]||text('戰鬥結束','戦闘終了');
     return text(`${c}：${outcome}。${typeof d.lost==='number'?`合計減員${d.lost}。`:''}請查看戰果與後續部署。`,`${c}：${outcome}。${typeof d.lost==='number'?`兵力損失は合計${d.lost}。`:''}結果と次の配置を確認してください。`);
    }
    case 'duel_started':return text(`${p}展開單挑，勝負依招式與武力判定。`,`${p}が一騎討ちに臨みます。技の選択と武力が勝負を左右します。`);
    case 'duel_result':return text(`${p}的單挑已結束。${d.result?label(d.result):'體力與退場結果已結算。'}`,`${p}の一騎討ちが終わりました。${d.result?label(d.result):'体力と退場結果は処理されています。'}`);
    case 'tactic':{
     const title=label(view?.catalog?.tactics?.[d.tactic]?.name||text('計略','計略'));
     return text(`${n.people[0]||p}施放${title}。${d.success===false?'未能奏效。':'效果與氣力消耗已結算。'}`,`${n.people[0]||p}が${title}を使用。${d.success===false?'効果はありませんでした。':'効果と気力の消費は精算されています。'}`);
    }
    case 'march_weather':return text(`${c}行軍途中遭遇險阻或暴風雨。${typeof d.lost==='number'?`減員${d.lost}兵。`:'實際兵損已計入部隊。'}`,`${c}への行軍中に難所や暴風雨に遭遇しました。${typeof d.lost==='number'?`${d.lost}の兵を失いました。`:'実際の損失を部隊に反映しています。'}`);
    case 'march_resupplied':{
     const unit=d.unit_kind==='convoy'?text('運輸隊','輸送隊'):text('行軍部隊','行軍部隊'),
      from=d.reason==='city'?text(`由${c}取得補給`,`${c}から補給を受け`):d.reason==='cargo'?text('從本隊貨糧轉裝口糧','輸送貨物の兵糧を携行分へ積み替え'):text('收到補給隊交付的兵糧','補給隊から兵糧を受け取り');
     return text(`${unit}${from}，增加隨軍糧${d.grain}。來源兵糧已實際扣除，後續行軍與等候依目前補給狀態處理。`,`${unit}が${from}、携行兵糧を${d.grain}補充しました。供給元の兵糧は差し引き済みで、以後の行軍・待機は現在の補給状況に従います。`);
    }
    case 'march_starvation':{
     const unit=d.unit_kind==='convoy'?text('運輸隊','輸送隊'):text('行軍部隊','行軍部隊');
     return text(`${c}附近的${unit}兵糧不足，目前缺糧${d.shortage_days}日，本次減員${d.lost}兵。缺糧損失已計入兵員帳本，武將不因這項減員被判定陣亡；請安排途中補給。`,`${c}付近の${unit}で兵糧が不足しています。欠乏日数は${d.shortage_days}日、今回の兵力損失は${d.lost}です。損失は兵力台帳に反映済みで、この減員による武将の戦死はありません。途中補給を手配してください。`);
    }
    case 'march_retreat':{
     const unit=d.unit_kind==='convoy'?text('運輸隊','輸送隊'):text('部隊','部隊');
     if(d.reason==='no_friendly_city')return text(`${unit}已無可達的本方城池，暫時原地等候。缺糧仍會按實際等候日數結算，請安排救援。`,`${unit}が到達できる自勢力の都市を失い、現地で待機しています。待機中も実際の日数に応じて兵糧不足を処理するため、救援を手配してください。`);
     if(d.reason==='completed')return text(`${unit}已完成撤退並抵達${c}，人員與剩餘物資按實際狀態入城。`,`${unit}は撤退を終えて${c}へ到着し、武将と残る物資を実際の状況に従って収容しました。`);
     const reason={shortage:text('持續缺糧','兵糧不足の継続'),route_blocked:text('行軍道路中斷','行軍経路の遮断'),origin_changed:text('出發城易主','出発都市の所属変更'),target_changed:text('目的城易主','目的都市の所属変更')}[d.reason]||text('目前補給狀況','現在の補給状況');
     return text(`${unit}因${reason}停止原任務，改向${c}撤退。撤退按實際道路與日數行走，不會立即返回原城。`,`${unit}は${reason}により元の任務を中止し、${c}への撤退に移りました。実際の経路と日数を使って移動し、出発都市へ瞬時には戻りません。`);
    }
    case 'route_discovered':return text(`${c}之間的探索航行成功，新航路已顯示於地圖。`,`${c}を結ぶ探索航行が成功し、新航路が地図に表示されました。`);
    case 'march_arrived':return text(`${p}抵達${c}。入城或戰鬥依抵達時狀態處理。`,`${p}が${c}へ到着しました。到着時の状況に従い入城・戦闘を処理します。`);
    case 'march_returned':{
     const source=n.cities[0]||text('出發城','出発都市'),target=n.cities[1]||text('目的城','目的都市');
     if(d.reason==='army_lost')return text(`前往${target}的部隊遭遇災害，帶兵全損。武將返回${source}原編制，未發現新航路。`,`${target}へ向かう部隊は災害で全兵力を失いました。武将は${source}の元の所属部隊へ戻り、新航路は発見していません。`);
     if(d.reason==='target_changed')return text(`目的城${target}已易主，調動取消。武將保留在${source}的原編制。`, `目的都市${target}の所属が変わったため、移動を取り消しました。武将は${source}の元の所属部隊に残ります。`);
     if(d.reason==='route_blocked')return text(`前往${target}的途中城池易主，調動路線中斷。部隊返回${source}原編制。`,`${target}への経由都市の所属が変わり、移動経路が途切れました。部隊は${source}の元の編制へ戻ります。`);
     if(d.reason==='origin_changed')return text(`出發城${source}失陷或行軍人員已退場，原行軍取消。武將所屬及位置依目前戰局處理。`, `出発都市${source}の陥落、または行軍中の武将の退場により、元の行軍を取り消しました。武将の所属と所在地は現在の戦況に従います。`);
     return text(`前往${target}的原行軍已取消，請核對${source}與在途部隊的現有編制。`,`${target}への元の行軍を取り消しました。${source}と行軍中の部隊の現在の編制を確認してください。`);
    }
    case 'new_year':return text(`${row.year}年到來。人物年代、各城收入與體力恢復已核對。`,`${row.year}年を迎えました。武将の年代・都市収入・体力回復を確認しました。`);
    case 'staff_candidate':return text(`地方人士${label(d.name||'文吏')}願在${c}任職。候選保留3個月，雇用費60金、月俸5金；確認後才錄用。此人為架空內政人才。`,`${label(d.name||'文官')}が${c}での勤務を希望しています。候補の有効期間は3か月、雇用費は金60、月俸は金5です。採用を確定するまで雇用されません。架空の内政人材です。`);
    case 'staff_hired':return text(`${label(d.name||'文吏')}受聘為${c}的地方文吏，花費${d.amount??60}金，使用本旬城池行動。地方人才可編兵出戰、單挑、轉屬與繼承君主，並可受任為內政官。`,`${label(d.name||'文官')}を${c}の在地文官として雇用しました。金${d.amount??60}を支払い、都市の今旬の行動を使用しました。地方人材も編成・出陣・一騎討ち・移籍・君主継承ができ、内政担当官に任命できます。`);
    case 'staff_declined':return text(`${c}此次未錄用${label(d.name||'文吏')}，沒有支出雇用費。該城進入3個月的文吏招募冷卻期。`,`${c}では${label(d.name||'文官')}の採用を見送りました。雇用費は発生せず、この都市の次の文官募集まで3か月待機します。`);
    case 'staff_expired':{
     if(d.reason==='filled')return text(`${c}的編制已補足，${label(d.name||'文吏')}的候選資格已撤回。`,`${c}の人員が充足したため、${label(d.name||'文官')}の候補を取り下げました。`);
     if(d.reason==='owner_changed')return text(`${c}的所屬已變更，原有文吏候選${label(d.name||'文吏')}已撤回。`,`${c}の所属が変わったため、文官候補${label(d.name||'文官')}を取り下げました。`);
     return text(`${label(d.name||'文吏')}在${c}的候選期限已結束，沒有自動錄用或扣款；該城進入3個月冷卻期。`,`${c}での${label(d.name||'文官')}の応募期限が切れました。自動での採用や支払いは行わず、次の募集まで3か月待機します。`);
    }
    case 'staff_salary':{
     const bonus=d.bonus||{},result=Object.entries({gold:text('錢','金'),grain:text('糧','兵糧'),reserves:text('預備兵','予備兵')}).filter(([k])=>bonus[k]>0).map(([k,l])=>`${l}+${bonus[k]}`).join(text('、','・'))||text('本月無額外收入','今月の追加収入なし');
     return text(`${f}本月${d.counts?.cities??1}城共有文吏${d.counts?.staff??0}人，應付月俸${d.amount??0}金，實付${d.paid??0}金。內政成果：${result}。${d.paid<d.amount?'未足額領俸者本月暫停工作。':''}`,`${f}の${d.counts?.cities??1}都市、文官${d.counts?.staff??0}人分の月俸は金${d.amount??0}、支払額は金${d.paid??0}です。業務成果：${result}。${d.paid<d.amount?'俸給を全額受け取れなかった文官は今月の業務を休止します。':''}`);
    }
    case 'staff_allegiance':return text(`${c}的行政歸屬改變，文吏${label(d.name||'文吏')}留在本城，現隨${f}管理地方事務。`,`${c}の行政上の所属が変わり、文官${label(d.name||'文官')}は都市に留任し、現在は${f}のもとで地方行政に従事します。`);
    case 'domestic_report':return d.reason==='month'?text(`${f}本月${d.cities}城的商農增收已入庫：金${d.gold}、糧${d.grain}。按實際任職旬數結算，不重複領取。`,`${f}の${d.cities}都市で、今月の商農加算を入庫しました。資金${d.gold}・兵糧${d.grain}。実際の勤務旬数で一度だけ精算しています。`):text(`${f}本旬${d.cities}城完成委任工作，花費金${d.gold}、糧${d.grain}；募得預備兵${d.reserves}，訓練度成果${d.morale}。`,`${f}の${d.cities}都市で今旬の担当業務を実行しました。支出は資金${d.gold}・兵糧${d.grain}、募兵は予備兵${d.reserves}、練度の成果は${d.morale}です。`);
    case 'transport_departed':return text(`${c}的運輸隊已出發，攜帶金${d.gold}、糧${d.grain}、預備兵${d.reserves}、寶${d.treasure??0}。貨物已從出發城扣除，正在途中，抵達後才入庫。`,`${c}への輸送隊が出発しました。資金${d.gold}・兵糧${d.grain}・予備兵${d.reserves}・宝${d.treasure??0}を運びます。出発都市から差し引き、到着時に入庫します。`);
    case 'transport_arrived':return text(`${c}的運輸隊已抵達，金${d.gold}、糧${d.grain}、預備兵${d.reserves}、寶${d.treasure??0}已按實際狀態入庫，人員與兵員帳本已核對。`,`${c}への輸送隊が到着しました。資金${d.gold}・兵糧${d.grain}・予備兵${d.reserves}・宝${d.treasure??0}を実際の状況に従って入庫し、人員と兵力の集計を確認しました。`);
    case 'transport_returned':{
     const reason={army_missing:text('受補給部隊已不在途中','補給先の部隊がすでに行軍中ではないため'),army_changed:text('受補給部隊的任務或歸屬改變','補給先部隊の任務・所属が変わったため'),rendezvous_wait:text('在會合點等待受補給部隊','会合地点で補給先の部隊を待つため'),rendezvous_missed:text('未能在會合點接上部隊','会合地点で部隊と合流できなかったため'),delivered:text('途中補給交付完成','途中補給の引き渡しを終えたため'),escort_return:text('押運武將沿實際道路返程','護送武将が実際の経路で帰還するため'),retreat:text('運輸隊改向友城撤退','輸送隊が友軍都市への撤退に移ったため')}[d.reason];
     return reason?text(`${c}：${reason}。現有金${d.gold}、糧${d.grain}、預備兵${d.reserves}、寶${d.treasure??0}仍按實際位置及返程處理，不會立即送回原城。`,`${c}：${reason}、資金${d.gold}・兵糧${d.grain}・予備兵${d.reserves}・宝${d.treasure??0}を実際の位置と帰路に従って処理します。出発都市へ瞬時に戻しません。`):text(`${c}的原運輸任務已中止或折返，現有金${d.gold}、糧${d.grain}、預備兵${d.reserves}、寶${d.treasure??0}按實際返程結算。`,`${c}への元の輸送任務は中止または帰還となりました。残る資金${d.gold}・兵糧${d.grain}・予備兵${d.reserves}・宝${d.treasure??0}は実際の帰路に従って精算します。`);
    }
    case 'transport_weather':return text(`${c}的運輸隊途中遇險，預備兵損失${d.lost}。現有貨物：金${d.gold}、糧${d.grain}、預備兵${d.reserves}、寶${d.treasure??0}；不重複結算同次災害。`,`${c}への輸送中に災害が発生し、予備兵${d.lost}を失いました。現在の貨物は資金${d.gold}・兵糧${d.grain}・予備兵${d.reserves}・宝${d.treasure??0}です。同じ災害を重複精算しません。`);
    case 'campaign_victory':return text(`${f}完成天下統一。本次戰役已結算，可保存進度。`,`${f}が天下を統一しました。戦役の精算を終え、進行状況を保存できます。`);
    case 'campaign_defeat':return text(`${f}已無法繼續作戰。可保存結果或重新選擇劇本。`,`${f}は戦いを続けられなくなりました。結果を保存するか、シナリオを選び直せます。`);
    default:{const attacker=n.factions[0]||f;return text(`${attacker}的${d.coordinated?'多路部隊正協同':'部隊正'}朝${c}推進。`,`${attacker}の${d.coordinated?'複数部隊が連携して':'部隊が'}${c}へ進軍しています。`);}
   }
  }
  function historicalIntroduction(row){
   if(row.city_ids.length!==1||row.city_ids[0]!=='qiao')return '';
   const renamed=row.kind==='city_renamed'&&row.year===219&&row.month===1,
    upgraded=row.kind==='city_upgraded'&&row.year===221&&row.month===1;
   if(!renamed&&!upgraded)return '';
   const body=renamed?text('史實的小沛（沛縣）與譙（今亳州）是不同城池。劉備曾駐小沛，譙則為曹操故鄉。本作依指定設定，在219年以前以此固定節點代理小沛，219年起改為顯示譙郡；這不是史實上小沛於219年改名譙郡，也不代表城池遷移或易主。','史実の小沛（沛県）と譙（現在の亳州）は別の都市です。劉備は小沛に駐屯し、譙は曹操の故郷でした。本作では指定された設定により、この固定拠点を219年より前は小沛の代理とし、219年から譙郡と表示します。史実で219年に小沛が譙郡へ改称されたことや、都市の移転・支配変更を意味するものではありません。'):
    text('《三國志·文帝紀》裴松之注引《魏略》記載，黃初二年（221年）以長安、譙、許昌、鄴、洛陽為五都。譙亦為曹操故鄉。本作參照譙在曹魏的地位，自221年1月上旬升為大都市；「大都市」及收入倍率是遊戲設定，不是史書的都市規模分級。','『三國志』文帝紀の裴松之注が引く『魏略』には、黄初二年（221年）に長安・譙・許昌・鄴・洛陽を五都とした記録があります。譙は曹操の故郷でもありました。本作では曹魏における譙の地位を参考に、221年1月上旬から大都市とします。「大都市」という等級と収入倍率はゲーム独自の設定で、史書の都市規模分類ではありません。');
   const sources=renamed?[['卷01','巻1'],['卷32','巻32']]:[['卷01','巻1'],['卷02','巻2']];
   return `<aside class="event-history" data-event-history="qiao-${row.year}"><h3>${text('史實背景','史実の背景')}</h3><p>${escape(body)}</p><p class="event-history-sources">${text('史料：','史料：')}${sources.map(([tc,ja])=>`<a href="https://zh.wikisource.org/zh-hant/三國志/${tc}" target="_blank" rel="noopener noreferrer">${escape(text(`《三國志》${tc}`,`『三國志』${ja}`))}</a>`).join(' · ')}</p></aside>`;
  }
  function illustration(rows){
   const row=rows[0],catalog=view?.catalog||{},world=catalog.world||{x:0,y:0,width:1352,height:1024,background:'/assets/map-navigation.png'};
   const ids=[...new Set(rows.flatMap(e=>[...e.person_ids,...(typeof e.details.actor==='string'?[e.details.actor]:[])]))].slice(0,4);
   const targetScene=new Set(['battle_started','battle_result','tactic','duel_started','duel_result','march_weather','route_discovered','march_arrived','ai_campaign','march_resupplied','march_starvation','march_retreat']);
   const cityIds=targetScene.has(row.kind)?[...row.city_ids].reverse():row.city_ids;
   const cityId=cityIds.find(id=>catalog.cities?.some(c=>c.id===id))||catalog.factions?.find(f=>f.id===view?.game?.player)?.city;
   const city=catalog.cities?.find(c=>c.id===cityId),center=city?.position||[(world.x||0)+world.width/2,(world.y||0)+world.height/2];
   const background=catalog.map_presentation?.road_center_corrections?.backgrounds?.[world.background]||world.background;
   const safeBackground=/^\/assets\/map(?:-[a-z-]+)?\.png$/.test(background||'')?background:'/assets/map-navigation.png';
   const x=Math.max(world.x||0,Math.min(center[0]-144,(world.x||0)+world.width-288)),y=Math.max(world.y||0,Math.min(center[1]-86,(world.y||0)+world.height-172));
   const fill=catalog.map_presentation?.castle_fill_pixels||[],outline=catalog.map_presentation?.castle_outline_pixels||[];
   const sprite=city?[[outline,'#000'],[fill,'#fff']].map(([pixels,color])=>pixels.map(([dx,dy])=>`<rect x="${center[0]+dx}" y="${center[1]+dy}" width="4" height="4" fill="${color}"/>`).join('')).join(''):'';
   const art=`<svg class="event-map" viewBox="${x} ${y} 288 172" role="img" aria-label="${escape(text('事件所在地圖示意','出来事の場所を示す地図'))}"><image href="${escape(root.GamePaths?.asset(safeBackground)||safeBackground)}" x="${world.x||0}" y="${world.y||0}" width="${world.width}" height="${world.height}"/>${sprite}</svg>`;
   let people=ids.map(id=>{const name=names({...row,person_ids:[id]}).people[0];return portraits?.entry?.(id)?`<figure class="event-person">${portraits.html(id,name,{size:'duel'})}<figcaption>${escape(name)}</figcaption></figure>`:'';}).join('');
   if(STAFF.has(row.kind)){
    const staff=[...new Map(rows.filter(e=>/^clerk-[0-9]{6,12}$/.test(e.details.staff_id||'')&&['clerk-1','clerk-2','clerk-3'].includes(e.details.portrait)).map(e=>[e.details.staff_id,e.details])).values()].slice(0,4);
    people+=staff.map(d=>`<figure class="event-person" data-event-staff="${escape(d.staff_id)}">${portraits?.civilHtml?portraits.civilHtml(d.portrait,d.name,{className:'event-staff-face',locale:locale()}):`<img class="event-staff-face" src="${root.GamePaths?.asset(`/assets/civil-staff/${d.portrait}.png`)||`/assets/civil-staff/${d.portrait}.png`}" width="32" height="40" alt="${escape(text(`${label(d.name)}・架空文吏共用像素肖像`,`${label(d.name)}・架空文官の共通ドット肖像`))}"/>`}<figcaption>${escape(label(d.name))}</figcaption></figure>`).join('');
   }
   const treasureArt=TREASURY.has(row.kind)?`<svg class="event-treasure" viewBox="0 0 32 28" shape-rendering="crispEdges" role="img" aria-label="${escape(text('寶箱與賞賜金錢示意','宝箱と褒美の資金のイメージ'))}"><path fill="#000" d="M4 3h20v3h3v17H1V6h3z"/><path fill="#aa4b00" d="M4 6h20v14H4z"/><path fill="#ffac20" d="M4 6h20v4H4zM4 13h20v2H4z"/><path fill="#ffdd60" d="M7 6h3v14H7zM18 6h3v14h-3zM12 11h4v6h-4z"/><path fill="#000" d="M21 20h9v6H18v-3h3z"/><path fill="#ffdd60" d="M22 21h6v3h-6zM19 24h9v1h-9z"/></svg>`:'';
   return `<div class="event-art">${art}${treasureArt}${people?`<div class="event-people">${people}</div>`:''}</div><p class="event-art-caption">${escape(STAFF.has(row.kind)?text('事件示意：目前地圖與架空文吏共用像素肖像；文吏另建名冊，不占歷史人物身分。','場面イメージ：現在の地図と架空文官の共通ドット肖像。文官は歴史人物とは別の名簿で管理します。'):text('事件示意：目前地圖與武將像素肖像','場面イメージ：現在の地図と武将のドット肖像'))}</p>`;
  }
  function render(){
   if(!active||!modal||disposed)return;
   const row=active[0],period={1:'上旬',11:'中旬',21:'下旬'}[row.day],count=active.length>1?text(` · 共${active.length}項`,` · ${active.length}件`):'';
   modal.innerHTML=`<div data-event-root data-l10n-native="${locale()}"><div class="event-heading"><div><p class="event-kicker">${escape(historyMode?text('事件回顧','出来事の記録'):text('戰役事件','戦役の出来事'))} · ${shown}/${total}</p><h2 id="event-title">${escape(KINDS[row.kind][locale()==='ja'?1:0])}${escape(count)}</h2></div><label class="language-picker">${text('語言','言語')}<select data-language-picker aria-label="${text('切換語言','言語切替')}"><option value="zh-Hant" ${locale()==='zh-Hant'?'selected':''}>繁體中文</option><option value="ja" ${locale()==='ja'?'selected':''}>日本語</option></select></label></div><p class="event-date">${row.year}年${row.month}月${period}</p>${illustration(active)}<div id="event-description" class="event-description">${active.map(e=>`<p>${escape(description(e))}</p>${historicalIntroduction(e)}`).join('')}</div><div class="dialog-actions event-actions">${queue.length?`<button data-event-skip>${text('略過本批','この一括表示を終了')}</button>`:''}<button class="primary" data-event-next autofocus>${queue.length?text('下一則','次へ'):text('返回戰役','戦役に戻る')}</button></div></div>`;
   modal.querySelector('[data-event-next]').onclick=advance;
   const skip=modal.querySelector('[data-event-skip]');if(skip)skip.onclick=clear;
   if(!modal.open)modal.showModal();
   modal.querySelector('[data-event-next]')?.focus({preventScroll:true});
  }
  function blocked(){return !modal||disposed||isBusy()||isPreview()||parent?.open;}
  function pump(){
   scheduled=false;if(active||!queue.length||blocked())return false;
   if(portraits?.load&&!portraitAttempted){portraitAttempted=true;Promise.resolve(portraits.load()).then(requestPump,requestPump);return false;}
   active=queue.shift();shown++;render();return true;
  }
  function requestPump(){if(disposed||scheduled)return;scheduled=true;schedule(pump);}
  function closeModal(){if(modal?.open)modal.close();}
  function advance(){if(queue.length){active=queue.shift();shown++;render();}else{active=null;historyMode=false;closeModal();}}
  function clear(){queue=[];active=null;historyMode=false;closeModal();}
  function observe(next,{baseline=false,newGame=false}={}){
   const nextKey=campaignKey(next),rows=eventRows(next),latest=rows.at(-1)?.id||0;view=next;refreshHistoryLabel();
   if(baseline||!nextKey||key!==nextKey||latest<cursor||newGame){clear();key=nextKey;cursor=newGame?0:latest;shown=0;total=0;}
   if(!nextKey||baseline)return;
   const fresh=rows.filter(row=>row.id>cursor);cursor=Math.max(cursor,latest);
   const visible=fresh.filter(row=>automatic(row,next.game.player));
   if(visible.length){const batches=groupRows(clone(visible));queue.push(...batches);if(!active&&shown===total){shown=0;total=0;}total+=batches.length;}
   requestPump();
  }
  function history(){
   if(blocked()||modal?.open)return false;
   view=getView()||view;const rows=eventRows(view);if(!rows.length)return false;
   clear();queue=groupRows(clone(rows));historyMode=true;shown=0;total=queue.length;requestPump();return true;
  }
  function onCancel(){queue=[];active=null;historyMode=false;}
  // Native close events are dispatched later. A previous close must not erase
  // a fresh history/new-game queue created before that event reaches us.
  function onClose(){if(modal?.open)return;if(active){active=null;queue=[];historyMode=false;}requestPump();}
  function onLanguage(){refreshHistoryLabel();if(active&&modal?.open)render();}
  modal?.addEventListener?.('cancel',onCancel);modal?.addEventListener?.('close',onClose);
  parent?.addEventListener?.('close',requestPump);doc?.addEventListener?.('game-language-change',onLanguage);
  refreshHistoryLabel();
  return Object.freeze({observe,pump:requestPump,history,clear,description,
   snapshot:()=>({key,cursor,pending:queue.map(group=>group.map(row=>row.id)),active:active?.map(row=>row.id)||null,historyMode,shown,total}),
   dispose(){clear();disposed=true;modal?.removeEventListener?.('cancel',onCancel);modal?.removeEventListener?.('close',onClose);parent?.removeEventListener?.('close',requestPump);doc?.removeEventListener?.('game-language-change',onLanguage);}
  });
 }
 if(typeof module==='object'&&module.exports)module.exports={create,validEvent,eventRows,campaignKey,groupRows,KINDS};else root.GameEvents={create};
})(typeof window==='object'?window:globalThis);
