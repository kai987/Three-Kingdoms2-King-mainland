# 整体逆向验收清单与现有缺口

本清单从本对话中的明确请求及冻结工程记录整理。当前不能宣称全ROM语义源码化；字节重建、多域源码对照和若干完整原流程已有证据。没有用候选减少或累计case数计算完成百分比。

“尽量整理成可读源码”是已有要求；独立可玩重制、原作者工程、源码编译成相同NES和新硬件模拟器列为建议扩展，没有自动算成用户已经提出的目标。字段确认需要有区分力的读写／实际行为依据，原作者的内部变量名不是要求。

## 来源与证据边界

需求摘录及逐维结果见 [requirements.json](requirements.json)。11项逐字摘录的原对话turn/message定位及相关用户原文见 [请求来源](request-provenance.json)，由阶段24通过应用read_thread核对，本轮只读复核其冻结来源及逐字映射；浏览器环境块没有当作请求。历史回执及正文作为归档证据读取，本脚本只核引用、哈希和源码语法，没有重跑历史游戏或覆盖旧输出。后期报告优先于冻结根README的旧阶段标题；新的更强对照不改写旧范围。

阶段28持续推进目标及战后阶段2同步调用链及后续NMI完成gate边界范围由协调对话报告，来源单列为coordinator_delegation_report，不冒充本对话的直接用户逐字指令。本轮执行边界是完成阶段28后等待父级评估，不自动开始阶段29。

未知服务总数仍为null。源码中出现external/dependency仅代表声明边界，必须结合实际mapper、entry与owner才能认定某服务缺失。详见 [源码边界清单](source-dependency-inventory.json)。

## A01 · 输入身份、字节与资源保全

来源：用户明确要求；关联请求 U01。

**验收状态：已验：原字节和核心身份；语义完成另项待验。**

本轮变化：同一原ROM、原核心及冻结27审计/归档身份保全；新68u32观察核心另立来源。正式8fresh、384控制帧完整初始及逐帧五缓冲一致，96原核帧与冻结27同输入结果一致。

本轮后仍缺：字节和核心身份保全仍不等于全部语义源码恢复。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：同一原ROM、原核心及冻结27审计/归档身份保全；新68u32观察核心另立来源。正式8fresh、384控制帧完整初始及逐帧五缓冲一致，96原核帧与冻结27同输入结果一致。

已验结果与具体回执：

- 冻结父阶段记录：原ROM身份、全部字节重建、PRG/CHR提取和资源数量有原始回执。 [frozen_historical_byte_and_resource_receipt](../../verification.json)
- 冻结父阶段记录：本轮输入仍绑定同一ROM，完整原核/观察核起始state一致。 [new_Native_buffer_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：新原核/独立核的完整起始state与逐帧五缓冲相等；8个fresh实例。 [new_Native_identity_and_buffer_receipt](../../phase25/runtime/validation.json)
- 冻结父阶段记录：新观察核心、固定原核心及祖先身份分别记录；正式4fresh对照640控制帧通过。 [new_Native_identity_and_repeat_receipt](../../phase26/runtime/validation.json)
- 冻结父阶段记录：同一原ROM、冻结26的525个源码/脚本和45263个历史依赖身份继续保全；新观察核另立provenance，两路线8个fresh实例的完整初始及逐帧五缓冲一致。 [phase27_current_bounded_receipt](../../phase27/runtime/validation.json)
- 同一原ROM、原核心及冻结27审计/归档身份保全；新68u32观察核心另立来源。正式8fresh、384控制帧完整初始及逐帧五缓冲一致，96原核帧与冻结27同输入结果一致。 [phase28_current_bounded_receipt](../runtime/validation.json)

待验／限制：

- 字节一致的NES重建不能证明语义恢复或高级源码编译成功。
- 根README冻结在历史阶段17标题，当前状态须优先看后期报告。
- 字节和核心身份保全仍不等于全部语义源码恢复。

可执行验收方法：

1. 以只读验证器核对原ROM哈希和重建的每个字节。
2. 用同一不可变输入核对资源、表偏移及输出哈希；未转写姓名继续保留原字形。

证据：[analysis/verification.json](../../verification.json) · [analysis/phase23/verification.json](../../phase23/verification.json) · [README.md](../../../README.md) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/validation.json](../../phase25/runtime/validation.json) · [analysis/phase26/runtime/validation.json](../../phase26/runtime/validation.json) · [analysis/phase27/runtime/validation.json](../../phase27/runtime/validation.json) · [analysis/phase27/runtime/core-provenance/build.json](../../phase27/runtime/core-provenance/build.json) · [analysis/phase28/runtime/validation.json](../runtime/validation.json) · [analysis/phase28/runtime/core-provenance/build.json](../runtime/core-provenance/build.json)

## A02 · 字段和数据表的语义

来源：用户明确要求；关联请求 U01, U03, U04, U09。

**验收状态：部分已验：资源回填精确协议；城市辅助字段正式含义待验。**

本轮变化：C027精确协议保留当前城与逃将状态判定、原outcome字节索引、16位先wrap再cap9999及实际数据页作用；玩法公式已有旧源码，不计首次发现。城市+1/+28..31正式含义仍未知。

