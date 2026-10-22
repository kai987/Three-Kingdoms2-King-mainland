#!/usr/bin/env node
'use strict';
// Transfer a stronger pixel-color study onto B's exact material masks.
// No generated silhouettes, eyes, nose strokes or beard strokes are imported.
const fs = require('node:fs'), path = require('node:path');
const crypto = require('node:crypto'), assert = require('node:assert/strict');
const { chromium } = require('playwright');
const dir = __dirname, root = path.resolve(dir, '../../../..');
const paths = {
  baseline: path.join(dir, '../zhuge-liang-preserved-v2/edge-refined-128x160.png'),
  original: path.join(root, 'game/assets/portraits/original/109.png'),
  identity: path.join(root, 'game/config/portrait-identity-map.json'),
  generated: path.join(dir, 'generation-source.png'),
};
const sha = b => crypto.createHash('sha256').update(b).digest('hex');
const input = Object.fromEntries(Object.entries(paths).map(([id, p]) => [id, fs.readFileSync(p)]));
const hashes = Object.fromEntries(Object.entries(input).map(([id, bytes]) => [id, sha(bytes)]));
assert.equal(hashes.original, '00ab7c41fc86e84deeede6f42ddf5510b928f7e9ede998ba853836936eb7306c');
assert.equal(hashes.baseline, '4e96dc9ebfba1344f68782c3e42c4823bea55f0ab700f61c225353bcf5f9448b');
const uri = b => 'data:image/png;base64,' + b.toString('base64');

