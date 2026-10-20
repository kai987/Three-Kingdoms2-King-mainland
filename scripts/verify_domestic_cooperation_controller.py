#!/usr/bin/env python3
"""Actual original6502 differential verification of readable domestic AI.

The independent CPU is confined to this validator. Complete calls and strict
missing-service/cooperative-wait prefixes are separate. No production opcode,
IR, fake acknowledgement or native CPU trace is inferred from these fixtures.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys,random
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.domestic_cooperation_controller import DomesticCooperationController,UIRegisters,ROM_SHA256
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.battle_nmi_services import ServiceCall,ServiceWait
from source.recovered.service_memory import ServiceMemory
OUT=ROOT/'analysis/phase14/domestic'
PARENT=ROOT/'analysis/phase11/runtime/cold-battle/picked-ruler'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class OriginalFixedHelpers:
    """Validator-only original fixed callee execution, counted separately."""
    def __init__(self):self.calls=Counter();self.steps=0
    def __call__(self,call):
        if call.target not in(0xF266,0xE88A,0xE89A,0xE8AA):return {'status':'dependency'}
        c=MPU(memory=call.memory)
        for k in('a','x','y','p','sp','pc'):setattr(c,k,getattr(call.registers,k))
        self.calls[call.target]+=1
        for n in range(1000):
            if n and c.pc==call.return_pc and c.sp==call.expected_sp:break
            c.step()
        else:raise RuntimeError(('fixed helper exceeded',hex(c.pc)))
        self.steps+=n
        for k in('a','x','y','p','sp','pc'):setattr(call.registers,k,getattr(c,k))
        return {'status':'returned'}
def memory(rom,prep=None,carry=None):
    ram=Path(str(PARENT)+'-ram.bin').read_bytes();sram=Path(str(PARENT)+'-sram.bin').read_bytes()
    m=ServiceMemory(rom,ram,sram,(16,10,11,31))
    m[0xE1:0xE4]=bytes([48,42,43]);m[0x1FE:0x200]=bytes([0x87,0xE1])
    for a,v in(prep or{}).items():m[int(a)]=v
    if carry:
        m.ram[:]=carry['RAM'];m.sram[:]=carry['SRAM'];m.banks[:]=carry['banks'];m[0x1FE:0x200]=bytes([0x87,0xE1])
    m.io_writes=[];return m

def verify(rom,quick=False):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
    rows=[];failures=[];guards=[];visited=Counter();external=Counter();counts=Counter();rng=random.Random(0x14A00F)
    def compare(entry=0xA000,prep=None,registers=None,mode='pure_source',tag='',carry=None):
        a=memory(rom,prep,carry);b=memory(rom,prep,carry)
        r=UIRegisters(a=17,x=23,y=31,p=32,sp=253,pc=entry)
        for k,v in(registers or{}).items():setattr(r,k,v)
        initial=vars(r).copy();helper=OriginalFixedHelpers()if mode=='original_fixed_helpers'else SceneSharedServices(b,rom)if mode=='pure_source'else None
        source=DomesticCooperationController(b,rom,helper);c=MPU(memory=a)
        for k,v in initial.items():setattr(c,k,v)
        try:
            result=source.run_entry(entry,registers=r)
            for n in range(1000000):
                if n and c.pc==r.pc and c.sp==r.sp and a.banks==b.banks and (result['status']!='waiting' or all(getattr(c,k)==getattr(r,k)for k in('a','x','y','p'))):break
                bank=a.banks[(c.pc-0x8000)//8192]if c.pc>=0x8000 else None
                if bank is not None:visited[(bank,c.pc,16+bank*8192+(c.pc&8191))]+=1
                c.step()
            else:raise RuntimeError(f'Original budget at{c.pc:04X}; source{r.pc:04X}/SP{r.sp:02X}')
            scope=list(range(2048))
            rd=[(i,a.ram[i],b.ram[i])for i in scope if a.ram[i]!=b.ram[i]]
            rg=[(k,getattr(c,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(c,k)!=getattr(r,k)]
            sd=[(i,a.sram[i],b.sram[i])for i in range(8192)if a.sram[i]!=b.sram[i]]
            assert not rd and not rg and not sd,dict(RAM=rd[:12],registers=rg,SRAM=sd[:12])
            assert a.io_writes==b.io_writes and a.io_reads==b.io_reads and a.banks==b.banks,dict(ports=(a.io_writes,b.io_writes),banks=(a.banks,b.banks))
            comparison='complete_return'if result['status']=='returned'else'strict_prefix'
            calls=sum(helper.calls.values())if isinstance(helper,OriginalFixedHelpers)else 0
            external.update(helper.calls if isinstance(helper,OriginalFixedHelpers)else{})
            counts[f'{mode}/{comparison}']+=1
            rows.append(dict(entry=entry,tag=tag,mode=mode,comparison=comparison,source_status=result['status'],
                prepared_bytes=prep or{},input_registers=initial,final_registers=vars(r).copy(),original_instructions=n,
                control_blocks=result['control_blocks'],original_CPU_helper_calls=calls,source_external_calls=len(result['events']),
                all_RAM_byte_count=len(scope),all_SRAM_byte_count=8192,ordered_ports=len(b.io_writes),final_banks=list(b.banks),
                before=source._before,after=source.fields(),SRAM_changes=sum(x!=y for x,y in zip(a.sram,memory(rom,prep,carry).sram)),
                changed_SRAM_bytes=[dict(address=0x6000+i,old=old,new=new)for i,(old,new)in enumerate(zip(memory(rom,prep,carry).sram,a.sram))if old!=new],
                waiting_field=result['pending'].address if isinstance(result['pending'],ServiceWait)else None,
                waiting_value=result['pending'].value if isinstance(result['pending'],ServiceWait)else None))
            return dict(RAM=bytes(a.ram),SRAM=bytes(a.sram),banks=list(a.banks))
        except Exception as exc:
            failures.append(dict(entry=entry,tag=tag,mode=mode,preparation=prep or{},error=str(exc),source_PC=r.pc))
            if len(failures)<=15:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
            return None
    # Main2/A000 true caller context;7rulers x3difficulty x3budgets x2ticks.
    for ruler in range(7):
        for difficulty in range(3):
            for budget in ((10,)if quick else(5,10,30)):
                index=(ruler*3+difficulty)*3+budget
                prep={0x6F03:ruler,0x6F02:difficulty,0x6F8B:0,0x6F5B:0,0x6F5D:budget,0x6F62:0,
                    0xEE:7+8*ruler,0xEF:0x6F,0x52:(index*13)&255,0x54:(index*23)&255,0x55:(index*43)&255}
                carry=compare(prep=prep,tag=f'ruler{ruler}/difficulty{difficulty}/budget{budget}/initialize')
                if carry:compare(carry=carry,tag=f'ruler{ruler}/difficulty{difficulty}/budget{budget}/decision')
    # Actual cooperation request1 is another entry branch, not ordinary
    # strategy phase1. Empty surviving battle-unit arrays are explicitCPU
    # fixtures; no battle/native completion is claimed from them.
    for i in range(2 if quick else 14):
        ruler=i%7;owned=[city for city in range(30)if memory(rom)[0x6000+32*city]&7==ruler]
        prep={0x6F03:ruler,0x6F02:i%3,0x6F8B:1,0x6F8C:1,0x6F8D:0,0x6F5B:1,0x6F5D:5,0x6F62:0,
            0xEE:7+8*ruler,0xEF:0x6F,0x38:owned[0],0x3A:owned[0],0x44:0,
            0x507:ruler,0x508:ruler,0x50E:owned[0],0x50F:3}
        for slot in range(20):prep[0x664+slot]=255
        compare(prep=prep,tag=f'battle-return-branch/empty-arrays{i}')
    # Every strategic branch is forced by legitimate immutable-weight inputs;
    # the sampling algorithm and all subsequent decisions remain original.
    for strategy,weights in enumerate(((16,0,0),(0,16,0),(0,0,16))):
        for i in range(3 if quick else 32):
            ruler=i%7;prep={0x6F03:ruler,0x6F02:i%3,0x6F8B:0,0x6F5B:1,0x6F5D:(5,10,30,100)[i%4],0x6F62:0,
                0xEE:7+8*ruler,0xEF:0x6F,0x52:i*7&255,0x54:i*13&255,0x55:i*19&255,
                0x6F5F:weights[0],0x6F60:weights[1],0x6F61:weights[2]}
            compare(prep=prep,tag=f'strategy{strategy}/fixture{i}')
    baseline=memory(rom)
    # Legitimate campaign-domain variations expose seasonal/resource and
    # officer/equipment paths which the all9999 super-ROM parent suppresses.
    for strategy in range(3):
        for i in range(2 if quick else 84):
            ruler=i%7;weights=[0,0,0];weights[strategy]=16
            prep={0x6F03:ruler,0x6F02:(i//7)%3,0x6F00:90,0x6F01:i%12,
                0x6F8B:0,0x6F5B:1,0x6F5D:(5,30,100,255)[i%4],0x6F62:0,
                0xEE:7+8*ruler,0xEF:0x6F,0x52:i*17&255,0x54:i*29&255,0x55:i*37&255,
                0x6F5F:weights[0],0x6F60:weights[1],0x6F61:weights[2]}
            values=(0,9,49,100,300,9999)
            for city in range(30):
                addr=0x6000+32*city
                for off in(2,4,6,8,12,14):
                    value=values[(i+city+off)%len(values)]
                    prep[addr+off]=value&255;prep[addr+off+1]=value>>8
                prep[addr+10]=(0,50,98,99)[(i+city)%4]
                prep[addr+11]=(0,50,70,99)[(i+city)%4]
                prep[addr+16]=(0,1,20,99)[(i+city)%4]
            for officer in range(237):
                addr=0x63C0+12*officer
                for off in(0,1,2,4):prep[addr+off]=(20+(i+officer*7+off*11)%80)
                if baseline[addr+3]!=100:prep[addr+3]=(10+(i+officer*13)%90)
                prep[addr+10]=(0,1,7,16,24,31)[(i+officer)%6]
            compare(prep=prep,tag=f'domain-strategy{strategy}/resources{i}')
    for request in (0x80,0xFB,0xFC,0xFD,0xFE,0xFF):
        compare(prep={0x6F8B:request},tag=f'signed-request{request}')
    # Missing service prefixes preserve actualF266 caller frame/flags.
    for i in range(3 if quick else 21):
        ruler=i%7;compare(prep={0x6F03:ruler,0x6F02:i%3,0x6F8B:0,0x6F5B:i%3,0xEE:7+8*ruler,0xEF:0x6F},mode='missing_service',tag=f'missing-fixed{i}')
    # Local exact field/cap/selection procedures retain arbitrary byte edges.
    catalog=json.loads((OUT/'static-catalog.json').read_text())
    local_entries=[0xC66F,0xC9A5,0xD105,0xD304,0xD0E1,0xD4CB,0xD583,0xCF3F,0xCF7C,0xD00C]
    for entry in local_entries:
        for i in range(3 if quick else 64):
            ruler=i%7;city=i%30;officer=i%237;prep={0x6F03:ruler,0x36:city,0x37:ruler,0x6F5E:city,
                0xEE:7+8*ruler,0xEF:0x6F,0x20:(0x63C0+12*officer)&255,0x21:(0x63C0+12*officer)>>8,
                0x3C:officer,0x3D:officer,0x40:ruler,0x41:(ruler+1)%7,0x42:ruler}
            if entry==0xD583:
                for j in range(128):prep[0x580+j]=rng.randrange(256)
            compare(entry,prep,registers={'a':officer if entry==0xC66F else city,'x':city,'y':i&255},tag=f'local{entry:04X}/{i}')
    # The complete death/succession body is now local source, not a hook.
    # These are controlled CPU inputs; actualFB/FC writes and all city/leader
    # changes are generated by the untouched original body on the oracle side.
    base=memory(rom)
    for ruler in range(7):
        owned=[city for city in range(30)if base[0x6000+32*city]&7==ruler]
        assert owned
        for heir in (False,True):
            prep={0x6F03:ruler,0x6F02:1,0x6F5B:2,0x6F5D:5,0x6F62:0,
                0xEE:7+8*ruler,0xEF:0x6F,0x6F0A+8*ruler:3}
            for j in range(7):
                leader=base[0x6F07+8*j]
                prep[0x63C0+12*leader+11]=(base[0x63C0+12*leader+11]&252)|(3 if j==ruler else 2)
            for city in owned:
                for j in range(10):prep[0x6000+32*city+17+j]=255
            if heir:
                off=16+11*8192+0xAD8+2*ruler
                candidate_pointer=int.from_bytes(rom[off:off+2],'little')
                candidate=rom[16+11*8192+(candidate_pointer&8191)]
                assert candidate<237
                prep[0x6000+32*owned[0]+17]=candidate
                prep[0x63C0+12*candidate+5]=owned[0]
                prep[0x63C0+12*candidate+11]=(base[0x63C0+12*candidate+11]&252)|2
            compare(0xCA19,prep,tag=f'complete-succession/ruler{ruler}/heir{heir}')
    # Literal cooperative wait entry snapshots; noack is supplied. Prefixes
    # stop after genuine LDA/CMP/BNE reaches its same waitingPC.
    for entry in (0xCA7F,0xCB79):
        for value in (0,1,0xFB,0xFC,255):compare(entry,{0x6F8B:value},tag=f'cooperative-wait{value}')
    # Source-only rejection/ownership/strict callback gates.
    for label,fn in [
        ('actual_registers_required',lambda:DomesticCooperationController(memory(rom),rom).run_entry()),
        ('wrong_physical_pair',lambda:DomesticCooperationController(ServiceMemory(rom,banks=(16,12,13,31)),rom).run_entry(registers=UIRegisters())),
        ('D_flag_rejected',lambda:DomesticCooperationController(memory(rom),rom).run_entry(registers=UIRegisters(p=40))),
        ('invalid_entry',lambda:DomesticCooperationController(memory(rom),rom).run_entry(0xA003,registers=UIRegisters())),
    ]:
        try:fn();raise AssertionError('Guard failed to reject')
        except ValueError:guards.append(dict(name=label,status='passed'))
    for status in(None,'waiting','error','blocked','dependency'):
        m=memory(rom,{0x6F8B:0,0x6F5B:0,0x6F03:2,0xEE:23,0xEF:0x6F})
        def fake(call):
            call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
            return None if status is None else {'status':status}
        s=DomesticCooperationController(m,rom,fake);out=s.run_entry(registers=UIRegisters())
        assert out['status']=='dependency'and s.pending is not None;guards.append(dict(name=f'explicit_return_required/{status}',status='passed'))
    # Retry a waiting loop cannot mutate request; an external write1 is needed.
    for entry in (0xCA7F,0xCB79):
        m=memory(rom,{0x6F8B:251});s=DomesticCooperationController(m,rom);r=UIRegisters()
        out=s.run_entry(entry,registers=r);before=(bytes(m.ram),bytes(m.sram),vars(r).copy())
        assert out['status']=='waiting'and s.resume()['status']=='waiting'and m[0x6F8B]==251
        assert before==(bytes(m.ram),bytes(m.sram),vars(r).copy())
        m[0x6F8B]=1;assert s.resume()['status']=='returned';guards.append(dict(name=f'genuine_external_ack/{entry:04X}',status='passed'))
    # Full RAM with originalfixedcallbacks validates protocol independently.
    for i in range(3 if quick else 21):
        ruler=i%7;compare(prep={0x6F03:ruler,0x6F02:i%3,0x6F8B:0,0x6F5B:i%2,0x6F5D:10,0x6F62:0,
            0xEE:7+8*ruler,0xEF:0x6F,0x52:i*13&255,0x54:i*23&255,0x55:i*43&255},
            mode='original_fixed_helpers',tag=f'protocol-oracle{i}')
    complete=sum(v for k,v in counts.items()if k.endswith('/complete_return'));prefix=len(rows)-complete
    pins={str(p.relative_to(ROOT)):sha(p)for p in [Path(__file__),ROOT/'scripts/analyze_domestic_cooperation_controller.py',
         ROOT/'source/recovered/domestic_cooperation_controller.py',ROOT/'source/recovered/global_ui_controller.py',
         ROOT/'source/recovered/scene_shared_services.py',ROOT/'source/recovered/controller_helpers.py',ROOT/'source/recovered/battle_nmi_services.py',
         ROOT/'source/recovered/service_memory.py',ROOT/'source/recovered/mapped_memory.py',Path(str(PARENT)+'-ram.bin'),Path(str(PARENT)+'-sram.bin'),
         ROOT/'analysis/phase14/domestic/static-catalog.json']}
    receipt=dict(schema='phase14-domestic-actual-CPU-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,quick=quick,
        rom_cpu_case_count=len(rows),source_guard_case_count=len(guards),case_count=len(rows)+len(guards),failed_count=len(failures),
        complete_return_count=complete,strict_prefix_count=prefix,counts=dict(counts),cases=rows,guards=guards,failures=failures,
        original_fixed_helper_calls=sum(external.values()),original_fixed_helper_calls_by_entry={f'{k:04X}':v for k,v in external.items()},
        comparison_scope=dict(RAM='all2048 bytes',SRAM='all8192 bytes',registers='A X Y P SP PC',ports='ordered writes/reads',mapper='all4physicalbanks'),
        production_original_CPU_callbacks=0,production_IR_interpretation=False,pure_source_original_CPU_callbacks=0,
        dynamic_instruction_positions=len(visited),source_and_validator_sha256=pins,original_ROM_modified=False,
        native_internal_CPU_trace=False,preparation='CPU-only explicit domain fixtures on pinned read-only natural parentRAM/SRAM; not nativeinputtrace')
    (OUT/'validation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    from inspect_game_data import OPS,SIZES
    executed=[]
    for (bank,pc,file),count in sorted(visited.items()):
        op,mode=OPS[rom[file]];size=SIZES[mode];executed.append(dict(bank=bank,cpu=pc,rom_offset=file,raw_hex=rom[file:file+size].hex(' ').upper(),executions=count))
    (OUT/'executed-instructions.json').write_text(json.dumps(dict(rom_sha256=ROM_SHA256,positions=executed),indent=2)+'\n')
    print(json.dumps({k:receipt[k]for k in('status','rom_cpu_case_count','source_guard_case_count','complete_return_count','strict_prefix_count','failed_count','dynamic_instruction_positions')},ensure_ascii=False))
    return not failures
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args()
    if not verify(a.rom.read_bytes(),a.quick):raise SystemExit(1)
