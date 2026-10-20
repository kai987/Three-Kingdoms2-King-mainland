#!/usr/bin/env python3
"""Pin the readable battlefield initial-row body, dependencies and F09C variant."""
import argparse,ast,hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES,disassemble
from source.recovered.battle_graphics_services import ROM_SHA256

RANGES=(
 ('initial_background_export',23,0xA000,0xA009,0xA00C,'code'),
 ('background_camera_save31_rows_wait_restore',23,0xA000,0xA2FF,0xA387,'code'),
 ('direct_initial_tile_row',23,0xA000,0xA485,0xA51C,'code'),
 ('row_metatile_quadrants',23,0xA000,0xA5A5,0xA604,'code'),
 ('descriptor_and_primary_chunk_lookup',23,0xA000,0xA604,0xA642,'code'),
 ('primary_chunk_pointers',23,0xA000,0xA642,0xA732,'data'),
 ('attribute_chunk_pointers',23,0xA000,0xA732,0xA822,'data'),
 ('primary_chunk_raw_mapper_selectors',23,0xA000,0xA822,0xA89A,'data'),
 ('nametable_and_attribute_headers',23,0xA000,0xA89A,0xA8FD,'code'),
 ('unit_overlay_and_shared_tile_lookup',23,0xA000,0xA8FD,0xAAE4,'code'),
 ('unit_tiles',23,0xA000,0xAAE4,0xAB26,'data'),
 ('camera_to_unit_coordinate_helper',23,0xA000,0xAB26,0xAB53,'code'),
 ('direct_initial_attribute_row_and_merge',23,0xA000,0xAD9F,0xAEB5,'code'),
 ('attribute_chunk_and_unit_overlay_helpers',23,0xA000,0xAEF3,0xB100,'code'),
 ('fast_consumer_attribute_branches',31,0xE000,0xEE98,0xEEAE,'code'),
 ('fast_PPU_consumer_and_row_helpers',31,0xE000,0xEEE6,0xF077,'code'),
 ('sprite_prologue_context',31,0xE000,0xF092,0xF09C,'context_code'),
 ('F09C_existing_clip_tile_offset_sprite_body',31,0xE000,0xF09C,0xF1AD,'code'),
 ('actual_map_data_window_helper',31,0xE000,0xF25F,0xF266,'code'),
 ('controller_record_pointer_helper',31,0xE000,0xF368,0xF379,'code'),
 ('controller_record_pointer_table',31,0xE000,0xF379,0xF387,'data'),
 ('background_metatiles',31,0xE000,0xF477,0xF877,'data'),
)
FILES=('source/recovered/battle_background_initialization.py','scripts/analyze_battle_background_initialization.py',
       'scripts/verify_battle_background_initialization.py','source/recovered/scroll_graphics_services.py',
       'source/recovered/battle_graphics_services.py','source/recovered/battle_nmi_services.py',
       'source/recovered/text_services.py','source/recovered/service_memory.py','source/recovered/audio_services.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(path):
 f=ROOT/path;return dict(path=path,bytes=f.stat().st_size,sha256=sha(f.read_bytes()))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase11/background');a=p.parse_args()
 rom=a.rom.read_bytes();assert sha(rom)==ROM_SHA256;out=a.out;out.mkdir(parents=True,exist_ok=True)
 v=json.loads((out/'validation.json').read_text());assert v['status']=='passed'and not v['failed_count']
 for path,digest in v['source_sha256'].items():assert sha((ROOT/path).read_bytes())==digest,path
 ranges=[];listing=[];locations=set()
 for name,bank,base,start,end,kind in RANGES:
  off=16+bank*8192+start-base;raw=rom[off:off+end-start]
  item=dict(name=name,physical_bank=bank,cpu_base=base,cpu_start=start,cpu_end_exclusive=end,rom_offset=off,
            byte_count=len(raw),raw_hex=raw.hex(' ').upper(),sha256=sha(raw),kind=kind)
  ranges.append(item);listing.append(f'; {name}, bank{bank}:${start:04X}..${end-1:04X}, file0x{off:06X}, {kind}\n')
  if kind.endswith('code'):
   pc=start
   while pc<end:
    op,mode=OPS[rom[16+bank*8192+pc-base]];size=SIZES[mode]
    assert op!='?'and pc+size<=end,(name,hex(pc),op)
    if kind=='code':locations.add((bank,pc))
    pc+=size
   listing.append(disassemble(rom,bank,base,start,end))
  else:
   for index in range(0,len(raw),16):listing.append(f'{off+index:06X} b{bank}:${start+index:04X} .byte '+','.join(f'${b:02X}'for b in raw[index:index+16])+' ; DATA\n')
  listing.append('\n')
 executed=json.loads((out/'executed-instructions.json').read_text());actual={(r['physical_bank'],r['cpu_address'])for r in executed}
 assert actual<=locations,sorted(actual-locations)
 source=(ROOT/FILES[0]).read_text();tree=ast.parse(source)
 imports=[n.module for n in ast.walk(tree)if isinstance(n,ast.ImportFrom)]
 assert not any(name in source for name in('program.json','MPU(','exec(','.step()'))
 (out/'original-ranges.asm').write_text(''.join(listing))
 e=dict(schema='phase11-readable-background-v1',rom_sha256=ROM_SHA256,ROM_modified=False,
        independent_algorithm=True,source_executes_ROM_or_IR=False,source_original_CPU_callbacks=0,
        ranges=ranges,dependency_pins=[pin(path)for path in FILES],disassembly_pin=pin(str((out/'original-ranges.asm').relative_to(ROOT))),
        source_AST_imports=imports,APIs=['BattleBackgroundInitialization(memory,rom,services=None)',
         'run_entry(entry=A009,registers=None,return_pc=None)','resume()','__call__(ServiceCall)',
         'InitialRows.tile_row(registers=None)','InitialRows.attribute_row(registers=None)','world_sprites_variant(registers=None)'],
        entry_mapping={'background':dict(physical_bank=23,export=0xA009,body=0xA2FF),
                       'tile_row':dict(physical_bank=23,body=0xA485),'attribute_row':dict(physical_bank=23,body=0xAD9F),
                       'caller_parameter_sprites':dict(physical_bank=31,body=0xF09C)},
        inputs={'008E..0091':'camera u16X/u16Y','00A8/A9':'mapped map descriptor pointer',
                '007E':'actual pending PPU/text request bits','009C':'original direction/cache byte, never overridden',
                'unit arrays':'0600/0614 coordinates,0628 affiliation,063C displayed-hundreds glyph cache',
                'F09C':'00/01 sprite descriptor,02 flips,03 tile offset,04 vertical clip,0A..0D coordinates,7C OAM cursor'},
        mechanics=['Counter1E starts30; BPL after decrement executes31 tile/attribute row pairs.',
                   'Each pair calls directA485/AD9F, not cache-direction wrappers A387/AB53.',
                   'AfterEEE6, A324 reads7E and branches back until every pending request is actually cleared.',
                   'No queue ack is synthesized. Missing2002 input and low-owned requests preserve real PC/SP and saved camera.',
                   'Camera Y low subtract8; borrow causes another subtract16 and high decrement; restoration pops actual saved bytes.',
                   'Restored camera determines92..95;9C/9D are both assigned90hex, not restored old values.',
                   'Tile row queues40bit at0164; attribute row queues10bit at019C. Empty initial queue takes62EEE6 calls.',
                   'AE58 both cachebit10 branches have identical merge logic; source uses their identical result without cache mutation.',
                   'F09C skipsF092 initialization of03/04 and retains caller tile offset/vertical clipping.',
                   'F09C negative-X descriptor uses complement without plus-one; rejected X may leave partialOAM writes without allocation.'],
        low_job_continuation=dict(prefix_PC=0xA321,prefix_SP=0xF8,prefix_jobs=0x11,
                                  actual_text_end_marker=0x80,text_cursor_before=0,text_cursor_after=255,
                                  jobs_after_real_text_consumer=0x10,jobs_after_background_resume=0,
                                  source_only_continuation=True,original_CPU_prefix_compared=True),
        scopes=dict(full_body_RAM_bytes=v['compared_RAM_bytes'],full_body_RAM_addresses=v['declared_RAM_addresses'],
                    row_primitive_RAM_addresses=v['row_primitive_RAM_addresses'],all_SRAM_bytes=8192,
                    full_body_registers='AXYP/SP/PC actual caller return',primitive_registers='AXYP body-end; caller owns RTS',
                    ordered_ports_and_final_banks=True,inactive_stack_residue_excluded=v['inactive_stack_residue_excluded'],
                    actual_frames=False,IRQ_NMI_timing=False,pixels=False,DMA=False,PCM=False,
                    dynamic_addresses=len(actual),evidence_range_code_addresses=len(locations),
                    coverage_note='Evidence ranges include reused helpers and paths beyond these entries; not a minimal static closure or fullbranch claim'),
        validation={k:v[k]for k in('status','rom_cpu_case_count','source_guard_case_count','original_complete_case_count','original_prefix_case_count','failed_count','counts')})
 (out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
 v['evidence_sha256']=sha((out/'evidence.json').read_bytes());(out/'validation.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
 (out/'README.md').write_text(f'''# 阶段11：战场背景初建与原参数精灵入口

`BattleBackgroundInitialization` 独立恢复 physical23 `$A009 → A2FF` 的完整有界背景初建，以及 fixed31 `$F09C` 的原调用参数精灵入口。生产源码为直接整数运算、循环和具名函数；不执行原 ROM、不解释 IR、不调用原 CPU fallback。复用的滚屏、单位字形与固定 PPU 消费者也是已经独立恢复的源码。它不是原始游戏源码或完整 NES 仿真器。

## 完整背景调用

原代码将四个相机字节 `$008E..0091` 压到真实栈，临时增加 Y 高字节。计数器以30开始，每次递减后以 BPL 判断，因此构造的是 **31组 tile/attribute 行**，不能把“30行屏幕”当作30次循环。每组从真实直接入口 `$A485`、`$AD9F` 构造请求，再调用 fixed `$EEE6`；`$A324` 读取 `$007E` 并回到 `$A321`，直到全部原请求实际清除。

tile行构造17个 metatile，请求缓冲 `$0164`、bit `$40`；attribute行构造8或9个属性，请求缓冲 `$019C`、bit `$10`。这两个直接入口不同于滚屏外层 `$A387/$AB53` 的方向选择。源码没有临时篡改 `$009C` 来借用另一个路径。`$AE58` 的两条 cachebit分支原来执行相同合并，因此保留相同结果。unit覆盖保留最低slot优先、原packed row15缺口、原数据bank切换和边缘合并。

行间 Y 低字节减8；借位时再减16并减高字节，保留原字节回绕。最后实际弹栈恢复四个相机字节，重新写 `$0092..0095` 缓存。`$009C/$009D` 都被置为 `$90`，原旧缓存值不恢复。默认仅这两项行请求、显式 PPUSTATUS=0 时，共有62次真实 `$EEE6` 消费调用。

API为 `BattleBackgroundInitialization(shared_memory, pinned_rom_bytes, services=None)`，`run_entry(entry=0xA009, registers=..., return_pc=None)` 接受现有调用栈；`resume()` 保留同一 generator、相机栈和真正等待位置。`__call__(ServiceCall)` 可被统一 coordinator 路由：background要求映射 physical23/24，返回必须满足原 return_pc / expected_sp；外部 EE07 调用框架随后仍由其原 owner 恢复银行。没有服务时默认使用独立 `BattleNMIServices` 的 `$EEE6`。

硬件读必须由 `ServiceMemory` 显式提供；缺少 `$2002` 时保留待消费请求和已发生端口序列，不重放早先写入。`$EEE6` 仅处理高四位请求，低位仍由其真实 owner处理。验证中的低位文本例停在 `$A321/SP=F8`、`7E=11`：真实空文本消费者将cursor `$0304` 置FF并仅清bit0，得到 `7E=10`；背景恢复后再执行真实属性消费者，才到 `7E=0` 并返回。这个续程是源端 ownership 检查；原 CPU 对照只将该例计入严格前缀，不虚称额外完整 CPU 比较。

## F09C 原调用参数

`world_sprites_variant(registers=...)` 从 `$F09C BIT $0002` 开始。只有 `$F092` 外层会将 `$0003=0`、`$0004=F0`，本入口保留调用者传入的 tile offset 和纵向clip。它保留相机相减、flip、Y gap、负X补码不再加1的异常，X高字节拒绝前已经写下的部分OAM及cursor满FF的边界。直接方法的合同是正文结束 AXYP，caller拥有RTS；通过 `__call__` 则弹出已有真实caller并比较返回PC/SP。不默认完成DMA或画面帧。

## 原CPU对照和边界

**{v['rom_cpu_case_count']}个原 CPU 对照：{v['original_complete_case_count']}完整返回 + {v['original_prefix_case_count']}严格依赖前缀；另{v['source_guard_case_count']}个续程检查，0失败。** 其中直接tile/attribute行各32例，完整31组背景16例，F09C真实caller144例；缺PPUSTATUS前缀2例、未消费低位任务前缀1例。所有指令都由原只读 ROM 字节执行。

完整背景/F09C比较{v['compared_RAM_bytes']}个RAM地址、全部8192B SRAM、有序端口写和最终PRG银行，以及AXYP/SP/PC。RAM只排除 `$01B4..01F8` 的空闲栈残留；真实palette/请求buffer/active相机栈与caller地址都比较。两个行primitive比较{len(v['row_primitive_RAM_addresses'])}个冻结声明RAM地址和正文结束AXYP，calleeRTS的空闲栈残留不属于此合同。源码没有原 CPU callback、假ready或输出PCM。

输入来自阶段3原核心snapshot，并明确准备合法RAM0400地图描述符、相机、单位/strength/ruler、调用栈和sprite descriptor。它是受控CPU输入，不宣称自然可达。只读地图表限定合法chunk0..119，单位slot0..19、字形strength0..10及ruler0..6；未终止的sprite表、非法数据和decimal fixture不属于支持域。此轮没有新增原核心像素、中断周期或DMA验证。动态触及{len(actual)}个原指令地址；证据范围还包含复用helper的其他路径，不能视为所有分支完整覆盖。

```sh
.venv-trace/bin/python scripts/verify_battle_background_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_battle_background_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

- [独立源码](../../../source/recovered/battle_background_initialization.py)
- [CPU回执与依赖哈希](validation.json)
- [原bytes、数据表和合同](evidence.json)
- [正确含iNES header的原范围反汇编](original-ranges.asm)
- [实际执行指令位置](executed-instructions.json)
''')
 print(json.dumps(dict(status='passed',ranges=len(ranges),CPU=v['rom_cpu_case_count'],guards=v['source_guard_case_count'],source_sha256=pin(FILES[0])['sha256'],evidence_sha256=v['evidence_sha256'])))
if __name__=='__main__':main()
