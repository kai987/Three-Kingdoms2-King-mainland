# 阶段21：城市辅助字段、实际总线访问与招募源码

本期重新追踪阶段20剩余的380条候选访问，排除其中4条，剩余376条。城市 `+1`、`+28..31` 的正式含义仍未确认；本期没有把字段常零、批量复制或有限路线未命中改称“保留/填充/未使用”。游戏整体尚未完成全部语义恢复。

## 字段与访问结论

| 范围 | 不相交 | 仍可能相交 | 指针或索引未决 |
|---|---:|---:|---:|
| 全部1526条已证间接访问 | 1150 | 106 | 270 |
| 原589条候选 | 243 | 92 | 254 |
| 控制图新增45条 | 37 | 1 | 7 |

完整380项逐项记录见 [旧候选处理](fields-static/phase20-remaining380-handling.json) 与 [实际总线关联](access-runtime/previous380-association.json)。对可信48754指令位置中的19174条直接/绝对索引访问另作盘点，没有目标命中；全部PRG另有345个可能碰到目标地址的原字节窗口，其可执行性尚未证明，不能混为实际访问者或全ROM未使用证明。

新增排除的四处为物理银行11 `$C726/$C73F/$C767/$C76D`。完整 `$E89A` 用 `$0053` 保存并恢复 X，阶段20只看到中间 `LDX $0054` 后作出的净破坏推断有误。阶段20文件原样冻结，由 [明确纠正](fields-static/superseding-erratum.json) 代替这项推断。在 `$C71A` 初始化入口、无新中断或外部改写的合同内，未提前录用成功时恰好扫描237条武将记录；成功时可提前跨层返回。这四处访问武将状态和所在地，不能触及城市字段。该合同不覆盖任意中途PC和被中断破坏的暂存。

`+1` 的确定专用读取为 `10:BD97`：与 `+2` 组成小端16位值，参与 `>=300` 判断；这不是通常位于 `+2/+3` 的金钱字段。新观察路线实际读12次，仍不足以给 `+1` 正式命名。`+28..31` 全30城被清零、模板复制，本路线没有专用消费者；不代表其他路径也没有。

## 原模拟器及独立观察核心

固定原核心、同一官方提交的未修改重建版、单独加入被动观察的重建版，分别冷启动双跑同一条11589帧自然路线，共6个进程、69534控制帧。初始完整存档缓冲及每帧RGB、PCM、2KiB RAM、8KiB SRAM、完整序列化API缓冲均严格匹配冻结阶段20；没有裁剪、补零或归一化存档。没有状态导入、内存/PC/RNG/request/ready改写。原固定核心和ROM未修改。

观察版核心有独立SHA256；其事件不是固定原二进制的内部trace。输出等价只对这六次已声明执行成立，不是全ROM二进制等价定理。完整源码补丁、构建记录、官方提交、许可证及观察ABI见 [运行说明](runtime/README.md)、[核心构建](runtime/core-provenance/build.json)。构建出的工具链二进制不放入结果ZIP，构建所需官方源码与补丁的取得方式写入记录。

实际观察3279条、每条72字节，缓冲溢出为0。612次目标城市总线事件中：

- 300次是 `STA (zp),Y` 写指令的虚读，紧接实际写入，不是游戏消费字段数据；
- 300次是清零、模板复制的实际写入，覆盖全部150个目标槽位各两次；
- 12次是 `10:BD97` 专用读取 `+1`。

这消除了“尾字段被读过就有玩法含义”的误判。原始流与JSONL逐条用生产者的同一ABI解码器复核，全部1526位置和旧380项均已关联，没有把未观察到提升成静态排除。[关联回执](access-runtime/verification.json)

原机实际三次进入 `$C71A`，每次237记录，共711个推进/终止检查。记录均无状态低两位0的合格在野武将，`$C732` 随机调用和 `$C794` 成功出口均为0；本期不能宣称自然战役中招募成功。另观察12组 `$E89A` 完整入口/出口，返回X一致，但不能证明所有中断交错下原子性。

## 继续整合的可读源码

