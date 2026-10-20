#!/usr/bin/env python3
"""Byte-pin the exact fixed menu producer and its real local call frames."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES
from source.recovered.city_menu_navigation import CityMenuNavigation
from source.recovered.officers import ROM_SHA256
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/menu-navigation');a=p.parse_args()
    rom=a.rom.read_bytes();assert sha(rom)==ROM_SHA256;out=a.out;out.mkdir(parents=True,exist_ok=True)
    instructions=[];pc=0xED19
    while pc<0xEDF5:
        f=16+31*8192+(pc&8191);op,mode=OPS[rom[f]];size=SIZES[mode]
        assert op!='?';raw=rom[f:f+size];value=int.from_bytes(raw[1:],'little')
        instructions.append(dict(physical_bank=31,cpu_address=pc,rom_offset=f,raw_hex=raw.hex(),op=op,mode=mode,operand=value))
        pc+=size
    assert pc==0xEDF5
    f=16+31*8192+0xD19;raw=rom[f:f+0xDC]
    (out/'original-ranges.asm').write_text('\n'.join(f'b31:{x["cpu_address"]:04X} file{x["rom_offset"]:06X} {x["raw_hex"]:<7s} {x["op"]} ${x["operand"]:04X}'for x in instructions)+'\n')
    receipt=json.loads((out/'validation.json').read_text());executed=json.loads((out/'executed-instructions.json').read_text())
    visited={x['cpu_address']for x in executed};scope={x['cpu_address']for x in instructions}
    source='source/recovered/city_menu_navigation.py';validator='scripts/verify_city_menu_navigation.py';analyzer='scripts/analyze_city_menu_navigation.py'
    evidence=dict(schema='phase13-fixed-menu-byte-provenance-v1',rom_sha256=ROM_SHA256,
        original_range=dict(physical_bank=31,cpu_address=0xED19,end_exclusive=0xEDF5,rom_offset=f,size=len(raw),sha256=sha(raw),raw_hex=raw.hex()),
        original_instruction_count=len(instructions),dynamic_original_instruction_count=len(scope&visited),not_dynamically_executed=sorted(scope-visited),
        original_instructions=instructions,public_entries=CityMenuNavigation.PUBLIC_ENTRIES,
        local_direction_entries=CityMenuNavigation.LOCAL_ENTRIES,
        real_call_frames=[dict(call_pc=p,target=t,return_word=p+2)for p,t in[(0xED4A,0xED71),(0xED54,0xED8D),(0xED5E,0xEDA9),(0xED68,0xEDBE),
            (0xED6B,0xEDDD),(0xED74,0xEDDD),(0xEDA1,0xEDDD),(0xEDAC,0xEDDD)]],
        source_sha256={p:sha((ROOT/p).read_bytes())for p in(source,validator,analyzer,'source/recovered/scene_shared_services.py','source/recovered/battle_nmi_services.py')},
        validation=dict(path=str((out/'validation.json').relative_to(ROOT)),sha256=sha((out/'validation.json').read_bytes()),status=receipt['status'],
            rom_cpu_case_count=receipt['rom_cpu_case_count'],source_guard_case_count=receipt['source_guard_case_count'],comparison=receipt['comparison']),
        distinctions=dict(order='right80,left40,down20,up10; writes0012 after all four directions and finalED6B call.',
            previous_selection='Only prior0012==0 enables wrap; it is not an inferred independent wrap flag.',
            horizontal_left='SkipFF only;80..FE can be selected by this original path.',
            right_down_up='Signbit detects boundaries; up count differs from FF-only left scan.',
            cyclic='Missing sentinel after a whole byte period returns source dependency at originalED9E/EDCF, preserves caller stack; source guards are not completeCPU cases.',
            arithmetic='row*width+column is wrapped byte offset; EDDD returns originalAXYP without stack seeding.'),
        production_source_original_CPU_callbacks=0,production_IR_interpretation=False)
    (out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    (out/'README.md').write_text(f'''# 精确菜单导航与局部调用栈

原fixed31 ED19..EDF4菜单服务独立恢复为`CityMenuNavigation`，保留Shared历史冻结文件。八个宽度入口ED19..ED3C给1..8，ED41使用原A宽度，EDDD计算原byte offset；不执行原代码、IR或PC指令表。

方向按right80、left40、down20、up10顺序执行。每个方向保留ED4A/54/5E/68真实JSR，内部值查询保留ED74/EDA1/EDAC真实JSR；最终ED6B→EDDD写原returnword ED6D。这修正了旧Shared语义menu在已返回后缺少两字节inactive stack残余的问题，玩法数据与旧规则一致，新的合同包含全部free-stack RAM。

0012旧选项为0才可换行/回绕，最后才写新选项；不把它另解释为独立开关。left拒绝仅FF，80..FE仍可被其选中；right/down与up终点按signbit判断，不能统一为FF判定。row×width+column、X/Y和字段均保留byte wrap。

{receipt['rom_cpu_case_count']}次原CPU完整返回，{receipt['source_guard_case_count']}个源码拒绝/依赖测试，0失败；比较全部2048RAM（包含全部inactive栈）、8192SRAM、AXYP/SP/PC、ports/banks。覆盖宽度1..8的合法三行/空项菜单、9种方向输入、原raw offset边界、全部256 callerSP和非FF负值left特性；这是明确准备的服务CPU输入，不是Native内部寄存器。静态{len(instructions)}原指令位置，动态命中{len(scope&visited)}；位置覆盖不等于全部输入组合。

两项缺sentinel测试保持原循环dependency于ED9E/EDCF，原caller不RTS；重复resume走真实循环仍等待，不清ready。它们单列source guards，不计原CPU完整返回。其余guards拒绝decimal协议、缺实际caller寄存器和未知target。

```python
owner = CityMenuNavigation(memory, rom, callbacks=None)
owner.run_service(0xED1E, actual_registers)
owner(service_call)  # original existing caller frame; never seeds a return
```

```sh
.venv-trace/bin/python scripts/verify_city_menu_navigation.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_menu_navigation.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[新源码](../../../source/recovered/city_menu_navigation.py) · [原字节/frames](evidence.json) · [实际CPU回执](validation.json) · [原汇编](original-ranges.asm)
''')
    print(json.dumps(dict(status='written',source_sha256=evidence['source_sha256'][source],CPU=receipt['rom_cpu_case_count'],guards=receipt['source_guard_case_count'],static=len(instructions),dynamic=len(scope&visited))))
if __name__=='__main__':main()
