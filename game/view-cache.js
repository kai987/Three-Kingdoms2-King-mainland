/* Immutable scenario metadata stays in this tab; saved game JSON is untouched. */
'use strict';
(function(root){
 function create(){
  const catalogs=new Map();let current='',routeCache=null;
  function hydrate(value){
   if(!value||value.transport!=='tk2-view-v1')return value;
   const token=value.catalog_token;
   if(typeof token!=='string'||!(/^[a-f0-9]{64}$/).test(token)||!value.view?.catalog)throw Error('Invalid view cache');
   let fixed=value.static_catalog||catalogs.get(token);
   if(!fixed||!Array.isArray(fixed.library)||!Array.isArray(value.view.catalog.library))throw Error('Missing view catalog');
   const byId=new Map(fixed.library.map(row=>[String(row.id),row]));
   const library=value.view.catalog.library.map(row=>{
    const base=byId.get(String(row.id));if(!base)throw Error('Unknown view person');
    return {...base,...row};
   });
   if(library.length!==fixed.library.length||new Set(library.map(row=>String(row.id))).size!==library.length)throw Error('Invalid view people');
   let travel=value.view.catalog.travel_quotes;
   const routeToken=value.quote_token;
   if(routeToken!==undefined){
    if(typeof routeToken!=='string'||!(/^[a-f0-9]{64}$/).test(routeToken))throw Error('Invalid route token');
    if(travel===undefined){if(routeCache?.token!==routeToken)throw Error('Missing route quotes');travel=routeCache.quotes;}
    if(!travel||typeof travel!=='object'||Array.isArray(travel))throw Error('Invalid route quotes');
   }
   // Commit cache state only after the entire response has passed validation.
   catalogs.delete(token);catalogs.set(token,fixed);
   while(catalogs.size>2)catalogs.delete(catalogs.keys().next().value);
   if(routeToken!==undefined)routeCache={token:routeToken,quotes:travel};
   current=token+(routeToken===undefined?'':':'+routeToken);
   return {...value.view,catalog:{...fixed,...value.view.catalog,library,...(routeToken===undefined?{}:{travel_quotes:travel})}};
  }
  return {hydrate,token:()=>current,clear(){catalogs.clear();current='';routeCache=null;}};
 }
 const api={create};if(typeof module==='object'&&module.exports)module.exports=api;else root.GameViewCache=api;
})(typeof window==='object'?window:globalThis);
