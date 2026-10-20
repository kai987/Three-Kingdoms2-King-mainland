"""Readable behavior recovered from this ROM's tactical battle machine code.

This is reconstructed analysis source, not the original game source and not a
complete battle engine. CPU addresses require the physical PRG bank listed in
ROUTINES. The labels for officer fields come from the ROM display template;
the sixteen strategy names are bound to their real menu/dispatch IDs.
"""
from dataclasses import dataclass
from .game_algorithms import PermutationRng
from .game_enums import Tactic, tactic_name

TACTIC_ENTRY_POINTS = (0xB062,0xB0DD,0xB155,0xB17A,0xB1D5,0xB243,
                      0xB062,0xB2CD,0xB31C,0xB3B6,0xB3D0,0xB42A,
                      0xB466,0xB4B8,0xB50C,0xB5A6)
DAMAGE_PREFIX_TACTICS = {0xB070:Tactic.FIRE_PLAN,0xB0EB:Tactic.PITFALL,
                         0xB188:Tactic.INTERCEPTION,0xB1E3:Tactic.DISTURB_WATER,
                         0xB4C6:Tactic.REPEATING_CROSSBOW,0xB55C:Tactic.RAID_FIRE}

ROM_SHA256 = "26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82"
ROUTINES = {
    "strategy_dispatch": (12, 0xB02B, 0x1903B),
    "grid_distance": (12, 0xB860, 0x19870),
    "strategy_gate": (12, 0xB7BE, 0x197CE),
    "conversion_gate": (12, 0xB72B, 0x1973B),
    "troop_loss": (12, 0xB68B, 0x1969B),
    "health_loss_core": (12, 0xB5D8, 0x195E8),
    "experience_from_accumulated_loss": (15, 0xD7FB, 0x1F80B),
    "damage_B070": (12, 0xB070, 0x19080),
    "damage_B0EB": (12, 0xB0EB, 0x190FB),
    "damage_B188": (12, 0xB188, 0x19198),
    "damage_B1E3": (12, 0xB1E3, 0x191F3),
    "damage_B4C6": (12, 0xB4C6, 0x194D6),
    "damage_B55C": (12, 0xB55C, 0x1956C),
    "duel_parameter_seed": (23, 0xB230, 0x2F240),
    "duel_strike_sample": (23, 0xBA15, 0x2FA25),
    "duel_health_strike": (23, 0xBB5B, 0x2FB6B),
    "duel_strike_effect": (23, 0xB8D3, 0x2F8E3),
    "duel_attack_parameters": (15, 0xC991, 0x1E9A1),
}


@dataclass(frozen=True)
class Officer:
    """Twelve raw officer bytes. Keep unrelated packed bits intact by default."""
    raw: bytes

    def __post_init__(self):
        if len(self.raw) != 12:
            raise ValueError("An officer record has exactly twelve bytes")

    @property
    def health(self): return self.raw[0]
    @property
    def martial(self): return self.raw[1]
    @property
    def intelligence(self): return self.raw[2]
    @property
    def loyalty(self): return self.raw[3]
    @property
    def virtue(self): return self.raw[4]
    @property
    def experience(self): return self.raw[6] | self.raw[7] << 8
    @property
    def troops(self): return self.raw[8] | (self.raw[9] & 3) << 8
    @property
    def level_index(self): return self.raw[11] >> 4


@dataclass(frozen=True)
class GateResult:
    passed: bool
    distance: int
    threshold: int | None
    sample: int | None


def grid_distance(actor_xy, target_xy):
    """$B860: max axis distance, after removing unused y row 15.

    This reproduces byte inputs even outside the normal battlefield bounds.
    Row values >=16 are reduced by one; value 15 is left untouched by the ROM.
    """
    ax, ay = (v & 255 for v in actor_xy)
    tx, ty = (v & 255 for v in target_xy)
    ay -= ay >= 16
    ty -= ty >= 16
    return max(abs(ax - tx), abs(ay - ty))


