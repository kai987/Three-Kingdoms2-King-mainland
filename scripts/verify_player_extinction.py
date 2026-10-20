#!/usr/bin/env python3
"""Original CPU versus readable player extinction and mode-zero ending.

Every source helper is independent recovered source. Original CPU runs only
on the oracle side. Existing caller stack words are explicit test inputs;
Native binary inputs are memory data, not internal CPU register observations.
"""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.player_extinction import PlayerExtinction, PlayerLossEnding, SuccessionRegisters
from source.recovered.battle_succession import ROM_SHA256
from source.recovered.service_memory import ServiceMemory
from source.recovered.game_engine import GameEngine

OUT = ROOT / 'analysis/phase17/extinction'
REGS = ('a', 'x', 'y', 'p', 'sp', 'pc')
def digest(raw): return hashlib.sha256(raw).hexdigest()
def sha(p): return digest(Path(p).read_bytes())
def reg(r): return {k: getattr(r, k) for k in REGS}
def memory(rom, ram, sram, banks, reset_edges=False, buttons=(0,0)):
    return ServiceMemory(rom, ram, sram, banks,
        read_ports={0x2002: [128,0]*8 if reset_edges else 0, 0x4015: 0, 0x5800: 127},
        repeat_read_ports=(0x2002, 0x4015, 0x5800), controller_buttons=buttons)

