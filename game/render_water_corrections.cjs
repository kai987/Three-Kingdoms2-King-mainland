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
 for(const[p,hash]of Object.entries(config.sources))if(sha(read(p))!==hash)throw Error('Water source changed: '+p);
 const browser=await chromium.launch({channel:'chrome',headless:true});
 let result;
 try{
  const page=await browser.newPage();
  result=await page.evaluate(async({config,groundUrl,terrainUrl,waterSvg,shadowSvg})=>{
   const[W,H]=config.size,N=W*H;
   const canvas=()=>Object.assign(document.createElement('canvas'),{width:W,height:H});
   async function pixels(url){const i=new Image();i.src=url;await i.decode();if(i.width!==W||i.height!==H)throw Error('Water source dimensions');const c=canvas(),ctx=c.getContext('2d');ctx.drawImage(i,0,0);return ctx.getImageData(0,0,W,H).data;}
   const original=await pixels(groundUrl),terrain=await pixels(terrainUrl),output=new Uint8ClampedArray(original);
   const doc=new DOMParser().parseFromString(waterSvg,'image/svg+xml');
   const svgUrl=svg=>'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(new XMLSerializer().serializeToString(svg));
   async function mask(select){const copy=doc.documentElement.cloneNode(true);for(const g of copy.querySelectorAll('[data-river],[data-lake]'))if(!select(g))g.remove();return pixels(svgUrl(copy));}
   const oldWei=await mask(g=>g.dataset.river==='wei'),otherWater=await mask(g=>g.dataset.river!=='wei');
   const affected=new Uint8Array(N),stats={oldWeiPixelsRestored:0,newWeiPixels:0,clippedMouthPixels:{},seaShadowMaskPixels:0};
   function restore(i){const k=i*4;output.set(terrain.subarray(k,k+4),k);}
   for(let y=0;y<H;y++)for(let x=config.wei.replace_from_x;x<W;x++){const i=y*W+x;if(oldWei[i*4+3]&&!otherWater[i*4+3]){restore(i);stats.oldWeiPixelsRestored++;}}
   // Use the same 2px cells and narrow, single blue stroke as the source map.
   const cells=new Set(),step=config.wei.pixel,radius=config.wei.width/2;
   for(let n=1;n<config.wei.points.length;n++){
    const a=config.wei.points[n-1],b=config.wei.points[n],count=Math.ceil(Math.hypot(b[0]-a[0],b[1]-a[1])*2);
    for(let j=0;j<=count;j++){
     const px=a[0]+(b[0]-a[0])*j/count,py=a[1]+(b[1]-a[1])*j/count;
     for(let y=Math.floor((py-radius)/step)*step;y<=py+radius;y+=step)for(let x=Math.floor((px-radius)/step)*step;x<=px+radius;x+=step)
      if(Math.hypot(x+step/2-px,y+step/2-py)<=radius)cells.add(x+','+y);
    }
   }
   const color=config.wei.color.match(/[a-f0-9]{2}/gi).map(v=>parseInt(v,16));
   for(const cell of cells){const[x,y]=cell.split(',').map(Number);for(let dy=0;dy<step;dy++)for(let dx=0;dx<step;dx++){const i=(y+dy)*W+x+dx;output.set([...color,255],i*4);stats.newWeiPixels++;}}
   for(const mouth of config.mouths){
    const river=await mask(g=>g.dataset.river===mouth.river);let count=0;
    for(let y=0;y<H;y++)for(let x=0;x<W;x++)if(river[(y*W+x)*4+3]&&(x+.5-mouth.shore[0])*mouth.outward[0]+(y+.5-mouth.shore[1])*mouth.outward[1]>0){restore(y*W+x);count++;}
    stats.clippedMouthPixels[mouth.river]=count;
   }
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
  },{config,groundUrl:'data:image/png;base64,'+read('game/map-source/road-ground.png').toString('base64'),terrainUrl:'data:image/png;base64,'+read('game/map-source/terrain-under-water.png').toString('base64'),waterSvg:read('game/map-source/historic-water.svg').toString(),shadowSvg:read('game/map-source/sea-shadow.svg').toString()});
 }finally{await browser.close();}
 const output='game/map-source/hydrology-ground.png',bytes=Buffer.from(result.png,'base64');fs.writeFileSync(path.join(root,output),bytes);
 const manifest={schema:'tk2-water-render-v1',config_sha256:sha(read(configPath)),sources:config.sources,output:{path:output,sha256:sha(bytes)},mask_runs:result.runs,stats:result.stats};
 fs.writeFileSync(path.join(root,'game/map-source/water-render.json'),JSON.stringify(manifest,null,2)+'\n');
 console.log(JSON.stringify({output,sha256:manifest.output.sha256,...result.stats},null,2));
}
main().catch(e=>{console.error(e);process.exitCode=1;});
