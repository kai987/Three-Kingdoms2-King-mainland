#!/usr/bin/env python3
"""Offline CFG structuring of the pinned normal-attack controller into Python source.

The old lifted graph is an analysis input only. The generated production file
has direct named calls, if statements and natural loops, never an IR executor.
"""
from pathlib import Path
import argparse, ast, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1]
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase11/attack'
SOURCE=ROOT/'source/recovered/attack_scene_controller.py'
BRANCHES={'BCC':'not r.p&C','BCS':'r.p&C','BEQ':'r.p&Z','BNE':'not r.p&Z',
          'BMI':'r.p&N','BPL':'not r.p&N','BVC':'not r.p&V','BVS':'r.p&V'}
MAIN_NAMES=('setup_and_information','formation_action_round','object_action','participant_menu',
 'result_confirmation','duel_handoff','first_formation','second_formation',
 'intelligence_action','object_animation','duel_selection')
HELPER_NAMES={
 0xA000:'attack_scene_tick',0xA00F:'scene_service_wrapper',0xA030:'participant_cards_then_control',
 0xA2A9:'check_round_participant_request',0xA32F:'scan_participant_object',0xA39D:'prepare_selected_object_side',
 0xA4D8:'selected_participant_health',0xA4E6:'mark_participant_withdrawal',0xA6D0:'set_object_result_phase',
 0xA7C5:'move_active_object',0xA7FE:'choose_object_destination',0xA84D:'resolve_object_collision',
 0xA871:'resolve_object_health_change',0xA8CF:'read_object_pair',0xA8F2:'read_object_parameters',
 0xA9A0:'commit_object_pair_health',0xA9BD:'test_selected_object_health',0xA9E6:'write_object_map_pair',
 0xAA0F:'queue_object_redraw',0xABC3:'participant_menu_choice',0xAC73:'choose_computer_participant_menu',
 0xACA8:'change_participant_control',0xAFF6:'prepare_intelligence_objects',0xB016:'advance_action_object',
 0xB036:'evaluate_action_object',0xB066:'resolve_action_success',0xB084:'queue_action_success',
 0xB0AC:'queue_action_failure',0xB15B:'round_health_update',0xB198:'draw_action_objects',
 0xB1B7:'draw_action_counter',0xB44B:'resolve_animation_collision',0xB48A:'update_animation_object',
 0xB4E3:'finish_animation_object',0xB548:'prepare_attack_object_arrays',0xB870:'text_readiness',
 0xB882:'build_object_nametable_packet',0xBA18:'insert_object_nametable_overlay',
 0xBA56:'prepare_object_packet_colors',0xBA79:'build_object_attribute_packet',0xBB8F:'initialize_attack_background',
 0xBE15:'build_initial_nametable_rows',0xBE76:'build_initial_attribute_rows',0xBF15:'flush_attack_background',
 0xBF4C:'draw_attack_scene_objects',0xBF9D:'object_position_to_world',0xBFA1:'object_position_to_world_saved',
 0xC01B:'animate_background_CHR',0xC064:'choose_object_axis_direction',0xC1CD:'probe_shifted_object_position',0xC20F:'choose_shifted_object_destination',
 0xC30F:'search_axis_object_target',0xC827:'classify_object_collision',0xC839:'check_object_side',
 0xC8FD:'draw_formation_selection_result',0xC926:'prepare_participant_statistics',
 0xC991:'compute_combat_equipment_parameters',0xCA3F:'write_attack_results_to_battle',
 0xCAC8:'probe_shifted_object_terrain',0xCAF9:'read_object_terrain_with_affinity',0xCBF1:'build_participant_stats_packets',
 0xCC7A:'participant_controller_input',0xCCA8:'selected_side_controller_input',
 0xCCDE:'side_controller_input',0xCD22:'active_side_controller_input',0xCE10:'restore_saved_main_phase',
 0xCF05:'formation_choice_input',0xD067:'round_stat_check',0xD0AE:'round_resource_check',
 0xD0CB:'test_first_commander',0xD102:'formation_pair_evaluation',0xD1D8:'formation_damage_evaluation',
 0xD2D4:'formation_object_parameters',0xD32A:'formation_probability_evaluation',
 0xD3C7:'formation_special_evaluation',0xD42F:'resolve_formation_results',
 0xD506:'commit_formation_damage',0xD558:'evaluate_routed_formation',0xD5A0:'draw_formation_counter',
 0xD5BC:'queued_object_map_update',0xD5F3:'draw_selected_participant',0xD612:'side_object_position',
 0xD652:'prepare_selected_side_object',0xD72B:'draw_other_participant_menu',0xD7FB:'experience_level_code',
 0xAFD2:'object_action_wait',0xAF26:'object_action_move',0xB00E:'object_action_advance',
 0xB02E:'object_action_evaluate',0xB07C:'object_action_success',0xB09C:'object_action_failure'}
