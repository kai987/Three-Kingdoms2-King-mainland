'use strict';
const assert=require('node:assert/strict');
const {install,SOURCE,ASSET}=require('../game/map-terrain.js');
const MAPS='svg#world-map, svg.event-map',VERSIONED_ASSET=ASSET+'?v=current-map-v2';
class Node{
 constructor(localName,attributes={}){this.localName=localName;this.attributes={...attributes};this.children=[];this.parentNode=null;this.nodeType=1;this.writes=0;}
 get isConnected(){return this.root===this.ownerDocument?.documentElement;}
 get root(){return this.parentNode?this.parentNode.root:this;}
 append(node){node.parentNode=this;node.ownerDocument=this.ownerDocument;this.children.push(node);for(const child of node.children)node.adopt(child);return node;}
 adopt(node){node.ownerDocument=this.ownerDocument;for(const child of node.children)this.adopt(child);}
 getAttribute(name){return this.attributes[name]??null;}
 getAttributeNS(ns,name){return this.attributes['xlink:'+name]??null;}
 hasAttributeNS(ns,name){return Object.hasOwn(this.attributes,'xlink:'+name);}
 setAttribute(name,value){this.attributes[name]=value;this.writes++;}
 setAttributeNS(ns,name,value){this.setAttribute(name,value);}
 matches(selector){if(selector===MAPS)return this.localName==='svg'&&(this.attributes.id==='world-map'||this.attributes.class?.split(' ').includes('event-map'));return selector==='g[data-terrain-recolor="chengdu-west"]'&&this.localName==='g'&&this.attributes['data-terrain-recolor']==='chengdu-west';}
 closest(selector){return this.matches(selector)?this:this.parentNode?.closest(selector)||null;}
 querySelectorAll(selector){return this.children.flatMap(node=>[...(node.matches(selector)?[node]:[]),...node.querySelectorAll(selector)]);}
 remove(){const parent=this.parentNode;if(parent)parent.children.splice(parent.children.indexOf(this),1);this.parentNode=null;}
}
function environment(){
 const network=new EventTarget(),timers=new Map();
 network.navigator={onLine:true};
 network.setTimeout=(fn,delay)=>{const id=Symbol();timers.set(id,{fn,delay});return id;};
 network.clearTimeout=id=>timers.delete(id);
 const document={defaultView:network,querySelectorAll:selector=>document.documentElement.querySelectorAll(selector)};
 document.documentElement=new Node('html');document.documentElement.ownerDocument=document;
 const images=[];
 class Image{
  constructor(){images.push(this);this.naturalWidth=1352;this.naturalHeight=1024;}
  decode(){this.decoded=true;return Promise.resolve();}
 }
 return {document,Image,images,network,timers};
}
function map(env,kind='world',source=SOURCE){
 const svg=new Node('svg',kind==='world'?{id:'world-map',viewBox:'0 0 1352 1024'}:{class:'event-map',viewBox:'50 300 288 172'});
 env.document.documentElement.append(svg);
 const defs=svg.append(new Node('defs')),background=svg.append(new Node('image',{href:source,x:'0',y:'0',width:'1352',height:'1024'}));
 const filter=svg.append(new Node('g',{'data-terrain-recolor':'chengdu-west'}));filter.append(new Node('image',{href:SOURCE}));
 const road=svg.append(new Node('path',{d:'M50 400L150 500'})),city=svg.append(new Node('g',{'data-city':'shujun'}));
 return {svg,defs,background,filter,road,city};
}
async function decode(env,index=0){env.images[index].onload();await Promise.resolve();await Promise.resolve();await Promise.resolve();}
(async()=>{
 const env=environment(),world=map(env),event=map(env,'event'),other=map(env,'world','/assets/map-basin.png');other.svg.attributes.id='other-map';
 const offMap=env.document.documentElement.append(new Node('image',{href:SOURCE}));
 const nested=world.defs.append(new Node('image',{href:SOURCE}));
 const xlink=map(env);delete xlink.background.attributes.href;xlink.background.attributes['xlink:href']=SOURCE;
 const names=Object.keys(world.background.attributes),before=JSON.stringify({viewBox:world.svg.attributes.viewBox,road:world.road.attributes,city:world.city.attributes});
 const controller=install(env);
 assert.equal(install(env),controller,'One preload per document');assert.equal(env.images.length,1);
 assert.equal(env.images[0].src,VERSIONED_ASSET);
 assert.equal(controller.active,false);assert.equal(world.background.getAttribute('href'),SOURCE);assert(world.svg.children.includes(world.filter),'Original art and recolor remain together until decoding');
 assert.equal(controller.resolve(SOURCE),SOURCE);
 await decode(env);assert.equal(await controller.ready,true);assert.equal(controller.active,true);assert(env.images[0].decoded);
 for(const row of [world,event]){assert.equal(row.background.getAttribute('href'),VERSIONED_ASSET);assert.equal(row.background.getAttribute('data-terrain-art'),'western-range-v1');assert(!row.svg.children.includes(row.filter));assert.deepEqual(row.svg.children,[row.defs,row.background,row.road,row.city],'Only old recolor is removed; remaining layer order stays intact');}
 assert.equal(nested.getAttribute('href'),SOURCE);assert.equal(offMap.getAttribute('href'),SOURCE);assert.equal(other.background.getAttribute('href'),'/assets/map-basin.png');assert(other.svg.children.includes(other.filter));
 assert.equal(JSON.stringify({viewBox:world.svg.attributes.viewBox,road:world.road.attributes,city:world.city.attributes}),before);
 for(const name of names.filter(name=>name!=='href'))assert.equal(world.background.getAttribute(name),{x:'0',y:'0',width:'1352',height:'1024'}[name]);
 assert.equal(xlink.background.getAttributeNS('', 'href'),VERSIONED_ASSET);
 const writes=world.background.writes;assert.equal(controller.refresh(),0);assert.equal(world.background.writes,writes);
 assert.equal(controller.resolve(SOURCE),VERSIONED_ASSET,'Resolve the decoded URL before inserting a new image');
 assert.equal(controller.resolve('/assets/map-basin.png'),'/assets/map-basin.png');
 env.network.dispatchEvent(new Event('online'));assert.equal(env.images.length,1,'An online event does not reload decoded art');
 controller.destroy();assert.equal(controller.resolve(SOURCE),SOURCE);assert.equal(controller.refresh(),0);
 env.network.dispatchEvent(new Event('online'));assert.equal(env.images.length,1);
 const retry=install(env);assert.notEqual(retry,controller);retry.destroy();assert.equal(await retry.ready,false);
 for(const failure of ['missing','size','decode']){
  const e=environment(),m=map(e),c=install(e);
  if(failure==='missing')e.images[0].onerror();
  else {if(failure==='size')e.images[0].naturalWidth=256;else e.images[0].decode=()=>Promise.reject(Error('Invalid image'));await decode(e);}
  assert.equal(await c.ready,false);assert.equal(c.active,false);assert.equal(m.background.getAttribute('href'),SOURCE);assert(m.svg.children.includes(m.filter),'Failed image leaves old art complete');
  assert.deepEqual([...e.timers.values()].map(timer=>timer.delay),[1000]);c.destroy();assert.equal(e.timers.size,0);
 }
 const offline=environment(),fallback=map(offline),recover=install(offline);
 offline.network.navigator.onLine=false;offline.images[0].onerror();
 assert.equal(await recover.ready,false);assert.equal(offline.timers.size,0);
 offline.network.navigator.onLine=true;offline.network.dispatchEvent(new Event('online'));
 offline.network.dispatchEvent(new Event('online'));assert.equal(offline.images.length,2);
 await decode(offline,1);
 assert.equal(recover.active,true);assert.equal(fallback.background.getAttribute('href'),VERSIONED_ASSET);
 assert(!fallback.svg.children.includes(fallback.filter));recover.destroy();
 const transient=environment(),delayed=install(transient);
 transient.images[0].onerror();
 const [[timerId,timer]]=[...transient.timers];
 transient.timers.delete(timerId);timer.fn();
 await decode(transient,1);
 assert.equal(delayed.resolve(SOURCE),VERSIONED_ASSET);delayed.destroy();
 const hashed=environment(),sha='a'.repeat(64);hashed.document.currentScript={getAttribute:()=>sha};
 const hashedMap=map(hashed),hashedController=install(hashed);assert.equal(hashed.images[0].src,ASSET+'?v='+sha);
 await decode(hashed);assert.equal(hashedMap.background.getAttribute('href'),ASSET+'?v='+sha);hashedController.destroy();
 const invalid=environment();invalid.document.currentScript={getAttribute:()=>'<untrusted>&token'};const invalidController=install(invalid);assert.equal(invalid.images[0].src,VERSIONED_ASSET);invalidController.destroy();
 assert.equal(install({}),null,'Non-browser callers do not install listeners');
 console.log('map terrain: render-time resolution, atomic recovery, offline/online and delayed retries, scoped layers and cleanup passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
