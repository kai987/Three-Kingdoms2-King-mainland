#!/usr/bin/env python3
"""Preserve original code/data evidence for independent officer name UI."""
from pathlib import Path
import argparse,ast,hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'analysis/phase12/officer-ui'
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
 def span(name,bank,start,end,kind):
  off=16+bank*8192+(start&8191);raw=rom[off:off+end-start]
  return dict(name=name,kind=kind,physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=off,byte_count=len(raw),raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest())
 ranges=[span(f'public_stub_{entry:04X}',29,entry,entry+3,'original_code')for entry in(0xA027,0xA02A,0xA030,0xA033,0xA036,0xA03C)]
 ranges += [span(name,bank,start,end,'original_code')for name,bank,start,end in[
  ('selected_unit_name',29,0xA830,0xA856),('palette_name_wrapper',29,0xA890,0xA8A4),
  ('left_name',29,0xA8A4,0xA8C3),('duel_name',29,0xA8FD,0xA91D),
  ('name_marks_and_glyphs',29,0xA957,0xA991),('participant_name',29,0xA991,0xA9C3),
  ('clear_attribute_buffer',29,0xBC66,0xBC71),('fixed_name_pointer_alignment',31,0xF308,0xF35F),
  ('reused_fixed_data_bank_mapper',31,0xF25F,0xF266)]]
 tables=[span(name,bank,start,end,'immutable_game_data')for name,bank,start,end in[
  ('selected_unit_name_packet',29,0xA856,0xA890),('left_name_packet',29,0xA8C3,0xA8FD),
  ('duel_name_packet',29,0xA91D,0xA957),('right_participant_packet',29,0xA9C3,0xA9FD),
  ('left_participant_packet',29,0xA9FD,0xAA37),('name_alignment_by_nonmark_code_count',31,0xF35F,0xF368),
  ('237_initial_encoded_names',16,0x901A,0x901A+2370)]]
 # Original loops copy 3A+1 bytes. Adjacent templates contain58 bytes, so
 # byte58 is the following region's first byte (code or another template);
 # preserve that observable read without interpreting it as an opcode.
 for table in tables:
  if 'packet'in table['name']:
   bank=table['physical_bank'];start=table['cpu_start'];table['actual_copy_length']=59
   table['actual_copy_raw_hex']=rom[16+bank*8192+(start&8191):16+bank*8192+(start&8191)+59].hex(' ').upper()
   table['actual_copy_includes_next_region_byte']=table['byte_count']<59
 source=ROOT/'source/recovered/officer_ui_services.py';tree=ast.parse(source.read_text());imports=[]
 for n in ast.walk(tree):
  if isinstance(n,ast.ImportFrom):imports.append(n.module)
  if isinstance(n,ast.Import):imports += [x.name for x in n.names]
 assert not any(w in mod for mod in imports for w in('py65','state_machine','runtime_services','analyze_'))
 pins=[dict(path=f,sha256=digest(ROOT/f))for f in('source/recovered/officer_ui_services.py','source/recovered/battle_nmi_services.py','source/recovered/mapped_memory.py','source/recovered/service_memory.py','scripts/analyze_officer_ui_services.py')]
 archives=[]
 for filename in('image.bin','mapping.json','evidence-bundle.json'):
  f=ROOT/'analysis/rea/pairs/pair-29'/filename;archives.append(dict(path=str(f.relative_to(ROOT)),sha256=digest(f),bytes=f.stat().st_size))
 entries=[dict(public=entry,target=target,mechanics=name)for entry,target,name in[
  (0xA030,0xA8A4,'ID0000 left-name packet'),(0xA03C,0xA991,'ID0000 participant-name packet;0001 zero vs nonzero'),
  (0xA033,0xA8FD,'ID04AE duel-name packet'),(0xA027,0xA830,'ID0664[0509] selected-unit-name packet'),
  (0xA02A,0xA890,'palette0 external EE07 A015 then preserved-ID left-name packet'),
  (0xA036,0xBC66,'clear0140..017F'),(0xF308,0xF308,'fixed encoded name pointer, nonmark count and alignment')]]
 d=dict(schema='phase12-independent-officer-name-UI-v1',rom_sha256=SHA,ROM_modified=False,
  source_original_CPU=False,source_control_IR=False,source_kind='handwritten structured packet/name/mapper source',
  ranges=ranges,tables=tables,public_entries=entries,dependency_pins=pins,REA_archive=archives,
  runtime_imports=imports,actual_far_callers='analysis/phase12/dependencies/callee-inputs/',
  semantics=['A030/A03C are name packet producers, not officer-stat cards or text consumers.',
   'The descending template copy really reads59 bytes, including the first byte of the next region.',
   'F308 writes0002,0000/1 andE1, writesE000 with30, and leaves physical16 in8000.',
   'Codes39/3A are non-advancing marks; X counts other codes and F35F[X] gives alignment.',
   'A957 stores marks at03A5+X; A976 stores ordinary codes at03B1+X;007E|4 requests later upload.'],
  external_calls=[dict(caller=0xA89B,target=0xEE07,selector=0x3D,inline_target=0xA015,return_pc=0xA8A0)],
  scope='Six banked entry stubs and shared name helpers; not full officer-stat UI or bank29 text controller.')
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'evidence.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 lines=['; Immutable original NES ranges, file offsets include16-byte iNES header.']
 for row in ranges+tables:
  lines += [f"; {row['name']} physical{row['physical_bank']} CPU${row['cpu_start']:04X} file0x{row['rom_offset']:06X}"]
  raw=bytes.fromhex(row['raw_hex'])
  for i in range(0,len(raw),16):lines.append(f"  .byte "+','.join(f'${v:02X}'for v in raw[i:i+16]))
 (OUT/'original-ranges.asm').write_text('\n'.join(lines)+'\n')
 print(json.dumps(dict(status='passed',ranges=len(ranges),tables=len(tables),source_sha256=digest(source))))
if __name__=='__main__':main()
