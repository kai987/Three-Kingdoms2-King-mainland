#!/usr/bin/env python3
"""Read-only original-byte evidence for independent audio service algorithms."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import disassemble,instruction,OPS,SIZES
from source.recovered.audio_services import AudioData,ROM_SHA256,REQUEST_COUNTS,SLOTS

RANGES=(
 ('reset_and_N163_upload',31,0xE000,0xE57F,0xE609,'code'),
 ('sequence_descriptor_request',31,0xE000,0xE609,0xE667,'code'),
 ('APU_disable_masks',31,0xE000,0xE667,0xE66B,'data'),
 ('consecutive_request_wrappers',31,0xE000,0xE66B,0xE6A6,'code'),
 ('N163_startup_wave',31,0xE000,0xE6A6,0xE6C6,'data'),
 ('audio_tick_trampoline',14,0xA000,0xA003,0xA006,'code'),
 ('eleven_slot_tick_and_music_parser',15,0xC000,0xD8D4,0xDD06,'code'),
 ('pitch_envelope_vibrato_tables',15,0xC000,0xDD06,0xDF6E,'data'),
 ('APU_N163_control_writer',15,0xC000,0xDF6E,0xDFBF,'code'),
 ('sequence_descriptor_table',2,0x8000,0x8000,0x82DC,'data'),
 ('immutable_music_data_bank2_tail',2,0x8000,0x82DC,0xA000,'music_data'),
 ('immutable_music_data_bank3',3,0xA000,0xA000,0xC000,'music_data'),
 ('actual_data_window_helper',31,0xE000,0xF25F,0xF266,'code'),
 ('NMI_audio_caller',31,0xE000,0xFAD5,0xFB0B,'context_code'),
 ('levelup_sound_caller',12,0xA000,0xAB46,0xAB52,'context_code'),
 ('normal_battle_music_resume',12,0xA000,0xAB67,0xAB6F,'context_code'),
 ('tactic_animation_sound_caller',26,0xC000,0xD737,0xD751,'context_code'),
 ('tactic_visual_to_sound_table',26,0xC000,0xD751,0xD75C,'data'),
 ('tactic_to_visual_table',26,0xC000,0xD549,0xD559,'data'),
 ('animation_end_battle_music_resume',26,0xC000,0xD416,0xD41F,'context_code'),
 ('controller_sampling_NOT_audio',31,0xE000,0xE6C6,0xE70E,'context_code'),
 ('palette_upload_NOT_audio',31,0xE000,0xE70E,0xE749,'context_code'),
)
TABLES=(('pitch_period_words',15,0xC000,0xDD06,0xDD4E),
 ('channel_masks',15,0xC000,0xDD4E,0xDD56),('channel_flags',15,0xC000,0xDD56,0xDD5E),
 ('vibrato_offsets',15,0xC000,0xDD5E,0xDDCE),('envelope_curves',15,0xC000,0xDDCE,0xDE6E),
 ('curve_times_volume',15,0xC000,0xDE6E,0xDF6E))

def sha(data):return hashlib.sha256(data).hexdigest()
def pin(relative):
 p=ROOT/relative;return dict(path=relative,sha256=sha(p.read_bytes()),bytes=p.stat().st_size)
def ranged(rom,name,bank,base,start,end,kind):
 offset=16+bank*8192+start-base;raw=rom[offset:offset+end-start]
 assert len(raw)==end-start
 return dict(name=name,physical_bank=bank,cpu_base=base,cpu_start=start,cpu_end_exclusive=end,
             rom_offset=offset,byte_count=len(raw),raw_hex=raw.hex(' ').upper(),sha256=sha(raw),kind=kind)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
 p.add_argument('--out',type=Path,default=ROOT/'analysis/phase10/audio');a=p.parse_args()
 rom=a.rom.read_bytes();data=AudioData.from_rom(rom);out=a.out;out.mkdir(parents=True,exist_ok=True)
 ranges=[];listing=[];code_instructions=0;service_locations=set()
 for name,bank,base,start,end,kind in RANGES:
  row=ranged(rom,name,bank,base,start,end,kind);ranges.append(row)
  listing.append(f'; {name} b{bank}:${start:04X}..${end-1:04X}, file0x{row["rom_offset"]:06X}, kind={kind}\n')
  if kind.endswith('code'):
   address=start
   while address<end:
    off=16+bank*8192+address-base;op,mode=OPS[rom[off]];size=SIZES[mode]
    assert op!='?'and address+size<=end,(name,hex(address),op)
    if kind=='code':code_instructions+=1;service_locations.add((bank,address))
    address+=size
   listing.append(disassemble(rom,bank,base,start,end))
  else:
   raw=bytes.fromhex(row['raw_hex'])
   for i in range(0,len(raw),16):
    listing.append(f'{row["rom_offset"]+i:06X} b{bank}:${start+i:04X} .byte '+','.join(f'${v:02X}'for v in raw[i:i+16])+' ; DATA\n')
  listing.append('\n')
 tables=[ranged(rom,n,b,base,s,e,'data')for n,b,base,s,e in TABLES]
 source_pin=pin('source/recovered/audio_services.py');validator_pin=pin('scripts/verify_audio_services.py')
 validation=json.loads((out/'validation.json').read_text())
 assert validation['status']=='passed'and not validation['quick']and validation['failed_count']==0
 assert source_pin['sha256']==validation['source_sha256']and validator_pin['sha256']==validation['validator_sha256']
 executed=json.loads((out/'executed-instructions.json').read_text())
 executed_locations={(row['physical_bank'],row['cpu'])for row in executed}
 assert executed_locations<=service_locations
 tree=ast.parse((ROOT/source_pin['path']).read_text())
 imports=[node.module for node in ast.walk(tree)if isinstance(node,ast.ImportFrom)]
 assert imports==['dataclasses']
 descriptor_rows=[]
 for ident in range(data.descriptor_count):
  raw=data.streams[ident*4:ident*4+4];x,channel,lo,hi=raw
  assert x in SLOTS and channel<8
  descriptor_rows.append(dict(sequence_id=ident,rom_offset=0x4010+ident*4,raw_hex=raw.hex(' ').upper(),slot_offset=x,
                              logical_channel=channel,stream_pointer=lo|((hi+0x40)&255)<<8))
 visual=bytes(rom[0x35559:0x35569]);sounds=bytes(rom[0x35761:0x3576C]);assert len(visual)==16 and len(sounds)==11
 sound_map=[]
 for tactic in range(16):
  kind=visual[tactic]>>1;ident=sounds[kind];entry=0xE683 if ident==0x88 else 0xE693 if ident==0x95 else 0xE68B
  sound_map.append(dict(tactic_id=tactic,visual_class=kind,visual_table_byte=visual[tactic],audio_sequence_id=ident,
                       request_entry=entry,consecutive_descriptors=REQUEST_COUNTS[entry],reset_before_request=True))
 retained=[f'analysis/rea/pairs/pair-29/functions/0x{pc:x}.{suffix}'for pc in (0xE57F,0xE609,0xE673,0xE6C6)for suffix in ('asm','c')]
 e=dict(schema='phase10-audio-services-v1',rom_sha256=ROM_SHA256,source_kind='Independent readable driver; immutable original music data, no IR/CPU fallback',
  ranges=ranges,tables=tables,dependency_pins=[source_pin,validator_pin,pin('source/recovered/service_memory.py'),pin('scripts/analyze_audio_services.py')],
  REA_archive=[pin(p)for p in retained if (ROOT/p).is_file()],
  source_AST_imports=imports,source_uses_IR_or_original_CPU=False,ROM_modified=False,
  APIs=['AudioServices(memory,AudioData.from_rom(rom))','reset(registers=None)','request(sequence_id,entry=E673,registers=None)',
        'tick(registers=None,command_budget=4096)'],
  entry_mapping={'reset':dict(bank=31,cpu=0xE57F),'request':dict(bank=31,cpu=0xE609),
                 'tick':dict(trampoline_bank=14,trampoline=0xA003,body_bank=15,body=0xD8D4)},
  data_mapping=dict(descriptor_count=183,descriptor_table_cpu=0x8000,descriptor_table_physical_bank=2,
                    music_windows=[dict(cpu_base=0x8000,physical_bank=2),dict(cpu_base=0xA000,physical_bank=3)],
                    driver_table_bank=15,tick_mapper_sequence=[dict(address=0xE000,value=0x22),dict(address=0xE800,value=0xE3)]),
  request_wrapper_counts={str(entry):count for entry,count in REQUEST_COUNTS.items()},descriptors=descriptor_rows,
  channel_model=dict(priority_slot_count=11,slot_stride=22,slot_offsets=list(SLOTS),logical_channels=8,
   class_flags=list(data.driver_tables[0x1D56:0x1D5E]),APU_channels=[0,1,2,3],N163_channels=[4,5,6,7],
   priority='0700..07F1 ascending slots; 07F2 suppresses subsequent same logicalchannel outputs while retaining state updates'),
  music_command_families={'F0..FE':'FD loop marker, other valuesignored','FF':'stop channel and request silence',
   'E0..EF':'negative volume-slide steps','D0..DF':'positive volume-slide steps','C0..CF':'envelope mode and denominator',
   'B0..BF':'absolute/marker loops, two signed byte counters; both finish and jump rebuild F0/F1',
   'A0':'volume','A1':'sweep','A2':'wave parameter','A3':'vibrato/gate delay or clear highflags',
   'A4':'clear channelhighflags','AD':'relative stream base and optional header restart',
   'AE':'tempo/pitch highbit','AF':'tempo low4','A5..AC':'ignored command words','00..9F':'note/rest plus duration'},
  original_quirks=['B loop counter reaching0 still entersD99B to reconstruct F0/F1.',
   'AD parameter0 jumpsD958->D940 and nests main scan; outer return additionally merges finalslot channelmask even ifinactive.',
   'AD nonzero rewrites00F1 while leaving00F0, so subsequent stream reads may address RAM; it is preserved ratherthanrepaired.',
   'N163 octave arithmetic keeps SBC30 carry/borrow fromCMP40; upper octave branches preserve originalcapshift5.',
   'VibratoDCD8 always writes4002+channel*4 even forN163: includes4012/4016/401A/401E. Unknown/reserved ports are observable requests, no invented sound effect.',
   'Periodlow is emitted before0712 cacheclamp2..FD; original emittedvalue is not repaired.'],
  audio_callers=dict(tactic_animation_sound_table=dict(bank=26,cpu=0xD751,bytes=list(sounds)),
   tactic_to_visual=dict(bank=26,cpu=0xD549,bytes=list(visual)),tactic_sound_map=sound_map,
   levelup=dict(bank=12,cpu=0xAB49,sequence_id=0x7B,request_entry=0xE68B,count=4,reset_before=True),
   battle_music_resume=[dict(bank=12,cpu=0xAB67,sequence_id=0x1D,entry=0xE673),dict(bank=26,cpu=0xD416,sequence_id=0x1D,entry=0xE673)],
   names='Numeric sequence IDs and confirmed callers, not unverified official song titles.'),
  scope=dict(driver_and_register_requests=True,N163_wave_upload_bytes=True,PCM_synthesis=False,oscillator_or_mixer=False,
             audio_time_or_IRQ_ack=False,readiness_ack=False,controller_E6C6=False,palette_E70E=False,
             body_registers='AXYP exact; SP preserved before actualcallerRTS; caller frame untouched, free stack residual writes excluded'),
  validation={k:validation[k]for k in ('status','case_count','rom_cpu_case_count','source_guard_case_count','failed_count','original_complete_case_count',
       'original_prefix_case_count','counts','compared_SRAM_bytes','original_instruction_locations')},
  static_service_instruction_count=code_instructions,
  dynamic_service_instruction_count=len(service_locations&executed_locations),
  instruction_address_coverage='Observed service instruction locations only; not all value/branch combinations or complete music/frame timing')
 (out/'original-ranges.asm').write_text(''.join(listing));e['disassembly_pin']=pin(str((out/'original-ranges.asm').relative_to(ROOT)))
 (out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
 validation['evidence_sha256']=sha((out/'evidence.json').read_bytes())
 (out/'validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
 (out/'README.md').write_text(f'''# Phase10 独立音频请求与逐tick驱动

`AudioServices`恢复固定31 E57F reset、E609与连续request包装，以及physical14 A003→15 D8D4完整11槽音序驱动。它读取原183个descriptor、bank2/3音乐命令和bank15数据表，不解释6502/IR、不调用原CPU、没有原ROM执行fallback。输出是精确APU/N163/mapper写请求与玩法RAM；它不合成波形/PCM、音频播放、时间或IRQ。真实Nestopia的WAV属于根线程另行捕获的原核心证据。

E6C6是4016/4017双手柄读取与0081/82新按键计算；E70E是palette2007上传。两者的原bytes在本目录明确作为context，而没有冒名为音频tick。真实NMI尾FAE6选择logical2E，FAE9调用A003；驱动将数据window映射physical2/3。

183个4B描述符包含slot offset、logicalchannel、指针low/highMinus40；E609替换该槽时会按旧APU类型更新07F6/4015。E66B/E673/E67B/E683/E68B/E693/E69B依次请求8/7/6/5/4/3/2个连续descriptor，E609请求1个。原table边界以第一个真实音乐header82DC确定；源拒绝将后续音乐byte假装descriptor。

驱动使用11个22B优先级槽，8种logicalchannel：2pulse、triangle、noise与4个N163。活动槽推进tempo/duration、volume slide、vibrato、envelope、word命令、循环与note/rest；07F2抑制后续同channel端口输出，不抹掉已更新状态。reset保留原11槽两字段清理顺序、APU寄存器请求、64零字节/32wave字节/4N163长度字段/音量字段上传与最终A5/F800=4C。

原quirks保留：B计数到0仍重建F0/F1；AD0重入scan后额外合并末槽mask（末槽inactive也会）；AD非0改F1但保留F0，可能读取RAM；N163 octave借位与上档shift5不修；0712缓存clamp发生在原periodlow已写端口之后。DCD8振音没有N163端口特判，会请求4012/4016/401A/401E；4018..401F只记录原写入，不编造其音效意义。

计略16ID通过26 D549选择11种visualclass，再查D751音序：88→E683/5、95→E693/3、8D或91→E68B/4，均先reset。等级提示12 AB49请求7B/E68B/4；后续12 AB67及动画结尾26 D416恢复1D/E673/7。数字是原请求ID，不是假定正式曲名。完整映射和原偏移在[evidence.json](evidence.json)。

最终 {validation['rom_cpu_case_count']} 原CPU比较 = {validation['original_complete_case_count']} 完整返回 + {validation['original_prefix_case_count']} 真实B0循环前缀；另 {validation['source_guard_case_count']} 源码guards，0失败。原183序列各40tick、5组多channel各128tick、全部160 note/rest byte×8channel×2变体、14种显式RAM控制命令连续8tick、5入口×所有256 SP，以及重复channel优先级冲突均检验。比较全部非栈2KiB RAM、完整8KiB SRAM、写端口顺序、N163128B寄存器图与AXYP/bodySP。显式RAM音乐fixture不是自然战役可达证明；原ROM未改。原CPU自由栈残留字节与周期/PCM不在该语义合同。服务静态{code_instructions}条指令地址中动态观察{len(service_locations&executed_locations)}条，不等于所有值域/分支组合、曲目长度或完整NES帧均已验证。

`registers=`可传现有a/x/y/p/sp对象：末值在实际caller RTS之前，源不植入0200返回、不弹callerframe。reset末A4C/X7F/Y3/NVZC=40；request末A/X为原X、Y3、flags按真实最后ADC/PLA；tick末AF2/XDC/Y末channel/NVZC=03。真实caller返回仍由调用方保持协议。验证用decimal-cleared py65上下文，源码按NES2A03二进制算术。budget前缀明确无returned registers、无假note/end/ack。

```python
audio = AudioServices(memory, AudioData.from_rom(rom))
audio.reset(registers=registers)
audio.request(0x1D, entry=0xE673, registers=registers)
result = audio.tick(registers=registers, command_budget=4096)
```

- [独立可读源码](../../../source/recovered/audio_services.py)
- [原CPU回执与最终pins](validation.json)
- [逐段原bytes及数据表](original-ranges.asm)
- [实际执行指令位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_audio_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_audio_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```
''')
 print(json.dumps(dict(status='passed',ranges=len(ranges),tables=len(tables),static_service_instruction_count=code_instructions,
                       source_sha256=source_pin['sha256'],validator_sha256=validator_pin['sha256'],
                       evidence_sha256=validation['evidence_sha256'],rom_cpu_case_count=validation['rom_cpu_case_count'],source_guard_case_count=validation['source_guard_case_count']),ensure_ascii=False))

if __name__=='__main__':main()
