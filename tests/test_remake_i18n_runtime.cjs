/* No npm dependency: exercise the shipped browser translator in a minimal DOM. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
class Element{
 constructor(tag,attrs={}){this.nodeType=1;this.tagName=tag.toUpperCase();this.attrs={...attrs};this.dataset={};this.children=[];this.parentElement=null;this.hidden=false;}
 append(node){node.parentElement=this;this.children.push(node);return node;}
 getAttribute(key){return this.attrs[key]??null;}
 setAttribute(key,value){this.attrs[key]=String(value);}
 matches(selector){return selector.split(',').some(part=>{const value=part.trim();if(value[0]==='#')return this.attrs.id===value.slice(1);if(value[0]==='['){const match=value.match(/^\[([^=\]]+)(?:=["']?([^\]"']+)["']?)?\]$/);return !!match&&this.getAttribute(match[1])!==null&&(match[2]===undefined||this.getAttribute(match[1])===match[2]);}return this.tagName.toLowerCase()===value;});}
 closest(selector){for(let node=this;node;node=node.parentElement)if(node.matches(selector))return node;return null;}
}
class Text{constructor(data){this.nodeType=3;this.data=data;this.parentElement=null;}}
const html=new Element('html'),head=html.append(new Element('head')),title=head.append(new Element('title')).append(new Text('三国·大陆战役')),body=html.append(new Element('body'));
const heading=body.append(new Element('button')).append(new Text('保存进度'));
const language=body.append(new Element('select',{id:'language','aria-label':'切换语言'}));language.value='zh-Hant';
language.append(new Element('option')).append(new Text('繁體中文'));language.append(new Element('option')).append(new Text('日本語'));
const input=body.append(new Element('input',{'aria-label':'随机种子'}));input.value='13579';input.checked=true;
const all=node=>[node,...(node.children||[]).flatMap(all)];
const events=[],document={documentElement:html,querySelector:s=>all(html).find(n=>n.nodeType===1&&n.matches(s))||null,querySelectorAll:s=>all(html).filter(n=>n.nodeType===1&&n.matches(s)),createTreeWalker(node){const nodes=all(node).slice(1);let index=0;return{currentNode:node,nextNode(){if(index===nodes.length)return false;this.currentNode=nodes[index++];return true;}};},addEventListener(){},dispatchEvent(e){events.push(e);return true;}};
Object.defineProperty(document,'title',{get:()=>title.data});
const storage=new Map([['three-kingdoms-demo-save','unchanged-game-save']]),requests=[];
const context={window:{},document,Node:{TEXT_NODE:3,ELEMENT_NODE:1},NodeFilter:{SHOW_ELEMENT:1,SHOW_TEXT:4},MutationObserver:class{observe(){}disconnect(){}},CustomEvent:class{constructor(type,options){this.type=type;this.detail=options.detail;}},localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,String(v))},fetch:async url=>{requests.push(url);return{ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,'game',url),'utf8'))};},console};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'game/i18n.js'),'utf8'),context,{filename:'game/i18n.js'});
(async()=>{
 const i18n=context.window.GameI18n;await i18n.ready;
 assert.equal(i18n.locale,'zh-Hant');assert.equal(document.title,'三國·大陸戰役');assert.equal(heading.data,'保存進度');
 const index=JSON.parse(fs.readFileSync(path.join(root,'game/data/main-scenarios-v12/index.json')));
 const rows=index.catalogs.map(file=>{const data=JSON.parse(fs.readFileSync(path.join(root,'game/data',file)));return{title:data.title,year:data.start_year,month:data.start_month,main_scenario:data.main_scenario};});
 const before=JSON.stringify(rows);i18n.registerScenarios(rows);
 const cases=[
  ['200年1月 · 官渡之战','200年1月 · 官渡の戦い'],
  ['208年10月 · 赤壁之战','208年10月 · 赤壁の戦い'],
  ['官渡之战','官渡の戦い'],['赤壁之战','赤壁の戦い'],
  ['元データ説明','元データ説明'],['关羽','関羽'],['张辽','張遼'],['许昌','許昌'],
  ['钱 123 · 粮 456 · 预备兵 789','資金 123 · 兵糧 456 · 予備兵 789'],
  ['关羽攻击张辽，损兵17。','関羽が張遼を攻撃。17の兵力損耗。'],
 ];
 for(const[source,expected]of cases){const translated=i18n.t(source,'ja');assert.equal(translated,expected,source);assert.equal(i18n.t(translated,'ja'),expected,'Japanese translation must be idempotent: '+source);}
 for(const row of rows){const once=i18n.t(row.title,'ja');assert.equal(i18n.t(once,'ja'),once,row.title);assert(!once.includes('の戦いの戦い'),row.title);}
 assert.equal(i18n.t('关羽','zh-Hant'),'關羽');
 for(let n=0;n<2;n++){assert(i18n.setLocale('ja'));assert.equal(heading.data,'セーブ');assert.equal(document.title,'三国志・大陸戦役');assert(i18n.setLocale('zh-Hant'));assert.equal(heading.data,'保存進度');assert.equal(document.title,'三國·大陸戰役');}
 const storageBefore=[...storage];assert.equal(i18n.setLocale('zh-CN'),false);assert.equal(i18n.locale,'zh-Hant');assert.deepEqual([...storage],storageBefore);
 assert.equal(input.value,'13579');assert.equal(input.checked,true);assert.equal(language.children[0].children[0].data,'繁體中文');assert.equal(language.children[1].children[0].data,'日本語');
 assert.equal(storage.get('three-kingdoms-demo-save'),'unchanged-game-save');assert.equal(JSON.stringify(rows),before);assert.equal(requests.length,3);assert(requests.every(url=>url.startsWith('/locales/')));
 console.log(`i18n runtime: ${cases.length} exact/idempotence cases, ${rows.length} scenario titles, both-language DOM restoration, immutable form/save and invalid-locale checks passed`);
})().catch(error=>{console.error(error);process.exitCode=1;});
