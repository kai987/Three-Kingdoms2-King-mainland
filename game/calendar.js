/* Fixed campaign calendar: three ten-day periods in every 30-day month. */
(function(root,factory){
 'use strict';
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 else root.GameCalendar=api;
})(typeof window==='object'?window:globalThis,function(){
 'use strict';
 function validate(date){
  if(!date||!Number.isSafeInteger(date.year)||date.year<1||!Number.isInteger(date.month)||date.month<1||date.month>12||![1,11,21].includes(date.day))throw new RangeError('Invalid campaign date');
  return date;
 }
 function period(day){
  const label={1:'上旬',11:'中旬',21:'下旬'}[day];
  if(!label)throw new RangeError('Invalid ten-day period');
  return label;
 }
 function advance(date,turns){
  validate(date);
  if(!Number.isSafeInteger(turns)||turns<0)throw new RangeError('Invalid turn duration');
  const absolute=(date.year-1)*36+(date.month-1)*3+(date.day-1)/10+turns;
  if(!Number.isSafeInteger(absolute))throw new RangeError('Campaign date overflow');
  return {year:Math.floor(absolute/36)+1,month:Math.floor(absolute%36/3)+1,day:absolute%3*10+1};
 }
 function text(date){validate(date);return `${date.year}年${date.month}月${period(date.day)}`;}
 function iso(date){validate(date);return `${String(date.year).padStart(4,'0')}-${String(date.month).padStart(2,'0')}-${String(date.day).padStart(2,'0')}`;}
 return Object.freeze({period,advance,text,iso});
});
