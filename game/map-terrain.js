/* Native map art replacement. Route geometry, camera and campaign data stay intact. */
'use strict';
(function(root){
 const VERSION='western-range-v1',SOURCE='/assets/map-road-centers.png',ASSET='/assets/map-western-range.png';
 const MAPS='svg#world-map, svg.event-map',XLINK='http://www.w3.org/1999/xlink';
 const RETRY_DELAYS=[1000,4000,16000];
 if(root?.GameMapTerrain?.version===VERSION&&root.GameMapTerrain.controller)return;
 const installed=new WeakMap();
 function install({document=root?.document,Image=root?.Image}={}){
  if(!document?.documentElement||typeof Image!=='function')return null;
  if(installed.has(document))return installed.get(document);
  const network=document.defaultView;
  let active=false,destroyed=false,image=null,retryTimer=null,retryCount=0;
  const source=root?.GamePaths?.asset(SOURCE)||SOURCE;
  const artHash=document.currentScript?.getAttribute?.('data-art-sha256');
  const revision=/^[a-f0-9]{64}$/i.test(artHash||'')?artHash:'current-map-v2';
  const asset=(root?.GamePaths?.asset(ASSET)||ASSET)+'?v='+encodeURIComponent(revision);
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
  let finish;
  const ready=new Promise(resolve=>{finish=resolve;});
  function cancelRetry(){
   if(retryTimer===null)return;
   network.clearTimeout(retryTimer);
   retryTimer=null;
  }
  function load(){
   if(destroyed||image)return;
   cancelRetry();
   const candidate=new Image();
   image=candidate;
   candidate.decoding='async';
   function loaded(ok){
    if(destroyed||image!==candidate||active)return;
    candidate.onload=candidate.onerror=null;
    active=ok&&candidate.naturalWidth===1352&&candidate.naturalHeight===1024;
    if(active){
     // Retain the decoded image so new SVGs can reuse it during an outage.
     refresh();
    }else{
     image=null;
     if(network?.navigator?.onLine!==false&&retryCount<RETRY_DELAYS.length){
      retryTimer=network?.setTimeout(()=>{
       retryTimer=null;
       load();
      },RETRY_DELAYS[retryCount++])??null;
     }
    }
    finish(active);
   }
   candidate.onerror=()=>loaded(false);
   candidate.onload=()=>{
    if(typeof candidate.decode==='function')Promise.resolve().then(()=>candidate.decode()).then(()=>loaded(true),()=>loaded(false));
    else loaded(true);
   };
   candidate.src=asset;
  }
  function reconnect(){
   retryCount=0;
   load();
  }
  // The renderers resolve before inserting SVG markup. Setting the fallback
  // href first would initiate a request even if it were replaced before paint.
  const controller={ready,refresh,resolve:background=>active&&background===source?asset:background,
   get active(){return active;},destroy(){
   if(destroyed)return;
   destroyed=true;active=false;
   cancelRetry();
   network?.removeEventListener('online',reconnect);
   if(image)image.onload=image.onerror=null;
   image=null;installed.delete(document);finish(false);
  }};
  installed.set(document,controller);
  // Until decoding succeeds the original map and recolor stay together. A
  // missing/corrupt asset therefore retains a complete, usable old map.
  network?.addEventListener('online',reconnect);
  load();
  return controller;
 }
 const api={version:VERSION,SOURCE,ASSET,install};
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root){root.GameMapTerrain=api;api.controller=install();}
})(typeof window==='object'?window:null);
