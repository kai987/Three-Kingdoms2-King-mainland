'use strict';
let view=null, busy=false, selectedCity=null, mapMode='all', actor=null, target=null, showLegacy=false, mapPositions=null, setupPreview=null;
const $=s=>document.querySelector(s), dialog=$('#dialog');
const escapeHtml=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const name=id=>view.catalog.names[String(id)]||'武将';
const faction=id=>view.catalog.factions.find(f=>f.id===id)?.name||'守备军';
const capacity=()=>view.catalog.rules.city_officer_capacity;
const mapPosition=c=>mapPositions?.positions[c.id]||c.position;
const cityName=id=>setupPreview?.city_names[id]||view.catalog.cities.find(c=>c.id===id)?.name||id;
const mapColor=id=>view.catalog.map_presentation.colors[id]||view.catalog.map_presentation.colors.neutral;
const displayLog=text=>view.catalog.cities.filter(c=>c.administrative_name!==c.name).reduce((s,c)=>s.replaceAll(c.administrative_name,c.name),text);
function notice(text='',error=false){$('#notice').textContent=text;$('#notice').classList.toggle('error',error);}
function setBusy(value){busy=value;document.body.classList.toggle('busy',value);if($('#city-jump'))$('#city-jump').disabled=value;}
async function request(path,body){
 const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const value=await response.json();
 if(!response.ok){if(response.status===409){view=await request('/api/state');render();}throw new Error(value.error||'操作未完成。');}
 return value;
}
async function command(kind,payload={}){
 if(busy)return false;
 setBusy(true);notice();
 try{view=await request('/api/command',{kind,payload,revision:view.revision});render();return true;}
 catch(e){notice(e.message,true);return false;}
 finally{await new Promise(resolve=>setTimeout(resolve,180));setBusy(false);}
}
function openDialog(title,body,actions){
 if(busy)return;
 dialog.innerHTML=`<h2 id="dialog-title">${escapeHtml(title)}</h2>${body}<div class="dialog-actions">${actions}</div>`;
 if(!dialog.open)dialog.showModal();
 dialog.querySelectorAll('[data-cancel]').forEach(b=>b.onclick=()=>dialog.close());
}
function selectFaction(){
 const current=view.catalog.scenario_id;
 if(dialog.open)dialog.close();
 const draw=(scenario)=>{
  const option=view.catalog.scenarios.find(x=>x.id===scenario), expanded=option.cities===96;
  const preferred=option.factions.some(f=>f.id==='shu')?'shu':option.factions[0].id;
  setupPreview={...option,faction:preferred,focus:option.factions.find(f=>f.id===preferred).city};
  const groups=[['base','原版本篇 · 7剧本'],['pk','威力加强版本篇 · 4剧本'],['legacy','旧版目录 · 存档兼容']];
  const legacy=showLegacy||!option.main_scenario||option.archived;
  const options=groups.map(([group,label])=>{const rows=view.catalog.scenarios.filter(x=>(x.main_scenario&&!x.archived?x.main_scenario.group:'legacy')===group&&(group!=='legacy'||legacy)).sort((a,b)=>a.year-b.year||a.month-b.month);return rows.length?`<optgroup label="${label}">${rows.map(x=>`<option value="${x.id}" ${x.id===scenario?'selected':''}>${escapeHtml(x.title)}${x.archived?'（旧版）':''}</option>`).join('')}</optgroup>`:'';}).join('');
  const content=`<label class="field" for="scenario">选择剧本<select id="scenario">${options}</select></label><label class="legacy-choice"><input id="legacy-choice" type="checkbox" ${legacy?'checked':''}>显示旧版战役</label><p class="intro">${option.year}年${option.month}月 · ${option.cities}城 · 每城${option.capacity}人<br>开局在籍${option.serving}人，在野${option.free}人。</p>${option.main_scenario?`<details class="scenario-notes"><summary>剧本资料与配置范围</summary><p>${escapeHtml(option.main_scenario.summary)}</p><p>本作96城改编，现有${option.configured}份完整属性。${option.main_scenario.virtue_default_policy?'部分德值按用户指定暂设60，人物库可查评分来源。':''}新年代的部分归属为前后快照推定，未确认者不自动入场。</p><a href="${escapeHtml(option.main_scenario.official_source)}" target="_blank" rel="noopener noreferrer">查看官方剧本目录</a></details>`:''}
  <div class="choice-list">${option.factions.map(f=>`<label class="faction-choice"><input type="radio" name="faction" value="${f.id}" ${f.id===preferred?'checked':''}><svg class="faction-swatch" width="16" height="16" aria-hidden="true"><rect width="16" height="16" fill="${mapColor(f.id)}"/></svg>${escapeHtml(f.name)}<span>${escapeHtml(f.captain)} · ${escapeHtml(cityName(f.city))}</span></label>`).join('')}</div>
  <p id="setup-summary" class="small" aria-live="polite"></p><label class="seed-label" for="seed">战局编号<input id="seed" type="number" min="1" max="4294967295" step="1" value="2026"></label>`;
  $('#inspector').innerHTML=`<div class="inspector-heading"><h2>选择势力</h2></div>${content}<div class="actions"><button class="primary" id="begin">开始战役</button>${view.game?'<button id="cancel-setup">返回当前战役</button>':''}</div>`;
  const refreshPreview=()=>{
   const chosen=option.factions.find(f=>f.id===setupPreview.faction),count=Object.values(option.initial_owners).filter(owner=>owner===chosen.id).length;
   $('#setup-summary').textContent=`${chosen.name} · ${count}座城池 · 根据地${cityName(chosen.city)}。地图已预览本剧本归属，开始后才建立新战役。`;
   $('#library').disabled=true;renderMap();
  };
  document.querySelectorAll('input[name=faction]').forEach(input=>input.onchange=()=>{setupPreview.faction=input.value;setupPreview.focus=option.factions.find(f=>f.id===input.value).city;refreshPreview();});
  if($('#cancel-setup'))$('#cancel-setup').onclick=()=>{setupPreview=null;render();};
  refreshPreview();
  $('#scenario').onchange=()=>draw($('#scenario').value);
  $('#legacy-choice').onchange=()=>{showLegacy=$('#legacy-choice').checked;draw(!showLegacy&&(!option.main_scenario||option.archived)?view.catalog.scenarios.find(x=>x.main_scenario&&!x.archived)?.id:scenario);};
  $('#begin').onclick=async()=>{
   const f=document.querySelector('input[name=faction]:checked')?.value,seed=Number($('#seed').value);
   if(!Number.isInteger(seed)||seed<1||seed>4294967295)return notice('战局编号请填写1到4294967295之间的整数。',true);
   const pending=setupPreview;setupPreview=null;
   if(await command('new',{faction:f,seed,scenario})){
    selectedCity=view.catalog.factions.find(x=>x.id===f).city;actor=target=null;mapMode=expanded?'all':'region';dialog.close();render();
   }else{setupPreview=pending;renderMap();}
  };
 };
 draw(current);
}
function renderMap(){
 const game=view.game,preview=setupPreview,owners=preview?.initial_owners||Object.fromEntries(Object.values(game?.cities||{}).map(c=>[c.id,c.owner]));
 const active=view.catalog.cities.filter(c=>(preview?.active_cities||view.catalog.active_cities).includes(c.id));
 const factions=preview?.factions||view.catalog.factions,ownerName=id=>factions.find(f=>f.id===id)?.name||'守备军';
 const focused=preview?.focus||selectedCity,selected=view.catalog.cities.find(c=>c.id===focused),center=selected?mapPosition(selected):[760,440];
 const box=mapMode==='region'?`${Math.max(0,Math.min(922,center[0]-215))} ${Math.max(0,Math.min(674,center[1]-175))} 430 350`:'0 0 1352 1024';
 const date=preview||game||view.catalog.scenarios.find(s=>s.id===view.catalog.scenario_id);
 if(preview)$('#date').textContent=`${date.year}年${date.month}月 · 选择势力`;
 const castles=active.map(c=>{
  const [x,y]=mapPosition(c),owner=owners[c.id]||'neutral';
  const colored=view.catalog.map_presentation.castle_fill_pixels.map(([dx,dy])=>`<rect class="castle-fill" x="${x+dx}" y="${y+dy}" width="4" height="4" fill="${mapColor(owner)}"/>`).join('');
  return `<g role="button" tabindex="0" class="city-hit ${focused===c.id?'selected':''} ${preview&&owner===preview.faction?'preview-owned':''}" data-city="${c.id}" data-owner="${owner}" aria-label="${escapeHtml(cityName(c.id))}，${escapeHtml(ownerName(owner))}"><title>${escapeHtml(cityName(c.id))} · ${escapeHtml(ownerName(owner))}</title>${colored}<rect class="city-outline" x="${x-21}" y="${y-21}" width="42" height="42"/><rect class="owner-marker" x="${x-8}" y="${y+18}" width="16" height="3" fill="${mapColor(owner)}"/></g>`;
 }).join('');
 $('#stage').innerHTML=`<div class="map-toolbar" role="group" aria-label="地图视角"><button id="region" class="${mapMode==='region'?'selected':''}" aria-pressed="${mapMode==='region'}">本城</button><button id="all-map" class="${mapMode==='all'?'selected':''}" aria-pressed="${mapMode==='all'}">全图</button><label class="city-jump">城池 <select id="city-jump" aria-label="选择城池" ${busy?'disabled':''}>${active.map(c=>`<option value="${c.id}" ${c.id===focused?'selected':''}>${escapeHtml(cityName(c.id))} · ${escapeHtml(ownerName(owners[c.id]))}</option>`).join('')}</select></label></div>
 <svg id="world-map" viewBox="${box}" aria-label="96城地图，${active.length}城开放"><image href="${view.catalog.map_presentation.background}" x="0" y="0" width="1352" height="1024"/>${castles}</svg>
 <time id="map-date" datetime="${String(date.year).padStart(4,'0')}-${String(date.month).padStart(2,'0')}" aria-label="${date.year}年${date.month}月">${date.year}年<span>${date.month}月</span></time>`;
 const choose=id=>{if(busy)return;if(preview){preview.focus=id;renderMap();return;}selectedCity=id;if(game.phase==='city')renderCity();renderMap();};
 $('#region').onclick=()=>{mapMode='region';renderMap();};$('#all-map').onclick=()=>{mapMode='all';renderMap();};
 $('#city-jump').onchange=()=>choose($('#city-jump').value);
 document.querySelectorAll('[data-city]').forEach(el=>{el.onclick=()=>choose(el.dataset.city);el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(el.dataset.city);}};});
}

