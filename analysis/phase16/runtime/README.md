# Phase16：原战后继承、后续月轮、玩家败北与资料适性

四案都加载公开原核心母档，恢复源码未安装进Nestopia。候选／无候选案继承Phase15真实city13/0战后点：四敌已由旧原核心陥穽死亡，原事前19／26byte受控准备完整引用，但此轮新增writes为0。此轮重新执行的是原city13 AD81继承消费者和完整下一月轮，不冒称重新冷启动打完整战争。

首跑17581帧／双跑35162帧，251真实检查点、1076非空产物整份双跑一致，其中36正式JSON。另排除251份0B VRAM与251份路径metadata。每跑新的Python进程，原serializebuffer不裁切／规范化。4完整48kHz双声道16bit WAV和逐帧原PCM/RGB/RAM/SRAMhash保留。

候选案ruler1 ID8→9，下一月轮AI含0、1、3、4、5、6；无候选案ID8→FF，但下一月轮城1／3仍owner1且名册全FF，AI仅0、3、4、5、6。不能把leaderFF写回叫全部城市自动中立。月轮期间其它城的真实owner变化独立记录，不能擅自归因于继承。两案均从189年1月走到2月、预算恢复3并回playercity0/sub1。

玩家案只准备曹操事前HP1／武1、敌袁绍武99与敌XY相邻共5byte。真实普通攻击败北后曹操原health=FF、status低2=3，严格保留FF而非规范成0或称已证实肉体死亡。原city13/phase4要求地图选城：普通方向键选ownedcity11、原武将名单选于禁5并确认，原ruler2 ID131→5、忠诚写100、回playercity0/sub1。没有注入结果、controller、request、ready、ack、死亡标志或候选。

适性案从天然battlecursor母档，在同一个原核心只改变曹操flags11地址69EF的mid2（0Cmask），保留tier/status：packed12、16、1A、1E。每次原B打开完整资料十行再原A关闭；0平／1山／2水，code3从三个合法值表后读原机器码A0、0B／4A、4A，因此是越界乱码，不是官方第四能力。四张原完整PNG的字形区域[64,192,80,208]都有独立RGBhash；门户仅对原图做CSS像素放大，不制造字形图。

逐帧新增完整30城32B原记录、237武将status低2／byte5原值、城byte1／27／28..31、资料worker040C/D和0380packet；完整原2K RAM／8K SRAM在检查点导出，每帧整份hash。byte5、城未命名尾字段保持raw，不能据单次显示猜新含义。所有新准备组含before/after完整RAM／SRAM并按声明old→new逐字节重建。继承母档的准备和此轮实际写入分开计数。

原帧是frame-end观测，没有内部PC／callee trace。实际AD81/C132/C386归属由同轮独立原CPU证据承担；Native未捕获FC/FB/ack1，不强套Domestic CA19。静态QA只核原文件、同帧图/内存、WAV和准备差分，Root另做浏览器验收。

## 原city13候选继承→完整下一月轮

3880帧，75检查点；此轮新增0byte写，继承旧准备19byte。

- [回执](heir-city13-month/validation.json)
- [整份双跑](heir-city13-month/repeat-validation.json)
- [检查点原图](heir-city13-month/checkpoints.json)
- [全部原帧字段](heir-city13-month/frame-services.json)
- [原按钮](heir-city13-month/input-plan.json)
- [准备／前后dump](heir-city13-month/preparation.json)
- [原事件](heir-city13-month/campaign-events.json)
- [完整原WAV](heir-city13-month/full-flow.wav)

## 原city13无候选leaderFF→残余空城与君主跳过

3800帧，72检查点；此轮新增0byte写，继承旧准备26byte。

- [回执](no-heir-city13-month/validation.json)
- [整份双跑](no-heir-city13-month/repeat-validation.json)
- [检查点原图](no-heir-city13-month/checkpoints.json)
- [全部原帧字段](no-heir-city13-month/frame-services.json)
- [原按钮](no-heir-city13-month/input-plan.json)
- [准备／前后dump](no-heir-city13-month/preparation.json)
- [原事件](no-heir-city13-month/campaign-events.json)
- [完整原WAV](no-heir-city13-month/full-flow.wav)

## 原普通攻击败北→玩家选城／于禁接任

7935帧，88检查点；此轮新增5byte写，继承旧准备0byte。

- [回执](player-defeat-successor/validation.json)
- [整份双跑](player-defeat-successor/repeat-validation.json)
- [检查点原图](player-defeat-successor/checkpoints.json)
- [全部原帧字段](player-defeat-successor/frame-services.json)
- [原按钮](player-defeat-successor/input-plan.json)
- [准备／前后dump](player-defeat-successor/preparation.json)
- [原事件](player-defeat-successor/campaign-events.json)
- [完整原WAV](player-defeat-successor/full-flow.wav)

## 原资料适性0／1／2／3：正式三种与越界字形

1966帧，16检查点；此轮新增4byte写，继承旧准备0byte。

- [回执](affinity-pages/validation.json)
- [整份双跑](affinity-pages/repeat-validation.json)
- [检查点原图](affinity-pages/checkpoints.json)
- [全部原帧字段](affinity-pages/frame-services.json)
- [原按钮](affinity-pages/input-plan.json)
- [准备／前后dump](affinity-pages/preparation.json)
- [原事件](affinity-pages/campaign-events.json)
- [完整原WAV](affinity-pages/full-flow.wav)

```sh
python3 scripts/capture_succession_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase16/runtime --repeat
```

[Manifest](evidence.json) · [汇总](validation.json) · [静态QA](static-validation.json)

冻结产物不能覆盖，复跑使用新目录。探索不参与正式通过计数。
