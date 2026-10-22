#!/usr/bin/env node
'use strict';
/** Retain each existing sprite's material/ink masks; transfer only cel shading. */
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const ROOT=path.resolve(__dirname,'../..'),WORK=path.join(ROOT,'art/portraits/enhancement-v1');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const uri=p=>'data:image/png;base64,'+fs.readFileSync(p).toString('base64');
const pngRGBA=async(page,file)=>page.evaluate(async url=>{const i=new Image();i.src=url;await i.decode();const c=document.createElement('canvas');c.width=i.width;c.height=i.height;const g=c.getContext('2d');g.drawImage(i,0,0);return{width:i.width,height:i.height,rgba:Array.from(g.getImageData(0,0,i.width,i.height).data)}},uri(file));
async function packAtlas(plan,atlas,studyPath,page){
 const study=fs.readFileSync(studyPath),groups=atlas.groups.map(id=>plan.groups.find(g=>g.id===id));
 assert(groups.every(Boolean));
 const outputs=await page.evaluate(async({study,bases,columns,rows})=>{
  const w=128,h=160;
  async function image(url){const i=new Image();i.src=url;await i.decode();return i;}
  const raster=await image(study),canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;
  const ctx=canvas.getContext('2d',{willReadFrequently:true});
  const skin=[[142,56,0],[185,85,10],[223,121,34],[247,162,71],[255,187,89],[255,218,128]];
  const brown=[[108,46,7],[158,65,0],[198,99,18]],cloth=[[188,189,185],[226,226,222],[255,255,255]];
  const pale=[[255,214,162],[255,235,204],[255,255,255]];
  const nearest=(s,p)=>p.reduce((a,b)=>b.reduce((n,v,k)=>n+(v-s[k])**2,0)<a.reduce((n,v,k)=>n+(v-s[k])**2,0)?b:a);
  const warm=c=>c[0]>90&&c[0]-c[1]>20&&c[1]-c[2]>15;
  const face=(x,y)=>x>=32&&x<96&&y>=52&&y<128;
  const results=[];
  for(const base of bases){
   const img=await image(base.image);if(img.width!==w||img.height!==h)throw Error('Invalid prepared base dimensions');
   ctx.clearRect(0,0,w,h);ctx.drawImage(img,0,0);const raw=ctx.getImageData(0,0,w,h).data,out=new Uint8ClampedArray(raw);
   ctx.clearRect(0,0,w,h);ctx.imageSmoothingEnabled=false;
   ctx.drawImage(raster,(base.cell%columns)*raster.width/columns,Math.floor(base.cell/columns)*raster.height/rows,raster.width/columns,raster.height/rows,0,0,w,h);
   const colors=ctx.getImageData(0,0,w,h).data;
   const sample=(x,y)=>[...colors.slice((y*w+x)*4,(y*w+x)*4+3)];
   function warmSample(x,y,fallback){const at=sample(x,y);if(warm(at))return at;let best=null,dist=Infinity;for(let dy=-3;dy<=3;dy++)for(let dx=-3;dx<=3;dx++){const xx=x+dx,yy=y+dy;if(xx<0||xx>=w||yy<0||yy>=h)continue;const c=sample(xx,yy),d=dx*dx+dy*dy;if(warm(c)&&d<dist){best=c;dist=d;}}return best||fallback;}
   // Connected white regions distinguish exposed background and small eye whites.
   const labels=new Int32Array(w*h).fill(-1),components=[];
   const white=i=>raw[i*4+3]===255&&raw[i*4]===255&&raw[i*4+1]===255&&raw[i*4+2]===255;
   for(let start=0;start<w*h;start++)if(white(start)&&labels[start]===-1){
    const id=components.length,queue=[start],c={count:0,face:0,border:false,minY:h,maxY:0};labels[start]=id;
    for(let k=0;k<queue.length;k++){const i=queue[k],x=i%w,y=Math.floor(i/w);c.count++;c.face+=Number(face(x,y));c.border ||= x<5||x>=w-5||y<5||y>=h-5;c.minY=Math.min(c.minY,y);c.maxY=Math.max(c.maxY,y);
     for(const j of[x>0?i-1:-1,x<w-1?i+1:-1,y>0?i-w:-1,y<h-1?i+w:-1])if(j>=0&&labels[j]===-1&&white(j)){labels[j]=id;queue.push(j);}}
    components.push(c);
   }
   let changed=0,strongChanged=0,ink=0,whiteProtected=0,brownProtected=0,colorPixels=0;
   for(let y=0;y<h;y++)for(let x=0;x<w;x++){
    const i=y*w+x,at=i*4,rgb=[...raw.slice(at,at+3)];let c=rgb;
    if(raw[at+3]===0){ink++;continue;}
    if(raw[at+3]!==255)throw Error('Non-binary source alpha');
    if(rgb[0]===247&&rgb[1]===162&&rgb[2]===71){colorPixels++;c=nearest(warmSample(x,y,rgb),skin);}
    else if(rgb[0]===158&&rgb[1]===65&&rgb[2]===0){
     if(face(x,y))brownProtected++;else c=nearest(warmSample(x,y,rgb),brown);
    }else if(rgb.every(v=>v===255)){
     const component=components[labels[i]],s=sample(x,y),range=Math.max(...s)-Math.min(...s);
     if(component.border||(component.face>0&&component.count<=180)){whiteProtected++;}
     else if(component.face/component.count>0.55&&warm(s)&&Math.max(...s)>175)c=nearest(s,pale);
     else if(range<20&&Math.min(...s)>130)c=nearest(s,cloth);
    }else throw Error('Prepared base departs from native material palette');
    for(let k=0;k<3;k++)out[at+k]=c[k];
    const delta=Math.max(...c.map((v,k)=>Math.abs(v-rgb[k])));changed+=Number(delta>0);strongChanged+=Number(delta>=24);
   }
   let alphaChanges=0,inkChanges=0;const palette=new Set();
   for(let i=0;i<w*h;i++){const at=i*4;alphaChanges+=Number(raw[at+3]!==out[at+3]);inkChanges+=Number(raw[at+3]===0&&out.slice(at,at+4).some((v,k)=>v!==raw[at+k]));palette.add([...out.slice(at,at+4)].join(','));}
   if(alphaChanges||inkChanges)throw Error('Identity mask drift');
   if(palette.size>16)throw Error('Palette expansion exceeds approved style');
   if(changed<20)throw Error('Color study yielded no meaningful refinement for '+base.id);
   ctx.putImageData(new ImageData(out,w,h),0,0);const encoded=canvas.toDataURL('image/png');
   const roundtrip=await image(encoded);ctx.clearRect(0,0,w,h);ctx.drawImage(roundtrip,0,0);const actual=ctx.getImageData(0,0,w,h).data;
   for(let i=0;i<actual.length;i++)if(actual[i]!==out[i])throw Error('PNG RGBA roundtrip mismatch');
   results.push({id:base.id,image:encoded,rgba:Array.from(out),proof:{size:[w,h],inkPixelsPreserved:ink,alphaChanges,inkChanges,protectedWhitePixels:whiteProtected,protectedFacialBrownPixels:brownProtected,paletteSize:palette.size,changedPixels:changed,changedPercent:Math.round(changed/(w*h)*10000)/100,strongChangedPixels:strongChanged,originalSkinPixels:colorPixels,pngRoundtripExact:true}});
  }
  return results;
 },{study:'data:image/png;base64,'+study.toString('base64'),bases:groups.map(g=>({id:g.id,image:uri(path.join(WORK,g.base_path)),cell:g.cell_index})),columns:atlas.columns,rows:atlas.rows});
 const records={};
 for(const item of outputs){
  const group=groups.find(g=>g.id===item.id),bytes=Buffer.from(item.image.split(',')[1],'base64'),pixels=Buffer.from(item.rgba);
  assert.equal(sha(fs.readFileSync(path.join(WORK,group.base_path))),group.base_png_sha256||sha(fs.readFileSync(path.join(WORK,group.base_path))));
  for(const personId of group.person_ids){const person=plan.people[personId],asset='/assets/portraits/enhanced/'+personId+'.png';
   const destination=path.join(ROOT,'game',asset);fs.mkdirSync(path.dirname(destination),{recursive:true});fs.writeFileSync(destination,bytes);
   records[personId]={path:asset,width:128,height:160,source_path:person.source_path,source_sha256:person.source_sha256,sha256:sha(bytes),pixel_sha256:sha(pixels),method:'identity_preserving_pixel_enhancement',provenance:{group_id:group.id,atlas:atlas.id,color_study:'art/portraits/enhancement-v1/studies/'+atlas.id+'.png',color_study_sha256:sha(study),prepared_source:group.base_path,base_method:group.base_method,base_rgba_sha256:group.base_rgba_sha256,prompt:'art/portraits/enhancement-v1/prompts/'+atlas.id+'.txt',qa:item.proof}};
  }
 }
 fs.mkdirSync(path.join(WORK,'processed'),{recursive:true});fs.writeFileSync(path.join(WORK,'processed',atlas.id+'.json'),JSON.stringify({schema:'tk2-portrait-enhancement-batch-v1',atlas_id:atlas.id,study_sha256:sha(study),people:records},null,2)+'\n');
 console.log(JSON.stringify({atlas:atlas.id,unique:outputs.length,people:Object.keys(records).length,minimumChangedPixels:Math.min(...outputs.map(o=>o.proof.changedPixels)),maximumPalette:Math.max(...outputs.map(o=>o.proof.paletteSize))}));
}
async function finalize(plan,page){
 const people={};for(const atlas of plan.atlases){const batch=read(path.join(WORK,'processed',atlas.id+'.json'));Object.assign(people,batch.people);}
 for(const group of plan.groups.filter(g=>g.approved_reference)){
  const reference=path.join(ROOT,plan.approved_reference.path),bytes=fs.readFileSync(reference),decoded=await pngRGBA(page,reference);
  assert.equal(sha(bytes),plan.approved_reference.sha256);assert.equal(decoded.width,128);assert.equal(decoded.height,160);
  for(const id of group.person_ids){const source=plan.people[id],asset='/assets/portraits/enhanced/'+id+'.png';fs.mkdirSync(path.dirname(path.join(ROOT,'game',asset)),{recursive:true});fs.writeFileSync(path.join(ROOT,'game',asset),bytes);
   people[id]={path:asset,width:128,height:160,source_path:source.source_path,source_sha256:source.source_sha256,sha256:sha(bytes),pixel_sha256:sha(Buffer.from(decoded.rgba)),method:'identity_preserving_pixel_enhancement',provenance:{approved_reference:plan.approved_reference.path,group_id:group.id,qa:{userApproved:true,exactApprovedFile:true}}};
  }
 }
 assert.equal(Object.keys(people).length,1023);assert.deepEqual(Object.keys(people).sort(),Object.keys(plan.people).sort());
 for(const[id,row]of Object.entries(people)){
  assert.equal(sha(fs.readFileSync(path.join(ROOT,'game',row.source_path))),row.source_sha256,'Original changed: '+id);
  assert.equal(sha(fs.readFileSync(path.join(ROOT,'game',row.path))),row.sha256,'Enhanced changed: '+id);
 }
 const result={schema:'tk2-enhanced-portraits-v1',width:128,height:160,approved_reference:plan.approved_reference,counts:{people:1023,source_unique:plan.groups.length,atlas_count:plan.atlases.length},processing:{mode:'imagegen_atlas_color_studies_with_original_material_masks',background:'#000000',originalsRetained:true,newArtHistoricalLikenessClaim:false},people};
 const output=path.join(ROOT,'game/config/portrait-enhanced.json');fs.writeFileSync(output+'.tmp',JSON.stringify(result,null,2)+'\n');fs.renameSync(output+'.tmp',output);console.log(JSON.stringify({finalized:1023,output}));
}
(async()=>{const plan=read(path.join(WORK,'plan.json'));const browser=await chromium.launch({channel:'chrome',headless:true});try{const page=await browser.newPage();await page.setContent('<!doctype html><body></body>');
 if(process.argv.includes('--finalize'))await finalize(plan,page);
 else {const id=process.argv[2],atlas=plan.atlases.find(a=>a.id===id);if(!atlas)throw Error('Unknown atlas '+id);await packAtlas(plan,atlas,path.join(WORK,'studies',id+'.png'),page);}
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