function rosterRows(city){return city.roster.officer_ids.map(id=>{const o=view.game.officers[id];return `<tr title="体${o.health}，德${o.profile.virtue}，忠${o.loyalty}，经验${o.experience}"><td>${escapeHtml(name(id))}</td><td>${o.profile.martial_strength}</td><td>${o.profile.intellect}</td><td>${o.troops}</td></tr>`;}).join('');}
function renderCity(){
 const game=view.game,city=game.cities[selectedCity],owned=city.owner===game.player;
 $('#inspector').innerHTML=`<div class="inspector-heading"><h2>${escapeHtml(cityName(city.id))}</h2><span class="owner">${faction(city.owner)}</span></div>
 <dl class="resources"><dt>金钱</dt><dd>${city.gold}</dd><dt>粮食</dt><dd>${city.grain}</dd><dt>预备兵</dt><dd>${city.reserves}</dd></dl>
 <div class="roster-scroll"><table class="roster-table"><thead><tr><th>武将</th><th>武</th><th>知</th><th>兵</th></tr></thead><tbody>${rosterRows(city)||'<tr><td colspan="4">暂无驻军</td></tr>'}</tbody></table></div>
 <p class="small">驻城 ${city.roster.officer_ids.length}/${capacity()}；每方出战上限10人。${city.action_used?'本城本回合已行动。':''}</p>
 <div class="actions">${owned?`<div class="action-pair"><button id="allocate" class="primary" ${!city.roster.officer_ids.length?'disabled':''}>编兵</button><button id="depart" class="primary" ${city.action_used?'disabled':''}>出征</button></div><div class="action-pair secondary-row">${view.catalog.rules.expanded_campaign?`<button id="recruit-officer" ${city.action_used||!city.roster.officer_ids.length?'disabled':''}>招募 / 劝降</button><button id="transfer" ${city.action_used||!city.roster.officer_ids.length?'disabled':''}>调动武将</button>`:''}</div><div class="secondary-row"><button id="recruit" ${city.action_used?'disabled':''}>征募预备兵</button></div>`:'<button id="home">返回本城</button>'}<button id="end-turn">结束回合</button></div>`;
 if(owned){$('#allocate').onclick=()=>allocate(city);$('#depart').onclick=()=>departure(city);$('#recruit').onclick=()=>{openDialog('征募预备兵','<p>花费20金钱、30粮食，征募100名预备兵。确认后消耗本城本回合行动。</p>','<button data-cancel>取消</button><button id="confirm-recruit" class="primary">确认征募</button>');$('#confirm-recruit').onclick=async()=>{if(await command('recruit',{city:city.id}))dialog.close();};};}
 else $('#home').onclick=()=>{selectedCity=Object.values(game.cities).find(c=>c.owner===game.player)?.id||selectedCity;render();};
 if($('#recruit-officer'))$('#recruit-officer').onclick=()=>recruitOfficer(city);
 if($('#transfer'))$('#transfer').onclick=()=>transferCity(city);
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
  openDialog('选择出征名单',`<label class="field" for="departure-target">目标城池<select id="departure-target">${targets.map(c=>`<option value="${c.id}" ${draft.target===c.id?'selected':''}>${escapeHtml(cityName(c.id))} · ${faction(c.owner)}</option>`).join('')}</select></label><p>选择1—10名武将，第一位为主将。</p><div class="officer-picker">${city.roster.officer_ids.map(i=>{const o=view.game.officers[i];return `<label><input type="checkbox" name="depart-officer" value="${i}" ${draft.officers.includes(i)?'checked':''} ${o.troops===0||view.game.extension?.officer_actions?.[i]===view.game.turn?'disabled':''}>${escapeHtml(name(i))}　${o.troops}兵</label>`;}).join('')}</div>`, '<button data-cancel>取消出征</button><button id="review-departure" class="primary">下一步</button>');
  $('#review-departure').onclick=()=>{draft.target=$('#departure-target').value;draft.officers=[...dialog.querySelectorAll('input[name=depart-officer]:checked')].map(x=>Number(x.value));if(!draft.officers.length||draft.officers.length>10)return notice('请选择1到10名有兵力的武将。',true);confirm();};
 };
 const confirm=()=>{const troops=draft.officers.reduce((n,i)=>n+view.game.officers[i].troops,0),cost=Math.max(1,Math.floor(troops/25));openDialog('出征确认',`<p>${escapeHtml(cityName(city.id))}出发，目标${escapeHtml(cityName(draft.target))}。</p><p>${draft.officers.map(i=>escapeHtml(name(i))).join('、')}，共${troops}兵，耗粮${cost}。</p><p class="small">确认后才出征。现在取消不会扣粮或消耗行动。</p>`,'<button data-cancel>取消出征</button><button id="back-to-pick">返回名单</button><button id="confirm-departure" class="primary">确认出征</button>');$('#back-to-pick').onclick=pick;$('#confirm-departure').onclick=async()=>{actor=target=null;if(await command('depart',draft))dialog.close();};};
 pick();
}

