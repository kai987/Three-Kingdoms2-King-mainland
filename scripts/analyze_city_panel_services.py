#!/usr/bin/env python3
"""Offline city/ruler panel closure; existing portraits/details keep their owners."""
import argparse,ast,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from analyze_city_ui_controller import collect,CityStructurer,FIELDS
from analyze_battle_scene_controller import HEADER
from ui_structuring import labelled_procedure,loop_exception_source
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase13/panels';SOURCE=ROOT/'source/recovered/city_panel_services.py'
PUBLIC=(0xA003,0xA006,0xA009,0xA00C,0xA015,0xA018,0xA01B,0xA01E,0xA024,0xA027,0xA02A,0xA02D,0xA030)
NAMES={0xA003:'ruler_panel_entry',0xA006:'city_c773_entry',0xA009:'city_a296_entry',0xA00C:'city_ad81_entry',
 0xA015:'city_b7d9_entry',0xA018:'city_b8d7_entry',0xA01B:'new_officer_event_entry',0xA01E:'city_c435_entry',
 0xA024:'city_ba70_entry',0xA027:'city_bb03_entry',0xA02A:'calendar_header_entry',0xA02D:'city_bc02_entry',
 0xA030:'city_bb73_entry',0xA033:'ruler_panel',0xBBDE:'calendar_header',0xB964:'new_officer_event',
 0xB7D9:'prepare_battle_departure',0xB859:'remove_departing_roster_ids',0xB879:'compact_departure_city_roster',
 0xA1EB:'find_officer_city',0xA209:'decrement_ruler_counter_nibbles',0xA240:'count_available_nonrulers'}
