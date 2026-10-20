#!/usr/bin/env python3
"""Compare reconstructed Python behavior to actual 6502 ROM instructions.

Requires py65 1.2.0. Run with --py65-path if installed in an isolated directory.
Tests CPU arithmetic/pointer/RNG routines only, not PPU, mapper IRQ, or gameplay.
"""
from pathlib import Path
import sys
import argparse
import json
import hashlib
import random
from datetime import datetime, timezone

def verify_call_protocols(blob):
    from py65.devices.mpu6502 import MPU
    checks=[]
    for jsr in [0x200,0x2fb,0x2fc,0x2fd,0x2fe,0x2ff]:
        m=MPU();m.memory[0xe000:0x10000]=blob[0x3e010:0x40010]
        m.memory[jsr:jsr+5]=[0x20,0x07,0xee,0x00,0x05]
        m.memory[0x500:0x503]=[0xa9,0xa7,0x60]
        m.memory[0xe2]=9;m.memory[0xe3]=10;m.y=0x28;m.pc=jsr
        for step in range(500):
            m.step()
            if m.pc==jsr+5:break
        else:raise AssertionError("EE07 failed return")
        assert m.a==9 and m.y==9 and m.memory[0xe2]==9 and m.memory[0xe3]==10 and m.sp==255
        checks.append({"helper":"EE07","call_cpu_address":f"0x{jsr:04X}","return_cpu_address":f"0x{m.pc:04X}","bank_before":9,"bank_restored":m.memory[0xe2],"stack_restored":m.sp==255,"instructions":step+1})
    for index in [0,1,2,3,126,127,128,129,255]:
        m=MPU();m.memory[0xe000:0x10000]=blob[0x3e010:0x40010]
        m.memory[0x200:0x203]=[0x20,0x00,0x03]
        m.memory[0x300:0x305]=[0xa9,index,0x20,0xde,0xea]
        for i in range(128):
            target=0x500+4*i
            m.memory[0x305+i*2:0x307+i*2]=[target&255,target>>8]
            m.memory[target:target+3]=[0xa9,i,0x60]
        base=0x304;lowoff=(2*index+1)&255;highoff=(lowoff+1)&255
        expected=m.memory[base+lowoff]+256*m.memory[base+highoff];m.pc=0x200
        for step in range(100):
            if m.pc==0xeaf4:break
            m.step()
        else:raise AssertionError("EADE did not reach dispatch")
        m.step();assert m.pc==expected
        check={"helper":"EADE","input_index":index,"target_cpu_address":f"0x{m.pc:04X}","table_low_byte_index":lowoff,"table_high_byte_index":highoff,"dispatch_matches_code":True}
        if index%128<127:
            m.step();m.step();assert m.pc==0x203 and m.a==index%128 and m.sp==255
            check.update(return_cpu_address="0x0203",outer_return=True,stack_restored=True)
        else:check["edge_note"]="Y wraps after low-byte read at 255; high byte comes from original JSR operand address, so index127/255 is not a normal final table entry."
        checks.append(check)
    return {"status":"passed","oracle":"py65 1.2.0 actual ROM helper bytes plus synthetic RAM callers and targets","case_count":len(checks),"checks":checks,"limitations":["CPU-only helper protocol; mapper writes use flat memory without real bank switching.","EE07 clobbers A and Y; this does not assert register preservation.","EE07 restores bank pair from saved E2; original A000/C000 banks assumed consecutive."]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("rom",type=Path)
    p.add_argument("--py65-path",type=Path)
    p.add_argument("--output",type=Path,default=Path("analysis/game_data/algorithm-validation.json"))
    a=p.parse_args()
    if a.py65_path:sys.path.insert(0,str(a.py65_path))
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"source/recovered"))
    from py65.devices.mpu6502 import MPU
    import game_algorithms as recovered
    blob=a.rom.read_bytes(); sha=hashlib.sha256(blob).hexdigest()
    if sha!="26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82":raise ValueError("Different ROM")
    fixed=blob[0x3e010:0x40010]
    def run(addr,regs=None,mem=None):
        m=MPU();m.memory[0xe000:0x10000]=fixed
        m.memory[0x200:0x203]=[0x20,addr&255,addr>>8];m.pc=0x200
        for k,v in (regs or {}).items():setattr(m,k,v)
        for k,v in (mem or {}).items():m.memory[k]=v
        for step in range(20000):
            m.step()
            if m.pc==0x203:return m,step+1
        raise AssertionError(f"Routine ${addr:04X} did not return; PC=${m.pc:04X}")
    def u16(m,base):return m.memory[base]+256*m.memory[base+1]
    def u24(m,base):return u16(m,base)+65536*m.memory[base+2]
    results=[]
    def save(name,count,examples):
        info=recovered.ROUTINES[name]
        results.append({"name":name,"status":"passed","case_count":count,"cpu_address":f"0x{info['cpu']:04X}","rom_offset":f"0x{info['rom_offset']:06X}","raw_routine_hex":blob[info['rom_offset']:info['rom_offset']+info['size']].hex(' ').upper(),"examples":examples})
    for name in ["table_a_ram_address","table_b_ram_address","table_b_initial_cpu_address"]:
        examples=[]
        for value in range(256):
            m,steps=run(recovered.ROUTINES[name]["cpu"],{"a":value})
            observed=u16(m,0);expected=getattr(recovered,name)(value)
            assert observed==expected,(name,value,observed,expected)
            if value in (0,29,236,255):examples.append({"input":value,"output":f"0x{observed:04X}","instructions_executed":steps})
        save(name,256,examples)
    rand=random.Random(163)
    for name,width,count in [("divide_u16",16,250),("divide_u24_by_u16",24,250)]:
        maxv=(1<<width)-1
        cases=[(0,1),(1,1),(maxv,1),(maxv,65535),(maxv,256),(5000,7),(0,0),(maxv,0)]
        cases += [(rand.randrange(1<<width),rand.randrange(1,65536)) for _ in range(count)]
        examples=[]
        for i,(value,divisor) in enumerate(cases):
            mem={3:divisor&255,4:divisor>>8}
            if width==16:mem.update({1:value&255,2:value>>8})
            else:mem.update({0:value&255,1:(value>>8)&255,2:value>>16})
            m,steps=run(recovered.ROUTINES[name]["cpu"],mem=mem)
            observed=(u16(m,1),u16(m,5)) if width==16 else (u24(m,0),u24(m,5))
            expected=getattr(recovered,name)(value,divisor)
            assert observed==expected,(name,value,divisor,observed,expected)
            if i<8:examples.append({"input":[value,divisor],"quotient":observed[0],"remainder":observed[1],"instructions_executed":steps})
        save(name,len(cases),examples)
    values=[0,1,9,10,99,100,9999,10000,999999,1000000,16777215]+[rand.randrange(1<<24) for _ in range(100)]
    examples=[]
    for i,value in enumerate(values):
        m,steps=run(0xe9ba,mem={1:value&255,2:(value>>8)&255,3:value>>16})
        observed=tuple(m.memory[j] for j in (7,8,9))
        assert observed==recovered.packed_bcd6(value),(value,observed)
        if i<11:examples.append({"input":value,"packed_bcd_low_to_high":[f"{v:02X}" for v in observed],"instructions_executed":steps})
    save("packed_bcd6",len(values),examples)
    permutation=blob[0x3e8ca:0x3e9ca]
    assert len(set(permutation))==256
    examples=[]
    for cursor in range(256):
        m,steps=run(0xe87a,{"x":0x42},{0x50:cursor})
        rng=recovered.PermutationRng(permutation,[cursor,0,0,0]); expected=rng.next_u8()
        assert (m.a,m.memory[0x50],m.x)==(expected,rng.cursors[0],0x42)
        if cursor in (0,1,255):examples.append({"cursor_before":cursor,"value":m.a,"cursor_after":m.memory[0x50],"X_preserved":m.x==0x42})
    save("rng_next",256,examples)
    examples=[];count=0
    for bound in [1,2,7,14,15,16,100,255]:
        for cursor in range(256):
            m,steps=run(0xe862,{"a":bound},{0x50:cursor})
            rng=recovered.PermutationRng(permutation,[cursor,0,0,0]);expected=rng.bounded(bound)
            assert (m.a,m.memory[0x50])==(expected,rng.cursors[0]),(bound,cursor)
            if cursor==0:examples.append({"bound":bound,"cursor_before":cursor,"value":m.a,"cursor_after":m.memory[0x50],"instructions_executed":steps})
            count+=1
    save("bounded_rng",count,examples)
    # Cross-check listing decoder opcode metadata against an independent tool.
    from py65.disassembler import Disassembler
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from inspect_game_data import OPS,SIZES
    for opcode,(mnemonic,mode) in enumerate(OPS):
        if mnemonic=="?":continue
        m=MPU();m.memory[0x200:0x203]=[opcode,0x34,0x12]
        size,text=Disassembler(m).instruction_at(0x200)
        assert size==SIZES[mode] and text.split()[0]==mnemonic,(opcode,size,text,mnemonic,mode)
    payload={"status":"passed","timestamp_utc":datetime.now(timezone.utc).isoformat(),"rom_sha256":sha,"oracle":"py65 1.2.0 MPU executes actual supplied ROM bytes, decimal mode disabled","random_seed":163,"case_count":sum(r['case_count'] for r in results),"results":results,"listing_decoder_cross_check":{"official_opcode_count":151,"status":"passed","oracle":"py65 disassembler size/mnemonic for each official opcode"},"limitations":["CPU-only flat-memory invocation; mapper side effects, PPU/APU timing, interrupts, and gameplay are not emulated.","RNG NMI cursor increment is statically supported by bytes at CPU $F8A1 (ROM $03F8B1); complete NMI path is not dynamically tested here.","The reconstructed Python API rejects RNG bound=0, while the ROM rejection loop would not terminate."]}
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n")
    protocols=verify_call_protocols(blob)
    (a.output.parent/"call-protocol-validation.json").write_text(json.dumps(protocols,ensure_ascii=False,indent=2)+"\n")
    print(f"Passed {payload['case_count']} actual-ROM cases plus 151 official opcode metadata checks. Wrote {a.output}")
    print(f"Passed {protocols['case_count']} synthetic-caller actual-ROM helper protocol cases.")

if __name__=="__main__":main()
