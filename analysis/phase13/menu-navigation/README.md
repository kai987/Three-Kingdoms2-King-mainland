# 精确菜单导航与局部调用栈

原fixed31 ED19..EDF4菜单服务独立恢复为`CityMenuNavigation`，保留Shared历史冻结文件。八个宽度入口ED19..ED3C给1..8，ED41使用原A宽度，EDDD计算原byte offset；不执行原代码、IR或PC指令表。

方向按right80、left40、down20、up10顺序执行。每个方向保留ED4A/54/5E/68真实JSR，内部值查询保留ED74/EDA1/EDAC真实JSR；最终ED6B→EDDD写原returnword ED6D。这修正了旧Shared语义menu在已返回后缺少两字节inactive stack残余的问题，玩法数据与旧规则一致，新的合同包含全部free-stack RAM。

0012旧选项为0才可换行/回绕，最后才写新选项；不把它另解释为独立开关。left拒绝仅FF，80..FE仍可被其选中；right/down与up终点按signbit判断，不能统一为FF判定。row×width+column、X/Y和字段均保留byte wrap。

2120次原CPU完整返回，5个源码拒绝/依赖测试，0失败；比较全部2048RAM（包含全部inactive栈）、8192SRAM、AXYP/SP/PC、ports/banks。覆盖宽度1..8的合法三行/空项菜单、9种方向输入、原raw offset边界、全部256 callerSP和非FF负值left特性；这是明确准备的服务CPU输入，不是Native内部寄存器。静态98原指令位置，动态命中98；位置覆盖不等于全部输入组合。

两项缺sentinel测试保持原循环dependency于ED9E/EDCF，原caller不RTS；重复resume走真实循环仍等待，不清ready。它们单列source guards，不计原CPU完整返回。其余guards拒绝decimal协议、缺实际caller寄存器和未知target。

```python
owner = CityMenuNavigation(memory, rom, callbacks=None)
owner.run_service(0xED1E, actual_registers)
owner(service_call)  # original existing caller frame; never seeds a return
```

```sh
.venv-trace/bin/python scripts/verify_city_menu_navigation.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_menu_navigation.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[新源码](../../../source/recovered/city_menu_navigation.py) · [原字节/frames](evidence.json) · [实际CPU回执](validation.json) · [原汇编](original-ranges.asm)