FIELD_NAMES={0x540:'STATE',0x541:'PHASE',0x542:'CONTROL',0x544:'BACKGROUND',
 0x545:'OBJECT_INDEX',0x546:'ACTION_CLASS',0x547:'ACTION_CURSOR',0x548:'SCAN_CURSOR',
 0x549:'ACTIVE_SIDE',0x54B:'SAVED_STATE',0x54C:'SAVED_PHASE',0x54F:'OBJECT_ACTION',
 0x560:'FIRST_OFFICER',0x561:'SECOND_OFFICER',0x562:'FIRST_CONTROLLER',0x563:'SECOND_CONTROLLER',
 0x56C:'FIRST_FORMATION',0x56D:'SECOND_FORMATION',0x580:'OBJECT_X',0x596:'OBJECT_Y',
 0x5AC:'OBJECT_VALUE',0x5C2:'OBJECT_ENCODING',0x81:'NEW_BUTTONS',0x87:'FADE_FLAG',
 0x7A:'GLOBAL',0x78:'NMI_SCENE',0x7E:'PPU_JOBS'}

HEADER='''"""Readable, bounded bank14/15 normal-attack scene controller.

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
STATE,PHASE,CONTROL,BACKGROUND=0x540,0x541,0x542,0x544
OBJECT_INDEX,ACTION_CLASS,ACTION_CURSOR,SCAN_CURSOR=0x545,0x546,0x547,0x548
ACTIVE_SIDE,SAVED_STATE,SAVED_PHASE,OBJECT_ACTION=0x549,0x54B,0x54C,0x54F
FIRST_OFFICER,SECOND_OFFICER,FIRST_CONTROLLER,SECOND_CONTROLLER=0x560,0x561,0x562,0x563
FIRST_FORMATION,SECOND_FORMATION=0x56C,0x56D
OBJECT_X,OBJECT_Y,OBJECT_VALUE,OBJECT_ENCODING=0x580,0x596,0x5AC,0x5C2
NEW_BUTTONS,FADE_FLAG,GLOBAL,NMI_SCENE,PPU_JOBS=0x81,0x87,0x7A,0x78,0x7E

@dataclass
class AttackRegisters:
    a:int=0
    x:int=0
    y:int=0
    sp:int=0xFD
    p:int=U
    pc:int=0xA069

class AttackBudgetExceeded(RuntimeError):pass

class AttackSceneController:
    def __init__(self,memory,rom,services=None):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:raise ValueError('Pinned attack ROM required')
        self.memory=memory;self.rom=bytes(rom);self.services=services
        self.registers=AttackRegisters();self.events=[];self.pending=None;self._program=None
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
    def _mark(self,pc):
        self.registers.pc=pc;self._blocks+=1
        if self._blocks>self._limit:raise AttackBudgetExceeded('Source control-block budget reached')
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
                try:result=self.services(call)
                except UnsupportedHardware:return self._result('dependency')
                if not isinstance(result,dict)or result.get('status')!='returned':return self._result('dependency')
                if self.registers.pc!=call.return_pc or self.registers.sp!=call.expected_sp:return self._result('dependency')
                self.pending=None
            try:self.pending=next(self._program)
            except AttackBudgetExceeded:
                self._program=None;return self._result('budget')
            except StopIteration:
                self._program=None
                if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')
                return self._result('returned')
    def _result(self,status):
        return dict(status=status,before=self._before,after=(self.memory[STATE],self.memory[PHASE],self.memory[CONTROL]),
                    control_blocks=self._blocks,events=list(self.events),pending=self.pending)
    def resume(self):
        if self._program is None:raise RuntimeError('No pending attack invocation')
        return self._drive()
    def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)
    def tick_control(self,registers=None,**kwargs):return self.run_entry(0xA069,registers=registers,**kwargs)
    def run_entry(self,entry=0xA000,*,registers=None,seed_return=False,return_pc=None,max_blocks=200000):
        if self._program is not None:raise RuntimeError('Resume the existing attack invocation first')
        self.registers=registers or AttackRegisters();r=self.registers
        if r.p&D:raise ValueError('NES binary arithmetic requires D=0')
        if seed_return:
            if return_pc not in(None,0x0200):raise ValueError('Synthetic fixture return only permits0200')
            self.memory[0x1FE:0x200]=bytes((255,1));r.sp=0xFD
        self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;self._before=(self.memory[STATE],self.memory[PHASE],self.memory[CONTROL])
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
        self.roots.update((0xA000,0xA00F,0xA030,0xA069))
        for x in instructions:
            if x['op']=='DISPATCH':self.roots.update(x['targets']);self.roots.add(x['pc'])
        self.names={e:HELPER_NAMES.get(e,f'local_{e:04x}')for e in self.roots}
        self.names[0xA069]='attack_tick'
        self.names[0xA06C]='attack_main_dispatch'
        self.names[0xAF17]='object_action_choice_dispatch'
        for state in catalog['states']:
            self.names[state['entry_cpu']]=MAIN_NAMES[state['state']]
            self.names[state['dispatch_cpu']]=f'{MAIN_NAMES[state["state"]]}_phase_dispatch'
            for sub in state['substates']:
                e=sub['entry_cpu']
                if e in self.roots and e!=state['entry_cpu']:
                    self.names[e]=f'{MAIN_NAMES[state["state"]]}_phase_{sub["substate"]}'
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
        if op=='NOP':return['pass  # original deliberate no-op']
        raise ValueError((op,x['pc']))
    def procedure(self,entry):
        G=self.graph(entry);dom,loops=self.dominators(G,entry);join=self.postdominators(G)
        lines=[f'    def {self.names[entry]}(self):',f'        """Original entry ${entry:04X}; explicit software control body."""','        r=self.registers;m=self.memory']
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
                        put(indent,f'self._push(0x{(pc+2)>>8:02X});self._push(0x{(pc+2)&255:02X})')
                        put(indent,f'yield from self.{self.names[target]}()')
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
        text+='        raise ValueError("Entry is outside the proven attack procedure catalog")\n\n'
        for entry in sorted(self.roots):
            if entry in MANUAL_BODIES:
                body=MANUAL_BODIES[entry].replace('METHOD_NAME',self.names[entry])
                self.stats.append(dict(entry=entry,name=self.names[entry],instruction_nodes=len(self.graph(entry)),source_lines=len(body.splitlines()),natural_loop_headers=[],semantic_rewrite=True))
                text+=body
            else:text+=self.procedure(entry)
        return text

MANUAL_BODIES={0xA095:'''    def METHOD_NAME(self):
        """A095..A0D2: wait for fade, clear control arrays, prepare both sides."""
        r=self.registers;m=self.memory
        self._mark(0xA095);self._a(m[FADE_FLAG])
        if not r.p&N:self._rts();return
        self._a(6);m[STATE]=r.a;self._a(0);m[PHASE]=r.a
        self._a(0)
        for address in (*range(0x550,0x558),*range(0x574,0x578)):m[address]=r.a
        self._a(0);m[SCAN_CURSOR]=r.a
        self._push(0xA0);self._push(0xD1)
        yield from self.prepare_participant_statistics()
        if r.pc!=0xA0D2:return
        self._rts();return

