#!/usr/bin/env python3
"""Offline CFG structuring of the pinned battle controller into Python source.

The old lifted graph is an analysis input only. The generated production file
has direct named calls, if statements and natural loops, never an IR executor.
"""
from pathlib import Path
import argparse, ast, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase11/battle'
SOURCE=ROOT/'source/recovered/battle_scene_controller.py'
BRANCHES={'BCC':'not r.p&C','BCS':'r.p&C','BEQ':'r.p&Z','BNE':'not r.p&Z',
          'BMI':'r.p&N','BPL':'not r.p&N','BVC':'not r.p&V','BVS':'r.p&V'}
MAIN_NAMES=('unit_selection','unit_information','attack_target','attack_confirmation',
 'movement','tactics','withdrawal','wait_action','computer_action','village_service',
 'next_side','duel_result','battle_result','defeated_roster','victor_roster','return_to_city')
PHASE_NAMES=(
 ('choose_actor_control','await_cursor_refresh','select_unit','action_menu','confirm_action_menu'),
 ('open_unit_information','navigate_unit_information','close_unit_information'),
 ('request_attack_target','choose_adjacent_target','acknowledge_attack_target','launch_attack_scene'),
 ('request_attack_target','choose_adjacent_target','acknowledge_attack_target','launch_attack_scene'),
 ('request_move_target','advance_move_cursor','check_destination_event','request_ambush_scan',
  'consume_ambush_result','acknowledge_ambush_damage','acknowledge_move_result'),
 ('initialize_tactic_list','build_tactic_list','request_tactic_menu','select_tactic','choose_tactic_target',
  'confirm_tactic','wait_animation_apply_tactic','scan_tactic_result','acknowledge_tactic_result',
  'acknowledge_upgrade_notice','acknowledge_invalid_target'),
 ('request_retreat','select_retreat_answer','open_retreat_destination','select_retreat_destination',
  'commit_retreat','acknowledge_retreat'),
 ('request_wait_action','confirm_wait_action','prepare_side_notice','acknowledge_side_notice',
  'refresh_units_for_side','inspect_strategy_notice','acknowledge_strategy_notice','wait_text_then_change_side'),
 ('request_AI_scan','await_AI_proposal','route_AI_proposal','prepare_AI_movement','commit_AI_movement',
  'prepare_AI_attack','show_AI_attack_target','launch_AI_attack','prepare_AI_tactic','show_AI_tactic_notice',
  'apply_AI_tactic','show_AI_tactic_actor','finish_AI_side','prepare_AI_withdrawal','show_AI_withdrawal',
  'confirm_AI_withdrawal','return_from_AI'),
 ('village_service',),
 ('prepare_next_side','prepare_first_side_control','prepare_second_side_control','enter_unit_selection',
  'acknowledge_next_side_notice','scan_next_officer','draw_next_officer_notice'),
 ('prepare_first_duel_result','prepare_second_duel_result','finish_duel_result','acknowledge_duel_upgrade'),
 ('prepare_result_summary','await_result_text','prepare_result_panel','confirm_result_panel',
  'select_result_resolution','acknowledge_result_exit'),
 ('prepare_defeated_roster','select_defeated_roster_destination','open_defeated_roster_selection',
  'choose_defeated_roster_officer','exclude_defeated_roster_officer','prepare_defeated_roster_confirmation',
  'confirm_defeated_roster_transfer'),
 ('prepare_victor_roster','select_victor_roster_destination','open_victor_roster_selection',
  'choose_victor_roster_officer','exclude_victor_roster_officer','prepare_victor_roster_confirmation',
  'confirm_victor_roster_transfer'),
 ('return_to_city',)*4)
