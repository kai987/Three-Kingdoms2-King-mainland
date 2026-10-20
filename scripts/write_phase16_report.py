#!/usr/bin/env python3
"""Write phase16 conclusions from current passed CPU and native receipts."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'analysis/phase16'

def main():
    areas=['fields','succession','audio-requests','graphics','loyalty']
    receipts={a:json.loads((OUT/a/'validation.json').read_text()) for a in areas}
    linked=json.loads((OUT/'audio-requests/actual-callers.json').read_text())
    integration=json.loads((OUT/'source-integration.json').read_text())
    native=json.loads((OUT/'runtime/validation.json').read_text())
    assert all(r['status']=='passed' and not r.get('quick') for r in [*receipts.values(),linked,integration,native])
    rows=[]
    for name,r in [*receipts.items(),('实际音频callee',linked),('统一入口与同一Session',integration)]:
        complete=r.get('complete_return_count',r.get('total_complete_return_CPU_cases'))
        prefix=r.get('strict_prefix_count',r.get('total_strict_prefix_CPU_cases'))
        assert complete+prefix==r['rom_cpu_case_count']
        rows.append(f"| {name} | {r['rom_cpu_case_count']:,} | {complete:,} | {prefix:,} | {r['source_guard_case_count']} |")
    total=sum(r['rom_cpu_case_count'] for r in [*receipts.values(),linked,integration])
    assert total==12703
    text='''# 第十六轮：实际战后继承、势力退出与适性编码

本轮恢复真正的战后城市控制器，并将年月图形、精确音频请求及忠诚跳转桥接入可读源码。适性3的机械行为已经确认；城市+1的正式名称和+28..31的专用用途仍未确认，保留原始值和待查访问，避免把推测写成游戏规则。

[交互证据页](index.html)提供五个源码域、四条原Nestopia流程、全部原画面/完整WAV和逐帧字段。[最终审计](verification.json)核对当前源码、原字节、回执和媒体；[统一入口对照](source-integration.json)独立检验调用栈与续程。原ROM只读，重建ROM逐字节一致；v15及更早版本ZIP保持原样。

## 城市未命名字段与适性3

| 字段 | 确认的行为与范围 |
|---|---|
| 城市+1 | physical10 BD97/BD9D读取`record[1] | record[2]<<8`并与300比较；+2同时是金的低字节，必须保留这种重叠读取。正式名称仍未决。 |
| 城市+28..31 | 初始表、整条清除和复制可涉及这些字节；尚未确证专用消费者，不能命名为人口、特产或保留字段。 |
| 有效武将的适性 | 237名有效武将初始值只有0/1/2：111/70/56名。实际资料页显示平、山、水。 |
| raw适性3 | 两位字段能表示3，但资料/阵形索引超过三项表；下文给出原机器码和实际字形，不定义第四兵种。 |

扩展调查合并61份冻结的静态/原CPU来源，覆盖32个PRG bank的46,518个指令位置；另扫描全部262,144个PRG字节。追踪F2AF/F2D7城市指针、复制别名、callee和Y范围，逐项保留原字节及producer证据。两个整条清除/复制访问确实覆盖尾部，但不赋予其专用含义。最后仍有647个候选访问无法完全解析：72项城市指针已确认而Y未知，575项指针或位移索引未解。因此这次扩大调查仍不足以证明全ROM不使用尾部字段。详见[字段报告](fields/README.md)、[候选清单](fields/city-tail-candidate-review.json)及[可读实现](../../source/recovered/field_semantics.py)。

适性3在physical25 B630的上行字形表越界，取到B64D/B64E机器码`A0 0B`；B64D下行前缀越界取到B719/B71A的`4A 4A`。physical15 CB40的地形匹配表四项中，code3与code0的匹配值均为0；D102的三行阵形表越界读D1C8后的`02 80 80 00 80 00 00 00`，后续80索引还能越过普通参数行。战場DD45复制raw两位到0628，玩家移动表code3行成本为0；既有AI读取byte8两次的原行为保持。

原场景初始化实际复制240×12字节，末三项ID237..239属于相邻表数据，byte11为FF/BE/FF，确实能出现raw适性3。它们不是有效武将；不能据237名有效初始英雄没有3就称所有初始化SRAM都没有3。已确认的17处有效武将byte11写入保留适性位，仍不能把局部扫描说成全ROM不存在其它生产者。

## 实际战后继承与势力退出

原战后路径是`27:A065 → EE07 → 25:A00C → AD81`，城市main13按AD84的七项表运行`AD95 / ADAA / AE0D / AE51 / BE01 / C132 / C37A`。这条实际路径区别于此前独立恢复的内政CA19/CB52/CA7F。本轮恢复其七阶段、玩家八阶段、AI六阶段和无候选三阶段，保留真实文字、图形、音频和等待协议。[battle_succession.py](../../source/recovered/battle_succession.py)使用可读的候选扫描、名册替换和忠诚处理函数。

- AI继承先扫描原家族优先表，再在本势力城市的连续名册中选德最高者；同德以原`>=`比较保留后遇者。名册首FF即结束，原算法没有另加HP、status或byte5资格过滤。
- 有候选时写新君主及忠诚100，并按原流程更新有关名册和其它武将忠诚；忠诚重算复用physical10 CF7C，保留家族豁免和字节运算；低忠诚离开另按25/26 C01E或C318处理，保留AI/玩家的地点、归属及放走差异。
- 无候选的C386只将君主ID写FF。原下一月轮实际跳过该势力，但空城归属可继续保持原owner；不能补写全城中立、清外交或自动全面删除事务。
- 玩家败北后真实BE01流程要求选本势力城市、选新君主、确认，然后返回城市。原普通攻击使曹操HP为FF、status低两位为3；源码保留原值，不擅自改成HP0。实际选城市11、武将5于禁并确认完成。

因此已补全本轮观测到的AI继承/无候选退出及玩家选继承人路径。“君主FF、月轮不再参与”是本次确认的灭亡表现；所有城市中立、玩家完全无候选的game over及自然全势力灭亡/统一胜利仍需要单独证据。

## 解除的真实依赖与源码续程

[postbattle_graphics.py](../../source/recovered/postbattle_graphics.py)恢复实际`29:A01E → A6B6`年月packet：raw年+100，raw月+1，两行七个tile写入2043/2063请求，沿原E9BA转换和007E队列协议。它不是另一个世界初始化器；raw月255的字节溢出也按原行为保留。

[exact_audio_requests.py](../../source/recovered/exact_audio_requests.py)恢复12个固定音频请求入口，包括E67B的六descriptor阶段。每层原PHA/PLA、JSR、尾调用和N163端口顺序均保留。旧全局/初始化服务的内部固定调用原本绕过coordinator；[integrated_scene_services.py](../../source/recovered/integrated_scene_services.py)现在用其已经形成的真实JSR栈帧委托新owner，不再增加栈帧。原旧服务文件不改，当前完整2048B比较包含闲置栈。

[postbattle_loyalty_bridge.py](../../source/recovered/postbattle_loyalty_bridge.py)恢复A009原JMP到既有CF7C；复用旧可读内政helper，而不是又声称恢复整份6053位置的内政程序。两种新服务及实际继承通过SceneCoordinator接入GameEngine，未知服务仍停在实际边界，不制造ready/ack或成功返回。

GameEngine提供`battle_succession_rules()`、`postbattle_graphics_rules()`、`postbattle_loyalty_rules()`及只读`city_unresolved_fields(city)`。`affinity_field_services()`的局部后缀必须使用声明的真实caller上下文：A796要求caller PHA，B64D只比较到B663的前缀，不能作为普通独立JSR自动路由。生产函数不运行原CPU、不解释控制IR；原ROM数据仅按原表索引读取。

## 原CPU与当前源码验证

| 域 | CPU父案例 | 完成边界 | 严格前缀 | guard |
|---|---:|---:|---:|---:|
ROWS
| 总计 | 12,703 | 12,442 | 261 | 54 |

0失败。主域、19份真实音频callee与24项统一入口分别计数；22份A00C输入由原城市callback及真实准备函数产生，其中21份走A000，一份A000按原节流直接返回，明确改用A01F后缀，不注入ready。它们使用Native内存和独立原CPU调用上下文，不是Nestopia内部寄存器trace。

另两个父案例在同一CampaignSession从实际global main1经过city13继承到world main0/sub1及文字空闲。每案接受681次显式NMI和3405次真实IRQ续程，内部阶段不再加计为CPU案例，也不等同自然视频帧。每个事件比较2048B RAM（含闲置栈）、8192B SRAM、AXYP/SP/PC、银行、顺序端口和N163寄存器图；无人工ack。严格前缀共261项不当完整母函数返回，未动态覆盖分支另列。

受新owner影响的旧phase5..15整合矩阵实际重新执行，旧只读总审计随后依据当前源码刷新；既有原核心媒体、HTML与版本ZIP保留历史原件。

## 原Nestopia实际流程

四案使用只读原ROM和Nestopia 2.0.0 135dfa6，独立进程各跑两次。首跑17,581帧，双跑35,162帧；251个同帧RGB/RAM/SRAM/state检查点，1,076份非空媒体与正式JSON重复一致。整份serializedstate不截断、不规范化；四份48kHz stereo WAV来自原核心，共14,041,675个样本对。源码没有安装到原核心，硬件RGB/PCM合成仍由原核心提供。

| 实际流程 | 首跑帧 | 本轮准备byte写次数 | 继承旧准备 |
|---|---:|---:|---:|
| AI有继承人city13→下一月 | 3,880 | 0 | 19 |
| AI无继承人city13→下一月跳过 | 3,800 | 0 | 26 |
| 玩家普通攻击败北→选城/选君主/确认 | 7,935 | 5 | 0 |
| 同一实例资料页适性0/1/2/3 | 1,966 | 4 | 0 |

四案各导入一份公开母档。本轮9次准备写与旧45次准备分别公开；两个city13母档已继承上一轮实际计略死亡，不称零准备自然灭亡。没有新增状态、死亡结果、ready或ack注入。适性资料页四次实际B开/A关，code3原16×16区域显示表外字形；证据页仅CSS放大原PNG，不编辑图像、不赋予官方名称。

有继承者君主8→9后继续参与月轮；无候选君主8→FF后跳过，但城市1/3仍owner1且名册为空。玩家攻击曹操HPFF/status3后完成于禁继承及city0/1返回。原帧末6F8B只观察到0/FF或FF，没有内部PC，也没有证明FB/FC/ack中间值或CA19入口。具体调用链由独立原CPU证据另证。完整来源与限制见[原核心报告](runtime/README.md)。

## 复现

```sh
.venv-trace/bin/python scripts/verify_field_semantics.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_battle_succession.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_exact_audio_requests.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_postbattle_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --area graphics
.venv-trace/bin/python scripts/verify_postbattle_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --area loyalty
.venv-trace/bin/python scripts/verify_phase16_integration.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/write_phase16_report.py
python3 scripts/build_phase16_browser.py --require-final
python3 scripts/verify_phase16.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/package_results.py
```

Native双跑与actual-caller准备命令另见各域报告。最终ZIP另做CRC、精确文件清单、源码/证据hash及关键文件解压核验，排除核心动态库、工具链、环境和探索文件。本轮完成的是声明范围的源码恢复与原流程验证；尚未恢复整款游戏的原作者工程或独立硬件时序核心。
'''.replace('ROWS','\n'.join(rows))
    (OUT/'README.md').write_text(text)
    print(json.dumps(dict(status='written',CPU_cases=total,guards=54),ensure_ascii=False))

if __name__=='__main__':main()
