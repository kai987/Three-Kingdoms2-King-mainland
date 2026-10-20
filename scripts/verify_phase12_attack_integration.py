#!/usr/bin/env python3
"""Probe attack callees and compare the pure scene owner with the original CPU.

The dependency-discovery adapter executes original helpers only in this script.
The integration side exclusively uses GameEngine/SceneCoordinator source, with
no original CPU callback, success stub or synthesized acknowledgement.
"""
import argparse,hashlib,json,sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.attack_scene_controller import AttackSceneController,AttackRegisters,ROM_SHA256
from source.recovered.game_engine import GameEngine
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import ServiceCall

OUT=ROOT/'analysis/phase12/dependencies'
REGS=('a','x','y','p','sp','pc')
RAM_SCOPE=tuple([*range(0x1B4),*range(0x200,0x800)])
INPUT_FIELDS=(0,1,2,3,4,0xA,0xB,0xC,0xD,0x12,0x50,0x5E,0x7A,0x78,0x7C,0x7E,0x81,0x87,0xA4,
              0x300,0x304,0x4BC,0x540,0x541,0x545,0x546,0x547,0x548,0x549,0x560,0x561)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def regdict(r):return {key:getattr(r,key)for key in REGS}
def diffs(actual,source,addresses):return [(a,actual[a],source[a])for a in addresses if actual[a]!=source[a]]

class DiscoveryOracle:
    """Validator-only real helper execution and far-callee boundary capture."""
    def __init__(self,bus,controller,case,out,snapshots):
        self.bus=bus;self.controller=controller;self.case=case;self.out=out
        self.snapshots=snapshots;self.calls=[];self.far_calls=[]
    def __call__(self,call):
        b=self.bus;r=call.registers;event=self.controller.events[-1]
        info=dict(case=self.case,target=call.target,kind=call.kind,return_pc=call.return_pc,
                  entry_banks=list(call.entry_banks),expected_sp=call.expected_sp,
                  call_pc=event['call_pc'],inline_target=event['inline_target'],registers_before=regdict(r),
                  fields_before={f'{a:04X}':b.peek(a)for a in INPUT_FIELDS})
        cpu=MPU(memory=b)
        for key in REGS:setattr(cpu,key,getattr(r,key))
        b.cpu=cpu;far_seen=False
        for n in range(200000):
            if cpu.pc==call.return_pc and cpu.sp==call.expected_sp:break
            if not far_seen and event['inline_target']is not None and cpu.pc==event['inline_target']:
                origin=b.origin(cpu.pc);bank=origin[0]if origin else None
                far=dict(case=self.case,physical_bank=bank,cpu_address=cpu.pc,entry_banks=list(b.banks),
                         call_pc=event['call_pc'],outer_helper=call.target,outer_return_pc=call.return_pc,
                         registers_before=regdict(cpu),fields_before={f'{a:04X}':b.peek(a)for a in INPUT_FIELDS})
                if origin is not None:
                    off=origin[1]+16;raw=self.controller.rom[off:off+16]
                    far.update(rom_offset=off,entry_bytes_hex=raw.hex(' ').upper(),entry_bytes_sha256=sha(raw))
                key=(bank,cpu.pc);saved=self.snapshots[key]
                if saved<3:
                    prefix=self.out/'callee-inputs'/f'bank{bank:02d}-{cpu.pc:04X}-case{self.case:03d}-{saved}'
                    prefix.parent.mkdir(parents=True,exist_ok=True)
                    Path(str(prefix)+'-ram.bin').write_bytes(b.ram);Path(str(prefix)+'-sram.bin').write_bytes(b.sram)
                    provenance=dict(far,fixture_kind='phase11 explicitly prepared legal attack state, not native core callee capture',
                                    RAM_sha256=sha(b.ram),SRAM_sha256=sha(b.sram),actual_original_helper_boundary=True)
                    Path(str(prefix)+'.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n')
                    far['snapshot_prefix']=str(prefix.relative_to(ROOT));self.snapshots[key]+=1
                self.far_calls.append(far);far_seen=True
            b.pc=cpu.pc;b.step_no=n
            if cpu.disassemble[b.peek(cpu.pc)][0]=='???':raise RuntimeError(f'Invalid original helper opcode ${cpu.pc:04X}')
            cpu.step()
        else:raise RuntimeError(f'Discovery helper did not return: ${cpu.pc:04X}')
        for key in REGS:setattr(r,key,getattr(cpu,key))
        info.update(original_CPU_instructions=n,registers_after=regdict(r),banks_after=list(b.banks))
        self.calls.append(info);return {'status':'returned'}

