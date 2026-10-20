# 阶段23：城市补兵重叠字的判别实验与资源依赖

本轮沿 `physical10:$BD97` 的完整补兵调用链继续分析。原模拟器的六组短对照证实，这条门槛不等同于“真实金币至少300”；城市 `+1`、`+28..31` 的正式名称仍未知，整体ROM语义恢复尚未完成。阶段1～22、原ROM、固定核心与版本归档保持冻结。

## 完整消费者及条件

既有具名 `BD7A..BEC6` 父过程保持原文件。它逐城调用 `11:D105` 取得完整城市指针并先限制金币、粮食，再比较城市归属与当前势力。只有归属匹配才在 `10:BD97` 读取 `city[1]`，随后读取 `city[2]`，按小端字与300比较。通过后继续扫描十个名册槽、挑选缺兵武将，才可能进入补兵结算；不能把局部门槛通过等同于任意城市必然补兵。

普通金币的字是 `LE16(city[2],city[3])`。这次比较用的是交叠的 `LE16(city[1],city[2])`，D105之后的精确条件为：

```text
gold = min(LE16(city[2],city[3]), 9999)
low = gold & 255
passes = low >= 2 or (low == 1 and city[1] >= 44)
```

因此low=0永远拒绝，low=1时受未知字节的43／44边界影响，low≥2通过。9999资源上限发生在检查之前，例如金币10000先变9999，不能把初始低字节当作检查时低字节。这个机器行为可以确认；它是否属于原作者的错位读取、历史布局兼容或其他设计意图，仍没有足够证据。

## 原模拟器判别实验

六案共享阶段22已自然取得的 `officer5-status2-frame14837.state`，祖先准备0。本轮各只导入一次，随后7或8帧无键续行至原request由0变FF；不是冷启动，也没有重跑上一轮长释放／招募路线。第一案新增准备0，后五案是明确的数值诊断。它们只改城2金币两字节，最后两案另改 `+1`；未准备兵数、库存、武将状态、名册、PC、RNG、request、答复或ready。

| 配置 | 真实金币 | +1 | 重叠字 | 第5帧武将5兵数 | 第5帧库存兵 | 原请求结束金币 |
|---|---:|---:|---:|---:|---:|---:|
| 自然续行 | 8888 | 0 | 47104 | 1000 | 7799 | 8850 |
| 诊断 | 257 | 0 | 256 | 700 | 8099 | 218 |
| 诊断 | 258 | 0 | 512 | 1000 | 7799 | 220 |
| 诊断 | 512 | 0 | 0 | 700 | 8099 | 473 |
| 诊断 | 257 | 43 | 299 | 700 | 8099 | 218 |
| 诊断 | 257 | 44 | 300 | 1000 | 7799 | 219 |

这组设计区分两种解释：真实金币258仍能补兵，而512反而不能；固定金币257，单改+1的43／44会改变分支。补兵三案第5帧均为兵700→1000、库存8099→7799、预算30→28，当帧金币保持输入值。最终金币还包含后续发展策略的真实费用，不是统一扣300金，也不能把最终差额直接归给补兵。

**快照时机：** `initial-sram.bin`、`initial-fields.json` 记录导入后、人工准备前的共同母态，六案城2 `+1/+2/+3` 都是 `[0,184,34]`，真实金币8888。诊断实验的起点是 `preparation.json` 中 `groups.after.SRAM` 指向的 `diagnostic-city2-numerical-counterfactual-after-sram.bin`，并由首帧实际SRAM复核；不是把准备前的initial文件改称257／258／512。准备前后完整RAM一致，SRAM只改变账本声明的2或3字节。

两核心各fresh双跑：六配置、24进程、180控制帧，其中固定原核心首跑45帧、双跑90帧。共12个配置准备字节、全部复跑48次实际准备写；自然配置为0。初始完整序列化缓冲及每帧RGB、PCM、2048B RAM、8192B SRAM、完整序列化API缓冲逐字节一致，未截断、补零或归一化。838份非空复跑文件、138张PNG及12份完整48kHz立体声WAV通过核验。

冻结观察核心共114条72B事件，只有已hook的 `BD97` 读取提供该opcode的实际 `+1` 总线字节；相邻帧的完整城市记录是frame envelope，不冒充未hook的 `+2` 瞬时trace。该短窗口没有辅助字段写入，只是局部负观察，不能证明全ROM无写者或字段unused。

[原核心路线、证据边界](runtime/README.md) · [原机证据](runtime/evidence.json) · [复跑回执](runtime/validation.json)

## 从真实PC到精确原CPU调用

每案新第3帧保存点实际PC为D6BA。独立原CPU从实际寄存器、栈、RAM／SRAM、PRG页与N163继续，不新增NMI／IRQ，不跳PC，不准备RNG或结果，2381条指令后到BD7A、2528条指令后到本城BD97，读取两个精确字节并走出与原模拟器一致的补兵／拒绝分支。

导出24个真实callee输入：六配置各含BD7A、返回BD90的D105、真实上层BD90下的D69D、D36F支付。自然四份无数值准备，诊断二十份继承各自原Native配置的公开2／3字节准备，独立CPU额外准备为0；不能把这些继承准备再计成新的原机写或自然可达证明。

这些是保存上下文后的独立CPU前序，不是固定原核心内部逐指令trace。其后续随机发展省略硬件NMI时序，最终金币可以不同，例如自然案独立CPU与原Native结算不同；精确局部门槛／补兵效果一致不能扩成整帧或整场战役完全等价。

[精确前序及输入来源](cpu-threshold/README.md) · [前序证据](cpu-threshold/evidence.json)

## 具名源码与验证域

