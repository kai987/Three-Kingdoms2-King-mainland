'use strict';
let view=null, busy=false, selectedCity=null, mapMode='all', actor=null, target=null;
const $=s=>document.querySelector(s), dialog=$('#dialog');
const escapeHtml=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const name=id=>view.catalog.names[String(id)]||'武将';
const faction=id=>view.catalog.factions.find(f=>f.id===id)?.name||'守备军';
const cityName=id=>view.catalog.cities.find(c=>c.id===id)?.name||id;
function notice(text='',error=false){$('#notice').textContent=text;$('#notice').classList.toggle('error',error);}
async function request(path,body){
 const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const value=await response.json();
 if(!response.ok){if(response.status===409){view=await request('/api/state');render();}throw new Error(value.error||'操作未完成。');}
 return value;
}
async function command(kind,payload={}){
 if(busy)return false;
 busy=true;document.body.classList.add('busy');notice();
 try{view=await request('/api/command',{kind,payload,revision:view.revision});render();return true;}
 catch(e){notice(e.message,true);return false;}
 finally{await new Promise(resolve=>setTimeout(resolve,180));busy=false;document.body.classList.remove('busy');}
}
function openDialog(title,body,actions){
 if(busy)return;
 dialog.innerHTML=`<h2 id="dialog-title">${escapeHtml(title)}</h2>${body}<div class="dialog-actions">${actions}</div>`;
 if(!dialog.open)dialog.showModal();
 dialog.querySelectorAll('[data-cancel]').forEach(b=>b.onclick=()=>dialog.close());
}
function selectFaction(inDialog=false){
 const content=`<p class="intro">荆襄四城，七名武将。从217年11月开始一场演练。</p>
 <div class="choice-list">${view.catalog.factions.map(f=>`<label class="faction-choice"><input type="radio" name="faction" value="${f.id}" ${f.id==='shu'?'checked':''}>${escapeHtml(f.name)}<span>${escapeHtml(f.captain)} · ${escapeHtml(cityName(f.city))}</span></label>`).join('')}</div>
 <label class="seed-label" for="seed">战局编号<input id="seed" type="number" min="1" max="4294967295" step="1" value="2026"></label>`;
 const begin=async()=>{const f=document.querySelector('input[name=faction]:checked')?.value,seed=Number($('#seed').value);if(!Number.isInteger(seed)||seed<1||seed>4294967295)return notice('战局编号请填写1到4294967295之间的整数。',true);if(await command('new',{faction:f,seed})){selectedCity=view.catalog.factions.find(x=>x.id===f).city;actor=target=null;mapMode='region';dialog.close();render();}};
 if(inDialog){openDialog('重开演练',content,'<button data-cancel>取消</button><button class="primary" id="begin">开始演练</button>');}
 else{$('#inspector').innerHTML=`<div class="inspector-heading"><h2>选择势力</h2></div>${content}<div class="actions"><button class="primary" id="begin">开始演练</button></div>`;}
 $('#begin').onclick=begin;
}
function renderMap(){
 const game=view.game;
 const active=view.catalog.cities.filter(c=>view.catalog.active_cities.includes(c.id));
 $('#stage').innerHTML=`<div class="map-toolbar" role="group" aria-label="地图视角"><button id="region" class="${mapMode==='region'?'selected':''}" aria-pressed="${mapMode==='region'}">荆襄</button><button id="all-map" class="${mapMode==='all'?'selected':''}" aria-pressed="${mapMode==='all'}">全图</button></div>
 <svg id="world-map" viewBox="${mapMode==='region'?'550 285 430 350':'0 0 1352 1024'}" aria-label="96城地图，荆襄四城可操作"><image href="/assets/map.png" x="0" y="0" width="1352" height="1024"/>
 ${game?active.map(c=>`<g role="button" tabindex="0" class="city-hit faction-${game.cities[c.id].owner} ${selectedCity===c.id?'selected':''}" data-city="${c.id}" aria-label="${escapeHtml(c.name)}，${faction(game.cities[c.id].owner)}"><title>${escapeHtml(c.name)} · ${faction(game.cities[c.id].owner)}</title><rect x="${c.position[0]-21}" y="${c.position[1]-21}" width="42" height="42" rx="1"/></g>`).join(''):''}</svg>`;
 $('#region').onclick=()=>{mapMode='region';renderMap();};$('#all-map').onclick=()=>{mapMode='all';renderMap();};
 document.querySelectorAll('[data-city]').forEach(el=>{const choose=()=>{if(busy)return;selectedCity=el.dataset.city;if(view.game.phase==='city')renderCity();renderMap();};el.onclick=choose;el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}};});
}
function rosterRows(city){return city.roster.officer_ids.map(id=>{const o=view.game.officers[id];return `<tr title="体${o.health}，德${o.profile.virtue}，忠${o.loyalty}，经验${o.experience}"><td>${escapeHtml(name(id))}</td><td>${o.profile.martial_strength}</td><td>${o.profile.intellect}</td><td>${o.troops}</td></tr>`;}).join('');}
function renderCity(){
 const game=view.game,city=game.cities[selectedCity],owned=city.owner===game.player;
 $('#inspector').innerHTML=`<div class="inspector-heading"><h2>${escapeHtml(cityName(city.id))}</h2><span class="owner">${faction(city.owner)}</span></div>
 <dl class="resources"><dt>金钱</dt><dd>${city.gold}</dd><dt>粮食</dt><dd>${city.grain}</dd><dt>预备兵</dt><dd>${city.reserves}</dd></dl>
 <table class="roster-table"><thead><tr><th>武将</th><th>武</th><th>知</th><th>兵</th></tr></thead><tbody>${rosterRows(city)||'<tr><td colspan="4">暂无驻军</td></tr>'}</tbody></table>
 <p class="small">驻城 ${city.roster.officer_ids.length}/20；每方出战上限10人。${city.action_used?'本城本回合已行动。':''}</p>
 <div class="actions">${owned?`<div class="action-pair"><button id="allocate" class="primary" ${!city.roster.officer_ids.length?'disabled':''}>编兵</button><button id="depart" class="primary" ${city.action_used?'disabled':''}>出征</button></div><div class="secondary-row"><button id="recruit" ${city.action_used?'disabled':''}>征募预备兵</button></div>`:'<button id="home">返回本城</button>'}<button id="end-turn">结束回合</button></div>`;
 if(owned){$('#allocate').onclick=()=>allocate(city);$('#depart').onclick=()=>departure(city);$('#recruit').onclick=()=>{openDialog('征募预备兵','<p>花费20金钱、30粮食，征募100名预备兵。确认后消耗本城本回合行动。</p>','<button data-cancel>取消</button><button id="confirm-recruit" class="primary">确认征募</button>');$('#confirm-recruit').onclick=async()=>{if(await command('recruit',{city:city.id}))dialog.close();};};}
 else $('#home').onclick=()=>{selectedCity=Object.values(game.cities).find(c=>c.owner===game.player)?.id||selectedCity;render();};
 $('#end-turn').onclick=()=>command('end_turn');
}
function allocate(city){
 const ids=city.roster.officer_ids;
 openDialog('编兵',`<p>本城预备兵 ${city.reserves}。调整兵力不消耗城池行动。</p><label class="field" for="allocation-officer">武将<select id="allocation-officer">${ids.map(i=>`<option value="${i}">${escapeHtml(name(i))}</option>`).join('')}</select></label><label class="field" for="allocation-troops">目标兵力<input id="allocation-troops" type="number" min="0" max="999" step="1" value="${view.game.officers[ids[0]].troops}"></label><p class="small" id="allocation-preview"></p>`, '<button data-cancel>取消</button><button id="confirm-allocation" class="primary">确认编兵</button>');
 const preview=()=>{const o=view.game.officers[$('#allocation-officer').value],n=Number($('#allocation-troops').value),delta=n-o.troops;$('#allocation-preview').textContent=Number.isInteger(n)&&n>=0&&n<=999?`确认后本城预备兵 ${city.reserves-delta}。`:'请输入0到999之间的整数。';};
 $('#allocation-officer').onchange=()=>{$('#allocation-troops').value=view.game.officers[$('#allocation-officer').value].troops;preview();};$('#allocation-troops').oninput=preview;preview();
 $('#confirm-allocation').onclick=async()=>{const id=Number($('#allocation-officer').value),troops=Number($('#allocation-troops').value);if(await command('allocate',{city:city.id,officer:id,troops}))dialog.close();};
}
function departure(city){
 const targets=Object.values(view.game.cities).filter(c=>c.owner!==view.game.player&&view.catalog.links.some(e=>e.includes(city.id)&&e.includes(c.id)));
 if(!targets.length)return notice('没有相邻的敌方城池。');
 const draft={source:city.id,target:targets[0].id,officers:[]};
 const pick=()=>{
  openDialog('选择出征名单',`<label class="field" for="departure-target">目标城池<select id="departure-target">${targets.map(c=>`<option value="${c.id}" ${draft.target===c.id?'selected':''}>${escapeHtml(cityName(c.id))} · ${faction(c.owner)}</option>`).join('')}</select></label><p>选择1—10名武将，第一位为主将。</p><div class="officer-picker">${city.roster.officer_ids.map(i=>{const o=view.game.officers[i];return `<label><input type="checkbox" name="depart-officer" value="${i}" ${draft.officers.includes(i)?'checked':''} ${o.troops===0?'disabled':''}>${escapeHtml(name(i))}　${o.troops}兵</label>`;}).join('')}</div>`, '<button data-cancel>取消出征</button><button id="review-departure" class="primary">下一步</button>');
  $('#review-departure').onclick=()=>{draft.target=$('#departure-target').value;draft.officers=[...dialog.querySelectorAll('input[name=depart-officer]:checked')].map(x=>Number(x.value));if(!draft.officers.length||draft.officers.length>10)return notice('请选择1到10名有兵力的武将。',true);confirm();};
 };
 const confirm=()=>{const troops=draft.officers.reduce((n,i)=>n+view.game.officers[i].troops,0),cost=Math.max(1,Math.floor(troops/25));openDialog('出征确认',`<p>${escapeHtml(cityName(city.id))}出发，目标${escapeHtml(cityName(draft.target))}。</p><p>${draft.officers.map(i=>escapeHtml(name(i))).join('、')}，共${troops}兵，耗粮${cost}。</p><p class="small">确认后才出征。现在取消不会扣粮或消耗行动。</p>`,'<button data-cancel>取消出征</button><button id="back-to-pick">返回名单</button><button id="confirm-departure" class="primary">确认出征</button>');$('#back-to-pick').onclick=pick;$('#confirm-departure').onclick=async()=>{actor=target=null;if(await command('depart',draft))dialog.close();};};
 pick();
}
function renderBattle(){
 const game=view.game,b=game.battle;
 const usable=b.attackers.filter(u=>u.troops>0&&!b.used.includes(u.id)),enemies=b.defenders.filter(u=>u.troops>0);
 if(!usable.some(u=>u.id===actor))actor=usable[0]?.id??null;
 if(!enemies.some(u=>u.id===target))target=enemies[0]?.id??null;
 const unitList=(units,side)=>units.map(u=>`<button class="unit ${u.troops===0?'routed':''}" data-${side}="${u.id}" aria-pressed="${(side==='actor'?actor:target)===u.id}" ${game.phase!=='battle'||u.troops===0||(side==='actor'&&b.used.includes(u.id))?'disabled':''}><span>${escapeHtml(name(u.id))}</span><span class="troops">${u.troops}兵</span></button>`).join('');
 $('#stage').innerHTML=`<div class="arena"><div class="arena-heading"><h2>${escapeHtml(cityName(b.target))}之战</h2><span>第${b.round}轮</span></div><div class="armies"><section class="army"><h3>本方</h3><div class="unit-list">${unitList(b.attackers,'actor')}</div></section><section class="army"><h3>守方</h3><div class="unit-list">${unitList(b.defenders,'target')||'<p>无守军</p>'}</div></section></div><p class="combat-hint">选择本方部队和守方目标。每支本方部队每轮行动一次，守方随后反击。</p></div>`;
 $('[data-actor]')&&document.querySelectorAll('[data-actor]').forEach(el=>el.onclick=()=>{actor=Number(el.dataset.actor);renderBattle();});document.querySelectorAll('[data-target]').forEach(el=>el.onclick=()=>{target=Number(el.dataset.target);renderBattle();});
 const labels={victory:'本方胜利',defeat:'本方败退',retreat:'本方退却'};
 $('#inspector').innerHTML=`<h2 class="battle-title">${game.phase==='result'?'战果':'本方行动'}</h2>${game.phase==='result'?`<p class="outcome">${labels[b.outcome]}</p><p>接收战果后，兵员、名册与城池资源一起结算。</p>`:`<p class="phase-description">本方${b.attackers.length}/10人，守方${b.defenders.length}/10人。</p><p>选择：${actor===null?'—':escapeHtml(name(actor))} 对 ${target===null?'—':escapeHtml(name(target))}</p>`}<ul class="battle-log">${b.log.slice(-8).map(t=>`<li>${escapeHtml(t)}</li>`).join('')}</ul><div class="actions">${game.phase==='result'?'<button id="settle" class="primary">接收战果</button>':`<button id="attack" class="primary" ${actor===null||target===null?'disabled':''}>攻击</button><button id="retreat">退却</button>`}</div>`;
 if(game.phase==='result')$('#settle').onclick=async()=>{const next=b.outcome==='victory'?b.target:b.source;if(await command('settle',{battle_id:b.id})){selectedCity=next;render();}};
 else{$('#attack').onclick=()=>command('attack',{battle_id:b.id,actor,target});$('#retreat').onclick=()=>{openDialog('退却确认','<p>剩余部队返回原城。已经发生的兵损和出征耗粮保留。</p>','<button data-cancel>继续作战</button><button id="confirm-retreat" class="primary">确认退却</button>');$('#confirm-retreat').onclick=async()=>{if(await command('retreat',{battle_id:b.id}))dialog.close();};};}
}
function render(){
 if(!view)return;
 const game=view.game;
 $('#save').disabled=!game;
 $('#restart').disabled=!game;
 $('#date').textContent=game?`${game.year}年${game.month}月　第${game.turn}回合`:'选择势力';
 if(!game){renderMap();selectFaction();return;}
 if(!selectedCity||!game.cities[selectedCity])selectedCity=Object.values(game.cities).find(c=>c.owner===game.player)?.id||view.catalog.active_cities[0];
 if(game.phase==='battle'||game.phase==='result')renderBattle();
 else{renderMap();if(game.phase==='city')renderCity();else if(game.phase==='ai'){$('#inspector').innerHTML='<div class="inspector-heading"><h2>电脑回合</h2></div><p>电脑势力整备驻军，随后收取月度收入，进入下一个本方回合。</p><div class="actions"><button id="run-ai" class="primary">执行电脑行动</button></div>';$('#run-ai').onclick=()=>command('ai',{turn:game.turn});}else{$('#inspector').innerHTML='<h2>演练结束</h2><p>本方已无可用驻军。</p><div class="actions"><button id="play-again" class="primary">重新选择势力</button></div>';$('#play-again').onclick=()=>selectFaction(true);}}
 $('#journal').innerHTML=game.log.slice(-5).map(t=>`<li>${escapeHtml(t)}</li>`).join('');
}
$('#rules').onclick=()=>openDialog('规则说明',`<div class="rules-body"><p>每城20人；每方出战最多10人，包含主将。</p><ul>${view.catalog.notes.map(t=>`<li>${escapeHtml(t)}</li>`).join('')}</ul><p>总人物库${view.catalog.library_count}人。本局只使用已配置且当年可登场的7人。战局编号决定随机序列，保存会保留其进度。</p></div>`,'<button data-cancel>返回演练</button>');
$('#restart').onclick=()=>selectFaction(true);
$('#save').onclick=async()=>{
 if(busy)return;
 try{const save=await request('/api/save');localStorage.setItem('three-kingdoms-demo-save',JSON.stringify(save));const blob=new Blob([JSON.stringify(save,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='荆襄演练存档.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice('进度已保存。可用“读取进度”恢复，也可保留下载的存档文件。');}catch(e){notice(e.message,true);}
};
async function loadSave(save){if(busy)return;busy=true;document.body.classList.add('busy');try{view=await request('/api/load',{save,revision:view.revision});selectedCity=null;actor=target=null;dialog.close();render();notice('进度已恢复。');}catch(e){notice(e.message,true);}finally{await new Promise(resolve=>setTimeout(resolve,180));busy=false;document.body.classList.remove('busy');}}
$('#load').onclick=()=>{const saved=localStorage.getItem('three-kingdoms-demo-save');openDialog('读取进度',`<div class="save-actions"><button id="load-local" ${saved?'':'disabled'}>读取本机保存</button><label class="field" for="save-file">选择存档文件<input id="save-file" type="file" accept=".json,application/json"></label></div><p class="small">存档无效时会保留当前进度。</p>`,'<button data-cancel>取消</button>');$('#load-local').onclick=()=>{try{loadSave(JSON.parse(saved));}catch(e){notice('存档无效，当前进度未改变。',true);}};$('#save-file').onchange=async()=>{try{const file=$('#save-file').files[0];if(!file)return;if(file.size>2*1024*1024)throw new Error('too large');await loadSave(JSON.parse(await file.text()));}catch(e){notice('存档无效，当前进度未改变。',true);}};};
request('/api/state').then(value=>{view=value;render();}).catch(e=>notice('游戏未能载入，请确认本地服务正在运行。',true));
