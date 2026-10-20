#!/usr/bin/env python3
"""Original-CPU checks for sixteen-effect integration and player settlement.

Compare declared gameplay RAM and all SRAM. Real display/input readiness is a
caller precondition for named after_* suffixes, never an automatic completion.
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from source.recovered.game_engine import GameEngine,ROM_SHA256
from source.recovered.battle_state_machine import Registers
from verify_phase6_integration import oracle,game_from_bus
from verify_tactical_ai_control import native_bus

RAM=[0x12,0x50,0xA4,*range(0x30,0x33),*range(0x300,0x301),*range(0x310,0x314),
     *range(0x42C,0x435),*range(0x4D8,0x4E0),*range(0x500,0x678)]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'))
    a=p.parse_args();rom=a.rom.read_bytes();assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    prefix=ROOT/'analysis/runtime/phase3/attack-intro-7'
    base_ram=Path(str(prefix)+'-ram.bin').read_bytes();base_sram=Path(str(prefix)+'-sram.bin').read_bytes()
    counts=Counter();failures=[];cases=[];native_cases=[]
    guards=[]

    def fresh():
        ram=bytearray(base_ram);ram[0x1FE:0x200]=bytes((255,1))
        # The supplied parent is a unit-menu frame with NMI bank29/30 cached.
        # These synchronous calls explicitly enter bank12/13; both saved
        # mapper contexts must describe that caller for real EE07 restoration.
        ram[0xDE:0xE4]=bytes((38,44,45,38,44,45))
        return native_bus(rom,ram,base_sram,banks=(6,12,13,31))

    def compare(kind,bus,entry,call,stop=0x200,label=None):
        try:
            game=game_from_bus(bus,rom);effects=game.tactical_effect_rules()
            result=call(effects)
            cpu,n=oracle(bus,entry,Registers(a=0,x=0,y=0,sp=0xFD,p=32),stop,max_steps=400000)
            rd=[(hex(i),bus.peek(i),game.memory[i])for i in RAM if bus.peek(i)!=game.memory[i]]
            sd=[(hex(0x6000+i),x,y)for i,(x,y)in enumerate(zip(bus.sram,game.memory.sram))if x!=y]
            assert not rd and not sd,(rd[:12],sd[:12])
            assert game._tactical_control is None
            counts[kind]+=1
            if sum(v['kind']==kind for v in cases)<6:
                cases.append(dict(kind=kind,input=label,entry=entry,stop=stop,
                                  original_instructions=n,result=result,all_SRAM_equal=True))
        except Exception as exc:
            failures.append(dict(kind=kind,input=label,error=f'{type(exc).__name__}: {exc}'))

    def compare_memory(bus,game):
        rd=[(hex(i),bus.peek(i),game.memory[i])for i in RAM if bus.peek(i)!=game.memory[i]]
        sd=[(hex(0x6000+i),x,y)for i,(x,y)in enumerate(zip(bus.sram,game.memory.sram))if x!=y]
        assert not rd and not sd,(rd[:12],sd[:12])

    def resume_original(cpu,bus,stop):
        for n in range(400000):
            if n and cpu.pc==stop:return n
            bus.pc=cpu.pc;bus.step_no=n;cpu.step()
        raise AssertionError(f'Original continuation budget at {cpu.pc:04X}')

    # The canonical GameEngine factory now dispatches all sixteen bodies.
    # Legal high-HP records avoid the separate death-map boundary here, while
    # both observed successful and failed gates are checked in native opcode.
    for tactic in range(16):
        for side in (0,128):
            for cursor in (0,63,127,255):
                bus=fresh();bus.ram[0x543]=tactic;bus.ram[0x50A]=0;bus.ram[0x509]=10
                bus.ram[0x504]=side;bus.ram[0x50]=cursor
                bus.ram[0x600]=10;bus.ram[0x614]=14
                bus.ram[0x60A]=11;bus.ram[0x61E]=14
                for slot,iq in ((0,99),(10,0)):
                    address=0x63C0+12*bus.ram[0x664+slot]
                    bus[address]=100;bus[address+2]=iq;bus[address+3]=0
                    bus[address+6]=152;bus[address+7]=58
                    bus[address+11]=0x70|(bus[address+11]&15)
                compare('all16_GameEngine_dispatch',bus,0xB02B,lambda e:e.dispatch(),
                        label=[tactic,side,cursor])

    # Preserve the actual caller stack through the synchronous D6CC call.
    # It executes only in the oracle; source resumes only after that call has
    # actually returned. No completed graphics flag is inserted in either side.
    for tactic in (1,9):
        for path in ('dispatch','player','AI'):
            for cursor in (0,17,71,127):
                bus=fresh();bus.ram[0x543]=tactic;bus.ram[0x50A]=0;bus.ram[0x509]=1
                bus.ram[0x50]=cursor;bus.ram[0x505]=16;bus.ram[0x501]=6;bus.ram[0x4C8]=0
                bus.ram[0x600]=10;bus.ram[0x614]=14;bus.ram[0x601]=11;bus.ram[0x615]=14
                for slot,iq,hp in ((0,99,100),(1,10,1)):
                    address=0x63C0+12*bus.ram[0x664+slot]
                    bus[address]=hp;bus[address+2]=iq;bus[address+11]=0x70|(bus[address+11]&15)
                bus.sram[0xF8C]=0;bus.sram[0xF8D]=tactic;bus.sram[0xF8E]=1
                try:
                    game=game_from_bus(bus,rom);effects=game.tactical_effect_rules()
                    entry=0xB02B if path=='dispatch' else 0xAA6C if path=='player' else 0xC083
                    final_stop=0xC0A7 if path=='AI' else 0x200
                    call=effects.dispatch if path=='dispatch' else effects.player_cast_after_animation if path=='player' else effects.cast_after_portrait
                    result=call()
                    if effects.individual.pending is None:
                        cpu,n=oracle(bus,entry,Registers(a=0,x=0,y=0,sp=0xFD,p=32),final_stop)
                        compare_memory(bus,game);counts['death_fixture_actual_gate_failure']+=1
                        continue
                    assert result['status']=='dependency' and result['resume']=='after_death_map_refresh'
                    cpu,n=oracle(bus,entry,Registers(a=0,x=0,y=0,sp=0xFD,p=32),0xB615)
                    compare_memory(bus,game)
                    before_ram=bytes(game.memory.ram);before_sram=bytes(game.memory.sram)
                    blocked=effects.after_death_map_refresh(map_refresh_returned=False)
                    assert blocked['status']=='dependency' and bytes(game.memory.ram)==before_ram and bytes(game.memory.sram)==before_sram
                    if not guards:
                        for method in ('dispatch','player_cast_after_animation','cast_after_portrait'):
                            pending=effects.individual.pending
                            try:
                                getattr(effects,method)()
                            except RuntimeError:
                                pass
                            else:
                                raise AssertionError(f'{method} must reject pending death reentry')
                            assert bytes(game.memory.ram)==before_ram and bytes(game.memory.sram)==before_sram
                            assert effects.individual.pending is pending
                            guards.append(dict(method=method,rejected=True,all_memory_unchanged=True))
                    graphics_steps=resume_original(cpu,bus,0xB618)
                    compare_memory(bus,game)
                    result=effects.after_death_map_refresh(map_refresh_returned=True)
                    suffix_steps=resume_original(cpu,bus,final_stop)
                    compare_memory(bus,game)
                    assert effects.individual.pending is None
                    counts['shared_death_prefix_real_service_and_caller_suffix']+=1
                    cases.append(dict(kind='shared_death_prefix_real_service_and_caller_suffix',
                                      input=[tactic,path,cursor],prefix_instructions=n,
                                      actual_oracle_graphics_instructions=graphics_steps,suffix_instructions=suffix_steps,
                                      source_graphics_execution=False,false_return_signal_kept_pending=True,
                                      result=result,all_SRAM_equal=True))
                except Exception as exc:
                    failures.append(dict(kind='shared-death',input=[tactic,path,cursor],error=f'{type(exc).__name__}: {exc}'))

    # The original unit-render scan explicitly waits on007E, then stops at the
    # actual D6CC service. No renderer is substituted in any of these fixtures.
    for cursor in range(20):
        for busy in (0,1,255):
            bus=fresh();bus.ram[0x50B]=cursor;bus.ram[0x7E]=busy
            compare('player_scan_prefix_or_wait',bus,0xAAA7,lambda e:e.player_result_scan(),
                    stop=0xAAB6 if busy==0 else 0x200,label=[cursor,busy])

    for tactic in range(16):
        for cursor in (0,18,19):
            for failed in (0,255):
                for dead in (255,22):
                    for troop_loss in (0,532):
                        bus=fresh();bus.ram[0x50B]=cursor;bus.ram[0x543]=tactic
                        bus.ram[0x544]=failed;bus.ram[0x432]=dead
                        bus.ram[0x42C:0x42E]=troop_loss.to_bytes(2,'little')
                        selected=1 if tactic==9 and troop_loss==0 else tactic
                        death_message=not failed and selected in (1,9)and dead!=255
                        stop=0x200 if cursor<19 or death_message else 0xAADD
                        compare('player_result_after_real_graphics',bus,0xAAB9,
                                lambda e:e.advance_player_result_after_graphics(),stop=stop,
                                label=[tactic,cursor,failed,dead,troop_loss])

    for buttons in range(256):
        bus=fresh();bus.ram[0x81]=buttons
        compare('player_confirmation_suffix',bus,0xAB32,
                lambda e:e.player_confirm_after_text_ready(),stop=0xAB41 if buttons&1 else 0x200,
                label=buttons)

    for i in range(64):
        bus=fresh();bus.ram[0x46C:0x470]=bytes((i,(i+17)&255,(i*3)&255,255-i))
        compare('player_cursor_restore_after_real_nochange_query',bus,0xAB6F,
                lambda e:e.finish_player_without_level_change_after_query(),stop=0xA1F7,label=i)

    for ident in (0,22,24,55,109,236,255):
        for level in (0,2,3,4,5,6,7,15):
            for unchanged in (False,True):
                for martial_delta in (0,5,255):
                    bus=fresh();address=0x63C0+12*ident;bus.ram[0x42C]=ident
                    bus[address+11]=(level<<4)|3;bus[address+1]=martial_delta
                    bus.ram[0x52C]=level<<4 if unchanged else (level<<4)^16
                    bus.ram[0x52E]=0
                    compare('complete_level_query_and_second_notice_gate',bus,0xDEE9,
                            lambda e:e.level_change_query(),label=[ident,level,unchanged,martial_delta])

    for i in range(16):
        bus=fresh();bus.ram[0x501]=i
        compare('level_changed_audio_boundary',bus,0xAB46,
                lambda e:e.player_level_change_after_query(),stop=0xAB49,label=i)

    for buttons in (0,1,2,3,255):
        for notice in (0,22,255):
            bus=fresh();bus.ram[0x81]=buttons;bus.ram[0x42D]=notice
            stop=0xAB67 if buttons&1 and notice==255 else 0x200
            compare('second_notice_or_audio_boundary',bus,0xAB57,
                    lambda e:e.player_second_notice_after_text_ready(),stop=stop,label=[buttons,notice])

    for tactic in range(16):
        for failed in (0,255):
            for dead in (255,22):
                for troop_loss in (0,532):
                    bus=fresh();bus.ram[0x543]=tactic;bus.ram[0x544]=failed
                    bus.ram[0x432]=dead;bus.ram[0x42C:0x42E]=troop_loss.to_bytes(2,'little')
                    compare('all16_AI_result_queue',bus,0xC0AA,lambda e:e.finish_after_graphics(),
                            label=[tactic,failed,dead,troop_loss])

    # The labelled animation checkpoint precedes the actual effect by several
    # frames. Import its unchanged records/map, then use the observed last
    # pre-effect frame's cursor50 and substate as explicit analytical inputs.
    # This changes only the source fixture, never a running original core.
    manifest=json.loads((ROOT/'analysis/phase9/runtime/evidence.json').read_text())
    for row in manifest['native_cases']:
        name=row['case'];path=ROOT/'analysis/phase9/runtime'/name
        try:
            frames=json.loads((path/'frame-fields.json').read_text())
            index=next(i for i,f in enumerate(frames)if f['tactic_0543']==row['tactic_id']
                       and f['result_0544']==0 and f['battle_state']==[5,7])
            before,after=frames[index-1],frames[index]
            game=GameEngine.from_snapshot(path/'effect-before',rom=rom,mapped=True,data_window_bank=6)
            imported=[]
            for address,value in ((0x50,before['fixed_rng_0050_0057'][0]),(0x501,before['battle_state'][1])):
                imported.append(dict(address=address,old=game.memory[address],observed=value,
                                     source=f'{name}/frame-fields.json frame{before["frame"]}'))
                game.memory[address]=value
            assert game.memory[0x509]==before['target_0509'] and game.memory[0x50A]==before['actor_or_scratch_050A']
            for ident,record in before['officer_records'].items():
                address=0x63C0+12*int(ident)
                assert bytes(game.memory[address+i]for i in range(12)).hex(' ').upper()==record['record_hex']
            effects=game.tactical_effect_rules();effect=effects.dispatch()
            used_death_resume=effects.individual.pending is not None
            if used_death_resume:
                # The core has actually completed the death path and removed
                # its slot. This is a postcondition inference from known flow,
                # not a claim of a native D6CC instruction-level observation.
                assert after['unit_arrays']['0x664'][before['target_0509']]==255
                effect=effects.after_death_map_refresh(map_refresh_returned=True)
            assert effect['status']=='returned'
            comparisons=[]
            def check(field,actual,expected):
                assert actual==expected,(field,actual,expected)
                comparisons.append(dict(field=field,source=actual,native=expected,equal=True))
            for ident,record in after['officer_records'].items():
                address=0x63C0+12*int(ident)
                check(f'officer{ident}.raw12',bytes(game.memory[address+i]for i in range(12)).hex(' ').upper(),record['record_hex'])
            check('result0544',game.memory[0x544],after['result_0544'])
            check('substate0501',game.memory[0x501],after['battle_state'][1])
            check('RNGcursor0050',game.memory[0x50],after['fixed_rng_0050_0057'][0])
            check('report042C..0433',[game.memory[a]for a in range(0x42C,0x434)],after['report_042C_0433'])
            check('resources0520..0527',[game.memory[a]for a in range(0x520,0x528)],after['resources_0520_0527'])
            check('counts/totals051A..051F',[game.memory[a]for a in range(0x51A,0x520)],after['side_aggregates_0518_051F'][2:])
            check('cache04D8..04DF',[game.memory[a]for a in range(0x4D8,0x4E0)],after['cache_04D8_04DF'])
            for base in (0x600,0x614,0x628,0x650,0x664):
                check(f'unit_array{base:04X}',[game.memory[base+i]for i in range(20)],after['unit_arrays'][hex(base)])
            fee=effects.data.player_costs[row['tactic_id']]
            check('AP fee table vs actual cast',(before['AP_0505']-fee)&255,after['AP_0505'])
            native_cases.append(dict(case=name,before_frame=before['frame'],after_frame=after['frame'],
                                     source_input_checkpoint=f'{name}/effect-before',observed_context_import=imported,
                                     inferred_sync_death_call_return=used_death_resume,native_instruction_trace=False,
                                     comparisons=comparisons,scope='Listed gameplay effects only; animation readiness, AP commit and video timing belong to the original core.'))
        except Exception as exc:
            failures.append(dict(kind='native-effect-fields',input=name,error=f'{type(exc).__name__}: {exc}'))

        # Independently prove the canonical targeting factory against AD80 on
        # this confirmed core context. This is a synchronous CPU fixture and
        # adds no new native frame or target-selection input event.
        try:
            ram=bytearray((path/'cast-confirmation-ram.bin').read_bytes())
            ram[0x1FE:0x200]=bytes((255,1));ram[0xDE:0xE4]=bytes((38,44,45,38,44,45))
            bus=native_bus(rom,ram,(path/'cast-confirmation-sram.bin').read_bytes(),banks=(6,12,13,31))
            game=game_from_bus(bus,rom);targeting=game.player_tactic_targeting_rules()
            result=targeting.eligible(row['tactic_id'])
            cpu,n=oracle(bus,0xAD80,Registers(a=0,x=0,y=0,sp=0xFD,p=32),0x200)
            declared=(0x0A,0x0B,0x10,0x11,0x509,0x50A,0x543)
            assert all(bus.peek(a)==game.memory[a]for a in declared)
            assert bytes(bus.sram)==bytes(game.memory.sram)
            assert bool(cpu.p&1)==result['carry']==result['eligible'] is True
            counts['shared_targeting_confirmed_context_CPU']+=1
            cases.append(dict(kind='shared_targeting_confirmed_context_CPU',case=name,
                              original_instructions=n,returned_carry=True,result=result))
        except Exception as exc:
            failures.append(dict(kind='shared-targeting',input=name,error=f'{type(exc).__name__}: {exc}'))

    # Two real level-notification confirmations, projected only to their
    # declared memory fields. The original core still owns text readiness,
    # queued-message drawing and the audio calls between these checkpoints.
    level_path=ROOT/'analysis/phase9/runtime/tactic-09-levelup'
    level_frames=json.loads((level_path/'frame-fields.json').read_text())
    for label,checkpoint,frame,second in (
            ('core-level-query','result-message',1568,False),
            ('core-second-notice','continuation-1',1810,True)):
        try:
            game=GameEngine.from_snapshot(level_path/checkpoint,rom=rom,mapped=True,data_window_bank=6)
            after=level_frames[frame-1];game.memory[0x81]=after['button_0081_0087'][0]
            assert game.memory[0x81]&1
            effects=game.tactical_effect_rules()
            if second:result=effects.player_second_notice_after_text_ready()
            else:
                request=effects.player_confirm_after_text_ready();assert request['pc']==0xAB41
                query=effects.level_change_query();assert query['level_changed'] and query['martial_delta_byte']==5
                result=effects.player_level_change_after_query()
            source_report=[game.memory[a]for a in range(0x42C,0x434)]
            assert source_report==after['report_042C_0433']
            assert game.memory[0x501]==after['battle_state'][1]
            native_cases.append(dict(case=label,before_checkpoint=f'tactic-09-levelup/{checkpoint}',after_frame=frame,
                                     observed_button_byte=game.memory[0x81],source_status=result['status'],
                                     comparisons=[dict(field='report042C..0433',source=source_report,native=after['report_042C_0433'],equal=True),
                                                  dict(field='substate0501',source=game.memory[0x501],native=after['battle_state'][1],equal=True)],
                                     scope='Actual original confirmation inputs; text completion and audio/rendering are not simulated here.'))
        except Exception as exc:
            failures.append(dict(kind=label,error=f'{type(exc).__name__}: {exc}'))

    result=dict(status='passed'if not failures else'failed',rom_sha256=ROM_SHA256,
                actual_ROM_CPU_comparison_count=sum(counts.values()),counts=dict(counts),
                native_core_field_comparison_count=len(native_cases),native_core_field_cases=native_cases,
                source_guard_count=len(guards),source_guards=guards,
                failures=failures,cases=cases,all_SRAM_compared_bytes=8192,declared_RAM_addresses=RAM,
                source_original_code_calls=0,semantic_source_IR_interpretation=False,
                limits=['Result scan stops at D6CC; no graphics completion is claimed.',
                        'Named after_* fixtures begin after the actual preceding service by their explicit contract.',
                        'CPU registers/stack/mapper writes and whole NES video frames are outside this semantic comparison.'],
                source_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest()for name in (
                    'source/recovered/game_engine.py','source/recovered/tactical_effects_complete.py',
                    'source/recovered/tactic_individual_effects.py','source/recovered/tactic_area_conversion.py',
                    'source/recovered/player_tactic_targeting.py')})
    out=ROOT/'analysis/phase9/source-integration.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({**{k:result[k]for k in ('status','actual_ROM_CPU_comparison_count','counts')},
                      'failed_count':len(failures),'failure_examples':failures[:8]},ensure_ascii=False))
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
