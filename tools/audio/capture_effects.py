#!/usr/bin/env python3
"""Isolate original short cues through the unchanged ROM driver and Nestopia APU.

Offline controlled audio fixture, not natural gameplay: a disclosed RAM caller
at $0600 sets the original NMI busy flag, calls the original reset, waits for
180 original NMI ticks, then requests exactly one proven descriptor group.
The original busy NMI runs the original music driver at its native timing.
No ROM/emulator code is patched; no waveform is reconstructed or synthesized.
"""
from __future__ import annotations
import argparse
import array
import ctypes as C
import json
from pathlib import Path
import struct
import tempfile
import wave
from capture_original import Recorder,ROOT,ROM_SHA,CORE_SHA,STATE_SHA,sha,seam_fade

BASE_STATE='analysis/runtime/map-ready.state'
SLOT_OFFSETS=tuple(range(0,242,22))
# IDs/entries are original requests, not invented sound names.
CUES={
 0x62:(0xE693,3),0x5E:(0xE609,1),0x5A:(0xE69B,2),0x5D:(0xE609,1),
 0x60:(0xE609,1),0x61:(0xE609,1),0x68:(0xE609,1),0x69:(0xE609,1),
 0x65:(0xE69B,2),0x88:(0xE683,5),0x8D:(0xE68B,4),0x91:(0xE68B,4),0x95:(0xE693,3),
}
# Proven original contexts versus explicit new UI placement of an original cue.
BINDINGS={
 'click':(0x60,'authorial_ui_reuse','原版單挑人物移動音，重製版用於選擇'),
 'confirm':(0x62,'original_context','原版城池面板A鍵確認提示音'),
 'cancel':(0x60,'authorial_ui_reuse','原版單挑人物移動音，重製版用於取消；未確認獨立原版取消音'),
 'error':(0x61,'authorial_ui_reuse','原版單挑動作音，重製版用於無效操作'),
 'march':(0x5A,'authorial_ui_reuse','原版普通攻擊移動階段音，重製版用於出發'),
 'attack':(0x5E,'original_context','原版普通攻擊動作階段3'),
 'attack_impact':(0x5D,'original_context','原版普通攻擊動作階段7'),
 'tactic_prepare':(0x65,'original_context','原版計略準備提示'),
 'tactic':(0x88,'original_context','原版計略效果音88組'),
 'tactic_88':(0x88,'original_context','原版計略效果音88組'),
 'tactic_8d':(0x8D,'original_context','原版計略效果音8D組'),
 'tactic_91':(0x91,'original_context','原版計略效果音91組'),
 'tactic_95':(0x95,'original_context','原版計略效果音95組'),
 'duel_start':(0x62,'authorial_ui_reuse','原版單挑動作0提示音，重製版用於接受挑戰'),
 'duel_refused':(0x60,'authorial_ui_reuse','原版單挑人物移動音，重製版用於拒絕挑戰'),
 'duel_strike':(0x61,'authorial_ui_reuse','原版單挑動作2／6音，對應本作突擊操作'),
 'duel_guard':(0x68,'authorial_ui_reuse','原版單挑動作8音，對應本作防守操作'),
 'duel_feint':(0x69,'authorial_ui_reuse','原版單挑動作2第二段音，對應本作佯攻操作'),
 'duel_withdraw':(0x60,'authorial_ui_reuse','原版單挑人物移動音，重製版用於退出'),
 'victory':(0x62,'authorial_ui_reuse','本作戰果短提示，複用原版確認音；非原版6C長曲'),
 'defeat':(0x61,'authorial_ui_reuse','本作戰果短提示，複用原版單挑動作音；非原版71長曲'),
}
# Every direct call is checked against the supplied immutable ROM before capture.
CALLS=[
 (0x62,0xE693,216499,'city panel A-button response'),
 (0x5E,0xE609,116320,'ordinary attack object action phase 3'),
 (0x5A,0xE69B,116538,'ordinary attack object action phase 6'),
 (0x5D,0xE609,116566,'ordinary attack object action phase 7'),
 (0x62,0xE693,198211,'duel action0 motion phase 5'),
 (0x61,0xE609,198609,'duel action2 motion phase 4'),
 (0x69,0xE609,198864,'duel action2 motion phase 7'),
 (0x61,0xE609,199239,'duel action6 motion'),
 (0x68,0xE609,199504,'duel action8 motion'),
 (0x60,0xE609,200450,'duel character motion'),
 (0x65,0xE69B,106573,'tactic preparation'),
]
TABLES=[
 ('tactic_sound_dispatcher',218951,'20 7f e5 ac c9 04 b9 51 d7 c9 88 f0 0a c9 95 f0 03 4c 8b e6 4c 93 e6 4c 83 e6'),
 ('tactic_visual_to_sound',218977,'95 88 88 8d 8d 8d 91 88 95 88 95'),
 ('tactic_id_to_visual',218457,'02 10 06 08 04 02 0e 08 0c 14 0a 08 04 12 02 00'),
]