def strategy_gate(actor: Officer, target: Officer, actor_xy, target_xy,
                  phase_type: int, environment: int, rng: PermutationRng):
    """$B7BE: shared success gate for many strategy effects.

    The meanings of phase_type ($050F) and environment ($6F02) are not claimed.
    RNG draws are full permutation bytes, rejecting >=100; no draw at range>=6.
    Arithmetic deliberately preserves the ROM's byte wraps and sign test.
    """
    distance = grid_distance(actor_xy, target_xy)
    if distance >= 6:
        return GateResult(False, distance, None, None)
    knowledge_difference = max(actor.intelligence - target.intelligence, 0)
    level_difference = 2 * max(actor.level_index - target.level_index, 0)
    bonus = 10
    if phase_type & 255 == 3:
        bonus = 10 if environment & 255 == 1 else 20 if environment & 255 == 2 else 5
    # Table bytes $B85A: 0F 0A 05 00 FB F6. Negative-looking table entries
    # remain bytes while the additions run; only the final sign is tested.
    value = ([15, 10, 5, 0, 251, 246][distance] + knowledge_difference) & 255
    value = (value + level_difference) & 255
    value = (value + bonus) & 255
    if value & 128:
        value = 0
    threshold = max(5, min(95, value))
    sample = rng.bounded(100)
    return GateResult(sample < threshold, distance, threshold, sample)


def conversion_gate(actor: Officer, target: Officer, actor_xy, target_xy,
                    rng: PermutationRng):
    """$B72B: gate used before $B32A flips target side bit ($0628 ^= $80).

    This recovers the success test, not the later ownership/list bookkeeping.
    Target loyalty >=71 and distance >=6 fail without consuming RNG.
    """
    distance = grid_distance(actor_xy, target_xy)
    if distance >= 6 or target.loyalty >= 71:
        return GateResult(False, distance, None, None)
    base = 60 if target.loyalty < 31 else 30 if target.loyalty < 51 else 10
    level_bonus = 2 * max(actor.level_index - target.level_index, 0)
    quotient = ((actor.intelligence + actor.virtue) & 255) // 10
    first = quotient + base
    # The second ADC retains carry from the first ADC (normally zero).
    threshold = ((first & 255) + level_bonus + (first > 255)) & 255
    sample = rng.bounded(100)
    return GateResult(sample < threshold, distance, threshold, sample)


def experience_from_accumulated_loss(actor: Officer, accumulated_loss: int):
    """Bank15 $D7FB via bank14 $A006: add floor(counter/2) experience.

    Addition wraps at 16 bits BEFORE capping at 49,999. At most one level is
    granted per call. Level threshold uses the uncapped wrapped sum. The high
    nibble is the zero-based level index, not a display-level assertion.
    Return (updated officer, new packed-level marker or zero).
    """
    raw = bytearray(actor.raw)
    total = (actor.experience + ((accumulated_loss & 65535) >> 1)) & 65535
    capped = min(total, 49999)
    raw[6], raw[7] = capped & 255, capped >> 8
    level = actor.level_index
    thresholds = (1000, 2000, 3500, 5000, 7500, 10000, 15000)
    marker = 0
    if level < 7 and total >= thresholds[level]:
        marker = (level + 1) << 4
        raw[11] = (raw[11] & 15) | marker
        war = raw[1]
        increment = 6 if war < 51 else 5 if war < 71 else 4 if war < 81 else 2 if war < 90 else 0
        raw[1] = (war + increment) & 255
    return Officer(bytes(raw)), marker


def troop_loss(actor: Officer, target: Officer, requested_loss: int,
               accumulated_loss: int = 0, *, same_record: bool = False):
    """$B68B, including real $EE07 far call to experience helper.

    Subtract with saturation; add actual loss to the u16 display accumulator.
    The helper awards experience from the NEW ACCUMULATOR on every call.
    The ROM writes byte9 from the remaining high byte, clearing any upper bits.
    By default actor and target represent distinct SRAM records. Pass same_record
    explicitly when both IDs select one address; its HP/experience changes then
    share that record. Return (updated actor, updated target, applied loss,
    accumulator, marker).
    """
    if same_record and actor.raw != target.raw:
        raise ValueError("Aliased actor/target must begin as the same record")
    loss = min(target.troops, requested_loss & 65535)
    remaining = target.troops - loss
    raw = bytearray(target.raw)
    raw[8], raw[9] = remaining & 255, remaining >> 8
    accumulated_loss = (accumulated_loss + loss) & 65535
    target = Officer(bytes(raw))
    actor, marker = experience_from_accumulated_loss(target if same_record else actor, accumulated_loss)
    return actor, actor if same_record else target, loss, accumulated_loss, marker