HELPER_NAMES={0xA1DE:'blink_command_cursor',0xA1F7:'return_command_cursor',0xA368:'orthogonal_attack_target',
 0xA3D2:'prepare_attack_parameters',0xA433:'save_attack_attributes',0xB02B:'apply_tactic',
 0xB5D8:'health_loss',0xB68B:'troop_loss',0xBDC0:'finish_side_turn',0xD5EE:'cursor_input',
 0xD4FB:'direction_repeat',0xD68A:'unit_at_cursor',0xDC4B:'target_side_filter',
 0xDD72:'commander_outcome',0xCAF8:'prepare_postbattle_summary',0xCA51:'result_yes_flag',
 0xC620:'round_resource_update',0xCC29:'draw_postbattle_units',0xD0E1:'postbattle_roster',
 0xD48D:'remove_postbattle_officer',0xD6CC:'map_refresh',0xD657:'battle_cursor',
 0xDC63:'dialog_highlight',0xDC70:'alternate_highlight',0xDF27:'text_readiness',
 0xDB03:'refresh_hundred_troops',0xDB46:'terrain_at_position',0xDB50:'raw_terrain_at_position',
 0xE850:'random_four',0xE856:'random_eight',0xE862:'random_bounded',0xEA7C:'divide_word',
 0xEAA5:'divide_24bit',0xEBE9:'multiply_24bit',0xF2AF:'city_pointer',0xF368:'ruler_pointer',
 0xA000:'scene_entry',0xA003:'battle_initialize_entry',0xA006:'duel_outcome_entry',0xA009:'scene_tick',
 0xDC99:'initialize_battle_arrays',0xC766:'apply_duel_outcomes',0xC75B:'find_duel_officer_slot',
 0xC782:'dispatch_duel_outcome',0xC799:'remove_duel_defeated_unit',0xC7DB:'collect_duel_captive',
 0xDF39:'select_battle_IRQ_layout',0xDF88:'adjust_battle_IRQ_delay'}
FIELD_NAMES={0x500:'STATE',0x501:'PHASE',0x502:'COMMAND',0x504:'SIDE',0x505:'AP',
 0x506:'ROUND',0x507:'RULERS',0x509:'SELECTED_SLOT',0x50A:'ACTOR_SLOT',0x50E:'CITY',
 0x50F:'CONTROLLER',0x543:'TACTIC',0x544:'TACTIC_FAILED',0x4C8:'ANIMATION',
 0x81:'NEW_BUTTONS',0x87:'REPEAT_BUTTONS',0x7A:'GLOBAL',0x78:'NMI_SCENE',0x7E:'PPU_JOBS'}

# Hand-written structured control for the first cooperative phase. This is a
# battle selection tick, not the global scene/army initializer.
MANUAL_PROCEDURES={0xA05E:'''    def choose_actor_control(self):
        """A05E: inspect commander outcome, AP and real text readiness.

        Controller3 enters the computer proposal path only with positive AP.
        Human control waits for text and then enters unit selection. Exhausted
        or signed-negative AP tail-calls the original side-change procedure.
        """
        r=self.registers;m=self.memory;self._mark(0xA05E)
        if not (yield from self._local_call(self.commander_outcome,0xA05E,0xA061)):return
        self._a(m[CONTROLLER]);self._compare(r.a,3)
        if r.p&Z:
            self._a(m[AP])
            if r.p&(Z|N):return (yield from self.finish_side_turn())
            self._a(8);m[STATE]=r.a
            self._a(0);m[PHASE]=r.a
            self._rts();return
        if not (yield from self._local_call(self.text_readiness,0xA07A,0xA07D)):return
        if not r.p&C:self._rts();return
        self._a(m[AP])
        if r.p&(Z|N):return (yield from self.finish_side_turn())
        m[PHASE]=self._nz(m[PHASE]+1)
        self._rts()

'''}

