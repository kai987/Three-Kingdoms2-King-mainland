/* Pure estimates; authoritative deductions and ledgers live in the campaign engine. */
(function(root){
 'use strict';
 const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const text=(locale,tc,ja)=>locale==='ja'?ja:tc;
 function departure(view,source,ids,quote,selected=null){
  const rules=view.catalog.battle_supply_rules,people=view.game.officers;
  if(!rules||rules.denominator!==1000||rules.officer_units!==100||rules.budget_days!==30)throw Error('Unsupported battle supply rules');
  const march=root.GameMarchSupply.estimate(people,ids,quote,0,view.game.cities,source.owner);
  const troops=ids.reduce((n,id)=>n+(people[id]?.troops||0),0),daily=troops+100*ids.length;
  const max=Math.max(0,Math.min(rules.limit-march,source.grain-march));
  const initial=Math.min(Math.ceil(daily*rules.budget_days/1000),max);
  const grain=selected===null?initial:Math.max(0,Math.min(max,Number.isFinite(Number(selected))?Math.trunc(Number(selected)):0));
  return {march_grain:march,battle_grain:grain,battle_grain_default:initial,battle_grain_max:max,total_grain:march+grain,daily_grain:Math.ceil(daily/1000),days_supported:daily?Math.floor(grain*1000/daily):0};
 }
 function summary(view,locale='zh-Hant'){
  const ledger=view?.catalog?.battle_supply;if(!ledger)return '';
  const own=view.game.battle.attacker===view.game.player?'attackers':'defenders',enemy=own==='attackers'?'defenders':'attackers';
  return `<div class="battle-provisions" data-battle-provisions>${[own,enemy].map((side,i)=>{const r=ledger.sides?.[side];if(!r)return '';return `<p data-battle-supply-side="${side}" data-battle-grain="${escape(r.grain)}">${text(locale,i?'敵軍':'我軍',i?'敵軍':'自軍')} · ${text(locale,'隨軍糧','携行兵糧')} ${r.initialized?escape(r.grain):'—'} · ${text(locale,'日耗','一日消費')} ${escape(r.daily_grain)} · ${text(locale,'可支撐','維持可能')} ${r.initialized?escape(r.days_supported):'—'}${text(locale,'日','日')}</p>`;}).join('')}<small>${text(locale,'雙方行動結束才結算一天，斷糧時撤退；損兵後按實際兵數計算。','双方の行動終了で一日分を消費し、兵糧不足で撤退します。損耗後の実兵数で計算します。')}</small></div>`;
 }
 const api=Object.freeze({departure,summary});
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.GameBattleSupply=api;
})(typeof window==='object'?window:globalThis);
