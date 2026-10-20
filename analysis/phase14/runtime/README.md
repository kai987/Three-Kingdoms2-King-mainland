# 第十四轮原核心：冷启动、复位与内政合作回放

三案都直接把只读原ROM载入新的锁定Nestopia核心，没有状态导入、battery文件导入或任何新增core RAM/SRAM、ready、结果、端口写入。普通按键和原libretro `retro_reset()`是唯一控制操作；恢复源码未安装进原核心。

首跑20658帧，两跑41316帧、208检查点；864份非空产物逐字节hash一致，含21份正式JSON。另排除208份0B VRAM和208份含目录路径的snapshot metadata JSON。所有256×240原RGB、RAM2048B/SRAM8192B与实际48000Hz双声道16bit PCM每帧完整hash公开，完整原WAV保留。这里原生帧不是内部CPU指令trace。

## 三案合同与终点

1. 冷启动到城市的前24步复用旧只读普通按键计划（2922帧）。原曹操初城11预备兵9999已满，所以首次原招募数量守卫保留0；游戏原同意界面仍消耗1张行动牌，然后普通分配将100现有预备兵交陈宫。后二次Up选择raw1，即100兵，各扣20金，再各给于禁100。行动预算6F05确实3→2→1→0，原队列、动画和名单提交均经原A/方向键完成。六个电脑君主依次出现6F8B请求0→完成FF，日期189年1月→2月；原A确认新玩家回合，最终global2/NMI2/city0/sub1，预算恢复3。未声称FC/FB出现在此自然样本。

2. 真冷启动城市frame2922之后直接调用原`retro_reset()`。调用本身不先写RAM或SRAM；立即读取的8192B SRAM与复位前完全相同，后续1200个真实帧后仍全部相同，189年1月与场景数据保留，RAM与画面已由原代码重新初始化到标题global10/NMI6。立即边界没有新RGB/PCM帧，故只有真实内存导出，不伪造即时reset截图。此证明同一加载实例的battery-backed SRAM复位保留；本前端没有实现进程退出/断电后的battery文件保存与重载。

3. 真冷启动无按键4000帧。原介绍计数0471:0470达到0B58（frame3063），标题main4/sub0清调色板，随后sub1的原JMP E000。frame3073观察global0，之后原标题初始化与呈现完成。该路径是介绍超时自动软件重启，不是猜测的菜单项。原JMP字节与实际字段跳转共同支撑解释；未直接采集原核心PC。

## 字段与证据范围

active_controller仅按真正global/NMI组合选择title/ruler/city/battle/attack/duel主态；其它状态数组保留为原字节，不能将inactive残余字节计成已执行场景。每帧保存日历/君主/行动预算、6F5B..62内政字段、6F8B..AB请求块、全ruler记录、palette、PPU/NMI/IRQ、text队列、bank缓存、audio RAM、3个相关武将原12B记录与城市11原32B记录。完整原RAM/SRAM只在检查点导出，每帧完整内容均hash。

原图/原WAV来自Nestopia，不是恢复源码生成。静态QA只核对PNG尺寸/模式/同帧RGBhash、RAM/SRAMhash、WAV格式/实际PCMhash与重复产物；未伪称浏览器验收或人工听音通过。硬件时序、原内部调用链和源码等价性由其它独立CPU回执承担。

## 真实冷启动→城市→行动耗尽→内政合作AI→二月玩家返回

12536帧，118检查点。three accepted player command cards exhausted; six original domestic AI request0→returnFF updates completed, January advanced toFebruary, real A returned to player world/city0/1。

- [实际按钮/复位计划](cold-city-domestic-cycle/input-plan.json)
- [逐帧原字段与四类完整hash](cold-city-domestic-cycle/frame-services.json)
- [真实检查点图像](cold-city-domestic-cycle/checkpoints.json)
- [实际完整WAV](cold-city-domestic-cycle/full-flow.wav)
- [观察到的预算/日历/请求/重启事件](cold-city-domestic-cycle/flow-events.json)
- [病例回执](cold-city-domestic-cycle/validation.json)
- [第二跑exact parity](cold-city-domestic-cycle/repeat-validation.json)

## 真实冷启动到城市后原核心复位：8KiB SRAM保留与标题重建

4122帧，68检查点。original libretro reset returned to title while all8192 SRAM bytes and saved189year/January fields remained identical。

- [实际按钮/复位计划](core-reset-battery-retention/input-plan.json)
- [逐帧原字段与四类完整hash](core-reset-battery-retention/frame-services.json)
- [真实检查点图像](core-reset-battery-retention/checkpoints.json)
- [实际完整WAV](core-reset-battery-retention/full-flow.wav)
- [观察到的预算/日历/请求/重启事件](core-reset-battery-retention/flow-events.json)
- [病例回执](core-reset-battery-retention/validation.json)
- [第二跑exact parity](core-reset-battery-retention/repeat-validation.json)

## 无按键冷标题介绍：0B58计时后原软件E000重启

4000帧，22检查点。unpressed cold title intro timed out, original title4/phase0→phase1→global0→title initialization completed。

- [实际按钮/复位计划](title-intro-software-restart/input-plan.json)
- [逐帧原字段与四类完整hash](title-intro-software-restart/frame-services.json)
- [真实检查点图像](title-intro-software-restart/checkpoints.json)
- [实际完整WAV](title-intro-software-restart/full-flow.wav)
- [观察到的预算/日历/请求/重启事件](title-intro-software-restart/flow-events.json)
- [病例回执](title-intro-software-restart/validation.json)
- [第二跑exact parity](title-intro-software-restart/repeat-validation.json)

```sh
python3 scripts/capture_boot_cooperation_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat
```

[原核心manifest](evidence.json) · [汇总回执](validation.json) · [静态产物QA](static-validation.json)

每一跑均在独立新的Python进程中创建/关闭原核心，避免复用同一动态库全局状态。所有原serialize输出buffer逐字节原样保留；没有裁去/规范化state尾部。先前同进程探索产生的序列化buffer尾4B差异已保存在探索目录，不纳入正式计数。需要重跑请指定新的输出目录；冻结产物不得覆盖。

同进程序列化差异的内部字节含义尚未识别；它与宿主heap或opaque序列化状态的关联仅是定位推断，不据此断言为无效payload。正式每跑独立进程，所有原输出buffer完整保留并实际exact parity通过。
