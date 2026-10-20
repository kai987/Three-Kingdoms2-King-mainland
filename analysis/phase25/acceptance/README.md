# 整体逆向验收清单与现有缺口

本清单从本对话中的明确请求及冻结工程记录整理。当前不能宣称全ROM语义源码化；字节重建、多域源码对照和若干完整原流程已有证据。没有用候选减少或累计case数计算完成百分比。

“尽量整理成可读源码”是已有要求；独立可玩重制、原作者工程、源码编译成相同NES和新硬件模拟器列为建议扩展，没有自动算成用户已经提出的目标。字段确认需要有区分力的读写／实际行为依据，原作者的内部变量名不是要求。

## 来源与证据边界

需求摘录及逐维结果见 [requirements.json](requirements.json)。11项逐字摘录的原对话turn/message定位及相关用户原文见 [请求来源](request-provenance.json)，由阶段24通过应用read_thread核对，本轮只读复核其冻结来源及逐字映射；浏览器环境块没有当作请求。历史回执及正文作为归档证据读取，本脚本只核引用、哈希和源码语法，没有重跑历史游戏或覆盖旧输出。后期报告优先于冻结根README的旧阶段标题；新的更强对照不改写旧范围。

阶段25持续推进目标及选链／服务索引范围由协调对话报告，来源单列为coordinator_delegation_report，不冒充本对话的直接用户逐字指令。本轮执行边界是完成阶段25后等待父级评估，不自动开始阶段26。

未知服务总数仍为null。源码中出现external/dependency仅代表声明边界，必须结合实际mapper、entry与owner才能认定某服务缺失。详见 [源码边界清单](source-dependency-inventory.json)。

## A01 · 输入身份、字节与资源保全

来源：用户明确要求；关联请求 U01。

**验收状态：已验：原字节与资源身份；语义完成另项待验。**

本轮变化：本轮只读保持同一原ROM与全部历史身份；新观察核心单独建档和复跑。

本轮后仍缺：字节保全仍不等于全部语义或可编译源码恢复。

现有范围：原ROM与重建ROM身份、全部PRG/CHR字节提取及原始图形资源已有冻结证据；可读源码恢复与原字节重建分开验收。

已验结果与具体回执：

- 冻结父阶段记录：原ROM身份、全部字节重建、PRG/CHR提取和资源数量有原始回执。 [frozen_historical_byte_and_resource_receipt](../../verification.json)
- 冻结父阶段记录：本轮输入仍绑定同一ROM，完整原核/观察核起始state一致。 [new_Native_buffer_receipt](../../phase24/runtime/validation.json)
- 新原核/独立核的完整起始state与逐帧五缓冲相等；8个fresh实例。 [new_Native_identity_and_buffer_receipt](../runtime/validation.json)

待验／限制：

- 字节一致的NES重建不能证明语义恢复或高级源码编译成功。
- 根README冻结在历史阶段17标题，当前状态须优先看后期报告。

可执行验收方法：

1. 以只读验证器核对原ROM哈希和重建的每个字节。
2. 用同一不可变输入核对资源、表偏移及输出哈希；未转写姓名继续保留原字形。

证据：[analysis/verification.json](../../verification.json) · [analysis/phase23/verification.json](../../phase23/verification.json) · [README.md](../../../README.md) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/validation.json](../runtime/validation.json)

## A02 · 字段和数据表的语义

来源：用户明确要求；关联请求 U01, U03, U04, U09。

**验收状态：部分已验：存储行为；城市辅助字段和地形1正式名待验。**

本轮变化：确认G033实际城市3、8B58表指针、bank17读取及ID152登场；城库存+12/+13实际写入9899。城市+1/+28..31正式名称没有新增依据。

本轮后仍缺：城市辅助字段正式语义、地形1原名及高6位其他可能用途继续未决。

现有范围：主要武将/城市字段和存储行为已有恢复。地形1正式名未知；兵数高6位已有数值生成、保留、丢弃及全字消费证据，未证明独立旗标含义；适性3有表外读取实证。城市+1及+28..31仍未命名，+1/+2门槛已验证。

已验结果与具体回执：

