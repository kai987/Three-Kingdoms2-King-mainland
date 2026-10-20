# 第27轮：战后资源结算、真实写入与完整指针合同

本轮聚焦 G106 的七处访问。全款逆向仍未完成；城市 `+1`、`+28..31` 的正式含义继续未确认。原ROM、固定核心、v26及更早源码、观察核心、证据和归档保持冻结，本轮仅新建27层。既有 [十维验收](acceptance/README.md) 分别记录本轮变化和待验范围，不按案例数或候选减少计算完成百分比。

## 新源码的实际范围

`battle_state_machine.py:postbattle_city_losses` 早已有玩法层计算；本轮不把旧算法再次计为首次恢复。新增 [PostbattleResourceServices](../../source/recovered/postbattle_resource_services.py) 覆盖 `08:BF0A/BF9E/BFB3/BFEC` 的精确寄存器、暂存、栈和外部服务协议，涉及118个原code位置、267字节，另有18字节原表数据。

[PostbattleResourceGameEngine / SceneCoordinator](../../source/recovered/postbattle_resource_integration.py) 从冻结26入口继承，仅将代码页8/9的四个新入口路由到本轮owner。原部署五入口及其他域继续沿既有owner。代码页12中的同地址不能混认。

完整父链为 `BattleSceneController.D4F0 → EE07(A006) → bank8 A006 → BAB3`，结算阶段2才进入 `BB93 → ECEE → BB96 → BF0A`。本轮没有补写整个 `A006/BAB3/BB93` 精确父控制器；直callee对照通过不能冒充完整父链源码闭包。协调器另有零CPU案例的严格依赖守卫，确认未实现父入口不会假装返回。

旧512个玩法oracle仅比较SRAM，实际只有256例进入写分支、城市与结果关联而偏向偶数城市；旧父结算比较还绕过ECEE。上述历史范围继续保留，不升级为本轮完整2KiB RAM/实际caller或新Native证据。

## 指针、尾调用与结算规则

`0514 != 0` 时，`BF0A` 直接返回原caller，本体不做资源读取、削减或目标写入。结果为0时才执行：

1. `F25F` 选择数据页16，`F2AF(050E)` 构造完整城市指针，再复制到 `$1A/$1B`；原 `$00..09` 随后可被算术服务复用。
2. 针对 `+6/+8/+14` word、`+11` byte、`+2/+4` word进行原计算；每次借真实栈保存并恢复Y，两个外部算术服务 `EBE9/EA7C` 必须完成实际PC/SP协议。
3. 五次word削减有四次JSR和末次 `BF9B → BF9E` 尾JMP。末次沿用原BF0A返回帧，没有新增JSR帧；实际原返回word `BB98` 对应返回PC `BB99`。
4. `BFDF` 写低字节；恢复Y不等于11时才经 `BFE9` 写高字节。每次实际读写都重新读取live `$1A/$1B`，不能把裸helper的目标word缓存成一个固定地址。

原16位乘积高位会被截断后再除10。例如 `9999 × 9` 的低16位是24455，再除10得到2445。原阈值表的比较方向也保留：正常入口固定表下，值不大于501时选9，大于501时选5。上述玩法规则已有旧源码，本轮新增的是精确协议与实际原模拟器证据。

## 两条原模拟器路线分别验收

正式 [Native回执](runtime/validation.json)、[输入及祖先来源](runtime/evidence.json)、[逐写观察](runtime/postbattle-observations.json) 和 [说明](runtime/README.md) 分开标记：

- **自然退却、outcome1**：冻结phase22早期存档普通无键续行64帧，实际到达 `BF0A` 后提前返回。本体没有目标逻辑读写，是自然可达和条件门的负对照，不证明自然资源削减写入已经覆盖。
- **受控祖先、outcome0**：冻结phase15战后存档普通无键续行32帧，继承19条明确记录的旧数值准备。更早导入/按钮元数据并未完全证明此前数值准备为0，原母档与后来同名cold-replay的已披露26B差异也不被替换。本轮新增数值、名册、结果、随机数、PC、ready注入均为0；该路线仍标为受控祖先场景，不能称自然胜利。

两路线合计96原输入帧，两核心各fresh双跑共8进程/384控制帧。完整初始API状态与每帧RAM、SRAM、RGB、PCM、未归一化序列化state五buffer逐字相等；864个非空复跑产物、192PNG、4段完整48kHz WAV已校验。本轮是8次存档导入、0个新冷启动。只有本轮独立被动观察核提供选定指令事件，固定原核没有内部CPUtrace。

