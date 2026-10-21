# 仓库范围与本地资料

本仓库交付恢复的Python游戏逻辑、C11计算库、分析与验证脚本、精选结构化分析资料、96城地图v42，以及1000位独立候选武将的年代和字段映射。

## 本地浏览

在仓库根目录运行：

```sh
python3 -m http.server 8765
```

打开 `http://127.0.0.1:8765/expansion/officers/index.html` 查看地图、武将检索、年代筛选和表格下载。地图单页位于 `expansion/map/city-map-city-sea-preview-v42.html`。GitHub仓库页只预览源码，不直接执行HTML。

```sh
python3 expansion/officers/build_roster.py
python3 expansion/officers/build_report.py
```

这两项不依赖原ROM。名单来源快照及SHA-256保存在 `expansion/officers/source/`。原NES的237人仍有229人缺少完整身份对照，尚不能据此确认净新增人数。新增人物的体、徳与适性等逐批配置。当前96城战役有148份完整属性配置，1000人的体力与适性已覆盖，852人的德仍待逐人补齐；另有六个可玩年代剧本；武、知已整理千人的第三方来源数值。独立战役启动见`game/README.md`，不需要原ROM。

## 逆向分析的外部输入

原ROM、完整ROM字节表示、模拟器存档、原始逐帧轨迹、音频、核心二进制、Ghidra安装、REA工作副本及历次封存ZIP保留在本地，不随Git提交，也没有作为“无用文件”删除。完整实验需要同一ROM和各报告声明的外部输入；仅克隆源码仓库不能重跑全部历史审计。

ROM身份为 SHA-256 `26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`，524304字节，Mapper 19。需要原ROM的历史脚本可能保留原运行环境路径，移机重跑时须按其参数或顶部配置指定本地输入。历史回执中的绝对路径是当时的证据记录，不能视为克隆后可用的路径。

REA上游基准为 `0043d9b134c0a353e8bf85c0bde4492275f1f720`，仓库为 https://github.com/morluto/rea 。6502适配改动保存在 `analysis/rea/6502-adapter.patch`；其余本地上游工作副本未删除，也未作为本项目嵌套Git仓库提交。

`docs/repository-files.txt` 为本次发布文件清单；`docs/publication-inventory.json` 记录未发布的大型静态分析文件的大小和SHA-256，并汇总其余本地证据的文件数与大小。选取的分析资料包括Markdown报告、CSV、控制IR等源码所需输入以及较小的静态JSON；大型轨迹和审计原件仅在本地。旧报告中的本地音画或原始证据链接可能因此无法在克隆中打开。每份回执声明的完成边界、前缀和未验证范围仍以其正文为准。

本项目尚未恢复成可独立运行的完整游戏，96城地图和千人候选库也尚未导入原NES。城市未决字段仍不得猜测为已确认含义。

## 许可证和来源

仓库沿用远端已有MIT许可证，适用于本项目原创代码。原游戏、参考素材、官方武将名单、第三方年表及OpenCC的权利与许可分别归其来源；MIT不覆盖或改变这些第三方权利。来源链接、快照哈希、OpenCC许可证及不确定性均随资料保留。
