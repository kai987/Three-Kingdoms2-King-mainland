#!/usr/bin/env python3
"""Generate phase14 report from passed CPU, integration and native receipts."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase14'
def read(path):return json.loads(path.read_text())
def main():
 areas={k:read(OUT/k/'validation.json')for k in('boot','domestic','tactical','city-cooperation-ui')};i=read(OUT/'source-integration.json');n=read(OUT/'runtime/validation.json')
 assert all(x['status']=='passed'for x in[*areas.values(),i,n])
 total=sum(x['rom_cpu_case_count']for x in areas.values());complete=sum(x['complete_return_count']for x in areas.values());prefix=sum(x['strict_prefix_count']for x in areas.values());guards=sum(x['source_guard_case_count']for x in areas.values())
 rows='\n'.join(f"| {k} | {r['rom_cpu_case_count']:,} | {r['complete_return_count']:,} | {r['strict_prefix_count']:,} | {r['source_guard_case_count']} |"for k,r in areas.items())
 text=f'''# 第十四轮：冷启动、重启与主循环合作 AI

本轮新增四份独立 Python 源码：[启动初始化](../../source/recovered/boot_initialization.py)、[内政合作 AI](../../source/recovered/domestic_cooperation_controller.py)、[战术合作 AI](../../source/recovered/tactical_cooperation_controller.py)及[合作反馈显示](../../source/recovered/city_cooperation_ui_services.py)。通过 [SceneCoordinator](../../source/recovered/scene_coordinator.py) 和 [GameEngine](../../source/recovered/game_engine.py) 共用显式 RAM、SRAM、端口输入与真实 caller 栈。生产路径不解释控制 IR、不执行原 6502，也没有原 CPU fallback。旧 IR API 保留供历史对照；新可读入口使用独立函数。

[交互证据页](index.html)提供四份完整源码、三条原 Nestopia 冷启动流程的原 PNG 和完整实际 WAV。[联合源码对照](source-integration.json)与[最终审计](verification.json)分别公开证据范围。

## 启动与非返回重启

固定 bank31 `$E000..$E065` 禁用 PPU，`SEI; CLD`，先完成 3 次 PPUSTATUS set/clear 握手，再初始化 APU，后完成 5 次握手。`Y=2/4` 的原循环实际执行 3/5 次。`TXS` 将 SP 置 `$FF`，清写 `$0004..$07FF` 共 2,044B，然后执行 `$F3BD` probe，写 `$007A=0`，直接到 `$E066`。

清零循环不写 `$0000..$0003`；`$0001/$0002` 是地址工作位，probe 又使用 `$0001`，普通 mismatch 路径保持入口 `$0000/$0003`。清零之后的 JSR 会重写 `$01FE/$01FF`，因此最终 RAM 不是整片全零。软件重启不是 RTS：统一入口在确实到达 `$E066,SP=$FF` 后退役旧 UI、NMI、主循环及 pending owner，再创建新服务对象，保留真实 RAM/SRAM 与端口日志。缺少 PPUSTATUS 输入时原位等待，不能凭空产生 vblank。

`$F3BD` 按 70 个自身 ROM 原始字节的低位比较 `(($4017>>1)^$FF)&1`。普通控制器输入会 mismatch 并返回，保留全部 8KiB 电池 SRAM。完全匹配才进入条件诊断：`$F422` 检查 8KiB 模式、`$F43F` 写模式、`$F458` 准备地址，`$F468` 生成 `(5*x+1)&255` 并跳过零。诊断填 32 个 palette 项并永久停在 `$F41E`，三种受控分支颜色为 `$01/$37/$16`。诊断含义依据代码行为推断；写故障分支是明确环境 fixture，不是本轮原模拟器中观察到的故障。

启动域 **304 项 E066 边界、549 项真实 caller RTS、3 项永久诊断前缀**，另 6 项 guard。127 条静态指令共 288B；动态清单 126 个位置，永久 JMP 本身在停止边界未执行。详细边界见 [启动报告](boot/README.md)。

## 合作主循环与 AI

全局 main2 原正文 `$E17D` 先执行 RNG 和 mapper 服务，再以真实 `$E188` caller 调用 bank10/11 `$A000→$A00F`。本轮将完整 6,053 个原控制位置整理成具名函数，包含月轮扫描、三类内政策略、忠诚、继承和归属反馈等此前遗漏正文。两处 `$D494` inline dispatch 保留原 scratch、flags、Y 与栈协议，固定 RNG 服务由既有独立 owner 执行。

`$CA7F/$CB79` 对 `$6F8B==1` 的等待保持同一个 generator/caller。启动一个新的 `$A000` 不能冒充续程，因为入口还会把某些相同字节解释为战斗返回。真实 NMI 反馈消费与恢复情况单列在联合回执；任何尚未恢复的显示服务均停在真实 callee，不能写 ack 或制造返回。

全局 main4 `$E221` 同样保留 RNG、mapper 与真实 `$E22C` caller，调用 bank8/9 `$A000→$A02D`。完整 2,213 个控制位置已从控制 IR 改为具名 Python 函数，含八种策略扫描与十六计略资格子函数；`$B517` 的 8/16 项 inline dispatch 保留真实协议。补给/治疗等策略可能提前改变资源与体力，`$B933` 会实际扣减低十位兵数，不能把全部 AI 仅称为无副作用的提案。攻击、计略执行与表现消费仍由原 NMI 场景层承担。

Domestic 动态执行 4,425/6,053 个局部位置；Tactical 为 1,669/2,213。覆盖完整静态闭包不等于每条分支都已动态验证。Tactical 的 448 项 `$B517` 协议前缀只核 inline callee 边界，另 2 项预算前缀及 1 项缺失 F266 fixture；它们不算完整武将决策。Domestic 的 22 项真实反馈等待和 21 项故意缺失 helper 前缀也分别统计。详细模块报告：[内政](domestic/README.md)、[战术](tactical/README.md)。

## 合作反馈显示与同一调用续程

补上 bank29/30 `$A042→$AA37` 的君主徽标 OAM/两行标题 producer，共 148 条正文指令，及 `$AB38` 姓名字形 badge producer。合法 caption0..3/FF、raw徽标ID、全部栈和OAM bytecursor的 1,264 项真实RTS及 5 项guard通过。producer只写实际`$0380`包与`$7E|4`任务；真实PPU consumer负责消费，继承反馈由原NMI2写`$6F8B=1`，没有人工ack。badge237..254只是原字节寻址测试，不能当有效武将身份。详见[辅助服务报告](city-cooperation-ui/README.md)。

## 原 CPU 与源码验证

| 域 | 原 CPU 对照 | 完成类别 | 严格前缀 | source guard |
|---|---:|---:|---:|---:|
{rows}
| 合计 | {total:,} | {complete:,} | {prefix:,} | {guards} |

完成类别包含启动的非返回 E066 边界，不能全部称 RTS。各域对照全 2,048B RAM（含闲置栈）、8,192B SRAM、AXYP/SP/PC、有序端口和银行。Domestic 的 21 项历史 helper oracle 模式及其 1,305 次 helper 调用仅用于验证；不安装在生产源码，且不额外加进 CPU case 总数。

统一入口另完成 **{i['rom_cpu_case_count']:,} 项原 CPU 对照、{i['source_guard_case_count']} 项 guard**：{i['reset_boundary_count']} 项 reset E066、{i['main_boundary_count']} 项普通主循环 E066、{i['actual_caller_return_count']} 项真正 caller RTS及 {i['strict_prefix_count']} 项严格前缀。两条继承场景的受控序列经 241 或 481 次真实 NMI2，由原 `$CBBD..$CBBF` 写 ack 后恢复同一待续主循环到 E066；每个长序列仍只计一个 CPU case，嵌套 NMI/helper 不重复加入总数。此两行预先固定 1,976B RAM 契约（UI 1,972B + 真实 `$01FC..$01FF` caller 4B栈），保留 `$01B4..$01FB` 闲置栈残差日志；首个 `$01EC` 原56/source166，不能称完整2,048B一致。其它主循环/16计略资格/启动组继续全2,048B。16资格分别覆盖true/false受控子调用，不等于main4自然选中全部16项计略。具体每行范围、真实 preparation 和 NMI interleave 以回执为准。源码内原 CPU callbacks 均为零。Native 只供应冻结 RAM/SRAM 输入，AXYP、caller frame 和显式硬件流均是独立 CPU fixture；没有宣称取得原核心内部 CPU trace。

## 原模拟器完整流程

使用原 ROM 与原 Nestopia 2.0.0 核心，三案均从零 SRAM 冷启动，不导入状态或 battery 文件，无新增 core RAM/SRAM、ready、结果写入。

- `cold-city-domestic-cycle`：12,536 帧。从标题选择曹操进入游戏，三次征兵/分配消耗玩家行动 3→2→1→0，随后六位 AI 君主分别出现原合作请求与完成字段，推进至 189 年 2 月，回到玩家世界地图/城市选择（main0/sub1），玩家行动恢复为 3。第一笔原后备兵已满，数量零的合法确认仍消耗行动；后两笔实际征兵 100、各花金币 20，并实际分配兵数。
- `core-reset-battery-retention`：4,122 帧。调用原 libretro `retro_reset`；即时和后续 1,200 帧的全部 8KiB SRAM 与复位前一致，RAM/场景重新初始化到标题。复位即时没有新 RGB 帧，未制造即时截图。
- `title-intro-software-restart`：4,000 帧。普通无按键演示计时完整达到 `$0B58`，原字段出现 title4，frame3073 出现 global0，再走启动。与原 Title `$D74C→$E000` 静态路径联合解释；不是内部 CPU PC 采样。

三案首跑 **{n['frames_first_run']:,} 帧**、双跑 **{n['frames_both_runs']:,} 帧**，**{n['checkpoint_count']} 个检查点、{n['nonempty_repeat_artifact_checks']} 份非空产物**逐字节 hash 一致（含 21 份正式 JSON 与未经修改的原序列化状态）。三份原 48kHz 双声道 WAV 共 **{n['PCM_stereo_sample_frames_first_run']:,} stereo sample frames**，每帧 PCM/RGB/RAM/SRAM hash 均核对；208 个 0B VRAM 和 snapshot 路径 metadata 单独排除。

两次回放分别用全新 Python 进程加载同一原核心。同进程尝试中部分序列化状态尾四字节不一致的原始产物保留在 exploratory，内部字段语义未确认；没有截断、normalize、打补丁或删除原证据。正式 fresh-process 双跑含完整 raw state 严格相等。

## 使用与边界

```python
from source.recovered.game_engine import GameEngine
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import NMIRegisters

# ports 必须由调用方提供真实观察或明确的 CPU fixture，不自动完成硬件。
memory = ServiceMemory(rom, ram, sram, banks, read_ports=ports)
game = GameEngine(memory, rom=rom, mapped=True)
result = game.initialize_readable_boot(actual_registers_at_E000)
# dependency 时保留同一上下文，供给硬件输入后 game.resume_readable_boot()
# reset_boundary 时寄存器已经位于 E066/SPFF，旧 caller 已退役。
# 继续 game.tick_readable_main(registers, entry=0xE066) 或相应真实 NMI API。
```

原 ROM 与重建 ROM 逐字节相同。当前整理仍是可读游戏逻辑/服务，不是原作者源码或能独立合成全部 NES 音画的重制版。硬件 RESET 微序列、PPU/APU/N163 时钟、IRQ/NMI 时序、RGB/PCM 合成由原核心验证。本轮证明三条原模拟器完整流程和声明的源码函数边界；未证明所有战役、异常继承、全部 AI 分支或所有硬件诊断组合均完整跑通。
'''
 (OUT/'README.md').write_text(text);print(json.dumps(dict(CPU=total,complete=complete,prefix=prefix,guards=guards,integration=i['rom_cpu_case_count'])))
if __name__=='__main__':main()
