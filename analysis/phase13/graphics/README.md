# 阶段13：真实图形数据服务调用协议

恢复physical23/24三个有界服务：`A012→A61C`选择地图块指针及数据窗；`A015→AEF0`选择属性指针及数据窗；`A018→A983`根据阵营控制方式、主将位置、显示兵力缓存和地形适性产生四个单位tile。生产源码是具名函数与普通if/loops，没有IR、opcode解释或原CPUfallback。已有BattleGraphicsServices曾具备这些结果的语义计算；本模块补真实caller栈、所有flags和mapper协议。

原120组chunk/attribute pointers和120个mapper selector逐条保持。输入0000的active slot0..19、063C显示缓存0..10、选中0507 ruler nibble0..6有明确源合同。单位控制byte0、1、其余原值分别选择三套字形；slot0/10有原主将覆写，满缓存10另有原字形覆写；affinity3保留各套默认字形，不赋不存在的正式名称。

`23A012`真实bytes是`4C1CA6`。`13D72E`是调用该服务的map-refresh位置，不能把它当本服务body。`29A012→BC41`是另一个独立入口，未混入这里。

最终9440原CPU完整返回病例，另7source guards，0失败；本地动态位置201/201。比较全部2048RAM（含实际stack残留）、8192SRAM、AXYP/SP/PC、端口写序与mapper banks。矩阵覆盖全部120块×两个exports/两个bodies×flags，20slot×11cache×4affinity×4controller raw值×2侧。CPU fixtures是明确准备的合法输入矩阵，不是自然游戏帧。这里没有PPU读取，F25F仅产生真实E000写请求；不上传nametable、合成帧或清ready。

```python
owner = UIGraphicsInitialization(memory, UIGraphicsData.from_rom(rom))
result = owner(actual_ServiceCall)  #actual23/24pair + real RTS frame
```

- [独立源码](../../../source/recovered/ui_graphics_initialization.py)
- [CPU对照与最终pins](validation.json)
- [原bytes、表和调用合同](evidence.json)
- [原汇编及明确数据](original-ranges.asm)
- [原CPU实际执行位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_ui_graphics_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_ui_graphics_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
