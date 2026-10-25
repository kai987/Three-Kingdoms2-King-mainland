# 史実シナリオの勢力・境界都市レビュー（2026年10月25日）

現在の史実23本を対象に、地方勢力、都市の初期所属と武将配置を確認する資料です。仮想6本は領土修正の対象から外します。地域単位の史料を現在の地図へ対応させたレビューであり、**すべての都市・すべての月の太守名簿が確定したという意味ではありません**。

生成元は [レビュー決定表](../game/config/references/scenario-history-review.json)、照合結果は [全都市・境界経路・人物のJSON](scenario-history-audit-20261025.json)です。同じ人物を一度の修正で複数回動かした場合は最後の記録を採用し、都市は最終的な `owner_expectations` と照合します。

今回の記録は追加勢力26件（シナリオごとの組合せ）、都市延べ88件（最終の都市・シナリオ単位87件）、人物延べ444件（同一シナリオ内の重複整理後444件）です。全都市一覧は変更対象以外も含みますが、変更のない都市を新たに逐月確証した件数とは数えません。

## 対象と判定の意味

| 区分 | 扱い |
| --- | --- |
| 史料 | 原典で確認できる所属・出来事。年が分かっても月や旬まで分かるとは限りません。 |
| 演義 | 『三國演義』や既存ゲームの人物関係を遊びのため残したもの。正史の駐将名簿とは区別します。 |
| 地域代理・本作配置 | 郡・地域の記録を固定都市へ写したものや、史料にない具体的駐防。 |
| 待考 | 実効支配や移管月が未確定。中立表示も無人や人口ゼロを意味しません。 |

207年の章陵を劉備に残す指定、208年8月を章陵帰曹の境界とする指定、小沛／譙郡の地域代理など、従来の明示されたゲーム設定は維持します。変更は新しい戦役の開始時に適用し、プレイ中の領土を史実へ強制的に戻しません。

## 23本の開幕勢力

| 開始年月 | シナリオ | 勢力の君主（本拠） | 都市／境界接続 | 今回の修正件数 |
| --- | --- | --- | --- | --- |
| 184年2月 | 184年2月 · 黄巾之乱 | 丁原（晉陽）、董卓（天水）、公孫瓚（漁陽）、何進（洛陽）、劉焉（薊）、馬騰（姑臧）、士燮（交趾）、宋建（枹罕）、孫堅（下邳）、張角（平原） | 108／64 | 勢力1・都市1・人物1 |
| 188年6月 | 揺らぐ漢朝 | 丁原（晉陽）、董卓（天水）、何進（洛陽）、韓遂（金城）、劉焉（成都）、劉虞（薊）、士燮（交趾）、孫堅（長沙）、張純（遼西） | 108／56 | 勢力1・都市1・人物7 |
| 190年1月 | 190年1月 · 反董卓联盟 | 鮑信（東平）、董卓（洛陽）、公孫度（襄平）、公孫瓚（漁陽）、韓馥（鄴）、韓遂（金城）、孔融（北海）、孔伷（許縣）、劉表（襄陽）、劉岱（濟陰）、劉焉（成都）、劉虞（薊）、馬騰（姑臧）、橋瑁（濮陽）、士燮（交趾）、劉備（平原）、孫堅（長沙）、陶謙（下邳）、王匡（河內）、曹操（陳留）、袁紹（南皮）、袁術（宛城）、袁遺（昌邑）、張超（東海）、張楊（上黨） | 108／93 | 勢力6・都市9・人物30 |
| 191年10月 | 191年10月 · 二袁的意图 | 鮑信（東平）、董卓（長安）、公孫度（襄平）、公孫瓚（漁陽）、韓遂（金城）、孔融（北海）、劉表（襄陽）、劉岱（濟陰）、劉焉（成都）、劉虞（薊）、馬騰（姑臧）、士燮（交趾）、劉備（平原）、孫堅（長沙）、陶謙（下邳）、曹操（濮陽）、袁紹（鄴）、袁術（宛城）、袁遺（昌邑）、張超（東海）、張邈（陳留）、張楊（河內） | 108／88 | 勢力4・都市7・人物50 |
| 194年6月 | 194年6月 · 群雄割据 | 公孫度（襄平）、公孫瓚（漁陽）、韓遂（金城）、孔融（北海）、李傕（長安）、劉表（襄陽）、劉繇（秣陵）、劉璋（成都）、呂布（濮陽）、馬騰（姑臧）、士燮（交趾）、劉備（小沛）、陶謙（下邳）、王朗（山陰）、曹操（鄄城）、許貢（吳）、袁紹（鄴）、袁術（壽春）、張魯（漢中）、張楊（河內） | 108／98 | 勢力2・都市6・人物32 |
| 196年6月 | 曹操の台頭 | 公孫度（襄平）、公孫瓚（漁陽）、韓遂（金城）、華歆（南昌）、孔融（北海）、李傕（長安）、劉表（襄陽）、劉繇（鄱陽）、劉璋（成都）、呂布（小沛）、馬騰（姑臧）、士燮（交趾）、劉備（下邳）、王朗（山陰）、曹操（陳留）、孫策（秣陵）、袁紹（鄴）、袁術（壽春）、張魯（漢中）、張楊（河內） | 108／99 | 勢力2・都市6・人物16 |
| 198年3月 | 呂布討伐戦 | 公孫度（襄平）、公孫瓚（漁陽）、韓遂（金城）、華歆（南昌）、李傕（長安）、劉表（襄陽）、劉璋（成都）、呂布（下邳）、馬騰（姑臧）、士燮（交趾）、劉備（小沛）、曹操（許縣）、孫策（秣陵）、袁紹（鄴）、袁術（壽春）、張魯（漢中）、張繡（宛城）、張楊（河內） | 108／94 | 勢力1・都市3・人物8 |
| 200年1月 | 200年1月 · 官渡之战 | 公孫度（襄平）、韓遂（金城）、劉表（襄陽）、劉璋（成都）、馬騰（姑臧）、士燮（交趾）、劉備（下邳）、曹操（許縣）、孫策（吳）、袁紹（鄴）、張魯（漢中） | 108／69 | 勢力1・都市9・人物28 |
| 202年6月 | 河北争乱 | 高幹（晉陽）、公孫度（襄平）、韓遂（金城）、劉表（襄陽）、劉璋（成都）、馬騰（姑臧）、士燮（交趾）、劉備（章陵）、曹操（許縣）、孫權（吳）、袁尚（鄴）、袁譚（北海）、袁熙（薊）、張魯（漢中） | 108／79 | 勢力1・都市9・人物26 |
| 207年9月 | 207年9月 · 三顾茅庐 | 公孫康（襄平）、韓遂（金城）、劉表（襄陽）、劉璋（成都）、馬騰（姑臧）、士燮（交趾）、劉備（章陵）、曹操（鄴）、孫權（吳）、吳巨（蒼梧）、張魯（漢中） | 108／61 | 勢力2・都市9・人物63 |
| 208年10月 | 208年10月 · 赤壁之战 | 公孫康（襄平）、韓遂（金城）、韓玄（長沙）、金旋（武陵）、劉度（零陵）、劉璋（成都）、馬超（姑臧）、士燮（交趾）、劉備（江夏）、曹操（鄴）、孫權（吳）、吳巨（蒼梧）、張魯（漢中）、趙範（桂陽） | 109／67 | 勢力2・都市9・人物65 |
| 211年7月 | 潼関の戦い | 公孫康（襄平）、韓遂（金城）、劉璋（成都）、馬超（姑臧）、士燮（交趾）、劉備（江陵）、曹操（鄴）、孫權（吳）、張魯（漢中） | 109／55 | 勢力1・都市4・人物29 |
| 212年12月 | 入蜀争奪戦 | 公孫康（襄平）、韓遂（金城）、劉璋（成都）、士燮（交趾）、劉備（涪縣）、曹操（鄴）、孫權（建業）、張魯（漢中） | 109／52 | 勢力1・都市10・人物79 |
| 215年8月 | 合肥の戦い | 公孫康（襄平）、士燮（交趾）、劉備（成都）、曹操（鄴）、孫權（建業） | 110／32 | 勢力0・都市0・人物0 |
| 217年7月 | 217年7月 · 汉中争夺战 | 公孫恭（襄平）、士燮（交趾）、劉備（成都）、曹操（鄴）、孫權（建業） | 110／32 | 勢力0・都市0・人物0 |
| 219年7月 | 219年7月 · 关羽包围网 | 公孫恭（襄平）、士燮（交趾）、劉備（成都）、曹操（鄴）、孫權（建業） | 110／32 | 勢力0・都市0・人物0 |
| 221年7月 | 221年7月 · 夷陵前夕 | 公孫恭（襄平）、士燮（交趾）、劉備（成都）、曹丕（洛陽）、孫權（武昌） | 111／32 | 勢力0・都市0・人物0 |
| 225年7月 | 南蛮征伐 | 公孫恭（襄平）、孟獲（建寧）、士燮（交趾）、劉禪（成都）、曹丕（洛陽）、孫權（武昌） | 111／37 | 勢力0・都市1・人物7 |
| 227年2月 | 227年2月 · 出师表 | 公孫恭（襄平）、劉禪（成都）、曹叡（洛陽）、孫權（武昌） | 111／29 | 勢力0・都市0・人物0 |
| 234年2月 | 秋風五丈原 | 公孫淵（襄平）、劉禪（成都）、曹叡（洛陽）、孫權（建業） | 111／25 | 勢力0・都市0・人物0 |
| 238年1月 | 238年1月 · 征讨辽东 | 公孫淵（襄平）、劉禪（成都）、曹叡（洛陽）、孫權（建業） | 111／25 | 勢力0・都市0・人物0 |
| 249年1月 | 249年1月 · 正始之变 | 劉禪（成都）、曹芳（洛陽）、孫權（建業） | 110／20 | 勢力0・都市0・人物0 |
| 263年5月 | 蜀漢の滅亡 | 呂興（交趾）、劉禪（成都）、曹奐（洛陽）、孫休（建業） | 113／23 | 勢力1・都市3・人物3 |

