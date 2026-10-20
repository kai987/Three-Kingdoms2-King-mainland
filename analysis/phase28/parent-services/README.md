# 精确战后阶段2父服务

PostbattleParentServices(PostbattleResourceServices)只新增A006/BAB3/BB93/C027四个入口。真实输入必须已在相应PC、code physical8/9、有原caller栈；拒绝seed_return、错误返回、错误银行及表外phase。A006是JMP BAB3，无新增帧；BAB3原EADE四项表仍为BAC1/BB3D/BB93/BBA0，但只实现phase2。0/1/3保留实际dispatch目标、栈和暂存为strict dependency，不能称整个四态控制器恢复。

本轮精确协议78个原位置/170B，另8B inline表。既有finalization_phase/return_campaign_supplies已恢复玩法，既有Shared已恢复ECEE、既有phase27已恢复BF0A。本轮不把这些再次记首次算法发现，也不把依赖的43B ECEE计入新增协议正文。

## ECEE等待措辞纠正

ECEE原文立即写87=1、88=0、89=4，设置00/01=0100、02/03=0120，复制32B palette后ED18 RTS到BB96。它不写8A，不轮询87，也不等待帧或硬件ack。冻结旧语义接口render_barrier及旧bypass只是旧测试合同，不能推论原ECEE是同步等待或软件未恢复。本轮通过已有exact Shared、原JSR帧执行它，没有fakeRTS。

真正的fade完成检查在后续phase3 BBA0读87符号；NMI EC67推进并最终写87FF。每帧阶段3是新的原调用，不是一个跨帧挂起的ECEE JSR。本Source只停到BBA0入口；Native可见完成仍不是本Source已执行阶段3正文的证据。

## 阶段2与补给

BB93真实顺序为JSR ECEE、BB96 JSR BF0A、BB99 JSR C027、BB9C INC0501、BB9F RTS。BF0A复用既有pure源码及真实localcall；BF9B tail不造帧。C027第一次以((0514<<1)&FF)^2索引0526/0522，加到050E城+2/+4；然后F25F选择17并检查052B。非FF selector经原F2D7，packed low2只有1/2时选择052C，否则回050E。第二次索引(0514<<1)&FF。所有raw8域保留，但与合法outcome0/1、city0..29、officer0..236分列。

每项先低/高带carry相加并实际写回，再以10000比较，达到上限时高先写27、低后写0F。先wrap16再cap9999，不能用无限整数先cap替代。同城会依次收到两份补给。C08E第一项cap是真实JSR；第二项cap是C0A5的fallthrough；C067第二份是tail JMP C07A，均不造新帧。每个byte读写重取live00/01。

F25F改变E1与实际8000数据页，F2AF/F2D7是已有exact服务；本体不保存/还原整个四页。返回Root外层EE07只恢复原代码窗口，数据页副作用必须保留。D4F5中段桥及其CC29之前绘制不在本四入口owner内，由Root独立声明。

## 对照范围

Source父case 1240，分类{"actual_caller_RTS": 1230, "strict_dependency_prefix": 10}；另9 guards。每案比较完整2048RAM（包括闲置栈）、8192SRAM、AXYP/SP/PC、四PRG、mixed logicalIO读写次序和明示共同N163。Source原CPUcallback0，无IR/CPU执行、无新NMI/IRQ、无ack/ready写入。裸raw/数值/原caller夹具与被动Native输入逐case分列。SP矩阵是明确子集，未声明所有堆栈与palette backup重叠的任意输入都正常返回。

两个same-generator序列先真实停在ECEE caller，再提供已恢复Shared服务后resume；原CPU从同callee继续，缺少PC/SP的“returned”不得推进。这是依赖可用性重试，不是跨帧淡出完成等待。stage0/1/3、missingfixed与越界guard分别计数，不以它们增加正常玩法成功数。

被动callee输入见../cpu-parent；瞬间N163/PPU/APU未捕，所有软件比较使用共同设备fixture。自然退却和受控祖先分别保留，positive继承19项已知准备及更早未知边界；本轮不替换母档身份。原CPU对照不是原机内部CPUtrace，Root frontdoor复用同一软件输入不增加独立Native输入数。

静态新增正文动态覆盖78/78原位置，仍不等于全部分支、四态完整父链或整ROM完成。城市辅助字段正式名和既有1526账本本轮不改。

复现：.venv-trace/bin/python scripts/analyze_postbattle_parent_services.py ROM --import-native-callees --import-only；.venv-trace/bin/python scripts/verify_postbattle_parent_services.py ROM；.venv-trace/bin/python scripts/analyze_postbattle_parent_services.py ROM --evidence-only。仅写新phase28目录，旧1..27不重跑或覆盖。
