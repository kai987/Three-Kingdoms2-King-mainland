#!/usr/bin/env python3
"""Exact original CPU vs pure GameEngine cooperation at the real E066 loop.

End-of-frame Native files provide memory, not an internal CPU-register trace.
The source side has no CPU callback, IR executor, artificial IRQ or ack store.
Cooperative waiting and original service interleaves are counted separately.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.game_engine import GameEngine
from source.recovered.global_ui_controller import UIRegisters
from source.recovered.service_memory import ServiceMemory
from source.recovered.battle_nmi_services import ServiceCall,ServiceWait
from source.recovered.officers import ROM_SHA256
from source.recovered.terrain_rules import city_chunks,map_cell,legal_cell

REGS=('a','x','y','p','sp','pc')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def sha(path):return digest(Path(path).read_bytes())
def reg(r):return {k:getattr(r,k)for k in REGS}
def verify(rom,out,quick=False):
    assert digest(rom)==ROM_SHA256
    pins=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))
    pins+=['scripts/verify_phase14_cooperation_integration.py']
    source_pins={p:sha(ROOT/p)for p in pins}
    rows=[];failures=[];guards=[];counts=Counter();visited=Counter();artifacts={}
    inputs={0x2002:0,0x4015:0,0x4016:0,0x4017:0}
    def load(prefix):
        prefix=ROOT/prefix if not Path(prefix).is_absolute()else Path(prefix)
        rp=Path(str(prefix)+'-ram.bin');sp=Path(str(prefix)+'-sram.bin')
        artifacts[str(rp.relative_to(ROOT))]=sha(rp);artifacts[str(sp.relative_to(ROOT))]=sha(sp)
        return bytearray(rp.read_bytes()),bytearray(sp.read_bytes())
    domestic_ram,domestic_sram=load('analysis/phase11/runtime/cold-battle/picked-ruler')
    city_ram,city_sram=load('analysis/phase11/runtime/cold-battle/city-commands')
    tactical_ram,tactical_sram=load('analysis/runtime/phase3/attack-intro-7')
    def memory(r,s,banks):
        return ServiceMemory(rom,r,s,banks,read_ports=inputs,repeat_read_ports=tuple(inputs))
    def differences(a,b,r,c,scope=None):
        full=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,b.ram))if x!=y]
        scope=set(range(2048)if scope is None else scope)
        rd=[x for x in full if x[0]in scope];excluded=[x for x in full if x[0]not in scope]
        sd=[(0x6000+i,x,y)for i,(x,y)in enumerate(zip(a.sram,b.sram))if x!=y]
        rg={k:(getattr(c,k),getattr(r,k))for k in REGS if getattr(c,k)!=getattr(r,k)}
        return dict(RAM=rd[:16],SRAM=sd[:16],registers=rg,RAM_scope_bytes=len(scope),RAM_difference_count=len(rd),SRAM_difference_count=len(sd),
            full_RAM_difference_count=len(full),excluded_RAM_differences=excluded,
            ordered_ports_equal=a.io_writes==b.io_writes,reads_equal=a.io_reads==b.io_reads,banks_equal=a.banks==b.banks)
    def equal(d):assert not d['RAM']and not d['SRAM']and not d['registers']and d['ordered_ports_equal']and d['reads_equal']and d['banks_equal'],d
    def original_to(a,c,r,b,result,*,limit=1500000):
        for n in range(limit):
            if n and c.pc==r.pc and c.sp==r.sp:
                if result['status']=='returned' or(reg(c)==reg(r)and a.ram==b.ram and a.sram==b.sram and a.io_writes==b.io_writes):return n
            if c.pc<0x8000:raise RuntimeError(f'Original entered RAM ${c.pc:04X}')
            bank=a.banks[(c.pc-0x8000)//8192];visited[(bank,c.pc,16+bank*8192+(c.pc&8191))]+=1
            c.step()
        raise RuntimeError(f'Original budget ${c.pc:04X}; source ${r.pc:04X}/{r.sp:02X}/{result["status"]}')
    def pipeline(group,r,s,metadata,*,banks=None,record=True):
        banks=tuple(banks or(r[0xDE]&31,r[0xDF]&31,r[0xE0]&31,31))
        a=memory(r,s,banks);b=memory(r,s,banks);game=GameEngine(b,rom=rom,mapped=True);co=game.readable_scene_rules()
        assert co.external_callback is None
        rr=UIRegisters(a=17,x=31,y=63,p=32,sp=255,pc=0xE066)
        c=MPU(memory=a)
        for k,v in reg(rr).items():setattr(c,k,v)
        initial=reg(rr);initial_ram=bytes(r);initial_sram=bytes(s)
        try:
            result=game.tick_readable_main(rr)
            n=original_to(a,c,rr,b,result)
            d=differences(a,b,rr,c);equal(d)
            comparison='complete_return'if result['status']=='returned'else'strict_prefix'
            assert result['status']in('returned','dependency','waiting'),result
            if result['status']=='returned':assert rr.pc==0xE066 and rr.sp==initial['sp'],'E066 is not RTS'
            row=dict(group=group,input=metadata,entry=0xE066,comparison=comparison,source_status=result['status'],
                completion_kind='main_E066_boundary'if result['status']=='returned'else'strict_prefix',
                initial_registers=initial,final_registers=reg(rr),original_instructions=n,original_main_return_site=0xE188 if initial_ram[0x7A]&31==2 else 0xE22C,
                preparation='Explicit AXYP/SP at E066; no replacement RTS frame',RAM_bytes=2048,SRAM_bytes=8192,
                final_banks=list(b.banks),port_write_count=len(b.io_writes),ordered_ports_sha256=digest(json.dumps(b.io_writes,separators=(',',':')).encode()),
                io_read_count=len(b.io_reads),source_calls=list(co.calls),pure_source_owner_counts=dict(Counter(x['kind']for x in co.calls)),
                source_original_CPU_callbacks=0,source_IR_interpretation=False,comparison_details=d,
                changed_RAM_count=sum(x!=y for x,y in zip(initial_ram,b.ram)),changed_SRAM_count=sum(x!=y for x,y in zip(initial_sram,b.sram)))
            if record:counts[group+':'+comparison]+=1;rows.append(row)
            return dict(original=a,memory=b,game=game,coordinator=co,registers=rr,cpu=c,result=result,initial=initial,row=row)
        except Exception as exc:
            failures.append(dict(group=group,input=metadata,error=str(exc),source_PC=rr.pc,source_SP=rr.sp,source_calls=co.calls))
            if len(failures)<=8:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
            return None
    def domestic(prep):
        r=bytearray(domestic_ram);s=bytearray(domestic_sram);r[0x7A]=2;r[0x78]=2
        r[0xDE:0xE4]=bytes([48,42,43,48,59,60])
        for a,v in prep.items():
            if a<2048:r[a]=v
            elif 0x6000<=a<0x8000:s[a-0x6000]=v
            else:raise ValueError(a)
        return r,s
    # Each ruler's three weighted strategies retain their original rejection
    # sampling and byte-budget behavior. Native super-ROM resources are kept.
    for ruler in range(7):
        for strategy,weights in enumerate(((16,0,0),(0,16,0),(0,0,16))):
            for budget in((30,)if quick else(5,30)):
                i=ruler*3+strategy
                prep={0x6F03:ruler,0x6F02:strategy,0x6F8B:0,0x6F5B:1,0x6F5D:budget,0x6F62:0,
                    0xEE:7+8*ruler,0xEF:0x6F,0x52:i*7&255,0x54:i*13&255,0x55:i*19&255,
                    0x6F5F:weights[0],0x6F60:weights[1],0x6F61:weights[2]}
                r,s=domestic(prep);pipeline('main2_all_rulers_three_strategies',r,s,dict(ruler=ruler,strategy=strategy,budget=budget,prepared_bytes=prep))
    for ruler in range(7):
        prep={0x6F03:ruler,0x6F02:ruler%3,0x6F8B:0,0x6F5B:0,0x6F5D:10,0x6F62:0,0xEE:7+8*ruler,0xEF:0x6F}
        r,s=domestic(prep);first=pipeline('main2_initialization',r,s,dict(ruler=ruler,prepared_bytes=prep))
        if first and first['result']['status']=='returned':pipeline('main2_following_decision',first['memory'].ram,first['memory'].sram,dict(ruler=ruler,continuation_of='main2_initialization'),banks=first['memory'].banks)
    def tactical(actor=0,side=0,ap=15):
        r=bytearray(tactical_ram);s=bytearray(tactical_sram);r[0x7A]=4;r[0x78]=3
        r[0xDE:0xE4]=bytes([38,40,41,38,40,41]);r[0x504]=side;r[0x505]=ap
        s[0xF8B]=0;s[0xF8C]=actor;s[0xF94:0xF97]=bytes(3)
        s[0xFA1:0xFB5]=bytes([255]*20);s[0xFA1+actor]=0
        r[0x4D8:0x4E0]=bytes([255]*8);r[0x20:0x3B]=bytes(27)
        return r,s
    for strategy in range(8):
        for side in(0,128):
            actor=10 if side else 0;enemy=0 if side else 10
            for ap in(0,15):
                for variant in(range(1)if quick else range(2)):
                    r,s=tactical(actor,side,ap);s[0xF94]=actor;s[0xFA1+actor]=strategy
                    r[0x650+actor]=(0,4)[variant];r[0x600+actor]=(2,2)[variant];r[0x614+actor]=(14,16)[variant]
                    r[0x600+enemy]=(3,17)[variant];r[0x614+enemy]=(14,16)[variant]
                    pipeline('main4_all_eight_strategies',r,s,dict(strategy=strategy,side=side,AP=ap,layout_variant=variant))
    # Immutable end-of-frame memories are inherited evidence. AXYP/SP are
    # declared synchronous fixtures, not registers recorded inside Nestopia.
    for path in sorted((ROOT/'analysis/phase7/runtime/natural-turn').glob('*-ram.bin')):
        r,s=load(path.with_name(path.name[:-8]));assert r[0x7A]&31==4
        pipeline('phase7_native_tactical_memory',r,s,dict(snapshot=str(path.relative_to(ROOT)),provenance='Inherited phase7 natural-turn; no new Native tactical run'))
    native=ROOT/'analysis/phase14/runtime/evidence.json'
    if native.exists():
        artifacts[str(native.relative_to(ROOT))]=sha(native);manifest=json.loads(native.read_text());assert manifest['status']=='passed'
        case=next(x for x in manifest['native_cases']if x['case']=='cold-city-domestic-cycle')
        cp=ROOT/'analysis/phase14/runtime'/case['checkpoints'];artifacts[str(cp.relative_to(ROOT))]=sha(cp)
        for item in json.loads(cp.read_text()):
            if item['label'].startswith('AI-ruler')and item['global_state']==2:
                prefix=cp.parent/Path(item['RAM']).name[:-8];r,s=load(prefix)
                pipeline('phase14_native_domestic_memory',r,s,dict(snapshot=str(prefix.relative_to(ROOT)),frame=item['frame'],
                    observed_ruler=s[0xF03],observed_request=s[0xF8B],provenance='Current cold-start no-memory-write Native; declared synchronous AXYP/SP'))
    # This is a separate original-call layer, not a claim the main4 chooser
    # naturally selects every tactic. AC7B includes actual map lookup and its
    # literal16-word B517 dispatch; the original AA5F JSR frame is declared.
    representatives={}
    for city in range(30):
        chunks=city_chunks(rom,city)
        for y in range(20):
            for x in range(1,30):
                if legal_cell(x,y):representatives.setdefault(map_cell(rom,chunks,x,y)['ai_class'],(city,x,y))
    assert set(representatives)==set(range(6))
    predicate_outcomes={i:set()for i in range(16)}
    def predicate_case(group,tactic,r,s,meta,expected=None):
        a=memory(r,s,(6,8,9,31));b=memory(r,s,(6,8,9,31))
        for m in(a,b):m[0x1FE]=0x61;m[0x1FF]=0xAA
        rr=UIRegisters(a=17,x=tactic,y=0,p=32,sp=253,pc=0xAC7B);initial=reg(rr);c=MPU(memory=a)
        for k,v in initial.items():setattr(c,k,v)
        game=GameEngine(b,rom=rom,mapped=True);co=game.readable_scene_rules()
        try:
            result=co(ServiceCall(0xAC7B,0xAA62,'tactic_eligibility_existing_caller_fixture',rr,b,tuple(b.banks),255))
            assert result['status']=='returned',result;n=original_to(a,c,rr,b,result);d=differences(a,b,rr,c);equal(d)
            carry=bool(rr.p&1)
            if expected is not None:assert carry==expected,dict(expected=expected,actual=carry)
            predicate_outcomes[tactic].add(carry);counts[group+':complete_return']+=1
            rows.append(dict(group=group,input=dict(tactic_ID=tactic,**meta),entry=0xAC7B,comparison='complete_return',
                completion_kind='actual_caller_RTS',source_status=result['status'],initial_registers=initial,final_registers=reg(rr),
                original_instructions=n,carry=carry,RAM_bytes=2048,SRAM_bytes=8192,final_banks=list(b.banks),source_calls=list(co.calls),
                source_original_CPU_callbacks=0,comparison_details=d,
                preparation='Explicit AC7B X=tactic fixture, existing AA5F->AA62 JSR frame; whole terrain and B517 body, no probability/effect.'))
        except Exception as exc:
            failures.append(dict(group=group,tactic=tactic,input=meta,error=str(exc)))
            if len(failures)<=8:print(json.dumps(failures[-1]),flush=True)
    for tactic in range(16):
        for terrain,(city,tx,ty)in sorted(representatives.items()):
            for strong in((True,)if quick else(False,True)):
                r,s=tactical();r[0x50E]=city;r[0xA8:0xAA]=bytes([0xAA,0]);r[0xAA:0xAE]=bytes(city_chunks(rom,city))
                r[0x664:0x678]=bytes([255]*20);r[0x664]=8;r[0x664+10]=109;r[0x664+11]=110
                r[0x600]=tx-1;r[0x614]=ty;r[0x600+10]=tx;r[0x614+10]=ty;r[0x600+11]=tx+1;r[0x614+11]=ty
                r[0x628]=0;r[0x628+10]=r[0x628+11]=128;r[0x2B]=10;s[0xF8C]=0
                for ident in(8,109,110):
                    o=0x3C0+12*ident;s[o+1]=s[o+2]=99 if strong else 84;s[o+3]=20 if strong else 100
                    value=1000 if strong else 99;s[o+8]=value&255;s[o+9]=value>>8
                predicate_case('all_sixteen_tactic_eligibility',tactic,r,s,dict(target_class=terrain,city=city,strong_record=strong))
    # Five specific legal-cell cases close the opposing carry outcomes which
    # a single representative of each terrain alone cannot exercise.
    adjacent_classes={}
    for city in range(30):
        chunks=city_chunks(rom,city)
        for y in range(20):
            for x in range(1,30):
                if not legal_cell(x,y):continue
                first=map_cell(rom,chunks,x,y)['ai_class']
                for nx,ny in((x-1,y),(x+1,y),(x,y-2 if y==16 else y-1),(x,y+2 if y==14 else y+1)):
                    if legal_cell(nx,ny):adjacent_classes.setdefault((first,map_cell(rom,chunks,nx,ny)['ai_class']),(city,x,y,nx,ny))
    for tactic,classes,expected in((5,(0,0),False),(9,(4,5),True),(10,(3,3),True),(12,(3,3),True),(13,(5,0),True)):
        city,x1,y1,x2,y2=adjacent_classes[classes];r,s=tactical();r[0x50E]=city
        r[0xA8:0xAA]=bytes([0xAA,0]);r[0xAA:0xAE]=bytes(city_chunks(rom,city));r[0x664:0x678]=bytes([255]*20)
        for slot,ident in((0,8),(10,109),(11,110)):
            r[0x664+slot]=ident;r[0x628+slot]=0 if slot==0 else 128
        s[0xF8C]=0;r[0x2B]=11 if tactic==5 else 10
        if tactic in(10,12):
            r[0x600+10]=x1;r[0x614+10]=y1;r[0x600+11]=x2;r[0x614+11]=y2
            spare=next((x,y)for y in range(20)for x in range(31)if legal_cell(x,y)and(x,y)not in((x1,y1),(x2,y2)))
            r[0x600],r[0x614]=spare
        else:
            r[0x600]=x1;r[0x614]=y1;r[0x600+10]=x2;r[0x614+10]=y2
            spare=next((x,y)for y in range(20)for x in range(31)if legal_cell(x,y)and(x,y)not in((x1,y1),(x2,y2)))
            r[0x600+11],r[0x614+11]=spare
        predicate_case('tactic_specific_carry_boundaries',tactic,r,s,dict(city=city,adjacent_class_pair=classes,target_slot=r[0x2B],coordinates=[x1,y1,x2,y2]),expected)
    # Start from initialized city memory, retaining its real ready/queue data.
    # A controlled battle-return/leader condition producesFB orFC naturally.
    # The same suspended E066 generator survives the actual hardwareNMI2;
    # neither this script nor source code writes a substitute acknowledgement.
    succession_sequences=[]
    for heir in(False,True):
        r=bytearray(city_ram);s=bytearray(city_sram);ruler=0
        owned=[i for i in range(30)if s[32*i]&7==ruler]
        prep={0x7A:2,0x78:2,0x400:9,0x401:1,0x40C:1,0x69:0,0x7B:0,
            0x6F03:ruler,0x6F02:1,0x6F8B:1,0x6F8C:1,0x6F8D:0,0x6F5B:1,0x6F5D:5,0x6F62:0,
            0xEE:7,0xEF:0x6F,0x38:owned[0],0x3A:owned[0],0x44:0,
            0x507:ruler,0x508:ruler,0x50E:owned[0],0x50F:3,0x6F0A:3}
        for address,value in prep.items():
            if address<2048:r[address]=value
            else:s[address-0x6000]=value
        for slot in range(20):r[0x664+slot]=255
        for j in range(7):
            leader=s[0xF07+8*j];s[0x3C0+12*leader+11]=(s[0x3C0+12*leader+11]&252)|(3 if j==ruler else 2)
        for city in owned:s[32*city+17:32*city+27]=bytes([255]*10)
        if heir:
            off=16+11*8192+0xAD8;pointer=int.from_bytes(rom[off:off+2],'little');candidate=rom[16+11*8192+(pointer&8191)]
            s[32*owned[0]+17]=candidate;s[0x3C0+12*candidate+5]=owned[0];s[0x3C0+12*candidate+11]=(s[0x3C0+12*candidate+11]&252)|2
        r[0xDE:0xE4]=bytes([48,42,43,48,59,60])
        state=pipeline('main2_succession_actual_NMI2_resume',r,s,dict(ruler=ruler,heir=heir,prepared_bytes=prep,
            record_preparation='Currentleadercondition3,otherleadercondition2; ownedrostersFF except validfamilycandidate ifheir;20surviving slotsFF'),record=False)
        if state is None:continue
        a=state['original'];b=state['memory'];game=state['game'];co=state['coordinator'];rr=state['registers'];c=state['cpu']
        assert state['result']['status']=='dependency'and rr.pc in(0xCA7F,0xCB79)and b[0x6F8B]in(251,252)
        paused_call=co.global_ui.pending;paused_PC=rr.pc;paused_SP=rr.sp
        # Existing audio/render services exclude idle high-stack residue.
        # Fix the scope before arrivals, rather than dropping differing bytes:
        # baseUI1972B plus the actual4B suspendedmain caller framesFC..FF.
        active_stack=list(range(0x100+paused_SP+1,0x200))
        NMI_scope=[*range(0x1B4),*range(0x200,0x800),*active_stack]
        assert len(NMI_scope)==1976 and active_stack==[0x1FC,0x1FD,0x1FE,0x1FF]
        before=(bytes(b.ram),bytes(b.sram),reg(rr),list(b.io_writes),list(b.banks));same=game.resume_readable_main()
        assert same['status']=='dependency'and co.global_ui.pending is paused_call and before==(bytes(b.ram),bytes(b.sram),reg(rr),list(b.io_writes),list(b.banks))
        guards.append(dict(name='same_suspended_main_without_original_ack_cannot_fake_complete',heir=heir))
        stages=[dict(kind='main_actual_succession_wait',original_instructions=state['row']['original_instructions'],PC=rr.pc,SP=rr.sp,request=b[0x6F8B])]
        original_total=state['row']['original_instructions'];NMI_count=0;scope_observations=[]
        try:
            for tick in range(1,505):
                result=game.tick_readable_nmi(rr,hardware_entry=True);c.nmi()
                n=original_to(a,c,rr,b,result);original_total+=n;d=differences(a,b,rr,c,NMI_scope);equal(d)
                NMI_count=tick
                if d['excluded_RAM_differences']:
                    scope_observations.append(dict(NMI=tick,full_RAM_difference_count=d['full_RAM_difference_count'],excluded_RAM_differences=d['excluded_RAM_differences']))
                if result['status']!='returned':
                    stages.append(dict(kind='NMI_dependency_prefix',NMI=tick,original_instructions=n,PC=rr.pc,SP=rr.sp,dependency=result.get('dependency')));break
                assert rr.pc==paused_PC and rr.sp==paused_SP,'ActualRTI must restore the suspended maincaller'
                if tick in(1,2,239,240,241,479,480,481)or b[0x6F8B]==1:
                    stages.append(dict(kind='actual_NMI2_RTIs',NMI=tick,original_instructions=n,PC=rr.pc,SP=rr.sp,city_phase=b[0x401],counter=b[0x40C],
                        request=b[0x6F8B],text_job=b[0x300],map_job=b[0x304],PPU_jobs=b[0x7E]))
                if b[0x6F8B]==1:
                    assert co.global_ui.pending is paused_call
                    result=game.resume_readable_main();assert result['status']=='returned'
                    n=original_to(a,c,rr,b,result);original_total+=n;d=differences(a,b,rr,c,NMI_scope);equal(d)
                    assert rr.pc==0xE066 and rr.sp==state['initial']['sp']
                    stages.append(dict(kind='same_generator_resume_main_E066',original_instructions=n,PC=rr.pc,SP=rr.sp,request=b[0x6F8B]))
                    break
            else:raise RuntimeError('Bounded505NMI arrivals did not reach originalack')
            complete=result['status']=='returned'and rr.pc==0xE066
            comparison='complete_return'if complete else'strict_prefix';counts['main2_succession_actual_NMI2_resume:'+comparison]+=1
            unique_calls=[];seen_calls=set()
            for call in co.calls:
                key=(call['target'],call['kind'],call['status'],tuple(call['banks']))
                if key not in seen_calls:seen_calls.add(key);unique_calls.append(call)
            row={**state['row'],'comparison':comparison,'completion_kind':'main_E066_boundary'if complete else'strict_prefix',
                'source_status':result['status'],'final_registers':reg(rr),'final_banks':list(b.banks),'original_instructions':original_total,
                'NMI_hardware_arrivals':NMI_count,'NMI_port_inputs':inputs,'main_generator_and_ServiceCall_retained':True,'ack_injected':False,
                'ack_origin':'Actual26CBBD..CBBF'if complete else None,'source_calls':unique_calls,'stages':stages,
                'source_calls_format':'Unique chronological first occurrences; total ordered log count/hash below',
                'pure_source_owner_counts':dict(Counter(x['kind']for x in co.calls)),
                'source_call_count':len(co.calls),'source_calls_sha256':digest(json.dumps(co.calls,separators=(',',':')).encode()),
                'port_write_count':len(b.io_writes),'ordered_ports_sha256':digest(json.dumps(b.io_writes,separators=(',',':')).encode()),
                'io_read_count':len(b.io_reads),'changed_RAM_count':sum(x!=y for x,y in zip(r,b.ram)),'changed_SRAM_count':sum(x!=y for x,y in zip(s,b.sram)),
                'RAM_bytes':len(NMI_scope),'RAM_scope_addresses':NMI_scope,'active_main_caller_stack':active_stack,
                'comparison_details':d,'NMI_fixed_scope_residue_observations':scope_observations,
                'boundary_scope':'Controlledinitialized city4009/sub1 andIRQreload69=0; realhardwareNMI/RTI software, notscanline/pixel timing.'}
            rows.append(row);succession_sequences.append(dict(heir=heir,comparison=comparison,NMI_hardware_arrivals=NMI_count,ack_injected=False,stages=stages,
                RAM_scope_bytes=len(NMI_scope),inactive_high_stack_excluded=[0x1B4,0x1FC],active_main_stack_preserved=active_stack,
                first_excluded_residue_difference=scope_observations[0]if scope_observations else None))
        except Exception as exc:
            failures.append(dict(group='main2_succession_actual_NMI2_resume',heir=heir,NMI=NMI_count,error=str(exc),source_PC=rr.pc,stages=stages))
            if len(failures)<=8:print(json.dumps(failures[-1]),flush=True)
    # Unknown owner preserves the real existing caller, not a fake completion.
    r,s=tactical();m=memory(r,s,(6,8,9,31));game=GameEngine(m,rom=rom,mapped=True);rr=UIRegisters(pc=0x8123)
    before=(bytes(m.ram),bytes(m.sram),list(m.io_writes),list(m.banks),reg(rr))
    result=game.readable_scene_rules()(ServiceCall(0x8123,0xE22C,'unknown',rr,m,tuple(m.banks),255))
    assert result['status']=='dependency'and before==(bytes(m.ram),bytes(m.sram),list(m.io_writes),list(m.banks),reg(rr))
    guards.append(dict(name='unknown_owner_preserves_PC_SP_memory_and_ports'))
    after={p:sha(ROOT/p)for p in pins};assert after==source_pins,'Production source changed during matrix; rerun after freeze'
    complete=sum(v for k,v in counts.items()if k.endswith(':complete_return'));prefix=sum(v for k,v in counts.items()if k.endswith(':strict_prefix'))
    main_count=sum(row['completion_kind']=='main_E066_boundary'for row in rows);caller_count=sum(row['completion_kind']=='actual_caller_RTS'for row in rows)
    result=dict(schema='phase14-pure-cooperation-integration-v1',status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,
        rom_cpu_case_count=sum(counts.values()),complete_return_count=complete,complete_main_boundary_count=main_count,main_boundary_count=main_count,actual_caller_return_count=caller_count,strict_prefix_count=prefix,
        source_guard_case_count=len(guards),failed_count=len(failures),counts=dict(counts),failures=failures,rows=rows,guards=guards,
        source_original_CPU_callbacks=0,source_IR_interpretation=False,production_fallback=False,native_internal_CPU_trace=False,
        comparison=dict(RAM_bytes=2048,SRAM_bytes=8192,CPU_registers='AXYP/SP/PC',free_stack_residue='included for synchronousmain/eligibility',
            interleaved_NMI_RAM_bytes=1976,interleaved_NMI_exclusion=[0x1B4,0x1FC],interleaved_NMI_active_main_stack=[0x1FC,0x1FD,0x1FE,0x1FF],ordered_ports_banks_reads=True),
        source_sha256=source_pins,artifact_sha256=artifacts,executed_original_locations=[dict(bank=b,CPU_address=p,ROM_offset=o,visits=n)for(b,p,o),n in sorted(visited.items())],
        tactic_predicate_outcomes={str(i):sorted(values)for i,values in predicate_outcomes.items()},succession_sequences=succession_sequences,
        nested_NMI_software_arrivals=sum(x['NMI_hardware_arrivals']for x in succession_sequences),
        auxiliary_UI_body_count_included_in_this_receipt=0,
        limits=['E066 completion is a main-loop boundary with unchanged outerSP; it does not execute or fabricate RTS.',
            'Source side uses only named readable controllers and pure recovered services; original6502 is confined to this validator.',
            'Native inputs supply end-of-frame RAM/SRAM, not captured CPU registers or internal instruction/NMI timing. Source did not render the original screenshots/PCM.',
            'Controlled strategy weights/AP/layouts have campaign-domain bytes but do not establish every fixture is naturally reachable.',
            'All16tactic eligibility subcalls are separate caller-level fixtures, not16naturallyselected main4 actions or probability/effect bodies.',
            'Two succession cases preserve the sameE066generator; explicit hardwareNMI arrivals are inputs, never fabricated readiness or a6F8B ackstore.',
            'NMI/helper stages inside one succession pipeline are nested comparisons and notadditional rom_cpu_case_count rows.',
            'SuccessionNMI pipelines fix1976B RAM scope in advance: UI1972B plus the actual4B suspendedmainstack; idle1B4..1FB residual differences are retained, not full2048B claimed.',
            'Unknown services and cooperative waits remain actual pending prefixes; no ack or interrupt edge is silently synthesized.'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','complete_main_boundary_count','strict_prefix_count','source_guard_case_count','failed_count')}),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase14/cooperation-integration.json');p.add_argument('--quick',action='store_true');a=p.parse_args()
    result=verify(a.rom.read_bytes(),a.out,a.quick);raise SystemExit(bool(result['failures']))
