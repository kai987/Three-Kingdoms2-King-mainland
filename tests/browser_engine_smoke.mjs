#!/usr/bin/env node
/* Real WebAssembly + CPU replay of the shipped, isolated browser campaign. */
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {gunzipSync} from 'node:zlib';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const build=path.resolve(root,process.argv[2]||'build/web');
const runtimeDirectory=path.join(root,'tools/web-runtime/node_modules/pyodide');
const candidateSave=process.argv[3];
const regionalSave=process.env.TK2_REGIONAL_BROWSER_FIXTURE;
const granarySave=process.env.TK2_GRANARY_BROWSER_FIXTURE;
const transportSave=process.env.TK2_TRANSPORT_CAPACITY_BROWSER_FIXTURE;
const transshipmentSave=process.env.TK2_TRANSSHIPMENT_BROWSER_FIXTURE;
const sha=value=>createHash('sha256').update(value).digest('hex');
const decode=bytes=>new TextDecoder('utf-8',{fatal:true}).decode(bytes);
const responseDecoder=new TextDecoder('utf-8',{fatal:true,ignoreBOM:true});
const jsonFile=name=>JSON.parse(fs.readFileSync(name,'utf8'));
const manifest=jsonFile(path.join(build,'runtime/engine-manifest.json'));
assert.equal(manifest.schema,'tk2-browser-engine-v1');
assert.equal(manifest.pyodide_version,'314.0.7');
assert.equal(jsonFile(path.join(runtimeDirectory,'package.json')).version,manifest.pyodide_version);
assert.equal(manifest.catalogs.length,29,'the release includes all 29 scenarios');
function artifact(url){
 assert.equal(typeof url,'string');
 const resolved=path.resolve(build,url);
 assert(resolved.startsWith(build+path.sep),'runtime artifacts stay inside the build');
 return fs.readFileSync(resolved);
}
const bundle=artifact(manifest.python_bundle.url),previewFile=artifact(manifest.previews.url),previewBytes=manifest.previews.encoding==='gzip'?gunzipSync(previewFile):previewFile;
assert.equal(sha(bundle),manifest.python_bundle.sha256,'shipped Python bundle integrity');
assert.equal(sha(previewBytes),manifest.previews.sha256,'shipped opening preview integrity');
const packedPreviews=JSON.parse(decode(previewBytes));
const previews=Array.isArray(packedPreviews)?packedPreviews:packedPreviews.rows.map(row=>({...row.values,...Object.fromEntries(Object.entries(row.refs).map(([field,index])=>[field,packedPreviews.shared[index].value]))}));
assert.equal(previews.length,29);
const initial=manifest.initial_scenario;
const another=manifest.catalogs.find(row=>row.id!==initial)?.id;
assert(another,'a second scenario is required for the lazy switching check');
const logisticsScenario='mainland217-07';
const regionalScenario='mainland208-10';
const catalogs=new Map();
for(const identity of new Set([initial,another,logisticsScenario,...(regionalSave||granarySave||transportSave?[regionalScenario]:[]),
 ...(transshipmentSave?['mainland227-02']:[])])){
 const row=manifest.catalogs.find(row=>row.id===identity);
 assert.match(row.path,/^\/tk2\/game\/data\/campaigns\/[a-zA-Z0-9-]+\.json$/);
 const bytes=gunzipSync(artifact(row.url));
 assert.equal(bytes.length,row.bytes);
 assert.equal(sha(bytes),row.sha256,'decompressed catalog retains its exact save identity');
 assert.equal(JSON.parse(decode(bytes)).id,row.id);
 catalogs.set(identity,{row,bytes});
}

