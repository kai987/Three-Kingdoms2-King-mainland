#!/usr/bin/env python3
"""Export reached caller inputs from explicit original-CPU continuations.

The release path can require one separately declared hardware NMI and A-port
input. Such inputs are labelled as CPU hardware fixtures, never as a passive
Native internal register trace. Pure continuations retain their saved PC.
"""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.nestopia_context import NestopiaContext,CapturedServiceMemory
ROM_SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase22/cpu'
REGS=('a','x','y','p','sp','pc')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def registers(c):return{k:getattr(c,k)for k in REGS}
def raw(m,a):return CapturedServiceMemory.__getitem__(m,a)
class TransitionMemory(CapturedServiceMemory):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.active=False;self.context=None;self.transitions=[]
 def __setitem__(self,address,value):
  before=raw(self,address)if self.active and isinstance(address,int)and 0x63C0<=address<0x6EDC else None
  super().__setitem__(address,value)
  if before is None:return
  officer,field=divmod(address-0x63C0,12)
  if field==11 and(before&3)!=(value&3):self.transitions.append(dict(**self.context,officer=officer,address=address,before=before,after=value&255,old_low2=before&3,new_low2=value&3))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--release-state',type=Path);p.add_argument('--recruit-state',action='append',type=Path,default=[]);p.add_argument('--output',type=Path,default=OUT);p.add_argument('--instruction-budget',type=int,default=300000);a=p.parse_args()
 rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA
 jobs=([(a.release_state,'release')]if a.release_state else[])+[(p,'recruit')for p in a.recruit_state]
 assert jobs,'Supply a formal Native state; no synthetic default PC is installed'
 out=a.output.resolve()
 if out==OUT and any(any(part.startswith('exploratory')for part in path.parts)for path,_ in jobs):raise ValueError('Exploratory mothers require an exploratory --output; formal inputs must not pin exploratory paths')
 out.mkdir(parents=True,exist_ok=True);rows=[];artifacts={}
 for path,kind in jobs:
  path=path.resolve();n=NestopiaContext.parse(path.read_bytes());buttons=(1,0)if kind=='release'else(0,0)
  hardware=dict(read_ports={0x2002:0,0x4015:0,0x5800:127},repeat_read_ports=(0x2002,0x4015,0x5800),controller_buttons=buttons)
  m=TransitionMemory(rom,n.ram,n.sram,n.prg_banks,**hardware);m.n163_ram[:]=n.n163_ram;m.n163_address=n.n163_address;m.n163_autoincrement=n.n163_autoincrement
  c=MPU(memory=m)
  for k,v in n.registers.items():setattr(c,k,v)
  events=[dict(kind='controller_ports',buttons=list(buttons),range='entire independent CPU continuation',write_to_RAM_buttons=False)]
  if kind=='release':
   events.insert(0,dict(kind='NMI',at_saved_PC=c.pc,before_any_original_instruction=True,entry='MPU.nmi actual6502 hardware stack/vector protocol'))
   c.nmi()
  origin='Native_snapshot_plus_declared_hardware_NMI_CPU_fixture'if kind=='release'else'actual_Native_snapshot_originalCPU_reached_caller'
  captured=[];stop=None;driver=None;first_request=m[0x6F8B];pending_C6CC=None
  for step in range(a.instruction_budget):
   if c.pc<0x8000:stop='non_ROM_PC_boundary';break
   pair=tuple(m.banks[1:3]);entries=(0xA000,0xD1F9,0xD20D)if pair==(12,13)else(0xA000,0xC5B9,0xC6CC,0xC71A,0xC765)if pair==(10,11)else()
   if c.pc in entries:
    key=f'entry-{c.pc:04X}'+(f'-pair{pair[0]}'if c.pc==0xA000 else'');folder=out/'actual-callers'/key
    return_pc=((m[0x100+((c.sp+1)&255)]|m[0x100+((c.sp+2)&255)]<<8)+1)&65535
    x=dict(schema='phase22-wild-recruitment-caller-input-v1',origin=origin,original_Native_state=str(path.relative_to(ROOT)),original_Native_state_sha256=sha(path),native_captured_registers=n.registers,
      original_CPU_prefix_instructions=step,registers=registers(c),physical_banks=list(m.banks),N163_address=m.n163_address,N163_autoincrement=m.n163_autoincrement,
      existing_return_PC=return_pc,synthetic_caller_or_PC_or_RNG_or_request_preparation=False,injected_new_NMI=1 if kind=='release'else 0,hardware_events=events,
      Native_internal_CPU_trace=False,prepared_numeric_bytes=[])
    if not folder.exists():
     folder.mkdir(parents=True);(folder/'input-ram.bin').write_bytes(m.ram);(folder/'input-sram.bin').write_bytes(m.sram);(folder/'input-n163.bin').write_bytes(m.n163_ram)
     (folder/'context.json').write_text(json.dumps(x,indent=2)+'\n')
    if key not in captured:captured.append(key)
    if kind=='recruit'and c.pc==0xC6CC:pending_C6CC=(bytes(m.ram),bytes(m.sram),bytes(m.n163_ram),x)
    if kind=='release'and c.pc==0xD1F9 and driver is None:driver=(return_pc,(c.sp+2)&255)
   if driver is not None and(c.pc,c.sp)==driver:stop='actual_D1F9_caller_RTS';break
   if c.pc==0xFB28:stop='actual_hardware_IRQ_wait';break
   if kind=='recruit'and first_request!=255 and m[0x6F8B]==255:stop='original_request_FF';break
   m.context=dict(step=step,physical_bank=m.banks[(c.pc-0x8000)//8192],pc=c.pc,registers=registers(c),pointer00=m[0]|m[1]<<8,pointer22=m[0x22]|m[0x23]<<8)
   previous_transitions=len(m.transitions);m.active=True
   try:c.step()
   finally:m.active=False
   if pending_C6CC and any(t['old_low2']==0 and t['new_low2']==2 for t in m.transitions[previous_transitions:]):
    # Select an already captured real entry by a subsequently observed
    # outcome; never reconstruct the entry from the successful final state.
    ram,sram,n163,context=pending_C6CC;key='entry-C6CC-success';folder=out/'actual-callers'/key
    if not folder.exists():
     folder.mkdir(parents=True);(folder/'input-ram.bin').write_bytes(ram);(folder/'input-sram.bin').write_bytes(sram);(folder/'input-n163.bin').write_bytes(n163)
     (folder/'context.json').write_text(json.dumps({**context,'subsequently_observed_success_transition':m.transitions[-1]},indent=2)+'\n')
    if key not in captured:captured.append(key)
    pending_C6CC=None
  else:stop='explicit_instruction_budget'
  rows.append(dict(native_state=str(path.relative_to(ROOT)),native_sha256=sha(path),origin=origin,saved_registers=n.registers,actual_banks=list(n.prg_banks),hardware_events=events,
   original_instructions=step,stop=stop,final_registers=registers(c),captured=captured,status_transitions=m.transitions,source_CPU_cases=0,Native_internal_CPU_trace=False))
  artifacts[str(path.relative_to(ROOT))]=sha(path)
 for p in(out/'actual-callers').rglob('*'):
  if p.is_file():artifacts[str(p.relative_to(ROOT))]=sha(p)
 result=dict(schema='phase22-originalCPU-wild-recruitment-input-trace-v1',status='bounded_original_CPU_observation',ROM_sha256=ROM_SHA,rows=rows,source_CPU_cases=0,Native_internal_CPU_trace=False,
  source_sha256={str(p.relative_to(ROOT)):sha(p)for p in(Path(__file__),ROOT/'source/recovered/nestopia_context.py',ROOT/'source/recovered/service_memory.py')},artifact_sha256=artifacts,
  limits=['No saved PC/register/stack/RNG/request/ready or gameplay data is rewritten.','A release origin explicitly injects one real hardware NMI and ordinary A-port input into the independent CPU; it is not a passive Native callee capture.','Pure saved-PC continuations do not schedule new interrupts; their outcome need not equal later Native frame timing.','Diagnostic preparation instructions and exported callees are not extra Source comparison cases.'])
 (out/'trace.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 if out==OUT:
  native=ROOT/'analysis/phase22/runtime/evidence.json'
  evidence=dict(schema='phase22-wild-recruitment-originalCPU-provenance-v1',status='bounded_original_CPU_observation',ROM_sha256=ROM_SHA,contexts=len(rows),
   original_CPU_prefix_instructions=sum(x['original_instructions']for x in rows),source_CPU_cases=0,Native_internal_CPU_trace=False,
   pure_saved_PC_context_count=sum(x['origin']=='actual_Native_snapshot_originalCPU_reached_caller'for x in rows),declared_hardware_NMI_context_count=sum(x['origin']=='Native_snapshot_plus_declared_hardware_NMI_CPU_fixture'for x in rows),
   exported_caller_inputs=len(list((out/'actual-callers').glob('entry-*/context.json'))),trace=dict(path=str((out/'trace.json').relative_to(ROOT)),sha256=sha(out/'trace.json')),
   source_sha256=result['source_sha256'],artifact_sha256=artifacts,formal_Native_evidence=dict(path=str(native.relative_to(ROOT)),sha256=sha(native)),limits=result['limits'])
  (out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
  (out/'README.md').write_text(f'''# 真保存点前序与严格区分的硬件事件夹具

本域不是原Nestopia内部逐指令记录。独立原CPU从正式原核心保存PC/SP/AXYP、实际MAP四银行与N163 image继续，不改原存档、caller、PC、RNG、request或ready；诊断与callee准备指令不加入Source比较case数。

两个上下文共{evidence['original_CPU_prefix_instructions']}条原指令。释放保存点`release-confirmation.state`实际PC E224/SPFF，按钮81=0，尚未进入下一次NMI。该输入**明确**在CPU模型安排一次真实6502 NMI压栈/向量协议及A手柄端口，标为`Native_snapshot_plus_declared_hardware_NMI_CPU_fixture`、`injected_new_NMI=1`。没有直接写按钮RAM或调用D1F9。原NMI3前序1215指令到A000、1722到D1F9、1728到D20D；2095指令停实际D1F9 caller RTS，原5/30两条记录2→0。它与Native本来的普通A帧是不同层次的证据，不能称实际Native内部callee寄存器。

录用输入`recruitment-success-previous-1-frame14836.state`实际PC D6A1/SPF7，52/54均10。它是**不新增任何中断**的pure保存PC前序：1288指令到C5B9、1343到首次C6CC(city0早退)、1750到成功C6CC(city2)、2013到C71A、2134到C765，2138时C76D真实将5号status24→26。最后24288条原指令到原requestFF。`entry-C6CC-success`是进入该函数时已经保存的真实RAM/SRAM/寄存器，之后根据实际观察0→2挑出，不是从结果反造输入。

8个callee输入分为5个pure录用输入与3个明示NMI释放输入。C5B9正常父返回；C6CC-success/C71A/C765成功会按原双PLA越过一层，保持真实非局部返回。C794时X可以被后续忠诚helper改成0，不能把这里的X误说成仍为录用ID5。Source矩阵与统一GameEngine组合另行记录，不能把本域的准备步骤重复计为额外Source例。

所有硬件读输入均明示：PPUSTATUS=0、APUstatus=0、NamcoIRQ读127；释放端口A，pure录用端口无键。本域没有模拟新视频帧/IRQ到达。Native的完整0→2、RGB/PCM/全state与passive observer证据由`../runtime`单列。

```sh
.venv-trace/bin/python scripts/trace_wild_recruitment.py '/Users/paulasmith/Downloads/三国志2超级版.nes' \\
  --release-state analysis/phase22/runtime/original-control/release-confirmation.state \\
  --recruit-state analysis/phase22/runtime/original-control/recruitment-success-previous-1-frame14836.state
```

[严格origin与hash](evidence.json) · [前序轨迹](trace.json) · [源码对照](../release/validation.json) · [原机记录](../runtime/README.md)
''')
 print(json.dumps(dict(contexts=len(rows),rows=[dict(origin=x['origin'],instructions=x['original_instructions'],stop=x['stop'],captured=x['captured'],status_transitions=len(x['status_transitions']))for x in rows])))
if __name__=='__main__':main()
