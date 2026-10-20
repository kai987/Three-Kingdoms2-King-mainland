"""All sixteen readable tactic effects and their explicit settlement windows.

The original ROM supplies immutable tables only. Graphics, sound, message and
input prerequisites remain real dependencies. No opcode IR or ROM CPU executor
is called by this semantic gameplay layer.
"""
from dataclasses import dataclass
import hashlib
from .tactical_effects import TacticalEffects,EffectData,SUPPORTED_EFFECT_IDS,ROM_SHA256

REMAINING_EFFECT_IDS=(1,5,7,8,9,10,12,14)
ALL_EFFECT_IDS=tuple(range(16))

@dataclass(frozen=True)
class CompleteEffectData:
    base:EffectData
    individual:object
    area_conversion:object
    player_result_messages:bytes
    level_notice_officers:bytes

    @classmethod
    def from_rom(cls,rom):
        if hashlib.sha256(rom).hexdigest()!=ROM_SHA256:
            raise ValueError('Complete tactic data requires the pinned original ROM')
        from .tactic_individual_effects import IndividualData
        from .tactic_area_conversion import AreaConversionData
        messages=bytes(rom[0x18B2A:0x18B3A])
        assert len(messages)==16
        return cls(EffectData.from_rom(rom),IndividualData.from_rom(rom),
                   AreaConversionData.from_rom(rom),messages,bytes(rom[0x133E8:0x133FE]))

