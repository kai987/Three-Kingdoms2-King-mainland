#!/usr/bin/env python3
"""Freeze original city/UI closure bytes and local-control comparison provenance."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert sha(a.rom)==SHA
 for area,module,generator,pair in [('city','city_ui_controller','analyze_city_ui_controller',27),('panels','city_panel_services','analyze_city_panel_services',25)]:
  out=ROOT/'analysis/phase13'/area;catalog=json.loads((out/'static-control.json').read_text());v=json.loads((out/'validation.json').read_text());assert v['status']=='passed'and not v['quick']
  occupied={}
  for row in catalog['original_instructions']+catalog['dispatch_tables']:
   bank=row['physical_bank'];start=row['rom_offset'];raw=bytes.fromhex(row['raw_hex']);assert rom[start:start+len(raw)]==raw
   pc=row.get('pc',row.get('cpu_address'));assert start==16+bank*8192+(pc&8191)
   occupied.setdefault(bank,set()).update(range(start,start+len(raw)))
  ranges=[]
  for bank,offsets in sorted(occupied.items()):
   ordered=sorted(offsets);lo=last=ordered[0]
   blocks=[]
   for x in ordered[1:]:
    if x!=last+1:blocks.append((lo,last+1));lo=x
    last=x
   blocks.append((lo,last+1))
   for lo,hi in blocks:
    pc=(0xA000 if bank==pair else 0xC000)+(lo-16-bank*8192);raw=rom[lo:hi]
    ranges.append(dict(physical_bank=bank,cpu_start=pc,cpu_end_exclusive=pc+len(raw),rom_offset=lo,byte_count=len(raw),raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
  local={(r['physical_bank'],r['pc'])for r in catalog['original_instructions']};visited={(r['physical_bank'],r['cpu_address'])for r in json.loads((out/'executed-instructions.json').read_text())}
  source=f'source/recovered/{module}.py';gen=f'scripts/{generator}.py';dependencies=[gen,'scripts/analyze_city_ui_controller.py','scripts/analyze_battle_scene_controller.py','scripts/inspect_game_data.py','scripts/verify_city_ui_source.py','source/recovered/battle_nmi_services.py']
  if area=='panels':dependencies.append('scripts/ui_structuring.py')
  e=dict(status='passed',rom_sha256=SHA,source_path=source,source_sha256=sha(ROOT/source),analyzer_path=gen,analyzer_sha256=sha(ROOT/gen),source_and_validator_sha256={x:sha(ROOT/x)for x in sorted(set(dependencies))},ranges=ranges,dispatch_tables=catalog['dispatch_tables'],original_instruction_count=len(local),executed_local_instruction_positions=len(local&visited),unexecuted_local_instruction_positions=len(local-visited),validation_path=f'analysis/phase13/{area}/validation.json',validation_sha256=sha(out/'validation.json'),static_control_path=f'analysis/phase13/{area}/static-control.json',static_control_sha256=sha(out/'static-control.json'),source_catalog_path=f'analysis/phase13/{area}/source-catalog.json',source_catalog_sha256=sha(out/'source-catalog.json'),REA_archive=f'analysis/rea/pairs/pair-{pair}',source_original_CPU_callbacks=0,source_IR_interpretation=False,comparison_scope='Local readable control against original CPU; external helper CPU exists only inside the validator. Pure owner integration has a separate receipt.',limitations=['Unexecuted local instruction positions are not path coverage claims.','Nearest-forward-arm inline-table extents are explicit analysis candidates, retained with exact raw words and validated on bounded legal inputs.','Invalid or nonterminating prepared panel fixtures are excluded, never successful cases.'])
  (out/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
  asm=['; Exact original opcode closure and inline dispatch data; offset includes16B iNES header.']
  for row in catalog['original_instructions']:
   asm.append(f"; bank{row['physical_bank']:02d} CPU${row['pc']:04X} ROM+{row['rom_offset']:06X}\n.byte "+','.join(f'${b:02X}'for b in bytes.fromhex(row['raw_hex']))+f" ; {row['op']} {row.get('operand','')}")
  for row in catalog['dispatch_tables']:asm.append(f"; EADE table at bank{row['physical_bank']} ${row['cpu_address']:04X}\n.word "+','.join(f'${x:04X}'for x in row['targets']))
  (out/'original-range.asm').write_text('\n'.join(asm)+'\n')
  title='城市菜单与NMI2控制器'if area=='city'else'城市、君主资料与菜单动作服务'
  text=f'# {title}\n\n源码：[{module}.py](../../../{source})。原bank{pair}/{pair+1}共{len(local)}个指令位置，直接结构化函数与分支，不在运行时解释控制IR或执行6502。静态closure原字节、表、带16B头的ROM偏移及REA旧archive均保留。\n\n原CPU对照：{v["rom_cpu_case_count"]}例，其中{v["complete_return_count"]}完整返回、{v["strict_prefix_count"]}严格前缀，{v["source_guard_case_count"]}个非返回callback guard。比较全2048RAM（包括stack）、8192SRAM、AXYP/SP/PC、有序端口读写和bank。{v["unusable_input_fixtures_excluded"]}个无效/不终止的准备输入明确排除。执行到的本地指令位置为{len(local&visited)}/{len(local)}；不将静态收录或helper CPU执行算成本地路径覆盖。\n\n此矩阵仅证实本地控制正文，外部helper原CPU只存在于validator；[统一GameEngine纯源码整合](../source-integration.json)另计，没有原CPU callback。调用必须提供寄存器和已有caller帧；显式测试seed_return不属于生产coordinator路径，未返回状态或PC/SP不符不能继续。\n\n'
  if area=='city':text+='主状态16项；主要子表：内政23、军事25、物资16、街市24、状态6的18项。原画面已确认main4物资输送／给予，main5街市／武器店。AD41调动名单保留目标追加、君主置首、源城删除与压紧；C81F保留四件装备的原PPU请求，不假定队列已被NMI完成。\n'
  else:text+='A02A→BBDE年历标题；A021→AFE5由独立武将资料控制器拥有，A012→B2D7由phase12资料服务拥有，避免混淆。B7D9包含出征初始化与持久数据变更；B859名单删除与B879压紧、A1EB归城查找、A209君主记录非零nibble递减及A240非君主可用武将计数均保留实际算术。E000重启与异步硬件等待保留显式边界。\n'
  text+='\n复现：`.venv-trace/bin/python scripts/'+generator+'.py ROM`，然后`verify_city_ui_source.py ROM --area '+area+'`，最后`build_phase13_city_evidence.py ROM`。再生成前须注意旧receipt失效，不能只改hash声明通过。\n'
  (out/'README.md').write_text(text)
  print(area,len(local),len(local&visited),len(ranges),v['rom_cpu_case_count'])
if __name__=='__main__':main()
