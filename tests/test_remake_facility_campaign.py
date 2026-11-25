"""Real campaigns exercise facility profiles, saves, disasters and combat.

Small calendars/rosters isolate practical boundaries; they are controlled game
fixtures and do not assert historical deployment, weather or city facilities.
"""
from copy import deepcopy
from pathlib import Path
import json
import os
import sys
import tempfile
from time import perf_counter
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake import civil_staff,facilities,grain_relief,payroll,treasures
from remake.campaign import Campaign,Catalog,SeedRng,digest,canonical
from remake.city_economy import income_at,monthly_income,tier_at
from remake.errors import GameError
from remake.march_core import using_backend,invoke,CoreUnavailable
from remake.session import CampaignSession
from remake.view_transport import ViewTransport
from campaign_fixtures import controlled_catalog, arrange_contact, record_garrison_charges
from test_remake_civil_staff_campaign import staff_catalog
from test_remake_tactical_ai import successful_rng


def facility_catalog(*,month=4,disasters=False):
    data=deepcopy(controlled_catalog().data)
    data.update(id='controlled-facility-campaign',start_month=month,facility_ai_default=False,
        facility_rules=deepcopy(facilities.RULES),
        facility_disaster_cities=dict(flood=['xiangyang'],drought=['xiangyang']))
    data['facility_rules'].update(disasters_enabled=disasters)
    # Facility visits have their own exact fee/RNG receipts. Keep independent
    # autonomous development out of this fixture; its real-AI shared transaction
    # is covered by test_remake_city_development instead.
    data.setdefault('city_development_rules', {})['ai_enabled'] = False
    data['rules']['persuade_officer_gold']=100000000
    data['initial_owners']['nanjun']='shu'
    for key in data['active_cities']:
        data['city_profiles'][key]['tier']='giant'
        data.get('city_scale_rules',{}).get('cities',{}).pop(key,None)
        data['initial_city_resources'][key]=dict(gold=5000,grain=100000,reserves=5000)
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'facilities.json'
        path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)


def _monthly_wages(state, city):
    """These fixtures have enough stock to pay the full wage once per month."""
    wages = [payroll.wage(state.officers[ident]) for ident in city.roster.officer_ids
             if state.officers[ident].alive and state.officers[ident].faction_id == city.owner]
    return {field: sum(wage[field] for wage in wages) for field in ('gold', 'grain')}


