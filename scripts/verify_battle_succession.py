#!/usr/bin/env python3
"""Actual ROM CPU against direct postbattle succession, genuine/declared frames.

Frozen Native RAM/SRAM is input data, not observed CPU registers. Original
city callback preparation creates real A00C farcall frames separately; those
preparation instructions are not additional source-comparison cases.
"""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from py65.devices.mpu6502 import MPU
from source.recovered.battle_succession import BattleSuccession,SuccessionRegisters,ROM_SHA256,SuccessionBlockBudget
from source.recovered.service_memory import ServiceMemory
from source.recovered.game_engine import GameEngine
from source.recovered.battle_nmi_services import ServiceCall
OUT=ROOT/'analysis/phase16/succession'
REGS=('a','x','y','p','sp','pc')
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def reg(r):return {k:getattr(r,k)for k in REGS}
def memory(rom,ram,sram,banks=(2,25,26,31)):
    return ServiceMemory(rom,ram,sram,banks,read_ports={0x2002:0,0x4015:0,0x4016:0,0x4017:0},repeat_read_ports=(0x2002,0x4015,0x4016,0x4017))
def router(m,rom):
    coor=GameEngine(m,rom=rom,mapped=True).readable_scene_rules();counts=Counter()
    def service(call):
        counts[(tuple(call.entry_banks[1:3]),call.target)]+=1
        return coor(call)
    return service,coor,counts

