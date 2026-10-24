/* Move the existing report, retaining its controls and scroll position. */
'use strict';
(()=>{
 const header=document.querySelector('.topbar'),heading=header?.querySelector('.topbar-heading'),nav=header?.querySelector('nav');
 const journal=document.querySelector('.journal'),home=journal?.parentElement,main=document.querySelector('main');
 if(!header||!heading||!nav||!journal||!home||!main)return;
 const anchor=document.createComment('report position on compact screens');
 home.insertBefore(anchor,journal);
 const wide=matchMedia('(min-width:1280px) and (min-height:720px)');
 const compact=matchMedia('(max-width:1000px), (max-height:540px)'),inspector=document.querySelector('#inspector');
 const bar=document.createElement('div');bar.className='mobile-inspector-bar';bar.hidden=true;
 const toggle=document.createElement('button');toggle.type='button';toggle.id='inspector-toggle';toggle.setAttribute('aria-controls','inspector');
 const information=document.createElement('button');information.type='button';information.id='inspector-compact-information';
 bar.append(toggle,information);inspector?.before(bar);
 let collapsed=false;
 function updateInspector(){
  // Setup and battle retain their full controls. Only the campaign command panel
  // can be collapsed, by an explicit player action; its DOM and handlers remain.
  const eligible=compact.matches&&!!inspector?.querySelector('.city-command-tabs')&&!inspector.classList.contains('setup-menu')&&!!document.querySelector('#world-map');
  const language=globalThis.GameI18n?.locale==='ja'?'ja':'zh-Hant',ja=language==='ja';
  bar.hidden=!eligible;
  document.body.classList.toggle('mobile-inspector-collapsed',eligible&&collapsed);
  const city=inspector?.querySelector('.inspector-heading h2')?.textContent?.trim()||'';
  toggle.textContent=ja?`${collapsed?'命令を開く':'命令を折りたたむ'}${city?'・'+city:''}`:`${collapsed?'展開命令':'收合命令'}${city?' · '+city:''}`;
  toggle.setAttribute('aria-expanded',String(!eligible||!collapsed));toggle.setAttribute('data-l10n-native',language);
  information.textContent='都市情報';information.setAttribute('data-l10n-native',language);
  information.disabled=!inspector?.querySelector('#city-information');
 }
 toggle.onclick=()=>{collapsed=!collapsed;updateInspector();};
 information.onclick=()=>inspector?.querySelector('#city-information')?.click();
 let queued=false;
 function update(){
  queued=false;
  updateInspector();
  const style=getComputedStyle(header),gap=parseFloat(style.columnGap)||0;
  const available=header.clientWidth-(parseFloat(style.paddingLeft)||0)-(parseFloat(style.paddingRight)||0)-heading.offsetWidth-nav.offsetWidth-2*gap;
  const frame=['paddingTop','paddingBottom','borderTopWidth','borderBottomWidth'].reduce((sum,key)=>sum+(parseFloat(style[key])||0),0);
  const headerHeight=Math.max(88,heading.offsetHeight,nav.offsetHeight)+frame;
  // Account for the future header height before moving the report. This keeps
  // the threshold stable and rejects tall windows that would letterbox the map.
  const mapHeight=main.clientHeight+header.offsetHeight-headerHeight;
  const mapWidth=(mapHeight-8)*1352/1024+8;
  const docked=wide.matches&&available>=320&&home.clientWidth>=mapWidth+8+336;
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
 compact.addEventListener('change',schedule);
 const observer=new ResizeObserver(schedule);
 for(const element of [header,heading,nav,main])observer.observe(element);
 if(inspector){
  const contentObserver=new MutationObserver(schedule);
  contentObserver.observe(inspector,{childList:true,subtree:true,attributes:true,attributeFilter:['class']});
 }
 document.addEventListener('game-language-change',schedule);
 document.fonts?.ready.then(schedule);
 update();
})();