本轮后仍缺：城市辅助字段、地形1正式名与兵数高6位其他用途待验；本轮零辅助命中不证明未使用。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：C027精确协议保留当前城与逃将状态判定、原outcome字节索引、16位先wrap再cap9999及实际数据页作用；玩法公式已有旧源码，不计首次发现。城市+1/+28..31正式含义仍未知。

已验结果与具体回执：

- 冻结父阶段记录：既有字段结论和适性边界记录冻结保留。 [frozen_historical_field_report](../../phase16/README.md)
- 冻结父阶段记录：阶段23原模拟器对+1/+2比较做了自然/准备条件区分；未确证专用字段名称。 [frozen_Native_threshold_receipt](../../phase23/runtime/validation.json)
- 冻结父阶段记录：本轮证实配兵指针属于武将记录；没有新增城市辅助字段自然生产者。 [new_original_CPU_pointer_contract_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：G033实际C61F由城市3的8B58读取ID152；状态和名册真实写入。 [new_passive_opcode_and_bus_observations](../../phase25/runtime/natural-appearance-pointer/opcode-observations.json)
- 冻结父阶段记录：B441是指针JSR，真实库存写在27:B449/B44F；两dummy读和两写尝试分列。 [new_passive_actual_submission_observations](../../phase25/runtime/natural-nonzero-reserve-submit/opcode-observations.json)
- 冻结父阶段记录：新自然观察8次实际ROM读与8次坐标存储配对，不能用帧末指针替代瞬时读；第二侧34×是历史文案更正。 [new_Native_read_store_pairs_and_static_erratum](../../phase26/runtime/deployment-observations.json)
- 冻结父阶段记录：G106实际读取城市4的+2/+4/+6/+8/+11/+14及相邻高字节；受控祖先路线7个字节变化、4次0→0写入，与随后C027的0→9999写入分开。城市+1及+28..31仍未正式命名。 [phase27_current_bounded_receipt](../../phase27/runtime/postbattle-observations.json)
- C027精确协议保留当前城与逃将状态判定、原outcome字节索引、16位先wrap再cap9999及实际数据页作用；玩法公式已有旧源码，不计首次发现。城市+1/+28..31正式含义仍未知。 [phase28_current_bounded_receipt](../parent-services/evidence.json)

待验／限制：

- 城市辅助字段缺少足以命名的专用自然生产者/消费者及行为链。
- 地形1已有机制与像素，仍缺原名称或图例联接。
- 高6位写者的局部调查不是全ROM其他用途不存在的证明。
- 城市辅助字段、地形1正式名与兵数高6位其他用途待验；本轮零辅助命中不证明未使用。

可执行验收方法：

1. 每个语义名称须对应完整读写链、有区分力的实际操作或原UI标签。
2. 检查边界及竞争解释；证据不能区分时保留raw和null名称。

证据：[source/recovered/troop_fields.py](../../../source/recovered/troop_fields.py) · [source/recovered/terrain_semantics.py](../../../source/recovered/terrain_semantics.py) · [analysis/phase16/README.md](../../phase16/README.md) · [analysis/phase23/README.md](../../phase23/README.md) · [analysis/phase23/runtime/evidence.json](../../phase23/runtime/evidence.json) · [analysis/phase23/runtime/validation.json](../../phase23/runtime/validation.json) · [analysis/phase24/fields-static/verification.json](../../phase24/fields-static/verification.json) · [analysis/phase25/runtime/natural-appearance-pointer/opcode-observations.json](../../phase25/runtime/natural-appearance-pointer/opcode-observations.json) · [analysis/phase25/runtime/natural-nonzero-reserve-submit/opcode-observations.json](../../phase25/runtime/natural-nonzero-reserve-submit/opcode-observations.json) · [analysis/phase26/runtime/deployment-observations.json](../../phase26/runtime/deployment-observations.json) · [analysis/phase26/context/historical-wording-erratum.json](../../phase26/context/historical-wording-erratum.json) · [analysis/phase27/runtime/postbattle-observations.json](../../phase27/runtime/postbattle-observations.json) · [analysis/phase27/fields-static/verification.json](../../phase27/fields-static/verification.json) · [analysis/phase28/parent-services/evidence.json](../parent-services/evidence.json) · [analysis/phase28/runtime/palette-lifecycle-observations.json](../runtime/palette-lifecycle-observations.json)

## A03 · 访问、原字节窗口和代码入口

来源：用户目标与工程验收方法分别标注；关联请求 U01, U10。

**验收状态：部分已验：本轮0处新增排除；328候选和raw入口待验。**

本轮变化：本轮聚焦父服务组合闭包，静态新排除0。冻结27账本1526＝1198条件不交＋81可能＋247未知，候选328；raw345＝104操作数/13数据/228未证控制窗口原样保留，没有新造phase28静态账本或重算完成比例。

本轮后仍缺：328候选与228个raw控制窗口继续待验；本轮无新增静态排除或独立CPU-only合同案例。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：本轮聚焦父服务组合闭包，静态新排除0。冻结27账本1526＝1198条件不交＋81可能＋247未知，候选328；raw345＝104操作数/13数据/228未证控制窗口原样保留，没有新造phase28静态账本或重算完成比例。

已验结果与具体回执：

- 冻结父阶段记录：本轮1526项为1185不交/81可能/260未知；351减至341，仅G086十处新证明。 [new_original_CPU_and_model_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：55组270未知生产者有排序；其余组未全面展开。 [new_static_inventory](../../phase24/fields-static/unknown-producer-ranking.json)
- 冻结父阶段记录：raw345保留104指令内部/13数据内部/228未证入口的基线账本。 [frozen_raw_entry_ledger](../../phase23/fields-static/raw345-executability-ledger.json)
- 冻结父阶段记录：新两个访问的正常前置合同及raw域保留，候选余339。 [new_original_CPU_contract_and_static_receipt](../../phase25/fields-static/verification.json)
- 冻结父阶段记录：先比较两条链的实际入口、mapper和信息价值，再只选G033。 [new_selection_and_independent_probe_report](../../phase25/fields-static/selection-comparison.json)
- 冻结父阶段记录：本轮G107四点条件不交与完整raw域/反例保留，36443 OriginalCPU合同分为1624RTS、34816构造前缀、3裸读取前缀；Source0。 [new_original_CPU_contract_and_static_classification](../../phase26/fields-static/verification.json)
- 冻结父阶段记录：稳定1526条可信间址访问本轮新增7处有条件不交，变为1198不交、81可能、247未知，剩余328候选；5891个原CPU合同与16个模型guard通过，raw345分类104/13/228不变。 [phase27_current_bounded_receipt](../../phase27/fields-static/verification.json)
- 本轮聚焦父服务组合闭包，静态新排除0。冻结27账本1526＝1198条件不交＋81可能＋247未知，候选328；raw345＝104操作数/13数据/228未证控制窗口原样保留，没有新造phase28静态账本或重算完成比例。 [phase28_current_bounded_receipt](../context/verification.json)

待验／限制：

- 指令账本是有界可信发现集，不是整块ROM所有可执行入口。
- 未知caller、mapper、完整指针生命周期及228个raw窗口仍待证。
- 证明任意损坏PC的全局行为属于更强工程目标，未见用户明确要求。
- py65只执行逻辑访问；IndY跨页额外dummy地址由官方核心规则推导，非跨页无额外读，不能说成py65实际总线观测。
- 328候选与228个raw控制窗口继续待验；本轮无新增静态排除或独立CPU-only合同案例。

可执行验收方法：

1. 每项保留bank/PC/raw/producer/caller和排除前提。
2. 逻辑有效地址与dummy读、may-write与must事实、正常caller与裸/raw反例分别核验。
3. 对请求中的游戏路径证明入口与服务归属；未决raw窗口保留来源，不静默删除。

证据：[analysis/phase23/fields-static/analysis-summary.json](../../phase23/fields-static/analysis-summary.json) · [analysis/phase23/fields-static/all-indirect-accesses.json](../../phase23/fields-static/all-indirect-accesses.json) · [analysis/phase23/fields-static/raw345-executability-ledger.json](../../phase23/fields-static/raw345-executability-ledger.json) · [analysis/phase24/fields-static/verification.json](../../phase24/fields-static/verification.json) · [analysis/phase24/fields-static/unknown-producer-ranking.json](../../phase24/fields-static/unknown-producer-ranking.json) · [analysis/phase25/fields-static/verification.json](../../phase25/fields-static/verification.json) · [analysis/phase25/fields-static/selection-comparison.json](../../phase25/fields-static/selection-comparison.json) · [analysis/phase26/fields-static/verification.json](../../phase26/fields-static/verification.json) · [analysis/phase27/fields-static/verification.json](../../phase27/fields-static/verification.json) · [analysis/phase27/fields-static/analysis-summary.json](../../phase27/fields-static/analysis-summary.json) · [analysis/phase28/context/verification.json](../context/verification.json) · [analysis/phase28/context/analysis-summary.json](../context/analysis-summary.json)

## A04 · 可读源码和服务闭包

来源：用户目标与工程验收方法分别标注；关联请求 U01, U02, U03, U05。

**验收状态：部分已验：阶段2父链及实际caller；整款服务闭包待验。**

本轮变化：具名A006/BAB3/BB93/C027恢复78原位置170代码B及8B分派表，仅实现stage2。新增D4F5中段桥复用旧suffix两位置4代码B+2inline，保留EE07原栈/代码pair恢复与E1副作用。子服务1240及统一工厂80例通过，RTS/非局部/严格前缀分列；14现场输入不因两层Source重复对照算更多Native输入。

本轮后仍缺：D4F5前CC29及A006阶段0/1/3仍未由本轮闭合；整款服务闭包待验，不能把原机后续放行当成Source3正文。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：具名A006/BAB3/BB93/C027恢复78原位置170代码B及8B分派表，仅实现stage2。新增D4F5中段桥复用旧suffix两位置4代码B+2inline，保留EE07原栈/代码pair恢复与E1副作用。子服务1240及统一工厂80例通过，RTS/非局部/严格前缀分列；14现场输入不因两层Source重复对照算更多Native输入。

已验结果与具体回执：

- 冻结父阶段记录：新具名配兵服务1038例=1036RTS+2严格前缀，5guards；无生产CPU/IR执行。 [new_source_vs_original_CPU_receipt](../../phase24/lifecycle/validation.json)
- 冻结父阶段记录：整合42例=41RTS+1非局部控制转移，3guards，真caller与owner恢复。 [new_coordinator_vs_original_CPU_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：2992源码比较=2991RTS+1严格缺F266前缀，3guards；旧C5D2正文继承。 [new_source_vs_original_CPU_receipt](../../phase25/appearance/validation.json)
- 冻结父阶段记录：45协调器比较=44RTS+1非局部返回，3guards；含2个G033和1个B431真实被动调用。 [new_coordinator_vs_original_CPU_receipt](../../phase25/source-integration.json)
- 冻结父阶段记录：服务索引按来源/owner/实际bank-entry-caller上下文分层；声明边界不等缺失函数数。 [new_readonly_service_inventory_receipt](../../phase25/services/verification.json)
- 冻结父阶段记录：新协调器48=45继承回归+3真实被动callee，完整2048RAM/8192SRAM/AXYP-SP-PC/实际栈/四页/读写混合逻辑IO/共同N163相等；生产CPU/IR回调0。 [new_Source_composition_differential_receipt](../../phase26/source-integration.json)
- 冻结父阶段记录：恢复具名BF0A/BF9E/BFB3/BFEC精确协议118原指令位置/267B及18B表。旧battle_state_machine.py已有玩法算式，本轮不重复计首次发现。Source3197例与新前端58例通过；48旧回归与10新软件输入分列，BF9B为tail不造JSR帧。 [phase27_current_bounded_receipt](../../phase27/resources/evidence.json)
- 具名A006/BAB3/BB93/C027恢复78原位置170代码B及8B分派表，仅实现stage2。新增D4F5中段桥复用旧suffix两位置4代码B+2inline，保留EE07原栈/代码pair恢复与E1副作用。子服务1240及统一工厂80例通过，RTS/非局部/严格前缀分列；14现场输入不因两层Source重复对照算更多Native输入。 [phase28_current_bounded_receipt](../parent-services/validation.json)

待验／限制：

- 已有按真实bank/entry/caller区分的有界服务索引，但没有覆盖全部请求路径及传递owner闭包。
- external/dependency标记不能直接当缺失服务数，须结合真实路由及暂停状态。
- 并非所有生成控制形态正文都具有同等可读性和动态覆盖。
- D4F5前CC29及A006阶段0/1/3仍未由本轮闭合；整款服务闭包待验，不能把原机后续放行当成Source3正文。

可执行验收方法：

1. 通过最新具名协调器重放真实caller，不启用CPU/IR后门或人工ack。
2. 逐案核对完成、等待、越层、reset的PC/SP所有权；未决边界明确记录。
3. 交付函数/原ROM范围/依赖/验证索引，区分既有算法与新恢复的调用协议。

证据：[source/recovered/game_engine.py](../../../source/recovered/game_engine.py) · [source/recovered/scene_coordinator.py](../../../source/recovered/scene_coordinator.py) · [analysis/phase14/README.md](../../phase14/README.md) · [analysis/phase23/source-integration.json](../../phase23/source-integration.json) · [analysis/phase24/lifecycle/validation.json](../../phase24/lifecycle/validation.json) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/appearance/validation.json](../../phase25/appearance/validation.json) · [analysis/phase25/source-integration.json](../../phase25/source-integration.json) · [analysis/phase25/services/verification.json](../../phase25/services/verification.json) · [analysis/phase26/source-integration.json](../../phase26/source-integration.json) · [analysis/phase26/context/verification.json](../../phase26/context/verification.json) · [analysis/phase27/resources/evidence.json](../../phase27/resources/evidence.json) · [analysis/phase27/resources/validation.json](../../phase27/resources/validation.json) · [analysis/phase27/source-integration.json](../../phase27/source-integration.json) · [analysis/phase27/context/verification.json](../../phase27/context/verification.json) · [analysis/phase28/parent-services/validation.json](../parent-services/validation.json) · [analysis/phase28/source-integration.json](../source-integration.json) · [analysis/phase28/parent-services/evidence.json](../parent-services/evidence.json)

## A05 · 独立运行与更强重制目标

来源：工程验收建议；关联请求 U02。

**验收状态：未列为用户必需目标：独立可玩重制；现有恢复范围见A04。**

本轮变化：本轮维持可读源码和原CPU/原机验证目标，没有把独立重制或高级源码重编译同一NES列为本轮任务。

本轮后仍缺：独立可玩重制未列为用户必需目标，另行要求须单独验收。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：本轮维持可读源码和原CPU/原机验证目标，没有把独立重制或高级源码重编译同一NES列为本轮任务。

已验结果与具体回执：

- 冻结父阶段记录：可读服务能在显式硬件上下文执行，声明边界具备对照；不能据此宣称独立完整游戏。 [new_bounded_source_execution_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：新增具名算术及继承服务仍依赖显式硬件输入；没有新重制程序。 [new_bounded_source_receipt](../../phase25/source-integration.json)
- 冻结父阶段记录：没有启动独立可玩重制或从高级源码重新编译NES；本轮仍沿既有可读恢复与原CPU对照范围推进。 [phase27_current_bounded_receipt](../../phase27/context/verification.json)
- 本轮维持可读源码和原CPU/原机验证目标，没有把独立重制或高级源码重编译同一NES列为本轮任务。 [phase28_current_bounded_receipt](../context/verification.json)

待验／限制：

- 未演示脱离原模拟器而完整可玩的宿主程序。
- 用户未明确要求原作者工程、移除全部ROM数据或源码编译成相同NES。
- 独立可玩重制未列为用户必需目标，另行要求须单独验收。

可执行验收方法：

1. 当前可读源码目标应提供声明软件服务的可执行driver及依赖日志，明确哪些输入仍需原硬件行为。
2. 若后续选择独立可玩移植，先另定输入、渲染、音频和验收范围，再把它列为必要完成门槛。

证据：[source/recovered/game_engine.py](../../../source/recovered/game_engine.py) · [source/recovered/campaign_session.py](../../../source/recovered/campaign_session.py) · [analysis/phase23/README.md](../../phase23/README.md) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/source-integration.json](../../phase25/source-integration.json) · [analysis/phase27/context/verification.json](../../phase27/context/verification.json) · [analysis/phase28/context/verification.json](../context/verification.json)

## A06 · NMI、IRQ、等待和重启交错

来源：用户目标与工程验收方法分别标注；关联请求 U03, U05, U06。

**验收状态：部分已验：同步请求和原NMI门控边界；全部交错待验。**

本轮变化：纠正旧render_barrier标签：ECEE同步请求fade并立即RTS，未初始化8A；真实等待是BBA0多次新回调，原EC67/EC95推进完成。Source只闭合阶段2；共同端口/N163夹具非即时设备，13整合guard含同owner前缀恢复/原call对象保留/reset退休。

本轮后仍缺：全部NMI/IRQ/等待/reset交错待验；当前NMI边界观察不证明所有busy/reentrant路径动态覆盖。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：纠正旧render_barrier标签：ECEE同步请求fade并立即RTS，未初始化8A；真实等待是BBA0多次新回调，原EC67/EC95推进完成。Source只闭合阶段2；共同端口/N163夹具非即时设备，13整合guard含同owner前缀恢复/原call对象保留/reset退休。

已验结果与具体回执：

- 冻结父阶段记录：历史主循环/NMI/reset证据范围保留，不回写旧掩码限制。 [frozen_historical_service_report](../../phase15/README.md)
- 冻结父阶段记录：本轮新增协调器保留严格owner及reset退役协议。 [new_bounded_coordinator_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：严格真实caller、非局部终止和reset factory guards均通过。 [new_bounded_coordinator_receipt](../../phase25/source-integration.json)
- 冻结父阶段记录：等待和有意缺依赖前缀按已实现owner分别索引。 [new_wait_and_closure_scope_ledger](../../phase25/services/closure-status-ledger.json)
- 冻结父阶段记录：2009子服务对照含2严格F266前缀及7guards，假returned字符串不能替代原调用PC/SP；协调器另校核reset终止身份退役。 [new_Source_prefix_and_owner_lifecycle_receipts](../../phase26/deployment/validation.json)
- 冻结父阶段记录：新服务保留真实栈返回和BF9B尾跳；58整合对照包含既有非局部返回，4个owner/reset/依赖guard通过。无新NMI/IRQ注入，N163和设备端口是声明的共同fixture。 [phase27_current_bounded_receipt](../../phase27/source-integration.json)
- 纠正旧render_barrier标签：ECEE同步请求fade并立即RTS，未初始化8A；真实等待是BBA0多次新回调，原EC67/EC95推进完成。Source只闭合阶段2；共同端口/N163夹具非即时设备，13整合guard含同owner前缀恢复/原call对象保留/reset退休。 [phase28_current_bounded_receipt](../source-integration.json)

待验／限制：

- 尚未证明所有可能中断相位和交错。
- 不新增NMI的独立CPU续行可与后续Native随机/资源结算不同。
- 全时钟精确硬件等价是更强建议目标，不自动包含在可读源码恢复要求内。
- 全部NMI/IRQ/等待/reset交错待验；当前NMI边界观察不证明所有busy/reentrant路径动态覆盖。

可执行验收方法：

1. 对声明服务覆盖进入/等待/续程、嵌套忙路径、真实RTI/caller恢复及reset退役。
2. 记录实际事件顺序，按声明范围核全RAM/SRAM/寄存器/IO/mapper/N163；前缀和掩码限制保留。
3. Native观察与明确的新硬件夹具分列，不把人工新增NMI说成此前已目击的原机入口。

证据：[analysis/phase14/README.md](../../phase14/README.md) · [analysis/phase15/README.md](../../phase15/README.md) · [source/recovered/campaign_session.py](../../../source/recovered/campaign_session.py) · [source/recovered/scene_coordinator.py](../../../source/recovered/scene_coordinator.py) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/source-integration.json](../../phase25/source-integration.json) · [analysis/phase25/services/closure-status-ledger.json](../../phase25/services/closure-status-ledger.json) · [analysis/phase26/deployment/validation.json](../../phase26/deployment/validation.json) · [analysis/phase27/source-integration.json](../../phase27/source-integration.json) · [analysis/phase27/resources/validation.json](../../phase27/resources/validation.json) · [analysis/phase28/source-integration.json](../source-integration.json) · [analysis/phase28/runtime/palette-lifecycle-observations.json](../runtime/palette-lifecycle-observations.json) · [analysis/phase28/context/verification.json](../context/verification.json)

## A07 · 图形、音频与硬件依赖

来源：用户目标与工程验收方法分别标注；关联请求 U01, U06。

**验收状态：部分已验：原核384控制帧完整音画一致；全场景待验。**

本轮变化：原核/新观察核两路线各fresh双跑，384控制帧完整五缓冲逐字一致；1074非空复跑产物、192PNG/4WAV通过。95,903原事件/84完整软件快照；两路线各观察19次hold和原完成标志，晚新fade单列。

本轮后仍缺：全场景音画与全部硬件交互待验；瞬时软件快照不等于即时PPU/APU/N163设备状态。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：原核/新观察核两路线各fresh双跑，384控制帧完整五缓冲逐字一致；1074非空复跑产物、192PNG/4WAV通过。95,903原事件/84完整软件快照；两路线各观察19次hold和原完成标志，晚新fade单列。

已验结果与具体回执：

- 冻结父阶段记录：本轮两核两次复跑728帧，五种完整buffer逐帧一致，26PNG/2WAV和1157复跑物核对。 [new_Native_buffer_and_repeat_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：既有表现软件服务恢复范围见阶段10，PPU/APU/N163硬件仍由原核心执行。 [frozen_historical_presentation_report](../../phase10/README.md)
- 冻结父阶段记录：424控制帧、1091份非空复跑、212PNG和4WAV精确核对，Source病例0。 [new_Native_media_and_repeat_receipt](../../phase25/runtime/validation.json)
- 冻结父阶段记录：640控制帧完整五buffer未归一化逐字比较，非仅RAM或摘要。 [new_Native_full_buffers_media_repeat_receipt](../../phase26/runtime/validation.json)
- 冻结父阶段记录：自然64帧与受控祖先32帧，两核心各独立复跑；384控制帧完整RAM/SRAM/RGB/PCM/未归一化序列化state逐帧一致，864非空重复核验、192PNG和4WAV通过。 [phase27_current_bounded_receipt](../../phase27/runtime/validation.json)
- 原核/新观察核两路线各fresh双跑，384控制帧完整五缓冲逐字一致；1074非空复跑产物、192PNG/4WAV通过。95,903原事件/84完整软件快照；两路线各观察19次hold和原完成标志，晚新fade单列。 [phase28_current_bounded_receipt](../runtime/validation.json)

待验／限制：

- 原核心像素/音频不能证明恢复源码独立合成同样音画。
- 尚未覆盖每个场景、PPU队列、IRQ相位和音色组合。
- 另写替代硬件模拟器属于建议扩展范围。
- 全场景音画与全部硬件交互待验；瞬时软件快照不等于即时PPU/APU/N163设备状态。

可执行验收方法：

1. 按声明IO对照软件packet、OAM、PPU/APU/N163写入、银行及caller行为。
2. 逐帧精确比较未修改原核与独立观察核的RGB/PCM/RAM/SRAM/完整state，并保留完整WAV和原图。
3. 软件源码证据与原核心音画证据分别标识。

证据：[analysis/phase10/README.md](../../phase10/README.md) · [analysis/phase12/README.md](../../phase12/README.md) · [analysis/phase14/README.md](../../phase14/README.md) · [source/recovered/battle_presentation_services.py](../../../source/recovered/battle_presentation_services.py) · [source/recovered/exact_audio_requests.py](../../../source/recovered/exact_audio_requests.py) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/validation.json](../../phase25/runtime/validation.json) · [analysis/phase26/runtime/validation.json](../../phase26/runtime/validation.json) · [analysis/phase27/runtime/validation.json](../../phase27/runtime/validation.json) · [analysis/phase27/runtime/repeat-artifact-checks.json](../../phase27/runtime/repeat-artifact-checks.json) · [analysis/phase28/runtime/validation.json](../runtime/validation.json) · [analysis/phase28/runtime/palette-lifecycle-observations.json](../runtime/palette-lifecycle-observations.json)

## A08 · 自然流程与异常边界

来源：用户目标与工程验收方法分别标注；关联请求 U05, U06, U07, U08, U11。

**验收状态：部分已验：自然早退、受控祖先阶段2；自然资源削减待验。**

本轮变化：自然早退64帧与受控祖先资源写32帧分别验证；受控继承19项已知历史准备、更早legacy准备未完全建立。本轮0新增数值/PC/结果/RNG/ready准备。14现场包含stage2直入口、D4F5实际中段及4个stage3严格前缀；BB93/D4F5最近实际转移未完整观察时保持null/unknown。

本轮后仍缺：自然资源扣减仍待验；受控祖先不能称自然胜利，未知旧祖先准备不能强称0；原机stage3完成不证明Source3闭合。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：自然早退64帧与受控祖先资源写32帧分别验证；受控继承19项已知历史准备、更早legacy准备未完全建立。本轮0新增数值/PC/结果/RNG/ready准备。14现场包含stage2直入口、D4F5实际中段及4个stage3严格前缀；BB93/D4F5最近实际转移未完整观察时保持null/unknown。

已验结果与具体回执：

- 冻结父阶段记录：12月战役和连续战斗各自起源/准备范围见原始场景证据。 [frozen_Native_campaign_receipt](../../phase15/runtime/evidence.json)
- 冻结父阶段记录：F8实际接受/拒绝结算按阶段20范围验证。 [frozen_Native_F8_receipt](../../phase20/runtime/evidence.json)
- 冻结父阶段记录：释放到在野招募成功在阶段22原机路线验证。 [frozen_Native_recruitment_receipt](../../phase22/runtime/evidence.json)
- 冻结父阶段记录：本轮新增一条自然配兵/退回/提交菜单路线，导入一次，祖先及新增准备均0。 [new_Native_allocation_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：实际登场和实际非零提交两条自然路线，无新增/祖先数值准备。 [new_Native_route_origin_and_effect_receipt](../../phase25/runtime/evidence.json)
- 冻结父阶段记录：自然存档祖先来源、0数字准备、四次导入与160帧原输入逐项绑定，3实际callee保留完整软件caller。 [new_Native_natural_route_and_ancestry_receipt](../../phase26/runtime/evidence.json)
- 冻结父阶段记录：自然祖先路线BF0A提前返回；受控祖先路线实际触发15逻辑读、11STA写及11寻址dummy读，完整19项已知phase15准备与更早未知准备边界记录。27新增数值/PC/栈准备为0。10新软件callee输入为1自然+9受控。 [phase27_current_bounded_receipt](../../phase27/runtime/evidence.json)
- 自然早退64帧与受控祖先资源写32帧分别验证；受控继承19项已知历史准备、更早legacy准备未完全建立。本轮0新增数值/PC/结果/RNG/ready准备。14现场包含stage2直入口、D4F5实际中段及4个stage3严格前缀；BB93/D4F5最近实际转移未完整观察时保持null/unknown。 [phase28_current_bounded_receipt](../runtime/evidence.json)

待验／限制：

- 受控继承和带准备的祖先不能称零准备自然战役。
- 尚未验证全部君主、战斗、继承组合或自然统一胜利。
- 完整自然胜利是有价值的建议端到端测试，未见用户直接提出为每轮必要门槛。
- 自然资源扣减仍待验；受控祖先不能称自然胜利，未知旧祖先准备不能强称0；原机stage3完成不证明Source3闭合。

可执行验收方法：

1. 维护场景矩阵：关联请求、母档来源、冷启动/导入次数、继承/新增写、真实输入和终点。
2. 逐项区分已实际执行与未覆盖分支，按缺口追加有判别力的验证。
3. 若扩展自然全局胜利，用同一实例连续记录指令和状态链，不强制结果。

证据：[analysis/phase15/runtime/evidence.json](../../phase15/runtime/evidence.json) · [analysis/phase16/README.md](../../phase16/README.md) · [analysis/phase17/README.md](../../phase17/README.md) · [analysis/phase20/runtime/evidence.json](../../phase20/runtime/evidence.json) · [analysis/phase22/runtime/evidence.json](../../phase22/runtime/evidence.json) · [analysis/phase23/runtime/evidence.json](../../phase23/runtime/evidence.json) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/evidence.json](../../phase25/runtime/evidence.json) · [analysis/phase26/runtime/evidence.json](../../phase26/runtime/evidence.json) · [analysis/phase27/runtime/evidence.json](../../phase27/runtime/evidence.json) · [analysis/phase27/source-integration.json](../../phase27/source-integration.json) · [analysis/phase27/runtime/README.md](../../phase27/runtime/README.md) · [analysis/phase28/runtime/evidence.json](../runtime/evidence.json) · [analysis/phase28/source-integration.json](../source-integration.json) · [analysis/phase28/cpu-parent/evidence.json](../cpu-parent/evidence.json)

## A09 · 可复现、回归与归档

来源：用户目标与工程验收方法分别标注；关联请求 U01, U02, U06。

**验收状态：部分已验：分项回执与冻结历史身份；总审计归档见最终回执。**

本轮变化：子服务1240例、整合80例、Native384控制帧、46只读context检查分别记账；十维摘要与最新回执交叉核验。冻结27审计和小增量身份保留；最终浏览器/总审计/归档以独立外置回执为准。

本轮后仍缺：复现限定声明环境与输入；最终ZIP实际SHA由封包后package-receipt给出，不以分项通过替代总审计。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：子服务1240例、整合80例、Native384控制帧、46只读context检查分别记账；十维摘要与最新回执交叉核验。冻结27审计和小增量身份保留；最终浏览器/总审计/归档以独立外置回执为准。

已验结果与具体回执：

- 冻结父阶段记录：v23增量全文件/解压/CRC和基线不变有冻结回执。 [frozen_postZIP_receipt](../../phase23/package-receipt.json)
- 冻结父阶段记录：本轮原始核、被动观察、五buffer和完整复跑检查已有分项回执。 [new_Native_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：本轮Native来源和重复运行已验证，最终包另由独立postZIP回执确认。 [new_Native_reproduction_receipt](../../phase25/runtime/validation.json)
- 冻结父阶段记录：本轮Source3197、整合58、静态5891、Native两路线和43项只读上下文检查分列回执，10验收维度重新核对；最终浏览器、总审计和小增量封包由独立回执记录。 [phase27_current_bounded_receipt](../../phase27/resources/validation.json)
- 子服务1240例、整合80例、Native384控制帧、46只读context检查分别记账；十维摘要与最新回执交叉核验。冻结27审计和小增量身份保留；最终浏览器/总审计/归档以独立外置回执为准。 [phase28_current_bounded_receipt](../parent-services/validation.json)

待验／限制：

- 隔离新环境仍需提供声明的锁定依赖及原ROM/核心。
- 许多历史producer有固定输出路径，不能覆盖冻结证据重跑。
- 复现限定声明环境与输入；最终ZIP实际SHA由封包后package-receipt给出，不以分项通过替代总审计。

可执行验收方法：

1. 先只读核旧pins，再让新producer只写新空目录。
2. 历史回归用新隔离harness/输出映射，保留其代码与数据来源，冻结产物不改。
3. 核精确归档允许清单、包含文件每字节、CRC及解压；外部基线依赖和排除项明确列出。

证据：[analysis/phase23/verification.json](../../phase23/verification.json) · [analysis/phase23/delivery-manifest.json](../../phase23/delivery-manifest.json) · [analysis/phase23/package-receipt.json](../../phase23/package-receipt.json) · [scripts/package_phase23_incremental.py](../../../scripts/package_phase23_incremental.py) · [analysis/phase24/runtime/validation.json](../../phase24/runtime/validation.json) · [analysis/phase25/runtime/validation.json](../../phase25/runtime/validation.json) · [analysis/phase27/resources/validation.json](../../phase27/resources/validation.json) · [analysis/phase27/source-integration.json](../../phase27/source-integration.json) · [analysis/phase27/fields-static/verification.json](../../phase27/fields-static/verification.json) · [analysis/phase27/runtime/validation.json](../../phase27/runtime/validation.json) · [analysis/phase27/context/verification.json](../../phase27/context/verification.json) · [analysis/phase28/parent-services/validation.json](../parent-services/validation.json) · [analysis/phase28/source-integration.json](../source-integration.json) · [analysis/phase28/runtime/validation.json](../runtime/validation.json) · [analysis/phase28/context/verification.json](../context/verification.json)

## A10 · 整体成功的声明边界

来源：工程验收建议；关联请求 U01, U02, U09, U10。

**验收状态：尚未整体完成：字段、其他父状态和自然覆盖缺口待验。**

本轮变化：本轮有效增量是阶段2父链和精确补给协议，城市辅助字段仍null、未知唯一服务总数null、全款闭包false、剩328候选；无完成百分比。完成28后等待评估，不自动开始29。

本轮后仍缺：字段正式语义、其他父状态与自然流程覆盖仍待验，尚未整体完成。

现有范围：继承至冻结阶段27的范围见下方冻结回执。本轮：本轮有效增量是阶段2父链和精确补给协议，城市辅助字段仍null、未知唯一服务总数null、全款闭包false、剩328候选；无完成百分比。完成28后等待评估，不自动开始29。

已验结果与具体回执：

- 冻结父阶段记录：本轮新增10处证明仍留341候选、260合同未知；不能按数字声称整体完成。 [new_static_and_original_CPU_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：最新整合有界执行通过，尚不是全ROM服务闭包证明。 [new_bounded_source_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：服务索引与10维缺口对应，unknown_unique_services=null、whole_game_service_closure_proven=false。 [new_service_acceptance_mapping](../../phase25/services/acceptance-map.json)
- 冻结父阶段记录：城市辅助字段仍null；候选328、未知唯一服务总数null、整款服务闭包false。候选减少与累计case不折算完成百分比，完成27后等待评估，不自动启动28。 [phase27_current_bounded_receipt](../../phase27/fields-static/analysis-summary.json)
- 本轮有效增量是阶段2父链和精确补给协议，城市辅助字段仍null、未知唯一服务总数null、全款闭包false、剩328候选；无完成百分比。完成28后等待评估，不自动开始29。 [phase28_current_bounded_receipt](../context/analysis-summary.json)

待验／限制：

- 每项宽泛请求已在本清单建立有界状态和回执映射；仍须补齐该项尚缺证据，矩阵本身不能替代游戏验证。
- 候选数量、测试case总数和字节重建衡量不同，不能相加或计算统一完成百分比。
- 字段正式语义、其他父状态与自然流程覆盖仍待验，尚未整体完成。

可执行验收方法：

1. 逐项将用户明确要求与其证据/未决项对应，在声明范围报告完成或部分完成。
2. 独立重制、硬件替代和穷尽证明继续标作建议，不追认为用户已授权的义务。
3. 即使本轮审计通过，也报告剩余未知和重要反例。

证据：[analysis/phase23/README.md](../../phase23/README.md) · [analysis/phase23/fields-static/analysis-summary.json](../../phase23/fields-static/analysis-summary.json) · [source/recovered/scene_coordinator.py](../../../source/recovered/scene_coordinator.py) · [analysis/phase24/fields-static/verification.json](../../phase24/fields-static/verification.json) · [analysis/phase24/source-integration.json](../../phase24/source-integration.json) · [analysis/phase25/services/acceptance-map.json](../../phase25/services/acceptance-map.json) · [analysis/phase26/context/verification.json](../../phase26/context/verification.json) · [analysis/phase27/fields-static/analysis-summary.json](../../phase27/fields-static/analysis-summary.json) · [analysis/phase27/context/verification.json](../../phase27/context/verification.json) · [analysis/phase28/context/analysis-summary.json](../context/analysis-summary.json) · [analysis/phase28/parent-services/evidence.json](../parent-services/evidence.json)

## 本清单的检查

运行 `python3 scripts/verify_reverse_acceptance_phase28.py` 只生成本轮新目录的清单、语法边界及引用回执，不执行游戏。其他需要重放的验收项必须另写新输出driver或使用新空目录；不要直接重跑历史固定OUT生成器。

整体状态：尚未全部完成；本清单本身不是新的游戏验证，也不授权推送、发布或扩展成重制工程。
