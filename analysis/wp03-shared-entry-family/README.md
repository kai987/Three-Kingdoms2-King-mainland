# WP03：EADE 共享内联分派入口族

本轮完成一个有界共享接口验收：49处已锁定caller，经真实JSR压栈、EADE生成完整01/02、EAE9/EAEE读取inline word，至EAF4间接跳转后停止。49处共331个合法表项获得验证；不执行目标首条指令，不计RTS或完整场景。

这里只纳入两个原记录：`I:26c8…2b82:b31:cpuEAE9:rom03EAF9`、`I:26c8…2b82:b31:cpuEAEE:rom03EAFE`。同用01/02的E04D独立保留。两个读取点共享的是当次JSR帧和原表映射合同，不能将历史G099容器整体认定为一个已闭合服务。

[范围修正版](family-scope-v2.json)、[共享接口合同](shared-interface-contract.json)、[最终验收](verification.json)。音频descriptor族仅在选族时只读比较，未执行；palette及EE07族没有加入本轮。

## 静态清单与实际范围

| 项目 | 数量及含义 |
|---|---|
| 可信atlas直接caller | 98处、745个declared inline word，原ROM逐字核对 |
| 本轮动态caller | 三个既有catalog的48处/328项，加BC49的3项，共49处/331项 |
| 仍只具静态证据的known caller | 49处；不因本次局部通过而声称全局覆盖 |
| 原CPU父案 / transfer或access前缀段 | 16,269 / 16,273 |
| 实际primary JSR / 原CPU指令 | 16,264 / 260,289 |
| 有效当前帧地址合同段 | 16,256；与合法索引范围分别记录 |
| Source前缀比较 | 4,035；其中同步battle/attack接口2,845，duel的ControlHelpers-only接口1,190 |
| 新Native / callerRTS / 完整Source场景 | 0 / 0 / 0 |

16,269案的 [矩阵](case-matrix.json) 和 [验收条件](acceptance.json) 在执行前锁定；[原运行](run-01/validation.json) 一次通过，未重跑旧producer。范围包括raw A全部256值、每个合法表项的5种SP边缘值、四个代表映射的全部incomingY及SP独立轴、真实起点重放、裸/中段/破坏/两代反例。有限独立轴不代表全状态笛卡尔穷举。

三catalog是明确子集，甚至battle Source中另有C784分派未在其中；[98处清单](known-direct-caller-inventory.json)也只是既有可信直接边，不排除computed、bare或其他映射入口。BC49只有3个word：BC52/BD59/BD67，没有第四项。合法表项数不等于自然到达次数。

## 共享producer与Source边界

具有已锁定caller的病例实际执行原 `JSR EADE` 的两次高/低写，EAE3/EAE6两个PLA的实际栈读带最后写者及动态代号；裸入口和中段反例不包含该JSR。得到完整raw返回字后，EAE9的Y=`(2A+1)&FF`、EAEE的Y=`(2A+2)&FF`；两读间只STA03和INY，live01/02不变。固定零页00..04不与0100栈页混同，SP环绕保留原顺序。raw127/255第二Y回0；地址合同不能按第一次EA+1替代。

raw字节得到的表外目标只作为地址前缀，绝不记作合法状态或执行其opcode。故障案保留旧6000完整覆盖、单字节破坏、同值外部重写、两次读之间改指针、裸EADE/中段6001及601C..601F别名。数值相等不等于当前写者来源仍有效。4个两代父案复用各自同一bus/CPU，host的PC/A/Y再入与旧栈准备明确记录；SP不由host改写，也不声称自然目标返回。见 [反例与两代](counterexamples-and-generations.json)。

Source比较执行已有 [Battle `_dispatch`](../../source/recovered/battle_scene_controller.py)、[Attack `_dispatch`](../../source/recovered/attack_scene_controller.py) 同步方法；postbattle使用同一继承方法。duel只比较实际 [ControlHelpers EADE分支](../../source/recovered/controller_helpers.py)，测试caller先在独立Source bus压入原帧，不进入duel generator或handler。所有前缀从共同初态独立执行，核完整2K/8K、AXYP/SP/PC及4PRG；没有CPU回填Source。Source helper的中间指令点/微周期写序不作等价声明。

