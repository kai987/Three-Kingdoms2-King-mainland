"""Readable behavior recovered from this ROM's bank 8/9 tactical decision code.

Not original source and not a complete AI engine. Algorithms preserve observed
6502 unsigned-byte/carry details; action numbers retain their encoding and now
have names verified by the UI/action-table link. All addresses refer to ROM
SHA-256 26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82.
"""
from dataclasses import dataclass
from typing import Callable, Sequence
from .game_enums import tactic_name

ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
ROUTINES = {
    'orthogonal_neighbors': {'bank': 8, 'cpu': 0xA837, 'file': 0x10847, 'end_cpu': 0xA8A8},
    'nearby_candidates': {'bank': 8, 'cpu': 0xA8D3, 'file': 0x108E3, 'end_cpu': 0xA944},
    'opposing_side_marker': {'bank': 8, 'cpu': 0xA944, 'file': 0x10954, 'end_cpu': 0xA95C},
    'knowledge_tier': {'bank': 8, 'cpu': 0xA965, 'file': 0x10975, 'end_cpu': 0xA986},
    'plan_basic_tactic': {'bank': 8, 'cpu': 0xA95C, 'file': 0x1096C, 'end_cpu': 0xA9CF},
    'choose_basic_action': {'bank': 8, 'cpu': 0xA9CF, 'file': 0x109DF, 'end_cpu': 0xAAF8},
    'special_ai_gate': {'bank': 8, 'cpu': 0xAAF8, 'file': 0x10B08, 'end_cpu': 0xAB1F},
    'choose_special_action': {'bank': 8, 'cpu': 0xAB68, 'file': 0x10B78, 'end_cpu': 0xAC31},
    'special_officer_whitelist': {'bank': 8, 'cpu': 0xAC31, 'file': 0x10C41, 'end_cpu': 0xAC4D},
    'action_suitability': {'bank': 8, 'cpu': 0xAC7B, 'file': 0x10C8B, 'end_cpu': 0xAE93,
                           'inline_pointer_table_cpu': 0xACAE, 'inline_pointer_table_size': 32},
    'rank_enemy_candidates': {'bank': 8, 'cpu': 0xAE93, 'file': 0x10EA3, 'end_cpu': 0xAF0D},
    'ai_rng_next': {'bank': 8, 'cpu': 0xB5D5, 'file': 0x115E5, 'end_cpu': 0xB5E5},
}
# CPU $AC65..$AC79, ROM file $010C75..$010C89; final $FF terminator
SPECIAL_OFFICERS = (161, 99, 167, 22, 196, 219, 234, 107, 206, 235, 183,
                    24, 55, 112, 213, 110, 103, 197, 86, 93, 109)


def opposing_side_marker(current_side_flag: int, target_side_flag: int) -> int:
    """$A944: same sign-bit -> 0, opposite sign-bit -> $80.

    Input flags are RAM $0504 and $0628[slot]. Only bit7 is inspected.
    """
    return (current_side_flag ^ target_side_flag) & 0x80


def normalize_y(value: int) -> int:
    """$A8DC: the stored Y coordinate skips a row at $10."""
    value &= 255
    return value-1 if value >= 16 else value


def abs_signed_u8_difference(a: int, b: int) -> int:
    """Exact SBC/BPL/EOR/ADC sequence; usual |a-b| for valid small coordinates."""
    delta=(a-b)&255
    return (-delta)&255 if delta&128 else delta


def nearby_candidates(actor_slot: int, active_officer_ids: Sequence[int],
                      xs: Sequence[int], ys: Sequence[int], side_flags: Sequence[int],
                      current_side_flag: int, radius: int) -> list[int]:
    """$A8D3: populate the 20-byte $6FC9 mask/distance work array.

    A valid slot has $0664[slot] != $FF. Both axis deltas must be <= radius;
    opposing slots receive bit7. Exact carry quirk: CMP on the Y delta leaves
    carry set when dy==radius, then ADC adds an extra 1 to dx+dy. This is not
    a generic Manhattan-distance function. Later ranking keeps bit7 slots.
    """
    if any(len(v)!=20 for v in (active_officer_ids,xs,ys,side_flags)):
        raise ValueError('ROM work arrays contain exactly 20 slots')
    radius &= 255
    ax=xs[actor_slot]&255; ay=normalize_y(ys[actor_slot])
    out=[]
    for slot in range(20):
        value=0
        if active_officer_ids[slot]&255 != 255:
            dx=abs_signed_u8_difference(xs[slot]&255,ax)
            if dx<=radius:
                dy=abs_signed_u8_difference(normalize_y(ys[slot]),ay)
                if dy<=radius:
                    value=((dx+dy+int(dy==radius))&255)
                    value |= opposing_side_marker(current_side_flag,side_flags[slot])
        out.append(value)
    return out


