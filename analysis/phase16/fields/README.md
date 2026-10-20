# 城市未决字节与适性编码3

本轮新增独立源码 `source/recovered/field_semantics.py`，旧字段表、历史源码、原ROM和既有Native产物保持原字节。适性编码3的**机械行为已确认，正式名称与自然生产者仍未确认**。城市+1只确认了错位word读取，+28..31仍未命名。

## 全银行调查范围

`all-bank-instruction-atlas.json` 汇集61份冻结静态控制图、原CPU执行目录及直接控制流闭包，共46,518个指令位置、107,156个指令字节。另以 `all-PRG-address-pool.json` 检查全部32个物理银行、262,144个PRG字节，原始Y立即数/间接寻址候选20,595项。原始候选明确分为已知指令起点与未分类/数据；没有把字节吻合直接提升为可执行代码。

`pointer-field-accesses.json` 在CFG上跟踪Y常量集合、常见计数循环、零页指针复制及原F2AF/F2D7/F368/F387、D105/D283/D2AB/B491生产者。1,463个间接访问中684项同时解出了指针种类与Y集合；779项仍缺指针身份或动态索引。此前预览742/721已在核查原producer合同后收紧：F368只有已证明ruler索引0..6才能称为君主指针，7..15会越14字节表；D105实际返回owner而非指针高字节，B491实际Y=0。未知callee会保守清除暂存事实，computed dispatch及$8000映射不明处保留边界。因此这些结果**不能证明全ROM无人生成某编码，也不能证明未决城市字节完全未使用**。银行0..7、16..22未获得可执行指令种子，不意味着它们的字节均已被证明是纯数据。

历史phase7/9等执行目录中的4,117条file-offset元数据没有包含16字节头。本轮以physical-bank/CPU地址重算后原字节吻合，并在新atlas的`metadata_offset_repairs`逐条保留旧值和新值；未改历史冻结文件。新证据全部使用 `16 + bank*8192 + (CPU & 8191)`。

新增 `pointer-taint-refinement.json` 不执行原CPU，仅在离线CFG上补充跨callee的may-write摘要、00/01到10/11及20/21、22/23复制、scratch计数游标、明确CLC/SEC的byte算式、不可变ROM表读取。未知间接store/计算分派会保守clobber所有跟踪字段，不假设它们不会写scratch。每个已排除访问带原指令字节、pointer producer JSR及原callee写集合；数值常量指针另外列原上下文。

细化后676项仍不能同时解出精确record/Y，另外以地址区域证明可排除其中部分：356项为其他record、14项ROM/name窗口、17项非city RAM/IO、421项已知city的其他偏移；1项仍是+1专用消费者。余654项进入 `city-tail-candidate-review.json`，再按原地址公式排除5个明显ROM/非city整块访问，并把2个真实整块清零/城市记录复制单列。最后**647项保守可能专用别名**留待复查，其中72项已知city pointer但Y未解，575项pointer/shifted-index仍未解；这不是647个已确认消费者，也不是“全ROM未使用”证明。

地址证明区分实际whole-record clear/copy与专用字段：30DD9A清6000..6FFF，30DDEF复制960B至6000..63BF，确实覆盖+1/+28..31；30DDED从16:8C00读city模板、30DE32从17:8000读officer模板、30DE34写63C0..6EFF，地址范围分别明确。30DBC4的palette pointer lookup对全部rawA byte/原Y0..31均不相交city SRAM；30DEAE的原公式946C+16*((3*A)&255)+Y也始终为ROM窗口。每项证据附producer/body/table原字节，未因数据为0就排除访问。

可移植来源：四份此前用于指令种子的探索目录JSON（phase13 action/city/panels quick、phase14 tactical quick）已逐字节复制到 `provenance/`，合计364,407B。`provenance/manifest.json`记录original_path→portable_path、bytes及SHA256；原路径只是来源位置，不再是归档必需文件。分析器读取可移植副本并保持原seed顺序，继续对照ROM原字节；这些quick种子不被加计为正式CPU或Native病例。归档不取消探索目录排除规则，也不跳过任何artifact哈希。

## 城市字段

| 字节 | 已确认机械作用 | 仍未确认 |
| --- | --- | --- |
| +1 | bank10 BD97读取+1，BD9D读取+2；以LE16(+1,+2)比较300。+2也是已确认金字段的低字节，因此这是实际重叠读取。 | 不能将+1单独命名为资源或旗标。原30条初值均0。 |
| +28..31 | 随完整32字节记录初始化/整段SRAM清零处理；原30条均为00 00 00 00。 | 扩大CFG域后未发现已解出的专用消费者。动态/间接未决域仍存在，不能写“unused”“reserved”。 |

原 `analysis/phase15/fields` 的+27冷却及6F06月事件latch结论继续有效，本轮没有修改它们的时钟或官方名称。`CityUnresolvedFields.from_memory(memory,city)` 是只读视图，提供`byte1`、`overlapping_assignment_word`与`tail28_31`。

## 武将适性字段

编码来自武将byte11的bits2..3：`(byte11 >> 2) & 3`。原237条合法初始记录中0有111条、1有70条、2有56条，3为0条。原UI正式字形0=平、1=山、2=水。原2880B scenario copier还复制了邻接数据槽237/238/239，byte11分别FF/BE/FF，三者bits2..3都是3（地址6EDC..6EFF）。它们来自指针/数据，不是三个额外合法武将；因此没有宣称整个初始化SRAM从未含code3。新`initial-records.json`将合法237和这三槽分列。

