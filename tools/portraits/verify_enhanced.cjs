#!/usr/bin/env node
'use strict';
/** Independent integrity/coverage checks for the complete published derivatives. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {decodePng}=require('./prepare_enhanced.cjs');
const ROOT=path.resolve(__dirname,'../..'),WORK=path.join(ROOT,'art/portraits/enhancement-v1');
const read=p=>JSON.parse(fs.readFileSync(path.join(ROOT,p),'utf8'));
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function redrawFile(relative,extension){
 assert.equal(typeof relative,'string');assert(relative.startsWith('art/portraits/supplement-hd-v2/'));
 assert(!path.isAbsolute(relative)&&!relative.split('/').includes('..')&&relative.endsWith(extension));
 const full=fs.realpathSync(path.join(ROOT,relative)),allowed=fs.realpathSync(path.join(ROOT,'art/portraits/supplement-hd-v2'))+path.sep;
 assert(full.startsWith(allowed),'Redraw provenance escapes retained art directory');return fs.readFileSync(full);
}
const plan=read('art/portraits/enhancement-v1/plan.json'),hd=read('game/config/portrait-enhanced.json');
const supplement={people:{}};
for(const name of ['historical-additions-v1','northwest-rising-v1','bian-zhang-v1']){
 const source=read(`art/portraits/${name}/enhanced-records.json`);
 assert.equal(source.schema,'tk2-portrait-supplement-enhanced-v1');
 for(const[id,row]of Object.entries(source.people)){
  assert(!supplement.people[id],'Supplemental identity is repeated');supplement.people[id]=row;
 }
}
const legacySupplement={...supplement.people},redrawnSupplement=read('art/portraits/supplement-hd-v2/enhanced-records.json');
assert.equal(redrawnSupplement.schema,'tk2-portrait-supplement-enhanced-v1');
assert.deepEqual(Object.keys(redrawnSupplement.people).sort(),Object.keys(legacySupplement).sort());
supplement.people=redrawnSupplement.people;
const canonical=read('game/config/campaigns/people.json'),allIds=[...new Set([...Object.keys(plan.people),...Object.keys(supplement.people)])];
const redrawPath='art/portraits/supplement-hd-v2/plan.json',redrawBytes=redrawFile(redrawPath,'.json'),redraw=JSON.parse(redrawBytes);
assert.equal(redraw.schema,'tk2-portrait-redraw-v2');assert.deepEqual(redraw.size,[128,160]);
assert.deepEqual(Object.keys(redraw.people).sort(),Object.keys(supplement.people).sort());
assert.deepEqual(Object.keys(hd.people).sort(),canonical.order.slice().sort());
assert.deepEqual(Object.keys(hd.people).sort(),allIds.sort());
const groupByPerson=new Map(plan.groups.flatMap(g=>g.person_ids.map(id=>[id,g]))),unique=new Set();
let changed=0,ink=0,approved=0,redrawn=0,minimumRedrawChangedPixels=Infinity,minimumRedrawNonUniformBlocks=Infinity;
for(const[id,row]of Object.entries(hd.people)){
 if(supplement.people[id]&&!plan.people[id]){
  const original=legacySupplement[id],binding=redraw.people[id],p=row.provenance;
  assert.deepEqual(row,supplement.people[id]);
  assert.equal(row.rendering,'redrawn128');assert.equal(p.base_method,'identity_preserving_redrawn128');
  assert.equal(row.source_path,original.source_path);assert.equal(row.source_sha256,original.source_sha256);
  assert.equal(p.redraw_plan,redrawPath);assert.equal(p.redraw_plan_sha256,sha(redrawBytes));
  assert.equal(binding.native.path,'game'+row.source_path);assert.equal(binding.native.sha256,original.source_sha256);
  assert.equal(p.original_enhanced,binding.original_enhanced.path);assert.equal(p.original_enhanced_sha256,original.sha256);
  assert.equal(binding.original_enhanced.sha256,original.sha256);
  const archivedBytes=redrawFile(p.original_enhanced,'.png'),archived=decodePng(archivedBytes);
  assert.equal(archived.width,128);assert.equal(archived.height,160);
  assert.equal(sha(archivedBytes),original.sha256);assert.equal(sha(archived.rgba),binding.original_enhanced.rgba_sha256);
  assert.equal(sha(archived.rgba),original.pixel_sha256);
  for(const key of ['generated_source','prompt']){
   assert.equal(p[key],binding[key]);assert.equal(p[key+'_sha256'],binding[key+'_sha256']);
   assert.equal(sha(redrawFile(p[key],key==='prompt'?'.txt':'.png')),p[key+'_sha256']);
  }
  const authoredSource=decodePng(redrawFile(p.generated_source,'.png'));
  assert(authoredSource.width>=128&&authoredSource.height>=160&&authoredSource.width<=4096&&authoredSource.height<=4096);
  assert.deepEqual(p.qa.source_size,[authoredSource.width,authoredSource.height]);
  const sourceBytes=fs.readFileSync(path.join(ROOT,'game',row.source_path)),source=decodePng(sourceBytes);
  const imageBytes=fs.readFileSync(path.join(ROOT,'game',row.path)),image=decodePng(imageBytes);
  assert.equal(sha(sourceBytes),row.source_sha256);assert.equal(sha(imageBytes),row.sha256);
  assert.equal(sha(image.rgba),row.pixel_sha256);assert.equal(image.width,128);assert.equal(image.height,160);
  assert.equal(source.width,32);assert.equal(source.height,40);
  assert.equal(sha(source.rgba),binding.native.rgba_sha256);
  const palette=new Set();let different=0;
  for(let y=0;y<160;y++)for(let x=0;x<128;x++){
   const at=(y*128+x)*4,nativeAt=(Math.floor(y/4)*32+Math.floor(x/4))*4;
   assert(archived.rgba.subarray(at,at+4).equals(source.rgba.subarray(nativeAt,nativeAt+4)),'Archived oldHD no longer preserves its native nearest4x:'+id);
   different+=Number(!image.rgba.subarray(at,at+4).equals(source.rgba.subarray(nativeAt,nativeAt+4)));
   assert(image.rgba[at+3]===0||image.rgba[at+3]===255);palette.add(image.rgba.subarray(at,at+4).toString('hex'));
  }
  assert(different>=1024,'Redraw has insufficient actual detail beyond nearest4x:'+id);
  assert(palette.size>4&&palette.size<=16,'Redraw palette departs from5..16colors:'+id);
  let nonUniformBlocks=0;
  for(let by=0;by<40;by++)for(let bx=0;bx<32;bx++){
   const colors=new Set();for(let y=0;y<4;y++)for(let x=0;x<4;x++){
    const at=((by*4+y)*128+bx*4+x)*4;colors.add(image.rgba.subarray(at,at+4).toString('hex'));
   }
   nonUniformBlocks+=Number(colors.size>1);
  }
  assert(nonUniformBlocks>=20,'Redraw still consists of coarse4x4 blocks:'+id);
  assert.deepEqual(p.qa.size,[128,160]);assert.equal(p.qa.changedPixels,different);assert.equal(p.qa.paletteSize,palette.size);assert.equal(p.qa.nearest4xExact,false);
  assert.equal(p.qa.nonUniformBlocks4x4,nonUniformBlocks);
  minimumRedrawNonUniformBlocks=Math.min(minimumRedrawNonUniformBlocks,nonUniformBlocks);
  minimumRedrawChangedPixels=Math.min(minimumRedrawChangedPixels,different);redrawn++;
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
const result={schema:'tk2-portrait-enhancement-verification-v1',people:canonical.order.length,uniqueEnhancedImages:unique.size,approvedReferencePeople:approved,oldPortraitFilesRetained:originalsRetained,originalSourceAtlasesRetained:generated.source_atlases.length,allSourceHashesMatch:true,allPersonBindingsMatch:true,allDimensions:[128,160],allLegacyNonReferenceInkAndAlphaMasksMatch:true,allNonReferencePalettesAtMost16Colors:true,protectedInkPixelsCompared:ink,totalEnhancedPixelsCompared:changed,allPublishedFileAndRgbaHashesMatch:true,unexpectedFiles:0,supplementalNearest4xPeople:0,supplementalRedrawn128People:redrawn,oldSupplementEnhancedFilesRetained:redrawn,minimumRedrawChangedPixels,minimumRedrawNonUniformBlocks,scope:'Per-file source, dimensions, hashes and legacy mask audit;7 redraws additionally require5..16colors, at least5percent actual pixel changes from nearest4x and20 nonuniform4x4 blocks. Visual likeness and quality reviewed separately'};
fs.writeFileSync(path.join(WORK,'verification.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
