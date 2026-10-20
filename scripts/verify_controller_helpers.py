#!/usr/bin/env python3
"""Compare source helper register/stack/RAM effects with actual fixed-bank code."""
import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from py65.devices.mpu6502 import MPU
from source.recovered.controller_helpers import ControlHelpers
from source.recovered.duel_state_machine import Registers

def context(memory, registers):
    ctx = SimpleNamespace(memory=memory, registers=registers)
    def push(value):
        memory[0x100+registers.sp] = value & 255
        registers.sp = (registers.sp-1) & 255
    def pop():
        registers.sp = (registers.sp+1) & 255
        return memory[0x100+registers.sp]
    ctx.push, ctx.pop = push, pop
    return ctx

def main():
    p = argparse.ArgumentParser(); p.add_argument('rom', type=Path); a = p.parse_args()
    blob = a.rom.read_bytes(); helpers = ControlHelpers()
    counts = {'dispatch':0,'officer_address':0,'rng_E87A':0,'rng_E88A':0,'rng_E89A':0,'rng_E8AA':0}
    for kind in counts:
        for value in range(256):
            for original_y in (0, 1, 127, 128, 255):
                for flags in (32, 33, 98, 225):
                    memory = bytearray(65536); memory[0xe000:] = blob[0x3e010:0x40010]
                    memory[0x1fe:0x200] = bytes([255,1])
                    if kind == 'dispatch':
                        memory[0x1fc:0x1fe] = bytes([4,3])
                        for i in range(128):
                            target = 0x500+4*i
                            memory[0x305+2*i:0x307+2*i] = bytes([target&255,target>>8])
                        low_index = (2*value+1)&255
                        target = memory[0x304+low_index] | memory[0x304+((low_index+1)&255)] << 8
                        entry, sp, helper_kind = 0xEADE, 0xFB, 'dispatch'
                    elif kind == 'officer_address':entry, sp, target, helper_kind = 0xF2D7, 0xFD, 0x200, 'call'
                    else:
                        entry=int(kind.split('_')[1],16);sp,target,helper_kind=0xFD,0x200,'call'
                        cursor={0xE87A:0x50,0xE88A:0x52,0xE89A:0x54,0xE8AA:0x55}[entry]
                        memory[cursor]=value
                    oracle_memory = bytearray(memory)
                    x=original_y if kind.startswith('rng_') else 71
                    cpu = MPU(memory=oracle_memory);cpu.pc=entry;cpu.a=value;cpu.x=x;cpu.y=original_y;cpu.sp=sp;cpu.p=flags
                    for _ in range(100):
                        cpu.step()
                        if cpu.pc == target:break
                    else:raise AssertionError('ROM helper failed to reach expected destination')
                    regs = Registers(a=value,x=x,y=original_y,sp=sp,p=flags,pc=entry)
                    ctx = context(memory,regs);helpers(ctx,entry,target,helper_kind)
                    for name in ('a','x','y','sp','p','pc'):
                        assert getattr(regs,name)==getattr(cpu,name), (kind,value,original_y,flags,name,getattr(regs,name),getattr(cpu,name))
                    assert memory[:0x200] == oracle_memory[:0x200], (kind,value,'scratch/stack mismatch')
                    counts[kind]+=1
    out=ROOT/'analysis/phase3';out.mkdir(parents=True,exist_ok=True)
    result={'status':'passed','case_count':sum(counts.values()),'counts':counts,
            'oracle':'Actual bank31 EADE, F2D7 and four permutation RNG entry bytes in py65, synthetic RAM callers',
            'checks':['A/X/Y/PC/SP/status flags','All zero-page and stack bytes'],
            'limitations':['Controller dispatch supplies an already validated target.','Decimal flag is clear, as in the original NES game.','No renderer or complete game validation is implied.']}
    (out/'shared-helper-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