(async () => {
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1060,height:1120},deviceScaleFactor:1});
    await page.setContent('<!doctype html><body></body>');
    const packed = await page.evaluate(async ({baseline,generated}) => {
      const w=128,h=160;
      async function decode(src) { const i=new Image();i.src=src;await i.decode();return i; }
      function read(img) {
        const c=document.createElement('canvas');c.width=w;c.height=h;
        const g=c.getContext('2d',{willReadFrequently:true});g.imageSmoothingEnabled=false;
        g.drawImage(img,0,0,w,h);return g.getImageData(0,0,w,h).data;
      }
      const b=await decode(baseline),g=await decode(generated);
      if(b.width!==w||b.height!==h)throw Error('Unexpected baseline dimensions');
      const raw=read(b),colors=read(g),out=new Uint8ClampedArray(raw);
      const skin=[[142,56,0],[185,85,10],[223,121,34],[247,162,71],[255,187,89],[255,218,128]];
      const brown=[[108,46,7],[158,65,0],[198,99,18]];
      const cloth=[[188,189,185],[226,226,222],[255,255,255]];
      const nearest=(sample,palette)=>palette.reduce((best,c)=>{
        const distance=c.reduce((s,n,k)=>s+(n-sample[k])**2,0);
        return distance<best.distance?{color:c,distance}:best;
      },{color:palette[0],distance:Infinity}).color;
      const isWarm=c=>c[0]>90 && c[0]-c[1]>20 && c[1]-c[2]>15;
      const sampled=(x,y)=>[...colors.slice((y*w+x)*4,(y*w+x)*4+3)];
      // Color boundaries from the study may differ by one pixel. Only sample
      // the original material's color family; imported geometry is discarded.
      function warmSample(x,y,fallback) {
        const at=sampled(x,y);if(isWarm(at))return at;
        let best=null,bestDistance=Infinity;
        for(let dy=-3;dy<=3;dy++)for(let dx=-3;dx<=3;dx++){
          const xx=x+dx,yy=y+dy;if(xx<0||xx>=w||yy<0||yy>=h)continue;
          const c=sampled(xx,yy),distance=dx*dx+dy*dy;
          if(isWarm(c)&&distance<bestDistance){best=c;bestDistance=distance;}
        }
        return best||fallback;
      }
      const eyeWhiteAt=(x,y)=>y>=68&&y<78&&x>=32&&x<96;
      const facialBrownAt=(x,y)=>y>=60&&y<128&&x>=32&&x<96;
      let changed=0,visibleChanged=0,inkCount=0,eyeCount=0,strokeCount=0,alphaChanges=0;
      let deltaSum=0;
      for(let y=0;y<h;y++)for(let x=0;x<w;x++){
        const at=(y*w+x)*4,rgb=[...raw.slice(at,at+3)];let color=rgb;
        if(!raw[at+3])inkCount++;
        else if(rgb[0]===247&&rgb[1]===162&&rgb[2]===71)color=nearest(warmSample(x,y,rgb),skin);
        else if(rgb[0]===158&&rgb[1]===65&&rgb[2]===0){
          if(facialBrownAt(x,y))strokeCount++;
          else color=nearest(warmSample(x,y,rgb),brown);
        } else if(rgb.every(n=>n===255)){
          if(eyeWhiteAt(x,y))eyeCount++;
          else {
            const c=sampled(x,y),range=Math.max(...c)-Math.min(...c);
            // Pure background remains white. Only neutral study shades are
            // transferred onto an existing white pixel, never new outlines.
            if(range<20&&Math.min(...c)>130)color=nearest(c,cloth);
          }
        } else throw Error('Unexpected B material');
        if(raw[at+3])for(let c=0;c<3;c++)out[at+c]=color[c];
        const delta=Math.max(...rgb.map((n,k)=>Math.abs(n-out[at+k])));
        changed+=Number(delta>0);visibleChanged+=Number(delta>=24);deltaSum+=delta;
        alphaChanges+=Number(out[at+3]!==raw[at+3]);
        if(!raw[at+3]&&out.slice(at,at+4).some((n,k)=>n!==raw[at+k]))throw Error('Original ink changed');
        if(raw[at+3]&&rgb.every(n=>n===255)&&eyeWhiteAt(x,y)&&out.slice(at,at+4).some((n,k)=>n!==raw[at+k]))throw Error('Eye white changed');
        if(raw[at+3]&&rgb[0]===158&&facialBrownAt(x,y)&&out.slice(at,at+4).some((n,k)=>n!==raw[at+k]))throw Error('Facial brown stroke changed');
      }
      if(alphaChanges)throw Error('Original alpha/ink geometry changed');
      if(visibleChanged<1000)throw Error('Refinement not visibly strong enough');
      const c=document.createElement('canvas');c.width=w;c.height=h;const ctx=c.getContext('2d',{willReadFrequently:true});
      ctx.putImageData(new ImageData(out,w,h),0,0);const encoded=c.toDataURL('image/png');
      const decoded=await decode(encoded);ctx.clearRect(0,0,w,h);ctx.drawImage(decoded,0,0);
      const rt=ctx.getImageData(0,0,w,h).data;
      for(let i=0;i<out.length;i++)if(rt[i]!==out[i])throw Error('PNG roundtrip mismatch');
      const palette=new Set();for(let i=0;i<out.length;i+=4)palette.add([...out.slice(i,i+4)].join(','));
      return {image:encoded,proof:{outputSize:[w,h],generatedNativeSize:[g.width,g.height],
        changedPixels:changed,changedPercent:Math.round(changed/(w*h)*10000)/100,
        materiallyChangedPixels:visibleChanged,materiallyChangedPercent:Math.round(visibleChanged/(w*h)*10000)/100,
        materialDifferenceThreshold:24,meanMaximumChannelDelta:Math.round(deltaSum/(w*h)*100)/100,
        originalInkPixelsUnchanged:inkCount,eyeWhitePixelsUnchanged:eyeCount,facialBrownStrokePixelsUnchanged:strokeCount,
        alphaChanges,allOriginalMaterialGeometryRetained:true,paletteSize:palette.size,
        pngRoundtripExact:true,aiColorStudy:true,generatedFeatureGeometryImported:false}};
    },{baseline:uri(input.baseline),generated:uri(input.generated)});
    const output=Buffer.from(packed.image.split(',')[1],'base64');
    fs.writeFileSync(path.join(dir,'portrait-128x160.png'),output);
    const html=`<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>諸葛亮・B 與明暗強化版</title><style>*{box-sizing:border-box}body{margin:0;padding:26px;background:#0b0b0b;color:#000;font-family:"PingFang TC",system-ui,sans-serif}main{max-width:1000px;margin:auto;padding:25px;background:#ffd5cb;border:6px double #000;outline:3px solid #ffd5cb}h1{font-size:29px;margin:0 0 10px}.intro{font-size:17px;line-height:1.65;margin:0 0 22px}section{display:grid;grid-template-columns:1fr 1fr;gap:22px}figure{margin:0;text-align:center}h2{font-size:21px;margin:0 0 12px}.frame{display:block;width:384px;height:480px;box-sizing:content-box;border:3px solid #000;background:#000;image-rendering:pixelated;margin:auto}.note{font-size:16px;line-height:1.7;margin:12px 0 0}.actual{margin-top:22px;padding-top:18px;border-top:2px solid #000}.actual .frame{width:128px;height:160px}.actual h2{font-size:17px}footer{font-size:14px;line-height:1.7;margin-top:22px;border-top:2px solid #000;padding-top:14px}@media(max-width:850px){body{padding:12px}main{padding:15px}.frame{width:256px;height:320px}}@media(max-width:620px){h1{font-size:22px}.intro{font-size:14px}.frame{width:128px;height:160px}h2{font-size:17px}.note{font-size:13px}section{gap:12px}}</style><main><h1>諸葛亮・B 與明暗強化版</h1><p class="intro">這次加入明顯的像素明暗：額頭、鼻樑、臉頰、帽冠和衣領。<br>沿用 B 的輪廓與五官線條。上排放大 3 倍，下排為遊戲內的實際尺寸。</p><section><figure><h2>B・原配色</h2><img class="frame" src="${uri(input.baseline)}" alt="B原配色"><p class="note">原色平塗<br>像素輪廓較清楚，明暗較少</p></figure><figure><h2>B++・明暗強化</h2><img class="frame" src="${packed.image}" alt="B明暗強化版"><p class="note">分層高光與陰影<br>保留原五官與帽冠結構</p></figure></section><section class="actual"><figure><h2>B・128×160</h2><img class="frame" src="${uri(input.baseline)}" alt="B128乘160實際尺寸"></figure><figure><h2>B++・128×160</h2><img class="frame" src="${packed.image}" alt="強化版128乘160實際尺寸"></figure></section><footer>新增明暗屬於美術強化，並非還原原始畫像未記錄的細節。<br>原圖、B、B+ 均保留；本次為樣稿，尚未替換正式遊戲畫像。</footer></main></html>`;
    fs.writeFileSync(path.join(dir,'comparison.html'),html);
    await page.setContent(html);await page.evaluate(async()=>Promise.all([...document.images].map(i=>i.decode())));
    await page.screenshot({path:path.join(dir,'comparison.png'),fullPage:true});
    for(const[id,p]of Object.entries(paths))assert.equal(sha(fs.readFileSync(p)),hashes[id]);
    const manifest={schema:'tk2-portrait-strong-color-refinement-v1',person_id:'san14-candidate-0440',runtime_id:439,name:'諸葛亮',
      original:{path:'game/assets/portraits/original/109.png',sha256:hashes.original,preserved:true},
      baseline:{path:'../zhuge-liang-preserved-v2/edge-refined-128x160.png',sha256:hashes.baseline,preserved:true},
      colorStudy:{path:'generation-source.png',sha256:hashes.generated,method:'built-in image_gen',prompt:'prompt.txt'},
      output:{path:'portrait-128x160.png',sha256:sha(output)},proof:packed.proof,
      method:'AI pixel-color study projected onto original B material masks; original transparent ink, eye whites and facial brown strokes locked',
      sampleOnly:true,formalGameIdentityMapUnchanged:true};
    fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
    console.log(JSON.stringify(manifest,null,2));
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
