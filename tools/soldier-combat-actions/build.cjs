#!/usr/bin/env node
'use strict';
/* Pack supplementary original-style attack poses. The game state, native
 * stand/walk images, original manifests and imagegen studies are read-only. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {decodePng,encodePng}=require('../portraits/prepare_enhanced.cjs');
const ROOT=path.resolve(__dirname,'../..'),ART='art/soldier-combat-actions-v1',OUT='game/assets/soldier-combat-actions-v1',PREFIX='/assets/soldier-combat-actions-v1/';
const TYPES=['infantry','archer','cavalry','general'];
const ACTIONS={infantry:['melee'],archer:['melee','ranged'],cavalry:['melee'],general:['melee']};
const PHASES={melee:['ready','windup','strike','recover'],ranged:['nock','draw','release','recover']};
const COLORS={black:[0,0,0],friendly:[167,181,188],enemy:[187,45,9],peach:[255,213,203]};
const FRAME=64,ANCHOR=32,MARGIN=2;
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const jsonBytes=value=>Buffer.from(JSON.stringify(value,null,2)+'\n');
function safeRead(name){
 assert(typeof name==='string'&&!path.isAbsolute(name)&&!name.split('/').includes('..'),'Unsafe soldier-art path');
 let target=ROOT;
 for(const part of name.split('/')){target=path.join(target,part);assert(!fs.lstatSync(target).isSymbolicLink(),'Soldier source/output cannot be a symlink');}
 assert(fs.statSync(target).isFile(),'Soldier source/output must be an ordinary file');
 return fs.readFileSync(target);
}
function safeDirectory(name,create=false){
 assert(typeof name==='string'&&!path.isAbsolute(name)&&!name.split('/').includes('..'),'Unsafe soldier-art directory');
 let target=ROOT;
 for(const part of name.split('/')){
  target=path.join(target,part);
  if(!fs.existsSync(target)){assert(create,'Missing soldier-art directory');fs.mkdirSync(target);}
  assert(!fs.lstatSync(target).isSymbolicLink()&&fs.statSync(target).isDirectory(),'Soldier-art directories cannot be symlinks');
 }
 return target;
}
function colorKey(rgb){
 const[r,g,b]=rgb;
 // Cyan is accepted only as an optional material annotation. Native bluish
 // gray is not cyan and is classified with the three original opaque colors.
 if(g>=60&&b>=60&&r<Math.min(g,b)*.55)return 1;
 if(Math.max(r,g,b)-Math.min(r,g,b)<18&&Math.max(r,g,b)>65)return 1;
 const palette=[COLORS.black,COLORS.friendly,COLORS.peach];let key=0,best=Infinity;
 for(let i=0;i<palette.length;i++){const distance=palette[i].reduce((sum,c,n)=>sum+(c-rgb[n])**2,0);if(distance<best){best=distance;key=i;}}
 return key;
}
function splitFigures(image,rows){
 const{width:w,height:h,rgba}=image,expected=4*rows;
 assert(Number.isInteger(w)&&Number.isInteger(h)&&w>=64&&h>=32&&w<=4096&&h<=4096,'Unexpected source study dimensions');
 assert([1,2].includes(rows)&&rgba.length===w*h*4,'Source study geometry');
 const seen=new Uint8Array(w*h),components=[];let opaque=0;
 for(let start=0;start<w*h;start++){
  if(rgba[start*4+3]<128)continue;opaque++;
  if(seen[start])continue;
  const pixels=[start];seen[start]=1;let left=w,top=h,right=0,bottom=0;
  for(let cursor=0;cursor<pixels.length;cursor++){
   const i=pixels[cursor],x=i%w,y=Math.floor(i/w);left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);
   for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
    const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=w||yy>=h)continue;const at=yy*w+xx;
    if(!seen[at]&&rgba[at*4+3]>=128){seen[at]=1;pixels.push(at);}
   }
  }
  components.push({pixels,box:[left,top,right+1,bottom+1]});
 }
 assert(opaque>w*h*.002&&opaque<w*h*.8,'Study must contain separate opaque figures on a transparent background');
 components.sort((a,b)=>b.pixels.length-a.pixels.length);
 assert(components.length>=expected&&components[expected-1].pixels.length>=12,'Study must contain every complete independent figure');
 const main=components.slice(0,expected),ordered=[];
 if(rows===1)ordered.push(...main.sort((a,b)=>(a.box[0]+a.box[2])-(b.box[0]+b.box[2])));
 else{
  main.sort((a,b)=>(a.box[1]+a.box[3])-(b.box[1]+b.box[3]));
  for(let row=0;row<2;row++)ordered.push(...main.slice(row*4,row*4+4).sort((a,b)=>(a.box[0]+a.box[2])-(b.box[0]+b.box[2])));
 }
 const groups=ordered.map(()=>[]);
 function distance(a,b){
  const x=(a[0]+a[2])/2,y=(a[1]+a[3])/2,mx=(b[0]+b[2])/2,my=(b[1]+b[3])/2;
  const dx=x<b[0]?b[0]-x:x>b[2]?x-b[2]:0,dy=y<b[1]?b[1]-y:y>b[3]?y-b[3]:0;
  return dx*dx+dy*dy+((x-mx)**2+(y-my)**2)*.001;
 }
 for(const component of components){
  let slot=ordered.indexOf(component);
  if(slot<0){let best=Infinity;for(let i=0;i<ordered.length;i++){const score=distance(component.box,ordered[i].box);if(score<best){best=score;slot=i;}}}
  groups[slot].push(component);
 }
 return groups.map((group,index)=>{
  const box=[Math.min(...group.map(c=>c.box[0])),Math.min(...group.map(c=>c.box[1])),Math.max(...group.map(c=>c.box[2])),Math.max(...group.map(c=>c.box[3]))];
  const[left,top,right,bottom]=box;assert(left>0&&top>0&&right<w&&bottom<h,'Source figure touches study edge; do not clip weapons, arrows or hooves');
  const width=right-left,height=bottom-top,rgbaOut=Buffer.alloc(width*height*4);
  for(const component of group)for(const i of component.pixels){const at=((Math.floor(i/w)-top)*width+i%w-left)*4;rgba.copy(rgbaOut,at,i*4,i*4+4);}
  const armor=[];
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){const at=(y*width+x)*4;if(rgbaOut[at+3]>=128&&colorKey(rgbaOut.subarray(at,at+3))===1)armor.push(x+.5);}
  assert(armor.length>=4,'Every figure must retain substantial original-gray armor or weapon pixels');armor.sort((a,b)=>a-b);
  const anchorX=armor[Math.floor(armor.length/2)];
  return{width,height,rgba:rgbaOut,index,source_rect:box,anchorX};
 });
}
function fitFigures(figures){
 // Register each figure by its gray body/armor, not by a swinging weapon's
 // bounding-box center. Sample directly onto the 64px output: compressing back
 // to 16px first erases bowstrings, blade tips, hands and facial outlines.
 const half=ANCHOR-MARGIN,scale=Math.min(...figures.map(p=>Math.min(half/Math.max(.5,p.anchorX),half/Math.max(.5,p.width-p.anchorX),(FRAME-MARGIN*2)/p.height)));
 const fitted=figures.map(p=>{
  const keys=new Int8Array(FRAME*FRAME).fill(-1),width=Math.max(1,Math.round(p.width*scale)),height=Math.max(1,Math.round(p.height*scale));
  const dx=ANCHOR-Math.round(p.anchorX*scale),dy=FRAME-MARGIN-height;
  assert(dx>=0&&dy>=0&&dx+width<=FRAME&&dy+height<=FRAME,'Complete action must fit its 64px canvas');
  for(let y=0;y<height;y++)for(let x=0;x<width;x++){
   const x1=x*p.width/width,x2=(x+1)*p.width/width,y1=y*p.height/height,y2=(y+1)*p.height/height;
   const weights=[0,0,0];let coverage=0;
   for(let sy=Math.floor(y1);sy<Math.ceil(y2);sy++)for(let sx=Math.floor(x1);sx<Math.ceil(x2);sx++){
    const at=(sy*p.width+sx)*4;if(p.rgba[at+3]<128)continue;
    const weight=Math.max(0,Math.min(sx+1,x2)-Math.max(sx,x1))*Math.max(0,Math.min(sy+1,y2)-Math.max(sy,y1));
    if(!weight)continue;coverage+=weight;weights[colorKey(p.rgba.subarray(at,at+3))]+=weight;
   }
   // Coverage sampling retains a narrow bowstring/shaft, then writes one of
   // the three original colors with hard alpha. No new poses are invented.
   if(coverage<Math.max(.005,(x2-x1)*(y2-y1)*.07))continue;
   let key=0;for(let k=1;k<3;k++)if(weights[k]>weights[key])key=k;
   keys[(y+dy)*FRAME+x+dx]=key;
  }
  assert([...keys].filter(k=>k>=0).length>=12&&keys.includes(1),'A complete visible figure must survive 64px sampling');
  return{keys,box:[dx,dy,dx+width,dy+height],source_rect:p.source_rect};
 });
 return{frames:fitted,scale};
}
function validateFrame(keys){
 assert(keys.length===FRAME*FRAME,'Combat frames are 64px, not a repeated native block');
 const seen=new Uint8Array(keys.length);let opaque=0,largest=0;
 for(let i=0;i<keys.length;i++){
  assert([-1,0,1,2].includes(keys[i]),'Only the three original material colors may be packed');
  if(keys[i]<0)continue;opaque++;
  const x=i%FRAME,y=Math.floor(i/FRAME);assert(x>0&&y>0&&x<FRAME-1&&y<FRAME-1,'Weapon tips and hooves require a transparent margin');
  if(seen[i])continue;const queue=[i];seen[i]=1;
  for(let n=0;n<queue.length;n++){
   const at=queue[n],xx=at%FRAME,yy=Math.floor(at/FRAME);
   for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
    const x2=xx+dx,y2=yy+dy;if(x2<0||y2<0||x2>=FRAME||y2>=FRAME)continue;const next=y2*FRAME+x2;
    if(!seen[next]&&keys[next]>=0){seen[next]=1;queue.push(next);}
   }
  }
  largest=Math.max(largest,queue.length);
 }
 assert(opaque>=96&&largest>=opaque*.7,'The complete figure must remain visible and connected after sampling');
 assert(keys.includes(0)&&keys.includes(1)&&keys.includes(2),'The figure must retain black outlines, original uniform gray and skin/horse');
 return opaque;
}
function rgbaFrame(keys,side){
 validateFrame(keys);
 const palette=[COLORS.black,COLORS[side],COLORS.peach],rgba=Buffer.alloc(FRAME*FRAME*4);
 for(let i=0;i<keys.length;i++){const key=keys[i];if(key<0)continue;const at=i*4;for(let c=0;c<3;c++)rgba[at+c]=palette[key][c];rgba[at+3]=255;}
 return rgba;
}
function packAction(type,action,side,frames){
 assert(ACTIONS[type].includes(action)&&frames.length===4,'Unknown action pack');
 const rgba=Buffer.alloc(256*FRAME*4),hashes=[];
 for(let i=0;i<4;i++){
  const frame=rgbaFrame(frames[i].keys,side);hashes.push(sha(frame));
  for(let y=0;y<FRAME;y++)frame.copy(rgba,(y*256+i*FRAME)*4,y*FRAME*4,(y+1)*FRAME*4);
 }
 assert(new Set(hashes).size===4,`${type}/${action} needs four visibly different poses`);
 for(let i=0;i<4;i++)for(let j=i+1;j<4;j++){
  let differences=0;for(let p=0;p<FRAME*FRAME;p++)if(frames[i].keys[p]!==frames[j].keys[p])differences++;
  assert(differences>=12,`${type}/${action} needs visibly articulated poses, not single-pixel variants`);
 }
 const bytes=encodePng(256,64,rgba),name=`${type}-${action}-${side}.png`;
 return{bytes,row:{path:PREFIX+name,width:256,height:64,facing:'right',anchor:{x:8,y:16},
  frames:PHASES[action].map((phase,i)=>({phase,source_rect:[i*64,0,64,64]})),
  sha256:sha(bytes),pixel_sha256:sha(rgba),frame_pixel_sha256:hashes}};
}
function prepare(){
 const prepared={},sources={};
 for(const type of TYPES){
  const study=`${ART}/studies/${type}.png`,prompt=`${ART}/prompts/${type}.txt`,reference=`${ART}/references/${type}-native-gray.png`;
  const bytes=safeRead(study),image=decodePng(bytes),figures=splitFigures(image,type==='archer'?2:1),fitted=fitFigures(figures);
  prepared[type]={};
  if(type==='archer'){prepared[type].ranged=fitted.frames.slice(0,4);prepared[type].melee=fitted.frames.slice(4,8);}
  else prepared[type].melee=fitted.frames;
  sources[type]={study,study_sha256:sha(bytes),prompt,prompt_sha256:sha(safeRead(prompt)),reference,reference_sha256:sha(safeRead(reference)),
   source_size:[image.width,image.height],source_rect_format:'left,top,right,bottom',source_grid:[4,type==='archer'?2:1],source_rects:figures.map(p=>p.source_rect),
   fitted_boxes:fitted.frames.map(p=>p.box),shared_scale:fitted.scale,
   source_order:type==='archer'?['ranged:nock','ranged:draw','ranged:release','ranged:recover','melee:ready','melee:windup','melee:strike','melee:recover']:PHASES.melee.map(phase=>'melee:'+phase)};
 }
 return{prepared,sources};
}
function result(input=prepare()){
 const files={},types={};
 for(const type of TYPES){types[type]={};for(const action of ACTIONS[type]){types[type][action]={};for(const side of ['friendly','enemy']){
  const packed=packAction(type,action,side,input.prepared[type][action]);types[type][action][side]=packed.row;files[packed.row.path]=packed.bytes;
 }}}
 const originals={};
 for(const type of TYPES)for(const side of ['friendly','enemy'])for(const suffix of ['0','move-0','move-1']){
  const file=`game/assets/siege-original/sprite-${type}-${side}-${suffix}.png`;originals[file]=sha(safeRead(file));
 }
 const provenance={schema:'tk2-soldier-combat-actions-provenance-v1',source_kind:'supplementary-imagegen-pixel-art',imagegen_mode:'built_in',
  scope:'New four-frame attack poses referenced from retained original stand/walk figures. Not recovered native-ROM attack frames.',
  originals_retained:true,original_files:originals,reference_frame_count:2,reference_frames:'retained native walking poses; not a claim that native attacks had two body frames',
  logical_canvas:[16,16],output_frame:[64,64],resolution_scale:4,rendering:'direct 64px coverage sampling with three original palette colors and hard alpha; not a 4x repetition of native pixels',
  palette_policy:'All original gray pixels, including weapons/armor, become gray for the friendly palette and red for the enemy palette. Skin/horse, black and alpha are identical across sides.',
  palettes:{friendly:[COLORS.black,COLORS.friendly,COLORS.peach],enemy:[COLORS.black,COLORS.enemy,COLORS.peach]},
  sources:input.sources,build:{tool:'tools/soldier-combat-actions/build.cjs',tool_sha256:sha(safeRead('tools/soldier-combat-actions/build.cjs'))}};
 const proofBytes=jsonBytes(provenance);files[PREFIX+'provenance.json']=proofBytes;
 const manifest={schema:'tk2-soldier-combat-actions-v1',scale:4,logical_size:[16,16],frame_size:[64,64],frames_per_action:4,
  types,provenance:{path:PREFIX+'provenance.json',sha256:sha(proofBytes)},originals_retained:true};
 files[PREFIX+'index.json']=jsonBytes(manifest);return{files,manifest,provenance};
}
function write(){
 const built=result();safeDirectory(OUT,true);
 for(const[url,bytes]of Object.entries(built.files)){
  const target=path.join(ROOT,'game',url.slice(1));assert(!fs.existsSync(target)||!fs.lstatSync(target).isSymbolicLink(),'Output cannot be a symlink');fs.writeFileSync(target,bytes);
 }
 return built.manifest;
}
function check(){
 const built=result(),folder=safeDirectory(OUT),names=Object.keys(built.files).map(p=>path.basename(p)).sort();
 assert.deepEqual(fs.readdirSync(folder).sort(),names,'Only reviewed combat action files may ship');
 for(const[url,expected]of Object.entries(built.files))assert(safeRead('game'+url).equals(expected),url+' must rebuild exactly');
 for(const type of TYPES)for(const action of ACTIONS[type]){
  const left=decodePng(built.files[built.manifest.types[type][action].friendly.path]),right=decodePng(built.files[built.manifest.types[type][action].enemy.path]);
  assert.equal(left.width,256);assert.equal(left.height,64);assert.equal(right.width,256);assert.equal(right.height,64);
  for(let y=0;y<64;y++)for(let x=0;x<256;x++){
   const at=(y*256+x)*4;
   assert.equal(left.rgba[at+3],right.rgba[at+3]);assert([0,255].includes(left.rgba[at+3]));
   if(!left.rgba[at+3])continue;
   const rgb=[...left.rgba.subarray(at,at+3)],enemy=[...right.rgba.subarray(at,at+3)];
   if(rgb.every((v,i)=>v===COLORS.friendly[i]))assert.deepEqual(enemy,COLORS.enemy);
   else{assert(rgb.every((v,i)=>v===COLORS.black[i])||rgb.every((v,i)=>v===COLORS.peach[i]));assert.deepEqual(enemy,rgb);}
  }
 }
 return{types:4,actions:5,frames_per_action:4,atlases:10,frames:40,frame_size:[64,64],resolution_scale:4,hard_alpha:true,palette_colors:3,originals_retained:true};
}
module.exports={ROOT,ART,OUT,PREFIX,TYPES,ACTIONS,PHASES,COLORS,sha,safeRead,safeDirectory,colorKey,splitFigures,fitFigures,validateFrame,rgbaFrame,packAction,prepare,result,write,check};
if(require.main===module){try{assert(process.argv.includes('--check')||process.argv.includes('--write'),'Use --write or --check explicitly');if(process.argv.includes('--write'))write();console.log(JSON.stringify(check()));}catch(error){console.error(error);process.exitCode=1;}}