def verify(rom,quick=False):
    assert digest(rom)==ROM_SHA256;OUT.mkdir(parents=True,exist_ok=True)
    parent=ROOT/'analysis/phase15/runtime/succession-heir/observed-g02-n02-city-013-005'
    base_ram=Path(str(parent)+'-ram.bin').read_bytes();base_sram=Path(str(parent)+'-sram.bin').read_bytes()
    catalog=json.loads((OUT/'static-catalog.json').read_text());rows=[];failures=[];guards=[];counts=Counter();visited=Counter();artifact={}
    families=[list(bytes.fromhex(catalog['family_table']['raw_hex'])[8*i:8*i+8])for i in range(7)]
    def fresh(ruler=1,controller=3,heir=True):
        r=bytearray(base_ram);s=bytearray(base_sram)
        r[0xE1:0xE4]=bytes([34,57,58]);r[0x400:0x403]=bytes([13,5,0]);r[0x40A]=ruler;r[0x40B]=s[0xF07+8*ruler]
        r[0x40C]=3;r[0x40D]=families[ruler][0];r[0x470:0x474]=bytes([2,6,13,3]);r[0x81]=r[0x87]=r[0x7E]=r[0x7C]=0
        r[0x300]=r[0x304]=255;r[0x4D0]=0;r[0x507]=0x21;r[0xEE]=7+8*2;r[0xEF]=0x6F
        r[0x12]=0;r[0x13]=1;r[0x478]=0;r[0x47C]=0x80
        s[0xF0A+8*ruler]=controller
        for city in range(30):
            if s[32*city]&7==ruler:s[32*city+17:32*city+27]=bytes([255]*10)
        # Explicit ownedcity3 permits allseven typedruler cases.
        s[96]=(s[96]&248)|ruler;s[113:123]=bytes([255]*10)
        if heir:s[113]=families[ruler][0]
        return r,s
    def compare(group,r,s,meta,*,entry=0xA00C,initial=None,banks=(2,25,26,31),missing=False,budget=200000,existing_frame=False):
        a=memory(rom,r,s,banks);b=memory(rom,r,s,banks)
        initial=initial or dict(a=17,x=23,y=31,p=32,sp=253,pc=entry)
        if not existing_frame:
            for m in(a,b):m[0x100+((initial['sp']+1)&255)]=0x67;m[0x100+((initial['sp']+2)&255)]=0x24
        rr=SuccessionRegisters(**initial);c=MPU(memory=a)
        for k,v in initial.items():setattr(c,k,v)
        services,coor,call_counts=router(b,rom);owner=BattleSuccession(b,rom,None if missing else services)
        before_sram=bytes(a.sram);writers=[]
        try:
            result=owner.run_entry(entry,registers=rr,max_blocks=budget)
            assert result['status']in('returned','dependency','budget'),result
            for n in range(500000):
                if (n or result['status']=='budget') and c.pc==rr.pc and c.sp==rr.sp and a.banks==b.banks:
                    if result['status']=='returned'or(reg(c)==reg(rr)and a.ram==b.ram and a.sram==b.sram):break
                if c.pc<0x8000:raise RuntimeError(f'Unexpected originalRAM PC${c.pc:04X}')
                bank=a.banks[(c.pc-0x8000)//8192];visited[(bank,c.pc,16+bank*8192+(c.pc&8191))]+=1
                old=bytes(a.sram);old_ruler=a[0x6F0F];pc=c.pc;c.step()
                if old_ruler!=a[0x6F0F]or any(old[i]!=a.sram[i]for i in range(0xF07,0xF3F)):
                    writers.append(dict(physical_bank=bank,PC=pc,rom_offset=16+bank*8192+(pc&8191),ruler_changes=[dict(address=0x6000+i,before=old[i],after=a.sram[i])for i in range(0xF07,0xF3F)if old[i]!=a.sram[i]]))
            else:raise RuntimeError(f'Original budget${c.pc:04X};source${rr.pc:04X}')
            rd=[(i,x,y)for i,(x,y)in enumerate(zip(a.ram,b.ram))if x!=y];sd=[(i,x,y)for i,(x,y)in enumerate(zip(a.sram,b.sram))if x!=y]
            rg={k:(getattr(c,k),getattr(rr,k))for k in REGS if getattr(c,k)!=getattr(rr,k)}
            assert not rd and not sd and not rg,dict(RAM=rd[:12],SRAM=sd[:10],registers=rg)
            assert a.io_writes==b.io_writes and a.io_reads==b.io_reads and a.banks==b.banks and a.n163_ram==b.n163_ram
            kind='complete_return'if result['status']=='returned'else'strict_prefix';counts[group+':'+kind]+=1
            rows.append(dict(group=group,input=meta,entry=entry,comparison=kind,completion_kind='actual_caller_RTS'if kind=='complete_return'else'strict_prefix',
                source_status=result['status'],initial_registers=initial,final_registers=reg(rr),original_instructions=n,
                source_blocks=result['control_blocks'],source_original_CPU_callbacks=0,source_service_calls=len(owner.events),
                exact_source_helper_calls={f'{pair}:{target:04X}':v for(pair,target),v in call_counts.items()},
                original_ruler_writers=writers,final_fields=owner.fields(),SRAM_changes=[dict(address=0x6000+i,before=x,after=y)for i,(x,y)in enumerate(zip(before_sram,a.sram))if x!=y],
                final_banks=list(b.banks),ordered_port_writes=len(b.io_writes),ordered_ports_sha256=digest(json.dumps(b.io_writes,separators=(',',':')).encode())))
            return a,b,rr,owner,result
        except Exception as exc:
            failures.append(dict(group=group,input=meta,entry=entry,error=str(exc),source_PC=rr.pc,source_SP=rr.sp,events=owner.events))
            if len(failures)<=10:print(json.dumps(failures[-1],ensure_ascii=False),flush=True)
            return None
    # Native inputs generate the genuine nestedEE07 frame within original
    # cityA000; initialAXYP/F206/F25F/F237/caller are explicitCPU preparation.
    native_rows=[];input_dir=OUT/'actual-callee-inputs';input_dir.mkdir(exist_ok=True)
    for phase,case in((15,'succession-heir'),(15,'succession-no-heir'),(16,'player-defeat-successor')):
        ck_path=ROOT/f'analysis/phase{phase}/runtime'/case/'checkpoints.json';checkpoints=json.loads(ck_path.read_text());artifact[str(ck_path.relative_to(ROOT))]=sha(ck_path)
        labels=['observed-g01-n02-city-013-000','observed-g02-n02-city-013-001','observed-g02-n02-city-013-005','postbattle-A1','postbattle-A2','observed-g02-n02-city-013-003']
        if case=='player-defeat-successor':labels=['observed-g02-n02-city-013-000','observed-g02-n02-city-013-002','observed-g02-n02-city-013-004','player-loss-A1','player-loss-A2','player-successor-city-selected','player-successor-A0','ruler2-ID5-frame7452','player-successor-A1','observed-g02-n02-city-013-003']
        if quick:labels=labels[:3]
        for label in labels:
            item=next(x for x in checkpoints if x['label']==label);prefix=ck_path.parent/label
            r=Path(str(prefix)+'-ram.bin').read_bytes();s=Path(str(prefix)+'-sram.bin').read_bytes()
            for ext in('-ram.bin','-sram.bin'):artifact[str(Path(str(prefix)+ext).relative_to(ROOT))]=sha(str(prefix)+ext)
            a=memory(rom,r,s,(r[0xDE]&31,r[0xDF]&31,r[0xE0]&31,31));c=MPU(memory=a);c.a=76;c.x=r[0x7C];c.y=0;c.p=32;c.sp=253
            preparations=[]
            for entry,Y in((0xF206,None),(0xF25F,r[0xE1]),(0xF237,0x3B)):
                if Y is not None:c.y=Y
                c.pc=entry;c.sp=253;a[0x1FE]=0x67;a[0x1FF]=0x24
                for n in range(200000):
                    if n and c.pc==0x2468 and c.sp==255:break
                    c.step()
                else:raise RuntimeError('Original callback preparation budget')
                preparations.append(dict(entry=entry,Y=Y,instructions=n))
            c.pc=0xA000;c.sp=253;a[0x1FE]=0x67;a[0x1FF]=0x24
            callback_entry=0xA000;cadence_return=False
            for n in range(100000):
                if tuple(a.banks[1:3])==(25,26)and c.pc==0xA00C:break
                if n and c.pc==0x2468:
                    # This endframeinput's directA000 cadence legitimately
                    # returnedbefore main dispatch. A01F is a declared exact
                    # suffix fixture; no repeat/input/readiness byte is faked.
                    cadence_return=True;callback_entry=0xA01F;c.pc=callback_entry;c.sp=253;a[0x1FE]=0x67;a[0x1FF]=0x24
                c.step()
            else:raise RuntimeError('Originalcity13 A00C discovery budget')
            actual_initial=reg(c);callee=input_dir/f'{case}-{label}'
            Path(str(callee)+'-ram.bin').write_bytes(a.ram);Path(str(callee)+'-sram.bin').write_bytes(a.sram)
            meta=dict(case=case,label=label,frame=item['frame'],native_snapshot=str(prefix.relative_to(ROOT)),initial_registers=actual_initial,actual_banks=list(a.banks),
                actual_return_PC=((a[0x100+((c.sp+1)&255)]|a[0x100+((c.sp+2)&255)]<<8)+1)&65535,actual_return_SP=(c.sp+2)&255,
                preparation=preparations,original_city_callback_prefix_instructions=n,callback_entry=callback_entry,A000_cadence_returned_before_dispatch=cadence_return,
                provenance='FrozenNativeRAM/SRAM, declaredoriginalCPU A000 callback or exact A01F dispatchsuffix after cadenceRTS, real F206/F25F/F237, genuine27A067 EE07 A00C frame; notNativeinternalCPUtrace')
            Path(str(callee)+'.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
            for ext in('-ram.bin','-sram.bin','.json'):artifact[str(Path(str(callee)+ext).relative_to(ROOT))]=sha(str(callee)+ext)
            compare('native_input_genuine_A00C',a.ram,a.sram,meta,initial=actual_initial,banks=tuple(a.banks),existing_frame=True)
            native_rows.append(meta)
    # All four actual tables, with legal active indexes only; busy/buttons are
    # originalinput fields. No text completion is performed afterentry.
    for master,sub_count in((0,1),(1,1),(2,1),(3,1),(4,8),(5,6),(6,3)):
        for sub in range(sub_count):
            for button in((0,1)if quick else(0,1,2,255)):
                for busy in((False,)if quick else(False,True)):
                    r,s=fresh(controller=0 if master==4 else 3);r[0x401]=master;r[0x402]=sub;r[0x81]=button;r[0x7E]=4 if busy else 0
                    r[0x4D0]=255;r[0x47C]=0x80;r[0x40E]=0;r[0x40F]=17
                    compare('legal_postbattle_and_nested_dispatch',r,s,dict(master=master,sub=sub,buttons=button,busy_PPU=busy))
    for ruler in range(7):
        for heir in(False,True):
            r,s=fresh(ruler=ruler,heir=heir);r[0x402]=1;r[0x4D0]=255
            compare('family_order_or_no_candidate_fallback',r,s,dict(ruler=ruler,heir=heir),entry=0xC158)
    # Family qualification ignores byte5, HP and condition, including rawHPFF
    # actually observed in the player's native death path.
    for health in((0,255)if quick else(0,1,127,128,255)):
        for condition in(range(1)if quick else range(4)):
            for location in((0,)if quick else(0,3,29,255)):
                r,s=fresh();ident=families[1][0];addr=0x3C0+12*ident;s[addr]=health;s[addr+5]=location;s[addr+11]=(s[addr+11]&252)|condition
                compare('candidate_HP_condition_location_not_predicates',r,s,dict(health=health,condition=condition,byte5=location),entry=0xC1A1)
    for hole in(False,True):
        for tie in(False,True):
            for high_owner in((0,)if quick else(0,0xF8)):
                r,s=fresh(heir=False);s[96]=1|high_owner;s[113:117]=bytes([20,255 if hole else 21,22,255]);s[0x3C0+12*20+4]=90;s[0x3C0+12*21+4]=90 if tie else 89;s[0x3C0+12*22+4]=90 if tie else 80
                compare('morality_tie_later_and_firstFF',r,s,dict(hole=hole,tie=tie,owner_high=high_owner),entry=0xC1DB)
    for roster_index in((0,9)if quick else range(10)):
        r,s=fresh();s[113:123]=bytes(range(20,30));r[0x40D]=20+roster_index
        compare('successor_roster_priority_swap',r,s,dict(roster_index=roster_index),entry=0xC101)
    # AI release vs player release differ: AI leaves location/owner intact.
    for roster_index in((0,)if quick else(0,5,9)):
        for alias in(False,True):
            r,s=fresh();s[113:123]=bytes(range(20,30));r[0x40D]=20 if alias else 99;r[0x31]=20;r[0x13]=17+roster_index
            r[0x10]=96;r[0x11]=0x60;record=0x63C0+12*20;r[0x22]=record&255;r[0x23]=record>>8;s[record-0x6000+5]=29
            compare('AI_release_alias_and_city_owner_preservation',r,s,dict(roster_index=roster_index,successor_alias=alias),entry=0xC318)
    # Nonfamily succession follows the actual loyaltyservice and draw<20.
    # Separateplayer/AI releases prove residence and owner write differences.
    for human in(False,True):
        for loyalty in(30,31):
            for sample in(19,20):
                ruler=2 if human else 1;r,s=fresh(ruler=ruler,controller=0 if human else 3,heir=False)
                r[0x40D]=20;r[0x409]=128;r[0x40E]=0;r[0x40F]=17;r[0x470]=3;r[0xEE]=7+8*ruler;r[0xEF]=0x6F
                old=r[0x40B];s[0x3C0+12*old+4]=50
                for city in(3,4):s[32*city]=(s[32*city]&248)|ruler;s[32*city+17:32*city+27]=bytes([255]*10)
                s[113]=21;s[145]=20
                for ident in(20,21):
                    addr=0x3C0+12*ident;s[addr+4]=50;s[addr+3]=loyalty;s[addr+5]=29;s[addr+8]=0x23;s[addr+9]=0xF1;s[addr+11]=0xF6
                table=rom[16+31*8192+0x8BA:16+31*8192+0x9BA];r[0x50]=table.index(sample)
                compare('nonfamily_followers_APU_complete_player_AI_release',r,s,dict(human=human,loyalty=loyalty,RNG_first=sample,raw_troops=0xF123),entry=0xC01E if human else 0xC289)
    for controller in((0,3)if quick else(0,1,2,3,0x83,255)):
        r,s=fresh(controller=controller);r[0x401]=6;r[0x402]=0
        compare('leaderFF_only_retirement',r,s,dict(controller=controller),entry=0xC386)
    for timer in((0,255)if quick else(0,1,254,255)):
        for entry in(0xC158,0xC280,0xC41E):
            r,s=fresh();r[0x4D0]=timer
            compare('actual_byte_timer_wrap',r,s,dict(timer=timer),entry=entry)
    r,s=fresh();compare('missing_owned_helper_preserves_true_frame',r,s,None,entry=0xC1A1,missing=True)
    r,s=fresh();compare('explicit_structured_budget',r,s,None,entry=0xC1A1,budget=0)
    # Source-only strict guards do not run original table-outside code.
    for name,kwargs,banks in[
        ('actual_registers_required',{},(2,25,26,31)),('wrong_pair',dict(registers=SuccessionRegisters()),(2,12,13,31)),
        ('wrong_entry',dict(entry=0xA000,registers=SuccessionRegisters()),(2,25,26,31)),('decimal',dict(registers=SuccessionRegisters(p=40)),(2,25,26,31)),
        ('negative_budget',dict(registers=SuccessionRegisters(),max_blocks=-1),(2,25,26,31)),
        ('returnword_mismatch',dict(registers=SuccessionRegisters(),return_pc=0x1234),(2,25,26,31))]:
        r,s=fresh();m=memory(rom,r,s,banks);before=(bytes(m.ram),bytes(m.sram),list(m.io_writes));owner=BattleSuccession(m,rom)
        try:owner.run_entry(**kwargs)
        except ValueError:pass
        else:raise AssertionError('Guard '+name)
        assert before==(bytes(m.ram),bytes(m.sram),list(m.io_writes));guards.append(name)
    for phase,sub in((7,0),(4,8),(5,6),(6,3)):
        r,s=fresh();r[0x401]=phase;r[0x402]=sub;m=memory(rom,r,s);m[0x1FE:0x200]=bytes([0x67,0x24]);owner=BattleSuccession(m,rom)
        try:owner.run_entry(registers=SuccessionRegisters())
        except ValueError:pass
        else:raise AssertionError('Out of table accepted')
        guards.append(f'active_table_index_{phase}_{sub}_rejected_without_originalCPU')
    r,s=fresh();m=memory(rom,r,s);m[0x1FE:0x200]=bytes([0x67,0x24]);rr=SuccessionRegisters();owner=BattleSuccession(m,rom)
    result=owner.run_entry(0xC1A1,registers=rr);assert result['status']=='dependency';pending=owner.pending
    before=(bytes(m.ram),bytes(m.sram),reg(rr));assert owner.resume()['status']=='dependency'and owner.pending is pending and before==(bytes(m.ram),bytes(m.sram),reg(rr));guards.append('same_pending_caller_waits_no_fake_RTS')
    for status in(None,'waiting','blocked','returned'):
        r,s=fresh();m=memory(rom,r,s);m[0x1FE:0x200]=bytes([0x67,0x24]);rr=SuccessionRegisters()
        owner=BattleSuccession(m,rom,lambda call,status=status:None if status is None else{'status':status})
        assert owner.run_entry(0xC1A1,registers=rr)['status']=='dependency';guards.append('invalid_helper_'+str(status)+'_cannot_fake_return')
    sources=sorted(str(p.relative_to(ROOT))for p in(ROOT/'source/recovered').glob('*.py'))+['scripts/verify_battle_succession.py','scripts/analyze_battle_succession.py']
    result=dict(schema='phase16-actual-postbattle-succession-originalCPU-v1',status='passed'if not failures else'failed',quick=quick,rom_sha256=ROM_SHA256,
        rom_cpu_case_count=sum(counts.values()),complete_return_count=sum(v for k,v in counts.items()if k.endswith(':complete_return')),
        strict_prefix_count=sum(v for k,v in counts.items()if k.endswith(':strict_prefix')),source_guard_case_count=len(guards),failed_count=len(failures),
        counts=dict(counts),rows=rows,failures=failures,guards=guards,source_original_CPU_callbacks=0,source_IR_interpretation=False,
        source_sha256={p:sha(ROOT/p)for p in sources},artifact_sha256=artifact,native_input_actual_callee_count=len(native_rows),
        comparison=dict(RAM_bytes=2048,free_stack='included',SRAM_bytes=8192,AXYP_SP_PC=True,ordered_ports_reads_banks=True,N163_image=True),
        executed_original_locations=[dict(physical_bank=b,cpu_address=pc,rom_offset=f,visits=v)for(b,pc,f),v in sorted(visited.items())],
        limits=['NativeRAM/SRAM sources are frozen endframe data, not Nestopia internalregister/instruction trace.',
            'Originalcitycallback F206/F25F/F237 and declaredAXYP/caller are context preparation; genuineA00Ccallee comparison counts once.',
            'Production and sourcecomposition have no originalCPU/IR fallback; coordinator exact10A009 bridge uses recoveredDomesticCF7C only, notCA19.',
            'Display/menu/input readiness remains originalsoftware state; no writes or fakeacks occur afterentry.',
            'Full legaldispatchdomain is bounded. Staticclosure and dynamic locations do not imply everybyte/valuepath or naturalcampaign is covered.'])
    (OUT/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','rom_cpu_case_count','complete_return_count','strict_prefix_count','source_guard_case_count','failed_count','native_input_actual_callee_count')}),flush=True)
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--quick',action='store_true');a=p.parse_args();r=verify(a.rom.read_bytes(),a.quick);raise SystemExit(bool(r['failures']))
