#!/usr/bin/env python3
"""Pin original byte provenance for the two readable bounded city actions."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_city_ui_controller import collect
from source.recovered.city_action_bridges import ROM_SHA256

def digest(raw):return hashlib.sha256(raw).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/action-bridges');a=p.parse_args()
    rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA256;out=a.out;out.mkdir(parents=True,exist_ok=True)
    instructions=[];bodies=[]
    for pair,entry,name in[(8,0xA01E,'shop_offers'),(10,0xA006,'recruitment_loyalty')]:
        I,tables=collect(rom,pair=pair,entries=(entry,));assert not tables and not any(x.get('hook')for x in I.values())
        raw=bytes.fromhex(''.join(x['raw_hex']for pc,x in sorted(I.items())))
        bodies.append(dict(name=name,pair=[pair,pair+1],export_entry=entry,original_instruction_count=len(I),
            original_instruction_byte_count=len(raw),sorted_instruction_bytes_sha256=digest(raw),external_calls=[]))
        instructions.extend(I.values())
        lines=[f'; Physical pair{pair}/{pair+1}, export ${entry:04X}; original immutable bytes.']
        for pc,x in sorted(I.items()):
            operand=''if x['mode']=='imp'else'A'if x['mode']=='acc'else f'${x["operand"]:04X}'
            lines.append(f'b{x["physical_bank"]:02d}:{pc:04X} file{x["rom_offset"]:06X}  {x["raw_hex"]:<7s}  {x["op"]} {operand}')
        (out/(name+'-original.asm')).write_text('\n'.join(lines)+'\n')
    ranges=[]
    for bank,address,size,label in[(9,0xC89E,64,'equipment_prices_32_words'),(9,0xC8DE,96,'shop_offers_6_groups_4_categories_4_items'),(28,0xC801,30,'city_shop_group_30_bytes')]:
        offset=16+bank*8192+(address&8191);raw=rom[offset:offset+size]
        ranges.append(dict(physical_bank=bank,cpu_address=address,rom_offset=offset,size=size,name=label,raw_hex=raw.hex(),sha256=digest(raw)))
    source='source/recovered/city_action_bridges.py';validator='scripts/verify_city_action_bridges.py';analyzer='scripts/analyze_city_action_bridges.py'
    receipt_path=out/'validation.json';receipt=json.loads(receipt_path.read_text())if receipt_path.exists()else None
    evidence=dict(schema='phase13-city-action-byte-provenance-v1',rom_sha256=ROM_SHA256,source_file=source,
        source_sha256={path:digest((ROOT/path).read_bytes())for path in(source,validator,analyzer,'source/recovered/battle_nmi_services.py')},
        production_source_original_CPU_callbacks=0,production_IR_interpretation=False,original_bodies=bodies,
        original_instructions=sorted(instructions,key=lambda x:(x['physical_bank'],x['pc'])),data_ranges=ranges,
        city_callers=[dict(pair=[27,28],call_pc=0xC7AB,inline_target=0xA01E,logical_selector=0x28,role='Shop category selection; group from28C801[0402], category0012'),
                      dict(pair=[27,28],call_pc=0xAD32,inline_target=0xA006,logical_selector=0x2A,role='Recruitment loyalty'),
                      dict(pair=[27,28],call_pc=0xD46C,inline_target=0xA006,logical_selector=0x2A,role='Additional loyalty caller')],
        distinctions=dict(shop='Prepare4IDs at044C and4LE16 prices with zero tags at042C; no purchase/resource deduction.',
            loyalty='Targetbyte3 only; no owner/roster/residence/status/troop write.',
            formula='max(10,min(90,((70+leader_virtue//10)-old_target_loyalty)&255))',
            CPU_protocol='OriginalD2AB field pointer,D40F sixteen-step restoring division and actual localJSR/callerRTS preserved.',
            domains='Shop group0..5/category0..3; actual city mapping group0..2. Rawbyte IDs including237..255 are service-address tests, not valid officer gameplay.',
            completion='Both bounded bodies have no external dependency or hardware read/write. No ready flag is acknowledged.'),
        validation=None if receipt is None else dict(path=str(receipt_path.relative_to(ROOT)),sha256=digest(receipt_path.read_bytes()),
            status=receipt['status'],rom_cpu_case_count=receipt['rom_cpu_case_count'],source_guard_case_count=receipt['source_guard_case_count'],comparison=receipt['comparison']))
    (out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    count=receipt['rom_cpu_case_count']if receipt else'pending';guards=receipt['source_guard_case_count']if receipt else'pending'
    readme=f'''# 城市动作服务：装备候选与招募忠诚

本轮补齐两个城市27/28远端动作，独立手写具名函数，不解释IR或执行原ROM代码。8 A01E（原 `4C 51 C8`）进入physical9 C851，42条原指令；10 A006（原 `4C 3F CF`）进入physical11 CF3F，含本地D2AB/D40F/D61E共79条原指令。两者没有外部callee、PPU/APU/mapper访问或等待确认。

## 装备候选

27/28 C7AB真实selector28调用8 A01E。0402索引physical28 C801的30字节城市组表，原数据仅为0/1/2；0012是0..3类别。C851选择 `group*16 + category*4` 开始的四项，写044C[4]装备ID，并按physical9 C89E的32个LE16数值建立042C的四个3字节记录，第三字节始终0。C8DE原offers表共有6组、每组4类×4项，source支持所有96项的表内上下文；它没有购买或扣金行为。

## 招募忠诚

27/28 AD32和D46C调用10 A006。原逻辑读取30指定的leader byte4徳与31指定的target byte3忠，计算 `max(10,min(90,(70+徳//10−旧忠)&255))`，仅写目标byte3。负差先按原8bit下溢再夹值，不能按普通有符号减法夹0。与旧OfficerTransfer纯玩法核心相同；本轮还恢复真实D2AB指针、D40F商/余数scratch、所有局部JSR栈残余与最终AXYP/SP/PC。D61E在此ROM中就是1字节RTS，原空body也保留真实caller栈写入。

FF/raw IDs仍按12字节寻址，不偷偷改为另一武将或假返回；237..255仅作为服务字节地址边界，不能宣称为正常武将。两个body均不写city owner、名册、驻城、status或兵数字段。

## 原 CPU 对照与范围

正式回执 {count} 次完整原CPU返回、{guards} 个源码拒绝测试。比较全部2048B RAM（包括free-stack残余）、全部8192B SRAM、AXYP/SP/PC、银行和有序端口；这些body实际端口序均为空。source侧原CPUcallbacks=0。覆盖全部6×4shop组合、忠诚夹值/下溢、同记录alias、原字节ID边界、word除法/除数0边界、全部256个callerSP；此处都是明确准备的有界service CPU输入，不是原核心内部trace。decimal flag需清除是该py65对照协议，源码在变更前拒绝D标志与表外shop索引；原CPU不执行这些非法表外索引。

实际原核心城市菜单及资料浏览双跑证据在[上一层runtime](../runtime/README.md)；该自然流程在动作确认前取消，没有自然观察这两个动作的扣资源/玩法后续。新的城市coordinator整合验证单列，不与这里的body对照混计。

```python
rules = CityActionBridges(memory, CityActionData.from_rom(rom))
rules.run_entry(0xA01E, registers=actual_caller_registers)
rules(ServiceCall(...))  # accepts only the exact physical pair/owned entry
```

```sh
.venv-trace/bin/python scripts/verify_city_action_bridges.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_action_bridges.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[源码](../../../source/recovered/city_action_bridges.py) · [验证回执](validation.json) · [字节、表与hash证据](evidence.json) · [原装备函数](shop_offers-original.asm) · [原忠诚函数](recruitment_loyalty-original.asm)
'''
    (out/'README.md').write_text(readme)
    print(json.dumps(dict(status='written',original_instructions=len(instructions),source_sha256=evidence['source_sha256'][source],CPU=count,guards=guards)))
if __name__=='__main__':main()
