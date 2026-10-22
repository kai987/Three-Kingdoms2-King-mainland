/* Preserve released save JSON spelling; the server validates its checksum. */
'use strict';
(function(root){
 function loadBody(raw,revision){
  if(typeof raw!=='string'||!Number.isSafeInteger(revision)||revision<0)throw new Error('存档无效，当前进度未改变。');
  let value;try{value=JSON.parse(raw);}catch{throw new Error('存档无效，当前进度未改变。');}
  if(!value||typeof value!=='object'||Array.isArray(value))throw new Error('存档无效，当前进度未改变。');
  // Parsing above checks the document, but re-encoding value would erase e.g.
  // 315.0 from current engine saves and invalidate the existing canonical checksum.
  const body='{"save":'+raw+',"revision":'+revision+'}';
  if(new TextEncoder().encode(body).length>2*1024*1024)throw new Error('存档无效，当前进度未改变。');
  return body;
 }
 const api={loadBody};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.SaveTransfer=api;
})(typeof window==='object'?window:globalThis);
