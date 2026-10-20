#!/usr/bin/env python3
"""Write phase17 conclusions from passed original CPU and native receipts."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'analysis/phase17'

def main():
    field = json.loads((OUT / 'fields/validation.json').read_text())
    extinction = json.loads((OUT / 'extinction/validation.json').read_text())
    integration = json.loads((OUT / 'source-integration.json').read_text())
    native = json.loads((OUT / 'runtime/validation.json').read_text())
    assert all(r['status'] == 'passed' and not r.get('quick') for r in [field, extinction, integration, native])
    total = sum(r['rom_cpu_case_count'] for r in [field, extinction, integration])
    assert total == 6973
    assert field['total_complete_return_CPU_cases'] == 4890 and field['total_strict_prefix_CPU_cases'] == 1658
    assert extinction['complete_return_count'] == 416 and extinction['reset_boundary_count'] == 4 and extinction['strict_prefix_count'] == 3
    assert integration['complete_return_count'] == integration['reset_boundary_count'] == 1
    assert native['case_count'] == 3 and native['original_core_frames_both_runs'] == 68124
    text = '''# 第十七轮：城市辅助字段与玩家无候选后的败亡结局

补全玩家无候选继承人后的势力退出、败亡通知、单人软件重启和双人继续流程，并接入同一游戏Session。城市+1已确认参与错位16位门槛判断；+28..31已确认在无界扫描的显式边界条件下可被访问，但这些字节的正式名称仍未证明。

[交互证据页](index.html)提供完整源码、三组原Nestopia画面、整份WAV与逐帧字段。[总审计](verification.json)、[源码组合对照](source-integration.json)、[字段证据](fields/README.md)和[败亡结局证据](extinction/README.md)分别保留原字节、实际返回、非局部重启与严格前缀。原ROM只读，重建ROM逐字节一致；旧v16及更早版本归档保持原字节。

## 城市+1及+28..31

| 字段或路径 | 确认的行为 |
|---|---|
| 城市+1 | bank10 BD95读取`city[1] | (city[2] << 8)`并与300比较。+2同时是金低字节，所以不能命名为正常独立金字段。+1=0时金255通过，而金256失败，源码保留原错位读取。 |
| 城市+28..31 | 整条复制/清零涵盖这些字节；无界插入扫描在绕过正常容量检查的输入下可以读写它们。没有专用字段名称、padding或全ROM不使用的证明。 |
| 城市名册17..26 | 合法容量10人，满员允许没有FF结束符。玩家满员迁移拒绝，AI目标在正常人数域不超过10。原提名C21D最多读取这十槽，首FF提前结束。 |
| 无界插入A442 | 本地没有十槽上界；显式FF位置测试可越过尾字节及下一城+1。全256字节无FF会循环，源保留真实waiting，不能当完整RTS或自然UI溢出。 |

原27 AD41以合法9+1迁移生成十人名册，随后原26 C21D只读17..26；两步CPU/源码对照已内含于6548例，不另算Native战役证据。C21D按武将+4徳提名，平局保留原后遇者；这一有界扫描与玩家BE2E的首槽资格判断不同。

通过87个连续JMP入口槽及可信远端/直接调用扩展调查，可信指令位置从46,518增至47,968，新增1,450位置及18处间接访问。旧647个可能城市辅助字段别名中58个有精确地址证明排除，589个仍未解析。F368的raw16槽也按实际相邻机器字节处理，不假定全是合法君主指针；raw8的5F20配大Y可进入城市区，因此只排除地址集合确实不相交的读写点。32银行全部PRG字节已检查，但未解析控制入口与161个控制屏障仍保留，不能声称全ROM无其它消费者。

## 玩家无候选与势力退出

真实战后`27:A065 → EE07 → 25:A00C → AD81`由新[PlayerExtinction](../../source/recovered/player_extinction.py)接管。BE2E等待两文字job完成及新A/B，然后扫30城：owner低3位等于本君主且名册首槽+17非FF就算候选城市。它不遍历十槽筛生存者，也不检查HP、status、byte5或家族；首FF后仍有武将也无法通过，首槽为HPFF/status3的曹操却可以通过。

扫描失败后转无候选阶段。C386只写君主leaderID=FF，不清城市owner、名册、驻城、controller或外交。ADAA/AE0D使用完整controller==3，C386使用controller低2位==3，两种raw边界保留。玩家C3C2等待文字完成和A/B，准备日期与另一君主信息，写global13、0541=0、04CA=0。此处040C是另一君主索引的临时别名，不是选继承城市。

global13 E46A配置NMI8并转global14。新[PlayerLossEnding](../../source/recovered/player_extinction.py)恢复mode0 D6AA：初始化真实palette与败亡文字，文本完成后逐次推进04CE及D755 marker表；markerFE表示可退出。这里**只有新A退出，B不退出**，与前面的城市A/B门槛不同。另一君主leader存在时请求D8，否则D9。

退出分支读取6F43。这个字节来自原标题人数选择与0543，含义是开局人数模式留下的配置，并非实时剩余人类势力计数。值0走实际tail E000，原SP重置FF并进入E066，旧调用者不再返回；非0清6F43，0400/01恢复0472/73、0402=0、global1继续。不能把所有玩家失势都写成全场结束，也不能补上自动城市中立。

## 源码整合与真实重启边界

[city_field_contracts.py](../../source/recovered/city_field_contracts.py)提供只读CityAuxiliaryContract、精确记录指针、资源夹值、原提名与声明的容量/扫描前缀。完整入口和前缀分开，协调器不会把四种前缀自动当完整返回。

[extinction_scene_services.py](../../source/recovered/extinction_scene_services.py)在冻结的全局UI组合中替换结局owner，保留此前精确音频caller的既有栈帧。[SceneCoordinator](../../source/recovered/scene_coordinator.py)将真实25/26 A00C/AD81、23/24 A01E和全局NMI8交给新owner；[GameEngine](../../source/recovered/game_engine.py)新增`player_extinction_rules()`、`player_loss_ending_rules()`、`city_field_contract(city)`及`city_field_services()`。此前`battle_succession_rules()`现在返回新战后owner，其它旧模块和历史媒体保持原字节。

生产不执行原6502、CPU helper或控制IR。缺少服务、持续低PPUSTATUS或无FF的扫描保留真正pending，不写ready/ack，不补假RTS。单人尾调用E000在实际E066/SPFF边界使Session退役旧caller；双人返回原主循环。同一Session组合两例逐事件比较全2048B RAM（含闲置栈）、8192B SRAM、AXYP/SP/PC、银行、顺序端口和N163图。单人449显式NMI/2240 IRQ，双人579 NMI/2895 IRQ；这些显式CPU事件不是原Nestopia视频帧，也不额外计为父案例。

## 原CPU及源码对照

| 域 | CPU父案例 | 完成边界 | E000/E066非局部重启 | 严格前缀 | guard |
|---|---:|---:|---:|---:|---:|
| 城市记录与边界 | 6548 | 4890 | 0 | 1658 | 7 |
| 玩家失势与败亡结局 | 423 | 416 | 4 | 3 | 16 |
| 同一Session组合 | 2 | 1 | 1 | 0 | 3 |
| 合计 | 6973 | 5307 | 5 | 1661 | 26 |

全部通过，生产CPU/IR回退0。字段域另比较全部SRAM读写顺序。1658字段前缀和3结局前缀不代表整份母菜单完整返回。423案内含28份从正式Native内存生成的真实城市/NMI caller：17份27A000，3份A000按原节流早退后的明确A01F后缀，8份接受原NMI后到FA85真实JSR A01E。初始化寄存器与准备NMI是独立原CPU夹具，原核心没有提供内部PC/寄存器trace。

新owner影响的旧phase5..16矩阵按原声明范围真实重跑并逐条检查生产文件未变；未变的旧字段2537矩阵检查原依赖hash。旧总审计随后只读刷新，历史Native、HTML、直接模块与版本ZIP不改。详见[父级回归日志](regression/parent-regression.json)。

## 原Nestopia三条完整流程

| 实际流程 | 首跑帧 | 检查点 | 本轮准备byte写 |
|---|---:|---:|---:|
| 单人空名册：曹操原攻击败北→leaderFF→败亡B无效→A重启→标题重新开局 | 10136 | 242 | 11 |
| 真实双人冷启动：原两只手柄→出征/补给→败亡→另一玩家继续 | 15991 | 265 | 11 |
| 原名单资格对照：败北HPFF/status3的曹操仍被接受并再立 | 7935 | 87 | 11 |

独立进程双跑共68,124帧，首跑34,062帧；594个原同帧RGB/RAM/SRAM/state检查点，2,429份非空产物（含30正式JSON）重复完全一致。整份serializedstate不截断、不归一化；3份48kHz stereo 16bit完整WAV共27,204,733个样本对。594份空VRAM与路径metadata另列排除。

三案各有11次明确战前准备：5次HP/武力/敌slot相邻数值，6次实际名单字节改变；HPFF/status3、leaderFF、结局flag和新场景均由原攻击/主循环产生，后续没有result、ready或ack注入。两案导入相同自然战前母档且未继承阶段16之后的准备，双人案真实coldboot并通过标题选2人产生6F43=1，真实第二手柄输入另有port1记录。它们是公开准备的完整原流程，不冒称零准备自然灭亡战役。

单人空城11/14在leaderFF后仍owner2；败亡markerFE时原B按2帧，松开观察120帧仍不退出，A后实见global0→标题→新剧本city1/1及新名册。该重新初始化不能说成战后自动复活或中立。双人实见modeflag1→0、global14→1，第二玩家ruler4普通手柄2输入后进入city0/1。资格对照原确认文字显示曹操，最终leader131仍HPFF/status3而没有败亡结局。完整准备dump、手柄计划、字段及媒体见[原核心说明](runtime/README.md)。

## 复现与交付

```sh
.venv-trace/bin/python scripts/verify_city_field_contracts.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_city_field_contracts.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_player_extinction.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --native-case analysis/phase17/runtime/single-player-empty-rosters-reset --native-case analysis/phase17/runtime/two-player-empty-rosters-continue --native-case analysis/phase17/runtime/former-leader-only-candidate
python3 scripts/analyze_player_extinction.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
.venv-trace/bin/python scripts/verify_phase17_integration.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/write_phase17_report.py
python3 scripts/build_phase17_browser.py --require-final
python3 scripts/verify_phase17.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/package_results.py
python3 scripts/validate_phase17_package.py
```

不带三个`--native-case`只验证395项结局核心矩阵，不能覆盖423项最终回执后仍引用原总数。Native双跑命令见runtime各案。最终v17 ZIP核验CRC、精确allowlist、全部源码byte、实际caller及关键文件临时解压hash；工具链/环境/核心动态库/探索文件不入包。城市未命名字节仍需后续专用消费者证据，硬件像素/PCM合成仍由原核心提供；当前可读逻辑不是原作者完整工程或独立NES重制。
'''
    (OUT / 'README.md').write_text(text)
    print(json.dumps(dict(status='written', CPU_cases=total, guards=26), ensure_ascii=False))

if __name__ == '__main__':
    main()
