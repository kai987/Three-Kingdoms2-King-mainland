#!/usr/bin/env python3
"""Capture original scene music from the user's pinned ROM with unmodified Nestopia.

Offline only: the game ships MP3 assets and never reads a ROM, emulator or state.
Requires an arm64 libretro Nestopia core, the explicit external state root and
ffmpeg. No ROM/core memory, CPU entry point, input or game state is patched.
"""
from __future__ import annotations
import argparse
import array
import ctypes as C
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

ROOT=Path(__file__).resolve().parents[2]
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CORE_SHA='924191ebb41b863993a96cf461321058b391c507a6fed2f1203df44eaa5a539a'
CASES={
 'menu':dict(slug='title',state='analysis/runtime/title.state',start=2177,period=3064,request=176,entry=0xE673,count=7,label='原版標題場景',loop_kind='original_title_controller_restart'),
 'strategy':dict(slug='strategy',state='analysis/runtime/map-ready.state',start=1,period=1536,request=129,entry=0xE673,count=7,label='原版戰略地圖',loop_kind='original_music_driver_loop'),
 'battle':dict(slug='battle',state='analysis/runtime/phase3/battle-tactics-true.state',start=1,period=2304,request=29,entry=0xE673,count=7,label='原版戰場',loop_kind='original_music_driver_loop'),
 'duel':dict(slug='duel',state='analysis/phase11/runtime/duel-return/first-duel-main-03.state',start=1408,period=4464,request=18,entry=0xE67B,count=6,label='原版單挑',loop_kind='original_music_driver_loop'),
}
STATE_SHA={
 'menu':'aebf5ce50d70604969dae65105e281f673d298271e6c75e070d0ff2d2c2323ee',
 'strategy':'7579ff3f4b26afadb759a4bf258a30a90b2cf97e067b376e9a3186d5e7354837',
 'battle':'af7f2175a19e81527b15d87416458bf364fdc9484ea6db3abac424ad92e0ad70',
 'duel':'192f6efc45b19495a4b5fa9bdb34fb2024fec3e7e53f7a3d64c470c70edfbc45',
}
ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
VIDEO=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AUDIO=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
POLL=C.CFUNCTYPE(None)
INPUT=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)
class Variable(C.Structure):_fields_=[('key',C.c_char_p),('value',C.c_char_p)]
class GameInfo(C.Structure):_fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class SystemInfo(C.Structure):_fields_=[('name',C.c_char_p),('version',C.c_char_p),('extensions',C.c_char_p),('fullpath',C.c_bool),('extract',C.c_bool)]
class Geometry(C.Structure):_fields_=[('w',C.c_uint),('h',C.c_uint),('maxw',C.c_uint),('maxh',C.c_uint),('aspect',C.c_float)]
class Timing(C.Structure):_fields_=[('fps',C.c_double),('sample_rate',C.c_double)]
class AVInfo(C.Structure):_fields_=[('geometry',Geometry),('timing',Timing)]
def sha(data):return hashlib.sha256(data).hexdigest()
class Recorder:
 def __init__(self,rom,core,directory):
  self.core=C.CDLL(str(core));self.directory=str(directory).encode();self.options={};self.pcm=bytearray()
  self.callbacks=[ENV(self.environment),VIDEO(lambda *args:None),AUDIO(self.sample),BATCH(self.batch),POLL(lambda:None),INPUT(lambda *args:0)]
  for name,callback in zip(['environment','video_refresh','audio_sample','audio_sample_batch','input_poll','input_state'],self.callbacks):
   setter=getattr(self.core,'retro_set_'+name);setter.argtypes=[type(callback)];setter(callback)
  self.core.retro_init();self.core.retro_get_system_info.argtypes=[C.POINTER(SystemInfo)];info=SystemInfo();self.core.retro_get_system_info(C.byref(info))
  self.info={'name':info.name.decode(),'version':info.version.decode(),'sha256':sha(core.read_bytes())}
  self.blob=C.create_string_buffer(rom.read_bytes());self.game=GameInfo(str(rom).encode(),C.cast(self.blob,C.c_void_p),rom.stat().st_size,None)
  self.core.retro_load_game.argtypes=[C.POINTER(GameInfo)];self.core.retro_load_game.restype=C.c_bool
  if not self.core.retro_load_game(C.byref(self.game)):raise ValueError('Original core rejected ROM')
  self.core.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];self.core.retro_unserialize.restype=C.c_bool
  self.core.retro_get_memory_data.argtypes=[C.c_uint];self.core.retro_get_memory_data.restype=C.c_void_p
  self.core.retro_get_system_av_info.argtypes=[C.POINTER(AVInfo)];av=AVInfo();self.core.retro_get_system_av_info(C.byref(av))
  self.av={'fps':av.timing.fps,'sample_rate':av.timing.sample_rate};assert self.av['sample_rate']==48000
 def environment(self,command,data):
  command&=0xffff
  if command in (9,30,31):C.cast(data,C.POINTER(C.c_char_p))[0]=self.directory;return True
  if command==10:return C.cast(data,C.POINTER(C.c_int))[0]in(0,1,2)
  if command==16:
   variables=C.cast(data,C.POINTER(Variable));i=0
   while variables[i].key:
    variable=variables[i];self.options[variable.key.decode()]=variable.value.decode().split(';',1)[-1].strip().split('|')[0].encode();i+=1
   self.options.update(nestopia_blargg_ntsc_filter=b'disabled',nestopia_overscan_v_top=b'0',nestopia_overscan_v_bottom=b'0');return True
  if command==15:
   variable=C.cast(data,C.POINTER(Variable)).contents;value=self.options.get(variable.key.decode())
   if value is None:return False
   variable.value=value;return True
  if command in(3,17):C.cast(data,C.POINTER(C.c_bool))[0]=command==3;return True
  if command==47:C.cast(data,C.POINTER(C.c_int))[0]=3;return True
  if command==39:C.cast(data,C.POINTER(C.c_uint))[0]=0;return True
  return command in(11,18,35,36,37)
 def sample(self,left,right):self.pcm.extend(int(left).to_bytes(2,'little',signed=True)+int(right).to_bytes(2,'little',signed=True))
 def batch(self,data,count):self.pcm.extend(C.string_at(data,count*4));return count
 def capture(self,state,frames):
  raw=state.read_bytes();buffer=C.create_string_buffer(raw)
  if not self.core.retro_unserialize(buffer,len(raw)):raise ValueError('Original core rejected state')
  keys=[];ends=[0];scenes=[]
  for _ in range(frames):
   self.core.retro_run();ram=C.string_at(self.core.retro_get_memory_data(2),2048)
   keys.append(sha(ram[0x700:0x7f2]+bytes([ram[0x7f6],ram[0x7f9]&15])))
   ends.append(len(self.pcm));scenes.append([ram[0x7a],ram[0x78]])
  return bytes(self.pcm),keys,ends,scenes
 def close(self):self.core.retro_unload_game();self.core.retro_deinit()
