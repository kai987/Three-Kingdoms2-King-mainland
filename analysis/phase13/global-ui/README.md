# 阶段13：独立全局UI控制、城市辅助与结局

本模块将此前尚用控制IR执行的全局UI入口恢复成独立 Python 源码：`source/recovered/global_ui_controller.py`。生产代码直接调用具名过程，使用条件、自然循环和有界状态表；不读取控制IR，不解释6502指令，不调用原CPU执行器。源码是依据原ROM重新写出的实现，不是原作者源码。

ROM保持只读，SHA256为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。所有证据中的文件偏移包含16字节iNES头：`16 + physical_bank*8192 + (CPU_address & 0x1FFF)`。

## 恢复入口与真实状态

| 领域 | 原入口与实际body | 真实控制字段 | 有界控制目录 |
|---|---|---|---|
| 固定主线程 | bank31 `E066` | `007A&1F` | 15项，单次更新止于下一个E066 |
| 城市辅助workers | pair29/30 `A009→ABD2`、`A00F→B989`、`A03F→BE36` | panel `0140/0150`、list `0478..047C`、animation `04A0/04A1/04A2` | 动画35kind及4setup phases |
| 城市辅助exports | 29 `A021→A77F`、`A024→A7B2`、`A02D→A78A`、`A039→BC71` | `005E` cadence、`6F05`值、parent `0401` | A039有6阶段表 |
| 标题/开局选择 | 10 `A003→11D717` | `0540/0541`，工作字节 `0542..0544` | 5main；26合法main/phase组合，含另一个23A021所有5phase |
| 新局/君主选择 | 8 `A024→9D70F` | `0540/0541`、`046C/046D`、`6F43` | main0的7phase |
| 结局显示 | 23 `A01E→24D693` | mode `0541`、phase `0542` | 6mode、17合法组合 |

银行内闭包共 **4583个原指令位置、163个过程root**：城市辅助2698/79、标题732/37、君主选择484/21、结局669/26。固定主loop目录另有398个位置，其中战斗、普通攻击、单挑的初始化继续复用已验证的 `SceneInitialization`。这些数目不是原作者函数总数，也不表示整款游戏全部分支已经穷尽。

NMI0/1原来均调用固定FA97；NMI2/6/7/8的固定框架已由阶段10 `BattleNMIServices` 恢复。本模块补银行内worker，不重复NMI保存/恢复、IRQ、OAM DMA或端口时间模拟。NMI2真正的城市主体是pair27/28 A000，属于阶段13 city领域；本模块的三个29辅助入口不是27城市主态表。主线程main2 physical10 A000的内政合作调用也不同于NMI6 physical10 A003的标题控制。

## 原机制与独立编排

固定E066读原15项表，保留004E/004F指针、AXYP与当前栈。main0冷显示设置进main9；main1建立city/NMI2并进main2；main9建立title/NMI6并进main10；main11请求新scenario SRAM初始化，建立NMI7并进main12；main13建立ending/NMI8并进main14。main10/12/14都是同一E3EB等待别名。主线程更新结束是E066边界，源码没有伪造RTS/RTI。

城市辅助请求和消费分开：0140的符号位触发panel初始化，007E bit08阻止新的panel行请求；A03F读取04A0，其正值请求1..35转换为kind0..34，04A0低位选择setup或active流程。队列生产者只设置原请求字节；不擅自清除007E、不宣称PPU上传已完成。35个kind目前按数字保留，不能仅凭动画内容推定官方命令名。

手写循环保留几个容易被通用结构化错误展平的原机制：AEC9的四组14tile行（源stride32）、CA4E的最多五组14tile包及早期FF、CB52的五组10tile行（源stride10、目标stride32）、DD0F的四色调色板分组及反复减16夹0F、D9DE的30城名册收集及byte游标回绕。Credits不去重、不扩大原缓冲；FE/FF、别名和溢出仍依原字节实现。

29A021不是姓名包：它检查 `(005E+5)&0F`，满足节奏时调用A7B2，将6F05这个byte转为BCD并请求header。A02D有不同的四拍节奏；A024直接请求同一header。正式字段称谓不由这个绘图helper单独推断。A7F6模板名义58字节，原Y=3A循环实际复制59字节，含A830的第一个opcode byte；该额外byte被当数据复制，生产代码不执行它。

结局6mode保留原分派：0为loss/extinction显示；1/2/3为此前评分低byte的不同结果显示；4为名册credits；5为最终文本。它不重新计算胜利、不清势力，不把“leaderFF事件”与完整所有权事务合并。E000冷reset路径仍是实际外部依赖。