件数は本作データの変更記録です。同じ勢力を複数の年代に追加した場合は各開幕で1件と数えます。JSONは全開放都市の所有者、各勢力の全開幕武将、異なる所有者を結ぶ接続を収録します。境界接続は陸路・内河・海路の都市間隣接であり、行政区の境界線を復元したものではありません。

## 史料による所属・年代

### 188年6月・揺らぐ漢朝

- 都市 長沙 `changsha`：ou_xing → sun_jian。187年冬區星叛亂已被平定；188年6月長沙由太守孫堅掌理，區星不再列為開局勢力，史料未明言其本人被殺。 [史料1](https://zh.wikisource.org/zh-hant/資治通鑑/卷058)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷46)
- 人物 區星 `san14-candidate-0065`：開幕対象外／―。《資治通鑑》記187年冬十月孫堅任長沙太守並討平區星；188年6月不再列區星為開局勢力。此為失勢排除，並非認定史料已證其本人死亡。 [史料1](https://zh.wikisource.org/zh-hant/資治通鑑/卷058)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷46)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂金城部曲，保留188遊戲聯軍故事映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 孫堅 `san14-candidate-0551`：sun_jian／長沙。《資治通鑑》繫孫堅任長沙太守、討平區星於187年冬十月；188年6月以長沙為其郡治據點，名義仍屬漢廷。 [史料1](https://zh.wikisource.org/zh-hant/資治通鑑/卷058)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷46)

### 190年1月・190年1月 · 反董卓联盟

- 都市 濮陽 `dongjun`：liu_dai → qiao_mao。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 都市 河內 `henei`：zhang_yang → wang_kuang。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 都市 昌邑 `shanyang`：wei → yuan_yi。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 都市 許縣 `yingchuan`：neutral → kong_zhou。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 袁遺 `san14-candidate-0024`：yuan_yi／昌邑。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 王匡 `san14-candidate-0047`：wang_kuang／河內。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 橋瑁 `san14-candidate-0209`：qiao_mao／濮陽。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 孔伷 `san14-candidate-0270`：kong_zhou／許縣。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 張楊 `san14-candidate-0661`：zhang_yang／上黨。張楊上黨活動區域代理，190不提前領河內。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 鮑韜 `san14-candidate-0829`：bao_xin／東平。鮑信之弟隨軍；190年內戰死不代表正月已死亡。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)

### 191年10月・191年10月 · 二袁的意图

- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 曹操 `san14-candidate-0521`：wei／濮陽。191年曹操治東武陽；東郡節點為郡域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)

### 194年6月・194年6月 · 群雄割据

- 都市 陳留 `chenliu`：wei → lubu。194年夏張邈、陳宮迎呂布，兗州郡縣響應；陳留由張邈—呂布聯盟控制，不能再作曹操本據。本作合併表示為呂布勢力，不另立敵對張邈勢力。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 夏侯惇 `san14-candidate-0124`：wei／鄄城。《夏侯惇傳》《荀彧傳》記夏侯惇由濮陽輕軍救鄄城，呂布遂據濮陽；駐本作鄄城代理節點。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 荀彧 `san14-candidate-0393`：wei／鄄城。《荀彧傳》記荀彧守鄄城，與夏侯惇保全留守；194年6月駐本作鄄城代理節點，不留在已叛的陳留。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 張邈 `san14-candidate-0653`：lubu／陳留。陳留太守張邈194年夏與陳宮迎呂布；沿用既有呂布聯盟身份，配置於陳留，不改為曹操或新造勢力。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 陳宮 `san14-candidate-0671`：lubu／濮陽。陳宮194年夏率留屯東郡之眾迎呂布，呂布據濮陽；配置於東郡/濮陽節點，保持呂布勢力。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 程昱 `san14-candidate-0689`：wei／鄄城。程昱撫范、守東阿，助保鄄城、范、東阿三縣；本作將三縣防區合併在鄄城代理節點，不把范縣誤作整個東平國。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)

### 196年6月・曹操の台頭

- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 劉繇 `san14-candidate-0963`：liu_you／鄱陽。劉繇退彭澤，以鄱陽節點作明示地域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)

### 198年3月・呂布討伐戦

- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)

### 200年1月・200年1月 · 官渡之战

- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)

### 202年6月・河北争乱

- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)

### 207年9月・207年9月 · 三顾茅庐

- 都市 蒼梧 `cangwu`：wu → wu_ju。劉表遣吳巨領蒼梧；210/211步騭入交州事件以前保留地方勢力。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 黃忠 `san14-candidate-0271`：liu_biao／長沙。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國志/卷32)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 吳巨 `san14-candidate-0285`：wu_ju／蒼梧。劉表遣吳巨領蒼梧；210/211步騭入交州事件以前保留地方勢力。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 劉磐 `san14-candidate-0951`：liu_biao／長沙。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國志/卷32)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)

### 208年10月・208年10月 · 赤壁之战

- 都市 蒼梧 `cangwu`：wu → wu_ju。劉表遣吳巨領蒼梧；210/211步騭入交州事件以前保留地方勢力。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 吳巨 `san14-candidate-0285`：wu_ju／蒼梧。劉表遣吳巨領蒼梧；210/211步騭入交州事件以前保留地方勢力。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 馬超 `san14-candidate-0769`：ma_teng／姑臧。馬騰入朝後馬超承領部曲。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)

### 211年7月・潼関の戦い

- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)

### 212年12月・入蜀争奪戦

- 人物 韋康 `san14-candidate-0003`：wei／天水。採通鑑213年馬超攻冀口徑；卷25有建安十七年異文，列明采擇。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 閻行 `san14-candidate-0030`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 霍峻 `san14-candidate-0099`：shu／葭萌。劉備南還後留霍峻守葭萌。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 嚴顏 `san14-candidate-0231`：liu_zhang／江州。嚴顏仍為劉璋巴郡太守。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 成公英 `san14-candidate-0475`：han_sui／金城。韓遂腹心/部將，不因聯軍合從而當作馬騰普通部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 孫權 `san14-candidate-0553`：wu／建業。孫權211年徙治秣陵，212年改名建業。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 鄭度 `san14-candidate-0701`：liu_zhang／成都。劉璋從事，拒劉備獻策。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 劉備 `san14-candidate-0952`：shu／涪縣。212年十二月劉備進據涪城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)

## 演義・ゲーム互換の配置

### 207年9月・207年9月 · 三顾茅庐

- 人物 韓玄 `san14-candidate-0158`：liu_biao／長沙。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 魏延 `san14-candidate-0189`：liu_biao／長沙。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 鞏志 `san14-candidate-0204`：liu_biao／武陵。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 金旋 `san14-candidate-0223`：liu_biao／武陵。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 邢道榮 `san14-candidate-0228`：liu_biao／零陵。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 趙範 `san14-candidate-0654`：liu_biao／桂陽。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 陳應 `san14-candidate-0668`：liu_biao／桂陽。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 鮑隆 `san14-candidate-0831`：liu_biao／桂陽。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 劉賢 `san14-candidate-0934`：liu_biao／零陵。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 劉度 `san14-candidate-0949`：liu_biao／零陵。劉表荊南郡域駐點；四太守確任月不詳，演義人物採地域兼容配置，不提前獨立。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)

### 208年10月・208年10月 · 赤壁之战

