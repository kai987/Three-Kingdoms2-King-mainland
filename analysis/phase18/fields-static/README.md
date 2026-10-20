# 城市辅助字节：跨过程访问合同精化

本目录调查城市 32 字节记录的 `+1`、`+28..31`。它是原 ROM 的离线静态分析，**不新增玩法源码、不执行原 CPU、不运行 Native 核心**，也不把“没有观察到访问”解释为未使用。阶段 16、17 的生成器、源码、Native、HTML 和归档均保持原件。

正式字段名称仍未确定。`+1` 的已知专用读取是错位的复合读取 `LE16(city+1, city+2)` 门槛；`city+2/+3` 才是已有 UI 与原代码确认的金字段。四个尾部字节仍可能被无界名册扫描或其他未解决别名访问，不能写成“保留／填充”定论。BD95 的完整施兵流程及真实调用输入由阶段 18 的 CPU/Source 和 Native 证据另行承担，本目录不重复计入它们的案例数。

## 本轮新增的分析能力

- 本地 callee 输入使用已审计 caller 的保守并集；循环 call graph 的 may-write 使用最小固定点，而不因遇到递归就一律清除全部事实。
- 指针函数的返回合同覆盖固定城市／武将函数，以及 `8:B469/B4E1/B4C2`、`11:D304/D319`。例如 D304 在首个 FF 处可以提前返回，其 `Y` 是 17..27，并非恒为 27。
- 所有本地 RTS 出口产生保守 may-return 字节摘要；未解析 computed/missing control exit 不产生该摘要。摘要不保证循环终止，不伪造 RTS。
- 没有地址证明的间接写在函数内部及 call footprint 中都清除可能受影响的零页事实。RAM 的 `0000/0800/1000/1800` 镜像统一处理；所有绝对索引写按 16 位地址回绕处理，未知索引保留 0..255。
- 追踪本地 PHA/PLA 保存值；仅明确平衡的原指针 helper 保留 caller 的已知栈上值。未知 call 丢弃这部分事实。
- 使用根部冻结的 bounded-control 图，保留正常 selector 域前提。`D0 00` 等零位移条件分支的两条目标相同，不能据目标 PC 过滤真假域。
- 指针低／高字节仍取**独立交叉乘积**。同一静态 call PC 不能证明循环中不同动态调用的字节属于同一代，因而本轮没有引入 pair-coherence 排除。

`access-contracts.json` 对原阶段 17 的 589 个候选逐项给出原始位置、pointer producer、callee/dispatcher 入口、Y 域、地址域及 backward producer 边界。Backward slice 仅是诊断清单，不参与排除统计；达到 512 个位置的切片明确标记 `truncated`。

`all-indirect-accesses.json` 包含修正控制图中的全部间接访问，`new-indirect-accesses.json` 单列相对阶段 17 新增的访问，以及旧非候选在更保守分析中未重新证明 disjoint 的项目。这些重新打开的域不是新发现的正式字段消费者；旧的局部手工证据仍须按自己的前置条件单独判断。

## 结果与边界


实际本轮结果：修正图 48,754 个指令位置、1,526 个间接访问。旧 589 项中排除 153 项，140 项的地址域仍可能相交，296 项的指针合同未知，合计仍可能 436 项。新增 45 项中排除 19 项，8 项仍可能相交、18 项未知，合计新增可能 26 项。

全部 1,526 项的新保守数值域中，621 项 disjoint、504 项可相交、401 项未知。它还把旧非候选的 443 项重新打开为“未重新证明 disjoint”；不把这些视作新实际消费者，也不推翻先前有更强前置条件的局部手工合同。这组全图数值域与仅旧 589 项的精化统计必须分开阅读。

镜像库存实际包含 84 个在 raw index0..255 域可能命中零页的绝对索引写；没有 zpx/zpy 写指令，也没有 direct 写命中上方镜像的指令。音序数组如 0701+X 的合法索引与 raw255 域分别列出。最后两轮旧候选分类均为 153/140/296，但安全 store 数仍为 271→272，因此没有宣称固定点完成。

实际计数以 `analysis-summary.json` 为准。本轮从未知输入及零个假设安全的间接 store 开始，进行了有限 8 轮精化；没有声明完整固定点已求得。指针、索引、映射或控制入口仍未解析的项目会保留，有限 Native／原 CPU trace 的未触及不能作为静态排除依据。

代码域是冻结控制图的已审计入口和正常 selector 范围，非任意外部跳转或错误 mapper 状态；它不构成全 ROM 无消费者证明。banks 0..7/16..22 的全部字节仍只有此前 raw 扫描与尚无可信执行入口的范围结论，不据此命名为纯数据银行。

复跑：

```sh
python3 scripts/analyze_city_auxiliary_accesses.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --passes 8
```

所有原指令在处理前均逐字节比较 immutable ROM，文件位置包含 16 字节 iNES 头。`RAM-mirror-write-inventory.json` 列出实际可能命中零页镜像的 direct/indexed 指令及原字节；`pointer-preserving-store-proofs.json`、`indexed-store-proofs.json` 和 `local-return-contracts.json` 保存地址及返回摘要依据。新结果不依赖排除归档的 exploratory 路径。
