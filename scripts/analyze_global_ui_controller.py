#!/usr/bin/env python3
"""Offline recovery of global/title/ruler-selection and city UI workers.

The original ROM is decoded only here. Production output contains direct,
named procedures, structured branches and natural loops, never a CPU/IR engine.
"""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from inspect_game_data import OPS,SIZES,instruction
import analyze_battle_scene_controller as BASE
from analyze_battle_scene_controller import Structurer,BRANCHES,HEADER
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase13/global-ui';SOURCE=ROOT/'source/recovered/global_ui_controller.py'
DOMAINS={
 'city-workers':dict(pair=29,entries=(0xA009,0xA00F,0xA03F,0xA021,0xA024,0xA02D,0xA039),minimum=0xA000,
  class_name='CityUIWorkers',names={0xA009:'panel_entry',0xABD2:'update_panel_job',0xA00F:'list_entry',0xB989:'update_list_job',0xA03F:'animation_entry',0xBE36:'update_animation_job',0xAEC9:'close_panel_row_group',0xADF3:'open_panel_row_group',0xAD92:'initialize_city_panel',0xCAC5:'initialize_packet_animation',0xCBD2:'finish_animation_row_batch',0xA021:'header_entry',0xA77F:'header_cadence_16',0xA024:'header_packet_entry',0xA7B2:'request_6F05_header',0xA02D:'alternate_header_entry',0xA78A:'header_cadence_4',0xA039:'block_menu_entry',0xBC71:'block_menu_tick'},
  exclusions={0xA000,0xA003,0xA006,0xA015,0xA018,0xA01B,0xA027,0xA02A,0xA030,0xA033,0xA036,0xA03C,0xA045,0xA048,0xA8A4,0xA991,0xDBB1,0xDD8B,0xDE7E,0xDEB9}),
 'title':dict(pair=10,entries=(0xA003,),minimum=0xD717,class_name='TitleUIController',
  names={0xA003:'title_entry',0xD717:'title_tick',0xDD34:'update_title_sprites',0xD74F:'introduction',0xD99C:'title_menu',0xDA7E:'scenario_menu',0xD732:'reset_title',0xDCC8:'advance_intro_palette',0xDD0F:'intro_palette_group'},exclusions=set()),
 'ruler-selection':dict(pair=8,entries=(0xA024,),minimum=0xD70F,class_name='RulerSelectionUIController',
  names={0xA024:'ruler_selection_entry',0xD70F:'ruler_selection_tick',0xD723:'ruler_selection',0xD73A:'initialize_ruler_selection',0xD778:'acknowledge_first_prompt',0xD7B0:'select_first_ruler',0xD80C:'acknowledge_second_prompt',0xD844:'select_second_ruler',0xD8A0:'inspect_selected_ruler',0xD8E4:'confirm_rulers_and_start',0xDC4A:'apply_selection_option_bits',0xD906:'ruler_menu_and_details',0xD97A:'initialize_seven_ruler_records',0xDAD9:'blink_prompt_marker',0xDAFE:'text_idle',0xDB10:'track_first_input_sequence',0xDB62:'track_second_input_sequence',0xDBB4:'track_third_input_sequence',0xDBFF:'track_fourth_input_sequence',0xDC9C:'install_option_profile'},exclusions=set()),
 'ending':dict(pair=23,entries=(0xA01E,),minimum=0xD693,class_name='EndingUIController',
  names={0xA01E:'ending_entry',0xD693:'ending_tick',0xD6AA:'loss_or_extinction_notice',0xD79B:'score_high_ending',0xD83A:'score_middle_ending',0xD8C9:'score_low_ending',0xD9CA:'officer_credits',0xD920:'final_text',0xDBF3:'ending_frame_sprites',0xD76D:'loss_palette'},exclusions=set()),
}
MODES={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp','rel':'rel'}
MANUAL={0xAEC9:'''    def close_panel_row_group(self):
        """AEC9: produce four14-tile rows and one4-byte attribute group.

        The original source strides32 bytes per row. Queue bit08 is a request;
        this producer does not upload PPU bytes or acknowledge consumption.
        """
        r=self.registers;m=self.memory;self._mark(0xAEC9)
        m[0x140]=self._nz(m[0x140]-1)
        self._y(48)
        yield from self._external(0xAECE,0xF25F,0xAED1,'call')
        if r.pc!=0xAED1:return
        self._a(m[0x143]);m[0x10]=r.a;self._a(m[0x144]);m[0x11]=r.a;self._x(0)
        while True:
            self._y(0)
            while True:
                self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535]);m[0x160+r.x]=r.a
                self._y(r.y+1);self._x(r.x+1);self._compare(r.y,14)
                if r.p&C:break
            self._a(m[0x10]);self._flag(C,False);self._add(32);m[0x10]=r.a
            self._a(m[0x11]);self._add(0);m[0x11]=r.a;self._compare(r.x,56)
            if r.p&C:break
        self._a(m[0x143]);self._flag(C,True);self._add(128,subtract=True);m[0x143]=r.a
        self._a(m[0x144]);self._add(0,subtract=True);m[0x144]=r.a
        self._a(m[0x145]);m[0x10]=r.a;self._a(m[0x146]);m[0x11]=r.a;self._y(0)
        while True:
            self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535]);m[0x14B+r.y]=r.a
            self._y(r.y+1);self._compare(r.y,4)
            if r.p&C:break
        # Source/attribute/destination pointers move upwards for the next job.
        for lo,amount in ((0x145,8),(0x147,8),(0x141,128)):
            self._a(m[lo]);self._flag(C,True);self._add(amount,subtract=True);m[lo]=r.a
            self._a(m[lo+1]);self._add(0,subtract=True);m[lo+1]=r.a
        self._a(m[0x7E]);self._a(r.a|8);m[0x7E]=r.a;self._rts()

''',0xCA4E:'''    def cityuiworkers_c9c5_phase_2(self):
        """CA4E: copy at most five14-tile packets, retaining earlyFF marker."""
        r=self.registers;m=self.memory;self._mark(0xCA4E)
        m[0x4A3]=self._nz(m[0x4A3]-1);self._a(m[0x4A3])
        if r.p&N:return (yield from self.initialize_packet_animation())
        self._a(m[0x4D4]);m[0]=r.a;self._a(m[0x4D5]);m[1]=r.a;self._y(0);self._x(0)
        terminated=False
        while True:
            self._a(14);m[0x380+r.x]=r.a;self._x(r.x+1)
            self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,255)
            if r.p&Z:
                self._x(r.x-1);m[0x380+r.x]=r.a;terminated=True;break
            m[0x380+r.x]=r.a;self._x(r.x+1);self._y(r.y+1)
            self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._flag(C,False);self._add(m[0x4D2]);m[0x380+r.x]=r.a
            self._x(r.x+1);self._y(r.y+1);self._a(0);m[2]=0
            while True:
                self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[0x380+r.x]=r.a
                self._x(r.x+1);self._y(r.y+1);m[2]=self._nz(m[2]+1)
                self._a(m[2]);self._compare(r.a,14)
                if r.p&C:break
            self._compare(r.y,80)
            if r.p&C:break
        if not terminated:
            self._a(255);m[0x380+r.x]=r.a
            self._a(m[0]);self._flag(C,False);self._add(80);m[0x4D4]=r.a
            self._a(m[1]);self._add(0);m[0x4D5]=r.a
        self._a(m[0x7E]);self._a(r.a|4);m[0x7E]=r.a;self._rts()

''',0xCB52:'''    def cityuiworkers_c9c5_phase_3(self):
        """CB52: five10-tile rows; source stride10, destination stride32."""
        r=self.registers;m=self.memory;self._mark(0xCB52)
        for src,dst in ((0x4D2,2),(0x4D3,3),(0x4D4,0),(0x4D5,1)):
            self._a(m[src]);m[dst]=r.a
        self._x(0);self._y(0)
        while True:
            self._a(10);m[0x380+r.x]=r.a;self._x(r.x+1)
            self._a(m[3]);m[0x380+r.x]=r.a;self._x(r.x+1)
            self._a(m[2]);m[0x380+r.x]=r.a;self._x(r.x+1);self._y(0)
            while True:
                self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[0x380+r.x]=r.a
                self._x(r.x+1);self._y(r.y+1);self._compare(r.y,10)
                if r.p&C:break
            for lo,amount in ((0,10),(2,32)):
                self._a(m[lo]);self._flag(C,False);self._add(amount);m[lo]=r.a
                self._a(m[lo+1]);self._add(0);m[lo+1]=r.a
            self._compare(r.x,65)
            if r.p&C:break
        self._a(255);m[0x380+r.x]=r.a
        for src,dst in ((2,0x4D2),(3,0x4D3),(0,0x4D4),(1,0x4D5)):
            self._a(m[src]);m[dst]=r.a
        return (yield from self.finish_animation_row_batch())

''',0xDD0F:'''    def intro_palette_group(self):
        """DD0F: four-color palette group, subtract16 repeatedly then clamp0F."""
        if False:yield None
        r=self.registers;m=self.memory;self._mark(0xDD0F)
        self._a(r.y);self._push(r.a)
        r.a=self._shift(r.a,True);r.a=self._shift(r.a,True);self._y(r.a)
        self._flag(C,False);self._add(4);m[0x11]=r.a
        while True:
            self._x(m[0x88]);self._a(m[((m[2]|m[3]<<8)+r.y)&65535])
            while True:
                self._x(r.x-1)
                if r.p&N:break
                self._flag(C,True);self._add(16,subtract=True)
                if r.p&N:self._a(15);break
            m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
            self._y(r.y+1);self._compare(r.y,m[0x11])
            if r.p&C:break
        self._a(self._pop());self._y(r.a);self._rts()

''',0xD9DE:'''    def endinguicontroller_d9cd_phase_0(self):
        """D9DE: credits buffer from all30 city rosters, retaining byte wrap.

        PrefixFE, highlighted officer042C, then each nonFF/nonhighlighted ID.
        The write cursor is byte-sized and neither deduplicates nor grows the
        original buffer. FE/FF markers finish it exactly as the original does.
        """
        r=self.registers;m=self.memory;self._mark(0xD9DE)
        self._y(48);yield from self._external(0xD9E0,0xF25F,0xD9E3,'call')
        if r.pc!=0xD9E3:return
        self._a(254);m[0x410]=r.a;self._a(m[0x42C]);m[0x411]=r.a
        self._x(0);self._a(2);m[2]=r.a
        while True:
            self._a(r.x);self._push(r.a)
            yield from self._external(0xD9F6,0xF2AF,0xD9F9,'call')
            if r.pc!=0xD9F9:return
            self._y(17)
            while True:
                self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,255)
                if not r.p&Z:
                    self._compare(r.a,m[0x411])
                    if not r.p&Z:
                        self._x(m[2]);m[0x410+r.x]=r.a;m[2]=self._nz(m[2]+1)
                self._y(r.y+1);self._compare(r.y,27)
                if r.p&C:break
            self._a(self._pop());self._x(r.a);self._x(r.x+1);self._compare(r.x,30)
            if r.p&C:break
        self._a(254);self._x(m[2]);m[0x410+r.x]=r.a;self._x(r.x+1)
        self._a(255);m[0x410+r.x]=r.a;self._a(0)
        m[0x40C]=m[0x40D]=m[0x401]=r.a;self._a(192);m[0x543]=r.a
        self._a(6);m[0x542]=r.a;self._a(241)
        yield from self._external(0xDA3D,0xF28B,0xDA40,'call')
        if r.pc!=0xDA40:return
        self._rts()

'''}
def offset(pair,pc):return 16+(31 if pc>=0xE000 else pair+int(pc>=0xC000))*8192+(pc&8191)
def pointer_table(rom,pair,pc):
    """Bound the inline table by its earliest forward body destination.

    This structural bound is independently checked against all covered state
    writes/catalogue below; it is not an assertion that arbitrary RAM indices
    are safe. An out-of-bound production index is rejected explicitly.
    """
    first=pc+3;end=0xE000;targets=[]
    while first+2*len(targets)<end:
        at=first+2*len(targets);o=offset(pair,at);target=int.from_bytes(rom[o:o+2],'little')
        if not 0xA000<=target<0xE000:raise ValueError(('invalid table destination',hex(pc),hex(target)))
        targets.append(target)
        if target>=first:end=min(end,target)
        if len(targets)>64:raise ValueError(('unbounded table',hex(pc)))
    assert first+2*len(targets)==end,('inline table overlap',hex(pc),targets)
    return targets
def collect(rom,domain):
    pair=domain['pair'];I={};todo=list(domain['entries']);tables=[];occupied={}
    def local(pc):return pc in domain['entries'] or domain['minimum']<=pc<0xE000 and pc not in domain['exclusions']
    while todo:
        pc=todo.pop()
        if pc in I:continue
        if not local(pc):raise ValueError(('unexpected local destination',pair,hex(pc)))
        file=offset(pair,pc);op,mode=OPS[rom[file]];size=SIZES[mode]
        assert op!='?',(pair,hex(pc),hex(rom[file]))
        value=int.from_bytes(rom[file+1:file+size],'little');nxt=pc+size
        if op in BRANCHES:value=(nxt+(value if value<128 else value-256))&65535
        raw_size=size
        x=dict(pc=pc,bank=pair+int(pc>=0xC000),file=file,op=op,mode=MODES.get(mode,mode),operand=value,next_pc=nxt)
        if op=='JSR'and value==0xEADE:
            targets=pointer_table(rom,pair,pc);x.update(op='DISPATCH',targets=targets)
            table_file=file+3;tables.append(dict(dispatch_pc=pc,cpu=pc+3,file=table_file,count=len(targets),targets=targets,
                raw_hex=rom[table_file:table_file+2*len(targets)].hex(' ').upper()))
        elif op=='JSR'and value==0xEE07:
            x.update(op='FARCALL',inline_target=int.from_bytes(rom[file+3:file+5],'little'),next_pc=pc+5,hook='far service');raw_size=5
        elif op in('JSR','JMP')and not local(value):x['hook']='explicit service'
        x['raw_hex']=rom[file:file+raw_size].hex(' ').upper();x['assembly']=instruction(rom,file,pc)[1]
        for k in range(pc,pc+size):
            assert k not in occupied or occupied[k]==pc,('overlap',pair,hex(k));occupied[k]=pc
        if x['op']=='DISPATCH':todo.extend(x['targets'])
        elif op in('RTS','RTI','BRK'):pass
        elif op=='JMP':
            if not x.get('hook'):todo.append(value)
        elif op in BRANCHES:todo.extend((value,nxt))
        else:
            todo.append(x['next_pc'])
            if op=='JSR'and local(value):todo.append(value)
        I[pc]=x
    for t in tables:assert not any(k in occupied for k in range(t['cpu'],t['cpu']+t['count']*2)),('table decoded as code',pair,hex(t['cpu']))
    return I,tables
class UIStructurer(Structurer):
    def simple(self,item):
        op=item['op']
        if op=='BIT':
            value=self.operand(item);return[f'bit_value={value}','self._flag(Z,not(r.a&bit_value))','self._flag(N,bit_value&128)','self._flag(V,bit_value&64)']
        if op=='PHP':return['self._push(r.p|B|U)']
        if op=='PLP':return['r.p=self._pop()|B|U']
        if op in('CLI','SEI','CLV','CLD'):return[f'self._flag({{"CLI":"I","SEI":"I","CLV":"V","CLD":"D"}}[op],{op=="SEI"})']
        return super().simple(item)
def compiler(I,tables,domain):
    b=UIStructurer.__new__(UIStructurer);b.I=I;b.catalog={}
    b.roots={v['operand']for v in I.values()if v['op']=='JSR'and not v.get('hook')}|set(domain['entries'])
    for v in I.values():
        if v['op']=='DISPATCH':b.roots.update(v['targets'])
    b.roots.update(v for v in domain['names']if v in I)
    b.names={v:domain['names'].get(v,f'{domain["class_name"].lower()}_{v:04x}')for v in b.roots}
    for t in tables:
        for index,entry in enumerate(t['targets']):
            if entry not in domain['names']:b.names[entry]=f'{domain["class_name"].lower()}_{t["dispatch_pc"]:04x}_phase_{index}'
    b.stats=[];b.loop_count=b.if_count=0;return b
def control_header():
    h=HEADER.replace('BattleSceneController','UIControlBase').replace('BattleRegisters','UIRegisters')
    h=h.replace('Readable, bounded bank12/13 battle scene controller.','Readable banked global UI controllers and auxiliary city presentation jobs.')
    h=h.replace('def tick(self,registers=None,**kwargs):return self.run_entry(0xA000,registers=registers,**kwargs)','def tick(self,registers=None,**kwargs):return self.run_entry(self.PUBLIC_ENTRIES[0],registers=registers,**kwargs)')
    h=h.replace('entry=0xA028,*,','entry=None,*,').replace("if self._program is not None:raise RuntimeError('Resume the existing battle invocation first')","if self._program is not None:raise RuntimeError('Resume the existing UI invocation first')\n        if entry is None:entry=self.PUBLIC_ENTRIES[0]")
    h=h.replace('return_pc=0x0200','return_pc=None').replace('if return_pc!=0x0200:','if return_pc not in(None,0x0200):')
    h=h.replace('self._return_pc=return_pc;self._before=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT])','self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;self._before=self.fields()')
    h=h.replace("if self.registers.pc!=self._return_pc:return self._result('nonlocal_return')","if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:return self._result('nonlocal_return')")
    h=h.replace('after=(self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT])','after=self.fields()')
    h+='''    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],UI_state=m[0x540],UI_phase=m[0x541],
                    panel_job=m[0x140],panel_kind=m[0x150],list_job=m[0x478],
                    animation_job=m[0x4A0],animation_kind=m[0x4A2],PPU_jobs=m[0x7E])
    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=self.PAIR or call.target not in self.PUBLIC_ENTRIES:
            return {'status':'dependency','reason':'UI caller pair/entry outside this owned domain'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns the pending UI request'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)

'''
    return h
DOMAIN_FIELDS={
 'city-workers':'''    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],parent_city_state=m[0x400],parent_city_phase=m[0x401],
                    panel_job=m[0x140],panel_kind=m[0x150],list_job=m[0x478],list_mode=m[0x479],list_cursor=m[0x47A],
                    animation_job=m[0x4A0],animation_phase=m[0x4A1],animation_kind=m[0x4A2],PPU_jobs=m[0x7E])
''',
 'title':'''    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],title_state=m[0x540],title_phase=m[0x541],
                    title_work_0542=m[0x542],title_index=m[0x543],title_timer=m[0x544],PPU_jobs=m[0x7E])
''',
 'ruler-selection':'''    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],ruler_state=m[0x540],ruler_phase=m[0x541],
                    ruler_cursor=m[0x46C],inspected_officer=m[0x46D],players_requested=m[0x6F43],PPU_jobs=m[0x7E])
''',
 'ending':'''    def fields(self):
        m=self.memory
        return dict(global_state=m[0x7A],NMI_scene=m[0x78],ending_mode=m[0x541],ending_phase=m[0x542],
                    ending_animation_04C9=m[0x4C9],ending_animation_04CA=m[0x4CA],ending_work_04CB=m[0x4CB],
                    ending_counter=m[0x4CD]|m[0x4CE]<<8,PPU_jobs=m[0x7E])
''',
}
def put(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def evidence(rom,catalog,allI):
    """Pin the new source, raw ranges, bounded tables and archived REA images."""
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    old=ROOT/'analysis/phase6/global/program.json';fixed=json.loads(old.read_text())
    main=[x for x in fixed['instructions']if 0xE05E<=x['pc']<0xE4DA]
    for x in main:
        assert bytes.fromhex(x['raw_hex'])==rom[x['file']:x['file']+len(bytes.fromhex(x['raw_hex']))]
    catalog['global-main']=dict(pair=[31],entry=0xE066,state_field=0x7A,mask=31,count=15,
        targets=fixed['main_targets'],instruction_count=len(main),boundary=0xE066,
        states=[dict(index=i,entry=pc,file=offset(29,pc))for i,pc in enumerate(fixed['main_targets'])],
        reused_initialization_entries=[0xE18B,0xE22F,0xE2E8],
        production_clock='One main-loop body; neither RTS nor an entire NMI/frame is synthesized')
    ranges=[];data_tables=[]
    for key,items in {**allI,'global-main':main}.items():
        positions={}
        for x in items:
            raw=bytes.fromhex(x['raw_hex']);assert rom[x['file']:x['file']+len(raw)]==raw
            for j in range(len(raw)):positions[(x['bank'],x['pc']+j)]=x['file']+j
        groups=[]
        for(bank,pc),file in sorted(positions.items()):
            if groups and groups[-1]['bank']==bank and groups[-1]['cpu_end_exclusive']==pc:groups[-1]['cpu_end_exclusive']+=1
            else:groups.append(dict(domain=key,bank=bank,cpu_start=pc,cpu_end_exclusive=pc+1,file=file))
        for group in groups:
            raw=rom[group['file']:group['file']+group['cpu_end_exclusive']-group['cpu_start']]
            group.update(raw_hex=raw.hex(' ').upper(),sha256=hashlib.sha256(raw).hexdigest());ranges.append(group)
        for table in catalog[key].get('tables',[]):data_tables.append(dict(domain=key,bank=DOMAINS[key]['pair']+int(table['cpu']>=0xC000),**table))
    for bank,cpu,length,name in((31,0xE07C,30,'original15_main_pointer_words'),(29,0xA7F6,59,'header_actual59_byte_copy')):
        file=16+bank*8192+(cpu&8191);raw=rom[file:file+length]
        data_tables.append(dict(name=name,bank=bank,cpu=cpu,file=file,length=length,raw_hex=raw.hex(' ').upper(),
            note='Nominal58-byte template; original Y=3A loop reads59 bytes including A830 firstopcode, copied as data only'if bank==29 else'15 legal main slots; invalid indices are source-domain guards'))
    archived={}
    for pair in(8,10,23,29):
        folder=ROOT/f'analysis/rea/pairs/pair-{pair:02d}'
        for name in('image.bin','mapping.json','catalog.json','evidence-bundle.json','pair-pseudocode.c'):
            path=folder/name
            if path.exists():archived[str(path.relative_to(ROOT))]=sha(path)
    source=SOURCE.read_text();tree=ast.parse(source)
    srcpins={str(p.relative_to(ROOT)):sha(p)for p in(SOURCE,Path(__file__),ROOT/'scripts/verify_global_ui_controller.py',ROOT/'scripts/analyze_battle_scene_controller.py')}
    put(OUT/'evidence.json',dict(schema='phase13-global-UI-independent-source-v1',rom_sha256=SHA,
        source_path=str(SOURCE.relative_to(ROOT)),analyzer_path=str(Path(__file__).relative_to(ROOT)),validator_path='scripts/verify_global_ui_controller.py',
        source_sha256=sha(SOURCE),source_and_analyzer_pins=srcpins,offline_graph_source=dict(path=str(old.relative_to(ROOT)),sha256=sha(old)),
        ranges=ranges,immutable_tables=data_tables,domains=catalog,REA_archive_pins=archived,
        banked_instruction_positions=sum(len(v)for v in allI.values()),fixed_main_instruction_positions=len(main),
        original_banked_procedure_roots=sum(len(d['procedure_roots'])for d in catalog.values()if'procedure_roots'in d),
        structured_if_count=sum(isinstance(n,ast.If)for n in ast.walk(tree)),natural_while_count=sum(isinstance(n,ast.While)for n in ast.walk(tree)),
        production_original_CPU_callbacks=0,production_IR_interpretation=False,
        interface=dict(main='GlobalUIController.run_main(entry=E066,registers) stops at nextE066 with actual callerSP',
                       callee='__call__(ServiceCall) and resume() retain owned generator and require explicit returned plus real PC/SP',
                       city_exports=list(DOMAINS['city-workers']['entries']),title_export=0xA003,ruler_export=0xA024,ending_export=0xA01E),
        title_crossbank_phase=dict(main0='D72A→EE07 selector37→23A021',phases=5,owner='TitleIntroGraphics; separate phase13/title-intro evidence'),
        metadata_fields=dict(city='parent0400/0401 plus140/150/478/479/47A/4A0/4A1/4A2',title='0540/0541/0542/0543/0544',ruler='0540/0541/046C/046D/6F43',ending='0541mode/0542phase and04C9..04CE'),
        remaining_dependencies=['E000 cold reset','E05E F3BD post-reset probe','Main2 physical10/11 A000 domestic cooperation','Main4 physical8/9 A000 tactical cooperation','Existing battle initialization dependencies are delegated, not falsely replaced by this UI module'],
        caution='No UI packet request is a consumed PPU queue, rendered pixel, elapsed frame, audio sample, or readiness acknowledgement. Labels preserve original numeric kinds where formal terminology lacks text evidence.'))
    (OUT/'global-main.asm').write_text('; Original fixed31 main control; pointer/data words excluded from instructions.\n'+'\n'.join(f'{x["file"]:06X} b31:${x["pc"]:04X} {x["raw_hex"]:<10} {x["assembly"]}'for x in main)+'\n')
GLOBAL_SOURCE='''
from .scene_initialization import SceneInitialization

MAIN_TARGETS=(0xE09A,0xE0DA,0xE17D,0xE18B,0xE221,0xE22F,0xE2E2,0xE2E8,
              0xE36A,0xE37C,0xE3EB,0xE3EE,0xE3EB,0xE46A,0xE3EB)

class GlobalUIController(SceneInitialization):
    """One main-loop update plus the three banked UI domains.

    run_main ends at the next real E066 boundary, without popping a synthetic
    RTS frame. Battle/attack/duel initialization is the existing independently
    recovered SceneInitialization. Banked callbacks retain their real caller.
    Unknown services, PPU input and fade completion remain explicit waits.
    """
    def __init__(self,memory,rom,services=None):
        self.services=services;self._pending_ui_owner=None;self._pending_ui_call=None
        super().__init__(memory,rom,self._strict_service)
        self.city_workers=CityUIWorkers(memory,rom,services)
        self.title=TitleUIController(memory,rom,services)
        self.rulers=RulerSelectionUIController(memory,rom,services)
        self.ending=EndingUIController(memory,rom,services)
    def _strict_service(self,call):
        if self.services is None:return {'status':'dependency','reason':'Unowned original UI service'}
        result=self.services(call)
        if not isinstance(result,dict)or result.get('status')!='returned':
            return {'status':'dependency','reason':'UI service has not returned explicitly'}
        return result
    def __call__(self,call):
        pair=tuple(call.entry_banks[1:3])
        owner={(29,30):self.city_workers,(10,11):self.title,(8,9):self.rulers,(23,24):self.ending}.get(pair)
        if self._pending_ui_owner is not None and self._pending_ui_call is not call:
            return {'status':'dependency','reason':'Another actual caller owns the pending UI domain'}
        if owner is not None and call.target in owner.PUBLIC_ENTRIES:
            owner.services=self.services
            result=owner(call)
            if result['status']=='returned':self._pending_ui_owner=self._pending_ui_call=None
            elif owner._program is not None:self._pending_ui_owner=owner;self._pending_ui_call=call
            return result
        return {'status':'dependency','reason':'Not a recovered global UI bank/entry','target':call.target}
    def resume(self):
        if self._pending_ui_owner is not None:
            owner=self._pending_ui_owner;owner.services=self.services;result=owner.resume()
            if result['status']=='returned':self._pending_ui_owner=self._pending_ui_call=None
            return result
        return super().resume()
    def run_main(self,entry=0xE066,registers=None):
        if self._pending_ui_owner is not None:raise RuntimeError('Resume the genuine pending banked UI caller first')
        if entry not in (0xE05E,0xE066,*MAIN_TARGETS):raise ValueError('Outside the15 main-state entries')
        def body():
            self.registers.pc=entry
            if entry==0xE05E:
                yield from self.call(0xE05E,0xF3BD);self.a(0);self.memory[0x7A]=0
                yield from self.dispatch_main()
            elif entry==0xE066:yield from self.dispatch_main()
            else:yield from self.main_body(entry)
        return self._start(body,registers,'global_main_boundary')
    tick_main=run_main
    def dispatch_main(self):
        r=self.registers;m=self.memory
        self.a(m[0x7A]);self.a(r.a&31);index=r.a
        if index>=15:raise ValueError('Main007A&31 outside original15 pointer words')
        self.shift_a('asl');self.y(r.a)
        self.a(m[0xE07C+r.y]);m[0x4E]=r.a;self.a(m[0xE07D+r.y]);m[0x4F]=r.a
        target=m[0x4E]|m[0x4F]<<8;r.pc=target
        yield from self.main_body(target)
    def main_body(self,entry):
        r=self.registers;m=self.memory
        if entry==0xE09A:yield from self.boot_display()
        elif entry==0xE0DA:yield from self.city_display()
        elif entry in self.SETUP_ENTRIES:yield from self.setup(entry)
        elif entry in (0xE17D,0xE221):
            pc=0xE17D if entry==0xE17D else 0xE221
            yield from self.call(pc,0xE87A)
            self.y(42 if entry==0xE17D else 40);yield from self.call(pc+5,0xF24B)
            yield from self.call(pc+8,0xA000)
        elif entry in (0xE2E2,0xE36A):yield from self.call(entry,0xE87A)
        elif entry==0xE37C:yield from self.title_display()
        elif entry==0xE3EE:yield from self.ruler_display()
        elif entry==0xE46A:yield from self.ending_display()
        elif entry!=0xE3EB:raise ValueError('Uncatalogued original main-state target')
        r.pc=0xE066
    def boot_display(self):
        r=self.registers;m=self.memory
        yield from self.call(0xE09A,0xE768);yield from self.call(0xE09D,0xE74D)
        yield from self.write(0x2001,r.a,0xE0A0);yield from self.call(0xE0A3,0xE57F)
        self.x(31);self.a(15)
        while True:
            m[0x100+r.x]=r.a;self.x(r.x-1)
            if r.p&N:break
        while True:
            self.a((yield from self.read(0x2002,0xE0B0)))
            if r.p&N:break
        self.a(76);m[0xA5]=r.a;yield from self.write(0xF800,r.a,0xE0BA)
        self.a(0);yield from self.call(0xE0BF,0xE51F)
        self.a(16);m[0x8B]=r.a;yield from self.write(0x2000,r.a,0xE0C7)
        self.a(0);m[0x8C]=r.a;yield from self.write(0x2001,r.a,0xE0CF)
        self.a(9);m[0x7A]=r.a
    def city_display(self):
        r=self.registers;m=self.memory
        yield from self.call(0xE0DA,0xE4DA);self.a(2);m[0x78]=r.a
        self.a(0);yield from self.call(0xE0E4,0xE370)
        self.y(48);yield from self.call(0xE0E9,0xF25F)
        self.a(0);m[0xA]=r.a;self.a(128);m[0xB]=r.a;self.a(32);m[1]=r.a
        self.a(0)
        for address in (0,4,5,6):m[address]=r.a
        self.a(4);m[7]=r.a;yield from self._select_pair(55,0xE110);yield from self.call(0xE113,0xA003)
        yield from self._select_pair(61,0xE118);self.a(0);m[0]=r.a;yield from self.call(0xE120,0xA015)
        yield from self.call(0xE123,0xEAF7);self.a(m[0x400]);self.cmp(r.a,13)
        if not r.p&Z:self.a(255);m[0x6F8B]=r.a
        yield from self._select_pair(61,0xE134);yield from self.call(0xE137,0xA036)
        yield from self.call(0xE13A,0xECBF);yield from self._select_pair(61,0xE13F)
        self.a(0);yield from self.call(0xE144,0xA045);self.a(160);m[0x98]=r.a;self.a(0)
        for address in(0x420,0x4E0,0x4E1,0x4E2,0x4E3):m[address]=r.a
        self.a(240);m[0x6F41]=r.a;self.a(128);m[0x6F3F]=r.a
        self.a(0);yield from self.call(0xE169,0xE51F);self.inc(0x7A)
        self.a(129);yield from self.call(0xE171,0xE673)
        yield from self.call(0xE174,0xE749);yield from self.call(0xE177,0xE753)
    def _raw_background_request(self,selector,pointer,select_pc,call_pc,clear=(0,4,5,6)):
        r=self.registers;m=self.memory;self.y(selector);yield from self.call(select_pc,0xF25F)
        self.a(pointer&255);m[0xA]=r.a;self.a(pointer>>8);m[0xB]=r.a
        self.a(32);m[1]=r.a;self.a(0)
        for address in clear:m[address]=r.a
        self.a(4);m[7]=r.a;yield from self._select_pair(55,call_pc-3);yield from self.call(call_pc,0xA003)
    def title_display(self):
        r=self.registers;m=self.memory;yield from self.call(0xE37C,0xE4DA)
        self.a(6);m[0x78]=r.a;self.a(11);yield from self.call(0xE386,0xE370)
        yield from self._raw_background_request(53,0x9A90,0xE38B,0xE3B5)
        yield from self._select_pair(61,0xE3BA);self.a(11);m[0]=r.a;yield from self.call(0xE3C2,0xA015)
        yield from self.call(0xE3C5,0xEAF7);yield from self.call(0xE3C8,0xECBF)
        yield from self._select_pair(61,0xE3CD);self.a(3);yield from self.call(0xE3D2,0xA045)
        self.a(160);m[0x98]=r.a;self.a(2);yield from self.call(0xE3DC,0xE51F)
        self.inc(0x7A);yield from self.call(0xE3E2,0xE749);yield from self.call(0xE3E5,0xE753)
    def ruler_display(self):
        r=self.registers;m=self.memory;yield from self.call(0xE3EE,0xE4DA)
        self.a(7);m[0x78]=r.a;self.a(12);yield from self.call(0xE3F8,0xE370)
        yield from self._raw_background_request(50,0x9AE3,0xE3FD,0xE427)
        yield from self._select_pair(61,0xE42C);yield from self.call(0xE42F,0xA018)
        yield from self._select_pair(61,0xE434);self.a(12);m[0]=r.a;yield from self.call(0xE43C,0xA015)
        yield from self.call(0xE43F,0xEAF7);yield from self.call(0xE442,0xECBF)
        yield from self._select_pair(61,0xE447);self.a(4);yield from self.call(0xE44C,0xA045)
        self.a(160);m[0x98]=r.a;self.a(2);yield from self.call(0xE456,0xE51F)
        self.inc(0x7A);self.a(8);yield from self.call(0xE45E,0xE683)
        yield from self.call(0xE461,0xE749);yield from self.call(0xE464,0xE753)
    def ending_display(self):
        r=self.registers;m=self.memory;yield from self.call(0xE46A,0xE4DA)
        self.a(8);m[0x78]=r.a;self.a(13);yield from self.call(0xE474,0xE370)
        self.y(54);yield from self.call(0xE479,0xF25F)
        self.a(146);m[0xA]=r.a;self.a(155);m[0xB]=r.a;self.a(0);m[0]=r.a;self.a(32);m[1]=r.a
        yield from self._select_pair(55,0xE492);yield from self.call(0xE495,0xA003)
        yield from self._select_pair(61,0xE49A);self.a(13);m[0]=r.a;yield from self.call(0xE4A2,0xA015)
        yield from self.call(0xE4A5,0xEAF7);yield from self._select_pair(61,0xE4AA)
        self.a(5);yield from self.call(0xE4AF,0xA045);self.a(160);m[0x98]=r.a
        self.a(2);yield from self.call(0xE4B9,0xE51F);self.inc(0x7A);self.y(m[0x541])
        if r.y:self.a(170);yield from self.call(0xE4CE,0xE67B)
        else:self.a(152);yield from self.call(0xE4C6,0xE673)
        yield from self.call(0xE4D1,0xE749);yield from self.call(0xE4D4,0xE753)
'''
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--inventory-only',action='store_true');a=p.parse_args()
    rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA;OUT.mkdir(parents=True,exist_ok=True)
    BASE.MANUAL_PROCEDURES=MANUAL;BASE.FIELD_NAMES={0x540:'UI_STATE',0x541:'UI_PHASE',0x81:'NEW_BUTTONS',0x87:'REPEAT_BUTTONS',0x7A:'GLOBAL',0x78:'NMI_SCENE',0x7E:'PPU_JOBS'}
    source=control_header()+'\nUI_STATE,UI_PHASE=0x540,0x541\n\n';catalog={};allI={}
    for key,d in DOMAINS.items():
        I,tables=collect(rom,d);b=compiler(I,tables,d);allI[key]=[I[k]for k in sorted(I)]
        hooks=[v for v in I.values()if v.get('hook')]
        catalog[key]=dict(pair=[d['pair'],d['pair']+1],entries=list(d['entries']),instruction_count=len(I),tables=tables,
                          external_calls=hooks,procedure_roots=sorted(b.roots))
        if not a.inventory_only:
            source+=f'class {d["class_name"]}(UIControlBase):\n    PAIR={d["pair"],d["pair"]+1}\n    PUBLIC_ENTRIES={d["entries"]}\n'+DOMAIN_FIELDS[key]+'\n    def _entry(self,entry):\n'
            for i,e in enumerate(sorted(b.roots)):source+=f'        {"if"if i==0 else"elif"} entry==0x{e:04X}:return self.{b.names[e]}()\n'
            source+='        raise ValueError("Entry outside immutable UI procedure catalog")\n\n'
            for entry in sorted(b.roots):source+=b.procedure(entry)
            catalog[key].update(procedures=b.stats,structured_if_count=b.if_count,natural_loop_count=b.loop_count)
    put(OUT/'catalog.json',dict(rom_sha256=SHA,domains=catalog));put(OUT/'offline-control-graph.json',dict(rom_sha256=SHA,domains=allI))
    lines=['; Phase13 new UI original code. Inline tables are data, not instructions.']
    for key,I in allI.items():
        lines.append('; '+key)
        for t in catalog[key]['tables']:lines.append(f'; {t["file"]:06X} ${t["cpu"]:04X} {t["raw_hex"]} ; {t["count"]} pointer words')
        for x in I:lines.append(f'{x["file"]:06X} b{x["bank"]:02d}:${x["pc"]:04X} {x["raw_hex"]:<14} {x["assembly"]}')
    (OUT/'original-ranges.asm').write_text('\n'.join(lines)+'\n')
    if not a.inventory_only:
        source+=GLOBAL_SOURCE;ast.parse(source);SOURCE.write_text(source);evidence(rom,catalog,allI)
        put(OUT/'catalog.json',dict(rom_sha256=SHA,domains=catalog))
    print(json.dumps({k:dict(instructions=v['instruction_count'],tables=[t['count']for t in v.get('tables',[])],procedures=len(v.get('procedure_roots',[])))for k,v in catalog.items()}))
if __name__=='__main__':main()
