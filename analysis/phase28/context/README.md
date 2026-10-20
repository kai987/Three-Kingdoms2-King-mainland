# 战后父链：同步请求、异步fade与最小Source范围

本目录为新28只读核查，新增Source/原CPU/Native均0，不运行旧producer或复制游戏实现。冻结27前门是PostbattleResourceGameEngine：BF0A已有四callee owner；A006/BAB3/BB93/BBA0/C027在该有限路由模型仍没有精确owner。固定ECEE/EC67/EE07已有IntegratedSceneInitialization→Shared/NMI服务，不能因旧syntax或旧bypass就称它们未恢复。

原13D4F0先JSR CC29，D4F3才LDY#28，D4F5 EE07 inlineA006→physical8/9 A006 JMPBAB3。若新实验从D4F5开始，它不覆盖CC29。四态表BAC1/BB3D/BB93/BBA0按0501分派；本轮最小目标仅sub2：BB93 ECEE→BB96 BF0A→BB99 C027→INC0501→RTS。不得据一个phase2完整返回宣布四态或整场战斗Source全闭合。

ECEE不是轮询屏障。原ECEE..ED18写87=1/88=0/89=4，把0100..011F复制到0120..013F后立即RTS，没有外callee、硬件端口或等待。它不写8A，所以第一步fade延迟取决于已有8A。已有Shared.begin_palette_transition(False)正是这个同步初始化。新28说明只纠正理解，不改冻结旧文档。

异步推进由正常非busy NMI的EC67执行；battle调用点F90B。它递减8A，必要时reload89、设置7D、更新88/palette，最终写87=FF。busy/reentrant NMI不调用该scene fade。实际父sub3 BBA0读87，非负经BPL到BBB7直接返回；负值才在BBA5调用BBB8，然后global1/city13。目标是BBB8，不是BBAB。Scene3 EE53在EC67前，所以87FF还不能证明同次NMI已上传刚计算的palette。Native观测fade完成与Source未实现sub3必须分开。

EE07是已有具名服务，不是本轮首次发现。它保存E2，callee通过真实EE4D返回后F237恢复原E2/E3代码pair；它不恢复E1数据页。BF0A outcome0的F25F#30留下bank16/E1副作用，需要完整四bank对照，不能笼统说恢复所有映射。尾返回、真实PC/SP、同一call对象和父generator身份都应保留；普通ECEE本身没有挂起，不能伪造其等待或每次resume重启fade。

旧battle_fsm已有资源扣减512案和补给归还512案，只比较SRAM；旧finalization256案两侧显式bypass ECEE。旧Shared完整矩阵的六entry palette/display组1536案包含256个ECEE直接测试，其RAM范围1856B并排除部分闲置栈，不可改称全2K。新28若补精确C027/caller协议是新scope，不能重算既有公式首次恢复。

稳定1526账本1198条件不交/81可能/247未知，剩328；raw345=104操作数/13已有数据/228未证入口均不变。此context新增排除0，城市+1/+28..31正式名与未知服务总数继续null。协调澄清属于Source/report事实，不新增directhumanquote。
