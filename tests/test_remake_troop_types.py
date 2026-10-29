"""Source-bound original troop types and read-only effective movement rules."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import troop_types,battle_grid
from remake.campaign import Campaign,Catalog,digest
from test_remake_tactical_ai import battle
from test_remake_battle_grid import fixture


def builder():
    spec=importlib.util.spec_from_file_location('troop_type_builder',ROOT/'tools/officer-placement/build_troop_types.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class OriginalTroopTypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((ROOT/'game/config/references/officer-troop-types-v1.json').read_text())
        cls.original=json.loads((ROOT/'game/config/references/original-officer-stats.json').read_text())

    def test_reference_is_reproducible_without_touching_canonical_people_or_catalogues(self):
        tool=builder()
        paths=[ROOT/'game/config/campaigns/people.json',ROOT/tool.ROM_SOURCE,
               ROOT/tool.CN_SOURCE,*sorted((ROOT/'game/data/campaigns').glob('*.json'))]
        before={path:sha256(path.read_bytes()).hexdigest()for path in paths}
        self.assertEqual(tool.build(),self.data)
        self.assertEqual({path:sha256(path.read_bytes()).hexdigest()for path in paths},before)
        self.assertEqual(self.data['counts']['people'],1052)
        self.assertEqual(self.data['counts']['sources']['verified_original_rom'],221)
        self.assertEqual(self.data['counts']['sources']['original_table_transcription'],9)

    def test_every_reviewed_original_person_uses_exact_byte11_bits_not_troop_bytes(self):
        raw_by_id={row['original_id']:row for row in self.original['records']}
        bound=0
        for pid,row in self.data['records'].items():
            if row['source_kind']!='verified_original_rom':continue
            original=raw_by_id[row['original_id']];raw=bytes.fromhex(original['record_hex'])
            self.assertEqual(pid,original['person_id'])
            self.assertEqual(row['code'],(raw[11]>>2)&3)
            self.assertEqual(row['rom_offset'],original['rom_offset']+11)
            self.assertEqual(row['record_sha256'],sha256(raw).hexdigest())
            bound+=1
        self.assertEqual(bound,221)
        self.assertEqual(len(self.data['rom_records']),237)
        self.assertFalse(any(row['raw_code']==3 for row in self.data['rom_records']))
        self.assertEqual(troop_types.effective_affinity('san14-candidate-0001',0),1)
        self.assertEqual(troop_types.metadata('historical-wang-jian-liaodong',0)['original_id'],11)

    def test_conflicting_public_transcription_is_retained_and_rom_wins(self):
        changes={row['name']:row for row in self.data['source_disagreements']}
        self.assertEqual(set(changes),{'吕范','吕蒙'})
        self.assertEqual((changes['吕范']['selected_rom_code'],changes['吕范']['transcription_code']),(2,0))
        self.assertEqual((changes['吕蒙']['selected_rom_code'],changes['吕蒙']['transcription_code']),(0,2))
        for row in changes.values():
            self.assertEqual(troop_types.effective_affinity(row['person_id'],1),row['selected_rom_code'])

    def test_transcription_only_bindings_have_no_invented_rom_slot(self):
        rows=[row for row in self.data['records'].values()if row['source_kind']=='original_table_transcription']
        self.assertEqual(len(rows),9)
        for row in rows:
            self.assertNotIn('original_id',row)
            self.assertRegex(row['source_row_id'],r'^cnblogs-line-\d{4}$')
        self.assertEqual(troop_types.effective_affinity('san14-candidate-0651',0),2)
        self.assertNotEqual(self.data['records']['san14-candidate-0652']['source_kind'],'original_table_transcription',
                            'The unrelated Shu Zhang Nan cannot inherit the Yuan Shao source row')

    def test_career_region_retained_and_unknown_sources_are_explicit_design(self):
        self.assertEqual(self.data['records']['san14-candidate-0726']['source_kind'],'design_trait_inference')
        self.assertEqual(troop_types.effective_affinity('san14-candidate-0726',0),2)
        for row in self.data['records'].values():
            if row['source_kind']not in {'verified_original_rom','original_table_transcription'}:
                self.assertTrue(row['source_kind'].startswith('design_')or row['source_kind']in {'retained_design','fallback_design'})
                self.assertNotIn('original_id',row)
        for code in (0,1,2):
            self.assertEqual(troop_types.effective_affinity('clerk-000001',code),code)
            self.assertEqual(troop_types.metadata('clerk-000001',code)['source_kind'],'generated_design')
        for bad in (True,3,-1,None):
            with self.assertRaises(ValueError):troop_types.effective_affinity('unknown',bad)

    def test_forged_original_offset_or_code3_and_stale_record_checksum_are_rejected(self):
        pid=next(pid for pid,row in self.data['records'].items()if row['source_kind']=='verified_original_rom')
        for edit in [lambda row:row.update(code=3),lambda row:row.update(byte11=255),lambda row:row.update(rom_offset=1),
                     lambda row:row.update(person_id='someone-else'),lambda row:row.update(code=True)]:
            invalid=deepcopy(self.data);edit(invalid['records'][pid])
            with self.assertRaises(ValueError):troop_types.validate(invalid)
            invalid['records_sha256']=builder().compact_digest(invalid['records'])
            with self.assertRaises(ValueError):troop_types.validate(invalid)


class EffectiveTroopIntegrationTests(unittest.TestCase):
    def test_actual_cost_uses_effective_original_type_while_raw_profile_and_rng_stay_intact(self):
        game=battle(three_enemies=False);state=game.state
        # Original Ahuinan is a mountain type. The actual game baseline also
        # happens to be mountain, so use Lu Meng's known old-water/new-plain
        # disagreement on an actual current-catalog object for a clear effect.
        from remake.officers import initialize_officer,appearance_values
        ident=next(i for i,row in game.catalog.by_id.items()if row['name']=='吕蒙')
        profile=game.catalog.profiles[ident]
        officer=initialize_officer(game.catalog.definitions[game.catalog.by_id[ident]['person_id']],ident,profile,
            year=state.year,faction_id='shu',troops=100,
            **appearance_values(profile,game.catalog.by_id[ident].get('initialization'),faction_id='shu'))
        old=state.officers.get(ident);state.officers[ident]=officer
        before=deepcopy((officer,state.rng));unit=dict(id=ident,troops=100)
        self.assertEqual(troop_types.effective_affinity(officer.person_id,profile.terrain_affinity),0)
        self.assertEqual(battle_grid.movement_cost(state,unit,2),1)
        self.assertEqual(battle_grid.movement_cost(state,unit,3),3)
        self.assertEqual((officer,state.rng),before)
        if old is None:del state.officers[ident]
        else:state.officers[ident]=old

    def test_all_affinity_rows_remain_original_cost_table_with_unknown_controlled_identity(self):
        game,state,b=fixture();actor=b['attackers'][0]
        state.officers[actor['id']].person_id='controlled-raw-cost-table'
        for code in (0,1,2):
            state.officers[actor['id']].profile.terrain_affinity=code
            self.assertEqual(tuple(battle_grid.movement_cost(state,actor,terrain)for terrain in range(6)),battle_grid.MOVEMENT_COSTS[code][0])

    def test_all_29_openings_and_current_catalog_saves_share_policy_without_profile_migration(self):
        index=json.loads((ROOT/'game/data/campaigns/index.json').read_text())
        self.assertEqual(len(index['catalogs']),29)
        for name in index['catalogs']:
            catalog=Catalog(ROOT/'game/data'/name)
            game=Campaign(catalog)
            result=game.command('new',dict(faction=next(iter(catalog.factions)),seed=2026),0)
            saved=game.export_save();rng=deepcopy(game.state.rng)
            for ident,officer in game.state.officers.items():
                row=result['catalog']['officer_troop_types']['officers'][str(ident)]
                self.assertEqual(row['code'],troop_types.effective_affinity(officer.person_id,officer.profile.terrain_affinity))
                self.assertEqual(saved['state']['officers'][str(ident)]['profile']['terrain_affinity'],officer.profile.terrain_affinity)
            for row in result['catalog']['library']:
                base=catalog.profiles[row['id']].terrain_affinity
                self.assertEqual(row['affinity'],troop_types.effective_affinity(row['person_id'],base))
            self.assertEqual(game.export_save(),saved)
            self.assertEqual(game.state.rng,rng)
            clone=Campaign(catalog);restored=clone.load_save(saved,0)
            self.assertEqual(clone.export_save(),saved)
            self.assertEqual(restored['catalog']['officer_troop_types'],result['catalog']['officer_troop_types'])
            self.assertEqual(clone.state.rng,rng)
            self.assertNotIn('officer_troop_types',saved['state'])

    def test_metadata_is_fresh_and_never_mutates_baseline_or_static_policy(self):
        game=battle(three_enemies=False)
        saved=game.export_save();original=deepcopy(troop_types.policy())
        first=game.view()['catalog']['officer_troop_types']
        first['kinds'][0]['label_tc']='wrong'
        next(iter(first['officers'].values()))['code']=3
        self.assertEqual(troop_types.policy(),original)
        self.assertEqual(game.export_save(),saved)
        self.assertNotEqual(game.view()['catalog']['officer_troop_types']['kinds'][0]['label_tc'],'wrong')


if __name__=='__main__':unittest.main()