def orthogonal_neighbors(slot: int, active_officer_ids: Sequence[int],
                         xs: Sequence[int], ys: Sequence[int], side_flags: Sequence[int],
                         current_side_flag: int) -> tuple[int,int,int,int]:
    """$A837: top, bottom, left, right occupied slots; $FF when empty.

    Every found slot's bit7 uses $A944's classification relative to $0504.
    Coordinate changes wrap to u8, as DEC/INC do in the ROM. The first matching
    active slot wins when coordinates are duplicated.
    """
    x=xs[slot]&255; y=normalize_y(ys[slot]); result=[]
    for dx,dy in [(0,-1),(0,1),(-1,0),(1,0)]:
        tx=(x+dx)&255;ty=(y+dy)&255
        found=255
        for candidate in range(20):
            if active_officer_ids[candidate]&255==255:
                continue
            if xs[candidate]&255==tx and normalize_y(ys[candidate])==ty:
                found=candidate|opposing_side_marker(current_side_flag,side_flags[candidate])
                break
        result.append(found)
    return tuple(result)


def action_suitability(action: int, actor_slot: int, target_slot: int,
                       active_officer_ids: Sequence[int], records: Sequence[Sequence[int]],
                       xs: Sequence[int], ys: Sequence[int], side_flags: Sequence[int],
                       current_side_flag: int, terrain_classes: Sequence[int],
                       reserve_bytes: Sequence[int]) -> bool:
    """$AC7B: all 16 predicates after its $B517 inline pointer dispatch.

    terrain_classes is the output of hardware-bank-dependent $B6E5, whose raw
    classes >=6 are folded to2. Numeric class names stay unassigned here.
    reserve_bytes represents eight bytes at $04D8; only byte0/4 is read.
    Neighbor discovery and field comparisons below are fully recovered.
    """
    action &= 255
    if not 0<=action<16:
        raise ValueError('Confirmed inline table contains 16 predicates')
    def terrain(slot):
        value=terrain_classes[slot]&255
        return 2 if value>=6 else value
    def neighbors(slot):
        return orthogonal_neighbors(slot,active_officer_ids,xs,ys,side_flags,current_side_flag)
    target=records[active_officer_ids[target_slot]&255]
    actor=records[active_officer_ids[actor_slot]&255]
    tt=terrain(target_slot);at=terrain(actor_slot)
    if action==0: return tt in (0,2)
    if action in (1,2,3): return tt in (0,4)
    if action==4: return tt==3
    if action==5: return target_slot in (0,10)
    if action==6:
        return tt==5 and any((n&127)==actor_slot for n in neighbors(target_slot))
    if action==7:
        return tt in (0,4) and any(n!=255 and n&128 for n in neighbors(target_slot))
    if action==8: return tt!=5 and (target[3]&255)<50
    if action==9:
        return at in (4,5) and any((n&127)==target_slot for n in neighbors(actor_slot)) and tt==5
    if action in (10,12):
        return tt==3 and any(n!=255 and n&128 and terrain(n&127)==3 for n in neighbors(target_slot))
    if action==11:
        has_min_troops=(actor[9]&255)!=0 or (actor[8]&255)>=100
        side_offset=4 if current_side_flag&128 else 0
        return at==0 and has_min_troops and (reserve_bytes[side_offset]&255)==255
    if action==13:
        return at==5 and any((n^128)==target_slot for n in neighbors(actor_slot))
    if action==14:
        return tt!=5 and any(n!=255 and n&128 and terrain(n&127)!=5 for n in neighbors(target_slot))
    # Action15 preserves the byte-wise test, not a guessed >=700 u16 threshold.
    # E.g. u16=768 has high>=2 but low=0, so this precise gate rejects it.
    return tt!=5 and ((target[1]&255)>=85 or (target[2]&255)>=85) and (target[9]&255)>=2 and (target[8]&255)>=188


@dataclass(frozen=True)
class RankedCandidates:
    slots: tuple[int,...]
    remaining_pass_counter: int
    passes_executed: int


