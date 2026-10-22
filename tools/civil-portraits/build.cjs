#!/usr/bin/env node
'use strict';
/* Original-identity pixel enhancement: imagegen supplies tone, never geometry.
 * This uses the same Scale4x/material-mask process as the approved portraits.
 */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {decodePng,encodePng,originalBase}=require('../portraits/prepare_enhanced.cjs');
const ROOT=path.resolve(__dirname,'../..'),WORK='art/civil-portraits/enhancement-v1';
const OUT='game/assets/civil-staff/enhanced',REFERENCE='art/portraits/hd-samples/zhuge-liang-preserved-v8/portrait-128x160.png';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),read=p=>fs.readFileSync(path.join(ROOT,p));
const uri=p=>'data:image/png;base64,'+read(p).toString('base64');
const KEYS=Object.freeze(['clerk-1','clerk-2','clerk-3']);
function check(){
 const file=path.join(ROOT,OUT,'index.json'),manifest=JSON.parse(fs.readFileSync(file));
 assert.equal(manifest.schema,'tk2-civil-portraits-v1');assert.equal(manifest.width,128);assert.equal(manifest.height,160);
 assert.equal(manifest.originals_retained,true);assert.deepEqual(Object.keys(manifest.portraits).sort(),KEYS);
 assert.equal(manifest.build.tool_sha256,sha(read('tools/civil-portraits/build.cjs')));
 assert.equal(manifest.approved_reference.sha256,sha(read(REFERENCE)));
 for(const key of KEYS){
  const row=manifest.portraits[key],source=read('game/assets/civil-staff/'+key+'.png'),native=decodePng(source),base=originalBase(native.rgba),bytes=read('game'+row.path),image=decodePng(bytes);
  assert.equal(row.path,`/assets/civil-staff/enhanced/${key}.png`);assert.equal(row.source_path,`/assets/civil-staff/${key}.png`);
  assert.deepEqual([native.width,native.height],[32,40]);assert.deepEqual([image.width,image.height],[128,160]);
  assert.equal(row.source_sha256,sha(source));assert.equal(row.sha256,sha(bytes));assert.equal(row.pixel_sha256,sha(image.rgba));assert.equal(row.base_rgba_sha256,sha(base));
  assert.equal(row.study_sha256,sha(read(row.study)));assert.equal(row.prompt_sha256,sha(read(row.prompt)));
  const colors=new Set();let changed=0;
  for(let i=0;i<128*160;i++){
   const at=i*4;assert.equal(image.rgba[at+3],base[at+3],'Native identity alpha must not drift');
   if(!base[at+3])assert(image.rgba.subarray(at,at+4).equals(base.subarray(at,at+4)),'Native ink/transparent details must not drift');
   colors.add(image.rgba.subarray(at,at+4).toString('hex'));if(!image.rgba.subarray(at,at+4).equals(base.subarray(at,at+4)))changed++;
  }
  assert(colors.size<=16);assert(changed>=20);assert.equal(row.qa.palette_size,colors.size);assert.equal(row.qa.changed_pixels,changed);
 }
 return {check:true,portraits:KEYS.length,width:128,height:160,originalsRetained:true};
}
async function build(){
 const {chromium}=require('playwright'),browser=await chromium.launch({channel:'chrome',headless:true});const portraits={};
 try{
  const page=await browser.newPage();
  for(const key of KEYS){
   const sourcePath='game/assets/civil-staff/'+key+'.png',source=read(sourcePath),native=decodePng(source),base=originalBase(native.rgba);
   assert.deepEqual([native.width,native.height],[32,40]);const study=WORK+'/studies/'+key+'.png',prompt=WORK+'/prompts/'+key+'.txt';
   const rendered=await page.evaluate(async({base,study})=>{
    const w=128,h=160,canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;const ctx=canvas.getContext('2d',{willReadFrequently:true});
    const img=new Image();img.src=study;await img.decode();ctx.imageSmoothingEnabled=false;ctx.drawImage(img,0,0,w,h);const tonal=ctx.getImageData(0,0,w,h).data;
    const raw=new Uint8ClampedArray(base),out=new Uint8ClampedArray(raw),skin=[[142,56,0],[185,85,10],[223,121,34],[247,162,71],[255,187,89],[255,218,128]],brown=[[108,46,7],[158,65,0],[198,99,18]],cloth=[[188,189,185],[226,226,222],[255,255,255]];
    const nearest=(s,p)=>p.reduce((a,b)=>b.reduce((n,v,k)=>n+(v-s[k])**2,0)<a.reduce((n,v,k)=>n+(v-s[k])**2,0)?b:a);
    const warm=c=>c[0]>90&&c[0]-c[1]>20&&c[1]-c[2]>15,face=(x,y)=>x>=32&&x<96&&y>=52&&y<128,sample=(x,y)=>[...tonal.slice((y*w+x)*4,(y*w+x)*4+3)];
    function warmSample(x,y,fallback){const c=sample(x,y);if(warm(c))return c;let best=null,dist=Infinity;for(let dy=-3;dy<=3;dy++)for(let dx=-3;dx<=3;dx++){const xx=x+dx,yy=y+dy;if(xx<0||xx>=w||yy<0||yy>=h)continue;const c=sample(xx,yy),d=dx*dx+dy*dy;if(warm(c)&&d<dist){best=c;dist=d;}}return best||fallback;}
    // White at the image border and eye whites stay white, as in approved art.
    const labels=new Int32Array(w*h).fill(-1),components=[],white=i=>raw[i*4+3]===255&&raw[i*4]===255&&raw[i*4+1]===255&&raw[i*4+2]===255;
    for(let start=0;start<w*h;start++)if(white(start)&&labels[start]===-1){const id=components.length,queue=[start],c={count:0,face:0,border:false};labels[start]=id;for(let k=0;k<queue.length;k++){const i=queue[k],x=i%w,y=Math.floor(i/w);c.count++;c.face+=Number(face(x,y));c.border ||= x<5||x>=w-5||y<5||y>=h-5;for(const j of[x>0?i-1:-1,x<w-1?i+1:-1,y>0?i-w:-1,y<h-1?i+w:-1])if(j>=0&&labels[j]===-1&&white(j)){labels[j]=id;queue.push(j);}}components.push(c);}
    let changed=0,ink=0;const palette=new Set();
    for(let y=0;y<h;y++)for(let x=0;x<w;x++){
     const i=y*w+x,at=i*4,rgb=[...raw.slice(at,at+3)];let c=rgb;
     if(raw[at+3]===0){ink++;palette.add([...out.slice(at,at+4)].join(','));continue;}
     if(raw[at+3]!==255)throw Error('Non-binary source alpha');
     if(rgb[0]===247&&rgb[1]===162&&rgb[2]===71)c=nearest(warmSample(x,y,rgb),skin);
     else if(rgb[0]===158&&rgb[1]===65&&rgb[2]===0){if(!face(x,y))c=nearest(warmSample(x,y,rgb),brown);}
     else if(rgb.every(v=>v===255)){const component=components[labels[i]],s=sample(x,y);if(!component.border&&!(component.face>0&&component.count<=180)&&Math.max(...s)-Math.min(...s)<20&&Math.min(...s)>130)c=nearest(s,cloth);}
     else throw Error('Unexpected original material palette');
     for(let k=0;k<3;k++)out[at+k]=c[k];changed+=Number(c.some((v,k)=>v!==rgb[k]));palette.add([...out.slice(at,at+4)].join(','));
    }
    if(palette.size>16||changed<20)throw Error('Study must meaningfully refine native art within16colors');
    return {rgba:Array.from(out),qa:{size:[128,160],palette_size:palette.size,changed_pixels:changed,ink_pixels_preserved:ink,alpha_changes:0,ink_changes:0}};
   },{base:Array.from(base),study:uri(study)});
   const rgba=Buffer.from(rendered.rgba),png=encodePng(128,160,rgba),target=OUT+'/'+key+'.png';
   fs.mkdirSync(path.join(ROOT,OUT),{recursive:true});fs.writeFileSync(path.join(ROOT,target),png);
   portraits[key]={path:'/assets/civil-staff/enhanced/'+key+'.png',width:128,height:160,source_path:'/assets/civil-staff/'+key+'.png',source_width:32,source_height:40,source_sha256:sha(source),sha256:sha(png),pixel_sha256:sha(rgba),base_rgba_sha256:sha(base),study,study_sha256:sha(read(study)),prompt,prompt_sha256:sha(read(prompt)),method:'imagegen_tone_study_native_scale4x_material_masks',qa:rendered.qa};
   assert.equal(sha(read(sourcePath)),sha(source),'Native original changed');
  }
 }finally{await browser.close();}
 const manifest={schema:'tk2-civil-portraits-v1',width:128,height:160,originals_retained:true,shared_templates:3,historical_likeness_claim:false,display_background:'#000000',approved_reference:{path:REFERENCE,sha256:sha(read(REFERENCE))},build:{tool:'tools/civil-portraits/build.cjs',tool_sha256:sha(read('tools/civil-portraits/build.cjs')),geometry:'Same approved native Scale4x and source-driven top/white preservation',appearance:'Imagegen studies transfer only finite palette tones; source alpha, ink, facial lines and white eye regions retained'},portraits};
 fs.writeFileSync(path.join(ROOT,OUT,'index.json'),JSON.stringify(manifest,null,2)+'\n');return check();
}
module.exports={check,build};
if(require.main===module)(async()=>console.log(JSON.stringify(process.argv.includes('--check')?check():await build())))().catch(error=>{console.error(error);process.exitCode=1;});
