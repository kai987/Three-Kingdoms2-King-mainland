# G086 配兵指针的完整生命周期

仅选择阶段23的一个 unknown-producer 组 G086 的配兵子链，针对其中10个D850..D8BC读写点；另3个装备包点及DC6F计数点不在本轮新body内，不声称整个14点组已闭合。新增 [PointerLifecycleServices](../../../source/recovered/pointer_lifecycle_services.py) 继承冻结 CityUIController，具名替换六个原生成helper：D64A、D773、D7A8、D94E、D96F、D987。原选择/配兵/数字packet正文共379指令位置、913原代码字节，39字节列表/光标数据独立记账。阶段5已证明的 `garrison_allocation`／`normalize_reserve` 算术不重新计为首次发现。

玩家在真实行游标上输入后，D805调F2AF建立城市指针，按`(0012+17)&255`读取名册ID，再由F2D7建立完整武将指针。D987保存00/01到10/11；D996..D99C把01/02当数值临时区，EA7C自身不写00；除法后恢复00/01，随后才读写+8/+9。显示前再次读取兵word，之后01转作数字临时区，该指针世代结束。父B431在结束行确认后重新取得城市指针，将工作库存042C/D写到city+12/+13。详见 [原字节与偏移](static-catalog.json)、[逐步生存期](pointer-lifetime.json)。

完整原16位兵数、999检查在归一前、10000库存边界及低字节超额修正、左右输入次序、选择取消/带洞压紧、真实调用栈、BCD/行地址packet均保留。031C..与007E|1是请求，不自动完成文本/PPU。裸raw ID、ZP/栈/16位回绕别名单列机械CPU输入，不推为正常UI可达性；完整指针保持合同只对不别名的真实武将记录和无额外中断模型有效。

[validation.json](validation.json) 当前 1038 原CPU父案通过，分类 {"actual_caller_RTS": 1036, "strict_missing_dependency_prefix": 2}，另5个源码guard。比较全部2048 RAM、8192 SRAM、AXYP/SP/PC、有序IO、四实际PRG页与N163，未排除闲置栈；Source原CPU callback=0。379新位置动态命中379个，位置覆盖不等于所有路径/输入已证明。受控数值/软件caller与真实Native调用输入分别标明。

API `PointerLifecycleServices(memory,rom,services).run_entry(entry,registers=actual)`／`__call__(ServiceCall)`，保留真实返回帧。要求物理27/28与实际入口PC，不允许seed_return；pending必须由同caller继续，缺少菜单/除法owner严格停留。其他冻结父菜单与真实固定服务继续复用。本轮并未给城市+1/+28..31新正式名称，也未恢复其他unknown-producer组。

```sh
.venv-trace/bin/python scripts/verify_pointer_lifecycle_services.py ROM.nes
.venv-trace/bin/python scripts/analyze_pointer_lifecycle_services.py ROM.nes
```
