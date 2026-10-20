"""Readable memory effects where the NMI battlefield consumes tactical proposals.

These are bounded suffixes of bank12, not a graphics queue or an NMI emulator.
The caller must perform each preceding real renderer request. No readiness or
acknowledgement flag is manufactured. Direction and tactic IDs are separate
encodings even though both occupy6F8D in different proposal states.
"""
from dataclasses import dataclass
from enum import IntEnum
import hashlib
from .game_enums import ROM_SHA256, tactic_name


class ProposalKind(IntEnum):
    MOVE = 0
    ATTACK = 1
    TACTIC = 2
    NO_ACTION = 3
    WITHDRAW = 4


@dataclass(frozen=True)
class TacticalExchangeData:
    route_substates: bytes

    @classmethod
    def from_rom(cls, rom):
        if hashlib.sha256(rom).hexdigest() != ROM_SHA256:
            raise ValueError('Wrong tactical exchange ROM identity')
        offset = 16 + 12 * 8192 + 0xBF14 - 0xA000
        table = bytes(rom[offset:offset + 5])
        if table != bytes((3, 5, 8, 12, 13)):
            raise ValueError('Wrong proposal route table')
        return cls(table)


class TacticalBattleBridge:
    def __init__(self, memory, data):
        self.memory, self.data = memory, data

    def proposal(self):
        """Inspect raw proposal fields without executing an action."""
        m = self.memory
        status, action = m[0x6F8F], m[0x6F8D]
        names = {0: 'move', 1: 'attack', 2: 'tactic', 3: 'no_action', 4: 'withdraw'}
        result = {'request_6f8b': m[0x6F8B], 'actor_slot': m[0x6F8C],
                  'kind_code': status, 'kind': names.get(status, 'secondary_or_unclassified'),
                  'action_raw': action, 'target_raw': m[0x6F8E],
                  'movement_cost': m[0x6F97], 'ap': m[0x505]}
        if status == ProposalKind.MOVE:
            result['direction'] = ('up', 'down', 'left', 'right')[action & 3]
        elif status == ProposalKind.TACTIC:
            result['tactic'] = tactic_name(action) if action < 16 else None
        elif status == ProposalKind.WITHDRAW:
            result['destination_city_raw'] = action
        return result

    def request_decision(self):
        """BEA6..BEB9: negative0087 requests phase0; does not force0087."""
        m = self.memory
        if not m[0x87] & 128:
            return {'requested': False}
        m[0x6F8B] = m[0x6F8D] = m[0x6F8E] = 0
        m[0x501] = (m[0x501] + 1) & 255
        return {'requested': True, 'battle_substate': m[0x501]}

    def route_proposal(self):
        """BF01..BF0A, before the no-action notice request atBF0E.

        This function corresponds only to the table read/write prefix. It
        neither polls6F8B nor centres the camera in precedingBEBA..BF00.
        """
        m = self.memory
        kind = m[0x6F8F]
        if not 0 <= kind < len(self.data.route_substates):
            raise ValueError('Only proposal kinds0..4 have a proven route entry')
        m[0x501] = self.data.route_substates[kind]
        return {'battle_substate': m[0x501], 'notice_request_pending': kind == 3}

    def commit_movement_coordinates(self):
        """BF26..BF7B after the real BF1F graphics request, excluding AP cost.

        Exact byte wrap and skipped row15 are retained. Even a horizontal
        move at invalid storedY15 changes it to16, as the original suffix does.
        """
        m = self.memory
        slot = m[0x509]
        if not 0 <= slot < 20:
            raise ValueError('Movement suffix requires a unit slot0..19')
        direction = m[0x6F8D]
        delta = 1 if direction & 1 else 255
        m[0] = m[1] = 0
        m[2] = delta
        m[((direction >> 1) & 1) ^ 1] = delta
        m[0x600 + slot] = (m[0x600 + slot] + m[0]) & 255
        y = (m[0x614 + slot] + m[1]) & 255
        if y == 15:
            y = (y - 1 if m[1] & 128 else y + 1) & 255
        m[0x614 + slot] = y
        m[0x501] = (m[0x501] + 1) & 255
        return {'slot': slot, 'x': m[0x600 + slot], 'y': y,
                'battle_substate': m[0x501], 'graphics_request_executed_here': False}

    def apply_movement_cost(self):
        """BF83..BF97 after BF80's real graphics request; no scene tick."""
        m = self.memory
        m[0x505] = (m[0x505] - m[0x6F97]) & 255
        m[0x500], m[0x501] = 4, 2
        return {'ap': m[0x505], 'battle_state': 4, 'battle_substate': 2,
                'graphics_request_executed_here': False}

    def request_secondary(self):
        """A51F..A534: movement controller requests B933 only when6F8B=FF."""
        m = self.memory
        if m[0x6F8B] != 255:
            return {'requested': False}
        m[0x6F8B], m[0x6F8C] = 1, m[0x509]
        m[0x501] = (m[0x501] + 1) & 255
        return {'requested': True, 'actor_slot': m[0x6F8C],
                'battle_substate': m[0x501]}
