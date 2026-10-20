#!/usr/bin/env python3
"""Postbattle allocation/control evidence; optional explicitly synthetic UI capture."""
from pathlib import Path
import argparse,json,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from source.recovered.postbattle import ROM_SHA256,PostbattleData
import analyze_battle_fsm as cfg
from inspect_game_data import instruction

APIS={
 (9,0xD6CD):('remove_inactive_unit_slot','Clear six active arrays,6FA1 and first matching attack cache'),
 (8,0xBC46):('process_ai_officers','Three disposition paths; side roster allocation and overflow'),
 (8,0xBDCD):('collect_ai_officers','Original side half, transferred half, captive entries, FF padding'),
 (8,0xBE55):('prioritize_commander','Original side commander to first list entry'),
 (8,0xBE90):('ai_neighbor_cities','Same-owner or neutral neighbors, original occupancy'),
 (12,0xBB84):('human_neighbor_cities','Original destination menu and occupancy scratch'),
 (13,0xD0E1):('build_postbattle_roster','Side-marked active units then captured arrays, FE terminator'),
 (13,0xD167):('toggle_officer_selection','Capacity10 and prohibition on releasing the ruler'),
 (13,0xD1F9):('apply_selected_officers','City/option30 writeback, status/location and first reference removal'),
 (13,0xD48D):('accept_remaining_current_city','Insert remaining<=10 into current city, erase first active/captive refs'),
 (13,0xCD9C):('release_all_without_destination','No-space outcome: leader status3, others status0/current city'),
 (13,0xCD16):('PostbattleEngine','Main13 seven stages'),
 (13,0xD2CD):('PostbattleEngine','Main14 seven stages'),
}