''',0xC926:'''    def METHOD_NAME(self):
        """C926..C990: derive each participant's martial/equipment/IQ fields.

        056A/B and04C1/2 hold the derived attack parameter,056E/F the armor
        correction,0570/1 the weapon correction,0572/3 floor(IQ/13). The real
        officer pointer and arithmetic services keep their calling conventions.
        """
        r=self.registers;m=self.memory
        self._mark(0xC926)
        for side,pointer_pc,parameter_pc,IQ_pointer_pc,division_pc in ((0,0xC929,0xC92C,0xC93E,0xC952),(1,0xC95E,0xC961,0xC973,0xC987)):
            self._a(m[FIRST_OFFICER+side])
            yield from self._external(pointer_pc,0xF2D7,pointer_pc+3,'call')
            self._push((parameter_pc+2)>>8);self._push(parameter_pc+2)
            yield from self.compute_combat_equipment_parameters()
            if r.pc!=parameter_pc+3:return
            m[0x56A+side]=m[0x4C1+side]=r.a;m[0x570+side]=r.y;m[0x56E+side]=r.x
            self._a(m[FIRST_OFFICER+side])
            yield from self._external(IQ_pointer_pc,0xF2D7,IQ_pointer_pc+3,'call')
            self._y(2);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[0]=r.a
            self._a(0);m[1]=r.a;self._a(13);m[3]=r.a
            yield from self._external(division_pc,0xEBCA,division_pc+3,'call')
            self._a(m[0]);m[0x572+side]=r.a
        self._rts();return

