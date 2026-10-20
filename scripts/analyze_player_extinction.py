#!/usr/bin/env python3
"""Read-only byte evidence for player no-candidate and mode-zero ending."""
from pathlib import Path
import argparse, hashlib, json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from inspect_game_data import OPS, SIZES
from source.recovered.battle_succession import ROM_SHA256

OUT = ROOT / 'analysis/phase17/extinction'
RANGES = [
    (25, 0xBE2E, 0xBE83, 'candidate_city_head_scan'),
    (26, 0xC37A, 0xC3BB, 'retirement_dispatch_and_leader_clear'),
    (26, 0xC3C2, 0xC435, 'human_loss_payload_and_AI_timer'),
    (24, 0xD693, 0xD69E, 'ending_mode_dispatch_prefix'),
    (24, 0xD6AA, 0xD755, 'mode_zero_loss_display_and_exit'),
    (24, 0xD76D, 0xD77B, 'loss_palette_copy'),
]
TABLES = [(26, 0xC380, 6, 'retirement three targets'),
          (26, 0xC3BB, 7, 'original seven ruler leader labels'),
          (24, 0xD69E, 12, 'six ending mode targets'),
          (24, 0xD755, 24, 'loss marker clock table'),
          (24, 0xD77B, 32, 'loss palette image')]

def digest(raw): return hashlib.sha256(raw).hexdigest()
def sha(path): return digest(Path(path).read_bytes())
def block(rom, bank, pc, length, role):
    off = 16 + bank * 8192 + (pc & 8191)
    raw = rom[off:off + length]
    return dict(physical_bank=bank, cpu_address=pc, rom_offset=off,
                length=length, role=role, raw_hex=raw.hex(), sha256=digest(raw))

def analyze(rom):
    OUT.mkdir(parents=True, exist_ok=True)
    instructions = []
    ranges = []
    for bank, lo, hi, name in RANGES:
        ranges.append(block(rom, bank, lo, hi - lo, name))
        pc = lo
        while pc < hi:
            # The inline retirement dispatch words are data.
            if bank == 26 and pc == 0xC380:
                pc = 0xC386
                continue
            off = 16 + bank * 8192 + (pc & 8191)
            op, mode = OPS[rom[off]]
            size = SIZES[mode]
            operand = int.from_bytes(rom[off + 1:off + size], 'little')
            raw = rom[off:off + size]
            instructions.append(dict(physical_bank=bank, cpu_address=pc,
                rom_offset=off, op=op, mode=mode, operand=operand,
                size=size, raw_hex=raw.hex()))
            pc += size
        assert pc == hi
    # These are provenance bytes, not additional recovered production bodies.
    producers = [block(rom, 11, 0xDADF, 29, 'title0012 ->0543;DAF4 writes6F43 exceptload index2'),
                 block(rom, 9, 0xD74E, 12, 'new-ruler0543 ->6F43 atD751'),
                 block(rom, 9, 0xD7D5, 14, '6F43 nonzero requestssecondhumanselection'),
                 block(rom, 9, 0xD850, 29, 'secondhumanselection writescontroller1 atD861')]
    catalog = dict(schema='phase17-player-extinction-byte-evidence-v1',
        rom_sha256=ROM_SHA256, instruction_count=len(instructions),
        original_instructions=instructions, code_ranges=ranges,
        data_tables=[block(rom, *x) for x in TABLES], opening_mode_producers=producers,
        public_routes={'postbattle': ['25A00C', '25AD81'], 'ending': ['23A01E']},
        local_override_functions=['BE2E', 'C386', 'C3C2', 'C41E', 'D6AA', 'D76D'],
        unchanged_parent_methods=['ADAA/AE0D wholecontroller routing', 'BE01 eight-phase dispatch',
            'A1C2 currentfocus', 'BED1 original citydetails list', 'C37A retirement dispatch',
            'A01E/D693 six-mode dispatch', 'DBF3 ending sprites', 'Global13 E46A setup',
            'E000 reset ->E066', 'title/new-ruler selection'])
    (OUT / 'static-catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'original.asm').write_text('; Offsets include the original16-byte iNES header; inline tables excluded.\n' + '\n'.join(
        f'b{x["physical_bank"]}:${x["cpu_address"]:04X} file{x["rom_offset"]:06X} {x["raw_hex"]:8s} {x["op"]} {x["mode"]} ${x["operand"]:04X}'
        for x in instructions) + '\n')
    print(json.dumps(dict(instructions=len(instructions), ranges=len(ranges), data_tables=len(TABLES))))

