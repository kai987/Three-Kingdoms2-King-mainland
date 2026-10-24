// Keep ship lanes on the existing sea and solid access roads on the existing
// land. This edits vector geometry only; it never changes terrain pixels.
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('playwright'),root=path.resolve(__dirname,'..');
(async()=>{const b=await chromium.launch({channel:'chrome',headless:true});try{
 const corridors=JSON.parse(fs.readFileSync(path.join(__dirname,'config/route-corridors.json')));assert.equal(corridors.schema,'tk2-route-corridors-v1');
 const riverNetwork=JSON.parse(require('node:child_process').execFileSync('python3',['-B',path.join(__dirname,'river_network.py')],{cwd:root,encoding:'utf8',maxBuffer:8*1024*1024}));
 assert.equal(corridors.river_network_source,'game/config/river-network.json');
 corridors.river_routes=[...(corridors.river_routes||[]),...riverNetwork.routes];
 const page=await b.newPage(),file=path.join(__dirname,'config/navigation-geometry.json'),catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'data/campaigns/249-01.json'))),positions=Object.fromEntries(catalog.cities.map(c=>[c.id,c.position]));
 const result=await page.evaluate(async({png,positions,corridors})=>{
  const image=new Image();image.src=png;await image.decode();const c=document.createElement('canvas');c.width=image.width;c.height=image.height;const ctx=c.getContext('2d');ctx.drawImage(image,0,0);const pixels=ctx.getImageData(0,0,c.width,c.height).data;
  const step=4,W=Math.floor(c.width/step),H=Math.floor(c.height/step),N=W*H;
  const blue=(x,y)=>{if(x<0||y<0||x>=c.width||y>=c.height)return false;const i=(y*c.width+x)*4;return pixels[i+2]>140&&pixels[i+2]>pixels[i]*1.4&&pixels[i+2]>pixels[i+1]*1.3};
  const candidates=new Uint8Array(N),sea=new Uint8Array(N);
  for(let y=0;y<H;y++)for(let x=0;x<W;x++){let water=0,total=0;for(let dy=-6;dy<=6;dy+=2)for(let dx=-6;dx<=6;dx+=2){total++;if(blue(x*step+dx,y*step+dy))water++;}if(water/total>=.72)candidates[y*W+x]=1;
   // The authored Qiongzhou strait is narrower than the river-exclusion
   // clearance. Admit its actual blue pixels, without opening inland rivers.
   const px=x*step,py=y*step;if(px>=550&&px<=660&&py>=850&&py<=910&&blue(px,py)){let local=0;for(let dy=-2;dy<=2;dy+=2)for(let dx=-2;dx<=2;dx+=2)if(blue(px+dx,py+dy))local++;if(local>=5)candidates[y*W+x]=1;}
  }
  const flood=[(H-3)*W+W-3];sea[flood[0]]=1;
  for(let n=0;n<flood.length;n++){const i=flood[n],x=i%W,y=Math.floor(i/W);for(const[dx,dy]of [[1,0],[-1,0],[0,1],[0,-1]]){const xx=x+dx,yy=y+dy,j=yy*W+xx;if(xx>=0&&yy>=0&&xx<W&&yy<H&&candidates[j]&&!sea[j]){sea[j]=1;flood.push(j);}}}
  const point=i=>[(i%W)*step,Math.floor(i/W)*step],index=p=>Math.round(p[1]/step)*W+Math.round(p[0]/step);
  const nearest=p=>{let best=-1,distance=Infinity;for(const i of flood){const q=point(i),d=(q[0]-p[0])**2+(q[1]-p[1])**2;if(d<distance){best=i;distance=d;}}return best};
  function route(start,goal,water){
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
     if(!water&&Math.hypot(q[0]-begin[0],q[1]-begin[1])>24){const k=(q[1]*c.width+q[0])*4,r=pixels[k],g=pixels[k+1],b=pixels[k+2];if((r<50&&g<70&&b<70)||(r>180&&g<130))cost*=10;else if(blue(q[0],q[1])&&!nearEnd)cost*=4;}
     const next=dist[i]+cost;if(next+.001<dist[j]){dist[j]=next;prev[j]=i;push([next+heuristic(j),j]);}
    }
   }throw Error('No '+(water?'sea':'land')+' approach');
  }
  function simplify(points){return points.filter((p,i,a)=>!i||i===a.length-1||(p[0]-a[i-1][0])*(a[i+1][1]-p[1])!==(p[1]-a[i-1][1])*(a[i+1][0]-p[0]));}
  const coastalIds=['liaodong','liaoxi','bohai','donghai','beihai','lelang','daifang','wujun','kuaiji','linhai','nanhai','gaoliang','hepu','jiaozhi','jiuzhen','rinan','zhuya','yizhou'];
  const priorPorts={wujun:[1174,426],liaodong:[1186,134],beihai:[1084,176],lelang:[1264,204],daifang:[1268,236],kuaiji:[1186,534],yizhou:[1120,690],hepu:[542,836],zhuya:[550,868],jiaozhi:[452,874],rinan:[434,994],nanhai:[774,802],gaoliang:[700,838]};
  const ports={},access={},routes=[];
  for(const id of coastalIds){
   ports[id]=nearest(priorPorts[id]||positions[id]);
   const points=corridors.access_overrides[id]?corridors.access_overrides[id].map(p=>[...p]):route(index(positions[id]),ports[id],false);
   points[0]=positions[id];const port=point(ports[id]);if(points.at(-1).some((v,i)=>v!==port[i]))points.push(port);
   access[id]=simplify(points);
  }
  const land_roads=corridors.land_connections.map(row=>{
   const junction=index(row.junction),from=route(index(positions[row.from]),junction,false),to=route(junction,index(positions[row.to]),false);
   from[0]=positions[row.from];to[to.length-1]=positions[row.to];
   return {...row,draw:[{mode:'land',points:simplify(from)},{mode:'land',points:simplify(to)}]};
  });
  for(let a=0;a<coastalIds.length;a++)for(let b=a+1;b<coastalIds.length;b++){
   const from=coastalIds[a],to=coastalIds[b],points=route(ports[from],ports[to],true);
   routes.push({from,to,draw:[{mode:'land',points:access[from]},{mode:'sea',points:simplify(points)},{mode:'land',points:[...access[to]].reverse()}]});
  }
  return {schema:'sea-mask-navigation-geometry-v1',coastal_cities:coastalIds,land_roads,river_routes:corridors.river_routes||[],river_rules:corridors.river_rules||{},ports:Object.fromEntries(Object.entries(ports).map(([id,i])=>[id,point(i)])),routes,
   method:'4px ocean-connected sea mask and A-star; smooth display follows sea cells. Approximate game ports, not identified historical harbours. Distances use separate geographic marine waypoints, never art pixels.'};
 },{png:'data:image/png;base64,'+fs.readFileSync(path.join(__dirname,'assets/map-navigation.png')).toString('base64'),positions,corridors});
 result.river_network={schema:riverNetwork.schema,source_sha256:riverNetwork.source_sha256,reach_count:riverNetwork.reach_count};
 fs.writeFileSync(file,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({routes:result.routes.length,coastal_cities:result.coastal_cities.length,river_routes:result.river_routes.length,shared_river_reaches:riverNetwork.reach_count}));
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1});
