"""Session response reuse and opening caches preserve saves, RNG and receipts."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign, GameError, digest
from remake.session import CampaignSession
import remake.session as session_module
from campaign_fixtures import controlled_catalog, arrange_contact


class SessionPreviewCacheTests(unittest.TestCase):
    paths=[ROOT/'game/data/campaigns'/f'{date}.json' for date in ('184-02','190-01','263-05','217-07')]

    def test_repeated_current_views_and_save_roundtrip_keep_exact_state(self):
        session=CampaignSession(self.paths)
        baseline=digest(session.view())
        self.assertEqual(digest(session.view()),baseline)
        self.assertIsNone(session.to_dict())
        for scenario,side in [('mainland184-02','yellow_turban'),('mainland217-07','shu'),('mainland263-05','wei')]:
            with self.subTest(scenario=scenario):
                session.command('new',dict(scenario=scenario,faction=side,seed=2026),session.revision)
                saved=session.export_save();state=deepcopy(session.to_dict());revision=session.revision
                rng=deepcopy(session.game.state.rng);baseline=digest(session.view())
                self.assertEqual(digest(session.view()),baseline)
                self.assertEqual(session.revision,revision);self.assertEqual(session.to_dict(),state)
                self.assertEqual(session.game.state.rng,rng)
                session.load_save(saved,revision)
                self.assertEqual(session.export_save(),saved);self.assertEqual(session.to_dict(),state)
                self.assertEqual(session.game.state.rng,rng)
                self.assertEqual(session.game.catalog.data['schema'],'tk2-campaign-v1')
                self.assertNotIn('content_generation',session.game.catalog.data)
                self.assertTrue(all('archived' not in row for row in session.view()['catalog']['scenarios']))

    def test_fresh_preview_containers_cannot_corrupt_cached_openings(self):
        session=CampaignSession(self.paths)
        expected=deepcopy(session.view()['catalog']['scenarios'])
        catalog_hashes={key:digest(c.data) for key,c in session.catalogs.items()}
        previews=session.view()['catalog']['scenarios'];row=previews[0];side=next(iter(row['faction_resources']))
        row['id']='corrupt';row['initial_owners']['nanyang']='corrupt'
        row['active_cities'].clear();row['city_names'].clear()
        row['map_cities'].clear();row['factions'].clear()
        row['city_profiles']['shujun']['tier']='corrupt'
        row['faction_resources'][side]['gold']=-1
        row['faction_officers'][side]=-1;row['faction_colors'][side]='#000000'
        previews.pop()
        self.assertEqual(session.view()['catalog']['scenarios'],expected)
        self.assertEqual({key:digest(c.data) for key,c in session.catalogs.items()},catalog_hashes)
        self.assertEqual(session.revision,0);self.assertIsNone(session.to_dict())

    def test_all_opening_ruler_portraits_use_dated_person_identity_and_fresh_rows(self):
        paths=sorted(path for path in (ROOT/'game/data/campaigns').glob('*.json')
                     if path.name!='index.json')
        session=CampaignSession(paths)
        previews=session._scenario_previews()
        self.assertEqual(len(previews),29)
        for row in previews:
            catalog=session.catalogs[row['id']]
            for faction in row['factions']:
                expected=catalog.by_id[catalog.data['faction_rulers'][faction['id']]]
                self.assertEqual(faction['ruler_person_id'],expected['person_id'])
                self.assertEqual(faction['captain'],expected['name'])
        expected=deepcopy(previews)
        previews[0]['factions'][0]['ruler_person_id']='corrupt'
        self.assertEqual(session._scenario_previews(),expected)

    def test_real_succession_renames_live_faction_and_portrait_without_rewriting_preview_or_identity(self):
        session=CampaignSession(self.paths)
        session.command('new',dict(scenario='mainland217-07',faction='shu',seed=2026),0)
        game=session.game;state=game.state
        original_catalog=deepcopy(game.catalog.data)
        previews=deepcopy(session._scenario_previews())
        from remake.view_transport import ViewTransport
        transport=ViewTransport();opening_wire=transport.pack(session.view(),game.catalog.sha256)
        colors=deepcopy(session.view()['catalog']['faction_colors'])
        owners={key:city.owner for key,city in state.cities.items()}
        previous=state.extension['leaders']['shu'];officer=state.officers[previous]
        city=next(c for c in state.cities.values() if previous in c.roster.officer_ids)
        city.roster.officer_ids.remove(previous);city.reserves+=officer.troops
        officer.troops=0;officer.alive=False;officer.faction_id=None;officer.loyalty=0
        game._reconcile_factions(state)
        provisional=state.extension['leaders']['shu']
        current=next(row for row in session.view()['catalog']['factions'] if row['id']=='shu')
        self.assertEqual((current['name'],current['captain']), (game.person_name(state,provisional),)*2)
        self.assertEqual(current['ruler_person_id'],state.officers[provisional].person_id)
        choices=state.extension['pending_succession']['shu']['candidates']
        selected=next(ident for ident in choices if ident!=provisional)
        session.command('choose_successor',dict(officer=selected),session.revision)
        current=next(row for row in session.view()['catalog']['factions'] if row['id']=='shu')
        state=game.state;expected=game.person_name(state,selected)
        self.assertEqual((current['name'],current['captain'],current['display_name']),(expected,)*3)
        self.assertEqual(current['ruler_id'],selected)
        self.assertEqual(current['ruler_person_id'],state.officers[selected].person_id)
        self.assertEqual(game.faction_name(state,'shu'),expected)
        changed_wire=transport.pack(session.view(),game.catalog.sha256,opening_wire['catalog_token'])
        self.assertNotIn('static_catalog',changed_wire)
        transmitted=next(row for row in changed_wire['view']['catalog']['factions'] if row['id']=='shu')
        self.assertEqual(transmitted,current,'Worker view-cache deltas must carry the live name and portrait identity')
        self.assertEqual({key:city.owner for key,city in state.cities.items()},owners)
        self.assertEqual(session.view()['catalog']['faction_colors'],colors)
        self.assertEqual(session._scenario_previews(),previews)
        self.assertEqual(game.catalog.data,original_catalog)
        preview=session.preview_city('mainland217-07',city.id)['city']
        self.assertEqual(preview['owner_name'],game.catalog.factions['shu']['name'])
        saved=session.export_save();rng=deepcopy(state.rng)
        returned=session.view();returned['catalog']['factions'][0]['name']='poisoned'
        self.assertEqual(session.export_save(),saved);self.assertEqual(game.state.rng,rng)
        clone=CampaignSession(self.paths);clone.load_save(saved,clone.revision)
        restored=next(row for row in clone.view()['catalog']['factions'] if row['id']=='shu')
        self.assertEqual(restored,current);self.assertEqual(clone.export_save(),saved)

    def test_preview_city_tiers_use_each_catalog_without_copying_economy_metadata(self):
        session=CampaignSession(self.paths)
        for row in session.view()['catalog']['scenarios']:
            expected={key:{'tier':profile['tier']} for key,profile in
                      session.catalogs[row['id']].data['city_profiles'].items()}
            self.assertEqual(row['city_profiles'],expected,row['id'])
            for tier in ('giant','large'):
                expected_ids={key for key,profile in expected.items()
                              if profile['tier']==tier and key in row['active_cities']}
                self.assertTrue(expected_ids,(row['id'],tier))
                self.assertEqual({key for key,profile in row['city_profiles'].items()
                                  if profile['tier']==tier and key in row['active_cities']},expected_ids)

    def test_cached_openings_do_not_rescan_other_scenarios(self):
        session=CampaignSession(self.paths)
        openings=deepcopy(session.view()['catalog']['scenarios'])
        def current_only(function):
            def checked(catalog,*args):
                self.assertIs(catalog,session.game.catalog,'unchanged opening metadata was rescanned')
                return function(catalog,*args)
            return checked
        with patch.object(session_module,'city_names',side_effect=current_only(session_module.city_names)), \
             patch.object(session_module,'faction_resources',side_effect=current_only(session_module.faction_resources)), \
             patch.object(session_module,'faction_officer_counts',side_effect=current_only(session_module.faction_officer_counts)), \
             patch.object(session_module,'faction_colors',side_effect=current_only(session_module.faction_colors)):
            for scenario,side in [('mainland184-02','yellow_turban'),('mainland217-07','shu')]:
                session.command('new',dict(scenario=scenario,faction=side,seed=2026),session.revision)
                saved=session.export_save()
                self.assertEqual(session.view()['catalog']['scenarios'],openings)
                session.load_save(saved,session.revision)
                self.assertEqual(session.view()['catalog']['scenarios'],openings)
                self.assertEqual(session.export_save(),saved)


class SessionResponseReuseTests(unittest.TestCase):
    def setUp(self):
        catalog=controlled_catalog()
        with patch.object(session_module,'Catalog',return_value=catalog):
            self.session=CampaignSession([ROOT/'controlled.json'])

    def single_view(self, operation):
        with patch.object(Campaign,'view',autospec=True,side_effect=Campaign.view) as base_view:
            result=operation()
        self.assertEqual(base_view.call_count,1,'one response recomputed the campaign view')
        self.assertIs(base_view.call_args.args[0],self.session.game)
        saved=self.session.export_save()
        self.assertEqual({k:v for k,v in result.items() if k!='presentation'},self.session.view())
        self.assertEqual(self.session.export_save(),saved,'reading the response changed saved state/RNG')
        return result

    def start(self):
        return self.single_view(lambda:self.session.command('new',dict(faction='shu',seed=2026),self.session.revision))

    def test_new_regular_load_and_idempotent_ai_generate_one_complete_view(self):
        session=self.session
        self.start()
        self.single_view(lambda:session.command('allocate',dict(city='xiangyang',officer=146,troops=250),session.revision))
        self.assertEqual(session.game.state.officers[146].troops,250)
        saved=session.export_save();rng=deepcopy(session.game.state.rng)
        self.single_view(lambda:session.load_save(saved,session.revision))
        self.assertEqual(session.export_save(),saved)
        self.assertEqual(session.game.state.rng,rng)
        turn=session.game.state.turn
        self.single_view(lambda:session.command('end_turn',{},session.revision))
        revision=session.revision
        self.single_view(lambda:session.command('ai',dict(turn=turn),revision))
        saved=session.export_save();committed=session.revision;journal=deepcopy(session.journal)
        result=self.single_view(lambda:session.command('ai',dict(turn=turn),revision))
        self.assertNotIn('presentation',result)
        self.assertEqual(session.export_save(),saved)
        self.assertEqual(session.revision,committed)
        self.assertEqual(session.journal,journal)

    def test_real_battle_receipt_survives_reuse_without_replaying_after_settlement_or_load(self):
        session=self.session
        self.start()
        game=session.game;state=game.state
        game._start_expanded_battle(state,state.cities['xiangyang'],state.cities['nanyang'],[146])
        arrange_contact(game)
        battle=state.battle;payload=dict(battle_id=battle['id'],actor=146,target=battle['defenders'][0]['id'])
        reference=Campaign(game.catalog)
        reference.load_save(session.export_save(),0)
        expected=reference.command('attack',payload,reference.revision)
        result=self.single_view(lambda:session.command('attack',payload,session.revision))
        self.assertEqual(result['presentation'],expected['presentation'])
        self.assertEqual(session.export_save(),reference.export_save())
        self.assertEqual(session.game.state.rng,reference.state.rng)
        self.assertNotIn('presentation',session.view())
        result=self.single_view(lambda:session.command('retreat',dict(battle_id=battle['id']),session.revision))
        self.assertEqual(result['presentation']['scenes'][0]['kind'],'retreat')
        revision=session.revision
        result=self.single_view(lambda:session.command('settle',dict(battle_id=battle['id']),revision))
        self.assertNotIn('presentation',result)
        saved=session.export_save();committed=session.revision;journal=deepcopy(session.journal)
        result=self.single_view(lambda:session.command('settle',dict(battle_id=battle['id']),revision))
        self.assertNotIn('presentation',result)
        self.assertEqual(session.export_save(),saved)
        self.assertEqual(session.revision,committed)
        self.assertEqual(session.journal,journal)
        result=self.single_view(lambda:session.load_save(saved,session.revision))
        self.assertNotIn('presentation',result)
        self.assertEqual(session.export_save(),saved)

    def test_failed_commands_and_loads_keep_state_rng_revision_and_game_identity(self):
        session=self.session
        self.start()
        game=session.game;saved=session.export_save();revision=session.revision;journal=deepcopy(session.journal)
        invalid=deepcopy(saved);invalid['checksum']='invalid'
        operations=[
            lambda:session.command('new',dict(scenario='missing',faction='shu',seed=2026),revision),
            lambda:session.command('new',dict(faction='missing',seed=2026),revision),
            lambda:session.command('allocate',dict(city='xiangyang',officer=146,troops=250),revision-1),
            lambda:session.command('allocate',dict(city='nanyang',officer=146,troops=250),revision),
            lambda:session.load_save(invalid,revision)]
        for index,operation in enumerate(operations):
            with self.subTest(operation=index):
                with patch.object(Campaign,'view',autospec=True,side_effect=Campaign.view) as base_view:
                    with self.assertRaises((GameError,ValueError)):
                        operation()
                self.assertEqual(base_view.call_count,0)
                self.assertIs(session.game,game)
                self.assertEqual(session.export_save(),saved)
                self.assertEqual(session.revision,revision)
                self.assertEqual(session.journal,journal)
        with patch.object(game,'validate',side_effect=ValueError('controlled post-action failure')), \
             patch.object(Campaign,'view',autospec=True,side_effect=Campaign.view) as base_view:
            with self.assertRaises(ValueError):
                session.command('allocate',dict(city='xiangyang',officer=146,troops=250),revision)
        self.assertEqual(base_view.call_count,0)
        self.assertIs(session.game,game)
        self.assertEqual(session.export_save(),saved)
        self.assertEqual(session.revision,revision)
        self.assertEqual(session.journal,journal)


if __name__=='__main__':unittest.main()
