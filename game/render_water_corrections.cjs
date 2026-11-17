#!/usr/bin/env node
'use strict';
// Local pixel/SVG compilation. Original terrain and scene layers stay intact.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),read=p=>fs.readFileSync(path.join(root,p));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
async function main(){
 const configPath='game/config/water-corrections.json',config=JSON.parse(read(configPath));
 if(config.schema!=='tk2-water-corrections-v1')throw Error('Unknown water correction source');
 const coast=config.northeast_coast;
 if(coast&&!Object.hasOwn(config.sources,coast.path))throw Error('Northeast coast patch lacks a source hash');
 for(const[p,hash]of Object.entries(config.sources))if(sha(read(p))!==hash)throw Error('Water source changed: '+p);
 const browser=await chromium.launch({channel:'chrome',headless:true});
 let result;
 try{
  const page=await browser.newPage();
  result=await page.evaluate(async({config,groundUrl,terrainUrl,coastUrl,waterSvg,shadowSvg})=>{
   const[W,H]=config.size,N=W*H;
   const canvas=()=>Object.assign(document.createElement('canvas'),{width:W,height:H});
   async function pixels(url){const i=new Image();i.src=url;await i.decode();if(i.width!==W||i.height!==H)throw Error('Water source dimensions');const c=canvas(),ctx=c.getContext('2d');ctx.drawImage(i,0,0);return ctx.getImageData(0,0,W,H).data;}
   const original=await pixels(groundUrl),terrain=await pixels(terrainUrl),output=new Uint8ClampedArray(original);
   const doc=new DOMParser().parseFromString(waterSvg,'image/svg+xml');
   const svgUrl=svg=>'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(svg));
   async function mask(select){const copy=doc.documentElement.cloneNode(true);for(const g of copy.querySelectorAll('[data-river],[data-lake]'))if(!select(g))g.remove();return pixels(svgUrl(copy));}
   const oldWei=await mask(g=>g.dataset.river==='wei'),otherWater=await mask(g=>g.dataset.river!=='wei');
   const affected=new Uint8Array(N),stats={oldWeiPixelsRestored:0,newWeiPixels:0,addedRiverPixels:0,regionalRiverPixels:{},clippedMouthPixels:{},seaShadowMaskPixels:0};
   function restore(i){const k=i*4;output.set(terrain.subarray(k,k+4),k);}
   const {wei}=config;
   const upper=wei.headwaters;
   if(upper&&(!upper.points.at(-1)?.every((v,i)=>v===upper.join[i])||
      !oldWei[(upper.join[1]*W+upper.join[0])*4+3]))throw Error('Wei headwaters must join the retained river');
   for(let y=0;y<H;y++)for(let x=0;x<W;x++){
    if(x<wei.replace_from_x&&(!upper||x>=upper.join[0]))continue;
    const i=y*W+x;
    if(oldWei[i*4+3]&&!otherWater[i*4+3]){restore(i);stats.oldWeiPixelsRestored++;}
   }
   // Use the same 2px cells and narrow, single blue stroke as the source map.
   function paintRiver(points,width,color,pixel=2){
    if(points.length<2||!points.every(p=>p.length===2&&p.every(Number.isFinite)&&0<=p[0]&&p[0]<W&&0<=p[1]&&p[1]<H))
     throw Error('River line is outside the native map');
    const cells=new Set(),radius=width/2;
    for(let n=1;n<points.length;n++){
     const a=points[n-1],b=points[n],count=Math.max(1,Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])*2));
     for(let j=0;j<=count;j++){
      const px=a[0]+(b[0]-a[0])*j/count,py=a[1]+(b[1]-a[1])*j/count;
      for(let y=Math.max(0,Math.floor((py-radius)/pixel)*pixel);y<=py+radius&&y<H;y+=pixel)
       for(let x=Math.max(0,Math.floor((px-radius)/pixel)*pixel);x<=px+radius&&x<W;x+=pixel)
        if(Math.hypot(x+pixel/2-px,y+pixel/2-py)<=radius)cells.add(y*W+x);
     }
    }
    const rgba=[...color.match(/[a-f0-9]{2}/gi).map(v=>parseInt(v,16)),255];
    for(const cell of cells)for(let dy=0;dy<pixel;dy++)for(let dx=0;dx<pixel;dx++)
     output.set(rgba,(cell+dy*W+dx)*4);
    return cells.size*pixel*pixel;
   }
   if(upper)stats.newWeiHeadwaterPixels=paintRiver(upper.points,wei.width,'#002af8',wei.pixel);
   // Surveyed additions use the very same narrow, single-blue 2px cells.
   // Paint these explicit source groups; the historical SVG otherwise only
   // serves as a restoration mask because its rivers are baked in baseline.
   const additions=await mask(g=>g.hasAttribute('data-authorial-addition'));
   for(let i=0;i<N;i++)if(additions[i*4+3]){output.set(additions.subarray(i*4,i*4+4),i*4);stats.addedRiverPixels++;}
   for(const mouth of config.mouths){
    const river=await mask(g=>g.dataset.river===mouth.river);let count=0;
    for(let y=0;y<H;y++)for(let x=0;x<W;x++)if(river[(y*W+x)*4+3]&&(x+.5-mouth.shore[0])*mouth.outward[0]+(y+.5-mouth.shore[1])*mouth.outward[1]>0){restore(y*W+x);count++;}
    stats.clippedMouthPixels[mouth.river]=count;
   }
   if(coastUrl){
    const {x,y,width,height}=config.northeast_coast.crop;
    const image=new Image();image.src=coastUrl;await image.decode();
    if(image.width!==width||image.height!==height||x<0||y<0||x+width>W||y+height>H)
     throw Error('Northeast coast patch is outside the native map');
    const patch=canvas().getContext('2d');patch.drawImage(image,x,y);
    const rgba=patch.getImageData(x,y,width,height).data;
    stats.northeastCoastPixels=0;
    for(let row=0;row<height;row++)for(let col=0;col<width;col++){
     const source=(row*width+col)*4;
     if(!rgba[source+3])continue;
     if(rgba[source+3]!==255)throw Error('Northeast coast patch must have hard opacity');
     const target=(y+row)*W+x+col;
     output.set(rgba.subarray(source,source+4),target*4);
     affected[target]=1;stats.northeastCoastPixels++;
    }
   }
   for(const river of config.regional_rivers||[]){
    stats.regionalRiverPixels[river.id]=paintRiver(river.points,river.width,'#002af8');
   }
   stats.newWeiPixels=paintRiver(wei.points,wei.width,wei.color,wei.pixel);
   // The old sea route shadow is baked into the baseline. Its widened mask
   // restores the clean ground, including antialiased dark-blue edge pixels.
   const shadow=new DOMParser().parseFromString(shadowSvg,'image/svg+xml').documentElement;
   for(const p of shadow.querySelectorAll('path')){p.setAttribute('stroke','#fff');p.setAttribute('stroke-width','6');p.setAttribute('opacity','1');}
   const shadowMask=await pixels(svgUrl(shadow));
   for(let i=0;i<N;i++){
    const k=i*4;
    if(shadowMask[k+3]){affected[i]=1;stats.seaShadowMaskPixels++;}
    if(output[k]!==original[k]||output[k+1]!==original[k+1]||output[k+2]!==original[k+2])affected[i]=1;
   }
   const runs=[];
   for(let y=0;y<H;y++)for(let x=0;x<W;x++)if(affected[y*W+x]){const start=x;while(x+1<W&&affected[y*W+x+1])x++;runs.push([y,start,x-start+1]);}
   const c=canvas();c.getContext('2d').putImageData(new ImageData(output,W,H),0,0);
   return {png:c.toDataURL('image/png').split(',')[1],runs,stats};
  },{config,groundUrl:'data:image/png;base64,'+read('game/map-source/road-ground.png').toString('base64'),terrainUrl:'data:image/png;base64,'+read('game/map-source/terrain-under-water.png').toString('base64'),coastUrl:coast?'data:image/png;base64,'+read(coast.path).toString('base64'):null,waterSvg:read('game/map-source/historic-water.svg').toString(),shadowSvg:read('game/map-source/sea-shadow.svg').toString()});
 }finally{await browser.close();}
 const output='game/map-source/hydrology-ground.png',bytes=Buffer.from(result.png,'base64');fs.writeFileSync(path.join(root,output),bytes);
 const manifest={schema:'tk2-water-render-v1',config_sha256:sha(read(configPath)),sources:config.sources,output:{path:output,sha256:sha(bytes)},mask_runs:result.runs,stats:result.stats};
 fs.writeFileSync(path.join(root,'game/map-source/water-render.json'),JSON.stringify(manifest,null,2)+'\n');
 console.log(JSON.stringify({output,sha256:manifest.output.sha256,...result.stats},null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
