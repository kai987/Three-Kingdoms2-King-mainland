#!/usr/bin/env python3
"""Replay the original ROM in Nestopia libretro, capture pixels/RAM/save states.

This uses a complete third-party NES core, unlike the bounded py65 trace.
No original ROM bytes are modified. Inputs and imported save state are explicit.
"""
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BUTTONS={'b':0,'select':2,'start':3,'up':4,'down':5,'left':6,'right':7,'a':8}
ENV=C.CFUNCTYPE(C.c_bool,C.c_uint,C.c_void_p)
VIDEO=C.CFUNCTYPE(None,C.c_void_p,C.c_uint,C.c_uint,C.c_size_t)
AUDIO=C.CFUNCTYPE(None,C.c_int16,C.c_int16)
BATCH=C.CFUNCTYPE(C.c_size_t,C.c_void_p,C.c_size_t)
POLL=C.CFUNCTYPE(None)
INPUT=C.CFUNCTYPE(C.c_int16,C.c_uint,C.c_uint,C.c_uint,C.c_uint)

class Variable(C.Structure):
    _fields_=[('key',C.c_char_p),('value',C.c_char_p)]
class GameInfo(C.Structure):
    _fields_=[('path',C.c_char_p),('data',C.c_void_p),('size',C.c_size_t),('meta',C.c_char_p)]
class SystemInfo(C.Structure):
    _fields_=[('library_name',C.c_char_p),('library_version',C.c_char_p),('valid_extensions',C.c_char_p),('need_fullpath',C.c_bool),('block_extract',C.c_bool)]

