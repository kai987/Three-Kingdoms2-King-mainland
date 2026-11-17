/* Immutable scenario metadata stays in this tab; saved game JSON is untouched. */
'use strict';
(function(root){
 function create(){
  const catalogs=new Map();let current='',routeCache=null,scenarioCache=null;
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
   const scenarioToken=value.scenarios_token;
   let sharedScenarios=scenarioCache;
   if(scenarioToken!==undefined){
    if(typeof scenarioToken!=='string'||!(/^[a-f0-9]{64}$/).test(scenarioToken))throw Error('Invalid scenarios token');
    if(Object.hasOwn(value,'shared_scenarios')){
     if(!Array.isArray(value.shared_scenarios))throw Error('Invalid shared scenarios');
     sharedScenarios={token:scenarioToken,scenarios:structuredClone(value.shared_scenarios)};
    }
    if(sharedScenarios?.token!==scenarioToken)throw Error('Missing shared scenarios');
   }
   const shared=scenarioToken===undefined?{}:{scenarios:structuredClone(sharedScenarios.scenarios)};
   // Commit cache state only after the entire response has passed validation.
   catalogs.delete(token);catalogs.set(token,fixed);
   while(catalogs.size>2)catalogs.delete(catalogs.keys().next().value);
   if(routeToken!==undefined)routeCache={token:routeToken,quotes:travel};
   scenarioCache=sharedScenarios;
   current=token+(routeToken===undefined?'':':'+routeToken);
   return {...value.view,catalog:{...fixed,...value.view.catalog,...shared,library,...(routeToken===undefined?{}:{travel_quotes:travel})}};
  }
  return {hydrate,token:(sharedScenarios=false)=>sharedScenarios
   ?'scenarios-v1|'+current+'|'+(scenarioCache?.token||''):current,
   clear(){catalogs.clear();current='';routeCache=null;scenarioCache=null;}};
 }
 const api={create};if(typeof module==='object'&&module.exports)module.exports=api;else root.GameViewCache=api;
})(typeof window==='object'?window:globalThis);
