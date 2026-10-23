/* Native map art replacement. Route geometry, camera and campaign data stay intact. */
'use strict';
(function(root){
 const VERSION='western-range-v1',SOURCE='/assets/map-road-centers.png',ASSET='/assets/map-western-range.png';
 const MAPS='svg#world-map, svg.event-map',XLINK='http://www.w3.org/1999/xlink';
 if(root?.GameMapTerrain?.version===VERSION&&root.GameMapTerrain.controller)return;
 const installed=new WeakMap();
 function install({document=root?.document,MutationObserver=root?.MutationObserver,Image=root?.Image}={}){
  if(!document?.documentElement||typeof MutationObserver!=='function'||typeof Image!=='function')return null;
  if(installed.has(document))return installed.get(document);
  let active=false,destroyed=false;
  const source=root?.GamePaths?.asset(SOURCE)||SOURCE,asset=root?.GamePaths?.asset(ASSET)||ASSET;
  const href=node=>node.getAttribute('href')||node.getAttributeNS(XLINK,'href');
  function replace(svg){
   if(destroyed||!active||!svg?.matches?.(MAPS)||!svg.isConnected)return false;
   // A map's direct image is its background. Never touch images in filters,
   // definitions, portraits, sprite layers or an unrelated SVG illustration.
   const background=Array.from(svg.children).find(node=>node.localName==='image'&&[source,asset].includes(href(node)));
   if(!background)return false;
   let changed=false;
   if(href(background)===source){
    background.setAttribute('href',asset);
    if(background.hasAttributeNS(XLINK,'href'))background.setAttributeNS(XLINK,'xlink:href',asset);
    background.setAttribute('data-terrain-art',VERSION);changed=true;
   }
   // The replacement already contains the complete mountain range. Applying
   // the previous three clipped color filters would tint those pixels twice.
   for(const layer of svg.querySelectorAll('g[data-terrain-recolor="chengdu-west"]')){layer.remove();changed=true;}
   return changed;
  }
  function refresh(){
   if(destroyed||!active)return 0;
   let changed=0;for(const svg of document.querySelectorAll(MAPS))if(replace(svg))changed++;
   return changed;
  }
  const observer=new MutationObserver(records=>{
   if(destroyed||!active)return;
   const maps=new Set();
   function collect(node){
    if(node?.nodeType!==1)return;
    const map=node.closest?.(MAPS);if(map)maps.add(map);
    for(const nested of node.querySelectorAll?.(MAPS)||[])maps.add(nested);
   }
   for(const record of records){collect(record.target);for(const node of record.addedNodes)collect(node);}
   // MutationObserver runs after the complete synchronous SVG render and
   // before painting. Attribute writes are not observed, while removing the
   // old layer produces at most one further, idempotent child-list callback.
   for(const svg of maps)replace(svg);
  });
  observer.observe(document.documentElement,{childList:true,subtree:true});
  let finish;
  const ready=new Promise(resolve=>{finish=resolve;});
  const image=new Image();image.decoding='async';
  let completed=false;
  function loaded(ok){
   if(completed)return;completed=true;image.onload=null;image.onerror=null;
   active=!destroyed&&ok&&image.naturalWidth===1352&&image.naturalHeight===1024;
   if(active)refresh();finish(active);
  }
  image.onerror=()=>loaded(false);
  image.onload=()=>{
   if(typeof image.decode==='function')Promise.resolve().then(()=>image.decode()).then(()=>loaded(true),()=>loaded(false));
   else loaded(true);
  };
  const controller={ready,refresh,get active(){return active;},destroy(){
   if(destroyed)return;destroyed=true;active=false;observer.disconnect();
   image.onload=null;image.onerror=null;installed.delete(document);finish(false);
  }};
  installed.set(document,controller);
  // Until decoding succeeds the original map and recolor stay together. A
  // missing/corrupt asset therefore retains a complete, usable old map.
  image.src=asset;
  return controller;
 }
 const api={version:VERSION,SOURCE,ASSET,install};
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root){root.GameMapTerrain=api;api.controller=install();}
})(typeof window==='object'?window:null);
