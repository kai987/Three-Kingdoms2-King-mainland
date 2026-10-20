#!/usr/bin/env python3
"""Read-only original-byte provenance for new city auxiliary source.

This analyzer records the B49C/BD7A control bodies and their genuine calls into
frozen readable source. It never emits or executes production opcodes or IR.
"""
from pathlib import Path
from collections import Counter
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_domestic_cooperation_controller import collect
from inspect_game_data import instruction
from source.recovered.city_auxiliary_services import CityAuxiliaryServices,ROM_SHA256
OUT=ROOT/'analysis/phase18/services'
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def dump(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
 I,tables=collect(rom)
 parent_tree=ast.parse((ROOT/'source/recovered/domestic_cooperation_controller.py').read_text())
 cls=next(x for x in parent_tree.body if isinstance(x,ast.ClassDef)and x.name=='DomesticCooperationController')
 entry=next(x for x in cls.body if isinstance(x,ast.FunctionDef)and x.name=='_entry')
 stop={x.value for x in ast.walk(entry)if isinstance(x,ast.Constant)and isinstance(x.value,int)}-{0xB49C,0xBD7A}
 queue=[0xB49C,0xBD7A];body={};deps=[]
 while queue:
  pc=queue.pop()
  if pc in body:continue
  x=I[pc];body[pc]=x;op=x['op']
  if op in('RTS','RTI','BRK'):continue
  if op=='FARCALL':
   deps.append(dict(call_pc=pc,target=x['operand'],inline_target=x['inline_target'],kind='far_call',physical_bank=x['bank'],rom_offset=x['file'],raw_hex=x['raw_hex'],owner='frozen_readable_far_service'))
   queue.append(x['next_pc']);continue
  if op in('JSR','JMP'):
   target=x['operand'];is_dep=x.get('hook')or target in stop
   if is_dep:deps.append(dict(call_pc=pc,target=target,kind='tail'if op=='JMP'else'call',physical_bank=x['bank'],rom_offset=x['file'],raw_hex=x['raw_hex'],owner='frozen_readable_fixed_service'if target>=0xE000 else'frozen_readable_domestic_procedure'))
   else:queue.append(target)
   if op=='JSR':queue.append(x['next_pc'])
  elif op in('BCC','BCS','BEQ','BNE','BMI','BPL','BVC','BVS'):queue.extend((x['operand'],x['next_pc']))
  else:queue.append(x['next_pc'])
 new_set=set(body);raw=bytes.fromhex(''.join(x['raw_hex']for pc,x in sorted(body.items())))
 catalog=dict(schema='phase18-city-auxiliary-original-byte-catalog-v1',rom_sha256=ROM_SHA256,physical_pair=[10,11],public_entries=list(CityAuxiliaryServices.PUBLIC_ENTRIES),new_body_instruction_count=len(body),new_body_byte_count=len(raw),sorted_instruction_bytes_sha256=digest(raw),instructions=sorted(body.values(),key=lambda x:x['pc']),real_dependencies=deps,reused_entry_frontdoor=[0xA000,0xA00F],reused_helpers_excluded_from_new_body_count=sorted({x['target']for x in deps if x['target']<0xE000}),original_ranges=[])
 for bank,start,end,name in((10,0xB49C,0xB53E,'assignment sampling and two roster passes'),(10,0xBD7A,0xBEC7,'allcity selection, shortage purchase, reserve and rawtroop write, budget tail')):
  f=16+bank*8192+(start&8191);data=rom[f:f+end-start]
  catalog['original_ranges'].append(dict(physical_bank=bank,cpu_start=start,cpu_end_exclusive=end,rom_offset=f,byte_count=len(data),raw_hex=data.hex(),sha256=digest(data),name=name))
 dump(OUT/'static-catalog.json',catalog)
 listing=[]
 for pc,x in sorted(body.items()):
  f=x['file'];_,asm=instruction(rom,f,pc);listing.append(f'{f:06X} b{x["bank"]:02d}:${pc:04X} {x["raw_hex"]:<14} {asm}')
 (OUT/'original.asm').write_text('\n'.join(listing)+'\n')
 receipt=json.loads((OUT/'validation.json').read_text());vis={(x['physical_bank'],x['cpu_address'])for x in receipt['executed_instruction_positions']}
 dynamic=sum((x['bank'],pc)in vis for pc,x in body.items())
 source_files=('source/recovered/city_auxiliary_services.py','source/recovered/domestic_cooperation_controller.py','source/recovered/global_ui_controller.py','source/recovered/scene_shared_services.py','source/recovered/battle_nmi_services.py','source/recovered/controller_helpers.py','source/recovered/service_memory.py','source/recovered/mapped_memory.py','scripts/analyze_city_auxiliary_services.py','scripts/verify_city_auxiliary_services.py','scripts/trace_city_auxiliary_fields.py')
 evidence=dict(schema='phase18-city-auxiliary-readable-evidence-v1',rom_sha256=ROM_SHA256,source_file=source_files[0],source_sha256={p:sha(ROOT/p)for p in source_files},production_IR_interpretation=False,production_original_CPU_callbacks=0,byte_catalog=dict(path=str((OUT/'static-catalog.json').relative_to(ROOT)),sha256=sha(OUT/'static-catalog.json')),validation=dict(path=str((OUT/'validation.json').relative_to(ROOT)),sha256=sha(OUT/'validation.json'),status=receipt['status'],rom_cpu_case_count=receipt['rom_cpu_case_count'],complete_return_count=receipt['complete_return_count'],strict_prefix_count=receipt['strict_prefix_count'],source_guard_case_count=receipt['source_guard_case_count']),coverage=dict(static_new_body_instruction_positions=len(body),dynamically_executed_new_body_positions=dynamic,not_dynamic=len(body)-dynamic,static_byte_pin_is_not_dynamic_path_validation=True),distinctions=dict(aux_byte1='Opaque; exact LE16(city+1,city+2) original gate, not inferred official field name.',pointer='10BD8D calls11D105;20/21 becomes6000+32*city. D105 caps true gold/grain first; no pointer+1 bias.',threshold='Unsigned overlapping word>=300; sufficient reserve recruitment itself deducts no gold. Shortage fee is wrapping byte20 per100-block loop; not300.',selection='All30cities, owner&7==ruler; all10roster bytes, skipFFholes; head score100, others officer武力; equality selects later entry/city.',troops='Eligibility/need use low10. Only low10==1000 is skipped; raw low10>1000 underflows need. Commit writes full16-bit03E8, clearing former upper6.',purchase='need>=reserve including exact equality enters purchase; first100 block bought even deficit0. Purchase loop stops on subtraction borrow, so exact multiples buy one extra block. Cost wraps8bit. D36F failure ignored by this caller.',budget='Original charge2 occurs after reserve/rawtroop write. Zero or borrow discards its own JSR frame then returns through real parentcaller; no extra frame invented forBD7A/BEC7 tail.',waiting='Missing fixed calls retain real callee frame, source refuses absent or non-returned service. SecondaryF8 busy branch retains original loop under explicit block budget; it is not automatically acknowledged.',source_scope='New hand-written B49C sampling/two passes and BD7A selection/purchase/commit. Secondary B5FC branch copied as fixed direct Python from frozen parent; helpers and BEC7 development are reused existing source.'),natural_memory_context=dict(prefix=str(PARENT.relative_to(ROOT))if(PARENT:=ROOT/'analysis/phase15/runtime/cold-yearwrap/AI-ruler1-status00-frame34623')else'',calendar=[89,6],display_date='189year7month',natural_city4_reserve=9499,target_head=167,prepared_common='realgold257 and officer167troops900',aux_cohort=[0,44],original_CPU_prefix_context='E066 declared AXYP/SP, actual original main2 dispatch creates B49C caller',Native_internal_CPU_trace=False),artifact_sha256={str(p.relative_to(ROOT)):sha(p)for p in[OUT/'static-catalog.json',OUT/'original.asm']})
 dump(OUT/'evidence.json',evidence)
 (OUT/'README.md').write_text(f'''# 城市辅助字节与 AI 补兵源码

新模块 [CityAuxiliaryServices](../../../source/recovered/city_auxiliary_services.py) 直接实现 physical10 `B49C` 的随机入口、两轮名册分配编排，以及 `BD7A..BEC6` 的全部城市选择、补兵、资源购买与预算退出。生产源码不解释 IR、不执行原 ROM，也不使用 CPU fallback。固定 RNG、城市指针、邻城/名册移动、资源支付和 `BEC7` 后续发展复用历史冻结的独立源码；`B5FC` 次级分支是从冻结源码提取的静态 Python 函数，运行时没有读取或编译该文件。

## 实际读法与作用

`10:BD8D` 真实调用 `11:D105`，令 `$20/$21 = $6000+32*城市ID`；这里没有偏移一字节的城市基址。D105 会先限制真正 gold/grain 到9999。`BD97` 读 city+1，`BD9D` 读 city+2，再以连续 SBC 判断二者组成的无符号 little-endian word 是否至少300。city+2 本身是真正金币的低字节。因此 `+1` 保留 opaque/raw 名称；本证据不足以命名为官职、专用收入或其他正式游戏字段，也没有“支付300金币”的行为。

通过门槛后，扫描全部30城中 owner低3位等于当前君主的城市，以及每城全部十个名册槽17..26。`FF` 只跳过当前槽，不结束扫描。低十位兵数正好1000才跳过；首槽候选固定评分100，其余读武力byte1。原 CMP/BCS 在平分时替换，所以靠后的武将或城市胜出。它不额外检查 HP、status、驻城byte5；这里只声明机器条件。

选中后，缺额为 `(1000−troops_low10)&65535`。库存大于缺额时直接扣库存，补兵本身不扣金币；库存等于或少于缺额会进入购买。每次加100库存块、将8bit费用加20，然后减100缺口，直到借位。缺口0也会购买一块；缺口恰好100的整数倍会多买一块。费用保留8bit回绕，`D36F` 支付失败的 carry 被调用者忽略，仍继续增加库存并写兵。最终将武将完整兵word写成 `03E8`，会清除原来的高六位。库存加减保留16bit运算，不擅自改成9999上限。

最后才扣 AI 预算2。预算减至0或借位时，原 `D152` 丢弃自己那层返回地址并从上一层真实 caller 返回；源码保持这个栈协议。预算足够时重新从全城选择开始，再无候选则直接 tail 到原发展流程。

## 验证与边界

当前回执 {receipt['rom_cpu_case_count']} 次原CPU对照：{receipt['complete_return_count']} 个完整实际 caller RTS、{receipt['strict_prefix_count']} 个缺少 E8AA 服务的真实前缀；另有 {receipt['source_guard_case_count']} 个源码 guard。比较全部2048B RAM（含闲置栈残余）、全部8192B SRAM、AXYP/SP/PC、有序端口读写、全部PRG银行与N163 register image。生产与 source侧 CPUcallbacks 都为0。准备的数值/名册边界单列，包括空名册/首FF/中间空洞、平分/跨城/重复ID alias、兵高六位/低十位1001..1023、库存等于缺额、不足支付、预算0/1/2/3/255、栈wrap。raw边界不当作合法自然玩法。

{len(body)} 个新控制body位置已静态锁定原字节，其中 {dynamic} 个被本矩阵实际执行，{len(body)-dynamic} 个未动态覆盖。原始字节全集并不证明全部运行路径都测试过。B5FC外交/请求分支的 `F8` 等待保留原 busy loop 和明确源码预算，未把未知请求当已完成；本矩阵完整返回只覆盖回执列出的输入。

两个高价值 B49C 输入从冻结原核心 frame34623 的 RAM/SRAM 开始，在明确的 E066 AXYP/SP 上用原CPU执行真正 main2 前序，捕获实际存在的 caller 栈；它们不是 Nestopia 内部 PC/寄存器 trace。共同只准备城4真金币257、首将167兵900，保留自然库存9499，城市+1对比0/44。正式原核心双跑由 runtime 域单列，不能把本地 CPU 返回数量当 Native 帧。

API:

```python
rules = CityAuxiliaryServices(memory, rom, services=readable_services)
rules.run_entry(0xB49C, registers=actual_caller_registers)
rules.run_entry(0xBD7A, registers=actual_caller_registers)
rules(service_call)  # 精确physical10/11与PUBLIC入口，同一pending owner需resume
```

PUBLIC 是 A000、A00F、B49C、BD7A。A000/A00F 真实调用将虚调用转到本轮 B49C；旧 GameEngine/coordinator 文件保持冻结，新加组合入口由 Root 单列。源码不会构造 sentinel caller 或自动确认其他 UI/硬件请求。

```sh
.venv-trace/bin/python scripts/verify_city_auxiliary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_auxiliary_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[原字节汇编](original.asm) · [静态目录](static-catalog.json) · [验证](validation.json) · [证据与hash](evidence.json) · [实际原CPU caller](actual-caller-inputs/aux44.json) · [有限访问追踪](../cpu/README.md)
''')
 print(json.dumps(dict(status='written',source_sha256=evidence['source_sha256'][source_files[0]],static=len(body),dynamic=dynamic,CPU=receipt['rom_cpu_case_count'],guards=receipt['source_guard_case_count'])))
if __name__=='__main__':main()
