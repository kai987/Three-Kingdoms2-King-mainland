// Relocate existing native mountain sprite instances in the authored map scene.
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),read=f=>JSON.parse(fs.readFileSync(path.join(root,f)));
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const p=await browser.newPage({viewport:{width:1352,height:1024},deviceScaleFactor:1});
  await p.setContent(fs.readFileSync(path.join(root,'expansion/map/city-map-city-sea-preview-v42.html'),'utf8'));
  const spec=read('game/config/city-map-refinement.json');
  for(const m of spec.moves)m.cells=m.runs.flatMap(([y,x,count])=>Array.from({length:count},(_,i)=>[x+i*spec.cellSize,y]));
  const result=await p.evaluate(async({spec,terrain,ground})=>{
   const cities=[...document.querySelectorAll('[data-city]')].map(e=>e.outerHTML),svg=document.querySelector('#map svg').outerHTML;
   const a=new Image(),g=new Image();a.src=terrain;g.src=ground;await Promise.all([a.decode(),g.decode()]);
   const c=document.createElement('canvas');c.width=a.width;c.height=a.height;const ctx=c.getContext('2d',{willReadFrequently:true});
   ctx.drawImage(a,0,0);const original=ctx.getImageData(0,0,c.width,c.height);ctx.drawImage(g,0,0);const floor=ctx.getImageData(0,0,c.width,c.height),out=ctx.createImageData(c.width,c.height);out.data.set(original.data);
   const edited=new Set(),destinations=new Set();let sourcePixels=0,destinationPixels=0;
   for(const m of spec.moves)for(const[x,y]of m.cells)for(let dy=0;dy<2;dy++)for(let dx=0;dx<2;dx++){
    const key=(y+dy)*c.width+x+dx+spec.mapCropX;edited.add(key);sourcePixels++;
    out.data.set(floor.data.subarray(key*4,key*4+4),key*4);
   }
   for(const m of spec.moves)for(const[x,y]of m.cells)for(let dy=0;dy<2;dy++)for(let dx=0;dx<2;dx++){
    const from=(y+dy)*c.width+x+dx+spec.mapCropX,to=(y+dy+m.dy)*c.width+x+dx+spec.mapCropX+m.dx;
    if(destinations.has(to))throw Error('Mountain destination masks overlap');destinations.add(to);edited.add(to);destinationPixels++;
    out.data.set(original.data.subarray(from*4,from*4+4),to*4);
   }
   let outsideChanges=0,translatedMismatches=0;
   for(let i=0;i<c.width*c.height;i++)if(!edited.has(i)&&original.data.subarray(i*4,i*4+4).some((v,k)=>v!==out.data[i*4+k]))outsideChanges++;
   for(const m of spec.moves)for(const[x,y]of m.cells)for(let dy=0;dy<2;dy++)for(let dx=0;dx<2;dx++){
    const from=(y+dy)*c.width+x+dx+spec.mapCropX,to=(y+dy+m.dy)*c.width+x+dx+spec.mapCropX+m.dx;
    if(original.data.subarray(from*4,from*4+4).some((v,k)=>v!==out.data[to*4+k]))translatedMismatches++;
   }
   ctx.putImageData(out,0,0);document.querySelector('#map canvas').style.backgroundImage=`url(${c.toDataURL('image/png')})`;
   document.querySelector('#road-legend').remove();
   return{sourcePixels,destinationPixels,outsideChanges,translatedMismatches,
    cityPositionsUnchanged:JSON.stringify(cities)===JSON.stringify([...document.querySelectorAll('[data-city]')].map(e=>e.outerHTML)),
    riversRoadsAndCityVectorsUnchanged:svg===document.querySelector('#map svg').outerHTML};
  },{spec,terrain:'data:image/png;base64,'+fs.readFileSync(path.join(root,spec.sourceTerrain)).toString('base64'),ground:'data:image/png;base64,'+fs.readFileSync(path.join(root,spec.ground)).toString('base64')});
  assert.equal(result.sourcePixels,result.destinationPixels);assert.equal(result.outsideChanges,0);assert.equal(result.translatedMismatches,0);
  assert(result.cityPositionsUnchanged&&result.riversRoadsAndCityVectorsUnchanged);
  const hazards=process.argv.includes('--hazards');
  const travel=process.argv.includes('--travel')||hazards;
  if(travel){
   const edited=await p.evaluate(()=>{
    const terrain=document.querySelector('#map canvas').style.backgroundImage;
    const city=document.querySelector('[data-city="wuwei"]');if(!city)throw Error('Missing original Wuwei sprite');city.remove();
    let removed=0;
    for(const path of document.querySelectorAll('path[d]')){
     const d=path.getAttribute('d'),next=d.replace(/M124 120[^M]*/g,'');
     if(next!==d){path.setAttribute('d',next);removed++;}
    }
    if(removed!==2)throw Error('Expected the two native land-road stroke layers');
    return {removedOriginalCity:'wuwei',removedRoadStrokeLayers:removed,terrainUnchanged:terrain===document.querySelector('#map canvas').style.backgroundImage};
   });
   assert(edited.terrainUnchanged);Object.assign(result,edited);
  }
  if(hazards){
   const removedSeaPaths=await p.evaluate(()=>{
    const paths=[...document.querySelectorAll('svg path[stroke-dasharray]')];
    for(const path of paths)path.remove();
    return paths.length;
   });
   assert.equal(removedSeaPaths,1);result.removedBakedSeaPaths=removedSeaPaths;
  }
  await p.screenshot({path:path.join(__dirname,hazards?'assets/map-navigation.png':travel?'assets/map-campaign.png':'assets/map-basin.png')});
  console.log(JSON.stringify(result));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
