# 阶段20：原Nestopia实际F8请求、选择、结算与AI续行

两案均为原ROM与原Nestopia真正冷启动，不导入state或battery，不写任何核心数据。沿冻结阶段19自然输入：标题选择袁紹、正常占领邻接中立城0令城数3→4、两次原征兵0数量消耗行动卡；第二次原分配菜单到おわり后额外无键等待73帧，再普通A确认。

73帧来自独立探索的有界8位正常输入相位扫描（命中即停）；正式两案重新从冷启动完整回放，未使用探索存档、RNG/策略权重准备或请求/回复/ready/PC注入。所有输入逐项公开。

原请求F8实际出现于10500帧，生产者ruler4/leader222、目标human ruler1/leader8、使者38，粮食报价与实际缓存均114。原city9/phase16显示原消息和横向选择；接受保持光标0、拒绝按Right至1，两者原A确认。

接受案实际reply0后清FF，原city2粮9999→9885、city4粮9999→10113，后续原帧再cap9999；双方外交原字节分别ruler1 [00,00,0A,00]与ruler4 [A0,00,00,00]。拒绝案实际reply1后清FF，回复当帧双方外交仍0、城2/4粮仍9999。后续AI继续执行，不能把最终月轮全部资源变化归因于这一请求。

每帧保存全部30城原32B/150B辅助字段、金粮/名册/owner、7君主完整8B及packed外交、报价与缓存、选择/文本/请求、实际保存的REG/PRG映射和原RGB/PCM/2KRAM/8KSRAM/wholeState hash。检查点保留全部原缓冲；首次F8前4/3/2/1真实帧另存，未重构或重新导入。君主byte1明确保留raw_byte1，未猜测正式含义。

正式2案，首跑23234帧／双跑46468帧，787检查点；3180非空文件精确复跑（含24正式JSON）。每run独立fresh Python进程，原serialized API全buffer不截断、不归一化。

[证据](evidence.json) · [回执](validation.json) · [原RGB/WAV/state静态QA](static-validation.json) · [捕获脚本](../../../scripts/capture_f8_native_flows.py)

原core逐帧C API观察与独立CPU指令验证分列；saved REG是边界快照，不是Native内部指令trace。原48000Hz双声道16bit PCM/WAV不称恢复源码的波形合成。0B VRAM和含目录路径的snapshot metadata JSON不计入非空精确复跑。

## natural-F8-accept
[回执](natural-F8-accept/validation.json) · [双跑](natural-F8-accept/repeat-validation.json) · [原输入](natural-F8-accept/input-plan.json) · [逐帧](natural-F8-accept/frame-services.json) · [检查点](natural-F8-accept/checkpoints.json) · [F8实际事件](natural-F8-accept/F8-events.json) · [原WAV](natural-F8-accept/full-audio.wav)

## natural-F8-reject
[回执](natural-F8-reject/validation.json) · [双跑](natural-F8-reject/repeat-validation.json) · [原输入](natural-F8-reject/input-plan.json) · [逐帧](natural-F8-reject/frame-services.json) · [检查点](natural-F8-reject/checkpoints.json) · [F8实际事件](natural-F8-reject/F8-events.json) · [原WAV](natural-F8-reject/full-audio.wav)