def chunk(blob,start,stop,wanted):
 position=start;found=[]
 while position<stop:
  if position+8>stop:raise ValueError('Truncated original state chunk')
  tag=blob[position:position+4];length=struct.unpack_from('<I',blob,position+4)[0];end=position+8+length
  if end>stop:raise ValueError('Original state chunk escapes container')
  if tag==wanted:found.append((position+8,end))
  position=end
 if len(found)!=1:raise ValueError('Missing/duplicate original state chunk')
 return found[0]

def caller(sequence,entry):
 # SEI; busy NMI; original reset; wait 180 original 07F9 increments.
 code=bytearray(bytes.fromhex('78 a9 01 85 7b 20 7f e5 a2 b4 ac f9 07 cc f9 07 f0 fb ca d0 f5 a9'))
 code.extend([sequence,0x20,entry&255,entry>>8]);code.extend(bytes.fromhex('a9 01 8d f0 06'))
 idle=0x600+len(code);code.extend([0x4c,idle&255,idle>>8]);return bytes(code)

def prepare(recorder,state,sequence,entry):
 raw=state.read_bytes();buffer=C.create_string_buffer(raw)
 if not recorder.core.retro_unserialize(buffer,len(raw)):raise ValueError('Original core rejected base state')
 pointer=recorder.core.retro_get_memory_data(2);program=caller(sequence,entry)
 C.memmove(pointer+0x600,program,len(program));C.memset(pointer+0x6F0,0,1)
 core=recorder.core;core.retro_serialize_size.restype=C.c_size_t
 core.retro_serialize.argtypes=[C.c_void_p,C.c_size_t];core.retro_serialize.restype=C.c_bool
 size=core.retro_serialize_size();buffer=C.create_string_buffer(size)
 if not core.retro_serialize(buffer,size):raise ValueError('Fixture serialization failed')
 fixture=bytearray(buffer.raw);end=8+struct.unpack_from('<I',fixture,4)[0]
 cpu=chunk(fixture,8,end,b'CPU\0');registers=chunk(fixture,*cpu,b'REG\0')
 fixture[registers[0]:registers[1]]=bytes.fromhex('00 06 fd 00 00 00 24')
 raw=bytes(fixture);buffer=C.create_string_buffer(raw)
 if not core.retro_unserialize(buffer,len(raw)):raise ValueError('Original core rejected disclosed caller fixture')
 return sha(raw),program.hex()

def pcm_peak(raw):
 samples=array.array('h',raw)
 return max((abs(value)for value in samples),default=0)