''',0xC991:'''    def METHOD_NAME(self):
        """C991..CA1E: martial coefficient, RNG bias and equipment corrections.

        Preserve the duplicate45 coefficient at both <50 and <65. RNG accepts
        only low-nibble0..8; rejected values consume the real permutation cursor.
        Weapon and armor are the original packed record byte10, not troop type.
        """
        r=self.registers;m=self.memory
        self._mark(0xC991);self._y(10);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._push(r.a)
        self._y(1);self._a(m[((m[0]|m[1]<<8)+r.y)&65535])
        for threshold,coefficient in ((50,45),(65,45),(80,50),(87,55),(92,60),(97,65)):
            self._y(coefficient);self._compare(r.a,threshold)
            if not r.p&C:break
        else:self._y(70)
        m[3]=r.y;m[0]=r.a;self._a(0);m[1]=m[2]=r.a
        yield from self._external(0xC9CE,0xEBE9,0xC9D1,'call')
        self._a(m[6]);m[1]=r.a;self._a(m[7]);m[2]=r.a
        self._a(100);m[3]=r.a;self._a(0);m[4]=r.a
        yield from self._external(0xC9E7,0xEA7C,0xC9EA,'call')
        while True:
            yield from self._external(0xC9EA,0xE87A,0xC9ED,'call')
            self._a(r.a&15);self._compare(r.a,9)
            if not r.p&C:break
        m[2]=r.a;self._a(m[1]);self._flag(C,False);self._add(9)
        self._flag(C,True);self._add(m[2],subtract=True)
        if not r.p&C:self._a(1)
        m[1]=r.a;self._a(self._pop());self._push(r.a)
        self._a(r.a&31);self._y(r.a);self._a(m[0xCA1F+r.y]);self._y(r.a)
        self._a(self._pop())
        for _ in range(5):r.a=self._shift(r.a,False)
        self._x(r.a);self._a(m[0xCA37+r.x]);self._x(r.a);self._a(m[1])
        self._rts();return

