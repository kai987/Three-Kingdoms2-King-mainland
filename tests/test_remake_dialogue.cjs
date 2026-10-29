/* Dialogue projects committed facts without commands, log parsing or RNG. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const dialogue=require('../game/dialogue.js'),events=require('../game/events.js');
const clone=value=>JSON.parse(JSON.stringify(value));
function freeze(value){if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
const i18n={locale:'zh-Hant',t:(value,language)=>language==='ja'?({'劉備':'劉備','關羽':'関羽','曹操':'曹操','成都':'成都'}[value]||value):value};
const base={revision:1,catalog:{scenario_id:'test',title:'測試',names:{0:'劉備',1:'關羽',2:'曹操'},library:[{id:0,person_id:'liu-bei',name:'劉備'},{id:1,person_id:'guan-yu',name:'關羽'},{id:2,person_id:'cao-cao',name:'曹操'}],factions:[{id:'shu',name:'劉備勢力',city:'home'}],cities:[{id:'home',name:'成都',position:[120,300]},{id:'enemy',name:'長安',position:[600,300]}],tactics:[{name:'火計'}],world:{width:1352,height:1024,background:'/assets/map-navigation.png'}},game:{seed:1,player:'shu',year:190,month:1,day:1,turn:1,officers:{0:{person_id:'liu-bei',troops:500,loyalty:100},1:{person_id:'guan-yu',troops:300,loyalty:80},2:{person_id:'cao-cao',troops:200,loyalty:100}},cities:{home:{reserves:100},enemy:{reserves:0}},extension:{leaders:{shu:0},civil_staff:{people:{}},travel:{marches:[]},events:{next_id:1,items:[]}}}};
const row=(kind,id=1,extra={})=>({id,kind,year:190,month:1,day:1,turn:1,person_ids:['guan-yu','cao-cao'],city_ids:['home'],factions:['shu'],audience:'player',details:{actor:'liu-bei',target:'guan-yu',governor:'guan-yu',staff_id:'clerk-000001',name:'王安',portrait:'clerk-1',success:false,tactic:0},...extra});
const payload={actor:1,target:2,officer:1,officers:[1],city:'home',source:'home',move:'guard',action:'treat',allocations:[{officer:1,troops:400}]};
const after=clone(base);after.revision=2;after.game.officers[1].troops=400;after.game.cities.home.reserves=200;after.game.extension.events={next_id:2,items:[row('tactic')]};
freeze(base);freeze(after);freeze(payload);
const bytes=JSON.stringify([base,after,payload]),random=Math.random;
Math.random=()=>{throw Error('Dialogue must never draw randomness');};
try{
 assert.deepEqual([...dialogue.EVENT_KINDS].sort(),Object.keys(events.KINDS).sort(),'Every registered event needs its own bilingual exchange');
 const bridge=fs.readFileSync(path.join(__dirname,'../source/remake/browser_runtime.py'),'utf8');
 const commands=[...bridge.match(/COMMANDS = frozenset\(\(([\s\S]*?)\)\)/)[1].matchAll(/'([a-z_]+)'/g)].map(match=>match[1]);
 assert.deepEqual(Object.keys(dialogue.COMMANDS).sort(),commands.sort(),'Every transport command is explicitly classified');
 for(const language of ['zh-Hant','ja']){
  for(const kind of dialogue.EVENT_KINDS){
   const event=freeze(row(kind)),before=JSON.stringify(event),lines=dialogue.event(event,base,language,i18n);
   assert(lines.length>=2&&lines.length<=3,kind);
   for(const line of lines){assert.equal(typeof line.name,'string');assert(line.name.length);assert.equal(typeof line.text,'string');assert(line.text.length);assert(!line.text.includes('undefined'),kind);}
   if(language==='ja')assert(lines.some(line=>/[ぁ-ゖァ-ヶ]/u.test(line.text)),kind+' requires Japanese prose');
   assert.equal(JSON.stringify(event),before);
   assert.deepEqual(dialogue.event(event,base,language,i18n),lines,'Projection is repeatable');
   const html=dialogue.html(lines,{language,portraits:null});assert(html.includes('data-dialogue-exchange'));assert(!html.includes('undefined'));
  }
  for(const [kind,mode]of Object.entries(dialogue.COMMANDS)){
   const lines=dialogue.command(kind,payload,base,after,{language,i18n});
   assert.equal(lines.length,mode==='inline'?2:0,kind);
   if(mode==='inline')assert(lines.every(line=>line.name&&line.text&&!line.text.includes('undefined')),kind);
   const failed=dialogue.command(kind,payload,base,base,{language,i18n,error:'資源不足 <script>bad</script>'});
   assert.equal(failed.length,2,kind+' errors have an ephemeral exchange');assert(failed[1].text.includes('資源不足'));
   const html=dialogue.html(failed,{language,portraits:null});assert(html.includes('&lt;script&gt;bad&lt;/script&gt;'));assert(!html.includes('<script>'));
  }
 }
 assert.equal(JSON.stringify([base,after,payload]),bytes,'All projections preserve state, receipt and request bytes');
 assert.deepEqual(dialogue.event(row('unrecognized'),base),[]);assert.deepEqual(dialogue.command('unrecognized',{},base,after),[]);
 const joined=dialogue.event(row('recruit_success'),base,'ja',i18n);assert.equal(joined[0].personId,'liu-bei');assert.equal(joined[1].personId,'guan-yu');assert.equal(joined[1].name,'関羽');
 const opening=dialogue.event(row('campaign_start',1,{person_ids:[]}),base);assert.equal(opening[1].personId,'liu-bei','Missing opening participant falls back to actual ruler');
 const coup=dialogue.event(row('faction_coup',1,{person_ids:['liu-bei','guan-yu','cao-cao']}),base);assert.equal(coup[1].personId,'cao-cao','Coup dialogue belongs to successor, never the victims');
 const owned=row('equipment_acquired',1,{person_ids:['liu-bei','guan-yu'],details:{actor:'liu-bei',target:'guan-yu',from_person:'guan-yu',method:'owned'}});
 const loot=row('equipment_acquired',1,{person_ids:['guan-yu','cao-cao'],details:{actor:'guan-yu',target:'guan-yu',from_person:'cao-cao',method:'duel'}});
 for(const language of ['zh-Hant','ja']){
  assert.equal(dialogue.event(freeze(owned),base,language,i18n)[0].personId,'guan-yu','Owned equipment speaks through wearer, not governor who executed command');
  assert.equal(dialogue.event(freeze(loot),base,language,i18n)[0].personId,'guan-yu','Duel loot speaks through its actual recipient');
  const plan=freeze(row('ai_campaign',1,{person_ids:[],city_ids:['enemy'],details:{target:'enemy',sources:['home'],arrival_turn:8,coordinated:true}}));
  const lines=dialogue.event(plan,base,language,i18n),text=lines.map(line=>line.text).join(' ');
  assert(text.includes(language==='ja'?'進軍計画':'進軍計畫'));assert(text.includes(language==='ja'?'全隊の出発を意味しません':'不代表各隊均已出發'));
  const labels={...i18n,locale:language},describer=events.create({i18n:labels});describer.observe(base,{baseline:true});
  const description=describer.description(plan);assert(description.includes(language==='ja'?'未出発':'尚未出發'));assert(!description.includes(language==='ja'?'進軍しています':'朝長安推進'));describer.dispose();
 }
 const expired=dialogue.event(row('staff_candidate',1,{person_ids:[]}),base);assert.equal(expired[0].name,'王安');assert.equal(expired[0].personId,'clerk-000001');
 let civilRequest=null;dialogue.html(expired,{portraits:{civilHtml:(key,name)=>{civilRequest=[key,name];return '<span>civil</span>';},html(){throw Error('Expired candidate must use its saved shared portrait');}}});assert.deepEqual(civilRequest,['clerk-1','王安']);
 const refusal=clone(after);refusal.presentation={revision:2,scenes:[{kind:'duel_start',actor:1,target:2,success:false}]};
 for(const language of ['zh-Hant','ja']){
  const text=dialogue.command('duel_start',payload,base,freeze(refusal),{language,i18n})[1].text;assert(text.includes(language==='ja'?'付き合う':'不與'));
 }
 const duelView=clone(base);duelView.game.battle={extended:{duel:{actor:1,target:2}}};
 const guarded=dialogue.command('duel_action',{move:'guard'},freeze(duelView),after);assert.equal(guarded[0].personId,'guan-yu');assert(guarded[0].text.includes('守住'));
 const unknown=clone(base);unknown.catalog.names={};unknown.catalog.library=[];unknown.game.officers={};
 assert(dialogue.event(row('recruit_success'),freeze(unknown)).every(line=>!line.personId),'Missing identities use neutral role labels');
 const hostile=clone(base);hostile.catalog.library[1].name='<img src=x onerror=bad>';hostile.catalog.names[1]='<img src=x onerror=bad>';
 const escaped=dialogue.html(dialogue.event(row('recruit_success'),freeze(hostile)),{portraits:null});assert(escaped.includes('&lt;img'));assert(!escaped.includes('<img'));
 const relationView=clone(base);relationView.catalog.officer_relations={officers:{1:{floor:98,reason:{zh:'結義與長期信任',ja:'義兄弟と長年の信頼'},blocked:false,sources:['https://example.org/history']}}};
 const relationBytes=JSON.stringify(relationView);freeze(relationView);
 assert(dialogue.relation(relationView,1).includes('任用忠誠基準98'));assert(dialogue.relation(relationView,1).includes('目前忠誠80'));assert(dialogue.relation(relationView,1).includes('不會改寫'));
 assert(dialogue.relation(relationView,1,'ja').includes('現在値は基準を下回ります'));assert.equal(JSON.stringify(relationView),relationBytes);
 const blocked=clone(relationView);blocked.catalog.officer_relations.officers[1].blocked=true;assert(dialogue.relation(freeze(blocked),1).includes('例外關係'));assert(!dialogue.relation(blocked,1).includes('基準98'));
 for(const language of ['zh-Hant','ja'])for(const kind of ['recruit_officer','persuade_officer']){const guidance=dialogue.guidance(kind,payload,base,language,i18n);assert.equal(guidance.length,2);assert.equal(guidance[0].personId,'guan-yu');assert.equal(guidance[1].personId,'guan-yu');}
}finally{Math.random=random;}

// Hazards can lose cargo only, and a rendezvous delivers directly to an army.
for(const language of ['zh-Hant','ja']){
 for(const kind of ['march_weather','transport_weather']){
  const lines=dialogue.event(row(kind,3,{details:{lost:0}}),base,language,i18n);
  assert(!/已有損失|已有兵員損失|兵員已有損失|兵に損失が出ました|人員に損失が出ました/.test(lines.map(x=>x.text).join('')));
 }
 const arrival=dialogue.event(row('transport_arrived',4),base,language,i18n).map(x=>x.text).join('');
 assert(!/入庫|倉庫に収め/.test(arrival),'Transport dialogue also covers direct army delivery');
}

class Target{constructor(){this.listeners=new Map();}addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,[]);this.listeners.get(name).push(fn);}removeEventListener(){}emit(name){for(const fn of this.listeners.get(name)||[])fn();}}
class Modal extends Target{constructor(){super();this.open=false;this.buttons=new Map();}set innerHTML(text){this.text=text;this.buttons.set('[data-event-next]',{focus(){}});this.buttons.set('[data-event-skip]',{focus(){}});}get innerHTML(){return this.text;}querySelector(selector){return this.buttons.get(selector);}showModal(){this.open=true;}close(){this.open=false;this.emit('close');}}
const modal=new Modal(),parent=new Target(),doc=new Target(),tasks=[];parent.open=false;doc.querySelector=()=>null;
let current=clone(base),busy=false;const controller=events.create({document:doc,modal,parentDialog:parent,dialogue,i18n,portraits:{entry:()=>null},getView:()=>current,isBusy:()=>busy,schedule:fn=>tasks.push(fn)});
const drain=()=>{let count=0;while(tasks.length){assert(count++<30);tasks.shift()();}};
controller.observe(current,{baseline:true});drain();
current=clone(base);current.game.extension.events={next_id:2,items:[row('recruit_success',1,{details:{actor:'liu-bei'}})]};
busy=true;controller.observe(current);drain();assert(!modal.open);busy=false;parent.open=true;controller.pump();drain();assert(!modal.open);parent.open=false;parent.emit('close');drain();assert(modal.open);
assert(modal.innerHTML.indexOf('data-dialogue-exchange')<modal.innerHTML.indexOf('event-facts'),'Speaker exchange precedes unchanged receipt');
const queueBefore=JSON.stringify(controller.snapshot()),saved=JSON.stringify(current);i18n.locale='ja';doc.emit('game-language-change');assert(modal.innerHTML.includes('お招き'));assert.equal(JSON.stringify(controller.snapshot()),queueBefore);assert.equal(JSON.stringify(current),saved);
modal.querySelector('[data-event-next]').onclick();controller.observe(current);drain();assert(!modal.open,'Acknowledged exchanges do not repeat');
current=clone(current);current.game.extension.events.items.push(row('tactic',2,{details:{tactic:0,success:false}}));current.game.extension.events.next_id=3;controller.observe(current);drain();assert(!modal.open,'Repeated battlefield tactics use inline dialogue, no interruption');
assert(controller.history());drain();assert(modal.open,'Tactical event remains available in history');controller.clear();controller.dispose();

// Verify the central command path forwards one real result or the original error.
(async()=>{
 const app=fs.readFileSync(path.join(__dirname,'../game/app.js'),'utf8'),body=app.slice(app.indexOf('async function command('),app.indexOf('\nfunction openDialog('));
 let clears=0;const notices=[],calls=[],ctx={busy:false,view:clone(base),audioOutcome:null,localAutosave:null,GameDialogue:dialogue,confirmOrderCommand:async()=>true,gameEvents:{observe(){}},notice:(...args)=>notices.push(args),setBusy(v){ctx.busy=v;},render(){},setTimeout:fn=>{fn();return 1},gameAudio:{play(){}},request:async()=>clone(after),clearDialogueFeedback(){clears++;},showDialogueFeedback:(...args)=>calls.push(args)};
 vm.createContext(ctx);vm.runInContext(body,ctx);assert(await ctx.command('recruit',{city:'home'}));assert.equal(calls.length,1);assert.equal(calls[0][0],'recruit');assert.equal(calls[0][2].revision,1);assert.equal(calls[0][3].revision,2);
 const meaningful=calls[0],meaningfulClears=clears;
 for(const kind of ['allocation_close','ai','arrivals']){assert(await ctx.command(kind));assert.equal(clears,meaningfulClears,'Internal '+kind+' must not clear last meaningful feedback');assert.equal(calls.length,1,'Internal '+kind+' must not replace feedback with empty dialogue');assert.equal(calls[0],meaningful);}
 ctx.request=async()=>{throw Error('internal closure refusal');};assert.equal(await ctx.command('allocation_close'),false);assert.equal(clears,meaningfulClears);assert.equal(calls.length,1);assert(notices.some(([message])=>message==='internal closure refusal'),'Silent command failure retains its exact notice');
 ctx.request=async()=>{throw Error('exact refusal text');};assert.equal(await ctx.command('attack',{actor:1,target:2}),false);assert.equal(calls.at(-1)[4],'exact refusal text');assert.equal(ctx.view.revision,2);
 assert.equal(clears,meaningfulClears+1,'Next meaningful command clears old feedback');
 assert(app.includes("$('#journal')?.prepend(panel)"),'Compact feedback occupies existing bounded report area');assert(!app.includes("$('#notice')?.after(panel)"));
 assert(app.includes('refreshPersonnelDialogue();GameI18n.apply()'));assert(app.includes('data-officer-relation='));
 console.log('dialogue: all 56 events, 44 commands, bilingual speakers, refusal receipts, portrait fallbacks, save/RNG immutability, modal queue/locale and central feedback passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
