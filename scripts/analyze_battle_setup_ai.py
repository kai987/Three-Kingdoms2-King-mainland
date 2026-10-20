#!/usr/bin/env python3
"""Recover original bank8/9 setup and NMI auxiliary procedures offline."""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from inspect_game_data import OPS,SIZES
from analyze_battle_scene_controller import Structurer,HEADER,BRANCHES
import analyze_battle_scene_controller as BASE
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase11/setup-ai';SOURCE=ROOT/'source/recovered/battle_setup_ai.py'
NAMES={0xA003:'initialize_entry',0xB130:'initialize_battle_AI',0xB1B0:'assign_strategies_and_positions',
 0xB2AE:'first_side_formation',0xB312:'second_side_formation',0xB371:'sort_noncommanders_by_martial',
 0xB3D2:'swap_three_unit_arrays',0xB469:'city_pointer_20',0xB491:'officer_pointer_20',0xB4C2:'ruler_pointer_20',
 0xA012:'HUD_entry',0xCFA2:'battle_HUD',0xA021:'camera_entry',0xD57B:'advance_camera',
 0xA015:'units_entry',0xD1ED:'battle_unit_sprites',0xD2F5:'select_unit_CHR',0xD337:'world_viewport_test',
 0xD126:'draw_HUD_digit'}

SEMANTIC='''
def strategy_profile(ruler,side_base,noncommander_count,rom):
    """Six original profiles, each with nine two-byte packed count records.

    The four counts allocate strategyIDs1..4; commander uses0. A count of0
    skips the original profile read and leaves its old parameter cache intact.
    """
    if not 0<=ruler<7 or side_base not in(0,10)or not 0<=noncommander_count<=9:
        raise ValueError('Setup domain ruler0..6,side0/10,count0..9')
    if noncommander_count==0:return None
    family=1 if ruler in(1,5)else 2 if ruler in(2,4)else 0
    profile=family+(3 if side_base==10 else 0)
    offset=16+8*8192+(0xB3FD&8191)+18*profile+2*(noncommander_count-1)
    a,b=rom[offset:offset+2];counts=(a>>4,a&15,b>>4,b&15)
    return dict(profile=profile,counts=counts,strategies=tuple(s for s,n in enumerate(counts,1)for _ in range(n)),
                file_offset=offset,raw_bytes=(a,b))

def ordered_noncommander_triplets(triplets,rom_or_records):
    """Exact adjacent swaps, including the original >= equality/tie behavior.

    Each tuple is(officerID,side/affinity,hundredTroops). Other battlefield
    arrays are deliberately not moved. The input is the contiguous nonleader
    prefix after the commander, not arbitrary sparse empty slots.
    """
    items=list(triplets)
    if len(items)>9 or any(not 0<=v[0]<237 for v in items):raise ValueError('At most9 valid officers')
    def martial(ident):
        if isinstance(rom_or_records,(bytes,bytearray))and len(rom_or_records)==524304:
            return rom_or_records[16+17*8192+12*ident+1]
        return rom_or_records[0x63C0+12*ident+1]
    for _ in range(max(0,len(items)-1)):
        for j in range(len(items)-1):
            if martial(items[j+1][0])>=martial(items[j][0]):items[j],items[j+1]=items[j+1],items[j]
    return tuple(items)
'''

MANUAL_ASSIGNMENT='''    def assign_strategies_and_positions(self):
        """B1B0: select one profile, distribute four groups and set formation.

        The commander keeps strategy0. Noncommanders have already undergone
        the exact martial adjacent swaps. Old profile cache survives count0.
        """
        r=self.registers;m=self.memory;self._mark(0xB1B0)
        self._a(m[0x22])
        family=18 if r.a in(1,5)else 36 if r.a in(2,4)else 0
        self._a(family);self._flag(C,False);self._add(m[0x20]);m[0x20]=r.a
        self._a(m[0x6F94])
        if r.a:
            self._flag(C,True);self._add(1,subtract=True)
            r.a=self._shift(r.a,True);self._flag(C,False);self._add(m[0x20]);m[0x20]=r.a
            self._a(0xFD);self._flag(C,False);self._add(m[0x20]);m[0x20]=r.a
            self._a(0xB3);self._add(0);m[0x21]=r.a
            self._x(0);self._a(m[0x6F91])
            if r.a:self._x(4)
            self._y(0)
            # Two bytes unpack into counts for strategy IDs1,2,3,4.
            while True:
                self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x22]=r.a
                for _ in range(4):r.a=self._shift(r.a,False)
                m[0x6F99+r.x]=r.a
                self._a(m[0x22]);self._a(r.a&15);m[0x6F9A+r.x]=r.a
                self._x(r.x+1);self._x(r.x+1);self._y(r.y+1);self._compare(r.y,2)
                if r.p&C:break
            self._x(0);self._a(m[0x6F91])
            if r.a:self._x(4)
            self._a(r.x);self._flag(C,False);self._add(4);m[0x22]=r.a
            self._a(1);m[0x20]=r.a;self._y(m[0x6F91]);self._y(r.y+1)
            while True:
                self._a(m[0x6F99+r.x])
                if r.a:
                    m[0x21]=r.a
                    while True:
                        self._a(m[0x20]);m[0x6FA1+r.y]=r.a;self._y(r.y+1)
                        m[0x21]=self._nz(m[0x21]-1);self._a(m[0x21])
                        if not r.a:break
                m[0x20]=self._nz(m[0x20]+1);self._x(r.x+1);self._compare(r.x,m[0x22])
                if r.p&C:break
        self._a(m[0x6F91])
        if r.a:
            if not(yield from self._local_call(self.second_side_formation,0xB263,0xB266)):return
        else:
            if not(yield from self._local_call(self.first_side_formation,0xB25D,0xB260)):return
        self._x(m[0x6F91]);self._a(r.x);self._flag(C,False);self._add(10);m[0x2A]=r.a
        self._y(0);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x614+r.x]=r.a
        self._y(r.y+1);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x600+r.x]=r.a;self._x(r.x+1)
        while True:
            self._a(m[0x6FA1+r.x]);self._compare(r.a,255)
            if r.p&Z:break
            self._flag(C,True);self._add(1,subtract=True);m[0x2B]=r.a;self._y(r.a)
            self._a(m[0x22+r.y]);self._y(r.a)
            self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x614+r.x]=r.a
            self._y(r.y+1);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x600+r.x]=r.a
            self._y(m[0x2B]);self._a(m[0x22+r.y]);self._flag(C,False);self._add(2);m[0x22+r.y]=r.a
            self._x(r.x+1);self._compare(r.x,m[0x2A])
            if r.p&C:break
        self._rts()

'''

