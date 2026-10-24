/* No npm dependency: exercise the shipped browser translator in a minimal DOM. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
class Element{
 constructor(tag,attrs={}){this.nodeType=1;this.tagName=tag.toUpperCase();this.attrs={...attrs};this.dataset={};for(const[key,value]of Object.entries(attrs))if(key.startsWith('data-'))this.dataset[key.slice(5).replace(/-([a-z])/g,(_,letter)=>letter.toUpperCase())]=value;this.children=[];this.parentElement=null;this.hidden=false;}
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
const nativeTC=body.append(new Element('section',{'data-l10n-native':'zh-Hant','data-locale-only':'zh-Hant','aria-label':'金錢、糧食、預備兵'}));
const nativeTCText=nativeTC.append(new Text('金城 · 金旋 · 劉金 · 花費金50、糧20，預備兵300；黃金甲。'));
const nativeJA=body.append(new Element('section',{'data-l10n-native':'ja','data-locale-only':'ja','title':'金銭・兵粮・予備兵'}));
const nativeJAText=nativeJA.append(new Text('金城の金旋へ金50、糧20。予備兵300と黄金甲を確認します。'));
const rawLink=body.append(new Element('a',{id:'city-金钱',href:'https://example.invalid/金钱/粮食?gold=100','data-city-id':'金城'}));rawLink.append(new Text('金錢'));
const all=node=>[node,...(node.children||[]).flatMap(all)];
const events=[],document={documentElement:html,querySelector:s=>all(html).find(n=>n.nodeType===1&&n.matches(s))||null,querySelectorAll:s=>all(html).filter(n=>n.nodeType===1&&n.matches(s)),createTreeWalker(node){const nodes=all(node).slice(1);let index=0;return{currentNode:node,nextNode(){if(index===nodes.length)return false;this.currentNode=nodes[index++];return true;}};},addEventListener(){},dispatchEvent(e){events.push(e);return true;}};
Object.defineProperty(document,'title',{get:()=>title.data});
const storage=new Map([['three-kingdoms-save','unchanged-game-save']]),requests=[];
const context={window:{},document,Node:{TEXT_NODE:3,ELEMENT_NODE:1},NodeFilter:{SHOW_ELEMENT:1,SHOW_TEXT:4},MutationObserver:class{observe(){}disconnect(){}},CustomEvent:class{constructor(type,options){this.type=type;this.detail=options.detail;}},localStorage:{getItem:k=>storage.get(k)??null,setItem:(k,v)=>storage.set(k,String(v))},fetch:async url=>{requests.push(url);return{ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(root,'game',url),'utf8'))};},console};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'game/i18n.js'),'utf8'),context,{filename:'game/i18n.js'});
(async()=>{
 const i18n=context.window.GameI18n;await i18n.ready;
 assert.equal(i18n.locale,'zh-Hant');assert.equal(document.title,'三國·大陸戰役');assert.equal(heading.data,'保存進度');
 assert.equal(nativeTCText.data,'金城 · 金旋 · 劉金 · 花費資金50、兵糧20，預備兵300；黃金甲。');
 assert.equal(nativeTC.getAttribute('aria-label'),'資金、兵糧、預備兵');
 assert.equal(nativeJAText.data,'金城の金旋へ資金50、兵糧20。予備兵300と黄金甲を確認します。');
 assert.equal(nativeJA.getAttribute('title'),'資金・兵糧・予備兵');
 const index=JSON.parse(fs.readFileSync(path.join(root,'game/data/campaigns/index.json')));
 assert.equal(index.schema,'tk2-campaign-index-v1');assert.equal(index.catalogs.length,29);
 const rows=index.catalogs.map(file=>{const data=JSON.parse(fs.readFileSync(path.join(root,'game/data',file)));return{title:data.title,year:data.start_year,month:data.start_month,main_scenario:data.main_scenario};});
 const before=JSON.stringify(rows);i18n.registerScenarios(rows);
 const cases=[
  ['史实','史実'],['假想','仮想'],
  ['河北爭亂','河北争乱'],['合淝之戰','合肥の戦い'],
  ['呂布討伐戰','呂布討伐戦'],['潼關之戰','潼関の戦い'],
  ['袁尚势力 · 9座城池 · 根据地邺。钱 100 · 粮 200 · 预备兵 300 · 武将 40人 · 文吏 0人。地图已预览本剧本归属，开始后才建立新战役。','袁尚勢力 · 9都市 · 本拠鄴。資金100 · 兵糧200 · 予備兵300 · 武将40人 · 文吏0人。開始時の所属を表示中です。確定すると新しく開始します。'],
  ['200年1月 · 官渡之战','200年1月 · 官渡の戦い'],
  ['208年10月 · 赤壁之战','208年10月 · 赤壁の戦い'],
  ['官渡之战','官渡の戦い'],['赤壁之战','赤壁の戦い'],
  ['元データ説明','元データ説明'],['关羽','関羽'],['张辽','張遼'],['许昌','許昌'],
  ['钱 123 · 粮 456 · 预备兵 789','資金 123 · 兵糧 456 · 予備兵 789'],
  ['关羽攻击张辽，损兵17。','関羽が張遼を攻撃。17の兵力損耗。'],
  ['钱 123 · 粮 456 · 预备兵 789 · 武将 42人','資金 123 · 兵糧 456 · 予備兵 789 · 武将 42人'],
  ['曹操势力合计：钱 123 · 粮 456 · 预备兵 789 · 武将 42人','曹操勢力の合計：資金 123 · 兵糧 456 · 予備兵 789 · 武将 42人'],
  ['经','経'],['经验999','経験999'],['关羽 · 300兵 · 武97 · 知75 · 德70 · 体力97 · 经验86','関羽 · 300兵 · 武97 · 知75 · 徳70 · 体力97 · 経験86'],
  ['1023人武将库','武将名鑑・1023人'],['全部1023人','全1023人'],
  ['荀勖','荀勗'],['施績','朱績'],
  ['容量不足，尚未登场','都市の定員不足・未登場'],
  ['217年7月中旬　第2回合 · 1旬10日','217年7月中旬　第2ターン · 1旬10日'],
  ['约323.8公里 · 估算44日 · 5旬（每旬10日）','約323.8キロ · 44日 · 5旬（1旬10日）'],
  ['预计217年9月上旬到达。陆路行军。','217年9月上旬に到着予定。陸路で行軍します。'],
  ['最短日数 · 22日','最短日数 · 22日'],
  ['最短日数（海陆并用） · 42日','最短日数（陸海併用） · 42日'],
  ['陆路 · 57日','陸路 · 57日'],
  ['最短日数（陆路1） · 10日','最短日数（陸路1） · 10日'],
  ['未知航路探索（海路） · 35日','未知航路の探索（海路） · 35日'],
  ['内河水路','内陸水路'],['海河并用','海路・内陸水路併用'],
  ['含内河水路及陆地接入。','内陸水路と接続する陸路を含みます。'],
  ['内河不适用海路季风、暴风雨减员。','内陸水路には海路の季節風・暴風雨による兵力損失は適用されません。'],
  ['长江','長江'],['湘水（含洞庭出口）','湘水（洞庭湖の出口を含む）'],
  ['顺流','下り'],['逆流','上り'],['航速','航海速度'],
  ['探索未知航路','未知航路を探索'],
  ['城名：巨大都市','都市名：巨大都市'],['城名：大都市','都市名：大都市'],
  ['名：巨','名：巨'],['名：大','名：大'],
  ['取消未知航路探索','未知航路の探索をやめる'],
  ['没有已知的可用路线。','利用できる既知の経路がありません。'],
  ['还需5旬','あと5旬'],
  ['关羽 · 武97 · 知75 · 德70 · 300兵 · 体98','関羽 · 武97 · 知75 · 徳70 · 300兵 · 体力98'],
  ['音樂設定','音楽設定'],['背景音樂','背景音楽'],['操作音效','操作効果音'],
  ['目标：关羽','目標：関羽'],
  ['217年7月中旬　各势力本旬行动完成，进入下一旬战略阶段；每旬固定10天。','217年7月中旬　各勢力の今旬の行動が終了し、次の旬の戦略段階に入ります。1旬は10日です。'],
  ['武 40 / 知 70 / 德 60。武知为参考生涯的本作设计值，并非《三国志14》原始能力。年代含游戏估计，详见来源。','武 40 / 知 70 / 徳 60。武力・知力は事績を参考にした本作独自の設定値で、『三国志14』の原能力値ではありません。年代にはゲーム用の推定を含みます。根拠は出典を参照してください。'],
 ];
 for(const[source,expected]of cases){const translated=i18n.t(source,'ja');assert.equal(translated,expected,source);assert.equal(i18n.t(translated,'ja'),expected,'Japanese translation must be idempotent: '+source);}
 for(const row of rows){const once=i18n.t(row.title,'ja');assert.equal(i18n.t(once,'ja'),once,row.title);assert(!once.includes('の戦いの戦い'),row.title);}
 assert.equal(i18n.t('关羽','zh-Hant'),'關羽');
 const resourceCases=[
  ['金錢・糧食・預備兵','資金・兵糧・預備兵','資金・兵糧・予備兵'],
  ['金钱 · 粮食 · 预备兵','資金 · 兵糧 · 預備兵','資金 · 兵糧 · 予備兵'],
  ['资金 123 · 兵粮 456 · 预备兵 789','資金 123 · 兵糧 456 · 預備兵 789','資金 123 · 兵糧 456 · 予備兵 789'],
  ['金 123 · 錢456 · 糧 789','資金 123 · 資金456 · 兵糧 789','資金 123 · 資金456 · 兵糧 789'],
  ['花費金50、糧20','花費資金50、兵糧20','花費資金50、兵糧20'],
  ['花費50金、20糧','花費資金50、兵糧20','花費資金50、兵糧20'],
  ['最高費用金14–17；收入50金。','最高費用資金14–17；收入資金50。','最高費用資金14–17；收入資金50。'],
  ['金：100 · 糧：200 · 預備兵：300','資金：100 · 兵糧：200 · 預備兵：300','資金：100 · 兵糧：200 · 予備兵：300'],
  ['金— · 糧—','資金— · 兵糧—','資金— · 兵糧—'],
  ['金城50 · 金旋20 · 劉金10 · 黃金甲 · 金盔 · 金鎧','金城50 · 金旋20 · 劉金10 · 黃金甲 · 金盔 · 金鎧','金城50 · 金旋20 · 劉金10 · 黃金甲 · 金盔 · 金鎧'],
  ['city_金钱50 grain_粮食20 city-資金100 https://example.invalid/金钱/粮食?gold=100','city_金钱50 grain_粮食20 city-資金100 https://example.invalid/金钱/粮食?gold=100','city_金钱50 grain_粮食20 city-資金100 https://example.invalid/金钱/粮食?gold=100'],
 ];
 for(const[source,tc,ja]of resourceCases)for(const[language,expected]of [['zh-Hant',tc],['ja',ja]]){const result=i18n.resourceText(source,language);assert.equal(result,expected,language+': '+source);assert.equal(i18n.resourceText(result,language),expected,'Resource normalization is idempotent');assert.deepEqual(result.match(/\d+/g),source.match(/\d+/g),'Resource labels preserve every integer');}
 for(const source of ['city_金钱50 grain_粮食20 city-資金100 https://example.invalid/金钱/粮食?gold=100','https://example.invalid/金城/金旋?name=劉金'])for(const language of ['zh-Hant','ja'])assert.equal(i18n.t(source,language),source,'Translation preserves technical tokens');
 assert.equal(i18n.t('金钱50 · 粮食20 · 预备兵300','zh-Hant'),'資金50 · 兵糧20 · 預備兵300');
 assert.equal(i18n.t('金钱50 · 粮食20 · 预备兵300','ja'),'資金50 · 兵糧20 · 予備兵300');
 assert.equal(i18n.t('金城 · 金旋 · 劉金','zh-Hant'),'金城 · 金旋 · 劉金');
 assert.equal(i18n.t('内河水路：顺流、逆流；长江与湘水（含洞庭出口）。','zh-Hant'),'內河水路：順流、逆流；長江與湘水（含洞庭出口）。');
 for(let n=0;n<2;n++){assert(i18n.setLocale('ja'));assert.equal(heading.data,'セーブ');assert.equal(document.title,'三国志・大陸戦役');assert(i18n.setLocale('zh-Hant'));assert.equal(heading.data,'保存進度');assert.equal(document.title,'三國·大陸戰役');}
 assert.equal(nativeTCText.data,'金城 · 金旋 · 劉金 · 花費資金50、兵糧20，預備兵300；黃金甲。');assert.equal(nativeJAText.data,'金城の金旋へ資金50、兵糧20。予備兵300と黄金甲を確認します。');
 assert.equal(rawLink.getAttribute('href'),'https://example.invalid/金钱/粮食?gold=100');assert.equal(rawLink.getAttribute('id'),'city-金钱');assert.equal(rawLink.getAttribute('data-city-id'),'金城');
 const storageBefore=[...storage];assert.equal(i18n.setLocale('zh-CN'),false);assert.equal(i18n.locale,'zh-Hant');assert.deepEqual([...storage],storageBefore);
 assert.equal(input.value,'13579');assert.equal(input.checked,true);assert.equal(language.children[0].children[0].data,'繁體中文');assert.equal(language.children[1].children[0].data,'日本語');
 assert.equal(storage.get('three-kingdoms-save'),'unchanged-game-save');assert.equal(JSON.stringify(rows),before);assert.equal(requests.length,3);assert(requests.every(url=>url.startsWith('/locales/')));
 console.log(`i18n runtime: ${cases.length} translation cases, ${resourceCases.length} bilingual resource cases, ${rows.length} scenario titles, native DOM restoration, immutable names/IDs/URLs/form/save and invalid-locale checks passed`);
})().catch(error=>{console.error(error);process.exitCode=1;});