新 [city_threshold_services.py](../../source/recovered/city_threshold_services.py) 只新增85个手工指令位置、149个原字节：

- `11:D105`，40B：`6000+32*rawA` 城市指针，真实ASL／ROL、资源限制调用、归属低三位返回；执行形式保留全部0..255 raw selector。
- `11:D69D`，51B：金币+2/+3、粮+4/+5先后比较10000并限制9999，保留读取、低／高字节写入顺序及flags；不写+1。
- `11:D36F`，58B：先限制、可选真实RNG附费、再次取指针和限制，再扣金或CLC拒绝；失败仍保留先前cap、RNG／暂存副作用。原补兵父过程忽略其carry，继续按原逻辑结算。

没有重拷已恢复的BD7A父过程，也没有原CPU、控制IR或动态代码生成进入生产源码。新的只读 `threshold_snapshot(city)` 仅检查真实0..29城市，解释D105之后的数据谓词，不修改内存，也不冒充CPU寄存器／栈协议。

新 [city_threshold_integration.py](../../source/recovered/city_threshold_integration.py) 将资源服务接入既有主循环所有者，保留阶段22战后释放工厂、真实caller PC/SP、招募非局部终态与reset所有者行为。

```python
from source.recovered.city_threshold_integration import CityThresholdGameEngine
game, registers = CityThresholdGameEngine.from_nestopia_state(rom_bytes, state_bytes)
coordinator = game.readable_scene_rules()
facts = game.city_threshold_services().threshold_snapshot(2)
# 继续既有ServiceCall／显式硬件服务协议；facts不执行或准备游戏流程。
```

源码服务比较3161案：3160真实RTS、1严格缺依赖前缀；5个guards、1项只读谓词模型检查（65536组输入）另计。入口整合38案：37 RTS、1真实非局部返回，3个guards另计。合计3199案源码／调用层比较，3197 RTS、1非局部、1依赖前缀；不是3199条不同自然战役。全2048B RAM、8192B SRAM、AXYP/SP/PC、有序IO、四个PRG银行及N163均比较，没有排除空闲栈。旧输入、受控夹具、新自然及诊断callee分别有来源标签。

另一个明确受控的完整BD7A原CPU／源码案例设金币1、+1=44、库存0：交叠字300通过，但购买所需40金支付失败，父流程仍忽略CLC并补至1000。它验证原代码的失败结算，不是本轮六组自然／诊断Native短路线中的第七条原机路线。

[源码原CPU回执](threshold/validation.json) · [原字节及动态位置](threshold/evidence.json) · [整合回执](source-integration.json)

## 候选分组、窗口和正式字段名

全部旧368项按共享指针、生产链、可信局部入口和已知incoming caller归组，原候选逐项保留。新增排除只接受完整关系合同及原CPU反例检查；原无界扫描、裸后缀、异常raw selector、无额外中断／外部改写前提，逻辑有效地址与dummy总线读仍分别记录。新模型不会把复用的零页0036在所有场景中都叫“当前城”。

最终共有110组；其中55个生产者未决组保留270项未知。17项新条件性排除使368→351；全部1526项为1175逻辑不交、81仍可能相交、270合同未决。新证明分别约束名单迭代17..26，以及完整资源调用的字段选择器6／8／14双字节或11单字节，没有给原无界首FF扫描强加十人上限。

模型只在完整有效地址域必定落到同一物理零页单元时建立“寄存器等于当前单元”的事实；若可能写零页或其他地址，只能失效旧事实，不能创建must关系。RAM镜像、未知callee及可能别名写均保留。独立复核发现并修正混合地址角落后，实际重生仍为17项；本次实际2轮加强、最多3轮上限，`complete_analysis_fixed_point_proven=false`。

新静态验证单列5643个原CPU合同：4107真实caller RTS、1024个CBA3 outward扫描前缀、512个两指令LDY／BMI前缀；不是5643个完整函数返回，也不是恢复Source比较。另有19项模型守卫，10个裸资源helper的+1／尾字段别名反例保留在原CPU合同矩阵中。

原345个raw窗口的口径仍是：104个位于已证指令内部、13个位于已有数据表内部、228个没有已证控制入口。账本归类或计数收紧不算新增动态覆盖，也不证明未知入口永不可执行。

城市+1仍缺可复现的专用自然生产者与足以说明用途的行为证据；+28..31也没有新的专用语义证据。D105／D69D／D36F不写+1只能说明这些明确服务的写域，不能推出全ROM无写者或正式命名为unused／padding／reserved。

[分组与合同说明](fields-static/README.md) · [共享生产者及调用者账本](fields-static/shared-producer-caller-groups.json) · [统计与当前剩余项](fields-static/analysis-summary.json) · [345窗口来源](fields-static/raw345-executability-ledger.json)

## 复现与交付

```sh
.venv-trace/bin/python scripts/verify_city_threshold_services.py ROM.nes
.venv-trace/bin/python scripts/verify_city_threshold_integration.py ROM.nes
.venv-trace/bin/python scripts/verify_city_auxiliary_phase23.py ROM.nes
python3 scripts/verify_phase23.py ROM.nes
```

正式Native目录已冻结；复跑请使用新空目录，命令见runtime说明。v23是小型增量包，包含可读源码、脚本与新证据，旧大产物以v22基线和SHA引用，不重复复制。包不含原NES、重建NES、完整ROM字节源或核心二进制；需要既有v22和用户自己的ROM复现。旧v22与通用完整归档不被替换，无推送或发布。

[交付范围](delivery-manifest.json) · [总审计](verification.json) · [交互证据页](index.html)；打包后另有归档外 `package-receipt.json`。本轮结束后停在阶段23，剩余候选、自然+1写入来源及硬件交错边界留待后续明确范围继续。
