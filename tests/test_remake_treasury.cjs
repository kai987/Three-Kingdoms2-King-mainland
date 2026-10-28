/* Treasury UI uses server reward previews; drafts, inspection and failed writes are pure. */
'use strict';
const commandBookFixture=require('./fixtures/command-books.cjs');
const assert=require('node:assert/strict');
globalThis.GameOfficerChoices=require('../game/officer-choice.js');
const treasury=require('../game/treasury.js');
const clone=value=>JSON.parse(JSON.stringify(value));
const officer=(id,virtue,loyalty,intellect=60)=>({runtime_id:id,person_id:String(id),faction_id:'shu',alive:true,troops:300,health:70,experience:50,loyalty,profile:{martial_strength:55,intellect,virtue,health_max:80}});
const target=(id,loyalty)=>({id,loyalty,gold_max:100,treasure_max:1,gold_rewards:[[1,23],[24,46],[47,69],[70,92],[93,100]].map(([min,max],index)=>({min,max,gain:index+1,loyalty:loyalty+index+1})),treasure_reward:{amount:1,gain:9,loyalty:loyalty+9}});
const policy={enabled:false,target_loyalty:90,gold_budget:100,gold_floor:100,treasure_floor:1,prefer:'gold'};
const base={revision:0,catalog:{scenario_id:'test-campaign',names:{1:'劉備',2:'太守',3:'甲將','clerk-000001':'文吏'},treasury:{schema:'tk2-treasury-view-v1',rules:{city_cap:99,search_gold:20,sell_gold_per_treasure:100,reward_gold_max:100,loyalty_cap:100},cities:{home:{owner:'shu',treasure:2,governor:2,governor_mode:'manual',governor_candidates:[1,2,3,'clerk-000001'],eligible_actors:[2,1,3,'clerk-000001'],can_manage:true,can_search:true,can_sell:true,can_reward:true,search_fee:20,search_chances:{1:65,2:50,3:58,'clerk-000001':59},sell_max:2,reward_targets:[target(2,70),target(3,40),target('clerk-000001',40),target(1,100)]}},factions:{shu:{policy}}}},game:{player:'shu',seed:2026,turn:1,phase:'city',rng:{state:2026,draws:0},cities:{home:{id:'home',owner:'shu',gold:125,action_used:false,roster:{officer_ids:[1,2,3,'clerk-000001']}}},officers:{1:officer(1,99,100),2:officer(2,80,70),3:officer(3,80,40,85),'clerk-000001':officer('clerk-000001',80,40,86)},extension:{leaders:{shu:1},treasury:{cities:{home:{treasure:2,governor:2,governor_mode:'manual'}}}}}};
commandBookFixture.attach(base);
const original=JSON.stringify(base);
assert.equal(treasury.count(base,'home'),2);assert.equal(treasury.count({catalog:base.catalog},'home'),2);assert.equal(treasury.count(base,'absent'),0);
assert.deepEqual(treasury.sortActors([2,1,3,'clerk-000001',2,'<bad>'],base),[1,'clerk-000001',3,2]);
assert.deepEqual(treasury.sortTargets(base.catalog.treasury.cities.home.reward_targets,base).map(row=>row.id),[3,'clerk-000001',2]);
for(const locale of ['zh-Hant','ja']){
 assert(treasury.attributes(base,1,locale).includes('忠--'));assert(treasury.attributes(base,2,locale).includes('忠70'));assert(treasury.attributes(base,2,locale).startsWith('兵300'));
 assert(treasury.summary(base,'home',{locale,bilingual:false}).includes('data-city-treasure="home">2</strong>/99'));
}
assert(treasury.summary(base,'home').includes('data-locale-only="ja"'));
const noGovernor=clone(base);noGovernor.catalog.treasury.cities.home.governor=null;
assert(treasury.summary(noGovernor,'home').includes('尚無適任者'),'An explicit current null governor must not fall back to a stale saved appointment');
assert.equal(treasury.rewardPreview(base,'home',3,'gold',43).gain,2);assert.equal(treasury.rewardPreview(base,'home',3,'gold',43).loyalty,42);
assert.deepEqual(treasury.rewardPreview(base,'home',3,'treasure',999),{max:1,amount:1,gain:9,loyalty:49,valid:true});
assert.equal(treasury.rewardPreview(base,'home',1,'gold',100).valid,false,'The current ruler cannot receive a reward');
assert.equal(treasury.rewardPreview(base,'home',2,'gold',100).valid,true,'The faction may reward its governor');
const gap=clone(base);gap.catalog.treasury.cities.home.reward_targets[1].gold_rewards=[];
assert.equal(treasury.rewardPreview(gap,'home',3,'gold',43).valid,false,'Never fabricate a preview when server intervals are absent');
assert.deepEqual(treasury.normalizePolicy(),policy);
assert.deepEqual(treasury.normalizePolicy({enabled:true,target_loyalty:999,gold_budget:1e9,gold_floor:-1,treasure_floor:100,prefer:'treasure',unknown:'discard'}),{enabled:true,target_loyalty:100,gold_budget:1000000,gold_floor:0,treasure_floor:99,prefer:'treasure'});
for(const value of ['01','clerk-1','clerk-000000','<img>','65535','-1'])assert.equal(treasury.ref(value),null);
assert.equal(JSON.stringify(base),original,'Pure helpers must not mutate resources, loyalty or RNG');
const injected=clone(base);injected.catalog.names[2]='<img src=x onerror=bad>';
assert(!treasury.summary(injected,'home').includes('<img'));assert(treasury.summary(injected,'home').includes('&lt;img'));

