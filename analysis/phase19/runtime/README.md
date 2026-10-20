# 阶段19：原模拟器输送命令与自然扩城月轮

原ROM和Nestopia未改。三组输送导入同一旧自然resource-menu母档；第四组真正冷启动，不导入存档或电池文件。所有双跑各用fresh Python进程，完整serialized API buffer不截断、不归一化。

三组都通过普通按键实际传送1金：城11 9999→9998、城14准备9899→9900，原行动卡3→2并回city0/1。共同仅准备目的城合法金容量2B；source+1组额外1B，destination tail组额外4B。对应完整准备前后2K/8K与每byte old→new见各案preparation和validation。

两扰动案与基线的2265实际帧RGB/PCM/2KRAM一致；实际SRAM与wholeState保留准备差异。所有150B辅助字节每帧保存且没有观察到原写入。这只说明该输送命令窗口没有可观察额外作用，不能证明unused/padding或正式名称。第三个输送数量对应city+16，仍叫raw第三项，不叫忠诚。

自然案原标题普通选择袁紹ruler1，自城1出征邻接中立0：原owner7→1、77原名册从1移至0、城数3→4、卡3→2。随后两次原征兵0数量且不分配兵力，原卡耗尽，实际月轮推进189年1月→2月并回ruler1世界界面。它是零前端内存写入的自然冷启动流程，未观察F8，更未验证其consumer/return。

探索最多四个普通月轮和同一自然allocation母档的八种正常确认时机仍无F8，保留在excluded exploratory目录，不作为正式通过病例或CPU内部trace。另行独立CPU分支覆盖不能改写这个Native负结果。

正式 4案；首跑17875帧／双跑35750帧；196检查点；856非空文件逐字节复跑（含44正式JSON）；11额外数据byte准备，1冷启动／3自然母档导入。

[总证据](evidence.json) · [回执](validation.json) · [静态RGB/WAV/全State检查](static-validation.json) · [跨组比较](cohort-comparison.json) · [捕获脚本](../../../scripts/capture_domestic_secondary_flows.py)

Native公开API的逐帧内存/画面/音频与独立原CPU指令验证是不同证据，未把原core的PCM称为源码波形合成。空0BVRAM和snapshot路径metadata JSON从非空复跑计数排除。

## resource-transfer-baseline
[结果](resource-transfer-baseline/validation.json) · [双跑](resource-transfer-baseline/repeat-validation.json) · [输入](resource-transfer-baseline/input-plan.json) · [逐帧字段](resource-transfer-baseline/frame-services.json) · [检查点](resource-transfer-baseline/checkpoints.json) · [原48kHz WAV](resource-transfer-baseline/full-audio.wav)

## resource-transfer-source-byte1-44
[结果](resource-transfer-source-byte1-44/validation.json) · [双跑](resource-transfer-source-byte1-44/repeat-validation.json) · [输入](resource-transfer-source-byte1-44/input-plan.json) · [逐帧字段](resource-transfer-source-byte1-44/frame-services.json) · [检查点](resource-transfer-source-byte1-44/checkpoints.json) · [原48kHz WAV](resource-transfer-source-byte1-44/full-audio.wav)

## resource-transfer-destination-tail
[结果](resource-transfer-destination-tail/validation.json) · [双跑](resource-transfer-destination-tail/repeat-validation.json) · [输入](resource-transfer-destination-tail/input-plan.json) · [逐帧字段](resource-transfer-destination-tail/frame-services.json) · [检查点](resource-transfer-destination-tail/checkpoints.json) · [原48kHz WAV](resource-transfer-destination-tail/full-audio.wav)

## natural-expansion-monthly-secondary-window
[结果](natural-expansion-monthly-secondary-window/validation.json) · [双跑](natural-expansion-monthly-secondary-window/repeat-validation.json) · [输入](natural-expansion-monthly-secondary-window/input-plan.json) · [逐帧字段](natural-expansion-monthly-secondary-window/frame-services.json) · [检查点](natural-expansion-monthly-secondary-window/checkpoints.json) · [原48kHz WAV](natural-expansion-monthly-secondary-window/full-audio.wav)
