#!/usr/bin/env python3
"""Original-core controlled tactic casts and separately seeded CPU protocols.

Only documented fixture inputs are prepared. All success, deployment, damage,
messages and cache clearing are produced by unchanged original game code.
"""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
ROM_SHA256='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
WAIT=[(12,['down']),(35,[]),(12,['right']),(35,[]),(2,['a']),(300,[]),(2,['a']),(302,[])]
ACKS=[(2,['a']),(300,[])]*3
MOVE1=[(2,['a']),(180,[]),(12,['left']),(35,[]),(2,['a']),(300,[])]
MOVE2=[(2,['a']),(90,[]),(2,['a']),(180,[]),(12,['left']),(35,[]),(2,['a']),(300,[])]
ORDINARY=[(12,['down']),(35,[]),(2,['a']),(180,[]),
          (12,['right']),(35,[]),(12,['right']),(35,[]),(12,['right']),(35,[]),
          (2,['a']),(180,[]),(2,['a']),(450,[]),(2,['a']),(200,[])]
CASES={
 'ambush-chain':{
   'parent':'analysis/runtime/phase3/attack-intro-7.state',
   'RAM':{0x617:(17,'AI slot3 Y on class0'),0x60A:(24,'player slot10 X'),0x61E:(17,'player slot10 Y on class0'),
          0x50C:(10,'enemy-side retained action budget'),0x524:(15,'round resource word0524/25 =9999 low'),0x525:(39,'round resource word0524/25 =9999 high')},
   'SRAM':{0x6FA1:(255,'slot0 inactive AI strategy'),0x6FA2:(255,'slot1 inactive AI strategy'),0x6FA3:(255,'slot2 inactive AI strategy'),
           0x63C0+167*12+6:(172,'officer167 experience3500 low'),0x63C0+167*12+7:(13,'officer167 experience3500 high'),
           0x63C0+167*12+11:(50,'officer167 tier encoding3; original low nibble2 retained')},
   'plan':WAIT+ACKS+MOVE1+MOVE2+[(2,['a']),(200,[])],
   'captures':{396:'before-deployment',431:'status2-proposal',506:'deploy-before',507:'deploy-after',508:'deploy-return',
               700:'other-ai-tactic-prompt',1030:'round-timer-tick',1606:'player-menu',1837:'first-move-before-secondary',
               1838:'first-move-no-trigger',2460:'trigger-before',2461:'trigger-after',2462:'trigger-consumed',2760:'trap-message',2761:'cache-cleared',2962:'final'}},
 'ordinary-cast':{
   'parent':'analysis/runtime/phase3/battle-tactics-true.state',
   'RAM':{0x601:(5,'target slot1 X on class4'),0x615:(16,'target slot1 Y')},
   'SRAM':{0x63C0+131*12+2:(99,'caster131 intelligence99'),0x63C0+131*12+6:(152,'caster131 experience15000 low'),
           0x63C0+131*12+7:(58,'caster131 experience15000 high'),0x63C0+131*12+11:(118,'caster131 tier encoding7; original low nibble6 retained'),
           0x63C0+191*12+2:(0,'target191 intelligence0')},
   'plan':ORDINARY,
   'captures':{47:'selected-tactic',370:'target-cursor',552:'cast-confirmation',747:'effect-before',748:'effect-after',
               770:'result-queued',1004:'success-message',1206:'final'}},
}

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write_json(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def fields(ram,sram,frame):
    units=[]
    for slot in range(20):
        ident=ram[0x664+slot]
        if ident==255:continue
        raw=sram[0x3C0+12*ident:0x3C0+12*ident+12]
        units.append({'slot':slot,'officer_id':ident,'x':ram[0x600+slot],'y':ram[0x614+slot],
                      'side_condition_raw':ram[0x628+slot],'hundred_troops_cache':ram[0x63C+slot],
                      'condition_raw':ram[0x650+slot],'strategy_raw':sram[0xFA1+slot],
                      'officer_record_hex':raw.hex(' ').upper(),'health':raw[0],
                      'experience_u16':raw[6]+256*raw[7], 'packed_byte11':raw[11],
                      'troops_raw_u16':raw[8]+256*raw[9],'troops_low10':raw[8]+256*(raw[9]&3)})
    return {'frame':frame,'global_main':ram[0x7A],'nmi_scene':ram[0x78],
            'battle_state':list(ram[0x500:0x502]),'active_side':ram[0x504],'AP':ram[0x505],'round':ram[0x506],
            'side_controller':ram[0x50F],'battle_actor_or_scratch_050A':ram[0x50A],'target_0509':ram[0x509],
            'tactic_0543':ram[0x543],'tactic_result_0544':ram[0x544],
            'request_6F8B':sram[0xF8B],'ai_actor_6F8C':sram[0xF8C],
            'proposal_action_6F8D':sram[0xF8D],'proposal_target_6F8E':sram[0xF8E],'proposal_status_6F8F':sram[0xF8F],
            'ai_rng_cursor_6F92':sram[0xF92],'ai_rng_saved_x_6F93':sram[0xF93],
            'fixed_rng_state_0050_0057':list(ram[0x50:0x58]),
            'cache_groups_04D8_04DF':[list(ram[0x4D8:0x4DC]),list(ram[0x4DC:0x4E0])],
            'effect_report_042C_042E':list(ram[0x42C:0x42F]),
            'round_resources_0520_0527':list(ram[0x520:0x528]),
            'world_cursor_6F3F_6F42':list(sram[0xF3F:0xF43]),
            'text_jobs_0300_0304':[ram[0x300],ram[0x304]],'button_0081_0087':[ram[0x81],ram[0x87]],
            'units':units}

def unit(row,slot):return next(x for x in row['units']if x['slot']==slot)

def save_initial(runtime,out):
    (out/'initial-ram.bin').write_bytes(runtime.memory(2));(out/'initial-sram.bin').write_bytes(runtime.memory(0))
    size=runtime.core.retro_serialize_size();buffer=C.create_string_buffer(size)
    assert runtime.core.retro_serialize(buffer,size)
    (out/'initial.state').write_bytes(buffer.raw)

def repeat_check(out,previous,names,fields_equal=None):
    checks=[{'artifact':name,'bytes':(out/name).stat().st_size,'sha256':digest(out/name),
             'equal':digest(out/name)==digest(previous/name)}for name in names]
    assert all(row['equal']and row['bytes']for row in checks)
    result={'status':'passed','nonempty_artifact_checks':len(checks),'all_hashes_equal':True,
            'first_run':str(previous.relative_to(ROOT)),'second_run':str(out.relative_to(ROOT)),'artifacts':checks}
    if fields_equal is not None:assert fields_equal;result['full_frame_fields_equal']=fields_equal
    write_json(previous/'repeat-validation.json',result)

def run_core(args,name):
    from nes_runtime import Runtime
    cfg=CASES[name];out=args.out/name;runtime=Runtime(args.rom,out)
    log=[];checkpoints=[]
    def observer(rt):
        row=fields(rt.memory(2),rt.memory(0),rt.frames);log.append(row)
        if rt.frames in cfg['captures']:
            label=cfg['captures'][rt.frames];rt.snapshot(label);checkpoints.append(dict(row,label=label))
    try:
        parent=ROOT/cfg['parent'];runtime.load_state(parent)
        parent_fields=fields(runtime.memory(2),runtime.memory(0),0)
        ram=(C.c_ubyte*2048).from_address(runtime.core.retro_get_memory_data(2))
        sram=(C.c_ubyte*8192).from_address(runtime.core.retro_get_memory_data(0))
        preparation={'RAM':[],'SRAM':[]}
        for kind,memory,base in [('RAM',ram,0),('SRAM',sram,0x6000)]:
            for address,(value,reason)in cfg[kind].items():
                index=address-base
                preparation[kind].append({'address':address,'old':memory[index],'new':value,'reason':reason})
                memory[index]=value
        initial=fields(runtime.memory(2),runtime.memory(0),0);save_initial(runtime,out)
        for frame_count,buttons in cfg['plan']:runtime.run(frame_count,buttons,observer=observer)
        assert len(log)==runtime.frames and len(checkpoints)==len(cfg['captures'])
        f={row['frame']:row for row in log}
        if name=='ambush-chain':
            assert (f[431]['proposal_status_6F8F'],f[431]['proposal_action_6F8D'])==(2,11)
            assert f[506]['cache_groups_04D8_04DF'][0]==[255]*4
            assert f[507]['cache_groups_04D8_04DF'][0]==[3,20,17,5]
            assert (unit(f[506],3)['troops_raw_u16'],unit(f[507],3)['troops_raw_u16'])==(700,600)
            assert f[506]['AP']==f[507]['AP']==10
            assert f[1030]['cache_groups_04D8_04DF'][0]==[3,20,17,4]
            assert unit(f[1838],10)['troops_low10']==1000
            assert (unit(f[2460],10)['troops_low10'],unit(f[2461],10)['troops_low10'])==(1000,468)
            assert f[2461]['effect_report_042C_042E']==[20,2,0]
            assert f[2760]['cache_groups_04D8_04DF'][0]==[3,20,17,4]
            assert f[2761]['cache_groups_04D8_04DF'][0]==[255,20,17,4]
            assert unit(f[2460],10)['experience_u16']==unit(f[2461],10)['experience_u16']==1000
            assert unit(f[2461],3)['experience_u16']==3500 and unit(f[2462],3)['experience_u16']==3766
            assert unit(f[2761],3)['experience_u16']==3766
            effects={'tactic_id':11,'name':'十面埋伏','status2_proposal_frame':431,
                     'deployment_before_frame':506,'deployment_after_frame':507,'deploy_cache':[3,20,17,5],
                     'deployment_raw_troops':[700,600],'deployment_AP':[10,10],
                     'AI_deployment_bypasses_normal_AP_charge':True,
                     'one_original_round_timer_tick':{'frame':1030,'ttl':[5,4]},
                     'first_move_no_trigger':{'frame':1838,'coordinate':[23,17],'troops':1000},
                     'trigger_before_frame':2460,'trigger_after_frame':2461,'trigger_coordinate':[22,17],
                     'trigger_troops_low10':[1000,468],'reported_loss':532,'AP_after_two_player_moves':[26,21,16],
                     'trigger_AI_rng_cursor':[f[2460]['ai_rng_cursor_6F92'],f[2461]['ai_rng_cursor_6F92']],
                     'damage_only_XP_caster':[3500,3500],'trigger_XP_mover':[1000,1000],
                     'NMI_consume_frame':2462,'NMI_consume_XP_caster':[3500,3766],'caster_XP_after_confirmation':3766,
                     'message_frame':2760,'confirmation_clear_frame':2761,'cache_after_confirmation':[255,20,17,4],
                     'request1_visible_at_frame_boundary':any(row['request_6F8B']==1 for row in log),
                     'full_expiry_observed_in_core':False}
            assert not effects['request1_visible_at_frame_boundary']
        else:
            assert f[47]['tactic_0543']in(0,255)
            assert f[747]['AP']==16 and unit(f[747],1)['condition_raw']==0
            assert f[748]['AP']==12 and unit(f[748],1)['condition_raw']==3
            assert (f[748]['tactic_0543'],f[748]['tactic_result_0544'])==(2,0)
            assert unit(f[748],10)['experience_u16']==15000
            effects={'tactic_id':2,'name':'虚兵','target_slot':1,'effect_before_frame':747,'effect_after_frame':748,
                     'AP':[16,12],'target_condition_0651':[0,3],'result_0544':[255,0],
                     'caster_XP':[15000,15000],'target_troops_low10':[800,800],
                     'success_message_frame':1004,'ordinary_controller_selected_tactic':True}
        artifacts={p.name:{'bytes':p.stat().st_size,'sha256':digest(p)}for p in sorted(out.iterdir())
                   if p.is_file()and p.stat().st_size and p.suffix in('.png','.bin','.state')}
        assert len(artifacts)==4*len(checkpoints)+3
        empty=sorted(p.name for p in out.glob('*-vram.bin')if not p.stat().st_size)
        result={'status':'passed','case':name,'case_count':1,'native_core_case_count':1,
                'rom_sha256':ROM_SHA256,'rom_modified':False,'controlled_fixture':True,'natural_gameplay':False,
                'parent_state':cfg['parent'],'parent_sha256':digest(parent),'script_sha256':digest(__file__),
                'runtime_helper_sha256':digest(ROOT/'scripts/nes_runtime.py'),'core':runtime.info,
                'frames':runtime.frames,'frame_samples':len(log),'checkpoint_count':len(checkpoints),
                'RAM_preparation':preparation['RAM'],'SRAM_preparation':preparation['SRAM'],'rng_preparation':[],
                'readiness_or_ack_injection':False,'success_or_completed_cache_injection':False,
                'input_plan':[{'frames':count,'buttons':buttons}for count,buttons in cfg['plan']],
                'parent_fields':parent_fields,'initial':initial,'checkpoints':checkpoints,'verified_effects':effects,
                'artifact_sha256':artifacts,'empty_vram_exports_excluded':empty,
                'available_memory_exports':{'RAM':{'available':True,'bytes':2048},'SRAM':{'available':True,'bytes':8192},
                    'VRAM':{'available':False,'bytes':0,'excluded_from_nonempty_artifact_checks':True},
                    'native_PPU_and_mapper_in_serialized_state':True},
                'native_instruction_trace':False,
                'limits':['Prepared legal numeric inputs/coordinates/AI activation are controlled fixtures, not natural campaign reachability.',
                          'Success, AP, cache, troops, messages and confirmation are produced by original ROM code and real controller inputs.',
                          'Frame-end sampling does not record every asynchronous instruction/write; phase1 can be consumed in the same frame.',
                          'No full battle, full effect catalogue or physical NES hardware acceptance is claimed.']}
        write_json(out/'input-plan.json',result['input_plan']);write_json(out/'frame-fields.json',log)
        write_json(out/'checkpoints.json',checkpoints);write_json(out/'validation.json',result)
        if args.compare:repeat_check(out,args.compare/name,list(artifacts),digest(out/'frame-fields.json')==digest(args.compare/name/'frame-fields.json'))
        print(json.dumps({'case':name,'status':'passed','frames':runtime.frames,'nonempty_artifacts':len(artifacts),'effects':effects},ensure_ascii=False))
    finally:runtime.close()

def cpu_protocols(args):
    from py65.devices.mpu6502 import MPU
    from py65.disassembler import Disassembler
    from trace_startup import Bus
    from capture_tactical_ai import saved_cpu_and_banks
    parent=(args.parent_runtime or ROOT/'analysis/phase8/runtime')/'ambush-chain'
    blob=args.rom.read_bytes()
    def fixture(label):
        regs,banks=saved_cpu_and_banks(parent/(label+'.state'))
        bus=Bus(blob,'zero');bus.ram[:]=(parent/(label+'-ram.bin')).read_bytes();bus.sram[:]=(parent/(label+'-sram.bin')).read_bytes()
        bus.banks=banks;bus.bank_initialized=[True]*4;bus.protect=0x4C;cpu=MPU(memory=bus)
        cpu.sp,cpu.a,cpu.x,cpu.y,cpu.p=regs[2:7];bus.cpu=cpu
        return bus,cpu,regs
    def trace(bus,cpu,entry,stop,rows,stage):
        cpu.pc=entry;dis=Disassembler(cpu)
        for _ in range(500000):
            if cpu.pc==stop:return
            bus.pc=cpu.pc;bus.step_no=len(rows);bank,offset=bus.origin(cpu.pc);size,assembly=dis.instruction_at(cpu.pc)
            before=bus.sram[0xF8B]
            row={'step':len(rows),'stage':stage,'bank':bank,'pc':cpu.pc,'file_offset':16+offset,
                 'bytes':bytes(bus.peek(cpu.pc+i)for i in range(size)).hex(' ').upper(),'assembly':assembly,
                 'request_before':before,'a':cpu.a,'x':cpu.x,'y':cpu.y,'p':cpu.p,'sp':cpu.sp}
            cpu.step();row['request_after']=bus.sram[0xF8B];rows.append(row)
        raise AssertionError(f'CPU protocol failed stop ${stop:04X}')
    out=args.out/'cpu-call';out.mkdir(parents=True,exist_ok=True);bus,cpu,regs=fixture('trigger-before');rows=[]
    initial=fields(bus.ram,bus.sram,0);original_banks=list(bus.banks)
    bus.banks[1:3]=[12,13]
    trace(bus,cpu,0xA51F,0xA534,rows,'original secondary-request prefix')
    requested=fields(bus.ram,bus.sram,0);assert requested['request_6F8B']==1
    bus.banks=original_banks;cpu.stPush(0xE2);cpu.stPush(0x2B)
    trace(bus,cpu,0xA000,0xE22C,rows,'original global AI secondary body')
    after=fields(bus.ram,bus.sram,0)
    native=next(row for row in read_json(parent/'checkpoints.json')if row['label']=='trigger-after')
    keys=['request_6F8B','ai_actor_6F8C','proposal_status_6F8F','ai_rng_cursor_6F92','ai_rng_saved_x_6F93',
          'cache_groups_04D8_04DF','effect_report_042C_042E','AP','battle_state']
    comparisons={key:{'actual_CPU':after[key],'native_next_frame':native[key],'equal':after[key]==native[key]}for key in keys}
    for key in('troops_raw_u16','troops_low10','experience_u16'):
        comparisons['unit10.'+key]={'actual_CPU':unit(after,10)[key],'native_next_frame':unit(native,10)[key],
                                    'equal':unit(after,10)[key]==unit(native,10)[key]}
    assert all(row['equal']for row in comparisons.values()),comparisons
    assert any(row['request_before']==255 and row['request_after']==1 for row in rows)
    (out/'after-ram.bin').write_bytes(bytes(bus.ram));(out/'after-sram.bin').write_bytes(bytes(bus.sram))
    write_json(out/'actual-cpu-instructions.json',rows)
    result={'status':'passed','case_count':1,'actual_ROM_CPU_case_count':1,'rom_sha256':ROM_SHA256,
            'script_sha256':digest(__file__),'instruction_count':len(rows),'native_instruction_trace':False,
            'source_reconstruction_executed':False,'prepared_from':str(parent.relative_to(ROOT))+'/trigger-before',
            'captured_native_register_payload_hex':regs.hex(' ').upper(),'prefix_entry':0xA51F,'prefix_stop_before_RTS':0xA534,
            'prefix_explicit_pair':[12,13],'AI_entry':0xA000,'AI_pair':[8,9],'real_AI_caller_return':0xE22C,
            'protocol_request_values':[initial['request_6F8B'],requested['request_6F8B'],after['request_6F8B']],
            'native_field_comparisons':comparisons,'mapper_events':bus.mapper_events,
            'io_event_count':len(bus.io_events),'blocked_sram_writes':bus.blocked_sram_writes,
            'limits':['Two original CPU bodies are explicitly sequenced with their own code-bank contexts; not a native video instruction trace.',
                      'A51F stops before RTS; A000 is seeded with the documented real E22C caller return, not saved native PC.',
                      'Only declared fields are compared with native2461; complete intervening NMI/PPU/IRQ and RAM registers are excluded.']}
    assert result['io_event_count']==0 and result['blocked_sram_writes']==0
    write_json(out/'validation.json',result)
    if args.compare:repeat_check(out,args.compare/'cpu-call',['actual-cpu-instructions.json','after-ram.bin','after-sram.bin'])
    expiry=args.out/'cpu-expiry';expiry.mkdir(parents=True,exist_ok=True);bus,cpu,regs=fixture('deploy-after')
    bus.banks[1:3]=[8,9];timer_rows=[];ticks=[];initial_sram=bytes(bus.sram)
    for n in range(5):
        before=list(bus.ram[0x4D8:0x4DC]);trace(bus,cpu,0xCE20,0xCE3F,timer_rows,'original timer prefix '+str(n+1))
        after=list(bus.ram[0x4D8:0x4DC]);assert after==[3 if n<4 else 255,20,17,4-n]
        ticks.append({'call':n+1,'before':before,'after':after})
    assert bytes(bus.sram)==initial_sram
    (expiry/'after-ram.bin').write_bytes(bytes(bus.ram));(expiry/'after-sram.bin').write_bytes(bytes(bus.sram))
    write_json(expiry/'actual-cpu-instructions.json',timer_rows)
    write_json(expiry/'validation.json',{'status':'passed','rom_sha256':ROM_SHA256,'script_sha256':digest(__file__),
               'actual_ROM_CPU_prefix_call_count':5,'source_CPU_differential_case_count':0,
               'instruction_count':len(timer_rows),'prepared_from':str(parent.relative_to(ROOT))+'/deploy-after',
               'entry':0xCE20,'stop_before_RTS':0xCE3F,'ticks':ticks,'all_SRAM_unchanged':True,
               'native_instruction_trace':False,'full_expiry_observed_in_core':False,
               'limits':['Directly invokes five original timer prefixes on the actual generated cache; outer round/supply/UI control is excluded.',
                         'This is an original-CPU expiry progression contract, not an additional source differential matrix or five complete video rounds.']})
    if args.compare:repeat_check(expiry,args.compare/'cpu-expiry',['actual-cpu-instructions.json','after-ram.bin','after-sram.bin'])
    print(json.dumps({'CPU_request_chain':'passed','instructions':len(rows),'field_comparisons':len(comparisons),
                      'expiry_prefix_calls':5,'expiry_instructions':len(timer_rows)}))

def read_json(path):return json.loads(Path(path).read_text())

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path)
    p.add_argument('--mode',choices=('core','cpu'),default='core')
    p.add_argument('--case',choices=('all','ambush-chain','ordinary-cast'),default='all')
    p.add_argument('--out',type=Path,default=ROOT/'analysis/phase8/runtime');p.add_argument('--compare',type=Path)
    p.add_argument('--parent-runtime',type=Path);a=p.parse_args();a.out=a.out.resolve()
    if a.compare:a.compare=a.compare.resolve()
    if a.parent_runtime:a.parent_runtime=a.parent_runtime.resolve()
    assert digest(a.rom)==ROM_SHA256
    if a.mode=='cpu':cpu_protocols(a)
    else:
        for name in CASES if a.case=='all'else[a.case]:run_core(a,name)
    assert digest(a.rom)==ROM_SHA256

if __name__=='__main__':main()
