# 城市动作服务：装备候选与招募忠诚

本轮补齐两个城市27/28远端动作，独立手写具名函数，不解释IR或执行原ROM代码。8 A01E（原 `4C 51 C8`）进入physical9 C851，42条原指令；10 A006（原 `4C 3F CF`）进入physical11 CF3F，含本地D2AB/D40F/D61E共79条原指令。两者没有外部callee、PPU/APU/mapper访问或等待确认。

## 装备候选

27/28 C7AB真实selector28调用8 A01E。0402索引physical28 C801的30字节城市组表，原数据仅为0/1/2；0012是0..3类别。C851选择 `group*16 + category*4` 开始的四项，写044C[4]装备ID，并按physical9 C89E的32个LE16数值建立042C的四个3字节记录，第三字节始终0。C8DE原offers表共有6组、每组4类×4项，source支持所有96项的表内上下文；它没有购买或扣金行为。

## 招募忠诚

27/28 AD32和D46C调用10 A006。原逻辑读取30指定的leader byte4徳与31指定的target byte3忠，计算 `max(10,min(90,(70+徳//10−旧忠)&255))`，仅写目标byte3。负差先按原8bit下溢再夹值，不能按普通有符号减法夹0。与旧OfficerTransfer纯玩法核心相同；本轮还恢复真实D2AB指针、D40F商/余数scratch、所有局部JSR栈残余与最终AXYP/SP/PC。D61E在此ROM中就是1字节RTS，原空body也保留真实caller栈写入。

FF/raw IDs仍按12字节寻址，不偷偷改为另一武将或假返回；237..255仅作为服务字节地址边界，不能宣称为正常武将。两个body均不写city owner、名册、驻城、status或兵数字段。

## 原 CPU 对照与范围

正式回执 2005 次完整原CPU返回、5 个源码拒绝测试。比较全部2048B RAM（包括free-stack残余）、全部8192B SRAM、AXYP/SP/PC、银行和有序端口；这些body实际端口序均为空。source侧原CPUcallbacks=0。覆盖全部6×4shop组合、忠诚夹值/下溢、同记录alias、原字节ID边界、word除法/除数0边界、全部256个callerSP；此处都是明确准备的有界service CPU输入，不是原核心内部trace。decimal flag需清除是该py65对照协议，源码在变更前拒绝D标志与表外shop索引；原CPU不执行这些非法表外索引。

实际原核心城市菜单及资料浏览双跑证据在[上一层runtime](../runtime/README.md)；该自然流程在动作确认前取消，没有自然观察这两个动作的扣资源/玩法后续。新的城市coordinator整合验证单列，不与这里的body对照混计。

```python
rules = CityActionBridges(memory, CityActionData.from_rom(rom))
rules.run_entry(0xA01E, registers=actual_caller_registers)
rules(ServiceCall(...))  # accepts only the exact physical pair/owned entry
```

```sh
.venv-trace/bin/python scripts/verify_city_action_bridges.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_action_bridges.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[源码](../../../source/recovered/city_action_bridges.py) · [验证回执](validation.json) · [字节、表与hash证据](evidence.json) · [原装备函数](shop_offers-original.asm) · [原忠诚函数](recruitment_loyalty-original.asm)
