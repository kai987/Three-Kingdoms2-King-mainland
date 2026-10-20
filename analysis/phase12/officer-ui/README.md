# 第十二轮：武将姓名包与精确F308服务

[officer_ui_services.py](../../../source/recovered/officer_ui_services.py) 是手写的条件/循环源码，恢复physical29/30的六个公共入口与两个局部姓名排列过程，并拥有固定F308。生产不读控制IR、不解码opcode、不执行原CPU。

**A030和A03C生成姓名图块包，不是武将属性卡，也不是Text.consume。** 它们写RAM0380后置007E.bit2，实际PPU消费、字体上传、文本推进及完整资料页由其它服务负责。没有替它们写入动画/文字ready。

| 原入口 | 实际主体 | 输入与行为 |
|---|---|---|
| 29 A030 | A8A4 | 0000武将ID；复制左侧姓名模板，排列标记/普通字形，置007E\|4 |
| 29 A03C | A991 | 0000武将ID；0001为0选A9FD模板，任何非0选A9C3模板 |
| 29 A033 | A8FD | 04AE武将ID，使用A91D模板 |
| 29 A027 | A830 | 按0664[0509]读取选中武将ID，使用A856模板 |
| 29 A02A | A890 | 保存0000；真实EE07 selector3D→A015请求palette0，再恢复ID并落入A8A4 |
| 29 A036 | BC66 | 清0140..017F，共64字节；没有设置PPU完成标志 |
| 31 F308 | F308 | A为ID；切姓名数据窗、计算指针、统计非标记code并返回对齐值 |

公共stub与主体、数据表及原偏移均在[evidence.json](evidence.json)和[original-ranges.asm](original-ranges.asm)，偏移包含16字节iNES头。原REA pair29映像、mapping和evidence bundle单独固定hash；REA/Ghidra产物是原分析背景，本模块不在运行时使用它们。

## 姓名算法的可观察副作用

F308先保存ID到0002，经真实F25F(Y=$30)向E000写$30，并将E1设$30。8000数据窗因此为physical16，调用后不自动恢复。它将 `$901A + 10*ID` 写0000/0001，再从该地址扫描到00。

X统计除$39/$3A之外的code；Y统计所有code，包括这两种标记。最后A取原`F35F[X]`对齐表，不能将它当作字符数返回。指针末尾原ADC对全部byte ID都清C和V；其它flags按真实扫描/对齐读取更新。初版完整flags矩阵发现并纠正了V遗漏，最终回执包含修正后的源码。

A957将$39/$3A写到`03A5+X`，普通code只推进X；A976将普通code写到`03B1+X`，跳过$39/$3A。两者都先真实调用F308，保留内层JSR与返回frame。姓名的公开作用与寄存器合同是分别恢复的，没有拿其它文字服务的临时AXYP来冒充。

每个模板的静态跨度为58字节，原代码却以Y=$3A开始下降复制，**实际读取59字节**。其中第59字节来自下一region：四张后接代码，一张A9C3后接A9FD另一模板。代码不执行这个字节，只将它作为原始数据复制到03BA；包的FF终止符位于此前。源码保留这个CPU可观察的写入，没有擅自把循环缩短为58字节。

## 真实caller与等待

```python
from source.recovered.officer_ui_services import OfficerUIServices

owner = OfficerUIServices(memory, rom, services=actual_scene_coordinator)
result = owner(call)  # ServiceCall，已有原caller栈/AXYP/银行
# 也可在已准备caller的上下文使用run_entry(0xA030, registers)。
# F308为固定helper，不要求当前pair是29/30。
```

`__call__`对banked入口要求physical29/30，F308可接其它真实caller。服务不种植0200或其它返回地址；直接CPU fixture才在验证器明确准备返回栈。

A030/A03C及共同helper不需要文字worker或PPUSTATUS输入，F25F由已有独立mapper服务完成。A02A则必须接真实EE07服务，callee A015可复用SceneInitialization；没有服务时停在EE07原边界，继续持有0000保存值与caller栈。只有dict status=returned且真实PC/SP匹配才能继续；None/waiting/error/blocked即便伪改PC/SP也不被接受。重复resume不重做prefix。

## 最终原CPU对照

[validation.json](validation.json) 共**5,557项实际原CPU完整返回、10项另列源码guard、0失败**。源码侧原CPUcallback与IR执行均为0；A02A五例使用独立SceneSharedServices/SceneInitialization组合。全体案例比较完整**2KiB RAM、8KiB SRAM、AXYPSPPC、银行、有序端口读写**，没有自由栈字节排除。

| 域 | CPU例数 |
|---|---:|
| F308全部256个ID byte ×4输入variant | 1,024 |
| A030全部237合法姓名 ×4原PPU请求byte | 948 |
| A03C全部237合法姓名 ×左右参数 ×4请求byte | 1,896 |
| A033全部237姓名 | 237 |
| A027全部237姓名 ×slot0/10/19 | 711 |
| A957/A976直接调用，全部237姓名 | 474 |
| 清属性buffer，256输入byte与D=0 flags组合 | 256 |
| palette wrapper+独立真实callee | 5 |
| 原攻击控制器在EE07 callee边界保存的caller frame | 6 |

最后六例直接读取[callee-inputs](../dependencies/callee-inputs/)的原RAM/SRAM/registers/banks，返回原EE4D恢复点。它们来自348项合法攻击控制CPU矩阵中的实际helper调用，不是Nestopia内部trace，也不是自然游戏录像；已有快照没有被改写。其它案例都是明确准备的CPU数据fixture。标准py65对照限制D=0；NES2A03本身没有decimal arithmetic，不以这些案例声称模拟了硬件时钟。

10个source-only guard覆盖未知入口、错误pair、strict callback状态与PC/SP、不重复prefix及真实callee后续恢复。它们不是十个原CPU案例，不是PPU/IRQ/文字完成证明。

```sh
python3 scripts/analyze_officer_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_officer_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

本范围不包含29 A003文字controller、25 A000肖像或完整武将属性/资料页。源端按真实数据读取保留F308的全部byte-ID行为，姓名包矩阵以237合法姓名为域；不将有限矩阵当作所有任意RAM别名/硬件时序已经穷尽。
