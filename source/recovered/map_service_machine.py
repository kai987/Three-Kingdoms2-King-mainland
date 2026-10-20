"""Thin entry wrapper for the independently bounded bank8/9 village services.

The 10 substate bodies are lifted control/ALU/memory IR. This is an explicit
C0BB entry API; it does not implement the caller's EE07 bank/return protocol.
"""
import json
from pathlib import Path
from .battle_state_machine import BattleStateMachine,Registers,InvalidState,UnresolvedDependency

ROOT=Path(__file__).resolve().parents[2]

class MapServiceMachine(BattleStateMachine):
    def __init__(self,memory,hooks=None,program=None):
        if program is None:program=json.loads((ROOT/'analysis/phase4/terrain/service-program.json').read_text())
        super().__init__(memory,hooks,program)

    def step(self,**kwargs):
        return self.run_entry(0xC0BB,**kwargs)

    def phase(self,substate,**kwargs):
        self.memory[0x500]=9;self.memory[0x501]=substate&255
        return self.step(**kwargs)

MapServiceController=MapServiceMachine