HEADER='''"""Readable, bounded bank12/13 battle scene controller.

Offline control-flow structuring produced named procedures and phase handlers.
Production reads immutable game data, never opcodes, control IR or PC->operation
tables. Services retain their real caller stack and explicit pending boundary.
CPU-register form is retained where flags/scratch/aliasing are observable.
"""
from dataclasses import dataclass
import hashlib
from .battle_nmi_services import ServiceCall, ServiceWait
from .mapped_memory import UnsupportedHardware

ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
C,Z,I,D,B,U,V,N=1,2,4,8,16,32,64,128
STATE,PHASE,COMMAND,SIDE,AP=0x500,0x501,0x502,0x504,0x505
ROUND,RULERS,SELECTED_SLOT,ACTOR_SLOT,CITY,CONTROLLER=0x506,0x507,0x509,0x50A,0x50E,0x50F
TACTIC,TACTIC_FAILED,ANIMATION=0x543,0x544,0x4C8
NEW_BUTTONS,REPEAT_BUTTONS,GLOBAL,NMI_SCENE,PPU_JOBS=0x81,0x87,0x7A,0x78,0x7E

@dataclass
class BattleRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA028

class BattleSceneController:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned battle ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=BattleRegisters();self.events=[];self.pending=None;self._program=None
        self._blocks=0;self._limit=200000
    def _nz(self,value):
        value&=255;self.registers.p=(self.registers.p&~(N|Z))|(N if value&128 else 0)|(Z if value==0 else 0)
        return value
    def _a(self,value):self.registers.a=self._nz(value)
    def _x(self,value):self.registers.x=self._nz(value)
    def _y(self,value):self.registers.y=self._nz(value)
    def _flag(self,bit,value):self.registers.p=(self.registers.p&~bit)|(bit if value else 0)
    def _compare(self,left,right):self._flag(C,left>=right);self._nz(left-right)
    def _add(self,value,subtract=False):
        r=self.registers;old=r.a;carry=bool(r.p&C)
        total=old-value-(1-carry)if subtract else old+value+carry
        self._flag(C,total>=0 if subtract else total>255)
        self._flag(V, bool(((old^value)&(old^total)&128)if subtract else (~(old^value)&(old^total)&128)))
        self._a(total)
    def _shift(self,value,left,rotate=False):
        carry=bool(self.registers.p&C);self._flag(C,value&128 if left else value&1)
        return self._nz(((value<<1)|(carry if rotate else 0))if left else ((value>>1)|(128 if rotate and carry else 0)))
    def _push(self,value):
        r=self.registers;self.memory[0x100+r.sp]=value&255;r.sp=(r.sp-1)&255
    def _pop(self):
        r=self.registers;r.sp=(r.sp+1)&255;return self.memory[0x100+r.sp]
    def _rts(self):self.registers.pc=((self._pop()|self._pop()<<8)+1)&65535
    def _local_call(self,method,pc,return_pc):
        self._push((pc+2)>>8);self._push(pc+2)
        yield from method()
        return self.registers.pc==return_pc
    def _mark(self,pc):
        self.registers.pc=pc;self._blocks+=1
        if self._blocks>self._limit:raise RuntimeError('Source control-block budget reached')
    def _dispatch(self,pc,targets):
        r=self.registers;m=self.memory;index=r.a
        if index>=len(targets):raise ValueError(f'Original bounded dispatch index {index} at ${pc:04X}')
        self._push((pc+2)>>8);self._push(pc+2)
        original_y=r.y;m[0]=original_y;base=self._pop()|self._pop()<<8
        m[1],m[2]=base&255,base>>8;target=targets[index];m[3],m[4]=target&255,target>>8
        r.a=target>>8;r.y=original_y;r.pc=target
        r.p=(r.p&~(C|N|Z))|(C if index&128 else 0)|(N if original_y&128 else 0)|(Z if original_y==0 else 0)
        return index
    def _external(self,pc,target,return_pc,kind,inline_target=None):
        r=self.registers;caller_sp=r.sp
        if kind!='tail':self._push((pc+2)>>8);self._push(pc+2)
        else:caller_sp=(r.sp+2)&255
        r.pc=target
        if return_pc is None:return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535
        event=dict(call_pc=pc,target=target,return_pc=return_pc,kind=kind,inline_target=inline_target)
        self.events.append(event)
        yield ServiceCall(target,return_pc,kind,r,self.memory,tuple(getattr(self.memory,'banks',())),caller_sp)
    def _drive(self):
        while True:
            if self.pending is not None:
                call=self.pending
                if self.services is None:return self._result('dependency')
                result=self.services(call)
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc:return self._result('nonlocal_return')
                return self._result('returned')
    def _result(self,status):
        return dict(status=status,before=self._before,after=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT]),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self):
        if self._program is None:raise RuntimeError('No pending battle invocation')
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)
    def run_entry(self,entry=0xA028,*,registers=None,seed_return=False,return_pc=0x0200,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing battle invocation first')
        self.registers=registers or BattleRegisters();r=self.registers
        if r.p&D:raise ValueError('NES binary arithmetic requires D=0')
        if seed_return:
            if return_pc!=0x0200:raise ValueError('Synthetic fixture return only permits0200')
            self.memory[0x1FE:0x200]=bytes((255,1));r.sp=0xFD
        self._return_pc=return_pc;self._before=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT])
        self.events=[];self.pending=None;self._blocks=0;self._limit=max_blocks;r.pc=entry
        self._program=self._entry(entry)
        return self._drive()

'''

