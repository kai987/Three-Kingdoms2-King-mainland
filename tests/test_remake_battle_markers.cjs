/* Native flag metadata and effective army types, without canvas font emulation. */
'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const api=require('../game/battle-scene.js'),clone=value=>JSON.parse(JSON.stringify(value));
const atlas=JSON.parse(fs.readFileSync(path.join(__dirname,'../game/assets/battle-markers-original/index.json'),'utf8'));
assert(api.validMarkerLibrary(atlas));assert.equal(Object.keys(atlas.frames).length,132);
for(const palette of ['friendly','enemy'])for(const type of [0,1,2])for(const teams of [0,1,9,10]){
 const ordinary=atlas.frames[`${palette}:${type}:${teams}`],commander=atlas.frames[`${palette}:${type}:${teams}:commander`];
 assert.deepEqual(ordinary.source_rect.slice(2),[64,64]);assert.equal(commander.source_rect[1]-ordinary.source_rect[1],384);
}
for(const mutate of [data=>data.atlas.path='/assets/../secret.png',data=>data.atlas.width=700,data=>data.pixel_scale=1,data=>delete data.frames['enemy:2:10:commander'],data=>data.frames['friendly:0:1'].source_rect[0]=-64,data=>data.frames['enemy:0:1'].source_rect=data.frames['friendly:0:1'].source_rect,data=>data.frames['friendly:1:1'].type=0]){
 const bad=clone(atlas);mutate(bad);assert.equal(api.validMarkerLibrary(bad),false);
}
const units=[{id:1,side:'attackers',troops:1000},{id:2,side:'attackers',troops:101},{id:3,side:'defenders',troops:300},{id:'clerk-000001',side:'defenders',troops:1}],officers={1:{profile:{terrain_affinity:0}},2:{profile:{terrain_affinity:1}},3:{profile:{terrain_affinity:2}},'clerk-000001':{profile:{terrain_affinity:1}}};
const types={officers:{1:{code:2,base_code:0,source_kind:'verified_original_rom'},2:{code:0,base_code:1,source_kind:'original_table_transcription'}}},commanders={attackers:1,defenders:3};
const before=JSON.stringify({units,officers,types,commanders}),markers=api.troopMarkers(units,officers,types,commanders);
assert.deepEqual(markers.map(row=>[row.type,row.teams,row.commander]),[['水',10,true],['平',2,false],['水',3,true],['山',1,false]]);
assert.equal(JSON.stringify({units,officers,types,commanders}),before,'Rendering effective types never rewrites baseline profiles or saves');
console.log('original markers:132 native frames, exact atlas bounds, separate commander/palette tiles, effective original types and immutable baseline profiles passed');
