#!/usr/bin/env python3
"""Original data/byte evidence for readable graphics and16 animation services."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.battle_graphics_services import GraphicsData,ROM_SHA256
from inspect_game_data import disassemble
RANGES=[('cursor_prelude',13,0xC000,0xD657,0xD68A),('map_refresh_and_attributes',13,0xC000,0xD6CC,0xDA17),
 ('highlight_preludes',13,0xC000,0xDC63,0xDC99),('map_chunk_pointer',23,0xA000,0xA61C,0xA642),
 ('attribute_pointer',23,0xA000,0xAEF0,0xAF0C),('unit_BG_tiles',23,0xA000,0xA983,0xAB26),
 ('fixed_sprite_renderers',31,0xE000,0xF092,0xF206),('animation_dispatch',26,0xC000,0xCFD6,0xD04A),
 ('eleven_animation_handlers',26,0xC000,0xD04A,0xD2C9),('animation_portrait_and_sprite',26,0xC000,0xD2C9,0xD3A3),
 ('animation_finish',26,0xC000,0xD3A3,0xD41F),('animation_panel_setup',26,0xC000,0xD41F,0xD549),
 ('animation_banner_palette_setup',26,0xC000,0xD559,0xD692),('animation_transition_and_audio',26,0xC000,0xD6EA,0xD75C),
 ('animation_stat_digits',26,0xC000,0xD75C,0xD7FF),('decimal_work_helper',31,0xE000,0xE9BA,0xEA7C),
 ('normal_palette_copy',30,0xC000,0xDBB1,0xDBCF)]
INLINE={13:[(0xD681,9,'cursor4B records+80 terminator'),(0xD731,2,'EE07 A012'),(0xD7B8,2,'EE07 A018'),(0xD7E3,2,'EE07 A015'),(0xD82A,2,'EE07 A015'),(0xD84A,2,'EE07 A015'),(0xDC94,5,'highlight4B record+80 terminator')],
 23:[(0xAAE4,66,'6 x11 unit tile lookup rows')],26:[(0xD00C,4,'2 mainstate entry words'),(0xD034,22,'11 visual class entry words'),(0xD0AC,12,'trap palettecycle data'),(0xD38B,24,'portraitx/y positions'),(0xD3EA,2,'EE07 A015'),(0xD425,10,'5 setup entry words'),(0xD751,11,'visualclass audio request IDs')]}
def analyze(rom,out):
 data=GraphicsData.from_rom(rom);out.mkdir(parents=True,exist_ok=True);ranges=[];listing=[]
 for name,bank,base,start,end in RANGES:
  offset=16+bank*8192+start-base;raw=rom[offset:offset+end-start]
  ranges.append(dict(name=name,physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,byte_count=len(raw),raw_hex=raw.hex(' '),sha256=hashlib.sha256(raw).hexdigest()))
  listing.append(f'; {name}, originalbank{bank} ${start:04X}..${end-1:04X}\n');cursor=start
  for address,size,label in sorted(INLINE.get(bank,[])):
   if not start<=address<end:continue
   listing.append(disassemble(rom,bank,base,cursor,address));o=16+bank*8192+address-base
   listing.append(f'{o:06X} b{bank:02}:${address:04X} .byte '+', '.join(f'${v:02X}'for v in rom[o:o+size])+f' ; {label}\n');cursor=address+size
  listing.append(disassemble(rom,bank,base,cursor,end))
 (out/'original-ranges.asm').write_text(''.join(listing))
 tables=[]
 def table(name,bank,base,address,size):
  o=16+bank*8192+address-base;raw=rom[o:o+size];tables.append(dict(name=name,physical_bank=bank,cpu_address=address,rom_offset=o,byte_count=size,raw_hex=raw.hex(' '),sha256=hashlib.sha256(raw).hexdigest()))
 for args in [('chunk_pointers',23,0xA000,0xA642,240),('attribute_pointers',23,0xA000,0xA732,240),('chunk_selectors',23,0xA000,0xA822,120),
  ('background256metatiles',31,0xE000,0xF477,1024),('tactic16_to_visual11',26,0xC000,0xD549,16),('eleven_palette_rows',26,0xC000,0xD692,88),
  ('three_banner_pages',26,0xC000,0xD7FF,96),('eleven_animation_frame_tables',26,0xC000,0xD85F,22),('normal_palette_mode1',30,0xC000,0xDC0B,32)]:table(*args)
 # Actual sprite records are data parsed byF1AD, not executableCPUinstructions.
 frames=[];counts=(3,0,3,3,4,2,4,2,3,3,1)
 for kind,(pointer,count)in enumerate(zip(data.animation_sprite_tables,counts)):
  o=0x34010+pointer-0xC000
  table(f'visual{kind}_frame_pointer_table',26,0xC000,pointer,count*2)
  for i in range(count):
   frame=int.from_bytes(rom[o+2*i:o+2*i+2],'little');fo=0x34010+frame-0xC000;raw=bytearray()
   for row in range(65):
    if rom[fo+4*row]==128:raw.append(128);break
    raw.extend(rom[fo+4*row:fo+4*row+4])
   else:raise AssertionError('Unterminated originalanimationrecord')
   frames.append(dict(visual_kind=kind,frame_1based=i+1,physical_bank=26,cpu=frame,rom_offset=fo,raw_hex=raw.hex(' '),byte_count=len(raw),sprite_count=(len(raw)-1)//4,sha256=hashlib.sha256(raw).hexdigest()))
 source=ROOT/'source/recovered/battle_graphics_services.py';v=json.loads((out/'validation.json').read_text())
 assert v['source_sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
 assert v['validator_sha256']==hashlib.sha256((ROOT/'scripts/verify_battle_graphics_services.py').read_bytes()).hexdigest()
 pins=[]
 for p in(source,ROOT/'source/recovered/audio_services.py',ROOT/'source/recovered/service_memory.py',ROOT/'source/recovered/mapped_memory.py',ROOT/'source/recovered/officers.py',ROOT/'scripts/verify_battle_graphics_services.py',Path(__file__)):
  pins.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 rea=[]
 for p in(ROOT/'analysis/rea/pairs/pair-12/procedure-index.json',ROOT/'analysis/rea/pairs/pair-25/functions/0xa00f.c',ROOT/'analysis/rea/pairs/pair-25/functions/0xcfd6.asm'):
  if p.exists():rea.append(dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 imports=[n.module for n in ast.walk(ast.parse(source.read_text()))if isinstance(n,ast.ImportFrom)]
 assert all(not any(word in(module or'')for word in('py65','state_machine','runtime_services','control','trace'))for module in imports)
 audio_ids=(149,136,136,141,141,141,145,136,149,136,149)
 e=dict(rom_sha256=ROM_SHA256,source_kind='independent readable graphics/OAM/data animation algorithms; no IR or ROM opcode executor; not originalsource',dependency_pins=pins,source_ast_imports=imports,REA_archive=rea,ranges=ranges,tables=tables,animation_frames=frames,
  APIs=['BattleGraphicsServices(shared_memory, GraphicsData.from_rom(rom))','map_refresh(registers=None)','cursor(registers=None)','highlight(registers=None,alternate=False)','world_sprites(registers=None)','screen_sprites(registers=None)','unit_tiles(slot)','animation_tick(registers=None)'],
  originals=dict(map_refresh='physical13 D6CC',cursor='physical13 D657',highlight=['physical13 DC63','physical13 DC70'],animation='physical25 A00F ->physical26 CFD6 atfixedF945',
   wrong_animation_label_corrected='physical23 AB53 atfixedF93A isscrollattributeupdates, not04C8 animation;23A387 atF937 isscrollBGtilecommands, notunitOAM. Those two services areoutside thisfile.'),
  map_refresh=dict(view='raw unitXY within15rows/16columns, cameraX=(8E+4)>>4 or16onoverflow',buffer=[0x380,0x38F],job_request='007E OR04 only',normal_attribute='currentchunk first; neighborchunk onlymerged atodd camera horizontal seam',draw_flag='0012 zero: omitselectedunit BG and palette overlay; nonzero: unit4tile override andincludeall20units',overlay='19down0 coordinates only, no activeID filter; allquadrants setpalette2 preserving otherbits',ports='RealEE07NMIpairF000/E800 andF25FE000 order; rawselectors retained',PPU_writes=False,queue_consumed=False),
  sprite_quirks=['F092Ysubtract has16-bytegap adjustment on borrow; verticalflip pre-adjust8 plusgap, horizontalflip pre-adjust16.', 'F092negativeX uses complement without+1, producing the original1pixel asymmetry.', 'Yclipping happensbeforeOAMwrite; Xhighclipping happensafter4B partialwrite butwithoutallocatingtheOAMcursor.', '007CFF fullsentinel; worldrenderer returnsviaCPXFF while screenrenderer wrapbranch endsviaLDXFF, soflagsdiffer.', 'DC63/DC70 blinkbit5E&10 skipsonlyafterwritingabsolute0A/0C bases.', 'Neither cursor norhighlight requests4014DMA; onlyRAMOAMconstructed.'],
  animation=dict(controller_states={'80':'setup','81':'animated'},setup_states=5,visual_class_count=11,tactic_to_visual=[b>>1 for b in data.animation_kinds],finish='Exact04D0==B0;04C8=0,requestpalette007D=1/BG007E|4/audio sequences;nohardwarework fabricated',
   actual_wait='04C8==0 no work;0300!=FF or0304!=FF returnswithoutadvancement',ruler_portrait='bank17 thirteen-byte portrait records, headerCHRpageC1 plusup to12OAMtiles',
   audio=[dict(visual_class=i,sequence_id=seq,entry=0xE693 if seq==149 else 0xE683 if seq==136 else 0xE68B,reset_first=0xE57F)for i,seq in enumerate(audio_ids)],end_audio=dict(sequence_id=29,entry=0xE673,reset_first=0xE57F),
   standalone_CPU_sequence='Each16ID executes191actualRTS calls:15setup+176animated; hostOAMcursor0beforeeach call, initialjobsFF, noNMI/video synthesis.',registers='Basic3servicesandunderlyingrenderers A/X/Y/P strict;animationfinalregisters excluded, callerstack/SP/PC external.'),
  validation={k:v[k]for k in('status','rom_cpu_case_count','source_guard_case_count','failed_count','counts','compared_SRAM_bytes','compared_RAM_bytes','original_instruction_locations')},
  limits=['CPUstackpageexcludedexceptactualpalette0100..011Fandunittile01B0..01B3;1792nonstackRAMplus36actualdata=1828bytes.', 'AnimationtickusespureAudioServicesreset/request, neitherdriverPCMnorPPUrender.', 'DoesnotconsumeNMIqueueorperformDMA; root owns separateconsumer.', '23A387/AB53scrollupdate services remain separate; unitbackground4tilehelper is complete.', 'No nativecoreframes are created by these CPUfixtures.'])
 (out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
 (out/'README.md').write_text(f'''# 第10阶段：战场图形请求与计略动画消费者

`BattleGraphicsServices` 独立恢复完整 physical13 D6CC地图刷新、D657光标、DC63/DC70高亮及固定F092/F1AD OAM构造。另补全真正的计略动画入口 physical25 A00F→26CFD6：16项计略映射到11个visual class，5个准备子状态、176次动画计数、真实portrait/sprite/palette命令与收尾音序。没有解释IR、执行原ROM opcode、图形空函数或自动ack；不是原作者源码。

## 调用与精确边界

```python
graphics = BattleGraphicsServices(shared_memory, GraphicsData.from_rom(rom))
result = graphics.map_refresh(GraphicsRegisters(a=17,x=23,y=31,p=32))
result = graphics.cursor()
result = graphics.highlight(alternate=False)
result = graphics.animation_tick()  # 真实NMI调用点的一次工作，无伪造frame
```

基础三个服务与两个renderer回传实际A/X/Y/P，供外层执行真实RTS/pop；没有改CPUstack、SP或PC。计略动画的内存/端口完整返回，最终CPU寄存器临时态明确不在合同；不能把它自动当作旧CPU控制器的寄存器等价hook。共享memory的真实io_write/普通索引记录PRG/APU/N163写入；没有默认硬件读。

D6CC只建立0380..038E的15B请求：两行各2tile、一个attribute byte和FF终止。原007E只OR4，不消费队列。先读当前chunk，odd camera横向拼缝时才合并邻chunk属性；reverse20槽叠加palette2，0012为0时跳过selectedunit。非零则按单位兵百位缓存0..10、所在ruler controller和0628适性生成4B单位背景图块。读取完整真实数据窗、更新E1与端口顺序，保持EE07的58..5D/E2/E3协议及rawselector别名。超视口早返亦复现寄存器/flags。

光标F092把世界坐标转换为屏幕OAM，含y借位16byte间隔、镜像预调整、负X少1的原公式和先写后裁剪的部分OAM。007C为FF会早返；分配回绕时world与screen路径最终flags不同，已独立核对。高亮先写0A/0C，再按5E.bit4闪烁跳过或追加屏幕sprite。没有4014DMA、PPU像素或frame时序合成。

## 真正的16项动画

NMI F93A调用physical23 A00F→AB53，是scroll属性更新；F937的23A00C→A387是scroll背景行/列命令。它们不读04C8，仍由独立scroll服务恢复，本文件不把它们标作动画或单位OAM。

真正动画在F945的selector39：25A00F→26CFD6。初始04C8=tactic+1保存原ID；准备80执行panel/数字/图块/调色板/音序五子状态，再进入81。16→11映射为 `{[b>>1 for b in data.animation_kinds]}`。11类都有独立可读handler，使用真实frame表与sprite records，并保持byte计数、双层sprite、颜色循环、portrait和OAMcursor。

0300或0304没有真实FF时直接等待；source不写FF完成它们。只有原04D0恰好达到B0的有效分支才清04C8，构造背景清除/标准palette/音序请求。这是原软件状态推进，未表示异步PPU或声音播放完成。音频调用复用独立`AudioServices.reset/request`，不调用旧RuntimeServices IR；结束标准palette用实际far3DA015→30DBB1的mode1数据复制。对应16动画序列每项191次原服务返回，15次准备+176次动画。

## 原CPU验证与来源

最终 **{v['rom_cpu_case_count']} 次原CPU完整返回、{v['source_guard_case_count']} source guards、{v['failed_count']}失败**。其中基础1520例严格比较A/X/Y/P；16条动画顺序共3056次返回，20例inactive/jobwait/init返回另列。完整8KiB SRAM、1828B RAM、bank映射和真实端口写序相等。RAM含全部非CPUstack字节，以及真正palette0100..011F和unit tile scratch01B0..01B3；其余CPUstack残余、SP/PC及animation寄存器排除。

顺序CPU输入每次将007C明确设0作为原NMI的OAM初始条件，0300/0304最初FF，不替软件确认。没有运行队列消费者、IRQ/NMI/video/PCM，也不把3056calls说成3056真实NESframes。全16路径、11visual类、起始/最终byte、常规和极值视口/翻转/裁剪/full OAM、ruler/适性/兵百位差异分别核对。

`evidence.json`固定原CPU范围、EE07/EADE内联数据、chunk/metatile/帧sprite及不可变ROM数据SHA；现有REA定位证据亦固定。`executed-instructions.json`的rom_offset明确包含16B iNES头，与原文件位置一致。validation固定源码与validator hash；不会把有限动态覆盖声称为所有分支证明。

```sh
.venv-trace/bin/python scripts/verify_battle_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_battle_graphics_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
''')
 print(json.dumps(dict(source_sha256=v['source_sha256'],rom_cpu_cases=v['rom_cpu_case_count'],guards=v['source_guard_case_count'],original_ranges=len(ranges),original_bytes=sum(r['byte_count']for r in ranges),sprite_frames=len(frames),source_pins=pins),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase10/graphics');a=p.parse_args();analyze(a.rom.read_bytes(),a.out)
