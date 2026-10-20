#!/usr/bin/env python3
"""Offline structuring of exact bank29 text/packet caller protocols.

Game-data command pointers80..9F are a bounded parser table. Production never
reads this offline graph, opcodes or IR, and preserves hardware read waits.
"""
import argparse,ast,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from inspect_game_data import OPS,SIZES
from analyze_battle_scene_controller import Structurer,HEADER,BRANCHES
import analyze_battle_scene_controller as BASE
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase12/text';SOURCE=ROOT/'source/recovered/text_scene_services.py'
ENTRIES=(0xA000,0xA003,0xA006,0xA048,0xA11B,0xA154,0xA158,0xEE72)
NAMES={0xA000:'text_consumer_entry',0xA003:'text_producer_entry',0xA006:'packet_consumer_entry',0xA048:'consume_text',0xA11B:'consume_nametable_packets',0xA154:'produce_text',0xA158:'begin_text_row',0xA1C8:'parse_text_tokens',0xA1DF:'advance_text_pointer',0xA1E8:'emit_text_symbol',0xA248:'end_message',0xA281:'next_text_row',0xA2A3:'enter_nested_message',0xA2C2:'restore_nested_message',0xA2DD:'enable_burst',0xA2E5:'disable_burst',0xA2ED:'set_next_position',0xA310:'disable_accents',0xA318:'enable_accents',0xA320:'set_symbol_offset',0xA32D:'report_officer_name',0xA397:'parameterized_officer_name',0xA3B1:'report_decimal_number',0xA426:'fixed_city_name',0xA4B0:'fixed_officer_name',0xA53E:'formatted_field_number',0xA60F:'clear_text_rows',0xA61D:'message_pointer',0xA690:'select_message_window'}
class TextStructurer(Structurer):
 def simple(self,item):
  if item['op']=='LDA'and item['mode']=='abs'and item['operand']==0x2002:
   return [f'self._a((yield from self._hardware_read(0x2002,0x{item["pc"]:04X})))']
  return super().simple(item)
