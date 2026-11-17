// Keep ship lanes on the existing sea and solid access roads on the existing
// land. This edits vector geometry only; it never changes terrain pixels.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('node:crypto');
const {chromium}=require('playwright'),root=path.resolve(__dirname,'..');
const read=file=>fs.readFileSync(path.join(root,file));
const uri=png=>'data:image/png;base64,'+png.toString('base64');
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});try{
 const corridors=JSON.parse(fs.readFileSync(path.join(__dirname,'config/route-corridors.json')));assert.equal(corridors.schema,'tk2-route-corridors-v1');
 const riverNetwork=JSON.parse(require('node:child_process').execFileSync('python3',['-B',path.join(__dirname,'river_network.py')],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024}));
 assert.equal(corridors.river_network_source,'game/config/river-network.json');
 corridors.river_routes=[...(corridors.river_routes||[]),...riverNetwork.routes];
 const page=await b.newPage(),file=path.join(__dirname,'config/navigation-geometry.json');
 const shared=JSON.parse(fs.readFileSync(path.join(__dirname,'config/campaigns/shared.json'))).catalog;
 const expansion=JSON.parse(fs.readFileSync(path.join(__dirname,'config/campaigns/city-expansion-map.json'))).cities;
 const positions=Object.fromEntries([...shared.cities.map(c=>[c.id,c.position]),...Object.entries(expansion).map(([id,c])=>[id,c.position])]);
 const revision=corridors.coastal_revision;
 const terrainSource='game/config/terrain-art.json';
 const luzonOutline=JSON.parse(read(terrainSource)).luzon.outline;
 const ground='game/map-source/hydrology-ground.png';
 const coast=revision?read(ground):null;
 const coastSha=coast&&crypto.createHash('sha256').update(coast).digest('hex');
 if(revision){
  const receipt=JSON.parse(read('game/map-source/water-render.json'));
  assert.equal(receipt.schema,'tk2-water-render-v1');
  assert.equal(receipt.output.path,ground);
  assert.equal(receipt.output.sha256,coastSha,'Rebuild the coastline hydrology before navigation geometry');
 }
 const result=await page.evaluate(async({png,coast,positions,corridors,luzonOutline})=>{
  async function imageData(url){
   const image=new Image();
   image.src=url;
   await image.decode();
   const canvas=Object.assign(document.createElement('canvas'),{width:image.width,height:image.height});
   const ctx=canvas.getContext('2d');
   ctx.drawImage(image,0,0);
   return ctx.getImageData(0,0,canvas.width,canvas.height);
  }
  const source=await imageData(png),{width,height}=source;
  const step=4,W=Math.floor(width/step),H=Math.floor(height/step),N=W*H;
  function ocean(pixels){
   const blue=(x,y)=>{if(x<0||y<0||x>=width||y>=height)return false;const i=(y*width+x)*4;return pixels[i+2]>140&&pixels[i+2]>pixels[i]*1.4&&pixels[i+2]>pixels[i+1]*1.3};
   const candidates=new Uint8Array(N),sea=new Uint8Array(N);
   for(let y=0;y<H;y++)for(let x=0;x<W;x++){let water=0,total=0;for(let dy=-6;dy<=6;dy+=2)for(let dx=-6;dx<=6;dx+=2){total++;if(blue(x*step+dx,y*step+dy))water++;}if(water/total>=.72)candidates[y*W+x]=1;
    // The authored Qiongzhou strait is narrower than the river-exclusion
    // clearance. Admit its actual blue pixels, without opening inland rivers.
    const px=x*step,py=y*step;if(px>=550&&px<=660&&py>=850&&py<=910&&blue(px,py)){let local=0;for(let dy=-2;dy<=2;dy+=2)for(let dx=-2;dx<=2;dx+=2)if(blue(px+dx,py+dy))local++;if(local>=5)candidates[y*W+x]=1;}
   }
   const flood=[(H-3)*W+W-3];sea[flood[0]]=1;
   for(let n=0;n<flood.length;n++){const i=flood[n],x=i%W,y=Math.floor(i/W);for(const[dx,dy]of [[1,0],[-1,0],[0,1],[0,-1]]){const xx=x+dx,yy=y+dy,j=yy*W+xx;if(xx>=0&&yy>=0&&xx<W&&yy<H&&candidates[j]&&!sea[j]){sea[j]=1;flood.push(j);}}}
   return {pixels,blue,sea,flood};
  }
  const original=ocean(source.data);
  let revised=original;
  const revision=corridors.coastal_revision;
  if(revision){
   const ground=await imageData(coast);
   const [left,top,right,bottom]=revision.region;
   if(ground.width!==width||ground.height!==height||
      !revision.region.every(Number.isInteger)||
      !(0<=left&&left<right&&right<=width&&0<=top&&top<bottom&&bottom<=height)){
    throw Error('Invalid revised coastline dimensions');
   }
   const pixels=source.data.slice();
   for(let y=top;y<bottom;y++){
    const start=(y*width+left)*4,end=(y*width+right)*4;
    pixels.set(ground.data.subarray(start,end),start);
   }
   // Luzon is drawn after route compilation in the display asset. Rasterize
   // its same geographic polygon here to keep water paths out of the island.
   const canvas=Object.assign(document.createElement('canvas'),{width,height});
   const ctx=canvas.getContext('2d');
   ctx.putImageData(new ImageData(pixels,width,height),0,0);
   ctx.beginPath();
   ctx.moveTo(...luzonOutline[0]);
   for(const p of luzonOutline.slice(1))ctx.lineTo(...p);
   ctx.closePath();
   ctx.fillStyle='#28d82c';
   ctx.fill();
   revised=ocean(ctx.getImageData(0,0,width,height).data);
  }
  const point=i=>[(i%W)*step,Math.floor(i/W)*step],index=p=>Math.round(p[1]/step)*W+Math.round(p[0]/step);
  function nearest(grid,target,requireWaterPixel=false){
   let best=-1,distance=Infinity;
   for(const i of grid.flood){
    const [x,y]=point(i);
    if(requireWaterPixel&&!grid.blue(x,y))continue;
    const d=(x-target[0])**2+(y-target[1])**2;
    if(d<distance){best=i;distance=d;}
   }
   return best;
  }
  function route({pixels,blue,sea},start,goal,water){
   const dist=new Float64Array(N).fill(Infinity),prev=new Int32Array(N).fill(-1),heap=[];
   const push=(v)=>{heap.push(v);let i=heap.length-1;while(i){const p=(i-1)>>1;if(heap[p][0]<=v[0])break;heap[i]=heap[p];i=p;}heap[i]=v};
   const pop=()=>{const first=heap[0],last=heap.pop();if(heap.length){let i=0;while(i*2+1<heap.length){let j=i*2+1;if(j+1<heap.length&&heap[j+1][0]<heap[j][0])j++;if(last[0]<=heap[j][0])break;heap[i]=heap[j];i=j;}heap[i]=last;}return first};
   const end=point(goal),begin=point(start),heuristic=i=>{const p=point(i);return Math.hypot(p[0]-end[0],p[1]-end[1])/step};
   dist[start]=0;push([heuristic(start),start]);
   while(heap.length){const[priority,i]=pop();if(priority>dist[i]+heuristic(i)+.001)continue;if(i===goal){const out=[];for(let n=i;n!==-1;n=prev[n])out.push(point(n));return out.reverse();}const x=i%W,y=Math.floor(i/W);
    for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){if(!dx&&!dy)continue;const xx=x+dx,yy=y+dy,j=yy*W+xx;if(xx<0||yy<0||xx>=W||yy>=H)continue;const q=point(j),nearEnd=Math.hypot(q[0]-end[0],q[1]-end[1])<=12;
     if(water?!sea[j]:sea[j]&&!nearEnd)continue;
     if(water&&dx&&dy&&(!sea[y*W+xx]||!sea[yy*W+x]))continue;
     let cost=Math.hypot(dx,dy);
     if(!water&&Math.hypot(q[0]-begin[0],q[1]-begin[1])>24){const k=(q[1]*width+q[0])*4,r=pixels[k],g=pixels[k+1],b=pixels[k+2];if((r<50&&g<70&&b<70)||(r>180&&g<130))cost*=10;else if(blue(q[0],q[1])&&!nearEnd)cost*=4;}
     const next=dist[i]+cost;if(next+.001<dist[j]){dist[j]=next;prev[j]=i;push([next+heuristic(j),j]);}
    }
   }throw Error('No '+(water?'sea':'land')+' approach');
  }
  function simplify(points){return points.filter((p,i,a)=>!i||i===a.length-1||(p[0]-a[i-1][0])*(a[i+1][1]-p[1])!==(p[1]-a[i-1][1])*(a[i+1][0]-p[0]));}
  const regularPorts=['liaodong','liaoxi','bohai','donghai','beihai','lelang','daifang','wujun','kuaiji','linhai','nanhai','gaoliang','hepu','jiaozhi','jiuzhen','rinan','zhuya','yizhou'];
  const limitedPorts=corridors.limited_port_connections??{};
  const coastalIds=[...regularPorts,...Object.keys(limitedPorts)];
  const seaConnections=regularPorts.flatMap((from,i)=>regularPorts.slice(i+1).map(to=>[from,to]));
  for(const [to,origins] of Object.entries(limitedPorts)){
   if(!positions[to]||regularPorts.includes(to)||!Array.isArray(origins)||!origins.length||
      new Set(origins).size!==origins.length||origins.some(from=>!regularPorts.includes(from))){
    throw Error('Invalid connections for limited port: '+to);
   }
   seaConnections.push(...origins.map(from=>[from,to]));
  }
  const priorPorts={wujun:[1174,426],liaodong:[1186,134],beihai:[1084,176],lelang:[1264,204],daifang:[1268,236],kuaiji:[1186,534],yizhou:[1120,690],hepu:[542,836],zhuya:[550,868],jiaozhi:[452,874],rinan:[434,994],nanhai:[774,802],gaoliang:[700,838]};
  const portHints=revision?.ports??{};
  const shoreApproaches=corridors.shore_access_overrides??{};
  const ports={},access={},routes=[],revisedPorts=new Set();
  for(const [id,port] of Object.entries(portHints)){
   if(!coastalIds.includes(id)||port.length!==2||!port.every(Number.isInteger)||
      !(0<=port[0]&&port[0]<width&&0<=port[1]&&port[1]<height)){
    throw Error('Invalid revised port position: '+id);
   }
  }
  for(const [id,points] of Object.entries(shoreApproaches)){
   if(!coastalIds.includes(id)||!Array.isArray(points)||points.length<2||
      points.some(p=>!Array.isArray(p)||p.length!==2||!p.every(Number.isInteger)||
        !(0<=p[0]&&p[0]<width&&0<=p[1]&&p[1]<height))||
      points[0].some((v,i)=>v!==positions[id][i])||revised.blue(...points.at(-1))){
    throw Error('Shore approach must join the city to dry ground: '+id);
   }
  }
  for(const id of coastalIds){
   const hint=priorPorts[id]||positions[id];
   const previous=nearest(original,hint);
   const useRevision=Object.hasOwn(portHints,id)||!revised.sea[previous];
   const grid=useRevision?revised:original;
   if(useRevision)revisedPorts.add(id);
   ports[id]=useRevision?nearest(grid,portHints[id]||hint,true):previous;
   if(shoreApproaches[id]){
    access[id]=simplify(shoreApproaches[id]);
    continue;
   }
   const points=corridors.access_overrides[id]?corridors.access_overrides[id].map(p=>[...p]):route(grid,index(positions[id]),ports[id],false);
   points[0]=positions[id];const port=point(ports[id]);if(points.at(-1).some((v,i)=>v!==port[i]))points.push(port);
   access[id]=simplify(points);
  }
  const land_roads=corridors.land_connections.map(({points,sections,...row})=>{
   if(points||sections){
    const matches=(a,b)=>a?.length===2&&b?.length===2&&a.every((v,i)=>v===b[i]);
    const parts=sections??[points];
    if((points&&sections)||!Array.isArray(parts)||!parts.length||
       parts.some((part,i)=>!Array.isArray(part)||part.length<2||
        part.some(p=>!Array.isArray(p)||p.length!==2||!p.every(Number.isFinite))||
        (i>0&&!matches(parts[i-1].at(-1),part[0])))||
       !matches(parts[0][0],positions[row.from])||!matches(parts.at(-1).at(-1),positions[row.to]))
     throw Error('Reviewed land corridor must join the city centers continuously: '+row.from+':'+row.to);
    return {...row,draw:parts.map(points=>({mode:'land',points}))};
   }
   const junction=index(row.junction),from=route(original,index(positions[row.from]),junction,false),to=route(original,junction,index(positions[row.to]),false);
   from[0]=positions[row.from];to[to.length-1]=positions[row.to];
   return {...row,draw:[{mode:'land',points:simplify(from)},{mode:'land',points:simplify(to)}]};
  });
  for(const [from,to] of seaConnections){
   const start=ports[from],end=ports[to];
   let points=route(revisedPorts.has(from)||revisedPorts.has(to)?revised:original,start,end,true);
   if(points.some(p=>!revised.sea[index(p)]))points=route(revised,start,end,true);
   const sea=simplify(points);
   // Begin the dashed leg at the shoreline while retaining the offshore grid node.
   if(shoreApproaches[from])sea.unshift(access[from].at(-1));
   if(shoreApproaches[to])sea.push(access[to].at(-1));
   routes.push({from,to,draw:[{mode:'land',points:access[from]},{mode:'sea',points:sea},{mode:'land',points:[...access[to]].reverse()}]});
  }
  return {schema:'sea-mask-navigation-geometry-v1',coastal_cities:coastalIds,land_roads,river_routes:corridors.river_routes||[],river_rules:corridors.river_rules||{},ports:Object.fromEntries(Object.entries(ports).map(([id,i])=>[id,point(i)])),routes,
   method:'4px ocean-connected sea mask and A-star; smooth display follows sea cells. Approximate game ports, not identified historical harbours. Distances use separate geographic marine waypoints, never art pixels.'};
 },{png:uri(read('game/assets/map-navigation.png')),coast:coast&&uri(coast),positions,corridors,luzonOutline});
 if(revision)result.coastal_revision={region:revision.region,source:ground,source_sha256:coastSha};
 result.island_coastline={city:'luzon',source:terrainSource,outline_sha256:crypto.createHash('sha256').update(JSON.stringify(luzonOutline)).digest('hex')};
 result.river_network={schema:riverNetwork.schema,source_sha256:riverNetwork.source_sha256,reach_count:riverNetwork.reach_count};
 fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({routes:result.routes.length,coastal_cities:result.coastal_cities.length,river_routes:result.river_routes.length,shared_river_reaches:riverNetwork.reach_count}));
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1});
