#!/usr/bin/env python3
"""Original CPU vs the actual AI-turn header/OAM producer, no source fallback."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.city_cooperation_ui_services import CityCooperationUIServices,CityCooperationData,ROM_SHA256
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.service_memory import ServiceMemory
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reg(r):return {k:getattr(r,k)for k in REGS}
def verify(rom,out,quick=False):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;out.mkdir(parents=True,exist_ok=True)
    parent=ROOT/'analysis/phase11/runtime/cold-battle/city-commands'
    ram=Path(str(parent)+'-ram.bin').read_bytes();sram=Path(str(parent)+'-sram.bin').read_bytes()
    data=CityCooperationData.from_rom(rom);counts=Counter();rows=[];failures=[];guards=[];visited=Counter()
    def compare(group,entry,caption,badge,counter,oam,*,p=32,sp=253):
        a=ServiceMemory(rom,ram,sram,(19,29,30,31));b=ServiceMemory(rom,ram,sram,(19,29,30,31))
        for m in(a,b):
            m[0xA]=caption;m[0xB]=badge;m[0xC]=counter;m[0x7C]=oam
            m[0x100+((sp+1)&255)]=0x67;m[0x100+((sp+2)&255)]=0x24;m.io_writes=[]
        r=NMIRegisters(a=17,x=31,y=63,p=p,sp=sp,pc=entry);initial=reg(r);c=MPU(memory=a)
        for k,v in initial.items():setattr(c,k,v)
        model=CityCooperationUIServices(b,data)
        try:
            result=model.run_entry(entry,r);assert result['status']=='returned'
            for n in range(20000):
                if n and c.pc==r.pc and c.sp==r.sp:break
                bank=a.banks[(c.pc-0x8000)//8192];visited[(bank,c.pc,16+bank*8192+(c.pc&8191))]+=1;c.step()
            else:raise RuntimeError(f'Original budget ${c.pc:04X}')
            rd=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,b.ram))if x!=y]
            sd=[(i,x,y)for i,(x,y)in enumerate(zip(a.sram,b.sram))if x!=y]
            rg={k:(getattr(c,k),getattr(r,k))for k in REGS if getattr(c,k)!=getattr(r,k)}
            assert not rd and not sd and not rg,dict(RAM=rd[:15],SRAM=sd[:8],registers=rg)
            assert a.io_writes==b.io_writes and a.banks==b.banks and a.io_reads==b.io_reads
            counts[group]+=1;rows.append(dict(group=group,entry=entry,caption=caption,raw_badge_ID=badge,counter=counter,OAM_before=oam,
                initial_registers=initial,final_registers=reg(r),original_instructions=n,comparison='complete_return',
                completion_kind='actual_caller_RTS',source_original_CPU_callbacks=0,final_banks=list(b.banks),port_writes=list(b.io_writes)))
        except Exception as exc:
            failures.append(dict(group=group,entry=entry,caption=caption,badge=badge,counter=counter,oam=oam,p=p,sp=sp,error=str(exc)))
            if len(failures)<6:print(json.dumps(failures[-1]),flush=True)
    for caption in(0,1,2,3,255):
        for badge in((0,131,255)if quick else(0,1,5,131,236,237,254,255)):
            for counter in(0,1,255):
                for p in(32,225):compare('caption_badge_counter_and_flags',0xA042,caption,badge,counter,0,p=p)
    for badge in(range(0,256,17)if quick else range(256)):
        for p in(32,225):compare('all_raw_badge_records',0xAB38,0,badge,0,252,p=p)
    for sp in((0,1,127,253,255)if quick else range(256)):
        compare('all_existing_caller_stack_positions',0xAA37,sp%4,131,0,0,sp=sp,p=(sp|32)&~8)
    for oam in(range(0,256,17)if quick else range(256)):
        compare('all_byte_OAM_cursors',0xAB38,0,131,0,oam)
    for name,caption,p in(('caption4',4,32),('caption254',254,32),('decimal',0,40),('missing_actual_registers',0,32)):
        m=ServiceMemory(rom,ram,sram,(19,29,30,31));m[0xA]=caption;m[0xC]=0;r=NMIRegisters(p=p);before=(bytes(m.ram),bytes(m.sram),reg(r))
        try:CityCooperationUIServices(m,data).run_entry(registers=None if name=='missing_actual_registers'else r)
        except ValueError:pass
        else:raise AssertionError('Missing source guard '+name)
        assert before==(bytes(m.ram),bytes(m.sram),reg(r));guards.append(name)
    m=ServiceMemory(rom,ram,sram,(19,27,28,31));r=NMIRegisters(pc=0xA042);before=(bytes(m.ram),bytes(m.sram),reg(r))
    result=CityCooperationUIServices(m,data)(ServiceCall(0xA042,0x2468,'wrong_pair',r,m,tuple(m.banks),255))
    assert result['status']=='dependency'and before==(bytes(m.ram),bytes(m.sram),reg(r));guards.append('wrong_physical_pair_preserves_actual_caller')
    pins=['source/recovered/'+n+'.py'for n in('city_cooperation_ui_services','scene_shared_services','battle_nmi_services','controller_helpers','battle_graphics_services','audio_services','service_memory','mapped_memory')]
    pins+=['scripts/verify_city_cooperation_ui_services.py']
    result=dict(schema='phase14-city-cooperation-UI-v1',status='passed'if not failures else'failed',quick=quick,rom_sha256=ROM_SHA256,
        rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(counts.values()),strict_prefix_count=0,source_guard_case_count=len(guards),
        failed_count=len(failures),counts=dict(counts),rows=rows,guards=guards,failures=failures,source_original_CPU_callbacks=0,source_IR_interpretation=False,
        comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,CPU_registers='AXYP/SP/PC',free_stack_residue='included',ordered_ports_banks_reads=True),
        source_sha256={p:sha(ROOT/p)for p in pins},artifact_sha256={str(Path(str(parent)+s).relative_to(ROOT)):sha(str(parent)+s)for s in('-ram.bin','-sram.bin')},
        executed_original_locations=[dict(physical_bank=b,cpu_address=p,rom_offset=o,visits=n)for(b,p,o),n in sorted(visited.items())],
        limits=['13-byte raw badge records are immutable data;237..255 directAB38 addressing cases do not establish valid gameplay identities.',
            'All256 stack/OAM byte cursors verify service arithmetic, not a claim the game naturally fills every position.',
            'A042/AA37 enqueue0380 and7E|4; this producer does not consume PPU jobs, select an heir or write6F8B acknowledgements.',
            'Real F25F and EBE9 source helpers run on actual localJSR frames; original CPU runs only in this script.'])
    (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count')}),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase14/city-cooperation-ui');p.add_argument('--quick',action='store_true');a=p.parse_args()
    result=verify(a.rom.read_bytes(),a.out,a.quick);raise SystemExit(bool(result['failures']))
