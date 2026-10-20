#!/usr/bin/env python3
"""CampaignSession's same-context main/NMI/succession, exact full memory.

The two boundedCPU fixtures are inherited unchanged from phase14, not Native
death observations. ExplicitNMI software arrivals drive the originalCBBF ack;
no source/opcode fallback, manualready, timeradvance or fakeack is installed.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.game_engine import GameEngine
from source.recovered.global_ui_controller import UIRegisters
from source.recovered.service_memory import ServiceMemory
from source.recovered.officers import ROM_SHA256
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def reg(r):return {k:getattr(r,k)for k in REGS}
def verify(rom,out):
    assert digest(rom)==ROM_SHA256
    source_files=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))+['scripts/verify_phase15_succession_integration.py']
    source_pins={p:sha(ROOT/p)for p in source_files}
    inherited=ROOT/'analysis/phase14/cooperation-integration.json';old=json.loads(inherited.read_text());assert old['status']=='passed'
    mother=ROOT/'analysis/phase11/runtime/cold-battle/city-commands'
    ram=Path(str(mother)+'-ram.bin').read_bytes();sram=Path(str(mother)+'-sram.bin').read_bytes()
    artifacts={str(inherited.relative_to(ROOT)):sha(inherited),**{str(Path(str(mother)+suffix).relative_to(ROOT)):sha(str(mother)+suffix)for suffix in('-ram.bin','-sram.bin')}}
    rows=[];failures=[];guards=[];visited=Counter();raw_input_ports={0x2002:0,0x4015:0,0x4016:0,0x4017:0}
    def equal(a,b,r,c):
        rd=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,b.ram))if x!=y];sd=[(i,x,y)for i,(x,y)in enumerate(zip(a.sram,b.sram))if x!=y]
        rg={k:(getattr(c,k),getattr(r,k))for k in REGS if getattr(c,k)!=getattr(r,k)}
        assert not rd and not sd and not rg,dict(RAM=rd[:20],SRAM=sd[:12],registers=rg)
        assert a.io_writes==b.io_writes and a.io_reads==b.io_reads and a.banks==b.banks
        assert a.n163_ram==b.n163_ram and a.n163_address==b.n163_address and a.n163_autoincrement==b.n163_autoincrement
    def original_to(a,b,r,c,result,limit=1500000):
        for n in range(limit):
            if n and c.pc==r.pc and c.sp==r.sp:
                if result['status']=='returned'or(reg(c)==reg(r)and a.ram==b.ram and a.sram==b.sram and a.io_writes==b.io_writes):return n
            assert c.pc>=0x8000,hex(c.pc)
            bank=a.banks[(c.pc-0x8000)//8192];visited[(bank,c.pc,16+bank*8192+(c.pc&8191))]+=1;c.step()
        raise RuntimeError(f'Original budget ${c.pc:04X};source ${r.pc:04X}/SP{r.sp:02X}')
    for inherited_row in old['rows']:
        if inherited_row['group']!='main2_succession_actual_NMI2_resume':continue
        meta=inherited_row['input'];heir=meta['heir'];r=bytearray(ram);s=bytearray(sram)
        for address,value in meta['prepared_bytes'].items():
            address=int(address)
            if address<2048:r[address]=value
            else:s[address-0x6000]=value
        owned=[city for city in range(30)if s[32*city]&7==0]
        for slot in range(20):r[0x664+slot]=255
        for ruler in range(7):
            leader=s[0xF07+8*ruler];s[0x3C0+12*leader+11]=(s[0x3C0+12*leader+11]&252)|(3 if ruler==0 else 2)
        for city in owned:s[32*city+17:32*city+27]=bytes([255]*10)
        if heir:
            offset=16+11*8192+0xAD8;pointer=int.from_bytes(rom[offset:offset+2],'little');candidate=rom[16+11*8192+(pointer&8191)]
            s[32*owned[0]+17]=candidate;s[0x3C0+12*candidate+5]=owned[0];s[0x3C0+12*candidate+11]=(s[0x3C0+12*candidate+11]&252)|2
        r[0xDE:0xE4]=bytes([48,42,43,48,59,60])
        def memory():return ServiceMemory(rom,r,s,(16,10,11,31),read_ports=raw_input_ports,repeat_read_ports=tuple(raw_input_ports))
        a=memory();b=memory();game=GameEngine(b,rom=rom,mapped=True);rr=UIRegisters(**inherited_row['initial_registers']);session=game.readable_campaign(rr)
        co=session.coordinator;assert co.external_callback is None and session.registers is rr
        c=MPU(memory=a)
        for k,v in reg(rr).items():setattr(c,k,v)
        stages=[];nmi_rows=[];instructions=0
        try:
            result=session.main();n=original_to(a,b,rr,c,result);instructions+=n;equal(a,b,rr,c)
            assert result['status']=='dependency'and rr.pc in(0xCA7F,0xCB79)and b[0x6F8B]in(251,252)
            assert len(session.pending)==1 and session.pending[0].kind=='main'
            pending_phase=session.pending[0];actual_call=co.global_ui.pending;paused_pc,paused_sp=rr.pc,rr.sp
            stages.append(dict(kind='main_actual_wait',original_instructions=n,registers=reg(rr),request=b[0x6F8B],pending_depth=len(session.pending),RAM_bytes=2048))
            before=(bytes(b.ram),bytes(b.sram),reg(rr),list(b.io_writes),list(b.banks));again=session.resume()
            assert again['status']=='dependency'and session.pending[0]is pending_phase and co.global_ui.pending is actual_call
            assert before==(bytes(b.ram),bytes(b.sram),reg(rr),list(b.io_writes),list(b.banks));guards.append(dict(heir=heir,name='same_session_without_actual_ack_cannot_advance'))
            for tick in range(1,505):
                before_port=len(b.io_writes);result=session.nmi();c.nmi();n=original_to(a,b,rr,c,result);instructions+=n;equal(a,b,rr,c)
                assert result['status']=='returned'and(rr.pc,rr.sp)==(paused_pc,paused_sp)
                assert len(session.pending)==1 and session.pending[0]is pending_phase and co.global_ui.pending is actual_call
                audio_writes=[x for x in co.calls if x['kind']=='audio_scene_exact']
                assert audio_writes,'New exact audio owner did not participate in actualNMI2'
                nmi_rows.append(dict(NMI=tick,original_instructions=n,returned_registers=reg(rr),request=b[0x6F8B],city_phase=b[0x401],counter=b[0x40C],
                    stack_01EC=b[0x1EC],RAM_bytes=2048,RAM_difference_count=0,SRAM_difference_count=0,register_difference_count=0,
                    ordered_ports_equal=True,bank_equal=True,N163_image_equal=True,port_writes_this_NMI=len(b.io_writes)-before_port))
                if tick in(1,2,9,10,239,240,241,479,480,481)or b[0x6F8B]==1:
                    stages.append(dict(kind='actual_hardware_NMI2_RTI',**nmi_rows[-1]))
                if b[0x6F8B]==1:
                    result=session.resume();n=original_to(a,b,rr,c,result);instructions+=n;equal(a,b,rr,c)
                    assert result['status']=='returned'and rr.pc==0xE066 and rr.sp==inherited_row['initial_registers']['sp']and not session.pending
                    stages.append(dict(kind='same_session_same_generator_main_E066',original_instructions=n,registers=reg(rr),request=b[0x6F8B],RAM_bytes=2048,pending_depth=0))
                    break
            else:raise RuntimeError('505actualNMI software arrivals did not produce originalack')
            assert tick==(481 if heir else 241)
            rows.append(dict(case='heir'if heir else'no-heir',input=meta,inherited_fixture='Frozenphase14 explicitCPUfixture, notNative observeddeath',
                pure_API='GameEngine.readable_campaign(actual_registers).main/nmi/resume',comparison='complete_return',completion_kind='main_E066_boundary',
                initial_registers=inherited_row['initial_registers'],final_registers=reg(rr),source_status=result['status'],original_instructions=instructions,
                NMI_software_arrivals=tick,NMI_parent_case_count=1,nested_NMI_comparisons_not_added_to_case_count=True,
                stages=stages,all_NMI_comparisons=nmi_rows,session_events=list(session.events),same_register_object=True,same_pending_phase=True,same_ServiceCall_and_generator=True,
                manual_ack_writes=0,ack_origin='Actual26CBBD..CBBF',source_original_CPU_callbacks=0,source_IR_interpretation=False,
                RAM_bytes=2048,SRAM_bytes=8192,idle_stack_exclusion=None,final_banks=list(b.banks),ordered_ports_sha256=digest(json.dumps(b.io_writes,separators=(',',':')).encode()),
                ordered_port_write_count=len(b.io_writes),io_reads=len(b.io_reads),N163_register_image_sha256=digest(b.n163_ram),
                pure_source_owner_counts=dict(Counter(x['kind']for x in co.calls)),source_call_count=len(co.calls),
                source_calls_sha256=digest(json.dumps(co.calls,separators=(',',':')).encode()),active_caller_preserved=True,
                all_declared_comparisons_equal=True,changed_SRAM_count=sum(x!=y for x,y in zip(s,b.sram))))
        except Exception as exc:
            failures.append(dict(case='heir'if heir else'no-heir',error=str(exc),source_registers=reg(rr),stages=stages));print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
    assert len(rows)+len(failures)==2
    assert source_pins=={p:sha(ROOT/p)for p in source_files},'Productionsourcechanged;rerun afterfreeze'
    result=dict(schema='phase15-same-campaign-context-succession-integration-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,
        rom_cpu_case_count=len(rows),complete_return_count=len(rows),main_boundary_count=len(rows),actual_caller_return_count=0,strict_prefix_count=0,
        source_guard_case_count=len(guards),failed_count=len(failures),rows=rows,failures=failures,guards=guards,source_original_CPU_callbacks=0,
        source_IR_interpretation=False,native_internal_CPU_trace=False,core_frames_generated=0,nested_NMI_arrivals=sum(x['NMI_software_arrivals']for x in rows),
        comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,CPU_registers='AXYP/SP/PC',free_stack_residue='included; no idle exclusion',ordered_ports_banks_reads=True,N163_image=True),
        source_sha256=source_pins,artifact_sha256=artifacts,executed_original_locations=[dict(physical_bank=b,cpu_address=p,rom_offset=o,visits=n)for(b,p,o),n in sorted(visited.items())],
        limits=['Two longsequences count as two parentCPUcases;722NMI software arrivals andcallees are nested stagecomparisons, notadditionalcases.',
            'Mother/record/status inputs intentionally reproduce the frozenphase14 controlledbattle-return fixtures. They are not naturallyobservedleaderdeath inputs.',
            'Source andoriginal use explicithardwareNMI arrivals withPPUSTATUS/controllerbytes0 andinitial69=0. No hardwarecycle/PCM/Nestopiapixel equivalence is asserted.',
            'No memory is patched afterentry. Only actualCBBF software writesack1; theoriginalsuspendedmain ServiceCall/generator/registerobject thenresumes.',
            'The exactaudioowner eliminates phase14 idle01EC difference within the declaredfull2048RAM comparisons; oldphase14 receipt andscope stayunchanged.'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','nested_NMI_arrivals')}),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase15/succession-integration.json');a=p.parse_args()
    result=verify(a.rom.read_bytes(),a.out);raise SystemExit(bool(result['failures']))