''',0xC064:'''    def METHOD_NAME(self):
        """C064..C1CC: two-axis object direction choice with one fallback.

        The object class chooses horizontal/vertical priority from the byte
        distances. Only the other axis is tried after a rejected probe; the
        original 0012 retry byte, zero-distance RNG and signed-byte quirks
        remain observable. This is not a general path search.
        """
        r=self.registers;m=self.memory
        self._mark(0xC064)
        self._a(0);m[0x12]=r.a
        self._a(m[OBJECT_ACTION]);self._compare(r.a,1)
        if r.p&Z:
            self._a(m[OBJECT_INDEX]);self._compare(r.a,11)
            if r.p&C:
                self._a(32);m[0x10]=r.a;self._a(m[OBJECT_Y]);m[0x11]=r.a
            else:
                self._a(255);m[0x10]=r.a;self._a(m[OBJECT_Y+11]);m[0x11]=r.a
        else:
            self._a(m[OBJECT_INDEX]);self._compare(r.a,11)
            if r.p&C:
                self._a(m[OBJECT_X]);m[0x10]=r.a;self._a(m[OBJECT_Y]);m[0x11]=r.a
            else:
                self._a(m[OBJECT_X+11]);m[0x10]=r.a;self._a(m[OBJECT_Y+11]);m[0x11]=r.a
        self._a(m[(OBJECT_X+r.y)&65535]);self._flag(C,True);self._add(m[0x10],subtract=True);m[0x10]=r.a
        if not r.p&C:self._a(r.a^255);self._flag(C,False);self._add(1)
        m[0]=r.a
        self._a(m[(OBJECT_Y+r.y)&65535]);self._flag(C,True);self._add(m[0x11],subtract=True);m[0x11]=r.a
        if not r.p&C:self._a(r.a^255);self._flag(C,False);self._add(1)
        m[1]=r.a
        self._a(m[(OBJECT_ENCODING+r.y)&65535]);self._a(r.a&15)
        if r.p&Z:
            compare_axes=True
        else:
            self._compare(r.a,3)
            if r.p&Z:compare_axes=True
            else:
                compare_axes=False;self._compare(r.a,2)
                if r.p&Z:
                    self._a(m[1]);self._compare(r.a,2);horizontal=not bool(r.p&C)
                else:
                    self._a(m[0]);self._compare(r.a,2);horizontal=bool(r.p&C)
        if compare_axes:
            self._a(m[1]);self._compare(r.a,m[0])
            if r.p&Z:
                yield from self._external(0xC116,0xE87A,0xC119,'call')
                self._a(r.a&1);horizontal=bool(r.p&Z)
            else:horizontal=not bool(r.p&C)
        while True:
            self._mark(0xC123 if horizontal else 0xC178)
            self._a(m[0x10 if horizontal else 0x11])
            if r.p&Z:
                call_pc=0xC12C if horizontal else 0xC181
                yield from self._external(call_pc,0xE87A,call_pc+3,'call')
                self._a(r.a&128);positive=not bool(r.p&Z)
            else:positive=bool(r.p&N)
            self._a(1 if horizontal and positive else 255 if horizontal else 0);m[0]=r.a
            self._a(0 if horizontal else 1 if positive else 255);m[1]=r.a
            probe_pc=(0xC157 if positive else 0xC13D)if horizontal else(0xC1AC if positive else 0xC192)
            self._push((probe_pc+2)>>8);self._push(probe_pc+2)
            yield from self.probe_shifted_object_position()
            if r.pc!=probe_pc+3:return
            if r.p&C:
                parameter_pc=(0xC15C if positive else 0xC142)if horizontal else(0xC1B1 if positive else 0xC197)
                self._push((parameter_pc+2)>>8);self._push(parameter_pc+2)
                yield from self.read_object_terrain_with_affinity()
                if r.pc!=parameter_pc+3:return
                accepted=bool(r.p&Z)
            else:accepted=False
            if accepted:
                self._a((3 if positive else 2)if horizontal else(1 if positive else 0));m[ACTIVE_SIDE]=r.a
                self._rts();return
            self._a(m[0x12])
            if not r.p&Z:
                self._a(255);m[ACTIVE_SIDE]=r.a;self._rts();return
            m[0x12]=self._nz(m[0x12]+1)
            horizontal=not horizontal

''',0xC20F:'''    def METHOD_NAME(self):
        """C20F..C30E: randomized four-neighbor occupied-object probe.

        Randomly choose an axis and its initial sign. Try that sign, its
        opposite, then the two signs on the other axis; only the axis switch
        draws another sign. A clear-carry nonzero collision code is accepted.
        """
        r=self.registers;m=self.memory
        self._mark(0xC20F);self._a(0);m[0x10]=m[0x11]=r.a
        yield from self._external(0xC217,0xE87A,0xC21A,'call')
        self._a(r.a&1);horizontal=bool(r.p&Z);choose_sign=True
        while True:
            self._mark(0xC221 if horizontal else 0xC298)
            if choose_sign:
                sign_pc=0xC221 if horizontal else 0xC298
                yield from self._external(sign_pc,0xE87A,sign_pc+3,'call')
                self._a(r.a&128);positive=not bool(r.p&Z)
            self._a(1 if horizontal and positive else 255 if horizontal else 0);m[0]=r.a
            self._a(0 if horizontal else 1 if positive else 255);m[1]=r.a
            probe_pc=(0xC26A if positive else 0xC232)if horizontal else(0xC2E1 if positive else 0xC2A9)
            self._push((probe_pc+2)>>8);self._push(probe_pc+2)
            yield from self.probe_shifted_object_position()
            if r.pc!=probe_pc+3:return
            if not r.p&C:
                self._y(r.a)
                if not r.p&Z:
                    m[0x54A]=r.x;self._a((3 if positive else 2)if horizontal else(1 if positive else 0))
                    m[ACTIVE_SIDE]=r.a;self._rts();return
            self._a(m[0x10]);self._compare(r.a,3)
            if r.p&Z:
                self._a(255);m[ACTIVE_SIDE]=r.a;self._rts();return
            self._compare(r.a,1);switch_axis=bool(r.p&Z)
            m[0x10]=self._nz(m[0x10]+1)
            if switch_axis:
                horizontal=not horizontal;choose_sign=True
            else:
                positive=not positive;choose_sign=False

