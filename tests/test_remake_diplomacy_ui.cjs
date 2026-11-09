'use strict';
const assert=require('node:assert/strict');
const diplomacy=require('../game/diplomacy.js');
const orders=require('../game/order-confirm.js');

async function test(){
 const view={game:{player:'shu',phase:'city',seed:2026,cities:{chengdu:{}}},catalog:{
  scenario_id:'test',factions:[{id:'wu',name:'孫權'}],diplomacy:{
   max_turns:72,can_command:true,
   cities:[{id:'chengdu',envoys:[{id:1,name:'諸葛亮',intellect:100,virtue:97}],limits:{gold:80,grain:200,treasure:3}}],
   targets:[{id:'wu',stage:'friendly',alliance:{historical:false,turns:8},
    actions:{goodwill:true,alliance:true,return_captives:true,request_attack:true,surrender:true},
    attack_cities:['xiangyang'],captives:[{id:'clerk-000001',name:'丁卓'}]}]
  }
 }};
 const target=view.catalog.diplomacy.targets[0];
 const i18n={locale:'zh-Hant',t:value=>value,apply(){}};
 let current,submissions=[],canSpend=true,release;
 const nodes=new Map(),listeners=new Map(),relations={open:false};
 const document={addEventListener:(event,callback)=>listeners.set(event,callback),
  removeEventListener:event=>listeners.delete(event)};
 const dialog={open:false,scrollTop:0,querySelector(selector){
  if(selector==='[data-diplomacy-dialog]')return current&&this.open?{}:null;
  if(selector==='[data-diplomacy-relations]')return relations;
  return nodes.get(selector.slice(1));
 }};
 const ui=diplomacy.create({document,dialog,i18n,getView:()=>view,
  cityName:id=>({chengdu:'成都',xiangyang:'襄陽'}[id]),
  commandBooks:{can:()=>canSpend,html:()=>'<p>books</p>'},
  openDialog(title,body,actions){
   current={title,body,actions};dialog.open=true;nodes.clear();
   for(const match of (body+actions).matchAll(/id="([^"]+)"([^>]*)>/g)){
    nodes.set(match[1],{disabled:/\bdisabled\b/.test(match[2]),value:'',focus(){}});
   }
  },
  command(kind,payload){submissions.push({kind,payload});return new Promise(resolve=>{release=resolve;});}
 });
 const element=id=>nodes.get('diplomacy-'+id);
 const select=(key,value)=>{const node=element(key);node.value=value;node.onchange();};
 const input=(key,value)=>{const node=element(key);node.value=value;node.oninput();return node;};
 const command=async expected=>{
  const request=element('submit').onclick();
  assert.deepEqual(submissions.at(-1),{kind:'diplomacy',payload:{city:'chengdu',envoy:1,target:'wu',...expected}});
  assert.equal(await element('submit').onclick(),false,'Only one submission while awaiting the engine');
  release(true);
  assert.equal(await request,true);
 };
 assert(ui.canOpen());assert(ui.open());
 assert.match(current.body,/親善/);assert.match(current.body,/友好/);assert.match(current.body,/剩餘 8 旬/);
 assert.match(current.body,/諸葛亮 · 知 100 · 德 97/);assert.match(current.body,/交涉勢力/);
 select('resource','treasure');assert.equal(input('amount','999').value,'3');
 await command({action:'goodwill',resource:'treasure',amount:3});
 assert.match(current.body,/外交指令已執行/);

 select('action','alliance');assert.equal(input('duration','200').value,'72');
 await command({action:'alliance',duration:72});
 select('action','return_captives');assert.match(current.body,/丁卓/);
 await command({action:'return_captives',prisoner:'clerk-000001'});
 select('action','request_attack');assert.match(current.body,/襄陽/);
 await command({action:'request_attack',attack_city:'xiangyang'});
 select('action','surrender');await command({action:'surrender'});
 target.actions.surrender=false;
 const submitted=submissions.length;
 assert.equal(await element('submit').onclick(),false,'Recheck target eligibility before writing');
 canSpend=false;target.actions.surrender=true;
 assert.equal(await element('submit').onclick(),false,'Command books remain authoritative');
 assert.equal(submissions.length,submitted);

 i18n.locale='ja';relations.open=true;listeners.get('game-language-change')();
 assert.match(current.body,/残り 8 旬/);assert.match(current.body,/交渉相手/);
 assert.match(current.actions,/降伏勧告/);assert.equal(relations.open,true);
 assert.match(orders.quote(view,'diplomacy',{city:'chengdu',action:'surrender'},{
  books:{cost:()=>1},locale:'ja',cityName:()=> '成都'
 }).message,/命令書1枚.*降伏勧告/);
 view.game.player='observer';
 assert(!ui.canOpen());assert(!ui.open());assert.equal(await element('submit').onclick(),false);
 ui.dispose();assert.equal(listeners.size,0);
 console.log('diplomacy UI: bilingual stage and alliance, all five canonical payloads, live eligibility and command-book guards passed');
}
test().catch(error=>{console.error(error);process.exitCode=1;});
