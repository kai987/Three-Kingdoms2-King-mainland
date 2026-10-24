/* Read-only equipment presentation. All combat effects and offers come from the engine. */
(function(root,factory){
 'use strict';
 const api=factory(root);
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root)root.GameEquipment=api;
})(typeof window==='object'?window:globalThis,function(root){
 'use strict';
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const language=value=>value==='ja'?'ja':'zh-Hant',text=(locale,tc,ja)=>locale==='ja'?ja:tc;
 const shown=value=>typeof value==='number'&&Number.isFinite(value)?String(value):'—';
 const signed=value=>typeof value==='number'&&Number.isFinite(value)?`${value>0?'+':''}${value}`:'—';
 const deduction=value=>typeof value==='number'&&Number.isFinite(value)?signed(-value):'—';
 const named=(value,locale)=>value?.[locale==='ja'?'name_ja':'name_tc']||value?.name_tc||value?.name_ja||'—';
 const interval=(a,b)=>typeof a==='number'&&typeof b==='number'&&Number.isFinite(a)&&Number.isFinite(b)?a===b?String(a):`${a}–${b}`:'—';
 const data=view=>view?.catalog?.equipment||null;
 const row=(view,id)=>data(view)?.officers?.[String(id)]||view?.catalog?.library?.find(person=>String(person.id)===String(id))?.equipment||null;
 function bilingual(render,options){
  return ['zh-Hant','ja'].map(locale=>`<div data-locale-only="${locale}" data-l10n-native="${locale}">${render({...options,locale,bilingual:false})}</div>`).join('');
 }
 function gear(value,slot,locale){
  return `<span class="equipment-item" data-equipment-slot="${slot}" data-equipment-item="${escape(value?.id??'')}"><strong>${text(locale,slot==='weapon'?'武器':'防具',slot==='weapon'?'武器':'防具')}</strong> ${escape(named(value,locale))} <span class="small">${text(locale,'強度','強さ')}${shown(value?.power)} · ${text(locale,'重量','重さ')}${shown(value?.weight)}</span></span>`;
 }
 function render(value,options={}){
  if(!value||typeof value!=='object'||!value.weapon||!value.armor)return '';
  const {bilingual:both=true,compact=false,id=value.runtime_id??value.person_id??''}=options,locale=language(options.locale);
  if(both)return bilingual(next=>render(value,next),{...options,id});
  const scope=value.scope==='initial'?'initial':'current',heading=text(locale,scope==='initial'?'初始裝備':'目前裝備',scope==='initial'?'初期装備':'現在の装備');
  const core=`${text(locale,'基礎武','基礎武')}${shown(value.base_martial)} · ${text(locale,'單挑攻擊','一騎討ちの攻撃')}${signed(value.attack_bonus)} · ${text(locale,'防禦','防御')}${signed(value.defense_bonus)}`;
  const weight=`${text(locale,'總重量','総重量')}${shown(value.total_weight)} · ${text(locale,'重量造成的攻擊減少','重さによる攻撃の低下')}${shown(value.weight_penalty)} · ${text(locale,'先手基準','先手の基準')}${shown(value.initiative_base)} · ${text(locale,'命中修正','命中補正')}${deduction(value.hit_penalty)}${text(locale,'百分點','ポイント')} · ${text(locale,'回避修正','回避補正')}${deduction(value.evasion_penalty)}${text(locale,'百分點','ポイント')}`;
  const retreat=text(locale,`退卻體力消耗 ${interval(value.retreat_health_min,value.retreat_health_max)}；觸發機率 ${shown(value.retreat_chance)}%。`,`退却時の体力消費 ${interval(value.retreat_health_min,value.retreat_health_max)}、発生確率 ${shown(value.retreat_chance)}%。`);
  const sourceLabels={
   cnblogs_original_equipment_transcription:['初始裝備參考原版公開武將表。','初期装備は原作の公開武将表を参考にしています。'],
   explicit_requested_novel_signature_override:['名將的代表兵器已配置為實際初始裝備；數值與重量依本作裝備規則計算。','名将の代表武器を実際の初期装備として設定し、数値と重さは本作の装備規則で計算します。'],
   'remake_role_default; not_original_equipment':['尚無對應的原版裝備資料，初始裝備採本作職能配置。','対応する原作の装備資料がないため、本作の役割別初期装備を使います。']
  };
  const initial=value.initial?.[locale==='ja'?'note_ja':'note_tc']||sourceLabels[value.initial?.basis]?.[locale==='ja'?1:0];
  return `<div class="equipment-summary${compact?' equipment-summary-compact':''}" data-officer-equipment="${escape(id)}" data-equipment-person="${escape(value.person_id??'')}" data-equipment-scope="${scope}" data-l10n-native="${locale}">${compact?'':`<h3>${heading}</h3>`}<div class="equipment-pair">${gear(value.weapon,'weapon',locale)}${gear(value.armor,'armor',locale)}</div><p class="small" data-equipment-effects>${core}</p>${compact?'':`<p class="small" data-equipment-weight>${weight}</p><p class="small" data-equipment-retreat>${retreat}</p>${initial?`<p class="small" data-equipment-initial-note>${escape(initial)}</p>`:''}<p class="small">${text(locale,'裝備修正另行計算，不改寫基礎武、知、德。','装備の補正は別に計算し、基礎の武・知・徳を書き換えません。')}</p>`}</div>`;
 }
 function summary(view,id,options={}){return render(row(view,id),{...options,id});}
 function preview(offer,id){return offer?.preview_by_officer?.[String(id)]||null;}
 function comparison(view,id,offer,options={}){
  const value=preview(offer,id),locale=language(options.locale);
  if(options.bilingual!==false)return bilingual(next=>comparison(view,id,offer,next),options);
  if(!value?.before||!value?.after)return `<p class="small equipment-no-preview" data-l10n-native="${locale}">${text(locale,'請選擇武將與裝備，確認引擎提供的效果比較。','武将と装備を選択して、エンジンによる効果比較を確認してください。')}</p>`;
  const fields=[['attack_bonus','單挑攻擊','一騎討ちの攻撃',signed],['defense_bonus','防禦','防御',signed],['total_weight','總重量','総重量',shown],['weight_penalty','重量造成的攻擊減少','重さによる攻撃の低下',shown],['initiative_base','先手基準','先手の基準',shown],['hit_penalty','重量造成的命中減少','重さによる命中の低下',shown],['evasion_penalty','重量造成的回避減少','重さによる回避の低下',shown],['retreat_chance','退卻耗體力機率','退却で体力を使う確率',shown]];
  const lines=fields.map(([key,tc,ja,format])=>`<span data-equipment-compare="${key}">${text(locale,tc,ja)} ${format(value.before[key])} → ${format(value.after[key])}${key==='hit_penalty'||key==='evasion_penalty'?text(locale,'百分點','ポイント'):key==='retreat_chance'?'%':''}</span>`).join('');
  const reason=value[locale==='ja'?'reason_ja':'reason_tc'];
  return `<div class="equipment-comparison" data-equipment-comparison="${escape(id)}" data-equipment-eligible="${value.eligible===true}" data-l10n-native="${locale}"><p><strong>${text(locale,'更換前 → 更換後','交換前 → 交換後')}</strong></p><div class="equipment-comparison-values">${lines}<span data-equipment-compare="retreat">${text(locale,'退卻體力消耗','退却時の体力消費')} ${interval(value.before.retreat_health_min,value.before.retreat_health_max)} → ${interval(value.after.retreat_health_min,value.after.retreat_health_max)}</span></div>${reason?`<p class="small" data-equipment-ineligible>${escape(reason)}</p>`:''}</div>`;
 }
 function acquisition(view,options={}){
  const values=data(view)?.special,locale=language(options.locale);
  if(!Array.isArray(values)||!values.length)return '';
  if(options.bilingual!==false)return bilingual(next=>acquisition(view,next),options);
  const rows=values.map(value=>{
   const item=data(view)?.items?.[value.slot]?.find(item=>item.id===value.item),name=named(value.name_tc||value.name_ja?value:item,locale);
   const condition=value[locale==='ja'?'condition_ja':'condition_tc']||text(locale,'條件尚未提供','条件は未表示');
   const holderRef=Object.keys(view?.game?.officers||{}).find(ref=>view.game.officers[ref]?.person_id===value.holder);
   const rawHolder=view?.catalog?.library?.find(person=>person.person_id===value.holder)?.name||
    (holderRef===undefined?null:view?.catalog?.names?.[holderRef]);
   const readableHolder=typeof rawHolder==='string'&&rawHolder!==holderRef&&rawHolder!==value.holder?rawHolder:null;
   const holder=readableHolder&&root.GameI18n?.t?root.GameI18n.t(readableHolder,locale):readableHolder;
   const status=value.claimed===true?text(locale,`本局已取得${holder?' · '+holder:''}`,`この戦役で入手済み${holder?'・'+holder:''}`):text(locale,'本局尚未取得','この戦役では未入手');
   return `<li data-special-equipment="${escape(value.slot)}:${escape(value.item)}"><strong>${escape(name)}</strong><p>${escape(condition)}</p><p class="small">${value.unique===true?text(locale,'本局唯一 · ','この戦役で1点限り・'):''}${escape(status)}</p></li>`;
  }).join('');
  return `<details class="equipment-guide" data-equipment-guide ${options.open?'open':''} data-l10n-native="${locale}"><summary>${text(locale,'特殊裝備與取得條件','特殊装備と入手条件')}</summary><ul>${rows}</ul></details>`;
 }
 return Object.freeze({data,row,render,summary,preview,comparison,acquisition,shown,signed,interval});
});