| 消费者 | 原地址/表 | 编码3实际行为 |
| --- | --- | --- |
| 资料页上半字形 | bank25 B630，B647..B64C仅3对；file0x033657 | 读B64D/B64E= A0 0B，正是下一函数`LDY #$0B`机器码。 |
| 资料页下半字形 | bank25 B64D，B713..B718仅3对；file0x033723 | 读B719/B71A=4A 4A，正是后续两个`LSR A`机器码。此函数随后落入兵数绘制，源码只恢复到B663前缀。 |
| 玩家移动 | bank12 A7E7；A823/A83F两张7×4表 | 七个物理表行的第四列均0。按063C[slot]>=6选第一表；正常有效兵量域下该缓存是low10兵数//100。表行存在不等于七种地形均是调用方合法值。 |
| AI移动后缀 | bank8 A796；A7CD/A7E9 | 第四列同样0。保留A7AA/A7AF两次读取byte8的原错误：byte8>=3选第一表，byte9不参与；不能替换为玩家的百兵规则。入口需要原caller先PHA的terrain字节。 |
| 普通攻击地形适性 | bank15 CB2F；CBE9=[0,2,3,0]、CBED=[0,2,4,0] | code3与code0同样匹配0。实际外层对原class0/1/5先返回，不应把直接调用后缀的边界输入当完整合法目标资格。 |
| 阵形参数 | bank15 D102；D1B0只有3×8项 | code3读取紧邻D1C8的参数记录[02,80,80,00,80,00,00,00]作为selector；selector80还可能让后续参数读取再次越出16字节参数块。源码按真实ROM字节保留，不赋予第四技能。背景5另走原特殊分支。 |
| 战场单位缓存 | bank13 DD2F + DB03 | 将code3直接写0628低2，后十槽附加side80；空ID=FF写FF。随后真实刷新063C为low10兵数//100，空槽FF。 |

`officer-flag-writers.json` 逐一列出17条可靠byte11更新域的原始字节：状态0/2/3更新使用AND FC和/或OR02/03，等级更新保留低半字节并OR16的倍数。它们都保持bits2..3，因而在这些域内不会把输入0/1/2变成3。该结论不覆盖所有未解间接store、异常指针/索引别名或任意整段复制；没有用“没有ORA #$0C字节”替代完整生产者证明。

## 原Nestopia资料页实验

正式证据来自 `analysis/phase16/runtime/affinity-pages`，一次导入原phase12天然战场母存档，以普通手柄完成四次打开/关闭资料页。只准备武将131的byte11 bits2..3，packed值为12/16/1A/1E，原tier与status保持。每页实际观察040D按0..9绘制后变FF，再保存原RGB/RAM/SRAM/whole-state。

`native-affinity-proof.json` 绑定完成帧272/756/1240/1724及原16×16区域(64,192)-(80,208)的RGB哈希。编码3画面确为越界字形，不能视为正式第四能力。Native没有内部CPU指令trace；它证明真实页面图像，原CPU矩阵另外证明服务指令效果。

![code0 平](../../phase16/runtime/affinity-pages/trait-code0-info-open.png)
![code3 越界字形](../../phase16/runtime/affinity-pages/trait-code3-info-open.png)

## 独立源码与原CPU验证

`AffinityFieldServices(memory,rom,services=None)` 提供 `run_entry(entry,registers=actual_registers)`、`__call__(ServiceCall)`、`resume()`；必须保留已有caller栈与显式physical pair，禁止默认stack seed。生产只运行具名Python条件/循环和独立固定服务，不读取控制IR、不解释opcode、不运行原CPU。缺F2D7等真实服务返回dependency，waiting/error/blocked/None即使篡改PC/SP也不被当成返回。

| 域 | 原CPU病例 | 结尾 |
| --- | ---: | --- |
| B630上半字形 | 256 | actual caller RTS |
| B64D下半字形 | 256 | explicit prefix B663，栈未pop |
| A7E7玩家移动 | 560 | actual caller RTS |
| A796 AI移动后缀 | 504 | 消费caller-PHA terrain后actual caller RTS |
| CB2F攻击地形后缀 | 64 | actual caller RTS；外层地形资格单独说明 |
| D102阵形参数 | 768 | actual caller RTS |
| DD2F+DB03缓存 | 128 | actual caller RTS，20槽混合原ID/空槽 |
| 缺F2D7 | 1 | strict原JSR前缀 |

合计2,537原CPU病例=2,280真实caller RTS+257明确前缀，10个源码guard，失败0。每例比较全2,048字节RAM（含闲置caller栈）、全8,192字节SRAM、AXYP/SP/PC、银行和有序端口读写；原动态指令位置300个。验证器调用原py65仅作oracle，生产和验证中的源码固定helper原CPUcallback均0。码3及255等输入明确为边界fixture，不宣称自然游戏会产生这些字段值；也不把下半字形前缀算成完成完整资料页。

复跑：

```sh
.venv-trace/bin/python scripts/verify_field_semantics.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_field_semantics.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

查看 `validation.json` 的逐例范围和计数，`static-catalog.json`/`raw.asm` 的原字节与不可变表，以及 `schema.json` 的置信度叠加；原ROM SHA256为26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82。
