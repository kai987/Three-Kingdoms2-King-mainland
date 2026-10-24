/* Current equipment, source previews and shop comparisons are pure engine projections. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const equipment=require('../game/equipment.js'),clone=value=>JSON.parse(JSON.stringify(value));
const sword={id:33,name_tc:'雙股劍',name_ja:'双股剣',power:14,weight:6,family:'sword',appearance:'dual-swords'};
const armor={id:2,name_tc:'兜',name_ja:'兜',power:5,weight:4};
const before={scope:'current',person_id:'liubei',base_martial:79,weapon:sword,armor,attack_bonus:7,defense_bonus:2,total_weight:10,weight_penalty:2,initiative_base:61,hit_penalty:8,evasion_penalty:3,retreat_health_min:1,retreat_health_max:2,retreat_chance:35,initial:{note_tc:'初始裝備依人物ID配置。',note_ja:'初期装備は人物IDに対応します。'},owned:[]};
const after={...clone(before),weapon:{...sword,id:35,name_tc:'新劍',name_ja:'新剣'},attack_bonus:19,defense_bonus:4,total_weight:13,weight_penalty:7,initiative_base:52,hit_penalty:17,evasion_penalty:11,retreat_health_min:2,retreat_health_max:4,retreat_chance:50};
const initial={...clone(before),scope:'initial'};
const view={catalog:{equipment:{schema:'tk2-equipment-v1',items:{weapon:[sword],armor:[armor]},officers:{'8':before},special:[{slot:'weapon',item:33,condition_tc:'指定人物取得，僅此一把。',condition_ja:'指定の人物が入手でき、1振り限りです。',unique:true,claimed:true,holder:'liubei'}]},library:[{id:8,person_id:'liubei',name:'劉備'},{id:9,person_id:'unspawned',name:'未登場',equipment:initial}]}};
const snapshot=JSON.stringify(view);
const tc=equipment.summary(view,8,{bilingual:false});
assert(tc.includes('目前裝備'));assert(tc.includes('雙股劍'));assert(tc.includes('equipment-item-name">兜'));
assert(tc.includes('基礎武79'));assert(tc.includes('單挑攻擊+7'));assert(tc.includes('防禦+2'));
assert(tc.includes('總重量10'));assert(tc.includes('攻擊減少2'));assert(tc.includes('先手基準61'));assert(tc.includes('命中修正-8百分點'));assert(tc.includes('回避修正-3百分點'));assert(tc.includes('退卻體力消耗 1–2'));assert(tc.includes('觸發機率 35%'));
assert(tc.includes('不改寫基礎武、知、德'));assert(tc.includes('初始裝備依人物ID配置'));
const ja=equipment.summary(view,'8',{locale:'ja',bilingual:false});
for(const text of ['現在の装備','双股剣','一騎討ちの攻撃+7','防御+2','命中補正-8ポイント','退却時の体力消費 1–2'])assert(ja.includes(text),text);
assert(!ja.includes('目前裝備'));assert(!ja.includes('雙股劍'));
const both=equipment.summary(view,8);assert(both.includes('data-locale-only="zh-Hant"'));assert(both.includes('data-locale-only="ja"'));
const compact=equipment.summary(view,8,{bilingual:false,compact:true});assert(compact.includes('雙股劍'));assert(!compact.includes('<h3>'));assert(!compact.includes('data-equipment-retreat'));
const unfolded=html=>html.replace(/<details\b[^>]*>[\s\S]*?<\/details>/g,'').replace(/<template\b[^>]*>[\s\S]*?<\/template>/g,'');
for(const html of [tc,ja]){
 const primary=unfolded(html);
 for(const key of ['attack_bonus','defense_bonus','total_weight'])assert(!primary.includes(`data-equipment-stat="${key}"`),'List entries show only the item artwork and name');
 assert(!primary.includes('equipment-slot-label'));assert(!primary.includes('equipment-item-stats'));assert(!primary.includes('data-equipment-item-stat'));
 assert(!primary.includes('data-equipment-weight'));assert(!primary.includes('data-equipment-retreat'));assert(!primary.includes('data-equipment-initial-note'));
 assert(/<details\b[^>]*data-equipment-details[^>]*><summary>[^<]+<\/summary>/.test(html),'Secondary effects and source have a native, labelled disclosure');
 assert(!/<details\b[^>]*data-equipment-details[^>]*\bopen(?:\s|>)/.test(html),'Secondary effects start folded');
}
assert(compact.includes('data-equipment-item-stat="power">武器強度 14'));assert(compact.includes('data-equipment-item-stat="power">防具強度 5'));assert(compact.includes('data-equipment-item-stat="weight">重量 6'));assert(compact.includes('總重量10'));
assert(!unfolded(compact).includes('總重量'));assert(!unfolded(compact).includes('單挑攻擊'));assert(!unfolded(compact).includes('防禦'));
assert.equal((compact.match(/<button\b/g)||[]).length,2);assert.equal((compact.match(/data-equipment-tooltip-content/g)||[]).length,2);
assert(compact.includes('aria-label="武器：雙股劍，顯示裝備詳細"'));assert(compact.includes('aria-expanded="false"'));assert(ja.includes('aria-label="武器：双股剣，装備の詳細を表示"'));
assert(tc.includes('data-officer-equipment="8"'));assert(tc.includes('data-equipment-person="liubei"'));
for(const key of ['weapon:33','armor:2'])assert(tc.includes(`data-equipment-key="${key}"`),'Visible equipment is bound to its real slot and item ID');
const pending=equipment.summary(view,9,{bilingual:false});assert(pending.includes('初始裝備'));assert(pending.includes('data-equipment-scope="initial"'));assert(!pending.includes('目前裝備'));
for(const[basis,tc,ja]of [['cnblogs_original_equipment_transcription','初始裝備參考原版公開武將表','原作の公開武将表'],['explicit_requested_novel_signature_override','代表兵器已配置為實際初始裝備','代表武器を実際の初期装備'],['remake_role_default; not_original_equipment','初始裝備採本作職能配置','役割別初期装備']]){const sourced={...clone(before),initial:{basis}};assert(equipment.render(sourced,{bilingual:false}).includes(tc));assert(equipment.render(sourced,{locale:'ja',bilingual:false}).includes(ja));assert(!equipment.render(sourced).includes(basis),'Implementation codes never become player-facing source labels');}
assert.equal(equipment.summary(view,'missing'),'');assert.equal(equipment.render(null),'');assert.equal(equipment.render({weapon:sword}),'');
const offer={id:35,preview_by_officer:{8:{before,after,eligible:true,reason_tc:'',reason_ja:''}}};
const comparison=equipment.comparison(view,8,offer,{bilingual:false});
for(const text of ['單挑攻擊 +7 → +19','防禦 +2 → +4','總重量 10 → 13','攻擊減少 2 → 7','先手基準 61 → 52','命中減少 8 → 17百分點','回避減少 3 → 11百分點','退卻耗體力機率 35 → 50%','1–2 → 2–4'])assert(comparison.includes(text),text);
assert(comparison.includes('data-equipment-eligible="true"'));
const primaryComparison=unfolded(comparison);
for(const key of ['attack_bonus','defense_bonus','total_weight'])assert(primaryComparison.includes(`data-equipment-compare="${key}"`));
for(const key of ['weight_penalty','initiative_base','hit_penalty','evasion_penalty','retreat_chance','retreat'])assert(!primaryComparison.includes(`data-equipment-compare="${key}"`),'Secondary comparison effects start folded');
assert(/<details\b[^>]*data-equipment-comparison-details[^>]*><summary>[^<]+<\/summary>/.test(comparison));
assert(comparison.includes('data-equipment-person="liubei"'));
assert.equal(equipment.preview(offer,'8'),offer.preview_by_officer[8]);
const unavailable=clone(offer);unavailable.preview_by_officer[8].eligible=false;unavailable.preview_by_officer[8].reason_tc='此人不能購買';unavailable.preview_by_officer[8].reason_ja='この武将は購入できません';
assert(equipment.comparison(view,8,unavailable,{bilingual:false}).includes('此人不能購買'));
assert(equipment.comparison(view,8,unavailable,{bilingual:false,locale:'ja'}).includes('この武将は購入できません'));
assert(unfolded(equipment.comparison(view,8,unavailable,{bilingual:false})).includes('此人不能購買'),'Eligibility reason stays visible when secondary effects are folded');
assert(equipment.comparison(view,8,{}, {bilingual:false}).includes('確認引擎提供的效果比較'));
const guide=equipment.acquisition(view,{bilingual:false,open:true});assert(guide.includes('data-equipment-guide open'));assert(guide.includes('雙股劍'));assert(guide.includes('指定人物取得'));assert(guide.includes('本局唯一'));assert(guide.includes('本局已取得 · 劉備'));
assert(equipment.acquisition(view,{bilingual:false,locale:'ja'}).includes('特殊装備と入手条件'));
const unclaimed=clone(view);unclaimed.catalog.equipment.special[0].claimed=false;assert(equipment.acquisition(unclaimed,{bilingual:false}).includes('本局尚未取得'));
const staffHolder=clone(view);staffHolder.catalog.equipment.special[0].holder='clerk-000001';staffHolder.game={officers:{'clerk-000001':{person_id:'clerk-000001'}}};staffHolder.catalog.names={'clerk-000001':'周文'};const staffGuide=equipment.acquisition(staffHolder,{bilingual:false});assert(staffGuide.includes('本局已取得 · 周文'));assert(!staffGuide.includes('clerk-000001'),'Generated holders use their human name, never the private ID');
for(const names of [{},{'clerk-000001':'clerk-000001'}]){staffHolder.catalog.names=names;const missingHolder=equipment.acquisition(staffHolder,{bilingual:false});assert(missingHolder.includes('本局已取得'));assert(!missingHolder.includes('clerk-000001'),'Missing human names never expose an internal fallback ID');}
const malicious=clone(view);malicious.catalog.equipment.officers[8].weapon.name_tc='<img src=x onerror=bad>';malicious.catalog.equipment.officers[8].initial.note_tc='<script>bad</script>';
malicious.catalog.equipment.special[0].condition_tc='<img src=y>';malicious.catalog.library[0].name='<script>holder</script>';
for(const html of [equipment.summary(malicious,8),equipment.acquisition(malicious)]){assert(!html.includes('<img'));assert(!html.includes('<script>'));assert(html.includes('&lt;'));}
const quoted=clone(before);quoted.weapon={...sword,id:'33" onclick="bad',name_tc:'劍" <svg>&\'尾'};
const quotedHtml=equipment.render(quoted,{bilingual:false,compact:true});assert(quotedHtml.includes('data-equipment-item="33&quot; onclick=&quot;bad"'));assert(quotedHtml.includes('劍&quot; &lt;svg&gt;&amp;&#39;尾'));assert(!quotedHtml.includes('<svg>'));assert(!quotedHtml.includes(' onclick="bad'));
const itemsOnly=equipment.render({weapon:sword,armor},{bilingual:false,compact:true});assert(!itemsOnly.includes('data-equipment-stat='),'Combined effects are shown only when supplied by the engine');
const malformed=clone(before);malformed.hit_penalty=null;malformed.evasion_penalty=Infinity;malformed.attack_bonus='100';malformed.retreat_chance=undefined;
const missing=equipment.render(malformed,{bilingual:false});assert(missing.includes('單挑攻擊—'));assert(missing.includes('命中修正—'));assert(missing.includes('回避修正—'));assert(missing.includes('觸發機率 —%'));
for(const bad of [null,undefined,Infinity,'7',{},NaN])assert.equal(equipment.signed(bad),'—');
assert.equal(equipment.signed(-4),'-4');assert.equal(equipment.signed(0),'0');assert.equal(equipment.signed(4),'+4');assert.equal(equipment.interval(2,2),'2');
assert.equal(JSON.stringify(view),snapshot,'Rendering and comparison never mutate profiles, equipment, inventory or RNG');
const originalUI=globalThis.GameOriginalUI,iconCalls=[];
globalThis.GameOriginalUI={equipment(slot,item,options){iconCalls.push({slot,id:item.id,locale:options.locale,className:options.className});return `<span class="${options.className}" role="img" aria-label="裝備分類圖示" data-original-equipment="${slot}:${item.id}"></span>`;}};
try{
 const withArt=equipment.summary(view,8,{bilingual:false});
 assert.deepEqual(iconCalls.map(call=>[call.slot,call.id]),[['weapon',33],['armor',2]]);
 assert(iconCalls.every(call=>call.locale==='zh-Hant'&&call.className==='equipment-item-icon'));
 assert(withArt.includes('data-original-equipment="weapon:33"'));assert(withArt.includes('data-original-equipment="armor:2"'));
 iconCalls.length=0;
 const changed=clone(view);changed.catalog.equipment.officers[8].weapon={...sword,id:0};
 const changedHtml=equipment.summary(changed,8,{locale:'ja',bilingual:false});
 assert.equal(iconCalls[0].id,0,'A famous weapon name or person never overrides the actual item ID');
 assert(changedHtml.includes('data-equipment-key="weapon:0"'));assert(changedHtml.includes('data-equipment-person="liubei"'));assert(changedHtml.includes('一騎討ちの攻撃+7'),'Presentation uses the supplied engine result even if item display data changes');
 iconCalls.length=0;equipment.acquisition(view,{locale:'ja',bilingual:false});
 assert.deepEqual(iconCalls.map(call=>[call.slot,call.id,call.locale]),[['weapon',33,'ja']]);
 assert.equal(JSON.stringify(view),snapshot,'Adding category art never mutates engine state');
}finally{if(originalUI===undefined)delete globalThis.GameOriginalUI;else globalThis.GameOriginalUI=originalUI;}
const browser={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../game/equipment.js'),'utf8'),browser);assert.equal(browser.window.GameEquipment.summary(view,8),equipment.summary(view,8));assert(Object.isFrozen(equipment));

// A small DOM harness exercises delegated lifecycle without a browser dependency.
// Geometry and portal assertions below also cover nested scroll containers and dialogs.
function domHarness(){
 const eventTarget=()=>({listeners:new Map(),addEventListener(type,fn){const entries=this.listeners.get(type)||[];entries.push(fn);this.listeners.set(type,entries);},removeEventListener(type,fn){this.listeners.set(type,(this.listeners.get(type)||[]).filter(entry=>entry!==fn));},emit(type,props={}){const event={type,defaultPrevented:false,stopped:false,preventDefault(){this.defaultPrevented=true;},stopPropagation(){this.stopped=true;},...props};for(const fn of this.listeners.get(type)||[])fn(event);return event;}});
 let doc;const observers=[],timers=new Map();let timerId=0;
 class Element{
  constructor(tag){this.tagName=tag;this.attributes=new Map();this.children=[];this.parentElement=null;this.style={};this.hidden=false;this.rect={left:10,top:10,right:110,bottom:54,width:100,height:44};}
  setAttribute(key,value){this.attributes.set(key,String(value));}
  getAttribute(key){return this.attributes.get(key)??null;}
  removeAttribute(key){this.attributes.delete(key);}
  get isConnected(){return this===doc.documentElement||!!this.parentElement?.isConnected;}
  contains(node){return !!node&&(this===node||this.children.some(child=>child.contains?.(node)));}
  closest(selector){for(let node=this;node;node=node.parentElement){if(selector==='[data-equipment-tooltip]'&&node.attributes.has('data-equipment-tooltip'))return node;if(selector==='dialog[open]'&&node.tagName==='dialog'&&node.attributes.has('open'))return node;if(selector==='dialog'&&node.tagName==='dialog')return node;if(selector==='[hidden],[aria-hidden="true"]'&&(node.hidden||node.attributes.has('hidden')||node.getAttribute('aria-hidden')==='true'))return node;}return null;}
  querySelector(selector){return selector==='template[data-equipment-tooltip-content]'?this.children.find(child=>child.tagName==='template')||null:null;}
  appendChild(child){child.remove?.();this.children.push(child);child.parentElement=this;return child;}
  remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(child=>child!==this);this.parentElement=null;}
  replaceChildren(fragment){this.html=fragment.html;}
  getClientRects(){return this.closest('[hidden],[aria-hidden="true"]')?[]:[this.getBoundingClientRect()];}
  getBoundingClientRect(){if(this.id==='game-equipment-tooltip'){const width=Math.min(220,parseFloat(this.style.maxWidth)||220),height=Math.min(160,parseFloat(this.style.maxHeight)||160);return {left:parseFloat(this.style.left)||0,top:parseFloat(this.style.top)||0,width,height,right:(parseFloat(this.style.left)||0)+width,bottom:(parseFloat(this.style.top)||0)+height};}return this.rect;}
  matches(selector){return selector===':popover-open'&&this.popoverOpen===true;}
  showPopover(){assert(this.isConnected);this.popoverOpen=true;}
  hidePopover(){this.popoverOpen=false;}
 }
 const win={...eventTarget(),innerWidth:800,innerHeight:600,setTimeout(fn){const id=++timerId;timers.set(id,fn);return id;},clearTimeout(id){timers.delete(id);},getComputedStyle(element){return {overflowX:element.overflowX||'visible',overflowY:element.overflowY||'visible'};},MutationObserver:class{constructor(callback){this.callback=callback;observers.push(this);}observe(){}disconnect(){this.disconnected=true;}},visualViewport:{...eventTarget(),offsetLeft:0,offsetTop:0,width:800,height:600}};
 doc={...eventTarget(),defaultView:win,createElement:tag=>new Element(tag)};doc.documentElement=new Element('html');doc.body=doc.documentElement.appendChild(new Element('body'));
 function button(html,parent=doc.body){
  const tag=html.match(/<button\b[^>]*>/)?.[0];assert(tag,'Equipment produces a native button');
  const result=new Element('button');for(const [,key,value]of tag.matchAll(/([\w-]+)="([^"]*)"/g))result.setAttribute(key,value);
  result.setAttribute('data-equipment-tooltip','');
  const template=result.appendChild(new Element('template')),content=html.match(/<template data-equipment-tooltip-content>([\s\S]*?)<\/template>/)?.[1];assert(content);
  template.content={cloneNode(){return {html:content};}};parent.appendChild(result);return result;
 }
 return {doc,win,button,element:tag=>new Element(tag),notify(records){for(const observer of observers)if(!observer.disconnected)observer.callback(records);},flushTimers(){for(const [id,fn]of [...timers]){timers.delete(id);fn();}},tip(){const find=node=>node.id==='game-equipment-tooltip'?node:node.children.map(find).find(Boolean);return find(doc.documentElement);}};
}
const dom=domHarness(),binding=equipment.bindTooltips(dom.doc),trigger=dom.button(compact);
assert.equal(equipment.bindTooltips(dom.doc),binding,'Delegated listeners install only once per document');
dom.doc.emit('pointerover',{target:trigger,pointerType:'touch'});assert.equal(dom.tip(),undefined,'Touch does not synthesize hover tips');
dom.doc.emit('pointerover',{target:trigger,pointerType:'mouse'});
let tip=dom.tip();assert(tip);assert.equal(tip.parentElement,dom.doc.body);assert.equal(tip.getAttribute('role'),'tooltip');assert.equal(tip.getAttribute('popover'),'manual');assert(tip.popoverOpen);assert(!tip.hidden);
assert(tip.html.includes('雙股劍'));assert(tip.html.includes('武器強度 14'));assert(tip.html.includes('重量 6'));assert(tip.html.includes('單挑攻擊+7'));assert(tip.html.includes('防禦+2'));assert(tip.html.includes('總重量10'));
assert.equal(trigger.getAttribute('aria-expanded'),'true');assert.equal(trigger.getAttribute('aria-describedby'),tip.id);assert.equal(trigger.getAttribute('aria-controls'),tip.id);assert.equal(tip.getAttribute('data-equipment-key'),'weapon:33');
dom.doc.emit('pointerout',{target:trigger,relatedTarget:dom.doc.body});dom.doc.emit('pointerover',{target:tip,pointerType:'mouse'});dom.flushTimers();assert(!tip.hidden,'The hover tip remains readable when the pointer moves onto it');
dom.doc.emit('pointerout',{target:tip,relatedTarget:dom.doc.body});dom.flushTimers();assert(tip.hidden);
dom.doc.emit('focusin',{target:trigger});assert(!tip.hidden,'Keyboard focus exposes equipment values');
for(const key of ['Enter',' ']){const event=dom.doc.emit('keydown',{target:trigger,key});assert(event.defaultPrevented);assert(!tip.hidden);}
const escapeEvent=dom.doc.emit('keydown',{target:trigger,key:'Escape'});assert(escapeEvent.defaultPrevented);assert(escapeEvent.stopped,'Escape dismisses equipment before closing its enclosing modal');assert(tip.hidden);assert.equal(trigger.getAttribute('aria-expanded'),'false');assert.equal(trigger.getAttribute('aria-describedby'),null);
dom.doc.emit('pointerdown',{target:trigger,pointerType:'touch'});dom.doc.emit('focusin',{target:trigger});dom.doc.emit('click',{target:trigger,detail:1});assert(!tip.hidden,'First touch opens values even when touch gives the button focus');
dom.doc.emit('click',{target:trigger,detail:1});assert(tip.hidden,'A second touch toggles the values closed');
dom.doc.emit('click',{target:trigger,detail:0});assert(!tip.hidden,'Native keyboard activation opens the tip');dom.doc.emit('pointerdown',{target:dom.doc.body});assert(tip.hidden,'An outside press dismisses the tip');
dom.doc.emit('focusin',{target:trigger});dom.doc.emit('focusout',{target:trigger,relatedTarget:dom.doc.body});assert(tip.hidden,'Leaving keyboard focus dismisses the tip');
dom.doc.emit('focusin',{target:trigger});dom.doc.emit('game-language-change');assert(tip.hidden,'The app language event removes old-language tooltip content');
dom.doc.emit('focusin',{target:trigger});dom.notify([{type:'attributes',target:dom.doc.documentElement,attributeName:'lang'}]);assert(tip.hidden);
dom.doc.emit('focusin',{target:trigger});trigger.setAttribute('data-equipment-key','weapon:0');dom.notify([{type:'attributes',target:trigger,attributeName:'data-equipment-key'}]);assert(tip.hidden,'Reusing a row for another item cannot retain stale values');
dom.doc.emit('focusin',{target:trigger});trigger.remove();dom.notify([{type:'childList',target:dom.doc.body}]);assert(tip.hidden);assert.equal(trigger.getAttribute('aria-expanded'),'false','Replacing the equipment DOM clears the old trigger state');

const dialog=dom.doc.body.appendChild(dom.element('dialog'));dialog.setAttribute('open','');
const scroller=dialog.appendChild(dom.element('div'));scroller.overflowY='auto';scroller.rect={left:0,top:0,right:180,bottom:160,width:180,height:160};
const japanese=dom.button(equipment.summary(view,8,{compact:true,bilingual:false,locale:'ja'}),scroller);japanese.rect={left:135,top:120,right:178,bottom:154,width:43,height:34};
dom.win.visualViewport.width=180;dom.win.visualViewport.height=160;
dom.doc.emit('focusin',{target:japanese});assert.equal(dom.tip(),tip,'Every equipment entry reuses one shared portal');assert.equal(tip.parentElement,dialog,'Modal equipment stays in its dialog top layer');assert(tip.popoverOpen);assert(tip.html.includes('双股剣'));assert(!tip.html.includes('雙股劍'));assert(tip.html.includes('一騎討ちの攻撃+7'));assert.equal(tip.getAttribute('data-l10n-native'),'ja');
assert(parseFloat(tip.style.left)>=8);assert(parseFloat(tip.style.top)>=8);assert(parseFloat(tip.style.left)+tip.getBoundingClientRect().width<=172);assert(parseFloat(tip.style.top)+tip.getBoundingClientRect().height<=152);
scroller.rect.bottom=110;dom.doc.emit('scroll',{target:scroller});assert(tip.hidden,'Scrolling the anchor out of its clipped roster dismisses the portal');
scroller.rect.bottom=160;dom.doc.emit('focusin',{target:japanese});dom.doc.emit('close',{target:dialog});assert(tip.hidden,'Closing the equipment modal also closes its portal');
dom.doc.emit('focusin',{target:japanese});dom.notify([{type:'childList',target:japanese}]);assert(tip.hidden,'Replacing tooltip content invalidates the active projection');
binding.destroy();assert.equal(dom.tip(),undefined);assert([...dom.doc.listeners.values()].every(entries=>entries.length===0));assert.equal(JSON.stringify(view),snapshot,'Tooltip interactions are read-only projections, including engine state and RNG');

for(const viewport of [{left:0,top:0,width:320,height:220},{left:40,top:30,width:180,height:160}])for(const anchor of [{left:0,top:0,right:40,bottom:44},{left:300,top:190,right:320,bottom:220}]){
 const result=equipment.tooltipPosition(anchor,{width:260,height:180},viewport),width=Math.min(260,result.maxWidth),height=Math.min(180,result.maxHeight);
 assert(result.left>=viewport.left+8);assert(result.top>=viewport.top+8);assert(result.left+width<=viewport.left+viewport.width-8);assert(result.top+height<=viewport.top+viewport.height-8);
}
const above=equipment.tooltipPosition({left:50,top:400,right:150,bottom:444},{width:200,height:140},{width:800,height:500});assert.equal(above.top,252,'A bottom-edge trigger flips its tip above the equipment');
console.log('equipment UI: icon/name-only lists, accessible hover/touch/keyboard tooltip lifecycle, shared dialog portal, scroll dismissal, language and identity invalidation, viewport positioning, immutable engine projections and escaping passed');
