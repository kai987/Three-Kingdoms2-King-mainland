/* Current equipment, source previews and shop comparisons are pure engine projections. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const equipment=require('../game/equipment.js'),clone=value=>JSON.parse(JSON.stringify(value));
const sword={id:33,name_tc:'雙股劍',name_ja:'双股剣',power:14,weight:6,family:'sword',appearance:'dual-swords'};
const armor={id:2,name_tc:'兜',name_ja:'兜',power:5,weight:4};
const before={scope:'current',person_id:'liubei',base_martial:79,weapon:sword,armor,attack_bonus:7,defense_bonus:2,total_weight:10,weight_penalty:2,initiative_base:61,hit_penalty:8,evasion_penalty:3,retreat_health_min:1,retreat_health_max:2,retreat_chance:35,initial:{note_tc:'初始裝備依人物ID配置。',note_ja:'初期装備は人物IDに対応します。'},owned:[]};
const after={...clone(before),weapon:{...sword,id:35,name_tc:'新劍',name_ja:'新剣'},attack_bonus:19,defense_bonus:4,total_weight:13,weight_penalty:7,initiative_base:52,hit_penalty:17,evasion_penalty:11,retreat_health_min:2,retreat_health_max:4,retreat_chance:50};
const initial={...clone(before),scope:'initial'};
const view={catalog:{equipment:{schema:'tk2-equipment-v1',items:{weapon:[sword],armor:[armor]},officers:{'8':before},special:[{slot:'weapon',item:33,condition_tc:'指定人物取得，僅此一把。',condition_ja:'指定の人物が入手でき、1振り限りです。',unique:true,claimed:true,holder:'liubei'}]},library:[{id:8,person_id:'liubei',name:'劉備'},{id:9,person_id:'unspawned',name:'未登場',equipment:initial}]}};
const snapshot=JSON.stringify(view);
const tc=equipment.summary(view,8,{bilingual:false});
assert(tc.includes('目前裝備'));assert(tc.includes('雙股劍'));assert(tc.includes('防具</strong> 兜'));
assert(tc.includes('基礎武79'));assert(tc.includes('單挑攻擊+7'));assert(tc.includes('防禦+2'));
assert(tc.includes('總重量10'));assert(tc.includes('攻擊減少2'));assert(tc.includes('先手基準61'));assert(tc.includes('命中修正-8百分點'));assert(tc.includes('回避修正-3百分點'));assert(tc.includes('退卻體力消耗 1–2'));assert(tc.includes('觸發機率 35%'));
assert(tc.includes('不改寫基礎武、知、德'));assert(tc.includes('初始裝備依人物ID配置'));
const ja=equipment.summary(view,'8',{locale:'ja',bilingual:false});
for(const text of ['現在の装備','双股剣','一騎討ちの攻撃+7','防御+2','命中補正-8ポイント','退却時の体力消費 1–2'])assert(ja.includes(text),text);
assert(!ja.includes('目前裝備'));assert(!ja.includes('雙股劍'));
const both=equipment.summary(view,8);assert(both.includes('data-locale-only="zh-Hant"'));assert(both.includes('data-locale-only="ja"'));
const compact=equipment.summary(view,8,{bilingual:false,compact:true});assert(compact.includes('雙股劍'));assert(compact.includes('防禦+2'));assert(!compact.includes('<h3>'));assert(!compact.includes('data-equipment-retreat'));
const pending=equipment.summary(view,9,{bilingual:false});assert(pending.includes('初始裝備'));assert(pending.includes('data-equipment-scope="initial"'));assert(!pending.includes('目前裝備'));
for(const[basis,tc,ja]of [['cnblogs_original_equipment_transcription','初始裝備參考原版公開武將表','原作の公開武将表'],['explicit_requested_novel_signature_override','代表兵器已配置為實際初始裝備','代表武器を実際の初期装備'],['remake_role_default; not_original_equipment','初始裝備採本作職能配置','役割別初期装備']]){const sourced={...clone(before),initial:{basis}};assert(equipment.render(sourced,{bilingual:false}).includes(tc));assert(equipment.render(sourced,{locale:'ja',bilingual:false}).includes(ja));assert(!equipment.render(sourced).includes(basis),'Implementation codes never become player-facing source labels');}
assert.equal(equipment.summary(view,'missing'),'');assert.equal(equipment.render(null),'');assert.equal(equipment.render({weapon:sword}),'');
const offer={id:35,preview_by_officer:{8:{before,after,eligible:true,reason_tc:'',reason_ja:''}}};
const comparison=equipment.comparison(view,8,offer,{bilingual:false});
for(const text of ['單挑攻擊 +7 → +19','防禦 +2 → +4','總重量 10 → 13','攻擊減少 2 → 7','先手基準 61 → 52','命中減少 8 → 17百分點','回避減少 3 → 11百分點','退卻耗體力機率 35 → 50%','1–2 → 2–4'])assert(comparison.includes(text),text);
assert(comparison.includes('data-equipment-eligible="true"'));
assert.equal(equipment.preview(offer,'8'),offer.preview_by_officer[8]);
const unavailable=clone(offer);unavailable.preview_by_officer[8].eligible=false;unavailable.preview_by_officer[8].reason_tc='此人不能購買';unavailable.preview_by_officer[8].reason_ja='この武将は購入できません';
assert(equipment.comparison(view,8,unavailable,{bilingual:false}).includes('此人不能購買'));
assert(equipment.comparison(view,8,unavailable,{bilingual:false,locale:'ja'}).includes('この武将は購入できません'));
assert(equipment.comparison(view,8,{}, {bilingual:false}).includes('確認引擎提供的效果比較'));
const guide=equipment.acquisition(view,{bilingual:false,open:true});assert(guide.includes('data-equipment-guide open'));assert(guide.includes('雙股劍'));assert(guide.includes('指定人物取得'));assert(guide.includes('本局唯一'));assert(guide.includes('本局已取得 · 劉備'));
assert(equipment.acquisition(view,{bilingual:false,locale:'ja'}).includes('特殊装備と入手条件'));
const unclaimed=clone(view);unclaimed.catalog.equipment.special[0].claimed=false;assert(equipment.acquisition(unclaimed,{bilingual:false}).includes('本局尚未取得'));
const staffHolder=clone(view);staffHolder.catalog.equipment.special[0].holder='clerk-000001';staffHolder.game={officers:{'clerk-000001':{person_id:'clerk-000001'}}};staffHolder.catalog.names={'clerk-000001':'周文'};const staffGuide=equipment.acquisition(staffHolder,{bilingual:false});assert(staffGuide.includes('本局已取得 · 周文'));assert(!staffGuide.includes('clerk-000001'),'Generated holders use their human name, never the private ID');
for(const names of [{},{'clerk-000001':'clerk-000001'}]){staffHolder.catalog.names=names;const missingHolder=equipment.acquisition(staffHolder,{bilingual:false});assert(missingHolder.includes('本局已取得'));assert(!missingHolder.includes('clerk-000001'),'Missing human names never expose an internal fallback ID');}
const malicious=clone(view);malicious.catalog.equipment.officers[8].weapon.name_tc='<img src=x onerror=bad>';malicious.catalog.equipment.officers[8].initial.note_tc='<script>bad</script>';
malicious.catalog.equipment.special[0].condition_tc='<img src=y>';malicious.catalog.library[0].name='<script>holder</script>';
for(const html of [equipment.summary(malicious,8),equipment.acquisition(malicious)]){assert(!html.includes('<img'));assert(!html.includes('<script>'));assert(html.includes('&lt;'));}
const malformed=clone(before);malformed.hit_penalty=null;malformed.evasion_penalty=Infinity;malformed.attack_bonus='100';malformed.retreat_chance=undefined;
const missing=equipment.render(malformed,{bilingual:false});assert(missing.includes('單挑攻擊—'));assert(missing.includes('命中修正—'));assert(missing.includes('回避修正—'));assert(missing.includes('觸發機率 —%'));
for(const bad of [null,undefined,Infinity,'7',{},NaN])assert.equal(equipment.signed(bad),'—');
assert.equal(equipment.signed(-4),'-4');assert.equal(equipment.signed(0),'0');assert.equal(equipment.signed(4),'+4');assert.equal(equipment.interval(2,2),'2');
assert.equal(JSON.stringify(view),snapshot,'Rendering and comparison never mutate profiles, equipment, inventory or RNG');
const browser={window:{}};vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../game/equipment.js'),'utf8'),browser);assert.equal(browser.window.GameEquipment.summary(view,8),equipment.summary(view,8));assert(Object.isFrozen(equipment));
console.log('equipment UI: actual/initial identities, bilingual current gear, server-only attack/defense/weight previews, special conditions, unknown values, HTML escaping and immutable rendering passed');
