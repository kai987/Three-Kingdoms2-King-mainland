'use strict';
const assert=require('node:assert/strict'),{execFileSync}=require('node:child_process'),path=require('node:path');
const supply=require('../game/march-supply.js');
const cases=[];
for(const troops of [0,1,300,999,9990,98901])for(const officers of [1,10,99])for(const days of [1,10,12,33,400])for(const reserves of [0,50,100000])cases.push([troops,officers,days,reserves]);
const actual=cases.map(row=>supply.requiredGrain(...row));
const expected=JSON.parse(execFileSync('python3',['-B','-c','import json,sys;from remake.march_supply import required_grain;print(json.dumps([required_grain(*x) for x in json.load(sys.stdin)]))'],{cwd:path.join(__dirname,'../source'),input:JSON.stringify(cases),encoding:'utf8'}));
assert.deepEqual(actual,expected);
assert.equal(supply.requiredGrain(1000,1,12),14);assert.equal(supply.requiredGrain(1000,1,10),11);
assert.equal(supply.estimate({a:{troops:600},b:{troops:300}},['a','b'],{days:20},200),26);
const quote={days:30,path:['home','empty','depot','front'],routes:[{days:7},{days:13},{days:10}]},
 cities={home:{owner:'wei'},empty:{owner:'neutral'},depot:{owner:'wei'},front:{owner:'wei'}},
 people={a:{troops:900}},snapshot=JSON.stringify({quote,cities,people});
assert.equal(supply.initialDays(quote,cities,'wei'),20,'A neutral city cannot supply the column');
assert.equal(supply.estimate(people,['a'],quote,0,cities,'wei'),20,'Only the first friendly supply interval is loaded');
assert.equal(supply.estimate(people,['a'],quote),30,'A bare duration remains valid for callers without ownership context');
assert.deepEqual(supply.position(quote,0),{city:'home',from:'home',to:'empty',progress_days:0,leg_days:7,arrived:false});
assert.equal(supply.position(quote,7).city,'empty');
assert.deepEqual(supply.position(quote,10),{city:null,from:'empty',to:'depot',progress_days:3,leg_days:13,arrived:false});
assert.equal(supply.position(quote,20).city,'depot');assert.equal(supply.position(quote,30).arrived,true);
assert.equal(supply.position(quote,999).city,'front');
assert.deepEqual(supply.nextStop(quote,10,cities,'wei'),{city:'depot',days:10});
assert.deepEqual(supply.nextStop(quote,20,cities,'wei'),{city:'depot',days:0});
assert.deepEqual(supply.nextStop(quote,21,cities,'wei'),{city:'front',days:9});
assert.equal(JSON.stringify({quote,cities,people}),snapshot,'Budgets and position previews do not mutate authoritative state');
cities.depot.owner='shu';assert.equal(supply.initialDays(quote,cities,'wei'),30,'Actual ownership changes invalidate the resupply stop');
cities.front.owner='shu';assert.equal(supply.initialDays(quote,cities,'wei'),30,'With no friendly stop, prepare the whole journey');
assert.equal(supply.nextStop(quote,10,cities,'wei'),null);
for(const bad of [-1,1.5,NaN,Infinity])assert.throws(()=>supply.requiredGrain(bad,1,10));
assert.throws(()=>supply.requiredGrain(Number.MAX_SAFE_INTEGER,99,1000000));
assert.throws(()=>supply.initialDays({days:10,path:['home','away'],routes:[{days:0.5}]},cities,'wei'));
const itinerary={path:['home','ally','depot-a','empty','depot-b','enemy'],days:13,routes:[3,2,4,1,3].map(days=>({days}))};
const itineraryCities={home:{owner:'wei',grain:1000},ally:{owner:'shu',grain:1000},
 'depot-a':{owner:'wei',grain:2},empty:{owner:'neutral',grain:1000},
 'depot-b':{owner:'wei',grain:5},enemy:{owner:'wu',grain:1000}};