写分支即时 `$1A/$1B = $6080`（城市4），实际PRG页 `[16,8,9,31]`。七点共15次逻辑LDA读取、11次STA写入、11次真正STA寻址dummy读分别列账；取指和操作数读取不混计。11次写入中7个字节改变、4次为0→0。`+6/+8/+14` word由9999变2445，`+11`由100变90；`+2/+4`的四个byte实际写0。随后 `C027` 回填金粮0→9999属于另一阶段，不能用最终净值代替G106逐写效果。

十四份完整软件callee快照包含十份本轮四入口输入和四份BAB3/C027父上下文。完整RAM、SRAM、寄存器、栈和实际四页可用于独立CPU续行；它们不是即时N163/PPU/APU设备快照。软件对照共同设备夹具显式声明。原图按实际帧展示：受控路线终点仍为真实淡出黑屏/城市13子态0，不能caption为完整城市UI。

## raw别名与七点地址合同

完整BF0A前置链下，Y的合法保存值和完整指针可约束七个读取/写入；裸helper不会自动获得“城市字段”类型。完整raw city0..255、字节索引、mapper与helper真实clobber都须保留。[原CPU/静态回执](fields-static/verification.json) 的5891例（5632个RTS、256个构造前缀、3个裸访问反例前缀）与16个模型guard通过。七点在声明合同下新增有条件不交，稳定1526项变为1198不交、81可能、247未知；候选从335降为328。raw345仍为104操作数字节、13数据、228未证控制窗口。

本轮新增的十个受控裸alias对照包含 `$001A/$001B`、RAM镜像及算术scratch。可区分反例包括：先写 `$001A` 改变指针，再改写 `$0003`；先写 `$081A` 的RAM镜像，再到 `$08D0`；scratch别名使第二次写入读取到已被首写改变的高字节。这些是原CPU与精确Source的受控协议证据，不是合法城市、自然流程或城市辅助字段正式含义的证明。栈破坏及未知硬件端口不被静默归为正常返回。

[七处访问](fields-static/selected-accesses.json)、[完整指针生命周期](fields-static/resource-pointer-lifetime-contract.json)、[全部1526账本](fields-static/all-indirect-accesses.json) 和 [保留候选](fields-static/remaining-accesses.json) 保存完整domain与前置条件。逻辑有效地址、STA的实际dummy读和其他派生dummy合同分开；py65不是总线周期模拟器。零城市辅助字段命中只限定这些观察路线，不证明填充或未使用。

## 对照、调用边界与交付

[子服务源码对照](resources/validation.json) 与 [协调器对照](source-integration.json) 比较完整2048RAM（含空闲栈）、8192SRAM、AXYP/SP/PC、实际四PRG页、读写混合逻辑IO和共同N163夹具；正常RTS、非局部返回、缺失服务前缀、自然与受控祖先输入分别计数。子服务3197例为3194个RTS与3个严格依赖前缀，另7个guard。协调器58例为57个返回与1个既有非局部返回，另4个guard。48个继承协调器fixture只是本轮回归；十个新软件输入明确分为自然祖先1、受控祖先9，九个JSR入口与一个真实tail入口，祖先准备列表及不完整历史边界逐例保留。同一份实际输入经两个Source层验证，不能算两个不同Native输入。生产新源码没有原CPU或控制IR解释回调。

[调用上下文](context/README.md) 是43项只读检查，新增CPU/Source/Native案例均0；精确callee owner与未闭合的父控制器有明确矩阵，未知唯一服务总数保持null。 [十维验收](acceptance/README.md) 的十个摘要与本轮账本、原模拟器回执交叉校验，104项证据引用和100份recovered Python语法检查通过；旧结果显式标为冻结父阶段记录。

最终 [浏览器回执](browser-validation.json)、[只读总审计](verification.json)、[交付清单](delivery-manifest.json) 与封包后外置 [归档回执](package-receipt.json) 分别验收。小增量包依赖冻结v22至v26、用户ROM与单独锁定核心/工具链，不替换旧包，也不分发ROM。后置封包回执不在封包前预写通过。

下一轮建议继续找outcome0资源削减的完整自然父路径，并从剩余候选中优先追踪能区分城市辅助字段意义的实际生产者/消费者。本轮完成后等待评估，不自动开始28。
