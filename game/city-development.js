/* Original three development commands. Quotes never consume campaign RNG. */
(function(root){
 'use strict';
 const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const kinds=Object.freeze({develop_land:['開墾土地','土地の開墾'],develop_industry:['開發產業','産業の開発'],develop_population:['町開發（人口）','町の開発（人口）']});
 const choose=(locale,tc,ja)=>locale==='ja'?ja:tc;
 const row=(v,id)=>v?.catalog?.city_development?.cities?.[id];
 const range=(a,b)=>Number.isFinite(a)&&Number.isFinite(b)?a===b?String(a):`${a}–${b}`:'—';
 function summary(view,id,locale=null){
  const c=row(view,id);if(!c)return '';
  if(!locale)return ['zh-Hant','ja'].map(l=>`<div data-locale-only="${l}" data-l10n-native="${l}">${summary(view,id,l)}</div>`).join('');
  const populationLimit=view.catalog.city_development.limits?.population??1999999;
  return `<dl class="development-stats" data-city-development="${esc(id)}">${[
   [choose(locale,'土地','土地'),c.land,999],[choose(locale,'產業','産業'),c.industry,999],
   [choose(locale,'人口','人口'),c.population,populationLimit],[choose(locale,'統治度','統治度'),c.governance,100]
  ].map(([k,v,cap])=>`<div><dt>${k}</dt><dd>${esc(v)}<small> / ${cap}</small></dd></div>`).join('')}</dl>`;
 }
 function agriculture(detail){
  const number=value=>esc(value),signed=value=>number(value>0?'+'.concat(value):value);
  const rate=value=>number(value)+'%',times=value=>number(value.toFixed(3))+'×';
  const render=locale=>{
   const field=(tc,ja,value,key)=>'<div><dt>'+choose(locale,tc,ja)+'</dt><dd data-agriculture-'+key+'>'+value+'</dd></div>';
   const stage=['前期','中期','後期'][detail.land_stage-1];
   return '<details data-locale-only="'+locale+'" data-l10n-native="'+locale+'" data-city-agriculture><summary>'+choose(locale,'農業與月收支明細','農業と月間収支の内訳')+'</summary><dl class="development-stats">'+
    field('居民人口','住民人口',number(detail.population),'population')+
    field('町等級','町の段階',number(detail.town),'town')+
    field('計入產糧人口','生産対象人口',number(detail.effective_population)+' / '+number(detail.population_cap),'effective-population')+
    field('人口產糧倍率','人口の収穫倍率',times(detail.population_multiplier),'population-multiplier')+
    field('町產糧加成','町の収穫補正','+'+rate(detail.town_bonus_percent),'town-bonus')+
    field('土地與開墾階段','土地・開墾段階',number(detail.land)+' · '+stage,'land-stage')+
    field('土地開發倍率','土地の収穫倍率',times(detail.land_multiplier),'land-multiplier')+
    field('稅率','税率',rate(detail.tax_rate),'tax')+
    field('災害損傷','災害損傷',number(detail.damage)+'/50','damage')+
    field('常規月產糧','月間の通常収穫',number(detail.regular_grain),'production')+
    field('民政官累計加成','民政官の累積補正','+'+number(detail.civil_bonus),'civil-bonus')+
    field('居民月耗糧','住民の月間消費',number(detail.civilian_grain)+' ('+rate(detail.resident_rate_percent)+')','civilian')+
    field('現役兵月耗糧','現役兵の月間消費',number(detail.active_grain),'active')+
    field('預備兵月耗糧','予備兵の月間消費',number(detail.reserve_grain),'reserve')+
    field('應付金糧月俸','月俸の金・兵糧',number(detail.wage_gold)+' / '+number(detail.wage_grain),'payroll')+
    field('月淨糧（含月俸）','兵糧月間収支（俸給込み）',signed(detail.net_grain),'net')+
    '</dl></details>';
  };
  return ['zh-Hant','ja'].map(render).join('');
 }
 function quote(view,id,actor,kind){return row(view,id)?.actor_quotes?.[String(actor)]?.[kind]||null;}
 function create({getView,cityName,openDialog,command,dialog,i18n,isBusy=()=>false,isPreview=()=>false}){
  let active=null,pending=false;
  const locale=()=>i18n.locale==='ja'?'ja':'zh-Hant',text=(tc,ja)=>choose(locale(),tc,ja);
  const query=s=>dialog.querySelector(s);
  const identity=v=>JSON.stringify([v?.catalog?.scenario_id,v?.game?.player,v?.game?.seed,v?.game?.turn]);
  const valid=token=>active===token&&dialog.open&&!!query('[data-development-dialog]')&&identity(getView())===token.identity&&getView()?.game?.cities?.[token.city]?.owner===token.owner;
  const actors=()=>root.GameFacilities?.sortActors(row(getView(),active.city)?.eligible_actors,getView())||row(getView(),active.city)?.eligible_actors||[];
  const name=id=>getView()?.catalog?.names?.[String(id)]||String(id);
  function readyNow(token){const v=getView(),q=quote(v,token.city,token.actor,token.kind);return !pending&&!isBusy()&&!isPreview()&&v?.game?.phase==='city'&&q?.eligible===true&&v.game.cities[token.city]?.gold>=q.gold_max&&actors().some(id=>String(id)===String(token.actor))&&root.GameCommandBooks?.can(v,token.kind)===true;}
  function render(){
   if(!active)return;
   const token=active,v=getView(),c=row(v,token.city);if(!c)return;
   const available=actors();if(!available.some(id=>String(id)===String(token.actor)))token.actor=available[0]??null;
   const q=quote(v,token.city,token.actor,token.kind),cash=v.game.cities[token.city].gold;
   const governorBonus=Number.isInteger(q?.governor_bonus_percent)?'+'+q.governor_bonus_percent+'%':'—';
   const ready=!pending&&!isBusy()&&!isPreview()&&v.game.phase==='city'&&q?.eligible===true&&cash>=q.gold_max&&root.GameCommandBooks?.can(v,token.kind)===true;
   openDialog(text('城池開發','都市の開発')+' · '+i18n.t(cityName(token.city)),`<div data-development-dialog>${summary(v,token.city,locale())}<label class="field">${text('執行武將（知優先）','実行武将（知を優先）')}<select id="development-actor">${available.map(id=>`<option value="${esc(id)}" ${String(id)===String(token.actor)?'selected':''}>${esc(i18n.t(name(id)))} · ${esc(root.GameFacilities?.attributes(v,id,locale())||'')}</option>`).join('')||`<option value="">${text('無可用武將','行動できる武将がいません')}</option>`}</select></label><label class="field">${text('開發項目','開発項目')}<select id="development-kind">${Object.entries(kinds).map(([k,labels])=>`<option value="${k}" ${k===token.kind?'selected':''}>${choose(locale(),...labels)}</option>`).join('')}</select></label><p id="development-quote" role="status">${text('資金','資金')} ${range(q?.gold_min,q?.gold_max)} · <span id="development-governor-bonus">${text('太守加成','太守補正')} ${governorBonus}</span> · <span id="development-gain">${text('加成後增幅','補正後の上昇量')} ${range(q?.gain_min,q?.gain_max)}${q?.development==='population'?'人':''}</span> · ${text('統治度','統治度')} +${range(q?.governance_gain_min,q?.governance_gain_max)}</p>${root.GameCommandBooks?.html(v,{kind:token.kind,locale:locale()})||''}<p class="small" id="development-boundary">${!q?text('目前無可執行的武將。','現在、実行できる武将がいません。'):!q.eligible?text('已達上限或目前無法開發。','上限に達しているか、現在は開発できません。'):cash<q.gold_max?text('請備妥費用範圍的最高資金。','費用範囲の最大額を用意してください。'):''}</p><details><summary>${text('規則與來源','規則と出典')}</summary><p class="small">${text('開發的基礎費用與增幅採原版的執行武將知力公式。太守知力加成計入實際增幅。人口以百人為單位。確認後抽取費用與增幅。各城初值、每月收入與旬制為本作適配。統治低於50有經濟損失風險，與防災分開計算。','開発費用と基本上昇量は実行武将の知を使う原版の式で計算します。実際の上昇量には太守の知による補正が加わります。人口は100人単位です。確認後に費用と上昇量を抽選します。各都市の初期値・月収・旬制は本作の調整です。統治50未満では防災とは別に経済損失の危険があります。')}</p></details></div>`,`<button data-cancel>${text('返回','戻る')}</button><button id="development-confirm" class="primary" ${ready?'':'disabled'}>${text('確認開發','開発を実行')}</button>`);
   query('#development-actor').onchange=e=>{if(pending)return;token.actor=root.GameFacilities?.ref(e.target.value)??e.target.value;render();};
   query('#development-kind').onchange=e=>{if(pending)return;token.kind=e.target.value;render();};
   query('#development-confirm').onclick=async()=>{
    if(!valid(token)||!readyNow(token))return;
    pending=true;query('#development-confirm').disabled=true;
    try{await command(token.kind,{city:token.city,actor:token.actor});}
    finally{pending=false;if(valid(token))render();}
   };
   i18n.apply();
  }
  function open(id){const v=getView();if(isBusy()||isPreview()||v?.game?.phase!=='city'||v.game.cities[id]?.owner!==v.game.player||!row(v,id))return;active={city:id,owner:v.game.player,identity:identity(v),kind:'develop_land',actor:null};render();}
  const language=()=>{if(active&&valid(active)&&!pending)render();};
  root.document?.addEventListener('game-language-change',language);
  return {open,dispose(){active=null;root.document?.removeEventListener('game-language-change',language);}};
 }
 const api=Object.freeze({kinds,summary,agriculture,quote,create});
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.GameCityDevelopment=api;
})(typeof window==='object'?window:globalThis);
