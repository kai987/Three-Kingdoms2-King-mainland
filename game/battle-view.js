/* Read-only battle UI reconciliation and semantic feedback. No command, RNG or save writes. */
'use strict';
(function(root){
 const TACTIC_FAMILIES=Object.freeze(['88','95','8d','8d','88','88','88','8d','91','95','8d','8d','88','88','88','95']);
 const RECEIPT_KINDS=Object.freeze({tactic:'tactic',duel_start:'duel_start',duel_action:'duel_action',attack:'attack',battle_move:'move',retreat:'retreat'});
 function sceneCue(scene){
  if(scene?.kind==='duel_start'&&scene.success===false)return 'duel_refused';
  if(scene?.skipped||scene?.success===false)return 'error';
  return scene?.kind==='move'?'march':scene?.kind==='tactic'?'tactic_'+(TACTIC_FAMILIES[scene.tactic]||'88'):scene?.kind==='ambush'?'tactic_8d':scene?.kind==='duel_start'?'duel_start':scene?.kind==='duel_action'?'duel_'+(scene.move==='desperate'?'strike':scene.move):scene?.kind==='retreat'?'cancel':'attack';
 }
 function resultScene(kind,payload,before,after){
  const receipt=after?.presentation,battle=after?.game?.battle||before?.game?.battle,wanted=RECEIPT_KINDS[kind];
  if(!wanted||!battle||!receipt||receipt.schema!=='tk2-battle-presentation-v1'||receipt.revision!==after?.revision||!Array.isArray(receipt.scenes)||receipt.scenes.length>192)return null;
  return receipt.scenes.find(row=>row&&row.kind===wanted&&row.battle_id===battle.id&&typeof row.success==='boolean'&&typeof row.skipped==='boolean'&&!row.counter&&(payload?.actor===undefined||String(row.actor)===String(payload.actor))&&(kind!=='tactic'||row.tactic===payload?.tactic))||null;
 }
 function commandCue(kind,payload,before,after){
  if(before?.game?.turn!==undefined&&after?.game?.turn>before.game.turn)return 'turn';
  const scene=resultScene(kind,payload,before,after);if(scene)return sceneCue(scene);
  if(kind==='duel_start')return after?.game?.battle?.extended?.duel?'duel_start':'duel_refused';
  if(kind==='duel_action')return 'duel_'+(payload?.move==='desperate'?'strike':payload?.move);
  // A missing presentation receipt has no authoritative success/failure flag.
  // Use neutral feedback rather than infer an outcome from localized prose.
  return {depart:'march',transfer:'march',attack:'attack',retreat:'cancel',tactic:'tactic'}[kind]||'confirm';
 }
 const escape=value=>String(value).replace(/[\\"]/g,'\\$&');
 function key(node){
  if(node.nodeType!==1)return null;
  for(const attribute of ['id','data-actor','data-target','data-unit-list'])if(node.hasAttribute(attribute))return attribute+':'+node.getAttribute(attribute);
  return node.hasAttribute('data-battle-scene')?'battle-scene':null;
 }
 function compatible(a,b){return a?.nodeType===b?.nodeType&&(a.nodeType!==1||a.tagName===b.tagName)&&key(a)===key(b);}
 function patchNode(current,next){
  if(current.nodeType!==1){if(current.nodeValue!==next.nodeValue)current.nodeValue=next.nodeValue;return;}
  // This subtree owns its canvas, timers, selectors and ResizeObserver. Only
  // GameBattleScene.mount updates its current view and draws new pixels.
  if(current.hasAttribute('data-battle-scene')){
   if(next.hasAttribute('data-l10n-native')&&current.getAttribute('data-l10n-native')!==next.getAttribute('data-l10n-native'))current.setAttribute('data-l10n-native',next.getAttribute('data-l10n-native'));
   return;
  }
  for(const attribute of [...current.attributes])if(!next.hasAttribute(attribute.name))current.removeAttribute(attribute.name);
  for(const attribute of [...next.attributes])if(current.getAttribute(attribute.name)!==attribute.value)current.setAttribute(attribute.name,attribute.value);
  patchChildren(current,next);
  if(current.tagName==='INPUT'){current.checked=next.checked;if(current.value!==next.value)current.value=next.value;}
  if(current.tagName==='OPTION')current.selected=next.selected;
 }
 function patchChildren(current,next){
  const old=[...current.childNodes],used=new Set();
  for(const [index,fresh]of [...next.childNodes].entries()){
   const named=key(fresh);let found=named?old.find(node=>!used.has(node)&&compatible(node,fresh)):old[index];
   if(!found||used.has(found)||!compatible(found,fresh))found=old.find(node=>!used.has(node)&&!key(node)&&compatible(node,fresh));
   if(found){used.add(found);patchNode(found,fresh);}else found=fresh.cloneNode(true);
   const position=current.childNodes[index];if(position!==found)current.insertBefore(found,position||null);
  }
  while(current.childNodes.length>next.childNodes.length)current.removeChild(current.lastChild);
 }
 function focusSelector(node){
  if(!node)return null;
  if(node.hasAttribute?.('data-duel-person')&&node.hasAttribute?.('data-duel-field'))return '[data-duel-person="'+escape(node.getAttribute('data-duel-person'))+'"][data-duel-field="'+escape(node.getAttribute('data-duel-field'))+'"]';
  for(const attribute of ['id','data-actor','data-target','data-battle-nav'])if(node.hasAttribute?.(attribute))return '['+attribute+'="'+escape(node.getAttribute(attribute))+'"]';
  return node.matches?.('[data-battle-canvas]')?'[data-battle-canvas]':null;
 }
 function create(options={}){
  const doc=options.document||root.document,win=options.window||root;let identity=null,mode=null;
  function fragment(html){const template=doc?.createElement?.('template');if(!template?.content)return null;template.innerHTML=html;return template.content;}
  function update(node,html){const tree=fragment(html);if(tree&&node?.childNodes)patchChildren(node,tree);else if(node)node.innerHTML=html;}
  function render(stage,html,settings={}){
   const sameBattle=identity===settings.key,sameMode=sameBattle&&mode===settings.mode,inspector=settings.inspector;
   const focused=doc?.activeElement,focus=(stage?.contains?.(focused)||inspector?.contains?.(focused))?focusSelector(focused):null;
   const page=win.scrollY||0,scrolls=[],details=[];
   if(sameMode){
    for(const node of stage?.querySelectorAll?.('.battle-layout,.battle-army-menu,.battle-log,[data-unit-list]')||[]){
     const selector=node.hasAttribute('data-unit-list')?'[data-unit-list="'+escape(node.getAttribute('data-unit-list'))+'"]':node.matches('.battle-layout')?'.battle-layout':node.matches('.battle-army-menu')?'.battle-army-menu':'.battle-log';
     scrolls.push([selector,node.scrollTop,node.scrollLeft||0]);
    }
    for(const node of stage?.querySelectorAll?.('details')||[])details.push([node.matches('.battle-army-menu')?'.battle-army-menu':node.closest('[data-duel-loadouts]')?'[data-duel-loadouts] details':null,node.open]);
   }
   const oldScene=sameBattle?stage?.querySelector?.('[data-battle-scene]'):null;
   if(sameMode)update(stage,html);
   else{
    const tree=fragment(html),fresh=tree?.querySelector?.('[data-battle-scene]');
    if(oldScene&&fresh){if(fresh.hasAttribute('data-l10n-native'))oldScene.setAttribute('data-l10n-native',fresh.getAttribute('data-l10n-native'));fresh.replaceWith(oldScene);}
    if(tree&&stage?.replaceChildren)stage.replaceChildren(tree);else if(stage)stage.innerHTML=html;
   }
   identity=settings.key;mode=settings.mode;
   for(const [selector,open]of details)if(selector){const node=stage.querySelector(selector);if(node)node.open=open;}
   return ()=>{
    for(const [selector,top,left]of scrolls){const node=stage.querySelector(selector);if(node){node.scrollTop=top;node.scrollLeft=left;}}
    if(focus){const candidate=stage.querySelector?.(focus)||inspector?.querySelector?.(focus),node=candidate&&!candidate.disabled&&!candidate.closest?.('[hidden]')?candidate:stage.querySelector?.('[data-battle-canvas]');node?.focus?.({preventScroll:true});win.scrollTo?.({top:page,behavior:'instant'});}
   };
  }
  return {render,controls:update,reset(){identity=mode=null;}};
 }
 const api={TACTIC_FAMILIES,sceneCue,resultScene,commandCue,patchChildren,create};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameBattleView=Object.freeze(api);
})(typeof window==='object'?window:globalThis);
