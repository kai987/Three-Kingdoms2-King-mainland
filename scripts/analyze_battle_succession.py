#!/usr/bin/env python3
"""Pin the actual postbattle city13 successor consumer and structure direct source.

This is an offline compiler of original bytes, not a production ROM or IR
executor. Player/computer/retirement phases retain real service boundaries.
"""
from pathlib import Path
import argparse,ast,hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from analyze_city_ui_controller import collect,CityStructurer
from ui_structuring import labelled_procedure,loop_exception_source
from analyze_audio_scene_services import HEADER as AUDIO_HEADER
SHA='26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
OUT=ROOT/'analysis/phase16/succession';SOURCE=ROOT/'source/recovered/battle_succession.py'
PUBLIC=(0xA00C,0xAD81)
NAMES={0xA00C:'postbattle_successor_entry',0xAD81:'postbattle_successor_tick',0xAD84:'dispatch_postbattle_phase',
0xAD95:'prepare_postbattle_city',0xADAA:'check_defeated_ruler',0xAE0D:'check_winning_ruler',0xAE51:'restore_city_or_ai_turn',
0xBE01:'player_succession_tick',0xBE04:'dispatch_player_succession',0xBE17:'announce_player_leader_death',
0xBE2E:'check_player_candidate_cities',0xBE83:'choose_player_candidate_city',0xBED1:'choose_player_candidate_officer',
0xBF2F:'confirm_player_successor',0xBFB9:'classify_player_successor_family',0xC01E:'adjust_player_followers',0xC0E5:'await_deserter_message',
0xC101:'promote_successor_roster_head',0xC132:'computer_succession_tick',0xC135:'dispatch_computer_succession',
0xC144:'announce_computer_leader_death',0xC158:'choose_family_successor',0xC1A1:'find_family_candidate_city',
0xC1DB:'choose_highest_morality_successor',0xC21D:'consider_city_candidates',0xC25D:'install_computer_successor',
0xC280:'wait_computer_successor_notice',0xC289:'adjust_computer_followers',0xC318:'remove_low_loyalty_follower',
0xC37A:'retirement_tick',0xC37D:'dispatch_retirement',0xC386:'commit_leader_absence',0xC3C2:'await_player_gameover',
0xC41E:'wait_computer_retirement_notice',0xA1C2:'draw_current_city_focus',0xA1EB:'find_officer_city',
0xC67C:'navigate_city_cursor',0xC708:'city_at_cursor'}
FIELDS={0x400:'CITY_MAIN',0x401:'POSTBATTLE_PHASE',0x402:'SUCCESSION_PHASE',0x40A:'AFFECTED_RULER',
0x40B:'OLD_LEADER',0x40C:'SUCCESSOR_CITY',0x40D:'SUCCESSOR',0x40E:'FOLLOWER_CITY',0x40F:'FOLLOWER_ROSTER',
0x470:'RETURN_PHASE',0x471:'NO_SUCCESSOR_PHASE',0x472:'RETURN_MAIN',0x473:'RETURN_MAIN_PHASE',
0x81:'NEW_BUTTONS',0x87:'REPEAT_BUTTONS',0x7A:'GLOBAL',0x78:'NMI_SCENE',0x7E:'PPU_JOBS',0x4D0:'NOTICE_TIMER'}
MANUAL={0xC1A1:'''    def find_family_candidate_city(self):
        """C1A1..C1DA: city owner low3 and compact roster prefix only.

        HP, officer status and record byte5 are not candidate predicates.
        Matching the candidate precedes the FF sentinel test. Success returns
        carry set and writes its city040C; failure preserves040C and clears C.
        """
        r=self.registers;m=self.memory;yield from self._checkpoint(0xC1A1);self._x(0)
        while True:
            yield from self._checkpoint(0xC1A3);self._a(r.x)
            yield from self._external(0xC1A4,0xF2AF,0xC1A7,'call')
            if r.pc!=0xC1A7:return
            self._y(0);self._a(m[(m[0]|m[1]<<8)]);self._a(r.a&7);self._compare(r.a,m[AFFECTED_RULER])
            if r.p&Z:
                self._y(17);m[4]=r.y
                while True:
                    yield from self._checkpoint(0xC1B7);self._y(m[4]);self._a(m[((m[0]|m[1]<<8)+r.y)&65535])
                    self._compare(r.a,m[SUCCESSOR])
                    if r.p&Z:m[SUCCESSOR_CITY]=r.x;self._flag(C,True);self._rts();return
                    self._compare(r.a,255)
                    if r.p&Z:break
                    m[4]=self._nz(m[4]+1);self._a(m[4]);self._compare(r.a,27)
                    if r.p&C:break
            self._x(r.x+1);self._compare(r.x,30)
            if r.p&C:break
        self._flag(C,False);self._rts();return

''',0xC21D:'''    def consider_city_candidates(self):
        """C21D..C25C: choose the last officer tying the highest raw morality.

        The roster stops at its first FF, even if later slots are occupied.
        Reads officer+4 only: no health/status/location/family exclusion here.
        Scratch0010=bestID and0011=bestvalue span the caller's city scan.
        """
        r=self.registers;m=self.memory;yield from self._checkpoint(0xC21D)
        self._a(m[0]);m[2]=r.a;self._a(m[1]);m[3]=r.a;self._y(17);m[4]=r.y
        while True:
            yield from self._checkpoint(0xC22E);self._y(m[4]);self._a(m[((m[2]|m[3]<<8)+r.y)&65535]);self._compare(r.a,255)
            if r.p&Z:break
            m[0x12]=r.a;yield from self._external(0xC23A,0xF2D7,0xC23D,'call')
            if r.pc!=0xC23D:return
            self._y(4);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[0x11])
            if r.p&C:m[0x11]=r.a;self._a(m[0x12]);m[0x10]=r.a;m[SUCCESSOR_CITY]=r.x
            m[4]=self._nz(m[4]+1);self._a(m[4]);self._compare(r.a,27)
            if r.p&C:break
        self._rts();return

''',0xC101:'''    def promote_successor_roster_head(self):
        """C101..C131: swap chosen ID with city roster[0], no location write.

        Search covers all ten slots, not a compact prefix. If ID is absent,
        leave the roster untouched. The actual PHA/PLA leaves its stack byte.
        """
        r=self.registers;m=self.memory;yield from self._checkpoint(0xC101);self._a(m[SUCCESSOR_CITY])
        yield from self._external(0xC104,0xF2AF,0xC107,'call')
        if r.pc!=0xC107:return
        self._a(m[SUCCESSOR]);m[2]=r.a;self._y(17)
        while True:
            yield from self._checkpoint(0xC10F);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);self._compare(r.a,m[2])
            if r.p&Z:
                self._a(r.y);self._push(r.a);self._y(17);self._a(m[((m[0]|m[1]<<8)+r.y)&65535]);m[3]=r.a
                self._a(m[2]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a
                self._a(self._pop());self._y(r.a);self._a(m[3]);m[((m[0]|m[1]<<8)+r.y)&65535]=r.a;self._rts();return
            self._y(r.y+1);self._compare(r.y,27)
            if r.p&C:break
        self._rts();return

''',0xC318:'''    def remove_low_loyalty_follower(self):
        """C318..C341: release non-successor and shift the remaining roster.

        AI branch clears condition low2; it does not write record byte5 or
        neutralize an empty city's owner. PlayerC01E has different effects.
        """
        r=self.registers;m=self.memory;yield from self._checkpoint(0xC318);self._a(m[0x31]);self._compare(r.a,m[SUCCESSOR])
        if r.p&Z:self._rts();return
        self._y(11);self._a(m[((m[0x22]|m[0x23]<<8)+r.y)&65535]);self._a(r.a&252);m[((m[0x22]|m[0x23]<<8)+r.y)&65535]=r.a
        self._y(m[0x13])
        while True:
            yield from self._checkpoint(0xC32C);self._compare(r.y,26)
            if r.p&Z:break
            self._y(r.y+1);self._a(m[((m[0x10]|m[0x11]<<8)+r.y)&65535]);self._y(r.y-1);m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a;self._y(r.y+1)
        self._a(255);m[((m[0x10]|m[0x11]<<8)+r.y)&65535]=r.a;m[0x13]=self._nz(m[0x13]-1);self._rts();return

'''}
HEADER=AUDIO_HEADER.replace('Exact audio scene caller service, including real local frames and idle stack.',
'Actual postbattle city13 succession, player selection and faction retirement.')
start=HEADER.index('Named Python functions');end=HEADER.index('from dataclasses')
HEADER=HEADER[:start]+'''Direct named Python phases preserve candidate ordering, byte arithmetic,
real caller frames and explicit display/input dependencies. Native postbattle
observations select this consumer; they do not imply DomesticCA19 was called.
No ROM/IR execution, interrupt scheduling or acknowledgement is synthesized.
"""\n'''+HEADER[end:]
HEADER=HEADER.replace('AudioRegisters','SuccessionRegisters').replace('AudioBlockBudget','SuccessionBlockBudget').replace('AudioSceneServices','BattleSuccession')
start=HEADER.index('    """Physical14');end=HEADER.index('    def _checkpoint')
HEADER=HEADER[:start]+'''    """Physical25/26 A00C ->AD81, actual city main13 postbattle consumer.

    PUBLIC owns only the real export/body. LOCAL entries are separately
    exposed for bounded original CPU tests, not broad coordinator routing.
    The four dispatch indices are postbattle0401<7, player0402<8,
    computer0402<6 and retirement0402<3. Out-of-table fixtures are rejected
    before decoding any original table-outside bytes.
    """
    PAIR=(25,26)
    PUBLIC_ENTRIES=(0xA00C,0xAD81)
    def __init__(self,memory,rom,services=None):
        super().__init__(memory,rom,services);self._call_owner=None
    def fields(self):
        m=self.memory
        return dict(global_state=m[GLOBAL],NMI_scene=m[NMI_SCENE],city_main=m[CITY_MAIN],
            postbattle_phase=m[POSTBATTLE_PHASE],succession_phase=m[SUCCESSION_PHASE],
            affected_ruler=m[AFFECTED_RULER],old_leader=m[OLD_LEADER],
            successor=m[SUCCESSOR],successor_city=m[SUCCESSOR_CITY],
            notice_timer=m[NOTICE_TIMER],return_state=tuple(m[x]for x in range(RETURN_PHASE,RETURN_MAIN_PHASE+1)),
            cooperation_request=m[0x6F8B],PPU_jobs=m[PPU_JOBS])
'''+HEADER[end:]
HEADER=HEADER.replace('No actual pending audio caller','No actual pending postbattle caller').replace('Actual pending audio caller','Actual pending postbattle caller')
HEADER=HEADER.replace('entry=0xA003','entry=0xA00C').replace('entry not in self.PUBLIC_ENTRIES','entry not in self.LOCAL_ENTRIES')
HEADER=HEADER.replace('Only genuine audio scene export/body entries','Entry outside original bounded postbattle closure').replace('Audio entry requires physical14/15 caller context','Succession entry requires physical25/26 caller context')
HEADER=HEADER.replace('return self.run_entry(0xA003','return self.run_entry(0xA00C')
HEADER=HEADER.replace("ROM_SHA256='"+SHA+"'",''.join(f'{name}=0x{a:X}\n'for a,name in FIELDS.items())+"\nROM_SHA256='"+SHA+"'")
class SuccessionStructurer(CityStructurer):
    def addr(self,item):
        n=item['operand'];mode=item['mode'];base=FIELDS.get(n,f'0x{n:04X}')
        if mode in('abs','zpg'):return base
        if mode in('abx','aby'):return f'({base}+r.{"x"if mode=="abx"else"y"})&65535'
        if mode in('zpx','zpy'):return f'({base}+r.{mode[-1]})&255'
        if mode=='iny':return f'((m[0x{n:02X}]|m[0x{(n+1)&255:02X}]<<8)+r.y)&65535'
        if mode=='inx':return f'm[({n}+r.x)&255]|m[({n}+r.x+1)&255]<<8'
        raise ValueError((mode,item['pc']))
    def procedure(self,entry):
        if entry in MANUAL:
            source=MANUAL[entry];self.stats.append(dict(entry=entry,name=self.names[entry],instruction_nodes=len(self.graph(entry)),source_lines=len(source.splitlines()),hand_written_structured_control=True));return source
        return labelled_procedure(self,entry)
