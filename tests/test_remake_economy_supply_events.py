"""Strict historical receipts for city development and battlefield supplies."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
from remake.events import validate


def event(kind, details, **extra):
    return dict(id=1,kind=kind,year=190,month=1,day=1,turn=1,
        person_ids=['person-a'],city_ids=['home'],factions=['shu'],
        audience='player',details=details,**extra)


class EconomySupplyEventTests(unittest.TestCase):
    def check(self, row):
        catalog=SimpleNamespace(definitions={'person-a'},map_cities={'home','enemy'},
            factions={'shu','wei'},data={})
        state=SimpleNamespace(year=190,month=1,day=1,turn=1,
            extension={'events':{'next_id':2,'items':[deepcopy(row)]}})
        snapshot=deepcopy(state.extension)
        validate(SimpleNamespace(catalog=catalog),state)
        self.assertEqual(state.extension,snapshot)

    def reject_details(self, row, changes):
        for change in changes:
            with self.subTest(kind=row['kind'],change=change):
                bad=deepcopy(row);bad['details'].update(change)
                with self.assertRaises(ValueError):
                    self.check(bad)
        for field in row['details']:
            bad=deepcopy(row);del bad['details'][field]
            with self.subTest(kind=row['kind'],missing=field),self.assertRaises(ValueError):
                self.check(bad)

    def test_development_units_caps_and_actual_governance_gain(self):
        base=dict(actor='person-a',development='land',gold=26,before=950,after=990,
            gain=40,governance_before=60,governance_after=62)
        land=event('city_developed',base);self.check(land)
        for details in [dict(development='industry'),
                dict(before=999,after=999,gain=0,governance_after=61),
                dict(governance_before=100,governance_after=100),
                dict(before=999800,after=999900,gain=100,development='population',
                    governance_before=99,governance_after=100)]:
            self.check(event('city_developed',{**base,**details}))
        self.reject_details(land,[dict(development='town'),dict(development=[]),
            dict(gold=True),dict(gold=9),dict(gold=11),dict(gold=28),dict(after=991),
            dict(after=1000,gain=50),dict(gain=-1),dict(governance_after=61),
            dict(governance_before=True),dict(actor='other'),dict(extra=1),
            dict(before=999,after=999,gain=0,governance_before=100,governance_after=100),
            dict(development='population',before=95000,after=95101,gain=101,governance_after=61)])

    def test_unrest_only_losses_from_the_committed_category(self):
        base=dict(governance=19,category='population',gold_loss=0,grain_loss=0,
            population_loss=400,land_loss=0,industry_loss=0)
        row=event('civil_unrest',base);row['person_ids']=[];self.check(row)
        for change in [dict(population_loss=0),
                dict(category='resources',population_loss=0,gold_loss=100,grain_loss=200),
                dict(category='development',population_loss=0,land_loss=40,industry_loss=20)]:
            self.check({**row,'details':{**base,**change}})
        self.reject_details(row,[dict(category='riot'),dict(category={}),dict(governance=50),
            dict(governance=True),dict(population_loss=401),dict(population_loss=-100),
            dict(gold_loss=1),dict(population_loss=1000000),dict(extra=1)])
        with self.assertRaises(ValueError):
            self.check({**row,'person_ids':['person-a']})

    def test_battle_exhaustion_is_a_bounded_snapshot_after_battle_ends(self):
        details=dict(battle_id='battle-12',side='attackers',days=3,grain=0,
            daily_grain=10,missing_units=2500,outcome='retreat')
        row=event('battle_supply_exhausted',details)
        row.update(person_ids=[],city_ids=['home','enemy'],factions=['shu','wei'])
        self.check(row)
        self.check({**row,'details':{**details,'side':'defenders','outcome':'victory'}})
        self.reject_details(row,[dict(battle_id='battle-0'),dict(battle_id='<script>'),
            dict(side='attacker'),dict(days=0),dict(days=31),dict(days=True),
            dict(grain=-1),dict(daily_grain=0),dict(daily_grain=23),
            dict(missing_units=0),dict(missing_units=10001),dict(outcome='victory'),dict(extra=1)])

    def test_battle_grain_destination_is_optional_as_one_complete_buy_receipt(self):
        base=dict(actor='person-a',direction='buy',batches=3,grain=300,gold=30,rate=10)
        self.check(event('grain_traded',base))
        battle=event('grain_traded',{**base,'battle_id':'battle-3','side':'attackers','destination':'battle'})
        self.check(battle)
        for missing in ('battle_id','side','destination'):
            bad=deepcopy(battle);del bad['details'][missing]
            with self.assertRaises(ValueError):self.check(bad)
        self.reject_details(battle,[dict(direction='sell'),dict(side='attackers<script>'),
            dict(destination='city'),dict(battle_id='battle-01'),dict(grain=299),dict(extra=1)])


if __name__ == '__main__':
    unittest.main()