''',0xC30F:'''    def METHOD_NAME(self):
        """C30F..C826: randomized axis rays, two-to-six cell target search.

        A nearer occupied cell or terrain blocks that ray. Distance5/6 needs
        the selected side's 0575 nibble. The negative horizontal failure
        re-enters its own failure test instead of probing the opposite sign;
        this original asymmetry is retained, not normalized to four rays.
        """
        r=self.registers;m=self.memory
        self._mark(0xC30F);self._a(0);m[0x10]=m[0x11]=r.a
        yield from self._external(0xC317,0xE87A,0xC31A,'call')
        self._a(r.a&1);horizontal=bool(r.p&Z);choose_sign=True
        while True:
            self._mark(0xC321 if horizontal else 0xC5A4)
            if choose_sign:
                sign_pc=0xC321 if horizontal else 0xC5A4
                yield from self._external(sign_pc,0xE87A,sign_pc+3,'call')
                self._a(r.a&128);positive=bool(r.p&Z)
            if horizontal:
                terrain_calls=(0xC473,0xC49B,0xC4C5,0xC4EF,0xC534,0xC55E)if positive else(0xC335,0xC35D,0xC387,0xC3B1,0xC3F6,0xC420)
            else:
                terrain_calls=(0xC6F6,0xC71E,0xC748,0xC772,0xC7B7,0xC7E1)if positive else(0xC5B8,0xC5E0,0xC60A,0xC634,0xC679,0xC6A3)
            for distance in range(1,7):
                if distance==5:
                    self._a(m[OBJECT_INDEX]);self._compare(r.a,11)
                    second=bool(r.p&C);self._a(m[0x575]);self._a(r.a&(240 if second else 15))
                    if r.p&Z:break
                delta=distance if positive else(-distance)&255
                self._a(delta if horizontal else 0);m[0]=r.a
                self._a(0 if horizontal else delta);m[1]=r.a
                terrain_pc=terrain_calls[distance-1]
                self._push((terrain_pc+2)>>8);self._push(terrain_pc+2)
                yield from self.probe_shifted_object_terrain()
                if r.pc!=terrain_pc+3:return
                self._y(r.a)
                if not r.p&Z:break
                self._a(delta if horizontal else 0);m[0]=r.a
                self._a(0 if horizontal else delta);m[1]=r.a
                probe_pc=terrain_pc+0x13
                self._push((probe_pc+2)>>8);self._push(probe_pc+2)
                yield from self.probe_shifted_object_position()
                if r.pc!=probe_pc+3:return
                if not r.p&C:
                    self._y(r.a)
                    if not r.p&Z:
                        if distance==1:break
                        self._a((distance-1)*16+12);m[0x54D]=r.x;m[SCAN_CURSOR]=r.a
                        self._a((3 if positive else 2)if horizontal else(1 if positive else 0));m[ACTIVE_SIDE]=r.a
                        self._rts();return
            while True:
                self._a(m[0x10]);self._compare(r.a,3)
                if r.p&Z:self._a(255);m[ACTIVE_SIDE]=r.a;self._rts();return
                self._compare(r.a,1);switch_axis=bool(r.p&Z)
                m[0x10]=self._nz(m[0x10]+1)
                if switch_axis:
                    horizontal=not horizontal;choose_sign=True;break
                if horizontal and not positive:
                    continue  # C466 JMP C44C, including the skipped +X ray
                positive=not positive;choose_sign=False;break

