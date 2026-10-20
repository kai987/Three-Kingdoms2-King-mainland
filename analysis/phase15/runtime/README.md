# Phase15：原核心长期回合、连续出征与受控战后继承

四案全部来自锁定原ROM/Nestopia。仅冷全年案没有状态导入与新增写入；其它三案导入公开母档，受控数据逐byte列明。恢复源码未安装进原核心，原图与48kHz双声道16bit PCM不是恢复源码生成。

首跑93596帧、双跑187192帧、957检查点。3891份非空产物整份hash一致，其中36份正式JSON；957份0B VRAM和957份含路径metadata排除。每跑独立新Python进程，不裁剪或归一化原serializebuffer。

冷全年案使用原城市招兵/分配命令消耗36张行动牌，十二次回到玩家回合，189年1月推进到190年1月。最初预备兵已满，部分请求数量被原上限守卫保留0；这是实际接受的行动，不称每次都增加兵数。五月等原月事件仅用普通A确认。每帧保存6F06、全30城owner、完整30城名册hash；检查点保存30×10名册及完整原SRAM。

连续两次出征在同一个导入实例完成原侵略、出兵、军粮、战场、退却和城市返回。第二战仅在战场准备敌指挥官XY两byte相邻坐标，原按键选择普通攻击；原前进数轮直到实际战斗对象数值降低，再在四列原菜单选择後退，返回战场后执行原退却消费者。两场以退却结束，不称两场胜利。

继承两案以自然战场母档为起点，公开准备曹操知力99/经验15000/等级7、AP30、四敌事前HP1/IQ10和四个唯一合法class0/4坐标。AP30是受控资源，不称自然可达。实际四次陥穽杀死191、51、167后最后袁绍8，原HP0/status3和六个active数组FF由原代码写入。候选案保留城3原袁谭9名册和原记录byte5=0/status2；无候选案另外把袁绍owned城市名册清空，属于异常受控准备。

原战后最终写ruler1 ID9或FF、城4owner2并回city0/sub1。两个继承案每帧6F8B仅观察FF，没有捕获FC/FB/ack1中间值，不能据此强认Domestic CA19/CB52/CA7F内部调用。具体原指令链和纯源码等价由独立CPU证据承担；此处仅证明已公开的数据准备后原核心实际死亡与战后写回结果。

每个准备组都有before/after完整2048B RAM与8192B SRAM，静态QA逐old→new重建全部差分；ready、结果、cache、request、ack、controller/global状态均未注入。每帧完整RAM/SRAM/RGB/PCM均hash，原active_controller区分真正场景与inactive残字节。检查点完整state含mapper/PPU，不把不可导出VRAM空文件当证据。

## 真实冷启动：189年1月至190年1月的十二次月回合

58186帧，620检查点，新增准备0byte写。actual cold189January→190January,12 original monthly returns and36 accepted command cards; no state import or additional core writes。

- [正式回执](cold-yearwrap/validation.json)
- [整份产物双跑](cold-yearwrap/repeat-validation.json)
- [原检查点/PNG](cold-yearwrap/checkpoints.json)
- [原逐帧字段](cold-yearwrap/frame-services.json)
- [实际按键](cold-yearwrap/input-plan.json)
- [准备与前后dump](cold-yearwrap/preparation.json)
- [原事件观察](cold-yearwrap/campaign-events.json)
- [完整原WAV](cold-yearwrap/full-flow.wav)

## 同实例两次出征与退却：第二战实际普通攻击交锋

17506帧，183检查点，新增准备2byte写。one disclosed natural city mother, two same-instance original invasion/army/supply/battle/retreat/return flows; second ordinary attack advances until actual object loss, then withdraws。

- [正式回执](consecutive-invasions-attack-return/validation.json)
- [整份产物双跑](consecutive-invasions-attack-return/repeat-validation.json)
- [原检查点/PNG](consecutive-invasions-attack-return/checkpoints.json)
- [原逐帧字段](consecutive-invasions-attack-return/frame-services.json)
- [实际按键](consecutive-invasions-attack-return/input-plan.json)
- [准备与前后dump](consecutive-invasions-attack-return/preparation.json)
- [原事件观察](consecutive-invasions-attack-return/campaign-events.json)
- [完整原WAV](consecutive-invasions-attack-return/full-flow.wav)

## 受控四敌连死：原战后候选9继承与城市返回

8952帧，77检查点，新增准备19byte写。controlled pre-combat data; four actual trap casts kill all four enemy officers, commander last; original postbattle ruler-ID9 orFF writeback, occupation and city return observed。

- [正式回执](succession-heir/validation.json)
- [整份产物双跑](succession-heir/repeat-validation.json)
- [原检查点/PNG](succession-heir/checkpoints.json)
- [原逐帧字段](succession-heir/frame-services.json)
- [实际按键](succession-heir/input-plan.json)
- [准备与前后dump](succession-heir/preparation.json)
- [原事件观察](succession-heir/campaign-events.json)
- [完整原WAV](succession-heir/full-flow.wav)

## 受控空名册与四敌连死：原战后君主FF结算

8952帧，77检查点，新增准备26byte写。controlled pre-combat data; four actual trap casts kill all four enemy officers, commander last; original postbattle ruler-ID9 orFF writeback, occupation and city return observed。

- [正式回执](succession-no-heir/validation.json)
- [整份产物双跑](succession-no-heir/repeat-validation.json)
- [原检查点/PNG](succession-no-heir/checkpoints.json)
- [原逐帧字段](succession-no-heir/frame-services.json)
- [实际按键](succession-no-heir/input-plan.json)
- [准备与前后dump](succession-no-heir/preparation.json)
- [原事件观察](succession-no-heir/campaign-events.json)
- [完整原WAV](succession-no-heir/full-flow.wav)

```sh
python3 scripts/capture_campaign_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --out analysis/phase15/runtime --repeat
```

[Manifest](evidence.json) · [汇总回执](validation.json) · [PNG/WAV/准备静态QA](static-validation.json)

冻结目录不可覆盖；复跑指定新的输出目录。探索文件不参与正式通过计数；静态QA不等于浏览器验收或人工听音，也不是内部CPU trace。
