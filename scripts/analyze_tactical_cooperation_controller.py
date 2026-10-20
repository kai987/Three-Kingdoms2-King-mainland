#!/usr/bin/env python3
"""Offline raw-ROM CFG to direct named tactical cooperative procedures.

The old phase7 IR is not a generation input. Inline B517 words are data;
the recovered production source imports no compiler, graph or interpreter.
"""
from pathlib import Path
import argparse,ast,hashlib,json,sys,types,re
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES,instruction
from analyze_battle_scene_controller import Structurer,HEADER,BRANCHES,successors
from ui_structuring import labelled_procedure,loop_exception_source

SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase14/tactical';SOURCE=ROOT/'source/recovered/tactical_cooperation_controller.py'
TABLES={0xA09E:(0xA0A1,8,'actor_strategy'),0xACAB:(0xACAE,16,'tactic_target_predicate')}
FIELDS={0x6F8B:'REQUEST',0x6F8C:'ACTOR_SLOT',0x6F8D:'PROPOSAL_ACTION',0x6F8E:'PROPOSAL_TARGET',0x6F8F:'PROPOSAL_STATUS',
        0x6F92:'RNG_CURSOR',0x6F93:'RNG_SAVED_X',0x6F94:'SCAN_SLOT',0x6F95:'NO_ACTION_COUNT',0x6F96:'ATTEMPTED_COUNT',0x6F97:'MOVE_COST',
        0x504:'SIDE',0x505:'AP',0x50E:'CITY',0x600:'UNIT_X',0x614:'UNIT_Y',0x628:'UNIT_CONDITION',0x664:'UNIT_IDS',0x6FA1:'UNIT_STRATEGY'}
NAMES={0xA000:'tactical_entry',0xA02D:'cooperative_update',0xA03C:'scan_eligible_actors',0xA099:'dispatch_actor_strategy',
 0xA0B1:'strategy_00_tactics_and_advance',0xA105:'strategy_01_opposite_commander',0xA166:'strategy_02_near_actor',
 0xA210:'strategy_03_escort_own_commander',0xA2AD:'strategy_04_actor_radius_three',0xA329:'strategy_05_resupply',
 0xA507:'strategy_06_heal',0xA606:'strategy_07_no_action',0xA944:'opposing_side_marker',0xA95C:'choose_basic_tactic',
 0xA9CF:'prioritize_basic_tactics',0xAC7B:'check_tactic_target',0xAE93:'rank_candidate_troops',0xAF0D:'propose_retreat',
 0xAFF6:'choose_retreat_city',0xB067:'sum_army_troops',0xB933:'consume_opposite_ambush_cache',
 0xA60C:'plan_two_axis_movement',0xA740:'quote_direction_ap_cost',0xA837:'find_orthogonal_neighbors',
 0xA8A8:'propose_adjacent_attack',0xAAF8:'choose_special_tactic',0xAB68:'prioritize_special_tactics',
 0xAC31:'scan_special_officer_whitelist',0xB0FB:'officer_record_pointer',0xB4E1:'initial_officer_record_pointer',
 0xB536:'divide_u24_by_u16',0xB585:'multiply_u24_by_u8',0xB5D5:'draw_ai_rng_byte',
 0xB6E5:'normalized_terrain_at_scratch_xy',0xB705:'read_terrain_chunk'}

