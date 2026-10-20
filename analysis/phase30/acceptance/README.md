# 整体逆向验收清单与现有缺口

本清单从本对话中的明确请求及冻结工程记录整理。当前不能宣称全ROM语义源码化；字节重建、多域源码对照和若干完整原流程已有证据。没有用候选减少或累计case数计算完成百分比。

“尽量整理成可读源码”是已有要求；独立可玩重制、原作者工程、源码编译成相同NES和新硬件模拟器列为建议扩展，没有自动算成用户已经提出的目标。字段确认需要有区分力的读写／实际行为依据，原作者的内部变量名不是要求。

## 来源与证据边界

需求摘录及逐维结果见 [requirements.json](requirements.json)。11项逐字摘录的原对话turn/message定位及相关用户原文见 [请求来源](request-provenance.json)，由阶段24通过应用read_thread核对，本轮只读复核其冻结来源及逐字映射；浏览器环境块没有当作请求。历史回执及正文作为归档证据读取，本脚本只核引用、哈希和源码语法，没有重跑历史游戏或覆盖旧输出。后期报告优先于冻结根README的旧阶段标题；新的更强对照不改写旧范围。

阶段30获准一次的战后前两态与真实BC46调用协议、独立CC29姓名指针合同范围由协调对话报告，来源单列为coordinator_delegation_report，不冒充本对话的直接用户逐字指令。本轮执行边界是完成阶段30后等待父级评估，不自动开始阶段31。

未知服务总数仍为null。源码中出现external/dependency仅代表声明边界，必须结合实际mapper、entry与owner才能认定某服务缺失。详见 [源码边界清单](source-dependency-inventory.json)。

## A01 · 输入身份、字节与资源保全

来源：用户明确要求；关联请求 U01。

**验收状态：已验：原字节和核心身份；语义完成另项待验。**

本轮变化：相同ROM和固定原核心身份保全；三分窗原核/新观察核各fresh双跑，12流192控制帧的initial及逐帧完整RAM/SRAM/RGB/PCM/state一致，未归一化。

本轮后仍缺：字节、核心与新窗口自身复跑一致不等全部语义完成，也不宣称与冻结29历史同绝对帧五缓冲逐字重现。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：相同ROM和固定原核心身份保全；三分窗原核/新观察核各fresh双跑，12流192控制帧的initial及逐帧完整RAM/SRAM/RGB/PCM/state一致，未归一化。

已验结果与具体回执：

- 冻结父阶段记录：原ROM身份、全部字节重建、PRG/CHR提取和资源数量有原始回执。 [frozen_historical_byte_and_resource_receipt](../../verification.json)
- 冻结父阶段记录：本轮输入仍绑定同一ROM，完整原核/观察核起始state一致。 [new_Native_buffer_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：新原核/独立核的完整起始state与逐帧五缓冲相等；8个fresh实例。 [new_Native_identity_and_buffer_receipt](../../phase25/runtime/validation.json)
- 冻结父阶段记录：新观察核心、固定原核心及祖先身份分别记录；正式4fresh对照640控制帧通过。 [new_Native_identity_and_repeat_receipt](../../phase26/runtime/validation.json)
- 冻结父阶段记录：同一原ROM、冻结26的525个源码/脚本和45263个历史依赖身份继续保全；新观察核另立provenance，两路线8个fresh实例的完整初始及逐帧五缓冲一致。 [phase27_current_bounded_receipt](../../phase27/runtime/validation.json)
- 冻结父阶段记录：同一原ROM、原核心及冻结27审计/归档身份保全；新68u32观察核心另立来源。正式8fresh、384控制帧完整初始及逐帧五缓冲一致，96原核帧与冻结27同输入结果一致。 [phase28_current_bounded_receipt](../../phase28/runtime/validation.json)
- 冻结父阶段记录：同一原ROM、原核心与冻结28身份保全；新29观察核独立来源。两路线8fresh共384控制帧，完整初始与逐帧RAM/SRAM/RGB/PCM/未归一化state相同，96原核帧与冻结28一致。 [phase29_current_bounded_receipts](../../phase29/runtime/validation.json)
- 阶段30：原核与观察核新窗口12次fresh、完整五缓冲一致；本轮新增内存写0，12次母档导入。 [Native复跑回执](../runtime/validation.json)
- 阶段30：观察核与固定原核心来源分列；旧核心和ROM不改。 [核心来源](../runtime/core-provenance/build.json)

待验／限制：

- 字节、核心与新窗口自身复跑一致不等全部语义完成，也不宣称与冻结29历史同绝对帧五缓冲逐字重现。

可执行验收方法：

1. 以只读验证器核对原ROM哈希和重建的每个字节。
2. 用同一不可变输入核对资源、表偏移及输出哈希；未转写姓名继续保留原字形。

证据：[analysis/verification.json](../../verification.json) · [analysis/phase23/verification.json](../../phase23/verification.json) · [README.md](../../../README.md) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/validation.json](../../phase25/runtime/validation.json) · [analysis/phase26/runtime/validation.json](../../phase26/runtime/validation.json) · [analysis/phase27/runtime/validation.json](../../phase27/runtime/validation.json) · [analysis/phase27/runtime/core-provenance/build.json](../../phase27/runtime/core-provenance/build.json) · [analysis/phase28/runtime/validation.json](../../phase28/runtime/validation.json) · [analysis/phase28/runtime/core-provenance/build.json](../../phase28/runtime/core-provenance/build.json) · [analysis/phase29/runtime/validation.json](../../phase29/runtime/validation.json) · [analysis/phase29/runtime/evidence.json](../../phase29/runtime/evidence.json) · [analysis/phase29/runtime/core-provenance/build.json](../../phase29/runtime/core-provenance/build.json) · [analysis/phase30/runtime/validation.json](../runtime/validation.json) · [analysis/phase30/runtime/core-provenance/build.json](../runtime/core-provenance/build.json)

## A02 · 字段和数据表的语义

来源：用户明确要求；关联请求 U01, U03, U04, U09。

**验收状态：部分已验：controller和名单归属合同；城市辅助字段正式含义待验。**

本轮变化：前两态读取ruler+3 controller，保留human13/14交接，AI按原side/outcome选择mode0/1/2。自然mode0真实城名单四槽FF→8,191,51,167；这不是在野录用。城市+1/+28..31正式名继续null。

本轮后仍缺：rawruler、裸pointer别名与完整32B搬运不等正式字段用途；两项姓名ROM指针排除也不证明城市辅助字节unused。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：前两态读取ruler+3 controller，保留human13/14交接，AI按原side/outcome选择mode0/1/2。自然mode0真实城名单四槽FF→8,191,51,167；这不是在野录用。城市+1/+28..31正式名继续null。

