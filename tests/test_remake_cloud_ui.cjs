/* Dependency-free DOM harness for explicit cloud actions and stale responses. */
'use strict';
const assert=require('node:assert/strict'),{create}=require('../game/cloud-save-ui.js');
const unescape=value=>String(value).replace(/&(?:amp|lt|gt|quot|#39);/g,v=>({'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&#39;':"'"}[v]));
class Text{constructor(text){this.textContent=unescape(text);this.parentNode=null;}}
class Element{
 constructor(tag,doc){this.tagName=tag.toUpperCase();this.doc=doc;this.attrs={};this.dataset={};this.children=[];this.parentNode=null;this.value='';this.disabled=false;this.listeners=new Map();this.scrollTop=0;this.selectionStart=null;this.selectionEnd=null;}
 get id(){return this.attrs.id||'';}
 setAttribute(key,value){this.attrs[key]=String(value);if(key==='value')this.value=unescape(value);if(key==='disabled')this.disabled=true;if(key.startsWith('data-'))this.dataset[key.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=String(value);}
 getAttribute(key){return this.attrs[key]??null;}
 get classList(){return {add:(...names)=>{this.attrs.class=[...new Set((this.attrs.class||'').split(/\s+/).filter(Boolean).concat(names))].join(' ');},remove:(...names)=>{this.attrs.class=(this.attrs.class||'').split(/\s+/).filter(n=>!names.includes(n)).join(' ');},contains:name=>(this.attrs.class||'').split(/\s+/).includes(name)};}
 append(child){child.parentNode=this;this.children.push(child);return child;}
 get textContent(){return this.children.map(c=>c.textContent).join('');}
 set textContent(value){this.children=[];this.append(new Text(value));}
 set innerHTML(html){
  for(const child of this.children)child.parentNode=null;this.children=[];const stack=[this];
  const pattern=/<\/?([a-z][\w-]*)([^>]*)>|([^<]+)/gi;let match;
  while((match=pattern.exec(html))){
   if(match[3]!==undefined){stack.at(-1).append(new Text(match[3]));continue;}
   const tag=match[1].toLowerCase();
   if(match[0][1]==='/'){if(stack.length>1)stack.pop();continue;}
   const node=new Element(tag,this.doc),attrs=/([^\s=]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s]+)))?/g;let attr;
   while((attr=attrs.exec(match[2])))node.setAttribute(attr[1],unescape(attr[2]??attr[3]??attr[4]??''));
   stack.at(-1).append(node);if(!['input','br','hr','img','meta','link'].includes(tag)&&!match[2].endsWith('/'))stack.push(node);
  }
 }
 matchesSimple(selector){
  if(selector[0]==='#')return this.id===selector.slice(1);
  if(selector[0]==='.')return this.classList.contains(selector.slice(1));
  if(selector[0]==='['){const match=selector.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/);return !!match&&this.getAttribute(match[1])!==null&&(match[2]===undefined||this.getAttribute(match[1])===match[2]);}
  return this.tagName.toLowerCase()===selector;
 }
 matches(selector){return selector.split(',').some(part=>{const tokens=part.trim().split(/\s+/);if(!this.matchesSimple(tokens.pop()))return false;let parent=this.parentNode;for(const token of tokens.reverse()){while(parent instanceof Element&&!parent.matchesSimple(token))parent=parent.parentNode;if(!(parent instanceof Element))return false;parent=parent.parentNode;}return true;});}
 querySelectorAll(selector){const result=[];const walk=node=>{for(const child of node.children){if(child instanceof Element){if(child.matches(selector))result.push(child);walk(child);}}};walk(this);return result;}
 querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
 contains(target){for(let node=target;node;node=node.parentNode)if(node===this)return true;return false;}
 addEventListener(name,fn){if(!this.listeners.has(name))this.listeners.set(name,new Set());this.listeners.get(name).add(fn);}
 removeEventListener(name,fn){this.listeners.get(name)?.delete(fn);}
 dispatchEvent(event){event.target??=this;for(const fn of this.listeners.get(event.type)||[])fn(event);return this['on'+event.type]?.(event);}
 click(){if(!this.disabled)this.dispatchEvent({type:'click',target:this});}
 focus(){this.doc.activeElement=this;}
 setSelectionRange(start,end){this.selectionStart=start;this.selectionEnd=end;}
 checkValidity(){return !(this.attrs.required!==undefined&&!this.value)&&!(this.attrs.type==='email'&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.value));}
 close(){this.open=false;this.dispatchEvent({type:'close'});}
 showModal(){this.open=true;}
}
function dom(){
 const doc={activeElement:null,listeners:new Map(),addEventListener:Element.prototype.addEventListener,removeEventListener:Element.prototype.removeEventListener,dispatchEvent:Element.prototype.dispatchEvent};
 const body=new Element('body',doc),dialog=body.append(new Element('dialog',doc)),button=body.append(new Element('button',doc));dialog.setAttribute('id','dialog');button.setAttribute('id','cloud-save');dialog.open=false;
 doc.querySelector=selector=>body.querySelector(selector);doc.getElementById=id=>doc.querySelector('#'+id);
 return {doc,dialog,button,openDialog(title,content,actions){dialog.innerHTML=`<h2 id="dialog-title">${title}</h2>${content}<div class="dialog-actions">${actions}</div>`;dialog.showModal();for(const el of dialog.querySelectorAll('[data-cancel]'))el.onclick=()=>dialog.close();}};
}
const a='10000000-0000-4000-8000-000000000001',b='10000000-0000-4000-8000-000000000002';
const raw=' {"state":{"distance":315.0},"checksum":"unchanged"} ';
const row=(slot=1,overrides={})=>({save_id:`00000000-0000-4000-8000-${String(slot).padStart(12,'0')}`,slot,label:'洛陽戰役',revision:3,scenario:'mainland190-01',game_year:190,game_month:1,game_turn:1,save_sha256:'a'.repeat(64),created_at:'2026-10-22T00:00:00Z',updated_at:'2026-10-22T00:00:00Z',...overrides});
function mockCloud(user=null){
 const listeners=new Set(),calls=[],state={configured:true,ready:true,user,authBusy:false,confirmationRetryAt:0};let rows=[row()];
 const cloud={state,calls,setRows:value=>{rows=value;},setUser(user){state.user=user;for(const fn of listeners)fn(state);},subscribe(fn){listeners.add(fn);fn(state);return()=>listeners.delete(fn);},
  async signIn(email,password){calls.push(['signIn',email,password]);cloud.setUser({id:a,email});return{user:state.user};},
  async signUp(email,password){calls.push(['signUp',email,password]);return {needsConfirmation:true,user:null};},
  async resendConfirmation(email){calls.push(['resendConfirmation',email]);state.confirmationRetryAt=Date.now()+60000;return {needsConfirmation:true,user:null};},
  async signOut(){calls.push(['signOut']);cloud.setUser(null);},
  async list(){calls.push(['list',state.user?.id]);return rows.map(r=>({...r}));},
  async read(slot){calls.push(['read',slot]);return {...rows.find(r=>r.slot===slot),save_text:raw};},
  async write(slot,label,raw,revision,saveId){calls.push(['write',slot,label,raw,revision,saveId]);const next=row(slot,{label,revision:revision+1});rows=rows.filter(r=>r.slot!==slot).concat(next);return next;},
  async remove(slot,revision,saveId){calls.push(['remove',slot,revision,saveId]);rows=rows.filter(r=>r.slot!==slot);},
 };return cloud;
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
const deferred=()=>{let resolve;const promise=new Promise(done=>{resolve=done;});return {promise,resolve};};
function setup(cloud=mockCloud(),extraOptions={}){
 const surface=dom(),i18n={locale:'zh-Hant',apply(){}},notices=[],loaded=[];let game={year:190},busy=false;
 const options={cloud,document:surface.doc,dialog:surface.dialog,button:surface.button,i18n,openDialog:surface.openDialog,
  getView:()=>({game}),getRawSave:async()=>raw,loadRawSave:async(value,guard)=>{if(!guard())return false;loaded.push(value);return false;},notice:value=>notices.push(value),isBusy:()=>busy,...extraOptions};
 const ui=create(options),el=id=>surface.doc.getElementById(id),language=value=>{i18n.locale=value;surface.doc.dispatchEvent({type:'game-language-change'});};
 return {...surface,cloud,options,ui,el,language,notices,loaded,setGame:value=>{game=value;},setBusy:value=>{busy=value;ui.refreshButton();}};
}
(async()=>{
 // Registration/login, immediate language updates, and no implicit upload.
 const x=setup();assert(x.ui.open());x.el('cloud-email').value='person@example.test';x.el('cloud-password').value='password123';
 x.el('cloud-register-mode').click();assert.equal(x.el('cloud-password').getAttribute('autocomplete'),'new-password');
 assert(x.dialog.textContent.includes('重複註冊不會變更密碼'));
 x.language('ja');assert.equal(x.el('cloud-email').value,'person@example.test');assert.equal(x.el('cloud-password').value,'password123');assert.equal(x.el('dialog-title').textContent,'クラウドセーブ');
 assert(x.dialog.textContent.includes('再登録ではパスワードは変更されません'));
 await x.el('cloud-auth-form').dispatchEvent({type:'submit',preventDefault(){}});await tick();
 assert(x.dialog.textContent.includes('登録したメールを確認'));assert(x.dialog.textContent.includes('認証済みのアカウントはそのままログイン'));assert.equal(x.el('cloud-password').value,'');assert.equal(x.cloud.calls[0][0],'signUp');
 x.el('cloud-password').value='password123';await x.el('cloud-auth-form').dispatchEvent({type:'submit',preventDefault(){}});await tick();
 assert(x.el('cloud-write-1'));assert.equal(x.cloud.calls.filter(c=>c[0]==='list').length,1);assert.equal(x.cloud.calls.filter(c=>['write','read','remove'].includes(c[0])).length,0);
 // Label drafts and caret survive language switches. Empty slot sends raw text.
 x.el('cloud-label-2').value='漢中進度';x.el('cloud-label-2').focus();x.el('cloud-label-2').setSelectionRange(2,2);x.language('zh-Hant');
 assert.equal(x.el('cloud-label-2').value,'漢中進度');assert.equal(x.doc.activeElement.id,'cloud-label-2');assert.equal(x.doc.activeElement.selectionStart,2);
 x.el('cloud-write-2').click();await tick();
 const saved=x.cloud.calls.find(c=>c[0]==='write');assert.deepEqual(saved,['write',2,'漢中進度',raw,0,null]);assert(x.dialog.textContent.includes('雲端存檔已保存'));
 // Existing slot requires explicit confirmation and both CAS identifiers.
 const beforeWrites=x.cloud.calls.filter(c=>c[0]==='write').length;x.el('cloud-write-1').click();assert(x.el('cloud-confirm'));assert.equal(x.cloud.calls.filter(c=>c[0]==='write').length,beforeWrites);
 x.cloud.write=async(...args)=>{x.cloud.calls.push(['write',...args]);throw {code:'conflict'};};x.el('cloud-confirm').click();await tick();
 assert(x.dialog.textContent.includes('此槽的雲端版本已變更'));assert.equal(x.el('cloud-write-1').disabled,true);assert.deepEqual(x.cloud.calls.at(-1).slice(-2),[3,row().save_id]);
 x.el('cloud-refresh').click();await tick();assert.equal(x.el('cloud-write-1').disabled,false);
 // Confirmation describes the actual read snapshot, then passes its exact raw.
 const actual=row(1,{label:'另一裝置新進度',revision:9,game_month:7,save_text:raw});x.cloud.read=async()=>actual;
 x.el('cloud-read-1').click();await tick();assert(x.dialog.textContent.includes('另一裝置新進度'));assert.equal(x.loaded.length,0);
 x.language('ja');assert(x.dialog.textContent.includes('別の端末')===false);assert(x.dialog.textContent.includes('190年7月'));x.el('cloud-confirm').click();await tick();assert.equal(x.loaded[0],raw);assert(x.dialog.textContent.includes('読み込めませんでした'));
 // Deletion is explicit and carries save_id as well as revision.
 x.el('cloud-remove-1').click();assert(x.el('cloud-confirm'));assert.equal(x.cloud.calls.filter(c=>c[0]==='remove').length,0);x.el('cloud-confirm').click();await tick();
 assert.deepEqual(x.cloud.calls.at(-1),['remove',1,3,row().save_id]);assert(!x.el('cloud-read-1'));assert(x.el('cloud-read-2'));
 // No active campaign: loading remains usable, saving is disabled.
 x.setGame(null);x.dialog.close();x.ui.open();await tick();assert.equal(x.el('cloud-write-2').disabled,true);assert.equal(x.el('cloud-read-2').disabled,false);
 // Closing while a read is pending never opens a late confirmation or loads.
 const later=deferred();x.cloud.read=()=>later.promise;x.el('cloud-read-2').click();x.dialog.close();later.resolve({...row(2),save_text:raw});await tick();assert.equal(x.dialog.open,false);assert.equal(x.loaded.length,1);
 x.setBusy(true);assert.equal(x.button.disabled,true);assert.equal(x.ui.open(),false);x.setBusy(false);x.ui.destroy();
 // A ready transition after Auth's busy notification must populate the list.
 const y=setup(mockCloud());y.ui.open();y.cloud.state.authBusy=true;y.cloud.setUser({id:a,email:'a@example.test'});y.cloud.state.authBusy=false;y.cloud.setUser({id:a,email:'a@example.test'});await tick();assert(y.el('cloud-read-1'));y.ui.destroy();
 // A prior account's in-flight list cannot leak into a new account's modal.
 const old=deferred(),fresh=deferred(),cloud=mockCloud({id:a,email:'a@example.test'});cloud.list=()=>cloud.state.user.id===a?old.promise:fresh.promise;
 const z=setup(cloud);z.ui.open();cloud.setUser({id:b,email:'b@example.test'});old.resolve([row(1,{label:'PRIVATE-A'})]);await tick();assert(!z.dialog.textContent.includes('PRIVATE-A'));
 fresh.resolve([row(5,{label:'B進度'})]);await tick();assert(z.dialog.textContent.includes('B進度'));assert(z.dialog.textContent.includes('b@example.test'));assert(!z.el('cloud-read-1'));assert(z.el('cloud-read-5'));z.ui.destroy();
 // Clear already-rendered private labels and drafts on an account change too.
 const privateCloud=mockCloud({id:a,email:'a@example.test'});privateCloud.setRows([row(1,{label:'PRIVATE-A'})]);
 const q=setup(privateCloud);q.ui.open();await tick();assert.equal(q.el('cloud-label-1').value,'PRIVATE-A');q.el('cloud-label-2').value='PRIVATE-DRAFT';
 privateCloud.setRows([]);privateCloud.setUser({id:b,email:'b@example.test'});await tick();assert.equal(q.el('cloud-label-1').value,'');assert.equal(q.el('cloud-label-2').value,'');assert(!q.dialog.textContent.includes('PRIVATE-A'));q.ui.destroy();
 // Account validation errors must not be presented as invalid save files.
 const bad=setup();bad.ui.open();bad.el('cloud-email').value='person@example.test';bad.el('cloud-password').value='password123';bad.cloud.signIn=async()=>{throw {code:'invalid'};};
 await bad.el('cloud-auth-form').dispatchEvent({type:'submit',preventDefault(){}});assert(bad.dialog.textContent.includes('請輸入有效電子郵件與密碼'));assert(!bad.dialog.textContent.includes('存檔無效'));bad.ui.destroy();
 // Resend never needs a password, only runs after a click, and survives reopening.
 let clock=1000;const mailCloud=mockCloud(),mail=setup(mailCloud,{now:()=>clock});mail.ui.open();assert.equal(mailCloud.calls.length,0);
 mail.el('cloud-resend').click();await tick();assert(mail.dialog.textContent.includes('重寄確認信不需要密碼'));assert.equal(mailCloud.calls.length,0);
 mail.el('cloud-email').value='person@example.test';mailCloud.resendConfirmation=async email=>{mailCloud.calls.push(['resendConfirmation',email]);mailCloud.state.confirmationRetryAt=clock+60000;};
 mail.el('cloud-resend').click();await tick();assert.deepEqual(mailCloud.calls,[['resendConfirmation','person@example.test']]);assert.equal(mail.el('cloud-resend').disabled,true);
 assert(mail.dialog.textContent.includes('若此信箱有待確認帳號'));assert(mail.el('cloud-resend').textContent.includes('60秒'));
 mail.el('cloud-resend').click();await tick();assert.equal(mailCloud.calls.length,1);mail.dialog.close();mail.ui.open();assert.equal(mail.el('cloud-resend').disabled,true);
 clock+=60000;mail.language('ja');assert.equal(mail.el('cloud-resend').disabled,false);assert(mail.dialog.textContent.includes('確認メールを再送'));
 mail.el('cloud-email').value='person@example.test';mailCloud.resendConfirmation=async()=>{throw {code:'email_delivery_unavailable'};};mail.el('cloud-resend').click();await tick();assert(mail.dialog.textContent.includes('メール配信設定'));assert(!mail.dialog.textContent.includes('パスワードを確認'));
 mail.language('zh-Hant');assert(mail.dialog.textContent.includes('郵件服務設定'));mail.ui.destroy();
 // A resend response arriving after the dialog closes cannot reopen its status.
 const lateMail=setup(),lateResend=deferred();lateMail.cloud.resendConfirmation=()=>lateResend.promise;lateMail.ui.open();lateMail.el('cloud-email').value='person@example.test';
 lateMail.el('cloud-resend').click();lateMail.dialog.close();lateResend.resolve();await tick();assert.equal(lateMail.dialog.open,false);lateMail.ui.destroy();
 // Show a localized scenario title; refresh untouched names but keep user drafts.
 const readable=setup(mockCloud({id:a,email:'a@example.test'}));readable.options.getView=()=>({game:{},catalog:{scenarios:[{id:row().scenario,title:'反董卓聯盟'}]}});
 readable.options.i18n.t=(title,locale)=>locale==='ja'?'反董卓連合':title;readable.ui.open();await tick();
 assert(readable.dialog.textContent.includes('反董卓聯盟'));assert(!readable.dialog.textContent.includes(row().scenario));readable.language('ja');assert(readable.dialog.textContent.includes('反董卓連合'));
 readable.cloud.setRows([row(1,{label:'新遠端名稱',revision:4})]);readable.el('cloud-refresh').click();await tick();assert.equal(readable.el('cloud-label-1').value,'新遠端名稱');
 readable.el('cloud-label-1').value='自己編輯的草稿';readable.el('cloud-label-1').dispatchEvent({type:'input'});readable.cloud.setRows([row(1,{label:'又一次遠端名稱',revision:5})]);readable.el('cloud-refresh').click();await tick();assert.equal(readable.el('cloud-label-1').value,'自己編輯的草稿');assert(readable.dialog.textContent.includes('又一次遠端名稱'));readable.ui.destroy();
 console.log('cloud UI: login/registration, native languages and input preservation, explicit raw-text save/load/delete, revision+UUID conflicts, disabled local-game save, Auth-ready and stale-account/modal responses passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
