#!/usr/bin/env node
'use strict';
// Restore the two original pure-white source cells at the crown's inner tips.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const assert=require('node:assert/strict'),{chromium}=require('playwright');
const dir=__dirname,root=path.resolve(dir,'../../../..');
const files={baseline:path.join(dir,'../zhuge-liang-preserved-v7/portrait-128x160.png'),study:path.join(dir,'generation-source.png'),original:path.join(root,'game/assets/portraits/original/109.png'),identity:path.join(root,'game/config/portrait-identity-map.json')};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),uri=b=>'data:image/png;base64,'+b.toString('base64');
const input=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,fs.readFileSync(file)]));
const hashes=Object.fromEntries(Object.entries(input).map(([key,bytes])=>[key,sha(bytes)]));
assert.equal(hashes.baseline,'2cc91c781fe4c9aa25ec10de89ca0eb204744a163da90ed12db8cfd1c6da7183');
assert.equal(hashes.original,'00ab7c41fc86e84deeede6f42ddf5510b928f7e9ede998ba853836936eb7306c');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await browser.newPage({viewport:{width:980,height:660},deviceScaleFactor:1});
 await page.setContent('<!doctype html><body></body>');
 const packed=await page.evaluate(async sources=>{
  const w=128,h=160;
  async function read(url){const i=new Image();i.src=url;await i.decode();const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d',{willReadFrequently:true});g.imageSmoothingEnabled=false;g.drawImage(i,0,0,w,h);return g.getImageData(0,0,w,h).data;}
  const base=await read(sources.baseline),original=await read(sources.original),out=new Uint8ClampedArray(base);
  const rois=[{x:32,y:8,width:4,height:4},{x:92,y:8,width:4,height:4}];
  const inside=(x,y)=>rois.some(r=>x>=r.x&&x<r.x+r.width&&y>=r.y&&y<r.y+r.height);
  for(const r of rois)for(let y=r.y;y<r.y+r.height;y++)for(let x=r.x;x<r.x+r.width;x++){
   const at=(y*w+x)*4;
   for(let k=0;k<4;k++){
    if(original[at+k]!==255)throw Error('Original source cell is not pure white');
    if(base[at+k]!==0)throw Error('Unexpected baseline pixel in requested white block');
    out[at+k]=255;
   }
  }
  let changed=0,outside=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
   const at=(y*w+x)*4,different=out.slice(at,at+4).some((n,k)=>n!==base[at+k]);
   changed+=Number(different);outside+=Number(different&&!inside(x,y));
  }
  if(changed!==32||outside)throw Error('Unexpected white correction coverage');
  const c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').putImageData(new ImageData(out,w,h),0,0);
  const image=c.toDataURL('image/png'),rt=await read(image);
  for(let i=0;i<out.length;i++)if(out[i]!==rt[i])throw Error('PNG roundtrip mismatch');
  function crop(data){const src=document.createElement('canvas');src.width=w;src.height=h;src.getContext('2d').putImageData(new ImageData(data,w,h),0,0);const c=document.createElement('canvas');c.width=96;c.height=24;c.getContext('2d').drawImage(src,16,4,96,24,0,0,96,24);return c.toDataURL('image/png');}
  return{image,beforeCrop:crop(base),afterCrop:crop(out),proof:{size:[w,h],editedRegions:rois,originalSourceCells:[{x:8,y:2},{x:23,y:2}],restoredColor:[255,255,255,255],matchesOriginalWhiteCells:true,changedPixels:changed,changedOutsideRegions:outside,allRemainingPixelsUnchanged:true,pngRoundtripExact:true}};
 },{baseline:uri(input.baseline),original:uri(input.original)});
 const output=Buffer.from(packed.image.split(',')[1],'base64');fs.writeFileSync(path.join(dir,'portrait-128x160.png'),output);
 const html=`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>諸葛亮・依原圖恢復白色</title><style>*{box-sizing:border-box}body{margin:0;padding:24px;background:#0b0b0b;color:#000;font-family:"PingFang TC",system-ui,sans-serif}main{max-width:940px;margin:auto;padding:24px;background:#ffd5cb;border:6px double #000;outline:3px solid #ffd5cb}h1{font-size:27px;margin:0 0 10px}.intro{font-size:16px;line-height:1.7;margin:0 0 23px}.grid{display:grid;grid-template-columns:280px 1fr;gap:26px;align-items:center}figure{margin:0;text-align:center}h2{font-size:19px;margin:0 0 10px}.frame{display:block;border:3px solid #000;box-sizing:content-box;image-rendering:pixelated;background:#000;margin:auto}.portrait{width:256px;height:320px}.crop{width:480px;height:120px}.detail figure+figure{margin-top:25px}footer{margin-top:23px;padding-top:15px;border-top:2px solid #000;font-size:14px;line-height:1.7}@media(max-width:850px){.grid{grid-template-columns:1fr}.crop{width:384px;height:96px}.portrait{width:128px;height:160px}}@media(max-width:460px){.crop{width:288px;height:72px}main{padding:14px}h1{font-size:21px}}</style><main><h1>諸葛亮・依原圖恢復白色</h1><p class="intro">紅框所指的兩處，恢復為與原圖一致的純白色。<br>橙色冠片、黑色外緣，以及人物明暗與五官皆保留。</p><div class="grid"><figure><h2>修正後完整畫像</h2><img class="frame portrait" src="${packed.image}" alt="諸葛亮兩處純白缺口修正版"></figure><div class="detail"><figure><h2>帽頂細節・修改前</h2><img class="frame crop" src="${packed.beforeCrop}" alt="修改前兩處黑色區塊"></figure><figure><h2>帽頂細節・修改後</h2><img class="frame crop" src="${packed.afterCrop}" alt="依原圖恢復兩處純白區塊"></figure></div></div><footer>輸出128×160。本次只恢復兩塊4×4區域，共32像素；與原圖的兩個白色像素一致。</footer></main></html>`;
 fs.writeFileSync(path.join(dir,'comparison.html'),html);await page.setContent(html);await page.evaluate(async()=>Promise.all([...document.images].map(i=>i.decode())));await page.screenshot({path:path.join(dir,'comparison.png'),fullPage:true});
 for(const[key,file]of Object.entries(files))assert.equal(sha(fs.readFileSync(file)),hashes[key]);
 const manifest={schema:'tk2-portrait-original-white-cells-sample-v1',person_id:'san14-candidate-0440',runtime_id:439,name:'諸葛亮',baseline:{path:'../zhuge-liang-preserved-v7/portrait-128x160.png',sha256:hashes.baseline,preserved:true},original:{path:'game/assets/portraits/original/109.png',sha256:hashes.original,preserved:true},source:{path:'generation-source.png',sha256:hashes.study,prompt:'prompt.txt',method:'built-in image_gen'},output:{path:'portrait-128x160.png',sha256:sha(output)},method:'Original-verified pure-white correction restricted to two 4x4 rectangles; generated changes elsewhere are discarded',proof:packed.proof,formalGameIdentityMapUnchanged:true,sampleOnly:true};
 fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');console.log(JSON.stringify(manifest,null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
