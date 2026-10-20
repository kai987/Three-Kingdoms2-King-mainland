# 内政合作 AI 的直接源码复原

本轮把固定主循环 `global=2` 实际调用的 physical10/11 `$A000→A00F` 完整可达控制闭包，恢复成具名 Python 函数、条件和循环。生产源码不读取 phase5 控制 IR、不解释 opcode、不调用原 6502，也不伪造 UI/NMI 确认。它是机器码复原源码，不是原作者源码；指令位置和分析根的数量不是作者函数数。

[生产源码](../../../source/recovered/domestic_cooperation_controller.py) · [原字节与数据证据](evidence.json) · [有界目录](static-catalog.json) · [原汇编](raw.asm) · [原 CPU 差分](validation.json) · [实际执行位置](executed-instructions.json)

ROM SHA256 为 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。ROM 全程只读；所有 file offset 都包含16字节 iNES 头。REA pair10 归档用于地址定位，算法和边界按原字节核对。

## 入口及主循环分工

`bank10 $A000` / file `0x014010` 是 `4C 0F A0 JMP $A00F`。实际正文 `$A00F` / `0x01401F` 属于**主循环内政合作 AI**。同 pair 的 `$A003→bank11 D717` 是标题控制器，已经由阶段13的 `TitleUIController` 恢复，两者没有共用语义。

固定 `$E17D` 选择 pair10/11，并在 `$E185` 调用 `$A000`，实际返回地址为 `$E188`。NMI2 的城市 UI 则调用 pair27/28 `$A000`，并非这个 AI。

| `$6F8B` 输入 | 原始行为 |
|---|---|
| bit7=1 | `$A012 BMI→A042 RTS`，保持既有通知/返回标记 |
| 1 | 建连通工作图后跳 `$A8D7`，处理战斗返回及君主死亡/继承 |
| 其他非负值 | 依原次序处理连通、君主位置、搜索/登用、体力、首将、君主驻城及低金卖米，然后按 `$6F5B` 分派 |

`$6F5B` 的三项表在 `$A03C..A041` / file `0x01404C`：`43 A0 9C A1 42 A0`。索引0初始化策略权重，索引1执行策略选择，索引2返回。

另一张三项策略表在 `$A1BF..A1C4` / file `0x0141CF`：`C5 A1 9C B4 C7 BE`。两张表都是 `$D494` 的自定义 inline 协议，使用 scratch `$20..24`、保留 Y、消费 JSR 返回字，再直接跳目标。源码没有用 `$EADE` 的 `$00..04` 协议替代它，也没有把指针当 opcode。

## 可读决策与持久效果

直接可达闭包含 **6,053 个原银行指令位置、134 个分析过程根、193 个源码 while、1,820 个源码 if**。离线图仅供分析和审计；运行时只调用源码中的具名过程。

| 过程 | 原入口 | 作用及边界 |
|---|---|---|
| `cooperate_domestic_ai` | A00F | 手工整理实际前处理次序及分派；保留真实 caller |
| `initialize_strategy_weights` | A043 | 读取难度/君主权重表，按邻接和名册压力分档修正；byte 运算回绕 |
| `choose_three_way_strategy` | A19C | 原低4位拒绝采样、两个 byte 阈值，然后进入三路；不是通常的无限精度加权抽样 |
| `military_strategy` | A1C5 | 外交/年份/难度门槛、攻击城市扫描、同连通城补将、补兵、金米调拨和出征准备 |
| `city_assignment_strategy` | B49C | 原城际分派、相关城市/武将筛选及提交路径；名称按机械作用，未冒称官方策略名称 |
| `city_development_strategy` | BEC7 | 原君主城市游标、发展/武将装备阶段；实际扣金米、人口/土地/产业/防灾/统治度变化 |
| `recruit_appearing_officers` / `recruit_unaffiliated_officers` | C5D2 / C6CC | 登场年/status/位置/概率检查、插入名册及忠诚更新 |
| `choose_city_governor` | C9A5 | 忠100优先，其余按 byte 回绕的忠+徳比较，保留原相等时选后槽的规则 |
| `consume_battle_return` | A8D7 | 原幸存单位、资源/名册、城市 owner 与继承后续；没有用统一政治“交易”重写 |
| `resolve_AI_leader_deaths` | CA19 | 原7君主扫描及继承/无继承人两条实际控制链，含真实等待 |
| `recalculate_recruited_loyalty` / `recalculate_shifted_loyalty` | CF3F / D00C | 忠诚原算法现在是局部源码，不再是原 CPU hook |

城市 word/byte 规则、武将 rawLE16 与战斗 low10、名单首FF计数等保持各原路径的取值方式。没有把所有整数统一为同一个“正常值”。城市地址读取 `$D105→D69D` 会封顶金/米；统治度费用先扣金而后缺米时，已扣金不会自动退款。实际变更逐案保存于回执 `changed_SRAM_bytes`，而非只比较摘要字段。

