/* Battle display updates preserve live nodes and use authoritative result flags. */
'use strict';
const assert=require('node:assert/strict'),view=require('../game/battle-view.js');
const document={activeElement:null},templates=new Map();
class Node{
 constructor(tag='',attributes={},children=[]){this.nodeType=tag?1:3;this.tagName=tag.toUpperCase();this.data=this.nodeValue=tag?'':String(attributes);this.attrs=new Map(tag?Object.entries(attributes):[]);this.childNodes=[];this.parentNode=null;this.scrollTop=this.scrollLeft=0;for(const child of children)this.insertBefore(child,null);}
 get attributes(){return [...this.attrs].map(([name,value])=>({name,value}));}
 get lastChild(){return this.childNodes.at(-1);}
 hasAttribute(name){return this.attrs.has(name);}
 getAttribute(name){return this.attrs.get(name)??null;}
 setAttribute(name,value){this.attrs.set(name,String(value));}
 removeAttribute(name){this.attrs.delete(name);}
 get disabled(){return this.hasAttribute('disabled');}
 get open(){return this.hasAttribute('open');}set open(value){if(value)this.setAttribute('open','');else this.removeAttribute('open');}
 get value(){return this.getAttribute('value')||'';}set value(v){this.setAttribute('value',v);}
 get checked(){return this.hasAttribute('checked');}set checked(v){if(v)this.setAttribute('checked','');else this.removeAttribute('checked');}
 get selected(){return this.hasAttribute('selected');}set selected(v){if(v)this.setAttribute('selected','');else this.removeAttribute('selected');}
 insertBefore(node,position){if(node.parentNode)node.parentNode.removeChild(node);const index=position?this.childNodes.indexOf(position):this.childNodes.length;this.childNodes.splice(index,0,node);node.parentNode=this;return node;}
 removeChild(node){this.childNodes.splice(this.childNodes.indexOf(node),1);node.parentNode=null;}
 replaceChildren(...nodes){for(const old of [...this.childNodes])this.removeChild(old);for(const node of nodes)for(const child of node.nodeType===11?[...node.childNodes]:[node])this.insertBefore(child,null);}
 replaceWith(node){const parent=this.parentNode;parent.insertBefore(node,this);parent.removeChild(this);}
 cloneNode(deep){const next=new Node(this.nodeType===1?this.tagName:'',this.nodeType===1?Object.fromEntries(this.attrs):this.nodeValue,deep?this.childNodes.map(n=>n.cloneNode(true)):[]);next.nodeType=this.nodeType;return next;}
 contains(node){return node===this||this.childNodes.some(child=>child.contains(node));}
 matches(selector){return selector.split(',').some(value=>{value=value.trim();if(value.includes(' ')){const at=value.lastIndexOf(' ');return this.matches(value.slice(at+1))&&!!this.parentNode?.closest(value.slice(0,at));}if(value[0]==='.')return(this.getAttribute('class')||'').split(' ').includes(value.slice(1));if(value[0]==='['){const match=/^\[([^=\]]+)(?:="([^"]*)")?\]$/.exec(value);return !!match&&this.hasAttribute(match[1])&&(match[2]===undefined||this.getAttribute(match[1])===match[2]);}return this.tagName===value.toUpperCase();});}
 closest(selector){return this.matches(selector)?this:this.parentNode?.closest(selector)||null;}
 querySelectorAll(selector){return this.childNodes.flatMap(child=>[...(child.nodeType===1&&child.matches(selector)?[child]:[]),...child.querySelectorAll(selector)]);}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
 focus(options){assert.deepEqual(options,{preventScroll:true});document.activeElement=this;}
}
const text=value=>new Node('',value),element=(tag,attrs={},children=[])=>new Node(tag,attrs,children),fragment=(...children)=>{const row=element('fragment',{},children);row.nodeType=11;return row;};
document.createElement=tag=>{assert.equal(tag,'template');const template={content:fragment()};Object.defineProperty(template,'innerHTML',{set(key){const factory=templates.get(key);assert(factory,'Only explicit fixture trees are parsed');template.content=factory();}});return template;};
let nativeLanguage='zh-Hant';
const surface=()=>element('div',{'data-battle-scene':'','data-l10n-native':nativeLanguage},[element('canvas',{'data-battle-canvas':''})]);
const roster=(ids,open=true)=>element('details',{class:'battle-army-menu',...(open?{open:''}:{})},[element('summary',{},[text('Roster')]),element('div',{'data-unit-list':'friendly'},ids.map(id=>element('button',{'data-actor':id,'aria-pressed':id==='a'?'true':'false'},[text('Unit '+id)])))]);
templates.set('first',()=>fragment(element('div',{class:'arena'},[element('h2',{},[text('Round 1')]),element('div',{class:'battle-layout'},[surface(),roster(['a','b'])])])));
templates.set('next',()=>fragment(element('div',{class:'arena'},[element('h2',{},[text('Round 2')]),element('div',{class:'battle-layout'},[surface(),roster(['b','a'])])])));
templates.set('removed',()=>fragment(element('div',{class:'arena'},[element('h2',{},[text('Round 3')]),element('div',{class:'battle-layout'},[surface(),roster(['b'])])])));
templates.set('duel',()=>fragment(element('div',{class:'arena battle-duel-arena'},[element('div',{class:'battle-layout'},[surface(),element('details',{class:'battle-army-menu battle-duel-record'},[element('summary',{},[text('Duel log')]),element('ul',{class:'battle-log'})])])])));
templates.set('controls',()=>fragment(element('button',{id:'move','data-battle-nav':'left'},[text('Move')])));
const stage=element('main'),inspector=element('aside'),positions=[],window={scrollY:90,scrollTo:row=>positions.push(row)},controller=view.create({document,window});
controller.render(stage,'first',{key:'battle-a',mode:'field',inspector})();
controller.controls(inspector,'controls');
const canvas=stage.querySelector('[data-battle-canvas]'),scene=stage.querySelector('[data-battle-scene]'),a=stage.querySelector('[data-actor="a"]'),b=stage.querySelector('[data-actor="b"]');
canvas.painted='actual battlefield';a.focus({preventScroll:true});stage.querySelector('[data-unit-list]').scrollTop=41;stage.querySelector('.battle-army-menu').open=false;stage.querySelector('.battle-layout').scrollTop=17;
nativeLanguage='ja';
const restore=controller.render(stage,'next',{key:'battle-a',mode:'field',inspector});restore();
assert.equal(stage.querySelector('[data-battle-canvas]'),canvas);assert.equal(stage.querySelector('[data-battle-scene]'),scene);assert.equal(canvas.painted,'actual battlefield');assert.equal(scene.getAttribute('data-l10n-native'),'ja');
assert.equal(stage.querySelector('[data-actor="a"]'),a);assert.equal(stage.querySelector('[data-actor="b"]'),b);assert.deepEqual(stage.querySelector('[data-unit-list]').childNodes,[b,a]);assert.equal(document.activeElement,a);
assert.equal(stage.querySelector('[data-unit-list]').scrollTop,41);assert.equal(stage.querySelector('.battle-layout').scrollTop,17);assert.equal(stage.querySelector('.battle-army-menu').open,false);assert.equal(stage.querySelector('h2').childNodes[0].nodeValue,'Round 2');
// Inspector focus is restored after its controls are updated, not midway through render.
const control=inspector.querySelector('[id="move"]');control.focus({preventScroll:true});const afterControls=controller.render(stage,'next',{key:'battle-a',mode:'field',inspector});controller.controls(inspector,'controls');afterControls();assert.equal(document.activeElement,control);assert.equal(inspector.querySelector('[id="move"]'),control);
control.setAttribute('disabled','');control.focus({preventScroll:true});controller.render(stage,'next',{key:'battle-a',mode:'field',inspector})();assert.equal(document.activeElement,canvas,'A disabled control returns focus to the usable canvas');
a.focus({preventScroll:true});controller.render(stage,'removed',{key:'battle-a',mode:'field',inspector})();assert.equal(document.activeElement,canvas,'A removed unit leaves keyboard focus on its live battlefield');
controller.render(stage,'duel',{key:'battle-a',mode:'duel',inspector})();assert.equal(stage.querySelector('[data-battle-canvas]'),canvas);assert.equal(stage.querySelector('.battle-army-menu').open,false,'A new mode uses its own open state');
controller.render(stage,'first',{key:'battle-b',mode:'field',inspector})();assert.notEqual(stage.querySelector('[data-battle-canvas]'),canvas,'A new battle cannot inherit old canvas/controller state');controller.reset();
const fallback={innerHTML:''};view.create({document:{},window:{}}).render(fallback,'plain',{key:'fallback',mode:'field'})();assert.equal(fallback.innerHTML,'plain');
const before={revision:3,game:{turn:2,battle:{id:7}}},after={revision:4,game:{turn:2,battle:{id:7}},presentation:{schema:'tk2-battle-presentation-v1',revision:4,scenes:[{battle_id:7,kind:'tactic',actor:9,tactic:3,success:false,skipped:false,counter:true},{battle_id:7,kind:'tactic',actor:8,tactic:3,success:true,skipped:false,counter:false}]}};
const unchanged=JSON.stringify([before,after]);assert.equal(view.commandCue('tactic',{actor:8,tactic:3},before,after),'tactic_8d');assert.equal(view.resultScene('tactic',{actor:8,tactic:3},before,after).success,true);assert.equal(view.resultScene('tactic',{actor:9,tactic:3},before,after),null);
assert.equal(view.commandCue('tactic',{actor:9,tactic:3},before,after),'tactic');assert.equal(view.commandCue('ai',{},before,{game:{turn:3}}),'turn');assert.equal(view.sceneCue({kind:'duel_start',success:false}),'duel_refused');assert.equal(view.sceneCue({kind:'duel_action',success:true,move:'desperate'}),'duel_strike');
assert.equal(JSON.stringify([before,after]),unchanged);assert.equal(view.resultScene('tactic',{actor:8,tactic:3},before,{...after,revision:5}),null);
// Load the actual dialogue module with the same adapter used by the app audio.
const sandbox={GameBattleView:view};sandbox.window=sandbox;
require('node:vm').runInNewContext(require('node:fs').readFileSync(require.resolve('../game/dialogue.js'),'utf8'),sandbox);
for(const success of [true,false]){
 const result=JSON.parse(JSON.stringify(after));result.presentation.scenes[1].success=success;result.game.battle.log=['Localized prose is deliberately unrelated: 未能奏效'];
 const speech=sandbox.GameDialogue.command('tactic',{actor:8,tactic:3},before,result);
 assert.equal(speech[1].text.includes('此計未能奏效'),!success);assert.equal(view.commandCue('tactic',{actor:8,tactic:3},before,result),success?'tactic_8d':'error');
}
console.log('battle view: live canvas/roster/control reuse, keyed ordering, focus/scroll/details, mode/new-battle reset, neutral missing-receipt fallback and shared read-only semantic feedback passed');