const referenceScript=String.raw`
from hashlib import sha256
import json, os, pathlib, sys, tempfile, zipfile
request=json.load(sys.stdin)
os.environ['MARCH_CORE_BACKEND']='python'
with tempfile.TemporaryDirectory(prefix='tk2-cpu-replay-') as directory:
    mount=pathlib.Path(directory)
    with zipfile.ZipFile(request['bundle']) as archive:
        archive.extractall(mount)
    sys.path.insert(0,str(mount/'source'))
    from remake.browser_runtime import BrowserRuntime
    catalog_paths={row['id']:str(mount/row['path'].removeprefix('/tk2/'))
                   for row in request['manifest']['catalogs']}
    for row in request['catalogs']:
        target=pathlib.Path(catalog_paths[row['id']])
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(pathlib.Path(row['raw']).read_bytes())
    previews=json.loads(pathlib.Path(request['previews']).read_text(encoding='utf-8'))
    engines={key:BrowserRuntime(catalog_paths,previews,request['manifest']['initial_scenario'])
             for key in ('primary','isolated')}
    results=[]
    for operation in request['trace']:
        bridge=engines[operation['instance']]
        # Missing optional body matches the browser's GET calling convention.
        response=(bridge.dispatch_json(operation['path'],operation['method'],operation['body'])
                  if 'body' in operation else
                  bridge.dispatch_json(operation['path'],operation['method']))
        semantic=json.dumps(json.loads(response['body']),sort_keys=True,ensure_ascii=False,allow_nan=False)
        results.append(dict(status=response['status'],
                            response_semantic_sha256=sha256(semantic.encode('utf-8')).hexdigest(),
                            **({'save':response['body']} if operation['path']=='/api/save' and response['status']==200 else {})))
    final=engines['primary'].dispatch_json('/api/save')
    assert final['status']==200
    print(json.dumps(dict(results=results,save=final['body'],
                         rng=json.loads(final['body'])['state']['rng']),ensure_ascii=False))
`;

let py,dispatchForSmoke;
const bridges=new Map(),trace=[],wasmResults=[];
function request(pathname,{method='GET',body,instance='primary',status=200}={}){
 const bridge=bridges.get(instance);assert(bridge,'known isolated runtime instance');
 const operation={instance,path:pathname,method,...(body===undefined?{}:{body})};
 if(body!==undefined)assert.equal(typeof body,'string','POST bodies remain JSON text');
 // JS null is JsNull in Pyodide 314, not Python None. Omit body for reads.
 const result=body===undefined?dispatchForSmoke(bridge,pathname,method):dispatchForSmoke(bridge,pathname,method,body);
 let response;
 try{response=result.toJs({create_pyproxies:false});}finally{result.destroy();}
 const [responseStatus,responseBytes,semantic]=response;
 assert(responseBytes instanceof Uint8Array,'WASM response is UTF-8 bytes');
 const responseBody=responseDecoder.decode(responseBytes);
 assert.equal(responseStatus,status,`${instance} ${method} ${pathname}: ${responseBody.slice(0,300)}`);
 trace.push(operation);
 wasmResults.push({status:responseStatus,response_semantic_sha256:semantic,
  ...(pathname==='/api/save'&&status===200?{save:responseBody}:{})});
 return responseBody;
}
function state(instance='primary'){return JSON.parse(request('/api/state',{instance}));}
function command(view,kind,payload={},instance='primary'){
 return JSON.parse(request('/api/command',{method:'POST',instance,
  body:JSON.stringify({kind,payload,revision:view.revision})}));
}
function load(raw,revision,instance='primary'){
 // Preserve the exported save text inside the request; avoid a parse/stringify
 // pass like the production JSON-file and cloud-slot import path.
 return JSON.parse(request('/api/load',{method:'POST',instance,body:`{"save":${raw},"revision":${revision}}`}));
}
function unchangedFailure(pathname,settings){
 const before=request('/api/save');
 request(pathname,settings);
 assert.equal(request('/api/save'),before,'rejected operations retain every saved byte and RNG draw');
}
function createBridge(name){
 const value=py.runPython(`BrowserRuntime(json.loads(_tk2_paths), json.loads(_tk2_previews), _tk2_initial)`);
 bridges.set(name,value);
}