let view=clone(base),currentDialog,renderCount=0,submitted=[],nextResult=false,busy=false,preview=false;
const elements=new Map(),listeners=new Map(),dialog={open:false,scrollTop:17,querySelector(selector){if(selector==='[data-treasury-dialog]')return currentDialog?.body.includes('data-treasury-dialog')?{}:null;return elements.get(selector)||null;}};
const i18n={locale:'zh-Hant',t:value=>value,apply(){}};
const document={addEventListener:(type,fn)=>listeners.set(type,fn),removeEventListener:(type,fn)=>{if(listeners.get(type)===fn)listeners.delete(type);}};
const ui=treasury.create({document,dialog,i18n,getView:()=>view,cityName:id=>id==='home'?'成都':id,isBusy:()=>busy,isPreview:()=>preview,openDialog(title,body,actions){
 currentDialog={title,body,actions};dialog.open=true;elements.clear();
 for(const[,id,attrs]of (body+actions).matchAll(/<(?:button|input|select|p)[^>]*?id="([^"]+)"([^>]*)>/g))elements.set('#'+id,{disabled:attrs.includes('disabled'),checked:attrs.includes('checked'),value:attrs.match(/value="([^"]*)"/)?.[1]||'',min:attrs.match(/min="([^"]*)"/)?.[1],max:attrs.match(/max="([^"]*)"/)?.[1],dataset:{},textContent:''});
 for(const[,id,options]of body.matchAll(/<select[^>]*id="([^"]+)"[^>]*>(.*?)<\/select>/gs)){
  const choices=[...options.matchAll(/<option value="([^"]*)"([^>]*)>/g)];elements.get('#'+id).value=(choices.find(row=>row[2].includes('selected'))||choices[0])?.[1]||'';
 }
 return ++renderCount;
},async command(kind,payload){submitted.push({kind,payload:clone(payload)});return typeof nextResult==='function'?nextResult(kind,payload):nextResult;}});
const el=id=>elements.get('#'+id),input=(id,value)=>{el(id).value=String(value);el(id).oninput();},select=(id,value)=>{el(id).value=String(value);el(id).onchange();};
const reset=()=>{view=clone(base);i18n.locale='zh-Hant';busy=preview=false;nextResult=false;submitted=[];assert(ui.open('home'));};

