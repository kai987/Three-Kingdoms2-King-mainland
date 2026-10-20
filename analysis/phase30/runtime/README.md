# 原核心战后早期阶段与独立被动观察

三个短窗口从冻结保存点导入，仅松开全部按键继续运行；没有新增数值、状态、指针、随机数、结果或就绪位写入。它们不是一次新的冷启动，也不是一场连续战斗的新全程回放。

| 窗口 | 保存点原帧 | 本次帧数 | 祖先 | 实际早期路径 |
|---|---:|---:|---|---|
| natural-stage0-human | phase22 的 6116 | 8 | 自然普通按键，已核祖先准备为 0 | BAC1 检查完整 controller byte=0，进入战场主态 13；未调用 BC46 |
| natural-stage1-mode0 | phase22 的 7635 | 32 | 同一自然案例的另一保存点 | BB3D 检查 controller byte=3，真实 BB8C JSR→BC46→BC52，模式 0 |
| controlled-stage0-human | phase15 的 8048 | 8 | 继承明确 19 字节准备；更早旧母档数值准备尚未完全确定 | BAC1 人类分支进入主态 14，之后 BB3D 经 BB8C→BC46→BD59，模式 1 |

两个自然保存点之间原路线相隔 1519 帧，本轮没有重新连续运行该间隔。`preparation.json` 保存各层来源、母档及原准备 before/after dumps 的散列；本次新增写入为 0。受控路线不得描述成自然获胜。

原未修改核心和新 phase30 被动观察核心分别在独立 Python 进程中各运行两遍，共 12 个进程、192 帧。首次原核心的 48 帧均逐帧保存原 RGB PNG、2 KiB RAM、8 KiB SRAM、完整序列化缓冲，以及 48 kHz 双声道 PCM。与观察核心的全部五个缓冲逐帧完全一致，初次序列化及导入后完整缓冲亦一致；没有裁剪、补零或归一化。879 项非空产物完成逐字节重复比较，其中有 96 对 PNG、6 对完整 WAV。

独立观察核心记录了 179547 个事件及 138 个完整软件快照。软件快照包括实际 A/X/Y/P/SP/PC、已有 CPU 栈、实际四个 PRG 页与 2 KiB/8 KiB 缓冲。没有捕获瞬时 N163、PPU 或 APU 设备状态；后续 Source/CPU 比较使用的共同设备夹具须另列。固定原核心本身没有新增内部跟踪。

实际 BB8C 调用出现两次。事件保留调用前的真实 JSR opcode 边界、BC46 入口 SP 减少 2、原返回栈字 BB8E，以及返回 PC BB8F，不以“返回地址减三”虚构调用现场。模式 0 收集到 `[8,191,51,167]`，原 BDB8 将城市 4 名册地址 6091..6094 从 FF 写为这些 ID：四次写入均改变字节。模式 1 的工作列表为空，没有早期城市名册写入。工作区填 FF 的同值写入另保留；名册重填不能称作新招募，也不能据此推断武将 status/location 改写。

本次没有观察到 AI stage0 的 BB36 调用和模式 2 的 BD67。它们由独立受控 CPU 用例验证；短窗口未命中不证明不可达。三路线城市辅助字节总线事件为 0，仅适用于这些实际路径，不能据此称字段未使用。

后续回归仍区分：ECEE 在当前帧立即 RTS；stage3 的 BBA0 是每次 NMI 的新调用，原 NMI 推进 87 后才进入后续路径。本次实际 2 次 ECEE 即时返回、23 次独立保持回调和 1 次完成回调，不注入任何 ack。后续 C027 补给及 stage3 完成属于继承逻辑，不能混入 BC46 名册作用。

可复核入口：

- [总证据](evidence.json)、[验证回执](validation.json)、[逐字节重复清单](repeat-artifact-checks.json)
- [早期调用与作用原事件](early-lifecycle-observations.json)、[图像/WAV 静态检查](media-static-validation.json)
- [新核心来源与构建](core-provenance/build.json)、[完整源码补丁](core-provenance/observer.patch)
- 各窗口的 `original-control/checkpoints.json`、`observer/events.jsonl`、`observer/bus-events.bin`、`observer/snapshot-index.jsonl` 与 `snapshots.bin`；ABI 为固定 68 个小端 u32，每条 272 字节，解码函数为新脚本的 `decode_event`。

原核心 SHA256 为 `924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a`；新观察核心为 `bb15dc22b1ee5cd1a0e449e9a979a86a26ae2d8762579921ed74a8052cd20996`。新核心仅用 const backing copy 读取软件快照，不额外调用模拟总线读取、写入或设备 API；旧核心与旧输出保持原散列。源码、构建日志与补丁留作可重建来源，工具链和核心二进制不进入增量包。
