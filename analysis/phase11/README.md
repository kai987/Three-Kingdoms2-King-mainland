# 第十一轮：战场、普通攻击、单挑的具名控制源码

本轮把三类控制 IR 的本地主态、子阶段、局部调用、循环和真实外层入口继续还原为普通 Python 源码，并补全全局状态3/5/7的实际场景初始化。生产新模块不读取 program.json、不解释6502 opcode、不用 PC→操作表，也不安装原CPU fallback。原IR仍保存为历史分析证据，离线结构化脚本可以使用它。

- [交互式报告：实际PNG/WAV、字段变化、当前源码和回执](index.html)
- [最终字节、依赖、CPU、原核心和浏览器总复核](verification.json)
- [统一源码集成对照](source-integration.json)
- [原模拟器三条回放及其起点来源](runtime/README.md)

## 新的源码组成

| 模块 | 已还原内容 | 证据 |
|---|---|---|
| [battle_scene_controller.py](../../source/recovered/battle_scene_controller.py) | 16个战斗主态、完整局部分派、A000真实包装、战斗初始化及单挑结果消费入口 | [battle](battle/README.md) |
| [attack_scene_controller.py](../../source/recovered/attack_scene_controller.py) | 11个普通攻击主态、编队/行动对象/菜单/结果/单挑交接，以及真实A000包装 | [attack](attack/README.md) |
| [duel_scene_controller.py](../../source/recovered/duel_scene_controller.py) | 22个单挑主态（含初始化别名）、116个合法主态/phase组合、HP写回、退却/追击和结果返回 | [duel](duel/README.md) |
| [scene_shared_services.py](../../source/recovered/scene_shared_services.py) | 真实消息请求、菜单、RNG、数学、淡入淡出请求、显示开关、清屏、指针和EE07跨银行调用 | [shared](shared/README.md) |
| [scene_initialization.py](../../source/recovered/scene_initialization.py) | E18B/E22F/E2E8三条初始化、CHR/IRQ/调色板配置、1024字节/RLE/元图块背景装载 | [initialization](initialization/README.md) |
| [battle_setup_ai.py](../../source/recovered/battle_setup_ai.py) | 双方AI初始化、策略配置、真实三数组排序、各城市编队路线、HUD、相机和部队显示 | [setup-ai](setup-ai/README.md) |
| [battle_background_initialization.py](../../source/recovered/battle_background_initialization.py) | 初始背景31组行、真实EEE6消费/等待，以及保留tile偏移和纵向裁剪的F09C精灵服务 | [background](background/README.md) |
| [scene_coordinator.py](../../source/recovered/scene_coordinator.py) | 将上述入口与第十轮服务接入同一ServiceMemory，按真实PRG银行和callee入口分配独立服务owner | [集成回执](source-integration.json) |

控制器保留可观察的AXYP、scratch、栈和mapper副作用。具名函数不会把模拟器一个video frame等同为一次业务tick；计时、按键、PPUSTATUS、队列消费都需要其实际来源。

## 统一调用

`GameEngine`新增 `readable_scene_rules()`、`tick_readable_scene(registers, scene=...)`、`resume_readable_scene()`、`initialize_readable_scene(entry, registers)` 和 `tick_readable_nmi(registers, hardware_entry=...)`。旧API保留历史合同，新API通过具名模块执行。

```python
engine = GameEngine(service_memory, rom=original_rom, mapped=True)
coordinator = engine.readable_scene_rules()
result = engine.initialize_readable_scene(0xE18B, actual_registers)
if result['status'] == 'dependency':
    # 为明确暂停的硬件/服务提供真实输入或完成其工作，再续原owner。
    result = coordinator.resume_setup()
```

内存必须是显式 `ServiceMemory`。场景调用使用已有真实caller栈和寄存器，生产不种植0200返回地址。每个pending `ServiceCall`保留自己的owner，嵌套初始化不能借用父调用的generator。只有明确`returned`且PC/SP符合原caller才能继续；unknown、waiting、error、blocked、None不会伪装返回。文本接口的合法early RTS与队列完全完成仍分别记录。

## 验证边界

各子目录validation记录完整返回和严格前缀，RAM地址范围、8KiB SRAM、寄存器、mapper及有序端口分别检查。控制器矩阵中的验证专用原CPUhelper调用单列计数，不能推断这些helper已经成为生产源码。共享、初始化、AI、背景和统一集成的纯源码案例不使用原CPUcallback。单挑源码自由栈残余与部分呈现服务的临时寄存器有各自声明范围。

统一集成目前26个原CPU对照：25个完整返回、1个普通攻击肖像callee处的严格前缀；另7个源码guard。初始化111个原CPU对照均完整返回，其中含三种战斗初始主态、七种普通攻击背景、九组单挑控制标志。普通攻击外层的physical25 A000肖像及其他尚未恢复的远端UI/资料服务保持明确dependency，不称整台独立NES已完成。

原Nestopia双跑22,870帧，91个检查点、387个非空产物及18份正式JSON重复一致。原RGB/48kHz双声道PCM、逐帧字段、实际输入和旧起点注入来源都可复核。本轮没有新增ROM或core内存写入。冷启动回放进入战场并回到操作界面；普通攻击回放通过真实後退命令返回；单挑从继承的明示fixture执行真实初始化、动作、HP/结果写回及战场交接，终点battle11/3仍在真实升级通知。它们不代表一场完整战争胜利，原核心字段也不是内部CPU/NMI trace或恢复源码的独立像素/PCM合成证明。

源码重建结果依旧是与原ROM逐字节一致的镜像；原ROM只读。复核命令与精确hash在总回执和子目录中保存，第五至第十轮集成也已按当前GameEngine重跑。
