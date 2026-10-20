# 原地形 class1：可确认的图形与规则

正式名称仍未证实。当前能确定的是原 ROM 的编码、背景像素、移动费用、计略地形条件以及普通攻击场景资源。连续橙色区域、绿色边缘或褐色斑点本身不足以把它命名为「道路」「砂漠」或其他正式词。本轮不修改原 ROM，也不把猜测名称写进已有枚举。

## 原数据与可复核图形

`class1-legal-cells.csv` 包含全部 **335 个合法格**，来自城市 ID 5/6/7/9/29，数量分别 56/117/17/105/40。合法地图域是 x=0..30、y=0..19，排除属性行 y=15。class1 没有被 DB46/B6E5 的 raw>=6→2 规则归一化。

| 原 metatile | 合法格数 | F477 的四个 BG code（左上/右上/左下/右下） |
|---|---:|---|
| 01 | 197 | 01 01 01 01 |
| 6A | 34 | 6C 01 01 01 |
| 6B | 15 | 01 01 7C 01 |
| 6C | 27 | 01 6D 01 01 |
| 6D | 37 | 01 01 01 7D |
| 70 | 8 | 01 6D 01 7D |
| 74 | 17 | 01 01 7C 7D |

`visual-evidence.json` 连同 `core-views/*-evidence.json` 记录三张新原核心全帧、RAM 改动、原 nametable 四元组、CHR 文件偏移/字节、调色板、64 个 OAM 项、精灵包围盒检查和像素映射。122 个完整可见 class1 格均满足原 BG quad=NMT quad，CHR 2bpp 像素=实际截图，没有 OAM 覆盖。图块 01 是 pixel-index1 纯色；其余变体只在边缘使用 index2。颜色来自固定 Nestopia/Royaltea 的原始渲染，不是人工上色的诊断图。

- [七种原图块的截图裁切](core-views/class1-seven-raw-tiles-56490c4d22fc.png)
- [城市5完整截图（3倍）](core-views/city5-map-e4613f07e4f9-fullframe-x3.png)
- [城市6完整截图（3倍）](core-views/city6-map-f949847ec5cb-fullframe-x3.png)
- [城市9完整截图（3倍）](core-views/city9-map-0c8a1fd93bb7-fullframe-x3.png)

这些是**明确注入 RAM 的原核心 fixture**，不是自然战役行进截图。输入父状态是 `analysis/runtime/phase3/attack-intro-7.state`；设置 050E 为目标城市、007A=3、保存视口 0510..0513=0。原 global3 重新设定城市 chunk 并恢复 camera0,0；运行300帧，0300/0304绘制队列均为FF。图块坐标使用原 world-pixel 减 camera；地图没有底部 UI 的纵向-2偏移。原 top BG page 写入协议是 bank31 F21E/file3F22E 对 B2..B5→A000/A800/B000/B800；不能把 end-of-frame 的底部字体 bank 当地图 bank。

全帧与每个 zoom 保持同一帧，文件名含内容 hash；`verify_terrain_semantics.py` 另外从全帧、原 ROM、state 的 NMT/OAM 和 RAM 重新验证裁切及像素，不只接受截图标题。曾用于诊断的 camera64旧 capture 已移至 `diagnostics/initial-camera64-assumption-rejected`，其初始坐标假设无效，不属于 `visual-evidence.json` 的有效证据列表。

普通攻击场景另有一个背景 fixture，见 `attack-background-evidence.json` 和 [完整原渲染背景](attack-view/class1-attack-background-deff5d0aa386-fullframe-x3.png)。它仅注入0544=1、007A=5，让 fixed31 E22F 正常加载该 terrain 的背景资源。原核心使用 BG pages `[149,121,120,25]`；640 个8×8背景 tile全部与原CHR/NMT/native像素吻合，显示连续土色场地与褐色斑点。本项只验证背景层；保留父fixture的单位/菜单参数，不宣称完成了真实进攻或单位布局验证。

## 移动表选择的真实差异

两套原移动费用表数值相同，但 AI 与玩家选择表的程序不同。独立源码在 `source/recovered/terrain_semantics.py`，原汇编在 `movement-selector.asm`。

