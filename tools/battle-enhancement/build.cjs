#!/usr/bin/env node
'use strict';
/* Offline, deterministic packing of imagegen-painted weapon/horse sprites.
 * Native pixels remain separate; originals are read and hash-checked only. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {decodePng,encodePng,scale2x}=require('../portraits/prepare_enhanced.cjs');
const {WEAPONS,HORSES}=require('../../game/duel-appearance.js');
const ROOT=path.resolve(__dirname,'../..'),OUT='game/assets/battle-enhanced',ART='art/battle-enhancement-v1',ACTION_ART='art/battle-enhancement-v2',TOOL='tools/battle-enhancement/build.cjs';
// The approved v1 two-pose files are immutable; expansion must not regenerate
// a larger legacy Cartesian product just because the public registry grows.
const LEGACY_WEAPONS=Object.freeze(['spear','serpent-spear','guandao','halberd','sword','dual-swords','axe','dual-axes','dual-ji']);
const LEGACY_HORSES=Object.freeze(['chestnut','white','black','red-hare','dilu']);
const ACTIONS=Object.freeze(['idle','strike','guard','feint','withdraw','desperate','hit','defeat']);
const ACTION_FRAME_WIDTH=512,ACTION_FRAME_HEIGHT=384;
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),read=p=>fs.readFileSync(path.join(ROOT,p)),json=p=>JSON.parse(read(p));
const PALETTE=[[0,0,0],[66,30,15],[103,43,18],[145,62,21],[186,86,29],[222,127,53],[247,162,71],[255,199,116],[255,226,168],[255,244,211],[255,255,255],[57,60,60],[100,105,104],[151,155,151],[203,207,197],[128,19,21],[208,49,32],[52,92,40],[90,143,56],[40,62,103]];
function write(name,bytes){const target=path.join(ROOT,OUT,name);fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes);return bytes;}
function native4x(image){
 assert.equal(new Uint8Array(new Uint32Array([0x01020304]).buffer)[0],4,'Pixel packing requires a little-endian Node runtime');
 const values=Uint32Array.from({length:image.width*image.height},(_,i)=>image.rgba.readUInt32LE(i*4));
 return Buffer.from(scale2x(scale2x(values,image.width,image.height),image.width*2,image.height*2).buffer);
}
function nearest4x(image){
 const width=image.width*4,height=image.height*4,rgba=Buffer.alloc(width*height*4);
 for(let y=0;y<height;y++)for(let x=0;x<width;x++){
  const src=(Math.floor(y/4)*image.width+Math.floor(x/4))*4,at=(y*width+x)*4;
  image.rgba.copy(rgba,at,src,src+4);
 }
 return rgba;
}
function nativeEntry(row,{nearest=false}={}){
 const sourcePath='game'+row.path,source=read(sourcePath),image=decodePng(source),rgba=(nearest?nearest4x:native4x)(image),width=image.width*4,height=image.height*4;
 const name='native-'+path.basename(row.path),bytes=write(name,encodePng(width,height,rgba));
 return {path:'/assets/battle-enhanced/'+name,width,height,logical_width:image.width,logical_height:image.height,anchor:row.anchor||{x:image.width/2,y:image.height},sha256:sha(bytes),pixel_sha256:sha(rgba),source_path:row.path,source_sha256:sha(source),method:nearest?'native_nearest4x':'native_scale4x'};
}
function poseImages(image){
 // The riders are separate transparent islands. Their bounding rectangles can
 // overlap inx (long weapon over the other horse's tail), so a50/50 sheet crop
 // would cut actual art. Trace connected painted islands instead.
 const {width:w,height:h,rgba}=image,seen=new Uint8Array(w*h),components=[];
 for(let start=0;start<w*h;start++){
  if(seen[start]||rgba[start*4+3]<128)continue;const queue=[start];seen[start]=1;let x1=w,y1=h,x2=0,y2=0;
  for(let k=0;k<queue.length;k++){const i=queue[k],x=i%w,y=Math.floor(i/w);x1=Math.min(x1,x);x2=Math.max(x2,x);y1=Math.min(y1,y);y2=Math.max(y2,y);
   for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const xx=x+dx,yy=y+dy;if(xx<0||xx>=w||yy<0||yy>=h)continue;const j=yy*w+xx;if(!seen[j]&&rgba[j*4+3]>=128){seen[j]=1;queue.push(j);}}
  }
  if(queue.length>=12)components.push({pixels:queue,box:[x1,y1,x2+1,y2+1]});
 }
 components.sort((a,b)=>b.pixels.length-a.pixels.length);assert(components.length>=2&&components[1].pixels.length>10000,'Source sheet must contain two separate complete mounted riders');
 const main=components.slice(0,2).sort((a,b)=>a.box[0]-b.box[0]),out=main.map((_,pose)=>({width:w,height:h,rgba:Buffer.alloc(rgba.length),pose}));
 const distance=(a,b)=>{const ax=(a[0]+a[2])/2,ay=(a[1]+a[3])/2,dx=ax< b[0]?b[0]-ax:ax>b[2]?ax-b[2]:0,dy=ay<b[1]?b[1]-ay:ay>b[3]?ay-b[3]:0;return dx*dx+dy*dy+Math.abs(ax-(b[0]+b[2])/2)*.01;};
 for(const component of components){let slot=main.indexOf(component);if(slot<0)slot=distance(component.box,main[0].box)<=distance(component.box,main[1].box)?0:1;
  for(const i of component.pixels)rgba.copy(out[slot].rgba,i*4,i*4,i*4+4);
 }
 return out;
}
function imageBounds(image){
 let x1=image.width,y1=image.height,x2=-1,y2=-1,count=0;
 for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++)if(image.rgba[(y*image.width+x)*4+3]>=128){x1=Math.min(x1,x);x2=Math.max(x2,x);y1=Math.min(y1,y);y2=Math.max(y2,y);count++;}
 assert(count>500&&x2>x1&&y2>y1,'Each transparent sheet half must contain a complete mounted rider');
 return [x1,y1,x2+1,y2+1];
}
function bounds(image,which){return imageBounds(poseImages(image)[which]);}
function nearest(rgb){let best=0,distance=Infinity;for(let k=0;k<PALETTE.length;k++){const d=PALETTE[k].reduce((sum,v,c)=>sum+(v-rgb[c])**2,0);if(d<distance){best=k;distance=d;}}return best;}
function fitted(image,box,scale){
 const rgba=Buffer.alloc(384*384*4),[left,top,right,bottom]=box,w=Math.round((right-left)*scale),h=Math.round((bottom-top)*scale),dx=Math.floor((384-w)/2),dy=384-h;
 assert(dx>=0&&dy>=0&&w>100&&h>100);
 // Two real output pixels per art pixel keep the NES pixel edge, while the
 // source study supplies more shape detail than a repeated native96px frame.
 for(let y=0;y<h;y+=2)for(let x=0;x<w;x+=2){
  const sx=Math.min(right-1,left+Math.floor((x+.5)/scale)),sy=Math.min(bottom-1,top+Math.floor((y+.5)/scale)),src=(sy*image.width+sx)*4;
  if(image.rgba[src+3]<128)continue;const color=PALETTE[nearest(image.rgba.subarray(src,src+3))];
  for(let yy=0;yy<2&&y+yy<h;yy++)for(let xx=0;xx<2&&x+xx<w;xx++){const at=((dy+y+yy)*384+dx+x+xx)*4;for(let c=0;c<3;c++)rgba[at+c]=color[c];rgba[at+3]=255;}
 }
 // These annotations protect only the upper rider/gauntlets in the approved
 // two-pose art layout. The horse's upper rump starts below this source area.
 const annotated=[[240,120,590,450],[1000,140,1390,440]][image.pose];
 const riderSourceRect=annotated?annotated.map((n,i)=>n*(i%2===0?image.width/1774:image.height/887)):null;
 return {rgba,box:[dx,dy,dx+w,dy+h],source_box:box,scale,rider_source_rect:riderSourceRect};
}
function horseMask(image){
 const {rgba,box}=image,w=384,h=384,minY=box[1]+Math.floor((box[3]-box[1])*.25),mask=new Uint8Array(w*h),seen=new Uint8Array(w*h),components=[];
 const warm=i=>{const at=i*4,r=rgba[at],g=rgba[at+1],b=rgba[at+2];return rgba[at+3]&&r>65&&r<=222&&g/r>=.32&&r-g>22&&g-b>4;};
 for(let y=minY;y<h;y++)for(let x=0;x<w;x++){
  const start=y*w+x;if(seen[start]||!warm(start))continue;const queue=[start];seen[start]=1;let x1=x,x2=x,y1=y,y2=y;
  for(let k=0;k<queue.length;k++){const i=queue[k],xx=i%w,yy=Math.floor(i/w);x1=Math.min(x1,xx);x2=Math.max(x2,xx);y1=Math.min(y1,yy);y2=Math.max(y2,yy);
   for(const j of[xx>0?i-1:-1,xx<w-1?i+1:-1,yy>minY?i-w:-1,yy<h-1?i+w:-1])if(j>=0&&!seen[j]&&warm(j)){seen[j]=1;queue.push(j);}
  }
  components.push({pixels:queue,box:[x1,y1,x2,y2]});
 }
 // Exclude thin wooden weapon shafts; the large warm horse patches remain.
 for(const component of components){
  const[x1,y1,x2,y2]=component.box;
  let protectedRider=false;
  if(image.rider_source_rect){
   const[l,t,r,b]=image.rider_source_rect,sx=image.source_box[0]+(x1-box[0]+.5)/image.scale,sy=image.source_box[1]+(y1-box[1]+.5)/image.scale,sr=image.source_box[0]+(x2-box[0]+.5)/image.scale,sb=image.source_box[1]+(y2-box[1]+.5)/image.scale;
   // Protect a complete leather patch within the rider annotation, rather
   // than cutting a rectangle out of a larger horse-neck/body component.
   protectedRider=sx>=l&&sy>=t&&sr<r&&sb<b;
  }
  if(component.pixels.length<128||(x2-x1<9&&y2-y1>40)||protectedRider)continue;
  for(const i of component.pixels)mask[i]=1;
 }
 assert(mask.reduce((a,b)=>a+b,0)>500,'Horse coat mask must cover a substantive painted horse region');return mask;
}
const COATS={
 chestnut:[[66,30,15],[103,43,18],[145,62,21],[186,86,29],[222,127,53],[247,162,71]],
 white:[[169,177,175],[220,225,216],[245,245,226],[255,251,235],[255,255,255],[255,255,255]],
 black:[[20,24,29],[47,53,61],[65,72,81],[85,92,101],[105,112,119],[132,139,145]],
 'red-hare':[[67,13,12],[105,20,15],[145,33,18],[190,51,24],[225,78,31],[247,126,49]],
 dilu:[[169,177,175],[220,225,216],[245,245,226],[255,251,235],[255,255,255],[255,255,255]]
};
function recolor(image,mask,horse){
 const rgba=Buffer.from(image.rgba),ramp=COATS[horse];let changed=0;
 for(let i=0;i<mask.length;i++)if(mask[i]){const at=i*4,luma=rgba[at]*.299+rgba[at+1]*.587+rgba[at+2]*.114,index=Math.min(5,Math.max(0,Math.floor((luma-30)/32))),color=ramp[index];for(let c=0;c<3;c++){changed+=Number(rgba[at+c]!==color[c]);rgba[at+c]=color[c];}}
 return {rgba,changed};
}
// Named coats are presentation palettes, not claims about an ancient horse's
// documented hair color. These ramps deliberately remain distinguishable.
const ACTION_COATS={...COATS,
 dilu:[[170,168,155],[216,213,193],[239,236,216],[250,247,226],[255,252,235],[255,255,245]],
 jueying:[[12,15,23],[25,29,43],[43,48,65],[60,67,87],[80,87,108],[108,115,137]],
 'zhuahuang-feidian':[[94,61,22],[143,97,31],[186,134,47],[220,171,72],[242,207,117],[255,234,170]],
 huiying:[[43,53,65],[69,83,99],[94,111,128],[124,141,157],[160,175,186],[200,212,219]],
 liaoyuanhuo:[[89,23,12],[135,39,13],[180,64,16],[217,92,23],[244,128,37],[255,173,74]],
 lifeisha:[[88,62,35],[128,94,49],[169,131,70],[202,164,96],[226,195,133],[246,223,173]],
 kuaihang:[[43,24,18],[73,39,26],[105,59,37],[138,82,49],[172,111,69],[204,148,100]],
 jingfan:[[38,43,43],[63,71,69],[92,104,97],[125,137,127],[162,174,161],[204,214,200]],
 'zhaoye-yushizi':[[168,185,195],[200,216,222],[225,235,238],[242,247,247],[252,254,253],[255,255,255]]
};
function actionGrid(image){const columns=image.width>=image.height?4:2;return {columns,rows:8/columns};}
function actionPoseImages(image){
 // Treat the grid as an ordering guide, not a destructive crop. A complete
 // horse tail, spear or arrow can project across the nominal cell boundary.
 const {columns}=actionGrid(image),w=image.width,h=image.height,seen=new Uint8Array(w*h),components=[];
 for(let start=0;start<w*h;start++){
  if(seen[start]||image.rgba[start*4+3]<128)continue;
  const pixels=[start];seen[start]=1;let left=w,top=h,right=0,bottom=0;
  for(let k=0;k<pixels.length;k++){
   const i=pixels[k],x=i%w,y=Math.floor(i/w);left=Math.min(left,x);right=Math.max(right,x);top=Math.min(top,y);bottom=Math.max(bottom,y);
   for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){
    const xx=x+dx,yy=y+dy;if(xx<0||yy<0||xx>=w||yy>=h)continue;const j=yy*w+xx;
    if(!seen[j]&&image.rgba[j*4+3]>=128){seen[j]=1;pixels.push(j);}
   }
  }
  if(pixels.length>=2)components.push({pixels,box:[left,top,right+1,bottom+1]});
 }
 components.sort((a,b)=>b.pixels.length-a.pixels.length);
 assert(components.length>=8&&components[7].pixels.length>5000,'An action source must contain eight separate complete mounted figures');
 const main=components.slice(0,8).sort((a,b)=>(a.box[1]+a.box[3])-(b.box[1]+b.box[3])),ordered=[];
 for(let row=0;row<8/columns;row++)ordered.push(...main.slice(row*columns,(row+1)*columns).sort((a,b)=>(a.box[0]+a.box[2])-(b.box[0]+b.box[2])));
 const groups=ordered.map(()=>[]),distance=(box,mainBox)=>{
  const x=(box[0]+box[2])/2,y=(box[1]+box[3])/2,mx=(mainBox[0]+mainBox[2])/2,my=(mainBox[1]+mainBox[3])/2;
  const dx=x<mainBox[0]?mainBox[0]-x:x>mainBox[2]?x-mainBox[2]:0,dy=y<mainBox[1]?mainBox[1]-y:y>mainBox[3]?y-mainBox[3]:0;
  return dx*dx+dy*dy+((x-mx)**2+(y-my)**2)*.001;
 };
 for(const component of components){
  let index=ordered.indexOf(component);
  if(index<0){let best=Infinity;for(let pose=0;pose<8;pose++){const next=distance(component.box,ordered[pose].box);if(next<best){best=next;index=pose;}}}
  groups[index].push(component);
 }
 return groups.map((group,pose)=>{
  const left=Math.min(...group.map(c=>c.box[0])),top=Math.min(...group.map(c=>c.box[1])),right=Math.max(...group.map(c=>c.box[2])),bottom=Math.max(...group.map(c=>c.box[3]));
  assert(left>0&&top>0&&right<w&&bottom<h,`Action ${ACTIONS[pose]} must retain complete weapons/hooves inside the source sheet`);
  const originX=left-1,originY=top-1,width=right-left+2,height=bottom-top+2,rgba=Buffer.alloc(width*height*4);let retained=0;
  for(const component of group)for(const i of component.pixels){const at=((Math.floor(i/w)-originY)*width+i%w-originX)*4;image.rgba.copy(rgba,at,i*4,i*4+4);retained++;}
  return {width,height,rgba,pose,source_rect:[originX,originY,width,height],retained_pixels:retained};
 });
}
function cyanCoat(rgb){return rgb[1]>=40&&rgb[2]>=40&&rgb[1]-rgb[0]>12&&rgb[2]-rgb[0]>12;}
function fittedAction(image,box,scale){
 const rgba=Buffer.alloc(ACTION_FRAME_WIDTH*ACTION_FRAME_HEIGHT*4),mask=new Uint8Array(ACTION_FRAME_WIDTH*ACTION_FRAME_HEIGHT),levels=new Uint8Array(ACTION_FRAME_WIDTH*ACTION_FRAME_HEIGHT),[left,top,right,bottom]=box,w=Math.round((right-left)*scale),h=Math.round((bottom-top)*scale),dx=Math.floor((ACTION_FRAME_WIDTH-w)/2),dy=ACTION_FRAME_HEIGHT-16-h;
 assert(dx>=0&&dy>=0&&w>60&&h>60,'Each action must contain a full mounted figure');
 for(let y=0;y<h;y+=2)for(let x=0;x<w;x+=2){
  const sx=Math.min(right-1,left+Math.floor((x+.5)/scale)),sy=Math.min(bottom-1,top+Math.floor((y+.5)/scale)),src=(sy*image.width+sx)*4;
  if(image.rgba[src+3]<128)continue;
  const rgb=image.rgba.subarray(src,src+3),coat=cyanCoat(rgb),color=PALETTE[nearest(rgb)],luma=rgb[0]*.299+rgb[1]*.587+rgb[2]*.114,level=Math.min(5,Math.max(0,Math.floor((luma-30)/32)));
  for(let yy=0;yy<2&&y+yy<h;yy++)for(let xx=0;xx<2&&x+xx<w;xx++){
   const i=(dy+y+yy)*ACTION_FRAME_WIDTH+dx+x+xx,at=i*4;
   for(let c=0;c<3;c++)rgba[at+c]=color[c];rgba[at+3]=255;
   if(coat){mask[i]=1;levels[i]=level;}
  }
 }
 assert(mask.reduce((a,b)=>a+b,0)>500,`Action ${ACTIONS[image.pose]} must have an explicit cyan horse-coat layer`);
 return {rgba,mask,levels,box:[dx,dy,dx+w,dy+h],source_box:box,scale};
}
function recolorAction(image,horse){
 const ramp=ACTION_COATS[horse];assert(ramp,`No presentation coat palette for ${horse}`);
 const rgba=Buffer.from(image.rgba);
 for(let i=0;i<image.mask.length;i++)if(image.mask[i])for(let c=0;c<3;c++)rgba[i*4+c]=ramp[image.levels[i]][c];
 return rgba;
}
function actionSource(weapon){
 const study=ACTION_ART+'/studies/'+weapon+'.png',prompt=ACTION_ART+'/prompts/'+weapon+'.txt',input=read(study),image=decodePng(input),poses=actionPoseImages(image),boxes=poses.map(imageBounds),scale=Math.min(...boxes.map(([l,t,r,b])=>Math.min(448/(r-l),352/(b-t))));
 const fitted=poses.map((pose,index)=>fittedAction(pose,boxes[index],scale));
 assert.equal(new Set(fitted.map(pose=>sha(pose.rgba))).size,ACTIONS.length,`${weapon} must contain eight independently drawn actions`);
 return {fitted,metadata:{study,study_sha256:sha(input),prompt,prompt_sha256:sha(read(prompt)),source_size:[image.width,image.height],source_grid:actionGrid(image),source_cells:poses.map(p=>p.source_rect),source_boxes:boxes,actions:[...ACTIONS],coat_method:'Explicit cyan/turquoise horse-coat region; rider and weapon use no cyan'}};
}
function actionAtlasEntry(weapon,horse,source){
 const width=ACTION_FRAME_WIDTH*ACTIONS.length,height=ACTION_FRAME_HEIGHT,rgba=Buffer.alloc(width*height*4),frames=[];let maskPixels=0;
 for(let pose=0;pose<ACTIONS.length;pose++){
  const image=source.fitted[pose],painted=recolorAction(image,horse);maskPixels+=image.mask.reduce((a,b)=>a+b,0);
  for(let y=0;y<ACTION_FRAME_HEIGHT;y++)painted.copy(rgba,(y*width+pose*ACTION_FRAME_WIDTH)*4,y*ACTION_FRAME_WIDTH*4,(y+1)*ACTION_FRAME_WIDTH*4);
  frames.push({action:ACTIONS[pose],source_rect:[pose*ACTION_FRAME_WIDTH,0,ACTION_FRAME_WIDTH,ACTION_FRAME_HEIGHT]});
 }
 const name=`duel-actions-${weapon}-${horse}.png`,bytes=write(name,encodePng(width,height,rgba));
 return {path:'/assets/battle-enhanced/'+name,width,height,logical_width:128,logical_height:96,anchor:{x:64,y:96},sha256:sha(bytes),pixel_sha256:sha(rgba),horse_mask_pixels:maskPixels,frames,method:'imagegen_action_atlas_cyan_coat_mask',study_key:weapon};
}
function build(){
 // Validate the complete new source set before writing any runtime asset.
 const actionSources=Object.fromEntries(WEAPONS.map(weapon=>[weapon,actionSource(weapon)])),actionAtlases={},actionStudies={};
 const originalPath='game/assets/battle-original/index.json',original=json(originalPath),backgrounds={},sprites={},duelists={},studies={};
 for(const[key,row]of Object.entries(original.backgrounds))backgrounds[key]=nativeEntry(row);
 for(const[key,row]of Object.entries(original.sprites))sprites[key]={facing:row.facing,frames:row.frames.map(frame=>nativeEntry(frame,{nearest:key.startsWith('attack_formation')}))};
 for(const weapon of LEGACY_WEAPONS){
  const study=ART+'/studies/'+weapon+'.png',prompt=ART+'/prompts/'+weapon+'.txt',input=read(study),image=decodePng(input),poses=poseImages(image),boxes=poses.map(imageBounds),scale=Math.min(...boxes.map(([l,t,r,b])=>Math.min(320/(r-l),352/(b-t))));
  assert(new Set(image.rgba.filter((_,i)=>i%4===3)).size>1,'Generated source must actually retain a transparent background');
  studies[weapon]={study,study_sha256:sha(input),prompt,prompt_sha256:sha(read(prompt)),source_size:[image.width,image.height],source_boxes:boxes};duelists[weapon]={};
  const fittedFrames=boxes.map((box,index)=>fitted(poses[index],box,scale)),masks=fittedFrames.map(horseMask);
  for(const horse of LEGACY_HORSES){const frames=[];
   for(let pose=0;pose<2;pose++){
    const rendered=recolor(fittedFrames[pose],masks[pose],horse),name=`duel-${weapon}-${horse}-${String(pose).padStart(2,'0')}.png`,bytes=write(name,encodePng(384,384,rendered.rgba));
    frames.push({path:'/assets/battle-enhanced/'+name,width:384,height:384,logical_width:96,logical_height:96,anchor:{x:48,y:96},sha256:sha(bytes),pixel_sha256:sha(rendered.rgba),method:'imagegen_painted_sprite_pixel_fit_coat_mask',study_key:weapon,pose,horse_mask_pixels:masks[pose].reduce((a,b)=>a+b,0)});
   }
   duelists[weapon][horse]={facing:'right',frames};
  }
 }
 for(const weapon of WEAPONS){
  actionStudies[weapon]=actionSources[weapon].metadata;actionAtlases[weapon]={};
  for(const horse of HORSES)actionAtlases[weapon][horse]=actionAtlasEntry(weapon,horse,actionSources[weapon]);
 }
 const manifest={schema:'tk2-battle-enhanced-v1',scale:4,originals_retained:true,logical_resolution:{width:256,height:240},resolution:{width:1024,height:960},build:{tool:TOOL,tool_sha256:sha(read(TOOL)),native_index:originalPath,native_index_sha256:sha(read(originalPath)),imagegen_mode:'built_in',native_method:'Scale2x twice for existing native cutouts; exact nearest4x for complete attack formations, retaining original palette and originals',duel_method:'Approved v1 two-pose files retained; eight separately imagegen-painted actions per weapon, explicit cyan horse-coat mask, offline named palettes; lazy runtime action-atlas loading, no new battle stats or RNG'},studies,backgrounds,sprites,duelists,actions:[...ACTIONS],action_studies:actionStudies,action_atlases:actionAtlases,horse_palettes:ACTION_COATS};
 write('index.json',Buffer.from(JSON.stringify(manifest,null,2)+'\n'));return check();
}
function entries(manifest){return [...Object.values(manifest.backgrounds),...Object.values(manifest.sprites).flatMap(row=>row.frames),...Object.values(manifest.duelists).flatMap(rows=>Object.values(rows).flatMap(row=>row.frames))];}
function atlasEntries(manifest){return Object.values(manifest.action_atlases).flatMap(rows=>Object.values(rows));}
function frameHasMargin(image,rect,margin=8){
 const[left,top,width,height]=rect;
 for(let y=0;y<height;y++){
  if(y<margin||y>=height-margin){for(let x=0;x<width;x++)if(image.rgba[((top+y)*image.width+left+x)*4+3])return false;}
  else for(let x=0;x<margin;x++)if(image.rgba[((top+y)*image.width+left+x)*4+3]||image.rgba[((top+y)*image.width+left+width-1-x)*4+3])return false;
 }
 return true;
}
function check(){
 const m=json(OUT+'/index.json');assert.equal(m.schema,'tk2-battle-enhanced-v1');assert.equal(m.scale,4);assert.equal(m.originals_retained,true);assert.equal(m.build.tool_sha256,sha(read(TOOL)));assert.equal(m.build.native_index_sha256,sha(read(m.build.native_index)));assert.deepEqual(Object.keys(m.duelists).sort(),[...LEGACY_WEAPONS].sort());
 let generated=0;const paths=new Set();
 for(const row of entries(m)){
  assert.match(row.path,/^\/assets\/battle-enhanced\/[a-zA-Z0-9_-]+\.png$/);paths.add(path.basename(row.path));const input=read('game'+row.path),image=decodePng(input);
  assert.deepEqual([image.width,image.height],[row.width,row.height]);assert.equal(row.width,row.logical_width*4);assert.equal(row.height,row.logical_height*4);assert.equal(row.sha256,sha(input));assert.equal(row.pixel_sha256,sha(image.rgba));
  if(row.source_path){const src=read('game'+row.source_path);assert.equal(row.source_sha256,sha(src));assert(['native_scale4x','native_nearest4x'].includes(row.method));assert((row.method==='native_nearest4x'?nearest4x:native4x)(decodePng(src)).equals(image.rgba),'Native4x must reproduce exactly');}
  else{generated++;assert.deepEqual([row.width,row.height],[384,384]);const alpha=new Set();let count=0;const palette=new Set();for(let i=0;i<image.rgba.length;i+=4){alpha.add(image.rgba[i+3]);if(image.rgba[i+3]){count++;palette.add(image.rgba.subarray(i,i+3).toString('hex'));}}assert.deepEqual([...alpha].sort((a,b)=>a-b),[0,255]);assert(count>1000);assert(palette.size<=26);assert(row.horse_mask_pixels>500);}
 }
 for(const weapon of LEGACY_WEAPONS){assert.deepEqual(Object.keys(m.duelists[weapon]).sort(),[...LEGACY_HORSES].sort());const study=m.studies[weapon];assert.equal(study.study_sha256,sha(read(study.study)));assert.equal(study.prompt_sha256,sha(read(study.prompt)));for(const horse of LEGACY_HORSES)assert.equal(m.duelists[weapon][horse].frames.length,2);}
 assert.equal(generated,LEGACY_WEAPONS.length*LEGACY_HORSES.length*2);
 assert.deepEqual(m.actions,[...ACTIONS]);assert.deepEqual(Object.keys(m.action_atlases).sort(),[...WEAPONS].sort());assert.deepEqual(m.horse_palettes,ACTION_COATS);
 let atlases=0;
 for(const weapon of WEAPONS){
  assert.deepEqual(Object.keys(m.action_atlases[weapon]).sort(),[...HORSES].sort());const source=m.action_studies[weapon];
  assert.equal(source.study_sha256,sha(read(source.study)));assert.equal(source.prompt_sha256,sha(read(source.prompt)));assert.deepEqual(source.actions,[...ACTIONS]);assert.deepEqual(source.source_grid,actionGrid({width:source.source_size[0],height:source.source_size[1]}));assert.equal(source.source_cells.length,8);assert.equal(source.source_boxes.length,8);
  for(const horse of HORSES){
   const row=m.action_atlases[weapon][horse];assert.equal(row.method,'imagegen_action_atlas_cyan_coat_mask');assert.equal(row.study_key,weapon);assert.match(row.path,/^\/assets\/battle-enhanced\/duel-actions-[a-z0-9-]+\.png$/);paths.add(path.basename(row.path));
   const input=read('game'+row.path),image=decodePng(input);assert.deepEqual([row.width,row.height,row.logical_width,row.logical_height],[4096,384,128,96]);assert.deepEqual([image.width,image.height],[4096,384]);assert.equal(row.sha256,sha(input));assert.equal(row.pixel_sha256,sha(image.rgba));assert.deepEqual(row.anchor,{x:64,y:96});assert(row.horse_mask_pixels>4000);
   assert.deepEqual(row.frames,ACTIONS.map((action,index)=>({action,source_rect:[index*ACTION_FRAME_WIDTH,0,ACTION_FRAME_WIDTH,ACTION_FRAME_HEIGHT]})));
   for(const frame of row.frames)assert(frameHasMargin(image,frame.source_rect),`${weapon}/${horse}/${frame.action} must have at least8transparent pixels around complete weapons and hooves`);
   const alpha=new Set(),palette=new Set();let count=0;
   for(let i=0;i<image.rgba.length;i+=4){alpha.add(image.rgba[i+3]);if(image.rgba[i+3]){count++;palette.add(image.rgba.readUInt32LE(i)&0xffffff);}}
   assert.deepEqual([...alpha].sort((a,b)=>a-b),[0,255]);assert(count>8000);assert(palette.size<=26);atlases++;
  }
 }
 assert.equal(atlases,WEAPONS.length*HORSES.length);
 assert.deepEqual(fs.readdirSync(path.join(ROOT,OUT)).filter(p=>p.endsWith('.png')).sort(),[...paths].sort(),'No stale final sprites');
 return{check:true,scale:4,native_files:paths.size-generated-atlases,legacy_generated_frames:generated,action_atlases:atlases,action_frames:atlases*ACTIONS.length,action_types:ACTIONS.length,weapon_types:WEAPONS.length,horse_types:HORSES.length,originals_retained:true};
}
module.exports={build,check,native4x,nearest4x,bounds,poseImages,imageBounds,fitted,horseMask,recolor,entries,atlasEntries,frameHasMargin,ACTIONS,ACTION_FRAME_WIDTH,ACTION_FRAME_HEIGHT,LEGACY_WEAPONS,LEGACY_HORSES,ACTION_COATS,actionGrid,actionPoseImages,cyanCoat,fittedAction,recolorAction,actionSource,actionAtlasEntry};
if(require.main===module){try{console.log(JSON.stringify(process.argv.includes('--check')?check():build()));}catch(error){console.error(error);process.exitCode=1;}}
