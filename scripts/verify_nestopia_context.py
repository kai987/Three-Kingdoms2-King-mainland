#!/usr/bin/env python3
"""Check pinned original-core snapshot contexts, never relabel as CPU trace."""
from pathlib import Path
from collections import Counter
import ctypes as C
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from source.recovered.nestopia_context import NestopiaContext, CapturedServiceMemory, chunks, uncompress
from nes_runtime import Runtime

OUT=ROOT/'analysis/phase19/state-format'
COMMIT='135dfa6dfda5e7603d61e751b9ddd0cc42546bc3'
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def main():
    rom=Path(sys.argv[1]);assert sha(rom)==ROM_SHA
    OUT.mkdir(parents=True,exist_ok=True)
    rows=[];pins={};mismatches=[]
    # Full frozen phase18 population; new phase19 Native cases can be added by
    # rerunning this new validator only after they have finished/frozen.
    paths=sorted((ROOT/'analysis/phase18/runtime').rglob('*.state'))
    paths+=sorted((ROOT/'analysis/phase19/runtime').rglob('*.state'))
    for path in paths:
        c=NestopiaContext.parse(path.read_bytes());key=str(path.relative_to(ROOT));pins[key]=sha(path)
        pair=[]
        for name,data in [('ram',c.ram),('sram',c.sram)]:
            p=path.with_name(path.stem+'-'+name+'.bin');assert p.read_bytes()==data,p
            pins[str(p.relative_to(ROOT))]=sha(p);pair.append(name)
        shadows=tuple([x&31 for x in c.ram[0xDE:0xE1]]+[31])
        if shadows!=c.prg_banks:mismatches.append(key)
        rows.append(dict(state=key,state_sha256=pins[key],registers=c.registers,
            actual_saved_PRG_banks=c.prg_banks,RAM_PRG_shadows=shadows,
            RAM_SRAM_dump_parity=pair,stream_bytes=c.stream_bytes,
            footer_bytes=len(c.footer),footer_sha256=hashlib.sha256(c.footer).hexdigest(),
            register_payload_offset=c.register_payload_offset,
            N163_RAM_sha256=hashlib.sha256(c.n163_ram).hexdigest(),
            N163_address=c.n163_address,N163_autoincrement=c.n163_autoincrement,
            N163_saved_IRQ_bytes=c.n163_IRQ_saved_bytes.hex(),
            RAM_compression_tag_offset=c.ram_payload_offset,
            SRAM_compression_tag_offset=c.sram_payload_offset,
            Native_instruction_trace=False))
    assert len(rows)>=118
    # Original, unchanged dylib independently accepts each selected state and
    # exposes exactly the decoded RAM/SRAM through its libretro memory API.
    selected=[p for p in paths if p.name=='initial.state' or str(p.relative_to(ROOT))in mismatches]
    original=[]
    generated=OUT/'original-core-roundtrip'
    generated.mkdir(exist_ok=True)
    # Remove only this validator's own unfrozen generated outputs before
    # rebuilding its manifest; original input states are elsewhere.
    for p in generated.glob('*.state'):p.unlink()
    core_info=None
    for path in selected:
        rt=Runtime(rom,OUT/'original-core-roundtrip')
        core_info=rt.info
        try:
            before=NestopiaContext.parse(path.read_bytes());rt.load_state(path)
            assert rt.memory(2)==before.ram and rt.memory(0)==before.sram
            n=rt.core.retro_serialize_size();buf=C.create_string_buffer(n)
            assert rt.core.retro_serialize(buf,n)
            after=NestopiaContext.parse(buf.raw)
            assert after.registers==before.registers and after.ram==before.ram
            assert after.sram==before.sram and after.prg_banks==before.prg_banks
            assert after.n163_ram==before.n163_ram and after.n163_address==before.n163_address
            assert after.n163_autoincrement==before.n163_autoincrement
            assert after.n163_IRQ_saved_bytes==before.n163_IRQ_saved_bytes
            phase=path.relative_to(ROOT/'analysis').parts[0]
            label=phase+'__'+path.parent.name+'__'+path.stem
            saved=OUT/'original-core-roundtrip'/(label+'.state')
            saved.write_bytes(buf.raw);pins[str(saved.relative_to(ROOT))]=sha(saved)
            original.append(dict(input=str(path.relative_to(ROOT)),output=str(saved.relative_to(ROOT)),
                input_sha256=sha(path),output_sha256=sha(saved),
                registers_RAM_SRAM_actual_PRG_banks_equal=True,core_frames_run=0,
                N163_RAM_pointer_autoincrement_IRQ_saved_bytes_equal=True,
                original_state_modified=False))
        finally:rt.close()
    guards=[]
    sample=paths[0].read_bytes()
    broken=[sample[:7],sample[:20],sample[:32]+b'REG\0'+b'\xff'*4+sample[40:],
            sample+b'\x01',sample[:4]+b'\xff'*4+sample[8:]]
    for i,data in enumerate(broken):
        try:NestopiaContext.parse(data)
        except ValueError:guards.append(dict(case='malformed-state-'+str(i),status='rejected'))
        else:raise AssertionError('Malformed state accepted')
    import zlib
    for mode,payload in [('raw',b'\x00abc'),('zlib',b'\x01'+zlib.compress(b'abc'))]:
        assert uncompress(payload,3)==b'abc';guards.append(dict(case=mode+'-block',status='passed'))
    for payload in [b'\x02abc',b'\x00abcd',b'\x01invalid',b'\x01'+zlib.compress(b'abcd'),b'\x01'+zlib.compress(b'abc')+b'x']:
        try:uncompress(payload,3)
        except ValueError:guards.append(dict(case='invalid-compressed-block-'+str(len(guards)),status='rejected'))
        else:raise AssertionError('Invalid compressed block accepted')
    n163_checks=0
    # Exhaust the exact saved address/autoincrement domain for both aliases
    # and read/write directions against the pinned upstream transition formula.
    for port in (0x4800,0x4FFF):
        for address in range(128):
            for increase in (False,True):
                for operation in ('read','write'):
                    memory=CapturedServiceMemory(rom.read_bytes())
                    memory.n163_ram[:]=bytes(range(128));memory.n163_address=address
                    memory.n163_autoincrement=increase
                    expected=bytearray(range(128))
                    if operation=='read':assert memory.io_read(port)==address
                    else:memory.io_write(port,231);expected[address]=231
                    assert memory.n163_address==(address+int(increase))&127
                    assert memory.n163_ram==expected
                    assert memory.n163_autoincrement==increase
                    n163_checks+=1
    memory=CapturedServiceMemory(rom.read_bytes(),read_ports={0x4800:165})
    memory.n163_address=127;memory.n163_autoincrement=True
    assert memory.io_read(0x4FFF)==165 and memory.n163_address==127
    n163_checks+=1
    upstream=[]
    for p in sorted((OUT/'upstream').iterdir()):
        if not p.is_file():continue
        origin=('libretro/'if p.name=='libretro.cpp'else 'source/core/')+p.name
        if p.name.startswith('NstBoard'):origin='source/core/board/'+p.name
        if p.name=='COPYING':origin='COPYING'
        upstream.append(dict(path=str(p.relative_to(ROOT)),sha256=sha(p),
            url=f'https://github.com/libretro/nestopia/blob/{COMMIT}/{origin}'))
        pins[str(p.relative_to(ROOT))]=sha(p)
    source_files=[Path(__file__),ROOT/'source/recovered/nestopia_context.py',ROOT/'scripts/nes_runtime.py']
    result=dict(schema='phase19-original-Nestopia-saved-context-v1',status='passed',
        ROM_sha256=ROM_SHA,core=core_info,upstream_commit=COMMIT,upstream=upstream,
        snapshot_count=len(rows),original_core_roundtrip_count=len(original),
        RAM_shadow_bank_mismatch_count=len(mismatches),RAM_shadow_bank_mismatches=mismatches,
        all_shadow_mismatch_snapshots_roundtripped=True,
        CPU_register_order=['PC_low','PC_high','SP','A','X','Y','P'],
        Native_instruction_trace=False,rows=rows,original_core_roundtrips=original,
        source_guard_count=len(guards),guards=guards,
        N163_boundary_transition_checks=n163_checks,
        N163_boundary_reference='NstBoardNamcot163.cpp saved-pointer and (exAddress+exIncrease)&0x7F',
        source_sha256={str(p.relative_to(ROOT)):sha(p)for p in source_files},
        artifact_sha256=pins,
        limits=['CPU/REG is an actual original-core saved register snapshot, not a per-instruction trace.',
          'No video frame or instruction is executed by load/serialize roundtrip.',
          'ServiceMemory construction copies actual banks and memory; it does not restore PPU/APU/interrupt timing.',
          'The original ROM and core dylib are unchanged.'])
    write(OUT/'validation.json',result)
    print(json.dumps({k:result[k]for k in('status','snapshot_count','original_core_roundtrip_count','source_guard_count','RAM_shadow_bank_mismatch_count')}))

if __name__=='__main__':main()