class FacilityCampaignTests(unittest.TestCase):
    def new(self,**options):
        game=Campaign(facility_catalog(**options))
        game.command('new',dict(faction='shu',seed=2026),0)
        return game

    def cmd(self,game,kind,**payload):
        return game.command(kind,payload,game.revision)

    def advance(self,game,count=1):
        for _ in range(count):
            game._complete_turn(game.state)
            game._reconcile_factions(game.state)
            civil_staff.synchronize(game,game.state,monthly=game.state.day==1)
            treasures.synchronize(game,game.state)
            facilities.synchronize(game,game.state)
            game.validate(game.state)

    def restore(self,game):
        saved=game.export_save();other=Campaign(game.catalog)
        other.load_save(json.loads(json.dumps(saved)),0)
        self.assertEqual(other.export_save(),saved)
        return other

    def fails(self,game,kind,**payload):
        before,revision,journal=game.export_save(),game.revision,deepcopy(game.journal)
        with self.assertRaises((GameError,ValueError,TypeError)):
            self.cmd(game,kind,**payload)
        self.assertEqual(game.export_save(),before)
        self.assertEqual(game.revision,revision)
        self.assertEqual(game.journal,journal)

    def test_all_29_openings_and_city_previews_keep_initial_facilities_and_rng_pure(self):
        paths=[path for path in sorted((ROOT/'game/data/campaigns').glob('*.json')) if path.name!='index.json']
        self.assertEqual(len(paths),29)
        session=CampaignSession(paths)
        for path in paths:
            catalog=session.catalogs[json.loads(path.read_text())['id']]
            game=Campaign(catalog)
            player=next(iter(catalog.factions))
            game.command('new',dict(faction=player,seed=2026),0)
            before=game.export_save()
            result=game.view()['catalog']['facilities']
            self.assertEqual(set(result['cities']),set(game.state.cities))
            for key,city in game.state.cities.items():
                with self.subTest(scenario=catalog.data['id'],city=key):
                    row=result['cities'][key]
                    expected = facilities.opening_view(catalog.data, key)
                    self.assertEqual((row['town'], row['preparedness'], row['damage']),
                                     (expected['town'], expected['preparedness'], expected['damage']))
                    preview=session.preview_city(catalog.data['id'],key)
                    self.assertEqual(preview['city']['owner'],city.owner)
            self.assertEqual(game.export_save(),before)
            self.assertEqual(session.game.state,None,'Opening city previews cannot start a campaign')
            self.assertFalse(result['factions'][player]['policy']['enabled'])
            self.assertTrue(all(row['policy']['enabled'] for key,row in result['factions'].items() if key!=player))

    def test_town_upgrade_receipts_and_older_gold_only_receipts_survive_loading(self):
        game = self.new()
        city_id, actor = 'xiangyang', 439
        game.state.extension['facilities']['cities'][city_id]['town'] = 1
        game.state.extension['city_development']['cities'][city_id]['population'] = 120_000
        base = income_at(game.catalog.data, city_id, game.state.year, game.state.month)['grain']
        from test_remake_economy_v2 import reference_adjusted

        land = game.state.extension['city_development']['cities'][city_id]['land']
        for before, gold, grain in ((1, 500, 2000), (2, 1000, 4000)):
            city = game.state.cities[city_id]
            city.gold, city.grain = gold, grain - 1
            self.fails(game, 'develop_town', city=city_id, actor=actor)
            city.grain = grain
            view = game.view()['catalog']
            self.assertEqual(view['facilities']['cities'][city_id]['develop'],
                dict(from_town=before,to_town=before+1,gold=gold,grain=grain,can_develop=True))
            self.assertEqual(view['city_development']['cities'][city_id]['income']['grain'],
                             2 * reference_adjusted(base, 120_000, before, land, land, 60, 60))
            used = game.state.extension['command_books']['factions']['shu']['used']
            self.cmd(game, 'develop_town', city=city_id, actor=actor)
            self.assertEqual(game.state.extension['command_books']['factions']['shu']['used'], used + 1)
            city = game.state.cities[city_id]
            self.assertEqual((city.gold, city.grain), (0, 0))
            self.assertEqual(game.state.extension['events']['items'][-1]['details']['grain'], grain)
            expected = 2 * reference_adjusted(base, 120_000, before + 1, land, land, 60, 60)
            self.assertEqual(monthly_income(game, city_id, game.state)['grain'], expected)
            game = self.restore(game)
            self.assertEqual(monthly_income(game, city_id, game.state)['grain'], expected)

        save = game.export_save()
        receipt = next(row['details'] for row in save['state']['extension']['events']['items']
                       if row['kind'] == 'town_developed')
        receipt.pop('grain')
        receipt['gold'] = 200
        save['checksum'] = digest({key: value for key, value in save.items() if key != 'checksum'})
        loaded = Campaign(game.catalog)
        loaded.load_save(save, 0)
        self.assertEqual(loaded.export_save(), save)

    def test_historical_school_profile_survives_cache_save_transfer_and_same_next_rng(self):
        game=self.new();ident=146;actor=439
        original=deepcopy(game.catalog.profiles[ident]);before=game.state.officers[ident].profile.intellect
        transport=ViewTransport();first=transport.pack(game.view(),game.catalog.sha256)
        known=first['catalog_token']+':'+first['quote_token']
        self.cmd(game,'study_officer',city='xiangyang',actor=actor,officer=ident)
        officer=game.state.officers[ident]
        self.assertGreater(officer.profile.intellect,before)
        self.assertEqual(game.catalog.profiles[ident],original)
        self.assertEqual(officer.profile.basis['intellect'],'source_initial_plus_campaign_school_learning')
        changed=transport.pack(game.view(),game.catalog.sha256,known)
        self.assertNotIn('static_catalog',changed)
        row=next(row for row in changed['view']['catalog']['library'] if row['id']==ident)
        self.assertEqual(row['intellect'],officer.profile.intellect)
        self.assertEqual(row['study_gain'],officer.profile.intellect-before)
        saved=game.export_save();loaded=self.restore(game)
        self.advance(game);self.advance(loaded)
        self.cmd(game,'improve_prevention',city='xiangyang',actor=actor)
        self.cmd(loaded,'improve_prevention',city='xiangyang',actor=actor)
        self.assertEqual(game.export_save(),loaded.export_save())
        self.assertEqual(game.state.rng,loaded.state.rng)
        self.assertEqual(saved['state']['officers'][str(ident)]['profile']['intellect'],officer.profile.intellect)
        for current in (game,loaded):
            self.advance(current)
            self.cmd(current,'transfer',source='xiangyang',target='nanjun',officers=[ident],route_mode='land')
            self.advance(current)
            self.cmd(current,'arrivals')
            self.assertIn(ident,current.state.cities['nanjun'].roster.officer_ids)
            self.assertNotIn(ident,current.state.cities['xiangyang'].roster.officer_ids)
            self.assertEqual(current.state.officers[ident].profile.intellect,officer.profile.intellect)
        self.assertEqual(game.export_save(),loaded.export_save())

    def test_generated_student_retains_base_identity_through_learning_and_save(self):
        catalog=staff_catalog()
        for seed, can_study in ((2027, True), (2026, False)):
            with self.subTest(seed=seed):
                game=Campaign(catalog)
                self.cmd(game,'new',faction='shu',seed=seed)
                city='nanjun';ident=game.state.extension['civil_staff']['cities'][city]['candidate']['id']
                self.cmd(game,'hire_staff',city=city,candidate=ident)
                self.advance(game)
                game.state.extension['facilities']['cities'][city]['town']=2
                base=deepcopy(game.state.extension['civil_staff']['people'][ident]['profile'])
                before=game.state.officers[ident].profile.intellect
                if can_study:
                    self.cmd(game,'study_officer',city=city,actor=ident,officer=ident)
                    self.assertGreater(game.state.officers[ident].profile.intellect,before)
                else:
                    self.assertGreaterEqual(before,facilities.RULES['study_cap'])
                    self.fails(game,'study_officer',city=city,actor=ident,officer=ident)
                    self.assertEqual(game.state.officers[ident].profile.intellect,before)
                self.assertEqual(game.state.extension['civil_staff']['people'][ident]['profile'],base)
                self.assertNotIn(ident,game.catalog.by_id)
                restored=self.restore(game)
                self.assertEqual(restored.state.officers[ident].profile,game.state.officers[ident].profile)
                self.assertEqual(restored.person_profile(restored.state,ident),restored.state.officers[ident].profile)

    def test_backend_changes_keep_real_facility_rolls_actions_and_save_bytes_equal(self):
        try:
            with using_backend('rust'):
                invoke('allocate',troops=[],numerator=1,denominator=1)
        except CoreUnavailable as error:
            if os.environ.get('MARCH_CORE_BACKEND')=='rust':raise
            self.skipTest(str(error))
        catalog=facility_catalog();saved=[]
        for backend in ('python','rust'):
            with using_backend(backend):
                game=Campaign(catalog);self.cmd(game,'new',faction='shu',seed=2026)
                self.cmd(game,'study_officer',city='xiangyang',actor=439,officer=146)
                self.advance(game)
                self.cmd(game,'improve_prevention',city='xiangyang',actor=439)
                self.advance(game)
                self.cmd(game,'buy_equipment',city='xiangyang',actor=439,officer=146,slot='weapon',item=21)
                saved.append(game.export_save())
        self.assertEqual(saved[0],saved[1])

    def test_actual_month_disaster_has_one_receipt_actual_resource_loss_and_no_military_teleport(self):
        game=self.new(month=7,disasters=True)
        game.catalog.data['facility_rules']['drought_chance']=100
        source=game.state.cities['xiangyang'];row=game.state.extension['facilities']['cities'][source.id]
        row.update(preparedness=0,damage=0)
        game.state.officers[146].health=0
        self.advance(game,2)
        before=deepcopy(game.state)
        income=monthly_income(game,source.id,before,date=(before.year,8))
        wages = _monthly_wages(before, before.cities[source.id])
        with record_garrison_charges() as paid:
            self.advance(game)
        events=[event for event in game.state.extension['events']['items'] if event['kind']=='city_disaster']
        self.assertEqual(len(events),1)
        receipt=events[0]['details'];current=game.state.cities[source.id]
        self.assertEqual(receipt['disaster'],'drought');self.assertEqual(receipt['rate'],10)
        self.assertEqual(current.gold, before.cities[source.id].gold + income['gold'] - wages['gold'])
        self.assertEqual(current.grain, before.cities[source.id].grain + income['grain']
                         - paid[source.id] - receipt['grain'] - wages['grain'])
        self.assertEqual(current.reserves,before.cities[source.id].reserves+income['reserves']-receipt['reserves'])
        self.assertEqual(game.state.soldiers['lost']-before.soldiers['lost'],receipt['reserves'])
        self.assertEqual(game.state.officers[146].health,8,'Only established monthly healing changes the wounded officer')
        self.assertEqual({i:o.troops for i,o in game.state.officers.items()},
            {i:o.troops for i,o in before.officers.items()})
        self.assertEqual(game.state.extension['travel'],before.extension['travel'])
        committed=game.export_save()
        self.assertEqual(facilities.month_rollover(game,game.state),[])
        self.assertEqual(game.export_save(),committed)
        self.restore(game)

    def test_repair_restores_later_month_production_and_preparedness_99_prevents_losses(self):
        game=self.new(month=4,disasters=True)
        game.catalog.data['facility_rules'].update(flood_plain_chance=100,flood_mountain_chance=100)
        row=game.state.extension['facilities']['cities']['xiangyang']
        row.update(preparedness=99,damage=50)
        self.advance(game,3)
        disaster=[e for e in game.state.extension['events']['items'] if e['kind']=='city_disaster'][-1]['details']
        self.assertEqual((disaster['gold'],disaster['grain'],disaster['reserves']),(0,0,0))
        base=income_at(game.catalog.data,'xiangyang',game.state.year,game.state.month)
        income_before=facilities.adjusted_income(game.state,'xiangyang',base)
        self.cmd(game,'improve_prevention',city='xiangyang',actor=439)
        income_after=facilities.adjusted_income(game.state,'xiangyang',base)
        self.assertGreater(income_after['gold'],income_before['gold'])
        self.assertGreater(income_after['grain'],income_before['grain'])
        self.advance(game,2)
        row=game.state.extension['facilities']['cities']['xiangyang'];row['preparedness']=99
        before=deepcopy(game.state.cities['xiangyang'])
        wages = _monthly_wages(game.state, before)
        expected=monthly_income(game,'xiangyang',game.state,date=(game.state.year,6))
        with record_garrison_charges() as paid:
            self.advance(game)
        current=game.state.cities['xiangyang']
        self.assertEqual(current.gold, before.gold + expected['gold'] - wages['gold'])
        self.assertEqual(current.grain, before.grain + expected['grain']
                         - paid['xiangyang'] - wages['grain'])
        self.assertEqual(current.reserves,before.reserves+expected['reserves'])
        self.restore(game)

    def test_market_quote_changes_at_rollover_and_matches_actual_transaction(self):
        game = self.new(month=9)
        city_id = 'xiangyang'

        def prices():
            market = game.view()['catalog']['facilities']['cities'][city_id]['trade']
            return market['buy']['rate'], market['sell']['rate']

        self.assertEqual(prices(), (10, 9))
        self.advance(game, 2)
        self.assertEqual((game.state.month, game.state.day), (9, 21))
        self.assertEqual(prices(), (10, 9))
        self.advance(game)
        self.assertEqual((game.state.month, game.state.day), (10, 1))
        self.assertEqual(prices(), (7, 6))
        stock = game.state.cities[city_id]
        before = stock.gold, stock.grain, deepcopy(game.state.rng)
        self.cmd(game, 'trade_grain', city=city_id, actor=146, direction='buy', batches=2)
        stock = game.state.cities[city_id]
        self.assertEqual((stock.gold, stock.grain, game.state.rng), (before[0] - 14, before[1] + 2000, before[2]))
        trade = game.state.extension['events']['items'][-1]
        self.assertEqual((trade['kind'], trade['details']['rate'], trade['details']['gold']), ('grain_traded', 7, 14))
        self.restore(game)

    def test_september_harvest_preserves_city_disaster_history_and_pays_once(self):
        game = self.new(month=8, disasters=True)
        game.catalog.data['facility_rules']['drought_chance'] = 100
        state = game.state
        state.extension['facilities']['cities']['xiangyang']['preparedness'] = 99
        self.advance(game, 3)
        self.assertEqual((state.month, state.day), (9, 1))
        disaster, = [r for r in state.extension['events']['items'] if r['kind'] == 'city_disaster']
        self.assertEqual(disaster['city_ids'], ['xiangyang'])
        self.assertEqual(disaster['details']['grain'], 0)
        self.assertEqual(state.extension['facilities']['harvest']['disasters'], {'xiangyang': state.year})
        self.advance(game, 2)
        game = self.restore(game)
        state = game.state
        forecast = {key: result.balances[0]
                    for owner in ('shu', 'wu', 'wei')
                    for key, result in grain_relief.forecasts(game, state, owner, turns=1).items()}
        expected = {key: monthly_income(game, key, state)['grain'] // 5
                    for key in state.cities if key != 'xiangyang'}
        self.advance(game)
        self.assertEqual((state.month, state.day), (10, 1))
        self.assertEqual({key: city.grain for key, city in state.cities.items()}, forecast)
        rows = state.extension['events']['items']
        harvest, = [row for row in rows if row['kind'] == 'city_harvest']
        self.assertEqual((harvest['city_ids'], harvest['factions']), (['nanjun'], ['shu']))
        self.assertEqual(harvest['details'], {'bonuses': [expected['nanjun']]})
        self.assertGreater(expected['nanjun'], 0)
        self.assertEqual([r for r in rows if r['kind'] == 'city_disaster'], [disaster])
        self.assertEqual(state.extension['facilities']['harvest']['settled_year'], state.year)
        game = self.restore(game)
        self.advance(game)
        self.assertEqual([r for r in game.state.extension['events']['items']
                          if r['kind'] == 'city_harvest'], [harvest])

    def test_harvest_skips_all_affected_player_cities_and_starts_fresh_next_year(self):
        game = self.new(month=9, disasters=True)
        state = game.state
        history = state.extension['facilities']['harvest']
        history['disasters'].update(xiangyang=state.year, nanjun=state.year)
        self.advance(game, 3)
        self.assertFalse(any(row['kind'] == 'city_harvest' for row in state.extension['events']['items']))
        game.catalog.data['facility_rules'].update(flood_plain_chance=0, flood_mountain_chance=0, drought_chance=0)
        self.advance(game, 33)
        self.assertEqual((state.year, state.month, state.day), (218, 9, 1))
        self.advance(game, 3)
        harvest, = [row for row in state.extension['events']['items'] if row['kind'] == 'city_harvest']
        self.assertEqual(harvest['city_ids'], ['nanjun', 'xiangyang'])
        self.assertEqual((harvest['year'], harvest['month'], harvest['day']), (218, 10, 1))

    def test_actual_ai_turn_treats_using_shared_fee_rng_and_local_actions(self):
        game=self.new();city=game.state.cities['nanyang'];ident=city.roster.officer_ids[0]
        officer=game.state.officers[ident]
        city.reserves+=officer.troops;officer.troops=0;officer.health=20
        other=game.state.cities['jiangxia']
        for other_id in other.roster.officer_ids:
            other.reserves+=game.state.officers[other_id].troops;game.state.officers[other_id].troops=0
        game.state.extension['facilities']['factions']['wei'].update(enabled=True,
            auto_prevent=False,auto_treat=True,auto_trade=False,auto_equip=False,auto_develop=False,auto_study=False)
        expected_rng=deepcopy(game.state.rng);healing=35+expected_rng.next()%11
        before_troops=deepcopy(game.state.soldiers)
        self.cmd(game,'end_turn');self.cmd(game,'ai',turn=game.state.turn)
        receipts=[e for e in game.state.extension['events']['items'] if e['kind']=='officer_treated' and e['city_ids']==['nanyang']]
        self.assertEqual(len(receipts),1)
        self.assertEqual(receipts[0]['details']['gold'],50)
        self.assertEqual(receipts[0]['details']['after']-receipts[0]['details']['before'],healing)
        self.assertEqual(game.state.rng,expected_rng)
        self.assertEqual(game.state.soldiers,before_troops)
        self.assertEqual(game.state.extension['officer_actions'][str(ident)],1)
        self.assertEqual(game.state.phase,'city');self.assertEqual(game.state.turn,2)
        self.restore(game)

    def test_bought_weapon_changes_real_duel_damage_without_extra_rng(self):
        bare=self.new();armed=self.restore(bare)
        self.cmd(armed,'buy_equipment',city='xiangyang',actor=439,officer=146,slot='weapon',item=21)
        losses=[];rng=[]
        for game in (bare,armed):
            self.advance(game)
            state=game.state
            game._start_expanded_battle(state,state.cities['xiangyang'],state.cities['nanyang'],[146])
            arrange_contact(game)
            successful_rng(state)
            battle=state.battle;target=battle['defenders'][0]['id']
            self.cmd(game,'duel_start',battle_id=battle['id'],actor=146,target=target)
            self.assertIsNotNone(game.state.battle['extended']['duel'])
            game.state.rng=SeedRng(2026)
            before=game.state.battle['extended']['support'][str(target)]['health']
            self.cmd(game,'duel_action',battle_id=game.state.battle['id'],move='strike')
            losses.append(before-game.state.battle['extended']['support'][str(target)]['health'])
            rng.append(deepcopy(game.state.rng))
            game.validate(game.state)
        self.assertGreater(losses[1],losses[0]);self.assertEqual(rng[0],rng[1])

    def test_foreign_actors_policy_and_saved_learning_or_rule_tampering_fail_atomically(self):
        game=self.new()
        for kind,payload in [('treat_officer',dict(city='nanyang',actor=123,officer=123)),
                ('study_officer',dict(city='xiangyang',actor=123,officer=146)),
                ('buy_equipment',dict(city='xiangyang',actor=439,officer=123,slot='weapon',item=21)),
                ('improve_prevention',dict(city='xiangyang',actor=True)),
                ('set_facility_policy',dict(faction='wei',policy=dict(enabled=True)))]:
            self.fails(game,kind,**payload)
        self.cmd(game,'study_officer',city='xiangyang',actor=439,officer=146)
        original=game.export_save()
        for mutate in (lambda p:p['state']['extension']['facilities']['study'].update({'146':100}),
                lambda p:p['state']['officers']['146']['profile'].update(intellect=99),
                lambda p:p['state']['extension']['facilities']['cities']['xiangyang'].update(damage=51),
                lambda p:p['state']['extension']['facilities']['factions']['shu'].update(enabled=1)):
            bad=deepcopy(original);mutate(bad)
            bad['checksum']=digest({k:v for k,v in bad.items() if k!='checksum'})
            with self.assertRaises(GameError):game.load_save(bad,game.revision)
            self.assertEqual(game.export_save(),original)


if __name__=='__main__':unittest.main()
