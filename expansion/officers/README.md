# 武将扩充候选资料

本轮先整理候选资料和导入映射，不修改原ROM、恢复源码或存档。

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

原版237人中，目前保留可核对的姓名转写为8条，均匹配到候选库；另229条尚未建立完整人物对照。因此，本轮确认的是候选库的1000人，尚不能断言合并原版后的总人数或净新增人数。

## 年代与原游戏逻辑

参考年筛选检查生年、登场年及卒年；卒年当年单列为边界待核，不伪造月份。选择来源具体剧本时保留其原始状态；251年英雄集结属于跨年代假想剧本，独立处理，不用生卒年剔除。

原作仍为体、武、知、忠、徳五项。SAN14统率和政治可保存为扩展资料；魅力不能直接改写徳。武／知换算规则尚未执行，新增人物的体、徳、适性、装备等需另行配置。原适性0平／1山／2水保留，编码3不作为新增兵种。

人物身份ID与运行时数组索引分开。1200人容量与16位运行ID仅为新引擎方案，还需迁移原作亲族、AI白名单、特殊武将、招募与继承引用，不能仅扩数组后直接写入原ROM。

## 重建

`python3 expansion/officers/build_roster.py` 从保留的快照离线重建名单，校验来源哈希。

`expansion/officers/build_workbook.mjs` 使用桌面提供的Artifact Tool生成Excel，并检查184／230参考年筛选、公式、原生筛选表与冻结窗格。`python3 expansion/officers/build_report.py` 生成交互核对页面。地图v42及海陆连接数据位于 [../map](../map/README.md)。交互页面使用相对链接，可随仓库移动或通过本地HTTP服务浏览。Excel已包含在仓库；重新生成Excel需要提供 `@oai/artifact-tool`，其余名单构建只需Python标准库。