def digest(b):return hashlib.sha256(b).hexdigest()
def analyze(rom):
    I,tables=collect(rom,pair=25,entries=PUBLIC);assert len(I)==877
    OUT.mkdir(parents=True,exist_ok=True)
    cat=dict(schema='phase16-postbattle-succession-raw-closure-v1',rom_sha256=SHA,pair=[25,26],public_entries=list(PUBLIC),
        original_instruction_count=len(I),original_instructions=sorted(I.values(),key=lambda x:x['pc']),dispatch_tables=list(tables.values()),
        external_calls=[dict(call_pc=x['pc'],target=x['operand'],inline_target=x.get('inline_target'),rom_offset=x['rom_offset'])for x in I.values()if x.get('hook')],
        family_table=dict(physical_bank=26,cpu_address=0xC342,rom_offset=16+26*8192+0x342,length=56,raw_hex=rom[16+26*8192+0x342:16+26*8192+0x37A].hex()),
        actual_bridge=dict(bank=27,call_pc=0xA067,selector=0x39,inline_target=0xA00C,rom_offset=16+27*8192+0x67,raw_hex=rom[16+27*8192+0x65:16+27*8192+0x6D].hex()))
    (OUT/'static-catalog.json').write_text(json.dumps(cat,ensure_ascii=False,indent=2)+'\n')
    (OUT/'original.asm').write_text('; Raw bounded postbattle city13 closure; all file offsets include16B header.\n'+'\n'.join(f'b{x["physical_bank"]:02d}:${x["pc"]:04X} file{x["rom_offset"]:06X} {x["raw_hex"]:9s} {x["op"]} {x["mode"]} ${x["operand"]:04X}'+(f' inline${x["inline_target"]:04X}'if'inline_target'in x else'')for x in sorted(I.values(),key=lambda x:x['pc']))+'\n')
    b=SuccessionStructurer.__new__(SuccessionStructurer);b.I=I;b.catalog={};b.roots=set(PUBLIC)|{x['operand']for x in I.values()if x['op']=='JSR'and not x.get('hook')}|{v for x in I.values()if x['op']=='DISPATCH'for v in x['targets']}|set(tables)|{e for e in NAMES if e in I}
    b.names={pc:NAMES.get(pc,f'succession_local_{pc:04x}')for pc in b.roots};b.stats=[];b.loop_count=b.if_count=0
    source=HEADER+'    LOCAL_ENTRIES='+repr(tuple(sorted(b.roots)))+'\n    def _entry(self,entry):\n'
    for index,pc in enumerate(sorted(b.roots)):source+=f'        {"if"if index==0 else"elif"} entry==0x{pc:04X}:return self.{b.names[pc]}()\n'
    source+='        raise ValueError("Outside original named postbattle body")\n\n'
    for pc in sorted(b.roots):
        body=b.procedure(pc)
        if pc not in MANUAL:body=re.sub(r'self\._mark\(([^\n;]+)\)',r'yield from self._checkpoint(\1)',body)
        source+=body
    source=source.replace('from dataclasses import dataclass',loop_exception_source(b.stats)+'from dataclasses import dataclass')
    ast.parse(source);SOURCE.write_text(source)
    (OUT/'source-catalog.json').write_text(json.dumps(dict(source_sha256=digest(source.encode()),procedures=b.stats,structured_ifs=b.if_count,natural_loops=b.loop_count,hand_written_core_functions=list(MANUAL),runtime_IR_interpretation=False),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(instructions=len(I),tables=[t['count']for t in tables.values()],procedures=len(b.roots),source_bytes=len(source.encode()))))
