"""Committed original-effect snapshots survive saves and reject contradictions."""
import json
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake.campaign import Campaign,Catalog,digest
from remake.errors import GameError
from browser_tactic_effect_fixture import fixture


class TacticEventSnapshots(unittest.TestCase):
    def committed(self,kind):
        data=fixture(kind)
        game=Campaign(Catalog(ROOT/'game/data/campaigns/208-10.json'))
        game.load_save(json.loads(json.dumps(data['save'])),game.revision)
        game.command('tactic',dict(battle_id=game.state.battle['id'],actor=data['actor'],
                                  target=data['target'],tactic=data['tactic']),game.revision)
        return game

    def rejects(self,game,patch):
        before=game.export_save()
        forged=deepcopy(before)
        row=next(row for row in reversed(forged['state']['extension']['events']['items']) if row['kind']=='tactic')
        patch(row['details'])
        forged['checksum']=digest({key:value for key,value in forged.items() if key!='checksum'})
        with self.assertRaises(GameError):
            game.load_save(json.loads(json.dumps(forged)),game.revision)
        self.assertEqual(game.export_save(),before)

    def test_fire_snapshot_equation_and_complete_group(self):
        game=self.committed('fire')
        for change in ({'grain_loss':-1},{'grain_after':0},{'affected_side':'city'},
                       {'success':False},{'tactic':4},{'grain_before':True}):
            with self.subTest(change=change):self.rejects(game,lambda details:details.update(change))
        self.rejects(game,lambda details:details.pop('grain_after'))

    def test_conversion_71_gate_is_a_committed_failure_snapshot(self):
        game=self.committed('conversion71')
        row=next(row for row in reversed(game.state.extension['events']['items']) if row['kind']=='tactic')
        self.assertEqual(row['details'],dict(tactic=8,success=False,success_percent=0,
                                           target_loyalty=71,guaranteed_failure=True))
        for change in ({'success':True},{'success_percent':10},{'target_loyalty':70},
                       {'guaranteed_failure':False},{'success_percent':True}):
            with self.subTest(change=change):self.rejects(game,lambda details:details.update(change))
        self.rejects(game,lambda details:details.pop('target_loyalty'))


if __name__=='__main__':unittest.main()
