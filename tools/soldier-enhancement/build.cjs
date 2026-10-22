#!/usr/bin/env node
'use strict';
/* Deterministic packing of separately painted soldier actions. No game state,
 * ROM, native image, RNG or source study is modified by this module. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {decodePng,encodePng}=require('../portraits/prepare_enhanced.cjs');
const ROOT=path.resolve(__dirname,'../..'),OUT='game/assets/battle-enhanced',ART='art/soldier-enhancement-v1',TOOL='tools/soldier-enhancement/build.cjs';
const ACTIONS=Object.freeze(['idle','march','ready','attack','guard','hit','retreat','defeat']);
const TYPES=Object.freeze(['infantry','archer','cavalry']);
const LOGICAL=Object.freeze({infantry:16,archer:16,cavalry:24});
// Cyan is an explicit source-art annotation for recolorable cloth/armor only.
// Metal, wood, skin and the horse never use this annotation and stay identical.
const PALETTE=Object.freeze([[0,0,0],[25,22,20],[77,86,87],[154,166,166],[232,240,230],[255,255,255],
 [144,61,21],[222,127,53],[255,199,116],[65,29,12],[103,43,18],[158,65,0],[211,115,35]]);
const UNIFORMS=Object.freeze({friendly:[[48,52,55],[83,89,94],[128,137,140],[185,197,197],[225,234,230]],
 enemy:[[57,6,10],[110,14,19],[172,35,31],[224,70,42],[255,132,71]]});
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function read(file){const target=path.join(ROOT,file);assert(!fs.lstatSync(target).isSymbolicLink(),'Soldier sources/outputs must be ordinary files');return fs.readFileSync(target);}
function cyan(rgb){return rgb[1]>=40&&rgb[2]>=40&&rgb[1]-rgb[0]>12&&rgb[2]-rgb[0]>12;}
function paletteIndex(rgb){let index=0,best=Infinity;for(let i=0;i<PALETTE.length;i++){const distance=PALETTE[i].reduce((n,c,k)=>n+(c-rgb[k])**2,0);if(distance<best){index=i;best=distance;}}return index;}
function colorKey(rgba,at){if(cyan(rgba.subarray(at,at+3))){const light=rgba[at]*.299+rgba[at+1]*.587+rgba[at+2]*.114;return PALETTE.length+Math.min(4,Math.max(0,Math.floor((light-35)/43)));}return paletteIndex(rgba.subarray(at,at+3));}
function actionPoseImages(image){
 const{width:w,height:h,rgba}=image,seen=new Uint8Array(w*h),components=[];
 assert(w>=256&&h>=128&&w/h>1.4&&w/h<2.8,'Soldier source must be a horizontal4×2 action sheet');
 let opaque=0,transparent=0;
 for(let start=0;start<w*h;start++){
  if(rgba[start*4+3]<128){transparent++;continue;}opaque++;
  if(seen[start])continue;const pixels=[start];seen[start]=1;let left=w,top=h,right=0,bottom=0;
  for(let n=0;n<pixels.length;n++){const i=pixels[n],x=i%w,y=Math.floor(i/w);left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);
   for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=w||yy>=h)continue;const j=yy*w+xx;if(!seen[j]&&rgba[j*4+3]>=128){seen[j]=1;pixels.push(j);}}
  }
  components.push({pixels,box:[left,top,right+1,bottom+1]});
 }
 assert(transparent>opaque*.2&&opaque>w*h*.025,'Each source must contain substantial transparent gutters and painted figures');
 components.sort((a,b)=>b.pixels.length-a.pixels.length);
 assert(components.length>=8&&components[7].pixels.length>Math.max(150,w*h*.0004),'Each source must contain eight independent complete soldier figures');
 const main=components.slice(0,8).sort((a,b)=>(a.box[1]+a.box[3])-(b.box[1]+b.box[3])),ordered=[];
 for(let row=0;row<2;row++)ordered.push(...main.slice(row*4,(row+1)*4).sort((a,b)=>(a.box[0]+a.box[2])-(b.box[0]+b.box[2])));
 // Resolve small detached bowstrings, arrows, speartips and helmets to their
 // nearest figure; rectangular cells alone would cut crossing long weapons.
 const distance=(a,b)=>{const x=(a[0]+a[2])/2,y=(a[1]+a[3])/2,mx=(b[0]+b[2])/2,my=(b[1]+b[3])/2,dx=x<b[0]?b[0]-x:x>b[2]?x-b[2]:0,dy=y<b[1]?b[1]-y:y>b[3]?y-b[3]:0;return dx*dx+dy*dy+((x-mx)**2+(y-my)**2)*.001;};
 const groups=ordered.map(()=>[]);
 for(const component of components){let slot=ordered.indexOf(component);if(slot<0){let best=Infinity;for(let i=0;i<8;i++){const d=distance(component.box,ordered[i].box);if(d<best){slot=i;best=d;}}}groups[slot].push(component);}
 return groups.map((group,pose)=>{
  const left=Math.min(...group.map(c=>c.box[0])),top=Math.min(...group.map(c=>c.box[1])),right=Math.max(...group.map(c=>c.box[2])),bottom=Math.max(...group.map(c=>c.box[3]));
  assert(left>0&&top>0&&right<w&&bottom<h,`${ACTIONS[pose]} source touches the sheet edge; do not crop weapons or hooves`);
  const width=right-left+2,height=bottom-top+2,x=left-1,y=top-1,isolated=Buffer.alloc(width*height*4);let kept=0;
  for(const component of group)for(const i of component.pixels){const at=((Math.floor(i/w)-y)*width+i%w-x)*4;rgba.copy(isolated,at,i*4,i*4+4);kept++;}
  return{width,height,rgba:isolated,pose,source_rect:[x,y,width,height],painted_pixels:kept};
 });
}
function imageBounds(image){let left=image.width,top=image.height,right=-1,bottom=-1;for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++)if(image.rgba[(y*image.width+x)*4+3]>=128){left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);}assert(right>left&&bottom>top,'A complete action figure is required');return[left,top,right+1,bottom+1];}
function fittedAction(image,box,scale,size){
 const keys=new Int16Array(size*size).fill(-1),mask=new Uint8Array(size*size),[left,top,right,bottom]=box,width=Math.max(1,Math.round((right-left)*scale)),height=Math.max(1,Math.round((bottom-top)*scale)),dx=Math.floor((size-width)/2),dy=size-4-height;
 assert(dx>=4&&dy>=4&&width<=size-8&&height<=size-8,'A soldier frame must preserve its transparent weapon/foot margin');
 for(let y=0;y<height;y++)for(let x=0;x<width;x++){
  const x1=left+x*(right-left)/width,x2=left+(x+1)*(right-left)/width,y1=top+y*(bottom-top)/height,y2=top+(y+1)*(bottom-top)/height,weights=new Map();let coverage=0;
  for(let sy=Math.floor(y1);sy<Math.ceil(y2);sy++)for(let sx=Math.floor(x1);sx<Math.ceil(x2);sx++){
   const at=(sy*image.width+sx)*4;if(image.rgba[at+3]<128)continue;
   const weight=Math.max(0,Math.min(sx+1,x2)-Math.max(sx,x1))*Math.max(0,Math.min(sy+1,y2)-Math.max(sy,y1));if(!weight)continue;
   const key=colorKey(image.rgba,at);coverage+=weight;weights.set(key,(weights.get(key)||0)+weight);
  }
  // Coverage sampling retains a thin spear/arrow within a pixel footprint.
  // Selecting a palette bin avoids blur and creates actual1pixel HD details.
  if(coverage<Math.max(.01,(x2-x1)*(y2-y1)*.08))continue;
  const key=[...weights].sort((a,b)=>b[1]-a[1]||a[0]-b[0])[0][0],index=(dy+y)*size+dx+x;keys[index]=key;mask[index]=Number(key>=PALETTE.length);
 }
 assert(mask.reduce((a,b)=>a+b,0)>=4,`${ACTIONS[image.pose]} must retain the explicit cyan uniform annotation`);
 return{size,keys,mask,box:[dx,dy,dx+width,dy+height],source_box:box,scale};
}
function paint(image,side){const rgba=Buffer.alloc(image.size*image.size*4);for(let i=0;i<image.keys.length;i++){const key=image.keys[i];if(key<0)continue;const color=key>=PALETTE.length?UNIFORMS[side][key-PALETTE.length]:PALETTE[key];for(let c=0;c<3;c++)rgba[i*4+c]=color[c];rgba[i*4+3]=255;}return rgba;}
function source(type){
 const study=`${ART}/studies/${type}.png`,prompt=`${ART}/prompts/${type}.txt`,reference=`${ART}/references/${type}-gray-study.png`,materialPrompt=`${ART}/prompts/material-mask.txt`,nativeReference='game/assets/battle-original/witness-attack.png',bytes=read(study),image=decodePng(bytes),poses=actionPoseImages(image),boxes=poses.map(imageBounds),size=LOGICAL[type]*4,scale=Math.min(...boxes.map(([l,t,r,b])=>Math.min((size-8)/(r-l),(size-8)/(b-t)))),fitted=poses.map((p,i)=>fittedAction(p,boxes[i],scale,size));
 assert.equal(new Set(fitted.map(p=>sha(paint(p,'friendly')))).size,8,`${type} needs eight separately painted, visibly distinct actions`);
 return{fitted,metadata:{study,study_sha256:sha(bytes),prompt,prompt_sha256:sha(read(prompt)),gray_reference:reference,gray_reference_sha256:sha(read(reference)),material_prompt:materialPrompt,material_prompt_sha256:sha(read(materialPrompt)),native_reference:nativeReference,native_reference_sha256:sha(read(nativeReference)),imagegen_mode:'built_in',scope:'New supplemental action artwork from original visual references, not recovered native-ROM action frames',source_size:[image.width,image.height],source_grid:[4,2],source_cells:poses.map(p=>p.source_rect),source_boxes:boxes,fitted_boxes:fitted.map(p=>p.box),scale,actions:[...ACTIONS],uniform_method:'Explicit cyan/turquoise source uniform annotation; grayscale friendly/red enemy, skin/metal/horse preserved'}};
}
function prepare(){return Object.fromEntries(TYPES.map(type=>[type,source(type)]));}
function atlas(type,side,prepared){
 const size=LOGICAL[type]*4,width=size*8,height=size,rgba=Buffer.alloc(width*height*4),frames=[],uniformPixels=[];
 for(let pose=0;pose<8;pose++){const frame=paint(prepared.fitted[pose],side);for(let y=0;y<size;y++)frame.copy(rgba,(y*width+pose*size)*4,y*size*4,(y+1)*size*4);frames.push({action:ACTIONS[pose],source_rect:[pose*size,0,size,size]});uniformPixels.push(prepared.fitted[pose].mask.reduce((a,b)=>a+b,0));}
 const file=`soldiers-${type}-${side}.png`,bytes=encodePng(width,height,rgba);
 return{bytes,row:{path:`/assets/battle-enhanced/${file}`,width,height,logical_width:LOGICAL[type],logical_height:LOGICAL[type],anchor:{x:LOGICAL[type]/2,y:LOGICAL[type]},facing:'right',frames,sha256:sha(bytes),pixel_sha256:sha(rgba),uniform_pixels:uniformPixels,method:'imagegen_soldier_action_atlas_uniform_mask',study_key:type}};
}
function result(prepared){const files={},types={};for(const type of TYPES){types[type]={};for(const side of ['friendly','enemy']){const item=atlas(type,side,prepared[type]);files[item.row.path]=item.bytes;types[type][side]=item.row;}}return{files,manifest:{schema:'tk2-soldier-actions-v1',scale:4,actions:[...ACTIONS],types,studies:Object.fromEntries(TYPES.map(type=>[type,prepared[type].metadata])),palettes:{shared:PALETTE,uniforms:UNIFORMS},build:{tool:TOOL,tool_sha256:sha(read(TOOL)),source_art:'built-in imagegen, original mixed formation references retained',scope:'Presentation-only infantry/archer/cavalry actions; no new troop counts, combat rules, RNG or save fields',originals_retained:true}}};}
function build(prepared=prepare()){const built=result(prepared);for(const[file,bytes]of Object.entries(built.files)){const target=path.join(ROOT,'game',file.slice(1));fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes);}return built.manifest;}
function check(manifest){
 assert(manifest&&manifest.schema==='tk2-soldier-actions-v1');assert.equal(manifest.scale,4);assert.deepEqual(manifest.actions,[...ACTIONS]);assert.equal(manifest.build.originals_retained,true);assert.equal(manifest.build.tool_sha256,sha(read(TOOL)));assert.deepEqual(Object.keys(manifest.types).sort(),[...TYPES].sort());
 const expected=result(prepare());assert.deepEqual(manifest,expected.manifest,'Soldier metadata/source hashes must rebuild exactly');
 for(const[file,bytes]of Object.entries(expected.files)){
  const loaded=read('game'+file);assert(loaded.equals(bytes),`${file} must rebuild exactly from its retained study`);
  const image=decodePng(loaded),alpha=new Set(),colors=new Set();let painted=0;
  for(let i=0;i<image.rgba.length;i+=4){alpha.add(image.rgba[i+3]);if(image.rgba[i+3]){painted++;colors.add(image.rgba.subarray(i,i+3).toString('hex'));}}
  assert.deepEqual([...alpha].sort((a,b)=>a-b),[0,255]);assert(colors.size<=PALETTE.length+5);assert(painted>200);
  const type=file.split('/').at(-1).split('-')[1],size=LOGICAL[type]*4;
  for(let pose=0;pose<8;pose++)for(let y=0;y<size;y++)for(let x=0;x<size;x++)if(x<4||y<4||x>=size-4||y>=size-4)assert.equal(image.rgba[(y*image.width+pose*size+x)*4+3],0,'The complete figure must retain transparent margins');
 }
 return{soldier_types:3,soldier_actions:8,soldier_atlases:6,soldier_frames:48,originals_retained:true};
}
module.exports={ACTIONS,TYPES,LOGICAL,PALETTE,UNIFORMS,cyan,colorKey,actionPoseImages,imageBounds,fittedAction,paint,source,prepare,atlas,result,build,check};
if(require.main===module){try{assert(process.argv.includes('--check'),'Rebuild through node tools/battle-enhancement/build.cjs');console.log(JSON.stringify(check(JSON.parse(read(OUT+'/index.json')).soldiers)));}catch(error){console.error(error);process.exitCode=1;}}
