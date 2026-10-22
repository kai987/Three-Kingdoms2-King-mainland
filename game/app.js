'use strict';
let view=null, busy=false, selectedCity=null, mapMode='all', actor=null, target=null, mapPositions=null, setupPreview=null, cityLabels='major', dialogGeneration=0;
let mapNavigation=null,mapCamera=null,mapCameraKey='',refreshRouteDialog=null;
let cloudSave=null,cloudSaveUI=null;
const $=s=>document.querySelector(s), dialog=$('#dialog'),survivorPreviews=new WeakMap();
const escapeHtml=v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const name=id=>view.catalog.names[String(id)]||'武将';
const faction=id=>id==='neutral'?'无主':view.catalog.factions.find(f=>f.id===id)?.name||'守备军';
const capacity=()=>view.catalog.rules.city_officer_capacity;
const marching=()=>new Set((view.game?.extension?.travel?.marches||[]).flatMap(r=>r.officers));
const routeModes=()=>[['fastest','最快路线（可用海陆联运）'],['land','仅走陆路'],...(view.catalog.travel_hazards?[['special','险道直达（阴平道／子午谷）'],['sea','已知直达海路'],['explore','探索未知海路（仅沿海城池）']]:[])];
const routeModeSelect=(mode='fastest')=>`<label class="field">行军路线<select id="route-mode">${routeModes().map(([id,label])=>`<option value="${id}" ${id===mode?'selected':''}>${label}</option>`).join('')}</select></label>`;
const travelQuote=(source,target,mode='fastest')=>(MarchCore.quotesFor(view)??view.catalog.travel_quotes)?.[`${source}:${target}:${mode}`];
const availableRouteModes=(source,target)=>routeModes().filter(([mode])=>travelQuote(source,target,mode));
function syncRouteModes(source,target,preferred='fastest'){
 const select=$('#route-mode');if(!select)return 'fastest';
 const available=availableRouteModes(source,target).map(([mode])=>mode);
 for(const option of select.options)option.disabled=!available.includes(option.value);
 select.value=available.includes(preferred)?preferred:available[0]||'fastest';
 return select.value;
}
function factionResources(id,preview=setupPreview){
 const supplied=(preview?.faction_resources||(!preview&&view.catalog.faction_resources))?.[id];
 const counts=preview?.faction_officers||(!preview&&view.catalog.faction_officers);
 const officers=counts?.[id]??(preview?preview.factions.find(f=>f.id===id)?.initial_officers||0:new Set(Object.values(view.game?.officers||{}).filter(o=>o.alive&&o.faction_id===id).map(o=>o.person_id)).size);
 if(supplied)return {...supplied,officers};
 if(preview)return null;
 const cities=Object.values(view.game?.cities||{}).filter(c=>c.owner===id);
 return cities.reduce((r,c)=>({...r,gold:r.gold+c.gold,grain:r.grain+c.grain,reserves:r.reserves+c.reserves,cities:r.cities+1}),{gold:0,grain:0,reserves:0,cities:0,officers});
}
function resourceSummary(id,preview=setupPreview){
 const r=factionResources(id,preview);
 return r?`钱 ${r.gold} · 粮 ${r.grain} · 预备兵 ${r.reserves} · 武将 ${r.officers}人`:'资源资料待载入';
}
function factionLedger(){
 return `<details class="faction-ledger"><summary>各势力资源</summary><p class="small">按当前所属城池合计，不含武将带兵。</p><p class="small">武将按当前在籍人数计，含在途；不含在野和已退场人物。</p><div class="faction-ledger-scroll"><table><thead><tr><th>势力</th><th>武将数</th><th>钱</th><th>粮</th><th>预备兵</th></tr></thead><tbody>${view.catalog.factions.map(f=>{const r=factionResources(f.id,null);return `<tr data-faction-resources="${f.id}"><th><svg class="faction-swatch ledger-swatch" width="12" height="12" aria-hidden="true"><rect width="12" height="12" fill="${mapColor(f.id)}"/></svg>${escapeHtml(f.name)}</th><td data-faction-officers="${f.id}">${r.officers}</td><td>${r.gold}</td><td>${r.grain}</td><td>${r.reserves}</td></tr>`;}).join('')}</tbody></table></div></details>`;
}
function routeRisk(quote){
 const lines=(quote.routes||[]).filter(r=>r.hazard).map(r=>{
  const h=r.hazard,lo=h.loss_percent_min,hi=h.loss_percent_max;
  const percent=value=>Number.isInteger(value)?String(value):value.toFixed(1);
  const loss=typeof lo==='number'?(lo===hi?`${percent(lo)}%`:`${percent(lo)}—${percent(hi)}%`):null;
  const detail=h.label||`行军损耗${loss?'：减员'+loss:''}`;
  return `${escapeHtml(detail)}${typeof h.speed_km_per_day==='number'?` · 航速${h.speed_km_per_day}公里/日`:typeof r.base_days==='number'?` · 平地基准${r.base_days}日，本段${r.days}日`:''}`;
 });
 if(view.catalog.travel_hazards&&(quote.routes||[]).some(r=>r.mode==='sea'&&!r.hazard))lines.push('季风过渡期：本次海段不叠加季风暴风雨减员。');
 if((quote.routes||[]).some(r=>r.exploration))lines.push('未知海路：成功完成航行后才会显示在地图上。');
 if((quote.routes||[]).some(r=>r.hazard?.kind==='monsoon_storm'))lines.push('暴风雨减员按整次航行结算一次，不按海路分段重复扣减。');
 return lines.length?`<div class="route-risks" role="note">${[...new Set(lines)].map(line=>`<p>${line}</p>`).join('')}<p>损耗从行军武将的带兵中结算；确认前不抽取事件结果、不扣兵。</p></div>`:'';
}
function travelEstimate(source,target,mode='fastest'){
 const q=travelQuote(source,target,mode);
 if(!q)return '<p class="small">没有符合条件的路线。</p>';
 const month=view.game.month-1+q.months,year=view.game.year+Math.floor(month/12);
 return `<p class="travel-estimate">${q.path.map(id=>escapeHtml(cityName(id))).join(' → ')}<br>约${q.distance_km}公里 · 估算${q.days}日 · ${q.months}个月回合<br>预计${year}年${month%12+1}月到达。${q.modes.includes('sea')?'含海路及上岸接驳。':'陆路行军。'}</p>${routeRisk(q)}`;
}
function previewSurvivors(element,quote,ids){
 if(!element)return;
 const token={};survivorPreviews.set(element,token);
 if(!quote||(quote.routes||[]).every(r=>!r.hazard)||!ids.length)return;
 const generation=dialogGeneration,counts=ids.map(id=>view.game.officers[id].troops),requestView=view;
 MarchCore.survivalPreview(requestView,quote,counts).then(result=>{
  if(!result||view!==requestView||!element.isConnected||generation!==dialogGeneration||survivorPreviews.get(element)!==token)return;
  const total=rows=>rows.reduce((sum,n)=>sum+n,0),lo=total(result.minimum),hi=total(result.maximum),range=lo===hi?lo:`${lo}—${hi}`;
  element.insertAdjacentHTML('beforeend',`<p class="small" data-locale-only="zh-Hant" data-l10n-native="zh-Hant">預計抵達兵力：${range}兵（行軍損耗區間）。</p><p class="small" data-locale-only="ja" data-l10n-native="ja">到着時の兵力見込み：${range}（行軍損耗の範囲）。</p>`);
  GameI18n.apply();
 });
}
function watchRouteDialog(refresh){
 const generation=dialogGeneration;
 refreshRouteDialog=()=>{if(dialog.open&&generation===dialogGeneration)refresh();};
}
MarchCore.subscribe(()=>refreshRouteDialog?.());
function renderMarches(){
 const rows=view.game?.extension?.travel?.marches||[];
 return rows.length?`<div class="marches"><h3>在途部队</h3>${rows.filter(r=>r.owner===view.game.player).map(r=>`<p data-march="${r.id}">${escapeHtml(cityName(r.source))} → ${escapeHtml(cityName(r.target))}<br>${r.officers.map(i=>escapeHtml(name(i))).join('、')} · ${r.quote.distance_km}公里<br>${r.arrival_turn<=view.game.turn?'已抵达，等待处理':`还需${r.arrival_turn-view.game.turn}个月回合`}</p>`).join('')||'<p>本方暂无在途部队。</p>'}<p class="small">在途者保留出发城编制与容量，不参加守城，不能再次行动。月回合按30日结算。</p></div>`:'';
}
const mapPosition=c=>(setupPreview?setupPreview.world:view.catalog.world)?c.position:mapPositions?.positions[c.id]||c.position;
const periodCityName=id=>setupPreview?.city_names[id]||view.catalog.cities.find(c=>c.id===id)?.name||id;
const cityName=id=>(setupPreview?setupPreview.city_history:view.catalog.city_history)?.[id]?periodCityName(id):view.catalog.map_presentation.city_names[id]?.displayName||periodCityName(id);
const cityCaption=id=>cityName(id)===periodCityName(id)?cityName(id):`${cityName(id)}（${periodCityName(id)}）`;
const mapColor=id=>(setupPreview?setupPreview.faction_colors:view.catalog.faction_colors)?.[id]||view.catalog.map_presentation.colors[id]||(setupPreview?.factions||view.catalog.factions).find(f=>f.id===id)?.color||view.catalog.map_presentation.colors.neutral;
function smoothMapPath(points){
 if(!Array.isArray(points)||points.length<2)return '';
 let d=`M${points[0].join(' ')}`;
 for(let i=1;i<points.length-1;i++)d+=`Q${points[i].join(' ')} ${(points[i][0]+points[i+1][0])/2} ${(points[i][1]+points[i+1][1])/2}`;
 return d+`L${points.at(-1).join(' ')}`;
}
const mapAccessKey=points=>[points[0].join(','),points.at(-1).join(',')].sort().join(':');
const displayLog=text=>view.catalog.cities.filter(c=>c.administrative_name!==cityName(c.id)).reduce((s,c)=>s.replaceAll(c.administrative_name,cityName(c.id)),text);
function notice(text='',error=false){$('#notice').textContent=text;$('#notice').classList.toggle('error',error);}
function setBusy(value){busy=value;document.body.classList.toggle('busy',value);if($('#city-jump'))$('#city-jump').disabled=value;$('#main-menu').disabled=value||!view?.game||!!setupPreview;cloudSaveUI?.refreshButton();}
async function request(path,body,{raw=false,text=false}={}){
 const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:raw?body:JSON.stringify(body)});
 const value=text&&response.ok?await response.text():await response.json();
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
 const generation=++dialogGeneration;refreshRouteDialog=null;
 dialog.innerHTML=`<div class="dialog-heading"><h2 id="dialog-title">${escapeHtml(title)}</h2><label class="language-picker">語言<select id="dialog-language" data-language-picker aria-label="切換語言"><option value="zh-Hant" ${GameI18n.locale==='zh-Hant'?'selected':''}>繁體中文</option><option value="ja" ${GameI18n.locale==='ja'?'selected':''}>日本語</option></select></label></div>${body}<div class="dialog-actions">${actions}</div>`;
 if(!dialog.open)dialog.showModal();
 dialog.querySelectorAll('[data-cancel]').forEach(b=>b.onclick=()=>dialog.close());
 return generation;
}
function selectFaction(){
 const current=view.catalog.scenario_id;
 const currentOption=view.catalog.scenarios.find(x=>x.id===current);
 const scenarios=[...new Map(view.catalog.scenarios.filter(x=>x.main_scenario&&!x.archived).map(x=>[x.id,x])).values()];
 const initial=scenarios.find(x=>x.id===current)||scenarios.find(x=>x.year===currentOption?.year&&x.month===currentOption?.month)||scenarios[0];
 $('#main-menu').disabled=true;$('#main-menu').setAttribute('aria-expanded','true');
 if(dialog.open)dialog.close();
 const draw=(scenario)=>{
  const option=scenarios.find(x=>x.id===scenario), expanded=option.cities>=96;
  const preferred=option.factions.some(f=>f.id===view.game?.player)?view.game.player:option.factions.some(f=>f.id==='shu')?'shu':option.factions[0].id;
  setupPreview={...option,faction:preferred,focus:option.factions.find(f=>f.id===preferred).city};
  const groups=[['base','原版本篇'],['pk','威力加强版本篇'],['dlc','DLC历史剧本'],['if','更新IF剧本'],['bonus','特典剧本'],['custom','用户自订剧本'],['supplement','补充年代']];
  const options=groups.map(([group,label])=>{const rows=scenarios.filter(x=>x.main_scenario.group===group).sort((a,b)=>a.year-b.year||a.month-b.month);return rows.length?`<optgroup label="${label} · ${rows.length}剧本">${rows.map(x=>`<option value="${x.id}" ${x.id===scenario?'selected':''}>${escapeHtml(x.title)}</option>`).join('')}</optgroup>`:'';}).join('');
  const meta=option.main_scenario||{},sources=meta.official_source?[meta.official_source]:meta.source_urls||[];
  const scenarioSource=sources.length?sources.map(url=>`<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">查看官方剧本目录</a>`).join(' · '):'<p>补充年代沿用旧版战役配置，并合并本版城池与驻将规则。</p>';
  const category=groups.find(([group])=>group===meta.group)?.[1]||'补充年代';
  const chronology=(meta.chronology_overrides||[]).map(row=>{const changes=Object.entries({birth_year:'出生年',service_year:'出仕年',death_year:'卒年'}).filter(([key])=>row.before[key]!==row.after[key]).map(([key,label])=>`${label} ${row.before[key]??'未详'} → ${row.after[key]??'未详'}`).join('、');return `<li>${escapeHtml(row.name)}：${changes}（${row.is_historical_correction?'史料修订':'本作游戏设定'}）。</li>`;}).join('');
  const scenarioKind=`<p class="small scenario-kind" data-scenario-kind>剧本类型：${escapeHtml(category)}${meta.fictional?' · 假想剧本（IF）':''}</p>`;
  const scenarioExtra=`${meta.story_note_i18n?.['zh-Hant']?`<p>${escapeHtml(meta.story_note_i18n['zh-Hant'])}</p>`:''}${meta.official_same_date_title?`<p>同年月官方剧本：${escapeHtml(meta.official_same_date_title['zh-Hant'])}。</p>`:''}${meta.scope_note?`<p>${escapeHtml(meta.scope_note)}</p>`:''}${chronology?`<details class="chronology-exceptions"><summary>人物年代例外</summary><p>仅本剧本采用以下个别年代修订；旧存档及其他剧本不变。游戏设定不等同史实。</p><ul>${chronology}</ul></details>`:''}`;
  const content=`<label class="field" for="scenario">选择剧本<select id="scenario">${options}</select></label><p class="intro">${option.year}年${option.month}月 · ${option.cities}城 · 每城${option.capacity}人<br>开局在籍${option.serving}人，在野${option.free}人。</p>${scenarioKind}${option.main_scenario?`<details class="scenario-notes"><summary>剧本资料与配置范围</summary><p>${escapeHtml(option.main_scenario.summary)}</p>${scenarioExtra}<p>本作${option.cities}城改编，现有${option.configured}份完整属性。${option.main_scenario.virtue_default_policy?'部分德值按用户指定暂设60，人物库可查评分来源。':''}新年代的部分归属为前后快照推定，未确认者不自动入场。</p>${scenarioSource}</details>`:''}
  ${option.main_scenario?.city_chronology_note?`<p class="small">${escapeHtml(option.main_scenario.city_chronology_note)}</p>`:''}<div class="choice-list">${option.factions.map(f=>`<label class="faction-choice"><input type="radio" name="faction" value="${f.id}" ${f.id===preferred?'checked':''}><svg class="faction-swatch" width="16" height="16" aria-hidden="true"><rect width="16" height="16" fill="${mapColor(f.id)}"/></svg><span class="faction-choice-body"><span class="faction-choice-heading"><span>${escapeHtml(f.name)}</span><span>${escapeHtml(f.captain)} · ${escapeHtml(cityName(f.city))}</span></span><span class="faction-choice-resources" data-faction-resources="${f.id}">${resourceSummary(f.id,option)}</span></span></label>`).join('')}</div>
  <p id="setup-summary" class="small" aria-live="polite"></p><label class="seed-label" for="seed">随机种子<input id="seed" type="number" min="1" max="4294967295" step="1" value="2026" aria-describedby="seed-help"></label><p id="seed-help" class="small">控制招募、战斗等随机判定；相同种子与操作可重现战局。</p>`;
  $('#inspector').classList.add('setup-menu');
  $('#inspector').innerHTML=`<div class="inspector-heading"><h2>主菜单</h2></div>${content}${view.game?'<p class="small">旧存档可继续，进度保持不变。</p>':''}<div class="actions">${view.game?`<button class="primary" id="cancel-setup">${view.game.phase==='finished'?'返回战役结果':'继续当前战役'}</button>`:''}<button class="${view.game?'':'primary'}" id="begin">${view.game?'开始新战役':'开始战役'}</button></div>`;
  const refreshPreview=()=>{
   const chosen=option.factions.find(f=>f.id===setupPreview.faction),count=Object.values(option.initial_owners).filter(owner=>owner===chosen.id).length;
   $('#setup-summary').textContent=`${chosen.name} · ${count}座城池 · 根据地${cityName(chosen.city)}。${resourceSummary(chosen.id,option)}。地图已预览本剧本归属，开始后才建立新战役。`;
   $('#library').disabled=true;renderMap();
  };
  document.querySelectorAll('input[name=faction]').forEach(input=>input.onchange=()=>{setupPreview.faction=input.value;setupPreview.focus=option.factions.find(f=>f.id===input.value).city;refreshPreview();});
  if($('#cancel-setup'))$('#cancel-setup').onclick=()=>{setupPreview=null;render();$('#main-menu').focus();};
  refreshPreview();
  $('#scenario').onchange=()=>draw($('#scenario').value);
  $('#begin').onclick=async()=>{
   const f=document.querySelector('input[name=faction]:checked')?.value,seed=Number($('#seed').value);
   if(!Number.isInteger(seed)||seed<1||seed>4294967295)return notice('随机种子请填写1到4294967295之间的整数。',true);
   const pending=setupPreview;setupPreview=null;
   if(await command('new',{faction:f,seed,scenario})){
    selectedCity=view.catalog.factions.find(x=>x.id===f).city;actor=target=null;mapMode=expanded?'all':'region';dialog.close();render();
   }else{setupPreview=pending;renderMap();}
  };
 };
 draw(initial.id);
 $('#scenario').focus();
}
function renderMap(){
 const game=view.game,preview=setupPreview,owners=preview?.initial_owners||Object.fromEntries(Object.values(game?.cities||{}).map(c=>[c.id,c.owner]));
 const board=preview?.map_cities||view.catalog.cities;
 const active=board.filter(c=>(preview?.active_cities||view.catalog.active_cities).includes(c.id));
 const factions=preview?.factions||view.catalog.factions,ownerName=(id,city)=>id==='neutral'?(preview?.city_history?.[city]?.opening.basis==='unmapped_local_han_administration'?'地方汉郡（中立）':'无主'):factions.find(f=>f.id===id)?.name||'守备军';
 const added=preview?.added_city_ids||view.catalog.added_city_ids||[],activeIds=new Set(active.map(c=>c.id));
 const focused=preview?.focus||selectedCity,selected=board.find(c=>c.id===focused),center=selected?mapPosition(selected):[760,440];
 const world=(preview?preview.world:view.catalog.world)||{x:0,y:0,width:1352,height:1024,background:view.catalog.map_presentation.background};
 const cameraKey=[world.x,world.y||0,world.width,world.height,world.background].join(':');
 if(mapNavigation){mapNavigation.destroy();mapNavigation=null;}
 if(cameraKey!==mapCameraKey){mapCamera=null;mapCameraKey=cameraKey;}
 const box=`${world.x} ${world.y||0} ${world.width} ${world.height}`;
 const date=preview||game||view.catalog.scenarios.find(s=>s.id===view.catalog.scenario_id);
 if(preview)$('#date').textContent=`${date.year}年${date.month}月 · 选择势力`;
 const spritePixels=pixels=>pixels.map(([x,y])=>`<rect x="${x}" y="${y}" width="4" height="4"/>`).join('');
 const spriteDefs=`<g id="castle-fill-pixels">${spritePixels(view.catalog.map_presentation.castle_fill_pixels)}</g><g id="castle-outline-pixels">${spritePixels(view.catalog.map_presentation.castle_outline_pixels)}</g>`;
 const castles=active.map(c=>{
  const [x,y]=mapPosition(c),owner=owners[c.id]||'neutral';
  // Cover the baked outline too: every pixel of an unowned castle is white.
  const outline=owner==='neutral'||added.includes(c.id)||view.catalog.map_presentation.new_city_ids?.includes(c.id)?`<use class="castle-border" href="#castle-outline-pixels" x="${x}" y="${y}" fill="${owner==='neutral'?'#fff':'#000'}"/>`:'';
  const colored=`<use class="castle-fill" href="#castle-fill-pixels" x="${x}" y="${y}" fill="${mapColor(owner)}"/>`;
  return `<g role="button" tabindex="0" class="city-hit ${owner==='neutral'?'unowned':''} ${focused===c.id?'selected':''} ${preview&&owner===preview.faction?'preview-owned':''}" data-city="${c.id}" data-owner="${owner}" aria-label="${escapeHtml(cityCaption(c.id))}，${escapeHtml(ownerName(owner,c.id))}"><title>${escapeHtml(cityCaption(c.id))} · ${escapeHtml(ownerName(owner,c.id))}</title>${outline}${colored}<rect class="city-outline" x="${x-21}" y="${y-21}" width="42" height="42"/></g>`;
 }).join('');
 const extras=preview?.road_additions||view.catalog.road_additions;
 const hazardous=!!(preview?preview.travel_hazards:view.catalog.travel_hazards);
 const roads=view.catalog.map_presentation.added_land_roads.filter(r=>extras.some(e=>e.includes(r.from)&&e.includes(r.to))).map(r=>{
  const ps=r.new_branch;let d=`M${ps[0].join(' ')}`;
  for(let i=1;i<ps.length-1;i++)d+=`Q${ps[i].join(' ')} ${(ps[i][0]+ps[i+1][0])/2} ${(ps[i][1]+ps[i+1][1])/2}`;
  d+=`L${ps.at(-1).join(' ')}`;
  const oneway=hazardous&&r.from==='yinping'&&r.to==='shujun';
  return `<g data-road="${r.from}-${r.to}"${oneway?' data-oneway="yinping-shujun"':''}><path class="road-underlay" d="${d}"/><path class="road-line" d="${d}"${oneway?' marker-end="url(#oneway-road-arrow)"':''}/></g>`;
 }).join('');
 const drawnAccess=new Set();
 const firstAccess=part=>{if(part.mode==='sea')return true;const key=mapAccessKey(part.points);if(drawnAccess.has(key))return false;drawnAccess.add(key);return true;};
 const expansionRoads=preview?.world||!preview&&view.catalog.world?view.catalog.map_presentation.expansion_connections.filter(r=>activeIds.has(r.from)&&activeIds.has(r.to)).flatMap(r=>r.draw.filter(part=>!hazardous||part.mode!=='sea'&&firstAccess(part)).map((part,index)=>{const d=part.points.map((p,i)=>(i?'L':'M')+p.join(' ')).join(' ');return part.mode==='sea'?`<path class="coastal-lane" d="${d}" data-coastal-route="${r.from}-${r.to}"/>`:`<g data-access-road="${r.from}-${r.to}-${index}"><path class="road-underlay" d="${d}"/><path class="road-line" d="${d}"/></g>`;})).join(''):'';
 const seaRoutes=hazardous?[...(preview?.sea_routes||view.catalog.sea_routes||[]),...(!preview?view.catalog.discovered_routes||[]:[])]:[];
 const discoveredIds=new Set(!preview?(view.catalog.discovered_routes||[]).map(r=>r.id||[r.from,r.to].sort().join(':')):[]);
 const seaPairs=new Set();
 const navigableSeas=seaRoutes.filter(r=>{
  const key=[r.from,r.to].sort().join(':');if(seaPairs.has(key)||!activeIds.has(r.from)||!activeIds.has(r.to))return false;seaPairs.add(key);return true;
 }).flatMap(r=>(r.draw||[]).filter(firstAccess).map((part,index)=>{
  const d=smoothMapPath(part.points);if(!d)return '';
  const discovered=discoveredIds.has(r.id||[r.from,r.to].sort().join(':'));
  return part.mode==='sea'?`<path class="coastal-lane${discovered?' discovered-lane':''}" d="${d}" data-coastal-route="${r.from}-${r.to}" data-sea-route="${escapeHtml(r.id||r.from+'-'+r.to)}"${discovered?' data-discovered-route="'+escapeHtml(r.id||r.from+'-'+r.to)+'"':''}/>`:`<g data-access-road="${r.from}-${r.to}-${index}"><path class="road-underlay" d="${d}"/><path class="road-line" d="${d}"/></g>`;
 })).join('');
 const regionalRoads=(preview?.regional_roads||view.catalog.regional_roads||[]).filter(r=>activeIds.has(r.from)&&activeIds.has(r.to)).flatMap(r=>r.draw.map(part=>{
  const ps=part.points;let d=`M${ps[0].join(' ')}`;
  for(let i=1;i<ps.length-1;i++)d+=`Q${ps[i].join(' ')} ${(ps[i][0]+ps[i+1][0])/2} ${(ps[i][1]+ps[i+1][1])/2}`;
  d+=`L${ps.at(-1).join(' ')}`;
  return `<g data-regional-road="${r.from}-${r.to}"><path class="road-underlay" d="${d}"/><path class="road-line" d="${d}"/></g>`;
 })).join('');
 const offsets=preview?.city_label_offsets||view.catalog.city_label_offsets||{};
 const labels=cityLabels==='none'?'':active.filter(c=>cityLabels==='all'||added.includes(c.id)||view.catalog.map_presentation.labelled_city_ids.includes(c.id)||c.id===focused).map(c=>{
  const [x,y]=mapPosition(c),[dx,dy,anchor]=offsets[c.id]||[0,-24,'middle'];return `<text class="map-city-name" x="${x+dx}" y="${y+dy}" text-anchor="${anchor}" data-city-label="${c.id}" aria-hidden="true">${escapeHtml(cityName(c.id))}</text>`;
 }).join('');
 $('#stage').innerHTML=`<div class="map-toolbar" role="group" aria-label="地图视角"><button id="region" class="${mapMode==='region'?'selected':''}" aria-pressed="${mapMode==='region'}">本城</button><button id="all-map" class="${mapMode==='all'?'selected':''}" aria-pressed="${mapMode==='all'}">全图</button><label class="city-jump">城池 <select id="city-jump" aria-label="选择城池" ${busy?'disabled':''}>${active.map(c=>`<option value="${c.id}" ${c.id===focused?'selected':''}>${escapeHtml(cityCaption(c.id))} · ${escapeHtml(ownerName(owners[c.id],c.id))}</option>`).join('')}</select></label><button id="map-labels" aria-label="切换城名显示">城名：${{major:'主城',all:'全部',none:'关闭'}[cityLabels]}</button></div>
 <svg id="world-map" viewBox="${box}" aria-label="${active.length}城地图，${active.length}城开放" aria-describedby="map-gesture-help"><defs>${spriteDefs}<marker id="oneway-road-arrow" viewBox="0 0 10 10" refX="26" refY="5" markerWidth="12" markerHeight="12" orient="auto" markerUnits="userSpaceOnUse"><path d="M0 0L10 5L0 10Z" fill="#704518" stroke="#e4b45e" stroke-width="1"/></marker></defs><image href="${world.background}" x="${world.x}" y="${world.y||0}" width="${world.width}" height="${world.height}"/>${roads}${expansionRoads}${regionalRoads}${navigableSeas}${castles}${labels}</svg>
 <div class="map-zoom-controls" role="group" aria-label="地图缩放比例（1–4倍）"><button id="map-zoom-out" aria-label="缩小地图" title="缩小地图">−</button><output id="map-zoom" aria-label="地图缩放比例（1–4倍）">100%</output><button id="map-zoom-in" aria-label="放大地图" title="放大地图">＋</button></div>
 <p id="map-gesture-help" class="visually-hidden">拖动地图；滚轮或双指缩放，范围1到4倍。</p>
 <time id="map-date" datetime="${String(date.year).padStart(4,'0')}-${String(date.month).padStart(2,'0')}" aria-label="${date.year}年${date.month}月">${date.year}年<span>${date.month}月</span></time>`;
 const choose=(id,inspect=false)=>{
  if(busy)return;
  if(preview)preview.focus=id;
  else{selectedCity=id;if(game.phase==='city'){$('#inspector').scrollTop=0;renderCity();}}
  if(!inspect){const city=board.find(c=>c.id===id);if(city)mapNavigation.focus(...mapPosition(city),mapCamera?.zoom||1);}
  renderMap();
  if(inspect)$(`[data-city="${id}"]`).focus({preventScroll:true});
  if(inspect||preview||game.phase!=='city')showCityInformation(id);
 };
 const navigationControls=()=>{
  const zoom=mapCamera.zoom;
  $('#map-zoom').textContent=`${Math.round(zoom*100)}%`;
  $('#map-zoom-out').disabled=zoom<=1+1e-6;$('#map-zoom-in').disabled=zoom>=4-1e-6;
  for(const[id,selected]of [['region',mapMode==='region'],['all-map',zoom<=1+1e-6]]){$('#'+id).classList.toggle('selected',selected);$('#'+id).setAttribute('aria-pressed',String(selected));}
 };
 let initialCameraUpdate=true;
 mapNavigation=MapNavigation.attach($('#world-map'),{world,initial:mapCamera||(mapMode==='region'?{x:center[0],y:center[1],zoom:3}:null),onChange:camera=>{mapCamera=camera;if(!initialCameraUpdate)mapMode=camera.zoom<=1+1e-6?'all':'custom';initialCameraUpdate=false;navigationControls();}});
 $('#region').onclick=()=>{mapNavigation.focus(center[0],center[1],3);mapMode='region';navigationControls();};
 $('#all-map').onclick=()=>mapNavigation.reset();
 $('#map-zoom-out').onclick=()=>mapNavigation.zoomBy(1/1.25);$('#map-zoom-in').onclick=()=>mapNavigation.zoomBy(1.25);
 $('#city-jump').onchange=()=>choose($('#city-jump').value);
 $('#map-labels').onclick=()=>{cityLabels={major:'all',all:'none',none:'major'}[cityLabels];renderMap();};
 document.querySelectorAll('[data-city],[data-city-label]').forEach(el=>{const id=el.dataset.city||el.dataset.cityLabel;el.onclick=e=>{if(!mapNavigation.shouldSuppressClick(e))choose(id,true);};el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(id,true);}};});
}

