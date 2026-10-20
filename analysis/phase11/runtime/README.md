# Phase11 原Nestopia三类控制回放

完整原ROM/冻结Nestopia运行，原RGB与48000Hz双声道16bit PCM直接来自libretro callbacks。脚本不修改ROM、不新增core RAM/SRAM、ready或result写入。每帧完整RAM/SRAM/RGB/PCM哈希、活跃三controller字段、palette、NMI/PPU/IRQ、音频RAM与全部PCM保留。原字段观察不是内部CPU/NMItrace，也不能证明恢复源码自身合成PCM。

双次独立回放：首跑11435帧，两跑22870帧；91checkpoint；387非空artifact逐项hash相同，另明确排除91个0B VRAM导出与目录metadata JSON。正式6类JSON逐字节一致，PNG/RAM/SRAM/state/WAV均非空。

## 冷启动进入战场及控制交互周期

7920帧，52checkpoint。本轮未追加A结果确认循环；原冷启动计划内的A输入仍逐段保留。最终global=4、NMI=3，active=battle/0/2。

从原冷启动，用已有78步7738帧普通输入计划，保留原capture标记，追加B2+release180。说明是进入战场与控制交互周期，没有声称一场战争胜利。

- [逐帧证据](cold-battle/frame-services.json)
- [实际输入计划](cold-battle/input-plan.json)
- [检查点图片与字段](cold-battle/checkpoints.json)
- [完整原PCM WAV](cold-battle/full-flow.wav)
- [首跑验证](cold-battle/validation.json)
- [第二跑逐artifact复验](cold-battle/repeat-validation.json)

## 普通攻击：原输入後退并返回战场

2401帧，24checkpoint，结果确认循环13次A脉冲（此前进入场景的A输入另见完整计划）。最终global=4、NMI=3，active=battle/0/2。

起点继承phase3唯一敌坐标准备：0600从20→3、0614从14→16。起点原global4/battle3/sub2，由原程序自行产生普通攻击参数；本轮仅原按钮将四列命令设後退、确认结果并返回，无新增参数或ready写入。

- [逐帧证据](ordinary-attack-return/frame-services.json)
- [实际输入计划](ordinary-attack-return/input-plan.json)
- [检查点图片与字段](ordinary-attack-return/checkpoints.json)
- [完整原PCM WAV](ordinary-attack-return/full-flow.wav)
- [首跑验证](ordinary-attack-return/validation.json)
- [第二跑逐artifact复验](ordinary-attack-return/repeat-validation.json)

## 单挑：含初始化、动作与结果返回

1114帧，15checkpoint，A确认脉冲32。最终global=4、NMI=3，active=battle/11/3。

起点继承旧明示单挑fixture-entry：global7、两ID/HP80与5、C991参数及旧RNG起点，原E2E8初始化尚未运行。本轮加载该只读state后只用A2/release30和最终release90，实际原初始化/动画/体力写回/结果/返回均由core执行；不能称自然战役进入单挑。精确旧准备在preparation_reference和该case validation中保留。

最后画面已返回战场，仍停在原升级通知（battle11/3），不能据此声称全部战场通知或整场战争结算完成。

- [逐帧证据](duel-return/frame-services.json)
- [实际输入计划](duel-return/input-plan.json)
- [检查点图片与字段](duel-return/checkpoints.json)
- [完整原PCM WAV](duel-return/full-flow.wav)
- [首跑验证](duel-return/validation.json)
- [第二跑逐artifact复验](duel-return/repeat-validation.json)

主态首次观察仅在匹配global/NMI活跃scene时计入；inactive原数组仍可在原RAM查看，但不会当成覆盖证据。每种scene/main首次观测和global/NMI变化已保存；PNG取实际core帧，无图形模拟。两次snapshot目录metadata JSON不计重复证据；0B VRAM单列排除。

`officer_records`保存原单挑/攻击ID字节所引用的记录；场景未活跃时，它们只是残留ID引用，不能当成当前战场选中武将。回执的`A_confirmation_pulses`仅计最后结果确认循环，不等于全部输入计划中的A输入段数。

## 截图、PCM与重复产物静态复核

[静态QA回执](static-validation.json)另行复核387非空双跑产物、18份正式JSON、91张256×240 PNG的RGB与同帧完整RAM/SRAM哈希，以及3份WAV的48kHz／双声道／16bit头、完整PCM哈希、11,435逐帧PCM段和11,435 audio callback段。三个最终完整截图已逐张查看：冷启动与普通攻击均回到战场武将指令光标，单挑返回后显示原升级通知。此复核不执行恢复控制器、不提供原核心内部CPU trace，也不把原核心WAV称为源码波形合成。

原捕获与双跑产物已冻结。重复命令必须使用全新的输出根目录；脚本拒绝覆盖已有case目录：

```sh
python3 scripts/capture_scene_controller_flows.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --repeat --out /tmp/phase11-new-replay/runtime
```

[机核总证据](evidence.json) · [总回执](validation.json) · [交互证据页](../index.html)
