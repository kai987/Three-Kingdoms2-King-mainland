#!/usr/bin/env node
'use strict';
// Compile only existing campaign legs from the actual currently painted SVG
// network. The catalogue's routes decide connectivity; art never adds a link.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const ROOT=path.resolve(__dirname,'..'),read=p=>fs.readFileSync(path.join(ROOT,p));
const json=p=>JSON.parse(read(p)),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const key=p=>p.map(n=>Math.round(n*1e6)/1e6).join(','),pair=(a,b)=>[a,b].sort().join(':');
function reversePath(d){
 const tokens=d.match(/[MLQ]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?/g)||[];
 if(tokens.join('').replaceAll('+','')!==d.replace(/[\s,]/g,'').replaceAll('+',''))throw Error('Unsupported rendered SVG path');
 let at=0,current=null;const segments=[],number=()=>{const n=Number(tokens[at++]);if(!Number.isFinite(n))throw Error('Invalid SVG coordinate');return n;};
 while(at<tokens.length){const cmd=tokens[at++];if(cmd==='M'){if(current)throw Error('Expected one SVG subpath');current=[number(),number()];continue;}
  if(!current||!['L','Q'].includes(cmd))throw Error('Invalid rendered SVG command');
  const control=cmd==='Q'?[number(),number()]:null,end=[number(),number()];segments.push({cmd,start:current,end,control});current=end;
 }
 if(!current)return '';
 return 'M'+current.join(' ')+segments.reverse().map(s=>s.cmd+(s.control?s.control.join(' ')+' ':'')+s.start.join(' ')).join('');
}
function shortest(graph,start,end,blocked=new Set()){
 const distances=new Map([[start,0]]),previous=new Map(),pending=[[0,start]];
 while(pending.length){
  pending.sort((a,b)=>b[0]-a[0]||b[1].localeCompare(a[1]));const [distance,here]=pending.pop();
  if(distance!==distances.get(here))continue;
  if(here===end){const edges=[];for(let at=end;at!==start;){const p=previous.get(at);edges.push(p.edge);at=p.from;}return {length:distance,edges:edges.reverse()};}
  for(const edge of graph.get(here)||[]){if(blocked.has(edge.to)&&edge.to!==end)continue;const next=distance+edge.length;
   if(next+1e-8<(distances.get(edge.to)??Infinity)){distances.set(edge.to,next);previous.set(edge.to,{from:here,edge});pending.push([next,edge.to]);}
  }
 }
 return null;
}
async function build({output='game/config/route-geometry.json'}={}){
 const {chromium}=require('playwright');
 const source=json('game/config/road-centers.json'),presentation=json('game/config/map-source.json').presentation;
 // Read canonical sources before timing, so changing a quote cannot change
 // geometry inputs or create a catalogue/geometry build dependency cycle.
 const canonical=JSON.parse(execFileSync('python3',['-B','-c',
  "import json,sys;sys.path.insert(0,'game');from build_campaigns import load_sources;idx,cs=load_sources(timing=False);keys=('id','from','to','mode','draw');out=[dict(cities=[dict(id=x['id'],position=x['position']) for x in c['cities']],travel_routes=[{k:r[k] for k in keys if k in r} for r in c['travel_routes']],exploration_routes=[{k:r[k] for k in keys if k in r} for r in c['exploration_routes']],regional_roads=c['regional_roads']) for c in cs];assert all(c==out[0] for c in out);print(json.dumps(dict(data=out[0],catalogs=len(cs)),ensure_ascii=False))"
 ],{cwd:ROOT,encoding:'utf8',maxBuffer:16*1024*1024}));
 const current=canonical.data,positions=Object.fromEntries(current.cities.map(c=>[c.id,c.position]));
 const app=read('game/app.js').toString(),pathSource=app.slice(app.indexOf('function smoothMapPath('),app.indexOf('function mapBackgroundHref('));
 const context={view:{catalog:current},setupPreview:null,mapPosition:c=>c.position};vm.createContext(context);vm.runInContext(pathSource,context);
 const corrected=JSON.parse(execFileSync('python3',['-B','-c',"import json,sys;sys.path.insert(0,'game');from road_centers import build;s=json.load(open('game/config/road-centers.json'));c=json.load(open('game/config/campaigns/shared.json'));print(json.dumps(build(s,{v['id']:v['position'] for v in c['catalog']['cities']})))"],{cwd:ROOT,encoding:'utf8'}));
 const replacements=new Map(corrected.changes.map(c=>[c.index,c.new_d])),removed=new Set(corrected.removed_obsolete_paths.map(c=>c.index));
 const strokes=source.original_paths.flatMap((d,i)=>removed.has(i)?[]:[{d:replacements.get(i)??d,source:'baked:'+i}]).filter(x=>x.d);
 const dynamic=new Map();
 const draw=(route,{smooth=false}={})=>route.draw.map((part,index)=>({mode:part.mode,d:part.mode!=='land'?context.smoothMapPath(part.points):context.landMapPath(part.points,{smooth,from:index===0?route.from:null,to:index===route.draw.length-1?route.to:null})}));
 function explicit(route,options){const parts=draw(route,options);dynamic.set(pair(route.from,route.to),{from:route.from,to:route.to,parts});for(const part of parts)if(part.mode==='land')strokes.push({d:part.d,source:'dynamic:'+route.from+':'+route.to});}
 for(const route of current.regional_roads||[])explicit(route,{smooth:true});
 for(const route of presentation.expansion_connections)if(route.mode==='land')explicit(route);
 for(const route of presentation.added_land_roads){const d=context.landMapPath(route.new_branch,{to:route.to});strokes.push({d,source:'branch:'+route.from+':'+route.to});}
 const routes=[...current.travel_routes,...current.exploration_routes];
 const allPaths=new Set(strokes.flatMap(s=>s.d.match(/M[^M]*/g)||[]));
 for(const route of routes)if(route.mode==='sea'||route.mode==='river')for(const part of draw(route))for(const d of part.d.match(/M[^M]*/g)||[])allPaths.add(d);
 for(const entry of dynamic.values())for(const part of entry.parts)for(const d of part.d.match(/M[^M]*/g)||[])allPaths.add(d);
 const browser=await chromium.launch({channel:'chrome',headless:true});let measured;
 try{const page=await browser.newPage();measured=await page.evaluate(paths=>{
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),p=document.createElementNS(svg.namespaceURI,'path');svg.append(p);document.body.append(svg);
  return paths.map(d=>{p.setAttribute('d',d);const length=p.getTotalLength(),a=p.getPointAtLength(0),b=p.getPointAtLength(length);return {d,length_px:length,start:[a.x,a.y],end:[b.x,b.y]};});
 },[...allPaths]);}finally{await browser.close();}
 const measures=new Map(measured.map(p=>[p.d,p]));
 const graph=new Map(),dedup=new Set();
 for(const stroke of strokes)for(const d of stroke.d.match(/M[^M]*/g)||[]){const m=measures.get(d);if(!m.length_px)continue;const a=key(m.start),b=key(m.end),id=pair(a,b)+':'+d;if(dedup.has(id))continue;dedup.add(id);
  if(!graph.has(a))graph.set(a,[]);if(!graph.has(b))graph.set(b,[]);
  graph.get(a).push({to:b,length:m.length_px,d,reverse:false,source:stroke.source});
  graph.get(b).push({to:a,length:m.length_px,d,reverse:true,source:stroke.source});
 }
 const cityNodes=new Set(Object.values(positions).map(key)),compiled={},unmatched=[],thirdCityExceptions=[];
 function part(mode,pieces){const first=pieces[0],last=pieces.at(-1),a=first.reverse?measures.get(first.d).end:measures.get(first.d).start,b=last.reverse?measures.get(last.d).start:measures.get(last.d).end;
  const length=pieces.reduce((n,p)=>n+measures.get(p.d).length_px,0),chord=Math.hypot(b[0]-a[0],b[1]-a[1]);
  return {mode,start:a,end:b,d:pieces.map(p=>p.reverse?reversePath(p.d):p.d).join(''),length_px:Math.round(length*1e6)/1e6,chord_px:Math.round(chord*1e6)/1e6,pieces:pieces.map(({d,reverse})=>({d,reverse:!!reverse}))};}
 for(const route of routes){
  const id=route.id;
  if(compiled[id])throw Error('Duplicate logical route ID: '+id);
  if(route.mode==='sea'||route.mode==='river'){
   const parts=draw(route).map(p=>part(p.mode,(p.d.match(/M[^M]*/g)||[]).map(d=>({d,reverse:false}))));
   compiled[id]={from:route.from,to:route.to,mode:route.mode,parts};continue;
  }
  const specific=dynamic.get(pair(route.from,route.to));
  if(specific){let pieces=specific.parts.flatMap(p=>(p.d.match(/M[^M]*/g)||[]).map(d=>({d,reverse:false})));
   if(specific.from!==route.from)pieces=pieces.reverse().map(q=>({...q,reverse:!q.reverse}));
   compiled[id]={from:route.from,to:route.to,mode:'land',parts:[part('land',pieces)]};continue;
  }
  const start=key(positions[route.from]),end=key(positions[route.to]),blocked=new Set([...cityNodes].filter(n=>n!==start&&n!==end));
  let found=shortest(graph,start,end,blocked);
  if(!found){const loose=shortest(graph,start,end);if(loose){thirdCityExceptions.push({id,via:loose.edges.map(e=>e.to).filter(n=>blocked.has(n)).map(n=>Object.keys(positions).find(c=>key(positions[c])===n)),policy:'Existing direct logical leg shares a displayed city-center road; no intermediate stop or route link is inserted'});found=loose;}else {unmatched.push(id);continue;}}
  compiled[id]={from:route.from,to:route.to,mode:'land',parts:[part('land',found.edges)]};
 }
 const ratios={land:[],sea:[],river:[]};for(const[id,r]of Object.entries(compiled))for(const p of r.parts)if(p.chord_px)ratios[p.mode].push({id,ratio:p.length_px/p.chord_px});
 const extrema=Object.fromEntries(Object.entries(ratios).map(([mode,rows])=>[mode,{min:rows.sort((a,b)=>a.ratio-b.ratio)[0],max:rows.at(-1)}]));
 const sourceIndex=json('game/config/campaigns/index.json');
 const inputs=['game/build_route_geometry.cjs','game/build_campaigns.py','game/config/road-centers.json','game/road_centers.py','game/config/navigation-geometry.json','game/config/route-corridors.json','game/build_navigation_geometry.cjs','game/config/river-network.json','game/river_network.py','game/config/map-source.json','game/app.js','game/config/campaigns/shared.json','game/config/campaigns/index.json',...sourceIndex.scenarios.map(s=>'game/config/campaigns/'+s.file)];
 const result={schema:'tk2-route-geometry-v1',policy:'Existing logical legs only. Actual rendered SVG curves; no straight-line fallback. Reviewed shared-city passages do not insert logical links or intermediate stops. Geographic conversion belongs to the campaign compiler.',sources:Object.fromEntries(inputs.map(p=>[p,sha(read(p))])),input_geometry_sha256:sha(Buffer.from(JSON.stringify(current))),routes:compiled,audit:{catalogs:canonical.catalogs,input_routes:routes.length,compiled_routes:Object.keys(compiled).length,graph_nodes:graph.size,graph_strokes:strokes.length,unmatched,shared_city_pass_through:thirdCityExceptions,curvature:extrema}};
 if(output)fs.writeFileSync(path.resolve(ROOT,output),JSON.stringify(result,null,2)+'\n');return result;
}
module.exports={shortest,reversePath,build};
if(require.main===module){const args=process.argv.slice(2),out=args.includes('--output')?args[args.indexOf('--output')+1]:'game/config/route-geometry.json';build({output:out}).then(r=>{console.log(JSON.stringify(r.audit,null,2));if(r.audit.unmatched.length)process.exitCode=1;}).catch(e=>{console.error(e);process.exitCode=1;});}