def offset(pc):return 16+8*8192+pc-0xA000
def collect(rom):
    pending=[0xA000];I={};tables=[];occupied={}
    while pending:
        pc=pending.pop()
        if pc in I:continue
        if not 0xA000<=pc<0xBAB3:raise ValueError(f'Unclassified tactical destination ${pc:04X}')
        f=offset(pc);op,mode=OPS[rom[f]];size=SIZES[mode];nxt=pc+size
        if op=='?':raise ValueError(f'Unclassified original code byte ${pc:04X}')
        for address in range(pc,nxt):
            if address in occupied:raise ValueError(f'Overlapping original instruction ${pc:04X}')
            occupied[address]=pc
        value=int.from_bytes(rom[f+1:f+size],'little')
        if op in BRANCHES:value=(nxt+(value if value<128 else value-256))&65535
        x=dict(pc=pc,physical_bank=8,bank=8,rom_offset=f,op=op,mode={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp'}.get(mode,mode),
               operand=value,next_pc=nxt,raw_hex=rom[f:f+size].hex())
        if pc in TABLES:
            address,count,name=TABLES[pc];assert op=='JSR'and value==0xB517 and address==nxt
            targets=tuple(int.from_bytes(rom[offset(address)+2*i:offset(address)+2*i+2],'little')for i in range(count))
            assert address+2*count==min(targets)
            x.update(op='DISPATCH',targets=targets);pending.extend(targets)
            tables.append(dict(call_pc=pc,helper=0xB517,table_cpu=address,rom_offset=offset(address),count=count,targets=targets,name=name,
                raw_hex=rom[offset(address):offset(address)+2*count].hex(),sha256=hashlib.sha256(rom[offset(address):offset(address)+2*count]).hexdigest()))
        elif op=='JSR':
            if value in(0xB517,0xEADE,0xEE07):raise ValueError(f'Unclassified inline helper ${pc:04X}')
            if 0xA000<=value<0xBAB3:pending.append(value)
            else:
                if value!=0xF266:raise ValueError(f'Unexpected external ${value:04X}')
                x['hook']='explicit original main-thread data-window helper'
            pending.append(nxt)
        elif op=='JMP':assert mode=='ab';pending.append(value)
        else:pending.extend(successors(x))
        I[pc]=x
    for t in tables:assert not any(t['table_cpu']<=pc<t['table_cpu']+2*t['count']for pc in occupied)
    return I,sorted(tables,key=lambda t:t['call_pc'])

class TacticalStructurer(Structurer):
    procedure=types.FunctionType(labelled_procedure.__code__,dict(labelled_procedure.__globals__,MANUAL_PROCEDURES={}),name='tactical_procedure')
    def addr(self,x):
        n=x['operand'];base=FIELDS.get(n,f'0x{n:04X}');mode=x['mode']
        if mode in('abs','zpg'):return base
        if mode in('abx','aby'):return f'({base}+r.{"x"if mode=="abx"else"y"})&65535'
        if mode in('zpx','zpy'):return f'({base}+r.{mode[-1]})&255'
        if mode=='iny':return f'((m[0x{n:02X}]|m[0x{(n+1)&255:02X}]<<8)+r.y)&65535'
        if mode=='inx':return f'm[({n}+r.x)&255]|m[({n}+r.x+1)&255]<<8'
        raise ValueError((mode,x['pc']))

TAIL='''    def _checkpoint(self,pc):
        self.registers.pc=pc
        if self._blocks>=self._limit:
            yield ServiceWait('control_budget',pc,value=self._limit,reason='Source block budget; no gameplay field or caller return is manufactured')
        self._blocks+=1
    def _dispatch(self,pc,targets):
        """Original B517 protocol; static inline words are immutable data."""
        r=self.registers;m=self.memory;index=r.a
        if index>=len(targets):raise ValueError(f'Original B517 bounded index {index} at ${pc:04X}')
        self._push((pc+2)>>8);self._push(pc+2);m[0x20]=r.y
        self._a(self._shift(r.a,True));self._y(r.a);self._y(r.y+1)
        self._a(self._pop());m[0x21]=r.a;self._a(self._pop());m[0x22]=r.a
        target=targets[index];self._a(target&255);m[0x23]=r.a;self._y(r.y+1)
        self._a(target>>8);m[0x24]=r.a;self._y(m[0x20]);r.pc=target
        return index
    def _external(self,pc,target,return_pc,kind,inline_target=None):
        r=self.registers;caller_sp=r.sp
        if kind!='tail':self._push((pc+2)>>8);self._push(pc+2)
        else:caller_sp=(r.sp+2)&255
        r.pc=target
        if return_pc is None:return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535
        self.events.append(dict(call_pc=pc,target=target,return_pc=return_pc,kind=kind))
        yield ServiceCall(target,return_pc,kind,r,self.memory,tuple(getattr(self.memory,'banks',())),caller_sp)
    def decision_state(self):
        m=self.memory
        return {name:m[address]for name,address in CONTROL_FIELDS}
    def _drive(self):
        while True:
            if isinstance(self.pending,ServiceWait):
                if self.pending.category=='control_budget':return self._result('budget')
                return self._result('dependency')
            if isinstance(self.pending,ServiceCall):
                call=self.pending
                if self.services is None:return self._result('dependency')
                try:result=self.services(call)
                except UnsupportedHardware:return self._result('dependency')
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                self._call_owner=None;return self._result('returned')
    def _result(self,status):
        return dict(status=status,before=self._before,after=self.decision_state(),registers=vars(self.registers).copy(),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self,*,max_blocks=None):
        if self._program is None:raise RuntimeError('No pending tactical invocation')
        if isinstance(self.pending,ServiceWait)and self.pending.category=='control_budget':
            if max_blocks is None:return self._result('budget')
            if not isinstance(max_blocks,int)or max_blocks<=0:raise ValueError('Explicit positive continuation budget required')
            self._limit=max_blocks;self._blocks=0;self.pending=None
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)
    def run_entry(self,entry=0xA000,*,registers=None,return_pc=None,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing tactical invocation first')
        if registers is None:raise ValueError('Supply actual caller registers and existing RTS frame')
        if entry not in self.LOCAL_ENTRIES:raise ValueError('Entry outside original tactical closure')
        if registers.p&D:raise ValueError('Binary CPU comparison requires D=0')
        if not isinstance(max_blocks,int)or max_blocks<0:raise ValueError('Nonnegative source block budget required')
        self.registers=registers;r=registers
        self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc
        self._return_sp=(r.sp+2)&255;self._before=self.decision_state()
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry);return self._drive()
    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=(8,9)or call.target not in self.LOCAL_ENTRIES:
            return {'status':'dependency','reason':'No tactical body owns this exact physical pair/entry'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns pending tactical update'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)

'''

def write_evidence(rom):
    catalog=json.loads((OUT/'static-catalog.json').read_text());source_catalog=json.loads((OUT/'source-catalog.json').read_text())
    v=json.loads((OUT/'validation.json').read_text());executed=json.loads((OUT/'executed-instructions.json').read_text())
    scope={(x['physical_bank'],x['pc'])for x in catalog['original_instructions']};seen={(x['physical_bank'],x['cpu_address'])for x in executed}
    helper_start=offset(0xB517);helper=rom[helper_start:offset(0xB536)]
    pins=['source/recovered/tactical_cooperation_controller.py','scripts/analyze_tactical_cooperation_controller.py','scripts/verify_tactical_cooperation_controller.py',
          'scripts/ui_structuring.py','scripts/analyze_battle_scene_controller.py']
    evidence=dict(schema='phase14-tactical-original-byte-provenance-v1',rom_sha256=SHA,entry=0xA000,body_entry=0xA02D,physical_pair=[8,9],
        trampoline=dict(cpu_address=0xA000,rom_offset=offset(0xA000),raw_hex='4c2da0'),
        original_instruction_count=len(scope),dynamic_original_body_positions=len(scope&seen),not_dynamically_executed=sorted(pc for bank,pc in scope-seen),
        sorted_original_instruction_bytes_sha256=hashlib.sha256(bytes.fromhex(''.join(x['raw_hex']for x in catalog['original_instructions']))).hexdigest(),
        independent_B517_protocol=dict(cpu_address=0xB517,end_exclusive=0xB536,rom_offset=helper_start,size=len(helper),raw_hex=helper.hex(),sha256=hashlib.sha256(helper).hexdigest(),
            observed_original_instruction_positions=sum(1 for bank,pc in seen if bank==8 and 0xB517<=pc<0xB536)),
        inline_tables=catalog['inline_tables'],external_calls=catalog['external_calls'],
        source_structure=dict(procedures=len(source_catalog['procedures']),structured_ifs=source_catalog['structured_ifs'],natural_loops=source_catalog['natural_loops'],
            source_generation=source_catalog['source_generation'],shared_tail_procedures='Named real acyclic joins avoid duplicate control paths; natural loops remain structured loops.'),
        control_fields=FIELDS,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in pins},
        validation=dict(path='analysis/phase14/tactical/validation.json',sha256=hashlib.sha256((OUT/'validation.json').read_bytes()).hexdigest(),
            status=v['status'],rom_cpu_case_count=v['rom_cpu_case_count'],complete_return_count=v['complete_return_count'],strict_prefix_count=v['strict_prefix_count'],
            source_guard_case_count=v['source_guard_case_count'],comparison=v['comparison']),
        production_source_original_CPU_callbacks=0,production_IR_interpretation=False,
        limits=['Static2213body bytes are pinned; remaining dynamic positions are individually listed and are not fullbranch coverage.',
            'Source block checkpoints are not originalCPU instruction counts.','OnlyF266 is an external software dependency; absent/nonreturnedhelper retains the real pending call.',
            'Strategy5/6 may change resources/HP before a coordinateproposal is consumed; secondaryB933 mutates low10troops. Controller is more than proposal-only.',
            'Downstream coordinate/APcommit, ordinaryattack, tacticpresentation and ambushmessage/experience consumers remain separate.'])
    (OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    (OUT/'README.md').write_text(f'''# 战术合作控制器：直接源码与真实调用协议

原main4入口8 A000 `4C 2D A0`跳至A02D，physical8/9。全部可达正文2213个原指令位置现离线按原ROM重建为160个具名Python函数、350个if、34个自然loop。生产只使用直接函数/条件/循环和独立byte/flag/stack算术，不读取旧phase7的program.json，不解释IR、opcode或PC指令字典，不执行原CPU。函数名是现代说明，8策略编号不宣称为正式游戏菜单名。

## 请求与字段

6F8B=FF立即返回；=1进入B933已有对侧埋伏缓存消费；其余raw byte进入演员扫描。6F94是原scan cursor；跳过6FA1[slot]=FF、异side或0664[slot]=FF，合格尝试增加6F96。策略返回6F8F=3才增加6F95并继续扫描，其他提案将request置FF交还调用方。扫描完计数不相等时重置94/95/96重扫，相等则status3、scan0、requestFF。计数保持u8回绕。

演员slot=6F8C；6F8D按status代表移动方向、攻击/计略编码或退却城市，6F8E为目标slot，6F8F状态由另一个战场消费者解释。普通计略ID与移动方向是不同编码。RNG使用6F92并把当时原X保存到6F93，保留拒绝抽样、废弃抽样及调用次序。

## 八策略与十六资格路由

| 策略 | 原入口 | 具名控制的优先次序 |
| ---: | --- | --- |
| 0 | A0B1 | 退却→特殊计略→side分支的基础计略/邻接攻击→抽样后移动或不行动 |
| 1 | A105 | 退却→特殊计略→对侧首槽邻接攻击→对侧首槽/原城市base坐标移动 |
| 2 | A166 | 退却→特殊计略→邻接攻击→actor半径2候选；无候选对侧首槽/base移动 |
| 3 | A210 | 退却→特殊计略→邻接攻击→本侧首槽半径2候选/友军情况→基础计略或靠近 |
| 4 | A2AD | 退却→特殊计略→邻接攻击→actor半径3候选；无候选基础计略/本侧首槽移动 |
| 5 | A329 | service0路线预测、标策略7、原资源word预算与补给写入 |
| 6 | A507 | service2路线预测、标策略7、资源扣50、原RNG/byte回绕治疗写入 |
| 7 | A606 | 直接提案status3 |

A09E只有8个合法B517索引；ACAB有16个计略资格索引。每个原inline word与其别名目标全部保留，表字节从原代码收集中剔除。B517真实协议保留scratch20..24、ASL/carry、原Y和弹栈，独立实现31字节原helper的作用。非法表外索引由source guard拒绝，原CPU不执行其表外字节。

基础/特殊候选排序、白名单、目标资格、两轴greedy移动、退却、raw16军队合计、24/16bit除法、24×8乘法、地图数据窗和费用读取均是本闭包的实际函数；已有[高层规则说明](../../phase8/strategies/README.md)可读对应玩法计算。新控制器另包含全部scratch、flags、局部JSR残余、callerRTS及F266真实mapper写入，补上旧高层API没有声明的CPU协议。F266使用主线程DE/E000数据窗。

该body除了提案也有真实副作用：策略5/6可能提前修改资源、HP和策略标志；B933消费至少由十面埋伏ID11建立的对侧缓存，扣low10兵并保留byte9高6位。原B965读取0614[group0/4]的quirk、discarded RNG与余下副作用保持。全部缓存producer没有由该名字链证明，Native输入也不等于新自然触发验证。实际坐标/APcommit、普通攻击、施放动画/结果与后续埋伏报告/经验仍由另外的原消费者执行，本body不清任何ready/IRQ/message等待。

## 原 CPU 矩阵与边界

正式{v['rom_cpu_case_count']}次原CPU比较：{v['complete_return_count']}完整RTS、{v['strict_prefix_count']}严格prefix、{v['source_guard_case_count']}source guards，0失败。prefix中448例只到B517所选策略/资格入口，2例为显式block预算暂停，1例为缺F266的真实call边界；这3组暂停后另外计完整续行对照。比较全部2048RAM（含完整inactive栈）、8192SRAM、AXYP/SP/PC、有序ports/banks；source侧原CPUcallback=0。

矩阵覆盖全部256requestbytes、八策略×两side×AP/位置条件、28功能入口、连续扫描、对侧缓存、补给/治疗资源边界、E22C真实caller、多种SP与B517全部256SP/24合法索引的组合。13个冻结phase7原机RAM/SRAM仅复用为同步CPU输入，没有增加Native帧或原机内部trace。静态2213正文位置，动态命中{len(scope&seen)}，其余{len(scope-seen)}位置明确列在evidence；静态完整收集不表示所有分支/值组合都动态验证。

```python
controller = TacticalCooperationController(memory, rom, services=actual_source_services)
result = controller.run_entry(0xA000, registers=actual_caller_registers)
# 有真实F266服务后恢复同一调用；预算暂停需显式正预算。
result = controller.resume(max_blocks=10000)
```

registers必须由调用方提供，返回PC/SP从其已有栈读取，无默认seed。`__call__(ServiceCall)`仅接受physical8/9与已恢复local入口。services必须明确返回status=returned并实际恢复callee PC/SP才继续。缺服务的resume、缺预算的resume保持原prefix；显式续预算不是游戏ack。max_blocks计源码control checkpoints，不计原CPU指令。

```sh
.venv-trace/bin/python scripts/analyze_tactical_cooperation_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/verify_tactical_cooperation_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes'
.venv-trace/bin/python scripts/analyze_tactical_cooperation_controller.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only
```

[新源码](../../../source/recovered/tactical_cooperation_controller.py) · [回执](validation.json) · [原字节/依赖/位置](evidence.json) · [原汇编](original-ranges.asm) · [离线原ROM目录](static-catalog.json) · [具名源码结构](source-catalog.json)
''')
    print(json.dumps(dict(status='evidence_written',source_sha256=evidence['source_sha256'][pins[0]],dynamic=len(scope&seen),unexecuted=len(scope-seen))))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--catalog-only',action='store_true');p.add_argument('--evidence-only',action='store_true');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    if a.evidence_only:write_evidence(rom);return
    I,tables=collect(rom);OUT.mkdir(parents=True,exist_ok=True)
    catalog=dict(rom_sha256=SHA,entry=0xA000,original_instruction_count=len(I),original_instructions=[I[x]for x in sorted(I)],inline_tables=tables,
        external_calls=[I[x]for x in sorted(I)if I[x].get('hook')])
    (OUT/'static-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    lines=[]
    for pc,x in sorted(I.items()):
        _,asm=instruction(rom,x['rom_offset'],pc);lines.append(f'b08:{pc:04X} file{x["rom_offset"]:06X} {x["raw_hex"]:<7s} {asm}')
        if pc in TABLES:
            t=next(t for t in tables if t['call_pc']==pc)
            lines.extend(f'b08:{t["table_cpu"]+2*i:04X} file{t["rom_offset"]+2*i:06X} .word ${v:04X} ; {t["name"]}{i}'for i,v in enumerate(t['targets']))
    pc=0xB517
    while pc<0xB536:
        f=offset(pc);op,mode=OPS[rom[f]];size=SIZES[mode];_,asm=instruction(rom,f,pc)
        lines.append(f'b08:{pc:04X} file{f:06X} {rom[f:f+size].hex():<7s} {asm} ; independent B517 protocol');pc+=size
    assert pc==0xB536;(OUT/'original-ranges.asm').write_text('\n'.join(lines)+'\n')
    if a.catalog_only:print(json.dumps(dict(instructions=len(I),external=sorted({x['operand']for x in I.values()if x.get('hook')}))));return
    b=TacticalStructurer.__new__(TacticalStructurer);b.I=I;b.catalog={'states':[]}
    b.roots={0xA000,0xA02D}|{x['operand']for x in I.values()if x['op']=='JSR'and not x.get('hook')}
    b.roots.update(v for x in I.values()if x['op']=='DISPATCH'for v in x['targets']);b.roots.update(v for v in NAMES if v in I)
    # Shared acyclic tails with an early RTS defeat postdominator sharing.
    # Turn these real join blocks into direct named tail procedures instead
    # of duplicating every path. Keep all natural-loop members together.
    joined=set()
    for entry in tuple(b.roots):
        G=b.graph(entry);_,loops=b.dominators(G,entry);loop_members=set().union(*loops.values())if loops else set()
        predecessors={pc:set()for pc in G}
        for pc,targets in G.items():
            for target in targets:predecessors[target].add(pc)
        joined.update(pc for pc,pred in predecessors.items()if len(pred)>1 and pc not in loop_members)
    b.roots.update(joined)
    b.names={v:NAMES.get(v,f'tactical_helper_{v:04x}')for v in b.roots}
    predicate_aliases=defaultdict(list)
    for index,target in enumerate(tables[1]['targets']):predicate_aliases[target].append(index)
    for target,aliases in predicate_aliases.items():b.names[target]='predicate_tactics_'+'_'.join(f'{i:02d}'for i in aliases)
    b.stats=[];b.loop_count=b.if_count=0
    prefix=HEADER[:HEADER.index('    def _mark(self,pc):')]
    prefix=prefix.replace('BattleSceneController','TacticalCooperationController').replace('BattleRegisters','TacticalRegisters').replace('bank12/13 battle scene controller','bank8/9 tactical cooperation controller')
    prefix=prefix.replace('Pinned battle ROM required','Pinned tactical ROM required').replace('pc:int=0xA028','pc:int=0xA000')
    lo=prefix.index('STATE,PHASE,');hi=prefix.index('@dataclass')
    control=tuple((name.lower(),address)for address,name in FIELDS.items())
    prefix=prefix[:lo]+''.join(f'{name}=0x{address:X}\n'for address,name in FIELDS.items())+'CONTROL_FIELDS='+repr(control)+'\n\n'+prefix[hi:]
    prefix=prefix.replace('self._blocks=0;self._limit=200000','self._blocks=0;self._limit=200000;self._call_owner=None')
    source=prefix+TAIL+'    LOCAL_ENTRIES='+repr(tuple(sorted(b.roots)))+'\n    def _entry(self,entry):\n'
    for index,entry in enumerate(sorted(b.roots)):source+=f'        {"if"if index==0 else"elif"} entry==0x{entry:04X}:return self.{b.names[entry]}()\n'
    source+='        raise ValueError("Entry outside original tactical closure")\n\n'
    for entry in sorted(b.roots):
        try:body=b.procedure(entry)
        except Exception as exc:raise ValueError(f'Tactical procedure ${entry:04X}: {exc}')from exc
        body=re.sub(r'self\._mark\(([^\n;]+)\)',r'yield from self._checkpoint(\1)',body)
        source+=body
    source=source.replace('from dataclasses import dataclass',loop_exception_source(b.stats)+'from dataclasses import dataclass')
    ast.parse(source);SOURCE.write_text(source)
    (OUT/'source-catalog.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(source.encode()).hexdigest(),procedures=b.stats,
        structured_ifs=b.if_count,natural_loops=b.loop_count,source_generation='RawROM CFG only; oldphase7 program.json not read'),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(instructions=len(I),procedures=len(b.roots),source_bytes=len(source.encode()),ifs=b.if_count,loops=b.loop_count)))
if __name__=='__main__':main()
