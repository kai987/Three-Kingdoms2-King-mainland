/* Three immutable civil templates get HD assets without changing identities. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const {create}=require('../game/portraits.js'),{check}=require('../tools/civil-portraits/build.cjs');
assert.equal(check().portraits,3);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const originalHashes=['a38597416450cb9032c7f54203dfafd70bc747c3dadebb49c6854752b6542b3a','c50b0fe4e7a0589c0e14a21bd2cbe1002c1cb7b9a64dcfa3c7ba1d8a01f7dfc3','28238152a87b79fcbdeeff9c952f52db5c65d30704f564d892feb98629bac834'];
for(let i=1;i<=3;i++)assert.equal(sha(fs.readFileSync(`game/assets/civil-staff/clerk-${i}.png`)),originalHashes[i-1],'Keep every native32x40 file byte-identical');
const frames=[],doc={querySelectorAll:()=>frames,addEventListener(){},createElement(){return{setAttribute(){},textContent:'',className:''};}},i18n={locale:'zh-Hant',t:value=>value};
const portraits=create({document:doc,i18n,fetch:async()=>({ok:true,json:async()=>({schema:'tk2-portraits-v1',width:32,height:40,people:{}})})});
const pool={people:[1,2,3].map((n)=>({id:`clerk-${String(n).padStart(6,'0')}`,name:'文吏'+n,portrait:'clerk-'+n}))},before=JSON.stringify(pool);
portraits.registerGenerated(pool);
for(let i=1;i<=3;i++){
 const id='clerk-'+String(i).padStart(6,'0'),key='clerk-'+i,row=portraits.entry(id),asset=portraits.asset(id);
 assert.equal(row.path,`/assets/civil-staff/${key}.png`);assert.equal(row.enhanced.path,`/assets/civil-staff/enhanced/${key}.png`);
 assert.equal(asset.width,128);assert.equal(asset.height,160);assert.equal(portraits.personId({},id),id);
 for(const size of ['roster','library','battle','duel','detail'])assert(portraits.html(id,'文吏',{size}).includes(`src="${asset.path}"`));
 for(const locale of ['zh-Hant','ja']){const html=portraits.civilHtml(key,'<文吏>',{locale,className:'event-staff-face'});assert(html.includes('width="128" height="160"'));assert(html.includes('event-staff-face'));assert(html.includes('&lt;文吏&gt;'));assert(html.includes(locale==='ja'?'架空の文吏':'架空文吏'));}
 assert(!portraits.failAsset(id,'/assets/civil-staff/enhanced/another.png'));assert.equal(portraits.asset(id).path,asset.path);
 assert(portraits.failAsset(id,asset.path));assert.equal(portraits.asset(id).path,row.path);assert.equal(portraits.asset(id).width,32);
 assert(portraits.failAsset(id,row.path));assert.equal(portraits.asset(id),null);assert(!portraits.html(id,'文吏').includes('<img'));
}
assert.equal(JSON.stringify(pool),before,'Asset registration and failures do not mutate generated people or saved portrait keys');
// Civil cards and event snapshots share the same fallback policy even when an
// event refers to an expired candidate absent from the current runtime pool.
const fallback=create({document:doc,i18n}),key='clerk-2',enhanced='/assets/civil-staff/enhanced/clerk-2.png',native='/assets/civil-staff/clerk-2.png';
function image(src){const attrs={'data-civil-portrait':key,src},img={className:'event-staff-face',replaced:null,hasAttribute:k=>Object.hasOwn(attrs,k),getAttribute:k=>attrs[k],setAttribute(k,v){attrs[k]=v;},replaceWith(node){this.replaced=node;}};return img;}
const first=image(enhanced),peer=image(enhanced);fallback.imageError({target:first});assert.equal(first.getAttribute('src'),native);assert.equal(first.getAttribute('width'),'32');assert.equal(first.getAttribute('height'),'40');
fallback.imageError({target:peer});assert.equal(peer.getAttribute('src'),native,'A late error on another image must also fall back');
fallback.imageError({target:first});assert(first.replaced);assert.equal(first.replaced.textContent,'吏');assert(!fallback.civilHtml(key,'文吏').includes('<img'));
fallback.imageError({target:peer});assert(peer.replaced);assert(!fallback.civilHtml(key,'文吏').includes('<img'),'Repeated native errors never restart enhanced requests');
assert(fallback.civilHtml('clerk-1','文吏').includes('/enhanced/clerk-1.png'),'One missing template cannot poison another');
for(const invalid of ['clerk-4','../clerk-1','clerk-1?x=1','https://evil.example/a.png','" onerror="x']){assert.equal(fallback.civilAsset(invalid),null);assert(!fallback.civilHtml(invalid,'文吏').includes('<img'));}
assert(!fallback.civilHtml('clerk-1','文吏',{className:'" onerror="x'}).includes('onerror'));
const staff=require('../game/civil-staff.js');assert(staff.portrait(pool.people[0]).includes('/assets/civil-staff/enhanced/clerk-1.png'));
console.log('civil portraits: three128x160 variants, original hashes/geometry/ink/palette, fixedclerkIDs, allportraitsurfaces, snapshotfallback, locale/escaping and read-only state passed');
