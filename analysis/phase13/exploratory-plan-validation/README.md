# 第十三轮原核心城市UI回放

两案从第十一轮无注入冷启动的city-commands自然母档开始，仅普通按键；不新增core RAM/SRAM、ready、结果或packet写入。原只读ROM及锁定Nestopia直接产生RGB和48000Hz双声道PCM，恢复源码未安装到原核心。每案最终全部8192B SRAM与母档逐字节一致。

首跑3100帧，两跑6200帧，47检查点；204份非空产物hash重复一致（包含12份正式JSON），排除47份0B VRAM和目录路径metadata JSON。完整逐帧RGB/RAM/SRAM/PCM哈希与WAV公开。

## 原入口及命名核对

这些自然界面保持global2/NMI2；城市callback由fixedF8EC selector3B进入physical27A000→A00C/A01F，主/phase为0400/0401。全局2的main10A000内政AI不是这个城市NMIcontroller。NMI2此前的29A009/A00F/A03F是另外的呈现worker。

图标0→main2/1内政，图标1→3/1军队；图标2→4/1原文字「ブッシをはこぶ」「あたえる」，保持物资操作名称，不称战斗计略。图标3→5/1原提示「ここはマチです」街菜单，首地点5/18明确「ブキヤ」武器店武将选择，不叫外交。所有选择在资源/目标最终确认之前取消。

地图/城市0/1按B打开12/2武将资料，实际far25A021 bytes4CE5AF→AFE5；25A01B→B964是另一个候选扫描，25A012→B2D7是已有绘制worker，三者不能混淆。资料里040C是原索引、0410..417是列表，down后0410仍131但0411=5、索引变1，图中于禁；不是410字段直接改变为当前显示ID。

## 城市四菜单、武将/目标选择与取消返回

2220帧、32检查点；最终global2/NMI2/city0/sub1，是UI周期结束，不称月轮或战役完成。

- [实际按钮计划](city-menu-cancel-cycle/input-plan.json)
- [逐帧字段、相机、银行缓存、OAM及hash](city-menu-cancel-cycle/frame-services.json)
- [检查点原图](city-menu-cancel-cycle/checkpoints.json)
- [完整实际WAV](city-menu-cancel-cycle/full-flow.wav)
- [母档来源和最终SRAM对照](city-menu-cancel-cycle/validation.json)
- [独立第二跑核对](city-menu-cancel-cycle/repeat-validation.json)

## 世界/城市界面武将资料：上下浏览与关闭

880帧、15检查点；最终global2/NMI2/city0/sub1，是UI周期结束，不称月轮或战役完成。

- [实际按钮计划](world-officer-browse-cycle/input-plan.json)
- [逐帧字段、相机、银行缓存、OAM及hash](world-officer-browse-cycle/frame-services.json)
- [检查点原图](world-officer-browse-cycle/checkpoints.json)
- [完整实际WAV](world-officer-browse-cycle/full-flow.wav)
- [母档来源和最终SRAM对照](world-officer-browse-cycle/validation.json)
- [独立第二跑核对](world-officer-browse-cycle/repeat-validation.json)

计划检查点先核对真实主/phase和300=FF、304=FF、7E=0，再保存图像；旧040D=FF单独不作为完成判断。自动状态截图只叫observed-state，不给其猜完成标签。原每帧数据不是内部CPU/NMItrace；相机/mapper缓存不会替代真实端口序或硬件时序证明。

```sh
python3 scripts/capture_city_ui_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat
```

[原核心manifest](evidence.json) · [汇总回执](validation.json)
