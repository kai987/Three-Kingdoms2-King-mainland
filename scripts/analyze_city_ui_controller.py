#!/usr/bin/env python3
"""Offline original-byte closure and direct source structuring for city NMI2.

EADE inline tables and EE07 words are data, never decoded as instructions.
Production imports neither this graph nor an opcode/IR interpreter.
"""
from pathlib import Path
import argparse,ast,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES
from analyze_battle_scene_controller import Structurer,HEADER,BRANCHES,successors
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase13/city';SOURCE=ROOT/'source/recovered/city_ui_controller.py'
PUBLIC=(0xA000,0xA003,0xA006,0xA009)
KNOWN_TABLE_COUNTS={0xA022:16,0xA080:3,0xA18E:2}
NAMES={0xA000:'city_scene_entry',0xA00C:'city_scene_tick',0xA01F:'city_main_dispatch',
 0xA003:'city_context_entry',0xA006:'city_setup_entry',0xA009:'city_state_entry',
 0xA07D:'world_map_selection',0xA18B:'command_bar',0xA295:'domestic_commands',
 0xADF2:'military_commands',0xB759:'resource_commands',0xB7BF:'town_menu',
 0xA089:'prepare_world_map_selection',0xA0DF:'navigate_world_map_selection',
 0xA179:'await_world_selection_text',0xA12D:'request_city_information',
 0xA161:'request_system_menu',0xA195:'prepare_command_bar',0xA1D0:'navigate_command_bar',
 0xDDAD:'text_request_readiness',0xDDF2:'world_selection_portrait',0xDEBA:'city_at_cursor',
 0xDE83:'update_cursor_repeat',0xDF35:'city_callback_preparation',0xAD41:'transfer_selected_officers',0xC81F:'queue_equipment_icons'}
FIELDS={0x400:'STATE',0x401:'PHASE',0x402:'CITY',0x410:'OFFICER_LIST',
 0x40C:'OFFICER_INDEX',0x40D:'DETAIL_ROW',0x470:'WORLD_CURSOR',0x471:'CURRENT_CITY',
 0x81:'NEW_BUTTONS',0x87:'REPEAT_BUTTONS',0x7A:'GLOBAL',0x78:'NMI_SCENE',0x7E:'PPU_JOBS'}