已验结果与具体回执：

- 冻结父阶段记录：既有字段结论和适性边界记录冻结保留。 [frozen_historical_field_report](../../phase16/README.md)
- 冻结父阶段记录：阶段23原模拟器对+1/+2比较做了自然/准备条件区分；未确证专用字段名称。 [frozen_Native_threshold_receipt](../../phase23/runtime/validation.json)
- 冻结父阶段记录：本轮证实配兵指针属于武将记录；没有新增城市辅助字段自然生产者。 [new_original_CPU_pointer_contract_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：G033实际C61F由城市3的8B58读取ID152；状态和名册真实写入。 [new_passive_opcode_and_bus_observations](../../phase25/runtime/natural-appearance-pointer/opcode-observations.json)
- 冻结父阶段记录：B441是指针JSR，真实库存写在27:B449/B44F；两dummy读和两写尝试分列。 [new_passive_actual_submission_observations](../../phase25/runtime/natural-nonzero-reserve-submit/opcode-observations.json)
- 冻结父阶段记录：新自然观察8次实际ROM读与8次坐标存储配对，不能用帧末指针替代瞬时读；第二侧34×是历史文案更正。 [new_Native_read_store_pairs_and_static_erratum](../../phase26/runtime/deployment-observations.json)
- 冻结父阶段记录：G106实际读取城市4的+2/+4/+6/+8/+11/+14及相邻高字节；受控祖先路线7个字节变化、4次0→0写入，与随后C027的0→9999写入分开。城市+1及+28..31仍未正式命名。 [phase27_current_bounded_receipt](../../phase27/runtime/postbattle-observations.json)
- 冻结父阶段记录：C027精确协议保留当前城与逃将状态判定、原outcome字节索引、16位先wrap再cap9999及实际数据页作用；玩法公式已有旧源码，不计首次发现。城市+1/+28..31正式含义仍未知。 [phase28_current_bounded_receipt](../../phase28/parent-services/evidence.json)
- 冻结父阶段记录：精确收尾仅outcome0写citybyte0=(old&F0)|(0507>>4)，BC00按owner&0F只跳过7，在17..26十槽找首将并交换；原FF邻接与byteY回绕保留。城市+1/+28..31正式含义仍null，既有归属公式不记首次发现。 [phase29_current_bounded_receipts](../../phase29/completion-services/validation.json)
- 阶段30：自然BB8C mode0四次BDB8名单变化与controlled mode1仅collector写入分别保存。 [原机实际写入](../runtime/early-lifecycle-observations.json)
- 阶段30：F368正常七君主和raw7..15相邻字节/硬件边界分列，不擅自clamp。 [只读原字节合同](../context/ruler-and-name-pointer-boundaries.json)

待验／限制：

- rawruler、裸pointer别名与完整32B搬运不等正式字段用途；两项姓名ROM指针排除也不证明城市辅助字节unused。

可执行验收方法：

1. 每个语义名称须对应完整读写链、有区分力的实际操作或原UI标签。
2. 检查边界及竞争解释；证据不能区分时保留raw和null名称。

证据：[source/recovered/troop_fields.py](../../../source/recovered/troop_fields.py) · [source/recovered/terrain_semantics.py](../../../source/recovered/terrain_semantics.py) · [analysis/phase16/README.md](../../phase16/README.md) · [analysis/phase23/README.md](../../phase23/README.md) · [analysis/phase23/runtime/evidence.json](../../phase23/runtime/evidence.json) · [analysis/phase23/runtime/validation.json](../../phase23/runtime/validation.json) · [analysis/phase24/fields-static/verification.json](../../phase24/fields-static/verification.json) · [analysis/phase25/runtime/natural-appearance-pointer/opcode-observations.json](../../phase25/runtime/natural-appearance-pointer/opcode-observations.json) · [analysis/phase25/runtime/natural-nonzero-reserve-submit/opcode-observations.json](../../phase25/runtime/natural-nonzero-reserve-submit/opcode-observations.json) · [analysis/phase26/runtime/deployment-observations.json](../../phase26/runtime/deployment-observations.json) · [analysis/phase26/context/historical-wording-erratum.json](../../phase26/context/historical-wording-erratum.json) · [analysis/phase27/runtime/postbattle-observations.json](../../phase27/runtime/postbattle-observations.json) · [analysis/phase27/fields-static/verification.json](../../phase27/fields-static/verification.json) · [analysis/phase28/parent-services/evidence.json](../../phase28/parent-services/evidence.json) · [analysis/phase28/runtime/palette-lifecycle-observations.json](../../phase28/runtime/palette-lifecycle-observations.json) · [analysis/phase29/context/verification.json](../../phase29/context/verification.json) · [analysis/phase29/completion-services/validation.json](../../phase29/completion-services/validation.json) · [analysis/phase29/context/ownership-and-roster-contract.json](../../phase29/context/ownership-and-roster-contract.json) · [analysis/phase30/context/verification.json](../context/verification.json) · [analysis/phase30/runtime/early-lifecycle-observations.json](../runtime/early-lifecycle-observations.json) · [analysis/phase30/context/ruler-and-name-pointer-boundaries.json](../context/ruler-and-name-pointer-boundaries.json)

## A03 · 访问、原字节窗口和代码入口

来源：用户目标与工程验收方法分别标注；关联请求 U01, U10。

**验收状态：部分已验：本轮2处条件排除；326候选和raw入口待验。**

本轮变化：独立完整CC29合同7188原CPU=7172RTS+16显式前缀，另21模型/前提检查，Source0/Native0；仅CC92/CCAC两处unknown→conditional，1526=1200/81/245，剩326，raw345=104/13/228保持。

本轮后仍缺：仅正常ruler0..6、当次完整生命周期、binary且无NMI/IRQ模型适用；rawID保留0..255。裸CCAA读6001/601C/601F反例及raw硬件边界保留，未证明unused或全域固定点。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：独立完整CC29合同7188原CPU=7172RTS+16显式前缀，另21模型/前提检查，Source0/Native0；仅CC92/CCAC两处unknown→conditional，1526=1200/81/245，剩326，raw345=104/13/228保持。

已验结果与具体回执：

- 冻结父阶段记录：本轮1526项为1185不交/81可能/260未知；351减至341，仅G086十处新证明。 [new_original_CPU_and_model_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：55组270未知生产者有排序；其余组未全面展开。 [new_static_inventory](../../phase24/fields-static/unknown-producer-ranking.json)
- 冻结父阶段记录：raw345保留104指令内部/13数据内部/228未证入口的基线账本。 [frozen_raw_entry_ledger](../../phase23/fields-static/raw345-executability-ledger.json)
- 冻结父阶段记录：新两个访问的正常前置合同及raw域保留，候选余339。 [new_original_CPU_contract_and_static_receipt](../../phase25/fields-static/verification.json)
- 冻结父阶段记录：先比较两条链的实际入口、mapper和信息价值，再只选G033。 [new_selection_and_independent_probe_report](../../phase25/fields-static/selection-comparison.json)
- 冻结父阶段记录：本轮G107四点条件不交与完整raw域/反例保留，36443 OriginalCPU合同分为1624RTS、34816构造前缀、3裸读取前缀；Source0。 [new_original_CPU_contract_and_static_classification](../../phase26/fields-static/verification.json)
- 冻结父阶段记录：稳定1526条可信间址访问本轮新增7处有条件不交，变为1198不交、81可能、247未知，剩余328候选；5891个原CPU合同与16个模型guard通过，raw345分类104/13/228不变。 [phase27_current_bounded_receipt](../../phase27/fields-static/verification.json)
- 冻结父阶段记录：本轮聚焦父服务组合闭包，静态新排除0。冻结27账本1526＝1198条件不交＋81可能＋247未知，候选328；raw345＝104操作数/13数据/228未证控制窗口原样保留，没有新造phase28静态账本或重算完成比例。 [phase28_current_bounded_receipt](../../phase28/context/verification.json)
- 冻结父阶段记录：本轮0处新增静态排除。冻结27/28账本1526=1198条件不交+81可能+247未知，余328；raw345=104操作数/13数据/228未证入口。CC29两处typedROM指针仅上下文提案，不改权威。 [phase29_current_bounded_receipts](../../phase29/context/verification.json)
- 阶段30：7188独立原CPU合同、7172RTS/16prefix与21模型检查分列；8份旧29软件输入不是新Native现场。 [独立指针合同](../fields-static/verification.json)
- 阶段30：只变两处权威合同，其他1524和raw345账本不改。 [全1526账本](../fields-static/all-indirect-accesses.json)

待验／限制：

- 仅正常ruler0..6、当次完整生命周期、binary且无NMI/IRQ模型适用；rawID保留0..255。裸CCAA读6001/601C/601F反例及raw硬件边界保留，未证明unused或全域固定点。

可执行验收方法：

1. 每项保留bank/PC/raw/producer/caller和排除前提。
2. 逻辑有效地址与dummy读、may-write与must事实、正常caller与裸/raw反例分别核验。
3. 对请求中的游戏路径证明入口与服务归属；未决raw窗口保留来源，不静默删除。

证据：[analysis/phase23/fields-static/analysis-summary.json](../../phase23/fields-static/analysis-summary.json) · [analysis/phase23/fields-static/all-indirect-accesses.json](../../phase23/fields-static/all-indirect-accesses.json) · [analysis/phase23/fields-static/raw345-executability-ledger.json](../../phase23/fields-static/raw345-executability-ledger.json) · [analysis/phase24/fields-static/verification.json](../../phase24/fields-static/verification.json) · [analysis/phase24/fields-static/unknown-producer-ranking.json](../../phase24/fields-static/unknown-producer-ranking.json) · [analysis/phase25/fields-static/verification.json](../../phase25/fields-static/verification.json) · [analysis/phase25/fields-static/selection-comparison.json](../../phase25/fields-static/selection-comparison.json) · [analysis/phase26/fields-static/verification.json](../../phase26/fields-static/verification.json) · [analysis/phase27/fields-static/verification.json](../../phase27/fields-static/verification.json) · [analysis/phase27/fields-static/analysis-summary.json](../../phase27/fields-static/analysis-summary.json) · [analysis/phase28/context/verification.json](../../phase28/context/verification.json) · [analysis/phase28/context/analysis-summary.json](../../phase28/context/analysis-summary.json) · [analysis/phase29/context/verification.json](../../phase29/context/verification.json) · [analysis/phase29/context/auxiliary-field-links.json](../../phase29/context/auxiliary-field-links.json) · [analysis/phase30/fields-static/verification.json](../fields-static/verification.json) · [analysis/phase30/fields-static/all-indirect-accesses.json](../fields-static/all-indirect-accesses.json)

## A04 · 可读源码和服务闭包

来源：用户目标与工程验收方法分别标注；关联请求 U01, U02, U03, U05。

**验收状态：部分已验：A006四态精确服务；整款服务闭包待验。**

本轮变化：新Early服务410原位置/912codeB+6B分派表，A006四态声明域组合已对照。子域1546=1506受控+26复用29现场+14新30现场，1540RTS/6prefix/11guards；Root131=130RTS/1非局部/4guards。两层1677=1670RTS/1非局部/6prefix/15guards。

本轮后仍缺：四态精确服务仅声明normal及显式硬件夹具域，人类13/14交接维持原状，整款闭包仍false；旧process_ai_officers与CC29不是首次算法恢复，两个层级同一现场不能重复算独立输入。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：新Early服务410原位置/912codeB+6B分派表，A006四态声明域组合已对照。子域1546=1506受控+26复用29现场+14新30现场，1540RTS/6prefix/11guards；Root131=130RTS/1非局部/4guards。两层1677=1670RTS/1非局部/6prefix/15guards。

已验结果与具体回执：

- 冻结父阶段记录：新具名配兵服务1038例=1036RTS+2严格前缀，5guards；无生产CPU/IR执行。 [new_source_vs_original_CPU_receipt](../../phase24/lifecycle/validation.json)
- 冻结父阶段记录：整合42例=41RTS+1非局部控制转移，3guards，真caller与owner恢复。 [new_coordinator_vs_original_CPU_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：2992源码比较=2991RTS+1严格缺F266前缀，3guards；旧C5D2正文继承。 [new_source_vs_original_CPU_receipt](../../phase25/appearance/validation.json)
- 冻结父阶段记录：45协调器比较=44RTS+1非局部返回，3guards；含2个G033和1个B431真实被动调用。 [new_coordinator_vs_original_CPU_receipt](../../phase25/source-integration.json)
- 冻结父阶段记录：服务索引按来源/owner/实际bank-entry-caller上下文分层；声明边界不等缺失函数数。 [new_readonly_service_inventory_receipt](../../phase25/services/verification.json)
- 冻结父阶段记录：新协调器48=45继承回归+3真实被动callee，完整2048RAM/8192SRAM/AXYP-SP-PC/实际栈/四页/读写混合逻辑IO/共同N163相等；生产CPU/IR回调0。 [new_Source_composition_differential_receipt](../../phase26/source-integration.json)
- 冻结父阶段记录：恢复具名BF0A/BF9E/BFB3/BFEC精确协议118原指令位置/267B及18B表。旧battle_state_machine.py已有玩法算式，本轮不重复计首次发现。Source3197例与新前端58例通过；48旧回归与10新软件输入分列，BF9B为tail不造JSR帧。 [phase27_current_bounded_receipt](../../phase27/resources/evidence.json)
- 冻结父阶段记录：具名A006/BAB3/BB93/C027恢复78原位置170代码B及8B分派表，仅实现stage2。新增D4F5中段桥复用旧suffix两位置4代码B+2inline，保留EE07原栈/代码pair恢复与E1副作用。子服务1240及统一工厂80例通过，RTS/非局部/严格前缀分列；14现场输入不因两层Source重复对照算更多Native输入。 [phase28_current_bounded_receipt](../../phase28/parent-services/validation.json)
- 冻结父阶段记录：具名完成服务BBA0/BBB8/BC00及A006/BAB3路由提供81原位置/166B精确协议，2853案=2847RTS+6严格前缀，9guards。Root115案=110RTS+1既有非局部+4前缀，8guards；34份新软件输入含子域26及既有CC29/D4F0八份，不能重复当60份。 [phase29_current_bounded_receipts](../../phase29/completion-services/validation.json)
- 阶段30：1546软件对照案，1506受控/40软件输入(26旧29+14新30)，1540RTS+6prefix，11guards。 [EarlyServices原CPU对照](../early-services/validation.json)
- 阶段30：Root131=115继承+2新BB36受控+14新30软件输入，130RTS+1非局部/4guards。 [统一前门原CPU对照](../source-integration.json)
- 阶段30：410/410原位置命中不等全路径穷举；生产不运行原CPU或控制IR。 [源码与原字节证据](../early-services/evidence.json)

待验／限制：

- 四态精确服务仅声明normal及显式硬件夹具域，人类13/14交接维持原状，整款闭包仍false；旧process_ai_officers与CC29不是首次算法恢复，两个层级同一现场不能重复算独立输入。

可执行验收方法：

1. 通过最新具名协调器重放真实caller，不启用CPU/IR后门或人工ack。
2. 逐案核对完成、等待、越层、reset的PC/SP所有权；未决边界明确记录。
3. 交付函数/原ROM范围/依赖/验证索引，区分既有算法与新恢复的调用协议。

证据：[source/recovered/game_engine.py](../../../source/recovered/game_engine.py) · [source/recovered/scene_coordinator.py](../../../source/recovered/scene_coordinator.py) · [analysis/phase14/README.md](../../phase14/README.md) · [analysis/phase23/source-integration.json](../../phase23/source-integration.json) · [analysis/phase24/lifecycle/validation.json](../../phase24/lifecycle/validation.json) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/appearance/validation.json](../../phase25/appearance/validation.json) · [analysis/phase25/source-integration.json](../../phase25/source-integration.json) · [analysis/phase25/services/verification.json](../../phase25/services/verification.json) · [analysis/phase26/source-integration.json](../../phase26/source-integration.json) · [analysis/phase26/context/verification.json](../../phase26/context/verification.json) · [analysis/phase27/resources/evidence.json](../../phase27/resources/evidence.json) · [analysis/phase27/resources/validation.json](../../phase27/resources/validation.json) · [analysis/phase27/source-integration.json](../../phase27/source-integration.json) · [analysis/phase27/context/verification.json](../../phase27/context/verification.json) · [analysis/phase28/parent-services/validation.json](../../phase28/parent-services/validation.json) · [analysis/phase28/source-integration.json](../../phase28/source-integration.json) · [analysis/phase28/parent-services/evidence.json](../../phase28/parent-services/evidence.json) · [analysis/phase29/context/verification.json](../../phase29/context/verification.json) · [analysis/phase29/completion-services/validation.json](../../phase29/completion-services/validation.json) · [analysis/phase29/completion-services/evidence.json](../../phase29/completion-services/evidence.json) · [analysis/phase29/source-integration.json](../../phase29/source-integration.json) · [analysis/phase30/context/verification.json](../context/verification.json) · [analysis/phase30/early-services/validation.json](../early-services/validation.json) · [analysis/phase30/source-integration.json](../source-integration.json) · [analysis/phase30/early-services/evidence.json](../early-services/evidence.json)

## A05 · 独立运行与更强重制目标

来源：工程验收建议；关联请求 U02。

**验收状态：未列为用户必需目标：独立可玩重制；现有恢复范围见A04。**

本轮变化：继续可读源码、真实原CPU对照和原模拟器证据；没有自动扩成独立可玩重制、原作者工程或源码编译同一NES项目。

本轮后仍缺：独立可玩重制是建议扩展而非本次必需目标；需单独明确范围和验收。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：继续可读源码、真实原CPU对照和原模拟器证据；没有自动扩成独立可玩重制、原作者工程或源码编译同一NES项目。

已验结果与具体回执：

- 冻结父阶段记录：可读服务能在显式硬件上下文执行，声明边界具备对照；不能据此宣称独立完整游戏。 [new_bounded_source_execution_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：新增具名算术及继承服务仍依赖显式硬件输入；没有新重制程序。 [new_bounded_source_receipt](../../phase25/source-integration.json)
- 冻结父阶段记录：没有启动独立可玩重制或从高级源码重新编译NES；本轮仍沿既有可读恢复与原CPU对照范围推进。 [phase27_current_bounded_receipt](../../phase27/context/verification.json)
- 冻结父阶段记录：本轮维持可读源码和原CPU/原机验证目标，没有把独立重制或高级源码重编译同一NES列为本轮任务。 [phase28_current_bounded_receipt](../../phase28/context/verification.json)
- 冻结父阶段记录：本轮继续可读源码与原CPU/原机验证，没有自动把独立重制、原作者工程或高级源码编译同一NES列为必需目标。 [phase29_current_bounded_receipts](../../phase29/context/historical-credit.json)
- 阶段30：已有BC46玩法与精确协议credit分开，不用同名代码或旧case累计推整款完成。 [历史去重](../context/historical-credit-and-return-erratum.json)

待验／限制：

- 独立可玩重制是建议扩展而非本次必需目标；需单独明确范围和验收。

可执行验收方法：

1. 当前可读源码目标应提供声明软件服务的可执行driver及依赖日志，明确哪些输入仍需原硬件行为。
2. 若后续选择独立可玩移植，先另定输入、渲染、音频和验收范围，再把它列为必要完成门槛。

证据：[source/recovered/game_engine.py](../../../source/recovered/game_engine.py) · [source/recovered/campaign_session.py](../../../source/recovered/campaign_session.py) · [analysis/phase23/README.md](../../phase23/README.md) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/source-integration.json](../../phase25/source-integration.json) · [analysis/phase27/context/verification.json](../../phase27/context/verification.json) · [analysis/phase28/context/verification.json](../../phase28/context/verification.json) · [analysis/phase29/context/historical-credit.json](../../phase29/context/historical-credit.json) · [analysis/phase30/context/historical-credit-and-return-erratum.json](../context/historical-credit-and-return-erratum.json)

## A06 · NMI、IRQ、等待和重启交错

来源：用户目标与工程验收方法分别标注；关联请求 U03, U05, U06。

**验收状态：部分已验：真实返回与依赖续程；全部中断交错待验。**

本轮变化：原BB36→BC46→BB39(rawreturnBB38)与BB8C→BC46→BB8F(rawreturnBB8E)协议核实；new owner动态复核ECEE假returned无PC/SP推进、同call/owner/generator接真实Shared完成，阶段3fresh87 gate与device wait另列。

本轮后仍缺：字段合同无IRQ是前提检查，非动态IRQ测试；此服务域通过不等所有NMI/IRQ/重启交错已验。依赖前缀保持等待，不计普通成功。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：原BB36→BC46→BB39(rawreturnBB38)与BB8C→BC46→BB8F(rawreturnBB8E)协议核实；new owner动态复核ECEE假returned无PC/SP推进、同call/owner/generator接真实Shared完成，阶段3fresh87 gate与device wait另列。

已验结果与具体回执：

- 冻结父阶段记录：历史主循环/NMI/reset证据范围保留，不回写旧掩码限制。 [frozen_historical_service_report](../../phase15/README.md)
- 冻结父阶段记录：本轮新增协调器保留严格owner及reset退役协议。 [new_bounded_coordinator_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：严格真实caller、非局部终止和reset factory guards均通过。 [new_bounded_coordinator_receipt](../../phase25/source-integration.json)
- 冻结父阶段记录：等待和有意缺依赖前缀按已实现owner分别索引。 [new_wait_and_closure_scope_ledger](../../phase25/services/closure-status-ledger.json)
- 冻结父阶段记录：2009子服务对照含2严格F266前缀及7guards，假returned字符串不能替代原调用PC/SP；协调器另校核reset终止身份退役。 [new_Source_prefix_and_owner_lifecycle_receipts](../../phase26/deployment/validation.json)
- 冻结父阶段记录：新服务保留真实栈返回和BF9B尾跳；58整合对照包含既有非局部返回，4个owner/reset/依赖guard通过。无新NMI/IRQ注入，N163和设备端口是声明的共同fixture。 [phase27_current_bounded_receipt](../../phase27/source-integration.json)
- 冻结父阶段记录：纠正旧render_barrier标签：ECEE同步请求fade并立即RTS，未初始化8A；真实等待是BBA0多次新回调，原EC67/EC95推进完成。Source只闭合阶段2；共同端口/N163夹具非即时设备，13整合guard含同owner前缀恢复/原call对象保留/reset退休。 [phase28_current_bounded_receipt](../../phase28/source-integration.json)
- 冻结父阶段记录：BBA0每次读87，非负立即真实RTS，负值才调用BBB8；完成后写global1/city13/phase0，不清0501或伪造87。rawowner8缺5F20及故意不给服务均严格保留dependency；真正caller/owner/PC/SP与reset缓存清理另经guards。 新增子域A006/BB93两案与Root整父链一案真实驱动回归：缺ECEE先停，伪returned未推进PC/SP不继续，接回真实Shared后同一call/owner/generator完成且不重复请求。 [phase29_current_bounded_receipts](../../phase29/completion-services/validation.json)
- 阶段30：实际call为BB36/BB8C，返回BB39/BB8F；冻结旧BB37/BB8D标记只在新文档更正。 [父链与栈合同](../context/early-stage-branches-and-callers.json)
- 阶段30：新owner真实ECEE续程、fresh87及严格硬件/依赖前缀均按各case范围验收。 [新owner协议回归](../early-services/validation.json)
- 阶段30：统一前门继承ECEE回归动态重跑，另两案BB36 modes0/2真实JSR/SP/stack对照。 [Root协议回归](../source-integration.json)

待验／限制：

- 字段合同无IRQ是前提检查，非动态IRQ测试；此服务域通过不等所有NMI/IRQ/重启交错已验。依赖前缀保持等待，不计普通成功。

可执行验收方法：

1. 对声明服务覆盖进入/等待/续程、嵌套忙路径、真实RTI/caller恢复及reset退役。
2. 记录实际事件顺序，按声明范围核全RAM/SRAM/寄存器/IO/mapper/N163；前缀和掩码限制保留。
3. Native观察与明确的新硬件夹具分列，不把人工新增NMI说成此前已目击的原机入口。

证据：[analysis/phase14/README.md](../../phase14/README.md) · [analysis/phase15/README.md](../../phase15/README.md) · [source/recovered/campaign_session.py](../../../source/recovered/campaign_session.py) · [source/recovered/scene_coordinator.py](../../../source/recovered/scene_coordinator.py) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/source-integration.json](../../phase25/source-integration.json) · [analysis/phase25/services/closure-status-ledger.json](../../phase25/services/closure-status-ledger.json) · [analysis/phase26/deployment/validation.json](../../phase26/deployment/validation.json) · [analysis/phase27/source-integration.json](../../phase27/source-integration.json) · [analysis/phase27/resources/validation.json](../../phase27/resources/validation.json) · [analysis/phase28/source-integration.json](../../phase28/source-integration.json) · [analysis/phase28/runtime/palette-lifecycle-observations.json](../../phase28/runtime/palette-lifecycle-observations.json) · [analysis/phase28/context/verification.json](../../phase28/context/verification.json) · [analysis/phase29/context/verification.json](../../phase29/context/verification.json) · [analysis/phase29/completion-services/validation.json](../../phase29/completion-services/validation.json) · [analysis/phase29/source-integration.json](../../phase29/source-integration.json) · [analysis/phase29/runtime/palette-lifecycle-observations.json](../../phase29/runtime/palette-lifecycle-observations.json) · [analysis/phase30/context/verification.json](../context/verification.json) · [analysis/phase30/context/early-stage-branches-and-callers.json](../context/early-stage-branches-and-callers.json) · [analysis/phase30/early-services/validation.json](../early-services/validation.json) · [analysis/phase30/source-integration.json](../source-integration.json)

## A07 · 图形、音频与硬件依赖

来源：用户目标与工程验收方法分别标注；关联请求 U01, U06。

**验收状态：部分已验：原核192控制帧音画一致；全场景待验。**

本轮变化：三路8/32/8帧共48首帧、12fresh、192控制帧；每保存点35字段，两核共96PNG/6原WAV/879非空repeat，179547观察事件/138软件快照。各新窗口自身完整五缓冲一致。

本轮后仍缺：没有声称与冻结29历史绝对帧五缓冲一致；软件快照不等即时N163/PPU/APU，Source中的共享硬件夹具另列。全场景音画仍待验。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：三路8/32/8帧共48首帧、12fresh、192控制帧；每保存点35字段，两核共96PNG/6原WAV/879非空repeat，179547观察事件/138软件快照。各新窗口自身完整五缓冲一致。

已验结果与具体回执：

- 冻结父阶段记录：本轮两核两次复跑728帧，五种完整buffer逐帧一致，26PNG/2WAV和1157复跑物核对。 [new_Native_buffer_and_repeat_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：既有表现软件服务恢复范围见阶段10，PPU/APU/N163硬件仍由原核心执行。 [frozen_historical_presentation_report](../../phase10/README.md)
- 冻结父阶段记录：424控制帧、1091份非空复跑、212PNG和4WAV精确核对，Source病例0。 [new_Native_media_and_repeat_receipt](../../phase25/runtime/validation.json)
- 冻结父阶段记录：640控制帧完整五buffer未归一化逐字比较，非仅RAM或摘要。 [new_Native_full_buffers_media_repeat_receipt](../../phase26/runtime/validation.json)
- 冻结父阶段记录：自然64帧与受控祖先32帧，两核心各独立复跑；384控制帧完整RAM/SRAM/RGB/PCM/未归一化序列化state逐帧一致，864非空重复核验、192PNG和4WAV通过。 [phase27_current_bounded_receipt](../../phase27/runtime/validation.json)
- 冻结父阶段记录：原核/新观察核两路线各fresh双跑，384控制帧完整五缓冲逐字一致；1074非空复跑产物、192PNG/4WAV通过。95,903原事件/84完整软件快照；两路线各观察19次hold和原完成标志，晚新fade单列。 [phase28_current_bounded_receipt](../../phase28/runtime/validation.json)
- 冻结父阶段记录：原核/新观察核两路线各fresh双跑，384控制帧完整五缓冲逐字一致；1182非空复跑、192PNG/4WAV。256197原事件/120软件快照(56/64)，city逻辑读77/leader读12/邻接ROM读12/实际STA15及dummy15，1字节变化和14次同值store均保留。 [phase29_current_bounded_receipts](../../phase29/runtime/validation.json)
- 阶段30：3分窗48首帧/192控制帧、35字段/点、96PNG/6WAV和879非空复跑检查。 [Native原音画回执](../runtime/validation.json)
- 阶段30：原核无内部trace；被动观察核与原核5buffer逐帧对照，138软件快照不当即时设备状态。 [观察范围与来源](../runtime/evidence.json)

待验／限制：

- 没有声称与冻结29历史绝对帧五缓冲一致；软件快照不等即时N163/PPU/APU，Source中的共享硬件夹具另列。全场景音画仍待验。

可执行验收方法：

1. 按声明IO对照软件packet、OAM、PPU/APU/N163写入、银行及caller行为。
2. 逐帧精确比较未修改原核与独立观察核的RGB/PCM/RAM/SRAM/完整state，并保留完整WAV和原图。
3. 软件源码证据与原核心音画证据分别标识。

证据：[analysis/phase10/README.md](../../phase10/README.md) · [analysis/phase12/README.md](../../phase12/README.md) · [analysis/phase14/README.md](../../phase14/README.md) · [source/recovered/battle_presentation_services.py](../../../source/recovered/battle_presentation_services.py) · [source/recovered/exact_audio_requests.py](../../../source/recovered/exact_audio_requests.py) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/validation.json](../../phase25/runtime/validation.json) · [analysis/phase26/runtime/validation.json](../../phase26/runtime/validation.json) · [analysis/phase27/runtime/validation.json](../../phase27/runtime/validation.json) · [analysis/phase27/runtime/repeat-artifact-checks.json](../../phase27/runtime/repeat-artifact-checks.json) · [analysis/phase28/runtime/validation.json](../../phase28/runtime/validation.json) · [analysis/phase28/runtime/palette-lifecycle-observations.json](../../phase28/runtime/palette-lifecycle-observations.json) · [analysis/phase29/runtime/validation.json](../../phase29/runtime/validation.json) · [analysis/phase29/runtime/completion-lifecycle-observations.json](../../phase29/runtime/completion-lifecycle-observations.json) · [analysis/phase30/runtime/validation.json](../runtime/validation.json) · [analysis/phase30/runtime/evidence.json](../runtime/evidence.json)

## A08 · 自然流程与异常边界

来源：用户目标与工程验收方法分别标注；关联请求 U05, U06, U07, U08, U11。

**验收状态：部分已验：自然和受控分窗；连续人类交接与mode2自然覆盖待验。**

本轮变化：两个自然窗口准备0，受控窗口继承19已知字节和olderunknown；本轮均新增写0。Native看到BB8C modes0/1和四次名单变化；BB36/mode2仅受控CPU。自然human13中间1519帧未连续新跑。

本轮后仍缺：自然资源削减、BB36/mode2及完整人类13/14交接自然路线仍待验；不把分窗或受控祖先称完整连续自然战役。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：两个自然窗口准备0，受控窗口继承19已知字节和olderunknown；本轮均新增写0。Native看到BB8C modes0/1和四次名单变化；BB36/mode2仅受控CPU。自然human13中间1519帧未连续新跑。

已验结果与具体回执：

- 冻结父阶段记录：12月战役和连续战斗各自起源/准备范围见原始场景证据。 [frozen_Native_campaign_receipt](../../phase15/runtime/evidence.json)
- 冻结父阶段记录：F8实际接受/拒绝结算按阶段20范围验证。 [frozen_Native_F8_receipt](../../phase20/runtime/evidence.json)
- 冻结父阶段记录：释放到在野招募成功在阶段22原机路线验证。 [frozen_Native_recruitment_receipt](../../phase22/runtime/evidence.json)
- 冻结父阶段记录：本轮新增一条自然配兵/退回/提交菜单路线，导入一次，祖先及新增准备均0。 [new_Native_allocation_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：实际登场和实际非零提交两条自然路线，无新增/祖先数值准备。 [new_Native_route_origin_and_effect_receipt](../../phase25/runtime/evidence.json)
- 冻结父阶段记录：自然存档祖先来源、0数字准备、四次导入与160帧原输入逐项绑定，3实际callee保留完整软件caller。 [new_Native_natural_route_and_ancestry_receipt](../../phase26/runtime/evidence.json)
- 冻结父阶段记录：自然祖先路线BF0A提前返回；受控祖先路线实际触发15逻辑读、11STA写及11寻址dummy读，完整19项已知phase15准备与更早未知准备边界记录。27新增数值/PC/栈准备为0。10新软件callee输入为1自然+9受控。 [phase27_current_bounded_receipt](../../phase27/runtime/evidence.json)
- 冻结父阶段记录：自然早退64帧与受控祖先资源写32帧分别验证；受控继承19项已知历史准备、更早legacy准备未完全建立。本轮0新增数值/PC/结果/RNG/ready准备。14现场包含stage2直入口、D4F5实际中段及4个stage3严格前缀；BB93/D4F5最近实际转移未完整观察时保持null/unknown。 [phase28_current_bounded_receipt](../../phase28/runtime/evidence.json)
- 冻结父阶段记录：自然早退64帧与受控祖先资源损失32帧分列；本轮0新增写，受控继承19项已知准备、更早legacy边界未完全建立。34份软件输入来自自然/受控祖先各17份，完整CC29/D4F0新组合均真RTS；两路线均未观察非平凡名单交换。 [phase29_current_bounded_receipts](../../phase29/runtime/evidence.json)
- 阶段30：三路的BC46 actual_JSR/entry、mode targets、controller读、city roster writes与23hold/1completion按原事件分列。 [原机早期生命周期](../runtime/early-lifecycle-observations.json)
- 阶段30：2自然窗+1受控祖先窗，1519帧中间UI不在本轮连续观察范围。 [祖先与分窗披露](../runtime/evidence.json)
- 阶段30：BB36 modes0/2仅新受控软件对照，14新软件现场自然/受控各7。 [软件与Native分界](../source-integration.json)

待验／限制：

- 自然资源削减、BB36/mode2及完整人类13/14交接自然路线仍待验；不把分窗或受控祖先称完整连续自然战役。

可执行验收方法：

1. 维护场景矩阵：关联请求、母档来源、冷启动/导入次数、继承/新增写、真实输入和终点。
2. 逐项区分已实际执行与未覆盖分支，按缺口追加有判别力的验证。
3. 若扩展自然全局胜利，用同一实例连续记录指令和状态链，不强制结果。

证据：[analysis/phase15/runtime/evidence.json](../../phase15/runtime/evidence.json) · [analysis/phase16/README.md](../../phase16/README.md) · [analysis/phase17/README.md](../../phase17/README.md) · [analysis/phase20/runtime/evidence.json](../../phase20/runtime/evidence.json) · [analysis/phase22/runtime/evidence.json](../../phase22/runtime/evidence.json) · [analysis/phase23/runtime/evidence.json](../../phase23/runtime/evidence.json) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/evidence.json](../../phase25/runtime/evidence.json) · [analysis/phase26/runtime/evidence.json](../../phase26/runtime/evidence.json) · [analysis/phase27/runtime/evidence.json](../../phase27/runtime/evidence.json) · [analysis/phase27/source-integration.json](../../phase27/source-integration.json) · [analysis/phase27/runtime/README.md](../../phase27/runtime/README.md) · [analysis/phase28/runtime/evidence.json](../../phase28/runtime/evidence.json) · [analysis/phase28/source-integration.json](../../phase28/source-integration.json) · [analysis/phase28/cpu-parent/evidence.json](../../phase28/cpu-parent/evidence.json) · [analysis/phase29/context/verification.json](../../phase29/context/verification.json) · [analysis/phase29/runtime/evidence.json](../../phase29/runtime/evidence.json) · [analysis/phase29/source-integration.json](../../phase29/source-integration.json) · [analysis/phase29/runtime/completion-lifecycle-observations.json](../../phase29/runtime/completion-lifecycle-observations.json) · [analysis/phase30/context/verification.json](../context/verification.json) · [analysis/phase30/runtime/early-lifecycle-observations.json](../runtime/early-lifecycle-observations.json) · [analysis/phase30/runtime/evidence.json](../runtime/evidence.json) · [analysis/phase30/source-integration.json](../source-integration.json)

## A09 · 可复现、回归与归档

来源：用户目标与工程验收方法分别标注；关联请求 U01, U02, U06。

**验收状态：部分已验：分项回执与冻结历史身份；总审计归档见最终回执。**

本轮变化：41项只读context、7188独立原CPU字段合同、1677两层Source对照及192原机控制帧分别记账；10维摘要跨最终分项回执核，冻结29保留。

本轮后仍缺：浏览器QA、最终总审计与增量包以随后各正式回执为准，本清单不预写其passed；不通过更新旧SHA或重跑旧producer改变历史。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：41项只读context、7188独立原CPU字段合同、1677两层Source对照及192原机控制帧分别记账；10维摘要跨最终分项回执核，冻结29保留。

已验结果与具体回执：

- 冻结父阶段记录：v23增量全文件/解压/CRC和基线不变有冻结回执。 [frozen_postZIP_receipt](../../phase23/package-receipt.json)
- 冻结父阶段记录：本轮原始核、被动观察、五buffer和完整复跑检查已有分项回执。 [new_Native_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：本轮Native来源和重复运行已验证，最终包另由独立postZIP回执确认。 [new_Native_reproduction_receipt](../../phase25/runtime/validation.json)
- 冻结父阶段记录：本轮Source3197、整合58、静态5891、Native两路线和43项只读上下文检查分列回执，10验收维度重新核对；最终浏览器、总审计和小增量封包由独立回执记录。 [phase27_current_bounded_receipt](../../phase27/resources/validation.json)
- 冻结父阶段记录：子服务1240例、整合80例、Native384控制帧、46只读context检查分别记账；十维摘要与最新回执交叉核验。冻结27审计和小增量身份保留；最终浏览器/总审计/归档以独立外置回执为准。 [phase28_current_bounded_receipt](../../phase28/parent-services/validation.json)
- 冻结父阶段记录：Source子2853+Root115=2968案，2957RTS+1既有非局部+10严格前缀/17guards；58项只读context与Native384控制帧分别记账。冻结28评估/归档保留，逐维摘要交叉核正式回执；最终总审计与ZIP见外置回执。 [phase29_current_bounded_receipts](../../phase29/completion-services/validation.json)
- 阶段30：41项只读检查；Source/原CPU/Native均0，不重复计旧512/256。 [只读context](../context/verification.json)
- 阶段30：独立7188合同及21模型检查，与Source和Native不混计。 [字段合同回执](../fields-static/verification.json)
- 阶段30：最终子服务分组1546与依赖6前缀明确。 [源码回执](../early-services/validation.json)
- 阶段30：Root131真实前门与继承回归，0原CPUfallback/IR。 [整合回执](../source-integration.json)
- 阶段30：新3分窗12fresh完整缓冲复跑。 [原机回执](../runtime/validation.json)

待验／限制：

- 浏览器QA、最终总审计与增量包以随后各正式回执为准，本清单不预写其passed；不通过更新旧SHA或重跑旧producer改变历史。

可执行验收方法：

1. 先只读核旧pins，再让新producer只写新空目录。
2. 历史回归用新隔离harness/输出映射，保留其代码与数据来源，冻结产物不改。
3. 核精确归档允许清单、包含文件每字节、CRC及解压；外部基线依赖和排除项明确列出。

证据：[analysis/phase23/verification.json](../../phase23/verification.json) · [analysis/phase23/delivery-manifest.json](../../phase23/delivery-manifest.json) · [analysis/phase23/package-receipt.json](../../phase23/package-receipt.json) · [scripts/package_phase23_incremental.py](../../../scripts/package_phase23_incremental.py) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/validation.json](../../phase25/runtime/validation.json) · [analysis/phase27/resources/validation.json](../../phase27/resources/validation.json) · [analysis/phase27/source-integration.json](../../phase27/source-integration.json) · [analysis/phase27/fields-static/verification.json](../../phase27/fields-static/verification.json) · [analysis/phase27/runtime/validation.json](../../phase27/runtime/validation.json) · [analysis/phase27/context/verification.json](../../phase27/context/verification.json) · [analysis/phase28/parent-services/validation.json](../../phase28/parent-services/validation.json) · [analysis/phase28/source-integration.json](../../phase28/source-integration.json) · [analysis/phase28/runtime/validation.json](../../phase28/runtime/validation.json) · [analysis/phase28/context/verification.json](../../phase28/context/verification.json) · [analysis/phase29/context/verification.json](../../phase29/context/verification.json) · [analysis/phase29/completion-services/validation.json](../../phase29/completion-services/validation.json) · [analysis/phase29/source-integration.json](../../phase29/source-integration.json) · [analysis/phase29/runtime/validation.json](../../phase29/runtime/validation.json) · [analysis/phase30/context/verification.json](../context/verification.json) · [analysis/phase30/fields-static/verification.json](../fields-static/verification.json) · [analysis/phase30/early-services/validation.json](../early-services/validation.json) · [analysis/phase30/source-integration.json](../source-integration.json) · [analysis/phase30/runtime/validation.json](../runtime/validation.json)

## A10 · 整体成功的声明边界

来源：工程验收建议；关联请求 U01, U02, U09, U10。

**验收状态：尚未整体完成：字段、全局闭包与自然覆盖缺口待验。**

本轮变化：阶段30获准一次，完成后停待评估，不自动31。城市字段正式名与未知唯一服务数保持null，整款closurefalse，没有完成百分比。

本轮后仍缺：剩326候选、raw入口、未覆盖全局服务和完整自然交错/人类交接仍待验；不能以四态服务或候选减少宣称整款完成。

现有范围：冻结29继承范围见父assessment和逐项历史回执。阶段30：阶段30获准一次，完成后停待评估，不自动31。城市字段正式名与未知唯一服务数保持null，整款closurefalse，没有完成百分比。

已验结果与具体回执：

- 冻结父阶段记录：本轮新增10处证明仍留341候选、260合同未知；不能按数字声称整体完成。 [new_static_and_original_CPU_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：最新整合有界执行通过，尚不是全ROM服务闭包证明。 [new_bounded_source_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：服务索引与10维缺口对应，unknown_unique_services=null、whole_game_service_closure_proven=false。 [new_service_acceptance_mapping](../../phase25/services/acceptance-map.json)
- 冻结父阶段记录：城市辅助字段仍null；候选328、未知唯一服务总数null、整款服务闭包false。候选减少与累计case不折算完成百分比，完成27后等待评估，不自动启动28。 [phase27_current_bounded_receipt](../../phase27/fields-static/analysis-summary.json)
- 冻结父阶段记录：本轮有效增量是阶段2父链和精确补给协议，城市辅助字段仍null、未知唯一服务总数null、全款闭包false、剩328候选；无完成百分比。完成28后等待评估，不自动开始29。 [phase28_current_bounded_receipt](../../phase28/context/analysis-summary.json)
- 冻结父阶段记录：本轮推进阶段3精确收尾和既有CC29父链组合；城市正式名与未知唯一服务数仍null、全款闭包false、余328无完成百分比。完成29后等待父级评估，不自动开始30。 [phase29_current_bounded_receipts](../../phase29/context/verification.json)
- 阶段30：条件账本仅1200/81/245，余326，正式城市辅助名null；无固定点/unused证明。 [当前字段账本](../fields-static/analysis-summary.json)
- 阶段30：未知唯一服务数null、full game closurefalse。 [声明边界](../context/analysis-summary.json)

待验／限制：

- 剩326候选、raw入口、未覆盖全局服务和完整自然交错/人类交接仍待验；不能以四态服务或候选减少宣称整款完成。

可执行验收方法：

1. 逐项将用户明确要求与其证据/未决项对应，在声明范围报告完成或部分完成。
2. 独立重制、硬件替代和穷尽证明继续标作建议，不追认为用户已授权的义务。
3. 即使本轮审计通过，也报告剩余未知和重要反例。

证据：[analysis/phase23/README.md](../../phase23/README.md) · [analysis/phase23/fields-static/analysis-summary.json](../../phase23/fields-static/analysis-summary.json) · [source/recovered/scene_coordinator.py](../../../source/recovered/scene_coordinator.py) · [analysis/phase24/fields-static/verification.json](../../phase24/fields-static/verification.json) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/services/acceptance-map.json](../../phase25/services/acceptance-map.json) · [analysis/phase26/context/verification.json](../../phase26/context/verification.json) · [analysis/phase27/fields-static/analysis-summary.json](../../phase27/fields-static/analysis-summary.json) · [analysis/phase27/context/verification.json](../../phase27/context/verification.json) · [analysis/phase28/context/analysis-summary.json](../../phase28/context/analysis-summary.json) · [analysis/phase28/parent-services/evidence.json](../../phase28/parent-services/evidence.json) · [analysis/phase29/context/verification.json](../../phase29/context/verification.json) · [analysis/phase30/fields-static/analysis-summary.json](../fields-static/analysis-summary.json) · [analysis/phase30/context/analysis-summary.json](../context/analysis-summary.json)

## 本清单的检查

运行 `python3 scripts/verify_reverse_acceptance_phase30.py` 只生成本轮新目录的清单、语法边界及引用回执，不执行游戏。其他需要重放的验收项必须另写新输出driver或使用新空目录；不要直接重跑历史固定OUT生成器。

整体状态：尚未全部完成；本清单本身不是新的游戏验证，也不授权推送、发布或扩展成重制工程。