MANUAL_SORT='''    def sort_noncommanders_by_martial(self):
        """B371: exclude commander, count occupied slots, swap three arrays.

        Adjacent ties also swap. Each outer pass repeats the full comparison
        range; this is deliberately not Python's stable sorted().
        """
        r=self.registers;m=self.memory;self._mark(0xB371)
        self._a(m[0x6F91]);self._y(r.a);self._flag(C,False);self._add(10);m[0x2A]=r.a
        self._x(0)
        while True:
            self._a(m[0x664+r.y]);self._compare(r.a,255)
            if not r.p&Z:self._x(r.x+1)
            self._y(r.y+1);self._compare(r.y,m[0x2A])
            if r.p&C:break
        self._x(r.x-1);m[0x6F94]=r.x;self._compare(r.x,2)
        if not r.p&C:self._rts();return
        self._y(1)
        while True:
            self._a(r.y);self._push(r.a);self._x(m[0x6F91]);self._a(r.x)
            self._flag(C,False);self._add(m[0x6F94]);m[0x2B]=r.a;self._x(r.x+1)
            while True:
                self._a(m[0x664+r.x])
                if not(yield from self._local_call(self.officer_pointer_20,0xB3A7,0xB3AA)):return
                self._y(1);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);m[0x2A]=r.a
                self._a(m[0x665+r.x])
                if not(yield from self._local_call(self.officer_pointer_20,0xB3B4,0xB3B7)):return
                self._y(1);self._a(m[((m[0x20]|m[0x21]<<8)+r.y)&65535]);self._compare(r.a,m[0x2A])
                if r.p&C:
                    if not(yield from self._local_call(self.swap_three_unit_arrays,0xB3C0,0xB3C3)):return
                self._x(r.x+1);self._compare(r.x,m[0x2B])
                if r.p&C:break
            self._a(self._pop());self._y(r.a);self._y(r.y+1);self._compare(r.y,m[0x6F94])
            if r.p&C:break
        self._rts()

'''

class SetupStructurer(Structurer):
    def simple(self,item):
        if item['op']=='BIT':
            value=self.operand(item)
            return [f'bit_value={value}','self._flag(Z,not(r.a&bit_value))',
                    'self._flag(N,bit_value&128)','self._flag(V,bit_value&64)']
        return super().simple(item)