const marching={1:{troops:1025}};
const provisions=supply.estimate(marching,[1],itinerary,0,itineraryCities,'wei');
assert.equal(provisions,6);
const loaded=provisions+4; // The engine treats battle grain as part of the march balance.
const before=JSON.stringify({marching,itinerary,itineraryCities});
const forecast=supply.refillForecast(marching,[1],itinerary,loaded,itineraryCities,'wei');
assert.deepEqual(forecast,[
 {city:'depot-a',next:'depot-b',days:5,stock:2,required:2,shortfall:0,conditional:false},
 {city:'depot-b',next:'enemy',days:3,stock:5,required:3,shortfall:0,conditional:false}
]);
assert.equal(supply.refillForecast(marching,[1],itinerary,provisions,itineraryCities,'wei')[0].required,6);
const lowCities={...itineraryCities,'depot-a':{owner:'wei',grain:1}};
assert.deepEqual(supply.refillForecast(marching,[1],itinerary,loaded,lowCities,'wei'),[
 {...forecast[0],stock:1,shortfall:1},{...forecast[1],conditional:true}
]);
const direct={path:['home','depot-a'],days:3,routes:[{days:3}]};
assert.deepEqual(supply.refillForecast(marching,[1],direct,loaded,itineraryCities,'wei'),[],'Arrival is not a transit refill');
assert.deepEqual(supply.refillForecast(marching,[],itinerary,0,itineraryCities,'wei'),[]);
assert.equal(JSON.stringify({marching,itinerary,itineraryCities}),before,'A forecast leaves game and quote data unchanged');

const observed=JSON.parse(execFileSync('python3',['-B','-c',`
import json, sys
from types import SimpleNamespace as N
from unittest.mock import patch
from remake.march_supply import advance_unit, create

arg = json.load(sys.stdin)
def run(cities, days):
    state = N(turn=1, cities={k:N(**v) for k,v in cities.items()}, officers={1:N(alive=True, faction_id='wei', troops=1025)})
    unit = dict(id=1, owner='wei', officers=[1])
    journey = dict(quote=arg['itinerary'], supply=create(state, [1], arg['itinerary'], initial_grain=arg['loaded']))
    with patch('remake.march_supply.transit_allowed', return_value=True):
        advance_unit(N(_supply_event=lambda *a, **kw: None), state, unit, journey, absolute_tick=days)
    return journey['supply']

print(json.dumps([run(arg['itineraryCities'], arg['itinerary']['days']), run(arg['lowCities'], 6)]))
`],{cwd:path.join(__dirname,'../source'),input:JSON.stringify({itinerary,loaded,itineraryCities,lowCities}),encoding:'utf8'}));
assert.deepEqual(observed[0].refills.map(row=>[row.source,row.grain]),forecast.map(row=>[row.city,row.required]),'Forecast matches actual engine refills');
assert.equal(observed[1].route_days,5,'The first deficient checkpoint stops the column');
assert.equal(observed[1].waiting,true);

const app=require('node:fs').readFileSync(require.resolve('../game/app.js'),'utf8');
const context={view:{game:{officers:marching,cities:lowCities}},GameMarchSupply:supply,GameI18n:{t:name=>name},
 cityName:city=>city,battleText:(tc,ja)=>`${tc} | ${ja}`,escapeHtml:city=>city};
require('node:vm').runInNewContext(app.slice(app.indexOf('function marchRefillForecastHtml('),app.indexOf('function departureBudget(')),context);
const markup=context.marchRefillForecastHtml(itinerary,[1],loaded,'wei');
assert.match(markup,/data-march-refill-stop="depot-a" data-current-grain="1" data-required-grain="2" data-grain-shortfall="1"/);
assert.match(markup,/補給待ち/);
assert.match(markup,/目前缺1糧/);
assert.match(markup,/手前の不足を補えた場合/);
assert.doesNotMatch(markup,/data-march-refill-stop="(?:ally|empty|enemy)"/);
assert.match(context.marchRefillForecastHtml(direct,[1],loaded,'wei'),/途中の補給都市はありません/);
console.log(`march supply: ${cases.length} real Python/JS budgets, positions, forecasts against engine refills, allied transit, reserve consumption, and read-only bilingual shortage notices passed`);
