/* Dependency-free invariants for the map's presentation-only camera. */
'use strict';
const assert=require('node:assert/strict');
const{Camera,MIN_ZOOM,MAX_ZOOM,attach}=require('../game/map-navigation.js');
const near=(a,b)=>assert(Math.abs(a-b)<1e-7,`${a} != ${b}`);
function bounded(c){const b=c.box(),w=c.world;assert(c.zoom>=MIN_ZOOM&&c.zoom<=MAX_ZOOM);for(const n of Object.values(b))assert(Number.isFinite(n));if(b.width<w.width){assert(b.x>=w.x-1e-7);assert(b.x+b.width<=w.x+w.width+1e-7)}else near(c.x,w.x+w.width/2);if(b.height<w.height){assert(b.y>=w.y-1e-7);assert(b.y+b.height<=w.y+w.height+1e-7)}else near(c.y,w.y+w.height/2);}
const world={x:-120,y:45,width:1352,height:1024};
const emptyInitial=new Camera(world,1000,500,null);near(emptyInitial.zoom,1);bounded(emptyInitial);
const c=new Camera(world,1000,500);near(c.box().height,1024);near(c.box().width,2048);near(c.zoom,1);bounded(c);
c.panPixels(1e8,-1e8);bounded(c);near(c.x,556);near(c.y,557);
c.focus(556,557,2);const anchor=c.point(.6,.4);c.zoomAt(3,.6,.4);near(c.point(.6,.4).x,anchor.x);near(c.point(.6,.4).y,anchor.y);bounded(c);
c.zoomAt(1e12);near(c.zoom,4);c.panPixels(1e10,-1e10);bounded(c);near(c.box().x,world.x);near(c.box().y+c.box().height,world.y+world.height);
c.zoomAt(-100);near(c.zoom,1);bounded(c);c.focus(1e20,-1e20,4);bounded(c);
c.focus(556,557,3);const snapshot=c.snapshot();c.resize(500,1000);near(c.zoom,snapshot.zoom);bounded(c);c.resize(1500,800);near(c.zoom,3);bounded(c);
for(const viewport of [[390,360],[1500,650],[1,1],[0,NaN]])for(const zoom of [0,1,2,4,999,NaN]){const camera=new Camera(world,...viewport,{zoom});camera.panPixels(-1e8,1e8);bounded(camera);camera.reset();near(camera.zoom,1);near(camera.x,556);near(camera.y,557);}
assert.throws(()=>new Camera({width:0,height:10},100,100),/Invalid map bounds/);

/* Pointer gesture completion must not steal the next intentional city tap. */
class Surface{
 constructor(){this.listeners=new Map();this.dataset={};this.captured=new Set();this.classes=new Set();this.classList={add:s=>this.classes.add(s),remove:s=>this.classes.delete(s)};}
 addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,new Set());this.listeners.get(name).add(fn);}
 removeEventListener(name,fn){this.listeners.get(name)?.delete(fn);}
 fire(name,event={}){const e={pointerId:1,pointerType:'mouse',button:0,clientX:400,clientY:250,detail:1,preventDefault(){this.prevented=true},stopImmediatePropagation(){this.stopped=true},...event};for(const fn of this.listeners.get(name)||[])fn(e);return e;}
 setAttribute(name,value){this[name]=value;}
 getBoundingClientRect(){return{left:0,top:0,width:1000,height:500};}
 setPointerCapture(id){this.captured.add(id);}
 hasPointerCapture(id){return this.captured.has(id);}
 releasePointerCapture(id){this.captured.delete(id);}
}
const win=new Surface();win.performance={now:()=>100};const svg=new Surface();svg.ownerDocument={defaultView:win};
let changes=0;const nav=attach(svg,{world,initial:null,onChange:()=>changes++});near(nav.snapshot().zoom,1);nav.focus(556,557,3);
svg.fire('pointerdown');win.fire('pointermove',{clientX:403});assert(!svg.captured.size);win.fire('pointerup',{clientX:403});assert(!nav.shouldSuppressClick({detail:1}));
svg.fire('pointerdown');win.fire('pointermove',{clientX:440});assert(svg.captured.has(1));win.fire('pointerup',{clientX:440});assert(nav.shouldSuppressClick({detail:1}));assert(!nav.shouldSuppressClick({detail:0}));assert(svg.fire('click').stopped);
svg.fire('pointerdown');win.fire('pointerup');assert(!nav.shouldSuppressClick({detail:1}));
const touch=(pointerId,x,y)=>({pointerId,pointerType:'touch',clientX:x,clientY:y});
svg.fire('pointerdown',touch(1,350,250));svg.fire('pointerdown',touch(2,650,250));const before=nav.snapshot().zoom;win.fire('pointermove',touch(2,750,250));assert(nav.snapshot().zoom>before);win.fire('pointerup',touch(2,750,250));const remain=nav.snapshot();win.fire('pointermove',touch(1,350,250));assert.deepEqual(nav.snapshot(),remain);win.fire('pointercancel',touch(1,350,250));assert(nav.shouldSuppressClick({detail:1}));
svg.fire('pointerdown',touch(3,300,200));win.fire('pointerup',touch(3,300,200));assert(!nav.shouldSuppressClick({detail:1}));
nav.zoomBy(1e6);near(nav.snapshot().zoom,4);nav.zoomBy(1e-6);near(nav.snapshot().zoom,1);const final=changes;nav.destroy();svg.fire('wheel',{deltaY:-100});win.fire('pointermove',{clientX:600});assert.equal(changes,final);assert(!svg.captured.size);
console.log('map navigation: fit/anchor/zoom/pan/resize bounds, drag-versus-click, pinch transition, cancel and listener cleanup passed');
