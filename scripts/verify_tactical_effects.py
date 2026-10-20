#!/usr/bin/env python3
"""Actual6502 versus readable semantic casts/lifecycle; no graphics ack."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,random,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from trace_startup import Bus
from py65.devices.mpu6502 import MPU
from source.recovered.tactical_effects import TacticalEffects,EffectData,ROM_SHA256,SUPPORTED_EFFECT_IDS,DECLARED_RAM_RANGES
from source.recovered.tactical_decisions import TacticalDecisions
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--out',type=Path,default=ROOT/'analysis/phase8/effects');args=p.parse_args()
 rom=args.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256;data=EffectData.from_rom(rom)
 prefix=ROOT/'analysis/runtime/phase3/attack-intro-7';base_ram=Path(str(prefix)+'-ram.bin').read_bytes();base_sram=Path(str(prefix)+'-sram.bin').read_bytes()
 rng=random.Random(0x808);counts=Counter();failures=[];rows=[];visited=set();effect_outcomes=Counter();secondary_outcomes=Counter();first_success=set()
 def fresh(pair=12):
  b=Bus(rom,'alternating');b.ram[:]=base_ram;b.sram[:]=base_sram;b.banks=[6,pair,pair+1,31];b.bank_initialized=[True]*4;b.protect=0x4c
  b.ram[0xe1:0xe4]=bytes([0x26,0x20+pair,0x21+pair]);b.ram[0x1fe:0x200]=bytes([255,1]);return b
 def flat(b):return [b.peek(i)for i in range(65536)]
 def cpu(b,entry,stop=0x200,registers=None):
  c=MPU(memory=b,pc=entry);c.sp=0xfd;c.p=32;b.cpu=c
  for k,v in(registers or{}).items():setattr(c,k,v)
  for i in range(200000):
   if i and c.pc==stop:return c,i
   if c.disassemble[b.peek(c.pc)][0]=='???':raise RuntimeError(f'Original opcode ${c.pc:04X}')
   visited.add((b.origin(c.pc)[0],c.pc));b.pc=c.pc;b.step_no=i;c.step()
  raise RuntimeError(f'Original budget ${c.pc:04X}')
 def compare(group,b,entry,fn,stop=0x200,registers=None,scratch=False,notes=None):
  m=flat(b);source=TacticalEffects(m,data)
  try:
   result=fn(source);c,n=cpu(b,entry,stop,registers)
   addresses=[i for lo,hi in DECLARED_RAM_RANGES for i in range(lo,hi)if scratch or not 0x20<=i<0x30]
   rd=[(i,m[i],b[i])for i in addresses if m[i]!=b[i]][:16];sd=[(0x6000+i,m[0x6000+i],b.sram[i])for i in range(8192)if m[0x6000+i]!=b.sram[i]][:16]
   good=not(rd or sd);counts[group]+=1
   if group=='supported_effect_dispatch':
    tactic=notes['tactic'];outcome='deployed'if tactic==11 else 'succeeded'if result.get('success')else'failed'
    effect_outcomes[(tactic,outcome)]+=1
    if outcome=='succeeded'and tactic not in first_success:
     first_success.add(tactic);rows.append({'group':group,'entry':entry,'stop':stop,'instructions':n,'result':result,'notes':notes,'passed':good,'first_success':True})
   if group=='secondary_trigger_and_consume':secondary_outcomes[result.get('reason')]+=1
   if not good:failures.append({'group':group,'entry':entry,'stop':stop,'ram':rd,'sram':sd,'notes':notes,'result':result})
   if group in ['AI_ambush_AP_bypass','continuous_deploy_expiry','secondary_trigger_and_consume']or notes and notes.get('sample'):rows.append({'group':group,'entry':entry,'stop':stop,'instructions':n,'result':result,'notes':notes,'passed':good})
   return m,result,c
  except Exception as exc:counts[group]+=1;failures.append({'group':group,'entry':entry,'error':str(exc)[:1200],'notes':notes});return m,None,None
 # Raw16 deployment with underflow/high6 borrow, both sides and all officer IDs.
 for i in range(512):
  b=fresh();actor=i%20;ident=i%237;b[0x50a]=actor;b[0x664+actor]=ident;b[0x504]=(i&1)*128;b[0x501]=i&255
  addr=0x63c0+12*ident;raw=[0,1,99,100,101,255,256,1023,1024,65535][i%10]if i<256 else rng.randrange(65536)
  b[addr+8]=raw&255;b[addr+9]=raw>>8
  compare('raw16_deployment',b,0xb42a,lambda s:s.deploy(),notes={'raw_word':raw,'side':b[0x504]})
 for terrain in range(6):
  for raw in [0,99,100,255,256,1023,1024,65535]:
   for side in [0,128]:
    for cached in [255,0]:
     b=fresh();b[0xb]=terrain;b[0x50a]=0;b[0x504]=side;b[0x4d8+(4 if side else 0)]=cached;addr=0x63c0+12*b[0x664];b[addr+8]=raw&255;b[addr+9]=raw>>8
     m,result,c=compare('player_ambush_eligibility',b,0xaf73,lambda s:s.ambush_eligible(terrain))
     if c is not None and bool(c.p&1)!=result:failures.append({'group':'eligibility_carry','raw':raw,'terrain':terrain,'side':side})
 # Recovered ordinary effects, true success gate/RNG/loss/experience and aliases.
 for tactic in SUPPORTED_EFFECT_IDS:
  for i in range(128):
   b=fresh();b[0x543]=tactic;b[0x50a]=0;b[0x509]=0 if i&1 else 10;b[0x501]=i&255;b[0x504]=(i&2)*64;b[0x50]=2*i;b[0x50f]=3 if i%3==0 else 0;b[0x6f02]=i%3
   for slot in [0,10]:
    addr=0x63c0+12*b[0x664+slot];b[addr+1]=[50,85,90,100][i%4];b[addr+2]=[0,50,92,100][(i+slot)%4]
    xp=[0,999,49999,65535][i%4];b[addr+6]=xp&255;b[addr+7]=xp>>8;b[addr+11]=((i%8)<<4)|(i%4)
    troops=[0,1,99,100,255,256,700,1000][i%8];b[addr+8]=troops&255;b[addr+9]=(troops>>8)|[0,4,128,252][i%4]
   b[0x600]=10;b[0x614]=14;b[0x60a]=10+(i%7);b[0x61e]=14
   compare('supported_effect_dispatch',b,0xb02b,lambda s:s.dispatch(),notes={'tactic':tactic,'variant':i,'sample':i<2})
 # Unrecovered effects stop at the real handler after the B02B clear prefix.
 for tactic in range(16):
  if tactic in SUPPORTED_EFFECT_IDS:continue
  b=fresh();b[0x543]=tactic
  compare('unrecovered_effect_boundaries',b,0xb02b,lambda s:s.dispatch(),stop=data.tactical and __import__('source.recovered.battle',fromlist=['TACTIC_ENTRY_POINTS']).TACTIC_ENTRY_POINTS[tactic])
 for i in range(512):
  b=fresh(8);b[0x4db]=i&255;b[0x4df]=(255-i)&255;b[0x4d8]=i%20;b[0x4dc]=(i+1)%20
  compare('all_byte_expiry_boundaries',b,0xce20,lambda s:s.tick_expiry())
 for slot in range(20):
  for pattern in range(4):
   b=fresh();b[0x4d8]=slot if pattern&1 else 255;b[0x4dc]=slot if pattern&2 else 255
   compare('both_slot_reference_clear',b,0xb341,lambda s:s.clear_cached_slot(slot),stop=0xb353,registers={'y':slot})
   b=fresh(8);b[0x4d8]=slot if pattern&1 else 255;b[0x4dc]=slot if pattern&2 else 255;b[0]=slot
   compare('first_whole_cache_and_unit_remove',b,0xd6cd,lambda s:s.remove_unit(slot))
 # Player fee is byte subtraction even if prevalidated costs are bypassed in a
 # direct CPU fixture; no animation completion flag is manufactured.
 for tactic in SUPPORTED_EFFECT_IDS:
  for ap in [0,1,9,10,255]:
   b=fresh();b[0x543]=tactic;b[0x50a]=0;b[0x509]=10;b[0x505]=ap;b[0x4c8]=0;b[0x501]=4
   compare('player_cast_after_real_animation_contract',b,0xaa6c,lambda s:s.player_cast_after_animation(),notes={'tactic':tactic,'ap':ap,'sample':tactic in [0,11]})
 for i in range(1,256):
  b=fresh();b[0x4c8]=i
  compare('animation_not_acknowledged',b,0xaa6c,lambda s:s.player_cast_after_animation())
 for tactic in range(16):
  b=fresh();b[0x543]=tactic;b[0x509]=10;b[0x501]=3
  compare('actual_confirmation_animation_queue_body',b,0xaa3f,lambda s:s.queue_player_animation_after_confirmation())
  b=fresh();b[0x6f8d]=tactic;b[0x6f8c]=0;b[0x6f8e]=10;b[0x501]=8
  compare('AI_ambush_AP_bypass'if tactic==11 else'AI_target_summary_boundary',b,0xc004,lambda s:s.prepare(),stop=0xc1c8 if tactic==11 else 0xc016,notes={'tactic':tactic})
  for ap in [0,10,255]:
   b=fresh();b[0x6f8d]=tactic;b[0x505]=ap;b[0x501]=8
   compare('AI_cost_and_real_queue_prefix',b,0xc01b,lambda s:s.prepare_after_portrait(),stop=0xc03d)
 for tactic in SUPPORTED_EFFECT_IDS:
  if tactic==11:continue
  b=fresh();b[0x6f8d]=tactic;b[0x6f8c]=0;b[0x6f8e]=10;b[0x501]=10
  compare('AI_cast_after_real_portrait_contract',b,0xc083,lambda s:s.cast_after_portrait(),stop=0xc0a7)
 for tactic in range(16):
  for outcome in [0,255]:
   for dead in [0,255]:
    b=fresh();b[0x543]=tactic;b[0x544]=outcome;b[0x432]=dead;b[0x42c]=0;b[0x42d]=0
    compare('AI_result_message_queue',b,0xc0aa,lambda s:s.finish_after_graphics())
 for request in [0,1,2,255]:
  b=fresh();b[0x6f8b]=request;b[0x509]=0;b[0x501]=3
  compare('real_secondary_request_poll',b,0xa51f,lambda s:s.request_secondary_after_move())
 # One local class0 cell is derived from the original maps, no terrain patch.
 fb=fresh(8);fm=flat(fb);dec=TacticalDecisions(fm,data.tactical)
 xy=next((x,y)for y in range(20)if y!=15 for x in range(1,30)if dec._terrain(x,y)==0)
 for side in [0,128]:
  for i in range(32):
   b=fresh(8);actor=10 if side else 0;cached=0 if side else 10;group=0 if side else 4
   b[0x504]=side;b[0x6f8b]=1;b[0x6f8c]=actor;b[0x600+actor],b[0x614+actor]=xy
   b[0x4d8+group]=cached if i%4 else 255;b[0x4d9+group]=xy[0]+[0,1,2,3][i%4];b[0x4da+group]=xy[1]
   b[0x6f92]=i*7
   compare('secondary_trigger_and_consume',b,0xb933,lambda s:s.trigger(),scratch=True,notes={'side':side,'variant':i,'map_xy':xy})
 for side in [0,128]:
  for i in range(16):
   b=fresh();actor=10 if side else 0;cached=0 if side else 10;group=0 if side else 4
   b[0x504]=side;b[0x6f8b]=255;b[0x6f8f]=0;b[0x6f8c]=actor;b[0x509]=actor;b[0x4d8+group]=cached
   b[0x42c]=[0,1,255,100][i%4];b[0x42d]=i&3
   compare('secondary_experience_suffix_to_portrait',b,0xa535,lambda s:s.consume_secondary(),stop=0xa5bb)
   b=fresh();b[0x504]=side;b[0x52e]=0;b[0x4d8+group]=cached
   compare('cache_clear_after_actual_confirmation',b,0xa5ea,lambda s:s.clear_triggered_cache_after_confirmation(),stop=0xa200)
 # Exact independent post-service continuations, no service is bypassed here.
 for entry,fn in [(0xc040,lambda s:s.advance_after_audio()),(0xa5c0,lambda s:s.finish_secondary_after_portrait()),
                  (0xa1f7,lambda s:s.finish_ambush_after_first_graphics()),(0xa203,lambda s:s.finish_cursor_reset_after_graphics())]:
  for i in range(8):
   b=fresh();b[0x509]=i;b[0x50a]=19-i
   compare('declared_post_service_windows',b,entry,fn,stop=0xa200 if entry==0xa1f7 else 0x200)
 # A203's RTS really returns to C1CE, JMP C1F0, then the caller. This is
 # one continuous original CPU chain after the second real graphics service;
 # the additional stack word is the actual C1CB JSR A1F7 return, not an ack.
 for i in range(8):
  b=fresh();b.ram[0x1fc:0x1fe]=bytes([0xcd,0xc1]);b[0x500]=8;b[0x501]=9;b[0xa4]=i
  compare('continuous_second_graphics_return_chain',b,0xa203,lambda s:s.finish_ambush_after_second_graphics(),registers={'sp':0xfb})
 for request in [0,1,254]:
  b=fresh();b[0x6f8b]=request
  compare('secondary_suffix_waits_without_ack',b,0xa535,lambda s:s.consume_secondary())
 for outcome in [1,3,255]:
  b=fresh();b[0x6f8b]=255;b[0x6f8f]=outcome
  compare('secondary_suffix_no_effect',b,0xa535,lambda s:s.consume_secondary(),stop=0xa200)
 for side in [0,128]:
  for martial in [1,255]:
   b=fresh();b[0x504]=side;b[0x52e]=martial;b[0x50a]=10 if side else 0
   compare('cache_clear_before_actual_level_query',b,0xa5ea,lambda s:s.clear_triggered_cache_after_confirmation(),stop=0xa606)
 # Only5 true round ticks expire normal deployments; two independent sides.
 for side in [0,128]:
  b=fresh();b[0x504]=side;b[0x50a]=0
  compare('continuous_deploy_expiry',b,0xb42a,lambda s:s.deploy())
  for tick in range(6):
   b.banks=[6,8,9,31];compare('continuous_deploy_expiry',b,0xce20,lambda s:s.tick_expiry(),notes={'side':side,'tick':tick})
 for i in range(512):
  b=fresh();slot=i%20;b[0x509]=slot;b[0x664+slot]=i%237;side=128 if i&1 else 0
  b[0x628+slot]=side|(i&127);b[0x504]=side^128
  address=0x63c0+12*(i%237);raw=[0,1,99,100,255,256,1000,1023,1024,65535][i%10]
  b[address+8]=raw&255;b[address+9]=raw>>8;troops=raw&1023
  total=[0,max(0,troops-1),troops,min(65535,troops+1),65535][(i//10)%5]
  where=0x51c if side else 0x51a;counter=0x51f if side else 0x51e;b[where]=total&255;b[where+1]=total>>8;b[counter]=i&255
  compare('retreat_masked_troops_and_counter_accounting',b,0xc91e,lambda s:s.detach_unit_accounting(),notes={'slot':slot,'side':side,'raw_officer_word':raw,'total':total,'count':i&255,'sample':i<10})
 evidence=json.loads((args.out/'evidence.json').read_text())
 for r in evidence['ranges']:
  raw=bytes.fromhex(r['raw_hex']);assert rom[r['file_start']:r['file_start']+len(raw)]==raw
 guards=0
 for slot in [-1,20]:
  m=flat(fresh());s=TacticalEffects(m,data)
  try:s.clear_cached_slot(slot);ok=False
  except ValueError:ok=True
  guards+=1
  if not ok:failures.append({'group':'invalid_slot_guard','slot':slot})
 report={'status':'passed'if not failures else'failed','rom_sha256':ROM_SHA256,'case_count':sum(counts.values())+guards,'rom_cpu_case_count':sum(counts.values()),'source_guard_case_count':guards,'failed_count':len(failures),
  'counts':dict(counts),'fully_recovered_effect_ids':list(SUPPORTED_EFFECT_IDS),'source_sha256':sha(ROOT/'source/recovered/tactical_effects.py'),'validator_sha256':sha(Path(__file__).resolve()),'evidence_sha256':sha(args.out/'evidence.json'),
  'supported_effect_outcomes':{str(i):{k:effect_outcomes[(i,k)]for k in ['succeeded','failed','deployed']}for i in SUPPORTED_EFFECT_IDS},'secondary_outcomes':dict(secondary_outcomes),
  'dependency_source_sha256':{n:sha(ROOT/'source/recovered'/n)for n in ['battle.py','game_algorithms.py','tactical_decisions.py']},
  'fixture_source':str(prefix.relative_to(ROOT)),'fixture_source_sha256':{suffix:sha(Path(str(prefix)+suffix))for suffix in ['-ram.bin','-sram.bin']},
  'declared_RAM_ranges':[list(r)for r in DECLARED_RAM_RANGES],'excluded_RAM_scratch':'0020..002F excluded except complete secondary trigger; CPU work pointers0000..0011/stack/cursor51/mapper excluded',
  'all_SRAM_compared_bytes':8192,'native_instruction_locations':len(visited),'source_uses_IR_or_original_CPU':False,'graphics_audio_acknowledged':False,
  'rows':rows,'failures':failures,'limitations':['Declared gameplay RAM+allSRAM compared; no CPU register/SP/mapper equality claim.','after_* input windows require actual preceding graphics/audio/readiness.','Only8 named effect bodies recovered here; other IDs stop at explicit entry boundaries.','TTL API is CE20 tail of original fullround hook, not complete round/NMI processing.','Controlled CPU fixtures do not prove native graphics rendering.']}
 (args.out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:report[k]for k in ['status','case_count','rom_cpu_case_count','source_guard_case_count','failed_count','counts']},ensure_ascii=False))
 if failures:raise SystemExit(1)
if __name__=='__main__':main()