def collect(rom):
    I={};todo=[0xA003,0xA012,0xA015,0xA021]
    modes={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp','rel':'rel'}
    while todo:
        pc=todo.pop()
        if pc in I:continue
        assert 0xA000<=pc<0xE000,hex(pc)
        bank=8+int(pc>=0xC000);file=16+bank*8192+(pc&8191)
        op,mode=OPS[rom[file]];size=SIZES[mode];assert op!='?',hex(pc)
        value=int.from_bytes(rom[file+1:file+size],'little');nxt=pc+size
        if op in BRANCHES:value=(nxt+(value if value<128 else value-256))&65535
        x=dict(pc=pc,bank=bank,file=file,op=op,mode=modes.get(mode,mode),operand=value,next_pc=nxt)
        if op=='JSR'and value==0xEE07:
            x.update(op='FARCALL',inline_target=int.from_bytes(rom[file+3:file+5],'little'),next_pc=pc+5,hook='far service')
        elif op in('JSR','JMP')and value>=0xE000:x['hook']='fixed service'
        if op=='RTS':pass
        elif op=='JMP':
            if not x.get('hook'):todo.append(value)
        elif op in BRANCHES:todo.extend((value,nxt))
        else:
            todo.append(x['next_pc'])
            if op=='JSR'and 0xA000<=value<0xE000:todo.append(value)
        I[pc]=x
    return I

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
    I=collect(rom);b=SetupStructurer.__new__(SetupStructurer);b.I=I;b.catalog={'states':[]}
    BASE.MANUAL_PROCEDURES[0xB1B0]=MANUAL_ASSIGNMENT
    BASE.MANUAL_PROCEDURES[0xB371]=MANUAL_SORT
    b.roots={v['operand']for v in I.values()if v['op']=='JSR'and not v.get('hook')}|{0xA003,0xA012,0xA015,0xA021}
    b.roots.update(v for v in NAMES if v in I)
    b.names={v:NAMES.get(v,f'local_{v:04x}')for v in b.roots};b.stats=[];b.loop_count=b.if_count=0
    header=HEADER.replace('BattleSceneController','BattleSetupAI').replace('BattleRegisters','SetupRegisters')
    header=header.replace('Readable, bounded bank12/13 battle scene controller.','Readable bank8/9 battle setup and NMI auxiliary software.')
    header=header.replace('def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)',
      'def tick(self,registers=None,**kwargs):return self.run_entry(0xA003,registers=registers,**kwargs)')
    header=header.replace('entry=0xA028','entry=0xA003').replace('pc:int=0xA028','pc:int=0xA003')
    header=header.replace('control_blocks=self._blocks,events=list(self.events),pending=self.pending)',
      'control_blocks=self._blocks,events=list(self.events),pending=self.pending,setup_fields=self.setup_state())')
    source=header+'''    def setup_state(self):
        m=self.memory
        return dict(side_base=m[0x6F91],noncommander_count_work=m[0x6F94],
                    scan_cursor=m[0x6F94],status3_count=m[0x6F95],qualified_attempts=m[0x6F96],
                    strategy_parameters=list(m[0x6F99+i]for i in range(8)),
                    unit_strategies=list(m[0x6FA1+i]for i in range(20)),
                    auxiliary_cache=list(m[0x6FC9+i]for i in range(20)),
                    ambush_cache=list(m[0x4D8+i]for i in range(8)),
                    camera_request=m[0x508],camera_x=m[0x8E]|m[0x8F]<<8,camera_y=m[0x90]|m[0x91]<<8)
    def initialize(self,**kwargs):return self.run_entry(0xA003,**kwargs)
    def draw_HUD(self,**kwargs):return self.run_entry(0xA012,**kwargs)
    def draw_units(self,**kwargs):return self.run_entry(0xA015,**kwargs)
    def step_camera(self,**kwargs):return self.run_entry(0xA021,**kwargs)

    def _entry(self,entry):
'''
    for i,e in enumerate(sorted(b.roots)):
        source+=f'        {"if"if i==0 else"elif"} entry==0x{e:04X}:return self.{b.names[e]}()\n'
    source+='        raise ValueError("Entry is outside bank8/9 setup procedure catalog")\n\n'
    for e in sorted(b.roots):source+=b.procedure(e)
    source+=SEMANTIC;tree=ast.parse(source);SOURCE.write_text(source);OUT.mkdir(parents=True,exist_ok=True)
    nodes=[]
    for v in sorted(I.values(),key=lambda v:v['pc']):
        file=v['file'];op,mode=OPS[rom[file]];size=5 if v['op']=='FARCALL'else SIZES[mode]
        nodes.append({**v,'rom_offset':file,'raw_hex':rom[file:file+size].hex(' ')})
    tables=[]
    for name,bank,cpu,size in [('six_strategy_profiles',8,0xB3FD,108),('ruler_pointers',8,0xB4D3,14),
      ('first_side_group_offsets',8,0xB30E,4),('second_side_group_offsets',8,0xB36D,4),
      ('first_side_formation_pointers',6,0x8C52,60),('second_side_formation_pointers',6,0x8000,60),
      ('city_adjacency',16,0x9D72,240),('first_side_formation_direction',17,0x9AB4,240),
      ('second_side_formation_direction',16,0x9E62,240)]:
        file=16+bank*8192+(cpu&8191);tables.append(dict(name=name,physical_bank=bank,cpu=cpu,rom_offset=file,byte_count=size,raw_hex=rom[file:file+size].hex(' ')))
    d=dict(rom_sha256=SHA,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      instruction_count=len(I),procedure_count=len(b.roots),structured_if_count=b.if_count,natural_loop_count=b.loop_count,
      public_entries={f'{e:04X}':b.names[e]for e in (0xA003,0xA012,0xA015,0xA021)},procedures=b.stats,
      original_instructions=nodes,tables=tables,source_original_CPU=False,source_control_IR=False,
      corrected_stub_mapping={'A021':'D57B','A027':'D66E'},
      source_pins=[dict(path=f,sha256=hashlib.sha256((ROOT/f).read_bytes()).hexdigest())for f in
        ('source/recovered/battle_setup_ai.py','scripts/analyze_battle_setup_ai.py','scripts/analyze_battle_scene_controller.py')])
    (OUT/'evidence.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in d.items()if k not in('procedures','original_instructions','tables','source_pins')}))
if __name__=='__main__':main()