MANUAL={0xAD41:'''    def transfer_selected_officers(self):
        """AD41..ADF1: append ten selected officers, promote the ruler and compact source roster.

        The two region records keep their real seventeen-byte header and ten
        roster bytes. Searches retain byte wrapping and actual caller flags.
        This body transfers roster membership; it does not infer allegiance.
        """
        r=self.registers;m=self.memory;self._mark(0xAD41)
        self._a(m[CURRENT_CITY]);yield from self._external(0xAD44,0xF2AF,0xAD47,'call')
        if r.pc!=0xAD47:return
        self._x(0);self._y(17)
        while True:
            self._mark(0xAD4B);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            self._y(r.y+1)
        while True:
            self._mark(0xAD55);self._a(m[(0x481+r.x)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            m[((m[0]|m[1]<<8)+r.y)&65535]=r.a;self._x(r.x+1);self._y(r.y+1);self._compare(r.x,10)
            if r.p&C:break
        self._y(0);self._a(m[(m[0xEE]|m[0xEF]<<8)]);m[2]=r.a;self._y(17)
        ruler_present=False
        while True:
            self._mark(0xAD6D);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[2])
            if r.p&Z:ruler_present=True;break
            self._y(r.y+1);self._compare(r.y,27)
            if r.p&C:break
        if ruler_present:
            self._a(r.y);self._push(r.a);self._y(17);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[3]=r.a
            self._a(m[2]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a;self._a(self._pop());self._y(r.a)
            self._a(m[3]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
            self._y(1);self._a(m[CURRENT_CITY]);m[((m[0xEE]|m[0xEF]<<8)+r.y)&65535]=r.a
        self._mark(0xAD98);self._a(m[WORLD_CURSOR]);yield from self._external(0xAD9B,0xF2AF,0xAD9E,'call')
        if r.pc!=0xAD9E:return
        self._x(0)
        while True:
            self._mark(0xADA0);self._a(m[(0x481+r.x)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            m[0x10]=r.a;self._y(17)
            while True:
                self._mark(0xADAC);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[0x10])
                if r.p&Z:
                    self._a(255);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a;break
                self._y(r.y+1)
            self._x(r.x+1);self._compare(r.x,10)
            if r.p&C:break
        self._x(0);self._a(255)
        while True:
            self._mark(0xADC7);m[(0x481+r.x)&65535]=r.a;self._x(r.x+1);self._compare(r.x,10)
            if r.p&C:break
        self._y(17);self._x(0)
        while True:
            self._mark(0xADD3);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,255)
            if not r.p&Z:m[(0x481+r.x)&65535]=r.a;self._x(r.x+1)
            self._y(r.y+1);self._compare(r.y,27)
            if r.p&C:break
        self._y(17);self._x(0)
        while True:
            self._mark(0xADE6);self._a(m[(0x481+r.x)&65535]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
            self._x(r.x+1);self._y(r.y+1);self._compare(r.x,10)
            if r.p&C:break
        self._mark(0xADF1);self._rts();return

''',0xC81F:'''    def queue_equipment_icons(self):
        """C81F..C8F9: four equipment records, two rows of eight tiles each.

        Requests the original nametable packet, keeps BC/BD font-page shadows
        and advances the city phase. It never acknowledges its PPU request.
        """
        r=self.registers;m=self.memory;self._mark(0xC81F)
        self._a(m[0x300]);self._compare(r.a,255)
        if not r.p&Z:self._rts();return
        self._y(48);yield from self._external(0xC829,0xF25F,0xC82C,'call')
        if r.pc!=0xC82C:return
        self._y(0);self._x(0);m[0x10]=m[0x11]=m[0x12]=r.x
        while True:
            self._mark(0xC839 if m[0x10]==0 else 0xC85B)
            self._y(m[0x10]);self._a(m[(0x44C+r.y)&65535]);r.a=self._shift(r.a,True);self._y(r.a)
            self._a(m[(0x9B12+r.y)&65535]);m[0]=r.a;self._y(r.y+1)
            self._a(m[(0x9B12+r.y)&65535]);self._flag(C,False);self._add(128);m[1]=r.a
            if m[0x10]==0:
                self._y(0);self._a(m[(m[0]|m[1]<<8)]);m[0xBC]=r.a
            self._y(0);m[0x14]=m[0x15]=r.y;self._a(m[(m[0]|m[1]<<8)]);self._compare(r.a,m[0xBC])
            if not r.p&Z:m[0xBD]=r.a;self._a(64);m[0x15]=r.a
            while True:
                self._mark(0xC88A);self._x(m[0x12]);self._a(m[(0xC8FA+r.x)&65535]);m[2]=r.a;self._x(r.x+1)
                self._a(m[(0xC8FA+r.x)&65535]);m[3]=r.a;self._x(r.x+1);m[0x12]=r.x;self._x(m[0x11])
                self._a(8);m[(0x380+r.x)&65535]=r.a;self._x(r.x+1);self._a(m[3]);m[(0x380+r.x)&65535]=r.a
                self._x(r.x+1);self._a(m[2]);m[(0x380+r.x)&65535]=r.a;self._a(0);m[0x13]=r.a
                while True:
                    self._mark(0xC8B9);self._x(r.x+1);self._y(r.y+1);self._a(m[((m[0]|m[1]<<8)+r.y)&65535])
                    self._flag(C,False);self._add(m[0x15]);m[(0x380+r.x)&65535]=r.a
                    m[0x13]=self._nz(m[0x13]+1);self._a(m[0x13]);self._compare(r.a,8)
                    if r.p&C:break
                self._x(r.x+1);m[0x11]=r.x;m[0x14]=self._nz(m[0x14]+1);self._a(m[0x14]);self._compare(r.a,2)
                if r.p&C:break
            m[0x10]=self._nz(m[0x10]+1);self._a(m[0x10]);self._compare(r.a,4)
            if r.p&C:break
        self._a(255);m[(0x380+r.x)&65535]=r.a;self._a(m[PPU_JOBS]);self._a(r.a|4);m[PPU_JOBS]=r.a
        m[PHASE]=self._nz(m[PHASE]+1);self._mark(0xC8F9);self._rts();return

'''}
def offset(pc,pair=27):return 16+(pair+int(pc>=0xC000))*8192+(pc&8191)
def inline_table(rom,pc,pair=27):
 start=pc+3;f=offset(start,pair)
 if pair==27 and pc in KNOWN_TABLE_COUNTS:n=KNOWN_TABLE_COUNTS[pc]
 else:
  # Candidate extent: the nearest forward arm is the first code boundary.
  # Each retained extent is independently emitted and checked by CPU cases.
  bound=0xE000;n=0
  while start+2*n<bound and n<128:
   target=int.from_bytes(rom[f+2*n:f+2*n+2],'little')
   if not 0xA000<=target<0xE000:raise ValueError(f'Unbounded inline table ${pc:04X}, word{n}=${target:04X}')
   if target>=start:bound=min(bound,target)
   n+=1
  if start+2*n!=bound:raise ValueError(f'Inline table/code boundary not aligned ${pc:04X}: {n}→${bound:04X}')
 targets=tuple(int.from_bytes(rom[f+2*i:f+2*i+2],'little')for i in range(n))
 return dict(call_pc=pc,physical_bank=pair+int(start>=0xC000),cpu_address=start,rom_offset=f,
  count=n,targets=targets,raw_hex=rom[f:f+2*n].hex(),extent_basis='explicit known table'if pair==27 and pc in KNOWN_TABLE_COUNTS else'nearest forward arm code boundary; retained for independent CPU checking')
