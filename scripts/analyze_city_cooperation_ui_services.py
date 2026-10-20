#!/usr/bin/env python3
"""Pin immutable raw bytes for29A042's AI-turn badge/header producer."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_city_ui_controller import collect
from source.recovered.city_cooperation_ui_services import ROM_SHA256
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase14/city-cooperation-ui');a=p.parse_args()
    rom=a.rom.read_bytes();assert digest(rom)==ROM_SHA256;out=a.out;out.mkdir(parents=True,exist_ok=True)
    I,tables=collect(rom,pair=29,entries=(0xA042,));assert len(I)==148 and not tables
    lines=['; Immutable original29A042 -> AA37, localAB38; source runtime does not execute these bytes.']
    for pc,x in sorted(I.items()):
        operand=''if x['mode']=='imp'else'A'if x['mode']=='acc'else f'${x["operand"]:04X}'
        lines.append(f'b{x["physical_bank"]:02d}:{pc:04X} file{x["rom_offset"]:06X} {x["raw_hex"]:<7s} {x["op"]} {operand}')
    (out/'original.asm').write_text('\n'.join(lines)+'\n')
    ranges=[]
    for bank,address,size,label in[(29,0xAB08,48,'four_two_row_captions'),(29,0xABB8,13,'badge_OAM_y'),(29,0xABC5,13,'badge_OAM_x'),(17,0x8DB4,3328,'raw256_badge_records_13_bytes')]:
        offset=16+bank*8192+(address&8191);raw=rom[offset:offset+size]
        ranges.append(dict(physical_bank=bank,CPU_address=address,ROM_offset=offset,size=size,label=label,raw_hex=raw.hex(),sha256=digest(raw)))
    paths=['source/recovered/city_cooperation_ui_services.py','source/recovered/scene_shared_services.py','source/recovered/battle_nmi_services.py',
        'scripts/verify_city_cooperation_ui_services.py','scripts/analyze_city_cooperation_ui_services.py']
    receipt=out/'validation.json';v=json.loads(receipt.read_text());raw=b''.join(bytes.fromhex(x['raw_hex'])for pc,x in sorted(I.items()))
    body=set(I);executed={x['cpu_address']for x in v['executed_original_locations']if x['physical_bank']==29};dynamic=body&executed
    catalog=dict(rom_sha256=ROM_SHA256,entry=0xA042,physical_pair=[29,30],original_instruction_count=len(I),original_instruction_bytes=len(raw),
        sorted_instruction_bytes_sha256=digest(raw),original_instructions=list(I.values()),data_ranges=ranges,
        fixed_calls=[dict(call_pc=0xAB3A,target=0xF25F,role='ActualNMI data windowE1/E000=49 -> bank17'),dict(call_pc=0xAB50,target=0xEBE9,role='Multiply rawbadgeID by13; real scratch and localJSR residue')])
    (out/'static-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    evidence=dict(schema='phase14-city-cooperation-UI-evidence-v1',rom_sha256=ROM_SHA256,status=v['status'],
        source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256={p:digest((ROOT/p).read_bytes())for p in paths},
        ROM_body=catalog,validation=dict(path=str(receipt.relative_to(ROOT)),sha256=digest(receipt.read_bytes()),rom_cpu_case_count=v['rom_cpu_case_count'],source_guard_case_count=v['source_guard_case_count'],comparison=v['comparison']),
        dynamic_body_instruction_count=len(dynamic),static_body_instruction_count=len(body),unexecuted_body_positions=sorted(body-dynamic),
        ownership=dict(pair=[29,30],public_entries=[0xA042,0xAA37,0xAB38]),
        caller=dict(pair=[25,26],call_pc=0xC835,selector=0x3D,inline_target=0xA042,role='Ruler cooperation turn display; furtherC7E0 branches also use this producer'),
        distinctions=['Body preserves0A/0B/0C. Raw0BFF skipsbadge;0C!=0 stops afterOAM. Caption0A0..3 selects12tiles;0AFF blank.',
            'Badge records selectCHRpageB9 and centered12tiles with originalFF earlystop, byte cursor and tile+C0 wrap.',
            'This produces0380 two-linePPUjob and7E|4. It neither waits for nor fabricates consumer completion or6F8B ack.'])
    (out/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    (out/'README.md').write_text(f'''# 城市合作 AI 的真实标记与文字请求

新增独立[CityCooperationUIServices](../../../source/recovered/city_cooperation_ui_services.py)，补齐 physical29/30 `A042 → AA37` 及本地 `AB38`。原闭包148条指令，两个固定调用 `AB3A → F25F`、`AB50 → EBE9` 复用已有独立源码，保留实际JSR栈、scratch和mapper协议。运行时不执行ROM、IR或opcode，也没有原CPUfallback。

`0A` 是四组标题编号0..3或FF空标题，`0B` 是标记记录ID（FF跳过），`0C` 非零时只绘制标记。AB38选择NMI数据窗E1/E000=49，即physical17；按13×rawID读取13字节记录，首字节写CHR页B9，其余至多12字节建立OAM。原FF提前终止、空列中心偏移、tile+C0及OAM7C的byte溢出均保留。直接237..255测试是字节寻址边界，不声称有效武将身份。

AA37保存并恢复0A/0B/0C。标题路径产生0380中的两行tile请求，写7E|4；它不消费PPU任务、不确认继承人、不写6F8B=1。真正城市NMI2从25/26 C7E0（C835等selector3D调用）使用此服务；后续等待/计时与主循环resume在上层整合回执单列。

正式原CPU对照 **{v['rom_cpu_case_count']}次完整callerRTS、{v['source_guard_case_count']}个源码拒绝测试、0失败**，全部2048B RAM（含inactive栈）、8192B SRAM、AXYP/SP/PC、银行、读口与有序写口比较。原148条body中动态覆盖{len(dynamic)}条；全256raw记录、256个原callerSP及256个OAMbyte cursor是有界服务输入，不代表自然核心逐一触发。测试不导入人为ready或结果标志。

```python
service = CityCooperationUIServices(memory, rom, services=None)
service.run_entry(0xA042, registers=actual_caller_registers)
service(ServiceCall(...))  # exact29/30 ownership; existingcallerframe
```

```sh
.venv-trace/bin/python scripts/verify_city_cooperation_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_city_cooperation_ui_services.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

[验证](validation.json) · [原始汇编](original.asm) · [字节和表](static-catalog.json) · [哈希证据](evidence.json)
''')
    print(json.dumps(dict(status=v['status'],body_positions=len(I),dynamic_body_positions=len(dynamic),CPU=v['rom_cpu_case_count'],guards=v['source_guard_case_count'],source_sha256=evidence['source_sha256'][paths[0]])))
if __name__=='__main__':main()
