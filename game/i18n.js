/* Presentation-only localization. Stable IDs, form values and saves stay raw. */
'use strict';
window.GameI18n=(()=>{
 const supported=['zh-Hant','ja'],storageKey='three-kingdoms-language';
 let locale='zh-Hant',stages=[],resources=[],exact=new Map(),words=new Map(),wordPattern=null,patterns=[],active=false;
 try{const saved=localStorage.getItem(storageKey);if(supported.includes(saved))locale=saved;}catch{}
 const originals=new WeakMap(),attributeOriginals=new WeakMap(),missing=new Set(),cache=new Map(),scenarioResources=[];let scenarioSignature='';
 const escapePattern=s=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
 function trie(entries){const root=new Map();for(const[source,target]of Object.entries(entries||{})){let node=root;for(const ch of source){if(!node.has(ch))node.set(ch,new Map());node=node.get(ch);}node.value=target;}return root;}
 function traditional(text){
  let result=String(text);
  for(const stage of stages){let out='';for(let i=0;i<result.length;){let node=stage.phrases,last=null,end=i;
   for(let j=i;j<result.length;){const ch=String.fromCodePoint(result.codePointAt(j));if(!node.has(ch))break;node=node.get(ch);j+=ch.length;if(node.value!==undefined){last=node.value;end=j;}}
   if(last!==null){out+=last;i=end;}else{const ch=String.fromCodePoint(result.codePointAt(i));out+=stage.characters[ch]??ch;i+=ch.length;}
  }result=out;}return result;
 }
 function rebuild(){
  exact=new Map();words=new Map();patterns=[];
  for(const data of [...resources,...scenarioResources]){
   for(const[source,target]of Object.entries(data.exact||{})){exact.set(source,target);exact.set(traditional(source),target);}
   for(const row of data.patterns||[]){for(const pattern of new Set([row.pattern,traditional(row.pattern)]))patterns.push({match:new RegExp(pattern,row.flags||'u'),replacement:row.replacement});}
   for(const[source,target]of [...Object.entries(data.names||{}),...(data.terms||[]),...Object.entries(data.exact||{})]){
    if(!source)continue;words.set(source,target);words.set(traditional(source),target);
   }
  }
  // Preserve completed Japanese phrases as whole tokens before their Chinese
  // source substrings (e.g. 官渡 -> 官渡の戦い) can match again.
  for(const target of [...exact.values(),...words.values()]){if(!exact.has(target))exact.set(target,target);if(!words.has(target))words.set(target,target);}
  wordPattern=words.size?new RegExp([...words.keys()].sort((a,b)=>b.length-a.length).map(escapePattern).join('|'),'gu'):null;
  cache.clear();missing.clear();
 }
 function replaceWords(text){if(!wordPattern)return text;wordPattern.lastIndex=0;return text.replace(wordPattern,source=>words.get(source));}
 function t(value,language=locale){
  const text=String(value??''),key=language+'\0'+text;
  if(cache.has(key))return cache.get(key);
  if(language==='zh-Hant'){const result=traditional(text);cache.set(key,result);return result;}
  const content=text.trim();let result,matched=false;
  if(exact.has(content)){result=exact.get(content);matched=true;}
  else if(words.has(content)){result=words.get(content);matched=true;}
  else{
   result=content;
   for(const row of patterns){row.match.lastIndex=0;const found=row.match.exec(result);if(found){result=row.replacement.replace(/\$(\d+)/g,(_,number)=>{const capture=found[Number(number)]||'';return capture===content?replaceWords(capture):t(capture,'ja');});matched=true;break;}}
   if(!matched&&wordPattern){let cursor=0,left='';wordPattern.lastIndex=0;result=result.replace(wordPattern,(source,offset)=>{left+=content.slice(cursor,offset);cursor=offset+source.length;matched=true;return words.get(source);});left+=content.slice(cursor);if(/[\u3400-\u9fff]{2}/u.test(left)&&!/[\u3040-\u30ff]/u.test(left))missing.add(content);}
  }
  if(!matched&&/[\u3400-\u9fff]/u.test(content)&&!/[\u3040-\u30ff]/u.test(content))missing.add(content);
  result=text.slice(0,text.length-text.trimStart().length)+(result??content)+text.slice(text.trimEnd().length);
  // Quotes and unidentified proper nouns remain readable in the source script;
  // Japanese UI prose is supplied explicitly, never invented by character swaps.
  if(!matched&&!/[\u3040-\u30ff]/u.test(content))result=traditional(result);
  if(cache.size>12000)cache.clear();cache.set(key,result);return result;
 }
 function originalLanguage(element){
  if(element.closest('[data-l10n-original],[data-locale-only="zh-Hant"]'))return 'zh-Hant';
  if(element.closest('[data-l10n-native]'))return element.closest('[data-l10n-native]').dataset.l10nNative;
  return locale;
 }
 function eligible(element){return element&&!element.closest('script,style,[contenteditable=true]');}
 function textNode(node){
  const parent=node.parentElement;if(!eligible(parent)||parent.closest('textarea,input,#language,[data-language-picker]')||!node.data.trim())return;
  const old=originals.get(node),source=old&&node.data===old.rendered?old.source:node.data;
  const rendered=parent.closest('[data-l10n-native]')&&!parent.closest('[data-l10n-original]')?source:t(source,originalLanguage(parent));originals.set(node,{source,rendered});if(node.data!==rendered)node.data=rendered;
 }
 const attributes=['aria-label','title','placeholder','alt','label'];
 function element(node){
  if(!eligible(node))return;
  if(node.dataset.localeOnly)node.hidden=node.dataset.localeOnly!==locale;
  let record=attributeOriginals.get(node);if(!record){record={};attributeOriginals.set(node,record);}
  for(const key of attributes){const actual=node.getAttribute(key);if(actual===null)continue;const old=record[key],source=old&&actual===old.rendered?old.source:actual,rendered=t(source,originalLanguage(node));record[key]={source,rendered};if(actual!==rendered)node.setAttribute(key,rendered);}
 }
 function localize(root=document.documentElement){
  if(root.nodeType===Node.TEXT_NODE){textNode(root);return;}
  if(root.nodeType!==Node.ELEMENT_NODE)return;
  element(root);const walker=document.createTreeWalker(root,NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){const node=walker.currentNode;if(node.nodeType===Node.TEXT_NODE)textNode(node);else element(node);}
 }
 const observer=new MutationObserver(records=>{
  observer.disconnect();
  try{for(const row of records){if(row.type==='childList')for(const node of row.addedNodes)localize(node);else if(row.type==='characterData')textNode(row.target);else element(row.target);}}
  finally{watch();}
 });
 function watch(){observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:attributes});}
 function apply(){
  observer.disconnect();localize();document.documentElement.lang=locale;
  for(const select of document.querySelectorAll('#language,[data-language-picker]'))select.value=locale;
  if(active)watch();
 }
 function setLocale(language){
  if(!supported.includes(language))return false;locale=language;
  try{localStorage.setItem(storageKey,language);}catch{}
  apply();document.dispatchEvent(new CustomEvent('game-language-change',{detail:{locale}}));return true;
 }
 function registerScenarios(rows){
  const data={exact:{}};
  for(const row of rows||[]){const scenario=row.main_scenario||row;
   for(const field of ['title','summary','story_note']){
    const values=scenario[field+'_i18n'];if(!values?.ja)continue;
    for(const source of [scenario[field],values['zh-Hant']])if(source)data.exact[source]=values.ja;
    if(field==='title'&&row.title&&row.year&&row.month)data.exact[row.title]=`${row.year}年${row.month}月 · ${values.ja}`;
   }
   if(scenario.title&&row.title&&row.year&&row.month)data.exact[row.title]=`${row.year}年${row.month}月 · ${scenario.title_i18n?.ja||t(scenario.title,'ja')}`;
   if(scenario.official_same_date_title?.ja)data.exact[scenario.official_same_date_title['zh-Hant']]=scenario.official_same_date_title.ja;
  }
  const signature=JSON.stringify(data.exact);if(signature===scenarioSignature)return;scenarioSignature=signature;scenarioResources.splice(0,scenarioResources.length,data);rebuild();if(active)apply();
 }
 const ready=Promise.all(['/locales/zh-hant.json','/locales/ui-ja.json','/locales/messages-ja.json'].map(async url=>{const response=await fetch(url);if(!response.ok)throw new Error('Language resource unavailable: '+url);return response.json();})).then(([conversion,...translations])=>{
  stages=(conversion.stages||[]).map(stage=>({phrases:trie(stage.phrases),characters:stage.characters||{}}));resources=translations;rebuild();active=true;
  document.addEventListener('change',event=>{if(event.target.matches('#language,[data-language-picker]'))setLocale(event.target.value);});apply();
 });
 return {ready,t,traditional,setLocale,registerScenarios,apply,missing,get locale(){return locale;}};
})();
