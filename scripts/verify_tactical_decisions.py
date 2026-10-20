#!/usr/bin/env python3
"""Original-byte6502 differential for the independent tactical decision APIs.

Fixtures explicitly choose valid battle actors, map chunks and API boundaries.
No predicate, RNG, mapper or helper is substituted in the original oracle.
This CPU verifier does not claim native game reachability or frame timing.
"""
from pathlib import Path
from collections import Counter
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.tactical_decisions import TacticalData,TacticalDecisions,ROM_SHA256
from source.recovered.terrain_rules import city_chunks,legal_cell
from verify_terrain_rules import fresh
from py65.devices.mpu6502 import MPU

RAM_ADDRESSES=list(range(0x20,0x30))+list(range(0x42C,0x42F))

def verify(rom,out):
    data=TacticalData.from_rom(rom);counts=Counter();failures=[];examples=[];coverage=Counter();guards=0
    def base(city=4,slot=0,x=10,y=10):
        bus=fresh(rom,8);bus.ram[:]=bytes([0xA5])*2048
        bus.ram[0xE1:0xE4]=bytes([49,40,41]);bus.ram[0x1FE:0x200]=bytes([255,1]);bus.ram[0x664:0x678]=bytes([255])*20
        bus.sram[0xFA1:0xFB5]=bytes([255])*20;bus.sram[0xF94:0xF97]=bytes([0])*3
        bus[0x504]=0;bus[0x505]=6;bus[0x6F8B]=0;bus[0x6F8C]=slot;bus[0x664+slot]=131;bus[0x600+slot]=x;bus[0x614+slot]=y
        bus[0x628+slot]=0;bus[0x650+slot]=0;bus[0x6FA1+slot]=2;bus[0x6F92]=0;bus[0xA8]=0xAA;bus[0xA9]=0
        for i,v in enumerate(city_chunks(rom,city)):bus[0xAA+i]=v
        return bus
    def clone(bus):
        m=bytearray(65536);m[:2048]=bus.ram;m[0x6000:0x8000]=bus.sram
        return m
    def run(bus,entry,stops=(0x200,),registers=None,limit=100000):
        cpu=MPU(memory=bus,pc=entry);cpu.sp=0xFD;cpu.p=cpu.UNUSED;bus.cpu=cpu
        for k,v in(registers or{}).items():setattr(cpu,k,v)
        for i in range(limit):
            if cpu.pc in stops:return cpu,i
            bus.pc=cpu.pc;bus.step_no=i;origin=bus.origin(cpu.pc)
            if origin is None:raise AssertionError(f'unexpectedRAM PC {cpu.pc:04X}')
            bank,offset=origin;coverage[(bank,cpu.pc,offset)]+=1;cpu.step()
        raise AssertionError(f'budget PC {cpu.pc:04X}')
    def compare(group,bus,entry,method,stops=(0x200,),registers=None,meta=None,ram=RAM_ADDRESSES):
        m=clone(bus);model=TacticalDecisions(m,data)
        try:
            expected=method(model);cpu,steps=run(bus,entry,stops,registers)
            delta=[(i,bus.peek(i),m[i])for i in ram if bus.peek(i)!=m[i]]
            sram_delta=[(0x6000+i,a,b)for i,(a,b)in enumerate(zip(bus.sram,m[0x6000:0x8000]))if a!=b]
            assert not delta and not sram_delta,(delta[:10],sram_delta[:10])
            counts[group]+=1
            if sum(v['group']==group for v in examples)<(8 if group=='secondary_quirks' else 4):
                examples.append(dict(group=group,input=meta,stop_pc=cpu.pc,instructions=steps,result=expected))
            return cpu,expected
        except Exception as exc:
            failures.append(dict(group=group,input=meta,error=str(exc)))
            if len(failures)>15:raise
    # Cooperative scan prefixes/suffixes. Comparisons include ALL SRAM, but
    # no zero-page scratch is written before the strategy entry.
    for flag in(0,1,2,254,255):
      for cursor in(0,1,9,19,20,255):
       for mode in('eligible','inactive','opponent','all_failed','counter_wrap'):
        b=base(slot=9);b[0x6F8B]=flag;b[0x6F94]=cursor
        if mode=='inactive':b[0x6FA1+9]=255
        if mode=='opponent':b[0x628+9]=128
        if mode=='all_failed':b[0x6F95]=b[0x6F96]=7
        if mode=='counter_wrap':b[0x6F96]=255;b[0x6F95]=0
        compare('actor_scan_prefix',b,0xA02D,lambda t:t.prepare_actor(),(0x200,0xA099,0xB933),meta=[flag,cursor,mode])
    for status in(0,1,2,3,4,255):
      for cursor in(0,9,10,20,255):
       for attempted,failed in((0,0),(1,0),(1,1),(255,254),(255,255)):
        b=base(slot=9);b[0x6F8F]=status;b[0x6F94]=cursor;b[0x6F96]=attempted;b[0x6F95]=failed
        compare('actor_finish_suffix',b,0xA062,lambda t:t.finish_actor(),(0x200,0xA099),meta=[status,cursor,attempted,failed])
    # Complete A60C original. Legal coordinates and controlled occupancy/ties;
    # anomalous target bytes test actual BPL delta rules without random states.
    target_offsets=[(0,0),(0,-1),(0,1),(-1,0),(1,0),(-4,-1),(4,1),(-1,4),(1,-4),(3,3),(-3,-3)]
    for city in(0,4,12,20,29):
      for actor_xy in((0,0),(10,10),(30,14),(10,16),(10,19)):
       for target_delta in target_offsets:
        for occupancy in('free','friendly','enemy','blocked'):
         b=base(city,x=actor_xy[0],y=actor_xy[1]);b[0x6FA1]=1 if occupancy=='enemy'else 2
         if occupancy=='blocked':b[0x650]=1
         if occupancy in('friendly','enemy'):
          # Duplicate coordinates select the lowest slot, as in A871.
          for j,(dx,dy)in enumerate(((0,-1),(0,1),(-1,0),(1,0)),1):
           b[0x664+j]=j;b[0x600+j]=(actor_xy[0]+dx)&255;b[0x614+j]=(actor_xy[1]+dy)&255;b[0x628+j]=128 if occupancy=='enemy'else 0
         target=(actor_xy[0]+target_delta[0])&255;ty=(actor_xy[1]-(actor_xy[1]>=16)+target_delta[1])&255
         b[0x20]=target;b[0x21]=ty
         compare('complete_greedy_movement',b,0xA60C,lambda t,x=target,y=ty:t.plan_movement(x,y),meta=[city,list(actor_xy),list(target_delta),occupancy])
    # Low8 selector, high8 irrelevance, AP exact/insufficient, direction bounds.
    for direction in range(4):
      for low in(0,2,3,88,89,255):
       for high in(0,255):
        for ap in(0,2,3,6,255):
         b=base();b[0x505]=ap;b[0x63C0+131*12+8]=low;b[0x63C0+131*12+9]=high
         cpu,q=compare('complete_direction_quote',b,0xA740,lambda t,d=direction:t.quote_direction(d),registers={'x':direction},meta=[direction,low,high,ap])or(None,None)
         if cpu:
          flags=int(q['carry'])|int(q['zero'])*2|int(q['overflow'])*64|int(q['negative'])*128
          assert (cpu.a,cpu.x,cpu.y,cpu.p&0xC3)==(q['remaining_ap'],q['return_x'],q['return_y'],flags)
    for x,y in((0,0),(30,19),(128,128),(255,255)):
      for d in range(4):
       b=base(x=x,y=y);compare('direction_bounds',b,0xA740,lambda t,d=d:t.quote_direction(d),registers={'x':d},meta=[x,y,d])
    for ap in(0,1,2,255):
      for side in(0,128):
       for layout in('absent','up','down','left','right','tie'):
        b=base();b[0x505]=ap;b[0x504]=side;b[0x628]=side
        if layout!='absent':
         for i,(dx,dy)in enumerate(((0,-1),(0,1),(-1,0),(1,0)),1):
          if layout!='tie'and layout!=('up','down','left','right')[i-1]:continue
          b[0x664+i]=i;b[0x600+i]=10+dx;b[0x614+i]=10+dy;b[0x628+i]=side^128
        compare('complete_adjacent_attack',b,0xA8A8,lambda t:t.adjacent_attack(),meta=[ap,side,layout])
    # Candidate-prefix ends at A1A8/A1C0; no selected target load/fallback.
    for side in(0,128):
      for layout in('none','tie','radius','zero_distance','signed_delta'):
       b=base();b[0x504]=side;b[0x628]=side
       for i,(dx,dy)in enumerate(((1,0),(-1,0),(2,2),(0,0),(255,128)),1):
        if layout=='none':continue
        if layout=='tie'and i>2:continue
        if layout=='radius'and i!=3:continue
        if layout=='zero_distance'and i!=4:continue
        if layout=='signed_delta'and i!=5:continue
        b[0x664+i]=i;b[0x600+i]=(10+dx)&255;b[0x614+i]=(10+dy)&255;b[0x628+i]=side^128
       compare('nearest_enemy_prefix',b,0xA17B,lambda t:t.nearest_enemy(2),(0xA1A8,0xA1C0),meta=[side,layout])
    # B933 real cached-effect branch uses class0; enumerate selected real cells.
    # Missing slot/radius/terrain gates are complete return paths.
    zeros=[];nonzeros=[]
    for city in(0,4,12,20,29):
      for y in range(20):
       for x in range(31):
        if not legal_cell(x,y):continue
        b=base(city,x=x,y=y);t=TacticalDecisions(clone(b),data);c=t._terrain(x,y)
        pool=zeros if c==0 else nonzeros
        if len(pool)<8:pool.append((city,x,y,c))
    for scenario in('empty','outside','exact_group_bug','different_group_y','terrain'):
      for city,x,y,terrain in (zeros[:3]+nonzeros[:3]):
       b=base(city,slot=2,x=x,y=y);b[0x4DC]=255 if scenario=='empty'else 3;b[0x4DD]=x;b[0x4DE]=y;b[0x664+3]=22;b[0x600+3]=x;b[0x614+3]=y;b[0x628+3]=128
       b[0x614+4]=y if scenario=='exact_group_bug'else(y+1)&255
       if scenario=='outside':b[0x4DD]=(x+10)&255
       compare('secondary_gates',b,0xB933,lambda t:t.secondary_effect(),meta=[scenario,city,x,y,terrain])
    for side in(0,128):
      for troops in(0,1,20,255,256,700,1023):
       for flags in(0,15,29,48,127,128,255):
        for cursor in(0,127,255):
         city,x,y,_=zeros[0];b=base(city,slot=2,x=x,y=y);b[0x504]=side;b[0x628+2]=side;group=0 if side&128 else 4
         b[0x4D8+group]=3;b[0x4D9+group]=x;b[0x4DA+group]=y;b[0x614+group]=y;b[0x664+3]=22;b[0x600+3]=x;b[0x614+3]=y;b[0x628+3]=side^128
         actor=0x63C0+131*12;cached=0x63C0+22*12;b[actor+8]=troops&255;b[actor+9]=0xFC|(troops>>8);b[actor+2]=255
         b[cached+2]=99;b[cached+11]=flags;b[0x6F92]=cursor
         compare('secondary_quirks',b,0xB933,lambda t:t.secondary_effect(),meta=[side,troops,flags,cursor])
    # Explicit source guards are not counted as original-ROM cases.
    for setup,call in[(lambda b:b.__setitem__(0x6F8C,20),lambda t:t.plan_movement(0,0)),
                       (lambda b:b.__setitem__(0x664,255),lambda t:t.secondary_effect()),
                       (lambda b:b.__setitem__(0x6FA1,8),lambda t:t.prepare_actor()),
                       (lambda b:b.__setitem__(0xAA,120),lambda t:t.quote_direction(0))]:
        b=base();setup(b)
        try:call(TacticalDecisions(clone(b),data))
        except ValueError:guards+=1
        else:raise AssertionError('expected source guard')
    status='passed'if not failures else'failed';out.mkdir(parents=True,exist_ok=True)
    evidence=[]
    for(bank,pc,offset),times in sorted(coverage.items()):evidence.append(dict(bank=bank,cpu=pc,rom_offset=offset,execution_count=times))
    source=ROOT/'source/recovered/tactical_decisions.py';analyzer=ROOT/'scripts/analyze_tactical_decisions.py'
    result=dict(status=status,rom_sha256=ROM_SHA256,case_count=sum(counts.values())+guards,rom_oracle_case_count=sum(counts.values()),source_guard_case_count=guards,failed_count=len(failures),counts=dict(counts),failures=failures,examples=examples,
                declared_ram_addresses=RAM_ADDRESSES,compared_sram_range=[0x6000,0x8000],compared_sram_size=8192,executed_instruction_count=len(coverage),
                original_complete_routine_case_count=sum(counts[k]for k in('complete_greedy_movement','complete_direction_quote','direction_bounds','complete_adjacent_attack','secondary_gates','secondary_quirks')),
                original_prefix_or_suffix_case_count=counts['actor_scan_prefix']+counts['actor_finish_suffix']+counts['nearest_enemy_prefix'],
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),verifier_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                scope='Independent high-level algorithms versus unchanged original6502; no substituted helper/predicate/RNG; explicit controlled fixtures; not CPU-register/stack/mapper equivalence or natural campaign proof',
                limits=['Scanning is prefix/suffix around an externally produced real strategy result, not a fabricated full strategy controller.',
                        'nearest_enemy is a prefix ending before caller target-coordinate/fallback.',
                        'Other8strategy orchestration and retreat/morale/resupply policies belong to the separate full CPU controller.',
                        'No native-core frame execution or screenshot is claimed by these CPU fixtures.'])
    (out/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');(out/'executed-instructions.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in('status','case_count','rom_oracle_case_count','source_guard_case_count','failed_count','counts','executed_instruction_count')},indent=2))
    if failures:print(json.dumps(failures[:8],ensure_ascii=False,indent=2));raise SystemExit(1)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase7/decisions');a=p.parse_args();verify(a.rom.read_bytes(),a.out)
