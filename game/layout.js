/* Move the existing report, retaining its controls and scroll position. */
'use strict';
(()=>{
 const header=document.querySelector('.topbar'),heading=header?.querySelector('.topbar-heading'),nav=header?.querySelector('nav');
 const journal=document.querySelector('.journal'),home=journal?.parentElement,main=document.querySelector('main');
 if(!header||!heading||!nav||!journal||!home||!main)return;
 const anchor=document.createComment('report position on compact screens');
 home.insertBefore(anchor,journal);
 const wide=matchMedia('(min-width:1280px) and (min-height:720px)');
 let queued=false;
 function update(){
  queued=false;
  const style=getComputedStyle(header),gap=parseFloat(style.columnGap)||0;
  const available=header.clientWidth-(parseFloat(style.paddingLeft)||0)-(parseFloat(style.paddingRight)||0)-heading.offsetWidth-nav.offsetWidth-2*gap;
  const frame=['paddingTop','paddingBottom','borderTopWidth','borderBottomWidth'].reduce((sum,key)=>sum+(parseFloat(style[key])||0),0);
  const headerHeight=Math.max(88,heading.offsetHeight,nav.offsetHeight)+frame;
  // Account for the future header height before moving the report. This keeps
  // the threshold stable and rejects tall windows that would letterbox the map.
  const mapHeight=main.clientHeight+header.offsetHeight-headerHeight;
  const mapWidth=(mapHeight-8)*1352/1024+8;
  const docked=wide.matches&&available>=320&&home.clientWidth>=mapWidth+8+320;
  if(header.classList.contains('has-journal')===docked)return;
  const focused=journal.contains(document.activeElement)?document.activeElement:null;
  const scroll=journal.querySelector('ol').scrollTop;
  if(docked)header.insertBefore(journal,nav);else home.insertBefore(journal,anchor.nextSibling);
  header.classList.toggle('has-journal',docked);
  document.body.classList.toggle('wide-map-layout',docked);
  journal.querySelector('ol').scrollTop=scroll;
  focused?.focus({preventScroll:true});
 }
 function schedule(){if(!queued){queued=true;requestAnimationFrame(update);}}
 wide.addEventListener('change',schedule);
 const observer=new ResizeObserver(schedule);
 for(const element of [header,heading,nav,main])observer.observe(element);
 document.addEventListener('game-language-change',schedule);
 document.fonts?.ready.then(schedule);
 update();
})();