def evidence():
    c = json.loads((OUT / 'static-catalog.json').read_text())
    v = json.loads((OUT / 'validation.json').read_text())
    body = {(x['physical_bank'], x['cpu_address']) for x in c['original_instructions']}
    seen = {(x['physical_bank'], x['cpu_address']) for x in v['executed_original_locations']}
    pins = dict(v['source_sha256'])
    pins['scripts/analyze_player_extinction.py'] = sha(__file__)
    stale = [p for p, h in pins.items() if sha(ROOT / p) != h]
    e = dict(schema='phase17-player-extinction-source-evidence-v1',
        status='passed' if v['status'] == 'passed' and not stale else 'failed',
        rom_sha256=ROM_SHA256, source_sha256=pins, stale_source_paths=stale,
        artifact_sha256={str((OUT / p).relative_to(ROOT)): sha(OUT / p)
                        for p in ('static-catalog.json', 'original.asm', 'validation.json')},
        rom_cpu_case_count=v['rom_cpu_case_count'], complete_return_count=v['complete_return_count'],
        reset_boundary_count=v['reset_boundary_count'], strict_prefix_count=v['strict_prefix_count'],
        source_guard_case_count=v['source_guard_case_count'], comparison=v['comparison'],
        native_input_actual_caller_count=v['native_input_actual_caller_count'],
        original_city_A000_actual_caller_count=sum(x['callback_entry']=='A000' for x in v['actual_caller_inputs']),
        declared_A01F_suffix_caller_count=sum(x['callback_entry']=='A01F_explicit_suffix' for x in v['actual_caller_inputs']),
        original_accepted_NMI8_actual_caller_count=sum(x['callback_entry']=='accepted_original_NMI8' for x in v['actual_caller_inputs']),
        original_body_position_count=len(body), dynamic_body_positions=len(body & seen),
        unexecuted_body_positions=[dict(physical_bank=b, cpu_address=p) for b, p in sorted(body - seen)],
        source_original_CPU_callbacks=0, source_IR_interpretation=False,
        predicates=dict(candidate_city='owner&7==040A AND roster[0]!=FF; no HP/status/location filter',
            defeat_trigger='ADAA/AE0D oldleader.condition&3==3',
            initial_routing='whole controller==3 ->computer, otherwise player',
            retirement_routing='controller&3==3 ->byte timer, otherwise human loss notice',
            human_loss='both text jobsFF AND newA/B ->global13 endingmode0',
            final_exit='markerFE AND newA;6F43==0 ->tailE000;nonzero ->clear6F43/restore0472/73/global1'),
        limits=v['limits'])
    (OUT / 'evidence.json').write_text(json.dumps(e, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'README.md').write_text(f'''# 玩家无候选、灭亡反馈与mode0结局

[PlayerExtinction / PlayerLossEnding](../../../source/recovered/player_extinction.py)在冻结战后/结局控制器中替换六段具名直接规则。真正A00C/AD81父流程的self局部调用进入新方法，NMI8 A01E父流程调用新mode0方法；没有额外伪JSR，没有IR/原CPUfallback。原图形、文字、固定helper、全局13初始化和E000重启继续使用已恢复的独立源码。

BE2E只在0300/0304均FF且新A或B后扫描30城：city.owner低3位等于040A、名册首槽+17不是FF就足够。没有ownedcity和所有ownedcity首FF都会进入0471保存的无候选phase。首FF后仍有武将的hole也算无候选；首槽为原死亡/status3/HPFF武将仍算有候选城市。不能把该判定改成所有十槽、活着的武将数或任职地byte5。

C386仅把君主表leaderID写FF，城市owner、名册、控制器、驻城和外交均保留。初始ADAA/AE0D用整个controller==3分电脑/玩家；C386则用controller&3==3分通知，因此83/FF等raw边界不会被统一清洗。电脑C41E等待8bit调用计数wrap；玩家C3C2等待两文字job完成及A/B，构造日期/对方leader信息后进入global13、0541=0、04CA=0。C3C2中的040C是另一君主索引的作用域别名，不是此阶段的城市ID；它或对方leader为FF时，随后mode0请求D9，否则请求D8。

Global13 E46A设置NMI8并转global14。mode0 D6AA初始化palette/真实消息，文本完成后04CE逐次增一、查原D755 marker表。markerFE时只新A退出，B和无输入保留。6F43来自原标题人数选择0/1及新君主0543，不是实时剩余人类君主数量：0实际tailE000，抛弃旧caller栈并回E066启动边界；非0清6F43、0400/01←0472/73、0402=0、global1继续。不能把所有global13都称胜利或所有玩家灭亡都称整场结束。

新类保留actual caller AXYP/SP/PC和既有stackword；missing服务必须保持同一pending，不凭status字符串提前RTS，不写ready/ack，不制造NMI/IRQ。只读candidate_city_report解释BE2E的首槽门槛，不代替正式caller执行。

原CPU回执{v['rom_cpu_case_count']}案：{v['complete_return_count']}实际callerRTS、{v['reset_boundary_count']}原E000非局部reset边界、{v['strict_prefix_count']}严格prefix，另{v['source_guard_case_count']}源码guard。全2048B RAM（包括闲置栈）、8192B SRAM、AXYP/SP/PC、端口读写序、银行与N163图逐byte比较；源码原CPUcallback0。静态范围{len(body)}位置，动态覆盖{len(body & seen)}，未执行位置逐项列evidence。受控原CPU输入和实际Native内存来源分别列在回执；不是Nestopia内部寄存器trace，也不是像素/PCM生成器。

其中{v['native_input_actual_caller_count']}项使用正式三案冻结Native内存生成原caller：{e['original_city_A000_actual_caller_count']}项原27A000城市回调、{e['declared_A01F_suffix_caller_count']}项A000真实cadence早退后的明示A01F dispatchsuffix、{e['original_accepted_NMI8_actual_caller_count']}项从声明E066寄存器接受原NMI，执行到FA85真实JSR A01E。FE上的额外新A只用于独立CPU夹具，经原E6C6读取显式手柄输入产生；不写按钮/ready/result/ack内存。准备过程不再加case，所有初始寄存器、实际returnword/banks与前序记录保存在[caller输入](actual-callee-inputs/)。完整reset夹具显式供PPUSTATUS80/00边沿；持续0则停原E00C等待，未知E000另保持原tail依赖。三条原模拟器视频/PCM流程和它们的准备字节见[正式Runtime](../runtime/README.md)。

```python
postbattle = PlayerExtinction(memory, rom, services=source_coordinator)
postbattle.run_entry(0xA00C, registers=actual_caller)
ending = PlayerLossEnding(memory, rom, services=source_coordinator)
ending.run_entry(0xA01E, registers=actual_caller)
```

```sh
python3 scripts/analyze_player_extinction.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_player_extinction.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_player_extinction.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
```

正式{v['rom_cpu_case_count']}项回执包含Native调用层，复现应给三次`--native-case analysis/phase17/runtime/目录`：`single-player-empty-rosters-reset`、`two-player-empty-rosters-continue`、`former-leader-only-candidate`。不带该参数仅运行395项有界核心矩阵；不得据此覆盖最终回执后仍引用{v['rom_cpu_case_count']}项声明。

[原汇编](original.asm) · [逐byte静态来源](static-catalog.json) · [CPU回执](validation.json) · [pins与未覆盖](evidence.json)
''')
    print(json.dumps(dict(status=e['status'], CPU=v['rom_cpu_case_count'], guards=v['source_guard_case_count'], stale=stale)))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('rom', type=Path); p.add_argument('--evidence-only', action='store_true')
    a = p.parse_args(); rom = a.rom.read_bytes(); assert digest(rom) == ROM_SHA256
    evidence() if a.evidence_only else analyze(rom)

if __name__ == '__main__': main()