function recruitOfficer(city){
 const free=view.catalog.recruitable?.[city.id]||[],enemy=view.catalog.persuadable?.[city.id]||[];
 if(!free.length&&!enemy.length)return notice('附近暂无可招募的在野武将或可劝降的敌将。可在“人物库”查看年代与配置。');
 openDialog('招募与劝降',`<label class="field">人事方式<select id="recruit-mode"><option value="recruit_officer" ${!free.length?'disabled':''}>在野招募 · 60金</option><option value="persuade_officer" ${!enemy.length?'disabled':''} ${!free.length?'selected':''}>邻城劝降 · 100金</option></select></label><p>一次寻访消耗本城行动，对方可能拒绝。取消不扣资源；君主不能直接劝降。</p><label class="field">执行武将<select id="recruit-actor">${city.roster.officer_ids.map(i=>`<option value="${i}" ${view.game.extension.officer_actions[i]===view.game.turn?'disabled':''}>${escapeHtml(name(i))} · 德${view.game.officers[i].profile.virtue}</option>`).join('')}</select></label><label class="field">目标武将<select id="recruit-person"></select></label><p class="small">最多${capacity()}人。转属成功后保留体力、带兵、装备和经验；忠诚按本作招募规则重新结算。</p>`,'<button data-cancel>取消</button><button id="confirm-officer" class="primary">确认寻访</button>');
 const draw=()=>{$('#recruit-person').innerHTML=($('#recruit-mode').value==='recruit_officer'?free:enemy).map(i=>`<option value="${i}">${escapeHtml(name(i))}${view.game.officers[i].faction_id?' · 忠'+view.game.officers[i].loyalty:''}</option>`).join('');};
 $('#recruit-mode').onchange=draw;draw();
 $('#confirm-officer').onclick=async()=>{if(await command($('#recruit-mode').value,{city:city.id,actor:Number($('#recruit-actor').value),officer:Number($('#recruit-person').value)}))dialog.close();};
}
function transferCity(city){
 const destinations=Object.values(view.game.cities).filter(c=>c.id!==city.id&&c.owner===view.game.player);
 openDialog('调动武将',`<p>沿连续的本方道路调动，费用为每人每段道路5粮。消耗出发城行动，目的城仍最多${capacity()}人。</p><label class="field">目的城<select id="transfer-city">${destinations.map(c=>`<option value="${c.id}">${escapeHtml(cityName(c.id))} · ${c.roster.officer_ids.length}/${capacity()}人</option>`).join('')}</select></label><div class="officer-picker">${city.roster.officer_ids.map(i=>`<label><input type="checkbox" name="transfer-officer" value="${i}" ${view.game.extension?.officer_actions?.[i]===view.game.turn?'disabled':''}>${escapeHtml(name(i))} · ${view.game.officers[i].troops}兵</label>`).join('')}</div>`,'<button data-cancel>取消</button><button id="confirm-transfer" class="primary">确认调动</button>');
 $('#confirm-transfer').onclick=async()=>{const ids=[...dialog.querySelectorAll('input[name=transfer-officer]:checked')].map(e=>Number(e.value));if(await command('transfer',{source:city.id,target:$('#transfer-city').value,officers:ids}))dialog.close();};
}
function showLibrary(){
 if(!view.catalog.library)return notice('请进入九十六城扩展战役查看千人配置状态。');
 openDialog('千人武将库',`<p>${view.catalog.coverage.configured_profiles}人属性齐全，${view.catalog.coverage.pending_profiles}人待配置。${view.catalog.coverage.default_virtue_profiles?`${view.catalog.coverage.history_designs_total}人参考史料评分，${view.catalog.coverage.default_virtue_profiles}人默认德60，1人沿用原作基线。`:view.catalog.coverage.health_configured?'体力与适性已覆盖1000人；缺德者仍待配置。':''}点击姓名查看评分依据与本年代驻城安排。</p><div class="library-tools"><input id="library-search" aria-label="检索武将" placeholder="姓名、别名或人物编号"><select id="library-filter" aria-label="人物筛选"><option value="all">全部1000人</option><option value="ready">属性齐全</option><option value="rated">史料参考德</option><option value="default60">默认德60</option><option value="available">年表资格合格</option><option value="free">已登场在野</option><option value="missing">待配置</option></select></div><div id="library-results"></div><div class="library-tools"><button id="library-prev">上一页</button><span id="library-count"></span><button id="library-next">下一页</button></div>`,'<button data-cancel>返回战役</button>');
 let page=0;
 const labels={not_born:'未出生',not_appeared:'未出仕',available:'年代合格',death_year_review:'卒年待核',dead:'已过卒年',unknown:'年代待核'};
 const fields={health_max:'体力',martial_strength:'武',intellect:'知',virtue:'德',terrain_affinity:'适性'};
 const draw=()=>{const q=$('#library-search').value.trim(),filter=$('#library-filter').value;const people=view.catalog.library.filter(p=>(!q||[p.name,p.person_id,...p.aliases].some(s=>s.includes(q)))&&(filter==='all'||filter==='ready'&&!p.missing.length||filter==='available'&&p.year_state==='available'||filter==='free'&&p.alive&&p.faction===null||filter==='missing'&&p.missing.length||filter==='rated'&&p.virtue_design?.status==='configured_design'||filter==='default60'&&p.virtue_design?.status==='configured_default'));const max=Math.max(0,Math.ceil(people.length/12)-1);page=Math.min(page,max);
 $('#library-results').innerHTML=`<table class="library-table"><thead><tr><th>武将</th><th>生/仕/卒</th><th>武/知/德</th><th>状态</th></tr></thead><tbody>${people.slice(page*12,(page+1)*12).map(p=>`<tr><td><button class="person-detail" data-person="${p.id}">${escapeHtml(p.name)}</button></td><td>${p.birth}/${p.service}/${p.death}</td><td>${p.martial??'待填'}/${p.intellect??'待填'}/${p.virtue??'待填'}${p.virtue_design?.status==='configured_default'?'（默认）':''}</td><td>${p.missing.length?'待补：'+p.missing.map(k=>fields[k]).join('、'):p.era_assignment?.status==='pending_history'?'归属待考':p.faction?faction(p.faction):p.alive===false?'已退出':p.alive?'在野 · '+escapeHtml(cityName(p.location)):labels[p.year_state]}</td></tr>`).join('')}</tbody></table>`;
 dialog.querySelectorAll('[data-person]').forEach(el=>el.onclick=()=>showPerson(Number(el.dataset.person)));
 $('#library-count').textContent=`${people.length}人 · ${page+1}/${max+1}页`;$('#library-prev').disabled=page===0;$('#library-next').disabled=page===max;};
 $('#library-search').oninput=$('#library-filter').onchange=()=>{page=0;draw();};$('#library-prev').onclick=()=>{page--;draw();};$('#library-next').onclick=()=>{page++;draw();};draw();
}
function virtueDescription(p){
 const d=p.virtue_design;
 if(d?.status==='configured_default')return `<p><strong>德60 · 用户指定默认值</strong></p><p>${escapeHtml(d.design_rationale)}</p><p class="small">授权日期 ${escapeHtml(d.authorized_on)}。尚无本作逐人四维评分，不代表历史评价；数值已用于本局规则。</p>`;
 if(d?.status==='configured_design')return `<p>${escapeHtml(d.design_rationale||d.notes||'逐人史料参考设计。')}</p>${d.calibration?`<p>尺度对照：${escapeHtml(d.calibration.name)}（德${d.calibration.virtue}）。本人的四维按所列事迹独立评分。</p>`:''}<p>恤民 ${d.dimensions.care} · 公正 ${d.dimensions.fairness} · 操守 ${d.dimensions.integrity} · 信义 ${d.dimensions.trust}。${d.confidence==='low'?'史料有限，低置信初评；':''}德是生涯综合游戏评分。</p><ul>${d.sources.map(s=>`<li><a href="${escapeHtml(s.url)}" target="_blank" rel="noreferrer">${escapeHtml(s.work+' · '+s.section)}</a></li>`).join('')}</ul>`;
 return `<p>${p.virtue===null?'史料与独立德评分尚待补齐，当前不进入战局。':'沿用原版人物基线，历史德重评待补。'}</p>`;
}
function showPerson(id){
 const p=view.catalog.library.find(x=>x.id===id),a=p.era_assignment;
 const affinity={0:'平地',1:'山地',2:'水地'};
 const sourceState={serving:'仕官',free:'在野',undiscovered:'未发现',not_appeared:'尚未登场',dead:'已故',unreviewed:'转属待复核'};
 const current=view.game?Object.values(view.game.cities).find(c=>c.roster.officer_ids.includes(id))?.id:null;
 openDialog(`${p.name} · 人物配置`,`<p class="small">${escapeHtml(p.person_id)} · 独立编号 ${id}</p><p>体力上限 ${p.health_max??'待配置'}；适性 ${affinity[p.affinity]??'待配置'}。体力与适性是本作初始化规则。</p><p>武 ${p.martial??'待填'} / 知 ${p.intellect??'待填'} / 德 ${p.virtue??'待考'}。武知来自第三方SAN14数值转写，年代为来源游戏设定。</p>${virtueDescription(p)}${a?`${a.membership_resolution?`<p>本篇归属依据：${escapeHtml({chapter_leader_setup:'剧本君主配置',reviewed_transition:'本作转属复核',bracketing_affiliation_agreement_inference:'前后快照归属一致（推定，未证实连续仕官）',bracketing_free_location_agreement_inference:'前后快照在野地点一致（推定）',pending_history:'归属待考，未自动加入本局'}[a.membership_resolution.basis]||'待核')}。</p>${a.membership_resolution.override?`<p class="small">${escapeHtml(a.membership_resolution.override.basis)}</p>`:''}`:''}${a.membership_revision?`<p>历史与分组修订：${escapeHtml(a.membership_revision.reason)}</p>`:''}<p>开局来源：${escapeHtml(a.source_ruler||sourceState[a.source_status]||'状态待核')}。开局规划：${escapeHtml(a.city?cityName(a.city):'驻城待考')}；${escapeHtml(a.faction?faction(a.faction):a.source_status==='unreviewed'?'归属待考':a.source_status==='dead'?'不登场':a.source_status==='not_appeared'?'尚未登场':a.source_status==='serving'?'势力待接入':'在野')}。</p><p class="small">来源身份与驻城分开记录。驻城使用地名映射或本作区域配置，不能当作已考证的历史驻军地点。${a.death_year_resolved?'本剧本配置为卒年开局仍在世，后续按年粒度处理。':''}</p>`:''}${p.alive?`<p>当前战局：${escapeHtml(p.faction?faction(p.faction):'在野')} · ${escapeHtml(cityName(current||p.location||'待归城'))}</p>`:''}`,'<button id="back-library">返回武将库</button><button data-cancel>返回战役</button>');
 $('#back-library').onclick=showLibrary;
}
function tactics(b){
 openDialog('选择计略',`<p>本队气力${b.extended.support[actor].energy}/18；每轮回复4。地形：${{plain:'平地',mountain:'山地',water:'水地'}[view.catalog.cities.find(c=>c.id===b.target).terrain]}。</p><label class="field">计略<select id="tactic-choice">${view.catalog.tactics.map(t=>`<option value="${t.id}">${escapeHtml(t.name)} · ${t.cost}气力</option>`).join('')}</select></label><p id="tactic-description"></p><p class="small">计略名称沿用原作，效果采用本重制版规则。确认后进行成功判定并消耗部队行动。</p>`,'<button data-cancel>取消</button><button id="confirm-tactic" class="primary">施放计略</button>');
 const change=()=>{$('#tactic-description').textContent=view.catalog.tactics[Number($('#tactic-choice').value)].description;};$('#tactic-choice').onchange=change;change();
 $('#confirm-tactic').onclick=async()=>{if(await command('tactic',{battle_id:b.id,actor,target,tactic:Number($('#tactic-choice').value)}))dialog.close();};
}
function renderDuel(b){
 const d=b.extended.duel,a=b.extended.support[d.actor],t=b.extended.support[d.target];
 $('#stage').innerHTML=`<div class="arena"><div class="arena-heading"><h2>阵前单挑</h2><span>第${d.round}合</span></div><div class="duel-fighters"><div><h3>${escapeHtml(name(d.actor))}</h3><p>体力 ${a.health} · 武 ${view.game.officers[d.actor].profile.martial_strength}</p><progress aria-label="本方体力" max="99" value="${a.health}"></progress></div><div><h3>${escapeHtml(name(d.target))}</h3><p>体力 ${t.health} · 武 ${view.game.officers[d.target].profile.martial_strength}</p><progress aria-label="对方体力" max="99" value="${t.health}"></progress></div></div><ul class="battle-log">${d.log.map(l=>`<li>${escapeHtml(l)}</li>`).join('')}</ul></div>`;
 $('#inspector').innerHTML='<div class="inspector-heading"><h2>选择招式</h2></div><p>突击直攻；防守减伤；佯攻克制防守，但易受突击。负伤者败退，二十合仍未分胜负则返回战场。</p><div class="actions"><button id="duel-strike" class="primary">突击</button><button id="duel-guard">防守</button><button id="duel-feint">佯攻</button><button id="duel-withdraw">退出单挑</button></div>';
 for(const move of ['strike','guard','feint','withdraw'])$('#duel-'+move).onclick=()=>command('duel_action',{battle_id:b.id,move});
}
function renderBattle(){
 const game=view.game,b=game.battle;
 if(b.extended?.duel)return renderDuel(b);
 const own=b.attacker===game.player?'attackers':'defenders',foe=own==='attackers'?'defenders':'attackers',friendly=b[own],hostile=b[foe];
 const usable=friendly.filter(u=>u.troops>0&&!b.used.includes(u.id)),enemies=hostile.filter(u=>u.troops>0);
 if(!usable.some(u=>u.id===actor))actor=usable[0]?.id??null;
 if(!enemies.some(u=>u.id===target))target=enemies[0]?.id??null;
 const unitList=(units,side)=>units.map(u=>`<button class="unit ${u.troops===0?'routed':''}" data-${side}="${u.id}" aria-pressed="${(side==='actor'?actor:target)===u.id}" ${game.phase!=='battle'||u.troops===0||(side==='actor'&&b.used.includes(u.id))?'disabled':''}><span>${escapeHtml(name(u.id))}</span><span class="troops">${u.troops}兵${b.extended?`<small>体${b.extended.support[u.id].health} 气${b.extended.support[u.id].energy}</small>`:''}</span></button>`).join('');
 $('#stage').innerHTML=`<div class="arena"><div class="arena-heading"><h2>${escapeHtml(cityName(b.target))}之战</h2><span>第${b.round}轮</span></div><div class="armies"><section class="army"><h3>本方${own==='defenders'?'（守方）':'（攻方）'}</h3><div class="unit-list">${unitList(friendly,'actor')}</div></section><section class="army"><h3>对方${own==='defenders'?'（攻方）':'（守方）'}</h3><div class="unit-list">${unitList(hostile,'target')||'<p>无守军</p>'}</div></section></div><p class="combat-hint">选择本方部队和守方目标。每支本方部队每轮行动一次，对方随后反击。</p></div>`;
 $('[data-actor]')&&document.querySelectorAll('[data-actor]').forEach(el=>el.onclick=()=>{actor=Number(el.dataset.actor);renderBattle();});document.querySelectorAll('[data-target]').forEach(el=>el.onclick=()=>{target=Number(el.dataset.target);renderBattle();});
 const labels={victory:own==='attackers'?'本方胜利':'本方城池失守',defeat:own==='attackers'?'本方败退':'本方守城成功',retreat:'攻方退却'};
 $('#inspector').innerHTML=`<h2 class="battle-title">${game.phase==='result'?'战果':'本方行动'}</h2>${game.phase==='result'?`<p class="outcome">${labels[b.outcome]}</p><p>接收战果后，兵员、名册与城池资源一起结算。</p>`:`<p class="phase-description">本方${friendly.length}/10人，对方${hostile.length}/10人。</p><p>选择：${actor===null?'—':escapeHtml(name(actor))} 对 ${target===null?'—':escapeHtml(name(target))}</p>`}<ul class="battle-log">${b.log.slice(-8).map(t=>`<li>${escapeHtml(t)}</li>`).join('')}</ul><div class="actions">${game.phase==='result'?'<button id="settle" class="primary">接收战果</button>':`<button id="attack" class="primary" ${actor===null||target===null?'disabled':''}>攻击</button>${b.extended?`<div class="action-pair"><button id="tactic" ${actor===null||target===null?'disabled':''}>计略</button><button id="duel" ${actor===null||target===null?'disabled':''}>单挑</button></div>`:''}<button id="retreat">退却</button>`}</div>`;
 if(game.phase==='result')$('#settle').onclick=async()=>{const next=own==='defenders'?b.target:b.outcome==='victory'?b.target:b.source;if(await command('settle',{battle_id:b.id})){selectedCity=next;render();}};
 else{if($('#tactic'))$('#tactic').onclick=()=>tactics(b);if($('#duel'))$('#duel').onclick=()=>{openDialog('单挑挑战','<p>对手可能拒绝。挑战消耗本队行动；接受后进入招式交锋。</p>','<button data-cancel>取消</button><button id="confirm-duel" class="primary">确认挑战</button>');$('#confirm-duel').onclick=async()=>{if(await command('duel_start',{battle_id:b.id,actor,target}))dialog.close();};};$('#attack').onclick=()=>command('attack',{battle_id:b.id,actor,target});$('#retreat').onclick=()=>{openDialog('退却确认','<p>保留已发生的兵损。攻方返回原城；守方撤离会失去城池，武将优先退往相邻本方城，无法退往时转在野。</p>','<button data-cancel>继续作战</button><button id="confirm-retreat" class="primary">确认退却</button>');$('#confirm-retreat').onclick=async()=>{if(await command('retreat',{battle_id:b.id}))dialog.close();};};}
}
function render(){
 if(!view)return;
 const game=view.game;
 $('#library').disabled=!view.catalog.library;
 $('#save').disabled=!game;
 $('#restart').disabled=!game;
 $('#date').textContent=game?`${game.year}年${game.month}月　第${game.turn}回合`:'选择势力';
 if(!game){renderMap();selectFaction();return;}
 if(!selectedCity||!game.cities[selectedCity])selectedCity=Object.values(game.cities).find(c=>c.owner===game.player)?.id||view.catalog.active_cities[0];
 if(game.phase==='battle'||game.phase==='result')renderBattle();
 else{renderMap();if(game.phase==='city')renderCity();else if(game.phase==='ai'){$('#inspector').innerHTML='<div class="inspector-heading"><h2>电脑回合</h2></div><p>电脑处理人事、调兵和出征。遭到攻击时由本方操作守军；接收战果后继续电脑行动，再推进年月。</p><div class="actions"><button id="run-ai" class="primary">执行电脑行动</button></div>';$('#run-ai').onclick=()=>command('ai',{turn:game.turn});}else{$('#inspector').innerHTML=`<h2>${game.extension?.outcome==='victory'?'天下归一':'战役结束'}</h2><p>本次战役已结算，可保存或重新选择势力。</p><div class="actions"><button id="play-again" class="primary">重新选择势力</button></div>`;$('#play-again').onclick=()=>selectFaction();}}
 $('#journal').innerHTML=game.log.slice(-5).map(t=>`<li>${escapeHtml(displayLog(t))}</li>`).join('');
}
$('#rules').onclick=()=>openDialog('规则说明',`<div class="rules-body"><p>每城${capacity()}人；每方出战最多10人，包含主将。</p><ul>${view.catalog.notes.map(t=>`<li>${escapeHtml(t)}</li>`).join('')}</ul><p>总人物库${view.catalog.library_count}人。仅已登场且配置齐全的人物进入本局。战局编号决定随机序列，保存会保留其进度。</p></div>`,'<button data-cancel>返回战役</button>');
$('#library').onclick=showLibrary;
$('#restart').onclick=()=>selectFaction();
$('#save').onclick=async()=>{
 if(busy)return;
 try{const save=await request('/api/save');localStorage.setItem('three-kingdoms-demo-save',JSON.stringify(save));const blob=new Blob([JSON.stringify(save,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=view.catalog.title+'存档.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice('进度已保存。可用“读取进度”恢复，也可保留下载的存档文件。');}catch(e){notice(e.message,true);}
};
async function loadSave(save){if(busy)return;setBusy(true);try{view=await request('/api/load',{save,revision:view.revision});setupPreview=null;selectedCity=null;actor=target=null;dialog.close();render();notice('进度已恢复。');}catch(e){notice(e.message,true);}finally{await new Promise(resolve=>setTimeout(resolve,180));setBusy(false);}}
$('#load').onclick=()=>{const saved=localStorage.getItem('three-kingdoms-demo-save');openDialog('读取进度',`<div class="save-actions"><button id="load-local" ${saved?'':'disabled'}>读取本机保存</button><label class="field" for="save-file">选择存档文件<input id="save-file" type="file" accept=".json,application/json"></label></div><p class="small">存档无效时会保留当前进度。</p>`,'<button data-cancel>取消</button>');$('#load-local').onclick=()=>{try{loadSave(JSON.parse(saved));}catch(e){notice('存档无效，当前进度未改变。',true);}};$('#save-file').onchange=async()=>{try{const file=$('#save-file').files[0];if(!file)return;if(file.size>2*1024*1024)throw new Error('too large');await loadSave(JSON.parse(await file.text()));}catch(e){notice('存档无效，当前进度未改变。',true);}};};
Promise.all([request('/api/state'),request('/assets/city-positions.json')]).then(([value,positions])=>{view=value;mapPositions=positions;render();}).catch(e=>notice('游戏未能载入，请确认本地服务正在运行。',true));
