#!/usr/bin/env python3
"""Phase22 original-core wild-officer exploration and reproducible capture.

Old phases, original ROM and cores are read-only. In particular this script
never prepares officer status/location/rosters, random cursors, controller
states, request/reply/readiness bytes or a CPU PC. All new preparations, when
used, are explicit pre-combat numerical data with complete before/after dumps.
"""
from pathlib import Path
import argparse, ctypes as C, json, sys, collections, subprocess, struct, wave
from PIL import Image
sys.dont_write_bytecode = True
from capture_succession_flows import Capture as ParentCapture, fields as parent_fields
from capture_boot_cooperation_flows import Capture as BootCapture, write, sha, digest, relative, ROM_SHA, CORE_SHA
from nes_service_runtime import ServiceRuntime
from capture_city_auxiliary_watchpoints import observer_start, observer_drain, decode_event
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source.recovered.nestopia_context import NestopiaContext

ROOT = Path(__file__).resolve().parents[1]
CITY_MOTHER = ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/city-commands.state'
BATTLE_MOTHER = ROOT/'analysis/runtime/phase3/attack-intro-7.state'
ORIGINAL_CORE=ROOT/'.toolchain/nestopia/nestopia_libretro.dylib'
OBSERVER_CORE=ROOT/'.toolchain/phase21-observer/observed/nestopia_libretro.dylib'
OBSERVER_SHA='45fcc79a7e2b9b4a2721640f7a2c1da81628a3b8283362e6f72fc623e27d5c5d'
FORMAL=('frame-services.json','checkpoints.json','input-plan.json','audio-callbacks.json','initial-fields.json',
        'state-transitions.json','flow-events.json','wild-events.json','campaign-events.json','preparation.json','observation-summary.json','buffer-hashes.json')
BUFFER_KEYS=('RAM_sha256','SRAM_sha256','RGB_sha256','PCM_sha256','whole_serialized_state_sha256')
VARIANTS={'original-control':ORIGINAL_CORE,'observer':OBSERVER_CORE}

def fields(ram, sram):
    f = parent_fields(ram, sram)
    f['all237_officer_records_raw12'] = [sram[0x3C0+12*i:0x3C0+12*(i+1)].hex() for i in range(237)]
    f['all237_officer_loyalty'] = [sram[0x3C0+12*i+3] for i in range(237)]
    f['all30_city_records_raw32'] = [sram[32*i:32*(i+1)].hex() for i in range(30)]
    return f

