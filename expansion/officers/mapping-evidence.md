# 千人武将库：字段映射与年代依据

本次交付是可审核的候选资料与导入规则设计。没有修改原 ROM、可读恢复源码、存档或实际游戏规则。原游戏237名有效武将与新库计划容量1200不是同一项限制；1200是独立引擎的设计容量。

完整29项映射见 [JSON](field-mapping.json) 与 [CSV](field-mapping.csv)，年代边界见 [chronology-policy.json](chronology-policy.json)。字段状态明确区分直接资料、仅作元数据、待人工配置、暂定换算和原始未解析位。数值换算尚未执行。

| 内容 | 可直接保留的资料 | 对原游戏的处理 |
|---|---|---|
| 姓名、源序号、别名 | 官方独立条目及原文 | 稳定人物ID；同名异人分开 |
| 生年、登场年、卒年 | 来源表逐行游戏设定 | 与史实年分开；按剧本筛选 |
| 武力、智力 | 取得可复查能力源后保留原值 | 拟定兼容换算需与原237人校准，本轮未填造数值 |
| 统率、政治、魅力 | SAN14扩展资料 | 暂不影响原公式，原12字节无同名对应位置 |
| 体、徳、平/山/水适性 | 原版重合人物保留原记录 | 新人物逐项配置；不把魅力直接当徳 |
| 忠、兵、在野地、所属城 | 属于具体剧本和游戏过程 | 不能当作人物永久固定属性 |
| 经验、等级、装备、计略 | 原版已有机制 | 另做初值与身份迁移；不是SAN14战法直译 |

## 原字段的证据和边界

- [武将12字节模型](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/officers.py:30)确认体、武、知、忠、徳；经验是LE16，兵数显示低10位，武器/防具共用一个字节，状态/适性/等级共用另一字节。[同文件有效记录提取](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/officers.py:95)限定237名。
- 原初始237条解码的范围为：体30..99、武18..99、知8..99、忠30..100、徳10..99。这是已有数据的观测范围，不是字节格式能表示的最大范围。[解码CSV](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/analysis/officer_fields/officers-decoded.csv)
- 徳参与[招入后的忠诚与换君主调整](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/officer_transfer.py:58)，也参与[城首选择](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/domestic_ai.py:101)。因此不能直接把它改称SAN14魅力。
- [兵数字段规则](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/troop_fields.py:1)表明不同路径会保留、清除或数值使用高6位。没有证据把它命名为训练、士气、伤兵或其他新字段。
- [适性3的实际行为](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/analysis/phase16/README.md:13)：有效武将只有0平、1山、2水；3会越过资料和阵形表的正常范围，不能设成第四适性。
- [状态解释](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/game_enums.py:52)保留强推断范围；原状态3是移除标志，不能等同永久死亡。未发现与可见在野也不能混成一个候选状态。

## 扩容时必须迁移的身份规则

[原寻址函数](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/game_algorithms.py:28)先将ID限制为8位。[特殊AI白名单](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/ai.py:199)、[诸葛亮ID109专属门槛](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/ai.py:291)、[招募偏好](/Users/paulasmith/Documents/Codex/Three-Kingdoms2-King-mainland/source/recovered/domestic_ai.py:96)、家族表和城市名册都引用原武将ID。仅扩大数组会造成截断和错误人物获得能力。

下一阶段应先以稳定人物身份迁移这些规则，再分配16位运行ID。建议运行ID0..1199，空槽FFFF；原ID单列保存。城市驻将、战场槽、继承人候选、家族和白名单须一起迁移。本轮没有声称已完成这项引擎改造。

## SAN14来源和年代策略

[官方1000人名单](https://www.gamecity.com.tw/sangokushi14/officers-list.html)是人物条目的基准，不是完整五维和年代的官方导出。[官方出征说明](https://www.gamecity.com.tw/manual/sangokushi14/5100.html)说明统率、武力、智力、阵形/战法及关系的作用；[官方内政说明](https://www.gamecity.ne.jp/manual/sangokushi14-pk/ce/cht/4200.html)区分统率、武力、智力、政治、魅力的用途。这些说明支持字段不同，不能据此生成每人的能力值。

公开年代表使用作者整理的[全历史武将各剧本登场位置表](https://xgodgame.blogspot.com/2020/02/14_9.html)。下载原文存于 [source/san14-xgodgame-chronology.html](source/san14-xgodgame-chronology.html)；SHA256为`d0672c0c14dbbfb955c9d7d346b535116b276751603a3965244127c74acf54b7`。两张表各1000人物行，生/登/卒年重复，后续按人物条目核对后合并剧本列。它是玩家整理的游戏设定，不是官方数据导出，更不是千人史实生卒年的认证。

采用以下边界：生年与登场年小于或等于剧本年，卒年大于或等于剧本年。卒年当年仅列为年粒度边界未决，不能据此声称全年仍在世；若来源剧本给出了明确状态，则保留该状态与来源。缺失年份使用null或CSV空白；不写0，也不以“生年+15”伪造登场年。未知资格另计，不自动并入可用人数。

来源的251英雄列采用假想设定，不纳入历史年代可用人数统计。原表给出的君主名表示已仕官势力，不表示所在地；地图96城与SAN14城市粒度不同，需要另做城市映射。角色在全库中保留，不代表可在184年等同一剧本全部同时出现。

## 本轮校验

29项映射的key唯一，CSV与JSON同项同序；年代策略文件可解析。原237条字段范围取自现有解码文件；原ROM未写入。五维能力、史实年份、体/徳/适性和装备等尚未导入或生成，文件中明确保留待配置项。