新增 [city_recruitment_services.py](../../source/recovered/city_recruitment_services.py) 将物理11 `$C5B9..$C794` 中225个手工恢复指令位置、476字节对应为具名流程：

- 城市逐一准备，先处理出仕武将，再处理在野武将；
- 原年表、容量、状态、概率与所在地/八邻城条件；势力偏好90，普通10；
- 成功保留状态高位、设置所属状态2、首FF名册追加及忠诚重算；
- 保留原8位索引回绕、无FF原循环等待和成功时双PLA跨层返回；不新增HP门槛、费用、假终止符或硬件完成信号。

[city_recruitment_integration.py](../../source/recovered/city_recruitment_integration.py) 接入 `CityRecruitmentGameEngine`，继承既有全局、合作AI与场景服务。正常父调用拥有完整 `$C5B9` 过程。裸 `$C6CC` 成功会越过原调用层，返回明确终态；重复观察同一调用不重新执行或再次弹栈，reset同步退休缓存和所有者。生产恢复源码不执行原CPU、控制IR或动态生成代码。入口示例：

```python
from source.recovered.city_recruitment_integration import CityRecruitmentGameEngine
game, registers = CityRecruitmentGameEngine.from_nestopia_state(rom_bytes, native_state_bytes)
coordinator = game.readable_scene_rules()
# 使用既有主循环/ServiceCall 协作协议及明确的硬件时序输入。
```

这不是把Python源码编译成NES，也不是取回原厂高级语言源码。既有按字节重建的 `.nes` 仍等于原ROM。

## 验证计数与边界

| 类别 | 本期结果 | 不代表 |
|---|---|---|
| 新服务原CPU/源码差分 | 2448案：2415 RTS、30非局部返回、1原循环等待、2严格依赖前缀；3 guards | 2448次原模拟器自然游戏 |
| 主循环组合/调用所有权 | 5案：4真实上下文RTS、1显式控制夹具非局部返回；3 guards | 在野成功已被Native自然触发 |
| 静态合同原CPU执行 | 65551案，另20模型/输出检查和1外部暂存改写模型反例 | 新恢复源码病例或全中断证明 |
| 保存点后独立原CPU诊断 | 3上下文、101157指令、7723城市访问、5次辅助字段读取 | 原Nestopia内部trace；新增中断执行 |
| 原核心/重建/观察控制 | 3核心各双跑、69534控制帧；121项非空检查点产物精确复现 | 六条不同战役或普遍等价 |

新源码比较合计2453案，所有完整2KiB/8KiB、AXYP/SP/PC、有序IO、四个PRG银行及N163状态均按各案真实返回/等待/前缀边界验证。225/225位置至少动态执行一次不等于所有路径或所有输入覆盖。5个实际callee输入由真实保存PC后的原指令形成，既有实际栈不伪造；独立CPU使用明确声明的硬件读输入，未调度新NMI/IRQ。[源码证据](recruitment/README.md) · [组合验证](source-integration.json) · [诊断范围](cpu/README.md)

仍需继续解决：376项剩余候选关系、345个未证可执行原字节窗口的归属、目标字段专用消费者及正式语义、真实具备在野候选时的完整招募成功路线、更多中断交错与异常名单路径。异常裸后缀能别名城市尾部，只证明机械访问可能性，不能给有效游戏字段命名。

## 复跑与交付

本期只新增文件；阶段1～20、旧源码/脚本、原核心、原ROM和旧版本ZIP按冻结哈希审计。最终以 [总审计](verification.json) 与打包后 `package-receipt.json` 为准；打包回执在ZIP外，避免自引用。

```sh
python3 scripts/correlate_city_auxiliary_watch.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_city_recruitment_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_city_recruitment_integration.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/verify_phase21.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

原观察需额外官方核心构建，详见runtime子目录；不要用旧阶段生成器覆盖冻结证据。浏览器 [index.html](index.html) 提供380项筛选、3279事件分组、8组原核心/观察版同帧对照、完整48kHz录音和两份完整新源码。v21包含既有所有允许交付的源码与证据，历史归档本身不递归打包。
