# 阶段13：新剧本持久记录初始化

真实入口是physical29 `A018`（原bytes `4C8BDD`）→physical30 `DD8B..DE7D`，来自全局main11 `E42F`。它不是图形loader；它有意替换游戏的新剧本记录。独立`ScenarioInitialization`使用具名Python循环、复制和原共享RNG／mapper服务，没有原CPU、IR或opcode执行。不会代替全局后续选择／背景／PPU工作。

先保存6F43，清6000..6FFF，恢复6F43；原E87A表采样低3位，遇5..7重抽，接受0..4写6F45。设置6F04/6FE2=FF和0400/0401=11/0。真实F25F selector48将数据窗映射physical16，从8C00复制960B到6000；selector49映射physical17，从8000复制2880B到63C0。后者是240个12B池槽的原copy长度，不代表确认了240个武将身份；已确认姓名／肖像仅237位。最后6F00=89、6F01=0，6F83..6F89=FF、6F8A=0。7000..7FFF不动，原6F43保留。

调用方须已经使低4KiBSRAM可写；本服务没有F800写，也不会偷偷改变mapper保护。CPU对照使用原Bus保护4C（低4KiB可写）与明确相同软件memory合同。复制与clear都保留真实scratch、flags、stack残留和返回PC/SP。64种RNGcursor×两个真实entry×两个保存byte／SP／flags共256原CPU完整返回病例，另3guards，0失败；本地执行位置103/103。全部2048RAM、8192SRAM、AXYP/SP/PC、写端口序和banks逐字节比对。

```python
owner = ScenarioInitialization(memory, ScenarioData.from_rom(rom))
result = owner(actual_ServiceCall)  #actual29/30pair, real caller frame
```

- [独立源码](../../../source/recovered/scenario_initialization.py)
- [最终原CPU验证与pins](validation.json)
- [原code／template数据／合同](evidence.json)
- [原汇编与数据范围](original-ranges.asm)
- [实际原CPU位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_scenario_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_scenario_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

这些是独立服务的CPU输入条件矩阵，不是自然整帧回放；没有完整NES或新剧本可玩性的额外声明。
