#!/usr/bin/env python3
"""Capture the pinned original core's actual PCM alongside its native video.

This extends, without modifying, the earlier Runtime. It only observes the
libretro audio/video callbacks. No ROM or running-core memory is patched.
"""
import ctypes as C
import hashlib
import wave
from pathlib import Path
from nes_runtime import Runtime,AUDIO,BATCH

class Geometry(C.Structure):
    _fields_=[('base_width',C.c_uint),('base_height',C.c_uint),('max_width',C.c_uint),('max_height',C.c_uint),('aspect_ratio',C.c_float)]
class Timing(C.Structure):
    _fields_=[('fps',C.c_double),('sample_rate',C.c_double)]
class AVInfo(C.Structure):
    _fields_=[('geometry',Geometry),('timing',Timing)]

class ServiceRuntime(Runtime):
    def __init__(self,rom,out,core=None):
        super().__init__(rom,out,core)
        self.pcm=bytearray();self.audio_calls=[]
        self.callbacks[2]=AUDIO(self.audio_sample);self.callbacks[3]=BATCH(self.audio_batch)
        self.core.retro_set_audio_sample(self.callbacks[2]);self.core.retro_set_audio_sample_batch(self.callbacks[3])
        self.core.retro_get_system_av_info.argtypes=[C.POINTER(AVInfo)]
        info=AVInfo();self.core.retro_get_system_av_info(C.byref(info))
        self.av_info={'fps':info.timing.fps,'sample_rate':info.timing.sample_rate,
                      'native_dimensions':[info.geometry.base_width,info.geometry.base_height]}
        self.audio_frame_start=0

    def audio_sample(self,left,right):
        self.pcm.extend(int(left).to_bytes(2,'little',signed=True)+int(right).to_bytes(2,'little',signed=True))

    def audio_batch(self,data,count):
        raw=C.string_at(data,count*4);self.pcm.extend(raw)
        self.audio_calls.append({'emulated_frame_start':self.frames,'stereo_sample_frames':int(count),'pcm_sha256':hashlib.sha256(raw).hexdigest()})
        return count

    def pcm_frame(self):
        raw=bytes(self.pcm[self.audio_frame_start:]);self.audio_frame_start=len(self.pcm)
        return raw

    def save_wav(self,path,start=0,stop=None):
        raw=bytes(self.pcm[start:stop]);assert len(raw)%4==0
        with wave.open(str(path),'wb')as w:
            w.setnchannels(2);w.setsampwidth(2);w.setframerate(round(self.av_info['sample_rate']));w.writeframes(raw)
        return {'sample_rate':self.av_info['sample_rate'],'stereo_sample_frames':len(raw)//4,
                'PCM_bytes':len(raw),'PCM_sha256':hashlib.sha256(raw).hexdigest(),
                'WAV_sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest()}
