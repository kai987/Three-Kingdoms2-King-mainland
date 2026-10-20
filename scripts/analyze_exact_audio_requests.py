#!/usr/bin/env python3
"""Read-only original-byte closure of exact fixed audio reset/request services."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from inspect_game_data import OPS,SIZES
from analyze_battle_scene_controller import BRANCHES
from source.recovered.exact_audio_requests import ExactAudioRequests,ROM_SHA256
OUT=ROOT/'analysis/phase16/audio-requests'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def analyze(rom):
    I={};todo=list(ExactAudioRequests.PUBLIC_ENTRIES);modes={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp'}
    while todo:
        pc=todo.pop()
        if pc in I:continue
        if not 0xE57F<=pc<0xE6A6:raise ValueError(f'Outside bounded fixed request body${pc:04X}')
        f=16+31*8192+(pc&8191);op,mode=OPS[rom[f]];size=SIZES[mode];nxt=pc+size;v=int.from_bytes(rom[f+1:f+size],'little')
        if op=='?':raise ValueError('Decoded immutabletable ascode')
        if op in BRANCHES:v=(nxt+(v if v<128 else v-256))&65535
        x=dict(physical_bank=31,pc=pc,cpu_address=pc,rom_offset=f,op=op,mode=modes.get(mode,mode),operand=v,next_pc=nxt,raw_hex=rom[f:f+size].hex());I[pc]=x
        if op=='RTS':continue
        if op=='JSR':
            if v==0xF25F:x['external_target']=v
            else:todo.append(v)
            todo.append(nxt)
        elif op=='JMP':todo.append(v)
        elif op in BRANCHES:todo.extend((v,nxt))
        else:todo.append(nxt)
    tables=[]
    for bank,pc,size,role in[(31,0xE667,4,'oldAPU channel disablemasks'),(31,0xE6A6,32,'initial N163wave data'),(2,0x8000,732,'183 legitimate4-byte music descriptors')]:
        off=16+bank*8192+(pc&8191);tables.append(dict(physical_bank=bank,cpu_address=pc,rom_offset=off,length=size,role=role,raw_hex=rom[off:off+size].hex(),sha256=hashlib.sha256(rom[off:off+size]).hexdigest()))
    OUT.mkdir(parents=True,exist_ok=True);c=dict(schema='phase16-exact-fixed-audio-original-bytes-v1',rom_sha256=ROM_SHA256,instruction_count=len(I),entries=list(ExactAudioRequests.PUBLIC_ENTRIES),original_instructions=sorted(I.values(),key=lambda x:x['pc']),data_tables=tables,sole_external=dict(call_pc=0xE60B,target=0xF25F,already_recovered=True))
    (OUT/'static-catalog.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
    (OUT/'original.asm').write_text('; Original fixedaudio code, offsets include16-byte header.\n'+'\n'.join(f'b31:${pc:04X} file{x["rom_offset"]:06X} {x["raw_hex"]:8s} {x["op"]} {x["mode"]} ${x["operand"]:04X}'for pc,x in sorted(I.items()))+'\n')
    print(json.dumps(dict(instructions=len(I),tables=len(tables),source_sha256=sha(ROOT/'source/recovered/exact_audio_requests.py'))))
def evidence():
    c=json.loads((OUT/'static-catalog.json').read_text());v=json.loads((OUT/'validation.json').read_text());body={x['pc']for x in c['original_instructions']};dynamic={x['cpu_address']for x in v['executed_original_locations']if x['physical_bank']==31}&body
    paths=['source/recovered/exact_audio_requests.py','source/recovered/global_ui_controller.py','source/recovered/scene_shared_services.py','source/recovered/service_memory.py','source/recovered/mapped_memory.py','source/recovered/battle_nmi_services.py','scripts/analyze_exact_audio_requests.py','scripts/verify_exact_audio_requests.py']
    e=dict(schema='phase16-exact-fixed-audio-source-evidence-v1',status=v['status'],rom_sha256=ROM_SHA256,source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256={p:sha(ROOT/p)for p in paths},artifact_sha256={str((OUT/p).relative_to(ROOT)):sha(OUT/p)for p in('static-catalog.json','original.asm','validation.json')},
        static_instruction_count=len(body),dynamic_instruction_count=len(dynamic),unexecuted_positions=sorted(body-dynamic),comparison=v['comparison'],rom_cpu_case_count=v['rom_cpu_case_count'],complete_return_count=v['complete_return_count'],strict_prefix_count=v['strict_prefix_count'],source_guard_case_count=v['source_guard_case_count'],limits=v['limits'])
    callers=json.loads((OUT/'actual-callers.json').read_text())if(OUT/'actual-callers.json').exists()else None
    if callers:
        e['genuine_callee_input_case_count']=callers['rom_cpu_case_count'];e['total_ROM_CPU_comparisons_including_genuine_callers']=v['rom_cpu_case_count']+callers['rom_cpu_case_count']
        e['artifact_sha256'][str((OUT/'actual-callers.json').relative_to(ROOT))]=sha(OUT/'actual-callers.json')
        e['genuine_callee_comparison_status']=callers['status']
    (OUT/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
    (OUT/'README.md').write_text(f'''# 固定音频reset/request的真实caller协议

[ExactAudioRequests](../../../source/recovered/exact_audio_requests.py)独立恢复固定31 E57F reset、E590硬件配置、E609 descriptor载入及连续请求入口。生产是手写具名函数和循环，不执行原CPU/IR；旧AudioServices、SceneShared和phase15音序正文不改。原E5FA/E5FB/E5FF/E607的PHA/PLA和每次真实JSR留在原栈，包括原玩家战后反馈曾在01F5..01FB留下的字节。

E673载入连续7项、独立入口E67B为6项、E683为5项、E68B为4项、E693为3项、E69B为2项，E66B为8项；每次加1为原8bit wrap，最后真正tail E609。E57F先载入descriptor0..6再关闭全部11音槽、写APU及N163初始化数据，最后写A5/F800=4C。E609通过真实F25F选择physical2，读4B记录；已有active APUchannel0..3先清4015对应位，然后替换slotchannel/streampointer/state。N163寄存器图和端口请求都是真实软件写入；没有合成PCM或完成音乐。

唯一外部软件依赖为E60B→F25F，已有独立固定源码。API要求实际AXYP/SP/PC及既有callerword，不能seed返回；未知/未实际返回的F25F保持同一ServiceCall与generator。预算也保留真实位置，需显式正预算才能resume。

另[实际caller回执](actual-callers.json)保留19个原JSR音频入口，来自正式玩家Native内存的受控原CPU A00C前序，包括reset内部嵌套调用；原parent1137步仅为上下文生成，不另加Native父案或视频帧。它们不是Nestopia内部CPU trace，与主体矩阵单列。

原CPU矩阵 {v['rom_cpu_case_count']} 例：{v['complete_return_count']}完整真实callerRTS、{v['strict_prefix_count']}严格前缀，另{v['source_guard_case_count']}源码guard，失败{v['failed_count']}。全部2048B RAM（闲置栈也包括）、8192B SRAM、AXYP/SP/PC、银行、端口读写序与N163图逐byte一致。静态{len(body)}位置、动态{len(dynamic)}，剩余位置在evidence列明。Descriptor0..182为已确认游戏数据；bytewrap扩展病例与正常音序入口范围分别列在回执，不由极值fixture声称自然曲目/音效。

```python
owner = ExactAudioRequests(memory, rom, services=exact_fixed_services)
owner.run_entry(0xE683, registers=actual_caller)
owner(actual_ServiceCall)
owner.resume()  # 同一真实caller，等待依赖完成
```

```sh
python3 scripts/analyze_exact_audio_requests.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_exact_audio_requests.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_exact_audio_requests.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --genuine-only
python3 scripts/analyze_exact_audio_requests.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
```

[原汇编](original.asm) · [静态来源](static-catalog.json) · [CPU回执](validation.json) · [最终pins](evidence.json)
''')
    print(json.dumps(dict(status=e['status'],CPU=e['rom_cpu_case_count'],guards=e['source_guard_case_count'],dynamic=len(dynamic),source_sha256=e['source_sha256'][paths[0]])))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--evidence-only',action='store_true');a=p.parse_args();r=a.rom.read_bytes();assert hashlib.sha256(r).hexdigest()==ROM_SHA256
    if a.evidence_only:evidence()
    else:analyze(r)
if __name__=='__main__':main()