def verify(rom, quick=False, native_cases=()):
    assert digest(rom) == ROM_SHA256
    OUT.mkdir(parents=True, exist_ok=True)
    source_paths = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'source/recovered').glob('*.py'))
    source_paths += ['scripts/verify_player_extinction.py']
    pins = {p: sha(ROOT / p) for p in source_paths}
    rows, failures, guards = [], [], []
    counts, visited = Counter(), Counter()
    artifact = {}
    mother = ROOT / 'analysis/phase16/runtime/player-defeat-successor/observed-g02-n02-city-013-004'
    base_r = Path(str(mother) + '-ram.bin').read_bytes()
    base_s = Path(str(mother) + '-sram.bin').read_bytes()
    for ext in ('-ram.bin', '-sram.bin'):
        path = Path(str(mother) + ext); artifact[str(path.relative_to(ROOT))] = sha(path)

    def fresh(ruler=2, controller=0, mode=0):
        r, s = bytearray(base_r), bytearray(base_s)
        r[0xE1:0xE4] = bytes([34, 57, 58])
        r[0x400:0x403] = bytes([13, 4, 1])
        r[0x40A] = ruler; r[0x40B] = s[0xF07 + 8 * ruler]; r[0x40C] = 1
        r[0x470:0x474] = bytes([2, 6, 13, 3])
        r[0x81] = r[0x87] = r[0x7E] = r[0x7C] = 0
        r[0x300] = r[0x304] = 255; s[0xF43] = mode
        r[0x541] = 0; r[0x542] = 0
        r[0x4D0] = 0; s[0xF0A + 8 * ruler] = controller
        for city in range(30):
            s[32 * city] = (s[32 * city] & 248) | 7
            s[32 * city + 17:32 * city + 27] = bytes([255] * 10)
        return r, s

    def compare(group, ram, sram, meta, *, entry, ending=False, missing=False,
                initial=None, banks=None, reset_edges=True, existing_frame=False):
        banks = banks or ((6, 23, 24, 31) if ending else (2, 25, 26, 31))
        edges = ending and sram[0xF43] == 0 and ram[0x81] & 1 and ram[0x4CB] == 254 and reset_edges
        left, right = memory(rom, ram, sram, banks, edges), memory(rom, ram, sram, banks, edges)
        initial = initial or dict(a=17, x=23, y=31, p=32, sp=253, pc=entry)
        if not existing_frame:
            for m in (left, right):
                m[0x100 + ((initial['sp'] + 1) & 255)] = 0x67
                m[0x100 + ((initial['sp'] + 2) & 255)] = 0x24
        r = SuccessionRegisters(**initial); c = MPU(memory=left)
        for k, v in initial.items(): setattr(c, k, v)
        game = GameEngine(right, rom=rom, mapped=True); co = game.readable_scene_rules()
        assert co.external_callback is None
        services = None if missing is True else (
            lambda call: {'status':'dependency','reason':'Explicit missing E000'} if call.target==0xE000 else co(call)
            ) if missing == 'reset' else co
        owner = (PlayerLossEnding if ending else PlayerExtinction)(right, rom, services)
        before_sram = bytes(left.sram)
        try:
            result = owner.run_entry(entry, registers=r)
            assert result['status'] in ('returned', 'reset_boundary', 'dependency'), result
            for n in range(1000000):
                if n and c.pc == r.pc and c.sp == r.sp and left.banks == right.banks:
                    if result['status'] in ('returned', 'reset_boundary') or (
                        reg(c) == reg(r) and left.ram == right.ram and left.sram == right.sram):
                        break
                if c.pc < 0x8000: raise RuntimeError(f'Oracle RAM PC{c.pc:04X}')
                bank = left.banks[(c.pc - 0x8000) // 8192]
                visited[(bank, c.pc, 16 + bank * 8192 + (c.pc & 8191))] += 1
                c.step()
            else: raise RuntimeError(f'Oracle budget PC{c.pc:04X}; sourcePC{r.pc:04X}')
            rd = [(i, a, b) for i, (a, b) in enumerate(zip(left.ram, right.ram)) if a != b]
            sd = [(0x6000 + i, a, b) for i, (a, b) in enumerate(zip(left.sram, right.sram)) if a != b]
            rg = {k: [getattr(c, k), getattr(r, k)] for k in REGS if getattr(c, k) != getattr(r, k)}
            assert not rd and not sd and not rg, dict(RAM=rd[:12], SRAM=sd[:12], registers=rg)
            assert left.io_writes == right.io_writes and left.io_reads == right.io_reads
            assert left.banks == right.banks and left.n163_ram == right.n163_ram
            completion = {'returned': 'actual_caller_RTS', 'reset_boundary': 'E000_nonlocal_E066_boundary',
                          'dependency': 'strict_prefix'}[result['status']]
            kind = 'complete_return' if result['status'] == 'returned' else (
                'reset_boundary' if result['status'] == 'reset_boundary' else 'strict_prefix')
            rows.append(dict(group=group, input=meta, entry=entry,
                comparison=kind, completion_kind=completion, source_status=result['status'],
                initial_registers=initial, final_registers=reg(r), original_instructions=n,
                source_original_CPU_callbacks=0, comparison_body_IRQ_or_NMI_injected=False,
                original_caller_prefix_accepts_NMI=bool(existing_frame and ending),
                source_service_calls=len(owner.events), final_fields=owner.fields(),
                SRAM_changes=[dict(address=0x6000+i, before=a, after=b)
                              for i, (a, b) in enumerate(zip(before_sram, left.sram)) if a != b],
                helper_owner_counts=dict(Counter(x['kind'] for x in co.calls)),
                RAM_bytes=2048, SRAM_bytes=8192, final_banks=list(right.banks),
                explicit_reset_PPUSTATUS_edges=edges,
                ordered_ports_sha256=digest(json.dumps(right.io_writes, separators=(',', ':')).encode())))
            counts[group + ':' + kind] += 1
            return left, right, r, owner, result
        except Exception as exc:
            failure = dict(group=group, input=meta, entry=entry, error=str(exc),
                           source_PC=r.pc, source_SP=r.sp, events=owner.events)
            failures.append(failure)
            if len(failures) < 12: print(json.dumps(failure, ensure_ascii=False), flush=True)
            return None

    # Typed ruler domains and original first-slot-only semantics. Dead HPFF
    # and condition3 reflect an observed former leader, not a live eligibility rule.
    for ruler in (range(2) if quick else range(7)):
        for shape in ('no_owned_city', 'owned_all_empty', 'firstFF_hole', 'dead_first', 'live_first'):
            r, s = fresh(ruler=ruler)
            if shape != 'no_owned_city':
                s[96] = (s[96] & 248) | ruler
                if shape == 'firstFF_hole': s[114] = 131
                elif shape in ('dead_first', 'live_first'):
                    s[113] = 131; s[0x3C0 + 12*131] = 255 if shape == 'dead_first' else 1
                    s[0x3C0 + 12*131 + 11] = 3 if shape == 'dead_first' else 0
            for button in ((1,) if quick else (0, 1, 2, 3, 255)):
                r[0x81] = button
                checked = compare('candidate_city_first_slot', r, s,
                    dict(ruler=ruler, roster_shape=shape, button=button), entry=0xBE2E)
                if checked:
                    report = checked[3].candidate_city_report(ruler)
                    assert report['no_candidate_city'] == (shape not in ('dead_first', 'live_first'))
    for busy in (0, 1, 2, 3):
        for button in (0, 1, 2, 255):
            r, s = fresh(); r[0x81] = button
            if busy & 1: r[0x300] = 0
            if busy & 2: r[0x304] = 0
            for entry in (0xBE2E, 0xC3C2):
                compare('genuine_text_and_new_button_gates', r, s,
                        dict(busy_mask=busy, button=button), entry=entry)
    # Entire-byte initial routing and low2 retirement routing deliberately disagree.
    for controller in ((0, 3) if quick else (0, 1, 2, 3, 4, 0x83, 255)):
        for ruler in ((2,) if quick else range(7)):
            r, s = fresh(ruler=ruler, controller=controller); r[0x401] = 6; r[0x402] = 0
            compare('leader_only_retirement_controller_low2', r, s,
                    dict(controller=controller, ruler=ruler), entry=0xC386)
        r, s = fresh(controller=controller); r[0x401] = 1; r[0x507] = 0x12
        s[0x3C0+12*s[0xF17]+11] |= 3
        compare('initial_controller_wholebyte', r, s, dict(controller=controller), entry=0xADAA)
    for other in ((1, 255) if quick else (0, 1, 2, 6, 255)):
        for year, month in ((0, 0), (155, 254), (156, 255), (255, 255)):
            r, s = fresh(); r[0x81] = 1; r[0x40C] = other
            s[0xF00] = year; s[0xF01] = month
            compare('loss_payload_other_ruler_and_date_word', r, s,
                    dict(other_ruler=other, year=year, month=month), entry=0xC3C2)
    for timer in (0, 1, 254, 255):
        r, s = fresh(); r[0x4D0] = timer
        compare('AI_retirement_byte_call_counter', r, s, dict(timer=timer), entry=0xC41E)
    # Legal nested retirement dispatches call the new methods inside their real local frames.
    for sub in range(3):
        r, s = fresh(controller=3 if sub == 2 else 0); r[0x401] = 6; r[0x402] = sub; r[0x81] = 1
        compare('actual_postbattle_parent_dispatch', r, s, dict(sub=sub), entry=0xA00C)

    for winner in (8, 255):
        r, s = fresh(); r[0x541] = 0; r[0x4CA] = 0; r[0x42E] = winner
        compare('initial_loss_notice_D8_D9', r, s, dict(winning_leader=winner), entry=0xA01E, ending=True)
    # Four legal sprite animation frames, marker bytes, text gating and bytecounter wrap.
    for animation in ((1,) if quick else (1, 2, 3, 4)):
        for marker in ((255, 254) if quick else (0, 1, 10, 255, 254)):
            for busy in ((0,) if quick else (0, 1, 2, 3)):
                r, s = fresh(); r[0x4CA] = animation; r[0x4CB] = marker
                r[0x4CD] = 255; r[0x4CE] = 91; r[0x541] = 0
                if busy & 1: r[0x300] = 0
                if busy & 2: r[0x304] = 0
                compare('loss_animation_marker_text_gates', r, s,
                    dict(animation=animation, marker=marker, busy_mask=busy), entry=0xD6AA, ending=True)
    for mode in ((0, 1) if quick else (0, 1, 2, 255)):
        for button in (0, 1, 2, 3, 255):
            r, s = fresh(mode=mode); r[0x4CA] = 1; r[0x4CB] = 254; r[0x81] = button
            compare('markerFE_A_only_reset_or_continue', r, s,
                    dict(opening_mode=mode, button=button), entry=0xD6AA, ending=True)
    r, s = fresh(); compare('strict_missing_record_service', r, s, None, entry=0xC386, missing=True)
    r, s = fresh(); r[0x4CA] = 1; r[0x4CB] = 254; r[0x81] = 1
    compare('strict_missing_real_reset', r, s, None, entry=0xD6AA, ending=True, missing='reset')
    compare('actual_reset_vblank_wait', r, s, dict(PPUSTATUS=0), entry=0xD6AA, ending=True, reset_edges=False)

    # Formal Native supplies RAM/SRAM only. Original caller preparations are
    # independently executed before the source-comparison input is captured.
    # No RAM ready/result/ack/button bytes are written during these prefixes.
    input_dir=OUT/'actual-callee-inputs';native_inputs=[]
    for case_dir in native_cases:
        case_dir=case_dir.resolve();ck_path=case_dir/'checkpoints.json'
        checkpoints=json.loads(ck_path.read_text());artifact[str(ck_path.relative_to(ROOT))]=sha(ck_path)
        selected=[];seen_states=set()
        for item in checkpoints:
            prefix=case_dir/item['label'];raw=Path(str(prefix)+'-ram.bin').read_bytes()
            key=(raw[0x7A],raw[0x78],raw[0x400],raw[0x401],raw[0x402])
            if raw[0x78]==2 and raw[0x400]==13 and raw[0x401] in (0,4,6) and raw[0x7A] in (1,2):
                relevant=raw[0x401]==0 or (raw[0x401]==4 and raw[0x402] in (0,1,2,3,4,5)) or raw[0x401]==6
                if relevant and key not in seen_states:
                    selected.append((item,False));seen_states.add(key)
            if raw[0x7A]==14 and raw[0x78]==8 and raw[0x541]==0:
                kind=('ending',raw[0x4CA]==0,raw[0x4CB]==254)
                if kind not in seen_states:
                    selected.append((item,True));seen_states.add(kind)
        for item,ending in selected:
            prefix=case_dir/item['label'];raw=Path(str(prefix)+'-ram.bin').read_bytes();sram=Path(str(prefix)+'-sram.bin').read_bytes()
            for ext in('-ram.bin','-sram.bin'):
                p=Path(str(prefix)+ext);artifact[str(p.relative_to(ROOT))]=sha(p)
            buttons_to_test=(0,1)if ending and raw[0x4CB]==254 else(0,)
            for button in buttons_to_test:
                banks=(raw[0xDE]&31,raw[0xDF]&31,raw[0xE0]&31,31)
                buttons=[0,0];buttons[sram[0xF44]&1]=button
                original=memory(rom,raw,sram,banks,buttons=tuple(buttons));cpu=MPU(memory=original)
                cpu.a=17;cpu.x=raw[0x7C];cpu.y=31;cpu.p=32;cpu.sp=255;cpu.pc=0xE066
                preparations=[];cadence=False
                if ending:
                    declared_parent=reg(cpu);cpu.nmi();callback_entry='accepted_original_NMI8'
                else:
                    for entry,y in((0xF206,None),(0xF25F,raw[0xE1]),(0xF237,0x3B)):
                        if y is not None:cpu.y=y
                        cpu.pc=entry;cpu.sp=253;original[0x1FE:0x200]=bytes([0x67,0x24])
                        for n in range(200000):
                            if n and(cpu.pc,cpu.sp)==(0x2468,255):break
                            cpu.step()
                        else:raise RuntimeError('Original city callback preparation budget')
                        preparations.append(dict(entry=entry,Y=y,instructions=n))
                    cpu.pc=0xA000;cpu.sp=253;original[0x1FE:0x200]=bytes([0x67,0x24]);callback_entry='A000'
                    declared_parent=reg(cpu)
                target=0xA01E if ending else 0xA00C;pair=(23,24)if ending else(25,26)
                for n in range(1000000):
                    if cpu.pc==target and tuple(original.banks[1:3])==pair:break
                    if not ending and n and cpu.pc==0x2468:
                        cadence=True;callback_entry='A01F_explicit_suffix';cpu.pc=0xA01F;cpu.sp=253
                        original[0x1FE:0x200]=bytes([0x67,0x24])
                    cpu.step()
                else:raise RuntimeError('Original callee discovery budget '+str(prefix))
                initial=reg(cpu);input_dir.mkdir(exist_ok=True)
                name=f'{case_dir.name}-{item["label"]}-'+('ending'if ending else'city')+f'-button{button}'
                callee=input_dir/name
                meta=dict(case=case_dir.name,label=item['label'],frame=item['frame'],
                    native_snapshot=str(prefix.relative_to(ROOT)),original_parent_registers=declared_parent,
                    initial_registers=initial,actual_banks=list(original.banks),
                    actual_return_PC=((original[0x100+((cpu.sp+1)&255)]|original[0x100+((cpu.sp+2)&255)]<<8)+1)&65535,
                    actual_return_SP=(cpu.sp+2)&255,preparation=preparations,
                    original_prefix_instructions=n,callback_entry=callback_entry,
                    A000_cadence_returned_before_dispatch=cadence,declared_controller_buttons=buttons,
                    additional_new_A_through_original_E6C6=bool(button),
                    native_internal_CPU_trace=False,
                    provenance='FrozenNative RAM/SRAM; declared originalCPU citycallback or acceptedNMI8 parent; actual original JSR frame. Preparation instructions are not extra source cases.')
                for ext,data in(('-ram.bin',original.ram),('-sram.bin',original.sram)):
                    Path(str(callee)+ext).write_bytes(data)
                Path(str(callee)+'.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
                for ext in('-ram.bin','-sram.bin','.json'):
                    p=Path(str(callee)+ext);artifact[str(p.relative_to(ROOT))]=sha(p)
                compare('formal_native_original_caller',original.ram,original.sram,meta,
                    entry=target,ending=ending,initial=initial,banks=tuple(original.banks),existing_frame=True)
                native_inputs.append(meta)

    # These cases exercise Source guards only; original table-outside instructions are not run.
    for cls in (PlayerExtinction, PlayerLossEnding):
        pair = cls.PAIR
        for name, args, banks in [
            ('actual_registers', {}, (2, *pair, 31)),
            ('pair', dict(registers=SuccessionRegisters()), (2, 12, 13, 31)),
            ('return_word', dict(registers=SuccessionRegisters(), return_pc=0x1234), (2, *pair, 31)),
            ('decimal', dict(registers=SuccessionRegisters(p=40)), (2, *pair, 31)),
            ('entry', dict(registers=SuccessionRegisters(), entry=0x8123), (2, *pair, 31))]:
            r, s = fresh(); m = memory(rom, r, s, banks); m[0x1FE:0x200] = bytes([0x67,0x24])
            owner = cls(m, rom); before = (bytes(m.ram), bytes(m.sram), list(m.io_writes))
            try: owner.run_entry(**args)
            except ValueError: pass
            else: raise AssertionError(f'{cls.__name__} guard {name}')
            assert before == (bytes(m.ram), bytes(m.sram), list(m.io_writes))
            guards.append(cls.__name__ + ':' + name)
    r, s = fresh(); m = memory(rom, r, s, (2,25,26,31)); owner = PlayerExtinction(m, rom)
    for ruler in (-1, 7, 255):
        try: owner.candidate_city_report(ruler)
        except ValueError: guards.append('candidate_report_typed_ruler_' + str(ruler))
        else: raise AssertionError('Invalid report ruler')
    for cls, entry, ending in ((PlayerExtinction,0xC386,False),(PlayerLossEnding,0xD6AA,True)):
        r,s=fresh(); r[0x4CA]=1; r[0x4CB]=254; r[0x81]=1
        m=memory(rom,r,s,(6,23,24,31)if ending else(2,25,26,31));m[0x1FE:0x200]=bytes([0x67,0x24])
        rr=SuccessionRegisters();o=cls(m,rom);res=o.run_entry(entry,registers=rr);assert res['status']=='dependency'
        pending=o.pending;before=(bytes(m.ram),bytes(m.sram),reg(rr));assert o.resume()['status']=='dependency'
        assert pending is o.pending and before==(bytes(m.ram),bytes(m.sram),reg(rr));guards.append(cls.__name__+':same_pending_no_fake_RTS')
    r,s=fresh();m=memory(rom,r,s,(6,23,24,31));m[0x1FE:0x200]=bytes([0x67,0x24])
    try:PlayerLossEnding(m,rom).run_entry(registers=SuccessionRegisters(),max_blocks=0)
    except ValueError:guards.append('loss_ending_zero_budget_not_fake_complete')
    else:raise AssertionError('Loss ending zero budget accepted')
    assert pins == {p: sha(ROOT / p) for p in source_paths}, 'Source changed during validation; rerun after freeze'
    result = dict(schema='phase17-player-extinction-original-CPU-v1',
        status='passed' if not failures else 'failed', rom_sha256=ROM_SHA256,
        rom_cpu_case_count=len(rows), complete_return_count=sum(x['comparison']=='complete_return' for x in rows),
        reset_boundary_count=sum(x['comparison']=='reset_boundary' for x in rows),
        strict_prefix_count=sum(x['comparison']=='strict_prefix' for x in rows),
        source_guard_case_count=len(guards), failed_count=len(failures), failures=failures,
        rows=rows, counts=dict(counts), guards=guards, source_sha256=pins, artifact_sha256=artifact,
        native_input_actual_caller_count=len(native_inputs),actual_caller_inputs=native_inputs,
        source_original_CPU_callbacks=0, source_IR_interpretation=False, native_internal_CPU_trace=False,
        comparison=dict(RAM_bytes=2048, SRAM_bytes=8192, idle_stack='included', AXYP_SP_PC=True,
                        ordered_IO_reads_writes_banks_N163=True),
        executed_original_locations=[dict(physical_bank=b,cpu_address=p,rom_offset=o,visits=v)
            for(b,p,o),v in sorted(visited.items())],
        limits=['Source applies only the exact software procedures and declared IO read inputs, with no hardware timing or pixels/PCM synthesis.',
                'Local typed RAM/SRAM/register/caller fixtures are controlled CPU inputs. Phase16 Native memory provenance does not imply Native internal CPU registers.',
                'Candidate-city report is read-only. Actual candidate selection uses the original list/confirmation procedures in the frozen parent, with their unchanged dependencies.',
                'Reset completions supply explicit alternating PPUSTATUS80/00 edges and compare E000→E066 nonlocal boundaries, never callerRTS. Missing reset and an actual PPUSTATUS0 wait remain separate strict dependencies.',
                'Opening mode1 and rawnonzero boundaries do not establish that any particular other human ruler is still alive.',
                'This matrix does not duplicate the whole877-position parent or all ending victory modes; the new overrides and their actual caller integration are the declared increment.'])
    (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','complete_return_count','reset_boundary_count','strict_prefix_count','source_guard_case_count','failed_count')},ensure_ascii=False))
    return bool(failures)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true')
    p.add_argument('--native-case',type=Path,action='append',default=[],help='Formal frozen Native directory; repeat once per case')
    a=p.parse_args();raise SystemExit(verify(a.rom.read_bytes(),a.quick,a.native_case))
if __name__=='__main__':main()
