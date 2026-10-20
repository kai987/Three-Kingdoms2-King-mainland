# WP02：B517 当次 JSR 合同

本有界工作包已完成：两处原指令读取在完整当次 JSR、固定8/9代码页且窗口内无中断或外部修改的前提下，可正式归入“有条件地址不交”。新账本剩余候选由325减至323；城市+1、+28..31正式名称仍未确认。

本次使用明确受控初态的原 ROM 指令 CPU（py65），没有新 Native/Nestopia 或生产 Source 执行。未确认这两处的 Native 瞬时调用现场，`actual_capture_origin` 保持 null。完整结论见 [最终验收](verification.json)、[逐行迁移](candidate-migrations.json) 和 [当前帧合同](current-jsr-contract.json)。

## 实际运行与验收

执行前已锁定 [验收条件](acceptance.json)、[17,207案矩阵](case-matrix.json) 及原指令/表清单。采用有限独立轴，不声称全状态笛卡尔穷举，也没有沿用旧32未执行的14,093/full或285/quick计划。

| 新证据 | 实际执行 |
|---|---:|
| 主矩阵受控父案 | 17,207 |
| 主矩阵前缀段 / 实际 primary JSR | 17,215 / 17,206 |
| 满足当前帧地址合同的段 | 17,190 |
| 主矩阵原 CPU 指令 | 752,661 |
| 单独预声明的同值外部写附录 | 4案、4次真实JSR、64条指令 |
| 本包合计 | 17,211案、752,725条指令 |
| 新 Source / Native / 实际 caller RTS | 0 / 0 / 0 |

主矩阵各组完整键、顺序、计数及案例全文哈希均核对通过，见 [主运行回执](run-01/validation.json) 和 [独立离线审计](semantic-validation.json)。每案从明确的2K RAM、8K SRAM字节模式和寄存器/四页PRG初始化，所有准备写入及故障注入均列入 `disclosed_mutations`；运行脚本、初态基底和Python/py65身份保存于 [执行输入](run-01/execution-inputs.json)。未设置游戏结果、ready或RNG样本，未执行未知目标的首条指令。

主矩阵覆盖两个callsite的raw A全部256值、合法索引与全部SP/入参Y的独立轴、A099的全部raw策略字节、完整AC7B的256种输入X×16种目标/行动单位象限组合、14个原相邻LDX/JSR前缀，以及完整覆盖旧6000栈、部分覆盖、裸B517和B525/B52B中段、两次读之间改指针、同bus/CPU两代调用。

17,190段“满足地址合同”中有4,458段超出合法inline目标索引。地址域不交与合法策略是两种结论，不能把它们合称为17,190次合法策略执行。

## 两次真实压栈与两次真实弹栈

| 原 callsite | 真实原字节 | 本次压入的 raw word | 实际消费者 |
|---|---|---|---|
| physical8:A09E | `20 17 B5` | A0A0 | B51D PLA低→21；B521 PLA高→22 |
| physical8:ACAB | `20 17 B5` | ACAD | 同上 |

每次primary JSR均实际执行原opcode，记录高、低字节两次CPU写；每次PLA只记录 `cpu.step` 真正发起的栈读，附带最后写者及动态代号。检查器额外的只读 `peek` 不记作CPU读。

SP=00时实际写0100高、01FF低，再从01FF低、0100高弹出；其他SP按模256同样成立。固定暂存20..24属于零页，不因SP环绕而变成0100栈页。B525/Y=`(2A+1)&FF`，B52B/Y=`(2A+2)&FF`；两读之间仅STA23和INY，完整live21/22保持。raw127/255的第二Y=00，第二EA回到raw返回字地址，不能错误地取第一次EA+1。

全部raw A的这两个EA仍落代码ROM窗口；这不证明越表目标合法。A099的 `AND #0F` 仅给0..15，strategy只有0..7合法，predicate为0..15合法。原始字节、两张inline表及已知call入口均由原ROM和受信控制图核对。

原B533是 `JMP ($23)`。本次完整段执行该JMP之后立即停止，目标首opcode未执行；原JSR帧已消费、SP回到JSR前，不是RTS或完整目标行为。中段反例仅执行其所选LDA即停止。

## 代际、部分覆盖与同值写

8个两代父案在各自同一bus/CPU对象内实执行两次JSR。代间由host受控重设PC/A/Y，并准备旧栈/旧live21/22；SP没有host重设，保留前段恢复的值。逐案REG前后差异、准备写、两代实际push/PLA及读指针见 [代间来源记录](generation-reentry-preparation.json)。这是完成transfer前缀后的受控再入，不是自然目标返回后再次调用。

