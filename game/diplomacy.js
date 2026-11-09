/* Player diplomacy controls. Eligibility and all effects are supplied by the campaign. */
'use strict';
(function(root){
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const stages={
  intimate:['親密','親密'],friendly:['友好','友好'],normal:['平常','平常'],
  discord:['不和','不和'],hostile:['險惡','険悪'],hateful:['敵視','敵視']
 };
 const actions={
  goodwill:{name:['親善','親善'],note:['派使節送出資金、兵糧或寶物，改善兩勢力的外交感情。','使者が資金・兵糧・宝を贈り、両勢力の外交感情を改善します。']},
  alliance:{name:['同盟','同盟'],note:['外交感情須達平常。盟友互不攻擊，部隊可通過同盟領地。','外交感情が平常以上で締結できます。同盟中は互いに攻撃せず、同盟領を通過できます。']},
  return_captives:{name:['歸還俘虜','捕虜返還'],note:['請對方交還被俘的本勢力武將。','相手勢力に捕らわれた自勢力の武将の返還を求めます。']},
  request_attack:{name:['請求攻擊','攻撃要請'],note:['可請求友好以上的同盟勢力攻打第三方據點，部隊按行軍規則出陣。','友好以上の同盟勢力に第三勢力の拠点への攻撃を要請します。部隊は行軍ルールに従って出陣します。']},
  surrender:{name:['勸告投降','降伏勧告'],note:['勸告對方勢力投降。外交感情、雙方國力及戰局會影響結果。','相手勢力に降伏を勧めます。外交感情、両勢力の国力と戦況が結果に影響します。']}
 };
 const resources={gold:['資金','資金'],grain:['兵糧','兵糧'],treasure:['寶物','宝']};
 const actionName=(id,locale)=>Object.hasOwn(actions,id)?actions[id].name[locale==='ja'?1:0]:null;
 const same=(a,b)=>String(a)===String(b);
 const find=(rows,id)=>rows.find(row=>same(row.id,id));
 const bounded=(value,maximum,minimum=0)=>{
  const n=Number(value);
  return Math.max(minimum,Math.min(maximum,Number.isFinite(n)?Math.trunc(n):minimum));
 };

 function create(options={}){
  const doc=options.document||root.document,dialog=options.dialog||doc?.querySelector?.('#dialog');
  const {getView,openDialog,command}=options;
  const cityName=options.cityName||(id=>id),isBusy=options.isBusy||(()=>false),isPreview=options.isPreview||(()=>false);
  const i18n=options.i18n||root.GameI18n,books=options.commandBooks||root.GameCommandBooks;
  const locale=()=>i18n?.locale==='ja'?'ja':'zh-Hant',text=(tc,ja)=>locale()==='ja'?ja:tc;
  const translate=value=>i18n?.t?.(String(value??''),locale())??String(value??'');
  const factionName=options.factionName||(id=>{
   const row=getView()?.catalog?.factions?.find(f=>f.id===id);
   return row?.display_name||row?.name||id;
  });
  const data=()=>getView()?.catalog?.diplomacy;
  const query=id=>dialog?.querySelector?.('#'+id);
  const validCampaign=()=>{
   const player=getView()?.game?.player;
   return !!player&&player!=='observer'&&!isPreview()&&getView()?.game?.phase==='city'&&
    Array.isArray(data()?.cities)&&Array.isArray(data()?.targets);
  };
  const identity=()=>JSON.stringify([getView()?.catalog?.scenario_id,getView()?.game?.seed,getView()?.game?.player]);
  let active=null,pending=false;
  const showing=()=>!!active&&dialog?.open===true&&!!dialog.querySelector('[data-diplomacy-dialog]');
  const canOpen=()=>validCampaign()&&!isBusy();
  const unavailable=()=>text('目前不符合此項外交指令的條件。','現在はこの外交指令の条件を満たしていません。');
  const field=(id,caption,value,choices)=>`<label class="field" for="${id}">${escape(caption)}<select id="${id}" ${choices.length?'':'disabled'}>${choices.length?choices.map(([key,title])=>`<option value="${escape(key)}" ${same(key,value)?'selected':''}>${escape(title)}</option>`).join(''):'<option value="">—</option>'}</select></label>`;
  const number=(id,caption,value,min,max)=>`<label class="field" for="${id}">${escape(caption)}<input id="${id}" type="number" inputmode="numeric" min="${min}" max="${max}" step="1" value="${value}" ${max<1?'disabled':''}></label>`;
  const stage=target=>Object.hasOwn(stages,target.stage)?text(...stages[target.stage]):'—';
  const alliance=target=>!target.alliance?text('無','なし'):target.alliance.historical?
   text('史實同盟','史実同盟'):text(`剩餘 ${target.alliance.turns} 旬`,`残り ${target.alliance.turns} 旬`);
  const envoyLabel=envoy=>`${translate(envoy.name)} · 知 ${envoy.intellect} · ${text('德','徳')} ${envoy.virtue}`;
  const native=value=>`<span data-l10n-native="${locale()}">${escape(value)}</span>`;
  function selection(){
   const current=data(),draft=active.draft;
   const city=find(current.cities,draft.city)||current.cities[0];
   const target=find(current.targets,draft.target)||current.targets[0];
   const envoys=[...(city?.envoys||[])].sort((a,b)=>
    (b.intellect+b.virtue)-(a.intellect+a.virtue)||b.virtue-a.virtue);
   const envoy=find(envoys,draft.envoy)||envoys[0];
   const captives=target?.captives||[],prisoner=find(captives,draft.prisoner)||captives[0];
   const attackCities=target?.attack_cities||[];
   const attackCity=attackCities.includes(draft.attack_city)?draft.attack_city:attackCities[0];
   Object.assign(draft,{city:city?.id,target:target?.id,envoy:envoy?.id,prisoner:prisoner?.id,attack_city:attackCity});
   const maximum=city?.limits?.[draft.resource]??0;
   return {current,draft,city,target,envoys,envoy,captives,prisoner,attackCities,attackCity,maximum};
  }
  function payload(row){
   const {current,draft,city,target,envoy,prisoner,attackCity,maximum}=row;
   if(!city||!target||!envoy||!current.can_command||target.actions?.[draft.action]!==true)return null;
   const commandData={action:draft.action,city:city.id,envoy:envoy.id,target:target.id};
   switch(draft.action){
    case 'goodwill':{
     const amount=bounded(draft.amount,maximum);
     return amount>0?{...commandData,resource:draft.resource,amount}:null;
    }
    case 'alliance':return {...commandData,duration:bounded(draft.duration,current.max_turns,1)};
    case 'return_captives':return prisoner?{...commandData,prisoner:prisoner.id}:null;
    case 'request_attack':return attackCity?{...commandData,attack_city:attackCity}:null;
    case 'surrender':return commandData;
    default:return null;
   }
  }
  function usable(row){
   return canOpen()&&!pending&&active.identity===identity()&&books?.can(getView(),'diplomacy')===true&&!!payload(row);
  }
  function relations(targets){
   if(!targets.length)return `<p>${text('目前沒有可交涉的其他勢力。','現在は交渉できる他勢力がありません。')}</p>`;
   return `<details data-diplomacy-relations><summary>${text('查看各勢力的外交感情','各勢力との外交感情を確認')}</summary>
   <div class="diplomacy-relations-scroll"><table><thead><tr><th scope="col">${text('勢力','勢力')}</th><th scope="col">${text('外交感情','外交感情')}</th><th scope="col">${text('同盟','同盟')}</th></tr></thead>
   <tbody>${targets.map(target=>`<tr><th scope="row">${escape(translate(factionName(target.id)))}</th><td>${escape(stage(target))}</td><td>${escape(alliance(target))}</td></tr>`).join('')}</tbody></table></div></details>`;
  }
  function extra(row){
   const {current,draft,captives,prisoner,attackCities,attackCity,maximum}=row;
   switch(draft.action){
    case 'goodwill':
     return `<div class="diplomacy-fields">${field('diplomacy-resource',text('贈禮種類','贈り物の種類'),draft.resource,Object.entries(resources).map(([id,name])=>[id,text(...name)]))}
      ${number('diplomacy-amount',text(`贈禮數量（最多 ${maximum}）`,`贈る量（最大 ${maximum}）`),bounded(draft.amount,maximum),1,maximum)}</div>`;
    case 'alliance':
     return number('diplomacy-duration',text(`同盟期間（最多 ${current.max_turns} 旬／24 個月）`,`同盟期間（最大 ${current.max_turns} 旬／24か月）`),
      bounded(draft.duration,current.max_turns,1),1,current.max_turns);
    case 'return_captives':
     return field('diplomacy-prisoner',text('請求歸還的武將','返還を求める武将'),prisoner?.id,captives.map(row=>[row.id,translate(row.name)]));
    case 'request_attack':
     return field('diplomacy-attack-city',text('請求攻擊的城池','攻撃を要請する都市'),attackCity,attackCities.map(id=>[id,translate(cityName(id))]));
    default:return '';
   }
  }
  function render(){
   if(!active||!validCampaign()||active.identity!==identity())return;
   const hadDialog=showing();
   const focused=hadDialog?doc?.activeElement?.id:null,scroll=hadDialog?dialog.scrollTop:0;
   const relationsOpen=hadDialog&&dialog.querySelector('[data-diplomacy-relations]')?.open;
   const row=selection(),{current,draft,city,target,envoys,envoy}=row;
   const action=actions[draft.action],allowed=target?.actions?.[draft.action]===true;
   const feedback=active.result==='done'?text('外交指令已執行。詳情請查看戰報。','外交指令を実行しました。詳しい結果は報告を確認してください。'):
    active.result==='blocked'?text('外交指令未執行。','外交指令は実行されませんでした。'):'';
   const body=`<section data-diplomacy-dialog data-l10n-native="${locale()}">
    ${relations(current.targets)}
    ${target?`<p class="small" data-diplomacy-stage="${escape(target.stage)}">${text('外交感情','外交感情')} · <strong>${escape(stage(target))}</strong>　${text('同盟','同盟')} · ${escape(alliance(target))}</p>`:''}
    <div class="diplomacy-fields">
     ${field('diplomacy-target',text('交涉勢力','交渉相手'),target?.id,current.targets.map(row=>[row.id,translate(factionName(row.id))]))}
     ${field('diplomacy-action',text('外交指令','外交指令'),draft.action,Object.entries(actions).map(([id,item])=>[id,text(...item.name)]))}
     ${field('diplomacy-city',text('派出城池','派遣元の都市'),city?.id,current.cities.map(row=>[row.id,translate(cityName(row.id))]))}
     ${field('diplomacy-envoy',text('使節武將','使者の武将'),envoy?.id,envoys.map(row=>[row.id,envoyLabel(row)]))}
    </div>
    ${extra(row)}
    <p class="small">${escape(text(...action.note))}</p>
    ${!allowed&&target?`<p class="small" role="status">${unavailable()}</p>`:''}
    ${!envoy&&city?`<p class="small" role="status">${text('這座城池目前沒有可派出的使節。','この都市には派遣できる使者がいません。')}</p>`:''}
    ${books?.html(getView(),{kind:'diplomacy',locale:locale()})||''}
    ${feedback?`<p class="small" role="status">${escape(feedback)}</p>`:''}
   </section>`;
   openDialog('外交',body,`<button type="button" data-cancel>${native(text('關閉','閉じる'))}</button><button type="button" id="diplomacy-submit" class="primary" ${usable(row)?'':'disabled'}>${native(text(...action.name))}</button>`);
   if(!showing())return;
   const relationsElement=dialog.querySelector('[data-diplomacy-relations]');
   if(relationsElement)relationsElement.open=!!relationsOpen;
   for(const [id,key] of [['target','target'],['action','action'],['city','city'],['envoy','envoy'],['resource','resource'],['prisoner','prisoner'],['attack-city','attack_city']]){
    const input=query('diplomacy-'+id);
    if(input)input.onchange=()=>{draft[key]=input.value;active.result=null;render();};
   }
   for(const [key,min,max] of [['amount',0,row.maximum],['duration',1,current.max_turns]]){
    const input=query('diplomacy-'+key);
    if(!input)continue;
    input.oninput=()=>{
     if(Number(input.value)>max)input.value=String(max);
     draft[key]=input.value;
     query('diplomacy-submit').disabled=!usable(selection());
    };
    input.onblur=()=>{draft[key]=bounded(input.value,max,min);input.value=String(draft[key]);};
   }
   query('diplomacy-submit').onclick=submit;
   i18n?.apply?.();
   if(focused)query(focused)?.focus?.({preventScroll:true});
   dialog.scrollTop=scroll;
  }
  async function submit(){
   if(!showing()||!canOpen()||active.identity!==identity())return false;
   const row=selection(),draft=payload(row);
   if(!draft||!usable(row))return false;
   const token=active;
   pending=true;
   query('diplomacy-submit').disabled=true;
   let done=false;
   try{done=await command('diplomacy',draft)===true;}catch{}finally{pending=false;}
   if(active===token&&showing()&&active.identity===identity()){
    active.result=done?'done':'blocked';
    render();
   }
   return done;
  }
  function open(){
   if(!canOpen()||pending)return false;
   active={identity:identity(),draft:{action:'goodwill',resource:'gold',amount:1,duration:data().max_turns}};
   render();
   return showing();
  }
  const refresh=()=>{if(showing()&&!pending&&!isBusy())render();};
  doc?.addEventListener?.('game-language-change',refresh);
  return {open,canOpen,dispose(){active=null;doc?.removeEventListener?.('game-language-change',refresh);}};
 }
 const api=Object.freeze({create,actionName});
 if(typeof module!=='undefined'&&module.exports)module.exports=api;
 if(root)root.GameDiplomacy=api;
})(typeof window!=='undefined'?window:globalThis);
