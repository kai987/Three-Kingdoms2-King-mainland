'use strict';
/* Actual painted sources, palette masks and reproducible4× atlases, not UI mocks. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'..'),builder=require('../tools/soldier-enhancement/build.cjs'),{decodePng}=require('../tools/portraits/prepare_enhanced.cjs');
const read=file=>fs.readFileSync(path.join(ROOT,file)),sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const original=JSON.parse(read('game/assets/battle-original/index.json')),manifest=JSON.parse(read('game/assets/battle-enhanced/index.json')).soldiers;
const originals=new Map();
(function visit(value){if(value&&typeof value==='object'){if(value.path&&value.sha256){const file='game'+value.path;assert.equal(sha(read(file)),value.sha256,'Original NES art must still match its retained native manifest');originals.set(file,sha(read(file)));}for(const child of Object.values(value))visit(child);}})(original);
const report=builder.check(manifest),prepared=builder.prepare();
assert.deepEqual(report,{soldier_types:3,soldier_actions:8,soldier_atlases:6,soldier_frames:48,originals_retained:true});
assert.deepEqual(builder.ACTIONS,['idle','march','ready','attack','guard','hit','retreat','defeat']);
let poses=0,protectedPixels=0,uniformPixels=0,highResolutionDetails=0;
for(const type of builder.TYPES){
 const study=manifest.studies[type],source=decodePng(read(study.study)),isolated=builder.actionPoseImages(source),assigned=new Uint8Array(source.width*source.height),size=builder.LOGICAL[type]*4,images={};
 assert.equal(sha(read(study.study)),study.study_sha256);assert.equal(sha(read(study.prompt)),study.prompt_sha256);assert.deepEqual(study.source_grid,[4,2]);assert.equal(isolated.length,8);
 for(const pose of isolated){const[left,top]=pose.source_rect;for(let y=0;y<pose.height;y++)for(let x=0;x<pose.width;x++){
  const at=(y*pose.width+x)*4;if(pose.rgba[at+3]<128)continue;const i=(y+top)*source.width+x+left;
  assert.equal(assigned[i],0,'No source pixel may appear in two different actions');assigned[i]=1;
  assert(pose.rgba.subarray(at,at+4).equals(source.rgba.subarray(i*4,i*4+4)),'Source isolation must preserve armor, weapons, skin and hooves');
 }}
 for(let i=0;i<assigned.length;i++)assert.equal(assigned[i],Number(source.rgba[i*4+3]>=128),'All painted source components, including detached arrows, must be assigned');
 for(const side of ['friendly','enemy']){
  const row=manifest.types[type][side],image=decodePng(read('game'+row.path));images[side]=image;
  assert.deepEqual([row.width,row.height],[size*8,size]);assert.deepEqual([image.width,image.height],[size*8,size]);assert.equal(row.width,row.logical_width*4*8);assert.equal(row.height,row.logical_height*4);assert.equal(row.facing,'right');
  assert.deepEqual(row.anchor,{x:builder.LOGICAL[type]/2,y:builder.LOGICAL[type]});assert.deepEqual(row.frames,builder.ACTIONS.map((action,i)=>({action,source_rect:[i*size,0,size,size]})));
  const hashes=new Set();
  for(let pose=0;pose<8;pose++){
   const frame=Buffer.alloc(size*size*4);for(let y=0;y<size;y++)image.rgba.copy(frame,y*size*4,(y*image.width+pose*size)*4,(y*image.width+(pose+1)*size)*4);
   hashes.add(sha(frame));let count=0;
   for(let y=0;y<size;y++)for(let x=0;x<size;x++){
    const i=y*size+x,at=i*4;if(!frame[at+3])continue;count++;assert.equal(frame[at+3],255);assert(x>=4&&y>=4&&x<size-4&&y<size-4,'Weapon tips and complete feet must retain a transparent margin');
    // At least some source-specific detail must differ inside original4×4
    // pixel blocks; this is painted HD art rather than nearest-neighbor NES art.
    if((x%4||y%4)&&!frame.subarray(at,at+4).equals(frame.subarray((Math.floor(y/4)*4*size+Math.floor(x/4)*4)*4,(Math.floor(y/4)*4*size+Math.floor(x/4)*4)*4+4)))highResolutionDetails++;
   }
   assert(count>=40,'Each real action must have a complete visible soldier');poses++;
  }
  assert.equal(hashes.size,8,'Every action must retain separately drawn art');
 }
 for(let pose=0;pose<8;pose++)for(let i=0;i<size*size;i++){
  const x=i%size,y=Math.floor(i/size),at=(y*images.friendly.width+pose*size+x)*4,a=images.friendly.rgba,b=images.enemy.rgba,key=prepared[type].fitted[pose].keys[i];
  assert.equal(a[at+3],b[at+3],'Enemy colors cannot change a silhouette');
  if(!prepared[type].fitted[pose].mask[i]){assert(a.subarray(at,at+4).equals(b.subarray(at,at+4)),'Skin, metal weapons, wood and horse coat are immutable across sides');if(a[at+3])protectedPixels++;}
  else{assert(key>=builder.PALETTE.length);assert.equal(a[at+3],255);assert(a.subarray(at,at+3).equals(Buffer.from(builder.UNIFORMS.friendly[key-builder.PALETTE.length])));assert(b.subarray(at,at+3).equals(Buffer.from(builder.UNIFORMS.enemy[key-builder.PALETTE.length])));assert(!a.subarray(at,at+3).equals(b.subarray(at,at+3)));uniformPixels++;}
 }
}
assert.equal(poses,48);assert(protectedPixels>500);assert(uniformPixels>150);assert(highResolutionDetails>200,'Painted soldier poses must add detail at the actual4× asset resolution');
for(const[file,hash]of originals)assert.equal(sha(read(file)),hash,'Building/reading new soldiers cannot overwrite native art');
const outputs=fs.readdirSync(path.join(ROOT,'game/assets/battle-enhanced')).filter(p=>p.startsWith('soldiers-')).sort();
assert.deepEqual(outputs,builder.TYPES.flatMap(type=>['friendly','enemy'].map(side=>`soldiers-${type}-${side}.png`)).sort(),'Exactly the six manifest-bound soldier atlases are shipped');
const bad=JSON.parse(JSON.stringify(manifest));bad.types.infantry.friendly.frames[0].source_rect[2]=0;assert.throws(()=>builder.check(bad),/metadata|rebuild/);
console.log(`Soldiers: ${report.soldier_types}visual types/24painted poses/${poses}faction-colored4× frames; ${uniformPixels}explicit uniform-mask pixels; ${protectedPixels}skin/metal/horse pixels unchanged; complete alpha margins, original hashes and deterministic rebuild passed`);