- 冻结父阶段记录：既有字段结论和适性边界记录冻结保留。 [frozen_historical_field_report](../../phase16/README.md)
- 冻结父阶段记录：阶段23原模拟器对+1/+2比较做了自然/准备条件区分；未确证专用字段名称。 [frozen_Native_threshold_receipt](../../phase23/runtime/validation.json)
- 冻结父阶段记录：本轮证实配兵指针属于武将记录；没有新增城市辅助字段自然生产者。 [new_original_CPU_pointer_contract_receipt](../../phase24/fields-static/verification.json)
- G033实际C61F由城市3的8B58读取ID152；状态和名册真实写入。 [new_passive_opcode_and_bus_observations](../runtime/natural-appearance-pointer/opcode-observations.json)
- B441是指针JSR，真实库存写在27:B449/B44F；两dummy读和两写尝试分列。 [new_passive_actual_submission_observations](../runtime/natural-nonzero-reserve-submit/opcode-observations.json)

待验／限制：

- 城市辅助字段缺少足以命名的专用自然生产者/消费者及行为链。
- 地形1已有机制与像素，仍缺原名称或图例联接。
- 高6位写者的局部调查不是全ROM其他用途不存在的证明。

可执行验收方法：

1. 每个语义名称须对应完整读写链、有区分力的实际操作或原UI标签。
2. 检查边界及竞争解释；证据不能区分时保留raw和null名称。

证据：[source/recovered/troop_fields.py](../../../source/recovered/troop_fields.py) · [source/recovered/terrain_semantics.py](../../../source/recovered/terrain_semantics.py) · [analysis/phase16/README.md](../../phase16/README.md) · [analysis/phase23/README.md](../../phase23/README.md) · [analysis/phase23/runtime/evidence.json](../../phase23/runtime/evidence.json) · [analysis/phase23/runtime/validation.json](../../phase23/runtime/validation.json) · [analysis/phase24/fields-static/verification.json](../../phase24/fields-static/verification.json) · [analysis/phase25/runtime/natural-appearance-pointer/opcode-observations.json](../runtime/natural-appearance-pointer/opcode-observations.json) · [analysis/phase25/runtime/natural-nonzero-reserve-submit/opcode-observations.json](../runtime/natural-nonzero-reserve-submit/opcode-observations.json)

## A03 · 访问、原字节窗口和代码入口

来源：用户目标与工程验收方法分别标注；关联请求 U01, U10。

**验收状态：部分已验：2处新增有条件不交；339候选及raw入口待验。**

本轮变化：本轮仅对G033的C61F/C624新增两处条件不交，1187/81/258，候选341降至339；所有raw城市和Y域保留，raw255可越过A000至物理10窗口。

本轮后仍缺：裸入口、无前置指针合同及其它339候选未关闭；raw345入口证据不变，没有全局固定点或不可达证明。

现有范围：阶段25当前1526项可信间址访问为1187条件不交、81可能、258合同未知，剩339；阶段24基线为1185/81/260及341。本轮只选G033两读，原raw345分类104/13/228不变。

已验结果与具体回执：

