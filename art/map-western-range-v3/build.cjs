#!/usr/bin/env node
'use strict';
// Compose two approved imagegen details; never rebuild game or route data.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const sharp=require('sharp'),{PNG}=require('pngjs');
const dir=__dirname,root=path.resolve(dir,'../..'),file=name=>path.join(dir,name);
const read=name=>fs.readFileSync(file(name)),sha=raw=>crypto.createHash('sha256').update(raw).digest('hex');
const beforeSHA='da66399bf99e50ebd9559957c686585292f3d974825004e14e60037257dafae2';
const crop={x:150,y:325,width:160,height:200};
const brownPolygon=[[198,360],[211,357],[220,362],[225,369],[234,373],[241,380],[233,387],[218,391],[201,384],[190,374],[191,366]];
const greenSourcePolygon=[[213,417],[220,424],[226,429],[234,435],[235,438],[231,442],[227,442],[225,445],[220,446],[214,444],[210,446],[205,442],[198,442],[192,439],[194,434],[204,425],[209,422]];
const greenShift={x:4,y:-5};
const grassTexture={x:268,y:353,width:16,height:21};
const river=(data,p)=>data[p+2]>140&&data[p+2]>data[p]+45&&data[p+2]>data[p+1]+35;
const green=(data,p)=>data[p+1]>110&&data[p+1]>data[p]*1.4&&data[p+1]>data[p+2]*1.7;
const brown=(data,p)=>data[p]>70&&data[p]>data[p+1]*1.25&&data[p]>data[p+2]*1.8;
function inside(x,y,polygon){let result=false;for(let i=0,j=polygon.length-1;i<polygon.length;j=i++){
 const[a,b]=polygon[i],[c,d]=polygon[j];if((b>y)!==(d>y)&&x<(c-a)*(y-b)/(d-b)+a)result=!result;
}return result;}
function bbox(points){const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);return{x:Math.min(...xs),y:Math.min(...ys),width:Math.max(...xs)-Math.min(...xs)+1,height:Math.max(...ys)-Math.min(...ys)+1};}
function runs(points){const rows=new Map();for(const[x,y]of points){if(!rows.has(y))rows.set(y,[]);rows.get(y).push(x);}
 const result=[];for(const[y,xs]of [...rows].sort((a,b)=>a[0]-b[0])){xs.sort((a,b)=>a-b);let start=xs[0],last=start;for(const x of xs.slice(1)){if(x===last+1)last=x;else{result.push([y,start,last-start+1]);start=last=x;}}result.push([y,start,last-start+1]);}return result;}
