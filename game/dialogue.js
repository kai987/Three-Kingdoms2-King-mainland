/* Deterministic, display-only exchanges. Facts remain in events/presentation. */
'use strict';
(function(root){
 const ROLES={ruler:['君主','君主'],officer:['執行武將','実行武将'],messenger:['傳令','伝令'],clerk:['書吏','書記'],merchant:['商人','商人'],doctor:['醫者','医師'],teacher:['學師','学問所の師'],recruit:['應募者','応募者'],soldier:['軍士','兵士'],steward:['庫吏','倉庫係']};
 const pick=(language,tc,ja)=>language==='ja'?ja:tc;
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 function context(view={},language='zh-Hant',i18n){
  const tr=value=>i18n?.t?i18n.t(String(value??''),language):String(value??'');
  const officers=view.game?.officers||{},library=view.catalog?.library||[],staff=view.game?.extension?.civil_staff?.people||{};
  function person(id,fallback='officer',snapshot){
   const runtime=officers[String(id)]||Object.values(officers).find(row=>row.person_id===id),entry=library.find(row=>row.person_id===id||String(row.id)===String(id));
   const civil=staff[id]||Object.values(staff).find(row=>row.id===id);
   const personId=runtime?.person_id||entry?.person_id||civil?.id||(typeof id==='string'&&/^clerk-\d{6,12}$/.test(id)?id:null);
   const rawName=snapshot?.name||view.catalog?.names?.[String(id)]||entry?.name||civil?.name||(runtime&&view.catalog?.names?.[String(Object.entries(officers).find(([,o])=>o===runtime)?.[0])]);
   return personId&&rawName?{role:fallback,personId,name:tr(rawName),...(snapshot?.portrait?{portrait:snapshot.portrait}:{})}:role(fallback);
  }
  function role(key){return {role:key,name:pick(language,...(ROLES[key]||ROLES.officer))};}
  const city=id=>tr(view.catalog?.cities?.find(row=>row.id===id)?.name||pick(language,'此城','この都市'));
  const faction=id=>tr((view.catalog?.factions||[]).find(row=>row.id===id)?.display_name||(view.catalog?.factions||[]).find(row=>row.id===id)?.name||pick(language,'本方','自軍'));
  return {person,role,city,faction,tr,t:(tc,ja)=>pick(language,tc,ja),language,view};
 }
 // Every event has an explicit exchange; no historical quotation is implied.
 const EVENTS={
  campaign_start:(c,d)=>[['messenger',c.t('各城名冊與軍需已呈上，請下達本旬方略。','各都市の名簿と軍需をお届けしました。今旬の方針をご指示ください。')],['subject',c.t('先察城防與人才，再定進退。諸將各守其職。','まず城の守りと人材を見よう。諸将はそれぞれの務めを果たせ。')]],
  officer_appeared:c=>[['messenger',c.t(`${c.subject.name}已在${c.place}現身，可遣人尋訪。`,`${c.subject.name}が${c.place}に現れました。使者を遣わして訪ねられます。`)],['clerk',c.t('已記入待訪名冊，是否登用仍須當面相詢。','在野の名簿に記しました。仕官の意思は本人にお尋ねください。')]],
  recruit_success:c=>[['actor',c.t('願請閣下出仕，共理軍民之事。','どうか仕官し、共に軍と民を支えていただきたい。')],['subject',c.t('既蒙相邀，願盡己力。','お招きに応じ、力を尽くしましょう。')]],
  recruit_failure:c=>[['actor',c.t('可願出仕，助我方一臂之力？','我らに仕え、お力添えいただけますか。')],['subject',c.t('此番尚難從命，請容我再作考量。','このたびはお受けできません。今しばらく考えさせてください。')]],
  defection:c=>[['actor',c.t('若願轉投本方，當與諸將一同任事。','我らのもとへ移られるなら、諸将と共に働いていただきたい。')],['subject',c.t('我意已決，今後願效力於此。','決心はつきました。これよりお力になりましょう。')]],
  officer_death:c=>[['messenger',c.t(`${c.subject.name}已逝，謹此稟告。`,`${c.subject.name}が亡くなられました。謹んでご報告します。`)],['clerk',c.t('請收整遺留軍務，按實際名冊交接。','残る軍務を整理し、名簿に従って引き継ぎましょう。')]],
  succession:c=>[['messenger',c.t(`眾務待理，請${c.subject.name}接掌軍政。`,`軍政の引き継ぎを、${c.subject.name}にお願いいたします。`)],['subject',c.t('當承此任，與諸將共守基業。','この務めを引き受け、諸将と共に基盤を守ろう。')]],
  faction_ended:c=>[['messenger',c.t('一方勢力已退出戰局，疆界又有變動。','一つの勢力が戦役から退き、情勢が変わりました。')],['clerk',c.t('已按當前歸屬重整名冊，請察看鄰境。','現在の所属に従い名簿を整理しました。周辺の情勢をご確認ください。')]],
  faction_founded:c=>[['subject',c.t('眾人既已聚集，當共同守土安民。','皆が集まったからには、共に土地と民を守ろう。')],['messenger',c.t('起兵已成，城池與人員以本次實際配置為準。','挙兵が成立しました。都市と人員は今回の実際の配置をご確認ください。')]],
  faction_founding_skipped:c=>[['messenger',c.t('城池或人員情勢已變，此番未能起兵。','都市または人員の状況が変わり、今回は挙兵に至りませんでした。')],['clerk',c.t('仍按現有戰局辦理，不另行改置人員。','現在の戦況に従って処理し、人物の配置を別途変更しません。')]],
  faction_coup:c=>[['messenger',c.t('營中發生奪權，原有主導者已被取代。','陣営で政変が起き、それまでの指導者が退けられました。')],['subject',c.t('軍政由我接掌，諸部聽令。','これより軍政を掌握する。各部隊は命に従え。')]],
  faction_coup_skipped:c=>[['messenger',c.t('原定奪權的條件已不成立。','政変の実行条件がそろいませんでした。')],['clerk',c.t('人物仍按現有戰局處置，未另行發動政變。','人物は現在の戦況に従い、別途の政変は起こしていません。')]],
  city_founded:c=>[['messenger',c.t(`${c.place}的新城建置已完成。`,`${c.place}の新しい都市が開設されました。`)],['clerk',c.t('城中人員與資源已列冊，請核對後再定部署。','都市の人員と資源を記録しました。ご確認のうえ配置をご指示ください。')]],
  city_captured:c=>[['messenger',c.t(`${c.place}已易主，城內情勢呈上。`,`${c.place}の支配が変わりました。都市の状況をご報告します。`)],['clerk',c.t('請核對守軍與庫存，安排後續防務。','守備隊と在庫を確認し、次の守備を整えましょう。')]],
  city_upgraded:c=>[['clerk',c.t(`${c.place}的都市規模已擴大。`,`${c.place}の都市規模が拡大しました。`)],['messenger',c.t('新規模的月收入已列明，請據此安排支出。','新しい規模の月収を記しました。今後の支出計画にご参照ください。')]],
  city_renamed:c=>[['clerk',c.t('年代已至，這一地圖節點的顯示城名依設定切換。','年代の境界に達し、この地図拠点の表示名が設定どおり切り替わりました。')],['messenger',c.t('現有歸屬與駐軍照舊列冊，詳情請閱史實背景。','現在の支配と駐屯を引き継いで記録しました。史実との関係は下の説明をご覧ください。')]],
  battle_started:c=>[['subject',c.t('敵我已接戰，諸隊依地形布置。','敵味方が交戦した。各隊、地形を見て布陣せよ。')],['other',c.t('戰陣已開，且看各自的本領。','戦いは始まった。互いの力を試そう。')]],
  battle_result:c=>[['messenger',c.t('戰鬥已分結果，兵損與歸降名冊在此。','戦闘の結果が出ました。損失と降伏の記録はこちらです。')],['clerk',c.t('請依戰果安排留守與後續行動。','戦果に従い、守備と次の行動を整えましょう。')]],
  duel_started:c=>[['subject',c.t('可敢與我一決高下？','我と勝負する覚悟はあるか。')],['other',c.t('既已應戰，便以手中兵刃見分曉！','勝負は受けた。この得物で決着をつけよう！')]],
  duel_result:c=>[['messenger',c.t('兩將交鋒已止，結果已呈報。','両将の打ち合いが終わりました。結果をご報告します。')],['clerk',c.t('體力與去留請按本次結果核對。','体力と戦場への残留は、今回の結果をご確認ください。')]],
  tactic:(c,d)=>[['subject',c.t('照此計行事，諸隊配合！','この計に従え。各隊、呼応せよ！')],['messenger',d.success===false?c.t('此計未能奏效，請另擇良策。','この計は効果を上げませんでした。次の策をご検討ください。'):c.t('計略已施行，實際成效請察看戰陣。','計略を実行しました。実際の効果は戦場をご確認ください。')]],
  march_weather:c=>[['messenger',c.t('行軍途中遇險，請核對各隊損失。','行軍中に災害が起きました。各隊の損失をご確認ください。')],['subject',c.t('清點各隊，依現有兵糧與兵力再作進退。','各隊を点呼し、残る兵糧と兵力を見て進退を決めよう。')]],
  route_discovered:c=>[['messenger',c.t('探索船隊已抵達，這條航路可以記入地圖了。','探索の船隊が到着しました。この航路を地図に記せます。')],['clerk',c.t('新航路已列入，往後仍須按實際日數與風險行走。','航路を登録しました。今後も実際の日数と危険に従って航行します。')]],
  march_arrived:c=>[['subject',c.t(`已抵達${c.place}，請核對接收與駐防。`,`${c.place}に到着しました。受け入れと守備をご確認ください。`)],['clerk',c.t('人員與物資按抵達時的城池狀態辦理。','武将と物資は、到着時の都市の状態に従って扱います。')]],
  march_returned:c=>[['messenger',c.t('原行軍已折返或取消，現況呈上。','元の行軍は帰還または中止となりました。現状をご報告します。')],['clerk',c.t('請核對人員實際位置，勿按原抵達計畫調兵。','武将の実際の位置を確認し、元の到着予定に基づく配置を見直しましょう。')]],
  march_resupplied:c=>[['steward',c.t('兵糧已實際交付，隨軍補給已入帳。','兵糧の引き渡しを終え、携行分に記録しました。')],['messenger',c.t('請按補給後的存量安排前進或等候。','補給後の在庫に従い、前進か待機をご指示ください。')]],
  march_starvation:c=>[['messenger',c.t('軍中兵糧不足，已發生缺糧減員。','軍中の兵糧が不足し、飢餓による損耗が出ています。')],['steward',c.t('請安排途中補給，現有存量與損失均在下方。','途中補給をご手配ください。残量と損失は下に記しました。')]],
  march_retreat:c=>[['messenger',c.t('部隊補給或道路有變，撤退狀況呈上。','部隊の補給または経路に変化があり、撤退の状況をご報告します。')],['clerk',c.t('請按實際去向安排接應，返程仍須行走。','実際の行き先に合わせて受け入れをご手配ください。帰還にも移動が必要です。')]],
  new_year:c=>[['clerk',c.t('歲序更新，人物年代與各城收支已核對。','年が改まり、武将の年代と各都市の収支を確認しました。')],['messenger',c.t('請察看新的名冊與疆界，再定今年方略。','新しい名簿と支配域を確かめ、本年の方針をご指示ください。')]],
  campaign_victory:c=>[['messenger',c.t('天下諸城已歸一統！','天下の諸都市が一つにまとまりました！')],['clerk',c.t('戰役結果已列冊，可保存這次進程。','戦役の結果を記録しました。この進行状況を保存できます。')]],
  campaign_defeat:c=>[['messenger',c.t('本方已無法繼續這場戰役。','我が勢力は、この戦役を続けられなくなりました。')],['clerk',c.t('結果仍可保存，亦可另選劇本再起。','結果は保存できます。別のシナリオで再び始めることもできます。')]],
  ai_campaign:c=>[['messenger',c.t('敵軍已擬定以我方城池為目標的進軍計畫，預定來源與會合期呈上。','敵軍が我らの都市を目標とする進軍計画を立てました。予定の出発地と合流時期をご報告します。')],['clerk',c.t('計畫不代表各隊均已出發；請核對在途部隊，預備守軍與補給。','計画の作成だけでは全隊の出発を意味しません。行軍中の部隊を確認し、守備と補給を整えましょう。')]],
  equipment_acquired:c=>[['target',c.t('此件武具已收入本人裝備，當善加運用。','この武具を自らの装備に収めました。使いこなしてみせましょう。')],['steward',c.t('持有人與取得方式已記明，並無重複添置。','所持者と入手方法を記しました。重複して追加していません。')]],
  town_developed:c=>[['actor',c.t('城町發展之事已辦妥，請查驗新設施。','町の発展を終えました。利用できる施設をご確認ください。')],['clerk',c.t('所需金錢已支付，新等級已入冊。','費用を支払い、新しい段階を記録しました。')]],
  officer_treated:c=>[['doctor',c.t('療治已畢，恢復情況請見下方。','治療を終えました。回復の結果は下をご覧ください。')],['target',c.t('有勞醫者，我會按目前體力安排軍務。','お世話になりました。今の体力に合わせて軍務にあたります。')]],
  officer_studied:c=>[['teacher',c.t('此次修學已畢，所學當用於實務。','今回の学びを終えました。得た知識を実務にお役立てください。')],['target',c.t('謹記教誨，願以所學報效。','教えを胸に、学んだことを役立てましょう。')]],
  grain_traded:c=>[['actor',c.t('依此次報價完成兵糧交易。','今回の相場に従い、兵糧の取引を終えました。')],['merchant',c.t('錢糧當面交割，數目在下方，請查點。','代金と兵糧を引き渡しました。下の数量をお確かめください。')]],
  equipment_bought:c=>[['merchant',c.t('所購武具已交付，請查驗。','お買い上げの武具をお渡しします。お確かめください。')],['target',c.t('武具已收妥，當依其長處運用。','確かに受け取りました。この武具の長所を活かしましょう。')]],
  prevention_improved:c=>[['actor',c.t('已完成本次防災整備與修繕。','今回の防災整備と修繕を終えました。')],['clerk',c.t('費用與整備成果已列明，請察看城況。','費用と整備の結果を記しました。都市の状態をご確認ください。')]],
  city_disaster:c=>[['messenger',c.t(`${c.place}遇災，損失數目在此。`,`${c.place}で災害が起きました。損失の記録はこちらです。`)],['clerk',c.t('按實際防災與庫存結算，請安排後續修整。','実際の防災と在庫に従い処理しました。今後の修繕をご手配ください。')]],
  treasure_found:c=>[['actor',c.t('此次尋訪有所得，已尋得寶物。','今回の探索で、宝を見つけました。')],['steward',c.t('寶物已入庫，搜尋費用亦已入帳。','宝を倉庫に収め、探索費用も記帳しました。')]],
  treasure_search_failed:c=>[['actor',c.t('四處尋訪，此番尚未尋得寶物。','各所を探しましたが、今回は宝を見つけられませんでした。')],['steward',c.t('搜尋費用已記錄，庫中未另添寶物。','探索費用を記録しました。倉庫の宝は増えていません。')]],
  treasure_sold:c=>[['actor',c.t('已依此次數量售出庫中寶物。','今回の指定数量に従い、倉庫の宝を売却しました。')],['merchant',c.t('寶物收妥，價金已交付，請查點。','宝を受け取り、代金をお渡ししました。お確かめください。')]],
  officer_rewarded:c=>[['actor',c.t('此份賞賜，願卿繼續盡力。','この褒美を受け取り、今後も力を尽くしてほしい。')],['target',c.t('承蒙厚賜，謹領此意。','ありがたき褒美、そのお心を受け止めます。')]],
  governor_assigned:c=>[['clerk',c.t('太守任用方式已登記。','太守の任用方法を登録しました。')],['governor',c.t('當按目前任用安排，照管城中事務。','現在の任用に従い、都市の務めを担当します。')]],
  staff_candidate:c=>[['staff',c.t('願在此城任事，請予考察。','この都市で働きたく存じます。ご検討ください。')],['clerk',c.t('已列為候選，是否雇用仍待確認。','候補として記しました。採用には確認が必要です。')]],
  staff_hired:c=>[['clerk',c.t('雇用手續已妥，職事與俸給照名冊辦理。','採用の手続きを終えました。務めと俸給は名簿に従います。')],['staff',c.t('承蒙錄用，願盡力任事。','採用いただき、力を尽くして働きます。')]],
  staff_declined:c=>[['clerk',c.t('此次未能錄用，還請見諒。','このたびは採用を見送ります。ご了承ください。')],['staff',c.t('既如此，我便另尋去處。','承知しました。別の勤め先を探しましょう。')]],
  staff_expired:c=>[['messenger',c.t('這位文吏的候選資格已撤回。','この文官の候補資格が取り下げられました。')],['clerk',c.t('未另行雇用或扣款，撤回原因已記明。','別途の採用や支払いはなく、理由を記録しました。')]],
  staff_salary:c=>[['clerk',c.t('本月文吏俸給與工作成果已列明。','今月の文官の俸給と業務成果をまとめました。')],['steward',c.t('應付與實付金額均有記錄，請察看欠薪情況。','支払予定額と実額を記録しました。未払いの状況をご確認ください。')]],
  staff_allegiance:c=>[['messenger',c.t('城池所屬已有變動，留任名冊呈上。','都市の所属が変わりました。留任者の名簿をお届けします。')],['staff',c.t('我仍留在本城，照目前歸屬辦理地方事務。','この都市に留まり、現在の所属に従って地方の務めを続けます。')]],
  domestic_report:c=>[['clerk',c.t('所委內政已結算，本次收支與成果呈上。','担当の内政を処理しました。今回の収支と成果をご報告します。')],['steward',c.t('帳冊已按實際支出與入庫核對。','実際の支出と入庫に照らし、帳簿を確認しました。')]],
  transport_departed:c=>[['steward',c.t('貨物已點清，運輸隊正式出發。','荷の点検を終え、輸送隊が出発しました。')],['messenger',c.t('途中仍須行走，抵達或交付後再報成果。','経路を進み、到着または引き渡し後に結果をご報告します。')]],
  transport_arrived:c=>[['messenger',c.t('運輸隊已抵達，請接收現存貨物。','輸送隊が到着しました。残る荷をお受け取りください。')],['steward',c.t('已按實際貨物完成交付。','実際の荷を確認し、引き渡しを終えました。')]],
  transport_returned:c=>[['messenger',c.t('運輸任務或返程狀態已有變化。','輸送任務または帰路の状況が変わりました。')],['steward',c.t('貨物按實際位置保管，請核對本次去向。','荷は実際の所在地で保管します。今回の行き先をご確認ください。')]],
  transport_weather:c=>[['messenger',c.t('運輸途中遇險，請核對人員與貨物損失。','輸送中に災害に遭いました。人員と荷の損失をご確認ください。')],['steward',c.t('現存貨物已點清，損失不重複記帳。','残る荷を確認しました。同じ損失を重ねて計上しません。')]]
 };
 function event(row,view,language='zh-Hant',i18n){
  if(!row||!Object.hasOwn(EVENTS,row.kind))return [];
  const c=context(view,language,i18n),d=row.details||{},ids=row.person_ids||[];
  const subjectId=row.kind==='faction_coup'?ids.at(-1):ids[0]??(row.kind==='campaign_start'?view?.game?.extension?.leaders?.[row.factions?.[0]||view?.game?.player]:null);
  const subject=c.person(subjectId),actor=c.person(d.actor),target=c.person(d.target||ids[0]),other=c.person(ids[1]);
  const speakers={subject,actor,target,other,governor:d.governor?c.person(d.governor):c.role('clerk'),staff:c.person(d.staff_id,'clerk',d),...Object.fromEntries(Object.keys(ROLES).map(key=>[key,c.role(key)]))};
  Object.assign(c,{subject,place:(row.city_ids||[]).map(c.city).join(' → ')||c.t('戰役各地','各地')});
  return EVENTS[row.kind](c,d).map(([who,text])=>({...speakers[who],text}));
 }
 const COMMANDS=Object.freeze({new:'event',persuade_officer:'event',recruit_officer:'event',transfer:'inline',tactic:'inline',duel_start:'inline',duel_action:'inline',allocate:'inline',allocation_close:'silent',recruit:'inline',depart:'inline',attack:'inline',battle_move:'inline',battle_wait:'inline',battle_facility:'inline',retreat:'inline',settle:'event',end_turn:'inline',ai:'silent',arrivals:'silent',siege_form:'inline',siege_orders:'inline',siege_step:'inline',siege_withdraw:'inline',hire_staff:'event',reject_staff:'event',staff_recruit:'event',choose_successor:'event',set_domestic:'inline',set_logistics:'inline',dispatch_transport:'event',search_treasure:'event',reward_officer:'event',sell_treasure:'event',set_governor:'event',set_treasury_policy:'inline',develop_town:'event',treat_officer:'event',study_officer:'event',trade_grain:'event',buy_equipment:'event',improve_prevention:'event',set_facility_policy:'inline',equip_owned:'event'});
 const ACTION_NAMES={new:['開始戰役','戦役開始'],persuade_officer:['勸降','引き抜き'],recruit_officer:['登用','登用'],transfer:['調動','移動'],tactic:['施放計略','計略の使用'],duel_start:['挑戰單挑','一騎討ちの挑戦'],duel_action:['單挑行動','一騎討ちの行動'],allocate:['編兵','兵の編制'],recruit:['徵募預備兵','予備兵の募兵'],depart:['出征','出陣'],attack:['攻擊','攻撃'],battle_move:['戰術移動','戦術移動'],battle_wait:['結束本方行動','自軍の行動終了'],battle_facility:['使用戰場設施','戦場施設の利用'],retreat:['撤退','撤退'],settle:['戰果結算','戦果の精算'],end_turn:['結束本旬','今旬の終了'],siege_form:['選擇陣形','陣形の選択'],siege_orders:['下達交鋒命令','交戦命令の指定'],siege_step:['推進交鋒','交戦の進行'],siege_withdraw:['退出交鋒','交戦からの離脱'],hire_staff:['雇用文吏','文官の採用'],reject_staff:['婉拒文吏','文官の採用見送り'],staff_recruit:['文吏尋訪','文官による登用'],choose_successor:['選擇繼承者','後継者の選択'],set_domestic:['內政委任','内政の担当'],set_logistics:['運輸方針','輸送の方針'],dispatch_transport:['派出運輸隊','輸送隊の派遣'],search_treasure:['尋寶','宝の探索'],reward_officer:['賞賜','褒美'],sell_treasure:['出售寶物','宝の売却'],set_governor:['任命太守','太守の任命'],set_treasury_policy:['寶庫方針','宝庫の方針'],develop_town:['發展城町','町の発展'],treat_officer:['療傷','治療'],study_officer:['修學','学習'],trade_grain:['交易兵糧','兵糧の取引'],buy_equipment:['購買武具','武具の購入'],improve_prevention:['防災整備','防災整備'],set_facility_policy:['設施方針','施設の方針'],equip_owned:['裝備備用武具','予備武具の装備']};
 function freshEvents(before,after){const floor=before?.game?.extension?.events?.next_id||1;return (after?.game?.extension?.events?.items||[]).filter(row=>row.id>=floor);}
 function command(kind,payload={},before,after,{language='zh-Hant',i18n,error=null}={}){
  if(!Object.hasOwn(COMMANDS,kind))return [];
  const c=context(after||before,language,i18n),prior=context(before,language,i18n),action=pick(language,...(ACTION_NAMES[kind]||['操作','操作']));
  const duel=kind==='duel_action'?before?.game?.battle?.extended?.duel:null,encounter=kind.startsWith('siege_')?before?.game?.battle?.extended?.siege:null;
  const actor=prior.person(payload.actor??payload.officer??payload.officers?.[0]??duel?.actor??encounter?.actor),target=prior.person(payload.target??duel?.target??encounter?.target),leader=prior.person(before?.game?.extension?.leaders?.[before?.game?.player],'ruler');
  const line=(speaker,text)=>({...speaker,text}),reply=text=>[line(leader,c.t(`${action}之事，請照此辦理。`,`${action}を、この指定で進めてほしい。`)),line(actor,text)];
  if(error)return [line(actor,c.t(`請示${action}。`,`${action}を願い出ます。`)),line(c.role('clerk'),c.t(`此次未能執行：${c.tr(error)}`,`今回は実行できません：${c.tr(error)}`))];
  if(COMMANDS[kind]==='silent'||COMMANDS[kind]==='event')return [];
  const receipt=after?.presentation,scenes=receipt?.revision===after?.revision&&Array.isArray(receipt.scenes)?receipt.scenes:[];
  const scene=scenes.find(row=>row.kind===({tactic:'tactic',duel_start:'duel_start',duel_action:'duel_action',attack:'attack',battle_move:'move'}[kind])&&String(row.actor)===String(payload.actor))||null;
  if(kind==='duel_start'){
   const refused=scene?.success===false,accepted=scene?.success===true||!!after?.game?.battle?.extended?.duel;
   return [line(actor,c.t('可敢與我一決高下？','我と勝負する覚悟はあるか。')),line(target,refused?c.t('今日不與你爭這匹夫之勇。','今はその勝負に付き合うつもりはない。'):accepted?c.t('既然相邀，便來一戰！','その勝負、受けて立とう！'):c.t('此次挑戰已處理，請察看戰場現況。','今回の挑戦を処理しました。戦場の現状をご確認ください。'))];
  }
  if(kind==='tactic'){
   const row=freshEvents(before,after).find(e=>e.kind==='tactic'&&e.details?.actor===actor.personId)||freshEvents(before,after).find(e=>e.kind==='tactic');
   const success=scene?scene.success:row?.details?.success;
   return [line(actor,c.t('依此計行事，諸隊配合！','この計に従え。各隊、呼応せよ！')),line(c.role('messenger'),success===false?c.t('此計未能奏效，請另擇良策。','この計は効果を上げませんでした。次の策をご検討ください。'):c.t('計略已執行，實際成效請察看戰場。','計略を実行しました。実際の効果は戦場をご確認ください。'))];
  }
  if(kind==='attack')return [line(actor,c.t('向敵軍進擊！','敵へ攻めかかれ！')),line(c.role('messenger'),c.t('接戰已處理，傷亡與位置請見戰場。','交戦を処理しました。損害と位置は戦場をご確認ください。'))];
  if(kind==='battle_move')return [line(actor,c.t('各隊隨我轉進，留意地勢。','各隊、我に続け。地形に気を配れ。')),line(c.role('messenger'),c.t('移動已處理，現有位置與機動力已更新。','移動を処理しました。現在地と機動力を更新しています。'))];
  if(kind==='duel_action'){
   const moves={strike:['接我一擊！','この一撃を受けよ！'],guard:['穩住架勢，先守住此招。','構えを保ち、この一手を防ごう。'],feint:['且試探對手的破綻。','相手の隙を探ってみよう。'],desperate:['全力一搏！','全力で勝負する！'],withdraw:['收住兵刃，尋機退下。','得物を引き、退く機を探ろう。']};
   return [line(actor,c.t(...(moves[payload.move]||['依所選招式應對。','選んだ技で応じよう。']))),line(c.role('messenger'),c.t('本合交鋒已處理，體力與勝負請見戰場。','この打ち合いを処理しました。体力と勝敗は戦場をご確認ください。'))];
  }
  if(kind==='battle_wait')return [line(c.role('officer'),c.t('本方暫止行動，各隊戒備。','自軍の行動を終える。各隊、警戒せよ。')),line(c.role('messenger'),c.t('已處理換方，請留意敵軍動向。','手番の交代を処理しました。敵の動きにご注意ください。'))];
  if(kind==='depart'||kind==='transfer'){
   const previous=new Set((before?.game?.extension?.travel?.marches||[]).map(row=>row.id)),march=(after?.game?.extension?.travel?.marches||[]).find(row=>!previous.has(row.id)&&row.source===payload.source&&row.target===payload.target);
   return [line(leader,c.t(`率所選諸將前往${c.city(payload.target)}。`,`選んだ諸将を率い、${c.city(payload.target)}へ向かえ。`)),line(actor,march?c.t('已奉命出發，按所選路線行軍；抵達時再報。','出発しました。選択した経路を進み、到着時にご報告します。'):c.t('命令已執行，請按目前部隊狀態調度。','命令を実行しました。現在の部隊状況に従ってご指示ください。'))];
  }
  if(kind==='recruit'){
   const id=payload.city,a=before?.game?.cities?.[id]?.reserves,b=after?.game?.cities?.[id]?.reserves;
   return reply(Number.isSafeInteger(a)&&Number.isSafeInteger(b)?c.t(`徵募已辦妥，本城預備兵由${a}增為${b}。`,`募兵を終えました。この都市の予備兵は${a}から${b}になりました。`):c.t('徵募已辦妥，名冊已更新。','募兵を終え、名簿を更新しました。'));
  }
  if(kind==='allocate'){
   const rows=Array.isArray(payload.allocations)?payload.allocations:[{officer:payload.officer}],changed=rows.filter(row=>before?.game?.officers?.[String(row.officer)]?.troops!==after?.game?.officers?.[String(row.officer)]?.troops).length;
   return reply(changed?c.t(`已按確認名單完成${changed}名武將的編兵。`,`確定した名簿に従い、${changed}名の武将の兵を編制しました。`):c.t('編兵數目未變，仍按目前名冊。','兵数に変更はありません。現在の名簿のままです。'));
  }
  if(kind.startsWith('set_'))return [line(leader,c.t('依此次選定的分工與方針辦理。','今回選んだ担当と方針に従って進めよ。')),line(c.role('clerk'),c.t(`${action}已登記，日後按實際條件執行。`,`${action}を登録しました。以後、実際の条件に従って実行します。`))];
  if(kind==='end_turn')return [line(leader,c.t('本旬部署既定，諸部依令行事。','今旬の配置は定まった。各部、命に従え。')),line(c.role('clerk'),c.t('本旬已交付處理，後續動向仍按實際進程。','今旬の処理へ進めました。以後の動きは実際の進行に従います。'))];
  if(kind==='battle_facility')return [line(actor,c.t('請依此次選項辦理。','今回の指定でお願いしたい。')),line(c.role(payload.action==='treat'?'doctor':'merchant'),c.t('手續已辦妥，費用與成效請見目前戰場。','手続きを終えました。費用と結果は現在の戦場をご確認ください。'))];
  if(kind==='retreat'||kind==='siege_withdraw')return [line(actor,c.t('諸隊收攏，依令退下。','各隊、まとまって退け。')),line(c.role('messenger'),c.t('撤退命令已執行，請察看目前戰況。','撤退の命令を実行しました。現在の戦況をご確認ください。'))];
  const replies={siege_form:['陣形已確定，請下達各隊命令。','陣形を確定しました。各隊の命令をご指定ください。'],siege_orders:['各隊命令已記錄，待推進交鋒。','各隊の命令を記録しました。交戦の進行をお待ちします。'],siege_step:['本巡交鋒已處理，請依現況再定進退。','この巡の交戦を処理しました。現状に合わせて進退をご指示ください。']};
  return reply(pick(language,...replies[kind]));
 }
 function relation(view,id,language='zh-Hant'){
  const row=view?.catalog?.officer_relations?.officers?.[String(id)];
  if(!row||typeof row.reason?.[language==='ja'?'ja':'zh']!=='string')return '';
  const reason=row.reason[language==='ja'?'ja':'zh'],loyalty=view?.game?.officers?.[String(id)]?.loyalty;
  const basis=row.blocked?pick(language,'；此為例外關係，不套用親緣或信任的任用忠誠基準','。例外関係のため、親族・信頼による任用時の忠誠基準は適用しません'):Number.isSafeInteger(row.floor)?pick(language,`；任用忠誠基準${row.floor}`,`。任用時の忠誠基準${row.floor}`):'';
  const current=Number.isSafeInteger(loyalty)?pick(language,`；目前忠誠${loyalty}`,`。現在の忠誠${loyalty}`):'';
  const lower=!row.blocked&&Number.isSafeInteger(loyalty)&&Number.isSafeInteger(row.floor)&&loyalty<row.floor?pick(language,'。目前數值低於基準，顯示依據不會改寫既有進度','。現在値は基準を下回ります。この説明の表示で既存の進行状況は書き換えません'):'';
  return pick(language,`與目前君主的關係依據：${reason}${basis}${current}${lower}。`,`現在の君主との関係の根拠：${reason}${basis}${current}${lower}。`);
 }
 function guidance(kind,payload,view,language='zh-Hant',i18n){
  if(!['recruit_officer','persuade_officer'].includes(kind))return [];
  const c=context(view,language,i18n),actor=c.person(payload.actor),target=c.person(payload.officer);
  return [{...actor,text:kind==='persuade_officer'?c.t('此番前往勸說，對方是否轉屬須待本人答覆。','引き抜きの説得に向かいます。移籍の意思は本人の返答を待ちます。'):c.t('此番尋訪，願請此人出仕；尚未提交前不作結果。','この人物を訪ね、仕官を願います。確定するまでは結果は決まりません。')},{...target,text:c.t('是否應允，待正式相詢後再答。','お受けするかは、正式なお話を伺ってからお答えします。')}];
 }
 function html(lines,{language='zh-Hant',portraits=root.GamePortraits,compact=false}={}){
  if(!Array.isArray(lines)||!lines.length)return '';
  return `<div class="dialogue-exchange${compact?' dialogue-compact':''}" data-dialogue-exchange data-l10n-native="${language==='ja'?'ja':'zh-Hant'}">${lines.map(line=>{
   const face=line.portrait&&portraits?.civilHtml?portraits.civilHtml(line.portrait,line.name):line.personId&&portraits?.html?portraits.html(line.personId,line.name,{size:'battle'}):`<span class="dialogue-role" aria-hidden="true">${escape(line.name?.slice(0,1)||'吏')}</span>`;
   return `<div class="dialogue-turn"${line.personId?` data-dialogue-person="${escape(line.personId)}"`:''}><div class="dialogue-face">${face}</div><div class="dialogue-words"><p class="dialogue-speaker">${escape(line.name)}</p><p>${escape(line.text)}</p></div></div>`;
  }).join('')}</div>`;
 }
 const api={event,command,guidance,relation,html,EVENT_KINDS:Object.freeze(Object.keys(EVENTS)),COMMANDS};
 if(typeof module==='object'&&module.exports)module.exports=api;else root.GameDialogue=api;
})(typeof window==='object'?window:globalThis);
