#!/usr/bin/env python3
"""Lift bounded fixed-bank input, message, mapper, audio-queue and math services."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from inspect_game_data import OPS,SIZES,instruction
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
ENTRIES={0xF237:'select PRG pair',0xF24B:'select and retain restore PRG pair',
0xF25F:'select PRG data window',0xF266:'select and retain restore data window',
0xF26D:'queue message type0',0xF283:'queue message type2',0xF28B:'queue message type4',
0xF293:'queue message type5',0xF29B:'queue simple message',
0xED1E:'navigate two-column menu',0xED23:'navigate three-column menu',0xED28:'navigate four-column menu',
0xE609:'load audio-channel sequence request',0xE683:'load five consecutive audio requests',
0xE693:'load three consecutive audio requests',0xE69B:'load two consecutive audio requests',
0xE843:'draw bounded100',0xE850:'draw bounded4',0xE856:'draw bounded8',
0xE85C:'draw bounded16',0xE862:'draw supplied bound',
0xEA7C:'divide16 by16',0xEAA5:'divide24 by16',0xEBE9:'multiply16 by16 low16',
0xE9BA:'packed decimal conversion',0xEBCA:'multiply8 by16',
0xF2AF:'city pointer',0xF368:'ruler pointer',0xF387:'initial ROM officer pointer'}
BRANCHES={'BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'}
def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path);a=p.parse_args();blob=a.rom.read_bytes()
    assert hashlib.sha256(blob).hexdigest()==SHA
    out=ROOT/'analysis/phase4/services';out.mkdir(parents=True,exist_ok=True)
    pending=list(ENTRIES);nodes={};issues=[]
    while pending:
        pc=pending.pop()
        if pc in nodes:continue
        if not 0xe000<=pc<0x10000:continue
        off=0x3e010+pc-0xe000;op,mode=OPS[blob[off]];size=SIZES[mode]
        if op=='?':raise ValueError(f'Unclassified opcode at {pc:04X}')
        value=int.from_bytes(blob[off+1:off+size],'little');nxt=pc+size
        item={'pc':pc,'bank':31,'file':off,'op':op,'mode':{'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp'}.get(mode,mode),
              'operand':value,'next_pc':nxt,'raw_hex':blob[off:off+size].hex()}
        if op in BRANCHES:
            item['operand']=(nxt+(value if value<128 else value-256))&65535
            pending.extend([item['operand'],nxt])
        elif op=='JSR':
            if value in (0xEADE,0xEE07):raise ValueError(f'Unexpected inline dispatch/farcall {pc:04X}')
            if value!=0xE87A:pending.append(value)
            else:item['hook']='independently recovered ControlHelpers RNG'
            pending.append(nxt)
        elif op=='JMP':
            if mode!='ab':raise ValueError(f'Unresolved indirect target {pc:04X}')
            pending.append(value)
        elif op not in ('RTS','RTI','BRK'):pending.append(nxt)
        nodes[pc]=item
    ranges=[]
    for item in nodes.values():
        size=(len(item['raw_hex'])//2)
        for byte in range(item['pc'],item['pc']+size):
            if byte in nodes and byte!=item['pc']:issues.append({'pc':item['pc'],'overlap':byte})
    assert not issues
    program={'rom_sha256':SHA,'instructions':sorted(nodes.values(),key=lambda i:i['pc'])}
    (out/'program.json').write_text(json.dumps(program,indent=2)+'\n')
    (out/'entries.json').write_text(json.dumps({'entries':[{'cpu':pc,'file':0x3e010+pc-0xe000,'name':name} for pc,name in ENTRIES.items()],
       'instructions':len(nodes),'unclassified':issues,'scope':'fixed-bank bounded services; actual display synthesis and PPU work excluded'},indent=2)+'\n')
    lines=[]
    for i in program['instructions']:
        _,s=instruction(blob,i['file'],i['pc']);lines.append(f"{i['file']:06X} b31:${i['pc']:04X} {i['raw_hex']:<10} {s}")
    (out/'services.asm').write_text('\n'.join(lines)+'\n')
    print(f'Lifted {len(ENTRIES)} entries, {len(nodes)} fixed service instructions')
if __name__=='__main__':main()
