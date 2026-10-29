'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const tool=require('../tools/soldier-combat-actions/build.cjs');
const {decodePng}=require('../tools/portraits/prepare_enhanced.cjs');
function fixture(rows=1){
 const width=256,height=rows*64+16,rgba=Buffer.alloc(width*height*4);
 function pixel(x,y,color){const at=(y*width+x)*4;for(let c=0;c<3;c++)rgba[at+c]=color[c];rgba[at+3]=255;}
 function line(x0,y0,x1,y1,color){const steps=Math.max(Math.abs(x1-x0),Math.abs(y1-y0));for(let i=0;i<=steps;i++)pixel(Math.round(x0+(x1-x0)*i/steps),Math.round(y0+(y1-y0)*i/steps),color);}
 for(let row=0;row<rows;row++)for(let pose=0;pose<4;pose++){
  const cx=30+pose*64,base=55+row*64;
  for(let y=base-26;y<base;y++)for(let x=cx-5;x<cx+5;x++)pixel(x,y,tool.COLORS.black);
  for(let y=base-23;y<base-3;y++)for(let x=cx-3;x<cx+3;x++)pixel(x,y,y<base-19?tool.COLORS.peach:tool.COLORS.friendly);
  const tips=[[cx+24,base-14],[cx+5,base-44],[cx+27,base-5],[cx+12,base-30]];
  line(cx+2,base-14,...tips[pose],tool.COLORS.friendly);
  pixel(cx-4,base,tool.COLORS.black);pixel(cx+4,base,tool.COLORS.black);
 }
 return{width,height,rgba};
}
const source=fixture(),before=Buffer.from(source.rgba),figures=tool.splitFigures(source,1),fitted=tool.fitFigures(figures);
assert.equal(figures.length,4);assert(source.rgba.equals(before),'Packing cannot repaint source studies');
for(let n=1;n<4;n++)assert(figures[n].source_rect[0]>figures[n-1].source_rect[0]);
assert.equal(tool.splitFigures(fixture(2),2).length,8);
const friendly=tool.packAction('infantry','melee','friendly',fitted.frames),enemy=tool.packAction('infantry','melee','enemy',fitted.frames);
assert.deepEqual(friendly.row.frames.map(r=>r.phase),['ready','windup','strike','recover']);
assert.deepEqual(friendly.row.frames.map(r=>r.source_rect),[[0,0,64,64],[64,0,64,64],[128,0,64,64],[192,0,64,64]]);
assert.equal(new Set(friendly.row.frame_pixel_sha256).size,4);
const a=decodePng(friendly.bytes),b=decodePng(enemy.bytes);assert.equal(a.width,256);assert.equal(a.height,64);
let uniform=0,shared=0,detail=0;
for(let y=0;y<64;y++)for(let x=0;x<256;x++){
 const at=(y*256+x)*4,origin=(Math.floor(y/4)*4*256+Math.floor(x/4)*4)*4;
 if(!a.rgba.subarray(at,at+4).equals(a.rgba.subarray(origin,origin+4)))detail++;
 assert.equal(a.rgba[at+3],b.rgba[at+3]);assert([0,255].includes(a.rgba[at+3]));
 if(!a.rgba[at+3])continue;
 if(a.rgba.subarray(at,at+3).equals(Buffer.from(tool.COLORS.friendly))){assert(b.rgba.subarray(at,at+3).equals(Buffer.from(tool.COLORS.enemy)));uniform++;}
 else{assert(a.rgba.subarray(at,at+4).equals(b.rgba.subarray(at,at+4)));shared++;}
}
assert(uniform&&shared&&detail,'64px frames must retain source detail rather than repeat 16px blocks');
assert.equal(tool.colorKey([0,220,220]),1);assert.equal(tool.colorKey(tool.COLORS.friendly),1);assert.equal(tool.colorKey(tool.COLORS.peach),2);assert.equal(tool.colorKey([0,0,0]),0);
const fragments=new Int8Array(64*64).fill(-1);
for(let y=2;y<14;y++)for(let x=2;x<14;x++)fragments[y*64+x]=x%3;
for(let y=46;y<58;y++)for(let x=46;x<58;x++)fragments[y*64+x]=x%3;
assert.throws(()=>tool.validateFrame(fragments),/visible and connected/);
const clipped=new Int8Array(fitted.frames[0].keys);clipped[0]=0;
assert.throws(()=>tool.validateFrame(clipped),/transparent margin/);
const originalSize=new Int8Array(16*16).fill(0);
assert.throws(()=>tool.validateFrame(originalSize),/64px/);
assert.throws(()=>tool.packAction('infantry','ranged','friendly',fitted.frames));
assert.throws(()=>tool.packAction('infantry','melee','friendly',Array(4).fill(fitted.frames[0])),/four visibly different/);
const opaque=fixture();for(let i=3;i<opaque.rgba.length;i+=4)opaque.rgba[i]=255;
assert.throws(()=>tool.splitFigures(opaque,1),/transparent background/);
assert.throws(()=>tool.safeRead('../outside.png'),/Unsafe/);
assert.throws(()=>tool.safeDirectory('/tmp/private'),/Unsafe/);
if(!process.argv.includes('--unit-only')){
 const protectedFiles=['game/assets/siege-original/index.json',...tool.TYPES.flatMap(type=>['friendly','enemy'].map(side=>`game/assets/siege-original/sprite-${type}-${side}-0.png`))];
 const originals=protectedFiles.map(file=>tool.sha(fs.readFileSync(path.join(tool.ROOT,file))));
 const result=tool.check();assert.equal(result.atlases,10);assert.equal(result.frames,40);assert.deepEqual(result.frame_size,[64,64]);
 assert.deepEqual(protectedFiles.map(file=>tool.sha(fs.readFileSync(path.join(tool.ROOT,file)))),originals);
}
console.log('soldier combat assets:4-frame pose separation, 64px detail and hard alpha, original 3-color side palettes, shared skin/horse/alpha, unsafe paths and original preservation passed');
