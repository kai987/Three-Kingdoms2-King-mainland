# 武将扩充候选资料

候选资料已继续接入独立重制版的人物规则与初始化模型，不修改原ROM、封存恢复源码或存档。

候选库保留 **1000个独立人物条目、994种姓名文本**。韓忠、張承、張南、馬忠、李豐共5组11位同名人物分别保留；不能把姓名字符串当作人物主键。来源两张年代表重复列出的同一1000人只计一次。

每人包含官方繁体姓名、简体显示名、日文名和读音、第三方SAN14设定的生年／登场年／卒年及10个剧本状态。历史生卒字段尚未逐人认证，保留空值。4处跨来源姓名差异留有核对标记，未当作已证实别名。

## 阅读与下载

- [交互名单、地图与去重说明](index.html)
- [可筛选Excel表格](../../outputs/01a1316a-d5cf-7641-8d98-1e47c65dfb1c/千人武将候选名单与字段映射.xlsx)
- [1000人CSV](data/roster-candidates.csv) / [完整JSON](data/roster-candidates.json)
- [年代表](data/chronology-candidates.csv)
- [10剧本状态，共10000条](data/scenario-states.csv)
- [29项字段映射](field-mapping.csv) / [映射证据](mapping-evidence.md)
- [去重审计](data/dedup-audit.json) / [原版身份对照](data/original-overlap-audit.json)
- [来源快照与哈希](source/san14-source-manifest.json)
- [已确认的重制规则](remake-rules.json) / [独立人物模型](../../source/remake/README.md)
- [1000份初始化配置与缺项](data/remake-profiles.json) / [CSV](data/remake-profiles.csv)
- [年度资格人数](data/remake-year-populations.json)
- [德的评分规则](virtue-rubric.json) / [首批5人史料说明](virtue-designs.json)

原版237人中，目前保留可核对的姓名转写为8条，均匹配到候选库；另229条尚未建立完整人物对照。因此，本轮确认的是候选库的1000人，尚不能断言合并原版后的总人数或净新增人数。

## 年代与原游戏逻辑

参考年筛选检查生年、登场年及卒年；卒年当年单列为边界待核，不伪造月份。选择来源具体剧本时保留其原始状态；251年英雄集结属于跨年代假想剧本，独立处理，不用生卒年剔除。

重制版每城20人，战场保持每方10人（含主将），全场最多20人。武力对应武，智力对应知；兼容范围1..99，来源100保留原值并映射99。德按恤民、公正、操守、信义独立设定，附史料和争议说明，不直接转换魅力。

新登场人物0兵、基础短剣和絹巾、经验0；体力按明确人物基准满值初始化。普通仕官的忠诚由剧本配置，招募和俘虏有各自的原规则。缺体力、适性、能力或德时继续留空，不能初始化为假完整人物。原适性0平／1山／2水保留，编码3不作为新增兵种。

阶段1原版基线仍保留8人完整属性对照。当前扩展版已另行整理[1000人的SAN14第三方能力表](data/san14-abilities.json)，11个同名条目按身份分开核对，不依赖表格顺序自动配人。原始数值和来源地址均保留，但尚非官方导出或逐条独立复核。

[96城扩展战役](../../game/README.md)已生成52份完整人物属性配置；其中51人采用逐人史料参考的德设计，阿会喃保留有来源的原版德基线。217年11月开局41人仕官、5人在野；另外948人仍缺德、体力或适性等必要配置，保留在总库供年代筛选，不自动填满城市。首批5人的德设计与后续46人设计分别保存在`virtue-designs.json`和`game/config/officer-designs.json`。本目录的`remake-profiles.json`、阶段1摘要和Excel仍是原基线资料；当前战役完整配置见[mainland.json](../../game/data/mainland.json)。

人物身份ID与运行时数组索引分开。1200人容量与16位运行ID仅为新引擎方案，还需迁移原作亲族、AI白名单、特殊武将、招募与继承引用，不能仅扩数组后直接写入原ROM。

## 重建

`python3 game/build_mainland.py`从已保存数值表、人物基线及逐人设计离线生成当前战役。重新采集能力表可运行`python3 expansion/officers/import_abilities.py --fetch`；网页缓存保存在忽略的`build/`，提交的是带来源哈希的数值记录。

`python3 expansion/officers/build_roster.py` 从保留的快照离线重建名单，校验来源哈希。

`python3 expansion/officers/build_remake.py` 生成独立初始化配置、缺项与年度人数。`python3 -m unittest discover -s tests -p 'test_remake_officers.py' -v` 检查20人容量、出战上限、原子转属、年代、初始化和原忠诚规则。

`expansion/officers/build_workbook.mjs` 使用桌面提供的Artifact Tool生成Excel，并检查184／230参考年筛选、公式、原生筛选表与冻结窗格。`python3 expansion/officers/build_report.py` 生成交互核对页面。地图v42及海陆连接数据位于 [../map](../map/README.md)。交互页面使用相对链接，可随仓库移动或通过本地HTTP服务浏览。Excel已包含在仓库；重新生成Excel需要提供 `@oai/artifact-tool`，其余名单构建只需Python标准库。
