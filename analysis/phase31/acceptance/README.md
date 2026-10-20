# 阶段31十维验收与范围

保留冻结30的11项直接人类原quote与逐turn/message定位。本轮继续范围由coordinator report单列，不编造新的直接人类逐字引用。

本脚本只核引用、身份、摘要和Source AST，原CPU/Source/Native新增执行均0。Source复用和独立字段合同按各自正式回执计数，不以case或候选数计算整体完成率。阶段31结束待评估，不自动32。

## A01 · 输入身份、字节与资源保全

**已验：原字节和核心身份；语义完成另项待验**

本轮变化：同一ROM、固定原核心与冻结30审计/ZIP保全；四条新导入窗口共16fresh/8816控制帧，初始及逐帧完整RAM/SRAM/RGB/PCM/serialized state两核与复跑相等，未归一化。

保留缺口：身份与字节保全不等全部语义完成；不宣称历史绝对帧PCM/state相等，新增窗口也不算新的冷启动。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：同一ROM、固定原核心与冻结30审计/ZIP保全；四条新导入窗口共16fresh/8816控制帧，初始及逐帧完整RAM/SRAM/RGB/PCM/serialized state两核与复跑相等，未归一化。

已验结果及回执：

- 冻结父阶段记录：原ROM身份、全部字节重建、PRG/CHR提取和资源数量有原始回执。 [frozen_historical_byte_and_resource_receipt](../../verification.json)
- 冻结父阶段记录：本轮输入仍绑定同一ROM，完整原核/观察核起始state一致。 [new_Native_buffer_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：新原核/独立核的完整起始state与逐帧五缓冲相等；8个fresh实例。 [new_Native_identity_and_buffer_receipt](../../phase25/runtime/validation.json)
- 冻结父阶段记录：新观察核心、固定原核心及祖先身份分别记录；正式4fresh对照640控制帧通过。 [new_Native_identity_and_repeat_receipt](../../phase26/runtime/validation.json)
- 冻结父阶段记录：同一原ROM、冻结26的525个源码/脚本和45263个历史依赖身份继续保全；新观察核另立provenance，两路线8个fresh实例的完整初始及逐帧五缓冲一致。 [phase27_current_bounded_receipt](../../phase27/runtime/validation.json)
- 冻结父阶段记录：同一原ROM、原核心及冻结27审计/归档身份保全；新68u32观察核心另立来源。正式8fresh、384控制帧完整初始及逐帧五缓冲一致，96原核帧与冻结27同输入结果一致。 [phase28_current_bounded_receipt](../../phase28/runtime/validation.json)
- 冻结父阶段记录：同一原ROM、原核心与冻结28身份保全；新29观察核独立来源。两路线8fresh共384控制帧，完整初始与逐帧RAM/SRAM/RGB/PCM/未归一化state相同，96原核帧与冻结28一致。 [phase29_current_bounded_receipts](../../phase29/runtime/validation.json)
- 冻结父阶段记录：阶段30：原核与观察核新窗口12次fresh、完整五缓冲一致；本轮新增内存写0，12次母档导入。 [Native复跑回执](../../phase30/runtime/validation.json)
- 冻结父阶段记录：阶段30：观察核与固定原核心来源分列；旧核心和ROM不改。 [核心来源](../../phase30/runtime/core-provenance/build.json)
- 阶段31：四正式窗口2204首跑/8816控制帧、16fresh，initial及五完整缓冲一致，本轮数值准备0。 [Native最终回执](../runtime/validation.json)
- 阶段31：原核心与72-u32被动观察核心身份/构建来源分列。 [核心来源](../runtime/core-provenance/build.json)

待验：

- 身份与字节保全不等全部语义完成；不宣称历史绝对帧PCM/state相等，新增窗口也不算新的冷启动。

验收方法：

1. 以只读验证器核对原ROM哈希和重建的每个字节。
2. 用同一不可变输入核对资源、表偏移及输出哈希；未转写姓名继续保留原字形。

## A02 · 字段和数据表的语义

**部分已验：名单和结果机械合同；城市辅助字段正式含义待验**

本轮变化：完整BC46→BD96→BDB8父链的名册17..26写域已证；自然DD9E原写0514=1与BB36mode2真返回观察到，但buffer空。natural13的6301仅D243 STA跨页dummy，逻辑写6401=2，非新城市辅助消费者。

保留缺口：城市+1/+28..31正式名仍null；无unused/padding/reserved证明。裸BD96异常03和raw125工作区自覆盖保留，不把名单/总线命中转写为官方字段意义。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：完整BC46→BD96→BDB8父链的名册17..26写域已证；自然DD9E原写0514=1与BB36mode2真返回观察到，但buffer空。natural13的6301仅D243 STA跨页dummy，逻辑写6401=2，非新城市辅助消费者。

已验结果及回执：

- 冻结父阶段记录：既有字段结论和适性边界记录冻结保留。 [frozen_historical_field_report](../../phase16/README.md)
- 冻结父阶段记录：阶段23原模拟器对+1/+2比较做了自然/准备条件区分；未确证专用字段名称。 [frozen_Native_threshold_receipt](../../phase23/runtime/validation.json)
- 冻结父阶段记录：本轮证实配兵指针属于武将记录；没有新增城市辅助字段自然生产者。 [new_original_CPU_pointer_contract_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：G033实际C61F由城市3的8B58读取ID152；状态和名册真实写入。 [new_passive_opcode_and_bus_observations](../../phase25/runtime/natural-appearance-pointer/opcode-observations.json)
- 冻结父阶段记录：B441是指针JSR，真实库存写在27:B449/B44F；两dummy读和两写尝试分列。 [new_passive_actual_submission_observations](../../phase25/runtime/natural-nonzero-reserve-submit/opcode-observations.json)
- 冻结父阶段记录：新自然观察8次实际ROM读与8次坐标存储配对，不能用帧末指针替代瞬时读；第二侧34×是历史文案更正。 [new_Native_read_store_pairs_and_static_erratum](../../phase26/runtime/deployment-observations.json)
- 冻结父阶段记录：G106实际读取城市4的+2/+4/+6/+8/+11/+14及相邻高字节；受控祖先路线7个字节变化、4次0→0写入，与随后C027的0→9999写入分开。城市+1及+28..31仍未正式命名。 [phase27_current_bounded_receipt](../../phase27/runtime/postbattle-observations.json)
- 冻结父阶段记录：C027精确协议保留当前城与逃将状态判定、原outcome字节索引、16位先wrap再cap9999及实际数据页作用；玩法公式已有旧源码，不计首次发现。城市+1/+28..31正式含义仍未知。 [phase28_current_bounded_receipt](../../phase28/parent-services/evidence.json)
- 冻结父阶段记录：精确收尾仅outcome0写citybyte0=(old&F0)|(0507>>4)，BC00按owner&0F只跳过7，在17..26十槽找首将并交换；原FF邻接与byteY回绕保留。城市+1/+28..31正式含义仍null，既有归属公式不记首次发现。 [phase29_current_bounded_receipts](../../phase29/completion-services/validation.json)
- 冻结父阶段记录：阶段30：自然BB8C mode0四次BDB8名单变化与controlled mode1仅collector写入分别保存。 [原机实际写入](../../phase30/runtime/early-lifecycle-observations.json)
- 冻结父阶段记录：阶段30：F368正常七君主和raw7..15相邻字节/硬件边界分列，不擅自clamp。 [只读原字节合同](../../phase30/context/ruler-and-name-pointer-boundaries.json)
- 阶段31已冻结字段支线：13998独立原CPU合同/29模型检查，Source0/Native0；仅完整BC46的BDB8条件域新增1排除，裸反例保留。 [独立字段合同(非Source/Native)](../fields-static/verification.json)
- 阶段31：BDB8完整父链正常域新增1条件不交，裸反例与同值/stack/FF洞/raw125实际后续反例保留。 [独立字段合同](../fields-static/verification.json)
- 阶段31：D243读总线6301是STA dummy而非逻辑aux读；真实目标6401。 [原机总线范围](../runtime/natural13-continuous/observations.json)
- 阶段31：DD9E local4原写0514=1；BC46 mode2临时buffer空，21次FF→FF、BDB8/城市写0。 [真实结果生产者与空名单范围](../runtime/natural-AI-mode2/observations.json)

待验：

- 城市+1/+28..31正式名仍null；无unused/padding/reserved证明。裸BD96异常03和raw125工作区自覆盖保留，不把名单/总线命中转写为官方字段意义。

验收方法：

1. 每个语义名称须对应完整读写链、有区分力的实际操作或原UI标签。
2. 检查边界及竞争解释；证据不能区分时保留raw和null名称。

## A03 · 访问、原字节窗口和代码入口

**部分已验：本轮1处条件排除；325候选和raw入口待验**

本轮变化：独立13998原CPU合同=13992实际RTS+6裸后缀前缀，另29模型/原字节/前提检查，Source0/Native0；仅8:BDB8 possible→conditional，1526=1201/80/245，候选326→325。raw345=104/13/228及其他1525权威域不改。

保留缺口：完整父链限normal current/source city0..29、ruler0..6、binary无中断等前提；all256 F2AF对齐word只作更宽store-address lemma，不能扩大父链域或证明unused。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：独立13998原CPU合同=13992实际RTS+6裸后缀前缀，另29模型/原字节/前提检查，Source0/Native0；仅8:BDB8 possible→conditional，1526=1201/80/245，候选326→325。raw345=104/13/228及其他1525权威域不改。

已验结果及回执：

- 冻结父阶段记录：本轮1526项为1185不交/81可能/260未知；351减至341，仅G086十处新证明。 [new_original_CPU_and_model_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：55组270未知生产者有排序；其余组未全面展开。 [new_static_inventory](../../phase24/fields-static/unknown-producer-ranking.json)
- 冻结父阶段记录：raw345保留104指令内部/13数据内部/228未证入口的基线账本。 [frozen_raw_entry_ledger](../../phase23/fields-static/raw345-executability-ledger.json)
- 冻结父阶段记录：新两个访问的正常前置合同及raw域保留，候选余339。 [new_original_CPU_contract_and_static_receipt](../../phase25/fields-static/verification.json)
- 冻结父阶段记录：先比较两条链的实际入口、mapper和信息价值，再只选G033。 [new_selection_and_independent_probe_report](../../phase25/fields-static/selection-comparison.json)
- 冻结父阶段记录：本轮G107四点条件不交与完整raw域/反例保留，36443 OriginalCPU合同分为1624RTS、34816构造前缀、3裸读取前缀；Source0。 [new_original_CPU_contract_and_static_classification](../../phase26/fields-static/verification.json)
- 冻结父阶段记录：稳定1526条可信间址访问本轮新增7处有条件不交，变为1198不交、81可能、247未知，剩余328候选；5891个原CPU合同与16个模型guard通过，raw345分类104/13/228不变。 [phase27_current_bounded_receipt](../../phase27/fields-static/verification.json)
- 冻结父阶段记录：本轮聚焦父服务组合闭包，静态新排除0。冻结27账本1526＝1198条件不交＋81可能＋247未知，候选328；raw345＝104操作数/13数据/228未证控制窗口原样保留，没有新造phase28静态账本或重算完成比例。 [phase28_current_bounded_receipt](../../phase28/context/verification.json)
- 冻结父阶段记录：本轮0处新增静态排除。冻结27/28账本1526=1198条件不交+81可能+247未知，余328；raw345=104操作数/13数据/228未证入口。CC29两处typedROM指针仅上下文提案，不改权威。 [phase29_current_bounded_receipts](../../phase29/context/verification.json)
- 冻结父阶段记录：阶段30：7188独立原CPU合同、7172RTS/16prefix与21模型检查分列；8份旧29软件输入不是新Native现场。 [独立指针合同](../../phase30/fields-static/verification.json)
- 冻结父阶段记录：阶段30：只变两处权威合同，其他1524和raw345账本不改。 [全1526账本](../../phase30/fields-static/all-indirect-accesses.json)
- 阶段31已冻结字段支线：13998独立原CPU合同/29模型检查，Source0/Native0；仅完整BC46的BDB8条件域新增1排除，裸反例保留。 [独立字段合同(非Source/Native)](../fields-static/verification.json)
- 阶段31：13998独立CPU合同与29模型检查，非Source对照；03=1/27..31/255先写、ZP/mirror/stack及raw125未来FF覆盖均真实保留。 [独立CPU合同回执](../fields-static/verification.json)
- 阶段31：全部1526分类1201条件不交/80可能/245未知，剩325；字段候选325不是软件案例325。 [权威账本](../fields-static/all-indirect-accesses.json)

待验：

- 完整父链限normal current/source city0..29、ruler0..6、binary无中断等前提；all256 F2AF对齐word只作更宽store-address lemma，不能扩大父链域或证明unused。

验收方法：

1. 每项保留bank/PC/raw/producer/caller和排除前提。
2. 逻辑有效地址与dummy读、may-write与must事实、正常caller与裸/raw反例分别核验。
3. 对请求中的游戏路径证明入口与服务归属；未决raw窗口保留来源，不静默删除。

## A04 · 可读源码和服务闭包

**部分已验：复用既有完整源码新对照；整款服务闭包待验**

本轮变化：没有新生产Source模块或首次玩法恢复。325软件case=192新数值+2旧30BB36数值+14旧被动+117新被动，317RTS/8故意缺服务严格前缀、0独立guard。117新31被动中87自然祖先/30受控祖先；每case全新Source实例，非单实例连续1551帧UI。

保留缺口：同一Native回调可对应多API层case，不能将软件case数叫独立Native现场；共同N163是显式软件夹具，不是即时设备捕获。整款闭包false；325软件case与325字段候选是两个不同分母。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：没有新生产Source模块或首次玩法恢复。325软件case=192新数值+2旧30BB36数值+14旧被动+117新被动，317RTS/8故意缺服务严格前缀、0独立guard。117新31被动中87自然祖先/30受控祖先；每case全新Source实例，非单实例连续1551帧UI。

已验结果及回执：

- 冻结父阶段记录：新具名配兵服务1038例=1036RTS+2严格前缀，5guards；无生产CPU/IR执行。 [new_source_vs_original_CPU_receipt](../../phase24/lifecycle/validation.json)
- 冻结父阶段记录：整合42例=41RTS+1非局部控制转移，3guards，真caller与owner恢复。 [new_coordinator_vs_original_CPU_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：2992源码比较=2991RTS+1严格缺F266前缀，3guards；旧C5D2正文继承。 [new_source_vs_original_CPU_receipt](../../phase25/appearance/validation.json)
- 冻结父阶段记录：45协调器比较=44RTS+1非局部返回，3guards；含2个G033和1个B431真实被动调用。 [new_coordinator_vs_original_CPU_receipt](../../phase25/source-integration.json)
- 冻结父阶段记录：服务索引按来源/owner/实际bank-entry-caller上下文分层；声明边界不等缺失函数数。 [new_readonly_service_inventory_receipt](../../phase25/services/verification.json)
- 冻结父阶段记录：新协调器48=45继承回归+3真实被动callee，完整2048RAM/8192SRAM/AXYP-SP-PC/实际栈/四页/读写混合逻辑IO/共同N163相等；生产CPU/IR回调0。 [new_Source_composition_differential_receipt](../../phase26/source-integration.json)
- 冻结父阶段记录：恢复具名BF0A/BF9E/BFB3/BFEC精确协议118原指令位置/267B及18B表。旧battle_state_machine.py已有玩法算式，本轮不重复计首次发现。Source3197例与新前端58例通过；48旧回归与10新软件输入分列，BF9B为tail不造JSR帧。 [phase27_current_bounded_receipt](../../phase27/resources/evidence.json)
- 冻结父阶段记录：具名A006/BAB3/BB93/C027恢复78原位置170代码B及8B分派表，仅实现stage2。新增D4F5中段桥复用旧suffix两位置4代码B+2inline，保留EE07原栈/代码pair恢复与E1副作用。子服务1240及统一工厂80例通过，RTS/非局部/严格前缀分列；14现场输入不因两层Source重复对照算更多Native输入。 [phase28_current_bounded_receipt](../../phase28/parent-services/validation.json)
- 冻结父阶段记录：具名完成服务BBA0/BBB8/BC00及A006/BAB3路由提供81原位置/166B精确协议，2853案=2847RTS+6严格前缀，9guards。Root115案=110RTS+1既有非局部+4前缀，8guards；34份新软件输入含子域26及既有CC29/D4F0八份，不能重复当60份。 [phase29_current_bounded_receipts](../../phase29/completion-services/validation.json)
- 冻结父阶段记录：阶段30：1546软件对照案，1506受控/40软件输入(26旧29+14新30)，1540RTS+6prefix，11guards。 [EarlyServices原CPU对照](../../phase30/early-services/validation.json)
- 冻结父阶段记录：阶段30：Root131=115继承+2新BB36受控+14新30软件输入，130RTS+1非局部/4guards。 [统一前门原CPU对照](../../phase30/source-integration.json)
- 冻结父阶段记录：阶段30：410/410原位置命中不等全路径穷举；生产不运行原CPU或控制IR。 [源码与原字节证据](../../phase30/early-services/evidence.json)
- 阶段31：复用冻结owner实际325案，317RTS/8严格依赖prefix、0guard、0OriginalCPU callback/IR；全2K/8K/AXYP-SP-PC/四banks/combinedIO/commonN163按回执核。 [Source实际软件对照](../player-disposition/validation.json)
- 阶段31：新Source模块0；BattleSceneController有阶段13/14正文，ReleaseController仅替换分配/释放并继承wrapper，EarlyServices承载A006四态。 [既有源码分工与信用](../player-disposition/evidence.json)

待验：

- 同一Native回调可对应多API层case，不能将软件case数叫独立Native现场；共同N163是显式软件夹具，不是即时设备捕获。整款闭包false；325软件case与325字段候选是两个不同分母。

验收方法：

1. 通过最新具名协调器重放真实caller，不启用CPU/IR后门或人工ack。
2. 逐案核对完成、等待、越层、reset的PC/SP所有权；未决边界明确记录。
3. 交付函数/原ROM范围/依赖/验证索引，区分既有算法与新恢复的调用协议。

## A05 · 独立运行与更强重制目标

**未列为用户必需目标：独立可玩重制；现有恢复范围见A04**

本轮变化：继续可读源码复用、新软件对照、原机连续窗口与字段合同；没有自动扩成独立重制、原作者工程或源码编译同一NES。

保留缺口：独立可玩重制仍是建议扩展，非本轮必需目标，须单独验收。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：继续可读源码复用、新软件对照、原机连续窗口与字段合同；没有自动扩成独立重制、原作者工程或源码编译同一NES。

已验结果及回执：

- 冻结父阶段记录：可读服务能在显式硬件上下文执行，声明边界具备对照；不能据此宣称独立完整游戏。 [new_bounded_source_execution_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：新增具名算术及继承服务仍依赖显式硬件输入；没有新重制程序。 [new_bounded_source_receipt](../../phase25/source-integration.json)
- 冻结父阶段记录：没有启动独立可玩重制或从高级源码重新编译NES；本轮仍沿既有可读恢复与原CPU对照范围推进。 [phase27_current_bounded_receipt](../../phase27/context/verification.json)
- 冻结父阶段记录：本轮维持可读源码和原CPU/原机验证目标，没有把独立重制或高级源码重编译同一NES列为本轮任务。 [phase28_current_bounded_receipt](../../phase28/context/verification.json)
- 冻结父阶段记录：本轮继续可读源码与原CPU/原机验证，没有自动把独立重制、原作者工程或高级源码编译同一NES列为必需目标。 [phase29_current_bounded_receipts](../../phase29/context/historical-credit.json)
- 冻结父阶段记录：阶段30：已有BC46玩法与精确协议credit分开，不用同名代码或旧case累计推整款完成。 [历史去重](../../phase30/context/historical-credit-and-return-erratum.json)
- 阶段31：既有Source复用不计首次算法或新模块；不以新对照数证明重制完成。 [范围与去重](../player-disposition/evidence.json)

待验：

- 独立可玩重制仍是建议扩展，非本轮必需目标，须单独验收。

验收方法：

1. 当前可读源码目标应提供声明软件服务的可执行driver及依赖日志，明确哪些输入仍需原硬件行为。
2. 若后续选择独立可玩移植，先另定输入、渲染、音频和验收范围，再把它列为必要完成门槛。

## A06 · NMI、IRQ、等待和重启交错

**部分已验：真实返回与依赖续程；全部中断交错待验**

本轮变化：自然mode2捕获local502 BB36→BC46→observed BB39且SP237恢复，BB8C→BC46→BB8F（rawreturnBB8E，实际returnBB8F）另按原记录；独立字段矩阵保留PHA→052C实际写→PLA→BDB8及同值store。8个软件prefix是故意缺服务边界，不当正常成功。

保留缺口：字段无IRQ是合同前提拒绝，非新动态IRQ测试；Source逐callee新实例不等原机完整跨帧同实例复演。全局NMI/IRQ/reset交错仍待验。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：自然mode2捕获local502 BB36→BC46→observed BB39且SP237恢复，BB8C→BC46→BB8F（rawreturnBB8E，实际returnBB8F）另按原记录；独立字段矩阵保留PHA→052C实际写→PLA→BDB8及同值store。8个软件prefix是故意缺服务边界，不当正常成功。

已验结果及回执：

- 冻结父阶段记录：历史主循环/NMI/reset证据范围保留，不回写旧掩码限制。 [frozen_historical_service_report](../../phase15/README.md)
- 冻结父阶段记录：本轮新增协调器保留严格owner及reset退役协议。 [new_bounded_coordinator_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：严格真实caller、非局部终止和reset factory guards均通过。 [new_bounded_coordinator_receipt](../../phase25/source-integration.json)
- 冻结父阶段记录：等待和有意缺依赖前缀按已实现owner分别索引。 [new_wait_and_closure_scope_ledger](../../phase25/services/closure-status-ledger.json)
- 冻结父阶段记录：2009子服务对照含2严格F266前缀及7guards，假returned字符串不能替代原调用PC/SP；协调器另校核reset终止身份退役。 [new_Source_prefix_and_owner_lifecycle_receipts](../../phase26/deployment/validation.json)
- 冻结父阶段记录：新服务保留真实栈返回和BF9B尾跳；58整合对照包含既有非局部返回，4个owner/reset/依赖guard通过。无新NMI/IRQ注入，N163和设备端口是声明的共同fixture。 [phase27_current_bounded_receipt](../../phase27/source-integration.json)
- 冻结父阶段记录：纠正旧render_barrier标签：ECEE同步请求fade并立即RTS，未初始化8A；真实等待是BBA0多次新回调，原EC67/EC95推进完成。Source只闭合阶段2；共同端口/N163夹具非即时设备，13整合guard含同owner前缀恢复/原call对象保留/reset退休。 [phase28_current_bounded_receipt](../../phase28/source-integration.json)
- 冻结父阶段记录：BBA0每次读87，非负立即真实RTS，负值才调用BBB8；完成后写global1/city13/phase0，不清0501或伪造87。rawowner8缺5F20及故意不给服务均严格保留dependency；真正caller/owner/PC/SP与reset缓存清理另经guards。 新增子域A006/BB93两案与Root整父链一案真实驱动回归：缺ECEE先停，伪returned未推进PC/SP不继续，接回真实Shared后同一call/owner/generator完成且不重复请求。 [phase29_current_bounded_receipts](../../phase29/completion-services/validation.json)
- 冻结父阶段记录：阶段30：实际call为BB36/BB8C，返回BB39/BB8F；冻结旧BB37/BB8D标记只在新文档更正。 [父链与栈合同](../../phase30/context/early-stage-branches-and-callers.json)
- 冻结父阶段记录：阶段30：新owner真实ECEE续程、fresh87及严格硬件/依赖前缀均按各case范围验收。 [新owner协议回归](../../phase30/early-services/validation.json)
- 冻结父阶段记录：阶段30：统一前门继承ECEE回归动态重跑，另两案BB36 modes0/2真实JSR/SP/stack对照。 [Root协议回归](../../phase30/source-integration.json)
- 阶段31已冻结字段支线：13998独立原CPU合同/29模型检查，Source0/Native0；仅完整BC46的BDB8条件域新增1排除，裸反例保留。 [独立字段合同(非Source/Native)](../fields-static/verification.json)
- 阶段31：BB36真实JSR/BC46入口/BB39实际返回PC与SP均原事件，不只derived JSR+3。 [原机真实返回边界](../runtime/natural-AI-mode2/observations.json)
- 阶段31：真实PHA/052C/PLA/BDB8先后与两个同值store保留，bare反例单列；Source/Native0。 [独立合同](../fields-static/verification.json)
- 阶段31：317正常RTS与8故意缺服务严格前缀分别记账，0原CPUfallback。 [复用Source协议范围](../player-disposition/validation.json)

待验：

- 字段无IRQ是合同前提拒绝，非新动态IRQ测试；Source逐callee新实例不等原机完整跨帧同实例复演。全局NMI/IRQ/reset交错仍待验。

验收方法：

1. 对声明服务覆盖进入/等待/续程、嵌套忙路径、真实RTI/caller恢复及reset退役。
2. 记录实际事件顺序，按声明范围核全RAM/SRAM/寄存器/IO/mapper/N163；前缀和掩码限制保留。
3. Native观察与明确的新硬件夹具分列，不把人工新增NMI说成此前已目击的原机入口。

## A07 · 图形、音频与硬件依赖

**部分已验：原核8816控制帧音画复跑；全场景待验**

本轮变化：四窗口64/32/557/1551帧共2204首跑、8816控制帧、16fresh、18639非空repeat、4408PNG/8WAV；每帧49公开字段。1376552观察事件/297软件snapshot单列。页面只展示选择点，完整2204帧manifest可查。

保留缺口：软件snapshot不等即时N163/PPU/APU；上游10段141636原核单跑自然祖先不能计入557窗口fresh复跑。全场景硬件音画仍待验。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：四窗口64/32/557/1551帧共2204首跑、8816控制帧、16fresh、18639非空repeat、4408PNG/8WAV；每帧49公开字段。1376552观察事件/297软件snapshot单列。页面只展示选择点，完整2204帧manifest可查。

已验结果及回执：

- 冻结父阶段记录：本轮两核两次复跑728帧，五种完整buffer逐帧一致，26PNG/2WAV和1157复跑物核对。 [new_Native_buffer_and_repeat_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：既有表现软件服务恢复范围见阶段10，PPU/APU/N163硬件仍由原核心执行。 [frozen_historical_presentation_report](../../phase10/README.md)
- 冻结父阶段记录：424控制帧、1091份非空复跑、212PNG和4WAV精确核对，Source病例0。 [new_Native_media_and_repeat_receipt](../../phase25/runtime/validation.json)
- 冻结父阶段记录：640控制帧完整五buffer未归一化逐字比较，非仅RAM或摘要。 [new_Native_full_buffers_media_repeat_receipt](../../phase26/runtime/validation.json)
- 冻结父阶段记录：自然64帧与受控祖先32帧，两核心各独立复跑；384控制帧完整RAM/SRAM/RGB/PCM/未归一化序列化state逐帧一致，864非空重复核验、192PNG和4WAV通过。 [phase27_current_bounded_receipt](../../phase27/runtime/validation.json)
- 冻结父阶段记录：原核/新观察核两路线各fresh双跑，384控制帧完整五缓冲逐字一致；1074非空复跑产物、192PNG/4WAV通过。95,903原事件/84完整软件快照；两路线各观察19次hold和原完成标志，晚新fade单列。 [phase28_current_bounded_receipt](../../phase28/runtime/validation.json)
- 冻结父阶段记录：原核/新观察核两路线各fresh双跑，384控制帧完整五缓冲逐字一致；1182非空复跑、192PNG/4WAV。256197原事件/120软件快照(56/64)，city逻辑读77/leader读12/邻接ROM读12/实际STA15及dummy15，1字节变化和14次同值store均保留。 [phase29_current_bounded_receipts](../../phase29/runtime/validation.json)
- 冻结父阶段记录：阶段30：3分窗48首帧/192控制帧、35字段/点、96PNG/6WAV和879非空复跑检查。 [Native原音画回执](../../phase30/runtime/validation.json)
- 冻结父阶段记录：阶段30：原核无内部trace；被动观察核与原核5buffer逐帧对照，138软件快照不当即时设备状态。 [观察范围与来源](../../phase30/runtime/evidence.json)
- 阶段31：四正式窗口16fresh/8816控制帧，全5buffers/initial精确一致；所有帧与页面展示点分母分开。 [原机复跑回执](../runtime/validation.json)
- 阶段31：4408原PNG和8原WAV只读格式校验。 [原媒体检查](../runtime/media-static-validation.json)
- 阶段31：72-u32/49fields、固定核无内部trace、被动软件snapshot非设备捕获。 [硬件与观察范围](../runtime/README.md)

待验：

- 软件snapshot不等即时N163/PPU/APU；上游10段141636原核单跑自然祖先不能计入557窗口fresh复跑。全场景硬件音画仍待验。

验收方法：

1. 按声明IO对照软件packet、OAM、PPU/APU/N163写入、银行及caller行为。
2. 逐帧精确比较未修改原核与独立观察核的RGB/PCM/RAM/SRAM/完整state，并保留完整WAV和原图。
3. 软件源码证据与原核心音画证据分别标识。

## A08 · 自然流程与异常边界

**部分已验：自然和受控窗口分列；非空mode2自然分配待验**

本轮变化：自然13连续1551帧经历13/0..6后返回15；controlled14-direct32帧仅14/0直接回15，不能称全部14交互。自然Start前缀64帧、自然AI mode2窗口557帧；本轮0新增准备，受控14继承19已知字节及olderunknown。 连续1551窗口完整覆盖母档6116至首次15/1帧7635的1519帧偏移；旧30两个已覆盖短窗之间未覆盖间隔为1511，不把1519称未覆盖gap。

保留缺口：自然mode2临时buffer空，没有非平凡名单分配或本轮Native完整BD96域证明；上游自然AI十段141636只单跑内容链，本次仅557四fresh；全战役/全部human14分支仍待验。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：自然13连续1551帧经历13/0..6后返回15；controlled14-direct32帧仅14/0直接回15，不能称全部14交互。自然Start前缀64帧、自然AI mode2窗口557帧；本轮0新增准备，受控14继承19已知字节及olderunknown。 连续1551窗口完整覆盖母档6116至首次15/1帧7635的1519帧偏移；旧30两个已覆盖短窗之间未覆盖间隔为1511，不把1519称未覆盖gap。

已验结果及回执：

- 冻结父阶段记录：12月战役和连续战斗各自起源/准备范围见原始场景证据。 [frozen_Native_campaign_receipt](../../phase15/runtime/evidence.json)
- 冻结父阶段记录：F8实际接受/拒绝结算按阶段20范围验证。 [frozen_Native_F8_receipt](../../phase20/runtime/evidence.json)
- 冻结父阶段记录：释放到在野招募成功在阶段22原机路线验证。 [frozen_Native_recruitment_receipt](../../phase22/runtime/evidence.json)
- 冻结父阶段记录：本轮新增一条自然配兵/退回/提交菜单路线，导入一次，祖先及新增准备均0。 [new_Native_allocation_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：实际登场和实际非零提交两条自然路线，无新增/祖先数值准备。 [new_Native_route_origin_and_effect_receipt](../../phase25/runtime/evidence.json)
- 冻结父阶段记录：自然存档祖先来源、0数字准备、四次导入与160帧原输入逐项绑定，3实际callee保留完整软件caller。 [new_Native_natural_route_and_ancestry_receipt](../../phase26/runtime/evidence.json)
- 冻结父阶段记录：自然祖先路线BF0A提前返回；受控祖先路线实际触发15逻辑读、11STA写及11寻址dummy读，完整19项已知phase15准备与更早未知准备边界记录。27新增数值/PC/栈准备为0。10新软件callee输入为1自然+9受控。 [phase27_current_bounded_receipt](../../phase27/runtime/evidence.json)
- 冻结父阶段记录：自然早退64帧与受控祖先资源写32帧分别验证；受控继承19项已知历史准备、更早legacy准备未完全建立。本轮0新增数值/PC/结果/RNG/ready准备。14现场包含stage2直入口、D4F5实际中段及4个stage3严格前缀；BB93/D4F5最近实际转移未完整观察时保持null/unknown。 [phase28_current_bounded_receipt](../../phase28/runtime/evidence.json)
- 冻结父阶段记录：自然早退64帧与受控祖先资源损失32帧分列；本轮0新增写，受控继承19项已知准备、更早legacy边界未完全建立。34份软件输入来自自然/受控祖先各17份，完整CC29/D4F0新组合均真RTS；两路线均未观察非平凡名单交换。 [phase29_current_bounded_receipts](../../phase29/runtime/evidence.json)
- 冻结父阶段记录：阶段30：三路的BC46 actual_JSR/entry、mode targets、controller读、city roster writes与23hold/1completion按原事件分列。 [原机早期生命周期](../../phase30/runtime/early-lifecycle-observations.json)
- 冻结父阶段记录：阶段30：2自然窗+1受控祖先窗，1519帧中间UI不在本轮连续观察范围。 [祖先与分窗披露](../../phase30/runtime/evidence.json)
- 冻结父阶段记录：阶段30：BB36 modes0/2仅新受控软件对照，14新软件现场自然/受控各7。 [软件与Native分界](../../phase30/source-integration.json)
- 阶段31：四窗口自然3/受控祖先1分列，2204首跑/8816控制，16次母档导入0新cold；新增写0不抹去controlled祖先19+olderunknown。 [正式路线与祖先](../runtime/evidence.json)
- 阶段31：自然AI十段141636原核单跑自然内容链；upstream fresh repeat=false，不充作本次557四跑。 [portable自然祖先](../ancestry/natural-AI-mode2/ancestry.json)
- 阶段31：自然mode2原调用正，但21FF同值为空；后续D4BA玩家回城及BC3C/43同值写不能算mode2分配。 [原机空名单限制](../runtime/natural-AI-mode2/observations.json)
- 阶段31口径更正：1519是6116母档到首次返回15/1帧7635的偏移，旧30两个短窗之间未覆盖间隔为1511；不改冻结旧文档。 [时序口径限定](../runtime/README.md)

待验：

- 自然mode2临时buffer空，没有非平凡名单分配或本轮Native完整BD96域证明；上游自然AI十段141636只单跑内容链，本次仅557四fresh；全战役/全部human14分支仍待验。

验收方法：

1. 维护场景矩阵：关联请求、母档来源、冷启动/导入次数、继承/新增写、真实输入和终点。
2. 逐项区分已实际执行与未覆盖分支，按缺口追加有判别力的验证。
3. 若扩展自然全局胜利，用同一实例连续记录指令和状态链，不强制结果。

## A09 · 可复现、回归与归档

**部分已验：分项回执与冻结历史身份；总审计归档见最终回执**

本轮变化：字段13998/29模型、复用Source325/8prefix和Native8816控制帧分别记账；十维摘要跨最终分项回执核，冻结30全部Source/Native/审计/ZIP保全。

保留缺口：BQA、最终readonly总审计与v31增量包见随后各自正式回执，本清单不预写passed；不重跑或改写冻结历史producer。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：字段13998/29模型、复用Source325/8prefix和Native8816控制帧分别记账；十维摘要跨最终分项回执核，冻结30全部Source/Native/审计/ZIP保全。

已验结果及回执：

- 冻结父阶段记录：v23增量全文件/解压/CRC和基线不变有冻结回执。 [frozen_postZIP_receipt](../../phase23/package-receipt.json)
- 冻结父阶段记录：本轮原始核、被动观察、五buffer和完整复跑检查已有分项回执。 [new_Native_receipt](../../phase24/runtime/validation.json)
- 冻结父阶段记录：本轮Native来源和重复运行已验证，最终包另由独立postZIP回执确认。 [new_Native_reproduction_receipt](../../phase25/runtime/validation.json)
- 冻结父阶段记录：本轮Source3197、整合58、静态5891、Native两路线和43项只读上下文检查分列回执，10验收维度重新核对；最终浏览器、总审计和小增量封包由独立回执记录。 [phase27_current_bounded_receipt](../../phase27/resources/validation.json)
- 冻结父阶段记录：子服务1240例、整合80例、Native384控制帧、46只读context检查分别记账；十维摘要与最新回执交叉核验。冻结27审计和小增量身份保留；最终浏览器/总审计/归档以独立外置回执为准。 [phase28_current_bounded_receipt](../../phase28/parent-services/validation.json)
- 冻结父阶段记录：Source子2853+Root115=2968案，2957RTS+1既有非局部+10严格前缀/17guards；58项只读context与Native384控制帧分别记账。冻结28评估/归档保留，逐维摘要交叉核正式回执；最终总审计与ZIP见外置回执。 [phase29_current_bounded_receipts](../../phase29/completion-services/validation.json)
- 冻结父阶段记录：阶段30：41项只读检查；Source/原CPU/Native均0，不重复计旧512/256。 [只读context](../../phase30/context/verification.json)
- 冻结父阶段记录：阶段30：独立7188合同及21模型检查，与Source和Native不混计。 [字段合同回执](../../phase30/fields-static/verification.json)
- 冻结父阶段记录：阶段30：最终子服务分组1546与依赖6前缀明确。 [源码回执](../../phase30/early-services/validation.json)
- 冻结父阶段记录：阶段30：Root131真实前门与继承回归，0原CPUfallback/IR。 [整合回执](../../phase30/source-integration.json)
- 冻结父阶段记录：阶段30：新3分窗12fresh完整缓冲复跑。 [原机回执](../../phase30/runtime/validation.json)
- 阶段31已冻结字段支线：13998独立原CPU合同/29模型检查，Source0/Native0；仅完整BC46的BDB8条件域新增1排除，裸反例保留。 [独立字段合同(非Source/Native)](../fields-static/verification.json)
- 阶段31：独立13998CPU/29模型、Source0/Native0，与软件325和字段候选325明确区分。 [字段回执](../fields-static/verification.json)
- 阶段31：Source325实际复用路径对照；新模块/首次算法0。 [软件回执](../player-disposition/validation.json)
- 阶段31：正式四窗口五缓冲/媒体复跑来源不改。 [Native回执](../runtime/validation.json)

待验：

- BQA、最终readonly总审计与v31增量包见随后各自正式回执，本清单不预写passed；不重跑或改写冻结历史producer。

验收方法：

1. 先只读核旧pins，再让新producer只写新空目录。
2. 历史回归用新隔离harness/输出映射，保留其代码与数据来源，冻结产物不改。
3. 核精确归档允许清单、包含文件每字节、CRC及解压；外部基线依赖和排除项明确列出。

## A10 · 整体成功的声明边界

**尚未整体完成：字段、闭包与自然覆盖缺口待验**

本轮变化：阶段31获准一次，完成停待评估，不自动32。城市辅助字段正式名和未知唯一服务总数null，整款closurefalse，没有完成百分比。

保留缺口：剩325字段候选、raw入口、全局服务闭包、自然非空分配和完整硬件交错仍待验；不把325软件case或一次mode2空名单成功当整款完成。

现有范围：冻结30继承范围见父assessment及逐项历史回执。阶段31：阶段31获准一次，完成停待评估，不自动32。城市辅助字段正式名和未知唯一服务总数null，整款closurefalse，没有完成百分比。

已验结果及回执：

- 冻结父阶段记录：本轮新增10处证明仍留341候选、260合同未知；不能按数字声称整体完成。 [new_static_and_original_CPU_receipt](../../phase24/fields-static/verification.json)
- 冻结父阶段记录：最新整合有界执行通过，尚不是全ROM服务闭包证明。 [new_bounded_source_receipt](../../phase24/source-integration.json)
- 冻结父阶段记录：服务索引与10维缺口对应，unknown_unique_services=null、whole_game_service_closure_proven=false。 [new_service_acceptance_mapping](../../phase25/services/acceptance-map.json)
- 冻结父阶段记录：城市辅助字段仍null；候选328、未知唯一服务总数null、整款服务闭包false。候选减少与累计case不折算完成百分比，完成27后等待评估，不自动启动28。 [phase27_current_bounded_receipt](../../phase27/fields-static/analysis-summary.json)
- 冻结父阶段记录：本轮有效增量是阶段2父链和精确补给协议，城市辅助字段仍null、未知唯一服务总数null、全款闭包false、剩328候选；无完成百分比。完成28后等待评估，不自动开始29。 [phase28_current_bounded_receipt](../../phase28/context/analysis-summary.json)
- 冻结父阶段记录：本轮推进阶段3精确收尾和既有CC29父链组合；城市正式名与未知唯一服务数仍null、全款闭包false、余328无完成百分比。完成29后等待父级评估，不自动开始30。 [phase29_current_bounded_receipts](../../phase29/context/verification.json)
- 冻结父阶段记录：阶段30：条件账本仅1200/81/245，余326，正式城市辅助名null；无固定点/unused证明。 [当前字段账本](../../phase30/fields-static/analysis-summary.json)
- 冻结父阶段记录：阶段30：未知唯一服务数null、full game closurefalse。 [声明边界](../../phase30/context/analysis-summary.json)
- 阶段31已冻结字段支线：13998独立原CPU合同/29模型检查，Source0/Native0；仅完整BC46的BDB8条件域新增1排除，裸反例保留。 [独立字段合同(非Source/Native)](../fields-static/verification.json)
- 阶段31：城市辅助正式名null，wholeclosure和fixedpoint均未证明，325候选只是当前条件账本。 [当前字段边界](../fields-static/analysis-summary.json)
- 阶段31：复用Source软件新证据不等全游戏重制或原作者源码。 [源码声明范围](../player-disposition/evidence.json)

待验：

- 剩325字段候选、raw入口、全局服务闭包、自然非空分配和完整硬件交错仍待验；不把325软件case或一次mode2空名单成功当整款完成。

验收方法：

1. 逐项将用户明确要求与其证据/未决项对应，在声明范围报告完成或部分完成。
2. 独立重制、硬件替代和穷尽证明继续标作建议，不追认为用户已授权的义务。
3. 即使本轮审计通过，也报告剩余未知和重要反例。

## 复现

`python3 scripts/verify_reverse_acceptance_phase31.py` 只生成新31验收输出；不执行历史producer、CPU或核心。最终BQA/总审计/包状态另见本轮正式回执。
