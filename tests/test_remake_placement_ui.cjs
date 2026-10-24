/* Optional placement evidence remains distinct from historical posting and runtime entry. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.resolve(__dirname,'..'),source=fs.readFileSync(path.join(root,'game/app.js'),'utf8');
const escapeHtml=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const elements=new Map(),element=key=>{if(!elements.has(key))elements.set(key,{onclick:null,value:'preserve search'});return elements.get(key);};
const person={id:1001,person_id:'historical-person-001',name:'張三',missing:[],alive:null,year_state:'not_appeared',health_max:90,affinity:0,martial:80,intellect:70,virtue:60,era_assignment:{city:'jianan',faction:'wu',source_status:'not_appeared'}};
const context={GameOfficerChoices:require('../game/officer-choice.js'),URL,escapeHtml,cityName:id=>({jianan:'建安',henan:'洛陽'})[id]||id,GameI18n:{locale:'zh-Hant',t:(value,language)=>language==='ja'?String(value).replace('入蜀爭奪戰','入蜀争奪戦'):String(value)},view:{catalog:{library:[person]},game:null},portraitHtml:()=>'<i>肖像</i>',sourceEvidence:()=>'',virtueDescription:()=>'<p>德60</p>',faction:String,showLibrary(){},$:element,openDialog(title,body){context.dialogContent={title,body};}};
vm.createContext(context);
vm.runInContext(source.slice(source.indexOf('function sourceReference('),source.indexOf('function virtueDescription(')),context);
vm.runInContext(source.slice(source.indexOf('function initialStatDescription('),source.indexOf('function showPerson(')),context);
vm.runInContext(source.slice(source.indexOf('function showPerson('),source.indexOf('function tactics(')),context);
for(const invalid of ['javascript:alert(1)','http://example.com','//example.com','data:text/html,<script>','https://user:password@example.com/x',' https://example.com','https://'])assert.equal(context.sourceReference(invalid),null,invalid);
assert.equal(context.sourceReference('https://example.com/source#section'),'https://example.com/source#section');
assert.equal(context.personPlacementEvidence(undefined),'');assert.equal(context.personPlacementEvidence({status:'serving',city:'henan'}),'');
const review={basis:'reviewed_biography_window',historical_certainty:'bounded_career_inference',source_urls:['https://example.com/source#section','javascript:alert(1)','https://example.com/source#section'],note:'同勢力防務配置 <script>bad()</script>',reference_date:[211,7],reference_scenario:'mainland211-07',title:'入蜀爭奪戰'};
const plan={start:[260,10],end:[263,12],city:'jianan',status:'future_free',basis:'reviewed_first_service_region'};
const a={...person.era_assignment,placement_review:review,appearance_plan:plan};
const before=JSON.stringify(a),html=context.personPlacementEvidence(a);
assert.equal(JSON.stringify(a),before,'Evidence rendering may not alter placement plans');
assert(html.includes('data-locale-only="zh-Hant" data-l10n-native="zh-Hant"'));
assert(html.includes('data-locale-only="ja" data-l10n-native="ja"'));
assert(html.includes('有年代界限的生涯推定'));assert(html.includes('年代を限定した経歴に基づく推定'));
assert(html.includes('參考年月：211年7月'));assert(html.includes('参照シナリオ：入蜀争奪戦'));
assert(html.includes('首次登場窗口：260年10月 — 263年12月'));assert(html.includes('予定都市：建安'));
assert(html.includes('不代表史實退仕'));assert(html.includes('史実の辞官・下野を示すものではなく'));
assert(html.includes('本作防務分配不等於史載駐軍'));assert(html.includes('史料に記録された駐屯を意味しません'));
assert(!html.includes('<script>'));assert(html.includes('&lt;script&gt;'));assert(!html.includes('javascript:'));
assert.equal((html.match(/href="https:\/\/example.com\/source#section"/g)||[]).length,2,'One safe source per language after deduplication');
for(const [certainty,tc,ja] of [['game_reference','公開遊戲配置參考','公開ゲームの配置資料'],['authorial_region_placement','本作區域防務配置','本作独自の地域・防衛配置']]){
 const result=context.personPlacementEvidence({placement_review:{...review,historical_certainty:certainty},appearance_plan:{...plan,status:'serving'}});assert(result.includes(tc));assert(result.includes(ja));assert(result.includes('開局在籍'));assert(result.includes('開始時に仕官中'));
}
const excluded=context.personPlacementEvidence({appearance_plan:{status:'excluded'}});assert(excluded.includes('本劇本不登場'));assert(excluded.includes('本シナリオでは登場しない'));assert(!excluded.includes('undefined'));
// Optional missing evidence does not invent an attribution or show obsolete membership text.
context.showPerson(person.id);assert(!context.dialogContent.body.includes('person-placement-evidence'));
person.era_assignment={...a,membership_resolution:{basis:'reviewed_career_window_v13'},membership_revision:{reason:'superseded-generation-proof'}};
const gameBefore=JSON.stringify(context.view);context.showPerson(person.id);
assert(context.dialogContent.body.includes('person-placement-evidence'));assert(context.dialogContent.body.includes('data-appearance-status="future_free"'));
assert(!context.dialogContent.body.includes('开局来源'));assert(!context.dialogContent.body.includes('superseded-generation-proof'));
assert(context.dialogContent.body.includes('武知来自第三方SAN14数值转写'));assert(context.dialogContent.body.includes('德60'));
assert.equal(JSON.stringify(context.view),gameBefore,'Person details must not change current game/library state');
context.GameI18n.locale='ja';context.showPerson(person.id);assert.equal(element('#library-search').value,'preserve search');assert.equal(JSON.stringify(context.view),gameBefore);
console.log('placement UI: current TC/JP evidence, first-appearance dates/city, safe links, historical caveats, no obsolete provenance and immutable game/input passed');