def seam_fade(raw,milliseconds=4):
 values=array.array('h',raw)
 if sys.byteorder!='little':values.byteswap()
 length=len(values)//2;fade=min(round(48*milliseconds),length//2)
 for i in range(fade):
  gain=i/(fade-1)
  for channel in(0,1):
   values[2*i+channel]=round(values[2*i+channel]*gain)
   index=2*(length-1-i)+channel;values[index]=round(values[index]*gain)
 if sys.byteorder!='little':values.byteswap()
 return values.tobytes()
def build(rom,core,state_root,out,ffmpeg):
 if sha(rom.read_bytes())!=ROM_SHA or sha(core.read_bytes())!=CORE_SHA:raise ValueError('Pinned ROM/core hash mismatch; no assets written')
 if any(sha((state_root/case['state']).read_bytes())!=STATE_SHA[scene]for scene,case in CASES.items()):raise ValueError('Pinned original scene state mismatch; no assets written')
 tracks={};core_info=None
 with tempfile.TemporaryDirectory(prefix='tk-original-audio-')as folder:
  temporary=Path(folder)
  for scene,case in CASES.items():
   state=state_root/case['state'];start,period=case['start'],case['period'];frames=start+2*period
   captures=[]
   for repetition in range(2):
    recorder=Recorder(rom,core,temporary)
    try:
     pcm,keys,ends,scenes=recorder.capture(state,frames);core_info=recorder.info;av=recorder.av
    finally:recorder.close()
    if keys[start-1:start-1+period]!=keys[start-1+period:start-1+2*period]:raise ValueError(f'{scene}: complete audio driver/vibrato period changed')
    captures.append(sha(pcm))
   if captures[0]!=captures[1]:raise ValueError(f'{scene}: two original PCM captures differ')
   raw=pcm[ends[start]:ends[start+period]];exported=seam_fade(raw)
   wav_path=temporary/(case['slug']+'.wav')
   with wave.open(str(wav_path),'wb')as stream:
    stream.setnchannels(2);stream.setsampwidth(2);stream.setframerate(48000);stream.writeframes(exported)
   output=out/'original'/(case['slug']+'.mp3');output.parent.mkdir(parents=True,exist_ok=True)
   subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-i',str(wav_path),'-map_metadata','-1','-codec:a','libmp3lame','-q:a','2',str(output)],check=True)
   duration=len(raw)/4/48000
   tracks[scene]=dict(path='/assets/audio/original/'+output.name,kind='original_rom_capture',label=case['label'],sha256=sha(output.read_bytes()),bytes=output.stat().st_size,duration=duration,loop_start=0,loop_end=duration,sample_rate=48000,channels=2,
    request=dict(id=case['request'],entry=case['entry'],descriptor_count=case['count']),provenance=dict(state_source=case['state'],state_sha256=sha(state.read_bytes()),captured_frames=frames,source_loop_frames=[start,start+period],period_frames=period,loop_kind=case['loop_kind'],key_fields=['0700..07F1','07F6','07F9 & 0F'],whole_period_state_comparison=True,repeat_original_pcm_sha256=captures,source_loop_pcm_sha256=sha(raw),exported_pcm_sha256=sha(exported),stereo_sample_frames=len(raw)//4,seam_fade_ms=4,observed_global_nmi_states=sorted({tuple(row)for row in scenes}),controller_inputs=[],rom_modified=False,core_memory_modified=False,pcm_source='unchanged Nestopia libretro audio callbacks'))
   print(f'{scene}: {period} frames / {duration:.3f}s / {output.stat().st_size} bytes',flush=True)
 result=dict(schema='tk2-original-audio-v1',rom_sha256=ROM_SHA,core=core_info,AV=av,tracks=tracks,rights='Original game recordings retain their original rights; captured from the user-provided ROM. Synthesized additions are separately identified.',tool_sha256=sha(Path(__file__).read_bytes()))
 out.mkdir(parents=True,exist_ok=True);(out/'index.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--rom',type=Path,required=True);parser.add_argument('--core',type=Path,required=True);parser.add_argument('--state-root',type=Path,required=True);parser.add_argument('--out',type=Path,default=ROOT/'game/assets/audio');parser.add_argument('--ffmpeg',default='ffmpeg');args=parser.parse_args()
 build(args.rom.resolve(),args.core.resolve(),args.state_root.resolve(),args.out.resolve(),args.ffmpeg)
