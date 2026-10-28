'use strict';
const api=require('../../game/command-books.js');
const paid=['recruit','recruit_officer','persuade_officer','staff_recruit','hire_staff','depart','transfer','dispatch_transport','search_treasure','reward_officer','sell_treasure','develop_town','treat_officer','study_officer','trade_grain','buy_equipment','improve_prevention','equip_owned','allocate','resupply_march','transport_treasure'];
const free=['set_domestic','set_logistics','set_governor','set_treasury_policy','set_facility_policy','reject_staff','choose_successor'];
function attach(view,total=13){
 view.game.turn??=1;view.catalog??={};
 const owners=new Set([view.game.player,...Object.values(view.game.cities||{}).map(city=>city.owner)].filter(owner=>owner&&owner!=='neutral'));
 view.catalog.command_books={schema:api.SCHEMA,turn:view.game.turn,maximum:13,refresh_days:10,costs:Object.fromEntries([...paid.map(key=>[key,1]),...free.map(key=>[key,0])]),factions:Object.fromEntries([...owners].map(owner=>[owner,{city_count:Object.values(view.game.cities||{}).filter(city=>city.owner===owner).length,total,used:0,remaining:total}]))};
 return view;
}
function consume(view,kind){const row=api.row(view),amount=api.cost(view,kind);if(!row||amount===null||row.remaining<amount)throw Error('Invalid fixture command');row.used+=amount;row.remaining-=amount;}
function exhaust(view){const row=api.row(view);row.used=row.total;row.remaining=0;}
module.exports={api,attach,consume,exhaust};
