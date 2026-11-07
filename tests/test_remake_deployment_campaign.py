"""Arrival-aware placement in unchanged current catalogs and exact saved battles.

The direct-start fixtures isolate initialization from unrelated strategic AI;
the public departure/arrival case uses real march food and calendar services.
No historical catalog, saved oracle, profile or ownership is rewritten.
"""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'source'),str(ROOT/'tests')]
from remake.campaign import Campaign,Catalog,digest
from remake import battle_grid,battle_deployment,battle_allegiance,battle_supply
from remake.errors import GameError

SOURCE,TARGET,ARRIVAL='baxi','hanzhong','jingzhao'


def command(game,kind,**payload):
    return game.command(kind,payload,game.revision)


class DeploymentCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=Catalog(ROOT/'game/data/campaigns/217-07.json')
        cls.catalog_digest=digest(cls.catalog.data)

    def fresh(self,player='shu'):
        game=Campaign(self.catalog)
        command(game,'new',faction=player,seed=2026)
        self.assertEqual(game.state.cities[SOURCE].owner,'shu')
        self.assertEqual(game.state.cities[TARGET].owner,'wei')
        self.assertIn(TARGET,game._neighbors(SOURCE,game.state))
        return game

    def start(self,player='shu',*,count=10,arrival_city=None):
        game=self.fresh(player);state=game.state
        source,target=state.cities[SOURCE],state.cities[TARGET]
        ids=[i for i in source.roster.officer_ids
             if state.officers[i].troops>0 and state.officers[i].health>0][:count]
        self.assertEqual(len(ids),count)
        before=deepcopy(state);opening=[]
        def inspect_opening(current):
            # Only hold the automatic response while inspecting its exact
            # entry state; later commands still use the actual AI service.
            opening.append(deepcopy(current.battle))
            self.assertEqual(current.phase,'battle')
        with patch.object(game,'_run_tactical_ai_turn',side_effect=inspect_opening):
            game._start_expanded_battle(state,source,target,ids,arrival_city=arrival_city)
        game.validate(state)
        self.assertEqual(digest(self.catalog.data),self.catalog_digest)
        return game,ids,before,opening

    def ready_march(self):
        game=self.fresh();source=game.state.cities[SOURCE]
        ident=next(i for i in source.roster.officer_ids if game.state.officers[i].troops>0)
        command(game,'depart',source=SOURCE,target=TARGET,officers=[ident],route_mode='land')
        row=game.state.extension['travel']['marches'][0]
        self.assertEqual(row['quote']['path'],[SOURCE,TARGET])
        self.assertFalse(row['risks'])
        arrival=row['arrival_turn']
        # Genuine daily meals/monthly services, without unrelated AI conquest
        # of this fixture's source. Arrival itself is a public transaction.
        while game.state.turn<arrival:
            game._complete_turn(game.state)
            game._spawn_eligible(game.state)
            game._reconcile_factions(game.state)
        game.state.phase='arrivals'
        game.validate(game.state)
        return game

    def test_new_player_and_ai_armies_share_twenty_native_positions_and_camp_commander(self):
        reference=None
        for player in('shu','wei','wu'):
            with self.subTest(player=player):
                game,ids,before,opening=self.start(player)
                state,battle=game.state,game.state.battle
                row=battle['extended']['tactical'];provenance=battle['extended']['deployment']
                self.assertEqual((len(battle['attackers']),len(battle['defenders'])),(10,10))
                self.assertEqual([u['id']for u in battle['attackers']],ids)
                self.assertEqual(len({(p['x'],p['y'])for p in row['positions'].values()}),20)
                camp=battle_grid._field(battle)['camp']
                self.assertEqual(row['positions'][str(battle['defenders'][0]['id'])],dict(x=camp[0],y=camp[1]))
                self.assertEqual((row['side'],row['passed']),('attackers',dict(attackers=False,defenders=False)))
                self.assertEqual(provenance['arrival_city'],SOURCE)
                self.assertEqual(provenance['policy'],'native_pair')
                if reference is None:reference=deepcopy((row,provenance))
                self.assertEqual((row,provenance),reference)
                self.assertEqual(state.rng,before.rng,'Planning must precede any real AI draws')
                self.assertEqual(state.soldiers,before.soldiers)
                # Only a defending player causes an automatic attacker turn.
                self.assertEqual(len(opening),int(player=='wei'))
                if opening:
                    self.assertIn('deployment',opening[0]['extended'])
                    self.assertIn('supply',opening[0]['extended'])
                    self.assertEqual(opening[0]['extended']['tactical']['side'],'attackers')

    def test_new_deployment_does_not_charge_extra_food_orders_or_refill_stock(self):
        game,_,before,_=self.start();state,battle=game.state,game.state.battle
        bags=battle['extended']['supply']['sides']
        self.assertEqual(state.cities[SOURCE].grain,
                         before.cities[SOURCE].grain-battle['supply_cost']-bags['attackers']['loaded'])
        self.assertEqual(state.cities[TARGET].grain,before.cities[TARGET].grain-bags['defenders']['loaded'])
        self.assertEqual(state.extension['command_books']['factions']['shu']['used'],
                         before.extension['command_books']['factions']['shu']['used']+1)
        for side in battle_grid.SIDES:
            self.assertEqual(bags[side]['consumed'],0)
            self.assertEqual(battle['extended']['tactical']['points'][side],
                             battle_grid.daily_points(sum(u['troops']for u in battle[side])))

    def test_public_march_arrival_transfers_its_real_remaining_grain_once(self):
        game=self.ready_march();before=deepcopy(game.state)
        march=before.extension['travel']['marches'][0]
        command(game,'arrivals')
        state,battle=game.state,game.state.battle
        self.assertEqual(state.phase,'battle')
        self.assertEqual(battle['extended']['deployment']['arrival_city'],march['quote']['path'][-2])
        row=battle['extended']['supply']['sides']['attackers']
        self.assertEqual((row['loaded'],row['initial_credit']),
                         (march['supply']['remaining'],march['supply']['credit_units']))
        self.assertEqual(state.cities[SOURCE].grain,before.cities[SOURCE].grain)
        self.assertEqual(state.rng,before.rng)
        self.assertEqual(state.extension['command_books'],before.extension['command_books'])
        self.assertFalse(state.extension['travel']['marches'])
        game.validate(state)

    def test_saved_actual_move_and_spent_ap_never_redeploy_or_refill(self):
        game,_,_,_=self.start(count=1);battle=game.state.battle
        actor=battle['attackers'][0]
        options=game.view()['catalog']['battle_tactical']['actors'][str(actor['id'])]['reachable']
        destination=min(options,key=lambda p:(p['cost'],p['y'],p['x']))
        provenance=deepcopy(battle['extended']['deployment'])
        ap=battle['extended']['tactical']['points']['attackers']
        command(game,'battle_move',battle_id=battle['id'],actor=actor['id'],x=destination['x'],y=destination['y'])
        self.assertEqual(game.state.battle['extended']['tactical']['points']['attackers'],ap-destination['cost'])
        saved=game.export_save();restored=Campaign(self.catalog);restored.load_save(deepcopy(saved),0)
        self.assertEqual(restored.export_save(),saved)
        self.assertEqual(restored.state.battle['extended']['deployment'],provenance)
        old=deepcopy(restored.state)
        battle_grid.initialize(restored,restored.state,restored.state.battle,directional=True,arrival_city=ARRIVAL)
        self.assertEqual(restored.state,old,'Even an explicit initialize cannot rearrange an existing grid')

    def test_existing_spatial_save_without_metadata_stays_byte_exact(self):
        game,_,_,_=self.start(count=1)
        old=game.export_save();old['state']['battle']['extended'].pop('deployment')
        old['checksum']=digest({k:v for k,v in old.items()if k!='checksum'})
        restored=Campaign(self.catalog);restored.load_save(deepcopy(old),0)
        self.assertEqual(restored.export_save(),old)
        self.assertNotIn('deployment',restored.state.battle['extended'])
        restored.view();restored.view()
        self.assertEqual(restored.export_save(),old)

    def test_nonspatial_legacy_bootstrap_uses_old_anchor_without_food_or_ai_replay(self):
        game,_,_,_=self.start('wei',count=1)
        for retain_bags in(True,False):
            with self.subTest(retain_bags=retain_bags):
                old=game.export_save();extended=old['state']['battle']['extended']
                # Both sections were absent in this declared historical input.
                extended.pop('tactical');extended.pop('deployment')
                if not retain_bags:extended.pop('supply')
                old['checksum']=digest({k:v for k,v in old.items()if k!='checksum'})
                restored=Campaign(self.catalog)
                with patch.object(restored,'_run_tactical_ai_turn',side_effect=AssertionError('Load must not replay AI')):
                    restored.load_save(deepcopy(old),0)
                state,battle=restored.state,restored.state.battle
                row=battle['extended']['tactical'];first=battle['attackers'][0]['id']
                self.assertEqual(row['positions'][str(first)],dict(x=29,y=10),
                                 'Pinned original-25 legacy anchor differs from the new native approach')
                self.assertEqual((row['side'],row['passed']),('defenders',dict(attackers=True,defenders=False)))
                self.assertNotIn('deployment',battle['extended'])
                self.assertEqual('supply'in battle['extended'],retain_bags)
                migrated=restored.export_save()
                for key in('cities','officers','rng','soldiers','extension'):
                    self.assertEqual(migrated['state'][key],old['state'][key])
                if retain_bags:self.assertEqual(migrated['state']['battle']['extended']['supply'],extended['supply'])
                restored.load_save(deepcopy(migrated),restored.revision)
                self.assertEqual(restored.export_save(),migrated)

    def test_converted_nineteen_one_and_twenty_zero_armies_keep_original_placement(self):
        game,_,_,_=self.start();state,battle=game.state,game.state.battle
        before=deepcopy(battle['extended']['tactical']);metadata=deepcopy(battle['extended']['deployment'])
        actor=battle['attackers'][0];targets=list(battle['defenders'])
        self.assertFalse({u['id']for u in targets}&set(state.extension['leaders'].values()))
        # Use the shared successful-conversion effect directly. Its loyalty/
        # random gate has separate tests; no extra officer or troops are added.
        for index,target in enumerate(targets):
            battle_allegiance.convert(game,state,battle,actor,target,'attackers','defenders')
            if index==8:
                game._reconcile_factions(state);game.validate(state)
                self.assertEqual((len(battle['attackers']),len(battle['defenders'])),(19,1))
                self.assertEqual(battle['extended']['tactical'],before)
                saved=game.export_save();restored=Campaign(self.catalog);restored.load_save(deepcopy(saved),0)
                self.assertEqual(restored.export_save(),saved)
        game._battle_result(state);game._reconcile_factions(state);game.validate(state)
        self.assertEqual((state.phase,len(battle['attackers']),len(battle['defenders'])),('result',20,0))
        self.assertEqual(battle['extended']['tactical'],before)
        self.assertEqual(battle['extended']['deployment'],metadata)
        saved=game.export_save();restored=Campaign(self.catalog);restored.load_save(deepcopy(saved),0)
        self.assertEqual(restored.export_save(),saved)

    def test_rehashed_bad_provenance_is_rejected_without_touching_state_or_revision(self):
        game,_,_,_=self.start();saved=game.export_save()
        for change in('schema','arrival_city','target_map','arrival_map','paired_source_map',
                      'attacker_zone','defender_zone','policy','extra','missing','wrong_type','missing_grid'):
            with self.subTest(change=change):
                bad=deepcopy(saved);record=bad['state']['battle']['extended']['deployment']
                if change=='schema':record['schema']='bad'
                elif change=='arrival_city':record['arrival_city']='missing-city'
                elif change in('target_map','arrival_map','paired_source_map'):record[change]='original-99'
                elif change=='attacker_zone':record['attacker_zone']=True
                elif change=='defender_zone':record['defender_zone']=-1
                elif change=='policy':record['policy']='compass-guessed'
                elif change=='extra':record['extra']=1
                elif change=='missing':record.pop('arrival_city')
                elif change=='missing_grid':bad['state']['battle']['extended'].pop('tactical')
                else:bad['state']['battle']['extended']['deployment']=[]
                bad['checksum']=digest({k:v for k,v in bad.items()if k!='checksum'})
                revision=game.revision
                with self.assertRaises(GameError):game.load_save(bad,revision)
                self.assertEqual(game.revision,revision)
                self.assertEqual(game.export_save(),saved)

    def test_last_route_city_is_forwarded_instead_of_the_original_source(self):
        game=self.ready_march();current=game.export_save();state=deepcopy(game.state)
        row=state.extension['travel']['marches'][0]
        self.assertNotEqual(ARRIVAL,SOURCE)
        # Current public attacks are one leg. Only this transient input at the
        # arrival service boundary has an extra approach point; it is never
        # committed/exported/loaded as an invalid multi-leg attack save.
        row['quote']['path']=[SOURCE,ARRIVAL,TARGET]
        seen=[];original=game._start_expanded_battle
        def capture(*args,**kwargs):
            seen.append(kwargs['arrival_city'])
            return original(*args,**kwargs)
        with patch.object(game,'_process_march_supply',return_value=0), \
                patch.object(game,'_start_expanded_battle',side_effect=capture):
            game._arrivals(state,{})
        self.assertEqual(seen,[ARRIVAL])
        self.assertEqual(state.battle['source'],SOURCE)
        self.assertEqual(state.battle['extended']['deployment']['arrival_city'],ARRIVAL)
        self.assertEqual(game.export_save(),current,'A controlled service-boundary sample is not committed')
        # The consumed transient march is absent; the resulting actual battle
        # still passes ordinary validation with its recorded approach.
        game.validate(state)
        fresh=deepcopy(state.battle);fresh['extended'].pop('tactical');fresh['extended'].pop('deployment')
        default=battle_deployment.plan(self.catalog,fresh,battle_grid._field(state.battle))
        self.assertNotEqual(default['provenance']['attacker_zone'],
                            state.battle['extended']['deployment']['attacker_zone'])


if __name__=='__main__':unittest.main()
