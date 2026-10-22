# 原版戰鬥像素素材

`game/assets/battle-original/index.json` 綁定原版256×240畫面、來源截圖／存態雜湊、原ROM、Nestopia核心與Royaltea調色盤。Web遊戲只讀PNG與JSON，不讀ROM、模擬器或研究檔案。

- 原ROM SHA-256：`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。
- 原核心：Nestopia2.0.0／135dfa6，SHA-256 `924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a`。
- 原圖來自已封存的本機逆向研究包，逐張核對其capture JSON的ROM、核心與調色盤記錄。沒有用影像生成改畫人物。

`backgrounds.plain`為原普通攻擊上方256×160草地；`backgrounds.tactical`為原戰術地形，僅把一個固定武將旗標以同一原圖的普通地面替換。`mountain`與`water`目前是這張混合山河戰術參考圖的別名，不代表已恢復每座城市的專屬戰場。普通攻擊近景應使用`plain`，戰術層可按需要重排`terrain`中的原版地面、樹林、山與河流貼片，並將新佈局明記為本作演出。

`sprite.frames`包含PNG路徑、原尺寸、底部anchor、原圖裁切位置及透明化操作。灰色`infantry`與紅色`infantry_enemy`為原普通攻擊兵卒；`cavalry`僅保留最初接線用的紅方兵卒別名，不表示確認騎兵種類，也不增加遊戲兵種。左右單挑騎將各兩個完整姿勢，使用96×96透明畫布保存原比例；左將朝右、右將朝左，衣甲、馬匹及武器保持原圖。這些是通用場景角色，不能當成新增武將的肖像身分。

普通攻擊透明兵卒以同一場景的原無兵地面逐像素相減。單挑角色只把原黑底轉透明，沒有重新取樣；接觸後僅剩馬尾的右將瞬間未作完整角色輸出。無法可靠確認的火焰、箭矢、命中及落石圖塊不臆造其原版身分；這四項在manifest明列為缺少的原版素材。

普通攻擊另有`sprites.attack_formation`與`attack_formation_enemy`：每方保留原版完整128×160半屏兵陣，而非反覆排列一張16×16士兵圖。兩個姿勢分別取自`first-attack-main-01`與`first-attack-main-04`，對照同場景草地逐像素透明化，原兵卒、長兵器、陣列間距、灰／紅調色與朝向不變。`witnesses.attack`與`attack_advance`保存對應256×240原畫面，離線測試逐像素驗證兵陣透明層可還原該畫面的兵卒。這兩張是已封存的原模擬器截圖，不表示本次重新完成了原遊戲整段戰鬥的動態追蹤；Web的接近、交鋒與退回時間仍屬於本作呈現層。

PPU記錄保存32色索引、CHR實體頁、OAM及nametable雜湊。大量兵卒／騎將本身由背景CHR呈現；原遊戲在掃描線中切換圖形與調色盤，不能用單一VBlank存態的CHR映射冒充完整PPU光柵重現。這些記錄用於來源稽核，實際顯示像素來自原模擬器影片回呼截圖。

```sh
python3 -B tools/battle-original/build.py --check
python3 -B tools/battle-original/build.py --state-root /absolute/path/to/research-archive --rom /absolute/path/to/三国志2超级版.nes
```

第一條不需要原ROM或研究檔案，驗證出貨圖片的路徑、雜湊、尺寸、透明度、非空精靈與工具版本。第二條才是明確的離線重建；需要Pillow（與現有肖像工具相同）。重建不改來源截圖／存態。

原遊戲圖像保留其原有權利，不因本倉庫程式碼採MIT授權而重新授權。原始截圖witness另存，供256×240布局與像素外觀比對；執行時不必顯示其固定姓名／數值。
