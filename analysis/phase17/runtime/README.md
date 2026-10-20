# 原玩家败亡与结局退出：三案双跑

三案均运行只读原ROM和固定Nestopia。恢复源码没有安装进核心，帧字段不等于CPU内部trace，原WAV也不是Python源码合成。每次重复都用新Python进程；整份序列化buffer不截断、不归一化。

单人和名单资格案加载Phase16玩家案的initial.state，该档是战前、准备之前的自然Phase3母档全文复制；whole bytes已断言相同，所以未继承Phase16后来5byte准备。双人案从真实coldboot、标题2人プレイ、原两只手柄、君主选择、出征、军队与补给完整开始，没有state/battery导入。三案都在实际普通攻击前声明11byte数值/名册准备，不冒称自然完整灭亡战役。

准备共同5byte：曹操131体力1、武力1，敌袁绍8武力99，敌slot0 X3/Y16相邻。空名单案清城11与14完整10槽，只有原6个非FF名单字节实际改变，owner保持2。资格案则城11首槽原5→仍活着的131，其余槽FF；曹操低2状态没有准备，后来HPFF/status3由真实原普通攻击产生。全部准备前后2048B RAM/8192B SRAM dump已逐byte重建；后续没有新增核心memorywrite、按钮之外的ready/ack/result/status/controller注入。

原BE2E只看所属city.owner低3和名单首槽是否FF，不筛候选体力/status/byte5。空名册→原city13/6 C386仅写leaderFF，再原文字完成与按键进入global13、原NMI8 loss模式0。结局动画04CB=FE后，单人B不能退出，A由原D752跳E000，实见global0→标题→原newgame重新初始化回城。该环节的场景重新初始化不能说成战后自动复活或城市中立。

双人设置6F43=1由原title和ruler初始化产生，第二手柄普通输入逐步记录controller_port=1。败亡结局A清该flag并global14→1恢复0472/73父流程，随后原第二玩家提示、手柄2 A和city0/1；它不是实时活玩家计数，未准备此flag。空城11/14在结局A之前仍owner2/空名单。名单仅曹操案原菜单确实接受HPFF/status3的131并回city0/1，没有ending；这是受控异常数据对照，不能称健康继任者或自然可达。

正式总计：34062首跑帧／68124两跑帧；594检查点；2429非空artifact原样hash相等（含30正式JSON）；3整份48kHz双声道16bit WAV；33准备byte写／0继承准备。594个0B VRAM及同数路径metadata JSON明确排除。

[正式总证据](evidence.json) · [总回执](validation.json) · [静态图像／WAV／准备审计](static-validation.json) · [脚本](../../../scripts/capture_player_extinction.py)

## 单人无候选：原败亡结局→软件重启→重新开局

10136帧，242检查点，11战前byte准备。

[回执](single-player-empty-rosters-reset/validation.json) · [双跑全文hash](single-player-empty-rosters-reset/repeat-validation.json) · [原检查点](single-player-empty-rosters-reset/checkpoints.json) · [每帧字段](single-player-empty-rosters-reset/frame-services.json) · [原手柄输入](single-player-empty-rosters-reset/input-plan.json) · [准备全文dump](single-player-empty-rosters-reset/preparation.json) · [原WAV](single-player-empty-rosters-reset/full-flow.wav)

## 真实双人开局：原败亡结局→另一玩家继续

15991帧，265检查点，11战前byte准备。

[回执](two-player-empty-rosters-continue/validation.json) · [双跑全文hash](two-player-empty-rosters-continue/repeat-validation.json) · [原检查点](two-player-empty-rosters-continue/checkpoints.json) · [每帧字段](two-player-empty-rosters-continue/frame-services.json) · [原手柄输入](two-player-empty-rosters-continue/input-plan.json) · [准备全文dump](two-player-empty-rosters-continue/preparation.json) · [原WAV](two-player-empty-rosters-continue/full-flow.wav)

## 资格对照：实际败北后的曹操仍被原名单接受

7935帧，87检查点，11战前byte准备。

[回执](former-leader-only-candidate/validation.json) · [双跑全文hash](former-leader-only-candidate/repeat-validation.json) · [原检查点](former-leader-only-candidate/checkpoints.json) · [每帧字段](former-leader-only-candidate/frame-services.json) · [原手柄输入](former-leader-only-candidate/input-plan.json) · [准备全文dump](former-leader-only-candidate/preparation.json) · [原WAV](former-leader-only-candidate/full-flow.wav)

