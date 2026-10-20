#!/usr/bin/env python3
"""Byte-exact original6502 comparisons for the independent scroll algorithms."""
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
import argparse,hashlib,json,random,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.scroll_graphics_services import ScrollGraphicsServices,GraphicsData,ROM_SHA256,DECLARED_RAM_ADDRESSES
from source.recovered.service_memory import ServiceMemory

class ScrollOracleBus(Bus):
    def __init__(self,rom,ram,sram):
        super().__init__(rom,'zero');self.ram[:]=ram;self.sram[:]=sram
        self.banks[:]=[2,23,24,31];self.bank_initialized=[True]*4;self.protect=0x4C;self.port_writes=[]
    def __setitem__(self,a,v):
        if ServiceMemory.is_write_port(a&65535):self.port_writes.append(dict(address=a&65535,value=v&255))
        super().__setitem__(a,v)
    def __getitem__(self,a):
        if isinstance(a,int)and 0x2000<=a<0x6000:raise RuntimeError(f'Undeclared scroll hardware read ${a:04X}')
        return super().__getitem__(a)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase10/scroll');p.add_argument('--quick',action='store_true');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;data=GraphicsData.from_rom(rom)
    rng=random.Random(0x5C0010);counts=Counter();failures=[];samples=[];visited=set();guards=[]
    def fresh(x,y,direction=0,kind='tile',axis='both',busy=0,units=0,chunk=0):
        ram=bytearray(rng.randbytes(2048));sram=bytearray(rng.randbytes(8192))
        ram[0x8E:0x92]=bytes((x&255,(x>>8)&1,y&255,(y>>8)&1));ram[0x9C]=direction;ram[0x7E]=busy
        ram[0x92]=y//8&31;ram[0x93]=((x+2)&255 if x&255>=254 else x&255)>>3
        ram[0x94]=y//16&15;ram[0x95]=((x-6)&255)>>3
        if kind=='tile':
            if axis in ('column','both'):ram[0x93]^=255
            if axis in ('row','both'):ram[0x92]^=255
        else:
            if axis in ('column','both'):ram[0x95]^=255
            if axis in ('row','both'):ram[0x94]^=255
        ram[0xA8:0xAA]=bytes((0,4));ram[0x400:0x500]=bytes((chunk+i*7)%120 for i in range(256))
        ram[0x600:0x628]=bytes([255]*40);ram[0x507]=0x10
        for ruler in range(7):sram[0xF07+8*ruler+3]=ruler%3
        for slot in range(20):
            ram[0x63C+slot]=(slot+units)%11;ram[0x628+slot]=(slot%4)|((slot&1)<<7)
            if units:
                ram[0x600+slot]=(x//16+(slot%4))&31;ram[0x614+slot]=(y//16+(slot%5))&31
        if units==2:
            # Multiple unit slots share a cell; descending scan retains slot0.
            ram[0x600:0x614]=bytes([x//16&31]*20);ram[0x614:0x628]=bytes([y//16&31]*20)
        ram[0x1FE:0x200]=bytes((255,1));return ram,sram
    def compare(group,kind,ram,sram,label,regs=None):
        regs=regs or SimpleNamespace(a=67,x=71,y=83,p=32,sp=253)
        source_regs=SimpleNamespace(**vars(regs));mem=ServiceMemory(rom,ram,sram,banks=(2,23,24,31));rules=ScrollGraphicsServices(mem,data)
        bus=ScrollOracleBus(rom,ram,sram);cpu=MPU(memory=bus);bus.cpu=cpu;cpu.pc=0xA00C if kind=='tile' else 0xA00F
        for k,v in vars(regs).items():setattr(cpu,k,v)
        try:
            result=(rules.tile_scroll if kind=='tile' else rules.attribute_scroll)(registers=source_regs)
            for n in range(100000):
                if n and cpu.pc==0x200:break
                bus.pc=cpu.pc;bus.step_no=n
                origin=bus.origin(cpu.pc)
                if origin:visited.add((origin[0],cpu.pc))
                cpu.step()
            else:raise AssertionError(f'Original instruction budget ${cpu.pc:04X}')
            rd=[(f'{i:04X}',bus.ram[i],mem.ram[i])for i in DECLARED_RAM_ADDRESSES if bus.ram[i]!=mem.ram[i]]
            sd=[(i,x,y)for i,(x,y)in enumerate(zip(bus.sram,mem.sram))if x!=y]
            actual={k:getattr(cpu,k)for k in ('a','x','y','p')};expected={k:getattr(source_regs,k)for k in actual}
            assert not rd and not sd,('memory',rd[:12],sd[:3])
            assert mem.io_writes==bus.port_writes,('ports',mem.io_writes,bus.port_writes)
            assert mem.banks==bus.banks,('banks',mem.banks,bus.banks)
            assert actual==expected and cpu.sp==(source_regs.sp+2)&255,('registers',actual,expected,cpu.sp,source_regs.sp)
            counts[group]+=1
            if sum(s['group']==group for s in samples)<3:samples.append(dict(group=group,label=label,original_instruction_count=n,result=result,body_SP=source_regs.sp,after_RTS_SP=cpu.sp))
            return mem.ram[:],mem.sram[:]
        except Exception as exc:
            failures.append(dict(group=group,label=label,error=f'{type(exc).__name__}: {exc}'));return None
    xs=(0,8,16,248,254)if a.quick else(0,1,4,6,7,8,15,16,24,31,32,120,128,240,247,248,251,252,253,254,255,256,264,496,504,510,511)
    ys=(0,16,232)if a.quick else(0,1,7,8,15,16,24,31,32,120,128,223,224,232,239,240,248,255,256,272,480,496,504,511)
    for kind in ('tile','attribute'):
        directions=(0,0xF0)if a.quick else(0,16,32,64,128,240)
        for axis in ('column','row','both','none'):
            for direction in directions:
                for i,x in enumerate(xs):
                    for j,y in enumerate(ys):
                        units=(i+j)%3
                        ram,sram=fresh(x,y,direction,kind,axis,units=units,chunk=(i*5+j*3)%120)
                        regs=SimpleNamespace(a=(i+j)&255,x=i*7&255,y=j*9&255,p=32|((i*37+j*11)&~8&255),sp=253)
                        compare('camera_seams_directions_and_unit_overlap',kind,ram,sram,[kind,axis,x,y,direction,units],regs)
    for busy in range(0,256,32 if a.quick else 1):
        for direction in (0,160):
            for axis in ('column','row','both'):
                ram,sram=fresh(128,232,direction,'tile',axis,busy=busy)
                compare('tile_busy_flags_cache_before_return','tile',ram,sram,[busy,direction,axis])
    # Continuous calls preserve queues, cached camera indices and mapper state;
    # an explicit fixture consumer clears flags between selected steps.
    for kind in ('tile','attribute'):
        for direction in (0,240):
            ram,sram=fresh(120,120,direction,kind,units=1)
            for frame in range(8 if a.quick else 32):
                ram[0x8E]=(ram[0x8E]+3)&255;ram[0x90]=(ram[0x90]+2)&255
                if frame%3==0:ram[0x7E]=0 # Explicit fixture queue input; no source ACK.
                result=compare('continuous_camera_and_pending_requests',kind,ram,sram,[kind,direction,frame])
                if result is None:break
                ram,sram=result
    # Guards are source-domain checks, not originalCPU cases.
    for kind in ('tile','attribute'):
        ram,sram=fresh(0,0,kind=kind);mem=ServiceMemory(rom,ram,sram,banks=(2,23,24,31));before=mem.ram[:]
        try:
            rules=ScrollGraphicsServices(mem,data);getattr(rules,kind+'_scroll')(SimpleNamespace(a=0,x=0,y=0,p=40,sp=253));okay=False
        except ValueError:okay=mem.ram==before and not mem.io_writes
        guards.append(dict(kind=kind,decimal_mode_rejected_before_mutation=okay))
        if not okay:failures.append(dict(group='guard',kind=kind))
    out=a.out;out.mkdir(parents=True,exist_ok=True)
    report=dict(schema='phase10-scroll-services-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,quick=a.quick,
                rom_cpu_case_count=sum(counts.values()),original_complete_case_count=sum(counts.values()),original_prefix_case_count=0,
                source_guard_case_count=len(guards),case_count=sum(counts.values())+len(guards),failed_count=len(failures),counts=dict(counts),
                declared_RAM_addresses=list(DECLARED_RAM_ADDRESSES),declared_RAM_count=len(DECLARED_RAM_ADDRESSES),SRAM_bytes=8192,
                compared=['all declared RAM','all SRAM','ordered port writes','mapper banks','AXYP','body SP vs originalRTS'],
                original_observed_instruction_count=len(visited),source_sha256=hashlib.sha256((ROOT/'source/recovered/scroll_graphics_services.py').read_bytes()).hexdigest(),
                validator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),dependency_pins=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in [ROOT/'source/recovered/battle_graphics_services.py',ROOT/'source/recovered/service_memory.py']],
                guards=guards,failures=failures,samples=samples)
    (out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=p,cpu=p,rom_offset=16+b*8192+(p&8191))for b,p in sorted(visited)],indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],CPU=sum(counts.values()),guards=len(guards),failed=len(failures),first_failures=failures[:8]),ensure_ascii=False))
    return int(bool(failures))
if __name__=='__main__':raise SystemExit(main())
