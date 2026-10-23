#!/usr/bin/env node
'use strict';
// Local imagegen repairs only. The immutable v1 map is the sole composition base.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sharp=require('sharp'),{PNG}=require('pngjs');
const dir=__dirname,root=path.resolve(dir,'../..');
const file=name=>path.join(dir,name),read=name=>fs.readFileSync(file(name));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const png=name=>PNG.sync.read(read(name));
const imageInfo=name=>({path:'art/map-western-range-v2/'+name,sha256:sha(read(name))});
const northernGrassTexture={x:268,y:353,width:16,height:21};
const formerNorthPeak=[[238,347],[250,350],[253,358],[266,365],[269,373],[250,379],[219,380],[211,375],[218,367],[229,363]];
const targets=[
 {id:'north',bbox:{x:208,y:346,width:63,height:40},
  polygon:[[210,355],[227,348],[241,346],[253,349],[267,366],[270,379],[251,385],[225,382],[209,375]],
  preview:{left:165,top:325,width:115,height:95},source:'generated-north.png'},
 {id:'south',bbox:{x:109,y:625,width:59,height:35},
  polygon:[[120,628],[139,625],[155,636],[167,646],[166,658],[140,659],[117,655],[109,646]],
  preview:{left:95,top:592,width:110,height:95},source:'generated-range-first-pass.png'}
];
function inside(x,y,polygon){
 let result=false;for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
  const [a,b]=polygon[i],[c,d]=polygon[j];
  if((b>y)!==(d>y)&&x<(c-a)*(y-b)/(d-b)+a)result=!result;
 }return result;
}
const river=(data,p)=>data[p+2]>140&&data[p+2]>data[p]+45&&data[p+2]>data[p+1]+35;
const green=(data,p)=>data[p+1]>110&&data[p+1]>data[p]*1.4&&data[p+1]>data[p+2]*1.7;
const brown=(data,p)=>data[p]>70&&data[p]>data[p+1]*1.25&&data[p]>data[p+2]*1.8;
async function build(){
 const immutableBeforeSHA='3ff9ce070e6424e7d3dae04fa7b08157ddf0659ebe70d80fca20d5e72c2c7de2';
 if(sha(read('before-map.png'))!==immutableBeforeSHA)throw Error('The saved v1 base image has changed');
 const before=png('before-map.png'),result=new PNG({width:before.width,height:before.height});
 const baseline=PNG.sync.read(fs.readFileSync(path.join(root,'game/assets/map-road-centers.png')));
 const ground=PNG.sync.read(fs.readFileSync(path.join(root,'game/map-source/hydrology-ground.png')));
 for(const value of [before,baseline,ground])if(value.width!==1352||value.height!==1024)throw Error('Unexpected original map dimensions');
 before.data.copy(result.data);
 const first=await sharp(file('generated-range-first-pass.png')).ensureAlpha().raw().toBuffer({resolveWithObject:true});
 if(first.info.width!==1024||first.info.height!==1536)throw Error('Unexpected full-range source dimensions');
 // The edited northern crop corresponds exactly to this rectangle of the full source.
 const northRect={left:650,top:210,width:320,height:220};
 const editedNorth=await sharp(file('generated-north.png')).resize(northRect.width,northRect.height,{kernel:'nearest'}).ensureAlpha().raw().toBuffer();
 const northFull=Buffer.from(first.data);
 for(let y=0;y<northRect.height;y++)editedNorth.copy(northFull,((northRect.top+y)*first.info.width+northRect.left)*4,y*northRect.width*4,(y+1)*northRect.width*4);
 const sources={};
 for(const [id,data] of [['north',northFull],['south',first.data]])sources[id]=await sharp(data,{raw:first.info}).resize(288,432,{kernel:'nearest'}).raw().toBuffer();
 const protectedPixels=new Uint8Array(before.width*before.height),mask=new Uint8Array(protectedPixels.length);
 // v1's original roads and castles differ from its roadless terrain reference.
 // Those exact pixels, plus the original blue river and a narrow bank, survive unchanged.
 for(let y=0;y<before.height;y++)for(let x=0;x<before.width;x++){
  const n=y*before.width+x,p=n*4;
  const changed=[0,1,2,3].some(k=>baseline.data[p+k]!==ground.data[p+k]);
  const blue=river(ground.data,p);
  if(!changed&&!blue)continue;
  const radius=blue?2:1;
  for(let dy=-radius;dy<=radius;dy++)for(let dx=-radius;dx<=radius;dx++){
   const xx=x+dx,yy=y+dy;if(xx>=0&&yy>=0&&xx<before.width&&yy<before.height)protectedPixels[yy*before.width+xx]=1;
  }
 }
 const stats=[];
 for(const target of targets){
  let candidates=0,protectedCount=0,changed=0,blueRejected=0,originalGrass=0,originalRidge=0;
  const source=sources[target.id];
  // The northern generated grass has oversized dots and brighter colors.
  // Fill only replacement grass from this adjacent roadless original grass
  // texture; leave all recovered imagegen rock and black crevices intact.
  for(let y=target.bbox.y;y<target.bbox.y+target.bbox.height;y++)for(let x=target.bbox.x;x<target.bbox.x+target.bbox.width;x++){
   if(!inside(x+.5,y+.5,target.polygon))continue;
   const n=y*before.width+x,p=n*4,q=((y-280)*288+x)*4;mask[n]=1;candidates++;
   if(protectedPixels[n]){protectedCount++;continue;}
   if(river(source,q)){blueRejected++;continue;}
   const sourceGrass=green(source,q);
   // Never cut away an already-correct brown ridge when revealing its foothill.
   if(sourceGrass&&brown(before.data,p)){originalRidge++;continue;}
   // Preserve surrounding grass. Only the northern former peak footprint, or
   // southern dark/saturated mountain faces, needs replacement grass.
   if(sourceGrass&&((target.id==='north'&&!inside(x+.5,y+.5,formerNorthPeak))||(target.id==='south'&&green(before.data,p)&&before.data[p]>5&&before.data[p+1]>170&&before.data[p+2]>10))){originalGrass++;continue;}
   let color=Array.from(source.subarray(q,q+3));
   if(sourceGrass&&target.id==='north'){
    const xx=northernGrassTexture.x+(x-target.bbox.x)%northernGrassTexture.width;
    const yy=northernGrassTexture.y+(y-target.bbox.y)%northernGrassTexture.height;
    const reference=(yy*before.width+xx)*4;
    if(!green(before.data,reference))throw Error('Original grass texture includes non-grass');
    color=Array.from(before.data.subarray(reference,reference+3));
   }
   for(let k=0;k<3;k++)result.data[p+k]=color[k];
   if([0,1,2,3].some(k=>result.data[p+k]!==before.data[p+k]))changed++;
  }
  stats.push({...target,candidate_pixels:candidates,protected_pixels:protectedCount,changed_pixels:changed,rejected_generated_river_pixels:blueRejected,preserved_original_grass_pixels:originalGrass,preserved_original_brown_ridge_pixels:originalRidge});
 }
 let outsideIdentical=0,protectedIdentical=0,changedTotal=0;
 for(let n=0;n<protectedPixels.length;n++){
  const p=n*4,different=[0,1,2,3].some(k=>result.data[p+k]!==before.data[p+k]);
  if((!mask[n]||protectedPixels[n])&&different)throw Error('Outside/protected pixel changed');
  if(!mask[n])outsideIdentical++;if(protectedPixels[n])protectedIdentical++;if(different)changedTotal++;
 }
 const output=PNG.sync.write(result);fs.writeFileSync(path.join(root,'game/assets/map-western-range.png'),output);
 for(const target of targets)for(const [label,input] of [['before',read('before-map.png')],['after',output]]){
  await sharp(input).extract(target.preview).resize(target.preview.width*5,target.preview.height*5,{kernel:'nearest'}).toFile(file(`${label}-${target.id}.png`));
 }
 await sharp(read('before-map.png')).extract({left:northernGrassTexture.x,top:northernGrassTexture.y,width:northernGrassTexture.width,height:northernGrassTexture.height}).resize(northernGrassTexture.width*10,northernGrassTexture.height*10,{kernel:'nearest'}).toFile(file('north-grass-reference.png'));
 const manifest={schema:'tk2-western-range-art-v2',map:{width:1352,height:1024},
  before:imageInfo('before-map.png'),sources:[imageInfo('generated-range-first-pass.png'),imageInfo('generated-north.png')],
  source_mapping:{full_range:{x:0,y:280,width:288,height:432},north_reference_in_full_source:northRect,resampling:'nearest-neighbor, hard native-pixel polygon mask; no alpha blending',
   original_grass_preserved:'North: keep all grass outside the former green-peak footprint. South: keep original green pixels when R>5, G>170, B>10 and the replacement is grass.',
   northern_grass_texture:{...northernGrassTexture,former_peak_polygon:formerNorthPeak,rule:'For remaining new green pixels, repeat the adjacent original grass texture at native pixel spacing. Never recolor red-brown rock or black crevices.'}},
  targets:stats,verification:{changed_pixels:changedTotal,outside_pixels_identical:outsideIdentical,protected_pixels_identical:protectedIdentical},
  protection_inputs:[{path:'game/assets/map-road-centers.png',sha256:sha(fs.readFileSync(path.join(root,'game/assets/map-road-centers.png')))},{path:'game/map-source/hydrology-ground.png',sha256:sha(fs.readFileSync(path.join(root,'game/map-source/hydrology-ground.png')))}],
  output:{path:'game/assets/map-western-range.png',sha256:sha(output)},
  rule:'Only two native-pixel polygons are editable. Original v1 map pixels outside the polygons, and all original road/castle/river protection pixels, are byte-identical. No city, route, distance, campaign or save data rebuilt.'};
 fs.writeFileSync(file('manifest.json'),JSON.stringify(manifest,null,2)+'\n');console.log(JSON.stringify(manifest,null,2));
}
build().catch(error=>{console.error(error);process.exitCode=1;});