def capture(rom,core,state,sequence,entry,count,directory):
 recorder=Recorder(rom,core,directory)
 try:
  fixture_sha,program=prepare(recorder,state,sequence,entry)
  blob=rom.read_bytes();descriptors=blob[16+2*8192+sequence*4:16+2*8192+(sequence+count)*4]
  allowed={descriptors[i]for i in range(0,len(descriptors),4)}
  channels=[descriptors[i+1]for i in range(0,len(descriptors),4)]
  if not allowed.issubset(SLOT_OFFSETS):raise ValueError('Unknown original audio slot')
  queued=None;inactive=None;ends=[0];rows=[];seen_active=False
  for frame in range(1,601):
   recorder.core.retro_run();ram=C.string_at(recorder.core.retro_get_memory_data(2),2048)
   active={offset for offset in SLOT_OFFSETS if ram[0x700+offset]!=255}
   rows.append(dict(frame=frame,active_slot_offsets=sorted(active),vibrato_clock=ram[0x7F9],busy=ram[0x7B],queued=ram[0x6F0],pcm_end=len(recorder.pcm)))
   ends.append(len(recorder.pcm))
   if ram[0x6F0]:
    if queued is None:queued=frame
    if not active.issubset(allowed):raise ValueError('Unrequested background audio slot became active')
    if active:seen_active=True
    elif seen_active and inactive is None:inactive=frame
   elif frame>1 and active:raise ValueError('Original reset did not clear background descriptors')
   if inactive is not None and frame>=inactive+20:break
  if queued is None or inactive is None:raise ValueError('Original cue did not finish under bounded capture')
  # The entire final pre-request frame must be silent after the long settling wait.
  silence=bytes(recorder.pcm[ends[queued-1]:ends[queued]])
  if pcm_peak(silence)>1:raise ValueError('Pre-cue background/filter residue remains audible')
  observed=rows[queued:]
  if any((b['vibrato_clock']-a['vibrato_clock'])%256!=1 for a,b in zip(observed,observed[1:])):raise ValueError('Original busy-NMI driver did not tick exactly once per frame')
  raw=bytes(recorder.pcm[ends[queued]:]);exported=seam_fade(raw,4)
  if pcm_peak(exported)<=1:raise ValueError('Original cue produced no audible PCM')
  return dict(raw=raw,exported=exported,full_sha=sha(recorder.pcm),fixture_sha=fixture_sha,program=program,frames=frame,queued=queued,inactive=inactive,slots=sorted(allowed),channels=channels,pre_cue_silence_peak=pcm_peak(silence),rows_sha=sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()),core=recorder.info,AV=recorder.av)
 finally:recorder.close()