| 原路径 | 选择 first table 的条件 | class1费用（已知适性0/1/2） |
|---|---|---|
| 玩家：bank12 A7E7 / file187F7 | RAM063C[slot]>=6；DB03 缓存 `(兵数word&1023)//100` | first=4；second=3 |
| AI：bank8 A78C / file1079C | **武将原记录 byte8>=3** | first=4；second=3 |

玩家表 A823 是 file0x018833；所有地址详见 evidence.json 的独立 bank/CPU/file 三元组。

AI 的 A7A8设Y=8；A7AA读取byte8、减59；A7AF没有INY，仍读取byte8、带前次carry减02，再以BCC选表。这等价于byte8>=3，byte9不参与，不能改写成“AI兵数>=600”。例如：原byte8=2、byte9=3，低10位兵数770，AI费3而玩家费4；byte8=3、byte9=0，兵数3，AI费4而玩家费3。原行为保留在恢复模型中，没有向用户 ROM 写补丁。

适性编码3费用为0，原UI越界/领域证据仍将它标作未定义编码，不给它发明技能名。报价函数返回A对应的剩余行动力、carry、NZV，以及各入口实际X/Y结果；不代替整个CPU入口的指针scratch、RAM或bank协议。

API：`TerrainSemanticsData.from_rom(rom)`，`ai_movement_quote(terrain_class,officer_flags,troops_low_byte,action_points,data=data)`，`player_movement_quote(terrain_class,officer_flags,hundred_troops_cache,action_points,data=data)`，`class1_profile(data=data)`。不修改旧 `game_enums.py`、`terrain_rules.py` 或 GameEngine。

## 地形条件能证明到哪里

原计略名与ID沿用已确认的同ID菜单/执行指针。class1不满足火計0的目标0/2、陥穽/虚兵/要撃1/2/3的目标0/4、水系4/10/12的目标3、需要城5的目标或森林0的发动格。籠絡8的 `terrain!=5` 部分、連弩13在发动者为城格时的目标部分、劫火14的 `terrain!=5` 部分、玩家奇門遁甲15的 `terrain!=3 && terrain!=5` 部分允许class1。兵数、智力、阵营、邻接和行动力等其他条件仍需满足。

效果代码另有独立验证：bank12 B3FE和B494对class1直接跳过水系效果；B538仅排除城5，所以class1通过劫火伤害入口。本轮验证停止在B55C真正伤害helper前，不把该前缀说成完整伤害算法恢复。B8FA区域目标发现同样只跳过城5。

普通攻击准备 A354→DB46→A364把目标规范地形写0544；attack renderer B891/CAF9据此索引BB48、BB1E、BB2C。class1对应PRG bank1的资源指针8570，图形/碰撞资源的索引关系是可证的；其中没有已关联的可读地形名。

名称查找范围见 `evidence.json/name_search_scope`：原分类表、metatile/CHR、移动与计略消费者、效果条件、普通攻击资源指针，以及已有解码菜单/消息。没有找到class1直接名称指针；这不是对全ROM文字不存在的穷尽证明。找到[原1992 Namco说明书的公开目录页](https://endlessfight.org/discuz/forum.php?mod=viewthread&tid=1261)，但扫描内容受会员/积分访问限制，未读取，不以目录、第三方攻略或相似游戏说明书填上名称。

## 验证与复跑

最终 **37,559 项通过、0失败**：**36,667 项原ROM Oracle** 与 **892 项图像/证据完整性检查**分别计数，见 `validation.json`。原6502算术与条件Oracle使用py651.2.0；图片复核使用系统Python3/Pillow，不修改 `.venv-trace` 环境。新模型是独立Python，原ROM仅用于Oracle/原渲染和提取表。

```sh
python3 scripts/analyze_terrain_semantics.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --render-core
.venv-trace/bin/python scripts/verify_terrain_semantics.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

覆盖：AI class1的全byte8域、byte9边界、四适性和行动力边界；所有256 packed flags和byte9值；其他5种规范地形选择边界；玩家class1全cache域；全部335格的玩家/AI地图查找；4个完整纯地形predicate；335格水效跳过/劫火前缀；4张完整core截图及其zoom、122格地图BG/CHR/OAM/crop和640个普通攻击BG tile独立像素复核。名字证实范围、原核心fixture可达性和报价CPU scratch恢复不混同为100%完整地形系统。
