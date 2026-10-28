/* Resolve shipped assets under both a domain root and a Pages project path. */
'use strict';
(function(root){
 const script=root.document?.currentScript?.src;
 const base=script?new URL('.',script):null;
 function asset(value){
  if(!base||typeof value!=='string'||!['/config/duel-appearances.json','/config/battlefield-city-bindings.json'].includes(value)&&!/^\/(?:assets|locales|wasm|vendor)\//.test(value)&&!/^\/[A-Za-z0-9-]+\.js$/.test(value))return value;
  return new URL('.'+value,base).pathname;
 }
 const api={asset,base:base?.href||null};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GamePaths=Object.freeze(api);
})(typeof window==='object'?window:globalThis);