- 冻结父阶段记录：本轮1526项为1185不交/81可能/260未知；351减至341，仅G086十处新证明。 [new_original_CPU_and_model_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：55组270未知生产者有排序；其余组未全面展开。 [new_static_inventory](../../phase24/fields-static/unknown-producer-ranking.json)
- 冻结父阶段记录：raw345保留104指令内部/13数据内部/228未证入口的基线账本。 [frozen_raw_entry_ledger](../../phase23/fields-static/raw345-executability-ledger.json)
- 新两个访问的正常前置合同及raw域保留，候选余339。 [new_original_CPU_contract_and_static_receipt](../fields-static/verification.json)
- 先比较两条链的实际入口、mapper和信息价值，再只选G033。 [new_selection_and_independent_probe_report](../fields-static/selection-comparison.json)

待验／限制：

- 指令账本是有界可信发现集，不是整块ROM所有可执行入口。
- 未知caller、mapper、完整指针生命周期及228个raw窗口仍待证。
- 证明任意损坏PC的全局行为属于更强工程目标，未见用户明确要求。
- py65只执行逻辑访问；IndY跨页额外dummy地址由官方核心规则推导，非跨页无额外读，不能说成py65实际总线观测。

可执行验收方法：

1. 每项保留bank/PC/raw/producer/caller和排除前提。
2. 逻辑有效地址与dummy读、may-write与must事实、正常caller与裸/raw反例分别核验。
3. 对请求中的游戏路径证明入口与服务归属；未决raw窗口保留来源，不静默删除。

证据：[analysis/phase23/fields-static/analysis-summary.json](../../phase23/fields-static/analysis-summary.json) · [analysis/phase23/fields-static/all-indirect-accesses.json](../../phase23/fields-static/all-indirect-accesses.json) · [analysis/phase23/fields-static/raw345-executability-ledger.json](../../phase23/fields-static/raw345-executability-ledger.json) · [analysis/phase24/fields-static/verification.json](../../phase24/fields-static/verification.json) · [analysis/phase24/fields-static/unknown-producer-ranking.json](../../phase24/fields-static/unknown-producer-ranking.json) · [analysis/phase25/fields-static/verification.json](../fields-static/verification.json) · [analysis/phase25/fields-static/selection-comparison.json](../fields-static/selection-comparison.json)

## A04 · 可读源码和服务闭包

来源：用户目标与工程验收方法分别标注；关联请求 U01, U02, U03, U05。

**验收状态：部分已验：选定服务和owner协议；整款服务闭包待验。**

本轮变化：具名D471乘法19指令/35B与实际C5D2调用协议已整合；2992子服务和45协调器比较共3037例，6guards。服务索引区分执行来源、可信静态与纯语法。

本轮后仍缺：服务索引是有界清单，尚未证明全款bank/entry/caller传递闭包；未知唯一服务数仍null。

现有范围：具名规则、控制器和owner在声明域内不运行原CPU/控制IR。本轮新增D471可读8×8乘法，旧C5D2继承；选定调用域与当前服务来源索引已验证，整款闭包仍未知。

已验结果与具体回执：

- 冻结父阶段记录：新具名配兵服务1038例=1036RTS+2严格前缀，5guards；无生产CPU/IR执行。 [new_source_vs_original_CPU_receipt](../../phase24/lifecycle/validation.json)
- 冻结父阶段记录：整合42例=41RTS+1非局部控制转移，3guards，真caller与owner恢复。 [new_coordinator_vs_original_CPU_receipt](../../phase24/source-integration.json)
- 2992源码比较=2991RTS+1严格缺F266前缀，3guards；旧C5D2正文继承。 [new_source_vs_original_CPU_receipt](../appearance/validation.json)
- 45协调器比较=44RTS+1非局部返回，3guards；含2个G033和1个B431真实被动调用。 [new_coordinator_vs_original_CPU_receipt](../source-integration.json)
- 服务索引按来源/owner/实际bank-entry-caller上下文分层；声明边界不等缺失函数数。 [new_readonly_service_inventory_receipt](../services/verification.json)

待验／限制：

- 已有按真实bank/entry/caller区分的有界服务索引，但没有覆盖全部请求路径及传递owner闭包。
- external/dependency标记不能直接当缺失服务数，须结合真实路由及暂停状态。
- 并非所有生成控制形态正文都具有同等可读性和动态覆盖。

可执行验收方法：

1. 通过最新具名协调器重放真实caller，不启用CPU/IR后门或人工ack。
2. 逐案核对完成、等待、越层、reset的PC/SP所有权；未决边界明确记录。
3. 交付函数/原ROM范围/依赖/验证索引，区分既有算法与新恢复的调用协议。

证据：[source/recovered/game_engine.py](../../../source/recovered/game_engine.py) · [source/recovered/scene_coordinator.py](../../../source/recovered/scene_coordinator.py) · [analysis/phase14/README.md](../../phase14/README.md) · [analysis/phase23/source-integration.json](../../phase23/source-integration.json) · [analysis/phase24/lifecycle/validation.json](../../phase24/lifecycle/validation.json) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/appearance/validation.json](../appearance/validation.json) · [analysis/phase25/source-integration.json](../source-integration.json) · [analysis/phase25/services/verification.json](../services/verification.json)

## A05 · 独立运行与更强重制目标

来源：工程验收建议；关联请求 U02。

**验收状态：未列为用户必需目标：独立可玩重制；现有可执行恢复范围另列A04。**

本轮变化：本轮保持可读软件服务范围，没有扩展成独立可玩重制。

本轮后仍缺：独立渲染/音频和完整宿主运行器仍是未选工程扩展。

现有范围：恢复源码能用ROM数据及显式硬件输入执行声明逻辑/服务；尚无独立合成整个NES音画的重制应用。

已验结果与具体回执：

