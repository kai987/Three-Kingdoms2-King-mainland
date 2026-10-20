# 战后调用的忠诚入口

新增[PostbattleLoyaltyBridge](../../../source/recovered/postbattle_loyalty_bridge.py)准确暴露physical10/11 `A009→CF7C`。A009原bytes`4C7CCF`仅JMP，不改flags或caller栈。CF7C和它的本地寻址/除法/RTS函数已在冻结[DomesticCooperationController](../../../source/recovered/domestic_cooperation_controller.py)独立恢复；本轮复用这些可读函数，**不重新进入A000/A00F内政主循环，也不调用CA19继承**。这是原25C2EA/C05B的真实远端忠诚依赖。

原七组家族排除表、徳/5差值、原ADC/SBC byte溢出、扣10及10..99截顶、同址记录均保留。scratch30/31/32/33的原输入含义以实际调用场合解释，不强把所有场合固定成旧/新君主。名册离开、状态/地点写回由后续战后消费者承担，本入口只执行真实忠诚body。

2,472项实际callerRTS、8guard、0失败。7组×4个30×4个33×5个31×3SP的别名矩阵、全部24条实际家族排除ID和全256忠诚×3徳组合比较全2048RAM（含闲置栈）、8192SRAM、AXYP/SP/PC、端口/银行和N163图；237/255等raw记录指针不当有效武将身份。JMP新增公开3B，既有正文局部闭包121位置、动态121，不把它们称本轮新写的全部内政代码。

调用必须有实际寄存器、进入PC/银行与已有返回栈，拒绝seed/错误returnword/SP，不伪造RTS。通过SceneCoordinator的精确入口owner接入；未知调用保留dependency。GPU回执和忠诚回执是独立服务对照，Native画面/声音和父战后整合另列，不混成新CPU例。

[原字节](original.asm) · [静态目录](static-catalog.json) · [原CPU位置](executed-instructions.json) · [对照回执](validation.json) · [证据及hash](evidence.json)
