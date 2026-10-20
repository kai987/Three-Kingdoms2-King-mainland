"""Small independent terrain models recovered from the supplied ROM.

These are reconstructed rules, not the original source. Class 1 deliberately
has no formal name: its original map pixels and mechanical behavior are known,
but a terrain-name string or an original manual legend has not been linked.
The AI movement selector reproduces a repeated-byte read in the original code.
It must not be replaced by the player's troop-cache rule.
"""
from dataclasses import dataclass
import hashlib

ROM_SHA256 = '26c8d921ff5c208191f136480bcd8d7e89c2e4ed40a0ac7b51482bcb52fe2b82'
CLASS1_FORMAL_NAME = None
CLASS1_RAW_TILES = (0x01, 0x6A, 0x6B, 0x6C, 0x6D, 0x70, 0x74)


@dataclass(frozen=True)
class TerrainSemanticsData:
    """Two exact 7×4 cost tables. Row 6 exists but is not a normalized class."""
    first: tuple
    second: tuple

    @classmethod
    def from_rom(cls, rom: bytes):
        if hashlib.sha256(rom).hexdigest() != ROM_SHA256:
            raise ValueError('This reconstruction is pinned to the supplied ROM')
        def rows(offset):
            return tuple(tuple(rom[offset+4*i:offset+4*i+4]) for i in range(7))
        # Physical bank 8 A7CD/A7E9 and bank 12 A823/A83F, respectively.
        first, second = rows(0x107DD), rows(0x107F9)
        if (first, second) != (rows(0x18833), rows(0x1884F)):
            raise ValueError('AI/player original cost tables are no longer equal')
        return cls(first, second)


def _quote(terrain_class, officer_flags, first_table, action_points, data):
    if not 0 <= terrain_class <= 5:
        raise ValueError('Normalized original playable terrain class must be 0..5')
    affinity = ((officer_flags & 255) >> 2) & 3
    table = data.first if first_table else data.second
    cost = table[terrain_class][affinity]
    ap = action_points & 255
    remaining = (ap-cost) & 255
    return {
        'terrain_class': terrain_class,
        'affinity': affinity,
        'affinity_supported': affinity < 3,
        'first_table': bool(first_table),
        'table_index': terrain_class*4+affinity,
        'cost': cost,
        'remaining_ap': remaining,
        'carry': ap >= cost,
        'negative': bool(remaining & 128),
        'zero': remaining == 0,
        'overflow': bool(((ap ^ cost) & (ap ^ remaining)) & 128),
    }


def ai_movement_quote(terrain_class: int, officer_flags: int,
                      troops_low_byte: int, action_points: int, *, data):
    """Bank 8 A78C..A7CC, after B6E5 has normalized the target terrain.

    A7A8 sets Y=8. A7AA reads officer byte 8, subtracts 0x59, then A7AF
    reads the SAME byte at Y=8 and subtracts 2 with the prior carry.
    Hence BCC selects the second table exactly when byte8<3. Byte9 and
    RAM 063C do not participate. X returns the table index; Y the cost;
    A and NZVC return the final action-point subtraction. This API quotes
    that calculation; pointer scratch and caller map lookup remain external.
    """
    low = troops_low_byte & 255
    prior_carry = low >= 0x59
    second_subtraction = low-2-(not prior_carry)
    result = _quote(terrain_class, officer_flags, second_subtraction >= 0,
                    action_points, data)
    result.update(selector_byte8=low, selector_reads_byte9=False,
                  return_x=result['table_index'], return_y=result['cost'])
    return result


def player_movement_quote(terrain_class: int, officer_flags: int,
                          hundred_troops_cache: int, action_points: int, *, data):
    """Bank 12 A7E7..A822. The player uses cached 063C[slot]>=6.

    DB03 populates this cache with (officer troop word &1023)//100.
    X returns cost, unlike the AI entry, where X returns the table index.
    """
    cache = hundred_troops_cache & 255
    result = _quote(terrain_class, officer_flags, cache >= 6, action_points, data)
    result.update(selector_cache=cache, return_x=result['cost'])
    return result


def class1_profile(*, data):
    """Known mechanics without assigning a guessed Japanese terrain name."""
    return {
        'class': 1, 'formal_name': CLASS1_FORMAL_NAME,
        'formal_name_status': 'unconfirmed', 'raw_tiles': CLASS1_RAW_TILES,
        'normalization': 'preserved as 1 in both player DB46 and AI B6E5',
        'first_table_costs': data.first[1], 'second_table_costs': data.second[1],
        'supported_affinities': (0, 1, 2), 'undefined_affinity': 3,
        'pure_terrain_gates': {
            'fire_0_target': False, 'trap_virtual_raid_1_2_3_target': False,
            'water_4_10_12_target': False, 'castle_6_target': False,
            'mutual_attack_7_target': False, 'conversion_8_target': True,
            'rock_9_target_or_actor': False, 'ambush_11_actor': False,
            'crossbow_13_target_if_actor_castle': True,
            'inferno_14_target': True, 'player_qimen_15_target': True,
        },
        'effect_terrain_gates': {
            'water_immobilization_B3FE': False,
            'water_damage_B494': False,
            'inferno_damage_B538': True,
            'area_neighbor_discovery_B8FA': True,
        },
        'gate_scope': 'terrain component only; adjacency, side, stats and resources still apply',
    }
