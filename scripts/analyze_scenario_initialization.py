#!/usr/bin/env python3
"""Pin29A018 persistent scenario initialization, original templates and contract."""
from pathlib import Path
import argparse,json,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_ui_graphics_initialization import finalize_bundle
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase13/scenario');a=p.parse_args();rom=a.rom.read_bytes()
 regions=[('new_scenario_public_trampoline',29,0xA018,0xA01B,'code'),('lower_SRAM_clear_random_variant_copy_initialization',30,0xDD8B,0xDE7E,'code'),('city_record_templates960bytes',16,0x8C00,0x8FC0,'data'),('officer_pool_template2880bytes',17,0x8000,0x8B40,'data'),('original_rng256byte_lookup',31,0xE8BA,0xE9BA,'data')]
 contract=dict(APIs=['ScenarioInitialization(memory,ScenarioData.from_rom(rom),services=None)','scenario_init() generator owned by run_entry','run_entry(entry=A018,registers)','__call__(ServiceCall)','resume()'],entry_mapping=dict(physical_public_bank=29,public=0xA018,public_bytes='4C8BDD',physical_body_bank=30,body=0xDD8B,end_exclusive=0xDE7E),
  caller='Actual29/30pair and existingRTS frame; original globalmain11 E42F callsA018. Lower4KiBSRAM must be writable under caller mapper protection; service makes noF800 protection request.',
  input_fields={'6F43':'saved before6000..6FFFclear, restored unchanged','0050':'original table RNG cursor, may advance repeatedly on rejected sample&7>=5','0051':'original RNG saved X scratch','source16':'960citytemplatebytes at8C00','source17':'2880officerpooltemplatebytes at8000'},
  effects=['Clear6000..6FFF only; preserve6F43 and leave7000..7FFF unchanged.','Reject RNG low3bits5..7; store accepted0..4 at6F45.','Set6F04/6FE2=FF and citymain0400=11/sub0401=0.','F25F selector48 mapsphysical16; copy960bytes8C00..8FBF→6000..63BF.','F25F selector49 mapsphysical17; copy2880bytes8000..8B3F→63C0..6EFF.','Set6F00=59hex(decimal89),6F01=0,6F83..6F89=FF,6F8A=0.'],
  template_note='Original2880byte officer pool copy is240 twelvebyte slots; only237 IDs have confirmed officer identities. No invented identities are assigned to trailing three slots.',
  scope='Persistent record producer only. Subsequent title/ruler selection, scenario customization, background rendering and globalUI controller calls remain their actual owners.',
  services={'E87A':'independentSceneSharedServices/ControlHelpers exact RNG/table flags and actualstack','F25F':'independent exact mapper window request'},
  verification='ExplicitCPUfixtures initialize allRAM/SRAM, RNG cursor/saved byte, callerflags/stack. Compareall2048RAM includingstack,all8192SRAM,AXYP/SP/PC,orderedE000 writes and finalbanks. No nativeframe orpixel/PPUclaim.')
 archives=[str(x.relative_to(ROOT))for x in(ROOT/'analysis/rea/pairs/pair-29/functions').glob('*')if x.stem=='0xdd8b'and x.suffix in('.asm','.c')]
 e,v=finalize_bundle(rom,a.out,'source/recovered/scenario_initialization.py','scripts/verify_scenario_initialization.py','scripts/analyze_scenario_initialization.py',regions,['scripts/analyze_ui_graphics_initialization.py','source/recovered/scene_shared_services.py','source/recovered/controller_helpers.py','source/recovered/battle_nmi_services.py','source/recovered/service_memory.py'],schema='phase13-scenario-record-init-v1',contracts=contract,archives=archives)
 (a.out/'README.md').write_text(f'''# 阶段13：新剧本持久记录初始化

真实入口是physical29 `A018`（原bytes `4C8BDD`）→physical30 `DD8B..DE7D`，来自全局main11 `E42F`。它不是图形loader；它有意替换游戏的新剧本记录。独立`ScenarioInitialization`使用具名Python循环、复制和原共享RNG／mapper服务，没有原CPU、IR或opcode执行。不会代替全局后续选择／背景／PPU工作。

先保存6F43，清6000..6FFF，恢复6F43；原E87A表采样低3位，遇5..7重抽，接受0..4写6F45。设置6F04/6FE2=FF和0400/0401=11/0。真实F25F selector48将数据窗映射physical16，从8C00复制960B到6000；selector49映射physical17，从8000复制2880B到63C0。后者是240个12B池槽的原copy长度，不代表确认了240个武将身份；已确认姓名／肖像仅237位。最后6F00=89、6F01=0，6F83..6F89=FF、6F8A=0。7000..7FFF不动，原6F43保留。

调用方须已经使低4KiBSRAM可写；本服务没有F800写，也不会偷偷改变mapper保护。CPU对照使用原Bus保护4C（低4KiB可写）与明确相同软件memory合同。复制与clear都保留真实scratch、flags、stack残留和返回PC/SP。64种RNGcursor×两个真实entry×两个保存byte／SP／flags共{v['rom_cpu_case_count']}原CPU完整返回病例，另{v['source_guard_case_count']}guards，0失败；本地执行位置{e['local_instruction_location_observed']}/{e['local_instruction_location_total']}。全部2048RAM、8192SRAM、AXYP/SP/PC、写端口序和banks逐字节比对。

```python
owner = ScenarioInitialization(memory, ScenarioData.from_rom(rom))
result = owner(actual_ServiceCall)  #actual29/30pair, real caller frame
```

- [独立源码](../../../source/recovered/scenario_initialization.py)
- [最终原CPU验证与pins](validation.json)
- [原code／template数据／合同](evidence.json)
- [原汇编与数据范围](original-ranges.asm)
- [实际原CPU位置](executed-instructions.json)

```sh
.venv-trace/bin/python scripts/verify_scenario_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
python3 scripts/analyze_scenario_initialization.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
```

这些是独立服务的CPU输入条件矩阵，不是自然整帧回放；没有完整NES或新剧本可玩性的额外声明。
''')
 print(json.dumps(dict(status=v['status'],CPU=v['rom_cpu_case_count'],guards=v['source_guard_case_count'],source=v['source_sha256'])))
if __name__=='__main__':main()
