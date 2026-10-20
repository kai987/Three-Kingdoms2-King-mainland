#!/usr/bin/env python3
"""Verify actual phase5 GameEngine APIs, shared memory and explicit boundaries.

Original ROM CPU execution is the comparator, never a fallback hook installed
in source GameEngine. Complete returns and strict dependency-prefix comparisons
are counted separately. No ack1 is injected: any ack comes from original CBBD.
"""
from pathlib import Path
from collections import Counter
from importlib.metadata import version
import argparse, hashlib, json, sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from source.recovered.game_engine import GameEngine,UnresolvedScene,snapshot_memory,ROM_SHA256
from source.recovered.mapped_memory import PrgDataMemory,UnsupportedHardware
from source.recovered.controller_helpers import MissingSharedHelper
from source.recovered.battle_state_machine import UnresolvedDependency
from source.recovered.domestic_ai import RulerTurnControl
from source.recovered.officer_transfer import officer_address,city_address,ruler_address
from verify_officer_transfer import TransferOracle,context,record,city,flags
from verify_domestic_ai import fresh,execute

DEPENDENCY_ERRORS=(MissingSharedHelper,UnresolvedDependency,UnsupportedHardware)
SOURCE_FILES=('source/recovered/game_engine.py','source/recovered/domestic_ai.py','source/recovered/officer_transfer.py','source/recovered/troop_fields.py','source/recovered/mapped_memory.py','source/recovered/runtime_services.py','source/recovered/controller_helpers.py','source/recovered/battle_state_machine.py','analysis/phase5/domestic-ai/program.json','analysis/phase5/domestic-ai/turn-program.json','analysis/phase4/services/program.json')

def game_from_bus(bus,rom):
    if hasattr(bus,"bus"):bus=bus.bus
    game=GameEngine(snapshot_memory(bytes(bus.ram),bytes(bus.sram)),rom=rom,mapped=True,data_window_bank=bus.banks[0])
    game.memory.banks[:]=bus.banks
    return game

def sram_compare(bus,game,label):
    got=bytes(game.memory.sram);expected=bytes(bus.sram)
    assert got==expected,(label,'SRAM',[(hex(0x6000+i),expected[i],got[i])for i in range(8192)if got[i]!=expected[i]][:12])

def controller_compare(bus,game,cpu,label):
    sram_compare(bus,game,label);assert bytes(bus.ram)==bytes(game.memory.ram),(label,'RAM',[(hex(i),bus.ram[i],game.memory.ram[i])for i in range(2048)if bus.ram[i]!=game.memory.ram[i]][:12])
    assert bus.banks==game.memory.banks,(label,'mapper',bus.banks,game.memory.banks)
    controller=game._domestic_control if label.startswith('domestic')else game._ruler_turn_control
    got=controller.registers
    assert all(getattr(cpu,n)==getattr(got,n)for n in ('a','x','y','sp','p','pc')),(label,'CPU',vars(got),{n:getattr(cpu,n)for n in ('a','x','y','sp','p','pc')})
    assert controller.machine.memory is game.memory


