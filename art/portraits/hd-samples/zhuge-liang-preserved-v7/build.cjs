#!/usr/bin/env node
'use strict';
// Restore the pre-widening v5 and fill only the two user-marked inner notches.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const assert=require('node:assert/strict'),{chromium}=require('playwright');
const dir=__dirname,root=path.resolve(dir,'../../../..');
const files={baseline:path.join(dir,'../zhuge-liang-preserved-v5/portrait-128x160.png'),study:path.join(dir,'generation-source.png'),original:path.join(root,'game/assets/portraits/original/109.png'),identity:path.join(root,'game/config/portrait-identity-map.json')};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),uri=b=>'data:image/png;base64,'+b.toString('base64');
const input=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,fs.readFileSync(file)]));
const hashes=Object.fromEntries(Object.entries(input).map(([key,bytes])=>[key,sha(bytes)]));
assert.equal(hashes.baseline,'9df3763bab9eca304aefc981e5510b4092e85ed4860e1d3196d0e336dc4229fb');
assert.equal(hashes.original,'00ab7c41fc86e84deeede6f42ddf5510b928f7e9ede998ba853836936eb7306c');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await browser.newPage({viewport:{width:980,height:660},deviceScaleFactor:1});
 await page.setContent('<!doctype html><body></body>');
 const packed=await page.evaluate(async source=>{
  const w=128,h=160;
  async function read(url){const i=new Image();i.src=url;await i.decode();const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d',{willReadFrequently:true});g.imageSmoothingEnabled=false;g.drawImage(i,0,0,w,h);return g.getImageData(0,0,w,h).data;}
  const base=await read(source),out=new Uint8ClampedArray(base);
  const rois=[{x:31,y:8,width:5,height:4},{x:92,y:8,width:5,height:4}];
  const inside=(x,y)=>rois.some(r=>x>=r.x&&x<r.x+r.width&&y>=r.y&&y<r.y+r.height);
  let whiteFilled=0,grayFilled=0;
  for(const r of rois)for(let y=r.y;y<r.y+r.height;y++)for(let x=r.x;x<r.x+r.width;x++){
   const at=(y*w+x)*4,rgb=[...base.slice(at,at+3)];
   if(base[at+3]){
    if(Math.max(...rgb)-Math.min(...rgb)>10||Math.min(...rgb)<200)throw Error('Non-neutral pixel in user notch');
    if(rgb.every(n=>n===255))whiteFilled++;else grayFilled++;
   }
   // Original black ink is zero RGBA, displayed on the black portrait backdrop.
   out[at]=out[at+1]=out[at+2]=out[at+3]=0;
  }
  let changed=0,outside=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){
   const at=(y*w+x)*4,different=out.slice(at,at+4).some((n,k)=>n!==base[at+k]);
   changed+=Number(different);outside+=Number(different&&!inside(x,y));
  }
  if(changed!==22||whiteFilled!==21||grayFilled!==1||outside)throw Error('Unexpected notch edit coverage');
  const c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').putImageData(new ImageData(out,w,h),0,0);
  const image=c.toDataURL('image/png'),rt=await read(image);
  for(let i=0;i<out.length;i++)if(out[i]!==rt[i])throw Error('PNG roundtrip mismatch');
  function crop(data){const src=document.createElement('canvas');src.width=w;src.height=h;src.getContext('2d').putImageData(new ImageData(data,w,h),0,0);const c=document.createElement('canvas');c.width=96;c.height=24;c.getContext('2d').drawImage(src,16,4,96,24,0,0,96,24);return c.toDataURL('image/png');}
  return{image,beforeCrop:crop(base),afterCrop:crop(out),proof:{size:[w,h],editedRegions:rois,whitePixelsFilled:whiteFilled,grayPixelsFilled:grayFilled,changedPixels:changed,changedOutsideRegions:outside,outerCurvesUnchanged:true,innerWhiteOpeningsBelowY12Unchanged:true,allRemainingPixelsUnchanged:true,pngRoundtripExact:true}};
 },uri(input.baseline));
 const output=Buffer.from(packed.image.split(',')[1],'base64');fs.writeFileSync(path.join(dir,'portrait-128x160.png'),output);
 const html=`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>諸葛亮・按紅框補黑</title><style>*{box-sizing:border-box}body{margin:0;padding:24px;background:#0b0b0b;color:#000;font-family:"PingFang TC",system-ui,sans-serif}main{max-width:940px;margin:auto;padding:24px;background:#ffd5cb;border:6px double #000;outline:3px solid #ffd5cb}h1{font-size:27px;margin:0 0 10px}.intro{font-size:16px;line-height:1.7;margin:0 0 23px}.grid{display:grid;grid-template-columns:280px 1fr;gap:26px;align-items:center}figure{margin:0;text-align:center}h2{font-size:19px;margin:0 0 10px}.frame{display:block;border:3px solid #000;box-sizing:content-box;image-rendering:pixelated;background:#000;margin:auto}.portrait{width:256px;height:320px}.crop{width:480px;height:120px}.detail figure+figure{margin-top:25px}footer{margin-top:23px;padding-top:15px;border-top:2px solid #000;font-size:14px;line-height:1.7}@media(max-width:850px){.grid{grid-template-columns:1fr}.crop{width:384px;height:96px}.portrait{width:128px;height:160px}}@media(max-width:460px){.crop{width:288px;height:72px}main{padding:14px}h1{font-size:21px}}</style><main><h1>諸葛亮・按紅框補黑</h1><p class="intro">只將靠近橙色冠片的兩個內側小缺口補成黑色。<br>兩側外緣、下方白色開口，以及臉部和衣領皆沿用原形。</p><div class="grid"><figure><h2>修正後完整畫像</h2><img class="frame portrait" src="${packed.image}" alt="諸葛亮兩個內側小缺口補黑版"></figure><div class="detail"><figure><h2>帽頂細節・修改前</h2><img class="frame crop" src="${packed.beforeCrop}" alt="修改前兩個小缺口"></figure><figure><h2>帽頂細節・修改後</h2><img class="frame crop" src="${packed.afterCrop}" alt="修改後缺口補黑，外緣保留"></figure></div></div><footer>輸出128×160。本次僅補黑22個像素，其餘像素完全未改；原圖與先前樣稿均保留。</footer></main></html>`;
 fs.writeFileSync(path.join(dir,'comparison.html'),html);await page.setContent(html);await page.evaluate(async()=>Promise.all([...document.images].map(i=>i.decode())));await page.screenshot({path:path.join(dir,'comparison.png'),fullPage:true});
 for(const[key,file]of Object.entries(files))assert.equal(sha(fs.readFileSync(file)),hashes[key]);
 const manifest={schema:'tk2-portrait-user-marked-notch-sample-v1',person_id:'san14-candidate-0440',runtime_id:439,name:'諸葛亮',baseline:{path:'../zhuge-liang-preserved-v5/portrait-128x160.png',sha256:hashes.baseline,preserved:true},source:{path:'generation-source.png',sha256:hashes.study,prompt:'prompt.txt',method:'built-in image_gen'},userReference:'User attached screenshot with two red circles; only marked inner white notches filled',output:{path:'portrait-128x160.png',sha256:sha(output)},method:'Local notch-fill edit restricted to two 5x4 native rectangles on v5; previous outer widening is not imported',proof:packed.proof,originalPreserved:true,formalGameIdentityMapUnchanged:true,sampleOnly:true};
 fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');console.log(JSON.stringify(manifest,null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