- 冻结父阶段记录：可读服务能在显式硬件上下文执行，声明边界具备对照；不能据此宣称独立完整游戏。 [new_bounded_source_execution_receipt](../../phase24/source-integration.json)
- 新增具名算术及继承服务仍依赖显式硬件输入；没有新重制程序。 [new_bounded_source_receipt](../source-integration.json)

待验／限制：

- 未演示脱离原模拟器而完整可玩的宿主程序。
- 用户未明确要求原作者工程、移除全部ROM数据或源码编译成相同NES。

可执行验收方法：

1. 当前可读源码目标应提供声明软件服务的可执行driver及依赖日志，明确哪些输入仍需原硬件行为。
2. 若后续选择独立可玩移植，先另定输入、渲染、音频和验收范围，再把它列为必要完成门槛。

证据：[source/recovered/game_engine.py](../../../source/recovered/game_engine.py) · [source/recovered/campaign_session.py](../../../source/recovered/campaign_session.py) · [analysis/phase23/README.md](../../phase23/README.md) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/source-integration.json](../source-integration.json)

## A06 · NMI、IRQ、等待和重启交错

来源：用户目标与工程验收方法分别标注；关联请求 U03, U05, U06。

**验收状态：部分已验：声明的等待/reset/返回协议；全部交错待验。**

本轮变化：25协调器保留既有严格owner、非局部终止和reset退役；Native实际中断与无中断独立CPU、硬件夹具分开记录。

本轮后仍缺：未穷尽所有NMI/IRQ相位；模型端口及共同N163夹具不能冒称原机瞬时硬件状态。

现有范围：同一战役session、真实caller栈、NMI/IRQ软件服务、等待及reset退役已有有界对照。旧RAM掩码仍为历史限制，后续全RAM案例不追改旧范围。

已验结果与具体回执：

- 冻结父阶段记录：历史主循环/NMI/reset证据范围保留，不回写旧掩码限制。 [frozen_historical_service_report](../../phase15/README.md)
- 冻结父阶段记录：本轮新增协调器保留严格owner及reset退役协议。 [new_bounded_coordinator_receipt](../../phase24/source-integration.json)
- 严格真实caller、非局部终止和reset factory guards均通过。 [new_bounded_coordinator_receipt](../source-integration.json)
- 等待和有意缺依赖前缀按已实现owner分别索引。 [new_wait_and_closure_scope_ledger](../services/closure-status-ledger.json)

待验／限制：

- 尚未证明所有可能中断相位和交错。
- 不新增NMI的独立CPU续行可与后续Native随机/资源结算不同。
- 全时钟精确硬件等价是更强建议目标，不自动包含在可读源码恢复要求内。

可执行验收方法：

1. 对声明服务覆盖进入/等待/续程、嵌套忙路径、真实RTI/caller恢复及reset退役。
2. 记录实际事件顺序，按声明范围核全RAM/SRAM/寄存器/IO/mapper/N163；前缀和掩码限制保留。
3. Native观察与明确的新硬件夹具分列，不把人工新增NMI说成此前已目击的原机入口。

证据：[analysis/phase14/README.md](../../phase14/README.md) · [analysis/phase15/README.md](../../phase15/README.md) · [source/recovered/campaign_session.py](../../../source/recovered/campaign_session.py) · [source/recovered/scene_coordinator.py](../../../source/recovered/scene_coordinator.py) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/source-integration.json](../source-integration.json) · [analysis/phase25/services/closure-status-ledger.json](../services/closure-status-ledger.json)

## A07 · 图形、音频与硬件依赖

来源：用户目标与工程验收方法分别标注；关联请求 U01, U06。

**验收状态：部分已验：原核心完整音画等同及软件服务；全场景待验。**

本轮变化：两条自然续行路线原核/新独立观察核各fresh双跑，共424控制帧五buffer精确相同；212PNG和4完整WAV检查。

本轮后仍缺：这些音画由原硬件核心产生，未证明恢复Python独立合成；尚无全部场景/硬件交错覆盖。

现有范围：图形、文本、动画及音序软件producer/consumer已有恢复服务与原机RGB/PCM证据；完整PPU/APU/N163时钟、波形和视频帧合成仍使用固定原核心。

已验结果与具体回执：