def build(rom,core,state_root,out):
 blob=rom.read_bytes();state=state_root/BASE_STATE
 if sha(blob)!=ROM_SHA or sha(core.read_bytes())!=CORE_SHA or sha(state.read_bytes())!=STATE_SHA['strategy']:raise ValueError('Pinned original input mismatch; no files written')
 calls=[]
 for sequence,entry,offset,role in CALLS:
  expected=bytes([0xA9,sequence,0x20,entry&255,entry>>8])
  if blob[offset-2:offset+3]!=expected:raise ValueError('Original audio caller bytes changed')
  calls.append(dict(sequence_id=sequence,entry=entry,rom_offset=offset-2,rom_call_offset=offset,bytes=expected.hex(' '),original_role=role))
 tables=[]
 for name,offset,hexbytes in TABLES:
  expected=bytes.fromhex(hexbytes)
  if blob[offset:offset+len(expected)]!=expected:raise ValueError('Original tactic audio table/dispatcher changed')
  tables.append(dict(name=name,rom_offset=offset,bytes=hexbytes,sha256=sha(expected)))
 sound_table=bytes.fromhex(TABLES[1][2]);visual_table=bytes.fromhex(TABLES[2][2])
 for sequence in(0x88,0x8D,0x91,0x95):
  calls.append(dict(sequence_id=sequence,entry=CUES[sequence][0],rom_offset=218951,bytes=TABLES[0][2],original_role='table-driven original tactic sound dispatcher',selector_table_rom_offset=218977,visual_classes=[i for i,value in enumerate(sound_table)if value==sequence],tactic_ids=[i for i,value in enumerate(visual_table)if sound_table[value>>1]==sequence]))
 assets={};long_cues={}
 with tempfile.TemporaryDirectory(prefix='tk-original-effects-')as temporary:
  for sequence,(entry,count)in CUES.items():
   first=capture(rom,core,state,sequence,entry,count,Path(temporary));second=capture(rom,core,state,sequence,entry,count,Path(temporary))
   for key in('raw','exported','full_sha','fixture_sha','rows_sha'):
    if first[key]!=second[key]:raise ValueError('Two original cue captures differ: '+key)
   slug=f'seq-{sequence:02x}';path=out/'original/effects'/(slug+'.wav');path.parent.mkdir(parents=True,exist_ok=True)
   with wave.open(str(path),'wb')as stream:stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(48000);stream.writeframes(first['exported'])
   provenance=dict(capture_kind='isolated_original_driver_fixture',not_natural_gameplay=True,rom_modified=False,emulator_code_modified=False,base_state=BASE_STATE,base_state_sha256=sha(state.read_bytes()),fixture_sha256=first['fixture_sha'],cpu_registers={'pc':0x600,'sp':253,'a':0,'x':0,'y':0,'p':0x24},ram_caller_address=0x600,ram_caller_hex=first['program'],marker_address=0x6F0,original_reset=0xE57F,warmup_original_nmi_ticks=180,original_nmi_busy_flag={'address':0x7B,'value':1},driver_tick='original busy NMI calls A003/D8D4 once per frame',only_requested_slots_active=True,requested_slot_offsets=first['slots'],requested_channels=first['channels'],pre_cue_silence_peak_int16=first['pre_cue_silence_peak'],captured_frames=first['frames'],cue_queued_frame=first['queued'],all_slots_inactive_frame=first['inactive'],tail_frames=20,seam_fade_ms=4,pcm_source='unchanged original ROM driver and Nestopia APU/N163 audio callbacks',source_loop=False,repeat_full_pcm_sha256=[first['full_sha'],second['full_sha']],source_cue_pcm_sha256=sha(first['raw']),exported_pcm_sha256=sha(first['exported']),repeat_frame_trace_sha256=[first['rows_sha'],second['rows_sha']],original_callers=[row for row in calls if row['sequence_id']==sequence])
   assets[sequence]=dict(kind='original_rom_capture',path='/assets/audio/original/effects/'+path.name,request={'id':sequence,'entry':entry,'descriptor_count':count},duration=len(first['exported'])/4/48000,bytes=path.stat().st_size,sha256=sha(path.read_bytes()),sample_rate=48000,channels=2,provenance=provenance)
   print(f'{slug}: {assets[sequence]["duration"]:.3f}s; slots{first["slots"]}; silencepeak{first["pre_cue_silence_peak"]}; repeat PCM equal',flush=True)
  # These original long cues exist, but are not cut into misleading short effects.
  for key,sequence,offset in [('victory',0x6C,195910),('defeat',0x71,197181)]:
   expected=bytes([0xA9,sequence,0x20,0x83,0xE6])
   if blob[offset:offset+5]!=expected:raise ValueError('Original long-cue caller bytes changed')
   try:capture(rom,core,state,sequence,0xE683,5,Path(temporary))
   except ValueError as error:
    if str(error)!='Original cue did not finish under bounded capture':raise
   else:raise ValueError('Original long cue now finishes inside the bound; review its adaptation')
   long_cues[key]=dict(request={'id':sequence,'entry':0xE683,'descriptor_count':5},original_caller={'rom_offset':offset,'bytes':expected.hex(' ')},native_frame_budget=600,warmup_original_nmi_ticks=180,all_slots_inactive_not_observed=True,exported=False,note='Original counterpart exists; its long-form cue is not truncated. The web short result cue is an explicitly labelled reuse of another original sound.')
 effects={key:{**assets[sequence],'adoption_kind':kind,'label':label}for key,(sequence,kind,label)in BINDINGS.items()}
 result=dict(schema='tk2-original-effects-v1',rom_sha256=ROM_SHA,core=first['core'],AV=first['AV'],effects=effects,original_tactic_tables=tables,tactic_index_sequence_ids=[sound_table[value>>1]for value in visual_table],tactic_effect_keys=[f'tactic_{sound_table[value>>1]:02x}'for value in visual_table],unadapted_original_long_cues=long_cues,rights='Original ROM sound recordings retain original game rights. Newly assigned UI meanings are marked authorial_ui_reuse; no dedicated original cancel routine is claimed.',tool_sha256=sha(Path(__file__).read_bytes()),recorder_sha256=sha((Path(__file__).parent/'capture_original.py').read_bytes()))
 (out/'effects.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--rom',type=Path,required=True);parser.add_argument('--core',type=Path,required=True);parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--out',type=Path,default=ROOT/'game/assets/audio');args=parser.parse_args()
 build(args.rom.resolve(),args.core.resolve(),args.state_root.resolve(),args.out.resolve())
