/* UI arrival dates must use the same fixed 10-day periods as the campaign. */
'use strict';
const assert=require('node:assert/strict'),calendar=require('../game/calendar.js');
assert.deepEqual(calendar.advance({year:217,month:7,day:1},1),{year:217,month:7,day:11});
assert.deepEqual(calendar.advance({year:217,month:7,day:11},1),{year:217,month:7,day:21});
assert.deepEqual(calendar.advance({year:217,month:7,day:21},1),{year:217,month:8,day:1});
assert.deepEqual(calendar.advance({year:217,month:12,day:21},2),{year:218,month:1,day:11});
assert.deepEqual(calendar.advance({year:217,month:1,day:1},36),{year:218,month:1,day:1});
assert.equal(calendar.text({year:234,month:8,day:21}),'234年8月下旬');
assert.equal(calendar.iso({year:234,month:8,day:11}),'0234-08-11');
for(const day of [0,2,10,20,30,31,NaN])assert.throws(()=>calendar.text({year:217,month:7,day}));
for(const turns of [-1,1.5,Infinity,NaN,Number.MAX_SAFE_INTEGER])assert.throws(()=>calendar.advance({year:217,month:7,day:1},turns));
console.log('Calendar UI: ten-day periods, monthly/yearly rollover, arrival dates and invalid inputs passed');