async function build(){
 const beforeBytes=read('before-map.png');if(sha(beforeBytes)!==beforeSHA)throw Error('Saved immutable v2 base changed');
 const before=PNG.sync.read(beforeBytes),baseline=PNG.sync.read(fs.readFileSync(path.join(root,'art/map-western-range-v3/source/road-centers-before-junctions.png'))),ground=PNG.sync.read(fs.readFileSync(path.join(root,'game/map-source/hydrology-ground.png')));
 for(const img of[before,baseline,ground])if(img.width!==1352||img.height!==1024)throw Error('Unexpected original map size');
 const generatedInfo=await sharp(file('generated-edit.png')).metadata();
 if(generatedInfo.width!==1122||generatedInfo.height!==1402)throw Error('Unexpected imagegen output size');
 const generated=await sharp(file('generated-edit.png')).resize(crop.width,crop.height,{kernel:'nearest'}).ensureAlpha().raw().toBuffer();
 const sample=(x,y)=>((y-crop.y)*crop.width+x-crop.x)*4;
 const result=new PNG({width:before.width,height:before.height});before.data.copy(result.data);
 const protectedPixels=new Uint8Array(before.width*before.height),infrastructure=new Uint8Array(protectedPixels.length),mask=new Uint8Array(protectedPixels.length);
 for(let y=0;y<before.height;y++)for(let x=0;x<before.width;x++){
  const n=y*before.width+x,p=n*4,changed=[0,1,2,3].some(k=>baseline.data[p+k]!==ground.data[p+k]),blue=river(ground.data,p);
  if(!changed&&!blue)continue;infrastructure[n]=1;const radius=blue?2:1;
  for(let dy=-radius;dy<=radius;dy++)for(let dx=-radius;dx<=radius;dx++){
   const xx=x+dx,yy=y+dy;if(xx>=0&&yy>=0&&xx<before.width&&yy<before.height)protectedPixels[yy*before.width+xx]=1;
  }
 }
 const apply=(x,y,color)=>{const p=(y*before.width+x)*4;for(let k=0;k<3;k++)result.data[p+k]=color[k];};
 const brownStats={id:'yinping-brown-foothill',polygon:brownPolygon,bbox:bbox(brownPolygon),candidate_pixels:0,protected_pixels:0,preserved_original_grass_pixels:0,preserved_original_brown_pixels:0,grass_texture_pixels:0,changed_pixels:0};
 for(let y=brownStats.bbox.y;y<brownStats.bbox.y+brownStats.bbox.height;y++)for(let x=brownStats.bbox.x;x<brownStats.bbox.x+brownStats.bbox.width;x++){
  if(!inside(x+.5,y+.5,brownPolygon))continue;const n=y*before.width+x,p=n*4,q=sample(x,y);mask[n]=1;brownStats.candidate_pixels++;
  if(protectedPixels[n]){brownStats.protected_pixels++;continue;}
  if(river(generated,q))throw Error('Generated water inside brown target');
  let color=Array.from(generated.subarray(q,q+3));
  if(green(generated,q)){
   if(brown(before.data,p)){brownStats.preserved_original_brown_pixels++;continue;}
   if(green(before.data,p)&&before.data[p]>5&&before.data[p+1]>170&&before.data[p+2]>10){brownStats.preserved_original_grass_pixels++;continue;}
   const xx=grassTexture.x+(x-brownStats.bbox.x)%grassTexture.width,yy=grassTexture.y+(y-brownStats.bbox.y)%grassTexture.height,ref=(yy*before.width+xx)*4;
   if(!green(before.data,ref))throw Error('Reference grass includes a non-grass pixel');
   color=Array.from(before.data.subarray(ref,ref+3));brownStats.grass_texture_pixels++;
  }
  apply(x,y,color);if([0,1,2].some(k=>result.data[p+k]!==before.data[p+k]))brownStats.changed_pixels++;
 }
 // The full mountain silhouette includes the bright left face and its
 // detached dark streak. Those are one visual mountain, even when their
 // dark pixels do not form a single connected component.
 const greenSource=bbox(greenSourcePolygon),shape=[];
 for(let y=greenSource.y;y<greenSource.y+greenSource.height;y++)for(let x=greenSource.x;x<greenSource.x+greenSource.width;x++)if(inside(x+.5,y+.5,greenSourcePolygon))shape.push([x,y]);
 const greenStats={id:'yinping-chengdu-green-mountain',source_polygon:greenSourcePolygon,source_bbox:greenSource,source_shift:greenShift,source_shape_pixels:shape.length,protected_pixels:0,clearance_rejected_pixels:0,rejected_generated_water_pixels:0,minimum_grass_gap_pixels:6,copied_pixels:0,changed_pixels:0};
 const copied=[];
 for(const[sx,sy]of shape){
  const x=sx+greenShift.x,y=sy+greenShift.y,n=y*before.width+x,p=n*4,q=sample(sx,sy);mask[n]=1;
  if(protectedPixels[n]){greenStats.protected_pixels++;continue;}
  // A seven-pixel distance leaves six complete native grass pixels before
  // the original road/river. Never paint over either the bank or road edge.
  let clear=true;for(let dy=-6;dy<=6&&clear;dy++)for(let dx=-6;dx<=6;dx++){
   if(dx*dx+dy*dy>=49)continue;const xx=x+dx,yy=y+dy;if(xx>=0&&yy>=0&&xx<before.width&&yy<before.height&&infrastructure[yy*before.width+xx]){clear=false;break;}
  }
  if(!clear){greenStats.clearance_rejected_pixels++;continue;}
  if(river(generated,q)){greenStats.rejected_generated_water_pixels++;continue;}
  apply(x,y,Array.from(generated.subarray(q,q+3)));copied.push([x,y]);greenStats.copied_pixels++;
  if([0,1,2].some(k=>result.data[p+k]!==before.data[p+k]))greenStats.changed_pixels++;
 }
 if(greenStats.copied_pixels<250)throw Error('Protected terrain clipped the mountain unexpectedly');
 greenStats.destination_bbox=bbox(copied);greenStats.destination_runs=runs(copied);
 if(greenStats.destination_bbox.y+greenStats.destination_bbox.height-1>441)throw Error('New mountain extends into the road grass gap');
 let changed=0,outside=0,protectedCount=0;
 for(let n=0;n<mask.length;n++){
  const p=n*4,different=[0,1,2,3].some(k=>result.data[p+k]!==before.data[p+k]);
  if((!mask[n]||protectedPixels[n])&&different)throw Error('Outside/protected original pixel changed');
  if(!mask[n])outside++;if(protectedPixels[n])protectedCount++;if(different)changed++;
 }
 const output=PNG.sync.write(result);fs.writeFileSync(path.join(root,'game/assets/map-western-range.png'),output);
 for(const[label,input]of[['before',beforeBytes],['after',output]])await sharp(input).extract({left:crop.x,top:crop.y,width:crop.width,height:crop.height}).resize(crop.width*5,crop.height*5,{kernel:'nearest'}).toFile(file(label+'-detail.png'));
 const manifest={schema:'tk2-western-range-art-v3',map:{width:1352,height:1024},before:{path:'art/map-western-range-v3/before-map.png',sha256:beforeSHA},source:{path:'art/map-western-range-v3/generated-edit.png',sha256:sha(read('generated-edit.png')),width:generatedInfo.width,height:generatedInfo.height},source_mapping:{full_map_crop:crop,resampling:'nearest-neighbor; no alpha blending',brown_foothill_grass_texture:grassTexture},targets:[brownStats,greenStats],verification:{changed_pixels:changed,outside_pixels_identical:outside,protected_pixels_identical:protectedCount},protection_inputs:['art/map-western-range-v3/source/road-centers-before-junctions.png','game/map-source/hydrology-ground.png'].map(name=>({path:name,sha256:sha(fs.readFileSync(path.join(root,name)))})),output:{path:'game/assets/map-western-range.png',sha256:sha(output)},rule:'Only two tight terrain masks are editable. Outside-mask and original road/castle/river protection pixels remain byte-identical to v2. A complete tight mountain silhouette including its green face and left shadow is added with six native grass pixels of infrastructure clearance. No route/campaign/save data rebuilt.'};
 fs.writeFileSync(file('manifest.json'),JSON.stringify(manifest,null,2)+'\n');console.log(JSON.stringify({output:manifest.output,targets:manifest.targets.map(({destination_runs,...row})=>row),verification:manifest.verification},null,2));
}
build().catch(error=>{console.error(error);process.exitCode=1;});
