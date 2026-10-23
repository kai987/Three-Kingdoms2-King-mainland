#!/usr/bin/env node
'use strict';
/* Audit every rendered land stroke against the approved road-free water pixels.
 * The output is presentation metadata only; campaign routes and saves are not
 * rewritten. SVG sampling follows the game's actual landMapPath implementation.
 */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),vm=require('node:vm');
const {execFileSync}=require('node:child_process');
const ROOT=path.resolve(__dirname,'..');
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const read=name=>fs.readFileSync(path.resolve(ROOT,name));
const json=name=>JSON.parse(read(name));
function findWaterRuns(samples,{step=.5,bank=1.5,minWater=1.5}={}){
 const result=[];
 for(let i=0;i<samples.length;i++){
  if(!samples[i].water)continue;
  const start=i;while(i+1<samples.length&&samples[i+1].water)i++;
  const end=i;
  // A coastal road that ends at a harbour is not an ocean-spanning bridge.
  if(start===0||end===samples.length-1||(end-start+1)*step<minWater)continue;
  const before=Math.max(0,start-Math.ceil(bank/step)),after=Math.min(samples.length-1,end+Math.ceil(bank/step));
  const points=samples.slice(before,after+1).map(p=>[p.x,p.y]);
  const middle=samples[Math.floor((start+end)/2)],a=points[0],b=points.at(-1),dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy);
  if(!length)continue;
  result.push({center:[middle.x,middle.y],axis:[dx/length,dy/length],water_length:(end-start+1)*step,points});
 }
 return result;
}
function compactPoints(points){
 const q=n=>Math.round(n*100)/100,unique=[];
 for(const p of points){const point=p.map(q);if(!unique.length||unique.at(-1).some((n,i)=>n!==point[i]))unique.push(point);}
 return unique.filter((p,i)=>!i||i===unique.length-1||Math.abs((p[0]-unique[i-1][0])*(unique[i+1][1]-p[1])-(p[1]-unique[i-1][1])*(unique[i+1][0]-p[0]))>1e-6);
}
function bridgePath(points){return compactPoints(points).map((p,i)=>(i?'L':'M')+p.join(' ')).join('');}
function appPathSource(){const source=read('game/app.js').toString('utf8');return source.slice(source.indexOf('function smoothMapPath('),source.indexOf('function mapBackgroundHref('));}
async function build({ground='game/map-source/hydrology-ground.png',output='game/assets/map-bridges.json'}={}){
 const {chromium}=require('playwright'),appSource=appPathSource(),source=json('game/config/road-centers.json'),presentation=json('game/config/map-source.json').presentation;
 const index=json('game/data/campaigns/index.json'),catalogs=index.catalogs.map(name=>({path:'game/data/'+name,data:json('game/data/'+name)}));
 const geometry=JSON.parse(execFileSync('python3',['-B','-c',"import json,sys;sys.path.insert(0,'game');from road_centers import build;s=json.load(open('game/config/road-centers.json'));c=json.load(open('game/config/campaigns/shared.json'));print(json.dumps(build(s,{v['id']:v['position'] for v in c['catalog']['cities']})))"],{cwd:ROOT,encoding:'utf8'}));
 const changed=new Map(geometry.changes.map(row=>[row.index,row.new_d])),removed=new Set(geometry.removed_obsolete_paths.map(row=>row.index));
 const baked=source.original_paths.map((d,i)=>removed.has(i)?'':changed.has(i)?changed.get(i):d).filter(Boolean);
 const dynamic=new Map(),routePaths={};
 for(const {data:catalog}of catalogs){
  const context={view:{catalog},setupPreview:null,mapPosition:city=>city.position};vm.createContext(context);vm.runInContext(appSource,context);
  const add=(route,part,index,{smooth=false}={})=>{
   if(part.mode!=='land')return;
   const d=context.landMapPath(part.points,{smooth,from:index===0?route.from:null,to:index===route.draw.length-1?route.to:null});
   if(!d)return;const key=[route.from,route.to].sort().join(':');
   dynamic.set(d,true);(routePaths[key]??=[]);if(!routePaths[key].includes(d))routePaths[key].push(d);
  };
  for(const route of catalog.regional_roads||[])route.draw.forEach((part,i)=>add(route,part,i,{smooth:true}));
  for(const route of [...(catalog.river_routes||[]),...(catalog.sea_routes||[]),...(catalog.exploration_routes||[]),...presentation.expansion_connections])route.draw?.forEach((part,i)=>add(route,part,i));
  for(const route of presentation.added_land_roads){
   const d=context.landMapPath(route.new_branch,{to:route.to});dynamic.set(d,true);const key=[route.from,route.to].sort().join(':');
   (routePaths[key]??=[]);if(!routePaths[key].includes(d))routePaths[key].push(d);
  }
 }
 const all=[...new Set([...baked,...dynamic.keys()])],browser=await chromium.launch({channel:'chrome',headless:true});let analyzed;
 try{
  const page=await browser.newPage();
  analyzed=await page.evaluate(async({ground,paths,algorithm})=>{
   const image=new Image();image.src=ground;await image.decode();const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
   const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(image,0,0);const pixels=ctx.getImageData(0,0,image.width,image.height).data;
   const water=(x,y)=>{const xx=Math.floor(x),yy=Math.floor(y);if(xx<0||yy<0||xx>=image.width||yy>=image.height)return false;const i=(yy*image.width+xx)*4;return pixels[i+3]>127&&pixels[i]<75&&pixels[i+1]<140&&pixels[i+2]>165;};
   const svg=document.createElementNS('http://www.w3.org/2000/svg','svg'),element=document.createElementNS(svg.namespaceURI,'path');svg.append(element);document.body.append(svg);
   const find=(0,eval)('('+algorithm+')'),records=[];
   for(const d of paths){element.setAttribute('d',d);const length=element.getTotalLength(),samples=[];
    for(let s=0;s<length;s+=.5){const p=element.getPointAtLength(s);samples.push({x:p.x,y:p.y,water:water(p.x,p.y)});}
    if(length){const p=element.getPointAtLength(length);samples.push({x:p.x,y:p.y,water:water(p.x,p.y)});}
    records.push({d,length,crossings:find(samples)});
   }
   return {width:image.width,height:image.height,records};
  },{ground:'data:image/png;base64,'+read(ground).toString('base64'),paths:all,algorithm:findWaterRuns.toString()});
 }finally{await browser.close();}
 const bridges={},bakedIds=new Set(),byPath={},assignments={},longCrossings=[];
 function register(crossing){
  const existing=Object.entries(bridges).find(([,b])=>Math.hypot(b.center[0]-crossing.center[0],b.center[1]-crossing.center[1])<2&&Math.abs(b.axis[0]*crossing.axis[0]+b.axis[1]*crossing.axis[1])>.96);
  if(existing)return existing[0];
  const id='bridge-'+String(Object.keys(bridges).length+1).padStart(3,'0');
  bridges[id]={d:bridgePath(crossing.points),center:crossing.center.map(n=>Math.round(n*100)/100),axis:crossing.axis.map(n=>Math.round(n*1000)/1000),water_length:Math.round(crossing.water_length*100)/100};return id;
 }
 const bakedSet=new Set(baked);
 for(const row of analyzed.records){
  const ids=[...new Set(row.crossings.map(crossing=>{if(crossing.water_length>50)longCrossings.push({path:row.d,...crossing});return register(crossing);}))];
  assignments[row.d]=ids;
  if(bakedSet.has(row.d))ids.forEach(id=>bakedIds.add(id));
  if(dynamic.has(row.d)&&ids.length)byPath[row.d]=ids;
 }
 const routeBridges=Object.fromEntries(Object.entries(routePaths).map(([key,paths])=>[key,[...new Set(paths.flatMap(d=>assignments[d]||[]))]]));
 const result={schema:'tk2-map-bridges-v1',world:[0,0,analyzed.width,analyzed.height],
  policy:'Presentation-only bridges over blue inland water along actual rendered land paths; sea lanes and terminal harbour water are excluded. Shared bridge IDs are drawn once, before castle sprites.',
  sources:{compiler_sha256:sha(read('game/build_map_bridges.cjs')),ground:{path:ground,sha256:sha(read(ground))},road_geometry_sha256:sha(read('game/config/road-centers.json')),land_path_sha256:sha(Buffer.from(appSource)),catalogs:Object.fromEntries(catalogs.map(c=>[c.path,sha(read(c.path))]))},
  style:[{stroke:'#51371e',width:5.4},{stroke:'#e9bf7a',width:2.8}],bridges,baked:[...bakedIds],by_path:byPath,
  audit:{land_strokes:all.length,baked_strokes:baked.length,dynamic_strokes:dynamic.size,water_crossings:analyzed.records.reduce((n,r)=>n+r.crossings.length,0),unique_bridges:Object.keys(bridges).length,baked_bridges:bakedIds.size,dynamic_bridge_paths:Object.keys(byPath).length,existing_bridge_marks:source.crossings.length/2,route_bridges:routeBridges,long_crossings:longCrossings.map(r=>({center:r.center,water_length:r.water_length}))}};
 fs.writeFileSync(path.resolve(ROOT,output),JSON.stringify(result,null,2)+'\n');return result;
}
module.exports={findWaterRuns,compactPoints,bridgePath,build};
if(require.main===module){const args=process.argv.slice(2),option=(flag,fallback)=>args.includes(flag)?args[args.indexOf(flag)+1]:fallback;
 build({ground:option('--ground','game/map-source/hydrology-ground.png'),output:option('--output','game/assets/map-bridges.json')}).then(result=>{const {route_bridges,...summary}=result.audit;console.log(JSON.stringify({output:option('--output','game/assets/map-bridges.json'),...summary,zangke_jiangzhou:route_bridges['bajun:zangke'],zangke_fuling:route_bridges['fuling:zangke']},null,2));}).catch(error=>{console.error(error);process.exitCode=1;});}
