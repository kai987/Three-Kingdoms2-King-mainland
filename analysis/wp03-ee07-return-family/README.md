# EE07 城市菜单远端调用：真实正文与返回链

本轮完成一个有界入口族的验证：`27:A06F` 的城市菜单初始化，以及 `27:A077` 的面板忙碌分支。两条路径都执行已有可读源码中的真实 callee，并通过 EE4D、F237、EE52 返回调用方。主路径不是仅抵达 callee：实际写入 `0470..0473 = 00 88 00 24`，`0401:0→1`。

| 项目 | 本轮证据 |
|---|---|
| Source / 原 ROM CPU | 各 656 个受控父案例，54,120 条原 CPU 指令 |
| 主路径 / 忙碌分支 | 各 328；主路径 owner 为 CityUIWorkers，次路径为 CityPanelServices |
| 真实 callee RTS / EE52 RTS | 各 656 次；停在 A074/A07C 首条指令之前 |
| 栈与输入 | 每入口覆盖 256 个 SP；32 个状态组合；8 个 raw E2 别名；32 个数据页 |
| 严格依赖 | 2 次缺 callee 停住，2 次 fake returned 零内存/REG进展，同 pending callee 真正恢复各一次 |
| 双方完整输出 | 每案保存初态、forward、callee 返回、最终 2K RAM+8K SRAM；Source/CPU 双方分开保存后三段 |
| 原模拟器新运行 | 0；没有这两个入口的自然瞬时现场，不将受控 CPU 对照记作自然 Native |

主路径：`A06F JSR EE07` → inline `A039` → selector `3D`、物理29/30 → `A039 JMP BC71` → `BC74` phase0 → `BC83..BC9A` → 真 RTS 到 `EE4D` → `F237` 恢复原代码页 → `EE52 RTS` → `A074`。

次路径：`A077 JSR EE07` → inline `A01E` → selector `39`、物理25/26 → `A01E JMP C435` → phase1 且 `007E!=0` → `C5BE RTS` → `EE4D/EE52` → `A07C`。这只覆盖忙碌返回，不代表面板其余阶段完成。

## 可读源码的整合

现有生产源码已经具备这两段正文及 coordinator 路由，因此本轮没有重写游戏算法。新增的 [窄入口适配器](readable_entry.py) 复用 `CityUIController._external` 与真实 `SceneCoordinator`，让当前 JSR 进入原有 Source owner。所有 callee 保留真实现有栈，`run_entry` 默认 `seed_return=False`；Source 不接收 CPU/IR 回调或原 CPU 输出。对照先运行独立 Source，再执行原 ROM CPU。

本轮起点直接是已声明的 A06F/A077 当前调用位置与 Y 寄存器；前置 LDY 未执行。不构造外层返回帧，不执行 A074/A07C 自身 RTS，不称整场城市 UI 或长期战役已经通过。测试使用基础 GameEngine/SceneCoordinator，不是 CampaignSession/frontdoor 连续战役测试。

## 字段与跨账本关系

城市 `+1`、`+28..31` 正式字段名继续为 `null`。1526 条总访问、1203 条条件排除、80 条 possible、243 条 unknown、剩余 323 条均保持原对象与分类；原始345窗口的104 operand /13 data /228未证入口也不迁移。

本轮给 raw249 `b27:off0072:rom036082`（39 A0 60）及 raw250 `b27:off007A:rom03608A`（1E A0 60）补充实际字节角色：前两字节由 `31:EE1F/EE25` 作为远端地址读取；第三字节仍是调用方原 RTS，本轮只到达它之前。两者都是混合窗口，不能整块叫纯数据，也未证明 raw 起点被当 opcode 执行或其他入口不可达。下游 `29:BCBF` / `26:C443` 均未执行，共同语义根仍为 `null`。

冻结 atlas 里共有 155 个独立直接 `JSR EE07` callsite，本轮纳入2个，其余153个是“该清单中未由本包覆盖的调用点”，不能当作全项目未恢复服务数。全局真正剩余服务数、完成比例和预计轮数仍为 `null`。

执行后元数据审查纠正了静态调用清单中8个 bank9 的 ID 填充：canonical 是十进制两位 `b09`。原清单、prepare 脚本及执行时哈希保持原样，另存 [canonical-v2 清单](known-direct-caller-inventory-v2.json) 和 [8条别名映射](typed-ID-normalization.json)。物理银行、CPU/ROM地址、病例及执行范围均未变化，也未重跑 Source/CPU。所选两个入口及跨账本映射的 ID 不受影响。

## 证据与边界

- [预锁范围](family-scope.json)、[656案矩阵](case-matrix.json)、[预锁验收](acceptance.json)
- [Root实际执行回执](run-01/validation.json)、[逐指令与Source边界记录](run-01/cases.jsonl)、[离线复核](semantic-validation.json)
- [raw窗口消费者](raw-window-consumer-evidence.json)、[严格依赖恢复](strict-callee-resume-evidence.json)、[账本零迁移](ledger-preservation.json)
- [独立下一包准备](next-minimal-package-readiness.json)：仅静态建议 A06F/phase1 的真实64字节复制与 E1 副作用；本轮未执行。

旧工作239445个路径应由最终 before/after 回执逐项保持；另外补充祖先核验，将 EADE 冻结的239404个哈希逐项承接，避免把新采样误当历史一致性。旧 EADE、WP02、WP05、WP08、phase31及phase32残留均不修改。执行前 scope/matrix/acceptance 及生产 Source/脚本哈希已锁定；最终 seal 还核跨账本 SHA。冻结历史和新包各自独立。

完成本包后停止，等待评估。没有宣称全游戏、在野招募自然成功、正式城市字段或完整战役闭环完成。
