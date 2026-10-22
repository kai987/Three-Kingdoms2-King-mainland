/* Read-only event playback. Acknowledgements never become campaign commands. */
'use strict';
(function(root){
 const KINDS=Object.freeze({
  campaign_start:['戰役揭幕','戦役の開幕'],officer_appeared:['武將登場','武将の登場'],
  recruit_success:['登用成功','登用に成功'],recruit_failure:['登用未果','登用を断られました'],
  defection:['武將轉屬','武将の移籍'],officer_death:['武將逝世','武将の死去'],
  succession:['主將繼任','君主の継承'],faction_ended:['勢力滅亡','勢力の滅亡'],
  city_founded:['新城建置','新都市の開設'],city_captured:['城池易主','都市の陥落'],
  battle_started:['戰鬥開始','戦闘開始'],battle_result:['戰果揭曉','戦闘の結果'],
  duel_started:['單挑交鋒','一騎討ち開始'],duel_result:['單挑結果','一騎討ちの結果'],
  tactic:['計略發動','計略の発動'],march_weather:['行軍遇險','行軍中の災害'],
  route_discovered:['發現新航路','新航路の発見'],march_arrived:['部隊抵達','部隊の到着'],
  march_returned:['部隊折返','部隊の帰還'],new_year:['新年更始','新年の到来'],
  campaign_victory:['天下歸一','天下統一'],campaign_defeat:['戰役結束','戦役の終了'],
  ai_campaign:['敵軍動向','敵軍の動向']
 });
 const BATCH=new Set(['officer_appeared','officer_death','recruit_success','recruit_failure','march_arrived','march_returned']);
 const WORLD=new Set(['campaign_start','officer_appeared','officer_death','succession','faction_ended','city_founded','city_captured','new_year','campaign_victory','campaign_defeat']);
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const clone=value=>JSON.parse(JSON.stringify(value));
 function validEvent(row){
  return !!row&&Number.isSafeInteger(row.id)&&row.id>0&&Object.hasOwn(KINDS,row.kind)&&['player','world'].includes(row.audience)&&
   Number.isSafeInteger(row.year)&&row.year>0&&Number.isInteger(row.month)&&row.month>=1&&row.month<=12&&[1,11,21].includes(row.day)&&Number.isSafeInteger(row.turn)&&row.turn>0&&
   ['person_ids','city_ids','factions'].every(key=>Array.isArray(row[key])&&row[key].every(id=>typeof id==='string'&&id.length<=128))&&
   !!row.details&&typeof row.details==='object'&&!Array.isArray(row.details);
 }
 function campaignKey(view){return view?.game?JSON.stringify([view.catalog?.scenario_id||view.catalog?.title||'',view.game.seed,view.game.player]):null;}
 function eventRows(view){const rows=view?.game?.extension?.events?.items;return Array.isArray(rows)?rows.filter(validEvent).sort((a,b)=>a.id-b.id):[];}
 function automatic(row,player){return row.audience==='player'||WORLD.has(row.kind)||row.factions.includes(player);}
 function groupRows(rows){
  const groups=[];
  for(const row of rows){const last=groups.at(-1);if(last&&BATCH.has(row.kind)&&last[0].kind===row.kind&&last[0].turn===row.turn)last.push(row);else groups.push([row]);}
  return groups;
 }
 function create(options={}){
  const doc=options.document||root.document,modal=options.modal||doc?.querySelector('#event-dialog'),parent=options.parentDialog||doc?.querySelector('#dialog');
  const i18n=options.i18n||root.GameI18n,portraits=options.portraits||root.GamePortraits;
  const schedule=options.schedule||(fn=>root.setTimeout(fn,0)),getView=options.getView||(()=>null),isBusy=options.isBusy||(()=>false),isPreview=options.isPreview||(()=>false);
  let key=null,cursor=0,queue=[],active=null,historyMode=false,view=null,scheduled=false,portraitAttempted=false,shown=0,total=0,disposed=false;
  const locale=()=>i18n?.locale==='ja'?'ja':'zh-Hant',text=(tc,ja)=>locale()==='ja'?ja:tc;
  const label=value=>i18n?.t?i18n.t(String(value??''),locale()):String(value??'');
  function refreshHistoryLabel(){const button=doc?.querySelector?.('#event-history');if(button){button.textContent=text('事件回顧','出来事の記録');button.setAttribute('data-l10n-native',locale());}}
  function names(row){
   const catalog=view?.catalog||{},people=new Map((catalog.library||[]).map(p=>[p.person_id,p.name]));
   const personName=id=>{const current=Object.entries(view?.game?.officers||{}).find(([,person])=>person.person_id===id);return people.get(id)||(current&&catalog.names?.[current[0]])||text('未具名武將','名前未設定の武将');};
   return {people:row.person_ids.map(id=>label(personName(id))),cities:row.city_ids.map(id=>label(catalog.cities?.find(c=>c.id===id)?.name||text('未知城池','不明な都市'))),
    factions:row.factions.map(id=>label(catalog.factions?.find(f=>f.id===id)?.name||(id==='neutral'?text('無主','空白都市'):text('未具名勢力','名前未設定の勢力'))))};
  }
  function description(row){
   const n=names(row),p=n.people.join(text('、','・'))||text('武將','武将'),c=n.cities.join(' → ')||text('戰役地圖','戦役地図'),f=n.factions.at(-1)||text('本方','自軍'),d=row.details;
   switch(row.kind){
    case 'campaign_start':return text(`${f}展開新的戰役。每旬10日，請安排人事、兵力與行軍。`,`${f}による新たな戦役が始まります。1旬10日、人事・兵力・行軍を整えましょう。`);
    case 'officer_appeared':return text(`${p}已到登場年代，在${c}待訪。`,`${p}が登場年を迎え、${c}で仕官先を待っています。`);
    case 'recruit_success':return text(`${p}接受登用，加入${f}。`,`${p}が登用に応じ、${f}へ加わりました。`);
    case 'recruit_failure':return text(`${p}此次未接受登用。尋訪費用已按規則結算。`,`${p}は今回の登用を断りました。訪問費用は規則どおり精算されています。`);
    case 'defection':return text(`${p}的所屬已變更，現歸${f}。`,`${p}の所属が変わり、現在は${f}に仕えています。`);
    case 'officer_death':return text(`${p}離世。兵員與主將繼任依當前戰局結算。`,`${p}が死去しました。兵力と君主の継承は現在の戦況に従い処理されます。`);
    case 'succession':return text(`${p}接任${f}主將，勢力繼續行動。`,`${p}が${f}の君主を継承し、勢力の活動を続けます。`);
    case 'faction_ended':return text(`${f}失去繼續作戰的條件，退出戰役。`,`${f}は戦いを続けられなくなり、戦役から退場しました。`);
    case 'city_founded':{const founded=n.cities[0]||c,parent=n.cities[1];return text(`${founded}依年代建置，承接${parent||'原城'}目前歸屬及部分資源。`,`${founded}が設定年代に開設され、${parent||'元の都市'}の現在の所属と一部の資源を引き継ぎました。`);}
    case 'city_captured':{const owner=n.factions[0]||f;return text(`${c}的歸屬改為${owner}。駐軍及資源已結算。`,`${c}は${owner}の支配下となりました。守備隊と資源は精算済みです。`);}
    case 'battle_started':return text(`${c}發生交戰。請依兵力、地形與敵軍狀態選擇行動。`,`${c}で戦闘が始まります。兵力・地形・敵の状態を見て行動を選びましょう。`);
    case 'battle_result':{
     const outcome={victory:text('攻方獲勝','攻撃側の勝利'),defeat:text('守方獲勝','防御側の勝利'),retreat:text('攻方退卻','攻撃側の撤退')}[d.outcome]||text('戰鬥結束','戦闘終了');
     return text(`${c}：${outcome}。${typeof d.lost==='number'?`合計減員${d.lost}。`:''}請查看戰果與後續部署。`,`${c}：${outcome}。${typeof d.lost==='number'?`兵力損失は合計${d.lost}。`:''}結果と次の配置を確認してください。`);
    }
    case 'duel_started':return text(`${p}展開單挑，勝負依招式與武力判定。`,`${p}が一騎討ちに臨みます。技の選択と武力が勝負を左右します。`);
    case 'duel_result':return text(`${p}的單挑已結束。${d.result?label(d.result):'體力與退場結果已結算。'}`,`${p}の一騎討ちが終わりました。${d.result?label(d.result):'体力と退場結果は処理されています。'}`);
    case 'tactic':{
     const title=label(view?.catalog?.tactics?.[d.tactic]?.name||text('計略','計略'));
     return text(`${n.people[0]||p}施放${title}。${d.success===false?'未能奏效。':'效果與氣力消耗已結算。'}`,`${n.people[0]||p}が${title}を使用。${d.success===false?'効果はありませんでした。':'効果と気力の消費は精算されています。'}`);
    }
    case 'march_weather':return text(`${c}行軍途中遭遇險阻或暴風雨。${typeof d.lost==='number'?`減員${d.lost}兵。`:'實際兵損已計入部隊。'}`,`${c}への行軍中に難所や暴風雨に遭遇しました。${typeof d.lost==='number'?`${d.lost}の兵を失いました。`:'実際の損失を部隊に反映しています。'}`);
    case 'route_discovered':return text(`${c}之間的探索航行成功，新航路已顯示於地圖。`,`${c}を結ぶ探索航行が成功し、新航路が地図に表示されました。`);
    case 'march_arrived':return text(`${p}抵達${c}。入城或戰鬥依抵達時狀態處理。`,`${p}が${c}へ到着しました。到着時の状況に従い入城・戦闘を処理します。`);
    case 'march_returned':{
     const source=n.cities[0]||text('出發城','出発都市'),target=n.cities[1]||text('目的城','目的都市');
     if(d.reason==='army_lost')return text(`前往${target}的部隊遭遇災害，帶兵全損。武將返回${source}原編制，未發現新航路。`,`${target}へ向かう部隊は災害で全兵力を失いました。武将は${source}の元の所属部隊へ戻り、新航路は発見していません。`);
     if(d.reason==='target_changed')return text(`目的城${target}已易主，調動取消。武將保留在${source}的原編制。`, `目的都市${target}の所属が変わったため、移動を取り消しました。武将は${source}の元の所属部隊に残ります。`);
     if(d.reason==='route_blocked')return text(`前往${target}的途中城池易主，調動路線中斷。部隊返回${source}原編制。`,`${target}への経由都市の所属が変わり、移動経路が途切れました。部隊は${source}の元の編制へ戻ります。`);
     if(d.reason==='origin_changed')return text(`出發城${source}失陷或行軍人員已退場，原行軍取消。武將所屬及位置依目前戰局處理。`, `出発都市${source}の陥落、または行軍中の武将の退場により、元の行軍を取り消しました。武将の所属と所在地は現在の戦況に従います。`);
     return text(`前往${target}的原行軍已取消，請核對${source}與在途部隊的現有編制。`,`${target}への元の行軍を取り消しました。${source}と行軍中の部隊の現在の編制を確認してください。`);
    }
    case 'new_year':return text(`${row.year}年到來。人物年代、各城收入與體力恢復已核對。`,`${row.year}年を迎えました。武将の年代・都市収入・体力回復を確認しました。`);
    case 'campaign_victory':return text(`${f}完成天下統一。本次戰役已結算，可保存進度。`,`${f}が天下を統一しました。戦役の精算を終え、進行状況を保存できます。`);
    case 'campaign_defeat':return text(`${f}已無法繼續作戰。可保存結果或重新選擇劇本。`,`${f}は戦いを続けられなくなりました。結果を保存するか、シナリオを選び直せます。`);
    default:{const attacker=n.factions[0]||f;return text(`${attacker}的${d.coordinated?'多路部隊正協同':'部隊正'}朝${c}推進。`,`${attacker}の${d.coordinated?'複数部隊が連携して':'部隊が'}${c}へ進軍しています。`);}
   }
  }
  function illustration(rows){
   const row=rows[0],catalog=view?.catalog||{},world=catalog.world||{x:0,y:0,width:1352,height:1024,background:'/assets/map-navigation.png'};
   const ids=[...new Set(rows.flatMap(e=>[...e.person_ids,...(typeof e.details.actor==='string'?[e.details.actor]:[])]))].slice(0,4);
   const targetScene=new Set(['battle_started','battle_result','tactic','duel_started','duel_result','march_weather','route_discovered','march_arrived','ai_campaign']);
   const cityIds=targetScene.has(row.kind)?[...row.city_ids].reverse():row.city_ids;
   const cityId=cityIds.find(id=>catalog.cities?.some(c=>c.id===id))||catalog.factions?.find(f=>f.id===view?.game?.player)?.city;
   const city=catalog.cities?.find(c=>c.id===cityId),center=city?.position||[(world.x||0)+world.width/2,(world.y||0)+world.height/2];
   const background=catalog.map_presentation?.road_center_corrections?.backgrounds?.[world.background]||world.background;
   const safeBackground=/^\/assets\/map(?:-[a-z-]+)?\.png$/.test(background||'')?background:'/assets/map-navigation.png';
   const x=Math.max(world.x||0,Math.min(center[0]-144,(world.x||0)+world.width-288)),y=Math.max(world.y||0,Math.min(center[1]-86,(world.y||0)+world.height-172));
   const fill=catalog.map_presentation?.castle_fill_pixels||[],outline=catalog.map_presentation?.castle_outline_pixels||[];
   const sprite=city?[[outline,'#000'],[fill,'#fff']].map(([pixels,color])=>pixels.map(([dx,dy])=>`<rect x="${center[0]+dx}" y="${center[1]+dy}" width="4" height="4" fill="${color}"/>`).join('')).join(''):'';
   const art=`<svg class="event-map" viewBox="${x} ${y} 288 172" role="img" aria-label="${escape(text('事件所在地圖示意','出来事の場所を示す地図'))}"><image href="${safeBackground}" x="${world.x||0}" y="${world.y||0}" width="${world.width}" height="${world.height}"/>${sprite}</svg>`;
   const people=ids.map(id=>{const name=names({...row,person_ids:[id]}).people[0];return portraits?.entry?.(id)?`<figure class="event-person">${portraits.html(id,name,{size:'duel'})}<figcaption>${escape(name)}</figcaption></figure>`:'';}).join('');
   return `<div class="event-art">${art}${people?`<div class="event-people">${people}</div>`:''}</div><p class="event-art-caption">${escape(text('事件示意：目前地圖與武將像素肖像','場面イメージ：現在の地図と武将のドット肖像'))}</p>`;
  }
  function render(){
   if(!active||!modal||disposed)return;
   const row=active[0],period={1:'上旬',11:'中旬',21:'下旬'}[row.day],count=active.length>1?text(` · 共${active.length}項`,` · ${active.length}件`):'';
   modal.innerHTML=`<div data-event-root data-l10n-native="${locale()}"><div class="event-heading"><div><p class="event-kicker">${escape(historyMode?text('事件回顧','出来事の記録'):text('戰役事件','戦役の出来事'))} · ${shown}/${total}</p><h2 id="event-title">${escape(KINDS[row.kind][locale()==='ja'?1:0])}${escape(count)}</h2></div><label class="language-picker">${text('語言','言語')}<select data-language-picker aria-label="${text('切換語言','言語切替')}"><option value="zh-Hant" ${locale()==='zh-Hant'?'selected':''}>繁體中文</option><option value="ja" ${locale()==='ja'?'selected':''}>日本語</option></select></label></div><p class="event-date">${row.year}年${row.month}月${period}</p>${illustration(active)}<div id="event-description" class="event-description">${active.map(e=>`<p>${escape(description(e))}</p>`).join('')}</div><div class="dialog-actions event-actions">${queue.length?`<button data-event-skip>${text('略過本批','この一括表示を終了')}</button>`:''}<button class="primary" data-event-next autofocus>${queue.length?text('下一則','次へ'):text('返回戰役','戦役に戻る')}</button></div></div>`;
   modal.querySelector('[data-event-next]').onclick=advance;
   const skip=modal.querySelector('[data-event-skip]');if(skip)skip.onclick=clear;
   if(!modal.open)modal.showModal();
   modal.querySelector('[data-event-next]')?.focus({preventScroll:true});
  }
  function blocked(){return !modal||disposed||isBusy()||isPreview()||parent?.open;}
  function pump(){
   scheduled=false;if(active||!queue.length||blocked())return false;
   if(portraits?.load&&!portraitAttempted){portraitAttempted=true;Promise.resolve(portraits.load()).then(requestPump,requestPump);return false;}
   active=queue.shift();shown++;render();return true;
  }
  function requestPump(){if(disposed||scheduled)return;scheduled=true;schedule(pump);}
  function closeModal(){if(modal?.open)modal.close();}
  function advance(){if(queue.length){active=queue.shift();shown++;render();}else{active=null;historyMode=false;closeModal();}}
  function clear(){queue=[];active=null;historyMode=false;closeModal();}
  function observe(next,{baseline=false,newGame=false}={}){
   const nextKey=campaignKey(next),rows=eventRows(next),latest=rows.at(-1)?.id||0;view=next;refreshHistoryLabel();
   if(baseline||!nextKey||key!==nextKey||latest<cursor||newGame){clear();key=nextKey;cursor=newGame?0:latest;shown=0;total=0;}
   if(!nextKey||baseline)return;
   const fresh=rows.filter(row=>row.id>cursor);cursor=Math.max(cursor,latest);
   const visible=fresh.filter(row=>automatic(row,next.game.player));
   if(visible.length){const batches=groupRows(clone(visible));queue.push(...batches);if(!active&&shown===total){shown=0;total=0;}total+=batches.length;}
   requestPump();
  }
  function history(){
   if(blocked()||modal?.open)return false;
   view=getView()||view;const rows=eventRows(view);if(!rows.length)return false;
   clear();queue=groupRows(clone(rows));historyMode=true;shown=0;total=queue.length;requestPump();return true;
  }
  function onCancel(){queue=[];active=null;historyMode=false;}
  // Native close events are dispatched later. A previous close must not erase
  // a fresh history/new-game queue created before that event reaches us.
  function onClose(){if(modal?.open)return;if(active){active=null;queue=[];historyMode=false;}requestPump();}
  function onLanguage(){refreshHistoryLabel();if(active&&modal?.open)render();}
  modal?.addEventListener?.('cancel',onCancel);modal?.addEventListener?.('close',onClose);
  parent?.addEventListener?.('close',requestPump);doc?.addEventListener?.('game-language-change',onLanguage);
  refreshHistoryLabel();
  return Object.freeze({observe,pump:requestPump,history,clear,description,
   snapshot:()=>({key,cursor,pending:queue.map(group=>group.map(row=>row.id)),active:active?.map(row=>row.id)||null,historyMode,shown,total}),
   dispose(){clear();disposed=true;modal?.removeEventListener?.('cancel',onCancel);modal?.removeEventListener?.('close',onClose);parent?.removeEventListener?.('close',requestPump);doc?.removeEventListener?.('game-language-change',onLanguage);}
  });
 }
 if(typeof module==='object'&&module.exports)module.exports={create,validEvent,eventRows,campaignKey,groupRows,KINDS};else root.GameEvents={create};
})(typeof window==='object'?window:globalThis);
