# 同一战役调用上下文与中断续程

[CampaignSession](../../../source/recovered/campaign_session.py)把原主循环、显式接受的NMI/IRQ和待决服务连接到同一个实际寄存器对象及ServiceMemory。它是协调层API，不新增ROM解释器或帧时钟。新精确音频owner接入[SceneCoordinator](../../../source/recovered/scene_coordinator.py)；城市补充字段由`GameEngine.city_auxiliary_fields(city)`只读提供。

`main()`必须从实际`E066`进入。主调用等待时保持原generator、ServiceCall、PC/SP和pending phase；不能新开主入口替代。每次显式NMI/IRQ到达创建独立owner，支持外层NMI仍等待IRQ时接受嵌套忙NMI。内层真正RTI回原PC/SP后，才能恢复外层。`resume()`只恢复最上层待决服务并核对暂停PC/SP；初始化到真实E066非返回边界时，reset epoch使旧pending和中断owner退役。IRQ的I位屏蔽遵循调用输入，NMI不受I位屏蔽。

[矩阵](validation.json)共51个父CPU案例、7项guard、0失败：21个案例覆盖7君主×3策略，每例同一上下文连续4次main2；30个案例覆盖IRQ模式/行与3种SP，执行外NMI→真实等待→嵌套忙NMI→IRQ服务清62→内NMI RTI→外NMI RTI。各内部步骤留在该案例，不能当新增案例或自然视频帧。每步比较全部2048B RAM、8192B SRAM、实际AXYP/SP/PC、银行和顺序端口读写。

另[两条受控继承续程](../succession-integration.json)由同一Session在原CA7F/CB79等待，给241/481次显式NMI2，到原CBBF写ack1，随后原主调用回E066。新音频owner使全部2048B RAM（含闲置栈）、SRAM、寄存器、端口、银行和N163寄存器图在每一步一致，无人工ack。722次内部NMI不额外加进CPU计数。这些CPU输入沿用第十四轮受控继承fixture，和本轮原模拟器实际战后继承观察分开；不能据原核心帧末君主字段反推它执行了内政CA19路径。

调用示意（`actual`必须是已有CPU调用上下文，不能从Native存档虚构寄存器）：

```python
session = game.readable_campaign(actual)
result = session.main()
# 只有外部真实输入协议明确给出中断到达时调用：
result = session.nmi()
result = session.irq()
# 已完成内层实际RTI，并处于原暂停PC/SP之后：
result = session.resume()
```

本层不生成按键、vblank、IRQ线、RGB、PCM或硬件周期，也不写准备/结果/就绪/ack。缺失服务保持原callee依赖；显式端口输入耗尽保持等待。原6502只运行于独立py65对照侧，生产不解释控制IR、不执行原CPU。原模拟器长流程另见[Native报告](../runtime/README.md)。

复跑：

```sh
.venv-trace/bin/python scripts/verify_campaign_session.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_phase15_succession_integration.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/build_phase15_integration_receipt.py
```
