#!/usr/bin/env python3
"""Pinned original portrait bytes, all237 identity maps and diagnostic pixels."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys,ast
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import disassemble,instruction
from source.recovered.portrait_ui_services import ROM_SHA256
def digest(data):return hashlib.sha256(data).hexdigest()
def pin(path):return dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,sha256=digest(path.read_bytes()))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase12/portraits');a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA256;a.out.mkdir(parents=True,exist_ok=True)
 def ranged(name,bank,start,end,kind='code',base=None):
  base=(0xE000 if bank==31 else 0xC000 if bank==26 else 0xA000 if bank==25 else 0x8000)if base is None else base
  offset=16+bank*8192+start-base;raw=rom[offset:offset+end-start]
  return dict(name=name,physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,byte_count=len(raw),raw_hex=raw.hex(' ').upper(),sha256=digest(raw),kind=kind)
 ranges=[ranged('public_portrait_trampoline',25,0xA000,0xA003),ranged('two_layer_portrait_body',26,0xCE1F,0xCED6),ranged('caller_parameter_OAM_variant',31,0xF1B7,0xF206),ranged('actual_data_window_mapper',31,0xF25F,0xF266)]
 tables=[ranged('officer_CHR_pages237',26,0xCED6,0xCFC3,'data'),ranged('adjacent19_ID_reads_are_not_officers',26,0xCFC3,0xCFD6,'adjacent_data'),
  ranged('portrait_base_frame_index237',1,0x99A0,0x9A8D,'data'),ranged('adjacent19_base_indices',1,0x9A8D,0x9AA0,'adjacent_data'),
  ranged('body20_pointers',1,0x9AA0,0x9AC8,'pointer_data'),ranged('body4_templates',1,0x9AC8,0x9BAC,'sprite_data'),
  ranged('ordinary_mouth20_pointers',1,0x9BAC,0x9BD4,'pointer_data'),ranged('ordinary_mouth16_templates',1,0x9BD4,0x9D64,'sprite_data'),
  ranged('talking_mouth20_pointers',1,0x9D64,0x9D8C,'pointer_data'),ranged('talking_mouth16_templates',1,0x9D8C,0x9F1C,'sprite_data'),
  ranged('identity_name_glyphs237_x13',17,0x8DB4,0x99BD,'identity_data')]
 def byte(address):return rom[0x2010+address-0x8000]
 def word(address):return byte(address)|byte(address+1)<<8
 def sprite(pointer):
  records=[]
  for index in range(64):
   addr=pointer+4*index
   if byte(addr)==128:return records
   records.append(list(rom[0x2010+addr-0x8000:0x2010+addr-0x8000+4]))
  raise ValueError('Expected original terminated sprite template')
 templates={};identities=[];CHR_ranges=[]
 pages=sorted(set(rom[0x34EE6:0x34EE6+237]))
 for page in pages:
  off=0x40010+1024*page;raw=rom[off:off+1024];CHR_ranges.append(dict(name=f'portrait_CHR_page_{page:02X}',rom_offset=off,byte_count=1024,raw_hex=raw.hex(' ').upper(),sha256=digest(raw),kind='CHR_2bpp_data'))
 for ident in range(237):
  base=byte(0x99A0+ident);frames=[]
  for frame in range(5):
   index=(base+frame)*2;record=dict(frame=frame,pointer_byte_index=index,body_pointer=word(0x9AA0+index),ordinary_mouth_pointer=word(0x9BAC+index),talking_mouth_pointer=word(0x9D64+index))
   for key in('body_pointer','ordinary_mouth_pointer','talking_mouth_pointer'):
    pointer=record[key];templates.setdefault(hex(pointer),dict(cpu_address=pointer,rom_offset=0x2010+pointer-0x8000,records=sprite(pointer),terminator=128))
   frames.append(record)
  nameoff=0x22DC4+13*ident;name=rom[nameoff:nameoff+13]
  identities.append(dict(officer_id=ident,CHR_page=rom[0x34EE6+ident],base_frame_index=base,frames=frames,
   name_glyph_record=dict(rom_offset=nameoff,raw_hex=name.hex(' ').upper(),sha256=digest(name),CHR_page=name[0],tile_indices=list(name[1:])),unicode_name_not_inferred=True))
 # NES2bpp/sprite descriptor interpretation, independent of an original core.
 def tile(page,index):
  raw=rom[0x40010+1024*page+16*index:0x40010+1024*page+16*index+16]
  return [[((raw[y]>>(7-x))&1)|(((raw[y+8]>>(7-x))&1)<<1)for x in range(8)]for y in range(8)]
 sheet=Image.new('RGB',(8*88,30*72),(248,246,240));draw=ImageDraw.Draw(sheet)
 for item in identities:
  ident=item['officer_id'];x0=(ident%8)*88;y0=(ident//8)*72;pixels={};frame=item['frames'][0]
  for key in('body_pointer','ordinary_mouth_pointer'):
   for dy,t,attr,dx in templates[hex(frame[key])]['records']:
    grid=tile(item['CHR_page'],t&63)
    for yy in range(8):
     for xx in range(8):
      value=grid[7-yy if attr&128 else yy][7-xx if attr&64 else xx]
      if value:pixels.setdefault((dx+xx,dy+yy),value) # original lower OAMindex wins
  for(x,y),value in pixels.items():
   if 0<=x<32 and 0<=y<32:sheet.putpixel((x0+28+x,y0+4+y),((205,205,205),(125,125,125),(25,25,25))[value-1])
  name=item['name_glyph_record'];j=0
  for t in name['tile_indices']:
   if t==255:break
   xx=16*(j//4)+8*(j%2);yy=8*((j%4)//2);grid=tile(name['CHR_page'],t)
   for y in range(8):
    for x in range(8):
     if grid[y][x]:sheet.putpixel((x0+20+xx+x,y0+38+yy+y),(35,35,35))
   j+=1
  draw.text((x0+26,y0+56),f'{ident:03d} / {item["CHR_page"]:02X}',fill=(60,60,60))
 atlas=a.out/'portrait-identity-atlas.png';sheet.save(atlas)
 # Raw CPU/data listings are pinned; pointer/descriptor bytes are never opcodes.
 lines=[]
 for item in ranges+tables:
  lines.append(f'; {item["name"]} physical{item["physical_bank"]} ${item["cpu_start"]:04X} file0x{item["rom_offset"]:06X} {item["kind"]}\n')
  if item['kind']=='code':lines.append(disassemble(rom,item['physical_bank'],0xE000 if item['physical_bank']==31 else 0xC000 if item['physical_bank']==26 else 0xA000,item['cpu_start'],item['cpu_end_exclusive']))
  else:
   raw=bytes.fromhex(item['raw_hex'])
   for i in range(0,len(raw),16):lines.append(f'{item["rom_offset"]+i:06X} ${item["cpu_start"]+i:04X} .byte '+','.join(f'${v:02X}'for v in raw[i:i+16])+'\n')
 (a.out/'original-ranges.asm').write_text(''.join(lines));(a.out/'identity-mappings.json').write_text(json.dumps(dict(officers=identities,templates=templates),ensure_ascii=False,indent=2)+'\n')
 validation=json.loads((a.out/'validation.json').read_text());assert validation['status']=='passed'and not validation['quick'];source=ROOT/'source/recovered/portrait_ui_services.py';tree=ast.parse(source.read_text())
 imports=[n.module for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)];assert not any(n in('py65','runtime_services','battle_state_machine')for n in imports)
 pins=[pin(source),pin(ROOT/'scripts/verify_portrait_ui_services.py'),pin(Path(__file__)),pin(ROOT/'source/recovered/battle_nmi_services.py'),pin(ROOT/'source/recovered/service_memory.py')]
 archive=[pin(p)for p in(ROOT/'analysis/rea/pairs/pair-25/functions').glob('*')if p.stem in('0xce1f','0xf1b7','0xf25f')and p.suffix in('.asm','.c')]
 e=dict(schema='phase12-portrait-ui-v1',rom_sha256=ROM_SHA256,ROM_modified=False,ranges=ranges,tables=tables,CHR_data_ranges=CHR_ranges,dependency_pins=pins,REA_archive=archive,
  disassembly_pin=pin(a.out/'original-ranges.asm'),identity_mapping_pin=pin(a.out/'identity-mappings.json'),diagnostic_atlas=pin(atlas),
  source_runtime_original_CPU=False,source_runtime_IR=False,source_AST_imports=imports,source_external_helper_callbacks=0,
  APIs=['PortraitUIServices(memory,PortraitData.from_rom(rom),services=None)','run_entry(A000/CE1F/F1B7/F25F,registers)','portrait(registers)','__call__(ServiceCall)','resume()'],
  caller_contract='Actual existing RTS frame consumed; all AXYP/SP/PC, fullRAM including CPUstack, fullSRAM, exactE000 write and bank normalized33→1 validated. ParentEE07 restores pair outside this callee.',
  officer_count=237,unique_CHR_pages=len(pages),frame_base_counts=dict(Counter(item['base_frame_index']for item in identities)),body_template_count=4,mouth_template_count_per_kind=16,
  input_fields={'0000':'8bitofficerID; namedofficers0..236;237..255 originaladjacentdata reads retained, not identities','X&1':'left/righttileoffset00/40 andCHRshadowB8/B9','000A':'unsignedscreenY','04BC':'screenXoverride;0means16;thenreset0','A4':'low3frame;bit7forcesordinarymouth','6FEA&4':'forceA4=3','6FEA&8':'forceA4=4 overridingbit4','7C':'actualOAMbytecursor,FFsaturated','7E/0304/0303/5E':'talkingmouthpredicate, noqueueack'},
  request_effects=['F25F selector33 selects physicalPRG1; source onlywritesE000 andE1 cache.','B8/B9CHRpage caches consumed by originalIRQ CHRports later; thiscallee doesnot uploadCHR or palette.',
   'Body14+mouth6 records give20sprites/80 OAMbytes beforeclipping or saturation.','m03tileoffset,m04absoluteYcutoff160,m02attributeXOR0 retained across F1B7. m05written0butnotconsumed.',
   'TalkingonlyifA4bit7clear,7Ebit0set,0304!=FF,0303==0,5Ebit3set.','Coordinates/additions/OAMwrites useoriginal8bitregisterwrap, includingOAMrecords crossing02FF for unalignedcursor.',
   'No palettewrite, textpacket, numericalattribute card, OAM DMA, PPU ack, frameorPCM synthesis occurs.'],
  frame_domain='Namedportraitframes0..4 address20originalpointerentries. A4mask admits5..7 mechanically; those canselectnextgroup or readadjacentbytes, so not labelledvalidnamedposes.',
  validation={k:validation[k]for k in('status','rom_cpu_case_count','original_complete_case_count','original_prefix_case_count','source_guard_case_count','failed_count','counts','comparison','source_original_CPU_callbacks','actual_call_fixtures')},
  atlas_contract='Diagnosticgray NES2bpp decoding of originalCHR/templates plus originalnameglyph pixels, frame0. Not a core screenshot, original palette or an OCR transcription.')
 (a.out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
 validation['evidence_sha256']=digest((a.out/'evidence.json').read_bytes());validation['dependency_pins']=pins
 (a.out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
 readme=f'''# Phase12 肖像实际服务

physical25 `$A000`只跳转到physical26 `$CE1F`，实际构造两层绝对屏幕OAM肖像，不是数字属性资料卡。独立`PortraitUIServices`用具名Python函数/条件/循环和真实callerowned generator执行；运行时不解释opcode/IR、不读program.json、不调用原CPU或空renderer。原ROM只作immutable数据。

`0000`选择武将，`X&1`选择左/右CHR缓存B8/B9及tile加00/40，`000A`是Y，`04BC`是Xoverride（0→16，用后清0）。`A4`低3位选择帧，bit7强制普通嘴部；SRAM6FEA bit2强制帧3，bit3再强制帧4。主体14个sprite，再加嘴部6个；固定F1B7保留caller03tileoffset/04cutoff160/02attributeXOR，不能用F1AD的清03/04前序替代。unsigned坐标/索引/溢出、FF满OAM、80descriptor终止全部保留。

原F25F写E1=33及E000=33，mapper将33映射到physical1资料窗。237肖像分别映射{len(pages)}个1KiB CHR页；baseindex0/5/10/15与五个正规帧构成20pointer条目。B8/B9只是CHR缓存，真实IRQ之后才写9000/9800。此入口不请求palette、文本包、数字参数卡、OAM DMA或完成PPU绘制。父EE07的银行保存/恢复在callee之外，服务只消费原callee现有RTS帧。

普通嘴部与说话嘴部严格使用原谓词：A4bit7clear、7Ebit0set、0304非FF、0303为0、5Ebit3set。任何一个不成立使用普通图形。237..255字节ID原程序会读相邻data，源码保留这些行为但不把它们称作额外武将；低3frame5..7也可能读下一组/相邻bytes，不能称正式姿势。

最终{validation['rom_cpu_case_count']}原CPU病例（{validation['original_complete_case_count']}完整RTS、{validation['original_prefix_case_count']}真实循环prefix）和{validation['source_guard_case_count']}单列guards，0失败。包含全部237身份×两槽×五帧×两嘴部、完整五谓词和6FEA覆盖顺序、signedA4、坐标/裁剪/溢出/OAM边界、相邻ID、F1B7任意caller参数，以及3个原attack CPU实际callee帧；后者保留原寄存器/SP/返回栈，无stack准备。这些原CPU捕获来自明示条件矩阵，不是native核心内部trace。生产外部原CPUhelper数=0。

逐字节对照全部2048RAM（含CPUstack残留）、8192SRAM、AXYP/SP/PC、mapper与端口序。缺失终止/无法饱和的原循环真正停pending并可同owner续跑，不fakeRTS；源码guard检查unknownentry、真实caller/mapper、pending重入和unknowncallee。图形的请求范围不等于一帧NES硬件执行。

```python
owner = PortraitUIServices(memory, PortraitData.from_rom(rom))
result = owner(actual_ServiceCall)  #真实caller register、SP、returnPC
# 或owner.run_entry(0xA000, actual_registers)
```

- [具名独立源码](../../../source/recovered/portrait_ui_services.py)
- [CPU回执/guards/pins](validation.json)
- [原bytes、CHR数据与REA来源](evidence.json)
- [代码与明确data反汇编](original-ranges.asm)
- [全部237身份、五帧及模板映射](identity-mappings.json)
- [姓名/肖像像素诊断图](portrait-identity-atlas.png)：原2bpp数据/模板灰度解码，不是真实截图、原palette或OCR；数字是ID/CHR页。

```sh
.venv-trace/bin/python scripts/verify_portrait_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_portrait_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
'''
 (a.out/'README.md').write_text(readme)
 print(json.dumps(dict(status='passed',CPU=validation['rom_cpu_case_count'],guards=validation['source_guard_case_count'],officers=237,CHRpages=len(pages),templates=len(templates),evidence_sha256=validation['evidence_sha256']),ensure_ascii=False))
if __name__=='__main__':main()
