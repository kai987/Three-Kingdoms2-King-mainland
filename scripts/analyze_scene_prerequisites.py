#!/usr/bin/env python3
"""Archive immutable ROM evidence for manually recovered shared/setup bodies.

This is offline analysis. Production modules contain named Python routines and
read only immutable game data; neither this receipt nor opcodes are executed.
"""
import argparse,ast,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
SPECS={
 'shared':dict(module='scene_shared_services',ranges=[(31,0xE749,0xE83A),(31,0xE843,0xE8BA),(31,0xE9BA,0xECBF),(31,0xECBF,0xEE55),(31,0xF092,0xF206),(31,0xF26D,0xF2F7),(31,0xF368,0xF3A5)],data=[(31,0xE8BA,0xE9BA)],
  claims=['Original message request queues remain pending until the text service consumes them.',
          'Palette backups0100..013F, actual display writes and real menu sentinel loops are retained.',
          'EE07 reads a two-byte inline callee pointer as data, saves/restores the real PRG pair and caller frame.',
          'Malformed menus and a zero RNG bound remain pending across repeated resume; no synthetic RTS.']),
 'initialization':dict(module='scene_initialization',ranges=[(31,0xE18B,0xE36A),(31,0xE370,0xE37B),(31,0xE4DA,0xE567),(23,0xA000,0xA087),(23,0xA087,0xA2FF),(30,0xDBB1,0xDBCF),(30,0xDE7E,0xDEA8),(30,0xDEB9,0xDF1A),(24,0xDF15,0xDF4A)],data=[(23,0xA06B,0xA087),(31,0xE2DE,0xE2E8),(31,0xE567,0xE57F),(30,0xDBCF,0xDBEB),(30,0xDF1A,0xDF6E),(24,0xDF4A,0xDF86),(1,0x946C,0x970C)],
  claims=['Global setup E18B/E22F/E2E8 requests battle/ordinary attack/duel and ends at E066, not a caller RTS.',
          'Display reset disables NMI/rendering, resets the original audio driver, clears nametables/OAM and real queues.',
          'Raw1024-byte, marker RLE, metatile, palette,48-byte CHR and IRQ loaders retain their mapper and port ordering.',
          'PPUSTATUS reads are explicit resumable inputs; requesting fade/rendering is not completed hardware time.'])}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert digest(a.rom)==SHA
 for area,s in SPECS.items():
  module=ROOT/f'source/recovered/{s["module"]}.py';tree=ast.parse(module.read_text());raw=[]
  for kind,items in [('code_evidence',s['ranges']),('immutable_data',s['data'])]:
   for bank,start,end in items:
    offset=16+bank*8192+(start&8191);data=rom[offset:offset+end-start]
    raw.append(dict(kind=kind,physical_bank=bank,cpu_address=start,end_exclusive=end,rom_offset=offset,bytes=len(data),raw_hex=data.hex(),sha256=hashlib.sha256(data).hexdigest()))
  if area=='initialization':
   table=16+30*8192+(0xDBCF&8191)
   for i in range(14):
    start=int.from_bytes(rom[table+2*i:table+2*i+2],'little');bank=29 if start<0xC000 else 30
    offset=16+bank*8192+(start&8191);data=rom[offset:offset+32]
    raw.append(dict(kind='palette_immutable_data',palette_index=i,physical_bank=bank,cpu_address=start,rom_offset=offset,bytes=32,raw_hex=data.hex(),sha256=hashlib.sha256(data).hexdigest()))
  deps=['source/recovered/scene_shared_services.py','source/recovered/battle_nmi_services.py','source/recovered/audio_services.py','source/recovered/battle_graphics_services.py','source/recovered/controller_helpers.py','source/recovered/service_memory.py']
  deps=[v for v in deps if ROOT/v!=module]
  e=dict(status='passed',rom_sha256=SHA,module=s['module'],source_sha256=digest(module),analyzer_path='scripts/analyze_scene_prerequisites.py',analyzer_sha256=digest(Path(__file__)),raw_ranges=raw,
         dependencies={v:digest(ROOT/v)for v in deps},named_procedures=[n.name for n in ast.walk(tree)if isinstance(n,ast.FunctionDef)],claims=s['claims'],
         source_original_CPU_callbacks=0,source_IR_interpretation=False,
         scope='Software RAM/register/port requests. Free stack residue is excluded by declared validator scope; real caller SP/PC is checked.',
         original_instruction_bytes_executed_by_source=False)
  out=ROOT/'analysis/phase11'/area;out.mkdir(parents=True,exist_ok=True);(out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
  (out/'README.md').write_text('# '+s['module']+'\n\n'+'\n\n'.join(s['claims'])+'\n\nRaw evidence offsets include the16-byte iNES header. See validation.json for exact comparisons, inputs and guards.\n')
 print(json.dumps({'status':'passed','areas':list(SPECS)}))
if __name__=='__main__':main()
