/* Local civil employees are a separate identity pool, never historical officers. */
'use strict';
(function(root){
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const choose=(locale,tc,ja)=>locale==='ja'?ja:tc;
 const specialtyLabels={commerce:['商務','商務'],farming:['農務','農務'],recruitment:['征募','募兵']};
 const reasons={no_available_staff:['本城沒有可行動且正常履職的文吏。','この都市に行動可能で勤務中の文吏がいません。'],no_historical_candidate:['本城與可訪問的鄰城目前沒有可登用的歷史武將。','現在、この都市と訪問可能な隣接都市には登用できる歴史武将がいません。'],no_candidate:['目前沒有候選文吏。','現在、候補の文吏はいません。'],not_owned:['僅能雇用本方城池的文吏。','自勢力の都市でのみ雇用できます。'],wrong_phase:['請在戰略階段辦理雇用。','戦略段階で雇用してください。'],command_books:['本勢力命令書不足。','この勢力の命令書が不足しています。'],battle:['交戰中的城池暫停雇用。','交戦中の都市では雇用できません。'],not_needed:['本城編制已足，暫停補充文吏。','この都市の人員は足りているため、補充を休止しています。'],staff_limit:['本城文吏已達上限。','この都市の文吏数は上限に達しています。'],city_full:['武將與文吏合計已達都市定員。','武将と文吏の合計が都市の定員に達しています。'],insufficient_gold:['本城金錢不足。','この都市の資金が不足しています。']};
 function data(view){return view?.catalog?.civil_staff||null;}
 function city(view,id){return data(view)?.cities?.[id]||null;}
 function count(view,id){const row=city(view,id);return row?.staff_count??row?.count??row?.employees?.length??0;}
 function occupancy(view,value){const id=typeof value==='string'?value:value?.id,row=city(view,id);return row?.occupancy??((typeof value==='object'?value:view?.game?.cities?.[id])?.roster?.officer_ids?.length??0)+count(view,id);}
 function month(value,locale='zh-Hant'){
  if(!Number.isInteger(value)||value<0)return '—';
  return choose(locale,`${Math.floor(value/12)}年${value%12+1}月`,`${Math.floor(value/12)}年${value%12+1}月`);
 }
 function portrait(record,locale='zh-Hant',{className='civil-staff-portrait'}={}){
  if(!['civil-staff-portrait','event-staff-face'].includes(className))className='civil-staff-portrait';
  const title=choose(locale,'架空文吏・共用像素肖像','架空の文吏・共用ドット肖像');
  if(root.GamePortraits?.civilHtml)return root.GamePortraits.civilHtml(record?.portrait,record?.name||'',{className,locale});
  return /^clerk-[123]$/.test(record?.portrait||'')?`<img data-civil-portrait="${record.portrait}" class="${className}" src="${root.GamePaths?.asset(`/assets/civil-staff/enhanced/${record.portrait}.png`)||`/assets/civil-staff/enhanced/${record.portrait}.png`}" width="128" height="160" alt="${title}" loading="lazy" decoding="async">`:`<span class="${className} civil-staff-placeholder" role="img" aria-label="${title}">吏</span>`;
 }
 function stat(value){return Number.isInteger(value)&&value>=0?value:'—';}
 function attributes(record,locale='zh-Hant',isRuler=record?.is_ruler===true){
  const p=record?.profile||{},experience=Number.isInteger(record?.experience)&&record.experience>=0&&record.experience<=49999?Math.floor(record.experience/50):'—';
  const loyalty=isRuler?'--':stat(record?.loyalty);
  return choose(locale,`兵${stat(record?.troops??0)} · 武${stat(p.martial_strength)} · 知${stat(p.intellect)} · 德${stat(p.virtue)} · 忠${loyalty} · 體${stat(record?.health??p.health_max)} · 經${experience}`,`兵${stat(record?.troops??0)}・武${stat(p.martial_strength)}・知${stat(p.intellect)}・徳${stat(p.virtue)}・忠${loyalty}・体力${stat(record?.health??p.health_max)}・経${experience}`);
 }
 function summary(view,id,{locale='zh-Hant',cityName=value=>value,bilingual=false}={}){
  if(bilingual)return ['zh-Hant','ja'].map(language=>`<div data-locale-only="${language}" data-l10n-native="${language}">${summary(view,id,{locale:language,cityName})}</div>`).join('');
  const row=city(view,id);if(!row)return '';
  const employees=row.employees||[],salary=row.monthly_salary??employees.length*(data(view)?.rules?.monthly_salary??5);
  const label=value=>root.GameI18n?.t?root.GameI18n.t(String(value),locale):String(value);
  return `<section class="civil-staff-summary" data-l10n-native="${locale}"><p class="small">${choose(locale,`武將 ${row.officer_count??view?.game?.cities?.[id]?.roster?.officer_ids?.length??0}人 · 文吏 ${count(view,id)}人 · 合計 ${occupancy(view,id)}/${view?.catalog?.rules?.city_officer_capacity??99}人`,`武将 ${row.officer_count??view?.game?.cities?.[id]?.roster?.officer_ids?.length??0}人・文吏 ${count(view,id)}人・合計 ${occupancy(view,id)}/${view?.catalog?.rules?.city_officer_capacity??99}人`)}</p>${employees.length?`<p class="small">${choose(locale,'地方文吏','地方文吏')}：${employees.map(p=>escape(label(p.name))).join('、')} · ${choose(locale,`月俸合計 ${salary}金`,`俸給は月額計${salary}`)}</p>`:''}${row.candidate?`<p class="small staff-candidate-notice">${choose(locale,`${escape(label(cityName(id)))}有文吏候選，等待雇用。`,`${escape(label(cityName(id)))}に雇用を待つ文吏候補がいます。`)}</p>`:''}</section>`;
 }
 function create(options={}){
  const doc=options.document||root.document,dialog=options.dialog||doc?.querySelector?.('#dialog'),i18n=options.i18n||root.GameI18n;
  const getView=options.getView||(()=>null),cityName=options.cityName||(id=>id),openDialog=options.openDialog,command=options.command,isBusy=options.isBusy||(()=>false),isPreview=options.isPreview||(()=>false);
  let active=null,pending=false,disposed=false;
  const bookReady=kind=>root.GameCommandBooks?.can(getView(),kind)===true,bookHint=kind=>root.GameCommandBooks?.html(getView(),{kind,locale:locale()})||'';
  const locale=()=>i18n?.locale==='ja'?'ja':'zh-Hant',text=(tc,ja)=>choose(locale(),tc,ja),label=value=>i18n?.t?i18n.t(value,locale()):String(value??'');
  const query=selector=>dialog?.querySelector?.(selector);
  const currentRuler=person=>root.GameOfficerChoices?.isRuler?.(person?.id,getView()?.game?.extension?.leaders)===true;
  function showing(){return !!active&&dialog?.open!==false&&!!query('[data-civil-staff-dialog]');}
  function card(person,{candidate=false}={}){
   const kind=specialtyLabels[person.specialty]||['內政','内政'];
   const working=person.working?text('履職中','勤務中'):text('待月結／欠薪暫停','月次精算待ち・未払い時は休務');
   const equipment=!candidate&&root.GameEquipment?.summary?root.GameEquipment.summary(getView(),person.id,{locale:locale(),bilingual:false,compact:true}):'';
   return `<article class="civil-staff-card" data-staff-id="${escape(person.id)}">${portrait(person,locale())}<div><p><strong>${escape(label(person.name))}</strong> <span class="civil-staff-kind">${text('架空文吏','架空の文吏')}</span></p><p class="small">${text('專長','得意分野')}：${kind[locale()==='ja'?1:0]}</p><p class="small">${attributes(person,locale(),!candidate&&currentRuler(person))}</p>${equipment}<p class="small">${candidate?text(`候選可雇用至${month(person.expires_month,locale())}開始前。`,`${month(person.expires_month,locale())}の月初まで雇用できます。`):working}${!candidate&&person.unpaid_months?text(` · 連續欠薪${person.unpaid_months}月`,`・俸給未払い${person.unpaid_months}か月`):''}</p></div></article>`;
  }
  function searchBody(row){
   const actors=[...(row.searchable_staff||[])].sort((a,b)=>b.profile.virtue-a.profile.virtue||b.profile.intellect-a.profile.intellect||a.id.localeCompare(b.id)),targets=[...(row.search_targets||[])].sort((a,b)=>b.virtue-a.virtue||b.intellect-a.intellect||String(a.id).localeCompare(String(b.id),undefined,{numeric:true}));
   if(!actors.some(p=>p.id===active.actor))active.actor=actors[0]?.id||'';
   if(!targets.some(p=>String(p.id)===String(active.target)))active.target=targets[0]?.id??'';
   const reason=reasons[row.search_blocked_reason];
   const historical=p=>{const runtime=getView()?.game?.officers?.[p.id];return {...p,profile:runtime?.profile||p,health:runtime?.health};};
   return `<section class="civil-staff-search"><h3>${text('文吏尋訪歷史武將','文吏による歴史武将の登用')}</h3><p class="small">${text('文吏可代辦在野登用，費用60金，使用原登用成功判定並使用全勢力共用命令書。','文吏が在野武将の登用を代行します。費用60で、既存の成功判定を使い、勢力共通の命令書を使います。')}</p><label class="field">${text('執行文吏','実行する文吏')}<select id="staff-search-actor">${actors.map(p=>`<option value="${escape(p.id)}" ${p.id===active.actor?'selected':''}>${escape(label(p.name))} · ${attributes(p,locale(),currentRuler(p))}</option>`).join('')||`<option value="">${text('沒有可行動的文吏','行動できる文吏がいません')}</option>`}</select></label><label class="field">${text('歷史武將候選','歴史武将の候補')}<select id="staff-search-target">${targets.map(p=>`<option value="${p.id}" ${String(p.id)===String(active.target)?'selected':''}>${escape(label(p.name))} · ${attributes(historical(p),locale(),currentRuler(p))}</option>`).join('')||`<option value="">${text('附近沒有可登用的歷史武將','近隣に登用できる歴史武将がいません')}</option>`}</select></label><p class="small" role="status">${reason?reason[locale()==='ja'?1:0]:''}</p>${bookHint('staff_recruit')}<button id="staff-search-confirm" ${pending||isPreview()||!bookReady('staff_recruit')||!row.can_search?'disabled':''}>${text('確認文吏尋訪','文吏の訪問を確定')}</button></section>`;
  }
  function rulesBody(rules={}){
   const fee=rules.hire_gold??60,salary=rules.monthly_salary??5;
   return `<details class="civil-staff-rules"><summary>${text('文吏招募與任職規則','文吏の募集と勤務規則')}</summary><p>${text(`雇用${fee}金，使用全勢力共用命令書；每人月俸${salary}金。不需要先指定武將，無駐將城也能辦理。`,`雇用費${fee}、一人の月額俸給${salary}。雇用は勢力共通の命令書を使います。実行武将の指定は不要で、武将がいない都市でも雇用できます。`)}</p><p>${text('普通城目標2人、大城與巨城3人；名冊中的行軍武將與30日內確定到達的增援也計入缺編判定。文吏與歷史武將合計最多99人。','通常都市の目標は2人、大都市・巨大都市は3人です。名簿に残る行軍中の武将と30日以内に到着予定の援軍も人員判定に含め、武将と文吏の合計定員は99人です。')}</p><p>${text('每月上旬檢查；持續缺編2個月後，一人城60%、大城二人時30%，連續3次未出現候選後下次保底。開局無人城直接推薦；戰後無人城須穩定30日。','月の上旬に判定します。2か月続けて人員不足なら、1人の都市は60%、大都市で2人の場合は30%。候補が3回続けて現れなければ次回は必ず推薦されます。開始時の無人都市には直ちに推薦し、戦後の無人都市では30日の安定を待ちます。')}</p><p>${text('每城同時一名候選，保留3個月；雇用、拒絕或過期後冷卻3個月。人物、肖像與能力生成後固定，讀檔不重抽。玩家與AI使用相同規則。','各都市の候補は一度に1人で、3か月間保持されます。雇用・辞退・期限切れ後は3か月休止します。候補の名前・肖像・能力は生成時に固定され、ロードでは変わりません。プレイヤーとAIは同じ規則です。')}</p><p>${text('地方文吏可像普通武將一樣編兵、出戰、單挑、轉屬與繼承君主，仍使用獨立身分。商農與募兵訓練改由兩名委任官管理，不重複疊加舊有個人收入加成；欠薪時暫停委任工作。','地方文吏も通常の武将と同じく編成・出陣・一騎討ち・移籍・君主継承が可能で、独立した人物IDを使います。商農と募兵・訓練は二人の担当官が管理し、従来の個人収入加算は重複しません。俸給未払い時は担当業務を休止します。')}</p></details>`;
  }
  function renderCity(){
   const view=getView(),row=city(view,active.city),record=view?.game?.cities?.[active.city];
   if(!view?.game||!record||!row)return;
   const rules=data(view).rules||{},candidate=row.candidate,reason=reasons[row.blocked_reason];
   const body=`<div data-civil-staff-dialog="city" data-civil-staff-city="${escape(active.city)}" data-l10n-native="${locale()}">${summary(view,active.city,{locale:locale(),cityName:id=>label(cityName(id))})}${bookHint('hire_staff')}<p>${text(`內政編制 ${row.effective_count??row.occupancy}/${row.minimum??row.target}人；文吏上限 ${row.limit}人。`,`内政の人員 ${row.effective_count??row.occupancy}/${row.minimum??row.target}人。文吏の上限は${row.limit}人です。`)}</p><h3>${text('本城文吏','この都市の文吏')}</h3>${row.employees?.length?row.employees.map(p=>card(p)).join(''):`<p>${text('本城尚未雇用文吏。','この都市には雇用済みの文吏がいません。')}</p>`}<h3>${text('本期候選','現在の候補')}</h3>${candidate?card(candidate,{candidate:true}):`<p>${text('目前沒有候選；每月上旬依實際缺編與冷卻條件推薦。','現在の候補はいません。月の上旬に人員不足と休止期間の条件に従って推薦されます。')}</p>`}${row.cooldown_until_month>(data(view).current_month??0)?`<p class="small">${text(`推薦冷卻至${month(row.cooldown_until_month,locale())}。`,`${month(row.cooldown_until_month,locale())}まで推薦を休止します。`)}</p>`:''}<p class="small" id="civil-staff-boundary" role="status">${candidate&&reason?reason[locale()==='ja'?1:0]:''}</p><p>${text(`雇用費資金${rules.hire_gold??60}；每人每月薪俸資金${rules.monthly_salary??5}。`,`雇用費は資金${rules.hire_gold??60}、一人の月額俸給は資金${rules.monthly_salary??5}。`)}</p>${active.error?`<p class="staff-command-error" role="alert">${text('操作未完成，請核對最新資源與候選後重試。','操作を完了できませんでした。最新の資源と候補を確認して、再度お試しください。')}</p>`:''}${row.employees?.length?searchBody(row):''}${rulesBody(rules)}</div>`;
   const buttons=`<button data-cancel>${text('返回戰役','戦役へ戻る')}</button><button id="staff-registry">${text('我方文吏名冊','自勢力の文吏名簿')}</button>${candidate?`<button id="reject-civil-staff" ${pending||isPreview()||!row.can_reject?'disabled':''}>${text('拒絕本期候選','今回の候補を断る')}</button><button id="hire-civil-staff" class="primary" ${pending||isPreview()||!bookReady('hire_staff')||!row.can_hire?'disabled':''}>${text('確認雇用','雇用を確定')}</button>`:''}`;
   if(openDialog(text(`地方文吏 · ${label(cityName(active.city))}`,`地方文吏・${label(cityName(active.city))}`),body,buttons)===undefined)return;
   query('#staff-registry').onclick=()=>openRegistry();
   for(const [selector,kind] of [['#hire-civil-staff','hire_staff'],['#reject-civil-staff','reject_staff']]){
    const button=query(selector);if(!button)continue;
    button.onclick=async()=>{
     const current=city(getView(),active.city);
     if(pending||isBusy()||isPreview()||!bookReady(kind)||!candidate||current?.candidate?.id!==candidate.id||!(kind==='hire_staff'?current.can_hire:current.can_reject))return;
     const token=active;pending=true;button.disabled=true;
     const other=query(selector==='#hire-civil-staff'?'#reject-civil-staff':'#hire-civil-staff');if(other)other.disabled=true;
     try{token.error=await command(kind,{city:token.city,candidate:candidate.id})===false;}catch{token.error=true;}
     finally{pending=false;if(active===token&&showing())renderCity();}
    };
   }
   const searchActor=query('#staff-search-actor'),searchTarget=query('#staff-search-target'),search=query('#staff-search-confirm');
   if(searchActor)searchActor.onchange=()=>{active.actor=searchActor.value;};
   if(searchTarget)searchTarget.onchange=()=>{active.target=searchTarget.value;};
   if(search)search.onclick=async()=>{
    if(pending||isBusy()||isPreview()||!bookReady('staff_recruit')||!row.can_search||!active.actor||active.target==='')return;
    const token=active;pending=true;search.disabled=true;
    try{token.error=await command('staff_recruit',{city:token.city,actor:token.actor,officer:root.GameOfficerChoices?.ref?root.GameOfficerChoices.ref(token.target):(/^clerk-[0-9]{6,12}$/.test(String(token.target))?token.target:Number(token.target))})===false;}catch{token.error=true;}
    finally{pending=false;if(active===token&&showing())renderCity();}
   };
   i18n?.apply?.();
  }
  function renderRegistry(){
   const view=getView();if(!view?.game)return;
   const source=data(view)?.people||[],people=(Array.isArray(source)?source:Object.values(source)).filter(p=>p.owner===view.game.player).sort((a,b)=>a.city.localeCompare(b.city)||a.id.localeCompare(b.id));
   const q=active.search||'',matches=people.filter(p=>[p.name,cityName(p.city),label(p.name),label(cityName(p.city))].some(v=>String(v).includes(q)));
   const body=`<div data-civil-staff-dialog="registry" data-l10n-native="${locale()}"><p>${text(`我方文吏${people.length}人。這些是架空的地方行政人員，與${view.catalog.library?.length??0}名歷史人物分開登記。`,`自勢力の文吏は${people.length}人です。架空の地方行政人員で、歴史人物${view.catalog.library?.length??0}人とは別に登録されています。`)}</p><label class="field">${text('搜尋姓名或城池','名前・都市を検索')}<input id="staff-search" type="search" value="${escape(q)}"></label><div class="civil-staff-registry-results">${matches.map(p=>`<section><h3>${escape(label(cityName(p.city)))}</h3>${card(p)}</section>`).join('')||`<p>${text('沒有符合條件的文吏。','条件に合う文吏はいません。')}</p>`}</div></div>`;
   if(openDialog(text('地方文吏名冊','地方文吏の名簿'),body,`<button data-cancel>${text('返回戰役','戦役へ戻る')}</button>`)===undefined)return;
   const input=query('#staff-search');input.oninput=()=>{active.search=input.value;const start=input.selectionStart;renderRegistry();const next=query('#staff-search');next.focus?.();next.setSelectionRange?.(start,start);};
   i18n?.apply?.();
  }
  function refresh(){if(!disposed&&showing()){const scroll=dialog.scrollTop;active.kind==='city'?renderCity():renderRegistry();dialog.scrollTop=scroll;}}
  function open(id){if(disposed||isBusy()||!city(getView(),id))return false;active={kind:'city',city:id};renderCity();return true;}
  function openRegistry(){if(disposed||isBusy()||!getView()?.game)return false;active={kind:'registry',search:''};renderRegistry();return true;}
  doc?.addEventListener?.('game-language-change',refresh);
  return {open,openRegistry,refresh,dispose(){disposed=true;active=null;doc?.removeEventListener?.('game-language-change',refresh);}};
 }
 const api=Object.freeze({data,city,count,occupancy,month,portrait,attributes,summary,create});
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.GameCivilStaff=api;
})(typeof window!=='undefined'?window:globalThis);
