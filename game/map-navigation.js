/* A presentation-only camera. Zoom is relative to a full, fitted map. */
'use strict';
(function(root){
 const MIN_ZOOM=1,MAX_ZOOM=4,DRAG_THRESHOLD=6;
 const finite=(value,fallback)=>Number.isFinite(value)?value:fallback;
 const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
 class Camera{
  constructor(world,width,height,initial={}){
   if(!world||!(world.width>0)||!(world.height>0)||![world.x??0,world.y??0,world.width,world.height].every(Number.isFinite))throw new TypeError('Invalid map bounds');
   initial=initial??{};
   this.world={x:world.x??0,y:world.y??0,width:world.width,height:world.height};
   this.x=finite(initial.x,this.world.x+world.width/2);this.y=finite(initial.y,this.world.y+world.height/2);
   this.zoom=clamp(finite(initial.zoom,1),MIN_ZOOM,MAX_ZOOM);this.resize(width,height);
  }
  resize(width,height){
   this.viewportWidth=Math.max(1,finite(width,1));this.viewportHeight=Math.max(1,finite(height,1));
   const aspect=this.viewportWidth/this.viewportHeight;
   this.fitWidth=Math.max(this.world.width,this.world.height*aspect);this.fitHeight=this.fitWidth/aspect;
   return this.constrain();
  }
  constrain(){
   const w=this.fitWidth/this.zoom,h=this.fitHeight/this.zoom,b=this.world;
   this.x=w>=b.width?b.x+b.width/2:clamp(this.x,b.x+w/2,b.x+b.width-w/2);
   this.y=h>=b.height?b.y+b.height/2:clamp(this.y,b.y+h/2,b.y+b.height-h/2);
   return this;
  }
  snapshot(){return {x:this.x,y:this.y,zoom:this.zoom};}
  box(){return {x:this.x-this.fitWidth/this.zoom/2,y:this.y-this.fitHeight/this.zoom/2,width:this.fitWidth/this.zoom,height:this.fitHeight/this.zoom};}
  point(u=.5,v=.5){const b=this.box();return {x:b.x+u*b.width,y:b.y+v*b.height};}
  zoomAt(zoom,u=.5,v=.5,anchor=this.point(u,v)){
   this.zoom=clamp(finite(zoom,this.zoom),MIN_ZOOM,MAX_ZOOM);
   this.x=anchor.x-(u-.5)*this.fitWidth/this.zoom;this.y=anchor.y-(v-.5)*this.fitHeight/this.zoom;
   return this.constrain();
  }
  panPixels(dx,dy){
   this.x-=finite(dx,0)*this.fitWidth/this.zoom/this.viewportWidth;
   this.y-=finite(dy,0)*this.fitHeight/this.zoom/this.viewportHeight;
   return this.constrain();
  }
  focus(x,y,zoom=3){this.x=finite(x,this.x);this.y=finite(y,this.y);this.zoom=clamp(finite(zoom,this.zoom),MIN_ZOOM,MAX_ZOOM);return this.constrain();}
  reset(){return this.focus(this.world.x+this.world.width/2,this.world.y+this.world.height/2,1);}
 }
 function attach(svg,{world,initial,onChange=()=>{}}){
  const win=svg.ownerDocument.defaultView,rect=()=>svg.getBoundingClientRect();let size=rect();
  const camera=new Camera(world,size.width,size.height,initial),pointers=new Map(),listeners=[];
  let destroyed=false,pinch=null,gestured=false,suppressUntil=0;
  const now=()=>win.performance.now();
  function paint(){if(destroyed)return;const b=camera.box();svg.setAttribute('viewBox',`${b.x} ${b.y} ${b.width} ${b.height}`);svg.dataset.zoom=String(camera.zoom);onChange(camera.snapshot());}
  function local(point){const r=rect();return {x:(point.x-r.left)/Math.max(1,r.width),y:(point.y-r.top)/Math.max(1,r.height)};}
  function capture(id){try{svg.setPointerCapture(id);}catch{}}
  function release(id){try{if(svg.hasPointerCapture(id))svg.releasePointerCapture(id);}catch{}}
  function startPinch(){
   const [a,b]=[...pointers.values()],center={x:(a.current.x+b.current.x)/2,y:(a.current.y+b.current.y)/2},p=local(center);
   pinch={distance:Math.max(1,Math.hypot(a.current.x-b.current.x,a.current.y-b.current.y)),zoom:camera.zoom,anchor:camera.point(p.x,p.y)};
   gestured=true;svg.classList.add('dragging');for(const id of pointers.keys())capture(id);
  }
  function down(e){
   if(e.pointerType!=='touch'&&e.button!==0)return;
   if(!pointers.size){gestured=false;suppressUntil=0;}
   const current={x:e.clientX,y:e.clientY};pointers.set(e.pointerId,{origin:current,current,last:current,dragging:false});
   if(pointers.size>=2){startPinch();e.preventDefault();}
  }
  function move(e){
   const p=pointers.get(e.pointerId);if(!p)return;
   p.current={x:e.clientX,y:e.clientY};
   if(pointers.size>=2){
    const[a,b]=[...pointers.values()],center=local({x:(a.current.x+b.current.x)/2,y:(a.current.y+b.current.y)/2});
    const distance=Math.max(1,Math.hypot(a.current.x-b.current.x,a.current.y-b.current.y));
    camera.zoomAt(pinch.zoom*distance/pinch.distance,center.x,center.y,pinch.anchor);e.preventDefault();paint();return;
   }
   if(!p.dragging&&Math.hypot(p.current.x-p.origin.x,p.current.y-p.origin.y)<DRAG_THRESHOLD)return;
   p.dragging=true;gestured=true;capture(e.pointerId);svg.classList.add('dragging');e.preventDefault();
   camera.panPixels(p.current.x-p.last.x,p.current.y-p.last.y);p.last=p.current;paint();
  }
  function finish(e){
   if(!pointers.has(e.pointerId))return;
   pointers.delete(e.pointerId);release(e.pointerId);pinch=null;
   if(pointers.size>=2)startPinch();
   else if(pointers.size===1){const p=[...pointers.values()][0];p.origin=p.last=p.current;p.dragging=gestured;}
   else{svg.classList.remove('dragging');if(gestured)suppressUntil=now()+700;}
  }
  function shouldSuppressClick(e){return e.detail!==0&&(gestured&&pointers.size>0||now()<suppressUntil);}
  function click(e){if(shouldSuppressClick(e)){e.preventDefault();e.stopImmediatePropagation();}}
  function zoomBy(factor,clientX,clientY){
   if(!(factor>0)||!Number.isFinite(factor))return;
   const p=Number.isFinite(clientX)&&Number.isFinite(clientY)?local({x:clientX,y:clientY}):{x:.5,y:.5};
   camera.zoomAt(camera.zoom*factor,p.x,p.y);paint();
  }
  function wheel(e){
   e.preventDefault();const r=rect(),delta=e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?r.height:1);
   zoomBy(Math.exp(-clamp(delta,-240,240)*.0025),e.clientX,e.clientY);
  }
  function resize(){const r=rect();if(r.width===size.width&&r.height===size.height)return;size=r;camera.resize(r.width,r.height);if(pointers.size>=2)startPinch();paint();}
  function listen(target,name,fn,options){target.addEventListener(name,fn,options);listeners.push(()=>target.removeEventListener(name,fn,options));}
  listen(svg,'pointerdown',down);listen(win,'pointermove',move,{passive:false});listen(win,'pointerup',finish);listen(win,'pointercancel',finish);listen(svg,'lostpointercapture',finish);
  listen(svg,'wheel',wheel,{passive:false});listen(svg,'click',click,true);
  const observer=typeof win.ResizeObserver==='function'?new win.ResizeObserver(resize):null;
  if(observer)observer.observe(svg);else listen(win,'resize',resize);
  paint();
  return {
   snapshot:()=>camera.snapshot(),zoomBy,shouldSuppressClick,resize,
   focus(x,y,zoom=3){camera.focus(x,y,zoom);paint();},reset(){camera.reset();paint();},
   destroy(){destroyed=true;for(const remove of listeners)remove();observer?.disconnect();for(const id of pointers.keys())release(id);pointers.clear();svg.classList.remove('dragging');}
  };
 }
 const api={MIN_ZOOM,MAX_ZOOM,Camera,attach};
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root)root.MapNavigation=api;
})(typeof window==='object'?window:null);
