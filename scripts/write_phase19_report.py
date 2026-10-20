#!/usr/bin/env python3
"""Write the current phase report from frozen machine-readable receipts."""
from pathlib import Path
from collections import Counter
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase19'
def read(p):return json.loads(Path(p).read_text())
def main():
 service=read(OUT/'services/validation.json');integration=read(OUT/'source-integration.json')
 state=read(OUT/'state-format/validation.json');runtime=read(OUT/'runtime/validation.json')
 consumers=read(OUT/'cpu/consumer-sequences.json')
 browser=read(OUT/'browser-validation.json')
 tables={n:read(OUT/'fields-static'/n)['accesses']for n in('all-indirect-accesses.json','access-contracts.json','new-indirect-accesses.json')}
 access_counts={n:dict(Counter(r['classification']for r in rows))for n,rows in tables.items()}
 old=read(ROOT/'analysis/phase18/services/validation.json');catalog=read(ROOT/'analysis/phase18/services/static-catalog.json')
 old_static={(r['bank'],r['pc'])for r in catalog['instructions']}
 old_dynamic={(r['physical_bank'],r['cpu_address'])for r in old['executed_instruction_positions']}
 new_dynamic={(r['physical_bank'],r['cpu_address'])for r in service['executed_instruction_positions']}
 new_dynamic.update((r['physical_bank'],r['cpu_address'])for r in consumers['executed_instruction_positions'])
 missing=old_static-old_dynamic;added=missing&new_dynamic;remaining=missing-new_dynamic
 cases=[]
 for p in sorted((OUT/'runtime').iterdir()):
  if p.is_dir()and(p/'validation.json').exists():cases.append((p.name,read(p/'validation.json')))
 nframes=sum(r['frames']for _,r in cases);npoints=sum(r['checkpoint_count']for _,r in cases)
 preparations=sum(len(r['preparation'])for _,r in cases)
 counts=Counter(r['comparison']for r in service['cases'])
 table='\n'.join(f'| {name} | {r["frames"]} | {r["checkpoint_count"]} | {len(r["preparation"])} |'for name,r in cases)
 report=f'''# 阶段十九：完整指针关系、次级内政AI与原核真实存档上下文

本阶段有新增源码、原CPU差分和原Nestopia回放；**整体ROM逆向仍未全部完成**。城市+1的已知机器读法继续保留，城市+1和+28..31的正式名称仍没有充分证据，不能改写成确定名称或宣称unused／padding。

[交互证据页](index.html) · [整体审计](verification.json) · [上阶段冻结记录](regression/frozen-phase18.json) · [上一阶段](../phase18/index.html)

## 城市字段与剩余访问

城市记录32字节。已确认的补兵选择读取是`city[1] | (city[2] << 8)`，阈值300；正常金币仍是`city[2] | (city[3] << 8)`。这两个读法有交叠，不能把前一个字直接命名为“金币”，也不能仅据值常零给city+1正式命名。

另外新确认邻近字段**city+16是“宝／タカラ”的数量**。正式原截图[transfer-gold-after-up.png](runtime/resource-transfer-baseline/transfer-gold-after-up.png)同时显示城市资料“宝99”和输送栏“タカラ0”；新指针分析将此UI与实际+16byte资源操作联接。新GameEngine的`city_auxiliary_record()`公开`treasure_count_plus16`，旧字段命名保留为历史产物。

新分析保留完整16位地址之间的关系，不把某次武将指针的低字节与另一地址的高字节自由拼接。只有满足记录合同的工厂、完整复制、合流和callee写入关系才保留该证明；部分写、潜在镜像写、未知上下文继续保守退回。限定关系域的固定点不等于所有可能机器状态的全ROM可达性证明。

| 本轮清单 | 完整条目数 | 逐项分类计数 |
| --- | ---: | --- |
| 全部间接访问 | 1526 | `{json.dumps(access_counts['all-indirect-accesses.json'],ensure_ascii=False)}` |
| 旧589候选 | 589 | `{json.dumps(access_counts['access-contracts.json'],ensure_ascii=False)}` |
| 阶段18新增访问 | 45 | `{json.dumps(access_counts['new-indirect-accesses.json'],ensure_ascii=False)}` |

[分析合同与边界](fields-static/README.md) · [统计](fields-static/analysis-summary.json) · [全部逐项合同](fields-static/all-indirect-accesses.json) · [旧589项](fields-static/access-contracts.json)

三组真实物资输送对照使用正常菜单提交“城11→城14、金1”，接收城金币先公开准备为9899以留容量；对照分别保留原aux、改source city+1为44、改destination +28..31为12/34/56/78(hex)。结果以原逐帧文件为准。局部对照没有形成正式字段名称或全局未使用证明。

## 新的可读游戏源码

- [domestic_secondary_services.py](../../source/recovered/domestic_secondary_services.py)：B5FC按原拒绝采样选择三分支；B619邻国交涉／资源报价；B98B低忠武将招揽与名册提交；BBB2降低对方忠诚与通知。保留整数溢出、原资格和原调用边界。
- [domestic_secondary_integration.py](../../source/recovered/domestic_secondary_integration.py)：`DomesticSecondaryGameEngine`和`DomesticSecondarySceneCoordinator`接入原有campaign main／NMI／IRQ与UI服务，保留真实caller PC/SP及独立等待owner。
- [nestopia_context.py](../../source/recovered/nestopia_context.py)：原核存档的严格分块读取；恢复CPU寄存器、RAM、SRAM、实际PRG页与N163状态。它不执行6502，不替代模拟器，也不恢复硬件时序。

同文件的新增`CapturedServiceMemory`修复N163自动增址127→0边界，按固定原核`(address+increase)&127`执行，保留旧ServiceMemory为历史产物。{state['N163_boundary_transition_checks']}项地址／自增／读写／别名及显式硬件覆盖检查通过；这是固定原源的服务合同检查，不是新增原机帧回放。

F8在request不再等于F8时才继续，F9／FA在request回0时才继续。源码不会自行清request、伪造ready或替玩家回复。原B5FC曾有控制形式的恢复，本轮用具名业务方法接管这些分支；其余历史模块继续冻结，不据此声称全源码都已去除控制IR。

## 原CPU差分与动态覆盖

本轮服务验证共**{len(service['cases'])}个父case**，分类：`{json.dumps(dict(counts),ensure_ascii=False)}`。每例比较完整2KiB RAM（含idle stack）、8KiB SRAM、AXYP/SP/PC、顺序IO、4个PRG页和N163，生产源码的原CPU回调数0、IR解释为false。受控调用帧／数值边界、真实存档前序、实际异步消费者序列分别保留标签；等待与缺依赖前缀不算RTS返回。

按阶段18原739位置的同一集合计算：此前未动态覆盖{len(missing)}处，本轮新增命中其中**{len(added)}处**，当前仍有**{len(remaining)}处**未被这两轮矩阵覆盖。局部绕过资格的边界case不等于正常策略自然可达。

[服务验证](services/validation.json) · [原字节与覆盖](services/evidence.json) · [服务分析](services/README.md)

另有**{consumers['rom_cpu_sequence_count']}个完整消费者父序列**通过：F8接受／拒绝由原UI消费者写0／1后原暂停策略继续RTS，F9／FA通知由原消费者回0再RTS。接受／拒绝各85次显式NMI、425次IRQ，两个通知各61次NMI、305次IRQ。后续输入只有真实控制器端口与显式中断，没有request／ready／reply／PC写入。初始资格和控制器归属是公开CPU夹具，不能当成自然原机可达证据。[完整序列](cpu/consumer-sequences.json)

整合验证另计2组完整序列：从原核保存的真实PC／SP／AXYP出发，只在验证器中让原CPU前序到达E066；随后纯恢复源码各执行2次主循环、2次NMI及实际软件IRQ服务，完整内存、寄存器、IO、映射及N163一致。没有新内存准备。硬件读值和中断到达次序仍为公开软件输入，不计作原Nestopia视频帧。

[主循环整合验证](source-integration.json) · [执行位置](integration-executed-instructions.json)

## 原Nestopia实际流程

原ROM SHA256：`26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82`。未改ROM、原核dylib或旧存档。

本轮{len(cases)}组fresh-process双跑，首跑{nframes}帧、{npoints}检查点、共{preparations}个公开数值准备字节。自然扩城案使用原标题按钮冷启动，选择袁紹并出征中立城0，使城数3→4，再正常耗卡进入月轮；该案零准备字节。

| 正式流程 | 首跑原帧 | 检查点 | 准备字节 |
| --- | ---: | ---: | ---: |
{table}

**原机本轮没有观察到F8；因此不能宣称原机已验证F8实际发出、消费和返回。** 有界探索的额外月轮与8种普通确认时机没有观察到该请求，探索目录不进入正式包。源码／原CPU消费者验证如已通过，只按各自合同计数。

[原核汇总](runtime/validation.json) · [原始证据](runtime/evidence.json) · [对照结果](runtime/cohort-comparison.json) · [原核说明](runtime/README.md)

## 从真实原核存档读取上下文

此前“libretro没有CPU寄存器接口”的限制需细分：通用memory API不直接提供寄存器，但固定版本Nestopia的序列化`CPU/REG`确实保存7字节PC低、PC高、SP、A、X、Y、P。原官方实现见[NstCpu.cpp](https://github.com/libretro/nestopia/blob/135dfa6dfda5e7603d61e751b9ddd0cc42546bc3/source/core/NstCpu.cpp)，分块长度与压缩见[NstState.cpp](https://github.com/libretro/nestopia/blob/135dfa6dfda5e7603d61e751b9ddd0cc42546bc3/source/core/NstState.cpp)。

已检查{state['snapshot_count']}个原存档，分块RAM／SRAM均与相应完整转储一致；{state['original_core_roundtrip_count']}组原dylib load→serialize保持寄存器、RAM、SRAM、实际PRG和N163一致，执行视频帧数0。其中{state['RAM_shadow_bank_mismatch_count']}个保存点的实际PRG页与RAM银行影子不同，已全部做原核往返检查；后续追踪须用存档中的实际映射。全部检查保留未裁剪原存档及libretro footer，不用字串搜索或猜偏移。

保存位置快照不是原核逐指令trace；复制存档上下文到软件bus也不等于恢复PPU／APU／中断时序。官方源码和GPL许可一并保留于[state-format/upstream](state-format/upstream/)。

[存档上下文验证](state-format/validation.json)

## 证据页验收

本地地址为`http://127.0.0.1:8765/analysis/phase19/index.html`，使用CUA控制Codex内置浏览器，默认桌面DOM尺寸{browser['viewport']['DOM_width']}×{browser['viewport']['DOM_height']}，没有设置视口覆盖或测试移动端。最终页面标题、非空内容、错误覆盖层、控制台、截图与交互均通过；控制台error／warn为0。

分类→1125条排除项→搜索A5F3→唯一8:A5F3、翻页、3份完整源码SHA、4组8个原PNG路径／SHA与全部checkpoint字段、160个首尾字段值、40个中间帧字段值、拒绝小数帧且保留表格、4份原音频实际播放与时长均已验收。新增明确aria-label解决选项文本进入控件名称的问题，重载后复测通过。未声称浏览页播放证明源码与原硬件时序等价。

[浏览器逐项验收](browser-validation.json) · [静态资产合同](browser-static-check.json)

![原机宝／タカラ与实际输送后状态](browser-proof.jpg)

## 复现与交付

```sh
.venv-trace/bin/python scripts/verify_domestic_secondary_services.py ROM.nes
.venv-trace/bin/python scripts/verify_phase19_integration.py ROM.nes
python3 scripts/verify_nestopia_context.py ROM.nes
python3 scripts/analyze_city_pointer_provenance.py ROM.nes
python3 scripts/verify_phase19.py ROM.nes
```

各脚本的参数与原核回放入口以`--help`和脚本声明为准。沿用REA保留的反汇编／控制分析材料，补充本地原字节证明与纯源码差分；未修改tools/rea上游项目。旧phase1..18源码／报告／回放和v18压缩包冻结保留。v19新增输出仅写phase19和新增Source／脚本；最终包在审计及浏览器验收后生成。

剩余工作：尚无正式名称证据的城市aux字段、未知指针上下文、未动态覆盖的分支、未在原Nestopia观察到的F8交涉，以及全ROM其余控制形式和硬件边界。不能将本阶段通过当作整个游戏已完全还原。
'''
 (OUT/'README.md').write_text(report)
 coverage=dict(old_static_positions=len(old_static),old_dynamic_in_static=len(old_static&old_dynamic),
  old_missing_positions=len(missing),newly_executed_old_missing_positions=len(added),
  remaining_old_missing_positions=len(remaining),remaining=[dict(physical_bank=b,cpu=p)for b,p in sorted(remaining)],
  local_boundary_cases_are_not_natural_reachability=True)
 (OUT/'coverage-comparison.json').write_text(json.dumps(coverage,indent=2)+'\n')
 print(json.dumps(dict(report='analysis/phase19/README.md',native_cases=len(cases),native_frames=nframes,coverage=coverage),ensure_ascii=False))
if __name__=='__main__':main()
