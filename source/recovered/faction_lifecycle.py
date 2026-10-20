"""Reconstructed faction/end-condition effects, not original developer source.

Leader absence, city owner7, an FB notification and an ending scene are distinct
facts. These services reproduce bounded effects; they never invent a faction-wide
city/roster/diplomacy transaction, renderer completion or an acknowledgement.
"""
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json

from .battle_state_machine import BattleStateMachine, UnresolvedDependency

ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
ROOT = Path(__file__).resolve().parents[2]


def city_address(city):
    if not 0 <= city < 30:
        raise ValueError('Original city domain0..29')
    return 0x6000 + 32*city


def ruler_address(ruler):
    if not 0 <= ruler < 7:
        raise ValueError('Original ruler domain0..6')
    return 0x6F07 + 8*ruler


def officer_address(officer):
    """Original byte-input pointer, including adjacent non-officer records."""
    return 0x63C0 + 12*(officer & 255)


def word(memory, address):
    return memory[address] | memory[address+1] << 8


def put_word(memory, address, value):
    memory[address], memory[address+1] = value & 255, (value >> 8) & 255


def queue_message(memory, ident, packet_type=4):
    """F26D/F28B packet writes only; progress0 requests work, not completion."""
    memory[0x311] = ident & 255
    memory[0x310] = packet_type
    memory[0x312] = memory[0x313] = 255
    memory[0x300] = 0


@dataclass(frozen=True)
class FactionTables:
    original_leader_ids: tuple
    turn_orders: tuple

    @classmethod
    def from_rom(cls, rom):
        if hashlib.sha256(rom).hexdigest() != ROM_SHA256:
            raise ValueError('Wrong original ROM identity')
        # Pair25/26 C3BB and C93A are identical seven-ID message substitutions.
        a = 16 + 26*8192 + 0xC3BB - 0xC000
        b = 16 + 26*8192 + 0xC93A - 0xC000
        if rom[a:a+7] != rom[b:b+7]:
            raise ValueError('Original notification-name tables disagree')
        order = 16 + 25*8192 + 0xA104 - 0xA000
        return cls(tuple(rom[a:a+7]), tuple(tuple(rom[order+8*i:order+8*i+7]) for i in range(5)))


