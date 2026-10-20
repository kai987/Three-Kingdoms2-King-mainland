# 实际保存上下文、原CPU caller与异步消费者

本目录分开记录原CPU发现与源码组合对照；所有 CPU 指令都只在验证器运行。生产源码没有原CPU/IR fallback，原模拟器没有替换为源码管线。

## 实际上下文前序

[actual-callers/discovery.json](actual-callers/discovery.json) 从冻结 Native `.state` 解析原 CPU/REG 的PC/SP/AXYP、实际MAP/PRG/BNK、完整2K/8K与N163 RAM/地址/自增。实际银行用于映射，不拿RAM DE..E0影子代替。独立原CPU从保存PC继续；显式PPUSTATUS/APUSTATUS/IRQ读取和controller值有记录，不新增NMI/IRQ、不改request/ready/result/ack或RNG。遇硬件等待、请求或指令预算即保留边界。

83个有界母点捕获了B5FC、B98B、BBB2三个原callee输入。前两者来自 phase15 ruler4 frame20790 的同一母点，不是两个独立Native发现；BBB2来自frame35192。现有原栈的返回字是捕获数据，不植入sentinel。输入文件保留全部RAM/SRAM/N163、实际regs/banks、原CPU前序指令数和已知JSR链。原prefix不是额外source比较case，三个不同入口的独立源码对照已计在[333次矩阵](../services/validation.json)。未捕获B619的自然callee输入。

这项发现利用了原保存点的真实CPU寄存器，并不等于记录了原Nestopia运行中的逐指令trace。继续后的时间、硬件输入与未发生的中断仍是明确的独立oracle范围。

## 四个受控真实消费者序列

[consumer-sequences.json](consumer-sequences.json) 验证原决定body先真正写请求，原NMI2城市UI后真正消费请求，再恢复同一暂停source generator到原caller RTS。起始只准备明确的campaign/owner/controller/数值与已有CPU caller栈；不是自然玩法可达证明。后续只输入普通controller ports、显式NMI/IRQ，没有ready/reply或PC注入。

| 序列 | 请求 | 原consumer回复 | 显式NMI | 显式IRQ |
|---|---:|---:|---:|---:|
| 邻国交涉接受 | F8 | 0 | 85 | 425 |
| 邻国交涉拒绝 | F8 | 1 | 85 | 425 |
| 挖将通知结束 | FA | 0 | 61 | 305 |
| 降忠通知结束 | F9 | 0 | 61 | 305 |

每条长序列只计一个父case，不把中断/callee准备重复计数。接受/拒绝通过原横向yes/no菜单，文字和通知完成来自原软件的消费者。每一边界比较完整2048B RAM（含闲置栈）、8192B SRAM、AXYP/SP/PC、有序IO、四银行以及N163 RAM/地址/自增；新bus使用官方N163地址127→0回绕。

这些NMI/IRQ事件不是Native视频帧时序。正式原核心有限扩城/月轮仍未观察F8；本目录CPUfixture成功不替代该缺口。

```sh
.venv-trace/bin/python scripts/trace_domestic_secondary_callers.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_domestic_secondary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_domestic_secondary_interleave.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_domestic_secondary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[具名源码/公式/边界](../services/README.md) · [覆盖集合](../services/coverage.json) · [正式原核心](../runtime/README.md)