def rank_enemy_candidates(mask_values: Sequence[int], active_officer_ids: Sequence[int],
                          raw_u16_by_officer: Sequence[int], pass_counter: int) -> RankedCandidates:
    """$AE93: compact negative mask entries; adjacent-swap by raw (+8,+9).

    Next>=current swaps, including ties. That is descending-order bubbling but
    is not stable. $002F is a caller-provided counter that this routine does NOT
    initialize. A counter 0 performs only one pass, potentially leaving the list
    partially sorted; >=candidate_count-2 suffices for complete value ordering.
    Return slots is the exact 20-byte work array including $FF tail entries.
    """
    if len(mask_values)!=20 or len(active_officer_ids)!=20:
        raise ValueError('ROM work arrays contain exactly 20 slots')
    slots=[i for i,v in enumerate(mask_values) if v&128]
    count=len(slots); counter=pass_counter&255; passes=0
    if count>=2:
        while True:
            passes+=1
            for x in range(count-1):
                left=raw_u16_by_officer[active_officer_ids[slots[x]]&255]&65535
                right=raw_u16_by_officer[active_officer_ids[slots[x+1]]&255]&65535
                if right>=left:
                    slots[x],slots[x+1]=slots[x+1],slots[x]
            counter=(counter-1)&255
            if counter&128:
                break
    return RankedCandidates(tuple(slots+[255]*(20-count)),counter,passes)


def knowledge_tier(knowledge: int) -> int:
    """$A965: officer byte+2 (知) determines the basic-action threshold tier."""
    value=knowledge&255
    return 1 if value<40 else 3 if value<60 else 5 if value<75 else 7 if value<85 else 9


def special_ai_gate(knowledge: int, packed_byte11: int) -> bool:
    """$AAF8: special candidate scan needs 知>=92 and experience level>=3."""
    return (knowledge&255)>=92 and ((packed_byte11&255)>>4)>=3


def special_officer_whitelist(officer_id: int, experience_level: int,
                              required_level: int, start_index: int) -> bool:
    """$AC31: level floor, then ID scan from Y to $AC65's $FF terminator."""
    if not 0<=start_index<=len(SPECIAL_OFFICERS):
        raise ValueError('Confirmed whitelist index must be within the terminated table')
    return (experience_level&255)>=(required_level&255) and (officer_id&255) in SPECIAL_OFFICERS[start_index:]


@dataclass
class AiPermutationRng:
    """$B5D5: bank8 copy of the permutation, with its own cursor.

    Table CPU $B5E5, file $0115F5, 256 bytes, identical to fixed $E8BA.
    Cursor is RAM $6F92; fixed-bank RNG uses different cursor addresses.
    """
    table: bytes
    cursor: int=0

    def __post_init__(self):
        if len(self.table)!=256:
            raise ValueError('AI RNG table must have 256 bytes')
        self.cursor &= 255

    def next_u8(self) -> int:
        value=self.table[self.cursor]
        self.cursor=(self.cursor+1)&255
        return value


@dataclass(frozen=True)
class ActionDecision:
    success: bool
    scratch_action: int
    final_status: int
    predicate_requests: tuple[int,...]
    random_samples: tuple[int,...]=()

    @property
    def chosen_tactic_name(self):
        return tactic_name(self.scratch_action) if self.success else None


def choose_basic_action(tier: int, resource: int, target_raw_u16: int,
                        target_condition_byte: int, suitable: Callable[[int],bool],
                        rng_next: Callable[[],int], initial_status: int=0,
                        initial_scratch_action: int=0) -> ActionDecision:
    """$A9CF: exact action-number priority/threshold flow for one target.

    suitable(action) corresponds to $AC7B's environment/neighbor predicates.
    This function recovers the caller's decision sequence; substituting that
    callback does not imply the full game or every predicate has been recovered.
    Return status is unchanged on success, or $6F8F=3 after all choices fail.
    """
    tier &= 255; resource &= 255; condition=target_condition_byte&255
    has_troops=bool(target_raw_u16&65535)
    requests=[]; samples=[]; action=initial_scratch_action&255
    def request(code):
        nonlocal action
        action=code; requests.append(code)
        return bool(suitable(code))
    def result(success):
        return ActionDecision(success,action,initial_status&255 if success else 3,
                              tuple(requests),tuple(samples))
    for code,min_tier,min_resource,needs_troops in [(6,6,8,True),(5,5,8,False),
                                                   (8,8,10,False),(9,9,9,True),
                                                   (7,7,8,True)]:
        if tier>=min_tier and resource>=min_resource and (has_troops or not needs_troops):
            if request(code): return result(True)
    if request(1):
        for _ in range(65536):
            draw=rng_next()&255; samples.append(draw); choice=draw&3
            if choice==0 or choice==3 and not has_troops:
                continue
            if choice==3:
                if tier>=3:
                    action=3
                    if resource>=6: return result(True)
            elif choice==1:
                if tier>=2 and not condition&15:
                    action=2
                    if resource>=4: return result(True)
            else:
                action=1
                if resource>=5: return result(True)
            break
        else:
            raise RuntimeError('Oracle callback never produced an acceptable low-two-bit sample')
    if tier>=4 and has_troops and resource>=7 and request(4): return result(True)
    if has_troops and resource>=6 and request(0): return result(True)
    return result(False)


