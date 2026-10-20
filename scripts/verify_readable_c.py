#!/usr/bin/env python3
"""Compare compiled C port to the independently ROM-validated Python model."""
import ctypes as C
import hashlib
import json
import random
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from recovered import battle,ai,game_algorithms

class Officer(C.Structure):_fields_=[('bytes',C.c_uint8*12)]
class Rng(C.Structure):_fields_=[('table',C.c_uint8*256),('cursor',C.c_uint8)]

def verify():
    dylib=ROOT/'build/libgame_recovered.dylib';dylib.parent.mkdir(exist_ok=True)
    cmd=['cc','-std=c11','-Wall','-Wextra','-Werror','-O2','-shared','-fPIC',
         str(ROOT/'source/readable_c/game_recovered.c'),'-o',str(dylib)]
    subprocess.run(cmd,check=True)
    lib=C.CDLL(str(dylib));p=C.POINTER(Officer);r=C.POINTER(Rng);u8=C.c_uint8;u16=C.c_uint16
    contracts={'rk_knowledge_tier':([u8],u8),'rk_special_ai_gate':([u8,u8],C.c_bool),
               'rk_strategy_threshold':([p,p,u8,u8,u8],C.c_int),'rk_conversion_threshold':([p,p,u8],C.c_int),
               'rk_strategy_damage_amount':([u16,p,r],u16),'rk_apply_health_loss':([p,u8],u8),
               'rk_award_experience':([p,u16],u8),
               'rk_apply_troop_loss':([p,p,u16,C.POINTER(u16),C.POINTER(u8)],u16),
               'rk_rng_bounded':([r,u8],u8)}
    for name,(args,ret) in contracts.items():getattr(lib,name).argtypes=args;getattr(lib,name).restype=ret
    rand=random.Random(0x6502);results=[]
    raw=(ROOT/'analysis/rom/prg.bin').read_bytes();table=raw[0x3e8ba:0x3e9ba]
    def record(data):return Officer((u8*12)(*data))
    def pair():
        a=bytes(rand.randrange(256) for _ in range(12));t=bytes(rand.randrange(256) for _ in range(12))
        return a,t,record(a),record(t),battle.Officer(a),battle.Officer(t)
    for n in range(256):assert lib.rk_knowledge_tier(n)==ai.knowledge_tier(n)
    results.append({'routine':'knowledge_tier','cases':256})
    for knowledge in range(256):
        for packed in range(0,256,16):assert lib.rk_special_ai_gate(knowledge,packed)==ai.special_ai_gate(knowledge,packed)
    results.append({'routine':'special_ai_gate','cases':4096})
    for name in ['strategy','conversion']:
        for _ in range(1024):
            a,t,ca,ct,pa,pt=pair();distance=rand.randrange(8);phase=rand.randrange(5);environment=rand.randrange(5)
            rng=game_algorithms.PermutationRng(table)
            if name=='strategy':
                expected=battle.strategy_gate(pa,pt,(0,0),(distance,0),phase,environment,rng).threshold
                got=lib.rk_strategy_threshold(C.byref(ca),C.byref(ct),distance,phase,environment)
            else:
                expected=battle.conversion_gate(pa,pt,(0,0),(distance,0),rng).threshold
                got=lib.rk_conversion_threshold(C.byref(ca),C.byref(ct),distance)
            assert got==(-1 if expected is None else expected),(name,a.hex(),t.hex(),got,expected)
        results.append({'routine':name+'_threshold','cases':1024})
    for entry in [0xB070,0xB0EB,0xB188,0xB1E3,0xB4C6,0xB55C]:
        for _ in range(512):
            a,t,ca,ct,pa,pt=pair();cursor=rand.randrange(256)
            cr=Rng((u8*256)(*table),cursor);pr=game_algorithms.PermutationRng(table,[cursor,0,0,0])
            expected=battle.strategy_damage_amount(entry,pa,pr)
            assert lib.rk_strategy_damage_amount(entry,C.byref(ca),C.byref(cr))==expected
            assert cr.cursor==pr.cursors[0]
        results.append({'routine':f'damage_{entry:04X}','cases':512})
    for _ in range(1024):
        a,t,ca,ct,pa,pt=pair();requested=rand.randrange(256)
        expected,loss,_=battle.health_loss_core(pt,requested)
        assert lib.rk_apply_health_loss(C.byref(ct),requested)==loss and bytes(ct.bytes)==expected.raw
    results.append({'routine':'health_loss_core','cases':1024})
    for _ in range(1024):
        a,t,ca,ct,pa,pt=pair();counter=rand.randrange(65536)
        expected,marker=battle.experience_from_accumulated_loss(pa,counter)
        assert lib.rk_award_experience(C.byref(ca),counter)==marker and bytes(ca.bytes)==expected.raw
    results.append({'routine':'experience','cases':1024})
    for _ in range(1024):
        a,t,ca,ct,pa,pt=pair();counter=rand.randrange(65536);requested=rand.randrange(65536)
        ea,et,loss,ec,em=battle.troop_loss(pa,pt,requested,counter)
        cc=u16(counter);cm=u8(0)
        got=lib.rk_apply_troop_loss(C.byref(ca),C.byref(ct),requested,C.byref(cc),C.byref(cm))
        assert (got,cc.value,cm.value,bytes(ca.bytes),bytes(ct.bytes))==(loss,ec,em,ea.raw,et.raw)
    results.append({'routine':'troop_loss_distinct_records','cases':1024})
    for bound in [1,2,14,15,100,255]:
        for cursor in range(256):
            cr=Rng((u8*256)(*table),cursor);pr=game_algorithms.PermutationRng(table,[cursor,0,0,0])
            assert lib.rk_rng_bounded(C.byref(cr),bound)==pr.bounded(bound) and cr.cursor==pr.cursors[0]
    results.append({'routine':'rng_bounded','cases':1536})
    report={'status':'passed','case_count':sum(v['cases'] for v in results),'results':results,
            'compiler_command':cmd,'source_sha256':hashlib.sha256((ROOT/'source/readable_c/game_recovered.c').read_bytes()).hexdigest(),
            'oracle':'compiled C vs reconstructed Python; Python is separately compared with actual ROM instructions',
            'limitations':['This C API supports distinct actor/target records only.',
                           'Action suitability, rendering and complete battle/AI state machines are not implemented.']}
    out=ROOT/'analysis/phase2';out.mkdir(exist_ok=True);(out/'c-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'status':'passed','case_count':report['case_count']}))

if __name__=='__main__':verify()
