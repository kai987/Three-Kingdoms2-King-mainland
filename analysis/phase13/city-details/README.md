# 阶段13：城市武将资料完整五阶段控制器

真实citymain12从27A04D经selector39 inline21A0调用physical25 `A021→AFE5`。原stub是`4CE5AF`；`A01B→B964`属于其他武将扫描路径，不是本资料UI。源码为12个具名函数、307个原指令位置、5阶段／1个inline分派，静态结构缺口0。不执行ROM、IR或opcode，不借原CPUfallback。

|0401|真实phase|作用|
|---:|---|---|
|0|AFF5|真实palette0、压紧城市10项名册、准备首张卡的row0|
|1|B041|每调用一次真实B2D7 ten-row producer；040D==FF后配置split／scroll进入2|
|2|B086|画当前肖像、上下切换／确认返回、原0140／0150通知任务处理|
|3|B136|画当前肖像并生成相邻资料卡；rowFF后进入4|
|4|B155|旧／新两肖像按方向移动、每次2pixels；80后更新选中index并回2|

portrait索引是`0410[0408]`，资料producer索引是`0410[040C]`。切页动画前后这两个index可不同：040C已指新卡时，0408仍指旧肖像，直到80pixel完成才递增／减。`0410`本身一直是列表第一项，不能把每帧0410直接标成当前显示武将。city32B record的17..26共10槽压紧时跳过FF；上下边界及下一项FF严格依原bytes处理。0083的10/20方向触发两种原切页；左右没有因此自动换武将。

原十行worker是25 `A012→B2D7`，不是AD81。复用冻结OfficerDetailsUIServices全部字段／blank／equipment请求；CE1F复用实际portrait caller；palette0通过真实EE07 farcall／mapper／stack进入29A015→30DBB1。等待007E bit2／0140是原软件状态，源码不清ready。所有PPU／IRQ／CHR变化是原shadow或queue请求，consumer及帧调度由其他真实服务执行。

最终7509原CPU完整返回病例，另5source guards，0失败；本地执行位置307/307。包括5phase×所有256button bytes×busy状态、全部237武将／关键rows／selected portrait、30城空／稀疏／满名册、10slot首末／空下一项、双向0..80transition／所有关键卡rows、notification0/1/2/9/10/11/127/128/FF与真实panel busy。全部2048RAM（含stack残留）、8192SRAM、AXYP/SP/PC、写端口序与banks比较，source原CPUhelper callback=0。fixture确实准备caller/cache/queue/record条件矩阵，不是native ordinary input证明。

```python
owner = CityOfficerDetailsController(memory, CityOfficerData.from_rom(rom))
result = owner(actual_ServiceCall) #actualphysical25/26 and realRTS frame
# run_entry(0xA021,registers) / tick(registers) are one cooperative update.
```

- [完整具名源码](../../../source/recovered/city_officer_details_controller.py)
- [原CPU矩阵与最终pins](validation.json)
- [原bytes、phase表、字段与合同](evidence.json)
- [原code和明确inlineDATA](original-ranges.asm)
- [静态闭包／5phase](static-control.json)
- [真实原CPU动态位置](executed-instructions.json)
- [冻结十行worker证据](../../phase12/details/evidence.json)
- [冻结肖像服务证据](../../phase12/portraits/evidence.json)

```sh
.venv-trace/bin/python scripts/verify_city_officer_details_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_city_officer_details_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence
```

`--generate-source`只在buildtime重生具名source，之后必须重跑原CPU矩阵。native城市打开／上下切换／返回在独立阶段13runtime域，不计入本模块CPU数；本模块不宣称整帧、完整NES或原始作者源码。
