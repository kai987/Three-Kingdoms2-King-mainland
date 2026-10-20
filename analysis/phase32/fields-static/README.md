# 阶段32：本次JSR栈帧与B517的两个ROM读取

等待Root执行独立原CPU合同；目前不迁移分类。分析器本身不执行CPU、Source、Native或旧生成器。

原8:A09E与8:ACAB都是真实`JSR B517`，分别把本次raw返回word A0A0／ACAD压入栈。B517把本次两字节PLA到21／22，B525与B52B读inline word，最后`JMP($23)`。验证停止于原JMP完成、目标第一条指令之前；这些是transfer前缀，不是RTS。

完整当次JSR、pair8/9、原代码/表、期间无中断或外部写的前提下，固定ZP写20..24不碰0100栈，SP环绕也不改变两次PLA的当代来源。两读之间只有STA23与INY，live21/22不变。全部rawA0..255只生成byteY；逻辑EA仍在代码ROM窗口。任意裸B517栈、B525/B52B中段入口不能借此合同。

`AND0F`只证明0..15。strategy表只有8项，predicate表16项；strategy8..15及更大rawA的越表目标保留，绝不伪称合法策略或继续执行目标。裸stackword6000及中段21/22=6000保留城市+1和+28..31反例。

全部1526项：1201条件不交／80可能／245未知，余325；本轮正式迁移0。其余1524项权威合同与raw345=104操作数／13数据／228未证入口不变。条件地址证明不等城市字段未用，正式名称仍null。

- [当代栈与原字节合同](current-frame-dispatch-contract.json)
- [原指令和inline数据](original-ranges.asm)
- [全部1526项](all-indirect-accesses.json)
- [两处被选访问](selected-accesses.json)
- [保留候选](remaining-accesses.json)
- [CPU合同回执](cpu-contract-validation.json)
- [分项终审](verification.json)

Source／Native病例均0。本轮不重记阶段7／14已知dispatch语义，不声称中断闭合、完整目标行为、全ROM未用或官方字段名。阶段32完成后等待评估，不自动33。
