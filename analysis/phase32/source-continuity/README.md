# 第32阶段：单实例可读 Source 连续处置

本子域新增 host driver，不新增玩法算法或场景 callee。冻结31及更早代码不变。当前作者仅作文本和 AST 检查；原 CPU、Native 和所有运行验证由根线程执行。没有运行回执时不能将脚本存在视为已通过。

`PostbattleContinuity(game, registers)` 组合现有 `CampaignSession`，保持同一 GameEngine、SceneCoordinator、memory、registers 和 session。主循环要求真实 E066 边界，NMI/IRQ 是显式 host 输入；`resume()` 保持原 pending phase、ServiceCall、owner 与 generator。已正常返回的独立 callee 可以在下次调用获得新 owner，这是冻结协调器的既有调用生命周期，不是重新创建 GameEngine。

生产 driver 不推进 CPU、不解释 IR、不导入下一帧 RAM、不写游戏按钮 RAM、ready、结果、RNG、62 或87。`set_buttons()` 只提供两个物理手柄字节，由原 E6C6 软件读取。它不调度 IRQ，也不把任意一次操作叫 Native 视频帧。

## 根线程运行接口

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-trace/bin/python scripts/verify_postbattle_continuity_phase32.py /Users/paulasmith/Downloads/三国志2超级版.nes --spec analysis/phase32/source-continuity/actual-spec.json --cycles 2 --skip-regressions
PYTHONDONTWRITEBYTECODE=1 .venv-trace/bin/python scripts/verify_postbattle_continuity_phase32.py /Users/paulasmith/Downloads/三国志2超级版.nes --spec analysis/phase32/source-continuity/actual-spec.json
python3 scripts/analyze_postbattle_continuity_phase32.py --evidence-only
```

`actual-spec.json` 可为单项或列表，每项包含 `case`、`origin`、`initial_context`、`input_plan`。`initial_context` 指向标准 `context.json` 目录或新被动核 E066 callee JSON，必须带真实 registers／actual_registers、physical_banks／actual_PRG_banks，并有 `input-ram.bin`／`input-sram.bin` 或同名 `-ram.bin`／`-sram.bin`。不得给该格式另加 initial_registers 覆盖。

`input_plan` 使用既有普通按钮行结构：`frames` 与 `buttons` 数组。这里的每个计划 tick 是声明的 main → NMI → 按实际62由原 IRQ 软件消化 → 同 NMI resume 的软件策略；它不是从 Native 恢复出来的逐周期中断时序。完整2K／8K、AXYP/SP/PC、四个实际 PRG 页、交错逻辑IO与共同 N163 状态在每个事件后比较。一条计划只计一个 parentcase，嵌套事件不重复计案。

稀疏软件现场没有即时 N163 时，`hardware.N163_fixture` 明确给出128字节、address、autoincrement；默认共同软件夹具也会记录。端口默认声明2002=0、4015=0、5800=127重复输入，控制器初值0／0。未知端口或服务必须保留前缀。原 py65 对照不提供真实 dummy 总线周期、图像、PCM 或视频帧时间模型。

不传 `--spec` 时仅提供继承31 mother内存加显式 E066 寄存器的受控软件起点，绝不称其为 Native saved REG。正式优先实际 E066 context。`--cycles` 是部分计划 smoke，不能声称完整 UI 路线复现。

验证器另列本轮 driver 的同 NMI ECEE 缺失 → 两次假返回且不推进 → 原 Shared 同 generator 续一次、随后多次 fresh NMI 读87的回归。ECEE 是同步初始化并立即 RTS；87完成来自原 palette 软件，不能人工 acknowledgement。EE07 的代码 pair 恢复与 E1 数据页保留须与原 CPU 同步比较。此项只有根线程实际执行成功后才具备本轮运行信用。

完成第32阶段后停止，不自动进入33；该 driver 不是独立可玩的 NES 重制。