def successors(x):
    if x['op']=='RTS' or x['op']=='DISPATCH':return []
    if x['op']=='JMP':return []if x.get('hook')else[x['operand']]
    if x['op']in BRANCHES:return [x['operand'],x['next_pc']]
    return [x['next_pc']]

class Structurer:
    def __init__(self,instructions,catalog):
        self.I={x['pc']:x for x in instructions};self.catalog=catalog
        self.roots={x['operand']for x in instructions if x['op']=='JSR'and not x.get('hook')}
        self.roots.add(0xA028)
        for x in instructions:
            if x['op']=='DISPATCH':self.roots.update(x['targets'])
        self.roots.update(e for e in HELPER_NAMES if e in self.I)
        self.names={e:HELPER_NAMES.get(e,f'local_{e:04x}')for e in self.roots}
        self.names[0xA028]='battle_tick'
        for state in catalog['states']:
            self.names[state['entry_cpu']]=MAIN_NAMES[state['state']]
            for sub in state['substates']:
                e=sub['entry_cpu']
                if e in self.roots and e!=state['entry_cpu']:
                    self.names[e]=PHASE_NAMES[state['state']][sub['substate']]
        self.stats=[];self.loop_count=0;self.if_count=0
    def graph(self,entry):
        G={};todo=[entry]
        while todo:
            pc=todo.pop()
            if pc in G:continue
            if pc in self.roots and pc!=entry:G[pc]=[];continue
            if pc not in self.I:raise ValueError(f'Unclassified destination {pc:04X}')
            G[pc]=successors(self.I[pc]);todo.extend(G[pc])
        return G
    @staticmethod
    def dominators(G,entry):
        nodes=set(G);pred={v:set()for v in G}
        for a,bs in G.items():
            for b in bs:pred[b].add(a)
        dom={v:({entry}if v==entry else set(nodes))for v in G}
        while True:
            old={v:set(d)for v,d in dom.items()}
            for v in nodes-{entry}:dom[v]={v}|set.intersection(*(dom[p]for p in pred[v]))
            if dom==old:break
        loops={}
        for a,bs in G.items():
            for b in bs:
                if b not in dom[a]:continue
                loop={a,b};todo=[a]if a!=b else[]
                while todo:
                    n=todo.pop()
                    for p in pred[n]:
                        if p not in loop:loop.add(p);todo.append(p)
                loops.setdefault(b,set()).update(loop)
        return dom,loops
    @staticmethod
    def postdominators(G):
        exit=-1;nodes=set(G)|{exit};S={v:(bs or[exit])for v,bs in G.items()};S[exit]=[]
        post={v:({exit}if v==exit else set(nodes))for v in nodes}
        while True:
            old={v:set(d)for v,d in post.items()}
            for v in G:post[v]={v}|set.intersection(*(post[b]for b in S[v]))
            if old==post:break
        immediate={}
        for v in G:
            choices=post[v]-{v,exit}
            immediate[v]=max(choices,key=lambda n:len(post[n]))if choices else None
        return immediate
    def addr(self,x):
        n=x['operand'];base=FIELD_NAMES.get(n,f'0x{n:04X}');mode=x['mode']
        if mode in('abs','zpg'):return base
        if mode in('abx','aby'):return f'({base}+r.{"x"if mode=="abx"else"y"})&65535'
        if mode=='iny':return f'((m[0x{n:02X}]|m[0x{(n+1)&255:02X}]<<8)+r.y)&65535'
        raise ValueError(mode)
    def operand(self,x):return f'0x{x["operand"]:02X}'if x['mode']=='imm'else f'm[{self.addr(x)}]'
    def simple(self,x):
        op=x['op'];val=self.operand(x)if x['mode']not in('imp','acc')else None
        if op in('LDA','LDX','LDY'):return [f'self._{op[-1].lower()}({val})']
        if op in('STA','STX','STY'):return [f'm[{self.addr(x)}]=r.{op[-1].lower()}']
        if op in('AND','ORA','EOR'):return [f'self._a(r.a { {"AND":"&","ORA":"|","EOR":"^"}[op]} {val})']
        if op in('CMP','CPX','CPY'):return[f'self._compare(r.{"a"if op=="CMP"else op[-1].lower()},{val})']
        if op in('ADC','SBC'):return[f'self._add({val}{",subtract=True"if op=="SBC"else""})']
        if op in('CLC','SEC'):return[f'self._flag(C,{op=="SEC"})']
        if op in('INC','DEC'):return[f'm[{self.addr(x)}]=self._nz({val}{"+1"if op=="INC"else"-1"})']
        if op in('INX','INY','DEX','DEY'):return[f'self._{op[-1].lower()}(r.{op[-1].lower()}{"+1"if op.startswith("IN")else"-1"})']
        if op in('TAX','TAY','TXA','TYA'):return[f'self._{op[2].lower()}(r.{op[1].lower()})']
        if op in('LSR','ASL','ROL','ROR'):
            expr=f'self._shift({"r.a"if x["mode"]=="acc"else val},{op in("ASL","ROL")},rotate={op in("ROL","ROR")})'
            return [f'r.a={expr}']if x['mode']=='acc'else[f'm[{self.addr(x)}]={expr}']
        if op=='PHA':return['self._push(r.a)']
        if op=='PLA':return['self._a(self._pop())']
        raise ValueError((op,x['pc']))
    def procedure(self,entry):
        G=self.graph(entry);dom,loops=self.dominators(G,entry);join=self.postdominators(G)
        if entry in MANUAL_PROCEDURES:
            self.stats.append(dict(entry=entry,name=self.names[entry],instruction_nodes=len(G),
              source_lines=len(MANUAL_PROCEDURES[entry].splitlines()),natural_loop_headers=sorted(loops),
              hand_written_structured_control=True))
            return MANUAL_PROCEDURES[entry]
        lines=[f'    def {self.names[entry]}(self):',f'        """${entry:04X}: {self.names[entry].replace("_"," ")}; retains flags/aliases/caller stack."""','        r=self.registers;m=self.memory']
        def put(indent,text):lines.append('    '*indent+text)
        def emit(start,stop,indent,active=(),path=()):
            pc=start
            while pc is not None:
                if pc==stop:return True
                if pc in active:
                    if pc!=active[-1]:raise ValueError(f'Outer loop transfer {entry:04X}:{pc:04X}')
                    put(indent,'continue');return False
                if pc in path:raise ValueError(f'Irreducible cycle {entry:04X}:{pc:04X}')
                if pc in loops:
                    lp=loops[pc];after=join[pc]
                    if after in lp:after=None
                    self.loop_count+=1;put(indent,f'while True:  # natural loop ${pc:04X}')
                    # On its first visit the loop header itself is not a backedge.
                    falls=emit_body(pc,after,indent+1,active+(pc,),path,first=True)
                    if falls:put(indent+1,'break')
                    if after is None:return False
                    pc=after;continue
                return emit_body(pc,stop,indent,active,path)
            return False
        def emit_body(pc,stop,indent,active,path,first=False):
            while pc is not None:
                if pc==stop:return True
                if pc in active and not first:
                    if pc!=active[-1]:raise ValueError(f'Outer loop transfer {entry:04X}:{pc:04X}')
                    put(indent,'continue');return False
                if pc in path:raise ValueError(f'Irreducible cycle {entry:04X}:{pc:04X}')
                if pc in loops and not first:return emit(pc,stop,indent,active,path)
                first=False;path=path+(pc,)
                if pc in self.roots and pc!=entry:
                    put(indent,f'return (yield from self.{self.names[pc]}())');return False
                x=self.I[pc];op=x['op']
                if pc==entry or len(G[pc])!=1:put(indent,f'self._mark(0x{pc:04X})')
                if op=='RTS':put(indent,'self._rts();return');return False
                if op=='DISPATCH':
                    targets=x['targets'];put(indent,f'index=self._dispatch(0x{pc:04X},{tuple(targets)})')
                    methods=','.join('self.'+self.names[t]for t in targets)
                    put(indent,f'return (yield from ({methods},)[index]())');return False
                if op in BRANCHES:
                    self.if_count+=1;end=join[pc]
                    if end is not None and end in path and end not in active:end=None
                    if stop is not None and end is not None and stop in dom.get(end,set()):end=stop
                    put(indent,f'if {BRANCHES[op]}:')
                    yes=emit(x['operand'],end,indent+1,active,path)
                    if yes:put(indent+1,'pass')
                    put(indent,'else:')
                    no=emit(x['next_pc'],end,indent+1,active,path)
                    if no:put(indent+1,'pass')
                    if yes or no:
                        if end==stop:return True
                        pc=end;continue
                    return False
                if op=='JMP':
                    if x.get('hook'):
                        put(indent,f'yield from self._external(0x{pc:04X},0x{x["operand"]:04X},None,"tail")');put(indent,'return');return False
                    pc=x['operand'];continue
                if op in('JSR','FARCALL'):
                    target=x['operand'];nxt=x['next_pc']
                    if op=='FARCALL'or x.get('hook'):
                        put(indent,f'yield from self._external(0x{pc:04X},0x{target:04X},0x{nxt:04X},"{ "far_call"if op=="FARCALL"else"call"}",{x.get("inline_target")})')
                    else:
                        put(indent,f'if not (yield from self._local_call(self.{self.names[target]},0x{pc:04X},0x{nxt:04X})):return')
                    if op=='FARCALL'or x.get('hook'):
                        put(indent,f'if r.pc!=0x{nxt:04X}:return  # preserve nonlocal stack return')
                    pc=nxt;continue
                for line in self.simple(x):put(indent,line)
                pc=x['next_pc']
            return False
        emit(entry,None,2)
        # Make even zero-callback bodies generators without introducing a fake event.
        lines.insert(3,'        if False:yield None')
        self.stats.append(dict(entry=entry,name=self.names[entry],instruction_nodes=len(G),source_lines=len(lines),natural_loop_headers=sorted(loops)))
        return '\n'.join(lines)+'\n\n'
    def source(self):
        text=HEADER+'    def _entry(self,entry):\n'
        for i,e in enumerate(sorted(self.roots)):
            text+=f'        {"if"if i==0 else"elif"} entry==0x{e:04X}:return self.{self.names[e]}()\n'
        text+='        raise ValueError("Entry is outside the proven battle procedure catalog")\n\n'
        for entry in sorted(self.roots):text+=self.procedure(entry)
        # States2 and3 deliberately share the same original A293 body/table.
        text+='    def attack_target(self):\n        """Main2 alias of original shared main2/3 A293 controller."""\n        return (yield from self.attack_confirmation())\n'
        return text

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    old=ROOT/'analysis/battle_fsm/program.json';program=json.loads(old.read_text())
    catalog=json.loads((ROOT/'analysis/battle_fsm/state-catalog.json').read_text())
    # The earlier A028-rooted closure omitted the real NMI3 A000 wrapper.
    # Decode this small bounded supplement directly from the immutable ROM;
    # neither the old lifted file nor any earlier receipt is rewritten.
    from inspect_game_data import OPS,SIZES
    known={x['pc']:x for x in program['instructions']};todo=[0xA000,0xA003,0xA006,0xA009,0xDF39,0xDF88]
    supplemented=[]
    modes={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp','rel':'rel'}
    while todo:
        pc=todo.pop()
        if pc in known:continue
        assert 0xA000<=pc<0xE000,hex(pc)
        bank=12+int(pc>=0xC000);file=16+bank*8192+(pc&8191)
        op,mode=OPS[rom[file]];size=SIZES[mode];assert op!='?',hex(pc)
        operand=int.from_bytes(rom[file+1:file+size],'little');next_pc=pc+size
        if op in BRANCHES:operand=(next_pc+(operand if operand<128 else operand-256))&65535
        item=dict(pc=pc,bank=bank,file=file,op=op,mode=modes.get(mode,mode),operand=operand,next_pc=next_pc)
        if op=='JSR'and operand==0xEADE and next_pc==0xC787:
            targets=[int.from_bytes(rom[file+3+2*i:file+5+2*i],'little')for i in range(8)]
            item.update(op='DISPATCH',targets=targets);todo.extend(targets)
        elif op=='JSR'and operand==0xEE07:
            item.update(op='FARCALL',inline_target=int.from_bytes(rom[file+3:file+5],'little'),next_pc=pc+5,hook='explicit far dependency')
        elif op in('JSR','JMP')and operand>=0xE000:item['hook']='explicit shared service'
        if op=='JSR'and 0xA000<=operand<0xE000:todo.append(operand)
        todo.extend(successors(item));known[pc]=item;supplemented.append(item)
    program['instructions']=list(known.values())
    for x in program['instructions']:
        bank=x['bank'];file=16+bank*8192+(x['pc']&8191)
        assert file==x['file']
        # The lifted payload has no raw bytes; decode the opcode only offline.
        sys.path.insert(0,str(ROOT/'scripts'));from inspect_game_data import OPS,SIZES
        op,mode=OPS[rom[file]]
        assert op==( 'JSR'if x['op']in('DISPATCH','FARCALL')else x['op'])
        size=SIZES[mode];value=int.from_bytes(rom[file+1:file+size],'little')
        if x['op']in BRANCHES:value=(x['pc']+2+(value if value<128 else value-256))&65535
        if x['op']!='DISPATCH':assert value==x['operand'],x
        if x['op']=='FARCALL':assert int.from_bytes(rom[file+3:file+5],'little')==x['inline_target']
        if x['op']=='DISPATCH':
            assert [int.from_bytes(rom[file+3+2*i:file+5+2*i],'little')for i in range(len(x['targets']))]==x['targets']
    builder=Structurer(program['instructions'],catalog);source=builder.source();tree=ast.parse(source)
    SOURCE.write_text(source);OUT.mkdir(parents=True,exist_ok=True)
    for state in catalog['states']:
        state['recovered_function']=MAIN_NAMES[state['state']]
        for phase in state['substates']:phase['recovered_function']=builder.names[phase['entry_cpu']]
    externals=[dict(call_pc=x['pc'],target=x['operand'],kind='far_call'if x['op']=='FARCALL'else'tail'if x['op']=='JMP'else'call',
        inline_target=x.get('inline_target'))for x in program['instructions']if x.get('hook')]
    artifact=dict(rom_sha256=SHA,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      offline_graph_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),procedures=builder.stats,
      structured_if_count=builder.if_count,natural_loop_count=builder.loop_count,
      original_instruction_nodes=len(program['instructions']),wrapper_supplement=supplemented,
      states=catalog['states'],external_services=externals)
    (OUT/'catalog.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n')
    pins=['source/recovered/battle_scene_controller.py','scripts/analyze_battle_scene_controller.py',
          'scripts/verify_battle_scene_controller.py','source/recovered/battle_nmi_services.py',
          'source/recovered/mapped_memory.py','analysis/battle_fsm/program.json','analysis/battle_fsm/state-catalog.json']
    ranges=[];listing=[]
    for x in sorted(program['instructions'],key=lambda x:x['pc']):
        file=x['file'];op,mode=OPS[rom[file]];size=5 if x['op']=='FARCALL'else SIZES[mode]
        if x['op']=='DISPATCH':size+=2*len(x['targets'])
        raw=rom[file:file+size]
        ranges.append(dict(physical_bank=x['bank'],cpu=x['pc'],rom_offset=file,byte_count=size,raw_hex=raw.hex(' '),
                          offline_operation=x['op']))
        listing.append(f'{file:06X} b{x["bank"]:02d}:${x["pc"]:04X} {raw.hex(" ")} ; {x["op"]}')
    evidence=dict(rom_sha256=SHA,source_kind='offline structured Python functions, not runtime IR',
      source_uses_original_CPU=False,source_uses_control_IR=False,original_instructions=ranges,
      main_state_count=16,legacy_main_phase_combinations=101,main_phase_scope='98 local-expanded legacy combinations plus3 extra bank8 aliases; main9 and main15 retain genuine cross-bank services',
      additional_duel_outcome_table=dict(cpu=0xC787,physical_bank=13,rom_offset=16+13*8192+0x787,count=8),
      actual_NMI_entry=0xA000,public_initialize_entry=0xA003,public_duel_result_entry=0xA006,
      local_dispatch_entry=0xA028,procedure_count=len(builder.stats),
      natural_loop_count=builder.loop_count,structured_if_count=builder.if_count,
      runtime_imports=[ast.unparse(x)for x in tree.body if isinstance(x,(ast.Import,ast.ImportFrom))],
      dependency_pins=[dict(path=f,sha256=hashlib.sha256((ROOT/f).read_bytes()).hexdigest())for f in pins])
    (OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    (OUT/'original-instructions.asm').write_text('\n'.join(listing)+'\n')
    audit=dict(status='passed',runtime_IR_loading=False,runtime_original_CPU_execution=False,runtime_PC_dictionary=False,
      one_time_entry_selection=True,method_count=sum(isinstance(x,ast.FunctionDef)for x in ast.walk(tree)),
      Python_if_count=sum(isinstance(x,ast.If)for x in ast.walk(tree)),Python_while_count=sum(isinstance(x,ast.While)for x in ast.walk(tree)),
      hand_written_structured_procedures=list(MANUAL_PROCEDURES),source_sha256=evidence['dependency_pins'][0]['sha256'])
    forbidden={'BattleStateMachine','ControlHelpers','MPU','RuntimeServices','json'}
    assert not any(isinstance(x,ast.Name)and x.id in forbidden for x in ast.walk(tree))
    assert not any(isinstance(x,ast.Call)and isinstance(x.func,ast.Name)and x.func.id in('eval','exec','open')for x in ast.walk(tree))
    (OUT/'static-validation.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({k:v for k,v in artifact.items()if k not in('procedures','states','external_services','wrapper_supplement')}))
if __name__=='__main__':main()
