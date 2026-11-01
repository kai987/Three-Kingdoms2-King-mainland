'use strict';
const assert=require('node:assert/strict'),api=require('../game/tutorial.js');
const clone=x=>JSON.parse(JSON.stringify(x));
function view(turn=1,revision=1){return {revision,catalog:{scenario_id:'scenario'},game:{turn,phase:'city',player:'p',seed:2026,cities:{a:{id:'a',owner:'p'},b:{id:'b',owner:'q'}},extension:{domestic:{factions:{p:{civil:null,military:null}}}}}};}
const model=api.createModel(),first=view();assert(!model.begin({}));model.begin(first,true);model.observe(first,'a');assert.equal(model.state().status,'offer');assert.equal(model.state().completed.length,0);
model.observe(view(4));assert.equal(model.state().status,'inactive','An ignored invitation ends quietly without inserting a late guide panel');
model.begin(first);const before=JSON.stringify(first);model.observe(first,'b');assert.equal(model.state().step,'city');model.observe(first,'a');assert.equal(model.state().step,'allocate');
model.command('allocate',{},first,first);assert.equal(model.state().step,'allocate','A failed/uncommitted allocation cannot advance guidance');
const allocated=view(1,2);model.command('allocate',{},first,allocated);assert.equal(model.state().step,'domestic');
const one=clone(allocated);one.game.extension.domestic.factions.p.civil=1;model.observe(one);assert.equal(model.state().step,'domestic');
const two=clone(one);two.game.extension.domestic.factions.p.military=2;model.observe(two);assert.equal(model.state().step,'route');model.routePreview();assert.equal(model.state().step,'turn');
model.observe(view(2));assert.equal(model.state().status,'active');model.observe(view(3));assert.equal(model.state().status,'active');model.observe(view(4));assert.equal(model.state().status,'complete');
assert.equal(JSON.stringify(first),before,'Guidance must not modify resources, officers, command books, RNG or saves');
model.begin(first);model.observe(view(4));assert.equal(model.state().status,'expired','Three turns without required actions is expiry, not fabricated completion');
model.begin(view(4));model.observe(view(2));assert.equal(model.state().status,'inactive','Loading an earlier turn cannot reuse future guidance progress');
model.begin(first);const another=view();another.game.seed++;model.observe(another);assert.equal(model.state().status,'inactive');model.routePreview();assert.equal(model.state().completed.length,0);
for(const [id,row]of Object.entries(api.MESSAGES)){assert.deepEqual(Object.keys(row).sort(),['ja','zh-Hant']);assert.equal(typeof row.ja,'string');assert.equal(typeof row['zh-Hant'],'string');const vars=s=>[...s.matchAll(/\{([a-z]+)\}/g)].map(m=>m[1]).sort();assert.deepEqual(vars(row.ja),vars(row['zh-Hant']),id);}
console.log('Tutorial: opt-in, committed-action steps, faction-wide posts, preview-only march, three-turn boundary, expiry, load isolation, bilingual IDs and immutable game state passed');
