# 第十一轮：战场AI初始化与NMI辅助服务

[battle_setup_ai.py](../../../source/recovered/battle_setup_ai.py) 独立恢复physical8/9的战场AI初始化及三个真实NMI辅助入口。生产代码不读取IR、不解码6502、不执行原CPU。原ROM只供不可变的数据/图形表读取；调用原CPU的是另外的验证器。

| 原公共入口 | stub实际目标 | 可读接口 | 行为 |
|---|---|---|---|
| 8 A003 | 8 B130 | `initialize()` | 两方controller gate、非主将排序、策略分组及原布阵坐标、缓存清理 |
| 8 A012 | 9 CFA2 | `draw_HUD()` | 按8F、04C8、0500和5E条件构造AP/回合/双方数值等HUD OAM |
| 8 A015 | 9 D1ED | `draw_units()` | 更新CHR选择字节、城市/单位世界坐标sprite请求及原视口判断 |
| 8 A021 | 9 D57B | `step_camera()` | 根据0508高4bit的原请求按2像素推进相机、更新009C与消除完成方向位 |

**A021不是D66E。** D66E属于A027另一入口，本模块未把它套入NMI包装。所有file offsets包含16字节头；799个原指令位置、19个局部过程、9张原数据表固定在[evidence.json](evidence.json)。大部分控制来自离线CFG结构化；B1B0策略/位置与B371排序另外人工写成条件和嵌套循环。离线自动结构化计数为66个if区域、8个自然循环，人工部分另有直接循环，不能把这些数字当原CPU动态指令数。

## 初始化的真实规则

B130首先将 `6FA1..6FE0` 共64字节设FF，再将 `6FC9..6FDC` 的20字节设0。按0507低/高nibble找两方ruler，只有该ruler记录byte3等于3才初始化该方AI。其它值不进入此分支，未按游戏常识另赋正式controller名称。

AI方的commander为slot0或10，策略值设0。B371数该侧十槽的非FF武将数再减1，将结果暂放6F94；非主将数量0..9的正常域内，当数量至少2时执行相邻比较。下一位武力**大于或等于**当前位就交换；重复完整比较范围，不是稳定排序。同值也交换，因而必须保留原tie行为。

交换仅涉及 `0664` 武将ID、`0628` 阵营/适性、`063C` 百兵缓存三组数组。坐标、condition和其它数组没有一起排序。输入应是commander后的连续非主将前缀；不能将稀疏空槽或全空AI军队当成这个高层正常域。全空时原减1会回绕FF，本轮没有为它虚构安全结果。

六种策略profile各有9个2字节记录，B3FD共108B。ruler1/5选family1，2/4选family2，0/3/6选family0；第二侧额外加3。每记录4个nibble分别是策略1..4的数量，总数等于1..9非主将数量。缓存写在6F99..6F9C或6F9D..6FA0，然后按排序后的次序填策略1..4。策略编号0..4是机械ID，此处没有凭名称猜正式策略名。

非主将数量0时跳过profile读取，**旧6F99..6FA0缓存未被统一清零**。两侧若没有AI分支，6F91也不被初始化为0。最终清除两组埋伏的完整8字节04D8..04DF，并将6F94/95/96归0；6F92随机游标没有因此被清零。

布阵分别使用原城市邻接/方向表和bank6的两个30项指针表。找052A出发城在当前城050E的邻接项；遇终止符仍未匹配时用原fallback0。第一侧偏移每模板32B、组起点 `[2,8,12,20]`；第二侧每模板36B、组起点 `[2,12,22,28]`。每坐标对是Y再X，先写commander，再按策略group分配位置。不能将两方模板大小或坐标次序合并成一种“统一布阵”。

`strategy_profile(ruler, side_base, noncommander_count, rom)` 独立解读上述表；`ordered_noncommander_triplets(triplets, rom_or_records)` 复现相邻/相等交换。传入原ROM时后者用初始武力；当前游戏应传共享记录内存，读取实时byte1。两函数都是高层数据规则，没有原CPU/IR执行。

## NMI辅助与F09C合同

CFA2只在8F=0、动画04C8=0、battle main<12及5E.bit5置位时构造HUD。D57B在main≥12时直接返回，否则按0508方向位独立检查X/Y推进，保留上/下边界、byte回绕、两方向同时置位及原009C掩码；不偷偷把它替换为手柄读取或高层移动报价。

D1ED构造OAM并维护B2/D6等CHR字节。它的F09C调用保留caller提供的0003 tile bias和0004 vertical clip，不能冒用会重设这些字段的F092。该变体复用 [BattleBackgroundInitialization](../../../source/recovered/battle_background_initialization.py) 的独立源码；本模块没有重复恢复renderer。PPU像素、DMA上传、IRQ信号和真实视频帧仍由硬件/core或外层服务负责。

```python
from source.recovered.battle_setup_ai import BattleSetupAI

setup = BattleSetupAI(memory, rom, services=actual_scene_coordinator)
result = setup.run_entry(0xA003, registers=call.registers,
                         seed_return=False, return_pc=call.return_pc)
# setup.draw_HUD(...), setup.draw_units(...), setup.step_camera(...)
# 缺失callee时result为dependency，真实服务到达caller后setup.resume()。
```

同严格ServiceCall协议：必须是dict status=returned，并且真实PC/SP匹配。缺少固定mapper、BCD、sprite等服务时保持pending，不能仅凭服务声明成功来pop。返回的 `setup_fields` 显式列出策略、参数、auxiliary/ambush cache和相机请求；6F94在初始化排序中暂作数量，初始化结束归0，后续AI合作扫描会复用同一原地址。

## 原CPU对照

[validation.json](validation.json) 最终**2,326项原CPU完整返回、4项单列源码guard，0失败**，源码侧的原CPUcallback次数为0。固定服务使用独立SceneSharedServices，F09C使用独立background模块：

- 280项：7种ruler、两侧gate组合、非主将0..9，以及等武力/不同武力的相邻交换；高层triplet/profile结果同时与实际原CPU输出核对。
- 1,024项：全部256个相机请求byte，四组边界/普通坐标。
- 158项：30个城市的邻接方向与fallback布阵输入。
- 768项：复用F09C的全部256种flags×3个clip值，保留caller bias；这是callee集成合同验证，不是本模块又恢复了一个renderer。
- 96项：HUD/单位服务的main、timer与animation条件。

比较AXYPSPPC、bank、有序端口读写、全8KiB SRAM与**1,972个声明RAM地址**：0000..01B3及0200..07FF。包含0100..011F palette、0120..013F备份、0140..01B3原图形数据；剩余自由CPU栈残余排除。完整地址列表和真实源码/依赖hash在回执内，不能写成比较全2KiB RAM。

这些是受控CPU数据fixture，不是自然campaign或原Nestopia视频。输入准备了ruler/controller、连续单位、武力和城市/相机字段，ROM未改；没有伪造ready/动画/PPU完成。4项guard仅校验高层profile域，不计入原CPU案例。未穷尽所有合法sprite descriptor、稀疏军队、错误ruler nibble或每种硬件时序。

```sh
python3 scripts/analyze_battle_setup_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_battle_setup_ai.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

分析器只在构建时复用已冻结结构化编译器；生成的生产模块没有该依赖。原字节、19个具名过程和不可变表逐项可核验，新源码不改变旧阶段文件。