def verify(rom,out,*,catalog_only=False,quick=False,register_contract='exact',base_only=False):
    assert sha(rom)==ROM_SHA256;out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    source_files=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))+[str(Path(__file__).relative_to(ROOT))]
    source_pins_before={p:sha((ROOT/p).read_bytes())for p in source_files}
    old=json.loads((ROOT/'analysis/attack_fsm/state-catalog.json').read_text())
    snapshot=ROOT/'analysis/runtime/phase3/injected-adjacent-attack/scene/attack-scene-menu'
    raw_ram=Path(str(snapshot)+'-ram.bin').read_bytes();raw_sram=Path(str(snapshot)+'-sram.bin').read_bytes()
    def fresh(state,phase,button):
        b=PortBus(rom);b.status_mode='alternating';b.ram[:]=raw_ram;b.sram[:]=raw_sram
        b.banks=[17,14,15,31];b.bank_initialized=[True]*4;b.protect=0x4C
        b.ram[0xDE:0xE4]=bytes([49,46,47,49,46,47]);b.ram[0x1FE:0x200]=bytes([255,1])
        for a,v in {0x540:state,0x541:phase,0x545:0,0x546:0,0x547:0,0x548:0,0x549:1,0x54A:1,0x54B:1,
                    0x560:131,0x561:47,0x564:0,0x565:1,0x568:0,0x569:0,
                    0x7C:0,0x7E:0,0x81:button,0x87:255,0x300:255,0x304:255,0x7A:6,0x78:4}.items():b[a]=v
        b.ram[0x550:0x558]=bytes(8);b.ram[0x580:0x596]=bytes([0]*21+[255])
        b.ram[0x5AC:0x5D8]=bytes(44);b.ram[0x522:0x526]=bytes([188,2,44,1]);return b
    def clone(b):
        c=PortBus(rom);c.status_mode=b.status_mode;c.ram[:]=b.ram;c.sram[:]=b.sram
        c.banks=b.banks[:];c.bank_initialized=[True]*4;c.protect=b.protect;c.record_ports=True;return c
    def original(b,entry,prefix=None):
        r=AttackRegisters();cpu=MPU(memory=b,pc=entry)
        for key in('a','x','y','p','sp'):setattr(cpu,key,getattr(r,key))
        b.cpu=cpu;b.record_ports=True
        for n in range(500000):
            if prefix is None:
                if cpu.pc==0x200 and cpu.sp==255:break
            else:
                m,regs=prefix;sp=cpu.sp
                stack_matches=all(b.peek(0x100+((sp+i)&255))==m[0x100+((sp+i)&255)]for i in(1,2))
                if cpu.pc==regs.pc and sp==regs.sp and b.banks==m.banks and stack_matches and len(b.ports)>=len(m.io_writes):break
            b.pc=cpu.pc;b.step_no=n;cpu.step()
        else:raise RuntimeError(f'Original attack budget ${cpu.pc:04X}')
        return cpu,n
    rows=[];discovery=[];far=[];snapshots=Counter();failures=[];counts=Counter();groups=Counter();guard_rows=[]
    cases=[('legal_phase_buttons',s['state'],h['substate'],button,entry,None)for s in old['states']for h in s['handlers']for button in(0,1,2)for entry in(0xA000,0xA069)]
    if not base_only:
        cases.extend(('direction_byte_inputs',s['state'],h['substate'],button,entry,None)for s in old['states']for h in s['handlers']for button in(4,8,16,32,64,128,255)for entry in(0xA000,0xA069))
        cases.extend(('AAEA_scan_completion',3,1,0,entry,scan)for scan in(4,5)for entry in(0xA000,0xA069))
    if quick:cases=[c for c in cases if c[3]==0]
    for case,(group,state,phase,button,entry,scan)in enumerate(cases):
        failures_before=len(failures)
        meta=dict(case=case,input_group=group,main_state=state,phase=phase,buttons=button,entry=entry,scan_cursor_override=scan)
        # Discover the complete original callee chain, using the already
        # frozen direct controller only as an explicitly oracle-backed probe.
        b=fresh(state,phase,button)
        if scan is not None:b[0x548]=scan
        c=clone(b);ctrl=AttackSceneController(c,rom)
        oracle=DiscoveryOracle(c,ctrl,case,out,snapshots);ctrl.services=oracle
        try:
            result=ctrl.run_entry(entry,registers=AttackRegisters());assert result['status']=='returned',result['status']
            cpu,n=original(b,entry)
            assert not diffs(b.ram,c.ram,range(2048))and b.sram==c.sram
            assert regdict(cpu)==regdict(ctrl.registers)and b.ports==c.ports and b.banks==c.banks
            counts['original_discovery_complete']+=1;groups['discovery_'+group]+=1;discovery.extend(oracle.calls);far.extend(oracle.far_calls)
        except Exception as exc:
            failures.append(dict(meta,stage='original_dependency_discovery',error=str(exc)));continue
        if catalog_only:continue
        b=fresh(state,phase,button)
        if scan is not None:b[0x548]=scan
        m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks),read_ports={0x2002:[128,0]*20000,0x4015:0,0x4016:0,0x4017:0},repeat_read_ports=(0x4015,0x4016,0x4017))
        game=GameEngine(m,rom=rom,mapped=True);coordinator=game.readable_scene_rules();r=AttackRegisters()
        try:
            source_call=None
            if entry==0xA000:result=game.tick_readable_scene(r,scene=4)
            else:
                source_call=ServiceCall(entry,0x200,'declared_existing_caller',r,m,tuple(b.banks),255)
                result=coordinator(source_call)
            assert result['status']in('dependency','returned'),result['status']
            prefix=result['status']=='dependency';cpu,n=original(b,entry,(m,r)if prefix else None)
            ram_diff=diffs(b.ram,m.ram,RAM_SCOPE);sram_diff=diffs(b.sram,m.sram,range(8192))
            register_diff=[(k,getattr(cpu,k),getattr(r,k))for k in REGS if getattr(cpu,k)!=getattr(r,k)]
            active_register_diff=[x for x in register_diff if register_contract=='exact'or x[0]in('sp','pc')]
            port_same=b.ports==m.io_writes;bank_same=b.banks==m.banks
            row=dict(meta,comparison='strict_prefix'if prefix else'complete_return',source_status=result['status'],
                     original_instructions=n,boundary_registers=regdict(r),original_registers=regdict(cpu),
                     boundary_banks=list(m.banks),source_calls=coordinator.calls,
                     register_differences=register_diff,RAM_differences=ram_diff[:30],SRAM_differences=sram_diff[:12],
                     port_sequences_equal=port_same,port_write_count=len(m.io_writes),banks_equal=bank_same,
                     ordered_ports_sha256=sha(json.dumps(m.io_writes,separators=(',',':')).encode()),
                     full_SRAM_equal=not sram_diff,declared_RAM_equal=not ram_diff,
                     source_original_CPU_callbacks=0)
            if prefix:
                missing=[]
                for owner,kind in coordinator._owners.values():
                    pending=getattr(owner,'pending',None)
                    if isinstance(pending,ServiceCall):missing.append(dict(kind=kind,target=pending.target,return_pc=pending.return_pc,
                                            entry_banks=list(pending.entry_banks),expected_sp=pending.expected_sp))
                row['pending_calls']=missing
                # Snapshot at the real first unresolved source edge, with no
                # borrowed original helper or automatically-cleared queue.
                guard_before=(bytes(m.ram),bytes(m.sram),list(m.io_writes),list(m.banks),regdict(r))
                second=game.resume_readable_scene(scene=4)if entry==0xA000 else coordinator(source_call)
                assert second['status']=='dependency'and guard_before==(bytes(m.ram),bytes(m.sram),list(m.io_writes),list(m.banks),regdict(r))
                guard_rows.append(dict(case=case,check='same_scene_pending_resumes_without_fake_completion'))
            if ram_diff or sram_diff or active_register_diff or not port_same or not bank_same:
                row['comparison_status']='failed';failures.append(dict(meta,stage='pure_source_CPU_comparison',
                    RAM=ram_diff[:12],SRAM=sram_diff[:8],registers=active_register_diff,ports_equal=port_same,banks_equal=bank_same))
            else:
                row['comparison_status']='passed';counts['pure_source_'+row['comparison']]+=1;groups[row['comparison']+'_'+group]+=1
            rows.append(row)
        except Exception as exc:
            failures.append(dict(meta,stage='pure_source_call',error=str(exc)))
        if len(failures)>failures_before and len(failures)<=8:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
    # Pure source rejects an unrelated/unknown callee; never execute its bytes.
    if not catalog_only:
        b=fresh(0,0,0);m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));g=GameEngine(m,rom=rom,mapped=True);r=AttackRegisters(pc=0x8123)
        before=(bytes(m.ram),bytes(m.sram),list(m.io_writes),list(m.banks),regdict(r))
        result=g.readable_scene_rules()(ServiceCall(0x8123,0x200,'unknown',r,m,tuple(b.banks),255))
        assert result['status']=='dependency'and r.pc==0x8123 and r.sp==253
        assert before==(bytes(m.ram),bytes(m.sram),list(m.io_writes),list(m.banks),regdict(r))
        guard_rows.append(dict(check='unknown_callee_has_no_success_stub'))
    fixed_counts=Counter(f'{x["target"]:04X}'for x in discovery)
    far_counts=Counter(f'b{x["physical_bank"]}:{x["cpu_address"]:04X}'for x in far)
    e=json.loads((ROOT/'analysis/phase11/attack/evidence.json').read_text())
    observed_sites={row['call_pc']for row in far};static_far=[]
    for site in e['far_call_sites']:
        pc=site['call_pc'];bank=14 if pc<0xC000 else 15;off=16+bank*8192+(pc&0x1FFF)-2
        raw=rom[off:off+7]
        assert raw[0]==0xA0 and raw[2:5]==bytes((0x20,0x07,0xEE))and int.from_bytes(raw[5:7],'little')==site['target']
        static_far.append(dict(site,caller_physical_bank=bank,logical_selector=raw[1],callee_physical_bank=raw[1]&31,
                               callee_pair=[raw[1]&31,(raw[1]&31)+1],inline_word_PC=pc+3,rom_offset=off,
                               raw_hex=raw.hex(' ').upper(),sha256=sha(raw),dynamically_observed=pc in observed_sites))
    files=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))+[str(Path(__file__).relative_to(ROOT))]
    source_pins_after={p:sha((ROOT/p).read_bytes())for p in files}
    drift=[p for p in sorted(source_pins_before.keys()|source_pins_after.keys())if source_pins_before.get(p)!=source_pins_after.get(p)]
    if drift:failures.append(dict(stage='source_dependency_hash_changed_during_run',paths=drift))
    catalog=dict(schema='phase12-attack-dependency-discovery-v1',status='passed'if counts['original_discovery_complete']==len(cases)else'failed',
        rom_sha256=ROM_SHA256,quick=quick,base_only=base_only,legal_main_phase_button_combinations=58*(1 if quick else 3),actual_entry_executions=len(cases),group_counts=dict(groups),
        validated_original_discovery_executions=counts['original_discovery_complete'],
        discovery_original_helper_callback_count=len(discovery),fixed_and_call_framework_counts=dict(fixed_counts),far_callee_counts=dict(far_counts),
        static_fixed_targets=e['external_fixed_targets'],static_far_call_sites=static_far,
        unobserved_far_call_sites=[site for site in static_far if not site['dynamically_observed']],
        original_helper_calls=discovery,original_far_callee_boundaries=far,
        static_targets_not_dynamically_called=[x for x in e['external_fixed_targets']if f'{x:04X}'not in fixed_counts],
        fixture_provenance=dict(snapshot=str(snapshot.relative_to(ROOT)),RAM_sha256=sha(raw_ram),SRAM_sha256=sha(raw_sram),
          prepared_fields='same bounded phase11 fixture, plusNMIscene4; every58legalphase x buttons0/1/2; direction bytes4/8/16/32/64/128/255 and separate0548=4/5; actualexisting0200caller frame',
          ordinary_snapshot_inherited_adjacent_enemy_preparation=True,hardware_inputs='explicit alternating80/00PPUSTATUS; explicit0APU/pads'),
        source_discovery_only_oracle_adapter=True,pure_integration_original_CPU_callbacks=0,original_ROM_modified=False,
        limits=['Base58legalphase x3buttons and twoentries are separate from7direction-byte groups and four explicit scancompletion inputs; all are boundedfixtures, not everybranch or naturalreachability.',
                'Original helper callbacks are dependency discovery only, never pure production completion.',
                'Farcallees are captured at actual banked-entryPC after original EE07 mapping; mappeddata reads are not executablecallee entries.',
                'Static fixed/farcall sites are copied from frozen independently byte-verified phase11 evidence; unobserved ones remain visible.'])
    (out/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    receipt=dict(schema='phase12-attack-pure-integration-v1',status='failed'if failures else'catalog_only'if catalog_only else'passed',
        rom_sha256=ROM_SHA256,quick=quick,base_only=base_only,counts=dict(counts),group_counts=dict(groups),actual_ROM_CPU_comparison_count=counts['pure_source_complete_return']+counts['pure_source_strict_prefix'],
        rom_cpu_case_count=counts['pure_source_complete_return']+counts['pure_source_strict_prefix'],
        attempted_ROM_CPU_comparison_count=len(rows),
        complete_return_count=counts['pure_source_complete_return'],strict_prefix_count=counts['pure_source_strict_prefix'],
        source_guard_count=len(guard_rows),source_guards=guard_rows,failed_count=len(failures),failures=failures,rows=rows,
        case_count=counts['pure_source_complete_return']+counts['pure_source_strict_prefix']+len(guard_rows),
        declared_RAM_addresses=RAM_SCOPE,compared_RAM_bytes=len(RAM_SCOPE),compared_SRAM_bytes=8192,active_caller_PC_SP_compared=True,
        register_contract=register_contract,semantic_AXYP_exclusion_explicit=register_contract!='exact',ordered_ports_and_final_banks_compared=True,
        source_original_CPU_callbacks=0,source_IR_interpretation=False,source_cpu_frame_or_ack_synthesis=False,
        discovery_original_helper_callbacks=len(discovery),catalog_sha256=sha((out/'catalog.json').read_bytes()),
        source_sha256=source_pins_after,source_dependency_hashes_stable_during_run=not drift,
        limits=['FullRAM except inactive01B4..01FF stackresidue; all8192SRAM and actual PC/SP,orderedports,banks.',
                'SP/PC and alldeclaredmemory remain required even with --register-contract semantic; AXYP diffs are then reported, not asserted equivalent.',
                'Existing Text/animation semantics are not silently promoted to exactAXYP. Default exact mode surfaces those gaps.',
                'Nativecore pixels/PCM/NMI timing not checked by this CPUfixture.'])
    (out/'source-integration.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:receipt[k]for k in('status','counts','group_counts','actual_ROM_CPU_comparison_count','source_guard_count','failed_count')},ensure_ascii=False))
    print(json.dumps(dict(discovery_helper_callbacks=len(discovery),far_callees=dict(far_counts)),ensure_ascii=False))
    if failures:raise SystemExit(1)
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    p.add_argument('--out',type=Path,default=OUT);p.add_argument('--catalog-only',action='store_true');p.add_argument('--quick',action='store_true')
    p.add_argument('--base-only',action='store_true',help='Retain original348-entry scope without extra direction/scan inputs')
    p.add_argument('--register-contract',choices=('exact','semantic'),default='exact');a=p.parse_args()
    verify(a.rom.read_bytes(),a.out,catalog_only=a.catalog_only,quick=a.quick,register_contract=a.register_contract,base_only=a.base_only)
