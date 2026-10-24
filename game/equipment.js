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
 function category(value,slot,locale){
  const label=text(locale,slot==='weapon'?'武器分類圖示':'防具分類圖示',slot==='weapon'?'武器の分類アイコン':'防具の分類アイコン');
  return root.GameOriginalUI?.equipment?.(slot,value,{locale,className:'equipment-item-icon'})||
   `<span class="equipment-category-fallback" role="img" aria-label="${label}">${slot==='weapon'?'武':'防'}</span>`;
 }
 function coreStats(value,locale){
  return [['attack_bonus','單挑攻擊','一騎討ちの攻撃',signed],['defense_bonus','防禦','防御',signed],['total_weight','總重量','総重量',shown]].filter(([key])=>Object.prototype.hasOwnProperty.call(value,key)).map(([key,tc,ja,format])=>`<span data-equipment-stat="${key}">${text(locale,tc,ja)}${format(value[key])}</span>`).join('');
 }
 function gear(value,slot,locale,effects){
  const label=slot==='weapon'?text(locale,'武器','武器'):text(locale,'防具','防具');
  const name=escape(named(value,locale)),description=text(locale,'顯示裝備詳細','装備の詳細を表示');
  const tooltip=`<strong class="equipment-tooltip-name">${name}</strong><span data-equipment-item-stat="power">${label}${text(locale,'強度','の強さ')} ${shown(value?.power)}</span><span data-equipment-item-stat="weight">${text(locale,'重量','重さ')} ${shown(value?.weight)}</span><span class="equipment-tooltip-effects">${coreStats(effects,locale)}</span>`;
  return `<button type="button" class="equipment-item" data-equipment-tooltip data-equipment-key="${slot}:${escape(value?.id??'')}" data-equipment-slot="${slot}" data-equipment-item="${escape(value?.id??'')}" data-equipment-locale="${locale}" aria-expanded="false" aria-label="${label}：${name}，${description}">${category(value,slot,locale)}<strong class="equipment-item-name">${name}</strong><template data-equipment-tooltip-content>${tooltip}</template></button>`;
 }
 function item(value,slot,options={}){
  if(!value||!['weapon','armor'].includes(slot))return '';
  return gear(value,slot,language(options.locale),{});
 }
 function render(value,options={}){
  if(!value||typeof value!=='object'||!value.weapon||!value.armor)return '';
  const {bilingual:both=true,compact=false,id=value.runtime_id??value.person_id??''}=options,locale=language(options.locale);
  if(both)return bilingual(next=>render(value,next),{...options,id});
  const scope=value.scope==='initial'?'initial':'current',heading=text(locale,scope==='initial'?'初始裝備':'目前裝備',scope==='initial'?'初期装備':'現在の装備');
  const core=coreStats(value,locale);
  const weight=`${text(locale,'總重量','総重量')}${shown(value.total_weight)} · ${text(locale,'重量造成的攻擊減少','重さによる攻撃の低下')}${shown(value.weight_penalty)} · ${text(locale,'先手基準','先手の基準')}${shown(value.initiative_base)} · ${text(locale,'命中修正','命中補正')}${deduction(value.hit_penalty)}${text(locale,'百分點','ポイント')} · ${text(locale,'回避修正','回避補正')}${deduction(value.evasion_penalty)}${text(locale,'百分點','ポイント')}`;
  const retreat=text(locale,`退卻體力消耗 ${interval(value.retreat_health_min,value.retreat_health_max)}；觸發機率 ${shown(value.retreat_chance)}%。`,`退却時の体力消費 ${interval(value.retreat_health_min,value.retreat_health_max)}、発生確率 ${shown(value.retreat_chance)}%。`);
  const sourceLabels={
   cnblogs_original_equipment_transcription:['初始裝備參考原版公開武將表。','初期装備は原作の公開武将表を参考にしています。'],
   explicit_requested_novel_signature_override:['名將的代表兵器已配置為實際初始裝備；數值與重量依本作裝備規則計算。','名将の代表武器を実際の初期装備として設定し、数値と重さは本作の装備規則で計算します。'],
   'remake_role_default; not_original_equipment':['尚無對應的原版裝備資料，初始裝備採本作職能配置。','対応する原作の装備資料がないため、本作の役割別初期装備を使います。']
  };
  const initial=value.initial?.[locale==='ja'?'note_ja':'note_tc']||sourceLabels[value.initial?.basis]?.[locale==='ja'?1:0];
  return `<div class="equipment-summary${compact?' equipment-summary-compact':''}" data-officer-equipment="${escape(id)}" data-equipment-person="${escape(value.person_id??'')}" data-equipment-scope="${scope}" data-l10n-native="${locale}">${compact?'':`<h3>${heading}</h3>`}<div class="equipment-pair">${gear(value.weapon,'weapon',locale,value)}${gear(value.armor,'armor',locale,value)}</div>${compact?'':`<details class="equipment-details" data-equipment-details><summary>${text(locale,'裝備效果／詳細','装備の効果／詳細')}</summary><p class="equipment-core-stats small" data-equipment-effects>${core}</p><p class="small">${text(locale,'基礎武','基礎武')}${shown(value.base_martial)}</p><p class="small" data-equipment-weight>${weight}</p><p class="small" data-equipment-retreat>${retreat}</p>${initial?`<p class="small equipment-source" data-equipment-initial-note>${escape(initial)}</p>`:''}<p class="small">${text(locale,'裝備修正另行計算，不改寫基礎武、知、德。','装備の補正は別に計算し、基礎の武・知・徳を書き換えません。')}</p></details>`}</div>`;
 }
 function summary(view,id,options={}){return render(row(view,id),{...options,id});}
 function preview(offer,id){return offer?.preview_by_officer?.[String(id)]||null;}
 function comparison(view,id,offer,options={}){
  const value=preview(offer,id),locale=language(options.locale);
  if(options.bilingual!==false)return bilingual(next=>comparison(view,id,offer,next),options);
  if(!value?.before||!value?.after)return `<p class="small equipment-no-preview" data-l10n-native="${locale}">${text(locale,'請選擇武將與裝備，確認引擎提供的效果比較。','武将と装備を選択して、エンジンによる効果比較を確認してください。')}</p>`;
  const fields=[['attack_bonus','單挑攻擊','一騎討ちの攻撃',signed],['defense_bonus','防禦','防御',signed],['total_weight','總重量','総重量',shown],['weight_penalty','重量造成的攻擊減少','重さによる攻撃の低下',shown],['initiative_base','先手基準','先手の基準',shown],['hit_penalty','重量造成的命中減少','重さによる命中の低下',shown],['evasion_penalty','重量造成的回避減少','重さによる回避の低下',shown],['retreat_chance','退卻耗體力機率','退却で体力を使う確率',shown]];
  const lines=fields.map(([key,tc,ja,format])=>`<span data-equipment-compare="${key}">${text(locale,tc,ja)} ${format(value.before[key])} → ${format(value.after[key])}${key==='hit_penalty'||key==='evasion_penalty'?text(locale,'百分點','ポイント'):key==='retreat_chance'?'%':''}</span>`);
  const reason=value[locale==='ja'?'reason_ja':'reason_tc'];
  return `<div class="equipment-comparison" data-equipment-comparison="${escape(id)}" data-equipment-person="${escape(row(view,id)?.person_id??value.before.person_id??'')}" data-equipment-eligible="${value.eligible===true}" data-l10n-native="${locale}"><p><strong>${text(locale,'更換前 → 更換後','交換前 → 交換後')}</strong></p><div class="equipment-comparison-values equipment-comparison-core">${lines.slice(0,3).join('')}</div>${reason?`<p class="small" data-equipment-ineligible>${escape(reason)}</p>`:''}<details class="equipment-details" data-equipment-comparison-details><summary>${text(locale,'重量影響／詳細比較','重さの影響／詳細比較')}</summary><div class="equipment-comparison-values">${lines.slice(3).join('')}<span data-equipment-compare="retreat">${text(locale,'退卻體力消耗','退却時の体力消費')} ${interval(value.before.retreat_health_min,value.before.retreat_health_max)} → ${interval(value.after.retreat_health_min,value.after.retreat_health_max)}</span></div></details></div>`;
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
   return `<li data-special-equipment="${escape(value.slot)}:${escape(value.item)}"><span class="equipment-special-heading">${category({...item,id:value.item},value.slot,locale)}<strong>${escape(name)}</strong></span><p>${escape(condition)}</p><p class="small">${value.unique===true?text(locale,'本局唯一 · ','この戦役で1点限り・'):''}${escape(status)}</p></li>`;
  }).join('');
  return `<details class="equipment-guide" data-equipment-guide ${options.open?'open':''} data-l10n-native="${locale}"><summary>${text(locale,'特殊裝備與取得條件','特殊装備と入手条件')}</summary><ul>${rows}</ul></details>`;
 }
 // Position in viewport coordinates, independent of the roster's scroll containers.
 function tooltipPosition(anchor,size,viewport){
  const gap=8,left=viewport.left||0,top=viewport.top||0;
  const width=Math.max(1,viewport.width-2*gap),height=Math.max(1,viewport.height-2*gap);
  const w=Math.min(size.width,width),h=Math.min(size.height,height);
  const below=top+viewport.height-anchor.bottom,above=anchor.top-top;
  const y=below>=h+gap||below>=above?anchor.bottom+gap:anchor.top-h-gap;
  return {left:Math.max(left+gap,Math.min(anchor.left,left+viewport.width-w-gap)),top:Math.max(top+gap,Math.min(y,top+viewport.height-h-gap)),maxWidth:width,maxHeight:height};
 }
 const tooltipBindings=new WeakMap();
 function bindTooltips(doc=root.document){
  if(!doc?.addEventListener)return null;
  if(tooltipBindings.has(doc))return tooltipBindings.get(doc);
  const win=doc.defaultView||root,selector='[data-equipment-tooltip]';
  let active=null,tip=null,mode='',dismissTimer=null,pointerIntent=null;
  const trigger=target=>target?.closest?.(selector)||null;
  const inTopLayer=()=>typeof tip?.showPopover==='function'&&tip.matches(':popover-open');
  const cancelDismiss=()=>{if(dismissTimer!==null){win.clearTimeout(dismissTimer);dismissTimer=null;}};
  function close(){
   cancelDismiss();
   if(active){active.setAttribute('aria-expanded','false');active.removeAttribute('aria-describedby');active.removeAttribute('aria-controls');}
   active=null;mode='';
   if(tip){if(inTopLayer())tip.hidePopover();tip.hidden=true;}
  }
  function viewport(){
   const visual=win.visualViewport;
   return {left:visual?.offsetLeft||0,top:visual?.offsetTop||0,width:visual?.width||win.innerWidth||doc.documentElement.clientWidth,height:visual?.height||win.innerHeight||doc.documentElement.clientHeight};
  }
  function reposition(){
   if(!active||!tip)return;
   if(!active.isConnected||active.closest('[hidden],[aria-hidden="true"]')||!active.getClientRects().length){close();return;}
   const area=viewport(),anchor=active.getBoundingClientRect();
   let visible={left:area.left,top:area.top,right:area.left+area.width,bottom:area.top+area.height};
   for(let parent=active.parentElement;parent&&win.getComputedStyle;parent=parent.parentElement){
    const style=win.getComputedStyle(parent),bounds=parent.getBoundingClientRect();
    if(/auto|scroll|hidden|clip/.test(style.overflowX)){visible.left=Math.max(visible.left,bounds.left);visible.right=Math.min(visible.right,bounds.right);}
    if(/auto|scroll|hidden|clip/.test(style.overflowY)){visible.top=Math.max(visible.top,bounds.top);visible.bottom=Math.min(visible.bottom,bounds.bottom);}
   }
   if(anchor.right<=visible.left||anchor.left>=visible.right||anchor.bottom<=visible.top||anchor.top>=visible.bottom){close();return;}
   tip.style.maxWidth=`${Math.max(1,Math.min(320,area.width-16))}px`;tip.style.maxHeight=`${Math.max(1,area.height-16)}px`;
   const position=tooltipPosition(anchor,tip.getBoundingClientRect(),area);
   tip.style.left=`${position.left}px`;tip.style.top=`${position.top}px`;
  }
  function open(button,nextMode){
   const content=button.querySelector('template[data-equipment-tooltip-content]');
   if(!content||!button.isConnected)return;
   cancelDismiss();
   if(active!==button){close();active=button;}
   mode=nextMode;
   if(!tip){tip=doc.createElement('div');tip.id='game-equipment-tooltip';tip.className='equipment-tooltip';tip.setAttribute('role','tooltip');tip.setAttribute('popover','manual');tip.hidden=true;}
   // A modal dialog makes body siblings inert. Keep the portal in its top layer.
   const host=button.closest('dialog[open]')||doc.body;
   if(tip.parentElement!==host){if(inTopLayer())tip.hidePopover();host.appendChild(tip);}
   tip.setAttribute('data-l10n-native',button.getAttribute('data-equipment-locale')||'zh-Hant');
   tip.setAttribute('data-equipment-key',button.getAttribute('data-equipment-key')||'');
   tip.replaceChildren(content.content.cloneNode(true));tip.hidden=false;
   if(tip.showPopover&&!inTopLayer())tip.showPopover();
   button.setAttribute('aria-expanded','true');button.setAttribute('aria-controls',tip.id);button.setAttribute('aria-describedby',tip.id);
   reposition();
  }
  function delayedClose(){cancelDismiss();dismissTimer=win.setTimeout(()=>{dismissTimer=null;if(mode==='hover')close();},120);}
  function pointerOver(event){
   if(event.pointerType==='touch')return;
   if(tip?.contains(event.target)){cancelDismiss();return;}
   const button=trigger(event.target);
   if(button&&!button.contains(event.relatedTarget)){if(active===button&&mode!=='hover')cancelDismiss();else open(button,'hover');}
  }
  function pointerOut(event){
   if(mode!=='hover'||!active)return;
   if(active.contains(event.relatedTarget)||tip?.contains(event.relatedTarget))return;
   if(active.contains(event.target)||tip?.contains(event.target))delayedClose();
  }
  function pointerDown(event){
   pointerIntent=trigger(event.target);
   if(active&&!active.contains(event.target)&&!tip?.contains(event.target))close();
  }
  function click(event){
   const button=trigger(event.target);
   if(!button){if(active&&!tip?.contains(event.target))close();pointerIntent=null;return;}
   event.preventDefault();event.stopPropagation();
   if(active===button&&mode==='pinned'&&event.detail!==0)close();else open(button,'pinned');
   pointerIntent=null;
  }
  function focusIn(event){const button=trigger(event.target);if(button&&pointerIntent!==button)open(button,'focus');}
  function focusOut(event){if(active?.contains(event.target)&&!active.contains(event.relatedTarget)&&!tip?.contains(event.relatedTarget))close();}
  function keyDown(event){
   if(event.key==='Escape'&&active){event.preventDefault();event.stopPropagation();close();return;}
   const button=trigger(event.target);
   if(button&&(event.key==='Enter'||event.key===' ')){event.preventDefault();event.stopPropagation();open(button,'pinned');}
  }
  function dialogClosed(event){if(active?.closest('dialog')===event.target)close();}
  const listeners=[['pointerover',pointerOver],['pointerout',pointerOut],['pointerdown',pointerDown],['pointerup',()=>{pointerIntent=null;}],['pointercancel',()=>{pointerIntent=null;}],['click',click,true],['focusin',focusIn],['focusout',focusOut],['keydown',keyDown,true],['scroll',reposition,true],['close',dialogClosed,true],['game-language-change',close]];
  for(const [type,listener,capture=false]of listeners)doc.addEventListener(type,listener,capture);
  win.addEventListener?.('resize',reposition);win.visualViewport?.addEventListener('resize',reposition);win.visualViewport?.addEventListener('scroll',reposition);
  const observer=win.MutationObserver?new win.MutationObserver(records=>{
   if(!active)return;
   if(!active.isConnected||records.some(record=>(record.type==='attributes'&&((record.attributeName==='lang'&&record.target===doc.documentElement)||record.target===active||record.target.contains?.(active)))||(record.type==='childList'&&active.contains(record.target))))close();
  }):null;
  observer?.observe(doc.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','aria-hidden','open','lang','data-equipment-key','data-equipment-locale']});
  const binding=Object.freeze({close,reposition,destroy(){
   close();observer?.disconnect();tip?.remove();
   for(const [type,listener,capture=false]of listeners)doc.removeEventListener(type,listener,capture);
   win.removeEventListener?.('resize',reposition);win.visualViewport?.removeEventListener('resize',reposition);win.visualViewport?.removeEventListener('scroll',reposition);tooltipBindings.delete(doc);
  }});
  tooltipBindings.set(doc,binding);return binding;
 }
 if(root.document?.addEventListener)bindTooltips(root.document);
 return Object.freeze({data,row,item,render,summary,preview,comparison,acquisition,shown,signed,interval,tooltipPosition,bindTooltips});
});