- 人物 魏延 `san14-candidate-0189`：han_xuan／長沙。依《三國演義》52/53回補齊既有人物隸屬；屬演義兼容設定，不冒稱正史任所。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 鞏志 `san14-candidate-0204`：jin_xuan／武陵。依《三國演義》52/53回補齊既有人物隸屬；屬演義兼容設定，不冒稱正史任所。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 邢道榮 `san14-candidate-0228`：liu_du／零陵。依《三國演義》52/53回補齊既有人物隸屬；屬演義兼容設定，不冒稱正史任所。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 陳應 `san14-candidate-0668`：zhao_fan／桂陽。依《三國演義》52/53回補齊既有人物隸屬；屬演義兼容設定，不冒稱正史任所。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 鮑隆 `san14-candidate-0831`：zhao_fan／桂陽。依《三國演義》52/53回補齊既有人物隸屬；屬演義兼容設定，不冒稱正史任所。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)
- 人物 劉賢 `san14-candidate-0934`：liu_du／零陵。依《三國演義》52/53回補齊既有人物隸屬；屬演義兼容設定，不冒稱正史任所。 [史料1](https://zh.wikisource.org/wiki/三國演義/第052回)、[史料2](https://zh.wikisource.org/wiki/三國演義/第053回)

## 地域代理・本作の配置

### 184年2月・184年2月 · 黄巾之乱

- 都市 枹罕 `longxi`：neutral → song_jian。《三國志》卷01、09記宋建據枹罕三十餘年、214年十月被夏侯淵討滅，未載確切建國月；《後漢書》卷72將宋建參與涼州亂列於184年冬。本篇依使用者要求於184年2月提前登場，以隴西節點代理枹罕據點，並非聲稱當月已建立政權或占有整個隴西郡。原典的丞相、百官無姓名，不虛構部下。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷09)、[史料3](https://zh.wikisource.org/zh-hant/後漢書/卷72)
- 人物 宋建 `historical-song-jian`：song_jian／枹罕。《三國志》卷01、09記宋建據枹罕三十餘年、214年十月被夏侯淵討滅，未載確切建國月；《後漢書》卷72將宋建參與涼州亂列於184年冬。本篇依使用者要求於184年2月提前登場，以隴西節點代理枹罕據點，並非聲稱當月已建立政權或占有整個隴西郡。原典的丞相、百官無姓名，不虛構部下。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷09)、[史料3](https://zh.wikisource.org/zh-hant/後漢書/卷72)

### 188年6月・揺らぐ漢朝

- 人物 韓當 `san14-candidate-0176`：sun_jian／長沙。《三國志》記韓當隨孫堅征伐，終孫堅之世為別部司馬；188年從屬為生涯窗口推定，具體合駐長沙為本作安排。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷55)
- 人物 黃蓋 `san14-candidate-0247`：sun_jian／長沙。《三國志》記黃蓋從孫堅南破山賊、北走董卓；188年從屬為生涯窗口推定，具體合駐長沙為本作安排。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷55)
- 人物 朱治 `san14-candidate-0390`：sun_jian／長沙。《三國志》記朱治隨孫堅征伐，中平五年拜司馬；188年6月延續其從屬，具體合駐長沙為本作安排，未斷言拜官月份。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷56)
- 人物 程普 `san14-candidate-0703`：sun_jian／長沙。《三國志》記程普隨孫堅討黃巾，188年延續其從屬；具體合駐長沙為本作安排，非逐月駐防已證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷55)

### 190年1月・190年1月 · 反董卓联盟

- 都市 東平 `dongping`：liu_dai → bao_xin。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 上黨 `shangdang`：neutral → zhang_yang。張楊當時在上黨募兵；節點作活動區域代理，不稱確證郡城。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 于禁 `san14-candidate-0016`：liu_dai／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 衛茲 `san14-candidate-0021`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 應劭 `san14-candidate-0062`：liu_dai／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 王必 `san14-candidate-0071`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 夏侯淵 `san14-candidate-0114`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 韓浩 `san14-candidate-0159`：zhang_yang／上黨。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 黃權 `san14-candidate-0250`：liu_yan／江州。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 史渙 `san14-candidate-0333`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 徐璆 `san14-candidate-0441`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 曹昂 `san14-candidate-0510`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 曹純 `san14-candidate-0514`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 張肅 `san14-candidate-0627`：liu_yan／閬中。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 陳宮 `san14-candidate-0671`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 卞氏 `san14-candidate-0816`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 方悅 `san14-candidate-0818`：zhang_yang／上黨。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 鮑信 `san14-candidate-0826`：bao_xin／東平。初平元年關東軍地方長官；鮑信使用泰山/濟北鄰近東平節點作區域代理。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 穆順 `san14-candidate-0835`：zhang_yang／上黨。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 楊醜 `san14-candidate-0865`：zhang_yang／上黨。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 楊松 `san14-candidate-0868`：liu_yan／宕渠。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 劉岱 `san14-candidate-0947`：liu_dai／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 劉瑁 `san14-candidate-0961`：liu_yan／涪縣。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 191年10月・191年10月 · 二袁的意图

- 都市 陳留 `chenliu`：wei → zhang_miao。初平地方任官延續映射；鮑信濟北相以鄰近東平代理，不稱東平相。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 都市 濮陽 `dongjun`：liu_dai → wei。曹操191擊白繞後領東郡太守。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 都市 東平 `dongping`：liu_dai → bao_xin。初平地方任官延續映射；鮑信濟北相以鄰近東平代理，不稱東平相。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 昌邑 `shanyang`：wei → yuan_yi。初平地方任官延續映射；鮑信濟北相以鄰近東平代理，不稱東平相。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 于禁 `san14-candidate-0016`：liu_dai／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 袁遺 `san14-candidate-0024`：yuan_yi／昌邑。初平地方任官延續映射；鮑信濟北相以鄰近東平代理，不稱東平相。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 閻圃 `san14-candidate-0038`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 應劭 `san14-candidate-0062`：liu_dai／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 王必 `san14-candidate-0071`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 王凌 `san14-candidate-0077`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 郭嘉 `san14-candidate-0095`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 樂進 `san14-candidate-0102`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 夏侯淵 `san14-candidate-0114`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 夏侯惇 `san14-candidate-0124`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 高沛 `san14-candidate-0274`：liu_yan／江州。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 國淵 `san14-candidate-0287`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 蔡琰 `san14-candidate-0318`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 史渙 `san14-candidate-0333`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 司馬朗 `san14-candidate-0353`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 周喁 `san14-candidate-0365`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 荀彧 `san14-candidate-0393`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 鍾繇 `san14-candidate-0424`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 徐奕 `san14-candidate-0429`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 徐璆 `san14-candidate-0441`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 徐宣 `san14-candidate-0450`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 任峻 `san14-candidate-0460`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 曹安民 `san14-candidate-0499`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 曹休 `san14-candidate-0505`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 曹昂 `san14-candidate-0510`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 曹洪 `san14-candidate-0511`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 曹純 `san14-candidate-0514`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 曹仁 `san14-candidate-0518`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 張肅 `san14-candidate-0627`：liu_yan／閬中。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 張邈 `san14-candidate-0653`：zhang_miao／陳留。初平地方任官延續映射；鮑信濟北相以鄰近東平代理，不稱東平相。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 陳宮 `san14-candidate-0671`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 程昱 `san14-candidate-0689`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 鄭渾 `san14-candidate-0696`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 丁斐 `san14-candidate-0702`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 典韋 `san14-candidate-0709`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 杜氏 `san14-candidate-0750`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 杜襲 `san14-candidate-0751`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 卞氏 `san14-candidate-0816`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 鮑信 `san14-candidate-0826`：bao_xin／東平。初平地方任官延續映射；鮑信濟北相以鄰近東平代理，不稱東平相。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 滿寵 `san14-candidate-0842`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 毛玠 `san14-candidate-0844`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 楊松 `san14-candidate-0868`：liu_yan／宕渠。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 李典 `san14-candidate-0913`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 劉岱 `san14-candidate-0947`：liu_dai／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 劉馥 `san14-candidate-0956`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 劉瑁 `san14-candidate-0961`：liu_yan／涪縣。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 194年6月・194年6月 · 群雄割据

- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 鄄城 `jiyin`：lubu → wei。194年夏曹操僅保鄄城、范、東阿三縣。鄄城屬濟陰郡；本劇本沿用濟陰節點代表鄄城據點及三縣防區，顯示鄄城，並非聲稱定陶郡治或整個濟陰郡歸曹操。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)、[史料5](https://zh.wikisource.org/zh-hant/後漢書/卷111)
- 都市 吳 `wujun`：neutral → xu_gong。許貢為吳郡太守，未被朱治逐走前不屬王朗部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 樂進 `san14-candidate-0102`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 郝萌 `san14-candidate-0108`：lubu／陳留。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 夏侯恩 `san14-candidate-0115`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 韓浩 `san14-candidate-0159`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 許貢 `san14-candidate-0211`：xu_gong／吳。許貢為吳郡太守，未被朱治逐走前不屬王朗部下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 許汜 `san14-candidate-0212`：lubu／陳留。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 黃權 `san14-candidate-0250`：liu_zhang／江州。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 史渙 `san14-candidate-0333`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 司馬朗 `san14-candidate-0353`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 秦宜祿 `san14-candidate-0456`：lubu／陳留。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 任峻 `san14-candidate-0460`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 曹安民 `san14-candidate-0499`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 曹昂 `san14-candidate-0510`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 曹純 `san14-candidate-0514`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 曹仁 `san14-candidate-0518`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 曹性 `san14-candidate-0519`：lubu／陳留。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 曹操 `san14-candidate-0521`：wei／鄄城。曹操194年夏自徐州回救，仍以鄄城為本據；本作沿用濟陰節點代表鄄城縣域，不表示曹操據有整個濟陰郡。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)、[史料5](https://zh.wikisource.org/zh-hant/後漢書/卷111)
- 人物 張松 `san14-candidate-0632`：liu_zhang／宕渠。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 丁斐 `san14-candidate-0702`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 卞氏 `san14-candidate-0816`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 毛玠 `san14-candidate-0844`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 楊懷 `san14-candidate-0854`：liu_zhang／涪縣。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 劉岱 `san14-candidate-0947`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)
- 人物 呂虔 `san14-candidate-0980`：wei／鄄城。194年兗州叛亂修正城池控制後，按原有勢力遷移駐軍；不因城池易手改投敵方。具體駐城為本作配置，非逐人史料確證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷01)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷07)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷10)、[史料4](https://zh.wikisource.org/zh-hant/資治通鑑/卷061)

### 196年6月・曹操の台頭

- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 廬江 `lujiang`：wu → yuan_shu。袁術破陸康後以劉勳領廬江，孫策199才襲取；196不提前歸孫策。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 都市 鄱陽 `poyang`：neutral → liu_you。劉繇退彭澤；鄱陽是現有地圖的彭澤區域代理，不是郡治確址。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 都市 南昌 `yuzhang`：liu_you → hua_xin。華歆領豫章，與退彭澤的劉繇分別配置。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 華歆 `san14-candidate-0091`：hua_xin／南昌。華歆領豫章，與退彭澤的劉繇分別配置。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 韓當 `san14-candidate-0176`：wu／吳。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 許貢 `san14-candidate-0211`：在野／吳。許貢被朱治逐出吳郡後投嚴白虎；以吳郡在野表示，不作王朗、曹操或孫氏的既成部將。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 黃權 `san14-candidate-0250`：liu_zhang／江州。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 周泰 `san14-candidate-0373`：wu／秣陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 蔣欽 `san14-candidate-0412`：wu／吳。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 孫賁 `san14-candidate-0572`：wu／秣陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 太史慈 `san14-candidate-0586`：liu_you／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 張松 `san14-candidate-0632`：liu_zhang／宕渠。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 陳武 `san14-candidate-0686`：wu／吳。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 楊懷 `san14-candidate-0854`：liu_zhang／涪縣。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 呂範 `san14-candidate-0986`：wu／秣陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)

