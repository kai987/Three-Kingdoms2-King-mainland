# G033 登场表指针与乘法

新增可读源码只替换physical11 `D471..D493` 的19条/35B八轮无符号8×8乘法；既有 `C5D2` 已具名录用流程不复制、不重复计发现。`AppearancePointerServices(CityThresholdServices)` 的 `PUBLIC_ENTRIES` 在既有入口外增加D471，`run_entry(..., registers=真实caller)`保留原JSR帧、二进制flags与严格依赖；父类调用通过真实别名进入新乘法。无CPU/IR/fallback/假ready。

20/21是破坏式工作字节，2C为移位高字节，2A/2B为完整乘积；X保持，Y最终FF，A/V来自最后真实加法或零乘数路径，不能从数学结果伪造寄存器。所有256城市原始字节×20保留；完整prefix `C5F8..C614` 建立22/23=`8B1C+20*rawcity`。实际读取C61F/C624的Y分别来自偶/奇byte循环，不存在10pair或FF自动终止条件。

合法城市0..29的所有byte索引落在physical17数据ROM；raw255+Y248..255跨到A000..A007、实际映physical10代码。逻辑EA与IndY dummy页分开。只证明这两处读的完整生命周期，不因此排除整个C5D2的status/名册/资源cap写入，更不命名城市+1或tail。

本轮Source原CPU对照 **2992** 个父案例，分类 `{"actual_caller_RTS": 2991, "strict_missing_dependency_prefix": 1}`，另 **3** guards；完整2048RAM/8192SRAM、AXYP/SP/PC、端口有序读写、实际四银行及共同N163模型相等。受控乘法/flags/SP边界与完整既有C5D2调用、真实被动callee分列；Root统一工厂层另计，静态原CPU合同也另计。

真实callee只有软件现场；N163是明示共同fixture。无新增中断或caller准备。原Native短路线已独立观察city3/8B58读ID152、原status1→2，详细producer与五buffer对照见 [runtime evidence](../runtime/evidence.json)，输入详见 [CPU来源](../cpu-appearance/README.md)。早期无新增NMI的独立CPUprobe没有复现录用成功，不能当Native成功证据。

复现：

```sh
.venv-trace/bin/python scripts/analyze_appearance_pointer_phase25.py ROM --import-native-callees
.venv-trace/bin/python scripts/verify_appearance_pointer_phase25.py ROM
.venv-trace/bin/python scripts/analyze_appearance_pointer_phase25.py ROM --evidence-only
.venv-trace/bin/python scripts/analyze_unknown_pointer_phase25.py ROM
.venv-trace/bin/python scripts/verify_unknown_pointer_phase25.py ROM
```