- 冻结父阶段记录：本轮两核两次复跑728帧，五种完整buffer逐帧一致，26PNG/2WAV和1157复跑物核对。 [new_Native_buffer_and_repeat_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：既有表现软件服务恢复范围见阶段10，PPU/APU/N163硬件仍由原核心执行。 [frozen_historical_presentation_report](../../phase10/README.md)
- 424控制帧、1091份非空复跑、212PNG和4WAV精确核对，Source病例0。 [new_Native_media_and_repeat_receipt](../runtime/validation.json)

待验／限制：

- 原核心像素/音频不能证明恢复源码独立合成同样音画。
- 尚未覆盖每个场景、PPU队列、IRQ相位和音色组合。
- 另写替代硬件模拟器属于建议扩展范围。

可执行验收方法：

1. 按声明IO对照软件packet、OAM、PPU/APU/N163写入、银行及caller行为。
2. 逐帧精确比较未修改原核与独立观察核的RGB/PCM/RAM/SRAM/完整state，并保留完整WAV和原图。
3. 软件源码证据与原核心音画证据分别标识。

证据：[analysis/phase10/README.md](../../phase10/README.md) · [analysis/phase12/README.md](../../phase12/README.md) · [analysis/phase14/README.md](../../phase14/README.md) · [source/recovered/battle_presentation_services.py](../../../source/recovered/battle_presentation_services.py) · [source/recovered/exact_audio_requests.py](../../../source/recovered/exact_audio_requests.py) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/validation.json](../runtime/validation.json)

## A08 · 自然流程与异常边界

来源：用户目标与工程验收方法分别标注；关联请求 U05, U06, U07, U08, U11。

**验收状态：部分已验：所列自然和受控场景；未覆盖组合继续待验。**

本轮变化：自然ID152登场status1→2及非零城市库存提交9999→9899两路线均实际触发，祖先及新增准备均0、每run导入一次；区别于此前在野status0→2招募。

本轮后仍缺：仍未验证全部城市、君主、继承和长期胜利组合；新22/84帧续行不是新冷启动。

现有范围：已有零准备冷启动12个月战役、公开坐标准备的连续两战、受控战后继承/灭亡、自然F8接受/拒绝及自然释放到在野录用路线；每案起源和准备范围不同。

已验结果与具体回执：

- 冻结父阶段记录：12月战役和连续战斗各自起源/准备范围见原始场景证据。 [frozen_Native_campaign_receipt](../../phase15/runtime/evidence.json)
- 冻结父阶段记录：F8实际接受/拒绝结算按阶段20范围验证。 [frozen_Native_F8_receipt](../../phase20/runtime/evidence.json)
- 冻结父阶段记录：释放到在野招募成功在阶段22原机路线验证。 [frozen_Native_recruitment_receipt](../../phase22/runtime/evidence.json)
- 冻结父阶段记录：本轮新增一条自然配兵/退回/提交菜单路线，导入一次，祖先及新增准备均0。 [new_Native_allocation_receipt](../../phase24/runtime/validation.json)
- 实际登场和实际非零提交两条自然路线，无新增/祖先数值准备。 [new_Native_route_origin_and_effect_receipt](../runtime/evidence.json)

待验／限制：

- 受控继承和带准备的祖先不能称零准备自然战役。
- 尚未验证全部君主、战斗、继承组合或自然统一胜利。
- 完整自然胜利是有价值的建议端到端测试，未见用户直接提出为每轮必要门槛。

可执行验收方法：

1. 维护场景矩阵：关联请求、母档来源、冷启动/导入次数、继承/新增写、真实输入和终点。
2. 逐项区分已实际执行与未覆盖分支，按缺口追加有判别力的验证。
3. 若扩展自然全局胜利，用同一实例连续记录指令和状态链，不强制结果。

证据：[analysis/phase15/runtime/evidence.json](../../phase15/runtime/evidence.json) · [analysis/phase16/README.md](../../phase16/README.md) · [analysis/phase17/README.md](../../phase17/README.md) · [analysis/phase20/runtime/evidence.json](../../phase20/runtime/evidence.json) · [analysis/phase22/runtime/evidence.json](../../phase22/runtime/evidence.json) · [analysis/phase23/runtime/evidence.json](../../phase23/runtime/evidence.json) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/evidence.json](../runtime/evidence.json)

## A09 · 可复现、回归与归档

来源：用户目标与工程验收方法分别标注；关联请求 U01, U02, U06。

**验收状态：部分已验：历史归档及本轮分项来源；最终总审计与封包另见回执。**