### 198年3月・呂布討伐戦

- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 許貢 `san14-candidate-0211`：在野／吳。許貢被朱治逐出吳郡後投嚴白虎；以吳郡在野表示，不作王朗、曹操或孫氏的既成部將。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 嚴顏 `san14-candidate-0231`：liu_zhang／巴東。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 射援 `san14-candidate-0355`：liu_zhang／江州。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 鄭度 `san14-candidate-0701`：liu_zhang／宕渠。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 劉璝 `san14-candidate-0928`：liu_zhang／涪縣。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 200年1月・200年1月 · 官渡之战

- 都市 高涼 `gaoliang`：wu → shi_xie。高涼為合浦舊縣，隨士氏合浦郡域配置；屬地域映射，不稱逐縣實控已確證。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 珠官 `hepu`：wu → shi_xie。士家兄弟分任南海/合浦，孫權210遣步騭前不提前全歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 臨賀 `linhe`：wu → neutral。臨賀為蒼梧舊縣，隨蒼梧的本開局地域配置；不表示此時已設臨賀郡。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 番禺 `nanhai`：wu → shi_xie。士家兄弟分任南海/合浦，孫權210遣步騭前不提前全歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 袁燿 `san14-candidate-0039`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 華歆 `san14-candidate-0091`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 郭嘉 `san14-candidate-0095`：wei／馮翊。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 夏侯淵 `san14-candidate-0114`：wei／許縣。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 許貢 `san14-candidate-0211`：在野／吳。許貢被朱治逐出吳郡後投嚴白虎；以吳郡在野表示，不作王朗、曹操或孫氏的既成部將。 [史料1](https://zh.wikisource.org/wiki/三國志/卷13)、[史料2](https://zh.wikisource.org/wiki/三國志/卷46)、[史料3](https://zh.wikisource.org/wiki/三國志/卷49)、[史料4](https://zh.wikisource.org/wiki/三國志/卷56)
- 人物 虞翻 `san14-candidate-0225`：wu／蘄春。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 吳國太 `san14-candidate-0292`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 史渙 `san14-candidate-0333`：wei／洛陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 周泰 `san14-candidate-0373`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 荀彧 `san14-candidate-0393`：wei／馮翊。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 蔣欽 `san14-candidate-0412`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 秦松 `san14-candidate-0462`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 宋謙 `san14-candidate-0508`：wu／蘄春。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 臧霸 `san14-candidate-0525`：wei／弘農。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 孫觀 `san14-candidate-0545`：wei／洛陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 孫靜 `san14-candidate-0567`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 孫瑜 `san14-candidate-0575`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 大喬 `san14-candidate-0584`：wu／吳。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 程普 `san14-candidate-0703`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 杜氏 `san14-candidate-0750`：wei／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 傅嬰 `san14-candidate-0802`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 卞喜 `san14-candidate-0815`：wei／弘農。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 梁習 `san14-candidate-0971`：wei／小沛。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 呂虔 `san14-candidate-0980`：wei／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 呂範 `san14-candidate-0986`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)

### 202年6月・河北争乱

- 都市 高涼 `gaoliang`：wu → shi_xie。高涼為合浦舊縣，隨士氏合浦郡域配置；屬地域映射，不稱逐縣實控已確證。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 珠官 `hepu`：wu → shi_xie。士家兄弟分任南海/合浦，孫權210遣步騭前不提前全歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 臨賀 `linhe`：wu → neutral。臨賀為蒼梧舊縣，隨蒼梧的本開局地域配置；不表示此時已設臨賀郡。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 番禺 `nanhai`：wu → shi_xie。士家兄弟分任南海/合浦，孫權210遣步騭前不提前全歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 閻圃 `san14-candidate-0038`：zhang_lu／漢中。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 王連 `san14-candidate-0079`：liu_zhang／江州。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 賈華 `san14-candidate-0086`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 闞澤 `san14-candidate-0171`：wu／南昌。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 吳景 `san14-candidate-0289`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 吳蘭 `san14-candidate-0315`：liu_zhang／宕渠。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 周泰 `san14-candidate-0373`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 朱然 `san14-candidate-0389`：wu／秣陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 徐氏 `san14-candidate-0444`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 全柔 `san14-candidate-0494`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 宋謙 `san14-candidate-0508`：wu／山陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 孫賁 `san14-candidate-0572`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 孫翊 `san14-candidate-0576`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 大喬 `san14-candidate-0584`：wu／廬江。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 張任 `san14-candidate-0637`：liu_zhang／涪縣。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 陳武 `san14-candidate-0686`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 董襲 `san14-candidate-0731`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 傅嬰 `san14-candidate-0802`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 孟光 `san14-candidate-0847`：liu_zhang／雒城。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 楊昂 `san14-candidate-0862`：zhang_lu／漢中。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 楊任 `san14-candidate-0869`：zhang_lu／漢中。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 劉循 `san14-candidate-0937`：liu_zhang／漢嘉。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 呂蒙 `san14-candidate-0988`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)

### 207年9月・207年9月 · 三顾茅庐

- 都市 高涼 `gaoliang`：wu → shi_xie。高涼為合浦舊縣，隨士氏合浦郡域配置；屬地域映射，不稱逐縣實控已確證。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 珠官 `hepu`：wu → shi_xie。士家兄弟分任南海/合浦，孫權210遣步騭前不提前全歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 臨賀 `linhe`：wu → wu_ju。臨賀為蒼梧舊縣，隨蒼梧的本開局地域配置；不表示此時已設臨賀郡。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 番禺 `nanhai`：wu → shi_xie。士家兄弟分任南海/合浦，孫權210遣步騭前不提前全歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 閻柔 `san14-candidate-0031`：wei／信都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 王修 `san14-candidate-0057`：wei／河內。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 賈華 `san14-candidate-0086`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 華歆 `san14-candidate-0091`：wei／北海。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 郝昭 `san14-candidate-0100`：wei／弘農。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 夏侯德 `san14-candidate-0123`：wei／南皮。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 賈信 `san14-candidate-0133`：wei／濟南。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 闞澤 `san14-candidate-0171`：wu／南昌。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 耿紀 `san14-candidate-0245`：wei／常山。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 黃蓋 `san14-candidate-0247`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 國淵 `san14-candidate-0287`：wei／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 顧邵 `san14-candidate-0300`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 吳範 `san14-candidate-0311`：wu／秣陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 周善 `san14-candidate-0370`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 朱蓋 `san14-candidate-0380`：wei／代郡。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 朱桓 `san14-candidate-0381`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 朱治 `san14-candidate-0390`：wu／山陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 朱靈 `san14-candidate-0392`：wei／鉅鹿。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 蔣濟 `san14-candidate-0418`：wei／東海。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 徐奕 `san14-candidate-0429`：wei／平原。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 徐詳 `san14-candidate-0448`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 辛憲英 `san14-candidate-0457`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 薛綜 `san14-candidate-0484`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 薛悌 `san14-candidate-0485`：wei／臨淄。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 全琮 `san14-candidate-0496`：wu／廬江。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 曹植 `san14-candidate-0516`：wei／東平。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 臧霸 `san14-candidate-0525`：wei／小沛。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 孫韶 `san14-candidate-0562`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 孫賁 `san14-candidate-0572`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 孫朗 `san14-candidate-0581`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 張燕 `san14-candidate-0601`：wei／范陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 趙儼 `san14-candidate-0615`：wei／甘陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 張承 `san14-candidate-0634`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 陳矯 `san14-candidate-0672`：wei／馮翊。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 陳琳 `san14-candidate-0688`：wei／上黨。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 程普 `san14-candidate-0703`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 丁奉 `san14-candidate-0706`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 杜畿 `san14-candidate-0748`：wei／河東。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 馬延 `san14-candidate-0758`：wei／上谷。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 步騭 `san14-candidate-0838`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 李異 `san14-candidate-0891`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 李典 `san14-candidate-0913`：wei／河間。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 劉勳 `san14-candidate-0933`：wei／昌邑。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 留贊 `san14-candidate-0935`：wu／蘄春。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 呂建 `san14-candidate-0981`：wei／洛陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 婁圭 `san14-candidate-0994`：wei／晉陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 魯肅 `san14-candidate-0997`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)

### 208年10月・208年10月 · 赤壁之战

