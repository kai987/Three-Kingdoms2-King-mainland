#!/usr/bin/env python3
"""Export byte-provenance and bounded scopes for independent tactical decisions."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.tactical_decisions import TacticalData,ROM_SHA256,STRATEGY_ENTRIES
from inspect_game_data import disassemble

RANGES={
 'scan_and_result_suffix':(0xA02D,0xA099),
 'eight_strategy_pointers':(0xA099,0xA0B1),
 'nearest_enemy_prefix':(0xA17B,0xA1A8),
 'greedy_movement_and_quote':(0xA60C,0xA7CD),
 'movement_cost_tables':(0xA7CD,0xA805),
 'blocked_attack_fallback':(0xA805,0xA837),
 'orthogonal_neighbors':(0xA837,0xA8A8),
 'adjacent_attack':(0xA8A8,0xA8D3),
 'candidate_map':(0xA8D3,0xA944),
 'side_marker':(0xA944,0xA95C),
 'officer_pointer':(0xB491,0xB4C2),
 'divide_scratch':(0xB536,0xB585),
 'multiply_scratch':(0xB585,0xB5D5),
 'ai_rng':(0xB5D5,0xB5E5),
 'terrain_lookup':(0xB6E5,0xB74B),
 'reserved_effect':(0xB933,0xBAB3),
}

def analyze(rom,out):
    data=TacticalData.from_rom(rom);out.mkdir(parents=True,exist_ok=True);routines=[];listing=[]
    for name,(start,end)in RANGES.items():
        offset=0x10010+start-0xA000;raw=rom[offset:offset+end-start]
        routines.append(dict(name=name,physical_bank=8,cpu_start=start,cpu_end_exclusive=end,rom_offset=offset,byte_count=len(raw),raw_hex=raw.hex(' '),sha256=hashlib.sha256(raw).hexdigest()))
        listing.append(f'; {name}: bank8 ${start:04X}..${end-1:04X}\n')
        if name in('eight_strategy_pointers','movement_cost_tables'):
            if name=='eight_strategy_pointers':
                listing.append(disassemble(rom,8,0xA000,start,0xA0A1))
                for i,target in enumerate(STRATEGY_ENTRIES):
                    pos=0x100B1+2*i
                    assert int.from_bytes(rom[pos:pos+2],'little')==target
                    listing.append(f'{pos:06X} b08:${0xA0A1+2*i:04X} {rom[pos:pos+2].hex(" ").upper()} .word ${target:04X} ; strategy{i}\n')
            else:
                for j in range(0,len(raw),4):listing.append(f'{offset+j:06X} b08:${start+j:04X} .byte {", ".join(f"${v:02X}"for v in raw[j:j+4])}\n')
        else:listing.append(disassemble(rom,8,0xA000,start,end))
    request_start,request_end=0xA51F,0xA545
    request_offset=0x18010+request_start-0xA000
    request_raw=rom[request_offset:request_offset+request_end-request_start]
    listing.append('; Physicalbank12 battle movement secondary request/check boundary\n'+disassemble(rom,12,0xA000,request_start,request_end))
    (out/'original-ranges.asm').write_text(''.join(listing))
    chunks=[]
    for i,tiles in enumerate(data.chunk_tiles):
        pointer=data.chunk_pointers[i];bank=(rom[0x118CB+i]&63)%32;offset=16+bank*8192+pointer-0x8000
        assert tiles==rom[offset:offset+256]
        chunks.append(dict(chunk=i,physical_bank=bank,cpu_pointer=pointer,rom_offset=offset,byte_count=256,sha256=hashlib.sha256(tiles).hexdigest()))
    dependencies=[dict(file=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())for p in(ROOT/'source/recovered/tactical_decisions.py',ROOT/'source/recovered/ai.py',ROOT/'source/recovered/terrain_semantics.py',ROOT/'scripts/verify_tactical_decisions.py',Path(__file__))]
    scopes=[
      dict(api='prepare_actor',entry=0xA02D,stop=[0xA099,0xB933,0x200],scope='prefix/route; strategy body deliberately not invoked',preconditions=['64K shared memory','active same-side slots with strategy low nibble0..7']),
      dict(api='finish_actor',entry=0xA062,stop=[0xA099,0x200],scope='suffix/prefix across scan;6F8F is explicit caller result',preconditions=['real existing strategy result in6F8F','scan counters/cursor reflect its pending attempt']),
      dict(api='plan_movement',entry=0xA60C,stop=[0x200],scope='complete original subroutine incl terrain/cost/neighbors; gameplayRAM equivalence',preconditions=['active actor0..19/officer0..236','targetx is byte, targety alreadynormalized','map chunk pointerA8/A9 and four IDsvalid']),
      dict(api='quote_direction',entry=0xA740,stop=[0x200],scope='complete original subroutine; semanticRAM and carry, valid quote A/X/Y/NZVC',preconditions=['direction0..3','same actor/map context']),
      dict(api='adjacent_attack',entry=0xA8A8,stop=[0x200],scope='complete original subroutine; proposal only',preconditions=['active actor domain','AP existing0505']),
      dict(api='nearest_enemy',entry=0xA17B,stop=[0xA1A8,0xA1C0],scope='prefix; original radius2 variant dynamically verified',preconditions=['active actor domain','same-side/target flags initialized']),
      dict(api='secondary_effect',entry=0xB933,stop=[0x200],scope='complete original subroutine; actual SRAM troops and effect report writes',preconditions=['active actor domain','cached slot04D8+sideoffset isFF or active slot0..19/officer0..236','original RNG permutation data'])]
    result=dict(rom_sha256=ROM_SHA256,source_kind='independent recovered high-level algorithms; not original game source',source='source/recovered/tactical_decisions.py',routines=routines,scopes=scopes,
      strategy_entries=[dict(id=i,entry=target)for i,target in enumerate(STRATEGY_ENTRIES)],
      fields={'control':0x6F8B,'actor':0x6F8C,'action_or_direction_or_attack_target':0x6F8D,'tactic_target':0x6F8E,'proposal_status':0x6F8F,'rng_cursor':0x6F92,'rng_saved_x':0x6F93,'scan_cursor':0x6F94,'no_action_count':0x6F95,'attempted_count':0x6F96,'movement_cost':0x6F97,'strategy_bytes':0x6FA1,'remembered_reverse_direction':0x6FB5,'candidate_masks':0x6FC9,'orthogonal_neighbors':0x6FDD,'action_points':0x505,'condition_bytes':0x650,'reserved_records':0x4D8},
      proposal_status={'0':'movement direction in6F8D','1':'adjacent ordinary attack target in6F8D','2':'tactic action6F8D and target6F8E (existingai.py)','3':'no action; attempted actor counted as failure','255':'reserved secondary effect not applied'},
      cost_tables={'first_rom_offset':0x107DD,'second_rom_offset':0x107F9,'first_rows':data.costs.first,'second_rows':data.costs.second,'selector':'same officer byte8 read twice; second table iff byte8<3; byte9 ignored'},
      terrain_data=dict(pointer_table_rom_offset=0x117DB,bank_table_rom_offset=0x118CB,class_table_rom_offset=0x1175B,classes_sha256=hashlib.sha256(data.terrain_classes).hexdigest(),chunks=chunks),
      secondary_request_provenance=dict(physical_bank=12,cpu_start=request_start,cpu_end_exclusive=request_end,rom_offset=request_offset,raw_hex=request_raw.hex(' '),sha256=hashlib.sha256(request_raw).hexdigest(),protocol='A51F waits controlFF then writes1/actor0509 and increments0501; A535 waitsFF and accepts status0'),
      rng_data=dict(rom_offset=0x115F5,byte_count=256,sha256=hashlib.sha256(data.rng).hexdigest(),is_permutation=len(set(data.rng))==256),
      important_quirks=['Attempted/no-action counters wrap modulo256; unequal counts cause a full scan reset.',
        'All movement target deltas use SBC/BPL signed-byte magnitude, not unbounded abs.',
        'Equal-axis target displacements prefer vertical; equal costs preserve that order.',
        'If already at target, original can still propose verticalpositive movement.',
        'Previously remembered reverse direction is copied to2F but never consulted in A60C.',
        'Only complete strategy byte1/5 enables blocked enemy fallback; high-nibble flags prevent it.',
        'Fallback writes candidate attack target before the AP>=2 check, even when final status3.',
        'B965 compares actorX but cached-groupY slot0/4 instead of actorY.',
        'Secondary actor candidate0 is rejected, including same-side zero-distance.',
        'Secondary IQdifference+10 and initial accepted0..100 random draw are dead computations; draw still changes RNGcursor/savedX.',
        'Secondary packedbyte11 multiplier isbyte arithmetic with an ADCcarry between additions; it is not10*experiencelevel.',
        'Secondary troop subtraction masks low10 and preserves upper6 bits of recordbyte9.'],
      boundaries=['Semantic APIs exclude CPUregisters/stack and F266 data-window DE/E000 writes except declared quote results; complete controller separately reconstructs them.',
        'No AP consumption, coordinate commit, proposal acknowledgement or UI completion is performed.',
        'Remaining eightstrategy orchestration, retreat policy, morale and resupply are not claimed as high-level source in this module.',
        'Runtime reachability in an unmodified campaign is not proved by these explicit CPUfixtures.'],
      dependency_pins=dependencies)
    (out/'evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    validation_path=out/'validation.json'
    validation=json.loads(validation_path.read_text())if validation_path.exists()else{}
    pins={p['file']:p['sha256']for p in dependencies}
    assert not validation or validation.get('source_sha256')==pins['source/recovered/tactical_decisions.py']
    assert not validation or validation.get('verifier_sha256')==pins['scripts/verify_tactical_decisions.py']
    count=validation.get('rom_oracle_case_count','pending');guard=validation.get('source_guard_case_count','pending')
    readme=f'''# Phase7：战场AI可读决策段\n\n新增 `source/recovered/tactical_decisions.py` 是根据6502行为独立重写的玩法算法，并非原始源码。它与单独的完整CPU控制器分开：当前模块恢复扫描边界、两个轴方向的移动选择、相邻攻击、最近候选前缀及已部署持续效果的应用。\n\n## API和验证边界\n\n构造 `TacticalDecisions(shared_memory, TacticalData.from_rom(rom))`；同一64K内存被直接读写。`decision_state()` 返回提案和扫描字段。\n\n| API | 原入口/终点 | 恢复范围 |\n|---|---|---|\n| `prepare_actor()` | A02D→A099/B933/RTS | 扫描前缀：跳过inactive、异侧、空武将；尝试计数，控制路由 |\n| `finish_actor()` | A062→A099/RTS | 以真实现有6F8F结果计数、yield或rescan；不替调用者制造成功 |\n| `plan_movement(x, normalized_y)` | A60C→RTS | 完整两个轴方向选择、地图/地形/AP报价、相邻占位、攻击fallback及提案写入 |\n| `quote_direction(direction)` | A740→RTS | 完整坐标边界和报价；不扣AP |\n| `adjacent_attack()` | A8A8→RTS | 完整AP>=2及上/下/左/右第一敌人提案 |\n| `nearest_enemy(radius)` | A17B→A1A8/A1C0 | 候选前缀，动态核对原radius2分支；不含后续目标加载/fallback |\n| `secondary_effect()` | B933→RTS | 完整缓存持续效果检查、实际扣兵、042C..042E及结束写回 |\n\n原ROM差分 **{count} 次**，另 **{guard} 项**源输入guard。每例比较完整 **8,192B SRAM** 和RAM `0020..002F`、`042C..042E`。方向报价还比较有效报价的A/X/Y和NZVC；越界报价比较carry。其他API不声称寄存器/栈/mapper等价。原Oracle执行真实ROM的地图、随机及算术辅助函数，无成功替换、无ROM补丁。\n\n## 扫描及提案协议\n\n`6F8B=FF`直接返回，`=1`交B933第二阶段，其余值扫描。`6F94`是下一槽号，`6F96`是已尝试合格actor次数，`6F95`是返回status3次数。三计数保持u8回绕。扫描到20若两个计数不相等，三者归0重扫；相等则status3、cursor0、controlFF。非3结果立即controlFF，交上层消费，不视为下一actor。strategy表有8项；不能因`AND0F`而虚构16项。\n\nstatus0将6F8D解释为方向，cost在6F97；status1将其解释为普通攻击目标槽。status2是旧ai.py已验证的计略ID/6F8E目标。移动提案不改坐标、不扣AP；其上层提交由根模块另行恢复。\n\n## 必须保留的原实现行为\n\n移动不是广度寻路：只比较朝目标的两个轴，较大位移优先，位移相等垂直优先；再按成本稳定排序。原SBC/BPL字节差不是普通整数绝对值。原来已经位于目标仍可能选择向下移动。反向记忆6FB5被复制至2F，但本段不读取2F参与选择。候选占位时只有完整strategy byte等于1或5才允许敌人fallback；fallback先写目标后检查AP，故失败status3仍可能改6F8D。condition0650非0阻止空位移动。\n\n报价保留两次读取同一officer byte8的代码：byte8<3用第二表，否则第一表；byte9不参与。地形affinity3的原0成本保持为原编码边界，不能给它编造新能力。\n\nB933的缓存组由当前side选0/4；B965先比较actorX，再用slot0/4的Y而非actorY。范围候选为0也拒绝。只有actor地形0继续。它先拒绝抽样到0..100，接受值及IQ差阈值随后被覆盖，但随机cursor消耗保留；再抽0..10。作用量为`floor(cachedIQ*(30+draw)/10)`加按整个packedbyte11执行的带carry字节倍率。扣兵针对10位，原byte9上6位保留。正式技能名称尚未由本段孤立地址确认，当前称“已部署缓存效果”。\n\n## 可复现\n\n```sh\n.venv-trace/bin/python scripts/verify_tactical_decisions.py '/Users/paulasmith/Downloads/三国志2超级版.nes'\n.venv-trace/bin/python scripts/analyze_tactical_decisions.py '/Users/paulasmith/Downloads/三国志2超级版.nes'\n```\n\n`evidence.json`保存每段ROM偏移、原字节、SHA、前置条件及完整/前缀终点；`original-ranges.asm`保存原指令；`validation.json`为差分回执和源码hash；`executed-instructions.json`是实际执行地址，不等于全部静态控制器覆盖。地图数据只提取原表和tiles，玩法源码不会执行ROM或回退到ROMadapter。\n\n本轮CPUfixtures明确控制actor、地图、occupancy、AP、RNG及缓存。未声称未修改的完整战役自然可达，也未声称画面/中断/硬件等价。全部8strategy编排、退却/士气/补给策略由完整CPU控制器继续执行；此模块尚未高层化这些整段策略。\n'''
    (out/'README.md').write_text(readme)
    print(json.dumps(dict(ranges=len(routines),original_range_bytes=sum(r['byte_count']for r in routines),chunks=len(chunks),rom_oracle_case_count=count,source_guard_case_count=guard),indent=2))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase7/decisions');a=p.parse_args();analyze(a.rom.read_bytes(),a.out)
