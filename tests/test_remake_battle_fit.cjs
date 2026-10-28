/* Exercise actual layout fitting without a DOM/game command or random source. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync(require.resolve('../game/battle-scene.js'),'utf8');
const begin=source.indexOf('  function fit(){'),end=source.indexOf('  function mount(',begin);
assert(begin>=0&&end>begin,'Controller fitting must remain an isolated display operation');
function style(){const values=new Map();return{writes:0,getPropertyValue:key=>values.get(key)||'',setProperty(key,value){this.writes++;values.set(key,value);},removeProperty(key){if(values.delete(key))this.writes++;}};}
function fitted({backing=[1024,960],viewport=[960,900],layoutWidth=1400,open=true}={}){
 const box={clientWidth:viewport[0],clientHeight:viewport[1]},canvas={width:backing[0],height:backing[1],style:{}};
 const roster={open},layout={clientWidth:layoutWidth,style:style(),querySelector:()=>roster};
 const host={style:style(),querySelector:()=>box,closest:()=>layout};
 const sandbox={host,canvas,WIDTH:256,HEIGHT:240,RESOLUTION_SCALE:4,Math};
 vm.runInNewContext(source.slice(begin,end)+'\nfit();',sandbox,{filename:'actual-battle-fit.js'});
 return{box,canvas,host,layout,roster,again:()=>vm.runInNewContext('fit()',sandbox)};
}
const normal=fitted();
assert.equal(normal.canvas.style.width,'960px');assert.equal(normal.canvas.style.height,'900px','Fractional scale must use available height rather than dropping to3x');
assert.equal(normal.host.style.getPropertyValue('--battle-canvas-aspect'),'256/240');
const writes=[normal.host.style.writes,normal.layout.style.writes];normal.again();
assert.deepEqual([normal.host.style.writes,normal.layout.style.writes],writes,'ResizeObserver repeats must not keep writing identical grid sizes');
const tactical=fitted({backing:[1984,1536],viewport:[800,640],open:false});
assert.equal(tactical.host.style.getPropertyValue('--battle-canvas-aspect'),'496/384');
assert.equal(tactical.canvas.style.width,'800px');assert.equal(tactical.canvas.style.height,'619px');
assert.equal(tactical.roster.open,true,'A wide roster stays visible without a second click');
assert.equal(tactical.layout.style.getPropertyValue('--battle-board-width'),'826px','Right column follows full-map aspect, reserving at least248px for the roster');
const mobile=fitted({backing:[1984,1536],viewport:[390,302],layoutWidth:390,open:false});
assert.equal(mobile.canvas.style.width,'390px');assert.equal(mobile.canvas.style.height,'301px');
assert.equal(mobile.roster.open,false,'Fitting must not reopen a user-collapsed mobile roster');
assert.equal(mobile.layout.style.getPropertyValue('--battle-board-width'),'');
const huge=fitted({backing:[1984,1536],viewport:[5000,5000],layoutWidth:8000});
assert.equal(huge.canvas.style.width,'1984px');assert.equal(huge.canvas.style.height,'1536px','Never upscale beyond the4x backing resolution');
console.log('battle fit: full tactical/close-up aspects, fractional sizing,4x cap, wide roster, mobile collapse and idempotent observer passed');