- 都市 高涼 `gaoliang`：wu → shi_xie。高涼為合浦舊縣，隨士氏合浦郡域配置；屬地域映射，不稱逐縣實控已確證。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 珠官 `hepu`：wu → shi_xie。士家兄弟分任南海/合浦，孫權210遣步騭前不提前全歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 臨賀 `linhe`：wu → wu_ju。臨賀為蒼梧舊縣，隨蒼梧的本開局地域配置；不表示此時已設臨賀郡。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 番禺 `nanhai`：wu → shi_xie。士家兄弟分任南海/合浦，孫權210遣步騭前不提前全歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 閻柔 `san14-candidate-0031`：wei／信都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 王思 `san14-candidate-0055`：wei／弘農。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 王凌 `san14-candidate-0077`：wei／北海。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 蒯越 `san14-candidate-0084`：wei／濟南。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 賈華 `san14-candidate-0086`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 郭淮 `san14-candidate-0111`：wei／南皮。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 夏侯儒 `san14-candidate-0121`：wei／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 韓浩 `san14-candidate-0159`：wei／常山。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 闞澤 `san14-candidate-0171`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 邯鄲淳 `san14-candidate-0172`：wei／鉅鹿。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 虞翻 `san14-candidate-0225`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 侯音 `san14-candidate-0246`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 國淵 `san14-candidate-0287`：wei／宛城。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 吳國太 `san14-candidate-0292`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 胡綜 `san14-candidate-0303`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 司馬芝 `san14-candidate-0347`：wei／代郡。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 謝旌 `san14-candidate-0358`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 周瑜 `san14-candidate-0379`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 朱蓋 `san14-candidate-0380`：wei／平原。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 蔣欽 `san14-candidate-0412`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 焦觸 `san14-candidate-0416`：wei／東海。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 鍾繇 `san14-candidate-0424`：wei／臨淄。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 徐詳 `san14-candidate-0448`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 審榮 `san14-candidate-0454`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 辛毘 `san14-candidate-0465`：wei／小沛。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 全琮 `san14-candidate-0496`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 曹純 `san14-candidate-0514`：wei／東平。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 曹真 `san14-candidate-0517`：wei／甘陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 孫皎 `san14-candidate-0555`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 孫資 `san14-candidate-0559`：wei／范陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 孫賁 `san14-candidate-0572`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 大喬 `san14-candidate-0584`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 仲長統 `san14-candidate-0593`：wei／上黨。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 張承 `san14-candidate-0634`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 張承 `san14-candidate-0635`：wei／馮翊。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 陳矯 `san14-candidate-0672`：wei／上谷。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 陳武 `san14-candidate-0686`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 丁奉 `san14-candidate-0706`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 田豫 `san14-candidate-0715`：wei／河東。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 杜畿 `san14-candidate-0748`：wei／昌邑。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 馬休 `san14-candidate-0760`：wei／洛陽。208年馬騰入曹廷、馬超承領部曲；具體入朝月依本開局取值，非原典確月。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 馬鐵 `san14-candidate-0770`：wei／洛陽。208年馬騰入曹廷、馬超承領部曲；具體入朝月依本開局取值，非原典確月。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 馬騰 `san14-candidate-0771`：wei／洛陽。208年馬騰入曹廷、馬超承領部曲；具體入朝月依本開局取值，非原典確月。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 潘璋 `san14-candidate-0781`：wu／鄱陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 卞氏 `san14-candidate-0816`：wei／河間。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 毛玠 `san14-candidate-0844`：wei／晉陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 李異 `san14-candidate-0891`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 劉延 `san14-candidate-0926`：wei／洛陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 留贊 `san14-candidate-0935`：wu／廬陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 劉先 `san14-candidate-0944`：wei／下邳。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 劉磐 `san14-candidate-0951`：在野／長沙。正史曾與黃忠共守攸縣，208具體職位未確證；保留長沙在野，不強列韓玄手下。 [史料1](https://zh.wikisource.org/wiki/三國志/卷32)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 呂建 `san14-candidate-0981`：wei／河內。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 魯肅 `san14-candidate-0997`：wu／新都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 人物 路招 `san14-candidate-0999`：wei／薊。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 211年7月・潼関の戦い

- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 西平 `xiping`：neutral → han_sui。韓遂/閻行西平活動有據；本節點為金城西部區域映射，非開局月逐城確證。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 閻柔 `san14-candidate-0031`：wei／信都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 王修 `san14-candidate-0057`：wei／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 溫恢 `san14-candidate-0082`：wei／北海。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 華歆 `san14-candidate-0091`：wei／鉅鹿。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 夏侯淵 `san14-candidate-0114`：wei／南皮。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 夏侯惇 `san14-candidate-0124`：wei／宛城。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 魏諷 `san14-candidate-0195`：wei／常山。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 金禕 `san14-candidate-0220`：wei／平原。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 崔琰 `san14-candidate-0317`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 司馬懿 `san14-candidate-0344`：wei／臨淄。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 朱靈 `san14-candidate-0392`：wei／代郡。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 蔣幹 `san14-candidate-0407`：wei／小沛。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 徐商 `san14-candidate-0447`：wei／東海。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 辛憲英 `san14-candidate-0457`：wei／甘陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 曹憲 `san14-candidate-0509`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 曹植 `san14-candidate-0516`：wei／上黨。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 蘇則 `san14-candidate-0536`：wei／東平。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 仲長統 `san14-candidate-0593`：wei／上谷。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 張泉 `san14-candidate-0643`：wei／范陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 陳琳 `san14-candidate-0688`：wei／昌邑。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 董昭 `san14-candidate-0735`：wei／河間。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 裴潛 `san14-candidate-0756`：wei／晉陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 毛玠 `san14-candidate-0844`：wei／河內。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 楊阜 `san14-candidate-0879`：wei／下邳。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 劉曄 `san14-candidate-0962`：wei／濟南。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 呂建 `san14-candidate-0981`：wei／薊。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 212年12月・入蜀争奪戦

- 都市 安定 `anding`：ma_teng → wei。潼關後區域重核；安定楊秋已降曹，天水依通鑑213年攻冀口徑仍韋康。武威實控未確證。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 都市 涪縣 `fuxian`：liu_zhang → shu。通鑑建安十七年十二月，劉備進據涪城；具體旬日為本作約定。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 都市 葭萌 `jiameng`：liu_zhang → shu。劉備從葭萌起事；本開局採十二月反目並據涪城後的階段。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 都市 金城 `jincheng`：ma_teng → han_sui。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 都市 隴西 `longxi`：ma_teng → wei。潼關後區域重核；安定楊秋已降曹，天水依通鑑213年攻冀口徑仍韋康。武威實控未確證。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 都市 天水 `tianshui`：ma_teng → wei。潼關後區域重核；安定楊秋已降曹，天水依通鑑213年攻冀口徑仍韋康。武威實控未確證。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 都市 姑臧 `wuwei`：ma_teng → neutral。潼關後區域重核；安定楊秋已降曹，天水依通鑑213年攻冀口徑仍韋康。武威實控未確證。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 都市 西平 `xiping`：neutral → han_sui。韓遂/閻行西平活動有據；本節點為金城西部區域映射，非開局月逐城確證。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 阿貴 `san14-candidate-0002`：在野／隴西。潼關敗後隴右殘部；依通鑑213年攻冀口徑，212年末不虛構固定郡城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 尹默 `san14-candidate-0013`：在野／梓潼。重定212年十二月後已到出仕年，以在野登場，不憑空推定仕官。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 袁渙 `san14-candidate-0028`：wei／安定。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 王思 `san14-candidate-0055`：wei／河間。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 王凌 `san14-candidate-0077`：wei／信都。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 王連 `san14-candidate-0079`：liu_zhang／江州。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 蒯越 `san14-candidate-0084`：wei／河內。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 樂進 `san14-candidate-0102`：wei／北海。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 夏侯淵 `san14-candidate-0114`：wei／長安。關中平亂後長安軍區代理。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 夏侯儒 `san14-candidate-0121`：wei／弘農。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 關羽 `san14-candidate-0147`：shu／江陵。此時尚留荊州，不能提前按213/214入蜀完成後配置。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 毌丘興 `san14-candidate-0153`：wei／南皮。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 韓遂 `san14-candidate-0166`：han_sui／金城。韓遂與馬騰/馬超是並列部曲；金城採有首尾史料支持的區域延續映射。 [史料1](https://zh.wikisource.org/wiki/三國志/卷15)、[史料2](https://zh.wikisource.org/wiki/三國志/卷36)
- 人物 魏延 `san14-candidate-0189`：shu／涪縣。劉備入蜀主力與隨軍配置；涪縣為本作集結駐點。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 魏諷 `san14-candidate-0195`：wei／濟南。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 吳懿 `san14-candidate-0241`：liu_zhang／雒城。212年仍屬劉璋，廣漢節點為益州北線軍政區域代理；不提前213年轉屬。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 侯音 `san14-candidate-0246`：wei／常山。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 黃權 `san14-candidate-0250`：liu_zhang／雒城。212年仍屬劉璋，廣漢節點為益州北線軍政區域代理；不提前213年轉屬。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 侯選 `san14-candidate-0259`：在野／隴西。潼關敗後隴右殘部；依通鑑213年攻冀口徑，212年末不虛構固定郡城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 公孫恭 `san14-candidate-0263`：在野／襄平。公孫康在位，公孫恭不提前作君主。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 公孫康 `san14-candidate-0264`：gongsun／襄平。遼東當主公孫康；卒年沿用本作220估年，非史實確年。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷08)、[史料3](https://zh.wikisource.org/wiki/三國志/卷12)
- 人物 黃忠 `san14-candidate-0271`：shu／涪縣。劉備入蜀主力與隨軍配置；涪縣為本作集結駐點。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 吳質 `san14-candidate-0295`：wei／濟陰。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 吳蘭 `san14-candidate-0315`：liu_zhang／宕渠。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 司馬孚 `san14-candidate-0350`：wei／陳留。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 朱贊 `san14-candidate-0385`：wei／鉅鹿。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 徐奕 `san14-candidate-0429`：wei／隴西。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 諸葛亮 `san14-candidate-0440`：shu／江陵。此時尚留荊州，不能提前按213/214入蜀完成後配置。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 辛憲英 `san14-candidate-0457`：wei／代郡。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 石韜 `san14-candidate-0479`：wei／宛城。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 曹彰 `san14-candidate-0515`：wei／東海。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 宋忠 `san14-candidate-0524`：wei／平原。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 孫資 `san14-candidate-0559`：wei／濮陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 卓膺 `san14-candidate-0589`：shu／涪縣。劉備入蜀主力與隨軍配置；涪縣為本作集結駐點。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 趙雲 `san14-candidate-0596`：shu／江陵。此時尚留荊州，不能提前按213/214入蜀完成後配置。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 趙儼 `san14-candidate-0615`：wei／臨淄。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 張肅 `san14-candidate-0627`：liu_zhang／雒城。212年仍屬劉璋，廣漢節點為益州北線軍政區域代理；不提前213年轉屬。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 張任 `san14-candidate-0637`：liu_zhang／雒城。212年仍屬劉璋，廣漢節點為益州北線軍政區域代理；不提前213年轉屬。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 張飛 `san14-candidate-0656`：shu／江陵。此時尚留荊州，不能提前按213/214入蜀完成後配置。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 張苞 `san14-candidate-0658`：在野／宛城。重定212年十二月後已到出仕年，以在野登場，不憑空推定仕官。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 張遼 `san14-candidate-0663`：wei／東平。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 程昱 `san14-candidate-0689`：wei／小沛。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 程畿 `san14-candidate-0691`：liu_zhang／建寧。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 鄧芝 `san14-candidate-0729`：在野／閬中。依龐羲的區域配置，不提前當作劉備定蜀後任官。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 董昭 `san14-candidate-0735`：wei／范陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 裴潛 `san14-candidate-0756`：wei／甘陵。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 馬雲騄 `san14-candidate-0757`：在野／隴西。潼關敗後隴右殘部；依通鑑213年攻冀口徑，212年末不虛構固定郡城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 馬岱 `san14-candidate-0766`：在野／隴西。潼關敗後隴右殘部；依通鑑213年攻冀口徑，212年末不虛構固定郡城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 馬超 `san14-candidate-0769`：在野／隴西。潼關敗後隴右殘部；依通鑑213年攻冀口徑，212年末不虛構固定郡城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 費禕 `san14-candidate-0787`：在野／江州。重定212年十二月後已到出仕年，以在野登場，不憑空推定仕官。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 費詩 `san14-candidate-0791`：liu_zhang／雒城。212年仍屬劉璋，廣漢節點為益州北線軍政區域代理；不提前213年轉屬。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 傅幹 `san14-candidate-0804`：在野／隴西。潼關敗後隴右殘部；依通鑑213年攻冀口徑，212年末不虛構固定郡城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 法正 `san14-candidate-0827`：shu／涪縣。劉備入蜀主力與隨軍配置；涪縣為本作集結駐點。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 龐統 `san14-candidate-0828`：shu／涪縣。劉備入蜀主力與隨軍配置；涪縣為本作集結駐點。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 龐德 `san14-candidate-0830`：在野／隴西。潼關敗後隴右殘部；依通鑑213年攻冀口徑，212年末不虛構固定郡城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 滿寵 `san14-candidate-0842`：wei／馮翊。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 孟獲 `san14-candidate-0845`：在野／雲南。重定212年十二月後已到出仕年，以在野登場，不憑空推定仕官。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 孟達 `san14-candidate-0849`：shu／江陵。此時尚留荊州，不能提前按213/214入蜀完成後配置。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 雍闓 `san14-candidate-0855`：在野／建寧。南中地方豪強，在野區域代理，不作212劉備南郡軍官。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 楊氏 `san14-candidate-0864`：在野／隴西。潼關敗後隴右殘部；依通鑑213年攻冀口徑，212年末不虛構固定郡城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 楊修 `san14-candidate-0866`：wei／上黨。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 楊秋 `san14-candidate-0867`：在野／隴西。潼關敗後隴右殘部；依通鑑213年攻冀口徑，212年末不虛構固定郡城。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 李恢 `san14-candidate-0892`：liu_zhang／建寧。尚在益州郡董和部，未提前投劉備。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 李嚴 `san14-candidate-0904`：liu_zhang／雒城。212年仍屬劉璋，廣漢節點為益州北線軍政區域代理；不提前213年轉屬。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 劉璝 `san14-candidate-0928`：liu_zhang／雒城。212年仍屬劉璋，廣漢節點為益州北線軍政區域代理；不提前213年轉屬。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 劉循 `san14-candidate-0937`：liu_zhang／江陽。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 劉劭 `san14-candidate-0939`：在野／鄴。重定212年十二月後已到出仕年，以在野登場，不憑空推定仕官。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 劉先 `san14-candidate-0944`：wei／河東。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 劉封 `san14-candidate-0959`：shu／江陵。此時尚留荊州，不能提前按213/214入蜀完成後配置。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)
- 人物 涼茂 `san14-candidate-0975`：wei／上谷。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 人物 冷苞 `san14-candidate-0992`：liu_zhang／雒城。212年仍屬劉璋，廣漢節點為益州北線軍政區域代理；不提前213年轉屬。 [史料1](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[史料2](https://zh.wikisource.org/wiki/三國志/卷32)、[史料3](https://zh.wikisource.org/wiki/三國志/卷40)、[史料4](https://zh.wikisource.org/wiki/三國志/卷41)、[史料5](https://zh.wikisource.org/wiki/三國志/卷43)、[史料6](https://zh.wikisource.org/wiki/三國志/卷45)、[史料7](https://zh.wikisource.org/wiki/三國志/卷47)

### 225年7月・南蛮征伐

- 都市 牂牁 `zangke`：shu → nanman。依使用者指定，225年7月牂牁歸孟獲並合併雍闓、高定、朱褒。原典所支持的馬忠已平牂牁判斷仍保留於overridden_historical_review；本次開局優先採用遊戲設定，並非推翻原史料或聲稱孟獲當月實際控制牂牁。 [史料1](https://zh.wikisource.org/wiki/華陽國志/卷四)、[史料2](https://zh.wikisource.org/wiki/三國志/卷43)
- 人物 金環三結 `san14-candidate-0221`：nanman／興古。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/華陽國志/卷四)、[史料2](https://zh.wikisource.org/wiki/三國志/卷43)
- 人物 高定 `san14-candidate-0272`：nanman／建寧。依用戶指定將高定納入孟獲勢力，沿用建寧駐地。史料所記活動地為越巂，且於225年南征時被斬；本庫死亡年251是第三方遊戲設定轉錄，本次不改共享生卒年，不將此開局歸屬與駐地宣稱為逐月史實。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷43)、[史料2](https://zh.wikisource.org/zh-hant/華陽國志_(四庫全書本)/卷04)
- 人物 祝融 `san14-candidate-0383`：nanman／興古。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/華陽國志/卷四)、[史料2](https://zh.wikisource.org/wiki/三國志/卷43)
- 人物 朱褒 `san14-candidate-0391`：nanman／牂牁。依用戶指定將朱褒納入孟獲勢力並駐牂牁；史料記朱褒曾反叛於牂牁，不能據此證明225年7月仍為孟獲部下。保留原資料死亡年225及當年出場確認，此為本作開局合併設定，非SAN14原始配置。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷43)、[史料2](https://zh.wikisource.org/zh-hant/華陽國志_(四庫全書本)/卷04)
- 人物 董荼那 `san14-candidate-0739`：nanman／興古。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/華陽國志/卷四)、[史料2](https://zh.wikisource.org/wiki/三國志/卷43)
- 人物 孟優 `san14-candidate-0850`：nanman／興古。原駐城歸屬修訂後保留原勢力，改駐本方城；具體駐防屬本作安排。 [史料1](https://zh.wikisource.org/wiki/華陽國志/卷四)、[史料2](https://zh.wikisource.org/wiki/三國志/卷43)
- 人物 雍闓 `san14-candidate-0855`：nanman／建寧。依用戶指定將雍闓納入孟獲勢力，駐建寧。史料記雍闓在諸葛亮南征途中已為高定部曲所殺；225年7月仍可出場為本作開局合併設定，保留原資料死亡年225及當年出場確認，非逐月史實或SAN14原始配置。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷43)、[史料2](https://zh.wikisource.org/zh-hant/華陽國志_(四庫全書本)/卷04)

### 263年5月・蜀漢の滅亡

- 都市 交趾 `jiaozhi`：neutral → lu_xing。《三國志》卷48記263年五月交趾郡吏呂興等反、殺孫諝；《資治通鑑》卷078記九真、日南響應。本篇於五月上旬開局即呈現叛軍控制，是月界配置；沒有確切日次，亦不提前視為魏國正式郡守。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷48)、[史料2](https://zh.wikisource.org/zh-hant/資治通鑑/卷078)
- 都市 九真 `jiuzhen`：neutral → lu_xing。《三國志》卷48記263年五月交趾郡吏呂興等反、殺孫諝；《資治通鑑》卷078記九真、日南響應。本篇於五月上旬開局即呈現叛軍控制，是月界配置；沒有確切日次，亦不提前視為魏國正式郡守。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷48)、[史料2](https://zh.wikisource.org/zh-hant/資治通鑑/卷078)
- 都市 日南 `rinan`：neutral → lu_xing。《三國志》卷48記263年五月交趾郡吏呂興等反、殺孫諝；《資治通鑑》卷078記九真、日南響應。本篇於五月上旬開局即呈現叛軍控制，是月界配置；沒有確切日次，亦不提前視為魏國正式郡守。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷48)、[史料2](https://zh.wikisource.org/zh-hant/資治通鑑/卷078)
- 人物 李統 `historical-li-tong-jiaozhi`：lu_xing／九真。《晉書》卷057陶璜傳記呂興被其功曹李統所殺，可證李統曾屬呂興，未載263年五月任職地。本篇依使用者要求以本陣營任職窗口推定配置九真，不聲稱該地曾任功曹；此李統與魏將李通為不同人物。該傳把事件繫於孫皓、晉武帝時，年代與《三國志》卷48不同，本作採後者的263年起事年月，生卒邊界另標估計。 [史料1](https://zh.wikisource.org/zh-hant/晉書/卷057)、[史料2](https://zh.wikisource.org/zh-hant/三國志/卷48)、[史料3](https://zh.wikisource.org/zh-hant/三國志/卷04)
- 人物 呂興 `historical-lu-xing`：lu_xing／交趾。《三國志》卷48記263年五月交趾郡吏呂興等反、殺孫諝；《資治通鑑》卷078記九真、日南響應。本篇於五月上旬開局即呈現叛軍控制，是月界配置；沒有確切日次，亦不提前視為魏國正式郡守。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷48)、[史料2](https://zh.wikisource.org/zh-hant/資治通鑑/卷078)
- 人物 唐譜 `historical-tang-pu`：lu_xing／交趾。《三國志》卷04於264年九月詔書記呂興遣都尉唐譜經霍弋上表；可證唐譜為呂興部下，不能證明263年五月已任都尉。本篇依使用者要求以本陣營任職窗口推定，提前配置交趾；駐城、出仕年及生卒邊界為本作估計，非263年逐將史證。 [史料1](https://zh.wikisource.org/zh-hant/三國志/卷04)

## 実効支配・月界の未確定事項

### 190年1月・190年1月 · 反董卓联盟

- 都市 武都 `wudu`：liu_yan → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：liu_yan → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 191年10月・191年10月 · 二袁的意图

- 都市 武都 `wudu`：liu_yan → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：liu_yan → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 194年6月・194年6月 · 群雄割据

- 都市 武都 `wudu`：liu_zhang → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：liu_zhang → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 196年6月・曹操の台頭

- 都市 武都 `wudu`：liu_zhang → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：liu_zhang → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 198年3月・呂布討伐戦

- 都市 武都 `wudu`：liu_zhang → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：liu_zhang → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 200年1月・200年1月 · 官渡之战

- 都市 蒼梧 `cangwu`：wu → neutral。蒼梧地方漢郡，200/202具體交接月待考，不提前歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 武都 `wudu`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 鬱林 `yulin`：wu → neutral。鬱林此時實控缺直接材料，不以名義督七郡推定孫權或士家已全控制。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)

### 202年6月・河北争乱

- 都市 蒼梧 `cangwu`：wu → neutral。蒼梧地方漢郡，200/202具體交接月待考，不提前歸吳。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)
- 都市 武都 `wudu`：zhang_lu → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：liu_zhang → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 鬱林 `yulin`：wu → neutral。鬱林此時實控缺直接材料，不以名義督七郡推定孫權或士家已全控制。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)

### 207年9月・207年9月 · 三顾茅庐

- 都市 武都 `wudu`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 鬱林 `yulin`：wu → neutral。鬱林此時實控缺直接材料，不以名義督七郡推定孫權或士家已全控制。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)

### 208年10月・208年10月 · 赤壁之战

- 都市 武都 `wudu`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 鬱林 `yulin`：wu → neutral。鬱林此時實控缺直接材料，不以名義督七郡推定孫權或士家已全控制。 [史料1](https://zh.wikisource.org/wiki/三國志/卷49)、[史料2](https://zh.wikisource.org/wiki/三國志/卷52)、[史料3](https://zh.wikisource.org/wiki/宋書/卷37)、[史料4](https://zh.wikisource.org/wiki/宋書/卷38)

### 211年7月・潼関の戦い

- 都市 武都 `wudu`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

### 212年12月・入蜀争奪戦

- 都市 武都 `wudu`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)
- 都市 陰平 `yinping`：wei → neutral。215年曹操進軍前，地方氐部與漢官並存；本開局實際控制待考，不斷言全屬曹操或張魯。 [史料1](https://zh.wikisource.org/wiki/三國志/卷01)、[史料2](https://zh.wikisource.org/wiki/三國志/卷16)、[史料3](https://zh.wikisource.org/wiki/華陽國志/卷二)

## 212年12月・入蜀争奪戦

『資治通鑑』巻66の建安十七年十二月は、劉備が葭萌から南へ兵を返し、張松・楊懐・高沛の死を経て涪城に進んだ段階を記します。本作はこの出来事の後を開幕に採ります。**具体的な上・中・下旬は原典で確定したものではありません**。劉備が益州全域を領有した214年の配置を前倒ししません。[巻66](https://zh.wikisource.org/wiki/資治通鑑/卷066)、[先主伝](https://zh.wikisource.org/wiki/三國志/卷32)、[霍峻伝](https://zh.wikisource.org/wiki/三國志/卷41)

| 初期所属 | 開放都市 |
| --- | --- |
| 公孫康（1） | 襄平 |
| 韓遂（2） | 金城、西平 |
| 劉璋（20） | 巴東、江州、閬中、宕渠、涪陵、雒城、漢嘉、江陽、建寧、南廣、犍為、成都、汶山、興古、永昌、越巂、雲南、牂牁、朱提、梓潼 |
| 士燮（3） | 交趾、九真、日南 |
| 劉備（8） | 長沙、涪縣、桂陽、葭萌、零陵、江陵、武陵、宜都 |
| 曹操（48） | 安定、信都、北海、南皮、常山、陳留、代郡、東海、濮陽、東平、范陽、馮翊、扶風、河東、河間、洛陽、河內、弘農、濟南、長安、壽春、濟陰、鉅鹿、遼西、隴西、宛城、平原、臨淄、小沛、甘陵、汝南、上黨、上谷、昌邑、晉陽、天水、鄴、襄陽、下邳、西河、新城、薊、雁門、許縣、章陵、漁陽、趙國、中山 |
| 孫權（16） | 蒼梧、建業、高涼、珠官、江夏、山陰、臨賀、廬江、廬陵、番禺、鄱陽、蘄春、吳、新都、鬱林、南昌 |
| 張魯（1） | 漢中 |
| 中立・地方実控未確定（10） | 帶方、敦煌、酒泉、樂浪、武都（地方氐部（控制待考））、姑臧、陰平（地方氐部（控制待考））、夷洲（岛屿地区（中立））、張掖、朱崖（岛屿地区（中立）） |

上表は最終データの全都市一覧です。史料の州・郡・客軍の位置を一都市一所属へ写した配置も含みます。韓遂は馬騰・馬超の通常配下としてまとめず、212年末の馬超は固定郡城の証明がない残部として在野に残します。天水の韋康は『通鑑』の213年冀城陥落の系年を採りますが、『三國志』楊阜伝の十七年記とは相違があり、この選択を無条件に原典一致とはしません。皖城・廬江の移管月も214年の落城から逆算して確定しません。

| 今回確認した人物 | 所属 | 駐点／扱い | 判定 |
| --- | --- | --- | --- |
| 阿貴 | 在野 | 隴西 | bounded_regional_inference |
| 韋康 | wei | 天水 | primary_text_chronology_choice |
| 尹默 | 在野 | 梓潼 | bounded_regional_inference |
| 袁渙 | wei | 安定 | authorial_garrison_relocation |
| 閻行 | han_sui | 金城 | primary_text_affiliation |
| 王思 | wei | 河間 | authorial_garrison_relocation |
| 王凌 | wei | 信都 | authorial_garrison_relocation |
| 王連 | liu_zhang | 江州 | authorial_garrison_relocation |
| 蒯越 | wei | 河內 | authorial_garrison_relocation |
| 霍峻 | shu | 葭萌 | primary_text_affiliation |
| 樂進 | wei | 北海 | authorial_garrison_relocation |
| 夏侯淵 | wei | 長安 | regional_primary_mapping |
| 夏侯儒 | wei | 弘農 | authorial_garrison_relocation |
| 關羽 | shu | 江陵 | regional_primary_mapping |
| 毌丘興 | wei | 南皮 | authorial_garrison_relocation |
| 韓遂 | han_sui | 金城 | regional_primary_mapping |
| 魏延 | shu | 涪縣 | regional_primary_mapping |
| 魏諷 | wei | 濟南 | authorial_garrison_relocation |
| 嚴顏 | liu_zhang | 江州 | primary_text_affiliation |
| 吳懿 | liu_zhang | 雒城 | regional_primary_mapping |
| 侯音 | wei | 常山 | authorial_garrison_relocation |
| 黃權 | liu_zhang | 雒城 | regional_primary_mapping |
| 侯選 | 在野 | 隴西 | bounded_regional_inference |
| 公孫恭 | 在野 | 襄平 | bounded_regional_inference |
| 公孫康 | gongsun | 襄平 | bounded_career_inference |
| 黃忠 | shu | 涪縣 | regional_primary_mapping |
| 吳質 | wei | 濟陰 | authorial_garrison_relocation |
| 吳蘭 | liu_zhang | 宕渠 | authorial_garrison_relocation |
| 司馬孚 | wei | 陳留 | authorial_garrison_relocation |
| 朱贊 | wei | 鉅鹿 | authorial_garrison_relocation |
| 徐奕 | wei | 隴西 | authorial_garrison_relocation |
| 諸葛亮 | shu | 江陵 | regional_primary_mapping |
| 辛憲英 | wei | 代郡 | authorial_garrison_relocation |
| 成公英 | han_sui | 金城 | primary_text_affiliation |
| 石韜 | wei | 宛城 | authorial_garrison_relocation |
| 曹彰 | wei | 東海 | authorial_garrison_relocation |
| 宋忠 | wei | 平原 | authorial_garrison_relocation |
| 孫權 | wu | 建業 | primary_text_affiliation |
| 孫資 | wei | 濮陽 | authorial_garrison_relocation |
| 卓膺 | shu | 涪縣 | regional_primary_mapping |
| 趙雲 | shu | 江陵 | regional_primary_mapping |
| 趙儼 | wei | 臨淄 | authorial_garrison_relocation |
| 張肅 | liu_zhang | 雒城 | regional_primary_mapping |
| 張任 | liu_zhang | 雒城 | regional_primary_mapping |
| 張飛 | shu | 江陵 | regional_primary_mapping |
| 張苞 | 在野 | 宛城 | bounded_regional_inference |
| 張遼 | wei | 東平 | authorial_garrison_relocation |
| 程昱 | wei | 小沛 | authorial_garrison_relocation |
| 程畿 | liu_zhang | 建寧 | authorial_garrison_relocation |
| 鄭度 | liu_zhang | 成都 | primary_text_affiliation |
| 鄧芝 | 在野 | 閬中 | bounded_regional_inference |
| 董昭 | wei | 范陽 | authorial_garrison_relocation |
| 裴潛 | wei | 甘陵 | authorial_garrison_relocation |
| 馬雲騄 | 在野 | 隴西 | bounded_regional_inference |
| 馬岱 | 在野 | 隴西 | bounded_regional_inference |
| 馬超 | 在野 | 隴西 | bounded_regional_inference |
| 費禕 | 在野 | 江州 | bounded_regional_inference |
| 費詩 | liu_zhang | 雒城 | regional_primary_mapping |
| 傅幹 | 在野 | 隴西 | bounded_regional_inference |
| 法正 | shu | 涪縣 | regional_primary_mapping |
| 龐統 | shu | 涪縣 | regional_primary_mapping |
| 龐德 | 在野 | 隴西 | bounded_regional_inference |
| 滿寵 | wei | 馮翊 | authorial_garrison_relocation |
| 孟獲 | 在野 | 雲南 | bounded_regional_inference |
| 孟達 | shu | 江陵 | regional_primary_mapping |
| 雍闓 | 在野 | 建寧 | bounded_regional_inference |
| 楊氏 | 在野 | 隴西 | bounded_regional_inference |
| 楊修 | wei | 上黨 | authorial_garrison_relocation |
| 楊秋 | 在野 | 隴西 | bounded_regional_inference |
| 李恢 | liu_zhang | 建寧 | regional_primary_mapping |
| 李嚴 | liu_zhang | 雒城 | regional_primary_mapping |
| 劉璝 | liu_zhang | 雒城 | regional_primary_mapping |
| 劉循 | liu_zhang | 江陽 | authorial_garrison_relocation |
| 劉劭 | 在野 | 鄴 | bounded_regional_inference |
| 劉先 | wei | 河東 | authorial_garrison_relocation |
| 劉備 | shu | 涪縣 | primary_text_affiliation |
| 劉封 | shu | 江陵 | regional_primary_mapping |
| 涼茂 | wei | 上谷 | authorial_garrison_relocation |
| 冷苞 | liu_zhang | 雒城 | regional_primary_mapping |

張松・楊懐・高沛は上記の開幕段階では既に没しています。馬騰・馬休・馬鉄の212年5月の死も、211年潼関シナリオで存命であることとは分けます。諸葛亮・張飛・趙雲らの213年の入蜀を先取りしません。

## 赤壁の荊南四郡

人数は君主を含みます。史実の地方行政官を可操作の勢力として分け、演義人物も使って少人数勢力を構成します。全員が正史で同じ太守の部下だったとする名簿ではありません。

| 郡・君主 | 開幕武将 | 人数 |
| --- | --- | --- |
| 長沙・韓玄 | 韓玄、魏延、黃忠 | 3 |
| 武陵・金旋 | 鞏志、金旋 | 2 |
| 桂陽・趙範 | 趙範、陳應、鮑隆 | 3 |
| 零陵・劉度 | 邢道榮、劉賢、劉度 | 3 |

黄忠が曹操の荊州確保後に韓玄の指揮下にあったことは『黄忠伝』に記されています。一方、魏延の韓玄配下、鞏志、陳応・鮑隆、劉賢・邢道栄などの配属は演義・ゲーム互換です。劉磐は黄忠と攸県を守った原典記録があっても、この月の職位や韓玄の配下を断定せず長沙方面の在野とします。[先主伝](https://zh.wikisource.org/wiki/三國志/卷32)、[黄忠伝](https://zh.wikisource.org/wiki/三國志/卷36)、[『三國演義』第53回](https://zh.wikisource.org/wiki/三國演義/第053回)

## 独立勢力にしていない地方勢力と未確定範囲

- 張燕、烏丸、厳白虎や地方氐部は、各時期に現在の節点を一つ丸ごと与える証拠や人物・都市の対応が不足する場合、独立した都市勢力にしていません。不存在や、すべて曹操の直轄だったという意味ではありません。
- 武都・陰平は215年以前の地方実控を中立で表す箇所があります。張魯・劉璋・曹操のどれかへ一律に塗り替える証明ではありません。
- 221年の南中は名義上の蜀属と実効支配を分けます。張裔が223年まで数年呉にいた記録と、劉備死後に反乱をまとめる記録には、雍闓の初動年月を確定しにくい点があります。黄元の222年12月〜223年3月の反乱は、現在の開幕時点の間にあります。
- 184年2月の宋建は利用者指定による前倒し登場です。隴西の節点を枹罕地域の代理とし、184年冬の記録を2月の確証とはしません。
- 225年7月は利用者指定で牂牁を孟獲に与え、雍闓・高定・朱褒をその配下にまとめます。史料上の討平時期と異なる開幕設定として明記し、史実の修正とは呼びません。
- 士徽の反乱は226年で、225年7月の士燮や227年2月の呉属とは別です。263年5月は呂興に応じた交趾・九真・日南を地方叛軍として表し、264年の正式な魏の任命を先取りしません。呂興は独立した人物IDの可操作勢力で、唐譜・李統の263年配置は後年の記録からの開幕推定です。詳しくは[追加人物と史料の境界](song-jian-lu-xing.md)を参照してください。

以下は決定表に保存した追加の制限です。

- Regional review, not a complete transcription of SAN14 or an attested prefect list for each exact month.
- Zhang Yan, Wuhuan, Yan Baihu and Di rulers lack separate matching city/person configurations; omission is recorded instead of inventing administrative city control.
- 184 early military groups retain playable command proxies: Sun Jian at Xiapi is grounded in his county-deputy posting, but not represented as a historically independent commandery governor.
- 207 Zhangling for Liu Bei,208 August Zhangling cutoff,209 IF Linjiang owner and other earlier explicit user settings are retained.
- Lujiang/Wan transition before213/214 and some Jiangxia cross-river splits lack a proven exact opening-month boundary; no unsupported backdating from214 conquest.
- Four Jingnan prefect groups are playable local administrations; the subordinate roster distinguishes primary history from Romance-game compatibility.
- Song Jian184-02 is an explicit early-opening Fuhan proxy; Lu Xing263-05 is a dated revolt mapping with Tang Pu and Li Tong retinue-window estimates;225 Nanzhong consolidation follows explicit user game setup over the retained primary historical interpretation.

## 再生成と照合

```sh
python3 -B game/build_campaigns.py --check
python3 -B tools/scenario-history/audit.py --write
python3 -B tools/scenario-history/audit.py --check
```

`--check` はファイルを書き換えず、23本の漏れ・重複、仮想6本の除外、最終都市所属、追加勢力の君主と本拠、人物の最終所属・駐点、生成済みレポートの一致を検査します。乱数、プレイヤーのセーブ、ネットワークやゲーム命令は使いません。史料解釈自体の正しさを自動証明する検査ではありません。

[2026年10月24日の19都市×19本レビュー](city-ownership-audit-20261024.md)は当時の基準として保存し、今回の23本の結果で過去の件数・年月を書き換えません。