async function showCityInformation(id){
 const preview=setupPreview,title=cityName(id)+' · 城池资料',period=periodCityName(id),close='<button data-cancel autofocus>关闭资料</button>';
 const generation=openDialog(title,'<p>正在读取城池资料……</p>',close);
 if(generation===undefined)return;
 try{
  let data;
  if(preview)data=await request('/api/city-preview?'+new URLSearchParams({scenario:preview.id,city:id}));
  else{
   const c=view.game.cities[id],def=view.catalog.cities.find(c=>c.id===id);
   data={title:view.catalog.title,year:view.game.year,month:view.game.month,capacity:capacity(),city:{...c,
    owner_name:faction(c.owner),terrain:def.terrain,profile:view.catalog.city_profiles[id],income:view.catalog.city_income[id],history:view.catalog.city_history?.[id],
    officers:c.roster.officer_ids.map(i=>{const o=view.game.officers[i];return {id:i,name:name(i),martial_strength:o.profile.martial_strength,intellect:o.profile.intellect,troops:o.troops};})}};
  }
  if(!dialog.open||generation!==dialogGeneration||preview!==setupPreview)return;
  const c=data.city,naming=view.catalog.map_presentation.city_names[id],history=c.history,troops=c.officers.reduce((n,o)=>n+o.troops,0);
  const rows=c.officers.map(o=>`<tr><td>${escapeHtml(o.name)}</td><td>${o.martial_strength}</td><td>${o.intellect}</td><td>${o.troops}</td></tr>`).join('');
  const garrisonLabels={attested_yanmen_post_227:'史料任职',reviewed_SAN14_source_city_to_board:'攻略驻城参考',retained_faction_ruler_seat:'君主营地'};
  const historySources=(history?.sources||[]).map((source,i)=>{const url=typeof source==='string'?source:source?.url,label=typeof source==='object'&&source?.note?source.note:`参考资料${i+1}`;return typeof url==='string'&&url?`<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>`:`<span>${escapeHtml(label)}</span>`;}).join(' · ');
  openDialog(title,`<div class="city-information" data-inspected-city="${id}" data-information-mode="${preview?'preview':'live'}">
   <p class="small">${preview?'剧本开局预览':'当前战役'} · ${data.year}年${data.month}月</p>
   <p class="city-information-owner">归属：${escapeHtml(c.owner_name)}</p>
   ${period!==cityName(id)?`<p class="small">本年代地名：${escapeHtml(period)}</p>`:''}
   ${naming?.detail?`<p class="small">${escapeHtml(naming.detail)}</p>`:''}
   ${history?`<details class="scenario-notes city-history"><summary>年代与开局归属依据</summary>${sourceEvidence(`<p>${escapeHtml(history.detail)}</p><p>${escapeHtml(history.opening.note)}</p>${historySources}`,'都市の年代・開始時所属について、史料の記録と本作の配置設定を区別しています。詳細な根拠と資料の精度は原資料で確認できます。')}<p>驻将按攻略参考、君主营地和同势力防务调配安排；史料任职会单独注明，不代表所有驻将均为史实郡守。</p>${history.garrisons?.length?`<p>开局驻防：${history.garrisons.map(g=>`${escapeHtml(g.name)}（${garrisonLabels[g.basis]||'区域防务调配'}）`).join('、')}</p>`:'<p>未虚构初始郡守，驻防名册暂空，可在战役中调将或招募。</p>'}</details>`:''}
   <p class="small">${escapeHtml(c.profile?.label||'旧版城市')} · 地形：${{plain:'平地',mountain:'山地',water:'水地'}[c.terrain]||'未配置'}</p>
   ${cityEconomyNote(c.profile)}
   <dl class="resources"><dt>金钱</dt><dd>${c.gold}</dd><dt>粮食</dt><dd>${c.grain}</dd><dt>预备兵</dt><dd>${c.reserves}</dd></dl>
   ${c.income?`<p class="small">${c.owner==='neutral'?'无主城暂无月收入':`每月金${c.income.gold} / 粮${c.income.grain} / 预备兵${c.income.reserves}`}</p>`:''}
   <p class="city-information-strength">驻城 ${c.officers.length}/${data.capacity}人 · 武将带兵合计 ${troops}</p>
   <div class="roster-scroll"><table class="roster-table"><thead><tr><th>武将</th><th>武</th><th>知</th><th>兵</th></tr></thead><tbody>${rows||'<tr><td colspan="4">暂无驻军</td></tr>'}</tbody></table></div>
   </div>`,close);
 }catch(e){if(dialog.open&&generation===dialogGeneration)openDialog(title,`<p role="alert">${escapeHtml(e.message)}</p>`,close);}
}

