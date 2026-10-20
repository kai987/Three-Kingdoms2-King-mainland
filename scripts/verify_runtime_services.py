#!/usr/bin/env python3
"""Compare independent fixed service source with actual ROM instructions."""
import argparse,json,hashlib,random,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from trace_startup import Bus
from source.recovered.battle_state_machine import BattleStateMachine,Registers,ROM_SHA256
from source.recovered.mapped_memory import PrgDataMemory,UnsupportedHardware
from source.recovered.runtime_services import RuntimeServices

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes()
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    meta=json.loads((ROOT/'analysis/phase4/services/entries.json').read_text())
    rng=random.Random(650204);counts=Counter();covered=set();failures=[]
    for entry in meta['entries']:
        target=entry['cpu']
        for n in range(512):
            bus=Bus(rom,'zero');bus.banks=[2,12,13,31];bus.bank_initialized=[True]*4;bus.protect=0x4C
            bus.ram[:]=rng.randbytes(0x800)
            bus.sram[:]=rng.randbytes(0x2000)
            bus.ram[0x1fe:0x200]=bytes([255,1])
            # Canonical nonsparse menu geometry; buttons span all direction
            # combinations and wrapping/suppression states.
            if target in (0xED1E,0xED23,0xED28):
                width={0xED1E:2,0xED23:3,0xED28:4}[target];height=1+n%4
                bus.ram[0x10:0x12]=bytes([0,4]);bus.ram[0x12]=n&1
                bus.ram[0x81]=(n%16)<<4
                bus.ram[0x424]=n%width;bus.ram[0x425]=(n//width)%height
                bus.ram[0x400:0x440]=bytes([255]*64)
                for index in range(width*height):bus.ram[0x400+index]=index
            if target in (0xEA7C,0xEAA5):
                divisor=(0,1,2,10,100,1000,32768,65535)[n%8]
                bus.ram[3:5]=divisor.to_bytes(2,'little')
            registers={'a':1+n%255 if target==0xE862 else n&255,
                       'x':rng.randrange(256),'y':rng.randrange(256),
                       'sp':0xFD,'p':32|(rng.randrange(256)&(1|2|4|64|128)),'pc':target}
            model_mem=PrgDataMemory(rom,bus.ram,bus.sram,bus.banks)
            context=BattleStateMachine(model_mem,program={'rom_sha256':ROM_SHA256,'instructions':[]})
            context.registers=Registers(**registers);services=RuntimeServices()
            cpu=MPU(memory=bus);bus.cpu=cpu
            for key,value in registers.items():setattr(cpu,key,value)
            try:
                for step in range(200000):
                    if cpu.pc==0x200:break
                    bus.pc=cpu.pc;bus.step_no=step;covered.add(cpu.pc);cpu.step()
                else:raise RuntimeError(f'Original budget exceeded {cpu.pc:04X}')
                services(context,target,0x200,'call')
                assert model_mem.ram==bus.ram,('RAM',[(i,bus.ram[i],model_mem.ram[i])for i in range(2048)if bus.ram[i]!=model_mem.ram[i]][:8])
                assert model_mem.sram==bus.sram,'SRAM'
                assert model_mem.banks==bus.banks,('banks',model_mem.banks,bus.banks)
                requests=[(e['address'],e['value']) for e in model_mem.hardware_requests]
                original=[(e['cpu_address'],e['value']) for e in bus.io_events if e['cpu_address']==0x4015]
                assert requests==original,('APU requests',requests,original)
                for key in registers:assert getattr(context.registers,key)==getattr(cpu,key),(key,getattr(context.registers,key),getattr(cpu,key))
                counts[f'{target:04X}']+=1
            except Exception as e:failures.append({'entry':target,'case':n,'error':str(e)})
    memory=PrgDataMemory(rom)
    try:memory[0x2000]=1
    except UnsupportedHardware:hardware_rejected=True
    else:hardware_rejected=False
    assert hardware_rejected
    out=ROOT/'analysis/phase4/services/validation.json'
    result={'status':'passed' if not failures else 'failed','case_count':sum(counts.values()),'entry_counts':dict(counts),
            'failed_count':len(failures),'failures':failures,'visited_original_instruction_locations':len(covered),
            'rom_sha256':ROM_SHA256,'source_fetches_original_instructions':False,'original_helper_adapter_in_source':False,
            'scope':'All registers/flags/SP/PC, complete RAM/SRAM and physical PRG mapper windows; explicit source services',
            'unsupported_hardware_rejected':hardware_rejected,
            'limits':['PPU/audio synthesis and queue completion are not executed. Requests retain original queued state.',
                      'D flag is clear as in this NES game. Rejection bound0 cannot terminate and is excluded.',
                      'Menus use bounded, terminated matrix fixtures; not arbitrary corrupted pointer data.']}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['status','case_count','failed_count','visited_original_instruction_locations']},ensure_ascii=False))
    if failures:print(json.dumps(failures[:10],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
