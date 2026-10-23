/* Account storage is explicit; it never uploads or replaces a campaign on login. */
'use strict';
(function(root){
 const copy={
  title:['雲端存檔','クラウドセーブ'],close:['返回遊戲','ゲームに戻る'],
  unavailable:['雲端存檔尚未設定，仍可使用本機保存及存檔檔案。','クラウドセーブは未設定です。本機保存とセーブファイルは引き続き使えます。'],
  preparing:['正在準備雲端連線……','クラウドへの接続を準備中…'],
  intro:['使用同一帳號，可在其他裝置讀取本遊戲的雲端存檔。登入不會自動上傳或替換目前戰役。','同じアカウントで、別の端末から本作のセーブを読み込めます。ログインだけでは送信や戦役の切り替えは行いません。'],
  email:['電子郵件','メールアドレス'],password:['密碼','パスワード'],
  login:['登入','ログイン'],register:['註冊新帳號','新規登録'],
  forgot:['忘記密碼','パスワードを忘れた場合'],backLogin:['返回登入','ログインに戻る'],
  resetSend:['發送密碼重設信','再設定メールを送信'],
  resetHelp:['請輸入原帳號信箱。收到信後，請在發送請求的同一個瀏覽器開啟連結。重新註冊不會變更原密碼。','登録済みのアドレスを入力してください。メールのリンクは、この操作を行った同じブラウザーで開いてください。再登録では元のパスワードは変更されません。'],
  resetRequested:['重設請求已處理。若此信箱可以找回帳號，系統將寄送重設信，請查看收件匣與垃圾郵件。','再設定を依頼しました。対象のアカウントがある場合はメールを送信します。受信箱と迷惑メールを確認してください。'],
  resetUnavailable:['管理者尚未設定本遊戲的密碼重設回跳網址，目前無法寄送重設信。','このゲームの再設定用URLが未設定です。管理者による設定後に送信できます。'],
  resetTitle:['設定新密碼','新しいパスワードを設定'],newPassword:['新密碼','新しいパスワード'],confirmPassword:['再次輸入新密碼','新しいパスワード（確認）'],
  resetWarning:['此帳號屬於共用認證專案。更新密碼也會影響使用同一帳號的其他應用程式；雲端存檔不會被刪除。','このアカウントは共通の認証プロジェクトに属します。同じアカウントを使う他のアプリのパスワードも変わります。クラウドセーブは削除されません。'],
  resetUpdate:['確認更新密碼','パスワードを更新'],resetCancel:['取消密碼重設','パスワードの再設定を中止'],
  passwordUpdated:['密碼已更新。請使用新密碼登入。','パスワードを更新しました。新しいパスワードでログインしてください。'],
  passwordMismatch:['兩次新密碼必須相同，並且至少8個字元。','確認用と同じパスワードを8文字以上で入力してください。'],
  recoveryExpired:['重設連結已失效或不屬於此瀏覽器。請重新發送重設信，並在同一瀏覽器開啟。','リンクが無効、期限切れ、または別のブラウザー用です。再設定メールを送り直し、同じブラウザーで開いてください。'],
  passwordUnchanged:['新密碼與原密碼相同，請換一組新密碼。','元と同じパスワードです。別の新しいパスワードを入力してください。'],
  invalidPassword:['新密碼不符合帳號安全要求，請至少使用8個字元。','新しいパスワードが要件を満たしていません。8文字以上で入力してください。'],
  loginHelp:['使用電子郵件與密碼登入。','メールアドレスとパスワードでログインします。'],
  registerHelp:['密碼至少8個字元。若需要確認信，請完成電子郵件確認後，回到本遊戲登入。若此信箱已註冊，請使用原密碼登入；重複註冊不會變更密碼。','パスワードは8文字以上です。確認メールで認証後、このゲームに戻ってログインしてください。登録済みのアドレスは元のパスワードでログインしてください。再登録ではパスワードは変更されません。'],
  confirmEmail:['註冊請求已處理。請查看註冊信箱與垃圾郵件；完成確認後，回到本遊戲登入。若未收到確認信，可稍後重寄。已確認的帳號可直接登入；重複註冊不會變更原密碼。','登録したメールを確認し、迷惑メールも確認してください。認証後にこのゲームに戻ってログインしてください。届かない場合は、しばらく待って再送できます。認証済みのアカウントはそのままログインできます。再登録では元のパスワードは変更されません。'],
  resend:['重寄確認信','確認メールを再送'],seconds:['秒','秒'],
  resendHelp:['沒有收到確認信？輸入註冊信箱後，可重寄確認信。每次請求至少間隔60秒，郵件服務仍可能有額外限制。','確認メールが届かない場合は、登録したアドレスを入力して再送できます。再送は60秒間隔で、配信側の制限が加わる場合もあります。'],
  resendRequested:['重寄請求已處理。若此信箱有待確認帳號，郵件服務會處理確認信；請查看收件匣與垃圾郵件。','再送を依頼しました。未認証の登録がある場合は、配信サービスが確認メールを処理します。受信箱と迷惑メールを確認してください。'],
  account:['目前帳號','アカウント'],logout:['登出此裝置','この端末からログアウト'],refresh:['刷新列表','一覧を更新'],
  slotsHelp:['每個帳號有5個存檔槽。本機進度與雲端分開保存；請主動選擇保存或讀取。','アカウントごとに5つの保存枠があります。本機とクラウドは別々です。保存・読込はボタンから行ってください。'],
  noCampaign:['目前尚未開始戰役，可以先讀取雲端存檔。','戦役はまだ始まっていません。クラウドのセーブは読み込めます。'],
  slot:['存檔槽','保存枠'],empty:['空白存檔槽','空き枠'],unlisted:['尚未取得列表','一覧は未取得'],label:['存檔名稱','セーブ名'],
  labelHelp:['最多80個字元','80文字以内'],save:['保存目前進度','現在の進行を保存'],load:['讀取','読込'],remove:['刪除','削除'],
  loading:['正在處理，請稍候……','処理中です。しばらくお待ちください…'],saved:['雲端存檔已保存。','クラウドに保存しました。'],
  deleted:['雲端存檔已刪除，本機進度保持原樣。','クラウドのセーブを削除しました。本機の進行はそのままです。'],loaded:['雲端進度已恢復。','クラウドの進行を読み込みました。'],
  cancel:['取消','キャンセル'],overwrite:['確認覆蓋此槽','この枠を上書き'],confirmLoad:['確認讀取此進度','この進行を読み込む'],confirmDelete:['確認刪除此槽','この枠を削除'],
  saveQuestion:['將以目前戰役覆蓋以下雲端存檔：','現在の戦役で、次のクラウドセーブを上書きします。'],
  loadQuestion:['將讀取以下雲端進度。若已開始戰役，目前未保存的進度將被替換：','次のクラウドセーブを読み込みます。戦役中の場合、現在の未保存の進行は置き換わります。'],
  deleteQuestion:['將刪除以下雲端存檔；本機保存與目前戰役不受影響：','次のクラウドセーブを削除します。本機の保存と現在の戦役には影響しません。'],
  updated:['更新時間','更新日時'],version:['版本','版'],turn:['回合','ターン'],
  unavailableError:['雲端服務目前無法使用，仍可保存本機進度。','現在クラウドを利用できません。本機には保存できます。'],
  authError:['請先登入帳號，再使用雲端存檔。','ログインしてからクラウドセーブを使ってください。'],
  authFailed:['電子郵件或密碼不正確。若忘記原密碼，請選擇「忘記密碼」，重新註冊不會更新密碼。','メールアドレスまたはパスワードを確認してください。元のパスワードを忘れた場合は再設定してください。再登録では変更されません。'],
  unconfirmed:['電子郵件尚未確認，請先完成信箱確認再登入。','メールアドレスが未認証です。認証後にログインしてください。'],
  deliveryUnavailable:['確認信服務未能寄送到此信箱，遊戲管理者需檢查郵件服務設定。重複註冊無法解除此限制。','このアドレスには確認メールを送信できません。ゲーム管理者によるメール配信設定の確認が必要です。登録を繰り返しても制限は解除されません。'],
  registrationDisabled:['目前未開放電子郵件註冊，請由遊戲管理者檢查帳號服務設定。','現在メールアドレスによる登録は無効です。ゲーム管理者による認証設定の確認が必要です。'],
  conflict:['此槽的雲端版本已變更。請先刷新列表，再選擇讀取或覆蓋；本次沒有覆蓋新版本。','この枠は別の端末などで更新されました。一覧を更新してから読込または上書きを選んでください。今回は上書きしていません。'],
  network:['連線未完成，請確認網路後再試。尚未確認雲端保存成功，本機進度不受影響。','通信が完了しませんでした。接続を確認して再試行してください。クラウドへの保存は未確認です。本機の進行には影響しません。'],
  invalid:['存檔無效或超過大小限制，目前進度未改變。','セーブが無効、またはサイズ制限を超えています。現在の進行は変更していません。'],
  invalidCredentials:['請輸入有效電子郵件與密碼；註冊密碼至少8個字元。','有効なメールアドレスとパスワードを入力してください。登録時は8文字以上必要です。'],
  invalidEmail:['請輸入有效的註冊信箱。重寄確認信不需要密碼。','有効な登録メールアドレスを入力してください。再送時にパスワードは不要です。'],
  rateLimited:['嘗試次數較多，請稍後再試。','試行回数が多いため、少し待ってからやり直してください。'],
  sessionChanged:['登入帳號已變更，請重新選擇操作。','ログイン中のアカウントが変わりました。操作を選び直してください。'],
  notFound:['此雲端存檔已不存在，請刷新列表。','このクラウドセーブは存在しません。一覧を更新してください。'],
  busy:['已有操作正在進行，請稍候再試。','別の操作を処理中です。完了後にやり直してください。'],
  loadFailed:['雲端存檔未能讀入，請查看遊戲提示。目前進度未改變。','クラウドセーブを読み込めませんでした。ゲームの通知を確認してください。現在の進行は変更していません。'],
 };
 const errorKeys={unavailable:'unavailableError',auth_required:'authError',auth_failed:'authFailed',email_unconfirmed:'unconfirmed',email_delivery_unavailable:'deliveryUnavailable',registration_disabled:'registrationDisabled',conflict:'conflict',network:'network',invalid:'invalid',rate_limited:'rateLimited',session_changed:'sessionChanged',not_found:'notFound',busy:'busy',recovery_unavailable:'resetUnavailable',recovery_expired:'recoveryExpired',password_unchanged:'passwordUnchanged',invalid_password:'invalidPassword'};
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function create(options){
  const doc=options.document||root.document,i18n=options.i18n||root.GameI18n,cloud=options.cloud,recovery=options.recovery;
  const dialog=options.dialog||doc.querySelector('#dialog'),button=options.button||doc.querySelector('#cloud-save');
  if(!dialog||!cloud)throw new Error('Cloud save UI requires a dialog and controller');
  let panel=null,generation=0,pending=false,rows=[],listed=false,currentUser=cloud.state.user?.id||null;
  let authMode='login',email='',message=null,confirmation=null,destroyed=false,resendTimer=null;
  const labels=new Map(),dirtyLabels=new Set(),conflicts=new Set();
  const locale=()=>i18n?.locale==='ja'?'ja':'zh-Hant';
  const t=key=>copy[key]?.[locale()==='ja'?1:0]||key;
  const now=()=>typeof options.now==='function'?options.now():Date.now();
  const resendWait=()=>Math.max(0,Math.ceil(((Number(cloud.state.confirmationRetryAt)||0)-now())/1000));
  const resetWait=()=>Math.max(0,Math.ceil(((Number(recovery?.state.retryAt)||0)-now())/1000));
  const query=selector=>panel?.querySelector(selector);
  const isBusy=()=>pending||!!options.isBusy?.()||!!cloud.state.authBusy||!!recovery?.state.busy;
  const isOpen=()=>!!panel&&dialog.open&&dialog.querySelector('[data-cloud-panel]')===panel;
  const stamp=()=>({generation,user:cloud.state.user?.id||null,panel});
  const valid=point=>!destroyed&&isOpen()&&point.generation===generation&&point.panel===panel&&point.user===(cloud.state.user?.id||null);
  function clear(){
   clearTimeout(resendTimer);resendTimer=null;
   for(const id of ['#cloud-password','#cloud-new-password','#cloud-confirm-password']){const password=query(id);if(password)password.value='';}
   panel=null;generation++;pending=false;rows=[];listed=false;confirmation=null;message=null;email='';labels.clear();dirtyLabels.clear();conflicts.clear();
   dialog.classList.remove('cloud-save-dialog');refreshButton();
  }
  function refreshButton(){
   if(!button)return;
   button.textContent=t('title');button.setAttribute('data-l10n-native',locale());
   button.setAttribute('aria-haspopup','dialog');button.disabled=!!options.isBusy?.()||pending||!!cloud.state.authBusy||!!recovery?.state.busy;
  }
  function date(row){
   const y=Number(row.game_year),m=Number(row.game_month),turn=Number(row.game_turn);
   return `${y}年${m}月 · ${turn}${t('turn')}`;
  }
  function moment(value){
   const time=new Date(value);if(!Number.isFinite(time.getTime()))return '—';
   return time.toLocaleString(locale()==='ja'?'ja-JP':'zh-TW',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hour12:false});
  }
  function scenarioName(row){
   const scenario=options.getView?.()?.catalog?.scenarios?.find(scenario=>scenario.id===row.scenario);
   return scenario?.title?(i18n?.t?.(scenario.title,locale())||scenario.title):row.scenario;
  }
  function info(row){return `<strong>${escape(row.label||`${t('slot')} ${row.slot}`)}</strong><p>${escape(date(row))}</p><p class="small">${escape(scenarioName(row))} · ${t('version')} ${escape(row.revision)}<br>${t('updated')} ${escape(moment(row.updated_at))}</p>`;}
  function preserve(){
   if(!panel)return {password:'',focus:null,start:null,end:null,scroll:dialog.scrollTop};
   const input=query('#cloud-email');if(input)email=input.value;
   for(const input of panel.querySelectorAll('[data-cloud-label]'))if(input.value!==input.dataset.cloudRenderedLabel){const slot=Number(input.dataset.cloudLabel);labels.set(slot,input.value);dirtyLabels.add(slot);}
   const focus=panel.contains(doc.activeElement)?doc.activeElement:null;
   return {password:query('#cloud-password')?.value||'',newPassword:query('#cloud-new-password')?.value||'',confirmPassword:query('#cloud-confirm-password')?.value||'',focus:focus?.id,start:focus?.selectionStart,end:focus?.selectionEnd,scroll:dialog.scrollTop};
  }
  function confirmationHtml(){
   if(!confirmation)return '';
   const kind=confirmation.kind,key={save:'saveQuestion',load:'loadQuestion',remove:'deleteQuestion'}[kind];
   const action={save:'overwrite',load:'confirmLoad',remove:'confirmDelete'}[kind];
   return `<section class="cloud-confirm" aria-labelledby="cloud-confirm-heading"><h3 id="cloud-confirm-heading">${t(key)}</h3>${info(confirmation.row)}<div class="cloud-slot-actions"><button id="cloud-confirm" class="primary">${t(action)}</button><button id="cloud-confirm-cancel">${t('cancel')}</button></div></section>`;
  }
  function slotHtml(slot){
   const row=rows.find(row=>row.slot===slot),label=labels.get(slot)??row?.label??'';
   const disabled=isBusy()||!options.getView?.()?.game||!listed||conflicts.has(slot);
   return `<section class="cloud-slot" data-cloud-slot="${slot}" aria-labelledby="cloud-slot-heading-${slot}"><h3 id="cloud-slot-heading-${slot}">${t('slot')} ${slot}${row?'':` · ${t(listed?'empty':'unlisted')}`}</h3>${row?info(row):''}<label class="field cloud-slot-label" for="cloud-label-${slot}">${t('label')}<input id="cloud-label-${slot}" data-cloud-label="${slot}" data-cloud-rendered-label="${escape(label)}" type="text" maxlength="80" value="${escape(label)}" placeholder="${t('labelHelp')}" ${isBusy()?'disabled':''}></label><div class="cloud-slot-actions"><button id="cloud-write-${slot}" data-cloud-write="${slot}" ${disabled?'disabled':''}>${t('save')}</button>${row?`<button id="cloud-read-${slot}" data-cloud-read="${slot}" ${isBusy()?'disabled':''}>${t('load')}</button><button id="cloud-remove-${slot}" data-cloud-remove="${slot}" ${isBusy()||conflicts.has(slot)?'disabled':''}>${t('remove')}</button>`:''}</div></section>`;
  }
  function draw({keepPassword=true,keepDrafts=true}={}){
   if(!isOpen())return;
   clearTimeout(resendTimer);resendTimer=null;
   const before=keepDrafts?preserve():{password:'',focus:null,start:null,end:null,scroll:0},lang=locale(),state=cloud.state,user=state.user;
   panel.setAttribute('data-l10n-native',lang);
   const title=dialog.querySelector('#dialog-title');if(title){title.setAttribute('data-l10n-native',lang);title.textContent=t('title');}
   const close=dialog.querySelector('.dialog-actions [data-cancel]');if(close){close.setAttribute('data-l10n-native',lang);close.textContent=t('close');}
   let body='';
   if(!state.configured)body=`<p>${t('unavailable')}</p>`;
   else if(!state.ready)body=`<p>${t('preparing')}</p>`;
   else if(recovery?.state.user){
    body=`<h3>${t('resetTitle')}</h3><p>${t('account')}：<strong>${escape(recovery.state.user.email)}</strong></p><p>${t('resetWarning')}</p><form id="cloud-reset-form"><label class="field" for="cloud-new-password">${t('newPassword')}<input id="cloud-new-password" type="password" required minlength="8" maxlength="256" autocomplete="new-password"></label><label class="field" for="cloud-confirm-password">${t('confirmPassword')}<input id="cloud-confirm-password" type="password" required minlength="8" maxlength="256" autocomplete="new-password"></label><button type="submit" class="primary">${t('resetUpdate')}</button></form><button id="cloud-reset-cancel" type="button">${t('resetCancel')}</button>`;
   }
   else if(!user){
    const wait=authMode==='recover'?resetWait():resendWait();
    if(authMode==='recover')body=`<h3>${t('forgot')}</h3><p>${t('resetHelp')}</p>${!recovery?.state.enabled?`<p>${t('resetUnavailable')}</p>`:''}<form id="cloud-recovery-form"><label class="field" for="cloud-email">${t('email')}<input id="cloud-email" name="email" type="email" required autocomplete="username" autocapitalize="none" spellcheck="false" maxlength="254" value="${escape(email)}"></label><button type="submit" class="primary" ${!recovery?.state.enabled||wait?'disabled':''}>${t('resetSend')}${wait?` (${wait}${t('seconds')})`:''}</button></form><button id="cloud-back-login" type="button">${t('backLogin')}</button>`;
    else{
    body=`<p>${t('intro')}</p><div class="cloud-auth-modes" role="tablist" aria-label="${t('title')}"><button id="cloud-login-mode" role="tab" aria-selected="${authMode==='login'}" ${authMode==='login'?'class="primary"':''}>${t('login')}</button><button id="cloud-register-mode" role="tab" aria-selected="${authMode==='register'}" ${authMode==='register'?'class="primary"':''}>${t('register')}</button></div><form id="cloud-auth-form" class="cloud-auth-form"><p class="small">${t(authMode==='login'?'loginHelp':'registerHelp')}</p><label class="field" for="cloud-email">${t('email')}<input id="cloud-email" name="email" type="email" required autocomplete="username" autocapitalize="none" spellcheck="false" maxlength="254" value="${escape(email)}"></label><label class="field" for="cloud-password">${t('password')}<input id="cloud-password" name="password" type="password" required minlength="${authMode==='register'?8:1}" maxlength="256" autocomplete="${authMode==='register'?'new-password':'current-password'}"></label><button id="cloud-auth-submit" type="submit" class="primary">${t(authMode==='login'?'login':'register')}</button></form><div class="cloud-confirmation-help"><p class="small">${t('resendHelp')}</p><button id="cloud-resend" type="button" ${wait?'disabled':''}>${t('resend')}${wait?` (${wait}${t('seconds')})`:''}</button></div>`;
    body+=`<button id="cloud-forgot" type="button">${t('forgot')}</button>`;
    }
    if(wait){resendTimer=setTimeout(()=>{resendTimer=null;draw();},1000);resendTimer.unref?.();}
   }else{
    body=`<div class="cloud-account"><p>${t('account')}：<strong>${escape(user.email||user.id)}</strong></p><div class="cloud-slot-actions"><button id="cloud-refresh">${t('refresh')}</button><button id="cloud-logout">${t('logout')}</button></div></div><p class="small">${t('slotsHelp')}</p>${!options.getView?.()?.game?`<p>${t('noCampaign')}</p>`:''}${confirmationHtml()}<div class="cloud-slots">${Array.from({length:5},(_,i)=>slotHtml(i+1)).join('')}</div>`;
   }
   panel.innerHTML=`<div id="cloud-status" class="cloud-status${message?.error?' error':''}" role="${message?.error?'alert':'status'}" aria-live="polite">${pending?t('loading'):message?t(message.key):''}</div>${body}`;
   for(const [id,key] of [['#cloud-password','password'],['#cloud-new-password','newPassword'],['#cloud-confirm-password','confirmPassword']]){const input=query(id);if(input&&keepPassword)input.value=before[key]||'';}
   for(const node of panel.querySelectorAll('button,input'))if(isBusy())node.disabled=true;
   bind();refreshButton();i18n?.apply?.();
   if(before.focus){const focus=doc.getElementById(before.focus);if(focus&&panel.contains(focus)&&!focus.disabled){try{focus.focus({preventScroll:true});if(before.start!==null&&typeof focus.setSelectionRange==='function')focus.setSelectionRange(before.start,before.end);}catch{}}}
   dialog.scrollTop=before.scroll;
  }
  function fail(error,point){
   if(!valid(point))return;
   pending=false;message={key:errorKeys[error?.code]||'network',error:true};confirmation=null;draw();
  }
  function begin(){
   if(!isOpen()||isBusy())return null;
   pending=true;message=null;const point=stamp();draw();return point;
  }
  async function refresh(){
   const point=begin();if(!point)return;
   try{
    const result=await cloud.list();if(!valid(point))return;
    rows=result;listed=true;conflicts.clear();confirmation=null;message=null;
    for(let slot=1;slot<=5;slot++)if(!dirtyLabels.has(slot)){const row=rows.find(row=>row.slot===slot);if(row)labels.set(slot,row.label||'');else labels.delete(slot);}
    pending=false;draw();
   }catch(error){fail(error,point);}
  }
  async function authenticate(event){
   event.preventDefault();
   const emailInput=query('#cloud-email'),passwordInput=query('#cloud-password');
   email=emailInput.value.trim();const password=passwordInput.value;
   if(!emailInput.checkValidity()||!password||(authMode==='register'&&password.length<8)){
    message={key:'invalidCredentials',error:true};draw();return;
   }
   const registering=authMode==='register',point=begin();if(!point)return;
   try{
    const result=registering?await cloud.signUp(email,password):await cloud.signIn(email,password);
    if(!valid(point))return;
    pending=false;
    if(registering&&result?.needsConfirmation){authMode='login';message={key:'confirmEmail'};draw({keepPassword:false});}
    else{draw({keepPassword:false});if(cloud.state.user&&!listed)void refresh();}
   }catch(error){
    if(valid(point)&&error?.code==='invalid'){pending=false;message={key:'invalidCredentials',error:true};draw();}
    else fail(error,point);
   }
  }
  async function resend(){
   if(resendWait())return;
   const input=query('#cloud-email');email=input.value.trim();
   if(!input.checkValidity()){message={key:'invalidEmail',error:true};draw();return;}
   const point=begin();if(!point)return;
   try{
    await cloud.resendConfirmation(email);if(!valid(point))return;
    pending=false;message={key:'resendRequested'};draw({keepPassword:false});
   }catch(error){
    if(valid(point)&&error?.code==='invalid'){pending=false;message={key:'invalidEmail',error:true};draw();}
    else fail(error,point);
   }
  }
  async function signOut(){
   const point=begin();if(!point)return;
   try{await cloud.signOut();if(valid(point)){pending=false;draw({keepPassword:false});}}
   catch(error){fail(error,point);}
  }
  async function requestRecovery(event){
   event.preventDefault();const input=query('#cloud-email');email=input.value.trim();
   if(!input.checkValidity()){message={key:'invalidEmail',error:true};draw();return;}
   const point=begin();if(!point)return;
   try{await recovery.request(email);if(valid(point)){pending=false;message={key:'resetRequested'};draw({keepPassword:false});}}
   catch(error){fail(error,point);}
  }
  async function updatePassword(event){
   event.preventDefault();const password=query('#cloud-new-password').value,again=query('#cloud-confirm-password').value;
   if(password.length<8||password.length>256||password!==again){message={key:'passwordMismatch',error:true};draw();return;}
   email=recovery.state.user?.email||email;const point=begin();if(!point)return;
   try{await recovery.update(password);if(valid(point)){pending=false;authMode='login';message={key:'passwordUpdated'};draw({keepPassword:false});}}
   catch(error){fail(error,point);}
  }
  async function cancelRecovery(){
   const point=begin();if(!point)return;
   try{await recovery.cancel();if(valid(point)){pending=false;authMode='login';message=null;draw({keepPassword:false});}}
   catch(error){fail(error,point);}
  }
  async function write(slot,row){
   if(!options.getView?.()?.game)return;
   const label=(labels.get(slot)||'').trim()||`${t('slot')} ${slot}`;
   const point=begin();if(!point)return;
   try{
    const raw=await options.getRawSave();if(!valid(point))return;
    const result=await cloud.write(slot,label,raw,row?.revision||0,row?.save_id||null);if(!valid(point))return;
    rows=rows.filter(row=>row.slot!==slot).concat(result).sort((a,b)=>a.slot-b.slot);labels.set(slot,result.label||label);dirtyLabels.delete(slot);
    pending=false;confirmation=null;message={key:'saved'};draw();
   }catch(error){if(valid(point)&&error?.code==='conflict')conflicts.add(slot);fail(error,point);}
  }
  async function read(slot){
   const point=begin();if(!point)return;
   try{const row=await cloud.read(slot);if(!valid(point))return;pending=false;confirmation={kind:'load',row};message=null;draw();query('#cloud-confirm')?.focus();}
   catch(error){fail(error,point);}
  }
  async function load(row){
   const point=begin();if(!point)return;
   try{
    if(!valid(point))return;
    const ok=await options.loadRawSave(row.save_text,()=>valid(point));
    if(ok&&point.user===(cloud.state.user?.id||null))options.notice?.(t('loaded'));
    if(!valid(point))return;
    pending=false;confirmation=null;message=ok?{key:'loaded'}:{key:'loadFailed',error:true};draw();
   }catch(error){fail(error,point);}
  }
  async function remove(row){
   const point=begin();if(!point)return;
   try{
    await cloud.remove(row.slot,row.revision,row.save_id);if(!valid(point))return;
    rows=rows.filter(value=>value.slot!==row.slot);labels.delete(row.slot);dirtyLabels.delete(row.slot);pending=false;confirmation=null;message={key:'deleted'};draw();
   }catch(error){if(valid(point)&&error?.code==='conflict')conflicts.add(row.slot);fail(error,point);}
  }
  function bind(){
   const bindClick=(id,handler)=>{const el=query(id);if(el)el.onclick=handler;};
   bindClick('#cloud-login-mode',()=>{if(isBusy())return;authMode='login';message=null;draw();});
   bindClick('#cloud-register-mode',()=>{if(isBusy())return;authMode='register';message=null;draw();});
   bindClick('#cloud-resend',()=>void resend());
   bindClick('#cloud-forgot',()=>{if(isBusy())return;authMode='recover';message=null;draw({keepPassword:false});});
   bindClick('#cloud-back-login',()=>{if(isBusy())return;authMode='login';message=null;draw({keepPassword:false});});
   bindClick('#cloud-reset-cancel',()=>void cancelRecovery());
   if(query('#cloud-recovery-form'))query('#cloud-recovery-form').onsubmit=requestRecovery;
   if(query('#cloud-reset-form'))query('#cloud-reset-form').onsubmit=updatePassword;
   if(query('#cloud-auth-form'))query('#cloud-auth-form').onsubmit=authenticate;
   if(query('#cloud-email'))query('#cloud-email').oninput=event=>{email=event.target.value;};
   bindClick('#cloud-refresh',()=>void refresh());bindClick('#cloud-logout',()=>void signOut());
   for(const input of panel.querySelectorAll('[data-cloud-label]'))input.oninput=()=>{const slot=Number(input.dataset.cloudLabel);labels.set(slot,input.value);dirtyLabels.add(slot);};
   for(const node of panel.querySelectorAll('[data-cloud-write]'))node.onclick=()=>{
    if(isBusy())return;preserve();const slot=Number(node.dataset.cloudWrite),row=rows.find(row=>row.slot===slot);
    if(row){confirmation={kind:'save',row};message=null;draw();query('#cloud-confirm')?.focus();}else void write(slot,null);
   };
   for(const node of panel.querySelectorAll('[data-cloud-read]'))node.onclick=()=>void read(Number(node.dataset.cloudRead));
   for(const node of panel.querySelectorAll('[data-cloud-remove]'))node.onclick=()=>{
    if(isBusy())return;confirmation={kind:'remove',row:rows.find(row=>row.slot===Number(node.dataset.cloudRemove))};message=null;draw();query('#cloud-confirm')?.focus();
   };
   bindClick('#cloud-confirm-cancel',()=>{if(isBusy())return;confirmation=null;message=null;draw();});
   bindClick('#cloud-confirm',()=>{
    if(!confirmation||isBusy())return;
    const {kind,row}=confirmation;if(kind==='save')void write(row.slot,row);else if(kind==='load')void load(row);else void remove(row);
   });
  }
  function open(){
   if(destroyed||isBusy())return false;
   generation++;pending=false;rows=[];listed=false;confirmation=null;message=null;labels.clear();dirtyLabels.clear();conflicts.clear();
   if(recovery?.state.error&&recovery.state.hasCallback){authMode='recover';message={key:errorKeys[recovery.state.error]||'recoveryExpired',error:true};}
   const token=generation;
   options.openDialog(t('title'),`<div class="cloud-panel" data-cloud-panel="${token}" data-l10n-native="${locale()}"></div>`,`<button data-cancel data-l10n-native="${locale()}">${t('close')}</button>`);
   panel=dialog.querySelector(`[data-cloud-panel="${token}"]`);
   if(!panel||!dialog.open){panel=null;return false;}
   dialog.classList.add('cloud-save-dialog');draw();
   if(cloud.state.ready&&cloud.state.user&&!recovery?.state.user)void refresh();
   return true;
  }
  function stateChanged(){
   const id=cloud.state.user?.id||null,changed=id!==currentUser;
   currentUser=id;refreshButton();
   if(changed){
    const password=query('#cloud-password');if(password)password.value='';
    generation++;pending=false;rows=[];listed=false;confirmation=null;message=null;labels.clear();dirtyLabels.clear();conflicts.clear();
   }
   if(isOpen()){draw({keepPassword:!changed,keepDrafts:!changed});if(id&&cloud.state.ready&&!listed&&!isBusy()&&!recovery?.state.user)void refresh();}
  }
  const unsubscribe=cloud.subscribe(stateChanged);
  let recoveryId=recovery?.state.user?.id||null;
  const unsubscribeRecovery=recovery?.subscribe(value=>{const next=value.user?.id||null,changed=next!==recoveryId;recoveryId=next;refreshButton();if(isOpen())draw({keepPassword:!changed});});
  const languageChanged=()=>{refreshButton();draw();};
  const closed=()=>{if(panel)clear();};
  const observer=typeof root.MutationObserver==='function'?new root.MutationObserver(()=>{if(panel&&!dialog.contains(panel))clear();}):null;
  observer?.observe(dialog,{childList:true});
  doc.addEventListener('game-language-change',languageChanged);dialog.addEventListener('close',closed);button?.addEventListener('click',open);refreshButton();
  return {open,refreshButton,destroy(){destroyed=true;unsubscribe?.();unsubscribeRecovery?.();observer?.disconnect();doc.removeEventListener('game-language-change',languageChanged);dialog.removeEventListener('close',closed);button?.removeEventListener('click',open);clear();}};
 }
 const api={create};if(typeof module==='object'&&module.exports)module.exports=api;else root.CloudSaveUI=api;
})(typeof window==='object'?window:globalThis);