def collect(rom):
 I={};todo=list(ENTRIES);modes={'zp':'zpg','ab':'abs','im':'imm','a':'acc','ix':'inx','iy':'iny','i':'imp','rel':'rel'}
 while todo:
  pc=todo.pop()
  if pc in I:continue
  assert 0xA000<=pc<0xA6A7 or pc==0xEE72,hex(pc)
  bank=31 if pc==0xEE72 else 29
  file=16+bank*8192+(pc&8191);op,mode=OPS[rom[file]];size=SIZES[mode];value=int.from_bytes(rom[file+1:file+size],'little');nxt=pc+size
  if op in BRANCHES:value=(nxt+(value if value<128 else value-256))&65535
  x=dict(pc=pc,physical_bank=bank,bank=bank,rom_offset=file,op=op,mode=modes.get(mode,mode),operand=value,next_pc=nxt,raw_hex=rom[file:file+size].hex())
  if op=='JSR'and value==0xEADE:
   assert pc==0xA205;table=file+3;targets=tuple(int.from_bytes(rom[table+2*i:table+2*i+2],'little')for i in range(32));x.update(op='DISPATCH',targets=targets);todo.extend(targets)
  elif op in('JSR','JMP')and value>=0xE000:x['hook']='fixed service'
  op=x['op']
  if op in('RTS','DISPATCH'):pass
  elif op=='JMP':
   if not x.get('hook'):todo.append(value)
  elif op in BRANCHES:todo.extend((value,nxt))
  else:
   assert op!='?',hex(pc);todo.append(nxt)
   if op=='JSR'and not x.get('hook'):todo.append(value)
  I[pc]=x
 return I
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==SHA
 I=collect(rom);b=TextStructurer.__new__(TextStructurer);b.I=I;b.catalog={'states':[]};b.roots=set(ENTRIES)|{v['operand']for v in I.values()if v['op']=='JSR'and not v.get('hook')}
 NAMES.update({0xA132:'next_nametable_packet',0xA146:'write_nametable_packet_tiles',0xEE72:'palette_cadence_tail'})
 b.roots.update(t for v in I.values()if v['op']=='DISPATCH'for t in v['targets']);b.roots.update(v for v in NAMES if v in I);b.names={v:NAMES.get(v,f'text_helper_{v:04x}')for v in b.roots};b.stats=[];b.loop_count=b.if_count=0
 header=HEADER.replace('BattleSceneController','TextSceneServices').replace('BattleRegisters','TextRegisters').replace('bank12/13 battle scene controller','bank29 text and nametable packet services')
 lo=header.index('STATE,PHASE,');hi=header.index('@dataclass')
 header=header[:lo]+'TEXT_PROGRESS,TEXT_CURSOR,MESSAGE_HEAD=0x300,0x304,0x310\nNEW_BUTTONS,GLOBAL,PPU_JOBS=0x81,0x7A,0x7E\n\n'+header[hi:]
 header=header.replace('self.memory[STATE],self.memory[PHASE],self.memory[ACTOR_SLOT]','self.memory[TEXT_PROGRESS],self.memory[TEXT_CURSOR],self.memory[MESSAGE_HEAD]')
 header=header.replace('entry=0xA028','entry=0xA003').replace('pc:int=0xA028','pc:int=0xA003')
 header=header.replace('return_pc=0x0200','return_pc=None').replace('if return_pc!=0x0200','if return_pc not in(None,0x0200)')
 header=header.replace('self._return_pc=return_pc;', 'self._return_pc=((self.memory[0x100+((r.sp+1)&255)]|self.memory[0x100+((r.sp+2)&255)]<<8)+1)&65535 if return_pc is None else return_pc;self._return_sp=(r.sp+2)&255;')
 header=header.replace('if self.registers.pc!=self._return_pc:', 'if self.registers.pc!=self._return_pc or self.registers.sp!=self._return_sp:')
 header=header.replace('            if self.pending is not None:\n                call=self.pending','            if isinstance(self.pending,ServiceWait):self.pending=None\n            if self.pending is not None:\n                call=self.pending')
 header=header.replace('            try:self.pending=next(self._program)','            try:\n                self.pending=next(self._program)\n                if isinstance(self.pending,ServiceWait):return self._result("dependency")')
 extra='''    PUBLIC_ENTRIES=(0xA000,0xA003,0xA006,0xA048,0xA11B,0xA154,0xA158,0xEE72)
    def __call__(self,call):
        if (tuple(call.entry_banks[1:3])!=(29,30)and call.target!=0xEE72)or call.target not in self.PUBLIC_ENTRIES:
            return {'status':'dependency','reason':'Not an exact bank29 text/packet entry'}
        if self._program is not None:
            if self._call_owner is not call:return {'status':'dependency','reason':'Another caller owns the pending text read'}
            return self.resume()
        self._call_owner=call
        return self.run_entry(call.target,registers=call.registers,return_pc=call.return_pc)
    def _hardware_read(self,address,pc):
        while True:
            self.registers.pc=pc
            try:return self.memory[address]
            except UnsupportedHardware as exc:yield ServiceWait('hardware_read',pc,address,reason=str(exc))

'''
 source=header+extra+'    def _entry(self,entry):\n'
 for i,e in enumerate(sorted(b.roots)):source+=f'        {"if"if i==0 else"elif"} entry==0x{e:04X}:return self.{b.names[e]}()\n'
 source+='        raise ValueError("Entry outside the bounded text service catalog")\n\n'
 for e in sorted(b.roots):source+=b.procedure(e)
 ast.parse(source);SOURCE.write_text(source);OUT.mkdir(parents=True,exist_ok=True)
 raw=[]
 for name,lo,size in [('command_pointers32',0xA208,64),('number_widths',0xA607,8),('message_selectors15',0xA6A7,15)]:
  file=16+29*8192+(lo&8191);data=rom[file:file+size];raw.append(dict(name=name,physical_bank=29,cpu_address=lo,rom_offset=file,bytes=size,raw_hex=data.hex(),sha256=hashlib.sha256(data).hexdigest()))
 e=dict(status='passed',rom_sha256=SHA,source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),analyzer_path='scripts/analyze_text_scene_services.py',original_instructions=list(sorted(I.values(),key=lambda v:v['pc'])),tables=raw,procedures=b.stats,procedures_count=len(b.roots),original_instruction_count=len(I),source_IR_interpretation=False,source_original_CPU_callbacks=0,REA_archive='analysis/rea/pairs/pair-29',dependencies={'scripts/analyze_battle_scene_controller.py':hashlib.sha256((ROOT/'scripts/analyze_battle_scene_controller.py').read_bytes()).hexdigest()})
 (OUT/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:e[k]for k in('status','procedures_count','original_instruction_count','source_sha256')}))
if __name__=='__main__':main()
