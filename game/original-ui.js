/* Original capture UI plus separately identified remake equipment icons. Read-only. */
(function(root,factory){
 'use strict';
 const api=factory(root);
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root)root.GameOriginalUI=api;
})(typeof window==='object'?window:globalThis,function(root){
 'use strict';
 const ICONS=Object.freeze({
  'facility-armory':['武器屋入口圖示','武器屋の入口アイコン'],
  'facility-hospital':['醫館入口圖示','医館の入口アイコン'],
  'facility-market':['市場入口圖示','市場の入口アイコン'],
  'facility-school':['學問所入口圖示','学問所の入口アイコン'],
  'command-city':['城政命令圖示','都市の命令アイコン'],
  'command-army':['軍務命令圖示','軍務の命令アイコン'],
  'command-warehouse':['倉庫命令圖示','倉庫の命令アイコン'],
  'command-town':['町設施命令圖示','町の施設の命令アイコン'],
  'equipment-weapon-category':['武器分類圖示','武器の分類アイコン'],
  'equipment-armor-category':['防具分類圖示','防具の分類アイコン']
 });
 const SCENES=Object.freeze({
  armory:['event-armory-interior','武具店插圖','武具店の挿絵'],
  market:['event-market-interior','商人交易插圖','商人取引の挿絵'],
  sortie:['event-sortie','騎將出陣插圖','騎将の出陣の挿絵']
 });
 const failed=new Set(),doc=root.document;
 const itemArt=id=>/^equipment-(weapon-(?:[0-9]|1[0-9]|2[0-8])|armor-[0-7])$/.test(id);
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const language=value=>value==='ja'?'ja':'zh-Hant';
 const text=(locale,tc,ja)=>locale==='ja'?ja:tc;
 const classes=value=>typeof value==='string'?value.split(/\s+/).filter(part=>/^[A-Za-z_][A-Za-z0-9_-]{0,79}$/.test(part)).slice(0,8).join(' '):'';
 function path(id){
  const canonical=itemArt(id)?`/assets/equipment-icons/${id.slice('equipment-'.length)}.png`:`/assets/original-ui/${id}-4x.png`;
  if(typeof root.GamePaths?.asset==='function')return root.GamePaths.asset(canonical);
  try{return doc?.baseURI?new URL(canonical.slice(1),doc.baseURI).href:canonical;}catch{return canonical;}
 }
 function image(id,kind,alt,options={},extra=''){
  if(failed.has(id))return '';
  const locale=language(options.locale),className=classes(options.className),decorative=options.decorative===true;
  return `<img class="original-ui-image original-ui-${kind}${className?' '+className:''}" data-original-ui="${id}" data-original-ui-kind="${kind}" data-original-ui-locale="${locale}" data-original-ui-provenance="${itemArt(id)?'remake-equipment-icon':'original-capture-derived'}" src="${escape(path(id))}" alt="${decorative?'':escape(alt)}"${decorative?' aria-hidden="true"':''}${extra} decoding="async" draggable="false">`;
 }
 function icon(id,options={}){
  if(typeof id!=='string'||!Object.hasOwn(ICONS,id))return '';
  const locale=language(options.locale),label=typeof options.label==='string'&&options.label.trim()?options.label:ICONS[id][locale==='ja'?1:0];
  return image(id,'icon',text(locale,`原版${label}`,`原版の${label}`),options);
 }
 function scene(id,options={}){
  if(typeof id!=='string'||!Object.hasOwn(SCENES,id))return '';
  const locale=language(options.locale),[asset,tc,ja]=SCENES[id];
  return image(asset,'scene',text(locale,`原版${tc}`,`原版の${ja}`),options);
 }
 function equipment(slot,item,options={}){
  if(!['weapon','armor'].includes(slot)||!item||typeof item!=='object'||Array.isArray(item)||!Number.isSafeInteger(item.id)||item.id<0||item.id>(slot==='weapon'?28:7))return '';
  const locale=language(options.locale),name=item[locale==='ja'?'name_ja':'name_tc']||item.name_tc||item.name_ja||'',category=slot==='weapon'?text(locale,'武器','武器'):text(locale,'防具','防具');
  const alt=text(locale,`${name?name+'・':''}${category}像素圖`,`${name?name+'・':''}${category}のピクセルアイコン`);
  return image(`equipment-${slot}-${item.id}`,'icon',alt,options,` data-equipment-key="${slot}:${item.id}" data-equipment-slot="${slot}" data-equipment-item="${item.id}"`);
 }
 function imageError(event){
  const node=event?.target,id=node?.getAttribute?.('data-original-ui');
  if(!id||node.getAttribute('src')!==path(id)||!Object.hasOwn(ICONS,id)&&!Object.values(SCENES).some(row=>row[0]===id)&&!itemArt(id))return;
  failed.add(id);
  const replacement=doc?.createElement?.('span');if(!replacement)return;
  const locale=language(node.getAttribute('data-original-ui-locale')),message=itemArt(id)?text(locale,'圖示載入失敗','アイコンを読み込めませんでした'):text(locale,'原圖載入失敗','原図を読み込めませんでした');
  replacement.className=(node.className||'')+' original-ui-missing';replacement.textContent=message;
  replacement.setAttribute('role','img');replacement.setAttribute('aria-label',`${node.getAttribute('alt')||''} · ${message}`);
  node.replaceWith?.(replacement);
 }
 doc?.addEventListener?.('error',imageError,true);
 return Object.freeze({icon,scene,equipment});
});
