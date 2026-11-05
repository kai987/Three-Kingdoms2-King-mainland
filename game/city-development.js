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
  return `<dl class="development-stats" data-city-development="${esc(id)}">${[
   [choose(locale,'土地','土地'),c.land,999],[choose(locale,'產業','産業'),c.industry,999],
   [choose(locale,'人口','人口'),c.population,999900],[choose(locale,'統治度','統治度'),c.governance,100]
  ].map(([k,v,cap])=>`<div><dt>${k}</dt><dd>${esc(v)}<small> / ${cap}</small></dd></div>`).join('')}</dl>`;
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
   const ready=!pending&&!isBusy()&&!isPreview()&&v.game.phase==='city'&&q?.eligible===true&&cash>=q.gold_max&&root.GameCommandBooks?.can(v,token.kind)===true;
   openDialog(text('城池開發','都市の開発')+' · '+i18n.t(cityName(token.city)),`<div data-development-dialog>${summary(v,token.city,locale())}<label class="field">${text('執行武將（知優先）','実行武将（知を優先）')}<select id="development-actor">${available.map(id=>`<option value="${esc(id)}" ${String(id)===String(token.actor)?'selected':''}>${esc(i18n.t(name(id)))} · ${esc(root.GameFacilities?.attributes(v,id,locale())||'')}</option>`).join('')||`<option value="">${text('無可用武將','行動できる武将がいません')}</option>`}</select></label><label class="field">${text('開發項目','開発項目')}<select id="development-kind">${Object.entries(kinds).map(([k,labels])=>`<option value="${k}" ${k===token.kind?'selected':''}>${choose(locale(),...labels)}</option>`).join('')}</select></label><p id="development-quote" role="status">${text('資金','資金')} ${range(q?.gold_min,q?.gold_max)} · ${text('增幅','上昇量')} ${range(q?.gain_min,q?.gain_max)} · ${text('統治度','統治度')} +${range(q?.governance_gain_min,q?.governance_gain_max)}</p>${root.GameCommandBooks?.html(v,{kind:token.kind,locale:locale()})||''}<p class="small" id="development-boundary">${!q?text('目前無可執行的武將。','現在、実行できる武将がいません。'):!q.eligible?text('已達上限或目前無法開發。','上限に達しているか、現在は開発できません。'):cash<q.gold_max?text('請備妥費用範圍的最高資金。','費用範囲の最大額を用意してください。'):''}</p><details><summary>${text('規則與來源','規則と出典')}</summary><p class="small">${text('三類開發的費用與效果採原版知力公式；實際費用及效果於確認後抽取。人口以百人為單位。115城初值、每月收入與旬制為本作適配。統治低於50有經濟損失風險，與防災分開計算。','三種の開発費用と効果には原版の知力式を使用し、確認後に抽選します。人口の単位は100人です。115都市の初期値・月収・旬制は本作の調整です。統治50未満では防災とは別に経済損失の危険があります。')}</p></details></div>`,`<button data-cancel>${text('返回','戻る')}</button><button id="development-confirm" class="primary" ${ready?'':'disabled'}>${text('確認開發','開発を実行')}</button>`);
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
 const api=Object.freeze({kinds,summary,quote,create});
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.GameCityDevelopment=api;
})(typeof window==='object'?window:globalThis);
