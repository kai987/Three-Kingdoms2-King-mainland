# 战后真正缺失的年月图形请求

新增[PostbattleGraphics](../../../source/recovered/postbattle_graphics.py)恢复physical29 `A01E→A6B6`，93条原指令、两次真实`E9BA`十进制转换调用。实际使用者是25`AD95/AE51`的远端`Y=3D,A01E`。它只构造`0380..0394`中的两条七字形请求，目标nametable2043/2063，写`7E|4`；不初始化世界、不完成PPU上传、不推进city13或写ack。真实消费者保持独立。

年值加100保留进位成word，年89/90显示189/190；原0-based月加1，月1..9的十位使用原空白字形。原月255字节加1回0后，高字节仍显式清0，保留这一边界；不是合法月份。Python抽出的字形写方法不制造额外JSR，只有A6CB/A714的真实帧。

4,548项实际callerRTS对照、8guard、0失败。全部256年×12月份、5年×244额外raw月份以及256个SP均核完整2048RAM含闲置栈、8192SRAM、AXYP/SP/PC、顺序端口读写、银行和N163图。局部动态93/93位置。原CPU只在独立py65对照侧运行，生产没有CPU/IR解释或模拟vblank。raw月12..255只是明确边界输入。

调用必须有实际寄存器、进入PC/银行与已有返回栈，拒绝seed/错误returnword/SP，不伪造RTS。通过SceneCoordinator的精确入口owner接入；未知调用保留dependency。GPU回执和忠诚回执是独立服务对照，Native画面/声音和父战后整合另列，不混成新CPU例。

[原字节](original.asm) · [静态目录](static-catalog.json) · [原CPU位置](executed-instructions.json) · [对照回执](validation.json) · [证据及hash](evidence.json)