class Capture(ParentCapture):
    def __init__(self, rom, out, core=ORIGINAL_CORE):
        # Same explicit runtime construction as the frozen parent captures,
        # with a separately pinned observer-core choice and no monkeypatch.
        self.out=Path(out).resolve();self.out.mkdir(parents=True,exist_ok=True)
        assert not any(self.out.iterdir()),'Use a fresh owned directory'
        assert sha(rom)==ROM_SHA
        assert sha(core)==(CORE_SHA if Path(core).resolve()==ORIGINAL_CORE else OBSERVER_SHA)
        self.rt=ServiceRuntime(rom,self.out,core)
        assert self.rt.av_info['sample_rate']==48000
        self.rows=[];self.points=[];self.plan=[];self.transitions=[];self.reset_events=[];self.flow_events=[]
        self.previous_fields=None;self.software_restarts=[];self.labels=set();self.last=None;self.seen=set()
        self.mother=None;self.preparation=[];self.preparation_groups=[];self.campaign_events=[];self.deaths=set()
        self.phase16_previous=None
        self.wild_previous = None
        self.wild_events = []
        self.numeric_loyalty = None
        self.retained_frames=collections.deque(maxlen=4)
        self.observer=observer_start(self.rt,self.out,'released-wild-recruitment')
        if self.observer is not None:
            schema=json.loads((self.out/'event-schema.json').read_text())
            schema.update(schema='phase22-passive-wild-recruitment-events-v1',
                original_reference_case='analysis/phase22/runtime/original-control',
                original_reference_frames='analysis/phase22/runtime/original-control/frame-services.json',
                frame_identity='Local frame N after the same declared natural mother import and ordinary input plan; compared against the new original-control frame N, not phase20.')
            write(self.out/'event-schema.json',schema)
        self.initial_RAM=self.rt.memory(2);self.initial_SRAM=self.rt.memory(0)
        for suffix,raw in(('-ram.bin',self.initial_RAM),('-sram.bin',self.initial_SRAM)):(self.out/('initial'+suffix)).write_bytes(raw)
        write(self.out/'initial-fields.json',dict(self.current(),cold_boot=True,state_imported=False,additional_core_memory_writes=0))
        (self.out/'initial.state').write_bytes(self.serialized())

    def serialized(self):
        size = self.rt.core.retro_serialize_size()
        buf = C.create_string_buffer(size)
        assert self.rt.core.retro_serialize(buf, size)
        return buf.raw

    def inherit(self,mother):
        super().inherit(mother)
        (self.out/'mother-input.state').write_bytes(Path(mother).read_bytes())
        # The imported source file and the actual full API reserialization
        # are separate artifacts. Neither is normalized or synthesized.
        (self.out/'initial.state').write_bytes(self.serialized())

    def current(self):
        return fields(self.rt.memory(2), self.rt.memory(0))

    def observe(self, rt):
        super().observe(rt)
        ram, sram = rt.memory(2), rt.memory(0)
        f = fields(ram, sram)
        row = self.rows[-1]
        for key in ('all237_officer_records_raw12','all237_officer_loyalty','all30_city_records_raw32'):
            row[key] = f[key]
        state = self.serialized()
        context=NestopiaContext.parse(state)
        assert context.ram==ram and context.sram==sram
        row['whole_serialized_state_sha256'] = digest(state)
        row['whole_serialized_state_bytes'] = len(state)
        row['actual_saved_CPU_registers']=context.registers
        row['actual_saved_PRG_banks']=context.prg_banks
        row['Native_instruction_trace']=False
        observer_drain(rt,self.observer)
        old = self.wild_previous
        if old is not None:
            for ID, (a, b) in enumerate(zip(old, f['all237_officer_status_low2'])):
                if a != b:
                    if a==0 and b==2:
                        for distance,p in enumerate(reversed(self.retained_frames),1):
                            self.save_retained('recruitment-success-previous-%d-frame%d'%(distance,p['frame']),p)
                    event = dict(frame=rt.frames, officer=ID, before_status=a,
                                 after_status=b, raw_record=f['all237_officer_records_raw12'][ID],
                                 location_byte5=f['all237_officer_byte5_raw'][ID],
                                 loyalty=f['all237_officer_loyalty'][ID],
                                 global_state=f['global_state'],nmi_scene=f['nmi_scene'],
                                 city_state=f['city_state_0400_040F'][:3],
                                 battle_state=f['battle_state_0500_050F'][:2])
                    self.wild_events.append(event)
                    self.snap('officer%d-status%d-frame%d' % (ID,b,rt.frames),
                              'Actual original-core record transition; no status prepared')
                    print(json.dumps(event, ensure_ascii=False), flush=True)
        self.wild_previous = f['all237_officer_status_low2']
        self.retained_frames.append(dict(frame=rt.frames,RAM=ram,SRAM=sram,state=state,image=rt.frame.copy(),
                                        fields=f,PCM_stop_byte=len(rt.pcm)))

    def save_retained(self,label,p):
        if label in self.labels:return
        self.labels.add(label);p['image'].save(self.out/(label+'.png'))
        for key,suffix in(('RAM','-ram.bin'),('SRAM','-sram.bin'),('state','.state')):
            (self.out/(label+suffix)).write_bytes(p[key])
        self.points.append(dict(label=label,frame=p['frame'],reason='Actual retained pre-success frame; never reconstructed or reimported',
            image=label+'.png',RAM=label+'-ram.bin',SRAM=label+'-sram.bin',state=label+'.state',
            PCM_stop_byte=p['PCM_stop_byte'],fields=p['fields']))

    def preparation_end(self):
        if self.numeric_loyalty is not None:
            ID, value = self.numeric_loyalty
            self.patch('SRAM', 0x63C0+12*ID+3, value,
                       'Declared pre-defeat follower loyalty only; original succession must generate any departure')
            self.numeric_loyalty = None
        return super().preparation_end()

    def patch(self, kind, address, value, reason):
        if kind == 'SRAM':
            assert 0x63C0 <= address < 0x6EDC and (address-0x63C0)%12 in (0,1,2,3,4,6,7,8,9,10), address
        else:
            assert 0x600 <= address < 0x628, address
        return super().patch(kind,address,value,reason)

    def invade_with_followers(self):
        """Ordinary original invasion, selecting all three real city officers."""
        self.inherit(CITY_MOTHER)
        plan=json.loads((ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json').read_text())
        for row in plan[24:34]:
            self.step(row['frames'],row.get('buttons',()),'Original natural invasion selection',row.get('capture'))
        for index in range(3):
            self.press('a',120,'Select real original army roster row%d' % index,'army-selected-row%d'%index)
            self.press('down',35,'Move to next original army roster row')
        self.snap('army-three-officers-end-cursor')
        for row in plan[46:74]:
            self.step(row['frames'],row.get('buttons',()),'Original army/supply/consent/battle input',row.get('capture'))
            f=self.current()
            if f['global_state']==4 and f['nmi_scene']==3 and f['battle_state_0500_050F'][:2]==[0,3]:break
        self.snap('three-officer-battle-action-menu')
        assert set(x['officer_id'] for x in self.current()['active_units'] if x['slot']>=10)=={131,5,30}

    def open_retreat(self):
        f=self.current()
        self.until(lambda f:f['text_progress_0300']==255 and f['text_cursor_0304']==255,
                   1200,purpose='Wait for actual original action-menu text completion')
        if f['battle_state_0500_050F'][:2]==[0,3] and self.rt.memory(2)[0x50A]!=10:
            self.press('b',240,'Close follower action menu before choosing commander')
            self.until(lambda f:f['battle_state_0500_050F'][:2]==[0,2] and f['text_progress_0300']==255 and f['text_cursor_0304']==255,
                       1200,purpose='Wait for actual original battlefield cursor readiness')
            self.move_cursor(2,16)
            self.press('a',180,'Choose original commander for actual army retreat')
            f=self.current()
        if f['battle_state_0500_050F'][:2]==[0,2]:self.press('a',180,'Open original commander action menu')
        assert self.current()['battle_state_0500_050F'][:2]==[0,3]
        for _ in range(2):self.press('down',35,'Choose original retreat command')
        self.press('a',180,'Open original retreat action','retreat-open')
        for i in range(8):
            f=self.current()
            if f['global_state'] in (3,4) and f['battle_state_0500_050F'][:2]==[13,2]:break
            self.press('a',240,'Advance original retreat instruction/confirmation','retreat-A%d'%i)
        self.snap('retreat-destination-menu')

    def probe_retreat(self):
        self.invade_with_followers()
        self.open_retreat()
        self.press('right',60,'Choose actual ざいや destination at original list index1','release-option-selected')
        assert self.rt.memory(2)[0x12]==1
        self.press('a',240,'Confirm original ざいや destination','release-destination-confirmed')
        self.press('a',240,'Acknowledge original release instruction','release-officer-list-opening')
        self.until(lambda f:f['battle_state_0500_050F'][:2]==[13,5],1200,
                   'release-officer-grid','Wait for actual original selectable officer grid')
        self.snap('release-officer-grid-ready')
        self.press('a',60,'Select original nonleader 于禁5 for ざいや release','release-selected-5')
        self.press('right',60,'Move to original nonleader 夏侯惇30')
        self.press('a',60,'Select original nonleader 夏侯惇30 for ざいや release','release-selected-5-and-30')
        self.press('right',60,'Move to original おわり row')
        self.press('a',240,'Submit actual original selected release roster','release-confirmation')
        self.press('a',300,'Confirm original ざいや release, original code must generate status0','release-original-status-writeback')
        for i in range(12):
            if self.ready(0,1)(self.current()):break
            self.press('a',240,'Original remaining postbattle settlement and city return','release-postbattle-A%d'%i)
        self.snap('release-city-return')

    def probe_leader(self):
        self.inherit(BATTLE_MOTHER)
        self.preparation_begin('declared-enemy-leader-precombat-data')
        for kind,addr,value,reason in (
            ('SRAM',0x63C0+12*8,1,'Enemy leader pre-combat health1; no death/status prepared'),
            ('SRAM',0x63C0+12*8+2,10,'Enemy leader pre-combat intelligence10; actual probability still runs'),
            ('RAM',0x600,5,'Enemy leader legal nearby battlefield X'),
            ('RAM',0x614,16,'Enemy leader legal nearby battlefield Y')):
            self.patch(kind,addr,value,reason)
        self.preparation_end()
        self.step(90,(),'Render original battle after pre-combat numerical preparation','leader-prepared')
        self.trap_target(0,1)
        for i in range(25):
            if self.ready(0,1)(self.current()):break
            self.press('a',240,'Ordinary post-defeat original result/retreat/settlement input','leader-postbattle-A%d'%i)
        self.snap('leader-bounded-end')

    def monthly_recruitment_search(self,months):
        """Spend actual city command cards, then allow real original AI turns."""
        ordinal=0
        for cycle in range(months):
            budget=self.current()['remaining_budget_raw_6F05']
            assert self.ready(0,1)(self.current()) and 0<budget<8
            for _ in range(budget):
                ordinal+=1
                self.recruitment(ordinal)
            self.next_player_message('recruitment-search-next-player-message-%d'%cycle)
            self.press_ready('a',0,1,'recruitment-search-next-world-%d'%cycle)
            self.snap('recruitment-search-month-%d-complete'%cycle)
            if any(e['before_status']==0 and e['after_status']==2 for e in self.wild_events):break

    def finish_probe(self,formal=False):
        self.snap('final')
        BootCapture.finish(self,exploratory=False)
        (self.out/'full-flow.wav').rename(self.out/'full-audio.wav')
        write(self.out/'wild-events.json',self.wild_events)
        write(self.out/'campaign-events.json',self.campaign_events)
        write(self.out/'preparation.json',dict(writes=self.preparation,groups=self.preparation_groups))
        write(self.out/('observation-summary.json' if formal else 'exploration-summary.json'),dict(status='observed',frames=self.rt.frames,
              mother=relative(self.mother) if self.mother else None,
              mother_sha256=sha(self.mother) if self.mother else None,
              new_numeric_preparations=self.preparation,wild_events=self.wild_events,
              final_fields=self.current(),full_audio=self.wav,ROM_sha256=ROM_SHA,
              core=self.rt.info,script_sha256=sha(Path(__file__)),
              no_status_location_roster_RNG_controller_request_ready_preparation=True,
              scope=('Formal bounded native observation.' if formal else 'Exploration only.')+' Original-core end-of-frame fields are not an internal CPU trace; observer-core sparse events are separate evidence.'))
        write(self.out/'buffer-hashes.json',[dict(frame=r['frame'],**{k:r[k] for k in BUFFER_KEYS},
              whole_serialized_state_bytes=r['whole_serialized_state_bytes']) for r in self.rows])

    def close(self):
        if self.observer is not None:
            self.observer['binary'].close();self.observer['JSON'].close()
        super().close()

def formal_capture(rom,out,variant):
    c=Capture(rom,out,VARIANTS[variant])
    try:
        c.probe_retreat()
        c.monthly_recruitment_search(2)
        f=c.current()
        assert not c.preparation and c.mother==CITY_MOTHER
        assert c.rt.frames==15200 and f['calendar_and_turn_6F00_6F06']==[89,2,0,2,1,3,1]
        assert f['global_state']==f['nmi_scene']==2 and f['city_state_0400_040F'][:2]==[0,1]
        assert f['cooperation_status_6F8B']==255
        expected=[(7635,5,2,0),(7635,30,2,0),(14573,152,1,2),(14837,5,0,2)]
        assert [(e['frame'],e['officer'],e['before_status'],e['after_status']) for e in c.wild_events]==expected
        assert f['all237_officer_status_low2'][5]==2 and f['all237_officer_status_low2'][30]==0
        assert f['city_rosters'][2]==[222,38,153,109,5,255,255,255,255,255]
        assert f['city_rosters'][11]==[131]+[255]*9 and f['all237_officer_loyalty'][5]==90
        c.finish_probe(True)
        assert all(len(r['all237_officer_status_low2'])==237 and len(r['all30_city_records_raw32'])==30 for r in c.rows)
        assert len(c.rows)==c.rt.frames and any(r['PCM_nonzero'] for r in c.rows)
        events=None
        if c.observer is not None:
            c.observer['binary'].flush();c.observer['JSON'].flush()
            events=dict(event_count=c.observer['count'],by_kind=dict(c.observer['kinds']),by_target=dict(c.observer['targets']),
                raw='bus-events.bin',decoded='events.jsonl',schema='event-schema.json',overflow=0,
                scope='Frozen phase21 observer core only. Original-control does not expose an internal CPU trace.')
        artifacts={};empty=[]
        for path in sorted(c.out.iterdir()):
            if not path.stat().st_size:empty.append(path.name);continue
            if path.suffix in('.png','.bin','.state','.wav','.jsonl') or path.name in FORMAL or path.name=='event-schema.json':
                artifacts[path.name]=dict(bytes=path.stat().st_size,sha256=sha(path))
        pins=[dict(path=relative(p),sha256=sha(p)) for p in (
            Path(__file__),ROOT/'scripts/capture_boot_cooperation_flows.py',ROOT/'scripts/capture_campaign_flows.py',
            ROOT/'scripts/capture_succession_flows.py',ROOT/'scripts/capture_city_auxiliary_watchpoints.py',
            ROOT/'scripts/nes_runtime.py',ROOT/'scripts/nes_service_runtime.py',ROOT/'source/recovered/nestopia_context.py',
            CITY_MOTHER,CITY_MOTHER.with_name('city-commands-ram.bin'),CITY_MOTHER.with_name('city-commands-sram.bin'),
            ROOT/'analysis/phase14/runtime/cold-city-domestic-cycle/validation.json',
            ROOT/'analysis/runtime/phase3/replay-cold-to-battle.json')]
        valid=dict(schema='phase22-native-wild-recruitment-flow-v1',status='passed',case='ordinary-release-and-wild-recruitment',variant=variant,
            rom_sha256=ROM_SHA,rom_modified=False,core=c.rt.info,AV=c.rt.av_info,
            cold_boot=False,state_imported=True,mother_state=relative(CITY_MOTHER),mother_sha256=sha(CITY_MOTHER),
            inherited_context=dict(controlled_fixture=False,inherited_preparation_byte_writes=0,
                validation='analysis/phase14/runtime/cold-city-domestic-cycle/validation.json',
                scope='Original city-commands checkpoint from an earlier zero-write cold-boot route. This case imports that unchanged natural mother; it does not claim to start cold.'),
            controlled_fixture=False,natural_gameplay=True,additional_core_memory_writes=0,preparation=[],preparation_groups=[],
            additional_core_memory_writes_after_declared_preparation=0,additional_ready_or_result_injections=0,
            status_location_roster_RNG_PC_request_reply_ready_prepared=False,fresh_process_per_run=True,
            frames=c.rt.frames,checkpoint_count=len(c.points),input_step_count=len(c.plan),
            full_audio=c.wav,all_frames_native_RGB_PCM_RAM_SRAM_hashed=True,all_full_serialized_buffers_hashed=True,
            native_internal_CPU_trace=False,observer_core_sparse_CPU_events=c.observer is not None,source_CPU_comparisons=0,
            observer_events=events,initial_RAM_sha256=digest(c.initial_RAM),initial_SRAM_sha256=digest(c.initial_SRAM),
            initial_actual_serialized_state_sha256=sha(c.out/'initial.state'),full_serialized_buffers_not_normalized=True,
            verified_effects=dict(original_three_officer_invasion=[131,5,30],original_commander_retreat=True,
                original_destination_menu=[11,30],destination30_original_glyph='ざいや',
                original_selected_release_officers=[5,30],release_frame=7635,
                released_statuses=[0,0],original_location_byte5_after_release={'5':2,'30':11},
                original_loyalty_after_release={'5':86,'30':92},release_city11_roster=[131]+[255]*9,
                actual_zero_quantity_commands=5,monthly_transitions=2,
                wild_recruitment=dict(frame=14837,officer=5,before_status=0,after_status=2,before_loyalty=86,after_loyalty=90,
                    byte5_preserved=2,destination_city=2,roster_before=[222,38,153,109]+[255]*6,
                    roster_after=[222,38,153,109,5]+[255]*5),
                separate_appearing_officer=dict(frame=14573,officer=152,before_status=1,after_status=2),
                unrecruited_released_officer30_status=0,actual_AI_continuation_returned_FF=True,
                final_calendar=[189,3],final_controller=[2,2,0,1]),
            final_fields=f,artifact_sha256=artifacts,excluded_empty_VRAM=empty,
            excluded_snapshot_metadata_JSON=sorted(x+'.json' for x in c.labels),formal_JSON=list(FORMAL),dependency_pins=pins,
            termination='Original release and two actual monthly rotations end at March player world after real wild recruitment and AI returnFF.',
            limits=['One input route, two separately pinned core streams. The observer log is not retroactively attributed to the original core.',
                'The original core observations are frame boundaries; only the unchanged passive observer supplies sparse instruction/bus events.',
                'Status1→2 appearance of152 is distinct from actual status0→2 recruitment of5.',
                'No direct RAM/SRAM preparation, no injected status/location/roster/RNG/PC/request/ready/result, and no ROM/core modification.',
                'Complete serialized API buffers are retained/hashes compared without trimming, padding, or normalization.'])
        write(c.out/'validation.json',valid)
        return valid
    finally:c.close()

def aggregate(out):
    """Rehash complete files and full raw buffers; no tolerance/normalization."""
    out=Path(out).resolve();repeat=out.parent/(out.name+'-repeat')
    receipts={};artifact_count=image_count=audio_count=0
    for variant in VARIANTS:
        first,second=out/variant,repeat/variant
        a=json.loads((first/'validation.json').read_text());b=json.loads((second/'validation.json').read_text())
        assert a==b and a['status']=='passed' and not a['preparation']
        assert a['frames']==15200 and a['cold_boot'] is False and a['state_imported'] is True
        for pin in a['dependency_pins']:assert sha(ROOT/pin['path'])==pin['sha256']
        assert sha(first/'validation.json')==sha(second/'validation.json')
        for name,pin in a['artifact_sha256'].items():
            p=first/name;q=second/name
            assert p.stat().st_size==q.stat().st_size==pin['bytes']>0
            assert sha(p)==sha(q)==pin['sha256'];artifact_count+=1
            if p.suffix=='.png':
                with Image.open(p) as im:im.load();assert im.size==(256,240) and im.mode=='RGB'
                image_count+=1
            if p.suffix=='.wav':
                with wave.open(str(p)) as w:
                    assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(2,2,48000)
                    raw=w.readframes(w.getnframes());assert digest(raw)==a['full_audio']['PCM_sha256'] and any(raw)
                audio_count+=1
        points=json.loads((first/'checkpoints.json').read_text())
        for point in points:
            context=NestopiaContext.parse((first/point['state']).read_bytes())
            assert context.ram==(first/point['RAM']).read_bytes() and context.sram==(first/point['SRAM']).read_bytes()
        r=dict(status='passed',variant=variant,first_run=relative(first),second_run=relative(second),
               artifacts_checked=len(a['artifact_sha256']),all_nonempty_artifact_bytes_exact=True,
               validation_bytes_exact=True,full_serialized_buffers_not_normalized=True)
        write(first/'repeat-validation.json',r);receipts[variant]=a
    original,observer=out/'original-control',out/'observer'
    a=json.loads((original/'buffer-hashes.json').read_text());b=json.loads((observer/'buffer-hashes.json').read_text())
    assert a==b and len(a)==15200
    for name in ('initial.state','initial-ram.bin','initial-sram.bin','mother-input.state','input-plan.json','full-audio.wav'):
        assert sha(original/name)==sha(observer/name)
    raw_count=0;by_pc=collections.Counter();entries=[];successful_scans=[];rng_pending=[];rng_pairs=[]
    with (observer/'bus-events.bin').open('rb') as binary,(observer/'events.jsonl').open() as decoded:
        while raw:=binary.read(72):
            raw_count+=1;r=decode_event(raw,sequence=raw_count)
            assert r==json.loads(next(decoded))
            if r['kind']=='opcode_boundary':
                by_pc[(r['physical_bank'],r['opcode_PC'])]+=1
                if r['physical_bank']==11:
                    if r['opcode_PC']==0xC71A:entries.append(r)
                    elif r['opcode_PC']==0xC794:
                        assert entries
                        entry=entries[-1]
                        assert r['SP']==(entry['SP']+2)&255
                        successful_scans.append(dict(scan_entry=entry,success_RTS_boundary=r,
                            two_PLA_stack_bytes_discarded=2,original_ROM_bytes_C792_C794='686860'))
                if r['physical_bank']==31 and r['opcode_PC']==0xE89A:rng_pending.append(r)
                elif r['physical_bank']==31 and r['opcode_PC']==0xE8A9:
                    assert rng_pending
                    entry=rng_pending.pop();assert entry['X']==r['X']
                    rng_pairs.append(dict(entry_sequence=entry['sequence'],exit_sequence=r['sequence'],
                                         entry_X=entry['X'],exit_X=r['X']))
        assert next(decoded,None) is None and not rng_pending
    assert len(successful_scans)>=1 and any(x['success_RTS_boundary']['frame']==14837 for x in successful_scans)
    assert by_pc[(11,0xC732)]>0 and by_pc[(11,0xC735)]>0 and by_pc[(11,0xC794)]>0
    write(out/'observer-success.json',dict(status='observed',event_count=raw_count,
        sparse_opcode_counts=[dict(physical_bank=k[0],opcode_PC=k[1],count=v) for k,v in sorted(by_pc.items())],
        successful_scans=successful_scans,E89A_observed_pairs=len(rng_pairs),all_observed_E89A_X_preserved=True,
        observer_core_sha256=OBSERVER_SHA,decode_function='scripts/capture_city_auxiliary_watchpoints.py:decode_event',
        scope='Sparse boundaries only in the unchanged passive core; not an original-core full instruction trace or universal interrupt-atomicity proof.'))
    summary=dict(status='passed',native_input_routes=1,original_core_cases=1,core_variants=2,fresh_process_runs=4,
        frames_per_route=15200,original_core_first_run_frames=15200,observer_first_run_frames=15200,
        total_control_frames_both_variants_both_runs=60800,original_core_repeated_frames=30400,
        checkpoints_per_original_route=receipts['original-control']['checkpoint_count'],
        nonempty_artifact_checks=artifact_count,decoded_PNG_checks=image_count,full_WAV_checks=audio_count,
        all_five_full_buffers_match_each_frame=True,initial_full_serialized_buffers_equal=True,
        all_nonempty_artifacts_repeat_exact=True,additional_core_memory_writes=0,state_imports_per_run=1,
        inherited_preparation_byte_writes=0,failed_count=0,observer_event_count=raw_count,
        C732_RNG_call_boundaries=by_pc[(11,0xC732)],C735_RNG_return_boundaries=by_pc[(11,0xC735)],
        C794_success_RTS_boundaries=by_pc[(11,0xC794)],source_CPU_comparisons=0)
    receipt=receipts['original-control'];points=json.loads((original/'checkpoints.json').read_text())
    case=dict(case=receipt['case'],folder='original-control',validation='original-control/validation.json',
        repeat_validation='original-control/repeat-validation.json',checkpoints='original-control/checkpoints.json',
        frame_services='original-control/frame-services.json',input_plan='original-control/input-plan.json',
        full_audio=dict(path='original-control/full-audio.wav',**receipt['full_audio']),
        images={p['label']:'original-control/'+p['image'] for p in points},
        verified_effects=receipt['verified_effects'],preparation=[],cold_boot=False,state_imported=True,
        mother_state=receipt['mother_state'],inherited_context=receipt['inherited_context'])
    evidence=dict(schema='phase22-native-wild-recruitment-streams-v1',status='passed',summary=summary,
        native_cases=[case],observer_runs=[dict(variant='observer',folder='observer',validation='observer/validation.json',
            repeat_validation='observer/repeat-validation.json',events='observer/events.jsonl',raw_ABI='observer/bus-events.bin',
            event_schema='observer/event-schema.json',success_observations='observer-success.json')],
        original_core_sha256=CORE_SHA,observer_core_sha256=OBSERVER_SHA,ROM_sha256=ROM_SHA,
        core_provenance='analysis/phase21/runtime/core-provenance/build.json',script_sha256=sha(__file__),
        parity=dict(reference='original-control/buffer-hashes.json',observer='observer/buffer-hashes.json',
            buffer_keys=list(BUFFER_KEYS),frames=15200,complete_API_buffer=True,normalization=False),
        limits=receipt['limits'])
    write(out/'evidence.json',evidence)
    write(out/'validation.json',dict(schema=evidence['schema'],**summary,ROM_sha256=ROM_SHA,
        evidence_sha256=sha(out/'evidence.json'),script_sha256=sha(__file__)))
    (out/'README.md').write_text('''# 阶段22：原模拟器真正释放在野并录用

本期是一条普通按键路线，导入阶段14零写入冷启动产生的自然city-commands存档；本期不是冷启动，继承准备0、新增RAM/SRAM准备0。原ROM、原核心及阶段21观察核心不改。原核心和已冻结观察核心各fresh进程双跑，共4次控制执行。

[证据](evidence.json) · [回执](validation.json) · [实际观察事件](observer-success.json) · [脚本](../../../scripts/capture_native_wild_recruitment.py)

原军队菜单选择131、5、30三人，正常出征后君主曹操选择退却。战后目的地列表是城11和特殊值30「ざいや」。普通Right/A选择该项，仅选择非君主5、30及「おわり」，再A确认。第7635帧原代码把二人status2→0，原byte5分别写2、11；忠诚仍86、92。返回城11后名册实际只剩131，未准备或直接移除名册。

随后五次实际接受的quantity0征兵命令耗掉剩余行动卡，完整经过两个原月轮。第14837帧于禁5从status0→2，忠诚86→90，byte5仍2，城2名册在[222,38,153,109]后追加5。第14573帧152的status1→2是另一种登场路径，单独列出，不作为在野招募。第15200帧已回189年3月玩家world/city0/1，AI请求FF；30在本窗口仍在野，不能称两人均录用。

逐帧完整RGB、实际48kHz立体声PCM、2048B RAM、8192B SRAM、完整serialized API buffer哈希在两核心间逐项相等；初始API序列化时机一致，不截断、补零或归一化。各流两次非空PNG/RAM/SRAM/state/WAV与正式JSON逐字节相同。0B VRAM与绝对路径/事件metadata JSON独立排除。

真正的内部事件仅属于独立observer核心，不能追认原核心具有内部trace。沿用阶段21同一ABI，记录C732/C735 RNG调用前后、C794两次PLA后的RTS边界及真实PRG页、SP/寄存器/指针。success前4帧保存实际全state供独立CPU前序对照。C71A到C794的SP差2与原C792/C793两次PLA相符；之后原AI续行和玩家返回由完整核心执行。此有限控制等价不扩展为普遍二进制等价、全游戏完成或unused字段结论。
''')
    print(json.dumps(summary),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('rom',type=Path)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--probe',choices=('retreat','leader','succession','continuation','retreat-search'))
    p.add_argument('--loyalty',type=int,default=0)
    p.add_argument('--mother',type=Path)
    p.add_argument('--months',type=int,default=1)
    p.add_argument('--formal-run',action='store_true')
    p.add_argument('--variant',choices=tuple(VARIANTS),default='original-control')
    p.add_argument('--verify-replay',action='store_true')
    p.add_argument('--aggregate',action='store_true')
    a=p.parse_args()
    if a.aggregate:aggregate(a.out);return
    if a.verify_replay:
        for variant in VARIANTS:
            for root in (a.out,a.out.parent/(a.out.name+'-repeat')):
                subprocess.run([sys.executable,str(Path(__file__)),str(a.rom),'--out',str(root/variant),
                                '--formal-run','--variant',variant],check=True)
        aggregate(a.out);return
    if a.formal_run:formal_capture(a.rom,a.out,a.variant);return
    assert a.probe is not None,'Choose an explicit exploratory probe or formal replay mode'
    c=Capture(a.rom,a.out)
    try:
        if a.probe=='retreat':c.probe_retreat()
        elif a.probe=='retreat-search':
            c.probe_retreat()
            c.monthly_recruitment_search(a.months)
        elif a.probe=='leader':c.probe_leader()
        elif a.probe=='continuation':
            assert a.mother is not None
            c.inherit(a.mother)
            c.monthly_recruitment_search(a.months)
        else:
            c.numeric_loyalty=(30,a.loyalty)
            c.player_failure()
    finally:
        if c.rt.frame is not None:c.finish_probe()
        c.close()

if __name__=='__main__':main()
