/* A map scene is reusable only while its complete visual input stays equal. */
'use strict';
(function(root){
 const scenes=new WeakMap();
 // Deliberately compare values rather than catalog identity: native responses
 // may replace objects without changing anything visible, or mutate a route.
 const key=scene=>JSON.stringify(scene);
 const matches=(svg,sceneKey)=>!!svg&&scenes.get(svg)===sceneKey;
 function remember(svg,sceneKey){if(svg)scenes.set(svg,sceneKey);}
 const api={key,matches,remember};
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root)root.GameMapRenderCache=api;
})(typeof window==='object'?window:null);
