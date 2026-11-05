/* Read-only effect forecasts supplied by the same campaign rules as execution. */
(function(root){
 'use strict';
 const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const choose=(locale,tc,ja)=>locale==='ja'?ja:tc;
 const integer=(n,max)=>Number.isSafeInteger(n)&&n>=0&&n<=max;
 function forecast(view,actor,target,tid){
  const q=view?.catalog?.battle_tactical?.actors?.[String(actor)]?.tactic_previews?.[String(tid)]?.[String(target)];
  if(q?.schema!=='tk2-tactic-effect-preview-v1'||q.tactic!==Number(tid)||!integer(q.success_percent,100))return null;
  if(q.tactic===5&&(!['attackers','defenders'].includes(q.affected_side)||!['grain_before','grain_loss_min','grain_loss_max'].every(k=>integer(q[k],100000000))||q.grain_loss_min>q.grain_loss_max||q.grain_loss_max>q.grain_before))return null;
  if(q.tactic===8&&(!integer(q.target_loyalty,100)||typeof q.guaranteed_failure!=='boolean'||q.guaranteed_failure!==(q.target_loyalty>=71)||q.guaranteed_failure!==(q.success_percent===0)))return null;
  return q.tactic===5||q.tactic===8?q:null;
 }
 function summary(view,actor,target,tid,{locale=null}={}){
  const q=forecast(view,actor,target,tid);if(!q)return '';
  if(!locale)return ['zh-Hant','ja'].map(language=>`<div data-locale-only="${language}" data-l10n-native="${language}">${summary(view,actor,target,tid,{locale:language})}</div>`).join('');
  const cost=view?.catalog?.battle_tactical?.tactic_costs?.[Number(tid)];
  let message;
  if(q.tactic===5)message=choose(locale,`成功率 ${q.success_percent}%（沿用本作成功判定）。敵軍隨軍糧 ${q.grain_before}；成功時燒毀 ${q.grain_loss_min}–${q.grain_loss_max}。不影響城內庫存。`,`成功率 ${q.success_percent}%（成功判定は本作の方式）。敵軍の携行兵糧 ${q.grain_before}。成功時は ${q.grain_loss_min}–${q.grain_loss_max} を焼失させます。都市の備蓄は減りません。`);
  else message=q.guaranteed_failure?choose(locale,`成功率 0%。目標忠誠 ${q.target_loyalty}：原作規則中，忠誠71以上必定失敗；執行仍消耗${integer(cost,60)?cost:'—'}機動力。`,`成功率 0%。対象の忠誠 ${q.target_loyalty}。原作の規則では忠誠71以上は必ず失敗します。実行すると機動力${integer(cost,60)?cost:'—'}を消費します。`):choose(locale,`成功率 ${q.success_percent}%。目標忠誠 ${q.target_loyalty}；知、德與雙方經驗等級共同影響成功率。`,`成功率 ${q.success_percent}%。対象の忠誠 ${q.target_loyalty}。知・徳と双方の経験等級が成功率に影響します。`);
  return `<p class="small tactic-effect-forecast" data-tactic-effect-forecast="${q.tactic}" data-tactic-success="${q.success_percent}" data-l10n-native="${escape(locale)}">${escape(message)}</p>`;
 }
 const api=Object.freeze({forecast,summary});
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.GameTacticEffects=api;
})(typeof window==='object'?window:globalThis);
