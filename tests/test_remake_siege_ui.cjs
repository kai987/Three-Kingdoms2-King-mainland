'use strict';
const assert=require('node:assert/strict'),api=require('../game/siege-ui.js');
const clone=value=>JSON.parse(JSON.stringify(value));
const value={catalog:{scenario_id:'controlled'},game:{seed:2026,player:'wei',phase:'battle',battle:{id:'test',attacker:'wei',defender:'wu',attackers:[{id:1,troops:999}],defenders:[{id:2,troops:300}],log:[],extended:{support:{1:{health:80},2:{health:75}},siege:{schema:'tk2-siege-v1',actor:1,target:2,fort:2,stage:'formation',round:1,formations:{attackers:null,defenders:3},orders:{attackers:{infantry:'advance',archer:'advance',cavalry:'advance',general:'advance'},defenders:{infantry:'advance',archer:'advance',cavalry:'advance',general:'wait'}},units:[{side:'attackers',kind:'general',health:80},{side:'defenders',kind:'general',health:75}]}}}}};
let view=clone(value),locale='zh-Hant',busy=false,refresh=0;const sent=[];
const ui=api.create({i18n:{get locale(){return locale;},t:t=>t},getView:()=>view,isBusy:()=>busy,name:id=>id===1?'<甲>':'乙',portrait:()=>'',refresh:()=>refresh++,command:async(kind,payload)=>{
 sent.push({kind,payload});const row=view.game.battle.extended.siege;
 if(kind==='siege_form'){row.formations.attackers=payload.formation;row.stage='orders';}
 if(kind==='siege_orders'){row.orders.attackers={...payload.orders};row.stage='combat';}
 if(kind==='siege_step'){row.round++;row.stage='orders';}
 if(kind==='siege_withdraw')delete view.game.battle.extended.siege;
 return true;
}});
function controls(){const html=ui.controls(),nodes=new Map();
 for(const match of html.matchAll(/id="(siege-[a-z-]+)"/g))nodes.set('#'+match[1],{});
 const formations=[0,1,2,3].map(formation=>({dataset:{siegeFormation:String(formation)}}));
 const orders=api.KINDS.map(kind=>({dataset:{siegeOrder:kind},value:ui.state().orders[kind]}));
 const host={querySelector:selector=>nodes.get(selector)||null,querySelectorAll:selector=>selector==='[data-siege-formation]'?formations:orders};ui.bind(host);return{html,nodes,formations,orders};
}
(async()=>{
 const original=JSON.stringify(view),form=controls();assert.equal(form.formations.length,4);assert(form.html.includes('長蛇'));assert(form.html.includes('魚鱗'));assert(!form.html.includes('data-siege-order'));
 form.formations[3].onclick();assert.equal(ui.state().formation,3);assert.equal(JSON.stringify(view),original,'Preview cannot write state, books or RNG');assert.equal(sent.length,0);assert(refresh>0);
 const event={key:'ArrowRight',target:{closest:()=>null},preventDefault(){this.defaultPrevented=true;}};ui.keyboard(event);assert(event.defaultPrevented);assert.equal(ui.state().formation,0);
 busy=true;event.defaultPrevented=false;ui.keyboard(event);assert.equal(ui.state().formation,0);busy=false;
 const buttonEvent={key:'Enter',target:{closest:selector=>selector==='button,a,summary,[role="button"]'?{}:null},preventDefault(){throw Error('Native unrelated button activation was stolen');}};assert.equal(ui.keyboard(buttonEvent),false);
 await form.nodes.get('#siege-form').onclick();assert.deepEqual(sent.at(-1),{kind:'siege_form',payload:{battle_id:'test',formation:0}});
 const commands=controls();assert.deepEqual(api.ORDERS,['advance','retreat','wait','surround']);assert.equal(commands.orders.length,4);
 commands.orders[3].value='wait';const before=JSON.stringify(view);commands.orders[3].onchange();assert.equal(JSON.stringify(view),before);
 await commands.nodes.get('#siege-step').onclick();assert.deepEqual(sent.slice(-2).map(r=>r.kind),['siege_orders','siege_step']);assert.equal(sent.at(-2).payload.orders.general,'wait');assert.equal(view.game.battle.extended.siege.round,2);
 view.game.battle.extended.siege.stage='combat';const paused=controls();paused.orders[0].value='retreat';paused.orders[0].onchange();await paused.nodes.get('#siege-step').onclick();assert.equal(sent.at(-2).kind,'siege_orders');assert.equal(sent.at(-2).payload.orders.infantry,'retreat','Paused combat must send edited orders before moving');
 view.game.battle.extended.siege.orders.attackers.infantry='wait';ui.reset();assert.equal(ui.state().orders.infantry,'wait','A load reset rebuilds drafts from the restored game even when battle identity is unchanged');
 locale='ja';assert(ui.controls().includes('城内戦'));assert(ui.controls().includes('包囲'));assert(ui.armies().includes('&lt;甲&gt;'));
 view.game.player='wu';view.game.battle.extended.siege.stage='formation';assert(!ui.controls().includes('data-siege-formation='));assert(ui.controls().includes('固定防衛配置'));
 view.game.player='wei';const leave=controls();await leave.nodes.get('#siege-withdraw').onclick();await Promise.resolve();assert.equal(sent.at(-1).kind,'siege_withdraw');assert.equal(api.current(view),null);ui.stop();assert.equal(ui.state().automatic,false);
 console.log('siege UI: four native formations, fixed fortified layout, group drafts, keyboard/native-control guards, exact commands, bilingual text, escaped names and no speculative state/RNG writes passed');
})().catch(error=>{ui.stop();console.error(error);process.exitCode=1;});
