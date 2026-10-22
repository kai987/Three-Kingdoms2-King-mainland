/* Stable identity, provenance, failed assets and read-only UI integration. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const {create,validIndex}=require('../game/portraits.js');
const manifest={schema:'tk2-portraits-v1',width:32,height:40,people:{
 'san14-person-a':{path:'/assets/portraits/original/000.png',kind:'nes_original',original_id:0},
 'san14-person-b':{path:'/assets/portraits/generated/san14-person-b.png',kind:'generated'},
 'historical-extra':{path:'/assets/portraits/generated/historical-extra.png',kind:'generated'},
}};
const library=[{id:0,person_id:'san14-person-a',name:'曹操'},{id:255,person_id:'san14-person-b',name:'趙雲'},
 {id:999,person_id:'historical-extra',name:'陸抗'}];
const catalog={library,names:{0:'曹操',255:'趙雲',999:'陸抗'}};
const source=fs.readFileSync(require('node:path').join(__dirname,'../game/app.js'),'utf8');
(async()=>{
 const events=new Map(),frames=[],doc={querySelectorAll:()=>frames,addEventListener:(name,fn)=>events.set(name,fn)};
 let requests=0;const i18n={locale:'zh-Hant',t:value=>value};
 const portraits=create({document:doc,i18n,fetch:async url=>{requests++;assert.equal(url,'/assets/portraits/index.json');return{ok:true,json:async()=>manifest};}});
 assert(portraits.html('san14-person-a','曹操',{source:true}).includes('肖像準備中'));
 const pending=portraits.load();assert.strictEqual(portraits.load(),pending);assert(await pending);assert.equal(requests,1);assert.equal(portraits.status,'ready');
 const original=portraits.html('san14-person-a','曹操',{size:'detail',source:true});
 assert(original.includes('portrait-detail'));assert(original.includes('原版像素肖像'));assert(original.includes('width="32" height="40"'));assert(original.includes('loading="lazy"'));assert(original.includes('decoding="async"'));assert(original.includes('alt="曹操的肖像"'));
 const generated=portraits.html('san14-person-b','趙雲',{source:true});assert(generated.includes('新增繪製肖像・非史實容貌'));assert(!generated.includes('原版像素肖像'));
 const before=JSON.stringify(catalog);assert.equal(portraits.personId(catalog,0),'san14-person-a');assert.equal(portraits.personId(catalog,'255'),'san14-person-b');assert.equal(portraits.personId(catalog,999),'historical-extra');assert.equal(portraits.personId(catalog,511),null);assert.equal(portraits.personId({library:[{id:255,person_id:'different-catalog-person'}]},255),'different-catalog-person');assert.equal(JSON.stringify(catalog),before);
 assert(!portraits.html('missing-id','未知',{source:true}).includes('<img'));assert(portraits.html('missing-id','未知',{source:true}).includes('肖像待補'));
 assert(!portraits.html('san14-person-b','<script>"',{}).includes('<script>'));assert(generated.includes('data-portrait-person="san14-person-b"'));
 for(const path of ['https://evil.example/a.png','/assets/portraits/original/../other.png','/assets/portraits/generated/a.svg','/assets/portraits/generated/a.png?x=1'])assert.throws(()=>validIndex({...manifest,people:{a:{kind:'generated',path}}}));
 assert.throws(()=>validIndex({...manifest,people:{a:{kind:'nes_original',original_id:255,path:'/assets/portraits/original/000.png'}}}));
 // A language change updates only portrait nodes, preserving unrelated inputs.
 const frame={dataset:{portraitPerson:'san14-person-b',portraitName:'趙雲',portraitSource:'1'},setAttribute(key,value){this[key]=value;},innerHTML:''};frames.push(frame);
 const untouchedInput={value:'unsaved search and cloud label'},unchanged=JSON.stringify(untouchedInput);
 i18n.locale='ja';events.get('game-language-change')();assert(frame.innerHTML.includes('趙雲の肖像'));assert(frame.innerHTML.includes('新規制作の肖像・史実の容貌ではありません'));assert.equal(JSON.stringify(untouchedInput),unchanged);
 const image={hasAttribute:key=>key==='data-portrait-image',closest:()=>frame};portraits.imageError({target:image});assert(!frame.innerHTML.includes('<img'));assert(frame.innerHTML.includes('肖像を読み込めませんでした'));
 const missing=create({document:doc,fetch:async()=>({ok:false})});assert.equal(await missing.load(),false);assert(missing.html('san14-person-a','曹操',{source:true}).includes('肖像待補'));
 let resolveLate;const stalled=create({timeoutMs:5,fetch:()=>new Promise(resolve=>{resolveLate=resolve;})});assert.equal(await stalled.load(),false);resolveLate({ok:true,json:async()=>manifest});await new Promise(resolve=>setImmediate(resolve));assert.equal(stalled.status,'unavailable');assert.equal(stalled.entry('san14-person-a'),null);
 // Rendering shipped views uses stable identities and never changes game state.
 const healthy=create({i18n,fetch:async()=>({ok:true,json:async()=>manifest})});await healthy.load();
 const elements=new Map(),element=selector=>{if(selector.startsWith('[data-')||selector==='#tactic'||selector==='#duel')return null;if(!elements.has(selector))elements.set(selector,{innerHTML:'',onclick:null});return elements.get(selector);};
 const officers={0:{health:90,loyalty:100,experience:0,troops:300,profile:{martial_strength:80,intellect:90,virtue:70}},255:{health:80,loyalty:80,experience:0,troops:300,profile:{martial_strength:95,intellect:80,virtue:85}},999:{health:70,loyalty:80,experience:0,troops:300,profile:{martial_strength:70,intellect:95,virtue:85}}};
 const context={view:{catalog,game:{player:'shu',officers,cities:{home:{id:'home',roster:{officer_ids:[0,255,999]}}},phase:'battle',rng:{state:123,draws:0}}},GamePortraits:healthy,GameI18n:i18n,escapeHtml:String,name:id=>catalog.names[id],marching:()=>new Set(),mapNavigation:null,actor:null,target:null,document:{querySelectorAll:()=>[]},$:element,cityName:String,command(){throw new Error('Rendering must not issue commands');},sourceEvidence:()=>'',virtueDescription:()=>'',showLibrary(){},openDialog(title,body){context.lastDialog={title,body};}};
 vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('const portraitHtml='),source.indexOf('\nconst faction=')),context);
 vm.runInContext(source.slice(source.indexOf('function rosterRows('),source.indexOf('function renderCity(')),context);
 vm.runInContext(source.slice(source.indexOf('function showPerson('),source.indexOf('function tactics(')),context);
 vm.runInContext(source.slice(source.indexOf('function renderDuel('),source.indexOf('function render(){')),context);
 const stateBefore=JSON.stringify(context.view.game),rows=context.rosterRows(context.view.game.cities.home);assert(rows.includes('san14-person-b'));assert(rows.includes('historical-extra'));assert(rows.includes('portrait-roster'));
 Object.assign(library[1],{era_assignment:null,alive:false,health_max:99,affinity:0,martial:95,intellect:80,virtue:85});context.showPerson(255);assert(context.lastDialog.body.includes('portrait-detail'));assert(context.lastDialog.body.includes('san14-person-b'));
 const battle={id:1,attacker:'shu',source:'home',target:'enemy',round:1,used:[],attackers:[{id:255,troops:300}],defenders:[{id:999,troops:300}],log:[]};context.view.game.battle=battle;const beforeBattle=JSON.stringify(context.view.game);context.renderBattle();assert(elements.get('#stage').innerHTML.includes('portrait-battle'));assert(elements.get('#stage').innerHTML.includes('historical-extra'));assert.equal(JSON.stringify(context.view.game),beforeBattle);
 battle.extended={duel:{actor:255,target:999,round:1,log:[]},support:{255:{health:80,energy:10},999:{health:70,energy:10}}};const beforeDuel=JSON.stringify(context.view.game);context.renderDuel(battle);assert.equal((elements.get('#stage').innerHTML.match(/portrait-duel/g)||[]).length,2);assert(elements.get('#stage').innerHTML.includes('san14-person-b'));assert(elements.get('#stage').innerHTML.includes('historical-extra'));assert.equal(JSON.stringify(context.view.game),beforeDuel);
 delete context.view.game.battle;assert.equal(JSON.stringify(context.view.game),stateBefore);
 console.log('portraits: stable IDs, original/generated provenance, single index load, native pixels, locale-only refresh, missing assets and read-only roster/profile/battle/duel views passed');
})().catch(error=>{console.error(error);process.exitCode=1});