## API与调用合同

```python
ui = GlobalUIController(memory, rom, services=exact_service_router)
result = ui.run_main(entry=0xE066, registers=actual_registers)
# 对银行入口用原始ServiceCall，保留已有真实caller frame：
result = ui(service_call)
# 仅在相同owner的真实依赖已有实现/输入后恢复：
result = ui.resume()
```

也可单独实例化 `CityUIWorkers`、`TitleUIController`、`RulerSelectionUIController`、`EndingUIController`，使用 `tick`、`run_entry`、`__call__` 和 `resume`。独立调用必须提供当前物理pair、数据窗和实际逻辑E1/E2/E3镜像；EE07返回根据逻辑镜像恢复银行，不是根据瞬时physical bank列表。Native前后RAM只是CPU试验母资料，不能冒称已经观测原core内的AXYP/SP。

`services(call)`只有明确返回字典 `status='returned'` 且PC/SP真的到达原caller时才允许继续。None/waiting/error/blocked，即使伪改了PC/SP，也不能推动后续控制。缺owner留在真实pending处；另一个caller不能借用该生成器。`_program`是Python协程continuation，不是旧program.json。

before/after已按各领域区分：城市使用0400/0401 parent与140/150/478/4A0..2；标题和君主使用540/541；结局使用541mode/542phase。0480是列表/包区域，不能标成标题主态；也不再借用战斗500/501/50A作这些UI的诊断名称。

## 原CPU对照与限制

最终当前回执 `validation.json`：**2432原CPU比较，2157完整返回、275严格前缀，0失败；另18个source guards**。完整返回中固定main表示“原调用SP未变并到下一E066”，不是原CPU的一次RTS，也不是完整NES帧。

两种source执行模式单列：pure_source **1124例**（1101完整、23前缀），源侧callee全部独立恢复，无原CPU回退；fixed_CPU **1308例**仅在验证器中执行原固定callee作为oracle，帮助隔离新银行body/flags/stack效果。实际原helper调用数在回执 `verification_only_original_CPU_callback_count` 中独立列出，不算生产能力。原CPU总数不会再加上这些helper调用，也不加35个动画前置fixture生成步骤。

新银行闭包的fixed_CPU模式比较全部2048B RAM与8192B SRAM、AXYP/SP/PC、mapper banks和有序端口读写。pure组合与固定main复用既有服务时，比较声明的1972B RAM（0000..01B3及0200..07FF）加当前活跃caller stack，并比较全部SRAM/寄存器/银行/端口；未使用的free-stack residue不在旧helper合同中，不能扩写成所有2KB精确一致。每例scope在回执中明列。

CPU fixtures来自不可改动的phase11 cold-battle母档，以及phase6 controlled unification-ending。PPUSTATUS128和双手柄0/0是两边相同的显式端口输入；部分fixture按原阶段准备空队列、文本闲置、字段和OAM cursor，不能把这些输入当作native已经完成消费。35个active动画后继输入由原CPU第一tick实际生成，不强写第二phase或结果；只准备下一调用的caller/OAM起点。两份29A021实际EE07入口快照也独立对照，来源明确为“从native帧末RAM重建的原CPU调用”，不是core内指令trace。

严格前缀保留E000冷reset、E05E的F3BD post-reset probe、main2内政A000、main4战术A000，以及调用者未装配的场景初始化服务。所有banked title/ruler/ending的本地控制已可执行；是否完成整帧取决于真实服务装配和NMI/IRQ/PPU时序。此次回执不生成像素或PCM，native画面/音频证据另见阶段13 runtime。

## 可复现命令

```sh
python3 scripts/analyze_global_ui_controller.py /Users/paulasmith/Downloads/三国志2超级版.nes
.venv-trace/bin/python scripts/verify_global_ui_controller.py /Users/paulasmith/Downloads/三国志2超级版.nes
```

`--quick`只供开发，不可作为最终收据。离线图和原汇编分别在 `offline-control-graph.json`、`original-ranges.asm`、`global-main.asm`；不可变表、+16偏移、REA旧档SHA及source/script pins在 `evidence.json`。生产代码不读取这些分析文件。既有冻结服务、旧native资料与版本化旧ZIP保持不改。共享GameEngine/coordinator已按新接口更新；旧阶段当前集成/审计回执由主任务重跑刷新pins，不能把这些当前回执称为旧冻结产物。