def health_loss_core(target: Officer, requested_loss: int):
    """$B5D8..$B610 core, before death/removal dependencies.

    Saturating byte subtraction. Zero health sets record byte11 low bits to 3.
    Removal, map updates and two subsequent far calls are outside this function.
    """
    loss = min(target.health, requested_loss & 255)
    raw = bytearray(target.raw)
    raw[0] -= loss
    if raw[0] == 0:
        raw[11] |= 3
    return Officer(bytes(raw)), loss, raw[0] == 0


def strategy_damage_amount(entry: int, actor: Officer, rng: PermutationRng):
    """Six actual successful-effect prefixes, selected by CPU entry address.

    These formulas do not include the preceding probability gate. Names such as
    fire/rockfall are deliberately not inferred from familiar game rules.
    All results are before the target loss helper clamps to remaining troops/HP.
    """
    level = actor.level_index
    if entry == 0xB070:
        quotient_low = (actor.intelligence * (rng.bounded(5) + 9) // 10) & 255
        return ((10 * level + quotient_low) & 255) + 30
    if entry == 0xB0EB:
        base = (level + ((actor.martial + actor.intelligence) & 255) // 10) & 255
        return (base * (rng.bounded(3) + 5) // 10) & 255
    if entry == 0xB188:
        return actor.martial * (rng.bounded(7) + 14) // 10
    if entry == 0xB1E3:
        return actor.intelligence * (rng.bounded(7) + 20) // 10 + level + 7
    if entry == 0xB4C6:
        return rng.bounded(200) + 150 + (((actor.martial + actor.intelligence) & 255) >> 1)
    if entry == 0xB55C:
        return actor.intelligence * (rng.bounded(6) + 30) // 10
    raise ValueError(f"Unrecovered effect entry ${entry:04X}")


def duel_parameter_seed(left: Officer, right: Officer, equipment_table: bytes,
                        rng: PermutationRng):
    """Bank23 $B230: derive two duel bytes and choose the greater index.

    Table is the exact 32 bytes at bank23 $B2C0: 24 weapon and 8 armor corrections.
    Equipment names come from the separate field/UI evidence. This is not claimed to be a
    damage or initiative formula: the later code uses these internal parameters
    for additional checks. All equipment indices, even 24..31, follow ROM reads.
    Return (base pair at $04B3/4, randomized pair at $04BD/E, selected index).
    """
    if len(equipment_table) != 32:
        raise ValueError("Expected the thirty-two ROM correction bytes")
    bases, randomized = [], []
    for officer in (left, right):
        packed = officer.raw[10]
        correction = (equipment_table[packed & 31] + equipment_table[24 + (packed >> 5)]) & 255
        value = ((((officer.health + officer.martial) & 255) // 10) + 20 - correction) & 255
        bases.append(value)
        randomized.append((value + rng.bounded(11)) & 255)
    return tuple(bases), tuple(randomized), 0 if randomized[0] >= randomized[1] else 1


def duel_strike_sample(attack_base: int, attack_modifier: int,
                       opposing_modifier: int, rng: PermutationRng):
    """Bank23 $BA15: produce hit-quality roll and provisional strike amount.

    Inputs correspond to selected $04C1[Y], $0570[Y], $056E[Y^1]: the martial-
    derived attack base, weapon bonus and opposing armor modifier produced by
    bank15 $C926/$C991. Equipment identity comes from the separate UI evidence.
    First RNG draw is <100; second is a low-nibble rejection sample <11.
    The final signed-byte BPL test is intentionally not Python max(int, 0).
    """
    roll = rng.bounded(100)
    base = (((attack_base & 255) + (attack_modifier & 255)) & 255) >> 1
    value = (base - (opposing_modifier & 255)) & 255
    value = (value + rng.bounded(11) - 5) & 255
    return roll, 0 if value & 128 else value


def duel_attack_parameters(officer: Officer, weapon_table: bytes,
                           armor_table: bytes, rng: PermutationRng):
    """Bank15 $C991: martial attack base plus equipment modifiers.

    weapon_table is 32 contiguous bytes at $CA1F (24 weapons then 8 armor
    bytes), because low-five-bit values 24..31 literally index the latter data.
    armor_table is the eight bytes at $CA37. Normal weapon IDs are 0..23.
    Producer $C926 stores returned A/Y/X in $04C1/$0570/$056E for one side.
    """
    if len(weapon_table) != 32 or len(armor_table) != 8:
        raise ValueError("Expected exact bank15 lookup bytes")
    martial = officer.martial
    coefficient = 45 if martial < 65 else 50 if martial < 80 else 55 if martial < 87 else 60 if martial < 92 else 65 if martial < 97 else 70
    quotient = martial * coefficient // 100
    base = (quotient + 9) & 255
    random_subtrahend = rng.bounded(9)
    base = (base - random_subtrahend) if base >= random_subtrahend else 1
    packed = officer.raw[10]
    return base, weapon_table[packed & 31], armor_table[packed >> 5]


def duel_health_strike(target: Officer, rng: PermutationRng):
    """Bank23 $BB5B: a duel outcome removes a random 5..14 body points.

    Unlike $B5D8, this path uses a signed BPL test after wrapped subtraction.
    HP outside normal 0..100 can therefore produce non-saturating outcomes.
    The reported damage byte remains 5..14 even when less HP was available.
    Result/death dialogue and later battle resolution are outside this helper.
    """
    requested = rng.bounded(10) + 5
    remainder = (target.health - requested) & 255
    raw = bytearray(target.raw)
    raw[0] = 0 if remainder & 128 else remainder
    return Officer(bytes(raw)), requested


def duel_strike_effect(attack_base: int, attack_modifier: int, opposing_modifier: int,
                       actor_health: int, target_health: int, boost_byte: int,
                       category: int, threshold: int, rng: PermutationRng):
    """Bank23 $B8D3..$B9A4, including $BA15 and message selection.

    Health here means the duel's temporary $04B1[2] buffers, initially copied
    from officer body points at $B160. This function does not assert that they
    have already been copied back to SRAM. Category and boost flag meanings are
    left neutral; outcomes/messages are identified by their exact ROM bytes.
    """
    roll, damage = duel_strike_sample(attack_base, attack_modifier, opposing_modifier, rng)
    actor_health &= 255
    target_health &= 255
    if boost_byte & 127:
        roll = (roll + 20) & 255
        # ASL and ADC both use an 8-bit accumulator before repeated subtraction.
        damage = (damage + (((3 * damage) & 255) // 10)) & 255
    category &= 255
    if category == 0:
        if roll >= 100:
            return {"actor_health":actor_health,"target_health":target_health,"message":0x25,"reported_damage":None,"roll":roll}
        damage //= 3
    elif category == 6:
        if roll < 30:
            damage = (2 * damage) & 255
        else:
            while True:
                self_loss = rng.next_u8() & 31
                if self_loss < 21:
                    break
            remainder = (actor_health - (self_loss + 10)) & 255
            actor_health = 0 if remainder & 128 else remainder
            return {"actor_health":actor_health,"target_health":target_health,"message":0x25,"reported_damage":None,"roll":roll}
    elif roll >= (threshold & 255):
        return {"actor_health":actor_health,"target_health":target_health,"message":0x25,"reported_damage":None,"roll":roll}
    if damage == 0 or damage & 128:
        return {"actor_health":actor_health,"target_health":target_health,"message":0x39,"reported_damage":None,"roll":roll}
    target_health = max(target_health - damage, 0)
    return {"actor_health":actor_health,"target_health":target_health,"message":0x22,"reported_damage":damage,"roll":roll}
