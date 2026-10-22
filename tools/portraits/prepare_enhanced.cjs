#!/usr/bin/env node
'use strict';
/* Prepare identity-bound 128x160 art references without modifying any old art.
 * NES bases use Scale4x plus source-driven flat-top/thin-white preservation.
 * New portraits recover their actual assigned high-resolution atlas cells.
 * This is reference preparation only; no procedural faces or shading are made.
 */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),zlib=require('node:zlib'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'../..'),WORK=path.join(ROOT,'art/portraits/enhancement-v1');
const REFERENCE='art/portraits/hd-samples/zhuge-liang-preserved-v8/portrait-128x160.png';
const PALETTE=[[0,0,0,0],[255,255,255,255],[247,162,71,255],[158,65,0,255]];
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const crcTable=Uint32Array.from({length:256},(_,i)=>{let n=i;for(let b=0;b<8;b++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0;});
function crc32(bytes,start=0,end=bytes.length){let crc=0xffffffff;for(let i=start;i<end;i++)crc=crcTable[(crc^bytes[i])&255]^(crc>>>8);return(crc^0xffffffff)>>>0;}
function decodePng(raw){
 if(!raw.subarray(0,8).equals(Buffer.from([137,80,78,71,13,10,26,10])))throw Error('Invalid PNG signature');
 let offset=8,header=null,ended=false;const idat=[];
 while(offset<raw.length){
  if(offset+12>raw.length)throw Error('Truncated PNG chunk');const length=raw.readUInt32BE(offset),end=offset+12+length;
  if(end>raw.length)throw Error('Truncated PNG data');const kind=raw.toString('ascii',offset+4,offset+8),data=raw.subarray(offset+8,end-4);
  if(crc32(raw,offset+4,end-4)!==raw.readUInt32BE(end-4))throw Error('PNG CRC mismatch');
  if(kind==='IHDR'){if(header||length!==13)throw Error('Invalid PNG header');header={width:data.readUInt32BE(0),height:data.readUInt32BE(4),depth:data[8],color:data[9],compression:data[10],filter:data[11],interlace:data[12]};}
  else if(kind==='IDAT')idat.push(data);
  else if(kind==='IEND'){if(length||end!==raw.length)throw Error('PNG trailing data');ended=true;}
  offset=end;
 }
 if(!header||!ended||header.depth!==8||![2,6].includes(header.color)||header.compression||header.filter||header.interlace)throw Error('Expected noninterlaced8bitRGB/RGBA PNG');
 const{width,height}=header;if(width<1||height<1||width>4096||height>4096)throw Error('Unexpected PNG dimensions');
 const channels=header.color===6?4:3,stride=width*channels,scan=zlib.inflateSync(Buffer.concat(idat)),rgba=Buffer.alloc(width*height*4);
 if(scan.length!==(stride+1)*height)throw Error('PNG scanline size mismatch');let previous=Buffer.alloc(stride);
 for(let y=0;y<height;y++){
  const at=y*(stride+1),filter=scan[at],row=Buffer.from(scan.subarray(at+1,at+1+stride));if(filter>4)throw Error('Unknown PNG row filter');
  if(filter)for(let x=0;x<stride;x++){
   const left=x>=channels?row[x-channels]:0,up=previous[x],corner=x>=channels?previous[x-channels]:0;let prediction=0;
   if(filter===1)prediction=left;else if(filter===2)prediction=up;else if(filter===3)prediction=(left+up)>>1;
   else{const p=left+up-corner,pa=Math.abs(p-left),pb=Math.abs(p-up),pc=Math.abs(p-corner);prediction=pa<=pb&&pa<=pc?left:pb<=pc?up:corner;}
   row[x]=(row[x]+prediction)&255;
  }
  if(channels===4)row.copy(rgba,y*width*4);else for(let x=0;x<width;x++){const a=(y*width+x)*4,s=x*3;rgba[a]=row[s];rgba[a+1]=row[s+1];rgba[a+2]=row[s+2];rgba[a+3]=255;}
  previous=row;
 }
 return{width,height,rgba};
}
function encodePng(width,height,rgba){
 if(rgba.length!==width*height*4)throw Error('RGBA size mismatch');
 function chunk(kind,data){const bytes=Buffer.alloc(data.length+12);bytes.writeUInt32BE(data.length,0);bytes.write(kind,4,4,'ascii');data.copy(bytes,8);bytes.writeUInt32BE(crc32(bytes,4,bytes.length-4),bytes.length-4);return bytes;}
 const header=Buffer.alloc(13);header.writeUInt32BE(width,0);header.writeUInt32BE(height,4);header[8]=8;header[9]=6;
 const scan=Buffer.alloc((width*4+1)*height);for(let y=0;y<height;y++)rgba.copy(scan,y*(width*4+1)+1,y*width*4,(y+1)*width*4);
 return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',zlib.deflateSync(scan,{level:9})),chunk('IEND',Buffer.alloc(0))]);
}
function scale2x(p,width,height){
 const out=new Uint32Array(width*height*4),ow=width*2;
 for(let y=0;y<height;y++)for(let x=0;x<width;x++){
  const e=p[y*width+x],b=p[Math.max(0,y-1)*width+x],d=p[y*width+Math.max(0,x-1)],f=p[y*width+Math.min(width-1,x+1)],south=p[Math.min(height-1,y+1)*width+x],at=y*2*ow+x*2;
  if(b!==south&&d!==f){out[at]=d===b?d:e;out[at+1]=b===f?f:e;out[at+ow]=d===south?d:e;out[at+ow+1]=south===f?f:e;}
  else out[at]=out[at+1]=out[at+ow]=out[at+ow+1]=e;
 }
 return out;
}
function originalBase(rgba){
 assert.equal(new Uint8Array(new Uint32Array([0x01020304]).buffer)[0],4,'This PNG pipeline requires a little-endian Node runtime');
 const native=Uint32Array.from({length:32*40},(_,i)=>rgba.readUInt32LE(i*4));
 const enlarged=scale2x(scale2x(native,32,40),64,80),orange=0xff47a2f7,white=0xffffffff;
 const get=(x,y)=>x<0||x>=32||y<0||y>=40?null:native[y*32+x];
 function restore(x,y,color){for(let yy=0;yy<4;yy++)for(let xx=0;xx<4;xx++)enlarged[(y*4+yy)*128+x*4+xx]=color;}
 for(let y=0;y<=4;y++)for(let x=0;x<32;){
  if(get(x,y)!==orange){x++;continue;}const start=x;while(x<32&&get(x,y)===orange)x++;
  if(x-start>=2&&Array.from({length:x-start},(_,n)=>start+n).every(xx=>get(xx,y-1)!==orange&&get(xx,y+1)===orange))for(let xx=start;xx<x;xx++)restore(xx,y,orange);
 }
 for(let y=0;y<10;y++)for(let x=0;x<32;x++)if(get(x,y)===white){
  const neighbors=Number(get(x-1,y)===white)+Number(get(x+1,y)===white)+Number(get(x,y-1)===white)+Number(get(x,y+1)===white);
  if(neighbors<=1)restore(x,y,white);
 }
 return Buffer.from(enlarged.buffer);
}
function quantizeAtlas(image){
 const indices=new Uint8Array(image.width*image.height),p=image.rgba;
 for(let i=0;i<indices.length;i++){
  const a=i*4,r=p[a],g=p[a+1],b=p[a+2];if(p[a+3]<128||Math.max(r,g,b)<=32)continue;
  let best=0,distance=r*r+g*g+b*b;
  for(let k=1;k<4;k++){const c=PALETTE[k],d=(r-c[0])**2+(g-c[1])**2+(b-c[2])**2;if(d<distance){best=k;distance=d;}}
  indices[i]=best;
 }
 return{width:image.width,height:image.height,indices};
}
function generatedBase(atlas,record){
 const source=record.source_visible_box,fit=record.native_fitted_box;
 if(!Array.isArray(source)||!Array.isArray(fit)||source.length!==4||fit.length!==4||![...source,...fit].every(Number.isInteger))throw Error('Missing recorded source/fitted bounds');
 const[sx,sy,sr,sb]=source,[left,top,right,bottom]=fit;
 if(sx<0||sy<0||sr>atlas.width||sb>atlas.height||sx>=sr||sy>=sb||left<0||top<0||right>32||bottom>40||left>=right||top>=bottom)throw Error('Invalid recorded source/fitted bounds');
 const rgba=Buffer.alloc(128*160*4),dw=(right-left)*4,dh=(bottom-top)*4,sw=sr-sx,sh=sb-sy;
 // Pixel-center nearest-neighbor mapping, directly from the assigned source art.
 for(let y=0;y<dh;y++)for(let x=0;x<dw;x++){
  const xx=sx+Math.min(sw-1,Math.floor((x+0.5)*sw/dw)),yy=sy+Math.min(sh-1,Math.floor((y+0.5)*sh/dh));
  const color=PALETTE[atlas.indices[yy*atlas.width+xx]],at=((top*4+y)*128+left*4+x)*4;
  for(let c=0;c<4;c++)rgba[at+c]=color[c];
 }
 return rgba;
}
function build({check=false}={}){
 const indexFile=path.join(ROOT,'game/assets/portraits/index.json'),currentBytes=fs.readFileSync(indexFile),snapshotFile=path.join(WORK,'source-index.json');
 // Publishing optional HD rows must not invalidate the immutable native input.
 // Preserve the exact original snapshot for provenance, but compare every
 // current native field and recheck its actual files before preparing/checking.
 if(!fs.existsSync(snapshotFile)){
  const existingPlan=path.join(WORK,'plan.json');
  if(fs.existsSync(existingPlan)&&JSON.parse(fs.readFileSync(existingPlan)).source_index_sha256!==sha(currentBytes))throw Error('Cannot snapshot a changed native index');
  if(check)throw Error('Missing immutable source-index.json snapshot');
  fs.mkdirSync(WORK,{recursive:true});fs.writeFileSync(snapshotFile,currentBytes);
 }
 const indexBytes=fs.readFileSync(snapshotFile),index=JSON.parse(indexBytes),current=JSON.parse(currentBytes);
 function nativeIndex(value){
  const people=Object.fromEntries(Object.entries(value.people||{}).map(([id,row])=>{const{enhanced,...native}=row;return[id,native];}));
  const sources={...value.sources};delete sources['portrait-enhanced.json'];
  return{...value,people,sources};
 }
 assert.deepEqual(nativeIndex(current),nativeIndex(index),'Current native portrait index changed');
 for(const[name,hash]of Object.entries(index.sources||{})){
  if(name==='portrait-enhanced.json')continue;
  if(sha(fs.readFileSync(path.join(ROOT,'game/config',name)))!==hash)throw Error('Native source configuration changed:'+name);
 }
 const generated=JSON.parse(fs.readFileSync(path.join(ROOT,'game/config/portrait-generated.json'))),runtime=new Map();
 for(const[id,person]of Object.entries(index.by_runtime_id||{})){if(!/^\d+$/.test(id)||runtime.has(person))throw Error('Invalid runtime/person binding');runtime.set(person,Number(id));}
 const entries=Object.entries(index.people||{}).sort((a,b)=>runtime.get(a[0])-runtime.get(b[0])||(a[0]<b[0]?-1:a[0]>b[0]?1:0));
 if(entries.length!==1023||runtime.size!==1023)throw Error('Expected1023stableportraitidentities');
 const sourceHashes=new Map(),nativeCache=new Map(),atlasCache=new Map(),groupsByHash=new Map(),people={};
 function loadFile(relative){const full=path.resolve(ROOT,relative);if(!full.startsWith(ROOT+path.sep))throw Error('Source outside repository');const bytes=fs.readFileSync(full);sourceHashes.set(full,sha(bytes));return bytes;}
 for(const[id,row]of entries){
  if(!/^[a-z0-9-]+$/.test(id)||!runtime.has(id)||!['nes_original','generated'].includes(row.kind)||!/^\/assets\/portraits\/(?:original|generated)\/[a-zA-Z0-9_-]+\.png$/.test(row.path))throw Error('Invalid portrait source identity');
  const bytes=loadFile('game'+row.path);if(sha(bytes)!==row.png_sha256)throw Error('NativePNGhashmismatch:'+id);
  if(!nativeCache.has(row.path)){const image=decodePng(bytes);if(image.width!==32||image.height!==40)throw Error('Unexpected native size');nativeCache.set(row.path,image);}
  const image=nativeCache.get(row.path);if(sha(image.rgba)!==row.rgba_sha256)throw Error('NativeRGBAhashmismatch:'+id);
  people[id]={name:row.name,runtime_id:runtime.get(id),source_path:row.path,source_sha256:row.png_sha256,source_rgba_sha256:row.rgba_sha256,kind:row.kind};
  if(!groupsByHash.has(row.rgba_sha256))groupsByHash.set(row.rgba_sha256,{id:row.rgba_sha256.slice(0,16),representative:id,person_ids:[],source_path:row.path,source_sha256:row.png_sha256,source_rgba_sha256:row.rgba_sha256});
  groupsByHash.get(row.rgba_sha256).person_ids.push(id);
 }
 const groups=[...groupsByHash.values()];if(groups.length!==982||new Set(groups.map(g=>g.id)).size!==982)throw Error('Unexpected distinct source coverage');
 const referenceBytes=loadFile(REFERENCE),referenceImage=decodePng(referenceBytes);if(referenceImage.width!==128||referenceImage.height!==160)throw Error('Approved reference size mismatch');
 const approvedSource=index.people['san14-candidate-0440'];if(approvedSource?.path!=='/assets/portraits/original/109.png')throw Error('Approved person/source identity changed');
 const approvedGroup=groupsByHash.get(approvedSource.rgba_sha256),bases=new Map();
 const approved_reference={person_id:'san14-candidate-0440',group_id:approvedGroup.id,path:REFERENCE,sha256:sha(referenceBytes),rgba_sha256:sha(referenceImage.rgba)};
 function write(relative,bytes){const target=path.join(WORK,relative);if(check){if(!fs.existsSync(target)||!fs.readFileSync(target).equals(bytes))throw Error('Prepared output differs:'+relative);}else{fs.mkdirSync(path.dirname(target),{recursive:true});fs.writeFileSync(target,bytes);}}
 for(const group of groups){
  const person=people[group.representative];let rgba,png;
  if(group===approvedGroup){rgba=referenceImage.rgba;png=referenceBytes;group.approved_reference=true;group.base_method='approved_zhuge_liang_v8_reference';}
  else if(person.kind==='nes_original'){rgba=originalBase(nativeCache.get(group.source_path).rgba);png=encodePng(128,160,rgba);group.base_method='Scale4x_with_native_flat_orange_top_and_thin_white_preservation';}
  else{
   const record=generated.by_person_id[group.representative];if(!record||record.path!==group.source_path||record.rgba_sha256!==group.source_rgba_sha256)throw Error('Generated source assignment mismatch');
   if(!atlasCache.has(record.source_atlas)){
    const bytes=loadFile(record.source_atlas);if(sha(bytes)!==record.source_atlas_sha256)throw Error('Recorded source atlas hash mismatch');atlasCache.set(record.source_atlas,{hash:sha(bytes),image:quantizeAtlas(decodePng(bytes))});
   }
   const atlas=atlasCache.get(record.source_atlas);if(atlas.hash!==record.source_atlas_sha256)throw Error('Conflicting atlas record');
   rgba=generatedBase(atlas.image,record);png=encodePng(128,160,rgba);group.base_method='assigned_source_atlas_visible_box_direct128_fixed_palette';
   Object.assign(group,{source_atlas:record.source_atlas,source_atlas_sha256:record.source_atlas_sha256,source_visible_box:record.source_visible_box,native_fitted_box:record.native_fitted_box,source_cell_index:record.cell_index,duplicate_fallback:record.duplicate_fallback||null});
  }
  const roundtrip=decodePng(png);if(!roundtrip.rgba.equals(rgba))throw Error('BasePNGroundtripfailed');
  group.base_path='bases/'+group.representative+'.png';group.base_png_sha256=sha(png);group.base_rgba_sha256=sha(rgba);group.atlas_id=null;group.cell_index=null;
  write(group.base_path,png);bases.set(group.id,rgba);
 }
 const pending=groups.filter(g=>!g.approved_reference),atlases=[];
 for(let start=0;start<pending.length;start+=64){
  const number=atlases.length+1,id='atlas-'+String(number).padStart(2,'0'),batch=pending.slice(start,start+64),rgba=Buffer.alloc(1024*1280*4);
  for(let at=3;at<rgba.length;at+=4)rgba[at]=255;
  batch.forEach((group,cell)=>{
   group.atlas_id=id;group.cell_index=cell;const base=bases.get(group.id),left=cell%8*128,top=Math.floor(cell/8)*160;
   for(let y=0;y<160;y++)for(let x=0;x<128;x++){const from=(y*128+x)*4,to=((top+y)*1024+left+x)*4;if(base[from+3]){rgba[to]=base[from];rgba[to+1]=base[from+1];rgba[to+2]=base[from+2];}}
  });
  const png=encodePng(1024,1280,rgba),relative='references/'+id+'.png';write(relative,png);
  atlases.push({id,path:relative,columns:8,rows:8,tile_width:128,tile_height:160,groups:batch.map(g=>g.id),png_sha256:sha(png),rgba_sha256:sha(rgba),padding_cells:64-batch.length});
 }
 const plan={schema:'tk2-portrait-enhancement-plan-v1',source_index:'game/assets/portraits/index.json',source_index_sha256:sha(indexBytes),size:[128,160],display_background:'#000000',approved_reference,
  counts:{people:entries.length,unique_source_images:groups.length,approved_groups:1,groups_to_generate:pending.length,atlases:atlases.length,original_people:entries.filter(([,p])=>p.kind==='nes_original').length,generated_people:entries.filter(([,p])=>p.kind==='generated').length},
  preparation_policy:{original:'Published Scale2x twice; native orange top runs and thin or isolated white top cells restored from source; no new facial geometry',generated:'Actual per-person source_atlas/source_visible_box/native_fitted_box, including any recorded duplicate fallback; high-resolution source nearest-resized directly into4xfit; original four-color quantization',atlas:'8x8 tiles of128x160 without gaps, opaque black backing, unused cells black',identity:'Group only byte-identical nativeRGBA; retain every stable personID and original sourcehash'},groups,people,atlases};
 write('plan.json',Buffer.from(JSON.stringify(plan,null,2)+'\n'));
 for(const[full,hash]of sourceHashes)if(sha(fs.readFileSync(full))!==hash)throw Error('Source changed during preparation:'+full);
 return plan;
}
module.exports={decodePng,encodePng,scale2x,originalBase,quantizeAtlas,generatedBase,build};
if(require.main===module){try{const check=process.argv.includes('--check'),plan=build({check});console.log(JSON.stringify({check,workdir:path.relative(ROOT,WORK),counts:plan.counts,approved_reference:plan.approved_reference,first_atlas:plan.atlases[0],last_atlas:plan.atlases.at(-1)},null,2));}catch(error){console.error(error);process.exitCode=1;}}
