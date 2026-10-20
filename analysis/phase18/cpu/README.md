# 城市辅助字节：独立原 CPU 访问来源

这里只执行原 ROM 指令，记录全部城市字节访问、实际 ZP 指针、Y、归一化 city/offset 和实际 JSR caller。它没有运行新生产源码，也没有采集 Nestopia 的内部 PC。`E066` 的 AXYP/SP 和端口输入明确声明，NMI/IRQ 是独立 CPU 测试的显式事件；不能把本地 update 数叫原模拟器帧。

## 正向原 caller

[frame34623](actual-caller-frame34623/aux44/trace.json) 继承 phase15 冷启自然全年运行的冻结 RAM/SRAM，当时为189年7月、君主1、city9/sub1/request0。共同准备城4真金币257与首将167兵900，保留原库存9499；仅对比 `city4+1 =0/44`。没有改策略权重、RNG、请求、ready/result/ack、ZP指针或controller。

两main及对应原NMI/IRQ后，aux0兵900、库存9499、预算10；aux44兵1000、库存9399、预算8。两者金币均237。真实 `BD8D→D105` 建立 `20/21=6080`，`BD97` 在 Y=1 读取城4+1，随后 `BD9D` 在Y=2读真正gold低字节。因此比较word分别是256与300。aux44满足门槛，BE后序选择167、扣100库存、写完整兵1000、扣预算2；这个库存充足分支没有支付300金币。随后发展流程两案都实际扣20金币。

Native同背景受控案例在 [runtime](../runtime/README.md)，原core于frame20实际补兵，完整请求结束在baseline26帧/target27帧。该whole-request范围最终金币229/239、预算3/1，与本地两main的237、10/8属于不同长度、不同硬件时间的明确观测。二者不可混成同一个输出快照。

## 未命中的短窗

[frame6758短窗](short-window-frame6758/aux44/trace.json) 在三cohort各30main/NMI的有限运行里没有执行BD95，也没有访问城市+1/+28..31。原策略执行其他发展行为并扣18金币。该结果只说明这段窗口没有消费所查辅助字段，不足以证明它们unused。早期错误officer8隔离与month8目录标签已放到 exploratory-*，不作为正式正向证据。

`+1` 正式名称仍未确定，tail28..31同样opaque；本次实际正向消费者是低位辅助字节与gold低位组成的重叠门槛，不自行猜设计意图。所有实际访问文件保持完整caller、原ROMoffset/bytes、实际基址与归一偏移。

```sh
.venv-trace/bin/python scripts/trace_city_auxiliary_fields.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --snapshot analysis/phase15/runtime/cold-yearwrap/AI-ruler1-status00-frame34623 --actor 167 --updates 2 --out analysis/phase18/cpu/actual-caller-frame34623
.venv-trace/bin/python scripts/trace_city_auxiliary_fields.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --snapshot analysis/phase15/runtime/cold-yearwrap/AI-ruler1-status00-frame6758 --actor 8 --updates 30 --out analysis/phase18/cpu/short-window-frame6758
```

[六组完整原CPU trace汇总与hash](evidence.json) · [可读源及独立差分](../services/README.md) · [原模拟器](../runtime/README.md)