function cityEconomyNote(profile){
 if(!profile?.economy_reference_date)return '';
 const [year,month]=profile.economy_reference_date,tc=escapeHtml(profile.economy_period_label_tc||''),ja=escapeHtml(profile.economy_period_label_ja||'');
 return `<p class="small city-economy-note" data-locale-only="zh-Hant" data-l10n-native="zh-Hant">開局經濟：${year}年${month}月 · ${tc}。資源數值為本作平衡設定，開局後隨實際戰役增減。</p><p class="small city-economy-note" data-locale-only="ja" data-l10n-native="ja">開始時の経済：${year}年${month}月 · ${ja}。資源量は本作の調整値で、開始後は実際の戦況に応じて増減します。</p>`;
}

function rosterRows(city){return city.roster.officer_ids.map(id=>{const o=view.game.officers[id];return `<tr title="体${o.health}，德${o.profile.virtue}，忠${o.loyalty}，经验${o.experience}"><td>${escapeHtml(name(id))}${marching().has(id)?'（在途）':''}</td><td>${o.profile.martial_strength}</td><td>${o.profile.intellect}</td><td>${o.troops}</td></tr>`;}).join('');}
function renderCity(){
 const game=view.game,city=game.cities[selectedCity],owned=city.owner===game.player;
 const scale=view.catalog.city_profiles[city.id],income=view.catalog.city_income[city.id],naming=view.catalog.map_presentation.city_names[city.id];
 $('#inspector').innerHTML=`<div class="inspector-heading"><h2>${escapeHtml(cityName(city.id))}</h2><span class="owner">${faction(city.owner)}</span></div>
 ${city.owner!=='neutral'?`<p class="small faction-total">${escapeHtml(faction(city.owner))}合计：${resourceSummary(city.owner,null)}</p>`:''}
 ${periodCityName(city.id)!==cityName(city.id)?`<p class="small">本年代地名：${escapeHtml(periodCityName(city.id))}。</p>`:''}
 ${naming?.detail?`<p class="small city-name-detail">${escapeHtml(naming.detail)}</p>`:''}
 <p class="small city-scale">${scale?`${escapeHtml(scale.label)} · ${city.owner==='neutral'?'无主城暂无月收入':`每月金${income.gold} / 粮${income.grain} / 预备兵${income.reserves}`}`:'旧版战役：沿用原有资源规则。'}</p>
 ${cityEconomyNote(scale)}
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
 const ids=city.roster.officer_ids.filter(i=>!marching().has(i));
 if(!ids.length)return notice('本城武将均在行军。');
 openDialog('编兵',`<p>本城预备兵 ${city.reserves}。调整兵力不消耗城池行动。</p><label class="field" for="allocation-officer">武将<select id="allocation-officer">${ids.map(i=>`<option value="${i}">${escapeHtml(name(i))}</option>`).join('')}</select></label><label class="field" for="allocation-troops">目标兵力<input id="allocation-troops" type="number" min="0" max="999" step="1" value="${view.game.officers[ids[0]].troops}"></label><p class="small" id="allocation-preview"></p>`, '<button data-cancel>取消</button><button id="confirm-allocation" class="primary">确认编兵</button>');
 const preview=()=>{const o=view.game.officers[$('#allocation-officer').value],n=Number($('#allocation-troops').value),delta=n-o.troops;$('#allocation-preview').textContent=Number.isInteger(n)&&n>=0&&n<=999?`确认后本城预备兵 ${city.reserves-delta}。`:'请输入0到999之间的整数。';};
 $('#allocation-officer').onchange=()=>{$('#allocation-troops').value=view.game.officers[$('#allocation-officer').value].troops;preview();};$('#allocation-troops').oninput=preview;preview();
 $('#confirm-allocation').onclick=async()=>{const id=Number($('#allocation-officer').value),troops=Number($('#allocation-troops').value);if(await command('allocate',{city:city.id,officer:id,troops}))dialog.close();};
}
function departure(city){
 const targets=Object.values(view.game.cities).filter(c=>c.owner!==view.game.player&&(view.catalog.travel_hazards?availableRouteModes(city.id,c.id).length:view.catalog.links.some(e=>e.includes(city.id)&&e.includes(c.id))));
 if(!targets.length)return notice(view.catalog.travel_hazards?'没有可出征的陆路或沿海城池。':'没有相邻的敌方城池。');
 const draft={source:city.id,target:targets[0].id,officers:[],route_mode:'fastest'};
 const pick=()=>{
  openDialog('选择出征名单',`<label class="field" for="departure-target">目标城池<select id="departure-target">${targets.map(c=>`<option value="${c.id}" ${draft.target===c.id?'selected':''}>${escapeHtml(cityName(c.id))} · ${faction(c.owner)}</option>`).join('')}</select></label><p>选择1—10名武将，第一位为主将。</p><div class="officer-picker">${city.roster.officer_ids.map(i=>{const o=view.game.officers[i];return `<label><input type="checkbox" name="depart-officer" value="${i}" ${draft.officers.includes(i)?'checked':''} ${o.troops===0||marching().has(i)||view.game.extension?.officer_actions?.[i]===view.game.turn?'disabled':''}>${escapeHtml(name(i))}　${o.troops}兵</label>`;}).join('')}</div>`, '<button data-cancel>取消出征</button><button id="review-departure" class="primary">下一步</button>');
  $('#review-departure').onclick=()=>{draft.target=$('#departure-target').value;draft.officers=[...dialog.querySelectorAll('input[name=depart-officer]:checked')].map(x=>Number(x.value));if(!draft.officers.length||draft.officers.length>10)return notice('请选择1到10名有兵力的武将。',true);confirm();};
 };
 const confirm=()=>{const troops=draft.officers.reduce((n,i)=>n+view.game.officers[i].troops,0),cost=Math.max(1,Math.floor(troops/25));openDialog('出征确认',`<p>${escapeHtml(cityName(city.id))}出发，目标${escapeHtml(cityName(draft.target))}。</p><p>${draft.officers.map(i=>escapeHtml(name(i))).join('、')}，共${troops}兵，耗粮${cost}。</p>${view.catalog.travel_rules?routeModeSelect(draft.route_mode)+`<div id="departure-estimate"></div>`:''}<p class="small">${view.catalog.travel_rules?'确认后部队进入行军，到达后才战斗。':'确认后才出征。'}现在取消不会扣粮或消耗行动。</p>`,'<button data-cancel>取消出征</button><button id="back-to-pick">返回名单</button><button id="confirm-departure" class="primary">确认出征</button>');const refresh=()=>{draft.route_mode=syncRouteModes(city.id,draft.target,draft.route_mode);const estimate=$('#departure-estimate'),quote=travelQuote(city.id,draft.target,draft.route_mode);estimate.innerHTML=travelEstimate(city.id,draft.target,draft.route_mode);previewSurvivors(estimate,quote,draft.officers);$('#confirm-departure').disabled=!quote;};if($('#route-mode')){$('#route-mode').onchange=()=>{draft.route_mode=$('#route-mode').value;refresh();};watchRouteDialog(refresh);refresh();}$('#back-to-pick').onclick=pick;$('#confirm-departure').onclick=async()=>{actor=target=null;if(await command('depart',draft))dialog.close();};};
 pick();
}

function recruitOfficer(city){
 const free=view.catalog.recruitable?.[city.id]||[],enemy=view.catalog.persuadable?.[city.id]||[];
 if(!free.length&&!enemy.length)return notice('附近暂无可招募的在野武将或可劝降的敌将。可在“人物库”查看年代与配置。');
 openDialog('招募与劝降',`<label class="field">人事方式<select id="recruit-mode"><option value="recruit_officer" ${!free.length?'disabled':''}>在野招募 · 60金</option><option value="persuade_officer" ${!enemy.length?'disabled':''} ${!free.length?'selected':''}>邻城劝降 · 100金</option></select></label><p>一次寻访消耗本城行动，对方可能拒绝。取消不扣资源；君主不能直接劝降。</p><label class="field">执行武将<select id="recruit-actor">${city.roster.officer_ids.map(i=>`<option value="${i}" ${(marching().has(i)||view.game.extension.officer_actions[i]===view.game.turn)?'disabled':''}>${escapeHtml(name(i))} · 德${view.game.officers[i].profile.virtue}</option>`).join('')}</select></label><label class="field">目标武将<select id="recruit-person"></select></label><p class="small">最多${capacity()}人。转属成功后保留体力、带兵、装备和经验；忠诚按本作招募规则重新结算。</p>`,'<button data-cancel>取消</button><button id="confirm-officer" class="primary">确认寻访</button>');
 const draw=()=>{$('#recruit-person').innerHTML=($('#recruit-mode').value==='recruit_officer'?free:enemy).map(i=>`<option value="${i}">${escapeHtml(name(i))}${view.game.officers[i].faction_id?' · 忠'+view.game.officers[i].loyalty:''}</option>`).join('');};
 $('#recruit-mode').onchange=draw;draw();
 $('#confirm-officer').onclick=async()=>{if(await command($('#recruit-mode').value,{city:city.id,actor:Number($('#recruit-actor').value),officer:Number($('#recruit-person').value)}))dialog.close();};
}
function transferCity(city){
 const destinations=Object.values(view.game.cities).filter(c=>c.id!==city.id&&c.owner===view.game.player);
 if(!destinations.length)return notice('没有其他本方城池可接收武将。');
 openDialog('调动武将',`<p>沿连续的本方路线调动，费用为每人每段道路5粮。消耗出发城行动，目的城仍最多${capacity()}人。</p>${view.catalog.travel_rules?routeModeSelect()+'<div id="transfer-estimate"></div>':''}<label class="field">目的城<select id="transfer-city">${destinations.map(c=>`<option value="${c.id}">${escapeHtml(cityName(c.id))} · ${c.roster.officer_ids.length}/${capacity()}人</option>`).join('')}</select></label><div class="officer-picker">${city.roster.officer_ids.map(i=>`<label><input type="checkbox" name="transfer-officer" value="${i}" ${(marching().has(i)||view.game.extension?.officer_actions?.[i]===view.game.turn)?'disabled':''}>${escapeHtml(name(i))} · ${view.game.officers[i].troops}兵</label>`).join('')}</div>`,'<button data-cancel>取消</button><button id="confirm-transfer" class="primary">确认调动</button>');
 const updateEstimate=()=>{if($('#transfer-estimate')){const destination=$('#transfer-city').value,mode=syncRouteModes(city.id,destination,$('#route-mode').value),estimate=$('#transfer-estimate'),quote=travelQuote(city.id,destination,mode),ids=[...dialog.querySelectorAll('input[name=transfer-officer]:checked')].map(e=>Number(e.value));estimate.innerHTML=travelEstimate(city.id,destination,mode);previewSurvivors(estimate,quote,ids);$('#confirm-transfer').disabled=!quote;}};
 $('#transfer-city').onchange=updateEstimate;if($('#route-mode'))$('#route-mode').onchange=updateEstimate;dialog.querySelectorAll('input[name=transfer-officer]').forEach(input=>input.onchange=updateEstimate);watchRouteDialog(updateEstimate);updateEstimate();
 $('#confirm-transfer').onclick=async()=>{const ids=[...dialog.querySelectorAll('input[name=transfer-officer]:checked')].map(e=>Number(e.value));if(await command('transfer',{source:city.id,target:$('#transfer-city').value,officers:ids,route_mode:$('#route-mode')?.value||'fastest'}))dialog.close();};
}
// Classify actual runtime entry before consulting immutable opening plans.
function libraryEntryStatus(p){
 if(p.alive===true)return p.faction?'serving':'free';
 if(p.alive===false||p.year_state==='dead')return 'retired';
 if(p.year_state==='not_born'||p.year_state==='not_appeared')return p.year_state;
 if(p.missing.length)return 'missing';
 if(['pending_history','pending_capacity','pending_faction','scenario_excluded'].includes(p.era_assignment?.status))return p.era_assignment.status;
 if(p.year_state==='death_year_review'&&!p.era_assignment?.death_year_resolved)return 'death_review';
 return p.year_state==='unknown'?'unknown':'unentered';
}
function libraryEntryCounts(people){
 const counts={serving:0,free:0,not_born:0,not_appeared:0,retired:0,death_review:0,pending_history:0,pending_capacity:0,pending_faction:0,scenario_excluded:0,missing:0,unknown:0,unentered:0};
 for(const p of people)counts[libraryEntryStatus(p)]++;
 return counts;
}
function libraryPlacementFilter(p,filter){
 const status=libraryEntryStatus(p);
 return filter==='entry:not_yet'?['not_born','not_appeared'].includes(status):filter==='entry:unentered'?['missing','unknown','unentered'].includes(status):filter==='entry:'+status;
}
const libraryEntryLabels={serving:['已登場在籍','登場済み・仕官中'],not_yet:['未出生／未出仕','未出生・未登場'],pending_history:['歸屬待考','所属未確定'],pending_capacity:['容量不足未入局','定員不足で未登場'],pending_faction:['本篇勢力待配置','所属勢力が未設定'],scenario_excluded:['本劇本排除','本シナリオ対象外'],death_review:['卒年邊界待核','没年の境界を要確認'],retired:['已退出／已過卒年','退場済み・没年経過'],unentered:['其他尚未入局','その他の未登場']};
function libraryEntryOptions(){
 return Object.entries(libraryEntryLabels).map(([key,labels])=>`<option value="entry:${key}" data-library-entry="${key}" data-l10n-native="${GameI18n.locale}">${escapeHtml(labels[GameI18n.locale==='ja'?1:0])}</option>`).join('');
}
function refreshLibraryEntryLabels(){
 for(const option of document.querySelectorAll('#library-filter [data-library-entry]')){
  option.dataset.l10nNative=GameI18n.locale;
  option.textContent=libraryEntryLabels[option.dataset.libraryEntry][GameI18n.locale==='ja'?1:0];
 }
}
function libraryEntrySummary(people,game){
 if(!game)return '<div class="small" data-locale-only="zh-Hant" data-l10n-native="zh-Hant">尚未開始戰役。總人物庫與開局規劃不等於實際駐城；開始後可查看本局在籍與在野人數。</div><div class="small" data-locale-only="ja" data-l10n-native="ja">戦役はまだ始まっていません。人物総数と開始時の配置計画は、実際の所属人数とは異なります。開始後に仕官中・在野の人数を確認できます。</div>';
 const c=libraryEntryCounts(people),actual=c.serving+c.free,other=c.missing+c.unknown+c.unentered;
 return `<div class="library-entry-summary" data-locale-only="zh-Hant" data-l10n-native="zh-Hant"><p>${game.year}年${game.month}月本局：在籍 <strong data-entry-count="serving">${c.serving}</strong> 人，在野 <strong data-entry-count="free">${c.free}</strong> 人；已登場 ${actual}／總庫 ${people.length} 人。</p><p class="small">未出生 ${c.not_born}、未出仕 ${c.not_appeared}、已退出／過卒年 ${c.retired}、卒年待核 ${c.death_review}；歸屬待考 ${c.pending_history}、勢力待配置 ${c.pending_faction}、容量不足 ${c.pending_capacity}、劇本排除 ${c.scenario_excluded}、其他未入局 ${other}。</p><p class="small">在籍包含行軍中的武將；在野者有所在地，但不佔城內名冊。待考或容量不足者不計入各城在籍，開局規劃不代表已經安置。</p></div><div class="library-entry-summary" data-locale-only="ja" data-l10n-native="ja"><p>${game.year}年${game.month}月の戦役：仕官中 <strong data-entry-count="serving">${c.serving}</strong> 人、在野 <strong data-entry-count="free">${c.free}</strong> 人。登場済み ${actual}／人物総数 ${people.length} 人。</p><p class="small">未出生 ${c.not_born}、登場前 ${c.not_appeared}、退場・没年経過 ${c.retired}、没年要確認 ${c.death_review}。所属未確定 ${c.pending_history}、勢力未設定 ${c.pending_faction}、定員不足 ${c.pending_capacity}、シナリオ対象外 ${c.scenario_excluded}、その他未登場 ${other}。</p><p class="small">仕官中には行軍中の武将も含みます。在野武将には現在地がありますが、都市の所属名簿には入りません。所属未確定・定員不足の人物は都市の人数に含めず、開始時の計画を実際の配置とはみなしません。</p></div>`;
}
document.addEventListener('game-language-change',refreshLibraryEntryLabels);
function personStatus(p){
 if(p.missing.length)return '待补：'+p.missing.map(k=>({health_max:'体力',martial_strength:'武',intellect:'知',virtue:'德',terrain_affinity:'适性'})[k]).join('、');
 if(p.alive===false)return '已退出';
 if(p.alive)return p.faction?escapeHtml(faction(p.faction)):'在野 · '+escapeHtml(cityName(p.location));
 const labels={not_born:'未出生',not_appeared:'未出仕',available:'年代合格',death_year_review:'卒年待核',dead:'已过卒年',unknown:'年代待核'};
 if(['not_born','not_appeared','dead'].includes(p.year_state))return labels[p.year_state];
 return {pending_history:'归属待考',pending_faction:'势力待接入',pending_capacity:'容量不足，尚未登场',scenario_excluded:'本剧本不登场'}[p.era_assignment?.status]||labels[p.year_state];
}
function showLibrary(){
 if(!view.catalog.library)return notice('请进入扩展战役查看人物配置状态。');
 const total=view.catalog.library.length;
 openDialog(`${total}人武将库`,`<p>${view.catalog.coverage.configured_profiles}人属性齐全，${view.catalog.coverage.pending_profiles}人待配置。${view.catalog.coverage.default_virtue_profiles?`${view.catalog.coverage.history_designs_total}人参考史料评分，${view.catalog.coverage.default_virtue_profiles}人默认德60，1人沿用原作基线。`:view.catalog.coverage.health_configured?'体力与适性已按人物库配置；缺德者仍待配置。':''}点击姓名查看评分依据与本年代驻城安排。</p>${libraryEntrySummary(view.catalog.library,view.game)}<div class="library-tools"><input id="library-search" aria-label="检索武将" placeholder="姓名、别名或人物编号"><select id="library-filter" aria-label="人物筛选"><option value="all">全部${total}人</option><option value="ready">属性齐全</option><option value="rated">史料参考德</option><option value="default60">默认德60</option><option value="available">年表资格合格</option><option value="free">已登场在野</option><option value="missing">待配置</option>${libraryEntryOptions()}</select></div><div id="library-results"></div>${view.catalog.library.some(p=>p.chronology_design?.death_year===null)?'<p class="small">＊为本作退场年，并非已知卒年；新增人物的估计年代可查看来源。</p>':''}<div class="library-tools"><button id="library-prev">上一页</button><span id="library-count"></span><button id="library-next">下一页</button></div>`,'<button data-cancel>返回战役</button>');
 let page=0;
 const draw=()=>{const q=$('#library-search').value.trim(),filter=$('#library-filter').value;const people=view.catalog.library.filter(p=>(!q||[p.name,p.person_id,...p.aliases].some(s=>[s,GameI18n.t(s,'zh-Hant'),GameI18n.t(s,'ja')].some(label=>label.includes(q))))&&(filter==='all'||filter.startsWith('entry:')&&libraryPlacementFilter(p,filter)||filter==='ready'&&!p.missing.length||filter==='available'&&p.year_state==='available'||filter==='free'&&p.alive&&p.faction===null||filter==='missing'&&p.missing.length||filter==='rated'&&p.virtue_design?.status==='configured_design'||filter==='default60'&&p.virtue_design?.status==='configured_default'));const max=Math.max(0,Math.ceil(people.length/12)-1);page=Math.min(page,max);
 $('#library-results').innerHTML=`<table class="library-table"><thead><tr><th>武将</th><th>生/仕/卒</th><th>武/知/德</th><th>状态</th></tr></thead><tbody>${people.slice(page*12,(page+1)*12).map(p=>`<tr><td><button class="person-detail" data-person="${p.id}">${escapeHtml(p.name)}</button></td><td>${p.birth}/${p.service}/${p.death}${p.chronology_design?.death_year===null?'＊':''}</td><td>${p.martial??'待填'}/${p.intellect??'待填'}/${p.virtue??'待填'}${p.virtue_design?.status==='configured_default'?'（默认）':''}</td><td>${personStatus(p)}</td></tr>`).join('')}</tbody></table>`;
 dialog.querySelectorAll('[data-person]').forEach(el=>el.onclick=()=>showPerson(Number(el.dataset.person)));
 $('#library-count').textContent=`${people.length}人 · ${page+1}/${max+1}页`;$('#library-prev').disabled=page===0;$('#library-next').disabled=page===max;};
 $('#library-search').oninput=$('#library-filter').onchange=()=>{page=0;draw();};$('#library-prev').onclick=()=>{page--;draw();};$('#library-next').onclick=()=>{page++;draw();};draw();
}
function sourceEvidence(body,japanese){return `<div data-locale-only="zh-Hant">${body}</div><div data-locale-only="ja" data-l10n-native="ja"><p>${japanese}</p><details class="source-original"><summary>原資料（繁体字中国語）</summary><div data-l10n-original lang="zh-Hant">${body}</div></details></div>`;}
function virtueDescription(p){
 const d=p.virtue_design;
 if(d?.status==='configured_default')return sourceEvidence(`<p><strong>德60 · 用户指定默认值</strong></p><p>${escapeHtml(d.design_rationale)}</p><p class="small">授权日期 ${escapeHtml(d.authorized_on)}。尚无本作逐人四维评分，不代表历史评价；数值已用于本局规则。</p>`,`徳60は指定による暫定値です。史料に基づく人物別の4項目評価は未実施で、歴史上の評価を意味しません。この値を本作の判定に使います。指定日：${escapeHtml(d.authorized_on)}。`);
 if(d?.status==='configured_design')return sourceEvidence(`<p>${escapeHtml(d.design_rationale||d.notes||'逐人史料参考设计。')}</p>${d.calibration?`<p>尺度对照：${escapeHtml(d.calibration.name)}（德${d.calibration.virtue}）。本人的四维按所列事迹独立评分。</p>`:''}<p>恤民 ${d.dimensions.care} · 公正 ${d.dimensions.fairness} · 操守 ${d.dimensions.integrity} · 信义 ${d.dimensions.trust}。${d.confidence==='low'?'史料有限，低置信初评；':''}德是生涯综合游戏评分。</p><ul>${d.sources.map(s=>`<li><a href="${escapeHtml(s.url)}" target="_blank" rel="noreferrer">${escapeHtml(s.work+' · '+s.section)}</a></li>`).join('')}</ul>`,`徳${p.virtue}は史料を参考にした本作独自の評価です。民への配慮 ${d.dimensions.care}・公正 ${d.dimensions.fairness}・節操 ${d.dimensions.integrity}・信義 ${d.dimensions.trust}。${d.calibration?`比較基準は${escapeHtml(GameI18n.t(d.calibration.name,'ja'))}（徳${d.calibration.virtue}）ですが、本人の事績から個別に評価しています。`:''}${d.confidence==='low'?'史料が少なく、確度の低い暫定評価です。':''}具体的な事績と出典は原資料を確認してください。`);
 return `<p>${p.virtue===null?'史料与独立德评分尚待补齐，当前不进入战局。':'沿用原版人物基线，历史德重评待补。'}</p>`;
}
function showPerson(id){
 const p=view.catalog.library.find(x=>x.id===id),a=p.era_assignment;
 const affinity={0:'平地',1:'山地',2:'水地'};
 const sourceState={serving:'仕官',free:'在野',undiscovered:'未发现',not_appeared:'尚未登场',dead:'已故',unreviewed:'转属待复核'};
 const current=view.game?Object.values(view.game.cities).find(c=>c.roster.officer_ids.includes(id))?.id:null;
 const abilityNote=p.ability_source?.kind==='historical_authorial_game_design'?'武知为参考生涯的本作设计值，并非《三国志14》原始能力。年代含游戏估计，详见来源。':'武知来自第三方SAN14数值转写，年代为来源游戏设定。';
 const sourceLinks=(p.ability_source?.source_urls||[]).filter(url=>typeof url==='string'&&url.startsWith('https://')).map(url=>`<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">查看人物史料</a>`).join(' · ');
 const abilityEvidence=p.ability_source?.kind==='historical_authorial_game_design'?sourceEvidence(`<p>${escapeHtml(p.ability_source.notes||'事迹参考与本作能力设计。')}</p>${sourceLinks?`<p>${sourceLinks}</p>`:''}`,'能力は事績を参考にした独自設定です。年代の一部はゲーム用の推定です。採用根拠と出典は原資料で確認できます。'):'';
 const pendingNote=p.alive==null?{pending_capacity:'本剧本所属势力的城内容量不足，本人尚未加入战局，不计入在籍人数。',scenario_excluded:'本剧本明确设为不登场，不会在后续月份自动加入。',pending_history:'本剧本的所属或驻城尚待考证，未自动加入战局。',pending_faction:'本剧本尚未接入所属势力，未自动加入战局。'}[a?.status]:null;
 openDialog(`${p.name} · 人物配置`,`<p class="small">${escapeHtml(p.person_id)} · 独立编号 ${id}</p><p>体力上限 ${p.health_max??'待配置'}；适性 ${affinity[p.affinity]??'待配置'}。体力与适性是本作初始化规则。</p><p>武 ${p.martial??'待填'} / 知 ${p.intellect??'待填'} / 德 ${p.virtue??'待考'}。${abilityNote}</p>${abilityEvidence}${pendingNote?`<p class="person-entry-status">${pendingNote}</p>`:''}${virtueDescription(p)}${a?`${a.membership_resolution?`<p>本篇归属依据：${escapeHtml({chapter_leader_setup:'剧本君主配置',reviewed_transition:'本作转属复核',bracketing_affiliation_agreement_inference:'前后快照归属一致（推定，未证实连续仕官）',bracketing_free_location_agreement_inference:'前后快照在野地点一致（推定）',pending_history:'归属待考，未自动加入本局',reviewed_career_window_v13:'史料参考任职窗口（连续性推定）',historical_expansion_career_window:'新增人物生涯窗口（本作配置）'}[a.membership_resolution.basis]||'待核')}。</p>${a.membership_resolution.override?sourceEvidence(`<p class="small">${escapeHtml(a.membership_resolution.override.basis)}</p>`,'この所属はシナリオごとの個別設定です。歴史設定と仮想設定を区別し、具体的な採用根拠を原資料に記録しています。'):''}`:''}${a.membership_revision?sourceEvidence(`<p>历史与分组修订：${escapeHtml(a.membership_revision.reason)}</p>`,'資料の分類と本作の所属設定を照合し、個別の修正を行っています。修正理由は原資料を確認してください。'):''}<p>开局来源：${escapeHtml(a.source_ruler||sourceState[a.source_status]||'状态待核')}。开局规划：${escapeHtml(a.city?cityName(a.city):'驻城待考')}；${escapeHtml(a.faction?faction(a.faction):a.source_status==='unreviewed'?'归属待考':a.source_status==='dead'?'不登场':a.source_status==='not_appeared'?'尚未登场':a.source_status==='serving'?'势力待接入':'在野')}。</p><p class="small">来源身份与驻城分开记录。驻城使用地名映射或本作区域配置，不能当作已考证的历史驻军地点。${a.death_year_resolved?'本剧本配置为卒年开局仍在世，后续按年粒度处理。':''}</p>`:''}${p.alive?`<p>当前战局：${escapeHtml(p.faction?faction(p.faction):'在野')} · ${escapeHtml(cityName(current||p.location||'待归城'))}</p>`:''}`,'<button id="back-library">返回武将库</button><button data-cancel>返回战役</button>');
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
 if(mapNavigation){mapNavigation.destroy();mapNavigation=null;}
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
 $('#inspector').innerHTML=`<h2 class="battle-title">${game.phase==='result'?'战果':'本方行动'}</h2>${game.phase==='result'?`<p class="outcome">${labels[b.outcome]}</p><p>接收战果后，兵员、名册与城池资源一起结算。</p>`:`<p class="phase-description">本方${friendly.length}/10人，对方${hostile.length}/10人。</p><p>选择：${actor===null?'—':escapeHtml(name(actor))} 对 ${target===null?'—':escapeHtml(name(target))}</p>`}<ul class="battle-log">${b.log.slice(-8).map(t=>`<li>${escapeHtml(displayLog(t))}</li>`).join('')}</ul><div class="actions">${game.phase==='result'?'<button id="settle" class="primary">接收战果</button>':`<button id="attack" class="primary" ${actor===null||target===null?'disabled':''}>攻击</button>${b.extended?`<div class="action-pair"><button id="tactic" ${actor===null||target===null?'disabled':''}>计略</button><button id="duel" ${actor===null||target===null?'disabled':''}>单挑</button></div>`:''}<button id="retreat">退却</button>`}</div>`;
 if(game.phase==='result')$('#settle').onclick=async()=>{const next=own==='defenders'?b.target:b.outcome==='victory'?b.target:b.source;if(await command('settle',{battle_id:b.id})){selectedCity=next;render();}};
 else{if($('#tactic'))$('#tactic').onclick=()=>tactics(b);if($('#duel'))$('#duel').onclick=()=>{openDialog('单挑挑战','<p>对手可能拒绝。挑战消耗本队行动；接受后进入招式交锋。</p>','<button data-cancel>取消</button><button id="confirm-duel" class="primary">确认挑战</button>');$('#confirm-duel').onclick=async()=>{if(await command('duel_start',{battle_id:b.id,actor,target}))dialog.close();};};$('#attack').onclick=()=>command('attack',{battle_id:b.id,actor,target});$('#retreat').onclick=()=>{openDialog('退却确认','<p>保留已发生的兵损。攻方返回原城；守方撤离会失去城池，武将优先退往相邻本方城，无法退往时转在野。</p>','<button data-cancel>继续作战</button><button id="confirm-retreat" class="primary">确认退却</button>');$('#confirm-retreat').onclick=async()=>{if(await command('retreat',{battle_id:b.id}))dialog.close();};};}
}
function render(){
 if(!view)return;
 MarchCore.update(view);
 GameI18n.registerScenarios(view.catalog.scenarios);
 $('#inspector').classList.remove('setup-menu');
 const game=view.game;
 $('#library').disabled=!view.catalog.library;
 $('#save').disabled=!game;
 $('#restart').disabled=!game;
 $('#main-menu').disabled=busy||!game||!!setupPreview;
 $('#main-menu').setAttribute('aria-expanded',String(!!setupPreview));
 cloudSaveUI?.refreshButton();
 $('#date').textContent=game?`${game.year}年${game.month}月　第${game.turn}回合`:'选择势力';
 if(!game){renderMap();selectFaction();return;}
 if(!selectedCity||!game.cities[selectedCity])selectedCity=Object.values(game.cities).find(c=>c.owner===game.player)?.id||view.catalog.active_cities[0];
 if(game.phase==='battle'||game.phase==='result')renderBattle();
 else{renderMap();if(game.phase==='city')renderCity();else if(game.phase==='arrivals'){$('#inspector').innerHTML='<h2>行军到达</h2><p>部队已到达预计月份。处理到达后入城或进入战斗；满城、易主和路线中断会重新核对。</p><div class="actions"><button id="process-arrivals" class="primary">处理到达部队</button></div>';$('#process-arrivals').onclick=()=>command('arrivals');}else if(game.phase==='ai'){$('#inspector').innerHTML='<div class="inspector-heading"><h2>电脑回合</h2></div><p>电脑处理人事、调兵和出征。遭到攻击时由本方操作守军；接收战果后继续电脑行动，再推进年月。</p><div class="actions"><button id="run-ai" class="primary">执行电脑行动</button></div>';$('#run-ai').onclick=()=>command('ai',{turn:game.turn});}else{$('#inspector').innerHTML=`<h2>${game.extension?.outcome==='victory'?'天下归一':'战役结束'}</h2><p>本次战役已结算，可保存或重新选择势力。</p><div class="actions"><button id="play-again" class="primary">重新选择势力</button></div>`;$('#play-again').onclick=()=>selectFaction();}}
 if(game.extension?.travel)$('#inspector').insertAdjacentHTML('beforeend',renderMarches());
 if(game.extension)$('#inspector').insertAdjacentHTML('beforeend',factionLedger());
 $('#journal').innerHTML=game.log.slice(-5).map(t=>`<li>${escapeHtml(displayLog(t))}</li>`).join('');
}
$('#rules').onclick=()=>openDialog('规则说明',`<div class="rules-body"><p>每城${capacity()}人；每方出战最多10人，包含主将。</p><ul>${view.catalog.notes.map(t=>`<li>${escapeHtml(t)}</li>`).join('')}</ul><p>总人物库${view.catalog.library_count}人。仅已登场且配置齐全的人物进入本局。随机种子决定招募、战斗等判定的随机序列；相同种子与操作可重现战局，保存会保留随机序列进度。</p></div>`,'<button data-cancel>返回战役</button>');
$('#library').onclick=showLibrary;
$('#main-menu').onclick=()=>{if(!busy)selectFaction();};
$('#restart').onclick=()=>selectFaction();
$('#save').onclick=async()=>{
 if(busy)return;
 try{const save=await request('/api/save',undefined,{text:true});localStorage.setItem('three-kingdoms-demo-save',save);const blob=new Blob([save],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=GameI18n.t(view.catalog.title)+' '+GameI18n.t('存档')+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);notice('进度已保存。可用“读取进度”恢复，也可保留下载的存档文件。');}catch(e){notice(e.message,true);}
};
async function loadSave(save,guard=()=>true){if(busy||!guard())return false;setBusy(true);try{view=await request('/api/load',SaveTransfer.loadBody(save,view.revision),{raw:true});setupPreview=null;selectedCity=null;actor=target=null;dialog.close();render();notice('进度已恢复。');return true;}catch(e){notice(e.message,true);return false;}finally{await new Promise(resolve=>setTimeout(resolve,180));setBusy(false);}}
$('#load').onclick=()=>{const saved=localStorage.getItem('three-kingdoms-demo-save');openDialog('读取进度',`<div class="save-actions"><button id="load-local" ${saved?'':'disabled'}>读取本机保存</button><label class="field" for="save-file">选择存档文件<input id="save-file" type="file" accept=".json,application/json"></label></div><p class="small">存档无效时会保留当前进度。</p>`,'<button data-cancel>取消</button>');$('#load-local').onclick=()=>{try{loadSave(saved);}catch(e){notice('存档无效，当前进度未改变。',true);}};$('#save-file').onchange=async()=>{try{const file=$('#save-file').files[0];if(!file)return;if(file.size>2*1024*1024)throw new Error('too large');await loadSave(await file.text());}catch(e){notice('存档无效，当前进度未改变。',true);}};};
GameI18n.ready.then(()=>Promise.all([request('/api/state'),request('/assets/city-positions.json'),request('/api/cloud-config').catch(()=>({enabled:false,slots:5}))])).then(([value,positions,cloudConfig])=>{
 view=value;mapPositions=positions;render();if(view.game)selectFaction();
 cloudSave=CloudSave.create(cloudConfig);
 cloudSaveUI=CloudSaveUI.create({cloud:cloudSave,getView:()=>view,getRawSave:()=>request('/api/save',undefined,{text:true}),loadRawSave:loadSave,openDialog,notice,isBusy:()=>busy});
 cloudSave.init().catch(()=>cloudSaveUI.refreshButton());
}).catch(e=>notice('游戏未能载入，请确认本地服务正在运行。',true));