可达预算过程保留原栈丢弃：`D152` 的零或借位退出、`D165` 的嵌套退出及 `D18D` 的较深退出。预算先按 byte 减法存回 `$6F5D`，再设置 phase2 / requestFF 等控制字段；没有将预算不足变成普通函数成功。此前 phase5 对独立局部 `D12D/D178` 等入口的原有模型和回执保持不变；本轮主入口闭包不将不可达局部工具硬算作可达覆盖。

## 真正的合作等待及服务依赖

继承 `$CB74..CB76` 写 request `FC`，无继承人 `$CA7A..CA7C` 写 `FB`；随后分别在 `$CB79`、`$CA7F` 轮询 **`$6F8B==1`**。源码生成 `ServiceWait('domestic_ack',...)`，保持通知、寄存器和实际栈。重复 `resume()` 不会写1、改 UI phase、清 readiness 或触发 IRQ；只有外部流程真实产生确认后才继续原 `LDA/CMP/BNE`。

本闭包只有四个固定 callee：`F266` 的17处调用点、`E88A` 的4处、`E89A` 的4处、`E8AA` 的1处；都可由已经独立恢复的 `SceneSharedServices` 执行。没有剩余 EE07 远端银行正文。`F266` 仍做真实 mapper 数据窗选择，随机数仍使用原 ROM 排列及 `$52/$54/$55` 游标。缺少任一服务时，源码停在实际 callee/SP；不会假 RTS。

```python
from source.recovered.domestic_cooperation_controller import DomesticCooperationController
from source.recovered.scene_shared_services import SceneSharedServices

services = SceneSharedServices(memory, rom)
ai = DomesticCooperationController(memory, rom, services)
result = ai.run_entry(0xA000, registers=actual_registers)
# 也支持真实 ServiceCall：ai(call)。外部确认到达后可 ai.resume()。
```

`run_entry` 必须提供实际 registers 和 occupied caller stack，当前 mapping 必须是 physical10/11。默认返回地址从真实栈读取；接口没有 synthetic seed 选项。`__call__` 只拥有 `$A000/$A00F` 两个导出，等待期间另一 caller 不能借用既有 generator。内部入口可用于明确局部差分，但不因此变成正式银行导出。

## 原 CPU 对照与有限范围

最终 **1,200 个原 CPU 对照成功、11 个源码边界检查成功、0失败**：

- 纯源码固定服务模式：**1,136 完整返回、22 严格前缀**。前缀是7君主×有/无继承人的14次真实通知等待，加两处轮询的8次未确认等待；没有推进不存在的确认。
- 缺固定服务：**21 个严格前缀**，两侧停在相同真实 callee/栈。
- 验证专用原 fixed-helper 模式：**21 完整返回**，另单列1,305次 helper 调用；这些调用不算额外 CPU 案例，也不进入生产源码。

总计 **1,157 完整返回 +43 严格前缀**。每案对照全部 **2,048 RAM byte、8,192 SRAM byte、A/X/Y/P/SP/PC、四个 physical bank、端口读写的原顺序**。本闭包的四个纯固定服务也在这一全RAM作用域内比较；没有沿用其他呈现模块排除闲置栈的作用域来扩大声明。

输入包含7君主×3难度×3预算的真实主入口连续初始化/决策、三路原采样输入、252组合法资源/武将/装备变化、14个 request1 的空幸存单位数组 fixture、局部筛选/忠诚/地址函数及继承通知。原 CPU 读取只读自然 parent RAM/SRAM，以明确的 CPU-only 参数准备展开；**不是新的自然 campaign、完整战斗结算或 native CPU 指令 trace**。request1 空数组仅验证这个控制分支，不证明某一自然战斗已经结束。

`executed-instructions.json` 共记录4,461个动态位置；其中 **4,425 /6,053** 属于本局部银行闭包。未动态执行的1,628个局部位置只有静态恢复和原字节证据，不称逐条动态验证。严格等待前缀比较的是原轮询完成一次 `LDA/CMP/BNE` 后的实际寄存器状态，不能在第一次到达同PC之前把未执行 CMP 的 flags当成相同边界。

11个边界检查涵盖实际寄存器缺失、错误 pair、D flag、错误导出、callback `None/waiting/error/blocked/dependency` 即使伪改 PC/SP 仍不能通过，以及两处等待不可自确认、外部显式输入1后才继续的合同。最后两项是源码接口检查，**不是原 UI 生成确认的证明**。

```sh
python3 scripts/analyze_domestic_cooperation_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_domestic_cooperation_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

生产源码不渲染 NES 像素、不合成音频、不推动 NMI/IRQ 时间。原核心普通输入流程及主循环接入由本阶段独立 runtime/集成回执提供，不把此 CPU 矩阵当作整机完成证据。历史 phase5 源码/回执、历史 Native 产物和版本ZIP均保持不变。
