# 真保存点前序与严格区分的硬件事件夹具

本域不是原Nestopia内部逐指令记录。独立原CPU从正式原核心保存PC/SP/AXYP、实际MAP四银行与N163 image继续，不改原存档、caller、PC、RNG、request或ready；诊断与callee准备指令不加入Source比较case数。

两个上下文共26383条原指令。释放保存点`release-confirmation.state`实际PC E224/SPFF，按钮81=0，尚未进入下一次NMI。该输入**明确**在CPU模型安排一次真实6502 NMI压栈/向量协议及A手柄端口，标为`Native_snapshot_plus_declared_hardware_NMI_CPU_fixture`、`injected_new_NMI=1`。没有直接写按钮RAM或调用D1F9。原NMI3前序1215指令到A000、1722到D1F9、1728到D20D；2095指令停实际D1F9 caller RTS，原5/30两条记录2→0。它与Native本来的普通A帧是不同层次的证据，不能称实际Native内部callee寄存器。

录用输入`recruitment-success-previous-1-frame14836.state`实际PC D6A1/SPF7，52/54均10。它是**不新增任何中断**的pure保存PC前序：1288指令到C5B9、1343到首次C6CC(city0早退)、1750到成功C6CC(city2)、2013到C71A、2134到C765，2138时C76D真实将5号status24→26。最后24288条原指令到原requestFF。`entry-C6CC-success`是进入该函数时已经保存的真实RAM/SRAM/寄存器，之后根据实际观察0→2挑出，不是从结果反造输入。

8个callee输入分为5个pure录用输入与3个明示NMI释放输入。C5B9正常父返回；C6CC-success/C71A/C765成功会按原双PLA越过一层，保持真实非局部返回。C794时X可以被后续忠诚helper改成0，不能把这里的X误说成仍为录用ID5。Source矩阵与统一GameEngine组合另行记录，不能把本域的准备步骤重复计为额外Source例。

所有硬件读输入均明示：PPUSTATUS=0、APUstatus=0、NamcoIRQ读127；释放端口A，pure录用端口无键。本域没有模拟新视频帧/IRQ到达。Native的完整0→2、RGB/PCM/全state与passive observer证据由`../runtime`单列。

```sh
.venv-trace/bin/python scripts/trace_wild_recruitment.py '/Users/paulasmith/Downloads/三国志2超级版.nes' \
  --release-state analysis/phase22/runtime/original-control/release-confirmation.state \
  --recruit-state analysis/phase22/runtime/original-control/recruitment-success-previous-1-frame14836.state
```

[严格origin与hash](evidence.json) · [前序轨迹](trace.json) · [源码对照](../release/validation.json) · [原机记录](../runtime/README.md)
