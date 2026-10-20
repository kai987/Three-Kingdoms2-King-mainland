#!/usr/bin/env python3
"""Pin phase9 player settlement provenance without executing ROM, IR or CPU.

This analysis reads the original ROM, AST/source text and existing comparison
receipt. It emits byte ranges, a disassembly with inline data separated, and
the exact current semantic-source/validator hashes. It adds no gameplay code.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from inspect_game_data import instruction, OPS, SIZES

ROM_SHA = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
NAMES = ('火計','陥穽','虚兵','要撃','乱水','火箭','偽撃転殺','共殺',
         '籠絡','落石','連環','十面埋伏','水攻','連弩','劫火','奇門遁甲')
ENTRIES = (0xB062,0xB0DD,0xB155,0xB17A,0xB1D5,0xB243,0xB062,0xB2CD,
           0xB31C,0xB3B6,0xB3D0,0xB42A,0xB466,0xB4B8,0xB50C,0xB5A6)
RANGES = (
    ('player_scan_and_message_selection',12,0xA000,0xAAA7,0xAB1A),
    ('player_result_message_table',12,0xA000,0xAB1A,0xAB2A),
    ('player_confirmation_and_notifications',12,0xA000,0xAB2A,0xABA4),
    ('level_change_query',13,0xC000,0xDEE9,0xDF27),
    ('second_notice_trampoline',8,0xA000,0xA018,0xA01B),
    ('second_notice_officer_gate',9,0xC000,0xD390,0xD3D8),
    ('second_notice_officer_table',9,0xC000,0xD3D8,0xD3EE),
    ('sixteen_effect_reset_and_dispatch',12,0xA000,0xB02B,0xB062),
)
DATA = {
    (12,0xAAE0):(2,'farcall_entry','EE07 inline target A027; selector3D -> physical29/30'),
    (12,0xAB1A):(16,'message_table','16 tactic result message bytes, not opcodes'),
    (13,0xDF15):(2,'farcall_entry','EE07 inline target A018; selector28 -> physical8/9'),
    (9,0xD3D8):(22,'officer_table','one FF-terminated tail table, not opcodes'),
    (12,0xB042):(32,'effect_pointer_table','16 little-endian EADE entries, not opcodes'),
}


def hash_bytes(value):
    return hashlib.sha256(value).hexdigest()


def file_offset(bank,base,address):
    return 16 + bank * 8192 + address - base


def pin(path):
    p = ROOT / path
    return dict(path=path,bytes=p.stat().st_size,sha256=hash_bytes(p.read_bytes()))


def analyze(rom,out):
    assert len(rom)==524304 and rom[:4]==b'NES\x1a' and hash_bytes(rom)==ROM_SHA
    out.mkdir(parents=True,exist_ok=True)
    ranges=[];listing=[];instruction_count=0;instructions=[]
    for name,bank,base,start,end in RANGES:
        assert base<=start<end<=base+8192
        offset=file_offset(bank,base,start);raw=rom[offset:offset+end-start]
        row=dict(name=name,physical_bank=bank,cpu_window_base=base,cpu_start=start,
                 cpu_end_exclusive=end,file_offset=offset,rom_offset=offset,byte_count=len(raw),
                 raw_hex=raw.hex(' ').upper(),sha256=hash_bytes(raw),segments=[])
        listing.append(f'; {name}\n; physical bank{bank} ${start:04X}..${end-1:04X}, file0x{offset:06X}, {len(raw)} bytes\n')
        pc=start
        while pc<end:
            data=DATA.get((bank,pc));at=file_offset(bank,base,pc)
            if data:
                size,kind,comment=data;assert pc+size<=end
                block=rom[at:at+size]
                row['segments'].append(dict(kind=kind,cpu_start=pc,cpu_end_exclusive=pc+size,
                    file_offset=at,byte_count=size,raw_hex=block.hex(' ').upper(),sha256=hash_bytes(block),description=comment))
                if kind=='farcall_entry':
                    assert rom[at-3:at]==bytes((0x20,0x07,0xEE))
                    listing.append(f'{at:06X} b{bank:02}:${pc:04X}  {block.hex(" ").upper():<8} .word ${int.from_bytes(block,"little"):04X} ; {comment}\n')
                elif kind=='effect_pointer_table':
                    for i in range(16):
                        listing.append(f'{at+2*i:06X} b{bank:02}:${pc+2*i:04X}  {block[2*i:2*i+2].hex(" ").upper():<8} .word ${int.from_bytes(block[2*i:2*i+2],"little"):04X} ; ID{i} {NAMES[i]}\n')
                else:
                    for i,value in enumerate(block):
                        label=f'ID{i} {NAMES[i]}' if kind=='message_table' else f'index{i}; '+('terminator' if value==255 else f'officerID{value}')
                        listing.append(f'{at+i:06X} b{bank:02}:${pc+i:04X}  {value:02X}       .byte ${value:02X} ; {label}\n')
                pc+=size;continue
            stop=min([end]+[address for (b,address) in DATA if b==bank and pc<address<end])
            beginning=pc
            while pc<stop:
                at=file_offset(bank,base,pc);op,mode=OPS[rom[at]];size=SIZES[mode]
                assert op not in ('?','BRK') and pc+size<=stop,(name,hex(pc),op,size)
                n,text=instruction(rom,at,pc);assert n==size
                listing.append(f'{at:06X} b{bank:02}:${pc:04X}  {rom[at:at+size].hex(" ").upper():<8} {text}\n')
                ins=dict(physical_bank=bank,cpu=pc,file_offset=at,bytes=rom[at:at+size].hex(' ').upper(),mnemonic=op,addressing_mode=mode,size=size)
                if mode=='rel':
                    displacement=rom[at+1];ins['target']=(pc+2+(displacement if displacement<128 else displacement-256))&65535
                elif mode=='ab' and op in ('JSR','JMP'):
                    ins['target']=int.from_bytes(rom[at+1:at+3],'little')
                instructions.append(ins);instruction_count+=1;pc+=size
            row['segments'].append(dict(kind='code',cpu_start=beginning,cpu_end_exclusive=stop,
                                       file_offset=file_offset(bank,base,beginning),byte_count=stop-beginning))
        assert sum(s['byte_count']for s in row['segments'])==len(raw)
        ranges.append(row);listing.append('\n')

    code_starts={(i['physical_bank'],i['cpu'])for i in instructions}
    for ins in instructions:
        if 'target' not in ins:continue
        targets=[r for r in ranges if r['physical_bank']==ins['physical_bank'] and r['cpu_start']<=ins['target']<r['cpu_end_exclusive']]
        if targets:
            assert (ins['physical_bank'],ins['target'])in code_starts,ins
    pointer_at=file_offset(12,0xA000,0xB042)
    entries=tuple(int.from_bytes(rom[pointer_at+2*i:pointer_at+2*i+2],'little')for i in range(16))
    assert entries==ENTRIES
    messages=rom[file_offset(12,0xA000,0xAB1A):file_offset(12,0xA000,0xAB2A)]
    notices=rom[file_offset(9,0xC000,0xD3D8):file_offset(9,0xC000,0xD3EE)]
    assert len(messages)==16 and len(notices)==22 and notices[-1]==255 and 255 not in notices[:-1]
    assert all(i<237 for i in notices[:-1])
    assert rom[file_offset(8,0xA000,0xA018):file_offset(8,0xA000,0xA01B)]==bytes((0x4C,0x90,0xD3))

    source=ROOT/'source/recovered/tactical_effects_complete.py'
    tree=ast.parse(source.read_text())
    slices=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id=='rom' and isinstance(node.slice,ast.Slice):
            slices.append([ast.literal_eval(node.slice.lower),ast.literal_eval(node.slice.upper)])
    assert sorted(slices)==sorted([[file_offset(12,0xA000,0xAB1A),file_offset(12,0xA000,0xAB2A)],
                                 [file_offset(9,0xC000,0xD3D8),file_offset(9,0xC000,0xD3EE)]])
    imports=[n.module for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)]
    assert all(not any(word in (module or '')for word in ('py65','state_machine','control','trace'))for module in imports)
    methods={n.name:dict(source_line=n.lineno,source_end_line=n.end_lineno)for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)}
    method_ranges={
        'dispatch':[(12,0xB02B,0xB042)],
        'player_result_scan':[(12,0xAAA7,0xAAB6)],
        'advance_player_result_after_graphics':[(12,0xAAB9,0xAAE3)],
        'queue_player_success_result':[(12,0xAAE3,0xAB1A),(12,0xAAD5,0xAAE3)],
        'player_confirm_after_text_ready':[(12,0xAB32,0xAB41)],
        'level_change_query':[(13,0xDEE9,0xDF27),(8,0xA018,0xA01B),(9,0xD390,0xD3D8)],
        'player_level_change_after_query':[(12,0xAB46,0xAB49)],
        'player_second_notice_after_text_ready':[(12,0xAB5A,0xAB67),(12,0xAB86,0xAB90)],
        'finish_player_without_level_change_after_query':[(12,0xAB6F,0xAB82)],
    }
    source_map=[]
    for method,windows in method_ranges.items():
        assert method in methods
        source_map.append(dict(method=method,**methods[method],original_windows=[dict(physical_bank=b,cpu_start=s,cpu_end_exclusive=e)for b,s,e in windows],
                               scope='Gameplay semantics under its explicit source caller/prelude contract; not CPU register or rendering equivalence'))
    receipt_path=ROOT/'analysis/phase9/source-integration.json';validation=json.loads(receipt_path.read_text())
    assert validation['status']=='passed' and validation['rom_sha256']==ROM_SHA and not validation['failures']
    assert validation['source_sha256']['source/recovered/tactical_effects_complete.py']==hash_bytes(source.read_bytes())
    total=sum(r['byte_count']for r in ranges)
    code_bytes=sum(s['byte_count']for r in ranges for s in r['segments']if s['kind']=='code')
    farcalls=[dict(physical_bank=b,call_cpu=at-3,inline_word_cpu=at,target=int.from_bytes(rom[file_offset(b,0xA000 if b==12 else 0xC000,at):file_offset(b,0xA000 if b==12 else 0xC000,at)+2],'little'),selector=selector,physical_pair=pair)
              for b,at,selector,pair in [(12,0xAAE0,0x3D,[29,30]),(13,0xDF15,0x28,[8,9])]]
    dependency_pins=[pin('source/recovered/tactical_effects_complete.py'),pin('scripts/verify_phase9_integration.py'),pin('scripts/analyze_phase9_settlement.py')]
    tables=[dict(name=s['kind'],physical_bank=r['physical_bank'],cpu_start=s['cpu_start'],
                 rom_offset=s['file_offset'],byte_count=s['byte_count'],raw_hex=s['raw_hex'],sha256=s['sha256'])
            for r in ranges for s in r['segments']if s['kind']in ('message_table','officer_table','effect_pointer_table')]
    rea_paths=('analysis/rea/pairs/pair-12/procedure-index.json','analysis/rea/pairs/pair-12/functions/0xb02b.asm','analysis/rea/pairs/pair-12/functions/0xb02b.c')
    evidence=dict(schema='phase9-settlement-provenance-v1',status='passed',rom_sha256=ROM_SHA,rom_bytes=len(rom),rom_modified=False,
        source_pin=pin('source/recovered/tactical_effects_complete.py'),validator_pin=pin('scripts/verify_phase9_integration.py'),
        generator_pin=pin('scripts/analyze_phase9_settlement.py'),
        referenced_CPU_receipt=pin('analysis/phase9/source-integration.json'),
        addressing='iNES16-byte header + physicalbank*8192 + (CPU-windowbase); bank12/13 map A000/C000, bank8/9 map A000/C000; fixed31 E000 helpers separate',
        ranges=ranges,tables=tables,dependency_pins=dependency_pins,REA_archive=[pin(p)for p in rea_paths if (ROOT/p).is_file()],
        REA_limit='The archived B02B view does not resolve all16 EADE inline entries; table sizes/entries and farcall words here are separately checked from originalbytes.',
        instructions=instructions,source_method_ranges=source_map,source_ROM_slices=slices,source_AST_imports=imports,
        inline_farcall_words=farcalls,
        effect_dispatch=dict(physical_bank=12,call_cpu=0xB03F,helper=0xEADE,table_cpu=0xB042,index='0543 & 0F',
             reset={'RAM_start':0x42C,'RAM_end_exclusive':0x435,'result_byte':0x544},
             entries=[dict(tactic_id=i,name=NAMES[i],target_cpu=target)for i,target in enumerate(entries)]),
        player_message_table=dict(physical_bank=12,cpu=0xAB1A,byte_count=16,messages=list(messages),
             death_override='ID1/9 with0432!=FF ->042C=deadID then F293 message4E job5',
             zero_loss_fallback='ID9 with042C:042D==0 selectsID1 text before death override',
             failed_cast='0544 nonzero ->A4=4,F283 message73 job2; restore0509=050A and real bank29 A027 portrait'),
        second_notice_table=dict(physical_bank=9,cpu=0xD3D8,byte_count=22,values=list(notices),
             starts_by_level={str(level):start for level,start in ((3,0),(4,11),(5,17),(6,20))},
             eligible_officer_tail_by_level={str(level):list(notices[start:-1])for level,start in ((3,0),(4,11),(5,17),(6,20))},
             semantics='All starts scan the SAME finalFF-terminated tail; unmatched/otherlevel sets042D=FF, match returns keeping042D. Announcement gate, no grant/roster/equipment writes.'),
        actual_call_chain=['bank12 AB41 JSR bank13 DEE9','bank13 DF12 JSR fixed31 EE07, selector28, inlineA018',
                          'bank8 A018 JMP bank9 D390','bank9 D390 reads record11 high4 and officer tail table',
                          'DEE9 queues4A/4D viaF293 and returnscarry; original caller AB44 chooseslevel/audio/cursor branch'],
        external_boundaries=[dict(bank=13,cpu=0xD6CC,role='actual unit/map graphics CALL atAAB6; source does not execute or acknowledge it'),
             dict(bank=29,cpu=0xA027,role='actual actor portrait afterAAE0 inline entry'),
             dict(bank=13,cpu=0xDF27,role='actual text readiness beforeAB32/AB5A suffix'),
             dict(bank=13,cpu=0xDC63,role='actual input service beforeAB32/AB5A suffix'),
             dict(bank=31,cpu=0xF283,role='queue message job2; queuewrite does not complete text'),
             dict(bank=31,cpu=0xF293,role='queue message job5; queuewrite does not complete text'),
             dict(bank=31,cpu=0xE57F,role='actual audio reset'),dict(bank=31,cpu=0xE68B,role='actual audio sequence7B'),
             dict(bank=31,cpu=0xE673,role='actual audio sequence1D'),dict(bank=12,cpu=0xA1F7,role='actual cursor graphics tailJMP')],
        original_only_blocks=[dict(bank=12,cpu_start=0xAB90,cpu_end_exclusive=0xABA4,
             source_implemented=False,CPU_tested_by_pinned_integration_verifier=False,
             behavior='DF27carry readiness then DC63 input, real0081bit0 ->0501=0; otherwiseRTS. This adjacent confirmation handler is listed only as originalbytes, not claimed as a recovered source API.')],
        referenced_validation={k:validation[k]for k in ('status','actual_ROM_CPU_comparison_count','counts','native_core_field_comparison_count','source_guard_count','all_SRAM_compared_bytes','limits')if k in validation},
        machine_checks=dict(ranges=len(ranges),ROM_bytes=total,code_bytes=code_bytes,data_bytes=total-code_bytes,
             static_instruction_count=instruction_count,inline_word_count=len(farcalls),table_count=3,
             whole_range_segment_coverage=True,all_in_range_control_targets_are_instruction_starts=True,
             sixteen_dispatch_entries_match_original=True,source_data_slices_match_actual_tables=True,
             source_hash_matches_existing_CPU_receipt=True,new_ROM_CPU_case_count=0,IR_execution_count=0),
        limitations=['This is static byte provenance and existing receipt pins, not a new CPU or original-core experiment.',
                     'Listed code boundaries do not recover actual graphics/audio/readiness service bodies.',
                     'AB90..ABA4 adjacent original-only handler is outside the current public semantic source and verifier.',
                     'Queued upgrade/second-notice text describes existing level change; D390 itself does not grant equipment/tactics or change membership.'])
    asm=''.join(listing);(out/'original-ranges.asm').write_text(asm)
    evidence['disassembly_pin']=dict(path=str((out/'original-ranges.asm').relative_to(ROOT)),sha256=hash_bytes(asm.encode()),bytes=len(asm.encode()))
    (out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    table_rows='\n'.join(f'| {r["name"]} | {r["physical_bank"]} | {r["cpu_start"]:04X}..{r["cpu_end_exclusive"]-1:04X} | 0x{r["file_offset"]:06X} | {r["byte_count"]} |'for r in ranges)
    (out/'README.md').write_text(f'''# Phase9 玩家结果与升级通知来源证据

本目录固定原ROM的8段结算字节、源码及验证器SHA。生成器只读取文件、做静态反汇编与AST/哈希核对，不执行ROM、IR、CPU、游戏帧或玩法公式。它没有新增原CPU病例；引用现有集成回执的{validation['actual_ROM_CPU_comparison_count']}项原CPU比较、{validation.get('native_core_field_comparison_count','未单列')}项原核心field比较与{validation.get('source_guard_count','未单列')}项源码guard时，各范围仍按该回执区分。

| 范围 | 物理bank | CPU闭区间 | 文件偏移 | 字节数 |
|---|---:|---|---|---:|
{table_rows}

合计{total}原字节：{code_bytes}代码字节、{total-code_bytes}数据字节；{instruction_count}条静态解码指令，不代表动态覆盖。`evidence.json`每段包含完整rawbytes、SHA、代码/数据分段及源码方法行号，`original-ranges.asm`逐地址显示文件偏移。完整段覆盖与段内跳转落点均实际检查。

AAA7先读真实007E。050B是结果扫描cursor，复制至0509，实际D6CC返回后才递增，20槽扫描完推进子状态并排结果消息。失败用73/job2；成功按16项AB1A表取消息。ID9无兵损按ID1文字处理，ID1/9有死者0432则用4E/job5。队列写入不等于原消息已完成。

AB2A/AB52分别调用真实DF27、DC63后检查0081 bit0。AB41调用DEE9查询已发生等级变化；改级时推进子状态，并交实际E57F/E68B音频。第二通知读042D，未用过时先置FF再排4B/job5；下一次真实A确认交E57F/E673，然后AB6F复制046C..046F到6F3F..6F42、清0500/0501，交A1F7光标绘制。源码的具名after_*合同只从实际前序服务已返回的位置继续，不默认完成服务。

内联数据精确为AAE0的A027（EE07 selector3D→29/30）和DF15的A018（selector28→8/9）。它们不是指令。B03F的EADE后B042..B061是16项LE16效果入口；AB1A..AB29是16个消息byte；D3D8..D3ED是22个通知tablebyte。三者均标数据，避免把表中6C误读成JMP或把inline18误读成CLC。

实际链为bank12 AB41→bank13 DEE9→fixed EE07(selector28、inlineA018)→bank8 A018 JMP→bank9 D390。D390用record11高4位：level3/4/5/6起点0/11/17/20，均扫描**同一个末FF终止的尾列表**。其作用仅决定042D第二通知标记，不发装备、不改名册、不在本段授予新计略；真实可见新计略文字属于消息说明，原玩法能力读取另有等级规则。

AB90..ABA3另有相邻确认handler：真实DF27/DC63和A通过后清0501，其余RTS。该块已附原bytes，当前统一高层源码和集成验证器没有对应方法/测试，明确记作original-only，不能据同一个大范围的存在声称已经高层化。

当前固定统一源码SHA `{hash_bytes(source.read_bytes())}`；验证器SHA `{hash_bytes((ROOT/'scripts/verify_phase9_integration.py').read_bytes())}`。源码ROM切片经AST核对精确对应16消息表与22通知表，并与现有CPU回执sourcepin一致。外部图形、音频、readiness与完整NMI仍按真实边界说明。

- [可机核全部证据与pins](evidence.json)
- [原字节反汇编及数据表](original-ranges.asm)
- [当前统一结算源码](../../../source/recovered/tactical_effects_complete.py)
- [当前原CPU集成验证器](../../../scripts/verify_phase9_integration.py)
- [引用集成回执](../source-integration.json)
- [正式原核心实验](../runtime/README.md)

```sh
python3 scripts/analyze_phase9_settlement.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
''')
    print(json.dumps(dict(output=str(out.relative_to(ROOT)),**evidence['machine_checks'],
                          source_sha256=evidence['source_pin']['sha256'],validator_sha256=evidence['validator_pin']['sha256'],
                          evidence_sha256=hash_bytes((out/'evidence.json').read_bytes()),disassembly_sha256=evidence['disassembly_pin']['sha256']),ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=ROOT/'analysis/phase9/settlement')
    a=p.parse_args();analyze(a.rom.read_bytes(),a.out)