def choose_special_action(officer_id: int, experience_level: int, resource: int,
                          target_raw_u16: int, target_condition_byte: int,
                          suitable: Callable[[int],bool], initial_status: int=0,
                          initial_scratch_action: int=0) -> ActionDecision:
    """$AB68: whitelist/level-gated actions 10..15, preserving their priority.

    Called by $AAF8's scan only after its 知>=92/level>=3 gate. ID109's name
    pixels are 諸葛亮; only this ID can request action15 here. The names of
    actions 10..15 are bound to menu names in game_enums.py.
    """
    officer_id &= 255; experience_level &= 255; resource &= 255
    condition=target_condition_byte&255; has_troops=bool(target_raw_u16&65535)
    requests=[]; action=initial_scratch_action&255
    def request(code):
        nonlocal action
        action=code; requests.append(code)
        return bool(suitable(code))
    def result(success):
        return ActionDecision(success,action,initial_status&255,tuple(requests))
    if special_officer_whitelist(officer_id,experience_level,3,0):
        if not condition&15 and resource>=9 and request(10): return result(True)
        if resource>=10 and request(11): return result(True)
    if special_officer_whitelist(officer_id,experience_level,4,11) and has_troops:
        if resource>=10 and request(12): return result(True)
        if resource>=8 and request(13): return result(True)
    if special_officer_whitelist(officer_id,experience_level,5,17) and has_troops:
        if resource>=12 and request(14): return result(True)
    if officer_id==109 and experience_level>=6 and not condition&240:
        if resource>=10 and request(15): return result(True)
    return result(False)


@dataclass(frozen=True)
class TacticalPlan:
    success: bool
    action: int
    target_slot: int
    final_status: int
    scratch_action: int
    candidate_slots: tuple[int,...]
    final_pass_scratch: int
    predicate_requests: tuple[tuple[int,int],...]
    random_samples: tuple[int,...]

    @property
    def chosen_tactic_name(self):
        return tactic_name(self.action) if self.success else None


def plan_basic_tactic(actor_slot: int, active_officer_ids: Sequence[int],
                     records: Sequence[Sequence[int]], xs: Sequence[int], ys: Sequence[int],
                     side_flags: Sequence[int], current_side_flag: int,
                     conditions: Sequence[int], resource: int, pass_counter: int,
                     suitable: Callable[[int,int],bool], rng_next: Callable[[],int],
                     initial_action: int=0, initial_target: int=0,
                     initial_status: int=0, initial_scratch_action: int=0) -> TacticalPlan:
    """$A95C: entire basic-tactic candidate/ordering/decision caller pipeline.

    Build radius-5 candidates, rank by raw (+8,+9), then test one target at a
    time using $A9CF's priorities. First successful target writes $6F8D(action),
    $6F8E(target), $6F8F=2. No success writes status3 and keeps the old action
    and target bytes. suitability is still the explicit $AC7B dependency.
    """
    tier=knowledge_tier(records[active_officer_ids[actor_slot]][2])
    masks=nearby_candidates(actor_slot,active_officer_ids,xs,ys,side_flags,current_side_flag,5)
    raw_values=[(r[8]&255)+256*(r[9]&255) for r in records]
    ranked=rank_enemy_candidates(masks,active_officer_ids,raw_values,pass_counter)
    scratch=initial_scratch_action&255; status=initial_status&255
    pass_scratch=ranked.remaining_pass_counter; requests=[]; samples=[]
    for position,target in enumerate(ranked.slots):
        if target==255:
            break
        officer=active_officer_ids[target]&255
        if officer==255:
            continue
        pass_scratch=position
        def predicate(code):
            requests.append((target,code))
            return suitable(target,code)
        decision=choose_basic_action(tier,resource,raw_values[officer],conditions[target],
                                     predicate,rng_next,status,scratch)
        samples.extend(decision.random_samples)
        scratch=decision.scratch_action;status=decision.final_status
        if decision.success:
            return TacticalPlan(True,scratch,target,2,scratch,ranked.slots,
                                pass_scratch,tuple(requests),tuple(samples))
    return TacticalPlan(False,initial_action&255,initial_target&255,3,scratch,
                        ranked.slots,pass_scratch,tuple(requests),tuple(samples))
