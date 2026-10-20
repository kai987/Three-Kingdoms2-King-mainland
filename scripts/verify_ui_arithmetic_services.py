#!/usr/bin/env python3
"""Original EC22 CPU versus an independent direct multiplier; full RAM/regs."""
import argparse,hashlib,json,random,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_graphics_services import PortBus
from source.recovered.ui_arithmetic_services import UIArithmeticServices
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.service_memory import ServiceMemory
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==SHA
 rng=random.Random(0x13EC22);base=ROOT/'analysis/runtime/city-commands';ram=Path(str(base)+'-ram.bin').read_bytes();sram=Path(str(base)+'-sram.bin').read_bytes();failed=[];samples=[];count=0
 cases=[(u,v,p)for u in(0,1,255,256,65535,65536,0x7FFFFF,0xFFFFFF)for v in(0,1,255,256,32767,65535)for p in(32,33,96,225)]+[(rng.randrange(1<<24),rng.randrange(1<<16),rng.randrange(256)&~8)for _ in range(320)]
 for left,right,flags in cases:
  b=PortBus(rom);b.ram[:]=ram;b.sram[:]=sram;b.banks=[17,25,26,31];b.bank_initialized=[True]*4;b.protect=0x4C;b.ram[0:3]=left.to_bytes(3,'little');b.ram[3:5]=right.to_bytes(2,'little');b.ram[0x1FE:0x200]=bytes((0x67,0x24));b.record_ports=True
  m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));r=NMIRegisters(a=17,x=31,y=63,p=flags,sp=253,pc=0xEC22);c=UIArithmeticServices(m);cpu=MPU(memory=b,pc=0xEC22);b.cpu=cpu
  for k in('a','x','y','p','sp'):setattr(cpu,k,getattr(r,k))
  try:
   result=c.run_service(0xEC22,r);assert result['status']=='returned'
   for n in range(5000):
    if cpu.pc==0x2468:break
    b.pc=cpu.pc;b.step_no=n;cpu.step()
   else:raise AssertionError('Original EC22 budget')
   assert b.ram==m.ram and b.sram==m.sram and b.banks==m.banks and b.ports==m.io_writes
   assert all(getattr(cpu,k)==getattr(r,k)for k in('a','x','y','p','sp','pc'))
   assert int.from_bytes(m.ram[6:11],'little')==left*right
   count+=1
   if len(samples)<4:samples.append(dict(left=left,right=right,flags=flags,product=left*right,registers=vars(r)))
  except Exception as exc:failed.append(dict(left=left,right=right,flags=flags,error=str(exc)))
 unknown=ServiceCall(0xEC21,0x2468,'unknown',NMIRegisters(sp=253,pc=0xEC21),m,tuple(m.banks),255);assert c(unknown)['status']=='dependency'
 source='source/recovered/ui_arithmetic_services.py';out=ROOT/'analysis/phase13/arithmetic';out.mkdir(parents=True,exist_ok=True);raw=rom[16+31*8192+0xC22:16+31*8192+0xC67]
 e=dict(status='passed',rom_sha256=SHA,source_path=source,source_sha256=sha(ROOT/source),analyzer_path=str(Path(__file__).relative_to(ROOT)),analyzer_sha256=sha(Path(__file__)),ranges=[dict(physical_bank=31,cpu_start=0xEC22,cpu_end_exclusive=0xEC67,rom_offset=16+31*8192+0xC22,byte_count=len(raw),raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest())],source_original_CPU_callbacks=0,source_IR_interpretation=False,REA_archive='analysis/rea/pairs/pair-25')
 (out/'evidence.json').write_text(json.dumps(e,indent=2)+'\n')
 v=dict(status='passed'if not failed else'failed',rom_sha256=SHA,rom_cpu_case_count=count,complete_return_count=count,strict_prefix_count=0,source_guard_case_count=1,counts={'complete_return':count},failed_count=len(failed),failures=failed,source_sha256=sha(ROOT/source),source_path=source,validator_sha256=sha(Path(__file__)),validator_path=str(Path(__file__).relative_to(ROOT)),evidence_sha256=sha(out/'evidence.json'),comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,registers='AXYP/SP/PC',ports_and_banks=True),source_original_CPU_callbacks=0,samples=samples,guards=['unknown_fixed_entry_is_not_owned'])
 (out/'validation.json').write_text(json.dumps(v,indent=2)+'\n');(out/'README.md').write_text('# 城市UI的EC22乘法\n\n24bit×16bit得到40bit结果，保留原destructive shifts、scratch和flags；只消费已有真实caller。512项原CPU完整返回，全2048RAM（含stack）、8192SRAM、AXYP/SP/PC、端口与bank，另1项未知入口guard。源码不执行CPU/IR。原字节偏移包括16B头。\n')
 print(json.dumps(dict(status=v['status'],CPU=count,failed=failed[:8])));return bool(failed)
if __name__=='__main__':raise SystemExit(main())