def analyze(rom,out):
 assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
 out.mkdir(parents=True,exist_ok=True);listing=out/'entries';listing.mkdir(exist_ok=True)
 cfg.TABLES={**cfg.TABLES,99:(0xBC4C,3)}
 entries=[];nodes={};issues=[]
 for (bank,entry),(api,description) in APIS.items():
  pair=8 if bank in(8,9) else 12
  direct,errs=cfg.decode_graph(rom,entry,pair)
  seen=set();pending=[entry];callee=[]
  while pending:
   target=pending.pop()
   if target in seen:continue
   seen.add(target);body,problem=cfg.decode_graph(rom,target,pair);issues.extend(problem)
   for node in body:
    nodes[(node['bank'],node['pc'])]=node
    if node['op']=='JSR' and 0xA000<=node['operand']<0xE000:pending.append(node['operand'])
   if target!=entry:callee.append(target)
  lines=[f'; {api}: {description}', '; Source semantics are direct Python; this is exact ROM provenance.']
  for node in direct:
   _,formatted=instruction(rom,node['file'],node['pc'])
   lines.append(f"{node['file']:06X} b{node['bank']:02}:${node['pc']:04X} {node['raw_hex'].upper():<14} {formatted}")
   if node.get('far_target') is not None:lines.append(f"; inline target ${node['far_target']:04X}")
  file=f'bank{bank:02d}-{entry:04X}.asm';(listing/file).write_text('\n'.join(lines)+'\n')
  entries.append({'bank':bank,'cpu':entry,'file':cfg.locate(entry,pair)[1],'source_api':api,'description':description,
      'direct_control_nodes':len(direct),'local_callees':sorted(callee),'issues':errs,'listing':'entries/'+file})
 def evidence(bank,cpu,size,description):
  pair=8 if bank in(8,9) else 12;off=cfg.locate(cpu,pair)[1]
  return {'bank':bank,'cpu':cpu,'file':off,'raw_hex':rom[off:off+size].hex(' '),'description':description}
 writes=[evidence(8,0xBD1C,10,'Special scratch02 match OR03 in packed status; first comparison ID starts as ruler leader'),
   evidence(8,0xBD2B,40,'Overflow nonmatch AND FC status0; scratch02 clobbered with city*8; random8-slot neighbor tobyte5'),
   evidence(13,0xCDC8,15,'No-destination nonleader AND FC, byte5=currentcity050E'),
   evidence(13,0xCDE6,8,'No-destination ruler OR03'),
   evidence(13,0xD21B,42,'Selectable release option30 status0 and randomneighborbyte5'),
   evidence(13,0xD26C,47,'Selected destination roster insertion and neutral cityowner preserving high nibble'),
   evidence(13,0xD2B2,27,'Erase first matching active6-arrays or captive entry; does not delete every alias'),
   evidence(12,0xB605,12,'Health0 tactic path writes low2=3'),
   evidence(9,0xD6CD,66,'Health0 aftermath clears active6-arrays and6FA1 slot; optional attack slot-cache quartet'),
   evidence(8,0xBD76,27,'Mode2 full-source-city branch does not clear scratch04 writtenBD by BC46/EADE')]
 payload={'rom_sha256':ROM_SHA256,'entrypoints':entries,'control_nodes':list(nodes.values()),'unclassified_edges':issues,
   'ai_dispatch':{'bank':8,'cpu':0xBC49,'table_cpu':0xBC4C,'table_file':0x11C5C,'selector':0x6F91,'targets':[0xBC52,0xBD59,0xBD67]},
   'human_dispatch':{'selector_main':0x500,'selector_sub':0x501,'main13':[0xCD2A,0xCD52,0xCDF2,0xCE56,0xCE76,0xCE9E,0xCF09],
                    'main14':[0xD2E1,0xD310,0xD34B,0xD3AF,0xD3D7,0xD3F7,0xD462]},
   'record_write_evidence':writes,
   'ui_choices':[{'destination_id':30,'formal_name':'ざいや','modern_chinese':'转为在野/解除归属','status':'confirmed original core pixels and RAM selector30, explicitly synthetic fixture','mechanics':'Release selected non-ruler to status0 with neighboring byte5; messagesE5/E6'},
       {'destination_ids':'real city IDs','formal_name':'actual city names','mechanics':'Insert into city roster; preserve officer record state; messagesDD/D8'}],
   'glyph_provenance':{'synthetic_fixture':True,'image':'synthetic-ui/main13-option30-cursor.png','zoom':'synthetic-ui/option30-glyph-zoom.png','cursor_ram0012':3,'list042C':[4,14,10,30],'confirmation_image':'synthetic-ui/main13-option30-confirmation.png','confirmation_ram0540':30,'confirmed_text':'ざいやにかえすブショウをえらんでください'},
   'message_ids':{'0xDC':{'original_text':'どのクニに たいきゃくしますか','modern_chinese':'选择撤退目的城','source':'../terrain/core-labels/message-dc.png'},'0xDF':{'original_text':'このクニにはいるブショウが10にんをこえました ほかのクニへどうぞ','modern_chinese':'驻城人数超限，请分配到其他城','source':'../terrain/core-labels/message-df.png'},'0xD7':'Destination prompt','0xDD':'Named city destination confirmation','0xE5':'Option30 confirmation prompt',
                  '0xDE':'Officer list','0xD8':'Selected officers city allocation confirmation','0xE6':'Option30 selected officers confirmation'},
   'status3_conclusion':'Removal/inactive code has several causes, not equivalent to health0. Normal health0 path clears active officerID and excludes it from later postbattle selection; clear-to0 paths alone do not prove natural revival.',
   'known_quirks':['Mode2 full-source-city path retains EADE scratch04=BD and reads6FA1[BD]. Natural campaign reachability unproven.',
     'AI overflow scratch02 initially leaderID is overwritten by city*8 after a nonmatch; later matching nonleaderID may receive status3.'],
   'scope':'Direct readable gameplay source; text readiness/cursor/rendering are explicit UI service inputs/events, not completed ROM stubs.'}
 (out/'evidence.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 print('Entry APIs',len(entries),'control nodes',len(nodes),'unclassified edges',len(issues))


def freeze_ui_images(out):
 """Hash-named full frames, with verified zoom provenance and paired RAM.

 Avoid ambiguous cached browser resources. No game/ROM state is changed here.
 """
 from PIL import Image,ImageChops
 ui=out/'synthetic-ui';items=[]
 for stem,zoom,crop,factor in (
     ('main13-option30-cursor','option30-glyph-zoom.png',(140,176,232,200),8),
     ('main13-option30-confirmation','option30-confirmation-zoom.png',(24,164,256,224),4)):
  source=ui/(stem+'.png')
  if not source.exists():continue
  raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest();im=Image.open(source)
  expected=im.crop(crop).resize(((crop[2]-crop[0])*factor,(crop[3]-crop[1])*factor),Image.Resampling.NEAREST)
  zoomim=Image.open(ui/zoom)
  if ImageChops.difference(expected,zoomim).getbbox() is not None:raise RuntimeError('Zoom pixels do not match paired full frame')
  kind='cursor' if stem.endswith('cursor') else 'confirmation'
  native=f'option30-{kind}-fullframe-{digest[:12]}.png'
  large=f'option30-{kind}-fullframe-x3-{digest[:12]}.png'
  (ui/native).write_bytes(raw);im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST).save(ui/large)
  ram=(ui/(stem+'-ram.bin')).read_bytes();meta=json.loads((ui/(stem+'.json')).read_text())
  items.append({'kind':kind,'original_file':source.name,'original_sha256':digest,'native_fullframe':native,
    'enlarged_fullframe':large,'enlarged_dimensions':[im.width*3,im.height*3],
    'enlargement':'nearest-neighbor3x of entire frame; no cropping','paired_zoom':zoom,'zoom_crop':list(crop),'zoom_factor':factor,
    'zoom_pixel_equality':True,'paired_ram':stem+'-ram.bin','paired_ram_sha256':hashlib.sha256(ram).hexdigest(),
    'core_frame':meta['frames'],'main0500':ram[0x500],'sub0501':ram[0x501],'cursor0012':ram[0x12],
    'destination_list042C':list(ram[0x42C:0x430]),'chosen0540':ram[0x540]})
 if not items:return
 manifest={'rom_sha256':ROM_SHA256,'synthetic_fixture':True,'items':items,
    'pixel_note':'Hash-named current filesystem frames are verified against their own zoom and paired RAM. A browser response showing another officer/scene must be compared to these file hashes before attributing it to the fixture.'}
 (ui/'image-integrity.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 evidence=out/'evidence.json'
 if evidence.exists():
  payload=json.loads(evidence.read_text());links=payload['glyph_provenance']
  for item in items:
   key='image' if item['kind']=='cursor' else 'confirmation_image'
   links[key]='synthetic-ui/'+item['native_fullframe']
   links[key+'_enlarged']='synthetic-ui/'+item['enlarged_fullframe']
  links['image_integrity']='synthetic-ui/image-integrity.json'
  evidence.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')

def capture_ui(rom_path,out):
 import ctypes as C
 from nes_runtime import Runtime
 ui=out/'synthetic-ui';r=Runtime(rom_path,ui)
 try:
  r.load_state(ROOT/'analysis/runtime/phase3/attack-intro-7.state')
  ram=(C.c_ubyte*r.core.retro_get_memory_size(2)).from_address(r.core.retro_get_memory_data(2))
  sram=(C.c_ubyte*r.core.retro_get_memory_size(0)).from_address(r.core.retro_get_memory_data(0))
  patches={'RAM':{'0500':13,'0501':1,'050B':17,'050E':11,'062A':128},'SRAM':{}}
  for key,value in patches['RAM'].items():ram[int(key,16)]=value
  address=32*4;sram[address]=(sram[address]&240)|2;patches['SRAM'][f'{0x6000+address:04X}']=int(sram[address])
  for offset in range(17,27):sram[address+offset]=255;patches['SRAM'][f'{0x6000+address+offset:04X}']=255
  r.events.append({'synthetic_fixture':True,'base':'natural attack-intro-7.state','patches':patches,'rom_writes':0})
  r.run(60);r.run(8,['a']);r.run(120);r.snapshot('main13-destination-menu')
  count=r.memory(2)[0x50A]
  for i in range(count):r.run(2,['down']);r.run(10)
  if r.memory(2)[0x12]!=count:r.run(2,['right']);r.run(10)
  current=r.memory(2)
  if current[0x42C+current[0x12]]!=30:raise RuntimeError('Fixture cursor did not select option30')
  r.snapshot('main13-option30-cursor')
  r.run(8,['a']);r.run(180);r.snapshot('main13-option30-confirmation')
  from PIL import Image
  im=Image.open(ui/'main13-option30-cursor.png');im.crop((140,176,232,200)).resize((736,192),Image.Resampling.NEAREST).save(ui/'option30-glyph-zoom.png')
  im=Image.open(ui/'main13-option30-confirmation.png');im.crop((24,164,256,224)).resize((928,240),Image.Resampling.NEAREST).save(ui/'option30-confirmation-zoom.png')
  (ui/'provenance.json').write_text(json.dumps({'rom_sha256':hashlib.sha256(rom_path.read_bytes()).hexdigest(),'synthetic_fixture':True,'patches':patches,'events':r.events,'limitations':['Only UI glyphs and controller linkage are being observed; this is not a natural defeat trajectory.']},ensure_ascii=False,indent=2)+'\n')
 finally:r.close()

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase4/postbattle');p.add_argument('--render-ui',action='store_true');a=p.parse_args()
 analyze(a.rom.read_bytes(),a.out)
 if a.render_ui:capture_ui(a.rom,a.out)
 freeze_ui_images(a.out)