def verify(rom):
    assert hashlib.sha256(rom).hexdigest()==ROM_SHA256
    start_hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in SOURCE_FILES}
    counts=Counter();cases=[];failures=[];mapping_checks=[];guards=[];semantics=[];waits=[]
    def shared(game):
        assert game.transfer_rules().memory is game.memory and game.troop_rules().memory is game.memory
        assert game.transfer_rules() is game.transfer_rules() and game.troop_rules() is game.troop_rules()
    def observe_mapping(game):
        seen=[];original=game.memory.activate_scene
        def observed(pair,data_bank):
            original(pair,data_bank);seen.append(list(game.memory.banks))
        game.memory.activate_scene=observed
        return seen
    def api_case(name,pair,entry,setup,action,*,stop=None,ram=()):
        bus=context(rom,pair);setup(bus);game=game_from_bus(bus,rom);shared(game)
        before=[game.officer(i).troops_raw for i in range(237)]
        result=action(game);bus.run(entry,stop=None if stop is None else lambda pc:pc==stop)
        sram_compare(bus.bus,game,name)
        for address in ram:assert bus.get(address)==game.memory[address],(name,hex(address))
        after=[game.officer(i).troops_raw for i in range(237)]
        assert before==after,(name,'transfer changed raw troop storage')
        assert all(game.troop_rules().views(i).raw_word==after[i]for i in range(237))
        if isinstance(result,dict)and'cpu_flags'in result:flags(bus,result)
        counts['unified_transfer_actual_ROM']+=1;semantics.append({'api':name,'entry':hex(entry),'stop':hex(bus.cpu.pc),'all_SRAM_equal':True,'all237_raw_troop_words_preserved':True})
    for raw in (0,999,1000,1023,1098,0xABCD,0xFFFF):
        def stats(bus,raw=raw):
            record(bus,20,virtue=90);record(bus,30,loyalty=99,status=0xEE)
            bus.load(officer_address(30)+8,[raw&255,raw>>8])
        def move_setup(bus):
            stats(bus);city(bus,3,0,[20,30,31]);city(bus,4,0,[40]);bus.load(0x0470,[3,4]);bus.load(0x0481,[30]+[255]*9);bus.load(0xEE,[7,0x6F])
        api_case('move_roster_group',27,0xAD41,move_setup,lambda g:g.transfer_rules().move_roster_group(3,4),ram=range(0x0481,0x048B))
        def recruit_setup(bus):stats(bus);city(bus,3,0,[20]);bus.set(0x0402,3);bus.set(0x0472,30)
        api_case('recruit_officer',27,0xACF0,recruit_setup,lambda g:g.transfer_rules().recruit_officer(3,30),stop=0xAD37,ram=(0x30,0x31))
        def release_setup(bus):
            stats(bus);city(bus,3,0,[30]);bus.load(0,[officer_address(30)&255,officer_address(30)>>8]);bus.load(0x10,[city_address(3)&255,city_address(3)>>8]);bus.set(0x040E,3);bus.set(0x040F,17);bus.set(0x31,30)
        api_case('release_city_officer',25,0xC099,release_setup,lambda g:g.transfer_rules().release_city_officer(3,17,30),stop=0xC0E2,ram=(0x0402,0x042C))
        def install_setup(bus):stats(bus);city(bus,3,0,[30]);bus.set(0x40,0);bus.set(0x27,30)
        api_case('install_ai_successor',10,0xCB52,install_setup,lambda g:g.transfer_rules().install_ai_successor(0,30),stop=0xCB79,ram=(0x27,0x45,0x52))
        for name,entry in [('loyalty_for_recruitment',0xA006),('loyalty_after_capture',0xA00C)]:
            def loyalty_setup(bus):stats(bus);bus.set(0x30,20);bus.set(0x31,30);bus.set(0x20,30)
            api_case(name,10,entry,loyalty_setup,lambda g,name=name:getattr(g.transfer_rules(),name)(20,30)if name=='loyalty_for_recruitment'else g.transfer_rules().loyalty_after_capture(30))
    # Use actual core's committed raw1098 record as input, with an explicit
    # direct-entry mapper/control fixture. No new natural transfer navigation.
    prefix=ROOT/'analysis/phase5/troops/core-fixture/committed-overflow'
    bus=TransferOracle(rom,27);bus.load(0,Path(str(prefix)+'-ram.bin').read_bytes());bus.load(0x6000,Path(str(prefix)+'-sram.bin').read_bytes());bus.load(0xE1,[0x31,0x3B,0x3C]);bus.load(0xEE,[0x17,0x6F]);bus.load(0x0470,[11,12]);bus.load(0x0481,[131]+[255]*9)
    city(bus,12,2,[]);game=game_from_bus(bus.bus,rom);shared(game);assert game.officer(131).troops_raw==1098
    game.transfer_rules().move_roster_group(11,12);bus.run(0xAD41);sram_compare(bus.bus,game,'core-record1098 move');assert game.officer(131).troops_raw==game.troop_rules().views(131).raw_word==1098;assert game.city(12).roster[0]==131
    counts['core_snapshot_troop_preservation_transfer']+=1
    def controller_case(kind,bus,controller=None,tag=None):
        game=game_from_bus(bus,rom);shared(game);seen=observe_mapping(game);error=None
        entry=0xA00F if kind=='domestic'else RulerTurnControl.ENTRIES[controller]
        try:
            if kind=='domestic':game.tick_domestic_ai(max_instructions=1000000)
            else:game.tick_ruler_turn(controller,max_instructions=1000000)
        except DEPENDENCY_ERRORS as e:error={'type':type(e).__name__,'message':str(e)}
        except Exception as e:
            failures.append({'case':tag,'stage':'source','error':f'{type(e).__name__}: {e}'});return
        machine=game._domestic_control if kind=='domestic'else game._ruler_turn_control
        stop=machine.registers.pc if error else 0x200
        try:
            expected,steps=execute(bus,entry,stop=stop)
            label='domestic-'+str(tag)if kind=='domestic'else 'turn-'+str(tag)
            controller_compare(bus,game,expected,label)
            pair=10 if kind=='domestic'else 25
            assert seen[0]==[2,pair,pair+1,31],(tag,seen)
            for service_key, service in game.services.items():
                if service_key == 'global-main':
                    # Phase6 bridges only the explicitly recovered source
                    # controllers, preserving the actual caller's stack.
                    assert service.fallback.__self__ is game
                    assert service.fallback.__func__ is GameEngine._global_source_call
                    assert game._global_user_hooks is None
                else:
                    assert service.fallback is None, 'Source was supplied an original-ROM fallback'
            name=kind+'_complete_source_return'if error is None else kind+'_strict_dependency_prefix'
            counts[name]+=1;mapping_checks.append({'case':tag,'entry_banks':seen[0],'final_banks':list(game.memory.banks)})
            cases.append({'case':tag,'controller':controller or'global_AI','original_entry':hex(entry),'status':'returned'if error is None else'explicit_dependency_boundary','source_pc':hex(stop),'original_instructions':steps,'dependency':error,'source_fixed_service_calls':len(game.services['domestic-global'if kind=='domestic'else'ruler-turn'].calls),'source_original_ROM_fallback':False})
        except Exception as e:failures.append({'case':tag,'stage':'original comparison','error':f'{type(e).__name__}: {e}'})
    for ruler in range(7):
        for difficulty in range(3):
            for flag in (255,0,1):
                b=fresh(rom,10);b[0x6F03]=ruler;b[0x6F02]=difficulty;b[0x6F8B]=flag;b[0x6F5B]=0;b[0x6F5D]=30;b[0x6F62]=0;b[0x52]=(ruler*13+difficulty*7)&255;b[0xEE]=ruler_address(ruler)&255;b[0xEF]=ruler_address(ruler)>>8
                if flag==1:
                    # Controlled valid battle-return scratch. Menu0038=222 is
                    # an officer/menu scratch byte, not a valid targetcity.
                    b[0x38]=4;b[0x39]=11;b[0x37]=3;b[0x3A]=3
                controller_case('domestic',b,tag=f'AI:ruler{ruler}:difficulty{difficulty}:flag{flag}')
    catalog=json.loads((ROOT/'analysis/phase5/domestic-ai/turn-controllers.json').read_text())
    for c in catalog['controllers']:
        for sub in range(c['count']):
            for idle in (0,255):
                for button in (0,1):
                    b=fresh(rom,25)
                    for address,value in {0x401:sub,0x402:0,0x400:0 if c['name']=='calendar'else 10 if c['name']=='turn_events'else 9,0x300:idle,0x304:idle,0x81:button,0x7c:0,0x7e:0,0x140:0,0x4a0:0,0x6f03:2,0x6f04:2,0x6f05:3,0x6f06:0,0x6f8b:255,0x40c:0,0x470:0,0x471:0,0x472:0,0x473:0,0x478:0,0x40b:131,0x40a:2,0x40e:11}.items():b[address]=value
                    b[0xEE]=0x17;b[0xEF]=0x6F
                    controller_case('turn',b,c['name'],tag=f'{c["name"]}:sub{sub}:job{idle}:button{button}')
    # Exact CB7F/CB9D timers: source drives only actual controller code, no
    # script store of6F8B=1 and no graphic/job completion substitution.
    for pending,start_state in ((252,11),(251,12)):
        for counter in (0,1,238,239):
            b=fresh(rom,25);b[0x401]=start_state;b[0x40C]=counter;b[0x6F8B]=pending;b[0xEE]=0x17;b[0xEF]=0x6F;b[0x300]=b[0x304]=0
            game=game_from_bus(b,rom);shared(game);game.tick_ruler_turn('ruler_ai_scene');cpu,steps=execute(b,0xC773);controller_compare(b,game,cpu,'wait-timer')
            if counter<239:assert game.memory[0x6F8B]==pending
            elif start_state==11:assert game.memory[0x6F8B]==pending and game.memory[0x401]==12
            else:assert game.memory[0x6F8B]==1 and game.memory[0x401]==1
            waits.append({'pending_flag_before':pending,'substate_before':start_state,'counter_before':counter,'flag_after':game.memory[0x6F8B],'substate_after':game.memory[0x401],'counter_after':game.memory[0x40C],'ack_injected':False,'ack_origin':'actual recovered CBBD..CBBF'if game.memory[0x6F8B]==1 else'pending remains'})
            counts['actual_FC_FB_wait_timer_paths']+=1
    sequences=[]
    for pending,start_state,calls_required in ((252,11,480),(251,12,240)):
        b=fresh(rom,25);b[0x401]=start_state;b[0x40C]=0;b[0x6F8B]=pending;b[0xEE]=0x17;b[0xEF]=0x6F;b[0x300]=b[0x304]=0
        game=game_from_bus(b,rom);checkpoints=[]
        for tick in range(1,calls_required+1):
            # Both direct calls enter with explicit pair25/data2. This is not
            # an emulated NMI and never sets queue completion/acknowledgement.
            b.banks[:]=[2,25,26,31]
            game.tick_ruler_turn('ruler_ai_scene');cpu,steps=execute(b,0xC773);controller_compare(b,game,cpu,'wait-sequence')
            if tick<calls_required:assert game.memory[0x6F8B]==pending
            else:assert game.memory[0x6F8B]==1 and game.memory[0x401]==1
            counts['FC_FB_default_controller_sequence_calls']+=1
            if tick in (1,239,240,479,480):checkpoints.append({'controller_call':tick,'substate':game.memory[0x401],'counter040C':game.memory[0x40C],'flag6F8B':game.memory[0x6F8B],'queue0300':game.memory[0x300],'message0311':game.memory[0x311]})
        sequences.append({'initial_flag':pending,'initial0401':start_state,'initial040C':0,'initial0300and0304':0,'required_controller_calls':calls_required,'ack_injected':False,'ack_write_original_PC':'bank26 CBBF','checkpoints':checkpoints,'scope':'Direct state11/12 cooperative-call sequences; preceding C7E0 far-render dependency remains separate'})
    # Strict API domain/mapping guards; no ROM case is invented for these.
    b=fresh(rom,10)
    for label,create,call in [
        ('domestic requires mapped',lambda:GameEngine(snapshot_memory(bytes(b.ram),bytes(b.sram)),rom=rom,data_window_bank=2),lambda g:g.tick_domestic_ai()),
        ('domestic requires entrydata bank',lambda:GameEngine(rom=rom,mapped=True),lambda g:g.tick_domestic_ai()),
        ('turn requires mapped',lambda:GameEngine(rom=rom,data_window_bank=2),lambda g:g.tick_ruler_turn('calendar')),
        ('turn requires entrydata bank',lambda:GameEngine(rom=rom,mapped=True),lambda g:g.tick_ruler_turn('calendar')),
        ('transfer requires pinned ROM',lambda:GameEngine(),lambda g:g.transfer_rules()),
        ('unknown turncontroller rejected',lambda:game_from_bus(b,rom),lambda g:g.tick_ruler_turn('unproven')),
    ]:
        try:call(create())
        except (UnresolvedScene,ValueError)as e:guards.append({'guard':label,'error':str(e)})
        else:raise AssertionError(('silent missing precondition',label))
    data=PrgDataMemory(rom,b.ram,b.sram);g=GameEngine(data,rom=rom,mapped=True,data_window_bank=2);shared(g);assert g.memory is data
    g.memory[0x1881]=123;assert g.memory[0x81]==123
    guards.append({'guard':'provided mapped memory identity and CPU RAM mirroring','passed':True});counts['source_API_contract_checks']=len(guards)
    end_hashes={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in SOURCE_FILES}
    assert start_hashes==end_hashes,'Shared source changed during validation; rerun against final artifact'
    return {'status':'passed'if not failures else'failed','case_count':sum(counts.values()),'FC_FB_host_sequences':sequences,'invalid_initial_context_diagnostic':{'initial_snapshot0038':222,'problem':'Manually setting6F8B=1 without battle-return targetcity leaves menu/officer scratch0038=222','actual_pointer':'D105 computes20/21=7BC0','original_write_PCs':['CE05','CE0C','CE5E','AA91','ACB5','ACBE','ACC9','ACD2','A90B'],'observed_difference':'13 initial invalid fixtures: PrgDataMemory writes upperSRAM while original Bus protect4C blocks7000..7FFF','final_controlled_fixture':'Flag1 cases explicitly seed0038=4 targetcity,0039=11 sourcecity,0037=3 enemycount,003A=3 owncount; normal write protection unchanged','scope':'No claim of natural battle-return snapshot; SRAM write protection remains outside PrgDataMemory model'},'original_rom_sha256':ROM_SHA256,'counts':dict(counts),'actual_ROM_comparison_count':sum(n for name,n in counts.items()if name!='source_API_contract_checks'),'source_contract_check_count':len(guards),'failures':failures,'mapping_checks':mapping_checks,'controller_cases':cases,'transfer_cases':semantics,'FC_FB_wait_cases':waits,'API_guards':guards,'source_sha256':end_hashes,'python_version':sys.version,'py65_version':version('py65'),
      'context':'menu-0 original core RAM/SRAM with explicitly seeded controller-entry pair/rawE1..E3 and case-specific RAM fields; direct-entry CPU fixtures, not natural complete-core phase5 gameplay.',
      'core_snapshot_troop1098_input':{'prefix':str(prefix.relative_to(ROOT)),'sram_sha256':hashlib.sha256(Path(str(prefix)+'-sram.bin').read_bytes()).hexdigest(),'transfer_fixture':'pair27, E1/E2/E3=31/3B/3C, EE=6F17, source11 destination12, selected131, destination record empty owner2','original_readonly_troop_word':1098},
      'scope':'Actual GameEngine front door; independent transfer game-memory effects and default lifted domestic/ruler controllers, actual original-ROM comparator. No original-ROM adapter supplied to source. All complete controller comparisons include2K RAM,8K SRAM,CPU A/X/Y/SP/P/PC and physicalbank windows. Explicit dependency prefixes are separate from returns.',
      'limits':['No complete PPU/NMI/audio/global scheduler execution in this script.','Direct global callbacks require caller-owned register/entryselector setup; data_window_bank supplied explicitly. Flag1 uses explicitly controlled valid battle-return scratch (0038=4/0039=11), not raw menu0038=222.', 'PrgDataMemory does not model upperSRAM write protection. The invalid222 pointer fixture exposed this limitation and is retained in diagnostic; valid game-record fixtures keep writes in the actual writable domain.','FC/FB is never set to1 by this script. Only the real CBBD..CBBF source/original instructions can produce acknowledgement after timerthreshold.','Timer units are controller calls, not validated video frames.','Missing farbank/reset/PPU helpers remain explicit boundaries; a matching prefix does not mean the original whole path is recovered.'],
      'command':'.venv-trace/bin/python scripts/verify_phase5_integration.py --rom "/Users/paulasmith/Downloads/三国志2超级版.nes"'}
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--rom',type=Path,default=Path('/Users/paulasmith/Downloads/三国志2超级版.nes'));p.add_argument('--out',type=Path,default=ROOT/'analysis/phase5/source-integration.json');a=p.parse_args();result=verify(a.rom.read_bytes());a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in ('status','case_count','counts','actual_ROM_comparison_count','source_contract_check_count','failures')},ensure_ascii=False,indent=2));sys.exit(bool(result['failures']))