'''}

def extend_original_wrapper(rom, instructions):
    """Fresh offline decode of NMI4's A000 wrapper, not audio's A003 entry."""
    from py65.devices.mpu6502 import MPU
    from py65.disassembler import Disassembler
    memory=bytearray(65536)
    memory[0xA000:0xC000]=rom[16+14*8192:16+15*8192]
    memory[0xC000:0xE000]=rom[16+15*8192:16+16*8192]
    cpu=MPU(memory=memory);dis=Disassembler(cpu)
    found={x['pc']:x for x in instructions};pending=[0xA000]
    while pending:
        pc=pending.pop()
        while 0xA000<=pc<0xE000 and pc not in found:
            size,assembly=dis.instruction_at(pc);op,mode=cpu.disassemble[memory[pc]]
            raw=bytes(memory[pc:pc+size]);operand=int.from_bytes(raw[1:],'little');nxt=pc+size
            if op in BRANCHES:operand=(pc+2+int.from_bytes(raw[1:2],'little',signed=True))&65535
            bank=14 if pc<0xC000 else 15;offset=16+bank*8192+(pc&8191)
            item=dict(pc=pc,bank=bank,file=offset,op=op,mode=mode,operand=operand,next_pc=nxt,assembly=assembly,bytes_hex=raw.hex())
            if op=='JSR' and operand==0xEE07:
                item.update(op='FARCALL',inline_target=int.from_bytes(memory[pc+3:pc+5],'little'),next_pc=pc+5)
            elif op in ('JSR','JMP'):
                if 0xA000<=operand<0xE000:pending.append(operand)
                else:item['hook']=f'{operand:04X}'
            elif op in BRANCHES:pending.append(operand)
            if op=='???':raise ValueError(f'Unclassified wrapper opcode at {pc:04X}')
            found[pc]=item
            if op in ('RTS','JMP'):break
            pc=item['next_pc']
    return [found[pc]for pc in sorted(found)]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    old=ROOT/'analysis/attack_fsm/program.json';program=json.loads(old.read_text())
    catalog=json.loads((ROOT/'analysis/attack_fsm/state-catalog.json').read_text())
    for x in program['instructions']:
        bank=x['bank'];file=16+bank*8192+(x['pc']&8191)
        assert file==x['file']
        assert rom[file:file+len(bytes.fromhex(x['bytes_hex']))]==bytes.fromhex(x['bytes_hex'])
        if x['op']=='FARCALL':assert int.from_bytes(rom[file+3:file+5],'little')==x['inline_target']
        # The lifted payload has no raw bytes; decode the opcode only offline.
        sys.path.insert(0,str(ROOT/'scripts'));from inspect_game_data import OPS,SIZES
        op,mode=OPS[rom[file]]
        assert op==( 'JSR'if x['op']in('DISPATCH','FARCALL')else x['op'])
    catalog_for_source={'states':[dict(state=s['state'],entry_cpu=s['entry'],dispatch_cpu=s['dispatch_pc'],substates=[dict(substate=h['substate'],entry_cpu=h['entry'])for h in s['handlers']])for s in catalog['states']]}
    instructions=extend_original_wrapper(rom,program['instructions'])
    builder=Structurer(instructions,catalog_for_source);source=builder.source();ast.parse(source)
    SOURCE.write_text(source);OUT.mkdir(parents=True,exist_ok=True)
    original_addresses=[dict(physical_bank=x['bank'],cpu_address=x['pc'],rom_offset=x['file'],raw_hex=x['bytes_hex'])for x in instructions]
    artifact=dict(rom_sha256=SHA,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      offline_graph_sha256=hashlib.sha256(old.read_bytes()).hexdigest(),procedures=builder.stats,
      structured_if_count=builder.if_count,natural_loop_count=builder.loop_count,
      original_instruction_nodes=len(instructions),old_IR_instruction_nodes=len(program['instructions']),states=catalog['states'],original_instruction_locations=original_addresses)
    (OUT/'catalog.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n')
    proof=[]
    for x in instructions:
        extra=''
        if x['op']=='FARCALL':extra=f' ; inline target ${x["inline_target"]:04X}'
        if x['op']=='DISPATCH':extra=' ; bounded targets '+','.join(f'${v:04X}'for v in x['targets'])
        proof.append(f'{x["file"]:06X} b{x["bank"]:02d}:${x["pc"]:04X} {x["bytes_hex"]:<9} {x["assembly"]}{extra}')
    (OUT/'original-ranges.asm').write_text('; Original byte evidence; offsets include16-byte iNES header.\n'+'\n'.join(proof)+'\n')
    ranges=[]
    for label,bank,lo,hi in [('actual_NMI_wrapper',14,0xA000,0xA069),('initialize_control',14,0xA095,0xA0D3),
                           ('participant_stat_preparation',15,0xC926,0xC991),('martial_equipment_parameters',15,0xC991,0xCA1F),
                           ('axis_direction_choice',15,0xC064,0xC1CD),('four_neighbor_choice',15,0xC20F,0xC30F),
                           ('axis_ray_target_search',15,0xC30F,0xC827),('background_CHR_wrapper',15,0xC01B,0xC064)]:
        offset=16+bank*8192+(lo&8191);raw=rom[offset:offset+hi-lo]
        ranges.append(dict(name=label,physical_bank=bank,cpu_start=lo,cpu_end_exclusive=hi,rom_offset=offset,byte_count=hi-lo,raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
    tables=[]
    for t in catalog['dispatch_tables']:
        raw=rom[t['table_file']:t['table_file']+2*t['count']]
        assert raw.hex(' ').upper()==t['raw_hex']
        tables.append(dict(call_pc=t['call_pc'],physical_bank=t['table_bank'],cpu_start=t['table_start'],rom_offset=t['table_file'],count=t['count'],raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest(),targets=t['targets']))
    for label,bank,lo,n in [('weapon_corrections',15,0xCA1F,24),('armor_corrections',15,0xCA37,8),('background_CHR_tiles',15,0xC054,8),('background_CHR_patterns',15,0xC05C,8)]:
        offset=16+bank*8192+(lo&8191);raw=rom[offset:offset+n]
        tables.append(dict(name=label,physical_bank=bank,cpu_start=lo,rom_offset=offset,count=n,raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest()))
    validation=json.loads((OUT/'validation.json').read_text())if(OUT/'validation.json').exists()else None
    evidence=dict(rom_sha256=SHA,source_kind='independent named Python procedures, structured branches/natural loops and six semantic algorithms',
                  main_state_count=11,expanded_substate_entry_count=58,distinct_substate_entry_count=56,
                  dispatch_table_count=13,legal_dispatch_arm_count=75,procedure_count=len(builder.stats),
                  original_instruction_count=len(instructions),original_instruction_bytes=sum(len(bytes.fromhex(x['bytes_hex']))for x in instructions),
                  source_runtime_IR_interpretation=False,source_original_code_fallback=False,
                  offline_graph_usage='All original graph instruction bytes are checked against pinned ROM; only analysis uses the old graph. Production imports no JSON or instruction model.',
                  source_file=str(SOURCE.relative_to(ROOT)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  REA_archive='analysis/rea/pairs/pair-14',
                  ranges=ranges,tables=tables,source_AST_counts=dict(if_count=sum(isinstance(n,ast.If)for n in ast.walk(ast.parse(source))),while_count=sum(isinstance(n,ast.While)for n in ast.walk(ast.parse(source))),for_count=sum(isinstance(n,ast.For)for n in ast.walk(ast.parse(source)))),
                  field_names={hex(k):v for k,v in FIELD_NAMES.items()},semantic_rewrites=[hex(v)for v in MANUAL_BODIES],
                  external_fixed_targets=sorted({x['operand']for x in instructions if x.get('hook')}),
                  far_call_sites=[dict(call_pc=x['pc'],target=x['inline_target'])for x in instructions if x['op']=='FARCALL'],
                  validation_summary=None if validation is None else{k:validation[k]for k in('status','rom_cpu_case_count','complete_CPU_count','strict_prefix_CPU_count','source_guard_case_count','dynamic_original_instruction_locations')},
                  limitations=['External helpers remain explicit services; actual CPU callbacks are only in the validator.',
                               'Static closure is not complete dynamic branch coverage; native frames and IRQ timing are not claimed here.',
                               'Object/value field names describe mechanical use, not newly confirmed formal gameplay names.',
                               'Entry selection occurs once; PC values thereafter are register/caller-protocol evidence, never an opcode/program dispatcher.'],
                  historical_offset_erratum='Old attack_fsm/handlers.asm mislabeled bank14 offsets by-0x2000. This new evidence uses16+physicalbank*8192+(CPU&1FFF); old frozen artifacts remain unchanged.')
    (OUT/'evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in artifact.items()if k not in('procedures','states','original_instruction_locations')}))
if __name__=='__main__':main()
