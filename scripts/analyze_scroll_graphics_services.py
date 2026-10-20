#!/usr/bin/env python3
"""Pin original-byte ranges and the tested readable map-scroll services."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import disassemble,OPS,SIZES
from source.recovered.scroll_graphics_services import ROM_SHA256,DECLARED_RAM_ADDRESSES
RANGES=(
 ('scroll_entry_trampolines',23,0xA000,0xA00C,0xA012,'code'),
 ('tile_scroll_control_and_quadrants',23,0xA000,0xA387,0xA604,'code'),
 ('descriptor_and_primary_chunk_helpers',23,0xA000,0xA604,0xA642,'code'),
 ('chunk_pointer_attribute_pointer_and_mapper_tables',23,0xA000,0xA642,0xA89A,'data'),
 ('nametable_and_attribute_request_headers',23,0xA000,0xA89A,0xA8FD,'code'),
 ('tile_unit_overlay_and_lookup',23,0xA000,0xA8FD,0xA983,'code'),
 ('shared_recovered_unit_tiles',23,0xA000,0xA983,0xAAE4,'code'),
 ('unit_tile_rows',23,0xA000,0xAAE4,0xAB26,'data'),
 ('camera_to_unit_coordinates',23,0xA000,0xAB26,0xAB53,'code'),
 ('attribute_scroll_control_lookup_overlay_and_merge',23,0xA000,0xAB53,0xB100,'code'),
 ('actual_primary_data_window_helper',31,0xE000,0xF25F,0xF266,'code'),
 ('shared_controller_record_pointer_helper',31,0xE000,0xF368,0xF379,'code'),
 ('controller_record_pointer_table',31,0xE000,0xF379,0xF387,'data'),
 ('background_metatiles',31,0xE000,0xF477,0xF877,'data'),
 ('NMI_battle_scroll_conditions_and_calls',31,0xE000,0xF923,0xF93D,'context_code'),
)
TABLES=(('primary_chunk_pointers',23,0xA000,0xA642,0xA732),
 ('attribute_chunk_pointers',23,0xA000,0xA732,0xA822),
 ('chunk_primary_window_selectors',23,0xA000,0xA822,0xA89A),
 ('unit_tiles',23,0xA000,0xAAE4,0xAB26),
 ('background_2x2_metatiles',31,0xE000,0xF477,0xF877))
def sha(b):return hashlib.sha256(b).hexdigest()
def pin(p):
 f=ROOT/p;return dict(path=p,sha256=sha(f.read_bytes()),bytes=f.stat().st_size)
def row(rom,name,bank,base,start,end,kind):
 off=16+8192*bank+start-base;raw=rom[off:off+end-start]
 return dict(name=name,physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,cpu_base=base,rom_offset=off,byte_count=len(raw),raw_hex=raw.hex(' ').upper(),sha256=sha(raw),kind=kind)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase10/scroll');a=p.parse_args()
 rom=a.rom.read_bytes();assert sha(rom)==ROM_SHA256;out=a.out;out.mkdir(parents=True,exist_ok=True)
 validation=json.loads((out/'validation.json').read_text());assert validation['status']=='passed'and not validation['quick']and not validation['failed_count']
 source=pin('source/recovered/scroll_graphics_services.py');validator=pin('scripts/verify_scroll_graphics_services.py')
 assert source['sha256']==validation['source_sha256']and validator['sha256']==validation['validator_sha256']
 listing=[];ranges=[];locations=set()
 for name,bank,base,start,end,kind in RANGES:
  r=row(rom,name,bank,base,start,end,kind);ranges.append(r);listing.append(f'; {name} b{bank}:${start:04X}..${end-1:04X}, file0x{r["rom_offset"]:06X}, {kind}\n')
  if kind.endswith('code'):
   pc=start
   while pc<end:
    off=16+bank*8192+pc-base;op,mode=OPS[rom[off]];size=SIZES[mode]
    assert op!='?'and pc+size<=end,(name,hex(pc),op)
    if kind=='code':locations.add((bank,pc))
    pc+=size
   listing.append(disassemble(rom,bank,base,start,end))
  else:
   raw=bytes.fromhex(r['raw_hex'])
   for i in range(0,len(raw),16):listing.append(f'{r["rom_offset"]+i:06X} b{bank}:${start+i:04X} .byte '+','.join(f'${v:02X}'for v in raw[i:i+16])+' ; DATA\n')
  listing.append('\n')
 executed=json.loads((out/'executed-instructions.json').read_text())
 actual={(r.get('physical_bank',r.get('bank')),r.get('cpu_address',r.get('cpu')))for r in executed}
 assert actual<=locations,actual-locations
 tree=ast.parse((ROOT/source['path']).read_text());imports=[n.module for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)]
 assert imports==['battle_graphics_services','officers']
 e=dict(schema='phase10-scroll-services-v1',rom_sha256=ROM_SHA256,ROM_modified=False,source_uses_IR_or_original_CPU=False,
        ranges=ranges,tables=[row(rom,n,b,base,s,e,'data')for n,b,base,s,e in TABLES],
        dependency_pins=[source,validator,pin('scripts/analyze_scroll_graphics_services.py'),pin('source/recovered/battle_graphics_services.py'),
                         pin('source/recovered/service_memory.py'),pin('source/recovered/audio_services.py')],REA_archive=[],source_AST_imports=imports,
        APIs=['ScrollGraphicsServices(memory,GraphicsData.from_rom(rom))','tile_scroll(registers=None)','attribute_scroll(registers=None)'],
        entry_mapping={'tile_scroll':dict(physical_bank=23,trampoline=0xA00C,body=0xA387),
                       'attribute_scroll':dict(physical_bank=23,trampoline=0xA00F,body=0xAB53)},
        NMI_caller=dict(physical_bank=31,guard=0xF923,conditions='0500<12 and 008F==0',logical_selector=0x37,
                        tile_call=0xF937,attribute_call=0xF93A),
        input_fields={'008E..0091':'camera low/high X,Y','0092/0093':'tile Y/X cached quotient','0094/0095':'attribute Y/X cached quotient',
                      '009C':'original direction bits','007E':'pending tile/attribute request flags','00A8/A9':'current mapped map-descriptor pointer',
                      '0600/0614':'20unit coordinate arrays','0628/063C':'unit side/affinity and strength tile cache','0507':'two ruler nibbles',
                      '6F07+8*ruler+3':'controller raw value used by recovered unit tile helper'},
        output_requests=[dict(kind=k,address=a,request_bit=b)for k,a,b in [('tile_column',0x140,128),('tile_row',0x164,64),('attribute_column',0x188,32),('attribute_row',0x19C,16)]],
        mechanics=['Tile X normalized FE/FF+2 wrap then>>3; caches are updated before busy helpers.',
                   'Tile service may queue both column and row in one call. Busy gates are007E bit7/bit6.',
                   'Attribute X subtract6 then>>3; changed column has priority and immediately returns; attribute helpers have no busy gate.',
                   '16 column metatiles/17 row metatiles; initial half-tile is skipped exactly, retaining old buffer tail.',
                   'Descending unit slot scans preserve lowest slot on duplicate coordinates; there is no officer-ID active filter.',
                   'Vertical tile seams skip the packed row15 gap and increment unit Y an extra step.',
                   'Attribute 8/9 byte paths preserve first-byte half merging and temporary0002 masks.',
                   'Primary chunks emit actualE000 selector writes; secondary attribute pointer lookup does not emit a second mapper write.',
                   'Header page parity branches both choose20(tile) or23(attribute), preserving originalbytes.',
                   'Unit replacement A8FD/A91E has a real two-return stack unwind; source models its semantic early route, not stack residue.',
                   'Tile row back-edge low addsF0 then subtracts10 ifcarry clear; high increments/decrements literally.'],
        scope=dict(independent_readable_request_builders=True,PPU_consumption=False,rendered_pixels=False,DMA=False,
                   readiness_ack=False,frame_timing=False,IRQ_or_NMI_completion=False,body_registers='AXYP exact; caller SP preserved, actualRTS external',
                   caller_stack='Default CPUfixture SPFD, no active stack overlap with0140..01B3 scrolldata; free stack residue excluded',
                   RAM_addresses=list(DECLARED_RAM_ADDRESSES),SRAM_bytes=8192),
        static_service_instruction_count=len(locations),dynamic_service_instruction_count=len(actual),
        instruction_address_coverage='Observed instruction addresses, not all CPUvalue/branch combinations or renderedframe proof',
        validation={k:validation[k]for k in ('status','rom_cpu_case_count','source_guard_case_count','case_count','failed_count','original_complete_case_count','original_prefix_case_count','counts')})
 (out/'original-ranges.asm').write_text(''.join(listing));e['disassembly_pin']=pin(str((out/'original-ranges.asm').relative_to(ROOT)))
 (out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
 validation['evidence_sha256']=sha((out/'evidence.json').read_bytes());validation['static_service_instruction_count']=len(locations);validation['dynamic_service_instruction_count']=len(actual)
 (out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
 (out/'README.md').write_text(f'''# Phase10 地图行列滚屏请求

独立可读 `ScrollGraphicsServices` 恢复 physical23 A00C→A387 与 A00F→AB53。前者构造 BG tile 行/列请求，后者构造 attribute 行/列请求。源码不解释原6502/IR，不回退原CPU执行，不消费PPU队列，不绘制像素、不完成DMA/IRQ/NMI，也不清除等待标志。根线程的原核心画面与服务集成属于另外的证据层。

原NMI战场路径 fixed31 F923 检查 `0500<12`、`008F==0`，选择logical37/physical23/24，F937调用A00C，F93A调用A00F。本模块调用从这两个合法入口的函数体开始；外部bankcall映射与真实callerRTS由调用方维持。

tile服务比较相机X/Y的8像素缓存；X为FE/FF时先+2回绕。原代码先写0093/0092缓存，即使007E bit7/bit6已忙也不撤销缓存。一次调用可构造列和行。列取16个metatile、行取17个；初始半tile按原分支跳过，旧缓冲尾未写部分保留。跨垂直packed row15边界会额外推进unitY并切换真实E000数据bank；横向列15边界保留原nibble回绕。

attribute服务先算 `(cameraX-6)&FF >>3`，列变化优先并立即返回；只有列未变时才检查Y的16像素缓存。属性helper没有tile busy检查。8/9字节路径保留第九项合并回首字节的顺序、0002的临时mask，以及primary/secondary两个地图块属性的混合。secondary pointer读表不再写mapper，原当前window语义保留。009C bit6=1选当前primary列，bit6=0交换primary邻列；bit4=1选当前row，bit4=0选垂直前沿+A0与原F0 gap处理。

单位坐标按slot19→0扫描，同坐标最后保留较小slot；原代码不额外检查officer-ID或擅自过滤inactive。BG单位4tile复用已冻结 `BattleGraphicsServices.unit_tiles`；按原controller/strength/affinity取字形，且保存00/01指针。palette覆盖保留原四quadrant palette2及跨缝查找。header奇偶两分支原来都用20/23，本源码保留而不替ROM修正。A8FD/A91E单位路线在原CPU实际弹出两层return再进入对应quad绘制；高层源码恢复该分支的作用，空闲栈残留不属于合同。

最终 {validation['rom_cpu_case_count']} 个完整原CPU返回对照、另 {validation['source_guard_case_count']} 个源域guard，0失败。矩阵覆盖27个X、24个Y、6方向组合、tile/attribute两入口、列/行/两者/不变、20unit同格覆盖；另所有256 busy值及连续camera/待处理请求。fixture明确在RAM0400放256个合法原chunkID描述符、相机/方向/单位配置由固定种子生成；它是受控CPU数据输入，不能称自然游戏可达。连续序列里每三步清007E是验证输入中的显式队列状态，不是源码假ack。原ROM始终只读。

对照完整8KiB SRAM、{len(DECLARED_RAM_ADDRESSES)}个声明RAM地址（全部非栈RAM，加0100..011F原palette区域与0140..01B3真实滚屏缓冲/单位tile数据）、有序E000端口请求、四PRGbank、AXYP及bodySP与原RTS后的SP关系。默认原CPUfixture SPFD，使真实调用栈不覆盖data缓冲；空闲栈残留与硬件周期不在合同。动态观察{len(actual)}/{len(locations)}个服务指令地址，是指令位置覆盖，不宣称所有值域/分支、PPU消费或完整NES帧。

```python
scroll = ScrollGraphicsServices(memory, GraphicsData.from_rom(rom))
result = scroll.tile_scroll(registers=registers)
result = scroll.attribute_scroll(registers=registers)
```

`registers=`接受a/x/y/p/sp对象，原AXYP末值会同步写回，SP不变。结果 `registers` 与 `contract_registers` 均是AXYP字典；`status='returned'`表示函数体完成，实际callerRTS尚由外层处理。`requests`列出本次构造请求；`PPU_queue_consumed=False`明确保留消费者责任。无动作/忙等待仍是原合法RTS返回；invalid chunk/单位数据域抛出明确异常，不替其构造成功。

- [独立源码](../../../source/recovered/scroll_graphics_services.py)
- [冻结验证与pins](validation.json)
- [机核原bytes证据](evidence.json)
- [原范围反汇编与数据表](original-ranges.asm)
- [观察到的执行指令位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_scroll_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_scroll_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
''')
 print(json.dumps(dict(status='passed',ranges=len(ranges),tables=len(TABLES),CPU=validation['rom_cpu_case_count'],guards=validation['source_guard_case_count'],static=len(locations),dynamic=len(actual),source_sha256=source['sha256'],validator_sha256=validator['sha256'],evidence_sha256=validation['evidence_sha256'])))
if __name__=='__main__':main()