4,035次Source对照由实际调用及运行时全buffer断言支持，未逐案另存4,035份Source原始输出buffer。独立QA复核了CPU日志、输入/输出重建以及Source隔离和比较断言源码，不能称为重新逐字节比较两套已保存的Source/CPU输出。

三catalog仅用于离线核原表及对应Source literal tuple，生产没有读取IR、执行原CPU或安装fallback。新玩法、服务算法和生产Source改动均0；本次是现有共享接口的证据闭合，不是首次恢复EADE语义或完整服务闭包。

## WP05真实BC49起点

从原观察核保存的local357、snapshot22/event245745直接导入实际REG A02/X40/Y03/P21/SPEC/PCBC49、PRG `[17,8,9,31]` 及完整2K/8K，不改寄存器、银行或内存。新原CPU前缀和独立Source前缀均精确匹配原snapshot23的BD67前边界，包括完整RAM/SRAM、REG、SP及银行。见 [起点、原事件和新重放](natural-anchor-evidence.json)。

此前Native确实观察到本次push01EC=BC、01EB=4B，以及PLA前后SP/栈/ZP和最终EAF4→BD67；没有直接捕获两个Pull8总线读取或EAE9/EAEE的LDA总线读取。新CPU重放补充这些原指令读记录，仍不升级为新的Native运行、视频时序或其他caller的自然信用。其余初态均为明确受控输入。

## 候选账本与raw关系

本轮解除“49处已锁定caller/331表项的共同当前帧接口未验收”这一局部依赖。其他49个已知caller及computed/bare/middle/映射/中断前提尚未闭合，因此不把两条全局指令直接改分类；G-ACCESS-CONTRACTS及全局服务闭包仍开放。

[全部1526行](all-indirect-accesses.json)、[剩余323行](remaining-accesses.json)、[raw345](raw345-executability-ledger.json)均从WP02逐字节复制，所有原对象及分类不变，见 [保全](ledger-preservation.json)。固定计数仍1203条件不交/80possible/243unknown，remaining323；raw345独立为104operand/13data/228入口未证，不能相加为语义缺口总数。

raw228与两条selected指令的语义关系继续null。三条已属operand类别的窗口（bank12 off1040、bank23 off1353、bank24 off094D）字节为 `DE EA xx`：前两字节来自原JSR操作数，第三字节是index0表低字节。新受控CPU实际EAE9读取支持该有限字节来源关系，见 [字节消费者证据](operand-byte-consumer-evidence.json) 及 [跨账本关系](cross-ledger-relations-v2.json)。这不是raw opcode执行、同一语义根或新的分类迁移；物理无交集也不证明语义不交。

## 身份版本与来源保全

执行前的v1 scope把bank字符串错误格式化为十六进制（如b1F），实际数字bank31、CPU地址、ROM offset、病例集合和字节从未改变。反馈到达时run-01已完成，因此保留 [原执行scope](family-scope.json)、原producer与at-run副本/哈希，另存v2及 [ID规范对应表](typed-ID-normalization.json)，与冻结closure的十进制bank typed ID逐条一致。没有倒填“执行前已修正”或更换旧执行身份。

实现前后逐路径核对239,404个既有工作文件，包含ROM/核心锚、WP02全部58产物/6脚本、WP08/WP05/31/32/closure和全部既有历史。见 [冻结前](frozen-before.json)、[冻结后](frozen-after.json)、[全旧清单](frozen-work-inputs.json)、[输入](input-manifest.json)、[输出](artifact-manifest.json)。新case使用py65；旧Nestopia核心未执行或修改，没有发布、推送或分发ROM。

城市+1、+28..31正式名仍null；未知服务总数、完成率及剩余轮数仍null。下一族EE07的bank27 A06F/A077已有原字节/inline入口来源，可在另行锁定输入及后续严格停止边界后验收；本包到此停止，不启动该族或其他路线。
