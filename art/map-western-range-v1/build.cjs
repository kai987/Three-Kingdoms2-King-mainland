#!/usr/bin/env node
// Assemble imagegen artwork into the approved map; never rebuild campaign data.
// Dependencies: sharp and pngjs (available in the Codex workspace runtime).
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sharp=require('sharp'),{PNG}=require('pngjs');
const root=path.resolve(__dirname,'../..');
const read=name=>fs.readFileSync(path.join(root,name));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const decode=name=>PNG.sync.read(read(name));
const write=(name,png)=>fs.writeFileSync(path.join(root,name),PNG.sync.write(png));
const rect={x:0,y:280,width:288,height:432};
// One continuous region, including the adjoining original ridges and valleys.
const boundary=[[0,0],[185,0],[181,42],[185,82],[208,118],[180,145],
 [166,170],[176,198],[173,226],[186,251],[179,276],[174,298],
 [166,323],[135,346],[119,370],[0,390]];
function inside(x,y){let result=false;for(let i=0,j=boundary.length-1;i<boundary.length;j=i++){
 const [a,b]=boundary[i],[c,d]=boundary[j];if((b>y)!==(d>y)&&x<(c-a)*(y-b)/(d-b)+a)result=!result;
}return result;}
function edgeDistance(x,y){let distance=Infinity;for(let i=0;i<boundary.length;i++){
 const [a,b]=boundary[i],[c,d]=boundary[(i+1)%boundary.length];
 // The map's left edge is not a seam.
 if(a===0&&c===0)continue;
 const dx=c-a,dy=d-b,t=Math.max(0,Math.min(1,((x-a)*dx+(y-b)*dy)/(dx*dx+dy*dy)));
 distance=Math.min(distance,Math.hypot(x-a-t*dx,y-b-t*dy));
}return distance;}
async function build(){
 const baseline=decode('game/assets/map-road-centers.png'),ground=decode('game/map-source/hydrology-ground.png');
 if(baseline.width!==1352||baseline.height!==1024||ground.width!==baseline.width||ground.height!==baseline.height)throw Error('Unexpected map dimensions');
 const raw=await sharp(path.join(__dirname,'generated-range.png')).resize(rect.width,rect.height,{kernel:'nearest'}).ensureAlpha().raw().toBuffer();
 const protect=new Uint8Array(rect.width*rect.height);
 let protectedPixels=0;
 for(let y=0;y<rect.height;y++)for(let x=0;x<rect.width;x++){
  const p=((y+rect.y)*baseline.width+x)*4;
  const different=[0,1,2,3].some(k=>baseline.data[p+k]!==ground.data[p+k]);
  const river=ground.data[p+2]>140&&ground.data[p+2]>ground.data[p]+45&&ground.data[p+2]>ground.data[p+1]+35;
  if(different||river){
   // Keep the original raster roads, river banks and castle silhouettes exactly.
   const radius=river?2:1;
   for(let dy=-radius;dy<=radius;dy++)for(let dx=-radius;dx<=radius;dx++){
    const xx=x+dx,yy=y+dy;if(xx>=0&&yy>=0&&xx<rect.width&&yy<rect.height)protect[yy*rect.width+xx]=1;
   }
  }
 }
 const result=new PNG({width:baseline.width,height:baseline.height});baseline.data.copy(result.data);
 let changed=0;
 for(let y=0;y<rect.height;y++)for(let x=0;x<rect.width;x++){
  const n=y*rect.width+x;if(protect[n]){protectedPixels++;continue;}
  if(!inside(x+.5,y+.5))continue;
  const q=n*4;
  // Generated art is terrain only; never introduce a displaced river pixel.
  if(raw[q+2]>140&&raw[q+2]>raw[q]+45&&raw[q+2]>raw[q+1]+35)continue;
  const alpha=Math.min(1,edgeDistance(x+.5,y+.5)/10);
  const p=((y+rect.y)*baseline.width+x)*4;
  for(let k=0;k<3;k++)result.data[p+k]=Math.round(baseline.data[p+k]*(1-alpha)+raw[q+k]*alpha);
  if([0,1,2].some(k=>result.data[p+k]!==baseline.data[p+k]))changed++;
 }
 let verifiedOutside=0,verifiedProtected=0;
 for(let y=0;y<baseline.height;y++)for(let x=0;x<baseline.width;x++){
  const localX=x-rect.x,localY=y-rect.y,n=localY*rect.width+localX;
  const inRegion=localX>=0&&localX<rect.width&&localY>=0&&localY<rect.height&&inside(localX+.5,localY+.5);
  const guarded=localX>=0&&localX<rect.width&&localY>=0&&localY<rect.height&&protect[n];
  if(!inRegion||guarded){
   const p=(y*baseline.width+x)*4;
   if([0,1,2,3].some(k=>baseline.data[p+k]!==result.data[p+k]))throw Error('Protected/outside map pixel changed');
   if(!inRegion)verifiedOutside++;if(guarded)verifiedProtected++;
  }
 }
 write('game/assets/map-western-range.png',result);
 const before=new PNG({width:rect.width,height:rect.height}),after=new PNG({width:rect.width,height:rect.height});
 for(let y=0;y<rect.height;y++){
  baseline.data.copy(before.data,y*rect.width*4,((y+rect.y)*baseline.width)*4,((y+rect.y)*baseline.width+rect.width)*4);
  result.data.copy(after.data,y*rect.width*4,((y+rect.y)*baseline.width)*4,((y+rect.y)*baseline.width+rect.width)*4);
 }
 write('art/map-western-range-v1/before.png',before);write('art/map-western-range-v1/after.png',after);
 const audit={schema:'tk2-western-range-art-v1',region:rect,boundary,changed_pixels:changed,protected_pixels:protectedPixels,
  verification:{outside_pixels_identical:verifiedOutside,protected_pixels_identical:verifiedProtected},
  baseline:{path:'game/assets/map-road-centers.png',sha256:sha(read('game/assets/map-road-centers.png'))},
  ground:{path:'game/map-source/hydrology-ground.png',sha256:sha(read('game/map-source/hydrology-ground.png'))},
  generated:{path:'art/map-western-range-v1/generated-range.png',sha256:sha(read('art/map-western-range-v1/generated-range.png'))},
  output:{path:'game/assets/map-western-range.png',sha256:sha(read('game/assets/map-western-range.png'))},
  rule:'One continuous mountain region; original raster roads, rivers and castle pixels protected. Outside region pixels identical.'};
 fs.writeFileSync(path.join(__dirname,'manifest.json'),JSON.stringify(audit,null,2)+'\n');
 console.log(JSON.stringify(audit,null,2));
}
build().catch(error=>{console.error(error);process.exitCode=1;});
