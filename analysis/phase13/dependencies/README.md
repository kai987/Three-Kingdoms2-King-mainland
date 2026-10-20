# 城市 UI 远端依赖动态调查

从本轮正式原核心 RAM/SRAM 检查点重建 13 个原 CPU 城市回调，physical27 A000 均在预算内真实返回。共观察 18 次 EE07 远端调用、3 个不同 callee；这份回执只用于定位依赖与提供真实 caller 输入，不是纯源码等价验证，也不是 Nestopia 内部逐指令录制。

回调上下文先执行原 fixed F206 清 OAM，再以原 E1 执行 F25F，最后 F237 selector3B 选入城市代码。A/X/P、0200 返回哨兵及 CPU 栈帧是明确的实验准备；原核心捕获没有新增 RAM/SRAM 写入。CPU 调查没有 NMI/IRQ 时钟，并采用明确的零 PPUSTATUS、默认 APU/手柄输入。它不能替代整机硬件时序验证。

## 已观察的远端调用

| 原调用点 | 文件偏移（含 iNES 16B 表头） | 原指令与内联 word | selector / physical callee | 次数 | 外层续点 |
| --- | --- | --- | --- | ---: | --- |
| 27 A014 | 36024 | `20 07 EE 2A A0` | 39 / 25 A02A→BBDE | 13 | A019 |
| 27 A04F | 3605F | `20 07 EE 21 A0` | 39 / 25 A021→AFE5 | 3 | A054 |
| 27 A0E4 | 360F4 | `20 07 EE 21 A0` | 3D / 29 A021→A77F | 2 | A0E9 |

上述地址及偏移用十六进制表示。实际 callee 栈顶返回 EE4D，SP=F8；外层续点是 EE07 恢复银行、消耗内联 word 后的 caller 地址，两者不同。[inventory.json](inventory.json) 保存每次原字节、哈希、寄存器、实际银行和来源检查点。每个 callee 的前两个输入保存在 [callee-inputs](callee-inputs/) 下，RAM/SRAM 二进制与 JSON 哈希一起公开。

25 A02A 出现在全部 13 个回调，由城市绘制前序调用。25 A021 的 3 次出现在武将资料首项、下一项和返回首项。29 A021 的两次实际来自 `world-map-return` 与 `officer-info-closed`（0400/0401=0/1），并非武将选择子菜单；A77F 检查 `(005E+5)&0F` 后更新 6F05 对应的 BCD 表头，不调用 F308 姓名 helper。

导出入口必须按原字节区分：25 A021 是 `4C E5 AF`（AFE5 资料 driver），25 A01B 是 `4C 64 B9`（B964 候选扫描），25 A012 是 `4C D7 B2`（B2D7 已有绘制 worker）。29 A021 是 `4C 7F A7`。仅数字 A021 相同不能跨 physical bank 归为同一服务。

## 范围与复现

13 个回调都完整返回，未出现预算截断；未将动态观察之外的城市主态、phase、按钮或字段分支宣称覆盖。根线程的新城市源码闭包及纯源码整合矩阵单独验证。调查脚本不在生产服务中提供 CPU fallback。

```sh
python3 scripts/capture_city_ui_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat
.venv-trace/bin/python scripts/discover_city_ui_dependencies.py
```

[原核心母档及完整回放说明](../runtime/README.md) · [原 CPU 输入与调用清单](inventory.json)

## 单列：统一纯源码接入

新的[纯源码整合回执](../source-integration.json)另外验证这13份正式Native RAM/SRAM输入：两侧分别执行真实F206/F25F/F237前序，再经统一`GameEngine.tick_readable_scene(registers,scene=2)`完成27A000回调，13例完整通过、1个未知callee拒绝测试。source侧原CPUcallbacks=0；比较全部2048RAM（包括inactive stack）、8192SRAM、AXYP/SP/PC、银行和有序端口。39次前序helper对照包含在13个pipeline病例中，不作为额外病例重复计数。

AXYP与0200既有caller frame是明确受控实验输入；没有把它们改称Native内部寄存器。原截图/WAV由Nestopia独立产生，源码pipeline没有绘制这些原图，也没有证明IRQ/NMI周期或PPU扫描线等价。正式源码及全部依赖在新回执单独hash固定。

```sh
.venv-trace/bin/python scripts/verify_phase13_city_integration.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
