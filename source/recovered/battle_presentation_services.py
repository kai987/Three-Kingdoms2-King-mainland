"""Compose real battle text/graphics/audio software services on shared memory.

The service layer emits original register requests. It does not manufacture a
NES frame, IRQ edge, input event or completed job. Missing scene controllers
remain explicit NMI callbacks; readable player-tactic bodies are exposed with
precise entry points, independent of their outer battle-controller wrappers.
"""
from .battle_graphics_services import BattleGraphicsServices,GraphicsData,GraphicsRegisters
from .audio_services import AudioServices,AudioData
from .text_services import TextServices,TextData
from .battle_nmi_services import BattleNMIServices,NMIRegisters
from .service_memory import ServiceMemory
from .scroll_graphics_services import ScrollGraphicsServices

class BattlePresentationServices:
    def __init__(self,game):
        if not isinstance(game.memory,ServiceMemory):raise ValueError('Presentation requires explicit ServiceMemory/register inputs')
        self.game=game;self.memory=game.memory;rom=game._require_rom()
        self.graphics=BattleGraphicsServices(self.memory,GraphicsData.from_rom(rom))
        self.audio=AudioServices(self.memory,AudioData.from_rom(rom))
        self.text=TextServices(self.memory,TextData.from_rom(rom))
        from .tactic_presentation_effects import TacticPresentationEffects
        previous=game.tactical_effect_rules()
        if previous.individual.pending is not None:raise RuntimeError('Resume the existing effect before enabling presentation')
        self.effects=TacticPresentationEffects(self.memory,previous.complete_data,self._banked,self.graphics)
        game._tactical_effects=self.effects
        self.nmi=BattleNMIServices(self.memory,callbacks=self.source_callback)
        self.fixed=BattleNMIServices(self.memory,callbacks=self.source_callback)
        self.irq=BattleNMIServices(self.memory)
        self.external_callback=None;self.last_callback_contract=None
        self.scroll=ScrollGraphicsServices(self.memory,self.graphics.data)

    def _program_pair(self,selector):
        m=self.memory;m[0xE2]=selector;m[0xE3]=(selector+1)&255
        m[0xF000]=m[0xE3];m[0xE800]=selector|192

    def _banked(self,selector,body):
        """Real EE07 identified-callee bank protocol around independent code."""
        restore=self.memory[0xE2];self._program_pair(selector)
        result=body();self._program_pair(restore);return result

    @staticmethod
    def _return_call(call):
        """The callee actually returned: consume its existing caller address."""
        r=call.registers;m=call.memory
        r.sp=(r.sp+1)&255;lo=m[0x100+r.sp]
        r.sp=(r.sp+1)&255;hi=m[0x100+r.sp]
        r.pc=((lo|hi<<8)+1)&65535
    @staticmethod
    def _apply_registers(registers,values):
        for key in ('a','x','y','p','sp'):
            if key in values:setattr(registers,key,values[key])

    def source_callback(self,call):
        """Only identified pure service bodies may satisfy an actual call.

        Text/animation transient CPU registers are outside their semantic API.
        Their NMI bridge is explicitly a software-service composition contract;
        it is not a substitute for the exact CPU-protocol controller interface.
        Other callbacks can be supplied by the real scene-controller owner.
        """
        pair=tuple(call.entry_banks[1:3]);target=call.target;r=call.registers;result=None
        if pair==(14,15)and target in(0xA003,0xD8D4):
            result=self.audio.tick(registers=r)
            if result.get('status')!='returned':return {**result,'status':'dependency'}
            self._apply_registers(r,result['contract_registers'])
            self.last_callback_contract='audio body returned-register contract'
        elif pair==(29,30):
            methods={0xA000:self.text.consume_text,0xA048:self.text.consume_text,
                     0xA003:self.text.produce_text,0xA154:self.text.produce_text,0xA158:self.text.produce_text,
                     0xA006:self.text.consume_map_commands,0xA11B:self.text.consume_map_commands,
                     0xA027:self.text.draw_actor_panel,0xA830:self.text.draw_actor_panel}
            if target in methods:
                result=methods[target]();self.last_callback_contract='text semantic RAM/port contract; transient registers excluded'
        elif pair==(25,26)and target in(0xA00F,0xCFD6):
            result=self.graphics.animation_tick(GraphicsRegisters(r.a,r.x,r.y,r.p))
            self.last_callback_contract='animation semantic RAM/port contract; transient registers excluded'
        elif pair==(23,24)and target in(0xA00C,0xA387,0xA00F,0xAB53):
            method=self.scroll.tile_scroll if target in(0xA00C,0xA387)else self.scroll.attribute_scroll
            result=method(registers=r)
            self.last_callback_contract='scroll body returned-register contract'
        elif pair==(12,13)and target in(0xD6CC,0xD657,0xDC63,0xDC70):
            method={0xD6CC:self.graphics.map_refresh,0xD657:self.graphics.cursor,
                    0xDC63:self.graphics.highlight,0xDC70:self.graphics.highlight}[target]
            kwargs={'alternate':True}if target==0xDC70 else{}
            result=method(GraphicsRegisters(r.a,r.x,r.y,r.p),**kwargs)
            self._apply_registers(r,result['registers']);self.last_callback_contract='graphics returned-register contract'
        if result is None:
            if self.external_callback is not None:return self.external_callback(call)
            return {'status':'dependency','target':target,'entry_banks':list(call.entry_banks),
                    'reason':'Scene/controller or service body still needs its explicit owner'}
        if result.get('status')not in('returned','waiting'):
            return {**result,'status':'dependency'}
        # "waiting" in text is a real early RTS with software work pending;
        # it does not imply a missing hardware input or a completed queue.
        self._return_call(call)
        return {'status':'returned','body':result,'contract':self.last_callback_contract}

    def run_nmi(self,registers=None,*,hardware_entry=False,external_callback=None):
        self.external_callback=external_callback
        return self.nmi.run_nmi(registers,hardware_entry=hardware_entry)
    def resume_nmi(self):return self.nmi.resume_nmi()
    def run_irq(self,registers=None,*,hardware_entry=False):
        return self.irq.run_irq(registers,hardware_entry=hardware_entry)

    def _cursor_return_request(self):
        """Complete12 A1F7: realqueue5, D6CC return, clear0424/0425."""
        m=self.memory;self.effects._queue(5,5);m[0x12]=1
        refresh=self.graphics.map_refresh();m[0x424]=m[0x425]=0
        return {'status':'returned','cursor_request':refresh,'actual_text_job':5}

    def player_tactic_body(self):
        """One exact player main5 body for sub5..10, not a video/NMI frame.

        Entry points AA2E/AA6C/AAA7/AB2A/AB52/AB90 begin after the parent
        controller's actual dispatch. Real text readiness, buttons, animation
        counters, map-command builders and audio drivers are used. Source map
        refresh can now return from its full body without a manual death ack.
        """
        m=self.memory
        if m[0x500]!=5 or not 5<=m[0x501]<=10:raise ValueError('Player tactic body requires battle5/sub5..10')
        sub=m[0x501]
        if sub==5:
            self.graphics.highlight();self.graphics.cursor()
            if not self.text.text_ready()or not m[0x81]&1:return {'status':'returned','waiting':'actual text/button'}
            m[0x501]=(m[0x501]+1)&255
            m[0xC3]=137;m[0xC4]=138;m[0xC5]=m[0xC2]=136
            m[0x650+m[0x509]]=0;m[0x4C8]=(m[0x543]+1)&255;m[0x310]=5;m[0x300]=0
            return {'status':'returned','animation_requested':m[0x4C8]}
        if sub==6:
            result=self.effects.player_cast_after_animation()
            if self.effects.individual.pending is not None:
                refresh=self.graphics.map_refresh()
                result=self.effects.after_death_map_refresh(map_refresh_returned=refresh['status']=='returned')
                result={**result,'actual_source_death_refresh':refresh}
            return result
        if sub==7:
            result=self.effects.player_result_scan()
            if result['status']=='waiting':return {'status':'returned','waiting':'actual PPU jobs','body':result}
            refresh=self.graphics.map_refresh();result=self.effects.advance_player_result_after_graphics()
            if result.get('pc')==0xAADD:
                panel=self._banked(61,self.text.draw_actor_panel)
                return {'status':'returned','result':result,'map_refresh':refresh,'actual_actor_panel':panel}
            return {'status':'returned','result':result,'map_refresh':refresh}
        if sub in(8,9):
            if not self.text.text_ready():return {'status':'returned','waiting':'actual text readiness'}
            self.graphics.highlight()
            if not m[0x81]&1:return {'status':'returned','waiting':'actual A button'}
            if sub==8:
                self.effects.player_confirm_after_text_ready();query=self.effects.level_change_query()
                if query['level_changed']:
                    self.effects.player_level_change_after_query();self.audio.reset();self.audio.request(0x7B,entry=0xE68B)
                    return {'status':'returned','level_query':query,'actual_audio_sequence':0x7B}
                self.effects.finish_player_without_level_change_after_query()
                return self._cursor_return_request()
            result=self.effects.player_second_notice_after_text_ready()
            if result.get('pc')==0xAB67:
                self.audio.reset();self.audio.request(0x1D,entry=0xE673)
                self.effects.finish_player_without_level_change_after_query();return self._cursor_return_request()
            return result
        # The original invalid-target acknowledgement is independent of
        # success/failure of an already submitted tactic effect.
        if self.text.text_ready():
            self.graphics.highlight()
            if m[0x81]&1:m[0x501]=0
        return {'status':'returned','invalid_target_acknowledgement':True}