def collect(rom,*,pair=27,entries=PUBLIC,stoplocals=()):
 I={};tables={};todo=list(entries);modes={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp'}
 while todo:
  pc=todo.pop()
  if pc in I:continue
  if not 0xA000<=pc<0xE000:raise ValueError(f'Local flow escaped ${pc:04X}')
  f=offset(pc,pair);op,mode=OPS[rom[f]];size=SIZES[mode];nxt=pc+size;value=int.from_bytes(rom[f+1:f+size],'little')
  if op=='?':raise ValueError(f'Unclassified code byte ${pc:04X}: {rom[f]:02X}')
  if op in BRANCHES:value=(nxt+(value if value<128 else value-256))&65535
  x=dict(pc=pc,bank=pair+int(pc>=0xC000),physical_bank=pair+int(pc>=0xC000),rom_offset=f,
   op=op,mode=modes.get(mode,mode),operand=value,next_pc=nxt,raw_hex=rom[f:f+size].hex())
  if op=='JSR'and value==0xEADE:
   t=inline_table(rom,pc,pair);tables[pc]=t;x.update(op='DISPATCH',targets=t['targets']);todo.extend(t['targets'])
  elif op=='JSR'and value==0xEE07:
   x.update(op='FARCALL',inline_target=int.from_bytes(rom[f+3:f+5],'little'),next_pc=pc+5,hook='real far-call inline word')
  elif op in('JSR','JMP')and (not 0xA000<=value<0xE000 or value in stoplocals):x['hook']='external owned service'
  if op=='JSR'and 0xA000<=value<0xE000 and not x.get('hook'):todo.append(value)
  todo.extend(successors(x));I[pc]=x
 return I,tables
class CityStructurer(Structurer):
 def procedure(self,entry):
  if entry in MANUAL:
   body=MANUAL[entry];self.stats.append(dict(entry=entry,name=self.names[entry],instruction_nodes=len(self.graph(entry)),source_lines=len(body.splitlines()),hand_written_structured_control=True));return body
  return super().procedure(entry)
 def addr(self,x):
  n=x['operand'];base=FIELDS.get(n,f'0x{n:04X}');mode=x['mode']
  if mode in('abs','zpg'):return base
  if mode in('abx','aby'):return f'({base}+r.{"x"if mode=="abx"else"y"})&65535'
  if mode in('zpx','zpy'):return f'({base}+r.{mode[-1]})&255'
  if mode=='iny':return f'((m[0x{n:02X}]|m[0x{(n+1)&255:02X}]<<8)+r.y)&65535'
  if mode=='inx':return f'm[({n}+r.x)&255]|m[({n}+r.x+1)&255]<<8'
  raise ValueError((mode,x['pc']))
 def simple(self,x):
  if x['op']=='PHP':return['self._push(r.p|0x30)']
  if x['op']=='PLP':return['r.p=self._pop()|0x30']
  if x['op']=='NOP':return[]
  if x['op']=='BIT':
   v=self.operand(x);return[f'value={v}', 'self._flag(Z,not(r.a&value));self._flag(N,value&128);self._flag(V,value&64)']
  return super().simple(x)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--catalog-only',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
 I,tables=collect(rom);OUT.mkdir(parents=True,exist_ok=True)
 catalog=dict(rom_sha256=SHA,original_instructions=sorted(I.values(),key=lambda x:x['pc']),dispatch_tables=list(tables.values()),original_instruction_count=len(I),external_targets=sorted({x['operand']for x in I.values()if x.get('hook')}))
 (OUT/'static-control.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(instructions=len(I),tables=len(tables),opcodes=sorted({x['op']for x in I.values()}),tables_counts={hex(k):v['count']for k,v in tables.items()})),flush=True)
 if a.catalog_only:return
 b=CityStructurer.__new__(CityStructurer);b.I=I;b.catalog={'states':[]};b.roots=set(PUBLIC)|{x['operand']for x in I.values()if x['op']=='JSR'and not x.get('hook')};b.roots.update(t for x in I.values()if x['op']=='DISPATCH'for t in x['targets']);b.roots.update(n for n in NAMES if n in I)
 b.names={e:NAMES.get(e,f'city_helper_{e:04x}')for e in b.roots};b.stats=[];b.loop_count=b.if_count=0
 h=HEADER.replace('BattleSceneController','CityUIController').replace('BattleRegisters','CityRegisters').replace('bank12/13 battle scene controller','bank27/28 city menu controller')
 lo=h.index('STATE,PHASE,');hi=h.index('@dataclass');h=h[:lo]+''.join(f'{v}=0x{k:X}\n'for k,v in FIELDS.items())+'ACTOR_SLOT=OFFICER_INDEX\n\n'+h[hi:]
 h=h.replace('Pinned battle ROM required','Pinned original city ROM required').replace('pc:int=0xA028','pc:int=0xA000').replace('entry=0xA028','entry=0xA000').replace('return_pc=0x0200','return_pc=None').replace('if return_pc!=0x0200','if return_pc not in(None,0x0200)')
 h=h.replace('self._return_pc=return_pc;', 'self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;')
 h=h.replace('if self.registers.pc!=self._return_pc:','if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:')
 h=h.replace('self._blocks=0;self._limit=200000','self._blocks=0;self._limit=200000;self._call_owner=None')
 h=h.replace('self.registers=registers or CityRegisters();r=self.registers',"if registers is None:raise ValueError('Supply actual caller registers and an existing RTS frame')\n        self.registers=registers;r=self.registers")
 h=h.replace('okay=result is None or isinstance(result,dict)and result.get("status")=="returned"','okay=isinstance(result,dict)and result.get("status")=="returned"')
 extra='''    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=(27,28) or call.target not in self.LOCAL_ENTRIES:
            return {'status':'dependency','reason':'No city body owns this exact pair/entry'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns pending city update'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)

'''
 source=h+extra+'    LOCAL_ENTRIES='+repr(tuple(sorted(b.roots)))+'\n    def _entry(self,entry):\n'
 for i,e in enumerate(sorted(b.roots)):source+=f'        {"if"if i==0 else"elif"} entry==0x{e:04X}:return self.{b.names[e]}()\n'
 source+='        raise ValueError("Entry outside original city menu closure")\n\n'
 for e in sorted(b.roots):
  try:source+=b.procedure(e)
  except Exception as exc:raise ValueError(f'City function {e:04X}: {exc}')from exc
 ast.parse(source);SOURCE.write_text(source)
 (OUT/'source-catalog.json').write_text(json.dumps(dict(procedures=b.stats,source_sha256=hashlib.sha256(source.encode()).hexdigest(),structured_ifs=b.if_count,natural_loops=b.loop_count),ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(procedures=len(b.stats),source_bytes=len(source.encode()))))
if __name__=='__main__':main()
