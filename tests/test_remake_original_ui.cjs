/* Shared artwork identity, subpath URLs, bilingual provenance and failure paths. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),crypto=require('node:crypto');
const art=require('../game/original-ui.js'),source=fs.readFileSync(path.join(__dirname,'../game/original-ui.js'),'utf8');
const ids=['facility-armory','facility-hospital','facility-market','facility-school','command-city','command-army','command-warehouse','command-town','equipment-weapon-category','equipment-armor-category'];
const manifest=JSON.parse(fs.readFileSync(path.join(__dirname,'../game/assets/original-ui/index.json'),'utf8')),hash=raw=>crypto.createHash('sha256').update(raw).digest('hex');
assert.equal(manifest.schema,'tk2-original-ui-v1');assert.equal(manifest.provenance,'original-capture-derived');assert.equal(manifest.native_dimensions_confirmed,false);
assert.deepEqual(manifest.assets.map(row=>row.id),[...ids,'event-armory-interior','event-market-interior','event-sortie','event-decorative-frame']);
assert.equal(manifest.files.length,42);assert.equal(new Set(manifest.files.map(row=>row.path)).size,42);
for(const row of manifest.files){
 assert(/^\/assets\/original-ui\/(?:source\/|pixel-base\/)?[a-z][a-z0-9-]+\.png$/.test(row.path));
 const bytes=fs.readFileSync(path.join(__dirname,'../game',row.path.slice(1)));assert.equal(hash(bytes),row.sha256);assert.equal(bytes.length,row.bytes);
 assert.equal(bytes.subarray(0,8).toString('hex'),'89504e470d0a1a0a');assert.equal(bytes.readUInt32BE(16),row.width);assert.equal(bytes.readUInt32BE(20),row.height);
}
for(const row of manifest.assets){
 assert.equal(row.provenance,'original-capture-derived');assert.equal(row.native_dimensions_confirmed,false);assert.equal(row.source_crop.sha256,row.reference_crop_sha256,'Accepted source crops are preserved byte for byte');
 assert.equal(row.display_4x.width,row.pixel_base.width*4);assert.equal(row.display_4x.height,row.pixel_base.height*4);assert.equal(row.processing.palette_quantization,'none; sampled capture colors preserved');assert.equal(row.processing.pixel_base_is_approximation,true);
 assert(row.source_file.startsWith('art/original-ui-study/2026-10-24/screenshots/'));assert(/^[a-f0-9]{64}$/.test(row.source_sha256));
}
assert.notEqual(manifest.assets.find(row=>row.id==='event-armory-interior').sha256,manifest.assets.find(row=>row.id==='event-market-interior').sha256,'The distinct armory and merchant scenes are not accidentally aliased');
for(const id of ids){const html=art.icon(id);assert(html.includes(`src="/assets/original-ui/${id}-4x.png"`));assert(html.includes('alt="原版'));assert(html.includes('original-capture-derived'));assert(!html.includes('original-export-verified'));}
for(const [id,asset]of [['armory','event-armory-interior'],['market','event-market-interior'],['sortie','event-sortie']]){
 const html=art.scene(id,{locale:'ja',className:'event-original-scene'});assert(html.includes(`src="/assets/original-ui/${asset}-4x.png"`));assert(html.includes('original-ui-scene event-original-scene'));assert(html.includes('alt="原版の'));assert(!html.includes('width='),'Unconfirmed native dimensions are not guessed');
}
for(const bad of ['unknown','__proto__','constructor','../event-sortie','event-armory-interior',null,{},['armory']]){assert.equal(art.icon(bad),'');assert.equal(art.scene(bad),'');}
for(const slot of ['weapon','armor']){
 const item={id:slot==='weapon'?15:7,name_tc:'青龍"<刀',name_ja:'青龍"<刀'},before=JSON.stringify(item),html=art.equipment(slot,item,{locale:'ja',className:'equipment-item-icon'});
 assert(html.includes(`data-equipment-key="${slot}:${item.id}"`));assert(html.includes('remake-equipment-icon'));assert(!html.includes('original-capture-derived'));assert(html.includes('青龍&quot;&lt;刀'));assert(!html.includes('青龍"<刀'));assert.equal(JSON.stringify(item),before);
 const sources=new Set();for(let id=0;id<(slot==='weapon'?29:8);id++){
  const icon=art.equipment(slot,{id,name_tc:'單件'}),src=icon.match(/src="([^"]+)"/)[1];
  assert.equal(src,`/assets/equipment-icons/${slot}-${id}.png`);sources.add(src);
 }assert.equal(sources.size,slot==='weapon'?29:8,'Each catalog item has an individual asset');
 for(const id of ['0',true,NaN,Infinity,-1,1.5,slot==='weapon'?29:8])assert.equal(art.equipment(slot,{id}), '');
}
for(const value of [null,[],{},15])assert.equal(art.equipment('weapon',value),'');
assert.equal(art.equipment('shield',{id:0}),'');
assert(art.icon('facility-armory',{label:'<img "onerror=',className:'valid invalid" onclick="bad'}).includes('alt="原版&lt;img &quot;onerror='));
assert(!art.icon('facility-armory',{className:'valid invalid" onclick="bad'}).includes('onclick='));
assert(art.icon('command-city',{decorative:true}).includes('alt="" aria-hidden="true"'));
function browser(baseURI,paths){
 const listeners=new Map(),document={baseURI,addEventListener:(type,fn,capture)=>listeners.set(type,{fn,capture}),createElement:()=>({setAttribute(key,value){this[key]=value;}})},window={document,GamePaths:paths};
 vm.runInNewContext(source,{window,URL});return{api:window.GameOriginalUI,listeners};
}
const prefix='/Three-Kingdoms2-King-mainland',sub=browser(`https://example.test${prefix}/index.html`);
assert(sub.api.scene('market').includes(`src="https://example.test${prefix}/assets/original-ui/event-market-interior-4x.png"`));
assert(sub.api.equipment('weapon',{id:24,name_tc:'雙股劍'}).includes(`src="https://example.test${prefix}/assets/equipment-icons/weapon-24.png"`));
const resolved=browser('https://wrong.test/',{asset:value=>prefix+value});
assert(resolved.api.icon('facility-school').includes(`src="${prefix}/assets/original-ui/facility-school-4x.png"`),'The shipped GamePaths resolver takes priority');
assert.equal(sub.listeners.get('error').capture,true,'Native image errors are captured without inline handlers');
const attributes={'data-original-ui':'event-market-interior','data-original-ui-locale':'ja',src:`https://example.test${prefix}/assets/original-ui/event-market-interior-4x.png`,alt:'原版の商人取引の挿絵'},node={className:'event-original-scene',getAttribute:key=>attributes[key],replaceWith(value){this.replacement=value;}};
sub.listeners.get('error').fn({target:node});assert.equal(sub.api.scene('market'),'','A known failed asset lets the next render use its existing fallback');assert(sub.api.scene('armory'));assert.equal(node.replacement.textContent,'原図を読み込めませんでした');assert(node.replacement['aria-label'].includes(attributes.alt));
const unrelated=browser(`https://example.test${prefix}/`),foreign={...node,getAttribute:key=>key==='src'?'https://unrelated.test/no.png':attributes[key]};
unrelated.listeners.get('error').fn({target:foreign});assert(unrelated.api.scene('market'),'Unrelated failures do not poison verified assets');
const gearBrowser=browser(`https://example.test${prefix}/`),gearAttributes={'data-original-ui':'equipment-weapon-24','data-original-ui-locale':'zh-Hant',src:`https://example.test${prefix}/assets/equipment-icons/weapon-24.png`,alt:'雙股劍・武器像素圖'},gearNode={className:'equipment-item-icon',getAttribute:key=>gearAttributes[key],replaceWith(value){this.replacement=value;}};
gearBrowser.listeners.get('error').fn({target:gearNode});assert.equal(gearBrowser.api.equipment('weapon',{id:24}),'');assert(gearBrowser.api.equipment('weapon',{id:25}));assert.equal(gearNode.replacement.textContent,'圖示載入失敗');assert(gearNode.replacement['aria-label'].includes('雙股劍'));
console.log('original UI: original capture mappings, individual remake equipment identities, truthful provenance, bilingual escaping, subpath URLs and image failure fallback passed');
