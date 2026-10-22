'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'..'),builder=require('../tools/battle-enhancement/build.cjs'),{decodePng}=require('../tools/portraits/prepare_enhanced.cjs'),{WEAPONS,HORSES}=require('../game/duel-appearance.js');
const manifest=JSON.parse(fs.readFileSync(path.join(ROOT,'game/assets/battle-enhanced/index.json')));
let islands=0,coats=0,redTasselPixels=0,protectedShoulderPixels=0,whiteCoatPixels=0;
for(const weapon of WEAPONS){
 const source=decodePng(fs.readFileSync(path.join(ROOT,manifest.studies[weapon].study))),poses=builder.poseImages(source),boxes=poses.map(builder.imageBounds),scale=Math.min(...boxes.map(([l,t,r,b])=>Math.min(320/(r-l),352/(b-t))));
 let painted=0,kept=0;
 for(let i=0;i<source.width*source.height;i++){
  const a=poses[0].rgba[i*4+3]>=128,b=poses[1].rgba[i*4+3]>=128;assert(!(a&&b),'Source pixels must never bleed into both poses');
  if(source.rgba[i*4+3]>=128){painted++;kept+=Number(a||b);}
 }
 assert(kept/painted>.995,'Connected-island packing retains all substantial painted source art');islands+=2;
 for(let pose=0;pose<2;pose++){
  const fitted=builder.fitted(poses[pose],boxes[pose],scale),mask=builder.horseMask(fitted),loaded={};
  for(const horse of HORSES){
   const row=manifest.duelists[weapon][horse].frames[pose],image=decodePng(fs.readFileSync(path.join(ROOT,'game'+row.path)));loaded[horse]=image.rgba;
   assert.notEqual(manifest.duelists[weapon][horse].frames[0].sha256,manifest.duelists[weapon][horse].frames[1].sha256,'Each weapon has two separately painted poses');
   let changed=0;
   for(let i=0;i<384*384;i++){
    const at=i*4;assert.equal(image.rgba[at+3],fitted.rgba[at+3],'Horse color changes cannot alter silhouettes or alpha');
    if(!mask[i])assert(image.rgba.subarray(at,at+4).equals(fitted.rgba.subarray(at,at+4)),'Rider, weapon and all pixels outside the horse coat mask must retain source color');
    else changed+=Number(!image.rgba.subarray(at,at+3).equals(fitted.rgba.subarray(at,at+3)));
    const r=fitted.rgba[at],g=fitted.rgba[at+1];
    if(fitted.rgba[at+3]&&r>90&&g/r<.30){assert(image.rgba.subarray(at,at+4).equals(fitted.rgba.subarray(at,at+4)),'Red weapon tassels must not become white/black with the horse');if(horse==='white')redTasselPixels++;}
   }
   assert(changed>500,'A selected coat must visibly differ from the source chestnut paint');coats++;
  }
  // Regression: the LiuBei idle frame has a brown leather shoulder, sharing
  // horse pigments. The original broad warm mask wrongly turned it gray.
  if(weapon==='dual-swords'&&pose===0)for(let y=210;y<238;y++)for(let x=163;x<192;x++){
   const at=(y*384+x)*4,r=fitted.rgba[at],g=fitted.rgba[at+1],b=fitted.rgba[at+2];
   if(fitted.rgba[at+3]&&r>=100&&r<=200&&g/r>.32&&r-g>25&&g-b>8){assert.equal(mask[y*384+x],0,'LiuBei shoulder leather is rider paint, not a horse coat');assert(loaded.white.subarray(at,at+4).equals(loaded.black.subarray(at,at+4)));protectedShoulderPixels++;}
  }
  // Conversely, protecting the rider must not leave a large chestnut rump or
  // neck on the white mount. These are source-confirmed horse-coat regions.
  if(weapon==='dual-swords'&&pose===0)for(const[l,t,r,b]of[[110,260,145,280],[237,224,267,250]])for(let y=t;y<b;y++)for(let x=l;x<r;x++){
   const at=(y*384+x)*4,rr=fitted.rgba[at],g=fitted.rgba[at+1],bb=fitted.rgba[at+2];
   if(fitted.rgba[at+3]&&rr>=100&&rr<=222&&g/rr>.32&&rr-g>25&&g-bb>8){assert.equal(mask[y*384+x],1,'The horse rump and neck must not be excluded as rider leather');assert(loaded.white[at+1]>g+40);whiteCoatPixels++;}
  }
 }
}
assert(redTasselPixels>100);assert(protectedShoulderPixels>20);assert(whiteCoatPixels>200);
console.log(`battle enhanced art: ${islands} complete source-isolated painted poses, ${coats} alpha-identical coats, no adjacent-pose bleed, ${redTasselPixels} red tassel and ${protectedShoulderPixels} LiuBei shoulder pixels preserved, ${whiteCoatPixels} white rump/neck pixels checked`);
