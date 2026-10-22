#!/usr/bin/env node
'use strict';
// Import the flat-tip color edit into four bounded rectangles only.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const assert=require('node:assert/strict'),{chromium}=require('playwright');
const dir=__dirname,root=path.resolve(dir,'../../../..');
const files={baseline:path.join(dir,'../zhuge-liang-preserved-v4/portrait-128x160.png'),study:path.join(dir,'generation-source.png'),original:path.join(root,'game/assets/portraits/original/109.png'),identity:path.join(root,'game/config/portrait-identity-map.json')};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const input=Object.fromEntries(Object.entries(files).map(([key,file])=>[key,fs.readFileSync(file)]));
const hashes=Object.fromEntries(Object.entries(input).map(([key,bytes])=>[key,sha(bytes)]));
const uri=b=>'data:image/png;base64,'+b.toString('base64');
assert.equal(hashes.baseline,'0ca300923c89872b7bbb2627ea102c0cfd61b52436a748025aa5ad64e8f89372');
assert.equal(hashes.original,'00ab7c41fc86e84deeede6f42ddf5510b928f7e9ede998ba853836936eb7306c');
(async()=>{const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await browser.newPage({viewport:{width:980,height:660},deviceScaleFactor:1});
 await page.setContent('<!doctype html><body></body>');
 const packed=await page.evaluate(async sources=>{
  const w=128,h=160;
  async function read(url){const i=new Image();i.src=url;await i.decode();const c=document.createElement('canvas');c.width=w;c.height=h;const g=c.getContext('2d',{willReadFrequently:true});g.imageSmoothingEnabled=false;g.drawImage(i,0,0,w,h);return g.getImageData(0,0,w,h).data;}
  const base=await read(sources.baseline),study=await read(sources.study),out=new Uint8ClampedArray(base);
  const tips=[36,52,68,84].map(x=>({x,y:8,width:8,height:5}));
  const inTip=(x,y)=>tips.some(r=>x>=r.x&&x<r.x+r.width&&y>=r.y&&y<r.y+r.height);
  const palette=[];const keys=new Set();
  for(let at=0;at<base.length;at+=4){const c=[...base.slice(at,at+3)],key=c.join(',');if(base[at+3]===255&&c[0]>=180&&c[0]-c[1]>20&&c[1]-c[2]>15&&!keys.has(key)){keys.add(key);palette.push(c);}}
  const nearest=c=>palette.reduce((a,b)=>b.reduce((s,n,k)=>s+(n-c[k])**2,0)<a.reduce((s,n,k)=>s+(n-c[k])**2,0)?b:a);
  for(const r of tips){
   for(let y=r.y;y<r.y+r.height;y++)for(let x=r.x;x<r.x+r.width;x++){
    const at=(y*w+x)*4;
    // Straight top lighting, with vertical side shading instead of a round glint.
    let sample=[...study.slice(at,at+3)];
    if(sample[0]<160||sample[0]-sample[1]<20||sample[1]-sample[2]<15){const fallback=((r.y+r.height)*w+x)*4;sample=[...base.slice(fallback,fallback+3)];}
    let color=nearest(sample);
    if(y===r.y)color=x-r.x<r.width-2?[255,187,89]:[223,121,34];
    for(let k=0;k<3;k++)out[at+k]=color[k];out[at+3]=255;
   }
  }
  let changed=0,outsideChanges=0;
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){const at=(y*w+x)*4;const different=out.slice(at,at+4).some((n,k)=>n!==base[at+k]);changed+=Number(different);outsideChanges+=Number(different&&!inTip(x,y));}
  if(outsideChanges||!changed)throw Error('Unbounded edit');
  for(const r of tips){
   for(let x=r.x;x<r.x+r.width;x++){
    const at=(r.y*w+x)*4;if(out[at+3]!==255||out[at]<180)throw Error('Non-flat top');
    const above=((r.y-1)*w+x)*4;if(base[above+3]!==255||base[above]!==255)throw Error('Unexpected geometry above tip');
   }
  }
  const c=document.createElement('canvas');c.width=w;c.height=h;c.getContext('2d').putImageData(new ImageData(out,w,h),0,0);
  const image=c.toDataURL('image/png'),decoded=await read(image);
  for(let i=0;i<out.length;i++)if(out[i]!==decoded[i])throw Error('PNG roundtrip mismatch');
  function crop(data){const c=document.createElement('canvas');c.width=72;c.height=24;const g=c.getContext('2d');const full=document.createElement('canvas');full.width=w;full.height=h;full.getContext('2d').putImageData(new ImageData(data,w,h),0,0);g.drawImage(full,28,4,72,24,0,0,72,24);return c.toDataURL('image/png');}
  return{image,beforeCrop:crop(base),afterCrop:crop(out),proof:{size:[w,h],editedRects:tips,changedPixels:changed,changedOutsideTipRects:outsideChanges,allFourTipTopsFlat:true,allFourTopEdgesAtY:8,faceAndRemainingPortraitExact:true,pngRoundtripExact:true,editSource:'built-in image_gen with restricted pixel composite'}};
 },{baseline:uri(input.baseline),study:uri(input.study)});
 const output=Buffer.from(packed.image.split(',')[1],'base64');fs.writeFileSync(path.join(dir,'portrait-128x160.png'),output);
 const html=`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>諸葛亮・帽頂平直修正版</title><style>*{box-sizing:border-box}body{margin:0;padding:24px;background:#0b0b0b;color:#000;font-family:"PingFang TC",system-ui,sans-serif}main{max-width:940px;margin:auto;padding:24px;background:#ffd5cb;border:6px double #000;outline:3px solid #ffd5cb}h1{font-size:27px;margin:0 0 10px}.intro{font-size:16px;line-height:1.7;margin:0 0 23px}.grid{display:grid;grid-template-columns:280px 1fr;gap:26px;align-items:center}figure{margin:0;text-align:center}h2{font-size:19px;margin:0 0 10px}.frame{display:block;border:3px solid #000;box-sizing:content-box;image-rendering:pixelated;background:#000;margin:auto}.portrait{width:256px;height:320px}.crop{width:432px;height:144px}.detail figure+figure{margin-top:21px}footer{margin-top:23px;padding-top:15px;border-top:2px solid #000;font-size:14px;line-height:1.7}@media(max-width:800px){.grid{grid-template-columns:1fr}.crop{width:288px;height:96px}.portrait{width:128px;height:160px}}</style><main><h1>諸葛亮・帽頂平直修正版</h1><p class="intro">四個冠片各自改為平頂、直角邊，保留間距與高度。<br>本次只修改帽頂，臉部、鬍鬚、衣領與其餘明暗完全沿用上一版。</p><div class="grid"><figure><h2>修正後完整畫像</h2><img class="frame portrait" src="${packed.image}" alt="諸葛亮平頂冠片修正版"></figure><div class="detail"><figure><h2>帽頂細節・修改前</h2><img class="frame crop" src="${packed.beforeCrop}" alt="修改前圓頭冠片"></figure><figure><h2>帽頂細節・修改後</h2><img class="frame crop" src="${packed.afterCrop}" alt="修改後平直冠片"></figure></div></div><footer>輸出仍為128×160。四處帽頂範圍以外的像素完全未改；原版與之前樣稿均保留。</footer></main></html>`;
 fs.writeFileSync(path.join(dir,'comparison.html'),html);await page.setContent(html);await page.evaluate(async()=>Promise.all([...document.images].map(i=>i.decode())));await page.screenshot({path:path.join(dir,'comparison.png'),fullPage:true});
 for(const[key,file]of Object.entries(files))assert.equal(sha(fs.readFileSync(file)),hashes[key]);
 const manifest={schema:'tk2-portrait-flat-crown-sample-v1',person_id:'san14-candidate-0440',runtime_id:439,name:'諸葛亮',baseline:{path:'../zhuge-liang-preserved-v4/portrait-128x160.png',sha256:hashes.baseline,preserved:true},source:{path:'generation-source.png',sha256:hashes.study,prompt:'prompt.txt',method:'built-in image_gen'},output:{path:'portrait-128x160.png',sha256:sha(output)},proof:packed.proof,originalPreserved:true,formalGameIdentityMapUnchanged:true,sampleOnly:true};
 fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');console.log(JSON.stringify(manifest,null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
