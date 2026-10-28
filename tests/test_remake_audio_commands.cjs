/* Semantic feedback follows the actual command result, not a generic button click. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const text=fs.readFileSync(require.resolve('../game/app.js'),'utf8');
const body=text.slice(text.indexOf('async function command('),text.indexOf('\nfunction openDialog('));
const effects=JSON.parse(fs.readFileSync(require.resolve('../game/assets/audio/effects.json'),'utf8'));
async function check(kind,payload,previous,next,expected,{result=null,error=false}={}){
 const heard=[],context={busy:false,view:{revision:1,game:previous},audioOutcome:null,localAutosave:null,confirmOrderCommand:async()=>true,
  gameAudio:{play:id=>heard.push(id)},setBusy:value=>{context.busy=value;},
  notice:(_message,bad)=>{if(bad)context.gameAudio.play('error');},
  request:async()=>{if(error)throw Error('Rejected');return{revision:2,game:next};},
  render:()=>{if(result){context.audioOutcome='result:new';context.gameAudio.play(result);}},setTimeout:fn=>fn()};
 vm.createContext(context);vm.runInContext(body,context);
 assert.equal(await context.command(kind,payload),!error);
 assert.deepEqual(heard,[expected],kind+' must produce exactly one result cue');
 assert.equal(context.busy,false);
}
(async()=>{
 const before={turn:1,battle:{log:['older event']}},after={turn:1,battle:{log:['older event','effect applied','counterattack'],extended:{duel:null}}};
 for(let tactic=0;tactic<16;tactic++)await check('tactic',{tactic},before,after,'tactic_'+effects.tactic_index_sequence_ids[tactic].toString(16));
 await check('tactic',{tactic:3},before,{...after,battle:{...after.battle,log:['older event','施放計略，未能奏效。','对手反击。']}},'error');
 const fullLog=Array.from({length:80},(_,i)=>'older event '+i),failure='施放計略，未能奏效。';
 await check('tactic',{tactic:3},{turn:1,battle:{log:fullLog}},{turn:1,battle:{log:[...fullLog.slice(2),failure,'对手反击。']}},'error');
 const staleFailure=[...fullLog.slice(0,78),failure,'previous counterattack'];
 await check('tactic',{tactic:3},{turn:1,battle:{log:staleFailure}},{turn:1,battle:{log:[...staleFailure.slice(2),'effect applied','counterattack']}},'tactic_8d');
 const repeated=Array.from({length:80},(_,i)=>i%2?'counterattack':failure);
 await check('tactic',{tactic:3},{turn:1,battle:{log:repeated}},{turn:1,battle:{log:[...repeated]}},'error');
 await check('duel_start',{},before,{...after,battle:{...after.battle,extended:{duel:{round:1}}}},'duel_start');
 await check('duel_start',{},before,after,'duel_refused');
 for(const move of ['strike','guard','feint','withdraw'])await check('duel_action',{move},before,after,'duel_'+move);
 await check('attack',{},before,after,'attack');
 await check('attack',{},before,after,'victory',{result:'victory'});
 await check('retreat',{},before,after,'defeat',{result:'defeat'});
 await check('end_turn',{},before,{turn:1,phase:'ai'},'confirm');
 await check('ai',{},before,{turn:2,phase:'city'},'turn');
 await check('allocate',{},before,after,'confirm');
 await check('depart',{},before,after,'march');
 await check('attack',{},before,after,'error',{error:true});
 console.log('command audio: 16 original tactic families, duel acceptance/moves, result priority, one turn cue and rejected-command feedback passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
