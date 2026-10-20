# Phase12 十行武将资料实际服务

战场main1/sub1 `$A244`先经selector39调用25A000肖像，随后真正调用25A012→B2D7资料producer。25A003→A033是年月／势力controller；25A006→C773是AI城市指令分派；25A030→BB73是城市金粮等word结转，均不能称属性页。29A030/A03C是姓名包而不是完整参数卡。

`OfficerDetailsUIServices`是有界独立具名Python：17函数、439原指令位置、1个十项inline分派，全部静态structuregaps为空。运行时只执行普通if/while和具名sourcecall，不解释opcode/IR/program.json，不用原CPUfallback。F308委托独立OfficerUIServices真namepointer／alignment；EA7C、E9BA、F2D7、F25F委托SceneSharedServices精确puremath／mapper；EADE复用ControlHelpers。不是语义textcallback冒充AXYP。

| 原row | 真实入口 | 显示／作用 | recordbyte |
|---:|---|---|---|
|0|`$B508`|姓名浊点/半浊点|None|
|1|`$B52D`|姓名／体／徳|[0, 4]|
|2|`$B507`|模板空行|[]|
|3|`$B5A6`|等级／知／忠|[11, 2, 3]|
|4|`$B630`|地形适性字形上半|[11]|
|5|`$B64D`|地形适性下半／兵／武／経|[11, 8, 9, 1, 6, 7]|
|6|`$B730`|武器／防具字形上半和CHR缓存准备|[10]|
|7|`$B770`|武器／防具字形下半|[10]|
|8|`$B4F3`|资料装备CHR shadow提交|[]|
|9|`$B507`|最后空行及终止|[]|

选择`0410[040C]`；`040D`是本卡的0..9行游标。目的地址是`[2400,2540,2680][040C%3]+32*040D`，即NAMETable中三个相隔十行的卡片资料槽，不按名称猜成水平三列。原0380命令20（32tiles）、0381/2地址、0383..03A2行内容、03A3=FF；007E只OR4并保留其他请求。若bit2已置位，直接真实RTS、不写row／packet；040D负值也真实早退。row9返回后游标存FF。源码不会清bit2、伪完成PPU或偷偷推进到下一行。

ID FE使所有行选原空白模板；ID≥ED跳过动态record叠加，其他无效ID仍可保留行标题。row0/1姓名用真正10byte原name记录、39/3Amarks及原alignment；与13byte汉字图身份表用途不同。知／忠／体／徳使用两十进制数字、首零留模板空白，忠100特殊输出两个原32tile；等级展示byte11high4+1的低十进制位。兵是低10bit字段，byte9high6不参与数字；経是原u16乘2后的高三位显示，等价floor(XP/50)，不改永久经验。

row4/5 affinity选择byte11mid2，前三编码原平／山／水，编码3读相邻原bytes不赋正式名。装备low5武器selector与high3防具selector+24，映射physical16的32个17byte资源record；byte0是CHR页、后16字节为上／下各8tiles，防具tile加40但空白01保持。row6准备040E/F，row8若0401!=3提交BC/BD；mode3不提交。row7已将数据窗恢复selector49→physical17。没有立即硬件CHR／palette上传。

最终6693原CPU完整返回病例、另5sourceguards，0失败；动态观察439/439本地原指令位置，不等于全部输入组合或整个NES帧已验证。覆盖全部237武将×十行×真实busy／available、FE／FF与负row、mod3卡槽、原SP边界、100忠特殊值、u10high6／u16XP、全部packedbyte11／全部装备byte10、mode3缓存、全部17localentry。全部2048RAM（包括stack残留）、8192SRAM、AXYP/SP/PC、端口序与mapper对照，生产原CPU helper callback=0。fixture明确准备record／row／queue字节作CPU条件矩阵，不冒充普通原游戏输入。重复producer调用保留queuedrow的guard单列；源码不替代真实consumer。

```python
owner = OfficerDetailsUIServices(memory, OfficerDetailsData.from_rom(rom))
result = owner(actual_ServiceCall)  #actualphysical25/26 + existingcallerframe
# run_entry(0xA012,actual_registers)或tick(actual_registers)
```

- [独立完整具名源码](../../../source/recovered/officer_details_ui_services.py)
- [最终CPU矩阵／guards／pins](validation.json)
- [十行字段、完整原bytes和服务合同](evidence.json)
- [原code／明确data／callercontext](original-ranges.asm)
- [静态闭包与inline分派](static-control.json)
- [原CPU实际位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_officer_details_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_officer_details_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence
```

`--generate`只在buildtime从原bytes重生source，之后必须重跑矩阵冻结pins。原core实际打开／返回／截图在单独native证据域，未包含于这里的CPU计数。
