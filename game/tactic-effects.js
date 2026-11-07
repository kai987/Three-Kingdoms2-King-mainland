/* Read-only effect forecasts supplied by the same campaign rules as execution. */
(function(root){
 'use strict';
 const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const choose=(locale,tc,ja)=>locale==='ja'?ja:tc;
 const integer=(n,max)=>Number.isSafeInteger(n)&&n>=0&&n<=max;
 function forecast(view,actor,target,tid){
  const q=view?.catalog?.battle_tactical?.actors?.[String(actor)]?.tactic_previews?.[String(tid)]?.[String(target)];
  if(q?.schema!=='tk2-tactic-effect-preview-v1'||q.tactic!==Number(tid)||!integer(q.success_percent,100))return null;
  if(!integer(q.tactic,15)||q.tactic===11)return null;
  if(q.success_gate!==undefined){
   if(q.tactic===8||!['shared_native','legacy_nonspatial'].includes(q.success_gate))return null;
   if(q.success_gate==='shared_native'&&(!integer(q.distance,30)||q.shared_bonus!==10||q.success_percent!==(q.distance>=6?0:Math.max(5,Math.min(95,q.success_percent)))))return null;
   if(q.success_gate==='legacy_nonspatial'&&(q.distance!==undefined||q.shared_bonus!==undefined))return null;
  }
  if(q.tactic===2&&(q.condition!=='phantom'||![2,3].includes(q.condition_count)||!integer(q.target_count,9)))return null;
  if(q.tactic===15&&(q.condition!=='qimen'||![5,6].includes(q.count_min)||q.count_max!==q.count_min+3||q.daily_loss_min!==80||q.daily_loss_max!==150||typeof q.source_present!=='boolean'))return null;
  if(q.tactic===10&&(q.condition!=='chain'||![3,4].includes(q.count_min)||q.count_max!==q.count_min+1||!Array.isArray(q.target_ids)||q.target_ids.length<2||q.target_ids.length>20||q.target_ids.some(id=>typeof id!=='string'||!id||id.length>128)||new Set(q.target_ids).size!==q.target_ids.length))return null;
  if(q.tactic===5&&(!['attackers','defenders'].includes(q.affected_side)||!['grain_before','grain_loss_min','grain_loss_max'].every(k=>integer(q[k],100000000))||q.grain_loss_min>q.grain_loss_max||q.grain_loss_max>q.grain_before))return null;
  if(q.tactic===8&&(!integer(q.target_loyalty,100)||typeof q.guaranteed_failure!=='boolean'||q.guaranteed_failure!==(q.target_loyalty>=71)||q.guaranteed_failure!==(q.success_percent===0)))return null;
  return [2,5,8,10,15].includes(q.tactic)||q.success_gate!==undefined?q:null;
 }
 function rate(q,locale){return q.success_gate==='shared_native'?choose(locale,`成功率 ${q.success_percent}%（原版距離、知與經驗等級；玩家／AI共用）。`,`成功率 ${q.success_percent}%（原作の距離・知・経験等級。プレイヤー／AI共通）。`):choose(locale,`成功率 ${q.success_percent}%（沿用本作成功判定）。`,`成功率 ${q.success_percent}%（成功判定は本作の方式）。`);}
 function summary(view,actor,target,tid,{locale=null}={}){
  const q=forecast(view,actor,target,tid),selected=Number(tid)===11?actor:target;
  const condition=view?.game?.battle?.extended?.conditions?.units?.[String(selected)],kind=condition?.kind,n=condition?.remaining;
  const count=['phantom','chain','qimen'].includes(kind)&&integer(n,{phantom:3,chain:5,qimen:9}[kind])&&n>0&&integer(Number(tid),15)?n:0;if(!q&&!count)return '';
  if(!locale)return ['zh-Hant','ja'].map(language=>`<div data-locale-only="${language}" data-l10n-native="${language}">${summary(view,actor,target,tid,{locale:language})}</div>`).join('');
  const cost=view?.catalog?.battle_tactical?.tactic_costs?.[Number(tid)];
  let message='';
  if(q?.tactic===2)message=rate(q,locale)+choose(locale,`成功時限制目標移動，施放時計數 ${q.condition_count}；按完整日界消退，仍可攻擊或施計。這是剩餘掃描次數，不是固定無法行動回合數。`,`成功すると移動を封鎖し、付与時カウントは ${q.condition_count}。日界ごとに減少し、攻撃や計略は可能です。固定の行動不能ターン数ではありません。`);
  else if(q?.tactic===15)message=rate(q,locale)+choose(locale,`成功後限制敵隊移動，施放時計數 ${q.count_min}–${q.count_max}。諸葛亮在場時，每次日界減1並損兵80–150，最後一次也損兵；不給本隊護盾，仍可攻擊或施計。${q.source_present?'':'目前諸葛亮不在場，倒數與損兵暫停。'}`,`成功すると敵の移動を封鎖し、付与時カウント ${q.count_min}–${q.count_max}。諸葛亮が戦場にいる間、日界に1減り80–150兵を失い、最後の走査も損兵します。自軍の盾ではなく、攻撃や計略は可能です。${q.source_present?'':'現在諸葛亮は不在のため、時計と損兵は停止します。'}`);
  else if(q?.tactic===10)message=rate(q,locale)+choose(locale,`成功後依連通順序，為 ${q.target_ids.length} 支水上敵隊各自抽取計數 ${q.count_min}–${q.count_max}。陸地敵隊只傳遞連通、不受效果；限制移動，仍可攻擊或施計。按日界消退，不是固定無法行動回合數。`,`成功後、接続順に水上の敵 ${q.target_ids.length} 隊へ個別にカウント ${q.count_min}–${q.count_max} を抽選。陸上の敵は接続を伝えるだけです。移動のみ封鎖し、攻撃や計略は可能。日界で減少し、固定の行動不能ターン数ではありません。`);
  else if(q?.tactic===5)message=rate(q,locale)+choose(locale,`敵軍隨軍糧 ${q.grain_before}；成功時燒毀 ${q.grain_loss_min}–${q.grain_loss_max}。不影響城內庫存。`,`敵軍の携行兵糧 ${q.grain_before}。成功時は ${q.grain_loss_min}–${q.grain_loss_max} を焼失させます。都市の備蓄は減りません。`);
  else if(q?.tactic===8)message=q.guaranteed_failure?choose(locale,`成功率 0%。目標忠誠 ${q.target_loyalty}：原作規則中，忠誠71以上必定失敗；執行仍消耗${integer(cost,60)?cost:'—'}機動力。`,`成功率 0%。対象の忠誠 ${q.target_loyalty}。原作の規則では忠誠71以上は必ず失敗します。実行すると機動力${integer(cost,60)?cost:'—'}を消費します。`):choose(locale,`成功率 ${q.success_percent}%。目標忠誠 ${q.target_loyalty}；知、德與雙方經驗等級共同影響成功率。`,`成功率 ${q.success_percent}%。対象の忠誠 ${q.target_loyalty}。知・徳と双方の経験等級が成功率に影響します。`);
  else if(q)message=rate(q,locale)+(q.success_gate==='shared_native'?choose(locale,`距離 ${q.distance} 格；預覽不抽取結果。`,`距離 ${q.distance}マス。表示では抽選しません。`):'');
  const result=q?`<p class="small tactic-effect-forecast" data-tactic-effect-forecast="${q.tactic}" data-tactic-success="${q.success_percent}" data-l10n-native="${escape(locale)}">${escape(message)}</p>`:'';
  const label=kind==='qimen'?['奇門遁甲','奇門遁甲']:kind==='chain'?['連環','連環']:['虛兵','虚兵'];
  const warning=choose(locale,`確認施計會先解除對象的${label[0]}（目前計數${count}），即使本次計略失敗也一樣。`,`計略を確定すると、対象の${label[1]}（現在カウント${count}）を先に解除します。今回の計略が失敗しても解除されます。`);
  return result+(count?`<p class="small" data-${kind}-clear-preview="${count}" data-l10n-native="${escape(locale)}">${escape(warning)}</p>`:'');
 }
 const api=Object.freeze({forecast,summary});
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.GameTacticEffects=api;
})(typeof window==='object'?window:globalThis);
