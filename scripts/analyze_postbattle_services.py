#!/usr/bin/env python3
"""Pin original postbattle header/loyalty bytes and existing source-body owners."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_city_ui_controller import collect
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--area',choices=('graphics','loyalty'),required=True);a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==SHA
 area=a.area;out=ROOT/'analysis/phase16'/area;v=json.loads((out/'validation.json').read_text());assert v['status']=='passed'and not v['quick']and not v['failed_count']
 module='postbattle_graphics'if area=='graphics'else'postbattle_loyalty_bridge';source='source/recovered/'+module+'.py';pair=29 if area=='graphics'else 10;entry=0xA01E if area=='graphics'else 0xA009
 I,tables=collect(rom,pair=pair,entries=(entry,));assert not tables
 paths=[*v['source_sha256'],'scripts/analyze_postbattle_services.py'];pins={f:digest((ROOT/f).read_bytes())for f in paths}
 assert all(pins[f]==h for f,h in v['source_sha256'].items())
 tree=ast.parse((ROOT/source).read_text());assert not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id in('exec','eval','compile')for n in ast.walk(tree))
 observed=json.loads((out/'executed-instructions.json').read_text());seen={(x['physical_bank'],x['cpu_address'])for x in observed};local={(x['physical_bank'],x['pc'])for x in I.values()}
 data=[]
 if area=='loyalty':
  base=16+11*8192+(0xCAD8&8191);raw=rom[base:base+14];data.append(dict(label='seven_family_list_pointers',physical_bank=11,CPU_address=0xCAD8,ROM_offset=base,raw_hex=raw.hex(),bytes=14,sha256=digest(raw)))
  for ruler in range(7):
   addr=int.from_bytes(raw[2*ruler:2*ruler+2],'little');offset=16+11*8192+(addr&8191);end=rom.index(255,offset)+1;sequence=rom[offset:end]
   data.append(dict(label='family_exemption_list_'+str(ruler),physical_bank=11,CPU_address=addr,ROM_offset=offset,raw_hex=sequence.hex(),bytes=len(sequence),sha256=digest(sequence)))
 catalog=dict(rom_sha256=SHA,original_instructions=list(I.values()),tables=data,local_instruction_count=len(I),local_instruction_bytes=sum(len(bytes.fromhex(x['raw_hex']))for x in I.values()))
 (out/'static-catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
 (out/'source-catalog.json').write_text(json.dumps(dict(source=source,public_entries=[entry,0xA6B6 if area=='graphics'else 0xCF7C],source_sha256=pins[source],procedures=[n.name for n in tree.body if isinstance(n,ast.ClassDef)for n in n.body if isinstance(n,ast.FunctionDef)],runtime_original_CPU=False,runtime_IR=False),indent=2)+'\n')
 lines=['; Original ROM byte locations include the16byte iNES header. No runtime source executes this listing.']
 for pc,x in sorted(I.items()):lines.append(f'b{x["physical_bank"]:02d}:{pc:04X} file{x["rom_offset"]:06X} {x["raw_hex"]:<8} {x["op"]} {x["mode"]} ${x["operand"]:04X}')
 (out/'original.asm').write_text('\n'.join(lines)+'\n')
 evidence=dict(schema='phase16-'+area+'-source-evidence-v1',status='passed',rom_sha256=SHA,source_original_CPU_callbacks=0,source_IR_interpretation=False,source_path=source,source_sha256=pins,artifact_sha256={f: digest((ROOT/f).read_bytes())for f in v['artifact_sha256']},body=catalog,local_dynamic_instruction_count=len(seen&local),unexecuted_local_positions=[dict(physical_bank=b,CPU_address=pc,ROM_offset=16+b*8192+(pc&8191))for b,pc in sorted(local-seen)],validation_path=str((out/'validation.json').relative_to(ROOT)),validation_sha256=digest((out/'validation.json').read_bytes()),REA_archive_pins={str(p.relative_to(ROOT)):digest(p.read_bytes())for p in(ROOT/f'analysis/rea/pairs/pair-{pair:02d}').glob('*')if p.name in('image.bin','mapping.json','catalog.json','evidence-bundle.json')},limits=v['limits'])
 (out/'evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
 if area=='graphics':
  text=f'''# 战后真正缺失的年月图形请求

新增[PostbattleGraphics](../../../{source})恢复physical29 `A01E→A6B6`，93条原指令、两次真实`E9BA`十进制转换调用。实际使用者是25`AD95/AE51`的远端`Y=3D,A01E`。它只构造`0380..0394`中的两条七字形请求，目标nametable2043/2063，写`7E|4`；不初始化世界、不完成PPU上传、不推进city13或写ack。真实消费者保持独立。

年值加100保留进位成word，年89/90显示189/190；原0-based月加1，月1..9的十位使用原空白字形。原月255字节加1回0后，高字节仍显式清0，保留这一边界；不是合法月份。Python抽出的字形写方法不制造额外JSR，只有A6CB/A714的真实帧。

{v['rom_cpu_case_count']:,}项实际callerRTS对照、{v['source_guard_case_count']}guard、0失败。全部256年×12月份、5年×244额外raw月份以及256个SP均核完整2048RAM含闲置栈、8192SRAM、AXYP/SP/PC、顺序端口读写、银行和N163图。局部动态{len(seen&local)}/{len(local)}位置。原CPU只在独立py65对照侧运行，生产没有CPU/IR解释或模拟vblank。raw月12..255只是明确边界输入。
'''
 else:
  text=f'''# 战后调用的忠诚入口

新增[PostbattleLoyaltyBridge](../../../{source})准确暴露physical10/11 `A009→CF7C`。A009原bytes`4C7CCF`仅JMP，不改flags或caller栈。CF7C和它的本地寻址/除法/RTS函数已在冻结[DomesticCooperationController](../../../source/recovered/domestic_cooperation_controller.py)独立恢复；本轮复用这些可读函数，**不重新进入A000/A00F内政主循环，也不调用CA19继承**。这是原25C2EA/C05B的真实远端忠诚依赖。

原七组家族排除表、徳/5差值、原ADC/SBC byte溢出、扣10及10..99截顶、同址记录均保留。scratch30/31/32/33的原输入含义以实际调用场合解释，不强把所有场合固定成旧/新君主。名册离开、状态/地点写回由后续战后消费者承担，本入口只执行真实忠诚body。

{v['rom_cpu_case_count']:,}项实际callerRTS、{v['source_guard_case_count']}guard、0失败。7组×4个30×4个33×5个31×3SP的别名矩阵、全部24条实际家族排除ID和全256忠诚×3徳组合比较全2048RAM（含闲置栈）、8192SRAM、AXYP/SP/PC、端口/银行和N163图；237/255等raw记录指针不当有效武将身份。JMP新增公开3B，既有正文局部闭包{len(local)}位置、动态{len(seen&local)}，不把它们称本轮新写的全部内政代码。
'''
 text+='''
调用必须有实际寄存器、进入PC/银行与已有返回栈，拒绝seed/错误returnword/SP，不伪造RTS。通过SceneCoordinator的精确入口owner接入；未知调用保留dependency。GPU回执和忠诚回执是独立服务对照，Native画面/声音和父战后整合另列，不混成新CPU例。

[原字节](original.asm) · [静态目录](static-catalog.json) · [原CPU位置](executed-instructions.json) · [对照回执](validation.json) · [证据及hash](evidence.json)
'''
 (out/'README.md').write_text(text)
 print(json.dumps(dict(area=area,status='passed',CPU=v['rom_cpu_case_count'],static=len(local),dynamic=len(seen&local))))
if __name__=='__main__':main()