class CompleteTacticalEffects(TacticalEffects):
    """Shared-memory, independently readable effect implementation.

    Full effect bodies can return a dependency at a real death-map refresh.
    Their documented continuation completes gameplay data after that service;
    it never acknowledges the service itself. Other after_* methods inherit
    the same precise external-prelude contract as the earlier eight effects.
    """
    def __init__(self,memory,data:CompleteEffectData):
        super().__init__(memory,data.base);self.complete_data=data
        from .tactic_individual_effects import IndividualTactics
        from .tactic_area_conversion import AreaConversionTactics
        self.individual=IndividualTactics(memory,data.individual)
        self.area_conversion=AreaConversionTactics(memory,data.area_conversion)
        self._pending_cast_path=None
        self._pending_effect_start=None
        self._pending_player_cost=None

    def dispatch(self):
        """B02B reset followed by one of all sixteen recovered effect bodies."""
        if self.individual.pending is not None:
            raise RuntimeError('Pending death refresh must return before another effect dispatch')
        tactic=self.memory[0x543]&15
        if tactic in SUPPORTED_EFFECT_IDS:return super().dispatch()
        for address in range(0x42C,0x435):self.memory[address]=0
        self.memory[0x544]=0
        if tactic in (1,5,9):
            result=self.individual.apply(tactic)
            if self.individual.pending is not None:
                self._pending_effect_start=result
                return {**result,'resume':'after_death_map_refresh'}
            return result
        return self.area_conversion.apply(tactic)

    def player_cast_after_animation(self):
        """Original player fee/effect window, retaining a death continuation."""
        if self.individual.pending is not None:
            raise RuntimeError('Pending death refresh must return before another player cast')
        result=super().player_cast_after_animation()
        if self.individual.pending is not None:
            self._pending_cast_path='player'
            self._pending_player_cost=self.data.player_costs[self.memory[0x543]]
            return {**result,'caller_path':'player','resume':'after_death_map_refresh'}
        return result

    def cast_after_portrait(self):
        """Original AI effect window, retaining its caller after a death."""
        if self.individual.pending is not None:
            raise RuntimeError('Pending death refresh must return before another AI cast')
        result=super().cast_after_portrait()
        if self.individual.pending is not None:
            self._pending_cast_path='AI'
            return {**result,'caller_path':'AI','resume':'after_death_map_refresh'}
        return result

    def after_death_map_refresh(self,*,map_refresh_returned):
        """Resume after the actual synchronous D6CC refresh request returned.

        This confirms a real call return, not completion of asynchronous PPU
        rendering. It never writes a graphics/audio/message completion flag.
        Restore the exact player/AI data suffix when the cast was suspended.
        """
        effect=self.individual.after_death_graphics(map_refresh_returned=map_refresh_returned)
        if effect['status']!='returned':
            return {**effect,'resume':'after_death_map_refresh','caller_path':self._pending_cast_path}
        if self._pending_effect_start is not None:
            effect={**effect,'success':self._pending_effect_start['success'],
                    'gate':self._pending_effect_start['gate']}
            self._pending_effect_start=None
        path=self._pending_cast_path;self._pending_cast_path=None
        if path=='player':
            self._refresh_selectors();self.memory[0x50B]=0
            cost=self._pending_player_cost;self._pending_player_cost=None
            return {'status':'returned','effect':effect,'caller_path':path,'ap_cost':cost}
        if path=='AI':
            self._refresh_selectors();self.memory[0x12]=1
            return self._boundary(0xC0A7,'D6CC unit graphics',effect=effect,
                                  caller_path=path,resume='finish_after_graphics')
        return effect

    def player_result_scan(self):
        """AAA7..AAB6: wait for actual007E, request one unit graphics pass.

        This is the original result scan cursor050B, not a selected target.
        The caller must perform the D6CC graphics service before continuing.
        """
        m=self.memory
        if m[0x7E]:return {'status':'waiting','flag_address':0x7E,'flag_value':m[0x7E]}
        if not 0<=m[0x50B]<20:raise ValueError('Original result scan cursor0..19 required')
        m[0x509]=m[0x50B];m[0x12]=1
        return self._boundary(0xAAB6,'D6CC unit graphics',resume='advance_player_result_after_graphics')

    def advance_player_result_after_graphics(self):
        """AAB9 suffix after an actual unit graphics pass returned."""
        m=self.memory;self._set(0x50B,m[0x50B]+1)
        if m[0x50B]<20:return {'status':'returned','scan_cursor':m[0x50B],'message_requested':False}
        self._set(0x501,m[0x501]+1)
        if m[0x544]:
            m[0xA4]=4;self._queue(0x73,2);m[0x509]=m[0x50A]
            return self._boundary(0xAADD,'bank29 A027 actor portrait',
                                  message=0x73,job=2,message_completed=False,
                                  resume='player_confirm_after_text_ready')
        return self.queue_player_success_result()

    def queue_player_success_result(self):
        """AAE3..AB19: actual message selection, with death-report override.

        Unlike the AI result suffix, successful player output sets00A4=3.
        ID9 with zero troop loss selects ID1 text; either can report0432 deadID.
        """
        m=self.memory;m[0xA4]=3;selected=m[0x543]&15
        if selected==9 and self._word(0x42C)==0:selected=1
        if selected in (1,9) and m[0x432]!=255:
            m[0x42C]=m[0x432];self._queue(0x4E,5)
            return {'status':'returned','message':0x4E,'job':5,'message_completed':False,
                    'death_report_officer':m[0x432]}
        message=self.complete_data.player_result_messages[selected];self._queue(message,2)
        m[0x509]=m[0x50A]
        return self._boundary(0xAADD,'bank29 A027 actor portrait',message=message,job=2,
                              message_completed=False,resume='player_confirm_after_text_ready')

    def player_confirm_after_text_ready(self):
        """AB32..AB41 after actual DF27/DC63 readiness services returned.

        Read the real button byte rather than synthesizing confirmation.
        The level query/pop-up remains a separately named real service.
        """
        m=self.memory
        if not m[0x81]&1:return {'status':'waiting','button_address':0x81,'button_mask':1}
        slot=m[0x50A]
        if not 0<=slot<20:raise ValueError('Original actor slot0..19 required')
        m[0x42C]=m[0x664+slot]
        return self._boundary(0xAB41,'DEE9 actual level-change query',
                              resume='level_change_query')

    def level_change_query(self):
        """Complete DEE9..DF26 plus bank8A018->bank9D390 notice helper.

        This announces an already applied experience level change. The raw
        officer byte may beFF on the original internal removed-actor path.
        D390 only decides a second notice; it does not grant an item or tactic,
        change equipment, or rewrite membership. Message queues stay pending.
        """
        m=self.memory;ident=m[0x42C];address=0x63C0+12*ident
        packed=m[address+11]&240
        if packed==m[0x52C]:return {'status':'returned','level_changed':False,'original_carry':False}
        m[0x42F]=(m[address+1]-m[0x52E])&255
        m[0x42D]=m[0x430]=m[0x431]=0
        level=packed>>4;start={3:0,4:11,5:17,6:20}.get(level)
        eligible=False
        if start is not None:
            for value in self.complete_data.level_notice_officers[start:]:
                if value==255:break
                if value==ident:eligible=True;break
        if not eligible:m[0x42D]=255
        message=0x4A if m[0x42F] else 0x4D;self._queue(message,5)
        return {'status':'returned','level_changed':True,'original_carry':True,
                'martial_delta_byte':m[0x42F],'second_notice_eligible':eligible,
                'message':message,'job':5,'message_completed':False,
                'resume':'player_level_change_after_query'}

    def player_level_change_after_query(self):
        """AB46..AB49 after the actual query returned carry set."""
        self._set(0x501,self.memory[0x501]+1)
        return self._boundary(0xAB49,'E57F audio reset, then E68B sequence7B',
                              resume='player_second_notice_after_text_ready')

    def player_second_notice_after_text_ready(self):
        """AB57..AB6F/AB86 after actual text/input readiness services.

        A eligible-officer second notice writes042D=FF before queuing4B, so
        another real confirmation enters the audio/cursor-return path.
        """
        m=self.memory
        if not m[0x81]&1:return {'status':'waiting','button_address':0x81,'button_mask':1}
        if m[0x42D]!=255:
            m[0x42D]=255;self._queue(0x4B,5)
            return {'status':'returned','message':0x4B,'job':5,'message_completed':False}
        return self._boundary(0xAB67,'E57F audio reset, then E673 sequence1D',
                              resume='finish_player_without_level_change_after_query')

    def finish_player_without_level_change_after_query(self):
        """AB6F..AB82 after the actual level query reported no change.

        Restore the four-byte map cursor saved by the original cast prelude.
        Cursor graphics A1F7 remains external; no text/input acknowledgement is
        implied by copying these memory fields.
        """
        m=self.memory
        for offset in range(3,-1,-1):m[0x6F3F+offset]=m[0x46C+offset]
        m[0x501]=m[0x500]=0
        return self._boundary(0xAB82,'A1F7 cursor graphics',scene_state=[0,0])
