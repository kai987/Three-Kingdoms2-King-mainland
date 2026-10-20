# 原城市辅助字节：菜单与真实AI补兵五组对照

五案只运行固定原ROM与Nestopia；恢复源码未安装，帧字段不是Native内部CPU trace，原WAV不是Python合成。每个重复独立fresh process，整份序列化buffer未截断、未归一化；每个原frame还保留整buffer hash。

前三案公开phase13自然城市菜单母档和冻结原按钮计划。基线无core写；仅city11+1 0→44一byte或尾28..31 0→12/34/56/78hex四byte；完整四菜单、资料/武将选择与B取消、2220帧回world0/1。这2220帧RGB/PCM/全部RAM及观察owner/名册/金/预备兵/武将记录与基线相同。准备的SRAM字节与wholeState不同并持续保留，不能把本地no-observed-effect写成unused/padding或官方含义。

AI两案自然母档是phase15零write全年回放frame34623，原calendar[89,6]表示189年7月。原已有request0，city4首167；共同仅真gold9504→257两byte、167兵1000→900低一byte，保留天然reserve9499、原兵highbyte03和所有状态。仅target另改city4+1 0→44，原错位word由256变300；不改pointer、RNG、weights、request、ready、ack或controller。

原核心target第20帧真实167兵900→1000、reserve9499→9399，当时gold257/budget28；baseline没有补兵。完整原AI请求FF时baseline26帧末兵900/res9499/gold229/budget3，target27帧末兵1000/res9399/gold239/budget1。后续原策略可以改变金与预算，故这些Native整个请求结果不能与独立CPU两main或前缀的gold237/budget10/8混成一条trace；补兵本身没有统一300金币费用。

正式总计：6713首跑帧／13426双跑帧，113points；547非空artifact全文双跑相等（含55formal JSON）、5完整48k stereo16bit WAV；12公开准备byte写、5自然母档imports／0cold／0继承准备／0ready或result注入。

[总证据](evidence.json) · [总回执](validation.json) · [完整cohort比较](cohort-comparison.json) · [图像/WAV/准备/逐帧wholeState静态QA](static-validation.json) · [捕获脚本](../../../scripts/capture_city_auxiliary_fields.py)

## 自然城市菜单周期基线

2220原帧／34检查点／0准备byte。

[回执](city-menu-baseline/validation.json) · [双跑全文hash](city-menu-baseline/repeat-validation.json) · [真实检查点](city-menu-baseline/checkpoints.json) · [每帧字段/hash](city-menu-baseline/frame-services.json) · [原按钮/idle](city-menu-baseline/input-plan.json) · [全部准备与前后dump](city-menu-baseline/preparation.json) · [原WAV](city-menu-baseline/full-audio.wav)

## 仅城市11+1扰动44

2220原帧／34检查点／1准备byte。

[回执](city-menu-byte1-44/validation.json) · [双跑全文hash](city-menu-byte1-44/repeat-validation.json) · [真实检查点](city-menu-byte1-44/checkpoints.json) · [每帧字段/hash](city-menu-byte1-44/frame-services.json) · [原按钮/idle](city-menu-byte1-44/input-plan.json) · [全部准备与前后dump](city-menu-byte1-44/preparation.json) · [原WAV](city-menu-byte1-44/full-audio.wav)

## 仅城市11尾28..31分别标记

2220原帧／34检查点／4准备byte。

[回执](city-menu-tail-markers/validation.json) · [双跑全文hash](city-menu-tail-markers/repeat-validation.json) · [真实检查点](city-menu-tail-markers/checkpoints.json) · [每帧字段/hash](city-menu-tail-markers/frame-services.json) · [原按钮/idle](city-menu-tail-markers/input-plan.json) · [全部准备与前后dump](city-menu-tail-markers/preparation.json) · [原WAV](city-menu-tail-markers/full-audio.wav)

## 原AI请求：错位word256基线

26原帧／5检查点／3准备byte。

[回执](ai-reinforce-byte1-0/validation.json) · [双跑全文hash](ai-reinforce-byte1-0/repeat-validation.json) · [真实检查点](ai-reinforce-byte1-0/checkpoints.json) · [每帧字段/hash](ai-reinforce-byte1-0/frame-services.json) · [原按钮/idle](ai-reinforce-byte1-0/input-plan.json) · [全部准备与前后dump](ai-reinforce-byte1-0/preparation.json) · [原WAV](ai-reinforce-byte1-0/full-audio.wav)

## 原AI请求：错位word300／实际补兵

27原帧／6检查点／4准备byte。

[回执](ai-reinforce-byte1-44/validation.json) · [双跑全文hash](ai-reinforce-byte1-44/repeat-validation.json) · [真实检查点](ai-reinforce-byte1-44/checkpoints.json) · [每帧字段/hash](ai-reinforce-byte1-44/frame-services.json) · [原按钮/idle](ai-reinforce-byte1-44/input-plan.json) · [全部准备与前后dump](ai-reinforce-byte1-44/preparation.json) · [原WAV](ai-reinforce-byte1-44/full-audio.wav)

