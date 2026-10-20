#!/usr/bin/env python3
"""Actual original6502 differential checks of phase13 readable global UI.

Native snapshots are read-only CPU-fixture inputs. Explicit PPSTATUS/pad input
is supplied to both sides; no software readiness/cache/ack is fabricated. A
CPU helper callback is a validator-only mode, counted independently from the
pure-source mode and strict missing-owner prefixes.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys,random
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.global_ui_controller import (CityUIWorkers,TitleUIController,RulerSelectionUIController,EndingUIController,
    GlobalUIController,UIRegisters,ROM_SHA256,MAIN_TARGETS)
from source.recovered.battle_nmi_services import NMIRegisters,ServiceCall
from source.recovered.service_memory import ServiceMemory
from source.recovered.scene_initialization import SceneInitialization
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.officer_ui_services import OfficerUIServices
from source.recovered.text_scene_services import TextSceneServices
from source.recovered.portrait_ui_services import PortraitUIServices,PortraitData
from source.recovered.officer_details_ui_services import OfficerDetailsUIServices,OfficerDetailsData
from source.recovered.battle_background_initialization import BattleBackgroundInitialization
from source.recovered.scenario_initialization import ScenarioInitialization,ScenarioData
from source.recovered.ui_graphics_initialization import UIGraphicsInitialization,UIGraphicsData
from source.recovered.title_intro_graphics import TitleIntroGraphics,TitleIntroData

OUT=ROOT/'analysis/phase13/global-ui'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def original_origin(memory,pc):
    if pc<0x8000:return None
    bank=memory.banks[(pc-0x8000)//8192];return bank,16+bank*8192+(pc&8191)
class ValidatorCPUHelpers:
    """Original fixed callee execution used only on the comparison side."""
    def __init__(self):self.calls=Counter();self.steps=0
    def __call__(self,call):
        if call.target in(0xEE07,0xE000)or call.target<0xE000:return {'status':'dependency','reason':'Banked/scene body remains an explicit boundary'}
        cpu=MPU(memory=call.memory)
        for k in('a','x','y','p','sp','pc'):setattr(cpu,k,getattr(call.registers,k))
        self.calls[call.target]+=1
        for n in range(50000):
            if n and cpu.pc==call.return_pc and cpu.sp==call.expected_sp:break
            cpu.step()
        else:raise RuntimeError(f'Original helper budget ${call.target:04X}→${cpu.pc:04X}')
        self.steps+=n
        for k in('a','x','y','p','sp','pc'):setattr(call.registers,k,getattr(cpu,k))
        return {'status':'returned'}
def pure_router(memory,rom,counts):
    owners={}
    def callback(call):
        pair=tuple(call.entry_banks[1:3]);target=call.target;key=id(call)
        if key not in owners:
            owner=None;kind=''
            if pair==(29,30)and target in CityUIWorkers.PUBLIC_ENTRIES:owner=CityUIWorkers(memory,rom,callback);kind='city_worker'
            elif pair==(10,11)and target==0xA003:owner=TitleUIController(memory,rom,callback);kind='title'
            elif pair==(8,9)and target==0xA024:owner=RulerSelectionUIController(memory,rom,callback);kind='ruler'
            elif pair==(23,24)and target==0xA01E:owner=EndingUIController(memory,rom,callback);kind='ending'
            elif target==0xF308 or pair==(29,30)and target in OfficerUIServices.ENTRIES:owner=OfficerUIServices(memory,rom,callback);kind='names'
            elif target==0xEE72 or pair==(29,30)and target in TextSceneServices.PUBLIC_ENTRIES:owner=TextSceneServices(memory,rom,callback);kind='text'
            elif pair==(25,26)and target in OfficerDetailsUIServices.LOCAL_ENTRIES:owner=OfficerDetailsUIServices(memory,OfficerDetailsData.from_rom(rom),callback);kind='details'
            elif target==0xF1B7 or pair==(25,26)and target in(0xA000,0xCE1F):owner=PortraitUIServices(memory,PortraitData.from_rom(rom),callback);kind='portrait'
            elif target==0xF09C or pair==(23,24)and target in(0xA009,0xA2FF):owner=BattleBackgroundInitialization(memory,rom,callback);kind='background'
            elif pair==(29,30)and target in ScenarioInitialization.LOCAL_ENTRIES:owner=ScenarioInitialization(memory,ScenarioData.from_rom(rom),callback);kind='scenario'
            elif pair==(23,24)and target in UIGraphicsInitialization.LOCAL_ENTRIES:owner=UIGraphicsInitialization(memory,UIGraphicsData.from_rom(rom),callback);kind='graphics_resources'
            elif pair==(23,24)and target in TitleIntroGraphics.LOCAL_ENTRIES:owner=TitleIntroGraphics(memory,TitleIntroData.from_rom(rom),callback);kind='title_intro'
            elif target in SceneInitialization.FIXED:owner=SceneInitialization(memory,rom,callback);kind='shared'
            else:
                trial=SceneInitialization(memory,rom,callback);result=trial.banked_graphics(call)
                if result['status']=='dependency'and trial._program is None:return result
                if result['status']!='returned':owners[key]=(trial,'graphics')
                counts['graphics']+=1;return result
            owners[key]=(owner,kind);counts[kind]+=1
        owner,kind=owners[key]
        result=owner(call)
        if result.get('status')=='returned':owners.pop(key,None)
        return result
    return callback
def verify(rom,quick=False):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
    counts=Counter();failures=[];rows=[];guards=[];visited=Counter();CPUcallbacks=Counter();sourcecalls=Counter();rng=random.Random(0x13E066)
    parents={name:ROOT/f'analysis/phase11/runtime/cold-battle/{prefix}'for name,prefix in
             [('city-workers','picked-ruler'),('title','title'),('ruler-selection','ruler-confirm'),('global','picked-ruler')]}
    parents['ending']=ROOT/'analysis/phase6/runtime/unification-ending/ending'
    domain_classes={'city-workers':CityUIWorkers,'title':TitleUIController,'ruler-selection':RulerSelectionUIController,'ending':EndingUIController}
    pairs={'city-workers':29,'title':10,'ruler-selection':8,'global':29,'ending':23}
    def memory(domain,prep=None,port_input=True):
        parent=parents[domain];ram=Path(str(parent)+'-ram.bin').read_bytes();sram=Path(str(parent)+'-sram.bin').read_bytes();pair=pairs[domain]
        data_bank=(ram[0xE1]&31)if domain!='global'else 16
        m=ServiceMemory(rom,ram,sram,(data_bank,pair,pair+1,31),
            **({'read_ports':{0x2002:128},'repeat_read_ports':(0x2002,), 'controller_buttons':(0,0)}if port_input else{}))
        # Genuine caller frame of the prepared CPU experiment, not a native trace.
        m[0x1FE:0x200]=bytes([0x67,0x24]);m[0x7C]=0
        # An NMI callee must have its genuine logical selector mirrors too:
        # EE07 restores these mirrors, not the transient physical bank list.
        m[0xE1:0xE4]=bytes([data_bank|32,pair|32,(pair+1)|32])
        for a,v in(prep or{}).items():m[a]=v
        m.io_writes=[];return m
    def compare(domain,entry,prep=None,mode='fixed_CPU',registers=None,tag='',main=False,carry=None,snapshot=None):
        a=memory(domain,prep);b=memory(domain,prep);r=UIRegisters(a=17,x=23,y=31,p=32,sp=253,pc=entry)
        if snapshot is not None:
            meta=json.loads(snapshot.read_text());base=str(snapshot)[:-5]
            saved_ram=Path(base+'-ram.bin').read_bytes();saved_sram=Path(base+'-sram.bin').read_bytes()
            assert hashlib.sha256(saved_ram).hexdigest()==meta['RAM_sha256']and hashlib.sha256(saved_sram).hexdigest()==meta['SRAM_sha256']
            for m in(a,b):m.ram[:]=saved_ram;m.sram[:]=saved_sram;m.banks[:]=meta['banks']
            for k,v in meta['registers'].items():setattr(r,k,v)
        if carry is not None:
            for m in(a,b):
                m.ram[:]=carry['RAM'];m.sram[:]=carry['SRAM'];m.banks[:]=carry['banks']
                m[0x1FE:0x200]=bytes([0x67,0x24]);m[0x7C]=0
        for k,v in(registers or{}).items():setattr(r,k,v)
        initial=vars(r).copy();helper=ValidatorCPUHelpers()if mode=='fixed_CPU'else pure_router(b,rom,sourcecalls)if mode=='pure_source'else None
        source=GlobalUIController(b,rom,helper)if main else domain_classes[domain](b,rom,helper)
        cpu=MPU(memory=a)
        for k,v in initial.items():setattr(cpu,k,v)
        try:
            result=source.run_main(entry,r)if main else source.run_entry(entry,registers=r)
            for n in range(400000):
                if n and cpu.pc==r.pc and cpu.sp==r.sp and a.banks==b.banks:break
                origin=original_origin(a,cpu.pc)
                if origin:visited[(origin[0],cpu.pc,origin[1])]+=1
                cpu.step()
            else:raise RuntimeError(f'Original comparison budget ${cpu.pc:04X} wanted${r.pc:04X}SP{r.sp:02X}')
            # Existing independently verified audio/display helpers contract
            # excludes inactive CPU-stack residue. The new banked closure's
            # fixed-CPU mode additionally compares every byte of RAM.
            scope=list(range(2048))if mode=='fixed_CPU'and not main else sorted(set([*range(0x1B4),*range(0x200,0x800),*(range(0x101+r.sp,0x200) if r.sp<255 else ())]))
            rd=[(i,a.ram[i],b.ram[i])for i in scope if a.ram[i]!=b.ram[i]]
            rg=[(k,getattr(cpu,k),getattr(r,k))for k in('a','x','y','p','sp','pc')if getattr(cpu,k)!=getattr(r,k)]
            assert not rd and not rg and a.sram==b.sram,dict(RAM=rd[:12],registers=rg,SRAM_differences=sum(x!=y for x,y in zip(a.sram,b.sram)))
            assert a.io_writes==b.io_writes and a.io_reads==b.io_reads,dict(ports=(len(a.io_writes),len(b.io_writes)),reads=(len(a.io_reads),len(b.io_reads)))
            comparison='complete_return'if result['status']=='returned'else'strict_prefix'
            if main and result['status']=='returned':assert r.pc==0xE066 and r.sp==initial['sp']
            counts[f'{domain}/{mode}/{comparison}']+=1
            rows.append(dict(domain=domain,entry=entry,tag=tag,mode=mode,comparison=comparison,source_status=result['status'],
                prepared_bytes=prep or{},input_registers=initial,final_registers=vars(r).copy(),final_banks=list(b.banks),
                original_instructions=n,source_control_blocks=result.get('control_blocks'),original_CPU_helper_calls=sum(helper.calls.values())if isinstance(helper,ValidatorCPUHelpers)else 0,
                ports=len(b.io_writes),RAM_scope='all2048'if mode=='fixed_CPU'and not main else'1972+active-stack',
                compared_RAM_byte_count=len(scope),active_stack_start=0x101+r.sp if r.sp<255 else None,
                original_preparation_instructions=carry['instructions']if carry else 0,
                original_caller_snapshot=str(snapshot.relative_to(ROOT))if snapshot else None,
                before=dict(source._before)if hasattr(source,'_before')else None))
            if isinstance(helper,ValidatorCPUHelpers):CPUcallbacks.update(helper.calls)
        except Exception as exc:
            failures.append(dict(domain=domain,entry=entry,tag=tag,mode=mode,preparation=prep or{},error=str(exc),source_PC=r.pc))
            if len(failures)<=12:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
    buttons=(0,1)if quick else(0,1,2,8,16,32,64,128)
    modes=('fixed_CPU','pure_source')
    # All legal title main/sub phases; the reset exit remains a strict E000 dependency.
    for state,phases in enumerate((5,9,3,7,2)):
        for phase in range(phases):
            for button in buttons:
                prep={0x540:state,0x541:phase,0x81:button,0x87:0,0x7E:0,0x7C:0,0x543:0,0x544:0,0xA4:0,0x470:0,0x471:0}
                for mode in modes:compare('title',0xA003,prep,mode,tag=f'main{state}/phase{phase}/buttons{button}')
    for phase in range(7):
        for button in buttons:
            prep={0x540:0,0x541:phase,0x81:button,0x87:0,0x7E:0,0x7C:0,0x545:0,0x546:0,0x547:0,0x548:0,0x549:0,0x46C:0,0x46D:131,0x300:255,0x304:255}
            for mode in modes:compare('ruler-selection',0xA024,prep,mode,tag=f'phase{phase}/buttons{button}')
    for ending_mode,phases in enumerate((1,1,1,1,7,6)):
        for phase in range(phases):
            for button in buttons:
                for animation_step in((0,)if quick else(0,1,128)):
                    prep={0x541:ending_mode,0x542:phase,0x81:button,0x87:255 if animation_step==128 else 0,0x7E:0,0x7C:0,
                          0x4C9:animation_step,0x4CA:0 if animation_step==0 else 1,0x4CB:254 if animation_step==128 else 255,0x4CC:0,0x4CD:0,0x4CE:0,0x4CF:0,
                          0x543:0,0x300:255,0x304:255,0x410:254,0x411:131,0x412:254,0x413:255,0x42C:131,0x42E:255}
                    for mode in modes:compare('ending',0xA01E,prep,mode,tag=f'mode{ending_mode}/phase{phase}/buttons{button}/animation{animation_step}')
    # Animation kinds are indexed0..34, requested by value1..35. Four setup
    # subphases are distinct from the per-kind active effect phase.
    for kind in range(35):
        for mode in modes:compare('city-workers',0xA03F,{0x4A0:kind+1,0x4A1:255,0x4A2:255,0x4A3:0,0x7E:0,0x150:0,0x7C:0},mode,tag=f'animation-positive-request/kind{kind}')
        for phase in range(4):
            for mode in modes:
                compare('city-workers',0xA03F,{0x4A0:128,0x4A1:phase,0x4A2:kind,0x4A3:0,0x7E:0,0x150:0,0x7C:0},mode,tag=f'animation-init/kind{kind}/phase{phase}')
        prep={0x4A0:129,0x4A1:0,0x4A2:kind,0x4A3:0,0x7E:0,0x150:0,0x7C:0}
        for mode in modes:compare('city-workers',0xA03F,prep,mode,tag=f'animation-active/kind{kind}/first-tick')
        if not quick:
            # Each kind initializes its own frame selector. A fabricated phase1
            # is invalid for several kinds, so derive the successor by actually
            # executing its first original tick; no ready/ack is forced.
            m=memory('city-workers',prep);cpu=MPU(memory=m,pc=0xA03F);cpu.sp=253;cpu.a=17;cpu.x=23;cpu.y=31;cpu.p=32
            for n in range(100000):
                if cpu.pc==0x2468:break
                cpu.step()
            else:raise RuntimeError('Original animation fixture preparation did not return')
            carry=dict(RAM=bytes(m.ram),SRAM=bytes(m.sram),banks=list(m.banks),instructions=n)
            for mode in modes:compare('city-workers',0xA03F,None,mode,tag=f'animation-active/kind{kind}/original-successor',carry=carry)
    for kind in range(6):
        for orientation in(0,128):
            for jobs in(0,8):
                for mode in modes:compare('city-workers',0xA009,{0x140:128,0x150:kind|orientation,0x37C:0,0x7E:jobs,0x402:1,0x7C:0},mode,tag=f'panel-open/kind{kind}/orientation{orientation}/jobs{jobs}')
    for job in(0,16,128,129,130,139,143):
        for mode in modes:compare('city-workers',0xA00F,{0x478:job,0x140:0,0x47C:255,0x7E:0,0x151:131,0x152:47,0x153:108,0x154:255,0x47D:1,0x7C:0},mode,tag=f'list-job{job}')
    for phase in range(6):
        for button in buttons:
            for mode in modes:compare('city-workers',0xA039,{0x401:phase,0x81:button,0x87:0,0x7E:0,0x7C:0,0x470:0,0x471:136,0x472:0,0x473:36},mode,tag=f'block-menu/phase{phase}/buttons{button}')
    for timer in(range(4)if quick else range(32)):
        for entry in(0xA021,0xA024,0xA02D):
            for mode in modes:compare('city-workers',entry,{0x5E:timer,0x6F05:timer,0x7E:0},mode,tag=f'header/timer{timer}')
    for state in range(15):
        for mode in modes:
            compare('global',0xE066,{0x7A:state,0x541:0,0x500:0,0x400:1},mode,tag=f'main-state{state}',main=True)
            compare('global',MAIN_TARGETS[state],{0x7A:state,0x541:1,0x500:11,0x400:13},mode,tag=f'direct-state{state}',main=True)
    if not quick:
        # Exact manual two-level loops, with carry/overflow/sign input variants.
        for group in range(8):
            for fade in range(8):
                for p in(32,97):
                    compare('title',0xDD0F,{0:0,1:1,2:32,3:1,0x88:fade},'fixed_CPU',dict(y=group,p=p),tag=f'palette-group{group}/fade{fade}/P{p}')
        for p in(32,33,96,97,160,161,224,225):
            for entry,prep in((0xAEC9,{0x143:0,0x144:128,0x145:0,0x146:128,0x147:64,0x148:35,0x141:0,0x142:36}),
                               (0xCA4E,{0x4A3:1,0x4D4:0,0x4D5:128,0x4D2:0}),
                               (0xCB52,{0x4A3:2,0x4D4:0,0x4D5:128,0x4D2:0,0x4D3:32})):
                compare('city-workers',entry,prep,'fixed_CPU',dict(p=p),tag=f'packet-loop/{entry:04X}/P{p}')
        for _ in range(32):
            state=rng.randrange(5);phase=rng.randrange((5,9,3,7,2)[state]);p=rng.choice((32,33,96,97,160,161,224,225))
            compare('title',0xA003,{0x540:state,0x541:phase,0x81:0,0x7C:0,0x87:0,0x543:0,0x544:0,0xA4:0},'fixed_CPU',dict(p=p,a=rng.randrange(256),x=rng.randrange(256),y=rng.randrange(256)),tag='random-title-register-input')
    snapshot_pins={}
    for snapshot in sorted((ROOT/'analysis/phase13/dependencies/callee-inputs').glob('bank29-*.json')):
        meta=json.loads(snapshot.read_text());entry=meta['CPU']
        if entry not in CityUIWorkers.PUBLIC_ENTRIES:continue
        for mode in modes:compare('city-workers',entry,mode=mode,tag='actual-controller-EE07-caller',snapshot=snapshot)
        for suffix in('.json','-ram.bin','-sram.bin'):
            path=Path(str(snapshot)[:-5]+suffix);snapshot_pins[str(path.relative_to(ROOT))]=sha(path)
    # Strict owner guards: a fake returned PC/SP cannot make None/wait/error a return.
    for outcome in(None,'waiting','error','blocked','returned'):
        b=memory('title',{0x540:0,0x541:0});source=TitleUIController(b,rom)
        def fake(call,value=outcome):
            if value!='returned':call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
            return None if value is None else{'status':value}
        source.services=fake
        assert source.run_entry(0xA003,registers=UIRegisters())['status']=='dependency'
        guards.append('banked_strict_'+str(outcome))
    for outcome in(None,'waiting','error','blocked'):
        b=memory('global');source=GlobalUIController(b,rom)
        def fake_main(call,value=outcome):
            call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
            return None if value is None else{'status':value}
        source.services=fake_main;assert source.run_main(0xE17D,NMIRegisters())['status']=='dependency';guards.append('main_strict_'+str(outcome))
    b=memory('global',{0x7A:15});source=GlobalUIController(b,rom)
    try:source.run_main(registers=NMIRegisters());ok=False
    except ValueError:ok=True
    assert ok;guards.append('main-table-bounded15')
    for domain,entry,prep in(('title',0xD717,{0x540:5}),('ruler-selection',0xD70F,{0x540:1}),('city-workers',0xBE36,{0x4A0:129,0x4A2:35})):
        b=memory(domain,prep);source=domain_classes[domain](b,rom,ValidatorCPUHelpers())
        try:source.run_entry(entry,registers=UIRegisters());ok=False
        except ValueError:ok=True
        assert ok;guards.append(domain+'-inline-table-bound')
    for prep in({0x541:6},{0x541:4,0x542:7},{0x541:5,0x542:6}):
        b=memory('ending',prep);source=EndingUIController(b,rom,ValidatorCPUHelpers())
        try:source.run_entry(0xA01E,registers=UIRegisters());ok=False
        except ValueError:ok=True
        assert ok;guards.append('ending-inline-table-bound-'+str(prep))
    b=memory('global',port_input=False);source=GlobalUIController(b,rom)
    result=source.run_main(0xE09A,NMIRegisters());assert result['status']=='dependency';writes=list(b.io_writes)
    assert source.resume()['status']=='dependency'and b.io_writes==writes;guards.append('missing-real-PPUSTATUS-preserves-prefix')
    b=memory('city-workers');source=GlobalUIController(b,rom);r=UIRegisters(sp=253)
    # The outer owner can resume a banked domain through the same genuine call.
    call=ServiceCall(0xA024,0x2468,'call',r,b,tuple(b.banks),255)
    result=source(call);assert result['status']=='dependency';saved=bytes(b.ram);ports=list(b.io_writes)
    for _ in range(2):assert source.resume()['status']=='dependency'and bytes(b.ram)==saved and b.io_writes==ports
    source.services=pure_router(b,rom,sourcecalls);assert source.resume()['status']=='returned'and r.pc==0x2468 and r.sp==255
    guards.append('facade-resumes-real-banked-owner-without-repeated-prefix')
    pins={f:sha(ROOT/f)for f in('source/recovered/global_ui_controller.py','scripts/analyze_global_ui_controller.py','scripts/verify_global_ui_controller.py',
        'source/recovered/scene_initialization.py','source/recovered/scene_shared_services.py','source/recovered/battle_nmi_services.py','source/recovered/service_memory.py',
        'source/recovered/officer_ui_services.py','source/recovered/text_scene_services.py','source/recovered/portrait_ui_services.py','source/recovered/officer_details_ui_services.py','source/recovered/battle_background_initialization.py',
        'source/recovered/scenario_initialization.py','source/recovered/ui_graphics_initialization.py','source/recovered/title_intro_graphics.py')}
    for parent in parents.values():
        for suffix in('-ram.bin','-sram.bin','.state','.json'):p=Path(str(parent)+suffix);pins[str(p.relative_to(ROOT))]=sha(p)
    pins.update(snapshot_pins)
    complete=sum(v for k,v in counts.items()if k.endswith('/complete_return'));prefix=sum(v for k,v in counts.items()if k.endswith('/strict_prefix'))
    report=dict(schema='phase13-global-UI-actual6502-v1',status='passed'if not failures else'failed',quick=quick,rom_sha256=ROM_SHA256,
        rom_cpu_case_count=complete+prefix,complete_return_count=complete,strict_prefix_count=prefix,source_guard_case_count=len(guards),
        failed_count=len(failures),counts=dict(counts),failures=failures,guards=guards,rows=rows,
        production_original_CPU_callbacks=0,production_IR_interpretation=False,native_internal_CPU_trace=False,
        verification_only_original_CPU_callback_count=sum(CPUcallbacks.values()),verification_only_CPU_helpers={hex(k):v for k,v in CPUcallbacks.items()},
        independent_source_service_calls=dict(sourcecalls),declared_minimum_RAM_addresses=[*range(0x1B4),*range(0x200,0x800)],
        full_RAM_compared_in_banked_fixed_CPU_mode=True,active_stack_frames_additionally_compared=True,all_SRAM_compared_bytes=8192,
        AXYPSPPC_compared=True,ordered_ports_reads_banks_compared=True,pins=pins,
        main_complete_meaning='One main-loop body reaches nextE066 with unchanged callerSP; no RTS/RTI or completeNESframe claim',
        fixture_defaults=dict(caller_frame='Prepared2468 RTS word at01FE/01FF unless an actual callee snapshot is supplied',
            hardware_input=dict(PPUSTATUS=128,controller_buttons=[0,0]),NMI_logical_mirrors='E1=data_bank|32,E2=pair|32,E3=(pair+1)|32 match prepared physical mapping',
            OAM_cursor='7C=0 as an explicit callback-entry fixture input; no PPU queue/readiness/ack consumption is invented',
            animation_successor='35 successor snapshots originate from actual original first ticks; second tick only resets7C and caller frame, no software ack patch'),
        scope='Prepared CPU fixtures from immutable native parent snapshots. PPSTATUS128 and controller0/0 are explicit oracle/source hardware inputs. New banked fixedCPU mode compares2048RAM; independently composed source/global mode compares1972RAM plus active stack frames, excluding unused free-stack residue of existing services. Missing owners stop at matched strictprefix; no software ready/ack invented.')
    (OUT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=o,count=n)for(b,pc,o),n in sorted(visited.items())],indent=2)+'\n')
    print(json.dumps({k:report[k]for k in('status','rom_cpu_case_count','complete_return_count','strict_prefix_count','source_guard_case_count','failed_count','counts')},ensure_ascii=False))
    if failures:raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();verify(a.rom.read_bytes(),a.quick)
