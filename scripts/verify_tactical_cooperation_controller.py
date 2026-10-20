#!/usr/bin/env python3
"""Original ROM vs direct source tactical body, caller protocol and strict waits.

Source services are independent fixed F266 only. The oracle alone executes
unchanged6502; no old tactical IR/executor is imported by this validator.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from verify_battle_scene_controller import ObservableBus
from source.recovered.tactical_cooperation_controller import TacticalCooperationController,TacticalRegisters,ROM_SHA256
from source.recovered.scene_shared_services import SceneSharedServices
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import ServiceCall,ServiceWait
from source.recovered.tactical_strategy_ai import StrategyData
from source.recovered.terrain_rules import city_chunks

REGS=('a','x','y','p','sp','pc')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def reg(r):return {k:getattr(r,k)for k in REGS}
def verify(rom,out,quick=False):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    catalog=json.loads((ROOT/'analysis/phase14/tactical/static-catalog.json').read_text())
    base=ROOT/'analysis/runtime/phase3/attack-intro-7';ram=Path(str(base)+'-ram.bin').read_bytes();sram=Path(str(base)+'-sram.bin').read_bytes()
    counts=Counter();failures=[];rows=[];visited=Counter();source_service_calls=Counter();guards=[];native_inputs={}
    def fresh(actor=0,side=0,ap=15):
        r=bytearray(ram);s=bytearray(sram);r[0xDE:0xE4]=bytes((38,40,41,38,40,41));r[0x504]=side;r[0x505]=ap
        s[0xF8B]=0;s[0xF8C]=actor;s[0xF94:0xF97]=bytes(3);s[0xFA1:0xFB5]=bytes([255]*20);s[0xFA1+actor]=0
        r[0x4D8:0x4E0]=bytes([255]*8);r[0x20:0x3B]=bytes(0x1B)
        return r,s
    def bus(r,s,banks):
        b=ObservableBus(rom,r,s);b.banks=list(banks);b.ports=[];b.port_reads=[];return b
    def record_actual(b,cpu):
        origin=b.origin(cpu.pc)
        if origin is None:raise RuntimeError(f'Original unexpectedly entered RAM ${cpu.pc:04X}')
        visited[(origin[0],cpu.pc,origin[1]+16)]+=1;b.pc=cpu.pc
    def equal(actual,m,r,cpu):
        rd=[(i,a,b)for i,(a,b)in enumerate(zip(actual.ram,m.ram))if a!=b]
        sd=[(i,a,b)for i,(a,b)in enumerate(zip(actual.sram,m.sram))if a!=b]
        rg={k:(getattr(cpu,k),getattr(r,k))for k in REGS if getattr(cpu,k)!=getattr(r,k)}
        assert not rd and not sd and not rg,dict(RAM=rd[:12],SRAM=sd[:10],registers=rg)
        assert actual.ports==m.io_writes and actual.banks==m.banks and not actual.port_reads
    def compare(group,entry,raw_ram,raw_sram,inputs=None,*,banks=(6,8,9,31),stop=0xE22C,mode='complete',limit=200000,meta=None):
        initial=dict(a=17,x=31,y=63,p=32,sp=253,pc=entry);initial.update(inputs or{})
        b=bus(raw_ram,raw_sram,banks);sp=initial['sp'];word=stop-1
        b.ram[0x100+((sp+1)&255)]=word&255;b.ram[0x100+((sp+2)&255)]=word>>8
        m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));shared=SceneSharedServices(m,rom)
        def service(call):
            source_service_calls[call.target]+=1
            if call.target!=0xF266:return {'status':'dependency','reason':'Validator source supports only recovered F266'}
            return shared(call)
        r=TacticalRegisters(**initial);ctrl=TacticalCooperationController(m,rom,service if mode!='missing_F266'else None)
        c=MPU(memory=b);b.cpu=c
        for k,v in initial.items():setattr(c,k,v)
        try:
            result=ctrl.run_entry(entry,registers=r,max_blocks=limit)
            if mode=='budget':assert result['status']=='budget',result
            elif mode=='missing_F266':assert result['status']=='dependency'and isinstance(ctrl.pending,ServiceCall),result
            else:assert result['status']=='returned',result
            for n in range(1500000):
                boundary=(c.pc==r.pc and c.sp==r.sp and b.banks==m.banks and len(b.ports)==len(m.io_writes))
                if boundary and (n or mode!='complete'):
                    if mode=='complete' or (reg(c)==reg(r)and b.ram==m.ram and b.sram==m.sram):break
                record_actual(b,c);b.step_no=n;c.step()
            else:raise RuntimeError(f'Original budget at ${c.pc:04X}')
            equal(b,m,r,c)
            boundary='complete_return'if mode=='complete'else'strict_prefix'
            counts[group+':'+boundary]+=1
            rows.append(dict(group=group,comparison=boundary,entry=entry,input=meta,initial_registers=initial,source_status=result['status'],
                original_instructions=n,source_blocks=result['control_blocks'],final_registers=reg(r),final_banks=list(m.banks),
                before=result['before'],after=result['after'],port_writes=list(m.io_writes),source_original_CPU_callbacks=0))
            if mode in('budget','missing_F266'):
                before=(bytes(m.ram),bytes(m.sram),reg(r),list(m.io_writes),list(m.banks));again=ctrl.resume()
                assert again['status']==result['status']and before==(bytes(m.ram),bytes(m.sram),reg(r),list(m.io_writes),list(m.banks))
                guards.append(dict(name='same_pending_does_not_fake_complete',group=group))
                if mode=='budget':continued=ctrl.resume(max_blocks=200000)
                else:ctrl.services=service;continued=ctrl.resume()
                assert continued['status']=='returned',continued
                for extra in range(1500000):
                    if c.pc==r.pc and c.sp==r.sp:break
                    record_actual(b,c);c.step()
                else:raise RuntimeError('Original resumed budget')
                equal(b,m,r,c);counts[group+'_resumed:complete_return']+=1
                rows.append(dict(group=group+'_resumed',comparison='complete_return',entry=entry,input=meta,original_instructions=extra,
                    final_registers=reg(r),final_banks=list(m.banks),source_original_CPU_callbacks=0))
            return bytes(m.ram),bytes(m.sram),result
        except Exception as exc:
            failures.append(dict(group=group,entry=entry,input=meta,error=str(exc),source_PC=r.pc))
            if len(failures)<=6:print(json.dumps(failures[-1]),flush=True)
            return raw_ram,raw_sram,None
    def officer(r,s,slot,**values):
        ident=r[0x664+slot];assert ident<237;offset=0x3C0+12*ident
        for key,value in values.items():
            if key=='troops':s[offset+8]=value&255;s[offset+9]=value>>8
            else:s[offset+dict(hp=0,iq=2,loyalty=3,flags=11)[key]]=value
    # Exact raw request modes, without illegal strategy-table accesses.
    for request in(range(0,256,17)if quick else range(256)):
        r,s=fresh();s[0xF8B]=request;s[0xFA1:0xFB5]=bytes([255]*20)
        compare('request_byte_modes',0xA000,r,s,dict(a=request,x=request*3&255,y=request*5&255,p=(request|32)&~8),meta=request)
    # Strategies0..7 as cooperative updates, with both signed sides/AP edges
    # and only the four known meaningful valid original-layout conditions.
    for strategy in range(8):
        for side in(0,128):
            actor=10 if side else 0;enemy=0 if side else 10
            for ap in((0,15)if quick else(0,1,2,3,5,10,15,255)):
                for variant in(range(1)if quick else range(4)):
                    r,s=fresh(actor,side,ap);s[0xF94]=actor;s[0xFA1:0xFB5]=bytes([255]*20);s[0xFA1+actor]=strategy
                    r[0x650+actor]=(0,4,128,64)[variant];r[0x600+actor]=(2,2,15,20)[variant];r[0x614+actor]=(14,16,17,13)[variant]
                    r[0x600+enemy]=(3,17,16,2)[variant];r[0x614+enemy]=(14,16,17,16)[variant]
                    compare('all_eight_cooperative_strategies',0xA02D,r,s,dict(a=65,x=actor,y=enemy,p=32|(variant&1)),meta=[strategy,side,ap,variant])
    # The28 previously exposed functional entries are checked from current
    # byte-derived addresses. Tail join functions are not entered at random.
    entries=[('secondary',0xB933),('scan',0xA03C),('dispatch_strategy',0xA099),('update',0xA02D)]
    entries+=[('strategy_'+str(i),v)for i,v in enumerate(catalog['inline_tables'][0]['targets'])]
    entries+=[('predicate_'+str(i),v)for i,v in enumerate(catalog['inline_tables'][1]['targets'])]
    for name,entry in entries:
        for variant in(range(1)if quick else range(4)):
            r,s=fresh();actor=0 if variant&1 else 10;s[0xF8C]=actor;s[0xF8E]=10 if actor==0 else 0
            r[0x504]=0 if actor==0 else 128;r[0x505]=(0,5,15,255)[variant]
            r[0x20]=(0,2,15,20)[variant];r[0x21]=(0,14,16,31)[variant]
            if name=='dispatch_strategy':s[0xFA1+actor]=variant
            compare('functional_entries',entry,r,s,dict(a=variant,x=actor,y=actor,p=(32,33,96,225)[variant]),meta=[name,variant])
    for variant in range(2 if quick else 16):
        r,s=fresh();s[0xFA1:0xFB5]=bytes([255]*20);r[0x505]=variant%6
        for slot in(0,1,2,3,10):s[0xFA1+slot]=(variant+slot)%8
        if variant&1:r[0x664+1]=255
        if variant&2:r[0x628+2]=128
        s[0xF94]=(variant*3)%20
        for tick in range(3):r,s,_=compare('consecutive_scan_updates',0xA02D,r,s,meta=[variant,tick])
    for side in(0,128):
        for variant in range(2 if quick else 16):
            r,s=fresh(10 if side else 0,side);s[0xF8B]=1;s[0xF8C]=10 if side else 0;r[0x4D8:0x4E0]=bytes([variant%20,0,0,5,variant%20,0,0,5])
            compare('secondary_cache_update',0xB933,r,s,meta=[side,variant])
    # Local ambush cache consumer state includes the original byte quirks;
    # it is not a claim to draw its later loss message/experience screen.
    data=StrategyData.from_rom(rom)
    for service,entry in((0,0xA329),(2,0xA507)):
        for city in((4,)if quick else(0,4,12,20,29)):
            tx,ty=data.service_coordinates[city][service]
            if not(1<=tx<30 and 0<=ty<20 and ty!=15):continue
            for gold in((49,50)if quick else(0,49,50,100,9999,65535)):
                r,s=fresh();r[0x50E]=city;r[0xAA:0xAE]=bytes(city_chunks(rom,city));r[0x600]=tx-1;r[0x614]=ty;r[0x505]=255
                for slot in range(1,20):r[0x664+slot]=255
                r[0x650]=0;r[0x526]=gold&255;r[0x527]=gold>>8;r[0x522]=100;r[0x523]=0;r[0x506]=1
                officer(r,s,0,hp=40,troops=1000);s[0xF92]=127
                compare('service_arrival_resource_boundaries',entry,r,s,meta=[service,city,gold])
    for sp in((0,1,253,255)if quick else(0,1,2,127,128,253,254,255)):
        r,s=fresh();s[0xF8B]=255
        compare('real_global_E22C_return',0xA000,r,s,dict(a=113,x=225,y=40,sp=sp,p=229),meta=sp)
    # Both inline tables: isolated B517 prefix terminates at the selected
    # strategy/predicate entry. No target body or RTS is claimed here.
    protocol_cases=[]
    for t in catalog['inline_tables']:
        for index in range(t['count']):
            for sp in((0,255)if quick else(0,1,2,127,128,253,254,255)):protocol_cases.append((t,index,sp))
    if not quick:
        for sp in range(256):
            t=catalog['inline_tables'][sp&1];protocol_cases.append((t,sp%t['count'],sp))
    for t,index,sp in protocol_cases:
        raw_r,raw_s=fresh();word=t['call_pc']+2
        raw_r[0x100+sp]=word>>8;raw_r[0x100+((sp-1)&255)]=word&255
        b=bus(raw_r,raw_s,(6,8,9,31));m=ServiceMemory(rom,b.ram,b.sram,tuple(b.banks));r=TacticalRegisters(a=index,x=sp*3&255,y=sp,p=sp|32,sp=sp,pc=t['call_pc'])
        ctrl=TacticalCooperationController(m,rom);ctrl.registers=r;cpu=MPU(memory=b,pc=0xB517);b.cpu=cpu
        cpu.a=r.a;cpu.x=r.x;cpu.y=r.y;cpu.p=r.p;cpu.sp=(sp-2)&255
        try:
            ctrl._dispatch(t['call_pc'],tuple(t['targets']))
            for n in range(64):
                if cpu.pc==r.pc and cpu.sp==r.sp:break
                record_actual(b,cpu);cpu.step()
            else:raise RuntimeError('B517 original boundary budget')
            equal(b,m,r,cpu);counts['B517_protocol_boundary:strict_prefix']+=1
        except Exception as exc:failures.append(dict(group='B517_protocol_boundary',index=index,sp=sp,error=str(exc)))
    # Reuse every frozen phase7 natural end-of-frame RAM/SRAM; this is a
    # synchronous source/CPU callback, not a new nativeframe or internaltrace.
    for path in sorted((ROOT/'analysis/phase7/runtime/natural-turn').glob('*-ram.bin')):
        sr=path.with_name(path.name.replace('-ram.bin','-sram.bin'));r=bytearray(path.read_bytes());s=bytearray(sr.read_bytes())
        native_inputs[str(path.relative_to(ROOT))]=sha(path);native_inputs[str(sr.relative_to(ROOT))]=sha(sr)
        compare('natural_snapshot_synchronous_call',0xA000,r,s,banks=(r[0xDE]&31,8,9,31),meta=path.stem)
    # Prefixes preserve real calls and resume only after an explicit budget
    # extension or actual pureF266 completion, never a forged readiness flag.
    for budget in(0,8):
        r,s=fresh();s[0xFA1:0xFB5]=bytes([255]*20)
        compare('explicit_block_budget',0xA000,r,s,mode='budget',limit=budget,meta=budget)
    r,s=fresh()
    compare('missing_F266_real_call_prefix',0xB4E1,r,s,mode='missing_F266',meta='template record data window')
    # Source guard domains are rejected before table-external original bytes
    # are executed; helpers maintain the existing caller rather than seed it.
    for t in catalog['inline_tables']:
        for index in(t['count'],255):
            r,s=fresh();m=ServiceMemory(rom,r,s,(6,8,9,31));ctrl=TacticalCooperationController(m,rom);ctrl.registers=TacticalRegisters(a=index)
            before=(bytes(m.ram),bytes(m.sram),reg(ctrl.registers))
            try:ctrl._dispatch(t['call_pc'],tuple(t['targets']))
            except ValueError:pass
            else:raise AssertionError('Missing inline table guard')
            assert before==(bytes(m.ram),bytes(m.sram),reg(ctrl.registers));guards.append(dict(name='out_of_table_index',table=t['call_pc'],index=index))
    for label,kwargs in [('missing_actual_registers',{}),('decimal_protocol',dict(registers=TacticalRegisters(p=40))),('negative_budget',dict(registers=TacticalRegisters(),max_blocks=-1))]:
        r,s=fresh();m=ServiceMemory(rom,r,s,(6,8,9,31));ctrl=TacticalCooperationController(m,rom);before=(bytes(m.ram),bytes(m.sram))
        try:ctrl.run_entry(**kwargs)
        except ValueError:pass
        else:raise AssertionError(label)
        assert before==(bytes(m.ram),bytes(m.sram));guards.append(dict(name=label))
    r,s=fresh();m=ServiceMemory(rom,r,s,(6,12,13,31));r=TacticalRegisters(pc=0xA000);before=(bytes(m.ram),bytes(m.sram),reg(r))
    res=TacticalCooperationController(m,rom)(ServiceCall(0xA000,0xE22C,'wrong_pair',r,m,(6,12,13,31),255))
    assert res['status']=='dependency'and before==(bytes(m.ram),bytes(m.sram),reg(r));guards.append(dict(name='wrong_physical_pair'))
    for status in(None,'waiting','blocked','returned_without_pop'):
        raw_r,raw_s=fresh();m=ServiceMemory(rom,raw_r,raw_s,(6,8,9,31));r=TacticalRegisters(a=17)
        m[0x1FE]=0x2B;m[0x1FF]=0xE2
        def bad(call,status=status):
            if status!='returned_without_pop':call.registers.pc=call.return_pc;call.registers.sp=call.expected_sp
            return None if status is None else {'status':'returned'if status=='returned_without_pop'else status}
        ctrl=TacticalCooperationController(m,rom,bad);result=ctrl.run_entry(0xB4E1,registers=r)
        assert result['status']=='dependency'and isinstance(ctrl.pending,ServiceCall)
        assert m[0x20]==raw_r[0x20]and m[0x21]==raw_r[0x21]
        guards.append(dict(name='uncompleted_helper_rejected',status=status,source_PC=r.pc,source_SP=r.sp))
    complete=sum(n for key,n in counts.items()if key.endswith(':complete_return'));prefix=sum(n for key,n in counts.items()if key.endswith(':strict_prefix'))
    pins=('source/recovered/tactical_cooperation_controller.py','source/recovered/scene_shared_services.py','source/recovered/battle_nmi_services.py','source/recovered/mapped_memory.py','source/recovered/service_memory.py',
          'scripts/verify_tactical_cooperation_controller.py','scripts/verify_battle_scene_controller.py','scripts/trace_startup.py')
    result=dict(schema='phase14-readable-tactical-controller-v1',status='passed'if not failures else'failed',quick=quick,rom_sha256=ROM_SHA256,
        rom_cpu_case_count=complete+prefix,complete_return_count=complete,strict_prefix_count=prefix,source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),failures=failures,rows=rows,guards=guards,
        source_original_CPU_callbacks=0,source_IR_interpretation=False,independent_source_F266_calls=sum(source_service_calls.values()),
        source_sha256={p:sha(ROOT/p)for p in pins},native_input_sha256=native_inputs,comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,registers='AXYP/SP/PC',free_stack_residue='included',ordered_ports_and_banks=True),
        original_executed_instruction_locations=len(visited),source_block_count_is_not_original_instruction_count=True,
        limits=['The isolatedB517 boundaries and sourcebudget/missing-helper prefixes are separate from completeRTS bodies.',
                'Native inputs are reused synchronousCPU fixtures, not new Nestopia frames or a source renderer/IRQ schedule.','Typed controlled layouts do not claim campaign reachability.',
                'Proposals and existing service resource effects are real; downstream movement/APcommit/attack/tacticpresentation stay separate.'])
    out.mkdir(parents=True,exist_ok=True);(out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'executed-instructions.json').write_text(json.dumps([dict(physical_bank=b,cpu_address=pc,rom_offset=f,count=n)for(b,pc,f),n in sorted(visited.items())],indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','complete_return_count','strict_prefix_count','source_guard_case_count','failed_count','counts')}),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'analysis/phase14/tactical');a=p.parse_args()
    res=verify(a.rom.read_bytes(),a.out,a.quick);raise SystemExit(bool(res['failures']))