本轮变化：v24及历史源码/证据/包冻结，本轮沿用只读总审计与小增量封包，来源/CRC/解压由最终回执记录。

本轮后仍缺：仍依赖v22/v23/v24、原ROM和锁定核心；本清单不会提前把未生成的封包回执当通过。

现有范围：冻结历史归档、来源哈希及本轮分项复跑已有证据；v25沿用v22完整包及v23/v24增量作为外部依赖。最终总审计和新ZIP由本轮verification.json/package-receipt.json分别确认，本清单不提前替代它们。

已验结果与具体回执：

- 冻结父阶段记录：v23增量全文件/解压/CRC和基线不变有冻结回执。 [frozen_postZIP_receipt](../../phase23/package-receipt.json)
- 冻结父阶段记录：本轮原始核、被动观察、五buffer和完整复跑检查已有分项回执。 [new_Native_receipt](../../phase24/runtime/validation.json)
- 本轮Native来源和重复运行已验证，最终包另由独立postZIP回执确认。 [new_Native_reproduction_receipt](../runtime/validation.json)

待验／限制：

- 隔离新环境仍需提供声明的锁定依赖及原ROM/核心。
- 许多历史producer有固定输出路径，不能覆盖冻结证据重跑。

可执行验收方法：

1. 先只读核旧pins，再让新producer只写新空目录。
2. 历史回归用新隔离harness/输出映射，保留其代码与数据来源，冻结产物不改。
3. 核精确归档允许清单、包含文件每字节、CRC及解压；外部基线依赖和排除项明确列出。

证据：[analysis/phase23/verification.json](../../phase23/verification.json) · [analysis/phase23/delivery-manifest.json](../../phase23/delivery-manifest.json) · [analysis/phase23/package-receipt.json](../../phase23/package-receipt.json) · [scripts/package_phase23_incremental.py](../../../scripts/package_phase23_incremental.py) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/validation.json](../runtime/validation.json)

## A10 · 整体成功的声明边界

来源：工程验收建议；关联请求 U01, U02, U09, U10。

**验收状态：尚未整体完成：字段、闭包和覆盖缺口明确待验。**

本轮变化：十维验收增加本轮变化和仍缺证据，字段、服务闭包与动态范围保持部分完成。

本轮后仍缺：不能以候选减少2或3037案例声明整体成功；无统一完成百分比。

现有范围：字节保全及多个有界语义/源码域已有证明；当前未知字段、服务闭包和覆盖缺口仍不足以支持全ROM语义源码化完成声明。

已验结果与具体回执：

- 冻结父阶段记录：本轮新增10处证明仍留341候选、260合同未知；不能按数字声称整体完成。 [new_static_and_original_CPU_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：最新整合有界执行通过，尚不是全ROM服务闭包证明。 [new_bounded_source_receipt](../../phase24/source-integration.json)
- 服务索引与10维缺口对应，unknown_unique_services=null、whole_game_service_closure_proven=false。 [new_service_acceptance_mapping](../services/acceptance-map.json)

待验／限制：

- 每项宽泛请求已在本清单建立有界状态和回执映射；仍须补齐该项尚缺证据，矩阵本身不能替代游戏验证。
- 候选数量、测试case总数和字节重建衡量不同，不能相加或计算统一完成百分比。

可执行验收方法：

1. 逐项将用户明确要求与其证据/未决项对应，在声明范围报告完成或部分完成。
2. 独立重制、硬件替代和穷尽证明继续标作建议，不追认为用户已授权的义务。
3. 即使本轮审计通过，也报告剩余未知和重要反例。

证据：[analysis/phase23/README.md](../../phase23/README.md) · [analysis/phase23/fields-static/analysis-summary.json](../../phase23/fields-static/analysis-summary.json) · [source/recovered/scene_coordinator.py](../../../source/recovered/scene_coordinator.py) · [analysis/phase24/fields-static/verification.json](../../phase24/fields-static/verification.json) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/services/acceptance-map.json](../services/acceptance-map.json)

## 本清单的检查

运行 `python3 scripts/verify_reverse_acceptance_phase25.py` 只生成本轮新目录的清单、语法边界及引用回执，不执行游戏。其他需要重放的验收项必须另写新输出driver或使用新空目录；不要直接重跑历史固定OUT生成器。

整体状态：尚未全部完成；本清单本身不是新的游戏验证，也不授权推送、发布或扩展成重制工程。
