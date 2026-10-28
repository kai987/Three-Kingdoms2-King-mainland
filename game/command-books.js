/* Display the authoritative faction command-book ledger; never spend or refill it. */
'use strict';
(function(root){
 const SCHEMA='tk2-command-books-v1';
 const integer=value=>Number.isSafeInteger(value)&&value>=0;
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const text=(locale,tc,ja)=>locale==='ja'?ja:tc;
 function data(view){const value=view?.catalog?.command_books;return value?.schema===SCHEMA&&integer(value.turn)&&integer(value.maximum)&&value.maximum>0?value:null;}
 function row(view,owner=view?.game?.player){
  const source=data(view),value=source?.factions?.[owner];
  if(!value||source.turn!==view?.game?.turn||![value.city_count,value.total,value.used,value.remaining].every(integer)||value.total>source.maximum||value.used+value.remaining!==value.total)return null;
  return value;
 }
 function cost(view,kind){const value=data(view)?.costs?.[kind];return integer(value)?value:null;}
 function can(view,kind,owner=view?.game?.player){const value=row(view,owner),amount=cost(view,kind);return !!value&&amount!==null&&value.remaining>=amount;}
 function reason(view,kind,locale='zh-Hant',owner=view?.game?.player){
  const value=row(view,owner),amount=cost(view,kind);
  if(!value||amount===null)return text(locale,'命令書資料尚未就緒。','命令書の情報を読み込めません。');
  if(value.remaining<amount)return text(locale,'本勢力命令書不足：需要'+amount+'張，剩餘'+value.remaining+'張。','この勢力の命令書が不足しています。必要'+amount+'枚、残り'+value.remaining+'枚です。');
  return '';
 }
 function summary(view,{kind,locale='zh-Hant',owner=view?.game?.player}={}){
  const value=row(view,owner),amount=kind===undefined?null:cost(view,kind);
  if(!value)return view?.game?text(locale,'命令書資料尚未就緒。','命令書の情報を読み込めません。'):'';
  const remaining=text(locale,'命令書 剩餘 '+value.remaining+'/'+value.total,'命令書 残り '+value.remaining+'/'+value.total);
  return remaining+(kind===undefined?'':amount===0?text(locale,' · 不消耗命令書',' · 命令書消費なし'):amount===null?text(locale,' · 費用待確認',' · 必要枚数を確認中'):text(locale,' · 本次消耗 '+amount+'張',' · 今回消費 '+amount+'枚'));
 }
 function html(view,options={}){
  const value=row(view,options.owner),content=summary(view,options);if(!content)return '';
  const amount=options.kind===undefined?null:cost(view,options.kind),locale=options.locale||'zh-Hant';
  const variant=language=>{
   const note=text(language,'全勢力共用，可集中投入同一城；每旬開始重置，不累積剩餘命令書。','勢力全体で共有し、同じ都市へ集中して使えます。毎旬の開始時に更新し、余りは持ち越しません。');
   const ended=value?.remaining===0&&amount!==0?text(language,' · 本旬已用完；可查看資料或設定免費方針。',' · 今旬は使い切りました。閲覧・無料の方針設定は可能です。'):'';
   return '<span data-locale-only="'+language+'" data-l10n-native="'+language+'" title="'+escape(note)+'"'+(locale===language?'':' hidden')+'>'+escape(summary(view,{...options,locale:language})+ended)+'</span>';
  };
  return '<p class="command-books small" data-command-books data-command-books-remaining="'+(value?.remaining??'')+'" data-command-books-total="'+(value?.total??'')+'"'+(amount===null?'':' data-command-book-cost="'+amount+'"')+' role="status">'+variant('zh-Hant')+variant('ja')+'</p>';
 }
 const api=Object.freeze({SCHEMA,data,row,cost,can,reason,summary,html});
 if(typeof module==='object'&&module.exports)module.exports=api;
 if(root)root.GameCommandBooks=api;
})(typeof window==='object'?window:globalThis);
