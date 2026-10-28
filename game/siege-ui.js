/* Original four-formation / four-group orders UI. Drafts never mutate a battle. */
'use strict';
(function(root){
 const KINDS=Object.freeze(['infantry','archer','cavalry','general']);
 const ORDERS=Object.freeze(['advance','retreat','wait','surround']);
 const FORMATIONS=Object.freeze([['長蛇','長蛇'],['雁行','雁行'],['錐行','錐行'],['魚鱗','魚鱗']]);
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function current(view){const row=view?.game?.battle?.extended?.siege;return row?.schema==='tk2-siege-v1'?row:null;}
 function ownSide(view){return view?.game?.battle?.attacker===view?.game?.player?'attackers':'defenders';}
 function create(options={}){
  let key='',draftFormation=0,draftOrders=null,automatic=false,timer=null,requesting=false;
  const locale=()=>options.i18n?.locale==='ja'?'ja':'zh-Hant';
  const text=(tc,ja)=>locale()==='ja'?ja:tc;
  const kindName=kind=>({infantry:text('步','歩'),archer:text('弓','弓'),cavalry:text('騎','騎'),general:text('將','将')}[kind]);
  const orderName=order=>({advance:text('前進','前進'),retreat:text('後退','後退'),wait:text('待機','待機'),surround:text('包圍','包囲')}[order]);
  const view=()=>options.getView();
  function synchronize(){
   const value=view(),row=current(value),next=row?[value.catalog?.scenario_id,value.game.seed,value.game.battle.id,row.actor,row.target].join(':'):'';
   if(next!==key){stop();key=next;draftFormation=0;draftOrders=null;}
   if(row&&!draftOrders)draftOrders={...row.orders?.[ownSide(value)]};
   return row;
  }
  function stop(){automatic=false;if(timer!==null){clearTimeout(timer);timer=null;}options.onAutoChange?.(false);}
  function payload(value={}){return {battle_id:view().game.battle.id,...value};}
  async function send(kind,value={}){
   if(requesting||options.isBusy?.())return false;
   requesting=true;let okay=false;
   try{okay=await options.command(kind,payload(value));return okay;}
   finally{requesting=false;if(!okay)stop();}
  }
  async function tick(){
   timer=null;const row=synchronize();if(!automatic||!row)return stop();
   if(root.document?.hidden||root.document?.querySelector('dialog[open]')){stop();options.refresh();return;}
   if(options.isBusy?.()||requesting){timer=setTimeout(tick,100);return;}
   if(row.stage==='formation'){stop();return;}
   if(!['orders','combat'].includes(row.stage))return stop();
   if(!await advance(true))return;
   if(automatic&&current(view()))timer=setTimeout(tick,450);else stop();
  }
  async function advance(fromAutomatic=false){
   // A paused combat stage may have unsent edits. Apply the current four
   // group orders before every tick, including after a mid-combat pause.
   if(!await send('siege_orders',{orders:{...draftOrders}}))return false;
   if(fromAutomatic&&!automatic)return true;
   return send('siege_step');
  }
  function reset(){stop();key='';draftFormation=0;draftOrders=null;}
  function state(){const row=synchronize();return {formation:draftFormation,orders:{...draftOrders},automatic,stage:row?.stage??null};}
  function sideSummary(side){
   const value=view(),row=current(value);
   const pieces=(row.units||[]).filter(unit=>unit.side===side);
   // Participating identities come from the two authoritative army lists.
   const id=value.game.battle[side].some(u=>u.id===row.actor)?row.actor:row.target;
   return `<section class="siege-army-summary"><h3>${escape(options.name(id))}</h3>${options.portrait?.(id)||''}<dl>${KINDS.map(kind=>`<div><dt>${kindName(kind)}</dt><dd>${kind==='general'?(pieces.find(p=>p.kind===kind)?.health??value.game.battle.extended.support[id]?.health??0):(pieces.filter(p=>p.kind===kind).reduce((sum,p)=>sum+p.troops,0))}</dd></div>`).join('')}</dl></section>`;
  }
  function armies(){synchronize();return ['attackers','defenders'].map(side=>sideSummary(side)).join('');}
  function controls(){
   const row=synchronize();if(!row)return '';
   const side=ownSide(view()),locked=view().game.battle[side].some(unit=>unit.id===row.fort);
   const introduction=`<p class="small">${text('先決定陣形，再對步、弓、騎、將分組下令。每巡依序移動或接敵攻擊，可暫停改令。','陣形を決め、歩・弓・騎・将へ命令します。各巡で移動・接敵攻撃を行い、途中で停止して命令を変更できます。')}</p>`;
   const heading=`<h2>${text('攻城 · 排兵布陣','城内戦・陣形と命令')}</h2><p>${text('第','第')}${row.round||1}${text('巡','巡')}</p>`;
   const formation=`<div class="siege-formation-options">${FORMATIONS.map(([tc,ja],i)=>`<button type="button" data-siege-formation="${i}" aria-pressed="${draftFormation===i}"><img width="33" height="33" alt="" src="${root.GamePaths?.asset('/assets/siege-original/formation-'+i+'.png')||'/assets/siege-original/formation-'+i+'.png'}"><span>${locale()==='ja'?ja:tc}</span></button>`).join('')}</div>`;
   const orders=`<div class="siege-orders">${KINDS.map(kind=>`<label class="field" for="siege-order-${kind}"><span>${kindName(kind)}</span><select id="siege-order-${kind}" data-siege-order="${kind}" ${automatic?'disabled':''}>${ORDERS.map(order=>`<option value="${order}" ${draftOrders?.[kind]===order?'selected':''}>${orderName(order)}</option>`).join('')}</select></label>`).join('')}</div>`;
   return heading+introduction+(row.stage==='formation'?`${locked?'<p>'+text('城內守方使用原版固定城防陣位。','城内側は原作の固定防衛配置を使います。')+'</p>':formation}<button type="button" class="primary" id="siege-form">${locked?text('確認守城陣','防衛配置を確認'):text('確定陣形','陣形を決定')}</button>`:`${orders}<div class="actions"><button type="button" id="siege-run" class="primary">${automatic?text('暫停改令','停止して命令を変更'):text('開始交戰','交戦を進める')}</button><button type="button" id="siege-step" ${automatic?'disabled':''}>${text('推進一巡','1巡進める')}</button></div>`)+`<p class="small">${text('本次接敵已使用2機動；城內布陣及分組命令不另耗命令書或機動力。','接敵時に機動力2を消費済みです。陣形と各組への命令に追加の命令書・機動力は使いません。')}</p><button type="button" id="siege-withdraw">${text('退出本次交鋒','この交戦から退く')}</button><ul class="battle-log">${view().game.battle.log.slice(-6).map(line=>`<li>${escape(options.i18n?.t?.(line)||line)}</li>`).join('')}</ul>`;
  }
  function bind(host){
   synchronize();
   for(const button of host.querySelectorAll('[data-siege-formation]'))button.onclick=()=>{draftFormation=Number(button.dataset.siegeFormation);options.refresh();};
   for(const input of host.querySelectorAll('[data-siege-order]'))input.onchange=()=>{draftOrders[input.dataset.siegeOrder]=input.value;};
   const form=host.querySelector('#siege-form');if(form)form.onclick=()=>send('siege_form',{formation:draftFormation});
   const run=host.querySelector('#siege-run');if(run)run.onclick=()=>{if(automatic){stop();options.refresh();}else{automatic=true;void tick();}};
   const step=host.querySelector('#siege-step');if(step)step.onclick=()=>advance();
   const withdraw=host.querySelector('#siege-withdraw');if(withdraw)withdraw.onclick=()=>{stop();void send('siege_withdraw');};
  }
  function keyboard(event){
   const row=current(view());if(!row||options.isBusy?.()||requesting||event.defaultPrevented||event.isComposing||event.altKey||event.ctrlKey||event.metaKey||root.document?.querySelector('dialog[open]')||event.target?.closest?.('input,select,textarea,[contenteditable],#utility-menu,nav'))return false;
   if(event.target?.closest?.('button,a,summary,[role="button"]')&&!event.target.closest('[data-siege-formation]'))return false;
   if(row.stage==='formation'&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key)){event.preventDefault();draftFormation=(draftFormation+(event.key==='ArrowLeft'||event.key==='ArrowUp'?3:1))%4;options.refresh();return true;}
   if(event.key==='Enter'&&row.stage==='formation'){event.preventDefault();void send('siege_form',{formation:draftFormation});return true;}
   if(event.key==='Escape'&&automatic){event.preventDefault();stop();options.refresh();return true;}
   return false;
  }
  return {armies,controls,bind,state,stop,reset,keyboard};
 }
 const api={create,current,ownSide,KINDS,ORDERS,FORMATIONS};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameSiegeUI=Object.freeze(api);
})(typeof window==='object'?window:globalThis);