const temporary=fs.mkdtempSync(path.join(os.tmpdir(),'tk2-wasm-smoke-'));
try{
 console.log('browser engine smoke: loading real Pyodide 314.0.7 WebAssembly from local pinned assets');
 const {loadPyodide}=await import(pathToFileURL(path.join(runtimeDirectory,'pyodide.mjs')).href);
 py=await loadPyodide({indexURL:runtimeDirectory+path.sep});
 assert.equal(py.version,manifest.pyodide_version);
 py.unpackArchive(new Uint8Array(bundle),'zip',{extractDir:'/tk2'});
 for(const {row,bytes} of catalogs.values()){
  py.FS.mkdirTree(path.posix.dirname(row.path));
  py.FS.writeFile(row.path,new Uint8Array(bytes));
 }
 py.globals.set('_tk2_paths',JSON.stringify(Object.fromEntries(manifest.catalogs.map(row=>[row.id,row.path]))));
 py.globals.set('_tk2_previews',decode(previewBytes));
 py.globals.set('_tk2_initial',initial);
 py.runPython(`import sys, json, os
sys.path.insert(0, '/tk2/source')
os.environ['MARCH_CORE_BACKEND'] = 'python'
from remake.browser_runtime import BrowserRuntime
from hashlib import sha256
def _tk2_smoke_dispatch(bridge, *args):
    response=bridge.dispatch_json(*args)
    body=response['body']
    # Hash the original JSON inside WASM and transfer the complete UTF-8 body once.
    semantic=json.dumps(json.loads(body),sort_keys=True,ensure_ascii=False,allow_nan=False)
    return response['status'],body.encode('utf-8'),sha256(semantic.encode('utf-8')).hexdigest()`);
 dispatchForSmoke=py.globals.get('_tk2_smoke_dispatch');
 const tacticalData=JSON.parse(py.runPython(`from remake.battle_grid import _library as _battle_library
from remake.tactical_ai import _learnability as _battle_learnability
json.dumps({'maps':len(_battle_library()[0]),'cities':len(_battle_library()[1]),
            'special_people':len(_battle_learnability()[1])})`));
 assert.deepEqual(tacticalData,{maps:30,cities:158,special_people:21},
  'Actual WebAssembly loads the same original battlefield and tactic tables as native Python');
 createBridge('primary');createBridge('isolated');
 const isolatedMenu=state('isolated');
 assert.equal(isolatedMenu.game,null);
 assert.equal(isolatedMenu.catalog.scenarios.length,29);
 let view=state();
 assert.equal(view.game,null);
 assert.equal(view.catalog.scenarios.length,29);
 assert.deepEqual(view.catalog.scenarios.map(row=>row.id),previews.map(row=>row.id));
 const opening=previews.find(row=>row.id===initial);
 const eligible=opening.factions.map(row=>row.id).filter(id=>opening.faction_officers[id]>=2&&opening.faction_resources[id]?.cities>0);
 assert(eligible.length,'initial scenario contains a playable force with multiple officers');
 const faction=eligible.includes('shu')?'shu':eligible[0];
 view=command(view,'new',{scenario:initial,faction,seed:20261023,difficulty:'normal'});
 assert.equal(view.game.player,faction);
 assert.equal(view.game.phase,'city');
 assert.deepEqual(state('isolated'),isolatedMenu,'another instance is still an untouched menu');
 const openingSave=request('/api/save'),openingRng=JSON.parse(openingSave).state.rng;
 const troopCap=view.catalog.rules.officer_troop_capacity;
 assert.equal(troopCap,10000);
 const ownCity=Object.values(view.game.cities).find(city=>city.owner===faction&&city.reserves>0&&city.roster.officer_ids.some(id=>view.game.officers[id].troops<troopCap));
 assert(ownCity,'the chosen force can meaningfully allocate reserve troops');
 const preview=JSON.parse(request('/api/city-preview?'+new URLSearchParams({scenario:initial,city:ownCity.id})));
 assert.equal(preview.city.id,ownCity.id);
 assert.equal(request('/api/save'),openingSave,'opening inspection cannot change RNG or state');
 assert.deepEqual(JSON.parse(request('/api/save')).state.rng,openingRng);
 const officer=ownCity.roster.officer_ids.find(id=>view.game.officers[id].troops<troopCap);
 const originalTroops=view.game.officers[officer].troops;
 const amount=Math.min(7,ownCity.reserves,troopCap-originalTroops);
 assert(amount>0);
 view=command(view,'allocate',{city:ownCity.id,officer,troops:originalTroops+amount});
 assert.equal(view.game.officers[officer].troops,originalTroops+amount);
 assert.equal(view.game.cities[ownCity.id].reserves,ownCity.reserves-amount);
 const allocated=request('/api/save');
 view=load(allocated,view.revision);
 assert.equal(request('/api/save'),allocated,'raw save import/export is byte-identical');

 const startTurn=view.game.turn;
 view=command(view,'end_turn');
 let aiCalls=0,battleSettlements=0;
 for(let step=0;step<48&&!(view.game.phase==='city'&&view.game.turn>startTurn);step++){
  switch(view.game.phase){
   case 'ai':view=command(view,'ai',{turn:view.game.turn});aiCalls++;break;
   case 'arrivals':view=command(view,'arrivals');break;
   case 'battle':view=command(view,'retreat',{battle_id:view.game.battle.id});break;
   case 'result':view=command(view,'settle',{battle_id:view.game.battle.id});battleSettlements++;break;
   default:assert.fail(`unexpected campaign phase during bounded turn advancement: ${view.game.phase}`);
  }
 }
 assert(aiCalls>0,'real AI decisions execute in WebAssembly');
 assert.equal(view.game.phase,'city','bounded AI and battle settlement returns to strategy');
 assert.equal(view.game.turn,startTurn+1,'exactly one ten-day turn advances');
 const afterTurn=request('/api/save');
 assert(JSON.parse(afterTurn).state.rng.draws>openingRng.draws,'AI consumes the actual deterministic random stream');
 unchangedFailure('/api/python',{status:404});
 unchangedFailure('/api/command',{method:'POST',status:409,
  body:JSON.stringify({kind:'allocate',payload:{city:ownCity.id,officer,troops:999},revision:view.revision-1})});
 unchangedFailure('/api/command',{method:'POST',status:400,
  body:`{"kind":"ai","kind":"end_turn","payload":{},"revision":${view.revision}}`});
 const corrupted=JSON.parse(afterTurn);corrupted.checksum='0'.repeat(64);
 unchangedFailure('/api/load',{method:'POST',status:400,
  body:JSON.stringify({save:corrupted,revision:view.revision})});
 assert.equal(request('/api/save'),afterTurn);

 const otherOpening=previews.find(row=>row.id===another);
 const otherFaction=otherOpening.factions.find(row=>otherOpening.faction_officers[row.id]>0&&otherOpening.faction_resources[row.id]?.cities>0)?.id;
 assert(otherFaction,'second scenario includes a force with officers');
 view=command(view,'new',{scenario:another,faction:otherFaction,seed:20261023});
 assert.equal(view.catalog.scenario_id,another);
 assert.equal(JSON.parse(request('/api/save')).scenario,another);
 view=load(afterTurn,view.revision);
 assert.equal(view.catalog.scenario_id,initial);
 const finalSave=request('/api/save');
 assert.equal(finalSave,afterTurn,'returning from another scenario restores the exact original save');
 assert.deepEqual(state('isolated'),isolatedMenu,'all primary commands leave the other instance untouched');
 assert.equal(JSON.parse(request('/api/march-status')).engine,'python');

 // Exercise the actual V2 quotation, route selection and granary write once
 // on the independently mounted browser campaign.
 const seat='isolated',source='shujun',target='bajun';
 let travel=command(isolatedMenu,'new',{scenario:logisticsScenario,faction:'shu',seed:2026},seat);
 assert.equal(travel.game.extension.logistics_rules_version,2);
 const sourceCity=travel.game.cities[source],ruler=travel.game.extension.leaders.shu;
 const escort=sourceCity.roster.officer_ids.find(id=>id!==ruler&&travel.game.officers[id].health>0);
 assert.notEqual(escort,undefined);
 const travelDraft={source,target,officers:[escort],route_mode:'minimum_grain'};
 const previous=request('/api/save',{instance:seat});
 const choices=JSON.parse(request('/api/logistics-preview',{method:'POST',instance:seat,
  body:JSON.stringify({...travelDraft,revision:travel.revision,purpose:'transfer',cargo:0,reserves:0})}));
 assert.equal(request('/api/save',{instance:seat}),previous);
 const promise=choices.primary;
 assert(promise&&choices.fastest&&choices.minimum);
 assert.equal(promise.logistics.total_grain,promise.logistics.base_grain+promise.logistics.extra_grain);
 assert.equal(Object.values(promise.logistics.time_ticks).reduce((a,b)=>a+b,0),
  promise.days*promise.logistics.ticks_per_day);
 travel=command(travel,'transfer',travelDraft,seat);
 assert.equal(travel.game.cities[source].grain,sourceCity.grain-promise.logistics.initial_grain);
 const committed=travel.game.extension.travel.marches.find(row=>row.target===target);
 assert(committed);
 assert.equal(committed.supply.loaded,promise.logistics.initial_grain);
 request('/api/save',{instance:seat});

 // A prebuilt opt-in game uses the real import, observer and save paths.
 let candidateTurns=0;
 if(candidateSave){
  const raw=fs.readFileSync(candidateSave,'utf8');
  let candidate=load(raw,travel.revision,seat);
  assert.equal(candidate.catalog.scenario_id,logisticsScenario);
  assert.equal(candidate.game.extension.ai_logistics_strategy_version,212);
  const first=candidate.game.turn;
  for(let index=0;index<3;index++)candidate=command(candidate,'observe_turn',{},seat);
  candidateTurns=candidate.game.turn-first;
  assert.equal(candidateTurns,3);
  const observed=request('/api/save',{instance:seat});
  candidate=load(observed,candidate.revision,seat);
  assert.equal(candidate.game.extension.ai_logistics_policy.after_six,60);
  assert.equal(request('/api/save',{instance:seat}),observed);
 }

 // Opt-in winter uses the same real worker, preview and save paths.
 let winter=command(state(seat),'new',{scenario:logisticsScenario,faction:'shu',
  seed:2026,weather_rules_version:22},seat);
 assert.equal(winter.game.extension.weather_rules_version,22);
 assert.equal(winter.game.extension.ai_logistics_strategy_version,211);
 const winterOpening=request('/api/save',{instance:seat});
 const winterQuote=JSON.parse(request('/api/logistics-preview',{method:'POST',instance:seat,
  body:JSON.stringify({...travelDraft,revision:winter.revision,purpose:'transfer',cargo:0,reserves:0})})).primary;
 assert.equal(winterQuote.logistics.weather.forecast,'current_conditions');
 assert.equal(winterQuote.logistics.weather.normal_days,winterQuote.logistics.weather.days);
 assert.equal(request('/api/save',{instance:seat}),winterOpening);
 winter=command(winter,'new',{scenario:initial,faction:'observer',seed:2026,weather_rules_version:22},seat);
 assert.equal(winter.catalog.weather.tick,0);
 const winterTurns=3;
 for(let index=0;index<winterTurns;index++)winter=command(winter,'observe_turn',{},seat);
 assert.equal(winter.catalog.weather.tick,30);
 assert(Object.values(winter.catalog.weather.regions).some(region=>region.snow_seen));
 const winterSave=request('/api/save',{instance:seat});
 const observedWeather=winter.catalog.weather;
 winter=load(winterSave,winter.revision,seat);
 assert.deepEqual(winter.catalog.weather,observedWeather);
 assert.equal(request('/api/save',{instance:seat}),winterSave);
 let revised=command(winter,'new',{scenario:initial,faction:'observer',seed:2026,weather_rules_version:221},seat);
 assert.equal(revised.game.extension.winter_weather.adjustments,3);
 for(let index=0;index<winterTurns;index++)revised=command(revised,'observe_turn',{},seat);
 assert.equal(revised.game.extension.weather_rules_version,221);
 assert.deepEqual(revised.catalog.weather.regions,observedWeather.regions);
 assert.deepEqual(revised.catalog.weather.ice,observedWeather.ice);
 const revisedSave=request('/api/save',{instance:seat});
 revised=load(revisedSave,revised.revision,seat);
 assert.equal(request('/api/save',{instance:seat}),revisedSave);
 assert.equal(revised.catalog.weather.tick,30);

 // A real opt-in V2.3 session uses the same observer turn, archive and CPU trace.
 let climate=command(state(seat),'new',{scenario:logisticsScenario,faction:'observer',seed:2026,
  weather_rules_version:23,weather_options:{exceptional_cold_wave:false}},seat);
 assert.equal(climate.game.extension.winter_weather.options.exceptional_cold_wave,false);
 assert.equal(climate.catalog.weather.regions.liaodong.depth_limit,50);
 const openingClimate=climate.game.turn;
 climate=command(climate,'observe_turn',{},seat);
 assert.equal(climate.game.turn,openingClimate+1);
 assert.equal(climate.game.extension.winter_weather.tick,10);
 const climateSave=request('/api/save?compact=1',{instance:seat});
 climate=load(climateSave,climate.revision,seat);
 assert.equal(climate.game.extension.weather_rules_version,23);
 assert.equal(request('/api/save?compact=1',{instance:seat}),climateSave);
 revised=climate;

 // The separate regional fixture was constructed using the published catalog
 // and comes through the same file import and authoritative worker commands.
 let regionalMarketOrder=null;
 if(regionalSave){
  const raw=fs.readFileSync(regionalSave,'utf8');
  let market=load(raw,revised.revision,seat);
  assert.equal(market.catalog.scenario_id,regionalScenario);
  assert.equal(market.game.extension.regional_market_rules_version,301);
  const regionalSource='wujun',regionalTarget='kuaiji',qty=5000,purpose='trade';
  const opening=request('/api/save',{instance:seat});
  const plan=JSON.parse(request('/api/regional-market-preview',{method:'POST',instance:seat,
   body:JSON.stringify({source:regionalSource,target:regionalTarget,qty,purpose,revision:market.revision})}));
  assert.equal(request('/api/save',{instance:seat}),opening);
  const offer=plan.quotes[0],stock=market.game.extension.grain_market[regionalSource].stock;
  const gold=market.game.cities[regionalSource].gold;
  market=command(market,'regional_market_order',{action:'buy',source:regionalSource,target:regionalTarget,
   qty,purpose,token:offer.token},seat);
  assert.equal(market.game.cities[regionalSource].gold,gold-offer.gold);
  assert.equal(market.game.extension.grain_market[regionalSource].stock,stock-offer.cargo);
  regionalMarketOrder=market.game.extension.regional_market.orders['1'];
  assert.equal(regionalMarketOrder.status,'dispatched');
  const after=request('/api/save',{instance:seat});
  market=load(after,market.revision,seat);
  assert.deepEqual(market.game.extension.regional_market.orders['1'],regionalMarketOrder);
  assert.equal(request('/api/save',{instance:seat}),after);
 }

 let granaryConvoy=null;
 if(granarySave){
  const source='wujun',target='kuaiji',quantity=4000;
  let granary=load(fs.readFileSync(granarySave,'utf8'),state(seat).revision,seat);
  const granaryVersion=Number(process.env.TK2_GRANARY_TEST_VERSION||302);
  assert.equal(granary.game.extension.strategic_granary_rules_version,granaryVersion);
  if(granaryVersion===3021)assert.ok(granary.catalog.strategic_granary.cities[target].demand);
  const initial=request('/api/save',{instance:seat});
  const quotePath='/api/strategic-granary-preview';
  const quoteBody=JSON.stringify({source,target,quantity,revision:granary.revision});
  const read=()=>request(quotePath,{method:'POST',instance:seat,body:quoteBody});
  const result=read();assert.equal(read(),result);
  assert.equal(request('/api/save',{instance:seat}),initial);
  const offer=JSON.parse(result).quotes[0],opening=granary.game.cities[source].grain;
  const targetGrain=granary.game.cities[target].grain;
  granary=command(granary,'strategic_granary_order',{action:'hold',city:target,amount:100},seat);
  granary=command(granary,'strategic_granary_order',{action:'reserve',source,target,quantity,token:offer.token},seat);
  assert.equal(granary.game.cities[source].grain,opening);
  const compact=request('/api/save?compact=1',{instance:seat});
  granary=load(compact,granary.revision,seat);
  assert.equal(granary.catalog.strategic_granary.cities[source].committed,offer.load+offer.rations);
  granary=command(granary,'strategic_granary_order',{action:'dispatch',order:1},seat);
  granaryConvoy=granary.game.extension.strategic_granary.orders['1'].convoy_id;
  assert.equal(granary.game.cities[source].grain,opening-offer.load-offer.rations);
  assert.equal(granary.game.cities[target].grain,targetGrain);
  const raw=request('/api/save',{instance:seat});
  granary=load(raw,granary.revision,seat);
  assert.equal(request('/api/save',{instance:seat}),raw);
  request('/api/command',{method:'POST',instance:seat,status:400,body:JSON.stringify({
   kind:'strategic_granary_order',payload:{action:'dispatch',order:1},revision:granary.revision})});
  assert.equal(request('/api/save',{instance:seat}),raw);
 }

 let transportConvoys=0;
 if(transportSave){
  const source='lujiang',target='danyang';
  let field=load(fs.readFileSync(transportSave,'utf8'),state(seat).revision,seat);
  assert.equal(field.game.extension.transport_capacity_rules_version,303);
  const ship=mode=>{
   const saved=request('/api/save',{instance:seat});
   const officers=field.catalog.logistics.cities[source].preview.officers;
   const plan={source,target,officers,route_mode:mode};
   const quotation=JSON.parse(request('/api/logistics-preview',{method:'POST',instance:seat,
    body:JSON.stringify({...plan,revision:field.revision,purpose:'convoy',cargo:47000,reserves:0})})).primary;
   assert.equal(request('/api/save',{instance:seat}),saved);
   const cap=quotation.capacity;
   assert.ok(cap.physical_capacity>=cap.load_grain+cap.rations);
   if(mode==='river')assert.equal(cap.mode,'mixed');
   const n=field.game.extension.logistics.convoys.length;
   field=command(field,'dispatch_transport',{...plan,cargo:{grain:cap.load_grain,gold:0,reserves:0}},seat);
   assert.equal(field.game.extension.logistics.convoys.length,n+1);
   assert.equal(field.game.extension.logistics.convoys.at(-1).journeys[0].capacity_load.limit,cap.physical_capacity);
  };
  ship('land');
  const controls={city:'end_turn',ai:'ai',arrivals:'arrivals'};
  const turn=field.game.turn;
  for(let step=0;step<4&&(field.game.turn===turn||field.game.phase!=='city');step++){
   const action=controls[field.game.phase];
   assert(action,'known strategic campaign phase');
   field=command(field,action,action==='ai'?{turn:field.game.turn}:{},seat);
  }
  assert.equal(field.game.turn,turn+1);
  assert.equal(field.game.phase,'city');
  ship('river');
  const reported=field.game.extension.logistics.convoys.filter(row=>row.source===source);
  assert.equal(reported.length,2);
  const compact=request('/api/save?compact=1',{instance:seat});
  field=load(compact,field.revision,seat);
  assert.deepEqual(field.game.extension.logistics.convoys.filter(row=>row.source===source),reported);
  assert.equal(field.game.extension.transport_capacity.dispatches[source][1],1);
  request('/api/save',{instance:seat});
  transportConvoys=reported.length;
 }

 let transshipmentBatch=null;
 if(transshipmentSave){
  let field=load(fs.readFileSync(transshipmentSave,'utf8'),state(seat).revision,seat);
  const before=field.game.extension.transshipment.plans['1'];
  assert.equal(field.game.extension.transshipment_rules_version,304);
  assert.equal(before.batches.length,2);
  assert.ok(before.batches.every(batch=>batch.receipt.grain>0));
  const quote=field.catalog.transshipment.plans[0].offers.find(row=>row.source==='yulin'&&row.stage===1);
  assert.equal(quote.capacity,100000);
  assert.ok(quote.max_cargo>50000&&!quote.blocked);
  field=command(field,'transshipment_order',{action:'dispatch',plan:1,stage:1,source:'yulin',
   officer:quote.officer,grain:quote.max_cargo},seat);
  const after=field.game.extension.transshipment.plans['1'];
  const batch=after.batches.at(-1);
  assert.equal(batch.parents.length,2);
  assert.equal(batch.parents.reduce((sum,pair)=>sum+pair[1],0),batch.grain+batch.rations);
  const compact=request('/api/save?compact=1',{instance:seat});
  field=load(compact,field.revision,seat);
  assert.deepEqual(field.game.extension.transshipment.plans['1'],after);
  request('/api/save',{instance:seat});
  transshipmentBatch=batch.convoy;
 }

 // Exercise the real optional wire path, not only the legacy bridge used by
 // CPU replay. Hydration must reconstruct the same complete current view.
 const {default:wireModule}=await import(pathToFileURL(path.join(root,'game/view-cache.js')).href);
 const wireClient=wireModule.create(),fullView=state(),beforeWire=request('/api/save');
 function compactView(token){
  const result=bridges.get('primary').dispatch_compact_json('/api/state','GET','',token);
  try{const response=result.toJs({dict_converter:Object.fromEntries});assert.equal(response.status,200);return {raw:response.body,packet:JSON.parse(response.body)};}finally{result.destroy();}
 }
 const initialWire=compactView('');assert.deepEqual(wireClient.hydrate(initialWire.packet),fullView);
 const cachedWire=compactView(wireClient.token());assert(!('static_catalog' in cachedWire.packet));
 assert.deepEqual(wireClient.hydrate(cachedWire.packet),fullView);
 assert.equal(request('/api/save'),beforeWire,'Compact reads retain every saved byte and RNG draw');
 assert(Buffer.byteLength(cachedWire.raw)<Buffer.byteLength(JSON.stringify(fullView))*.6,'Cached responses omit the immutable catalog');
 console.log('browser view cache: real WASM full/cached hydration matches legacy state and exact save bytes');
 console.log(`browser engine smoke: ${trace.length} real requests, one AI turn, ${battleSettlements} battle settlements; replaying identical trace on CPU Python`);
 // Snapshot the verified build inputs so a concurrent build cannot change the
 // reference interpreter's sources or catalog identities during this check.
 const bundlePath=path.join(temporary,'python.zip'),previewsPath=path.join(temporary,'previews.json');
 fs.writeFileSync(bundlePath,bundle);fs.writeFileSync(previewsPath,previewBytes);
 const referenceCatalogs=[];
 for(const [identity,{bytes}] of catalogs){
  const raw=path.join(temporary,identity+'.json');fs.writeFileSync(raw,bytes);referenceCatalogs.push({id:identity,raw});
 }
 const reference=spawnSync(process.env.PYTHON||'python3',['-B','-c',referenceScript],{
  cwd:root,input:JSON.stringify({bundle:bundlePath,previews:previewsPath,manifest,catalogs:referenceCatalogs,trace}),
  encoding:'utf8',maxBuffer:32*1024*1024,timeout:180000,
  env:{...process.env,MARCH_CORE_BACKEND:'python',PYTHONDONTWRITEBYTECODE:'1'}
 });
 assert.ifError(reference.error);
 assert.equal(reference.status,0,reference.stderr);
 const cpu=JSON.parse(reference.stdout);
 assert.equal(cpu.results.length,wasmResults.length);
 for(let index=0;index<wasmResults.length;index++){
  const expected=wasmResults[index],actual=cpu.results[index],operation=trace[index];
  const label=`request ${index+1}: ${operation.instance} ${operation.method} ${operation.path}`;
  assert.equal(actual.status,expected.status,label+' status');
  assert.equal(actual.response_semantic_sha256,expected.response_semantic_sha256,label+' JSON response semantics');
  if('save' in expected)assert(actual.save===expected.save,label+' exact save text');
 }
 assert(cpu.save===finalSave,'final raw save agrees across CPython and real Python WebAssembly');
 const rng=JSON.parse(finalSave).state.rng;
 assert.deepEqual(cpu.rng,rng,'final RNG state and draw count agree');
 console.log(JSON.stringify({ok:true,pyodide:py.version,previews:previews.length,catalogs:catalogs.size,
  requests:trace.length,ai_turns:1,battle_settlements:battleSettlements,logistics_route_parity:true,
  save_sha256:sha(finalSave),rng,cpu_save_bytes_equal:true,v212_observer_turns:candidateTurns,
  weather_observer_turns:winterTurns,weather_save_sha256:sha(winterSave),regional_market_roundtrip:regionalMarketOrder?.convoy??null,
  granary_convoy_roundtrip:granaryConvoy,transport_capacity_roundtrip:transportConvoys,
  transshipment_batch_roundtrip:transshipmentBatch}));
}finally{
 for(const bridge of bridges.values())bridge.destroy();
 dispatchForSmoke?.destroy();
 fs.rmSync(temporary,{recursive:true,force:true});
}