class FactionLifecycle:
    """Independent game-memory effects with explicit original entry contracts.

Most services preserve all SRAM except their documented write. Scratch/register
contracts are narrower than full CPU emulation. A caller must enter the stated
prefix, rather than treat one service as a complete faction or video-frame tick.
"""
    def __init__(self, memory, tables):
        self.memory, self.tables = memory, tables

    def snapshot(self, ruler):
        m = self.memory; a = ruler_address(ruler)
        owned = [c for c in range(30) if m[city_address(c)] & 7 == ruler]
        return {'ruler': ruler, 'leader_id': m[a], 'leader_absent': m[a] == 255,
                'controller_byte': m[a+3], 'cities': owned,
                'diplomacy_bytes': [m[a+i] for i in range(4, 8)],
                'rostered_entries': sum(m[city_address(c)+s] != 255 for c in owned for s in range(17, 27)),
                'no_automatic_cleanup': True}

    def count_owned_cities(self, ruler):
        """Bank28 DDBF: owner low3, all30 cities; no leader/status prerequisite."""
        ruler_address(ruler)
        return sum(self.memory[city_address(c)] & 7 == ruler for c in range(30))

    def select_next_active_ruler(self):
        """Bank25 A041..A090 until A091, with a seven-slot bounded scan.

        Only leaderID==FF is skipped: no city-count or controller test. Calendar
        and diplomacy advance while skipping. If allseven are absent, original
        code loops forever (while advancing calendar); this API returns after
        one scan period and explicitly does not call that a completed turn.
        """
        m = self.memory; order = m[0x6F45]
        if not 0 <= order < 5 or m[0x6F04] not in (*range(7), 255):
            raise ValueError('Proven turn-order0..4 and slot0..6/initialFF required')
        if not 0 <= m[0x6F01] < 12: raise ValueError('Proven calendar month0..11')
        scanned = []
        for _ in range(7):
            m[0x6F41] = 240; slot = (m[0x6F04]+1) & 255; m[0x6F04] = slot
            if slot >= 7:
                m[0x6F04] = m[0x6F06] = 0; slot = 0
                month = m[0x6F01]+1
                if month >= 12: month = 0; m[0x6F00] = (m[0x6F00]+1) & 255
                m[0x6F01] = month
                for ruler in range(7):
                    a = ruler_address(ruler)
                    for offset in range(4, 8):
                        value = m[a+offset]
                        lo, hi = value & 15, value >> 4
                        m[a+offset] = (max(hi-1, 0) << 4) | max(lo-1, 0)
            ruler = self.tables.turn_orders[order][slot]; pointer = ruler_address(ruler)
            m[0x6F03] = ruler; put_word(m, 0xEE, pointer); scanned.append(ruler)
            if m[pointer] != 255:
                return {'status': 'selected', 'ruler': ruler, 'scanned': scanned, 'stop_cpu': 0xA091}
        return {'status': 'no_active_ruler_in_scan_period', 'scanned': scanned,
                'original_nonterminating_if_all_absent': True, 'stop_cpu': 0xA041}

    def victory_entry_check(self):
        """Bank27 A089..A0AF, stop A0B0 when count differs from30.

        True changes0400 to15. It does not yet calculate a score or enter NMI8.
        The original dispatcher requires sub0 on entry; this prefix does not
        independently reset0401, so stale substate must not be concealed.
        """
        m = self.memory
        for a in (0x470, 0x471, 0x472, 0xA4, 0x4E4): m[a] = 0
        ruler = m[0x6F03]; count = self.count_owned_cities(ruler)
        m[0x10], m[0x11] = ruler, count
        if count == 30: m[0x400] = 15
        return {'city_count': count, 'all30_owned': count == 30,
                'stop_cpu': 0x0200 if count == 30 else 0xA0B0}

    def surviving_officer_pool(self, ruler):
        """Bank25 A240: exclude other leader IDs and low2status3, scan237.

        Includes status0/1/2 and the current ruler's leader. This is not city count,
        an owner-filtered roster count, or a check of health. F25F's mapper/CPU
        effects are outside this pure field contract.
        """
        m = self.memory; ruler_address(ruler)
        leaders = [m[ruler_address(r)] for r in range(7)]
        leaders[ruler] = 255
        for r, ident in enumerate(leaders): m[0x42C+r] = ident
        included = [i for i in range(237)
                    if i not in leaders and m[officer_address(i)+11] & 3 != 3]
        m[0x10], m[0x11] = 237, len(included)
        return {'count': len(included), 'included_ids': included,
                'termination_threshold': 30, 'below_threshold': len(included) < 30}

    def prepare_pool_warning(self):
        """Bank25 A094..A0A4; count already supplied in0011 by A240."""
        m = self.memory
        if m[0x11] >= 30: return {'warning': False, 'stop_cpu': 0xA0A5}
        m[0x401] = 3; queue_message(m, 0xD5)
        return {'warning': True, 'message_id': 0xD5, 'awaits_idle_then_A': True}

    def pool_warning_reset_gate(self):
        """Bank25 A186: no memory write; eligible branch is JMP E000."""
        m = self.memory
        ready = m[0x300] == 255 and m[0x304] == 255 and bool(m[0x81] & 1)
        return {'reset_requested': ready, 'boundary_cpu': 0xE000 if ready else None}

    def commit_no_successor_event(self, ruler):
        """Bank11 CA74..CA7E, after CA68 found neither successor route.

        Only leaderID and6F8B are changed. Residence, controller, diplomacy,
        officer status and cities/rosters are left exactly as they stand.
        """
        m = self.memory; m[ruler_address(ruler)] = 255; m[0x6F8B] = 0xFB
        return {'event': 'no_successor', 'wait_pc': 0xCA7F,
                'ack_address': 0x6F8B, 'required_ack': 1}

    def successor_wait_gate(self):
        """CA7F/CB79 busy loop requires the exact value1, not any nonnegative byte."""
        return self.memory[0x6F8B] == 1

    def repair_after_successor_ack(self, ruler):
        """CA52..CA57 bounded continuation after the real acknowledgement.

        Reuses the independently recovered C98F/C9A5 city-chief service. Finance
        words are capped as itsD105 calls do, and owned-city chief slots may swap.
        Leader/controller/diplomacy and cityownership are not reset. The outer
        loop atCA58 and later D249/BEC7 are explicitly separate control work.
        """
        ruler_address(ruler)
        if not self.successor_wait_gate(): return {'status': 'waiting', 'wait_cpu': 0xCA7F}
        from .officer_transfer import OfficerTransfer
        chiefs = OfficerTransfer(self.memory, None).repair_ruler_city_chiefs(ruler)
        return {'status': 'city_chiefs_repaired', 'selected_slots': chiefs,
                'next_cpu': 0xCA58, 'outer_ruler_loop_external': True}

    def no_successor_prompt(self, ruler):
        """Bank26 C91B..C939, on FB received by C7E0 (far-render prefix external)."""
        m = self.memory; ruler_address(ruler)
        m[0x42C], m[0x42D] = m[0x38], self.tables.original_leader_ids[ruler]
        queue_message(m, 0xC3); m[0x401], m[0x40C] = 12, 0
        return {'message_id': 0xC3, 'substate': 12, 'ack_not_written': True}

    def successor_timer_step(self, substate):
        """Bank26 CB7F/CB9D. Cooperative calls are not asserted to be video frames.

        sub11 needs240 increments then sub12 another240; sub12 alone needs240.
        INC is byte arithmetic, including a starting255 wrapping to0. Queues are
        requested normally. The actual stores CBBD..CBBF produce acknowledgement1.
        """
        if substate not in (11, 12): raise ValueError('Only proven timer substates11/12')
        m = self.memory; m[0x40C] = (m[0x40C]+1) & 255
        if m[0x40C] < 240: return {'ack_written': False, 'threshold': False}
        if substate == 11:
            m[0x42C] = m[0x27]; queue_message(m, 0xC2)
            m[0x401] = (m[0x401]+1) & 255; m[0x40C] = 0
            return {'ack_written': False, 'threshold': True, 'message_id': 0xC2}
        queue_message(m, 0xBB); m[0x42C] = m[word(m, 0xEE)]
        m[0x401], m[0x40C], m[0x6F8B] = 1, 0, 1
        return {'ack_written': True, 'threshold': True, 'message_id': 0xBB}

    def retire_faction(self, ruler):
        """Bank26 C386..C3BA player/common no-successor notification body.

        Exact controller test is(byte3&3)==3, unlike CA19's whole-byte==3.
        This prefix clears only leaderID; no inferred city/diplomacy transaction.
        """
        m = self.memory; a = ruler_address(ruler)
        m[0x42D] = self.tables.original_leader_ids[ruler]; queue_message(m, 0xC3)
        m[0x42C], m[a] = m[a], 255
        computer = m[a+3] & 3 == 3
        if computer: m[0x4D0] = 0
        m[0x402] = (m[0x402] + (2 if computer else 1)) & 255
        return {'computer_route': computer, 'leader_absent': True,
                'next_phase_0402': m[0x402], 'owners_unchanged': True}

    def human_extinction_end(self):
        """Bank26 C3DB..C41D after idle/input/renderer gate C3C2.

        Stores result substitutions and requests global13 with ending mode0.
        Faction clear already occurred atC386. Global E46A setup is not executed.
        """
        m = self.memory; other = m[0x40C]
        if other != 255: ruler_address(other)
        m[0x42E] = 255 if other == 255 else m[ruler_address(other)]
        put_word(m, 0x42F, m[0x6F00]+100); m[0x431] = 0
        put_word(m, 0x432, m[0x6F01]+1); m[0x434] = 0
        m[0x7A], m[0x541], m[0x4CA] = 13, 0, 0
        return {'global_scene': 13, 'ending_mode': 0, 'renderer_setup_external': True}

    def victory_score(self, ruler_record=None):
        """Bank26 C441..C599; original EE/EF is the leader-record dependency.

        Reads every city's governance and all10 roster slots. No owner, health,
        status or uniqueness filtering. Count is byte; loyalty sum isword.
        Division by0 returnsFFFF for the original16-bit divide. Subsequent total
        is24-bit and ranking later consults score lowbyte only.
        """
        m = self.memory; pointer = word(m, 0xEE) if ruler_record is None else ruler_record
        leader = m[pointer]; m[0x42C] = leader
        loyalty_sum = governance_sum = count = 0
        for city in range(30):
            a = city_address(city); governance_sum = (governance_sum+m[a+11]) & 65535
            for slot in range(17, 27):
                ident = m[a+slot]
                if ident in (255, leader): continue
                loyalty_sum = (loyalty_sum+m[officer_address(ident)+3]) & 65535
                count = (count+1) & 255
        loyalty_component = 65535 if count == 0 else loyalty_sum//count
        roster_component = (count*100)//130
        governance_component = governance_sum//30
        score = ((loyalty_component+roster_component+governance_component) & 0xFFFFFF)//3
        for i in range(3): m[0x435+i] = (score >> (8*i)) & 255
        put_word(m, 0x44C, (m[0x6F00]-89) & 255); m[0x44E] = 0
        put_word(m, 0x42F, m[0x6F00]+100); m[0x431] = 0
        put_word(m, 0x432, m[0x6F01]+1); m[0x434] = 0
        put_word(m, 0x44F, m[0x6F02]+1); m[0x451] = 0
        m[0x401] = (m[0x401]+1) & 255
        return {'leader': leader, 'loyalty_sum16': loyalty_sum, 'count8': count,
                'governance_sum16': governance_sum,
                'components': [loyalty_component, roster_component, governance_component],
                'score24': score, 'rank_uses_lowbyte': score & 255}

    def best_intellect_for_summary(self):
        """Bank26 C626..C67B, current-owner cities, all slots; later ties win."""
        m = self.memory; ruler = m[0x6F03]; ruler_address(ruler)
        chosen = best = 0
        for city in range(30):
            a = city_address(city)
            if m[a] & 7 != ruler: continue
            for slot in range(17, 27):
                ident = m[a+slot]
                if ident == 255: continue
                value = m[officer_address(ident)+2]
                if value >= best: best, chosen = value, ident
        m[0x10], m[0x11] = chosen, best
        return {'officer_id': chosen, 'intellect': best}

    def accept_victory_summary(self):
        """Bank26 C606..C624 after message/input gate, not before it."""
        m = self.memory; low = m[0x435]; mode = 1 if low >= 70 else 2 if low >= 40 else 3
        m[0x7A], m[0x541], m[0x4C9], m[0x4CA] = 13, mode, 0, 0
        return {'global_scene': 13, 'ending_mode': mode, 'score_lowbyte': low,
                'renderer_setup_external': True}

    def ending_credits_roster(self):
        """Bank24 D9DE..DA40, including original byte index/wrap and aliases.

        BeginsFE, leader; visits all30x10 entries, including duplicate IDs. The
        buffer has no300-entry bound. Byte index can wrap and overwrite earlier
        bytes, including leader substitution0411. Do not replace with a deduped
        or safely expanded list: abnormal crowded fixtures expose actual aliases.
        """
        m = self.memory; m[0x410], m[0x411] = 254, m[0x42C]; index = 2
        appended = 0
        for city in range(30):
            a = city_address(city)
            for slot in range(17, 27):
                ident = m[a+slot]
                if ident == 255 or ident == m[0x411]: continue
                m[0x410+index] = ident; index = (index+1) & 255; appended += 1
        m[0x410+index] = 254; index = (index+1) & 255; m[0x410+index] = 255
        m[0x40C] = m[0x40D] = m[0x401] = 0
        m[0x543], m[0x542] = 192, 6; queue_message(m, 0xF1)
        return {'appended': appended, 'final_ff_index8': index,
                'original_unbounded_byte_buffer': True}

    def ending_loss_exit(self):
        """Bank24 D72A..D754, after animation marker04CB=FE.

        If6F43==0, A requests reset. Nonzero6F43 allows continuation restoring
        0400/0401 from0472/0473 and global1. This does not
        revive a leader or neutralize cities.
        """
        m = self.memory
        if not m[0x81] & 1: return {'action': 'wait'}
        if m[0x6F43] == 0: return {'action': 'reset', 'boundary_cpu': 0xE000}
        m[0x6F43] = 0; m[0x400], m[0x401] = m[0x472], m[0x473]
        m[0x402], m[0x7A] = 0, 1
        return {'action': 'restore_parent', 'global_scene': 1}


