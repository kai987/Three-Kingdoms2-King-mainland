#!/usr/bin/env python3
"""Offline structure14A003/15D8D4 into direct readable audio caller services."""
from pathlib import Path
import argparse,ast,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from analyze_city_ui_controller import collect
from analyze_global_ui_controller import compiler
from ui_structuring import labelled_procedure,loop_exception_source
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase15/audio-domain';SOURCE=ROOT/'source/recovered/audio_scene_services.py'
NAMES={0xA003:'audio_entry',0xD8D4:'update_audio_driver',0xD99B:'decode_stream_commands',
    0xDC03:'write_frequency_high',0xDC31:'channel_disabled_mask',0xDC3F:'stop_note',
    0xDC90:'apply_vibrato',0xDCD8:'apply_volume_slide',0xDF6E:'apply_volume',
    0xDF71:'emit_current_volume',0xDF92:'write_N163_volume_and_wave_pair'}
HEADER='''"""Exact audio scene caller service, including real local frames and idle stack.

Named Python functions implement the original stream parser and APU/N163
requests. Immutable ROM bytes supply tables/music data, never executable code
or IR. No oscillator, PCM, video frame, IRQ or readiness is synthesized.
"""
from dataclasses import dataclass
from .global_ui_controller import UIControlBase,UIRegisters,C,Z,I,D,B,U,V,N
from .battle_nmi_services import ServiceCall

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
AudioRegisters=UIRegisters

@dataclass(frozen=True)
class AudioBlockBudget:
    pc:int
    reason:str='Explicit structured-control block budget; no artificial return'

class AudioSceneServices(UIControlBase):
    """Physical14 A003 ->15D8D4 caller protocol on shared mapped memory.

    run_entry requires actual registers and an existing caller frame. Only
    fixedF25F is external. All localJSR/PHA/PLA/free-stack writes are real,
    notably the pairedDF92/DF93 pushes used for N163 volume/wave requests.
    LegacyAudioServices remains unchanged with its semantic stack exclusions.
    """
    PAIR=(14,15)
    PUBLIC_ENTRIES=(0xA003,0xD8D4)
    def __init__(self,memory,rom,services=None):
        super().__init__(memory,rom,services);self._call_owner=None
    def fields(self):
        m=self.memory
        return dict(slot_states=tuple(m[0x700+x]for x in range(0,242,22)),
            channel=m[0x7F3],disable_mask=m[0x7F2],frame_cursor=m[0x7F9],
            data_window=m[0xE1],second_data_window=m[0xE2],wave_address=m[0xA5])
    def _checkpoint(self,pc):
        self.registers.pc=pc
        if self._blocks>=self._limit:yield AudioBlockBudget(pc)
        self._blocks+=1
    def _drive(self):
        while True:
            if self.pending is not None:
                if isinstance(self.pending,AudioBlockBudget):return self._result('budget')
                call=self.pending
                if self.services is None:return self._result('dependency')
                result=self.services(call)
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
    def resume(self,*,max_blocks=None):
        if self._program is None:raise RuntimeError('No actual pending audio caller')
        if max_blocks is not None:
            if not isinstance(max_blocks,int)or max_blocks<=0:raise ValueError('Explicit positive additional block budget required')
            if not isinstance(self.pending,AudioBlockBudget):raise ValueError('No structured budget boundary is pending')
            self._limit=self._blocks+max_blocks;self.pending=None
        return self._drive()
    def run_entry(self,entry=0xA003,*,registers=None,return_pc=None,max_blocks=200000):
        if registers is None:raise ValueError('Supply actual caller registers and existing stack; no seeded return')
        if entry not in self.PUBLIC_ENTRIES:raise ValueError('Only genuine audio scene export/body entries')
        if tuple(getattr(self.memory,'banks',())[1:3])!=self.PAIR:raise ValueError('Audio entry requires physical14/15 caller context')
        if not isinstance(max_blocks,int)or max_blocks<0:raise ValueError('Nonnegative explicit block budget required')
        actual_return=((self.memory[0x100+((registers.sp+1)&255)]|self.memory[0x100+((registers.sp+2)&255)]<<8)+1)&65535
        if return_pc is not None and return_pc!=actual_return:raise ValueError('Caller returnPC must match the existing stack word')
        return super().run_entry(entry,registers=registers,return_pc=return_pc,max_blocks=max_blocks)
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA003,registers=registers,**kwargs)

'''
def digest(b):return hashlib.sha256(b).hexdigest()
def evidence():
    v=json.loads((OUT/'validation.json').read_text());w=json.loads((OUT/'writer-provenance.json').read_text());catalog=json.loads((OUT/'static-catalog.json').read_text())
    src=json.loads((OUT/'source-catalog.json').read_text());body={x['pc']for x in catalog['original_instructions']}
    dynamic={x['cpu_address']for x in v['executed_original_locations']if x['physical_bank']in(14,15)}&body
    paths=['source/recovered/audio_scene_services.py','source/recovered/global_ui_controller.py','source/recovered/scene_shared_services.py',
        'source/recovered/battle_nmi_services.py','source/recovered/audio_services.py','source/recovered/service_memory.py','source/recovered/mapped_memory.py',
        'scripts/analyze_audio_scene_services.py','scripts/verify_audio_scene_services.py','scripts/trace_cooperation_audio_writer.py']
    receipts={str((OUT/name).relative_to(ROOT)):digest((OUT/name).read_bytes())for name in('validation.json','writer-provenance.json','static-catalog.json','source-catalog.json','original.asm')}
    actual_writers=[dict(heir=r['heir'],NMI=r['NMI'],writer=x)for r in w['rows']for x in r['actual_stack_writers']if x['stack_address']==0x1EC]
    e=dict(schema='phase15-audio-scene-direct-source-evidence-v1',status='passed'if v['status']==w['status']=='passed'else'failed',rom_sha256=SHA,
        source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256={p:digest((ROOT/p).read_bytes())for p in paths},artifact_sha256=receipts,
        body_instruction_count=len(body),dynamic_body_positions=len(dynamic),unexecuted_body_positions=sorted(body-dynamic),
        source_structure=dict(procedures=len(src['procedures']),structured_ifs=src['structured_ifs'],natural_loops=src['natural_loops']),
        CPU_counts=dict(body_matrix=v['rom_cpu_case_count'],body_complete=v['complete_return_count'],body_prefix=v['strict_prefix_count'],source_guards=v['source_guard_case_count'],
            actual_NMI_callee_frames=w['rom_cpu_case_count'],total_comparisons=v['rom_cpu_case_count']+w['rom_cpu_case_count']),
        original_01EC_writers=actual_writers,remaining_service_catalog=dict(investigated_paths='Frozenphase14 two controlled241/481succession pipelines',
            unowned_real_callees=0,existing_owner_protocol_gap='14A003/15D8D4 legacysemantic audio excludesfree-stack; newexactownercloses this gap',
            sole_body_dependency=dict(call_pc=0xD8D6,target=0xF25F,already_recovered=True,role='NMI data window E1/E000=34'),
            deliberate_missing_helper_prefixes_are_real_missing_services=False,
            broader_scope='No claim about everycampaign/controllercallee outside investigatedclosures'),
        comparison=v['comparison'],guards=v['guards'],limits=v['limits']+w['limits'])
    (OUT/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
    (OUT/'README.md').write_text(f'''# 音频场景的真实调用与闲置栈边界

新增[AudioSceneServices](../../../source/recovered/audio_scene_services.py)恢复physical14 `A003 → 15D8D4`，原可达514条指令。生产是具名Python函数、if/while、真实localJSR/PHA/PLA/RTS和byte/flag计算，运行时不执行ROM/IR、也没有原CPUfallback。音乐token属于游戏数据；解析它不等于解释6502指令。固定D8D6→F25F是唯一外部软件调用，已有独立源码；原AudioServices和Presentation均保持冻结。

## 01EC 的真实 writer

原physical15 DF92/DF93连续 `48 48`（两个PHA），file offsets01FFA2/01FFA3。DF7E读取 `0706+X`，将bit4左移后并入控制值；当 `07F5>=16` 转入N163分支，两次压栈保存同一字节。随后DF9C/DFA8的PLA分别恢复它来写音量和波形控制，最后正常RTS。闲置RAM没有自动清除，这是正常栈残余。

冻结phase14的两种控制输入重新由原CPU从E066进入CA7F/CB79等待，再给显式NMI2软件到达。真实F8CB→A003 callee输入有20份：两种上下文×10次NMI，保留实际AXYP/SP/PC、银行和既有returnframe，没有另外植入caller。两条链的NMI2和NMI10都实测DF93：A=38hex、SP=EC、X=DC（slot220）、0706+X=18hex、07F5=18hex，真实写01EC=38hex/56。NMI2随后其它调用覆盖该残余，因此旧phase14整次NMI第一个可见差异在NMI10；不能把第一次writer等同于第一次完整NMI差异。

旧AudioServices声明free-stack excluded，旧值A6hex/166保留在该接口之外；这是已有owner的协议范围，不能称为未知callee。新exactowner记录这些真实栈操作。[writer回执](writer-provenance.json)保留原写PC/bytes/value及旧语义层差异，新源码20个actualcallee均完整2048B匹配。这些是受控原CPU/NMI上下文，**不是Nestopia内部trace**，也没有新增核心帧。

## 验证与未覆盖范围

独立body矩阵{v['rom_cpu_case_count']}比较：{v['complete_return_count']}完整callerRTS、{v['strict_prefix_count']}严格prefix，{v['source_guard_case_count']}个guards，0失败；另20个真实NMI audio frame完整返回。共{e['CPU_counts']['total_comparisons']}次CPU比较，sourceCPUcallbacks=0。全部2048B RAM（含inactive栈）、8192B SRAM、AXYP/SP/PC、orderedports/banks/reads和N163寄存器image均比较。

原183descriptor×4ticks、全部256callerSP、八channel的音符/音量/滑音/包络/循环/新header/pitch/tempo数据分支及duplicate-channel真实弹栈路径均有有界测试。另一个缺F25F prefix是测试故意不提供已有helper，之后同一caller以纯F25F恢复；B0无限音乐token循环只给原PC/flags/stack prefix，不假装音乐结束。缺registers、decimal、错误pair/entry、returnPC不匹配、无实际PC/SP的helper返回、无正预算的resume均严格拒绝或维持pending。

静态514位置，动态body矩阵覆盖{len(dynamic)}位置；余下{len(body-dynamic)}位置列于[evidence](evidence.json)。这些服务矩阵不宣称所有数据值、自然玩法或所有campaigncallee均覆盖。Scope调查确认两条既有继承链没有真正unowned callee；新服务补的是音频caller协议。它只发原APU/N163请求，不合成PCM、IRQ、帧时钟或ready/ack。完整主循环/NMI组合将在phase15新回执全2048B检查，phase14旧1976B报告原样保留。

```python
owner = AudioSceneServices(shared_memory, rom, services=exact_fixed_services)
owner.run_entry(0xA003, registers=actual_caller_registers)
owner(ServiceCall(...))  # exactphysical14/15 A003 orD8D4
owner.resume()          # same pendingcaller; requires realhelper completion
```

```sh
.venv-trace/bin/python scripts/analyze_audio_scene_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_audio_scene_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/trace_cooperation_audio_writer.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_audio_scene_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
```

[原汇编](original.asm) · [静态字节](static-catalog.json) · [body验证](validation.json) · [实际caller与writer](writer-provenance.json) · [证据与hash](evidence.json)
''')
    print(json.dumps(dict(status=e['status'],CPU=e['CPU_counts'],dynamic=len(dynamic),source_sha256=e['source_sha256'][paths[0]])))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--catalog-only',action='store_true');p.add_argument('--evidence-only',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==SHA;OUT.mkdir(parents=True,exist_ok=True)
    if a.evidence_only:evidence();return
    I,tables=collect(rom,pair=14,entries=(0xA003,0xD8D4));assert len(I)==514 and not tables
    catalog=dict(schema='phase15-exact-audio-scene-source-v1',rom_sha256=SHA,pair=[14,15],entries=[0xA003,0xD8D4],
        original_instruction_count=len(I),original_instructions=sorted(I.values(),key=lambda x:x['pc']),
        external_calls=[dict(call_pc=x['pc'],target=x['operand'],rom_offset=x['rom_offset'])for x in I.values()if x.get('hook')],
        writer_provenance=dict(bank=15,CPU_addresses=[0xDF92,0xDF93],ROM_offsets=[16+15*8192+0x1F92,16+15*8192+0x1F93],raw_hex='4848',
            role='Two genuine PHA copies of encoded volume/control byte; PLA consumes each copy for N163volume and wave fields; idle bytes remain after RTS.'))
    (OUT/'static-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    lines=['; Immutable original audio scene closure; file offsets include16-byte header.']
    for pc,x in sorted(I.items()):lines.append(f'b{x["physical_bank"]:02d}:{pc:04X} file{x["rom_offset"]:06X} {x["raw_hex"]:<7s} {x["op"]} '+(''if x['mode']=='imp'else'A'if x['mode']=='acc'else f'${x["operand"]:04X}'))
    (OUT/'original.asm').write_text('\n'.join(lines)+'\n')
    if a.catalog_only:return
    b=compiler(I,tables,dict(pair=14,entries=(0xA003,0xD8D4),names=NAMES,class_name='AudioSceneServices'))
    b.procedure=labelled_procedure.__get__(b,type(b));source=HEADER+'    def _entry(self,entry):\n'
    for i,pc in enumerate(sorted(b.roots)):source+=f'        {"if"if i==0 else"elif"} entry==0x{pc:04X}:return self.{b.names[pc]}()\n'
    source+='        raise ValueError("Outside named original audio body")\n\n'
    for pc in sorted(b.roots):
        body=b.procedure(pc);source+=re.sub(r'self\._mark\(([^\n;]+)\)',r'yield from self._checkpoint(\1)',body)
    source=source.replace('from dataclasses import dataclass',loop_exception_source(b.stats)+'from dataclasses import dataclass')
    ast.parse(source);SOURCE.write_text(source)
    (OUT/'source-catalog.json').write_text(json.dumps(dict(source_sha256=digest(source.encode()),procedures=b.stats,structured_ifs=b.if_count,natural_loops=b.loop_count,
        runtime_IR_interpretation=False,source_generation='Offline rawCFG structuring only; no production program/opcode dictionary'),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(source_bytes=len(source.encode()),procedures=len(b.roots),instructions=len(I),ifs=b.if_count,loops=b.loop_count)))
if __name__=='__main__':main()