(async()=>{
 assert(ui.open('home'));assert.equal(currentDialog.title,'寶物與賞賜 · 成都');assert.equal(el('treasury-actor').value,'1');assert.equal(el('treasury-reward-officer').value,'3');
 assert(currentDialog.body.includes('兵300 · 武55 · 知85 · 德80 · 忠40 · 體70'));
 const rewardOptions=currentDialog.body.match(/<select id="treasury-reward-officer">([\s\S]*?)<\/select>/)[1];assert(!rewardOptions.includes('value="1"'));assert(rewardOptions.includes('value="2"'),'The governor remains an eligible reward target');
 input('treasury-reward-amount',43);assert.equal(el('treasury-reward-preview').dataset.gain,'2');assert.equal(el('treasury-reward-preview').dataset.loyalty,'42');
 select('treasury-reward-kind','treasure');input('treasury-reward-amount',999);assert.equal(el('treasury-reward-amount').value,'1');assert.equal(el('treasury-reward-preview').dataset.gain,'9');
 select('treasury-reward-kind','gold');assert.equal(el('treasury-reward-amount').value,'43','Each reward kind retains its own local amount');
 input('treasury-sell-amount',999);assert.equal(el('treasury-sell-amount').value,'2');assert(el('treasury-sell-preview').textContent.includes('200'));
 input('treasury-policy-target',999);input('treasury-policy-budget',1e9);input('treasury-policy-gold-floor',-1);input('treasury-policy-treasure-floor',100);select('treasury-policy-prefer','treasure');el('treasury-policy-enabled').checked=true;el('treasury-policy-enabled').onchange();
 const before=JSON.stringify(view);i18n.locale='ja';listeners.get('game-language-change')();assert.equal(el('treasury-reward-amount').value,'43');assert.equal(el('treasury-policy-budget').value,'1000000');assert.equal(el('treasury-policy-target').value,'100');assert.equal(el('treasury-policy-treasure-floor').value,'99');assert(el('treasury-policy-enabled').checked);assert(currentDialog.body.includes('原作ROMから復元した計算式ではありません'));assert.equal(dialog.scrollTop,0);
 assert.equal(JSON.stringify(view),before,'Locale and input changes never touch the save or RNG');
 await el('treasury-reward').onclick();assert.deepEqual(submitted.at(-1),{kind:'reward_officer',payload:{city:'home',officer:3,kind:'gold',amount:43}});assert(dialog.open);assert(currentDialog.body.includes('role="alert"'));assert.equal(JSON.stringify(view),before,'Failed command keeps draft and state intact');
 nextResult=(kind,payload)=>{if(kind==='reward_officer'){view.game.cities.home.gold-=payload.amount;view.game.officers[3].loyalty=42;view.game.cities.home.action_used=true;commandBookFixture.consume(view,'reward_officer');Object.assign(view.catalog.treasury.cities.home,{can_search:true,can_sell:true,can_reward:true,reward_targets:[target(2,70),target(3,42)]});}return true;};
 await el('treasury-reward').onclick();assert.equal(view.game.officers[3].loyalty,42);assert(dialog.open);assert(!el('treasury-reward').disabled);assert(!el('treasury-search').disabled);assert.equal(commandBookFixture.api.row(view).remaining,12);commandBookFixture.exhaust(view);ui.refresh();assert(el('treasury-reward').disabled);assert(el('treasury-search').disabled);assert(currentDialog.body.includes('role="status"'));assert.equal(el('treasury-policy-budget').value,'1000000','A manual operation must not discard an unsaved policy draft');
 select('treasury-governor','clerk-000001');await el('treasury-set-governor').onclick();assert.deepEqual(submitted.at(-1),{kind:'set_governor',payload:{city:'home',officer:'clerk-000001'}});
 select('treasury-governor','');await el('treasury-set-governor').onclick();assert.deepEqual(submitted.at(-1),{kind:'set_governor',payload:{city:'home',officer:null}});
 await el('treasury-save-policy').onclick();assert.equal(submitted.at(-1).kind,'set_treasury_policy');assert.equal(submitted.at(-1).payload.faction,'shu');assert.deepEqual(submitted.at(-1).payload.policy,{enabled:true,target_loyalty:100,gold_budget:1000000,gold_floor:0,treasure_floor:99,prefer:'treasure'});

 reset();view.game.cities.home.gold=19;ui.refresh();assert(el('treasury-search').disabled);await el('treasury-search').onclick();assert.equal(submitted.length,0,'Even an invoked disabled search cannot spend missing funds');
 reset();view.game.extension.treasury.cities.home.treasure=99;ui.refresh();assert(el('treasury-search').disabled);await el('treasury-search').onclick();assert.equal(submitted.length,0);
 reset();view.game.cities.home.gold=20;view.catalog.treasury.cities.home.reward_targets[1].gold_max=20;input('treasury-reward-amount',999);assert.equal(el('treasury-reward-amount').value,'20');await el('treasury-reward').onclick();assert.equal(submitted.at(-1).payload.amount,20);
 reset();view.game.extension.treasury.cities.home.treasure=0;view.catalog.treasury.cities.home.sell_max=0;ui.refresh();assert.equal(el('treasury-sell-amount').value,'0');assert(el('treasury-sell').disabled);assert(el('treasury-sell-max').disabled);
 reset();select('treasury-actor','clerk-000001');nextResult=true;await el('treasury-search').onclick();assert.deepEqual(submitted.at(-1),{kind:'search_treasure',payload:{city:'home',actor:'clerk-000001'}});
 reset();input('treasury-sell-amount',999);nextResult=true;await el('treasury-sell').onclick();assert.deepEqual(submitted.at(-1),{kind:'sell_treasure',payload:{city:'home',actor:1,amount:2}});
 for(const flag of ['busy','preview','phase','owner']){
  reset();if(flag==='busy')busy=true;if(flag==='preview')preview=true;if(flag==='phase')view.game.phase='ai';if(flag==='owner')view.game.cities.home.owner='wei';
  await el('treasury-reward').onclick();await el('treasury-search').onclick();await el('treasury-save-policy').onclick();assert.equal(submitted.length,0,flag+' blocks all writes');assert.equal(ui.open('home'),false);
 }
 reset();const unchanged=JSON.stringify(view);let resolve;nextResult=()=>new Promise(done=>{resolve=done;});
 const waiting=el('treasury-reward').onclick();await el('treasury-reward').onclick();assert.equal(submitted.length,1,'A pending request cannot submit twice');dialog.open=false;const calls=renderCount;resolve(true);await waiting;assert.equal(renderCount,calls,'Completion never reopens a closed panel');assert.equal(JSON.stringify(view),unchanged);
 reset();nextResult=()=>new Promise(done=>{resolve=done;});const replaced=el('treasury-search').onclick();currentDialog={body:'<div>another modal</div>'};const otherCount=renderCount;resolve(true);await replaced;assert.equal(renderCount,otherCount,'Completion never replaces another dialog');
 reset();nextResult=()=>new Promise(done=>{resolve=done;});const stale=el('treasury-search').onclick();view.game.seed=2027;const staleCount=renderCount;resolve(true);await stale;assert.equal(renderCount,staleCount,'A different campaign cannot inherit an earlier operation panel');
 reset();view.catalog.names[2]='<img src=x onerror=bad>';ui.refresh();assert(!currentDialog.body.includes('<img'));assert(currentDialog.body.includes('&lt;img'));
 dialog.open=false;const closed=renderCount;i18n.locale='ja';listeners.get('game-language-change')();assert.equal(renderCount,closed);ui.dispose();assert(!listeners.has('game-language-change'));assert.equal(ui.open('home'),false);
 console.log('treasury UI: pure bilingual inventory, server-derived reward intervals, contextual rulers/governors, actor/target sorting, numeric caps, policy drafts, canonical payloads, resource/phase guards, escaped labels and async dialog ownership passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