class Runtime:
    def __init__(self,rom,out,core=None):
        self.rom=Path(rom);self.out=Path(out);self.out.mkdir(parents=True,exist_ok=True)
        self.blob=self.rom.read_bytes();self.core_path=core or ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
        self.core=C.CDLL(str(self.core_path));self.buttons=set();self.options={};self.format=0;self.frame=None;self.frames=0
        self.directory=str(self.out.resolve()).encode();self.events=[]
        self.callbacks=[ENV(self.environment),VIDEO(self.video),AUDIO(lambda l,r:None),BATCH(lambda data,count:count),POLL(lambda:None),INPUT(self.input)]
        for name,cb in zip(['environment','video_refresh','audio_sample','audio_sample_batch','input_poll','input_state'],self.callbacks):
            getattr(self.core,'retro_set_'+name).argtypes=[type(cb)];getattr(self.core,'retro_set_'+name)(cb)
        self.core.retro_get_system_info.argtypes=[C.POINTER(SystemInfo)]
        self.core.retro_init();info=SystemInfo();self.core.retro_get_system_info(C.byref(info))
        self.info={'name':info.library_name.decode(),'version':info.library_version.decode(),'core_sha256':hashlib.sha256(Path(self.core_path).read_bytes()).hexdigest()}
        self.buf=C.create_string_buffer(self.blob);self.game=GameInfo(str(self.rom.resolve()).encode(),C.cast(self.buf,C.c_void_p),len(self.blob),None)
        self.core.retro_load_game.argtypes=[C.POINTER(GameInfo)];self.core.retro_load_game.restype=C.c_bool
        if not self.core.retro_load_game(C.byref(self.game)):raise RuntimeError('Nestopia rejected ROM')
        self.core.retro_get_memory_size.argtypes=[C.c_uint];self.core.retro_get_memory_size.restype=C.c_size_t
        self.core.retro_get_memory_data.argtypes=[C.c_uint];self.core.retro_get_memory_data.restype=C.c_void_p
        self.core.retro_serialize_size.restype=C.c_size_t
        self.core.retro_serialize.argtypes=[C.c_void_p,C.c_size_t];self.core.retro_serialize.restype=C.c_bool
        self.core.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];self.core.retro_unserialize.restype=C.c_bool

    def environment(self,cmd,data):
        basic=cmd&0xffff
        if basic in (9,30,31):C.cast(data,C.POINTER(C.c_char_p))[0]=self.directory;return True
        if basic==10:self.format=C.cast(data,C.POINTER(C.c_int))[0];return self.format in (0,1,2)
        if basic==16:
            variables=C.cast(data,C.POINTER(Variable));i=0
            while variables[i].key:
                v=variables[i];key=v.key.decode();options=v.value.decode().split(';',1)[-1].strip().split('|')
                self.options[key]=options[0].encode();i+=1
            # Disable synthetic composite filtering/cropping for native pixels.
            self.options.update(nestopia_blargg_ntsc_filter=b'disabled',
                                nestopia_overscan_v_top=b'0',nestopia_overscan_v_bottom=b'0')
            return True
        if basic==15:
            v=C.cast(data,C.POINTER(Variable)).contents
            if v.key.decode() not in self.options:return False
            v.value=self.options[v.key.decode()];return True
        if basic in (3,17):C.cast(data,C.POINTER(C.c_bool))[0]=(basic==3);return True
        if basic==47:C.cast(data,C.POINTER(C.c_int))[0]=3;return True
        if basic==39:C.cast(data,C.POINTER(C.c_uint))[0]=0;return True
        if basic in (11,18,35,36,37):return True
        return False

    def input(self,port,device,index,ident):
        return int(port==0 and device==1 and ident in self.buttons)

    def video(self,data,w,h,pitch):
        if not data:return
        raw=C.string_at(data,pitch*h)
        if self.format==1:
            self.frame=Image.frombytes('RGB',(w,h),raw,'raw','BGRX',pitch)
        else:
            pixels=[]
            for y in range(h):
                for x in range(w):
                    v=int.from_bytes(raw[y*pitch+x*2:y*pitch+x*2+2],'little')
                    if self.format==2:r=(v>>11)&31;g=(v>>5)&63;b=v&31;pixels.append((r*255//31,g*255//63,b*255//31))
                    else:r=(v>>10)&31;g=(v>>5)&31;b=v&31;pixels.append((r*255//31,g*255//31,b*255//31))
            self.frame=Image.new('RGB',(w,h));self.frame.putdata(pixels)

    def run(self,frames,buttons=(),observer=None):
        self.buttons={BUTTONS[b] for b in buttons}
        self.events.append({'start_frame':self.frames,'frames':frames,'buttons':list(buttons)})
        for _ in range(frames):
            self.core.retro_run();self.frames+=1
            if observer is not None:observer(self)
        self.buttons=set()

    def memory(self,ident):
        size=self.core.retro_get_memory_size(ident);ptr=self.core.retro_get_memory_data(ident)
        return C.string_at(ptr,size) if size and ptr else b''

    def snapshot(self,label):
        if self.frame is None:raise RuntimeError('No framebuffer')
        self.frame.save(self.out/(label+'.png'))
        for ident,name in [(0,'sram'),(2,'ram'),(3,'vram')]:
            (self.out/(label+'-'+name+'.bin')).write_bytes(self.memory(ident))
        size=self.core.retro_serialize_size();buf=C.create_string_buffer(size)
        if not self.core.retro_serialize(buf,size):raise RuntimeError('Serialization failed')
        (self.out/(label+'.state')).write_bytes(buf.raw)
        ram=self.memory(2)
        metadata={'label':label,'frames':self.frames,'rom_sha256':hashlib.sha256(self.blob).hexdigest(),
                  'engine':self.info,'pixel_format':self.format,'image_size':list(self.frame.size),
                  'core_options':{k:v.decode() for k,v in self.options.items()},
                  'events':self.events,'ram_bytes':len(ram),'sram_bytes':len(self.memory(0)),
                  'vram_bytes':len(self.memory(3)),
                  'state_007a':ram[0x7a] if len(ram)>0x7a else None,
                  'limitations':['Emulator rendering is not physical console validation.',
                                 'Save states belong to this pinned core; original ROM is unchanged.']}
        (self.out/(label+'.json')).write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
        return metadata

    def load_state(self,path):
        raw=Path(path).read_bytes();buf=C.create_string_buffer(raw)
        if not self.core.retro_unserialize(buf,len(raw)):raise RuntimeError('State rejected')
        self.events.append({'imported_state':str(path),'sha256':hashlib.sha256(raw).hexdigest()})

    def close(self):self.core.retro_unload_game();self.core.retro_deinit()

def main():
    p=argparse.ArgumentParser();p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,default=ROOT/'analysis/runtime');p.add_argument('--state',type=Path)
    p.add_argument('--plan',type=Path);p.add_argument('--frames',type=int,default=300);p.add_argument('--label',default='boot')
    a=p.parse_args();r=Runtime(a.rom,a.out)
    try:
        if a.state:r.load_state(a.state)
        if a.plan:
            for step in json.loads(a.plan.read_text()):
                r.run(step['frames'],step.get('buttons',[]))
                if step.get('capture'):r.snapshot(step['capture'])
        else:r.run(a.frames)
        print(json.dumps(r.snapshot(a.label),ensure_ascii=False))
    finally:r.close()

if __name__=='__main__':main()