def evidence():
    v=json.loads((OUT/'validation.json').read_text());c=json.loads((OUT/'static-catalog.json').read_text());st=json.loads((OUT/'source-catalog.json').read_text())
    static={x['pc']for x in c['original_instructions']};dynamic={x['cpu_address']for x in v['executed_original_locations']if x['physical_bank']in(25,26)}&static
    native=[x for x in v['rows']if x['group']=='native_input_genuine_A00C'];source_pins=v['source_sha256'];stale=[p for p,h in source_pins.items()if digest((ROOT/p).read_bytes())!=h]
    e=dict(schema='phase16-battle-succession-direct-source-evidence-v1',status=v['status']if not stale else'failed',rom_sha256=SHA,
        source_original_CPU_callbacks=0,source_IR_interpretation=False,source_sha256=source_pins,stale_source_paths=stale,
        artifact_sha256={str((OUT/p).relative_to(ROOT)):digest((OUT/p).read_bytes())for p in('static-catalog.json','source-catalog.json','original.asm','validation.json')},
        static_instruction_count=len(static),dynamic_instruction_count=len(dynamic),unexecuted_body_positions=sorted(static-dynamic),
        source_structure=dict(procedures=len(st['procedures']),structured_ifs=st['structured_ifs'],natural_loops=st['natural_loops'],hand_written_core_functions=st['hand_written_core_functions']),
        rom_cpu_case_count=v['rom_cpu_case_count'],complete_return_count=v['complete_return_count'],strict_prefix_count=v['strict_prefix_count'],source_guard_case_count=v['source_guard_case_count'],comparison=v['comparison'],
        native_input_genuine_callee_count=len(native),A000_derived_callee_count=sum(not x['input']['A000_cadence_returned_before_dispatch']for x in native),
        explicitly_declared_A01F_suffix_count=sum(x['input']['A000_cadence_returned_before_dispatch']for x in native),
        phases=[dict(index=i,entry=pc,name=NAMES[pc])for i,pc in enumerate([0xAD95,0xADAA,0xAE0D,0xAE51,0xBE01,0xC132,0xC37A])],
        exact_chain=dict(battle_end_native='global4/NMI3 battle12/15 then global1/NMI2 city13, frozenNative observations only',
            original_city_dispatch='27A065 LDY39;27A067 EE07 inlineA00C ->25A00C JMPAD81',
            computer='ADAA affectedlow nibble0507, oldleaderstatus3 and wholecontroller3 ->C132',
            human='ADAA orAE0D affectedrulerstatus3, wholecontroller!=3 ->BE01',
            family='C158 family table26C342, C1A1 scansowner low3 and compactrosters; firstfamily list candidate found wins',
            nonfamily='C1DB/C21D lastmoralitytie in orderedcity/roster prefixes wins; noHP/status/byte5 predicate',
            computer_commit='C25D rulerbyte0, C101 roster-headswap, C289 candidate忠100; AIdoesnotwrite rulerresidence or candidatebyte5',
            player_commit='BF2F confirmation setsrulerbyte0 andEE/EF+1 residence, C101 headswap; BFB9/C01E candidate忠100',
            no_candidate='C1DB sets0401=0471 thenC37A/C386 clears only affectedrulerleaderFF; UIthenC41E256-byteclock orC3C2 actualhumanending',
            distinct_from_Domestic='NoCA19/CB52 acknowledgement chain, and theseC132/C37A subflows never emitFB/FC. 6F8B onlywrittenby separateAE51 AIturnrestore branch.'),
        guards=v['guards'],limits=v['limits']+['Thisbody does not redo battleD6CC deaths, casualty/loot/prisoner settlement or initialcityowneroccupation; those precede its Nativeinputs.',
            'AIretirement is leader-only, not a uniformallcity/roster/diplomacy neutralization. Playerrelease canneutralizeoneemptycity withwholebyte7; AIreleaseleavesowner/location unchanged.'])
    (OUT/'evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
    lines=['# 原战后继承：城市13消费者与灭亡反馈','',
        '[BattleSuccession](../../../source/recovered/battle_succession.py)独立恢复physical25/26 A00C→AD81的7阶段、玩家8子阶段、电脑6子阶段、无继承3子阶段。生产为具名直接Python函数、分支/循环/generator，没有ROM/IR执行或原CPUfallback。四项核心扫描/首将swap/脱离名单为手写可读循环，保留原flags、scratch、实际JSR/PHA/PLA/RTS、同址写序。旧CityPanel和Domestic模块不改。',
        '', '## 实际入口和phase15内政链的区别','',
        '冻结原Nestopia记录中：袁紹8死亡后battle12/15结束，转global1/NMI2 city13/0；电脑候选9或空名单最终分别写9/FF，玩家失败则city13/4选择所属城及新君主。本轮以这些原RAM/SRAM从原27A000回调生成真实27A067 EE07→25A00C的callerframe，另一个frame6253依原A000 cadence早退，明示使用A01F合法dispatchsuffix。AXYP/前置固定调用是CPU fixture，不是Nestopia内部寄存器/指令trace；不能把这些输入称完整硬件帧。',
        '', 'Native战后候选不是phase15受控DomesticCA19/CB52链。实际ADAA按0507低nibble检查败方；AE0D按高nibble检查另一方。只有leader.status低2==3才触发继承；此时controller整个byte==3走电脑C132，其余controller走玩家BE01。未触发则进入后续检查/返回。Native候选9的byte5=0仍合格，原码没有从它推断任职地。',
        '', '| 0401 | 函数 | 作用/真实门槛 |','|---:|---|---|']
    descriptions=['清04E4，请求29A01E年月packet，回返后phase++','等7E==0，查败方leader/status，设置玩家或电脑继承入口','查胜方leader/status，同样保留原controller分支','按当前EE/EF控制器恢复人类城市/驻城光标或AI回合','玩家选择所属城市→原武将名单→确认→忠诚和可能脱离','通知→8bit计时→家族→德fallback→写回→通知等待→followers','无候选：通知/leaderFF；人类输入进入ending或电脑8bit计时返回']
    lines += [f'| {i} | {NAMES[pc]} / ${pc:04X} | {descriptions[i]} |'for i,pc in enumerate([0xAD95,0xADAA,0xAE0D,0xAE51,0xBE01,0xC132,0xC37A])]
    lines += ['', '## 候选、写回与原差异','',
        '- 电脑先按26C342每君主8B家族名单的既定次序查找；所属城条件只有city.owner&7==040A。名单遇第一FF停止；家族命中先于FF检查。候选HP、状态、byte5都不是资格字段。',
        '- 家族无候选后C1DB遍历30城，C21D对各城紧凑前缀按武将+4徳选择；原CMP的carry包括等号，所以同值后来的候选替换前者。没有过滤死亡/在野状态，也没有按bodyHP取代名单资格。',
        '- C25D电脑提交只写affectedruler.byte0和城市首将swap；不写ruler驻城byte1或候选byte5。确认后候选忠诚100；家族候选跳过followers调整。',
        '- 玩家原地图必须选owner&7匹配的城，再选原名单并确认。BF2F写新leader、EE/EF+1驻城，再首将swap。低忠诚非新leader可能脱离：玩家C01E清status低2并写byte5=city，空名单的owner整个byte写7；电脑C318清status低2/紧凑名单，保留byte5和owner。这些不统一为相同转属事务。',
        '- 无候选C386只写affectedruler.byte0=FF，保留controller/外交/城市归属/其余名单。此处controller按低2位==3分通知分支，和ADAA/AE0D对整个byte==3的测试不同。电脑C41E在04D0原8bit增一计时的256调用wrap后回0472/0473；人类C3C2必须真实文字完成和A/B输入才进入global13。调用不是视频帧。',
        '- raw兵数字节与高6位不改；边界病例包括F123完整word，源和原CPU全8KiB SRAM比较。battle死亡、战胜占领、败退和俘虏数组等在前序已发生，本消费者不能据leaderFF再补一遍统一清理。',
        '', '## 服务/调用合同','',
        'PUBLIC仅(A00C,AD81)、PAIR25/26；LOCAL38入口供独立原CPU定向fixture，不抢其它panel。run_entry要求实际registers和已有returnword，无seed参数；ServiceCall只有status returned且原PC/SP真实返回才继续。四dispatch索引严格限定7/8/6/3，非法fixture只做源码guard，不执行原表外code。',
        '', '真正依赖为固定record/message/menu/RNG，29A01E年月producer、27A006候选城市资料、10A009→CF7C忠诚及固定E57F/E673/E683音频请求。根协调器现接独立exact owners，源码侧原CPUhelper调用0。文字、城市资料与PPU状态由真实consumer推进；正文不写ready或ack，不自动制造按钮/NMI/IRQ。',
        '', '## 验证范围','',
        f'原CPU {v["rom_cpu_case_count"]} 项：{v["complete_return_count"]}完整实际callerRTS、{v["strict_prefix_count"]}严格prefix（刻意缺recordhelper及显式零预算）；另{v["source_guard_case_count"]}源码guard。全部2048B RAM（含闲置栈）、8192B SRAM、AXYP/SP/PC、端口读写序/映射银行/N163图相同，失败{v["failed_count"]}。',
        f'其中{len(native)}个原Native输入callee：{e["A000_derived_callee_count"]}由原A000回调产生，{e["explicitly_declared_A01F_suffix_count"]}明示A01F suffix；准备步骤不再计新增case。覆盖全合法dispatch索引、7君主family/noheir、HP/condition/byte5边界、firstFF/tie、首将swap、31忠诚/20RNG门槛、玩家/电脑脱离、raw兵和计时wrap。',
        f'原静态877位置，动态{len(dynamic)}，尚未动态覆盖{len(static-dynamic)}位置逐项列evidence；完整静态正文不等于所有分支/数据值/自然战役已验证。Native原画面/声音由原核心生成，另见phase16 runtime，不能由本软件比较声称硬件像素/PCM等价。',
        '', '```python','owner = BattleSuccession(memory, rom, services=exact_source_coordinator)','owner.run_entry(0xA00C, registers=actual_caller)','owner(actual_ServiceCall)','owner.resume()  # 同一真实pending，等待外部服务返回','```','',
        '```sh',"python3 scripts/analyze_battle_succession.py '/Users/paulasmith/Downloads/三国志2超级版.nes'", ".venv-trace/bin/python scripts/verify_battle_succession.py '/Users/paulasmith/Downloads/三国志2超级版.nes'", "python3 scripts/analyze_battle_succession.py '/Users/paulasmith/Downloads/三国志2超级版.nes' --evidence-only",'```','',
        '[原汇编](original.asm) · [静态catalog](static-catalog.json) · [原CPU回执](validation.json) · [真实caller输入](actual-callee-inputs/) · [完整pins/未覆盖](evidence.json)']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(dict(status=e['status'],CPU=v['rom_cpu_case_count'],guards=v['source_guard_case_count'],dynamic=len(dynamic),stale=stale)))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('rom',type=Path);p.add_argument('--evidence-only',action='store_true');a=p.parse_args();rom=a.rom.read_bytes();assert digest(rom)==SHA
    if a.evidence_only:evidence()
    else:analyze(rom)
if __name__=='__main__':main()