ENDING_FIELDS = {'global_007a': 0x7A, 'mode_0541': 0x541, 'subphase_0542': 0x542,
                 'display_row_04c9': 0x4C9, 'animation_04ca': 0x4CA,
                 'sprite_marker_04cb': 0x4CB, 'clock_lo_04cd': 0x4CD,
                 'clock_hi_04ce': 0x4CE, 'continuation_6f43': 0x6F43}


def _ending_snapshot(memory):
    return {name: memory[address] for name, address in ENDING_FIELDS.items()}


class _EndingExecutor(BattleStateMachine):
    def external(self, item, target, return_pc, kind):
        self.events.append({'call_pc': item['pc'], 'target': target, 'kind': kind,
                            'control': _ending_snapshot(self.memory),
                            'registers': vars(self.registers).copy(),
                            'inline_target': item.get('inline_target')})
        if self.hooks is None: raise UnresolvedDependency(target, item['pc'], kind)
        self.hooks(self, target, return_pc, kind)


class EndingControl:
    """Bounded pair23/24 NMI8 controller D693, modes0541=0..5.

    Original globalE46A prelude/PPU/NMI is excluded. Caller maps pair23/24 and
    preparesE1..E3/OAM/renderer context; F25F in D693 selects physicaldata6.
    External graphics/farbank/reset services are explicit hooks, never no-op.
    """
    def __init__(self, memory, hooks=None, program=None):
        if program is None:
            program = json.loads((ROOT/'analysis/phase6/factions/ending-program.json').read_text())
        self.memory = memory; self.machine = _EndingExecutor(memory, hooks, program)

    def run_entry(self, entry=0xD693, **kwargs):
        before = _ending_snapshot(self.memory)
        result = self.machine.run_entry(entry, **kwargs)
        result.update(before=before, after=_ending_snapshot(self.memory),
                      control_fields=dict(ENDING_FIELDS))
        return result

    def step(self, **kwargs): return self.run_entry(**kwargs)

    @property
    def registers(self): return self.machine.registers

    @property
    def executed(self): return self.machine.executed
