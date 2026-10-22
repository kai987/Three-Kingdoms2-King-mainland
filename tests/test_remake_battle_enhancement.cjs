'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'..'),builder=require('../tools/battle-enhancement/build.cjs'),{decodePng}=require('../tools/portraits/prepare_enhanced.cjs'),{WEAPONS,HORSES}=require('../game/duel-appearance.js');
const manifest=JSON.parse(fs.readFileSync(path.join(ROOT,'game/assets/battle-enhanced/index.json')));
let nativeFormationPixels=0;
for(const key of ['attack_formation','attack_formation_enemy']){
 const formation=manifest.sprites[key];assert.equal(formation.frames.length,2);
 for(const row of formation.frames){
  assert.equal(row.method,'native_nearest4x');assert.deepEqual([row.width,row.height,row.logical_width,row.logical_height],[512,640,128,160]);
  const src=decodePng(fs.readFileSync(path.join(ROOT,'game'+row.source_path))),image=decodePng(fs.readFileSync(path.join(ROOT,'game'+row.path)));
  for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++){
   const dst=(y*image.width+x)*4,at=(Math.floor(y/4)*src.width+Math.floor(x/4))*4;
   assert(image.rgba.subarray(dst,dst+4).equals(src.rgba.subarray(at,at+4)),'Each original attack pixel must remain an exact4×4 block including its transparent edge');nativeFormationPixels++;
  }
 }
}
let islands=0,coats=0,redTasselPixels=0,protectedShoulderPixels=0,whiteCoatPixels=0;
for(const weapon of builder.LEGACY_WEAPONS){
 const source=decodePng(fs.readFileSync(path.join(ROOT,manifest.studies[weapon].study))),poses=builder.poseImages(source),boxes=poses.map(builder.imageBounds),scale=Math.min(...boxes.map(([l,t,r,b])=>Math.min(320/(r-l),352/(b-t))));
 let painted=0,kept=0;
 for(let i=0;i<source.width*source.height;i++){
  const a=poses[0].rgba[i*4+3]>=128,b=poses[1].rgba[i*4+3]>=128;assert(!(a&&b),'Source pixels must never bleed into both poses');
  if(source.rgba[i*4+3]>=128){painted++;kept+=Number(a||b);}
 }
 assert(kept/painted>.995,'Connected-island packing retains all substantial painted source art');islands+=2;
 for(let pose=0;pose<2;pose++){
  const fitted=builder.fitted(poses[pose],boxes[pose],scale),mask=builder.horseMask(fitted),loaded={};
  for(const horse of builder.LEGACY_HORSES){
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
// New action art is independently painted, not a renamed pointer to either of
// the old two poses. Check the complete source grid, all named coats and every
// rider/weapon pixel outside its deliberately cyan horse-only source region.
let actionFrames=0,actionCoatPixels=0,actionRiderPixels=0,actionTasselPixels=0;
assert.deepEqual(manifest.actions,[...builder.ACTIONS]);assert.equal(WEAPONS.length,12);assert.equal(HORSES.length,13);
for(const weapon of WEAPONS){
 const info=manifest.action_studies[weapon],source=decodePng(fs.readFileSync(path.join(ROOT,info.study))),poses=builder.actionPoseImages(source),boxes=poses.map(builder.imageBounds),scale=Math.min(...boxes.map(([l,t,r,b])=>Math.min(448/(r-l),352/(b-t))));
 assert.equal(poses.length,8);assert.deepEqual(info.source_grid,builder.actionGrid(source));assert.deepEqual(info.source_cells,poses.map(pose=>pose.source_rect));
 const assignments=new Uint8Array(source.width*source.height);let sourcePaint=0,keptPaint=0;
 for(let i=0;i<source.width*source.height;i++)sourcePaint+=Number(source.rgba[i*4+3]>=128);
 for(const pose of poses){const[left,top]=pose.source_rect;for(let y=0;y<pose.height;y++)for(let x=0;x<pose.width;x++){
  const at=(y*pose.width+x)*4;if(pose.rgba[at+3]<128)continue;const sourceIndex=(y+top)*source.width+x+left;
  assert.equal(assignments[sourceIndex],0,'No painted source pixel may bleed into two adjacent action figures');assignments[sourceIndex]=1;keptPaint++;
  assert(pose.rgba.subarray(at,at+4).equals(source.rgba.subarray(sourceIndex*4,sourceIndex*4+4)),'Figure isolation must preserve the original painted pixels');
 }}
 assert(keptPaint/sourcePaint>.995,'Complete mounted figures, extended weapons, horse tails and detached arrows must remain intact');
 const base=poses.map((pose,index)=>builder.fittedAction(pose,boxes[index],scale)),referenceMasks=base.map(p=>p.mask);
 const originalBodies=base.map(p=>{const rgba=Buffer.from(p.rgba);for(let i=0;i<p.mask.length;i++)if(p.mask[i])rgba.fill(0,i*4,i*4+4);return rgba;});
 const bodyInfo=base.map(p=>{let count=0;const red=[];for(let i=0;i<p.mask.length;i++)if(!p.mask[i]&&p.rgba[i*4+3]){count++;const at=i*4;if(p.rgba[at]>90&&p.rgba[at+1]/p.rgba[at]<.30)red.push(i);}return {count,red};});
 for(const horse of HORSES){
  const row=manifest.action_atlases[weapon][horse],image=decodePng(fs.readFileSync(path.join(ROOT,'game'+row.path)));
  assert.deepEqual([image.width,image.height],[4096,384]);assert.deepEqual(row.frames.map(f=>f.action),[...builder.ACTIONS]);
  for(const frame of row.frames)assert(builder.frameHasMargin(image,frame.source_rect),'Every actual action frame must retain transparent weapon/hoof margins instead of touching its cell edge');
  const unique=new Set();
  for(let pose=0;pose<8;pose++){
   const frame=Buffer.alloc(512*384*4);for(let y=0;y<384;y++)image.rgba.copy(frame,y*512*4,(y*4096+pose*512)*4,(y*4096+(pose+1)*512)*4);
   unique.add(require('node:crypto').createHash('sha256').update(frame).digest('hex'));
   const rider=Buffer.from(frame),mask=referenceMasks[pose];let visibleCoat=0;
   for(let i=0;i<mask.length;i++){
    const at=i*4;
    if(mask[i]){
     assert.equal(frame[at+3],255,'A named coat cannot hide or grow the horse silhouette');
     const expected=builder.ACTION_COATS[horse][base[pose].levels[i]];
     assert(frame[at]===expected[0]&&frame[at+1]===expected[1]&&frame[at+2]===expected[2],'Every actual horse pixel must use its selected named palette, not a relabeled generic atlas');
     visibleCoat++;rider.fill(0,at,at+4);
    }
   }
   assert(rider.equals(originalBodies[pose]),'A named horse palette must never repaint the rider, face, weapon, reins or transparent padding');
   const red=bodyInfo[pose].red;
   for(const i of red){const at=i*4;assert(frame.subarray(at,at+4).equals(base[pose].rgba.subarray(at,at+4)),'Weapon tassels and rider red remain independent of horse color');}
   actionTasselPixels+=red.length;actionCoatPixels+=visibleCoat;actionRiderPixels+=bodyInfo[pose].count;actionFrames++;
  }
  assert.equal(unique.size,8,'All eight action silhouettes/poses must be independently drawn, not aliases of idle/strike');
 }
}
assert.equal(actionFrames,12*13*8);assert(actionRiderPixels>100000);assert(actionCoatPixels>100000);
assert.equal(new Set(HORSES.map(horse=>JSON.stringify(builder.ACTION_COATS[horse]))).size,13,'Every named mount has its own explicit presentation palette');
console.log(`battle enhanced art: ${nativeFormationPixels} exact original formation pixels, ${islands} preserved v1 poses, ${coats} v1 coats; ${actionFrames} independently painted action frames, ${actionCoatPixels} protected coat pixels, ${actionRiderPixels} preserved rider/weapon pixels and ${actionTasselPixels} untouched red detail pixels`);
