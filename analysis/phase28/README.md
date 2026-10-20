# 第28轮：战后阶段2父链、远调用与真实淡出边界

本轮仅恢复物理8/9的战后阶段2精确协议，并把物理13的D4F5中段远调用接入新统一工厂。城市 `+1`、`+28..31` 的正式含义仍未知，整体逆向没有完成。稳定账本沿用冻结27的1526＝1198条件不交＋81可能＋247未知，候选328；raw345仍为104操作数／13数据／228未证控制窗口。本轮不以父服务闭包工作虚增静态排除。

## 同步请求与真正等待

`31:ECEE..ED18` 会写 `$87=1/$88=0/$89=4`、设置算术暂存并复制32字节调色板，然后立即RTS。它**不初始化 `$8A`，也不等待 `$87`**。旧高层 `render_barrier` 标签不能改写原程序；已有 `SceneSharedServices.begin_palette_transition(False)` 正是此具名正文，本轮不重复计首次算法恢复。

真正的淡出等待在下一阶段：`BBA0` 读取 `$87`，非负时 `BBA3 BPL → BBB7 RTS`，下一次原回调再进入；负值时才 `BBA5 JSR BBB8`。这是多次新回调的门控，不是一份悬挂21帧的ECEE调用。正常非busy NMI中的 `EC67` 按既有 `$8A` 计时推进，完成时原 `EC95` 写 `$87=FF`；busy/reentrant分支不会推进该fade。已有 `EE53` 后续上传与新一次fade请求须分开，当前存档的完成帧不能概括成固定时长。

## 可读源码和实际范围

本轮精确协议涉及78个原指令位置、170字节代码，另8字节四态inline表；继承27的118个资源指令位置和既有ECEE正文不重复计入。新增 [PostbattleParentServices](../../source/recovered/postbattle_parent_services.py) 保留 `A006 JMP BAB3` 与原四项EADE分派栈协议；仅阶段2实现 `BB93 → ECEE → BB96 BF0A → BB99 C027 → INC0501 → RTS`。阶段0/1/3分别停在原BAC1/BB3D/BBA0依赖，原caller和栈保持；不能把其中一次原机后续完成视为四态Source已闭合。

`C027` 的具名精确协议保留原城市／逃将状态判定、outcome字节ASL截断、两次金米回填、16位先wrap再cap9999、同城两次回填、实际暂存／寄存器／栈／mapper作用。其玩法算式已有 `return_campaign_supplies`；旧512 SRAM对照与旧256个显式bypass ECEE的父stage对照不升级为本轮完整RAM或真实等待证据。`BF0A`、`BF9B`尾跳及算术服务继承冻结27，尾跳不增加JSR帧。

D4F5桥仅暴露冻结父源码已有suffix的2个位置／4代码字节及2字节inline数据，不计首次算法恢复。新增 [PostbattleParentGameEngine / ReturnBridge](../../source/recovered/postbattle_parent_integration.py) 从冻结27工厂继承。只将代码pair8/9的NEW4和pair12/13的实际中段 `D4F5` 接入新owner。D4F5输入已带真实Y28；本桥不补前面的 `D4F0 JSR CC29` 与D4F3。已有EE07读取原inline A006、保存原E2并建立原EE4C callee返回word；原callee RTS到EE4D后经F237恢复代码pair，再RTS跳过inline到D4FA。**EE07没有保存或恢复E1数据页**，必须保留BF0A/C027对8000数据窗口的实际副作用，不能笼统说“四bank全部还原”。

正式子服务1240例分为1230个RTS与10个严格依赖前缀，另9个guard；统一工厂80例分为69个返回、1个继承非局部返回、10个严格前缀，另13个guard。统一工厂的58个旧回归、8个受控中段fixture与14个新现场输入分列，14现场为自然7/受控祖先7。子服务使用其中12份；同一输入经两层Source验证不能计作更多Native输入。BB93与D4F5最近一次实际转移未完整观察时，metadata保留null/unknown，仅由静态原字节说明已有协议；不以returnword−3伪造caller。

所有Source对照比较完整2048RAM（含空闲栈）、8192SRAM、AXYP/SP/PC、四PRG映射、读写交织逻辑IO及共同N163。设备和端口夹具不冒充瞬时Native设备快照。生产新源码无原CPU或IR执行回退；正常RTS、非局部返回与未实现依赖前缀分别计数。

## 祖先、证据和交付边界

原机观察沿冻结27同一两母档和普通无键输入：自然早退64帧与受控祖先写分支32帧分别记账。后者继承19项明确phase15准备，更早legacy准备未完全建立，不能强称0；本轮不新增数值、PC、名册、结果、RNG或ready准备。原始母档不能以后来同名重放替换。自然条件下的实际资源削减仍待证明。

正式原机两路线共96原输入帧，两核心各fresh双跑共8进程／384控制帧、8次存档导入／0新冷启动。完整初始API缓冲及每帧RAM/SRAM/RGB/PCM/未归一化state逐字相同；1074个非空重复产物、192张PNG与4份完整WAV通过。95,903个选定原事件和84份完整软件快照来自单独新观察核，固定原核没有内部CPUtrace；96个原核帧也与冻结27同输入结果一致。

每条路线观察到一次ECEE请求和当帧真实RTS、一次完整stage2返回。local2..20共19次原sub3门控返回；local21由原EC95写87=FF后放行到BBB8；local24另一次ECBF请求单列。这是当前两个母档的观察，不是固定21帧定理。原BB9C的INC0501有两次真实RMW写尝试（2→2、2→3），只记一次阶段推进。该远调用入口至返回区间，EE07恢复原E2代码pair，而E1从49变48及8000数据页副作用保持。

正式Source、Native、调用整合、只读上下文和十维验收回执分别交付，不把它们相加成覆盖比例。新被动观察核心与固定原核心的完整初始／逐帧RAM、SRAM、RGB、PCM、未归一化API state必须双核双跑一致；软件snapshot不等于即时PPU/APU/N163。原机后续stage3放行属于Native边界观察，Source本轮仍只到stage2。

本轮 [只读上下文](context/README.md) 有46项检查，新增CPU/Core均0。最终 [源码回执](parent-services/validation.json)、[统一工厂回执](source-integration.json)、[原机回执](runtime/validation.json)、[十维验收](acceptance/README.md)、[浏览器回执](browser-validation.json)、[总审计](verification.json) 和封包后外置 [归档回执](package-receipt.json) 分别说明范围。

本轮只新建28层，不覆盖原ROM、原核心、阶段27及更早Source/scripts/观察核心/证据/审计/旧归档。增量包依赖原v22至v27基线、用户ROM和单独锁定工具链，不是可独立运行的重制。未知唯一服务总数仍null，不报告整体完成百分比。

下一步应在本轮精确阶段2和Native门控边界基础上，独立恢复stage3 BBB8后的实际城市归属收尾服务，并继续寻找能区分城市辅助字段正式含义的专用读写链。本轮完成后等待评估，不自动启动29。
