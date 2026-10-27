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
 // An enhanced variant is an optional presentation asset; original bindings
 // and their provenance remain the canonical row even when it is displayed.
 const enhancedPath=id=>`/assets/portraits/enhanced/${id}.png`;
 const enhancedManifest={...manifest,people:{...manifest.people,
  'san14-person-a':{...manifest.people['san14-person-a'],enhanced:{path:enhancedPath('san14-person-a'),width:128,height:160}},
  'san14-person-b':{...manifest.people['san14-person-b'],enhanced:{path:enhancedPath('san14-person-b'),width:128,height:160}},
 }};
 const validEnhanced=validIndex(enhancedManifest);
 assert.equal(validEnhanced.width,32);assert.equal(validEnhanced.height,40);
 assert.equal(validEnhanced.people['san14-person-a'].path,manifest.people['san14-person-a'].path);
 assert.equal(validEnhanced.people['san14-person-a'].original_id,0);
 assert(Object.isFrozen(validEnhanced.people['san14-person-a'].enhanced));
 for(const variant of [null,[],true,'image.png',{},
  {path:enhancedPath('san14-person-a'),width:32,height:40},
  {path:enhancedPath('san14-person-a'),width:128,height:159},
  {path:enhancedPath('san14-person-a'),width:'128',height:160},
  ...[null,'unknown',true,4].map(rendering=>({path:enhancedPath('san14-person-a'),width:128,height:160,rendering})),
  {path:[enhancedPath('san14-person-a')],width:128,height:160},
  ...['https://evil.example/a.png','/assets/portraits/enhanced/../a.png','/assets/portraits/enhanced/a.svg','/assets/portraits/enhanced/a.png?x=1','/assets/portraits/generated/a.png','/assets/portraits/enhanced/.png',`/assets/portraits/enhanced/${'a'.repeat(129)}.png`].map(path=>({path,width:128,height:160})),
 ])assert.throws(()=>validIndex({...manifest,people:{a:{...manifest.people['san14-person-a'],enhanced:variant}}}));
 const enhancedFrames=[],enhancedEvents=new Map(),enhancedI18n={locale:'zh-Hant',t:value=>value};
 const enhancedDoc={querySelectorAll:()=>enhancedFrames,addEventListener:(name,fn)=>enhancedEvents.set(name,fn)};
 const enhanced=create({document:enhancedDoc,i18n:enhancedI18n,fetch:async()=>({ok:true,json:async()=>enhancedManifest})});
 assert(await enhanced.load());
 for(const size of ['roster','library','battle','duel','detail']){
  const html=enhanced.html('san14-person-a','曹操',{size,source:true});
  assert(html.includes(`portrait-${size}`));assert(html.includes(`src="${enhancedPath('san14-person-a')}"`));
  assert(html.includes('width="128" height="160"'));assert(html.includes('原版像素肖像・明暗強化'));
 }
 assert(enhanced.html('san14-person-b','趙雲',{source:true}).includes('新增繪製肖像・明暗強化・非史實容貌'));
 assert(enhanced.html('historical-extra','陸抗',{source:true}).includes('width="32" height="40"'));
 const enhancedCatalogBefore=JSON.stringify(catalog);
 for(const officer of library)assert.equal(enhanced.personId(catalog,officer.id),officer.person_id);
 assert.equal(JSON.stringify(catalog),enhancedCatalogBefore);
 const hdFrame={dataset:{portraitPerson:'san14-person-a',portraitName:'曹操',portraitSource:'1'},setAttribute(key,value){this[key]=value;},innerHTML:''};
 enhancedFrames.push(hdFrame);enhanced.refresh();
 enhancedI18n.locale='ja';enhancedEvents.get('game-language-change')();
 assert(hdFrame.innerHTML.includes('原作のドット肖像・陰影強化'));assert(hdFrame.innerHTML.includes('曹操の肖像'));
 const attemptedImage=path=>({hasAttribute:key=>key==='data-portrait-image',getAttribute:key=>key==='src'?path:null,closest:()=>hdFrame});
 enhanced.imageError({target:attemptedImage('/assets/portraits/enhanced/unrelated.png')});
 assert(hdFrame.innerHTML.includes(enhancedPath('san14-person-a')));
 enhanced.imageError({target:attemptedImage(enhancedPath('san14-person-a'))});
 assert(hdFrame.innerHTML.includes(`src="${manifest.people['san14-person-a'].path}"`));
 assert(hdFrame.innerHTML.includes('width="32" height="40"'));assert(!hdFrame.innerHTML.includes('陰影強化'));
 assert(hdFrame.innerHTML.includes('原作のドット肖像'));assert(enhanced.html('san14-person-b','趙雲').includes(enhancedPath('san14-person-b')));
 // A late error from the detached HD image must not mark the native fallback
 // as failed, and a subsequent native failure should become the placeholder.
 enhanced.imageError({target:attemptedImage(enhancedPath('san14-person-a'))});
 assert(hdFrame.innerHTML.includes(`src="${manifest.people['san14-person-a'].path}"`));
 enhanced.imageError({target:attemptedImage(manifest.people['san14-person-a'].path)});
 assert(!hdFrame.innerHTML.includes('<img'));assert(hdFrame.innerHTML.includes('肖像を読み込めませんでした'));
 // The actual Pages resolver changes DOM URLs while failedPaths and registry
 // identity remain canonical. Both historical and civil HD failures must load
 // their native asset under the same project path, never the domain root.
 const subpath='/Three-Kingdoms2-King-mainland',subFrames=[],subEvents=new Map();
 const subDoc={currentScript:{src:`https://kai987.github.io${subpath}/paths.js`},querySelectorAll:()=>subFrames,addEventListener:(name,fn)=>subEvents.set(name,fn),createElement:()=>({setAttribute(){}})};
 const subWindow={document:subDoc,GameI18n:{locale:'zh-Hant',t:value=>value},fetch:async()=>({ok:true,json:async()=>enhancedManifest})};
 const subContext=vm.createContext({window:subWindow,URL,AbortController,setTimeout,clearTimeout});
 vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../game/paths.js'),'utf8'),subContext);
 vm.runInContext(fs.readFileSync(require('node:path').join(__dirname,'../game/portraits.js'),'utf8'),subContext);
 const subPortraits=subWindow.GamePortraits;assert(await subPortraits.load());
 const subFrame={dataset:{portraitPerson:'san14-person-a',portraitName:'曹操',portraitSource:'1'},setAttribute(){},innerHTML:''};subFrames.push(subFrame);subPortraits.refresh();
 assert(subFrame.innerHTML.includes(`src="${subpath}${enhancedPath('san14-person-a')}"`));
 const subImage=path=>({hasAttribute:key=>key==='data-portrait-image',getAttribute:key=>key==='src'?path:null,closest:()=>subFrame});
 subPortraits.imageError({target:subImage(`${subpath}${enhancedPath('san14-person-a')}`)});
 assert(subFrame.innerHTML.includes(`src="${subpath}${manifest.people['san14-person-a'].path}"`));
 assert(subFrame.innerHTML.includes('width="32" height="40"'));
 assert.equal(subPortraits.asset('san14-person-a').path,manifest.people['san14-person-a'].path);
 assert.equal(subPortraits.asset('san14-person-b').path,enhancedPath('san14-person-b'));
 subPortraits.imageError({target:subImage(`${subpath}${enhancedPath('san14-person-a')}`)});
 assert.equal(subPortraits.asset('san14-person-a').path,manifest.people['san14-person-a'].path);
 subPortraits.imageError({target:subImage(`${subpath}${manifest.people['san14-person-a'].path}`)});
 assert.equal(subPortraits.asset('san14-person-a'),null);assert(!subFrame.innerHTML.includes('<img'));
 const civilAttrs={'data-civil-portrait':'clerk-1',src:`${subpath}/assets/civil-staff/enhanced/clerk-1.png`,alt:'文吏'};
 const subCivil={className:'civil-staff-portrait',hasAttribute:key=>key in civilAttrs,getAttribute:key=>civilAttrs[key]??null,setAttribute:(key,value)=>{civilAttrs[key]=value;},replaceWith(node){this.replacement=node;}};
 subPortraits.imageError({target:subCivil});
 assert.equal(civilAttrs.src,`${subpath}/assets/civil-staff/clerk-1.png`);assert.equal(civilAttrs.width,'32');assert.equal(civilAttrs.height,'40');
 assert.equal(subPortraits.civilAsset('clerk-1').path,'/assets/civil-staff/clerk-1.png');
 assert(subPortraits.civilHtml('clerk-1','文吏').includes(`src="${subpath}/assets/civil-staff/clerk-1.png"`));
 subPortraits.imageError({target:subCivil});assert.equal(subPortraits.civilAsset('clerk-1'),null);assert.equal(subCivil.replacement.textContent,'吏');
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
 const context={GameOfficerChoices:require('../game/officer-choice.js'),view:{catalog,game:{player:'shu',officers,cities:{home:{id:'home',roster:{officer_ids:[0,255,999]}}},phase:'battle',rng:{state:123,draws:0}}},GamePortraits:healthy,GameI18n:i18n,escapeHtml:String,name:id=>catalog.names[id],marching:()=>new Set(),mapNavigation:null,actor:null,target:null,document:{querySelectorAll:()=>[]},$:element,cityName:String,command(){throw new Error('Rendering must not issue commands');},sourceEvidence:()=>'',virtueDescription:()=>'',showLibrary(){},openDialog(title,body){context.lastDialog={title,body};}};
 vm.createContext(context);
 vm.runInContext(source.slice(source.indexOf('const portraitHtml='),source.indexOf('\nconst faction=')),context);
 vm.runInContext(source.slice(source.indexOf('function officerAttributes('),source.indexOf('function renderCity(')),context);
 vm.runInContext(source.slice(source.indexOf('function initialStatDescription('),source.indexOf('function showPerson(')),context);
 vm.runInContext(source.slice(source.indexOf('function showPerson('),source.indexOf('function tactics(')),context);
 vm.runInContext(source.slice(source.indexOf('function renderDuel('),source.indexOf('function render(){')),context);
 context.view.game.extension={leaders:{shu:0}};context.isRuler=id=>context.GameOfficerChoices.isRuler(id,context.view.game.extension.leaders);
 const stateBefore=JSON.stringify(context.view.game),rows=context.rosterRows(context.view.game.cities.home);assert(rows.includes('san14-person-b'));assert(rows.includes('historical-extra'));assert(rows.includes('portrait-roster'));assert(rows.includes('忠--'));assert(rows.includes('<td>--</td>'));assert(rows.includes('<td>80</td>'));
 Object.assign(library[1],{era_assignment:null,alive:false,health_max:99,affinity:0,martial:95,intellect:80,virtue:85});context.showPerson(255);assert(context.lastDialog.body.includes('portrait-detail'));assert(context.lastDialog.body.includes('san14-person-b'));
 const battle={id:1,attacker:'shu',source:'home',target:'enemy',round:1,used:[],attackers:[{id:255,troops:300}],defenders:[{id:999,troops:300}],log:[]};context.view.game.battle=battle;const beforeBattle=JSON.stringify(context.view.game);context.renderBattle();assert(elements.get('#stage').innerHTML.includes('portrait-battle'));assert(elements.get('#stage').innerHTML.includes('historical-extra'));assert.equal(JSON.stringify(context.view.game),beforeBattle);
 battle.extended={duel:{actor:255,target:999,round:1,log:[]},support:{255:{health:80,energy:10},999:{health:70,energy:10}}};const beforeDuel=JSON.stringify(context.view.game);context.renderDuel(battle);assert.equal((elements.get('#stage').innerHTML.match(/portrait-duel/g)||[]).length,2);assert(elements.get('#stage').innerHTML.includes('san14-person-b'));assert(elements.get('#stage').innerHTML.includes('historical-extra'));assert.equal(JSON.stringify(context.view.game),beforeDuel);
 delete context.view.game.battle;assert.equal(JSON.stringify(context.view.game),stateBefore);
 // Use the shipped index and canonical identities for the appended rulers and
 // retainers, so runtime1024+ cannot silently fall back to an old portrait.
 const shipped=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../game/assets/portraits/index.json'),'utf8'));
 const peoplePool=JSON.parse(fs.readFileSync(require('node:path').join(__dirname,'../game/config/campaigns/people.json'),'utf8'));
 const additions=['historical-song-jian','historical-lu-xing','historical-tang-pu','historical-li-tong-jiaozhi','historical-beigong-boyu','historical-li-wenhou','historical-bian-zhang'];
 i18n.locale='zh-Hant';
 const released=create({i18n,fetch:async()=>({ok:true,json:async()=>shipped})});assert(await released.load());
 const allGenerated=Object.entries(shipped.people).filter(([,row])=>row.kind==='generated');assert.equal(allGenerated.length,831);
 assert.equal(Object.keys(shipped.people).length,1052);
 assert.equal(Object.values(shipped.people).filter(row=>row.kind==='nes_original').length,221);
 assert.equal(shipped.by_runtime_id['1044'],'historical-wang-jian-liaodong');
 assert.equal(shipped.people['historical-wang-jian-liaodong'].kind,'nes_original');
 assert.equal(shipped.people['historical-wang-jian-liaodong'].original_id,11);
 for(const[pid,row]of allGenerated){
  const display=released.asset(pid);assert.equal(display.enhanced,true,pid);
  assert.equal(display.path,row.enhanced.path,pid);assert.equal(display.width,128,pid);assert.equal(display.height,160,pid);
 }
 const appendedCatalog={library:additions.map(pid=>({id:peoplePool.people[pid].runtime_id,person_id:pid,name:peoplePool.people[pid].name}))};
 for(const[at,pid]of additions.entries()){
  const runtime=1024+at;assert.equal(peoplePool.people[pid].runtime_id,runtime);
  assert.equal(shipped.by_runtime_id[String(runtime)],pid);assert.equal(released.personId(appendedCatalog,runtime),pid);
  assert.equal(released.asset(pid).path,`/assets/portraits/enhanced/${pid}.png`);
  const visible=released.html(pid,peoplePool.people[pid].name,{source:true});
  assert(visible.includes(`data-portrait-person="${pid}"`));
  assert(visible.includes('128×160'));assert(visible.includes('非史實容貌'));assert(!visible.includes('4倍放大'));
  assert.equal(shipped.people[pid].enhanced.rendering,'redrawn128');
  assert.equal(shipped.people[pid].kind,'generated');assert.equal(shipped.people[pid].original_id,null);
 }
 i18n.locale='ja';
 const redrawnJapanese=released.html(additions[0],'宋建',{source:true});
 assert(redrawnJapanese.includes('128×160'));assert(redrawnJapanese.includes('史実の容貌ではありません'));assert(!redrawnJapanese.includes('4倍拡大'));
 console.log('portraits: stable IDs, original/generated provenance, enhanced variants and native error fallback, strict paths/dimensions, single index load, locale-only refresh, missing assets and read-only roster/profile/battle/duel views passed');
})().catch(error=>{console.error(error);process.exitCode=1});
