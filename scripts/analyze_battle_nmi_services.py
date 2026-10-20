#!/usr/bin/env python3
"""Archive immutable bank31 NMI/IRQ/input/PPU byte evidence."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler
from source.recovered.officers import ROM_SHA256
from source.recovered.battle_nmi_services import SCENE_ENTRIES,IRQ_ENTRIES,BattleNMIServices
RANGES=(('controllers',0xE6C6,0xE70E),('palette_upload',0xE70E,0xE749),
        ('OAM_tail',0xE825,0xE843),('scroll_control',0xEAF7,0xEB1A),('palette_fade',0xEC67,0xECBF),
        ('PPU_work_consumers',0xEE53,0xF092),('CHR_and_PRG_windows',0xF206,0xF26D),
        ('NMI_IRQ_split_services',0xF800,0xFFD7))
DATA=((0xF87B,0xF88D),(0xFD1A,0xFD2A))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes()
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 out=ROOT/'analysis/phase10/nmi';out.mkdir(parents=True,exist_ok=True);m=[0]*65536;m[0xE000:]=rom[16+31*8192:16+32*8192]
 dis=Disassembler(MPU(memory=m));ranges=[];lines=[]
 for name,start,end in RANGES:
  offset=16+31*8192+start-0xE000;raw=rom[offset:offset+end-start]
  ranges.append(dict(name=name,physical_bank=31,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,byte_count=len(raw),raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest()))
  pc=start
  while pc<end:
   table=next((b for x,b in DATA if x<=pc<b),None)
   if table:
    size=2;asm=(f'.word ${m[pc]+256*m[pc+1]:04X}'if pc<0xF88D else f'.byte ${m[pc]:02X}, ${m[pc+1]:02X} ; IRQ delay pair')
   else:size,asm=dis.instruction_at(pc)
   off=16+31*8192+pc-0xE000;lines.append(f'{off:06X} b31:${pc:04X} {bytes(m[pc:pc+size]).hex(" ").upper():8} {asm}');pc+=size
 e={'rom_sha256':ROM_SHA256,'ranges':ranges,'scene_table':{'cpu':0xF87B,'file':16+31*8192+0xF87B-0xE000,'entries':list(SCENE_ENTRIES)},
    'IRQ_mode_entries':list(IRQ_ENTRIES),'fixed_service_entries':list(BattleNMIServices.FIXED),
    'PPU_queue':{'priority':'007D nonzero before highest set007E bit7..0; one transaction each call',
     'entries':{'7':'EF0B column30','6':'EF71 row32','5':'EFC0 attribute_column8','4':'F028 attribute_row8',
                '3':'logical3D A00C','2':'logical3D A006','1':'logical3D A012','0':'logical3D A000; flag not cleared by EE53'},
     'no_work':'E70E palette upload, not audio'},
    'dependencies':['physical14/15 A003 audio frame service','banked scene controller/graphics/text bodies','explicit PPU/controller/counter port samples','actual IRQ execution for nonzero0062'],
    'limits':['Static byte provenance only; no dynamic CPU or native core frame count from this file.','IRQ delays retain byte-loop effects; physical scanline/cycle timing remains external.']}
 e['source_contract']={'source':'source/recovered/battle_nmi_services.py','source_sha256':hashlib.sha256((ROOT/'source/recovered/battle_nmi_services.py').read_bytes()).hexdigest(),
   'class':'BattleNMIServices','register_class':'NMIRegisters','methods':['run_service','run_nmi','run_irq','resume','resume_nmi'],
   'intrinsic_original_code_execution':False,'control_IR_interpretation':False,
   'callback':'ServiceCall(target,return_pc,kind,registers,memory,entry_banks,expected_sp); must actually return PC/SP',
   'hardware_entry':'Explicit already-accepted interrupt push; no signal or cycle timing generated'}
 e['dependency_pins']=[{'path':f'source/recovered/{n}','sha256':hashlib.sha256((ROOT/'source/recovered'/n).read_bytes()).hexdigest()}for n in('service_memory.py','mapped_memory.py')]
 e['analysis_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 (out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n');(out/'original-ranges.asm').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'ranges':len(ranges),'bytes':sum(r['byte_count']for r in ranges),'scene_entries':9,'IRQ_entries':13}))
if __name__=='__main__':main()
