#!/usr/bin/env python3
"""Pin bounded original graphics data services and independently tested source."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES,disassemble
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
 f=ROOT/path;return dict(path=path,bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
def ranged(rom,name,bank,start,end,kind):
 offset=16+bank*8192+(start&8191);raw=rom[offset:offset+end-start]
 return dict(name=name,physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,byte_count=len(raw),raw_hex=raw.hex(' ').upper(),sha256=sha(raw),kind=kind)
def finalize_bundle(rom,out,source,validator,analyzer,regions,deps,*,schema,contracts,archives=()):
 assert sha(rom)==SHA;out.mkdir(parents=True,exist_ok=True)
 v=json.loads((out/'validation.json').read_text());assert v['status']=='passed'and v['failed_count']==0 and not v['quick']
 assert v['source_sha256']==pin(source)['sha256'];assert v['validator_sha256']==pin(validator)['sha256']
 ranges=[];tables=[];listing=[];local_locations=set()
 for name,bank,start,end,kind in regions:
  item=ranged(rom,name,bank,start,end,kind);(ranges if kind=='code'else tables).append(item)
  listing.append(f'; {name}: physical{bank} ${start:04X}..${end-1:04X}, file0x{item["rom_offset"]:06X}, {kind}\n')
  if kind=='code':
   pc=start
   while pc<end:
    op,mode=OPS[rom[16+bank*8192+(pc&8191)]];size=SIZES[mode];assert op!='?'and pc+size<=end,(name,hex(pc),op)
    local_locations.add((bank,pc));pc+=size
   listing.append(disassemble(rom,bank,0xA000 if bank%2 else 0xC000,start,end))
  else:
   raw=bytes.fromhex(item['raw_hex'])
   for i in range(0,len(raw),16):listing.append(f'{item["rom_offset"]+i:06X} b{bank}:${start+i:04X} .byte '+','.join(f'${b:02X}'for b in raw[i:i+16])+' ; DATA\n')
  listing.append('\n')
 (out/'original-ranges.asm').write_text(''.join(listing))
 # No execution machinery is permitted in production source imports/calls.
 tree=ast.parse((ROOT/source).read_text());imports=[n.module for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)]
 assert not any(x and(x.startswith('py65')or x in('runtime_services','battle_state_machine','duel_state_machine'))for x in imports)
 assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in('exec','eval','compile')for n in ast.walk(tree))
 actual=json.loads((out/'executed-instructions.json').read_text());observed={(r['physical_bank'],r['cpu_address'])for r in actual}
 primary_observed=observed&local_locations
 dependencies=[pin(x)for x in dict.fromkeys((source,validator,analyzer,*deps))]
 e=dict(schema=schema,rom_sha256=SHA,ROM_modified=False,ranges=ranges,tables=tables,dependency_pins=dependencies,REA_archive=[pin(x)for x in archives],
  disassembly_pin=pin(str((out/'original-ranges.asm').relative_to(ROOT))),source_AST_imports=imports,source_runtime_IR=False,source_runtime_CPU=False,source_runtime_opcode_decode=False,source_original_CPU_callbacks=0,
  source_sha256=v['source_sha256'],validator_sha256=v['validator_sha256'],
  local_instruction_location_total=len(local_locations),local_instruction_location_observed=len(primary_observed),local_unobserved_locations=[dict(physical_bank=b,cpu_address=pc,rom_offset=16+b*8192+(pc&8191))for b,pc in sorted(local_locations-primary_observed)],
  validation={k:v[k]for k in('status','rom_cpu_case_count','original_complete_case_count','original_prefix_case_count','source_guard_case_count','failed_count','counts','comparison')},contracts=contracts)
 (out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
 v.update(evidence_sha256=sha((out/'evidence.json').read_bytes()),analyzer_sha256=pin(analyzer)['sha256'],dependency_pins=dependencies,local_instruction_location_total=len(local_locations),local_instruction_location_observed=len(primary_observed))
 (out/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
 return e,v

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/graphics');a=p.parse_args();rom=a.rom.read_bytes()
 regions=[('public_chunk_attribute_unit_trampolines',23,0xA012,0xA01B,'code'),('chunk_resource_pointer_helper',23,0xA61C,0xA642,'code'),('attribute_resource_pointer_helper',23,0xAEF0,0xAF0C,'code'),('unit_tile_controller_leader_strength_affinity',23,0xA983,0xAAE4,'code'),
  ('chunk_pointer_table120',23,0xA642,0xA732,'data'),('attribute_pointer_table120',23,0xA732,0xA822,'data'),('data_window_selector_table120',23,0xA822,0xA89A,'data'),('three_unit_tile_families',23,0xAAE4,0xAB26,'data')]
 contracts=dict(APIs=['UIGraphicsInitialization(memory,UIGraphicsData.from_rom(rom),services=None)','run_entry(entry=A012,registers)','__call__(ServiceCall)','resume()'],entry_mappings={'23A012':'23A61C..A641','23A015':'23AEF0..AF0B','23A018':'23A983..AAE3'},
  caller='Real physical23/24 pair and existing RTS frame. Exact AXYP/SP/PC, all2048RAM including stack residue, all8192SRAM, orderedE000 writes and finalbanks are compared.',
  input_domains={'0000_chunk':'0..119, original120-row pointer/mapper tables','0000_slot':'active0..19','063C+slot':'displayed strength-hundreds0..10','0507':'two ruler nibbles, selected nibble0..6','0628+slot':'highbit selects ruler nibble; low2 choose original affinity tiles','6F07+8*ruler+3':'controller raw0,1,other select three visual families'},
  output={'A012':'0000/1 mapped chunk pointer,0002/3 fixedF477 metatile pointer; Y data selector and actualF25F port request','A015':'0000/1 mapped attribute pointer and actualF25F;0002/3 unchanged','A018':'01B0..01B3 four original unit tiles;0000/1 restored by ruler lookup; no PPU/OAM upload'},
  helper_providers={'F25F':'SceneSharedServices exact stack/mapper request','F368':'SceneSharedServices original ruler pointer/table'},
  distinction='Bank13D72E is an existing map-refresh JSR site whose far target is23A012. It is not the entry/body of23A012.',limits=['No pixels, CHR writes, DMA, queue completion, IRQ/NMI timing or frame emulation.','The displayed hundreds cache is a tile selector, not raw troop count.','Undefined chunks>=120, slots>=20, rulers>=7 and cache>10 are explicit source guards, not invented wrapping rules.'])
 archives=[str(x.relative_to(ROOT))for x in(ROOT/'analysis/rea/pairs/pair-23/functions').glob('*')if x.stem in('0xa61c','0xa983','0xaef0')and x.suffix in('.asm','.c')]
 e,v=finalize_bundle(rom,a.out,'source/recovered/ui_graphics_initialization.py','scripts/verify_ui_graphics_initialization.py','scripts/analyze_ui_graphics_initialization.py',regions,['source/recovered/scene_shared_services.py','source/recovered/battle_nmi_services.py','source/recovered/controller_helpers.py','source/recovered/service_memory.py'],schema='phase13-ui-graphics-data-v1',contracts=contracts,archives=archives)
 (a.out/'README.md').write_text(f'''# 阶段13：真实图形数据服务调用协议

恢复physical23/24三个有界服务：`A012→A61C`选择地图块指针及数据窗；`A015→AEF0`选择属性指针及数据窗；`A018→A983`根据阵营控制方式、主将位置、显示兵力缓存和地形适性产生四个单位tile。生产源码是具名函数与普通if/loops，没有IR、opcode解释或原CPUfallback。已有BattleGraphicsServices曾具备这些结果的语义计算；本模块补真实caller栈、所有flags和mapper协议。

原120组chunk/attribute pointers和120个mapper selector逐条保持。输入0000的active slot0..19、063C显示缓存0..10、选中0507 ruler nibble0..6有明确源合同。单位控制byte0、1、其余原值分别选择三套字形；slot0/10有原主将覆写，满缓存10另有原字形覆写；affinity3保留各套默认字形，不赋不存在的正式名称。

`23A012`真实bytes是`4C1CA6`。`13D72E`是调用该服务的map-refresh位置，不能把它当本服务body。`29A012→BC41`是另一个独立入口，未混入这里。

最终{v['rom_cpu_case_count']}原CPU完整返回病例，另{v['source_guard_case_count']}source guards，0失败；本地动态位置{e['local_instruction_location_observed']}/{e['local_instruction_location_total']}。比较全部2048RAM（含实际stack残留）、8192SRAM、AXYP/SP/PC、端口写序与mapper banks。矩阵覆盖全部120块×两个exports/两个bodies×flags，20slot×11cache×4affinity×4controller raw值×2侧。CPU fixtures是明确准备的合法输入矩阵，不是自然游戏帧。这里没有PPU读取，F25F仅产生真实E000写请求；不上传nametable、合成帧或清ready。

```python
owner = UIGraphicsInitialization(memory, UIGraphicsData.from_rom(rom))
result = owner(actual_ServiceCall)  #actual23/24pair + real RTS frame
```

- [独立源码](../../../source/recovered/ui_graphics_initialization.py)
- [CPU对照与最终pins](validation.json)
- [原bytes、表和调用合同](evidence.json)
- [原汇编及明确数据](original-ranges.asm)
- [原CPU实际执行位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_ui_graphics_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_ui_graphics_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
''')
 print(json.dumps(dict(status='passed',CPU=v['rom_cpu_case_count'],guards=v['source_guard_case_count'],source=v['source_sha256'])))
if __name__=='__main__':main()