MANUAL={0xB859:'''    def remove_departing_roster_ids(self):
        """B859..B878: remove up to ten selected0151 IDs from the city roster.

        The original inner search has no sentinel test. Caller roster validity
        determines termination; byte-index wrapping is preserved.
        """
        r=self.registers;m=self.memory
        while True:
            self._mark(0xB859);self._a(m[(0x151+r.x)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            m[2]=r.a;self._y(17)
            while True:
                self._mark(0xB865);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[2])
                if r.p&Z:break
                self._y(r.y+1)
            self._a(255);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
            self._x(r.x+1);self._compare(r.x,10)
            if r.p&C:break
        yield from self.compact_departure_city_roster()

''',0xA1EB:'''    def find_officer_city(self):
        """A1EB..A208: scan30 cities' ten roster slots for000A; zero if absent."""
        r=self.registers;m=self.memory;self._x(0)
        while True:
            self._mark(0xA1ED);self._a(r.x);yield from self._external(0xA1EE,0xF2AF,0xA1F1,'call')
            if r.pc!=0xA1F1:return
            self._y(17)
            while True:
                self._mark(0xA1F3);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[0xA])
                if r.p&Z:self._a(r.x);self._rts();return
                self._y(r.y+1);self._compare(r.y,27)
                if r.p&C:break
            self._x(r.x+1);self._compare(r.x,30)
            if r.p&C:break
        self._a(0);self._rts();return

''',0xA209:'''    def decrement_ruler_counter_nibbles(self):
        """A209..A23F: seven ruler records, four bytes; each nonzero nibble decays."""
        r=self.registers;m=self.memory;self._a(0);m[2]=r.a
        while True:
            self._mark(0xA20E);self._a(m[2]);yield from self._external(0xA211,0xF368,0xA214,'call')
            if r.pc!=0xA214:return
            self._y(4)
            while True:
                self._mark(0xA216);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._a(r.a&15)
                if not r.p&Z:
                    self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._flag(C,True);self._add(1,subtract=True)
                    m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
                self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._a(r.a&240)
                if not r.p&Z:
                    self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._flag(C,True);self._add(16,subtract=True)
                    m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
                self._y(r.y+1);self._compare(r.y,8)
                if r.p&C:break
            m[2]=self._nz(m[2]+1);self._a(m[2]);self._compare(r.a,7)
            if r.p&C:break
        self._rts();return

''',0xA240:'''    def count_available_nonrulers(self):
        """A240..A295: copy seven ruler IDs; count nonrulers whose low state bits are not3."""
        r=self.registers;m=self.memory;self._y(49);yield from self._external(0xA242,0xF25F,0xA245,'call')
        if r.pc!=0xA245:return
        self._y(0);self._x(0)
        while True:
            self._mark(0xA249);self._a(m[(0x6F07+r.y)&65535]);m[(0x42C+r.x)&65535]=r.a
            self._x(r.x+1);self._a(r.x)
            for _ in range(3):r.a=self._shift(r.a,True)
            self._y(r.a);self._compare(r.x,7)
            if r.p&C:break
        self._x(m[0x6F03]);self._a(255);m[(0x42C+r.x)&65535]=r.a
        self._a(0);m[0x10]=m[0x11]=r.a
        while True:
            self._mark(0xA269);self._x(0);is_ruler=False
            while True:
                self._mark(0xA26B);self._a(m[(0x42C+r.x)&65535]);self._compare(r.a,m[0x10])
                if r.p&Z:is_ruler=True;break
                self._x(r.x+1);self._compare(r.x,7)
                if r.p&C:break
            if not is_ruler:
                self._a(m[0x10]);yield from self._external(0xA27B,0xF2D7,0xA27E,'call')
                if r.pc!=0xA27E:return
                self._y(11);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._a(r.a&3);self._compare(r.a,3)
                if not r.p&Z:m[0x11]=self._nz(m[0x11]+1)
            m[0x10]=self._nz(m[0x10]+1);self._a(m[0x10]);self._compare(r.a,237)
            if r.p&C:break
        self._rts();return

'''}
class PanelStructurer(CityStructurer):
 def procedure(self,e):
  if e in MANUAL:
   body=MANUAL[e];self.stats.append(dict(entry=e,name=self.names[e],instruction_nodes=len(self.graph(e)),source_lines=len(body.splitlines()),hand_written_structured_control=True));return body
  # City-only hand-written bodies belong to physical27/28, not this pair.
  return labelled_procedure(self,e)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--catalog-only',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
 I,tables=collect(rom,pair=25,entries=PUBLIC,stoplocals=(0xB2D7,0xCE1F,0xAFE5));OUT.mkdir(parents=True,exist_ok=True)
 cat=dict(rom_sha256=SHA,original_instructions=sorted(I.values(),key=lambda x:x['pc']),dispatch_tables=list(tables.values()),original_instruction_count=len(I),external_targets=sorted({x['operand']for x in I.values()if x.get('hook')}))
 (OUT/'static-control.json').write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n');print(json.dumps(dict(instructions=len(I),tables=len(tables))),flush=True)
 if a.catalog_only:return
 b=PanelStructurer.__new__(PanelStructurer);b.I=I;b.catalog={'states':[]};b.roots=set(PUBLIC)|{x['operand']for x in I.values()if x['op']=='JSR'and not x.get('hook')};b.roots.update(t for x in I.values()if x['op']=='DISPATCH'for t in x['targets']);b.roots.update(e for e in NAMES if e in I)
 b.roots.update(I[e]['operand']for e in PUBLIC if I[e]['op']=='JMP'and not I[e].get('hook'))
 b.roots.update(tables)
 b.names={e:NAMES.get(e,f'panel_helper_{e:04x}')for e in b.roots};b.stats=[];b.loop_count=b.if_count=0
 h=HEADER.replace('BattleSceneController','CityPanelServices').replace('BattleRegisters','CityPanelRegisters').replace('bank12/13 battle scene controller','bank25/26 city and ruler panel services')
 lo=h.index('STATE,PHASE,');hi=h.index('@dataclass');h=h[:lo]+''.join(f'{v}=0x{k:X}\n'for k,v in FIELDS.items())+'ACTOR_SLOT=OFFICER_INDEX\n\n'+h[hi:]
 h=h.replace('Pinned battle ROM required','Pinned original UI ROM required').replace('pc:int=0xA028','pc:int=0xA02A').replace('entry=0xA028','entry=0xA02A').replace('entry(0xA000','entry(0xA02A').replace('return_pc=0x0200','return_pc=None').replace('if return_pc!=0x0200','if return_pc not in(None,0x0200)')
 h=h.replace('self._return_pc=return_pc;', 'self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;')
 h=h.replace('if self.registers.pc!=self._return_pc:','if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:').replace('self._blocks=0;self._limit=200000','self._blocks=0;self._limit=200000;self._call_owner=None')
 h=h.replace('self.registers=registers or CityPanelRegisters();r=self.registers',"if registers is None:raise ValueError('Supply actual caller registers and an existing RTS frame')\n        self.registers=registers;r=self.registers")
 h+='''    def __call__(self,call):
        if tuple(call.entry_banks[1:3])!=(25,26)or call.target not in self.LOCAL_ENTRIES:
            return {'status':'dependency','reason':'No independent panel owns this exact pair/entry'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns this pending panel'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)

'''
 source=h+'    LOCAL_ENTRIES='+repr(tuple(sorted(b.roots)))+'\n    def _entry(self,entry):\n'
 for i,e in enumerate(sorted(b.roots)):source+=f'        {"if"if i==0 else"elif"} entry==0x{e:04X}:return self.{b.names[e]}()\n'
 source+='        raise ValueError("Entry outside original city panel closure")\n\n'
 for e in sorted(b.roots):
  try:source+=b.procedure(e)
  except Exception as exc:raise ValueError(f'Panel function {e:04X}: {exc}')from exc
 source=source.replace('class CityPanelServices:',loop_exception_source(b.stats)+'class CityPanelServices:')
 ast.parse(source);SOURCE.write_text(source);(OUT/'source-catalog.json').write_text(json.dumps(dict(procedures=b.stats,source_sha256=hashlib.sha256(source.encode()).hexdigest(),structured_ifs=b.if_count,natural_loops=b.loop_count),ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(dict(procedures=len(b.stats),source_bytes=len(source.encode()))))
if __name__=='__main__':main()
