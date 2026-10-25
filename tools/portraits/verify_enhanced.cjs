#!/usr/bin/env node
'use strict';
/** Independent integrity/coverage checks for the complete published derivatives. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {decodePng}=require('./prepare_enhanced.cjs');
const ROOT=path.resolve(__dirname,'../..'),WORK=path.join(ROOT,'art/portraits/enhancement-v1');
const read=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),'utf8'));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const plan=read('art/portraits/enhancement-v1/plan.json'),hd=read('game/config/portrait-enhanced.json');
const supplement={people:{}};
for(const name of ['historical-additions-v1','northwest-rising-v1','bian-zhang-v1']){
 const source=read(`art/portraits/${name}/enhanced-records.json`);
 assert.equal(source.schema,'tk2-portrait-supplement-enhanced-v1');
 for(const[id,row]of Object.entries(source.people)){
  assert(!supplement.people[id],'Supplemental identity is repeated');supplement.people[id]=row;
 }
}
const canonical=read('game/config/campaigns/people.json'),allIds=[...new Set([...Object.keys(plan.people),...Object.keys(supplement.people)])];
assert.deepEqual(Object.keys(hd.people).sort(),canonical.order.slice().sort());
assert.deepEqual(Object.keys(hd.people).sort(),allIds.sort());
const groupByPerson=new Map(plan.groups.flatMap(g=>g.person_ids.map(id=>[id,g]))),unique=new Set();
let changed=0,ink=0,approved=0;
for(const[id,row]of Object.entries(hd.people)){
 if(supplement.people[id]&&!plan.people[id]){
  assert.deepEqual(row,supplement.people[id]);
  const sourceBytes=fs.readFileSync(path.join(ROOT,'game',row.source_path)),source=decodePng(sourceBytes);
  const imageBytes=fs.readFileSync(path.join(ROOT,'game',row.path)),image=decodePng(imageBytes);
  assert.equal(sha(sourceBytes),row.source_sha256);assert.equal(sha(imageBytes),row.sha256);
  assert.equal(sha(image.rgba),row.pixel_sha256);assert.equal(image.width,128);assert.equal(image.height,160);
  assert.equal(source.width,32);assert.equal(source.height,40);
  for(let y=0;y<160;y++)for(let x=0;x<128;x++){
   const at=(y*128+x)*4,nativeAt=(Math.floor(y/4)*32+Math.floor(x/4))*4;
   assert(image.rgba.subarray(at,at+4).equals(source.rgba.subarray(nativeAt,nativeAt+4)),'Supplemental nearest4x identity drift:'+id);
  }
  assert.equal(row.provenance.base_method,'native32x40_exact_nearest4x');
  unique.add(row.pixel_sha256);continue;
 }
 const group=groupByPerson.get(id),source=plan.people[id];assert(group);
 assert.equal(row.path,'/assets/portraits/enhanced/'+id+'.png');assert.equal(row.source_path,source.source_path);
 assert.equal(row.source_sha256,source.source_sha256);
 assert.equal(sha(fs.readFileSync(path.join(ROOT,'game',source.source_path))),source.source_sha256,'Source altered:'+id);
 const bytes=fs.readFileSync(path.join(ROOT,'game',row.path)),img=decodePng(bytes);
 assert.equal(sha(bytes),row.sha256);assert.equal(sha(img.rgba),row.pixel_sha256);
 assert.equal(img.width,128);assert.equal(img.height,160);unique.add(row.pixel_sha256);
 if(group.approved_reference){assert.equal(row.sha256,plan.approved_reference.sha256);approved++;continue;}
 const baseBytes=fs.readFileSync(path.join(WORK,group.base_path)),base=decodePng(baseBytes);
 assert.equal(sha(baseBytes),group.base_png_sha256);assert.equal(sha(base.rgba),group.base_rgba_sha256);
 const palette=new Set();let different=0;
 for(let i=0;i<img.rgba.length;i+=4){
  assert(img.rgba[i+3]===0||img.rgba[i+3]===255);assert.equal(img.rgba[i+3],base.rgba[i+3],'Alpha/outline altered:'+id);
  if(base.rgba[i+3]===0){ink++;assert(img.rgba.subarray(i,i+4).equals(base.rgba.subarray(i,i+4)),'Black facial/outline stroke altered:'+id);}
  different+=Number(!img.rgba.subarray(i,i+4).equals(base.rgba.subarray(i,i+4)));
  palette.add(img.rgba.subarray(i,i+4).toString('hex'));
 }
 assert(palette.size<=16,'Palette drift:'+id);assert(different>=20,'Unenhanced output:'+id);changed+=different;
 assert.equal(row.provenance.group_id,group.id);assert.equal(row.provenance.base_rgba_sha256,group.base_rgba_sha256);
}
assert.equal(unique.size,plan.groups.length+Object.keys(supplement.people).filter(id=>!plan.people[id]).length,'Unexpected new image collision');
// Check the full old archive, including17 unbound originals, and retained art atlases.
const originals=read('game/config/portrait-originals.json'),generated=read('game/config/portrait-generated.json');
let originalsRetained=0;
for(const row of [...Object.values(originals.by_original_id),...Object.values(generated.by_person_id)]){
 const bytes=fs.readFileSync(path.join(ROOT,'game',row.path)),png=decodePng(bytes);
 assert.equal(sha(bytes),row.png_sha256);assert.equal(sha(png.rgba),row.rgba_sha256);originalsRetained++;
}
for(const a of generated.source_atlases)assert.equal(sha(fs.readFileSync(path.join(ROOT,a.path))),a.sha256);
const files=fs.readdirSync(path.join(ROOT,'game/assets/portraits/enhanced')).filter(f=>f.endsWith('.png'));
assert.equal(files.length,canonical.order.length);assert.equal(originalsRetained,237+generated.count);
const result={schema:'tk2-portrait-enhancement-verification-v1',people:canonical.order.length,uniqueEnhancedImages:unique.size,approvedReferencePeople:approved,oldPortraitFilesRetained:originalsRetained,originalSourceAtlasesRetained:generated.source_atlases.length,allSourceHashesMatch:true,allPersonBindingsMatch:true,allDimensions:[128,160],allNonReferenceInkAndAlphaMasksMatch:true,allNonReferencePalettesAtMost16Colors:true,protectedInkPixelsCompared:ink,totalEnhancedPixelsCompared:changed,allPublishedFileAndRgbaHashesMatch:true,unexpectedFiles:0,supplementalNearest4xPeople:Object.keys(supplement.people).length,scope:'Per-file automatic source, identity-mask, dimensions and hash audit; visual quality reviewed separately'};
fs.writeFileSync(path.join(WORK,'verification.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