完整当次JSR会覆盖旧6000栈字；只恢复一字节或两次读取间改live21/22就不再满足合同。高字节恢复旧60可实际命中城市辅助字段；低字节恢复00可能仍读ROM，不能要求每个违约输入都命中辅助域。裸B517/中段反例保留6001及601C..601F五个offset命中。数值、来源前提和aux命中独立记录于 [反例证据](counterexample-and-overwrite-evidence.json)。

主矩阵没有动态同值故障，因此另行先声明并锁定 [4案计划](samevalue-appendix/plan.json)，再执行 [同值附录](samevalue-appendix/run-01/validation.json)：两处callsite×SP00/FD，真实JSR后host把高栈字节写成它刚压入的同值A0/AC。四案均before==value，PLA高字节最后写者变为external，当前来源前提为false；数值raw word和实际ROM读取仍完全正确。每案保存完整16条原指令前后REG/读写轨迹及完整初始/最终RAM/SRAM。附录不改写主矩阵或其回执。

附录与原权威合同的联系、合并计数及“数值相等不足以证明来源”的结论见 [合同补充](contract-samevalue-addendum.json)。原主矩阵反例文件中的同值静态注记属于附录执行前的范围，4案动态补证单独记账。

## AC7B：保留的是 live2C

原AC7B先STX002C；两次B6E5经B6EF/F266正常返回。B731会把X改为0，ACA8再从live2C取A后到ACAB，不能用返回后的X推断原索引。本次覆盖四象限的16种异位组合及原chunk表项0/1/32/64，实际F266返回共8,220次；核验2C、正常返回栈、DE及最后数据页副作用。逻辑mapper模型明确使用E000原写值的低5位选择PRG页，没有声称硬件时序复演。

14个已知相邻LDX/JSR前缀仅出现X=0、1、4..15；2/3是合法predicate表项，却不属于这14个已知前缀。各组分别计数。

## 可读源码与账本整合

已有生产实现位于 [TacticalCooperationController._dispatch](../../source/recovered/tactical_cooperation_controller.py)、`check_tactic_target`、`normalized_terrain_at_scratch_xy` 和 `read_terrain_chunk`。本包补齐它们的当次调用合同及证据映射，没有新增服务算法或在生产源码加入CPU/IR fallback；现有源码保持冻结。旧7/14的裸B517或预填栈测试不能替代此次真实JSR代际证明。

历史受控CPU轨迹确有4次A09E调用，但其来源是Native帧末内存后另设A000入口/压E22B的同步CPU执行，原Native PC为AE9D；没有ACAB瞬时捕获。原文件hash和四段原轨迹另列 [历史支持](historical-controlled-support.json)，没有升级成自然Native调用现场，也未计入本次新CPU案例。

从正式31账本建立 [新1526行账本](all-indirect-accesses.json)，仅更新physical8:B525/B52B两行，稳定typed ID包含ROM SHA、bank、CPU及ROM offset。每行前后完整对象、旧/新前提和证据均保留，其余1,524行完整对象逐项相等。`wp02_newly_proved_disjoint`只标记这两行；旧BDB8的legacy newly=true作为31历史原样保留，不算第三条本轮新增。

| 域 | 之前 | 本包之后 |
|---|---:|---:|
| 条件地址不交 | 1,201 | 1,203 |
| possible | 80 | 80 |
| unknown | 245 | 243 |
| 剩余候选 | 325 | 323 |

raw345仍是独立域：104操作数/13数据/228入口未证；[raw账本](raw345-executability-ledger.json)与正式31逐字节相同，不与323相加当作语义缺口总数。有条件排除不等于字段未使用或正式命名，城市+1和+28..31名称继续为null。

## 冻结与停止边界

实现前冻结全部239,340个既有工作路径，覆盖analysis/source/scripts/build/tools/.toolchain及根文件，另核既有正式pins；WP08的5个当前源码/脚本单独校验并完整纳入。WP08、WP05、closure、31及32所有已有文件和过期草案都保留，没有就地修旧回执。运行后再次逐路径核对，见 [冻结前](frozen-before.json)、[冻结后](frozen-after.json)、[完整旧工作清单](frozen-work-inputs.json)、[输入](input-manifest.json)、[输出](artifact-manifest.json)。运行环境`.venv-trace`另记实际解释器及py65哈希；不分发ROM，不发布或推送。

本轮合同、反例及逐行迁移完成后停止。自然在野招募成功、城市字段正式语义、完整中断矩阵及整款逆向仍未完成；未知服务总数、完成百分比和剩余轮数均null。下一个已就绪工作包建议WP03：按producer/entry逐条补足剩余访问及raw窗口合同；这里只建议，不自动执行。
