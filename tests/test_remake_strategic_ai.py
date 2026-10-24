"""Persistent objectives and real, resource-conserving campaign orders."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from remake.campaign import Campaign, Catalog, canonical
from remake import facilities, treasures
from remake.march_core import using_backend
from remake.march_supply import estimate as march_grain
from remake.strategic_ai import StrategicAI, validate_strategies
from campaign_fixtures import controlled_catalog


def catalog_from_data(data):
    with tempfile.TemporaryDirectory() as temporary:
        path=Path(temporary)/'strategic.json';path.write_text(json.dumps(data,ensure_ascii=False))
        return Catalog(path)


def strategic_catalog(*, defenders=1, troops=900, second=700, budget=3, unsafe=False, flank=False):
    data = deepcopy(controlled_catalog().data)
    data['rules']['ai_max_attacks_per_turn'] = budget
    active = ['nanyang','yingchuan','runan','xiangyang','nanjun','jiangxia']
    data.update(id='controlled-strategic-ai',active_cities=active,
                initial_owners=dict(zip(active,['wei','wei','wei','shu','shu','wu'])))
    rows = data['initial_officers']
    rows[0].update(city='nanyang',troops=700)
    rows[1].update(city='xiangyang',troops=troops)
    rows[2].update(city='yingchuan',troops=second)
    rows[3].update(city='runan',troops=600)
    rows[4].update(city='nanyang' if flank else 'runan',troops=300)
    data['initial_city_resources'] = {key:dict(gold=20 if flank and key=='nanyang' else 0,
        grain=3800,reserves=250 if flank and key=='nanyang' else 0) for key in active}
    data['city_income'] = {key:dict(gold=0,grain=0,reserves=0) for key in active}
    pairs = [('nanyang','xiangyang',20),('yingchuan','xiangyang',10),
             ('runan','nanyang',1),('runan','yingchuan',1),('xiangyang','nanjun',1)]
    if flank:
        pairs.append(('nanyang','jiangxia',1))
    data['links'] = [[a,b] for a,b,_ in pairs]
    data['travel_routes'] = [dict(id=f'strategy:{a}:{b}',**{'from':a,'to':b},mode='land',
        terrain='plain',days=days,distance_km=days*30,land_km=days*30,sea_km=0) for a,b,days in pairs]
    if unsafe:
        for row in data['travel_routes'][:2]:
            row.update(mode='sea',terrain='sea',land_km=0,sea_km=1200)
        data['start_month'] = 7
    if defenders>1:
        current=json.loads((ROOT/'game/data/campaigns/217-07.json').read_text())
        used={r['person_id'] for r in rows}
        for source in current['initial_officers']:
            if source['person_id'] in used:
                continue
            row=deepcopy(source);row.update(city='xiangyang',troops=troops,ruler=False)
            rows.append(row);used.add(row['person_id'])
            if sum(r['city']=='xiangyang' for r in rows)>=defenders:
                break
    return catalog_from_data(data)


class StrategicAITests(unittest.TestCase):
    def new(self, **options):
        game=Campaign(strategic_catalog(**options))
        game.command('new',dict(faction='shu',seed=2026,difficulty='normal'),0)
        return game

    def ai_turn(self,game):
        self.assertEqual(game.state.phase,'city')
        turn=game.state.turn
        game.command('end_turn',{},game.revision)
        game.command('ai',dict(turn=turn),game.revision)

    def resume(self,game):
        saved=game.export_save();other=Campaign(game.catalog);other.load_save(saved,0)
        self.assertEqual(other.export_save(),saved)
        return other

    def test_planning_is_read_only_and_uses_actual_top_ten_defenders(self):
        game=self.new(defenders=13,troops=100)
        before=game.export_save();ai=StrategicAI(game,game.state)
        target=game.state.cities['xiangyang']
        self.assertEqual(len(target.roster.officer_ids),13)
        self.assertEqual(len(ai.defenders(target)),10)
        self.assertEqual(ai.strength(target),1000)
        objective,orders=ai.objective('wei')
        self.assertEqual(objective,'xiangyang')
        self.assertEqual(len(orders),2,'1400 can overcome the actual1000 defenders, even though the full roster totals1300')
        self.assertEqual(game.export_save(),before)
        self.assertEqual(game.state.rng.draws,0)

    def test_preparation_does_not_charge_or_preempt_shared_domestic_allocation(self):
        game=self.new(flank=True)
        city=game.state.cities['nanyang']
        self.assertGreater(city.reserves,0)
        # The old AI-only branch could spend money/grain and give troops to a
        # weaker general before the military official's shared turn-end work.
        for military in (None, city.roster.officer_ids[0]):
            game.state.extension['domestic']['factions']['wei']['military']=military
            before=game.export_save()
            StrategicAI(game,game.state).prepare(city)
            self.assertEqual(game.export_save(),before)

    def test_two_cities_depart_on_different_turns_for_one_real_arrival_and_resume_battle(self):
        game=self.new()
        original=deepcopy(game.state.soldiers)
        self.ai_turn(game)
        plan=game.state.extension['ai_strategy']['wei']
        self.assertEqual((plan['target'],plan['created_turn'],plan['arrival_turn']),('xiangyang',1,3))
        orders={o['source']:o for o in plan['orders']}
        self.assertEqual(orders['nanyang']['departure_turn'],1)
        self.assertIsNotNone(orders['nanyang']['march_id'])
        self.assertEqual(orders['yingchuan']['departure_turn'],2)
        self.assertIsNone(orders['yingchuan']['march_id'])
        self.assertEqual(game.state.rng.draws,0)
        game=self.resume(game)
        if game.state.phase=='arrivals':game.command('arrivals',{},game.revision)
        self.ai_turn(game)
        plan=game.state.extension['ai_strategy']['wei']
        self.assertEqual(plan['created_turn'],1)
        columns=[m for m in game.state.extension['travel']['marches'] if m['kind']=='attack' and m['owner']=='wei']
        self.assertEqual(len(columns),2)
        self.assertEqual({m['arrival_turn'] for m in columns},{3})
        self.assertEqual({m['departure_turn'] for m in columns},{1,2})
        self.assertTrue(all(len(m['officers'])<=10 for m in columns))
        self.assertEqual(game.state.soldiers,original)
        game.command('arrivals',{},game.revision)
        self.assertEqual(game.state.phase,'battle')
        game=self.resume(game)
        battle=game.state.battle['id']
        game.command('retreat',dict(battle_id=battle),game.revision)
        game.command('settle',dict(battle_id=battle),game.revision)
        game.command('arrivals',{},game.revision)
        self.assertEqual(game.state.phase,'city')
        self.assertEqual(game.state.cities['xiangyang'].owner,'wei')
        self.assertFalse(game.state.extension['travel']['marches'])
        self.assertEqual(game.state.turn,3,'Defending, save/resume and processing the second column do not tick the calendar')
        game.validate(game.state)

    def test_long_term_objective_survives_preparation_and_a_new_weaker_target(self):
        game=self.new(second=100,troops=999)
        self.ai_turn(game)
        plan=deepcopy(game.state.extension['ai_strategy']['wei'])
        self.assertEqual(plan['target'],'xiangyang');self.assertFalse(plan['orders'])
        # A newly adjacent neutral city is tempting, but the stored objective
        # persists until its review date while rear reinforcements gather.
        game.catalog.data['travel_routes'].append(dict(id='new-opportunity',**{'from':'nanyang','to':'nanjun'},
            mode='land',terrain='plain',days=1,distance_km=30,land_km=30,sea_km=0))
        # Use the explicit Python reference for this controlled mutable graph.
        with using_backend('python'):
            if game.state.phase=='arrivals':game.command('arrivals',{},game.revision)
            self.ai_turn(game)
        current=game.state.extension['ai_strategy']['wei']
        self.assertEqual(current['target'],'xiangyang')
        self.assertEqual(current['created_turn'],plan['created_turn'])
        self.assertEqual(current['review_turn'],plan['review_turn'])

    def test_rear_reinforcement_loads_normal_queue_rations_and_keeps_a_home_officer(self):
        # Faction appointees present at this source stay home; spare real
        # officers may reinforce under the ordinary guard and ration rules.
        data=deepcopy(strategic_catalog(second=100,troops=999).data)
        used={r['person_id'] for r in data['initial_officers']}
        actual=json.loads((ROOT/'game/data/campaigns/217-07.json').read_text())
        extra=next(r for r in actual['initial_officers'] if r['person_id'] not in used)
        data['initial_officers'].append(dict(extra,city='runan',troops=600,ruler=False))
        game=Campaign(catalog_from_data(data))
        game.command('new',dict(faction='shu',seed=2026,difficulty='normal'),0)
        source=game.state.cities['runan'];ids=set(source.roster.officer_ids);grain=source.grain
        before=deepcopy(game.state.soldiers)
        self.ai_turn(game)
        moving=[m for m in game.state.extension['travel']['marches'] if m['source']=='runan']
        self.assertEqual(len(moving),1)
        self.assertEqual(moving[0]['kind'],'transfer')
        self.assertGreaterEqual(len(moving[0]['officers']),1)
        self.assertLess(len(moving[0]['officers']),len(ids))
        self.assertTrue(ids-set(moving[0]['officers']))
        posts=game.state.extension['domestic']['factions']['wei']
        self.assertTrue({posts['civil'],posts['military']}.isdisjoint(moving[0]['officers']))
        self.assertEqual(source.grain,grain,'The command commits a copy; the old source object is untouched')
        live=game.state.cities['runan']
        loaded = march_grain(game.state, moving[0]['officers'], moving[0]['quote'])
        self.assertEqual(live.grain,grain-loaded)
        self.assertEqual(moving[0]['supply']['loaded'], loaded)
        self.assertEqual(moving[0]['supply']['consumed'], loaded,
            'This one-day transfer has completed its actual route day at the next strategic phase')
        self.assertEqual(game.state.soldiers,before)
        game.validate(game.state)

    def test_attack_budget_uses_troops_officers_and_actual_route_days(self):
        for days, required in ((1, 1), (20, 16), (100, 80)):
            data=deepcopy(strategic_catalog(troops=100).data)
            route=next(r for r in data['travel_routes'] if r['from']=='nanyang' and r['to']=='xiangyang')
            route.update(days=days,distance_km=days*30,land_km=days*30)
            for backend in ('python','rust'):
                with self.subTest(days=days,backend=backend), using_backend(backend):
                    game=Campaign(catalog_from_data(data));game.command('new',dict(faction='shu',seed=2026),0)
                    source,target=(game.state.cities[k] for k in ('nanyang','xiangyang'))
                    source.grain=required
                    before=game.export_save()
                    option=StrategicAI(game,game.state).attack_option(source,target)
                    self.assertIsNotNone(option,'Exactly enough daily rations permits the route')
                    self.assertEqual(option['quote']['days'],days)
                    self.assertEqual(march_grain(game.state,option['officers'],option['quote']),required)
                    self.assertEqual(game.export_save(),before,'Planning never loads or consumes grain')
                    source.grain=required-1
                    self.assertIsNone(StrategicAI(game,game.state).attack_option(source,target))

    def test_coordinated_departure_budget_rechecks_future_month_route_days(self):
        data=deepcopy(strategic_catalog(troops=100).data)
        data['start_month']=6
        data['travel_hazards']['ziwu'].update(**{'from':'nanyang','to':'xiangyang'},
            dry_loss_percent=0,rain_loss_percent=0)
        route=data['travel_routes'][0]
        route.update(days=10,distance_km=300,land_km=300,special='ziwu')
        second=data['travel_routes'][1]
        second.update(days=40,distance_km=1200,land_km=1200)
        for backend in ('python','rust'):
            with self.subTest(backend=backend), using_backend(backend):
                game=Campaign(catalog_from_data(data));game.command('new',dict(faction='shu',seed=2026),0)
                game._complete_turn(game.state);game._complete_turn(game.state)
                self.assertEqual((game.state.month,game.state.day),(6,21))
                source,target=(game.state.cities[k] for k in ('nanyang','xiangyang'))
                source.grain=16
                ai=StrategicAI(game,game.state)
                members=[ai.attack_option(game.state.cities[key],target) for key in ('nanyang','yingchuan')]
                self.assertTrue(all(members))
                self.assertEqual(members[0]['quote']['days'],20)
                self.assertEqual(ai.schedule(members),[],
                    'Holding the June column into July needs 40 days of grain, not its old 20-day loading budget')
                source.grain=32
                before=game.export_save()
                orders=ai.schedule(members)
                self.assertEqual(len(orders),2)
                order=next(o for o in orders if o['source']=='nanyang')
                quote=ai.quote(source,target,order['mode'],adjacent=True,departure=order['departure_turn'])
                self.assertEqual((ai.month_at(order['departure_turn']),quote['days']),(7,40))
                self.assertEqual(march_grain(game.state,order['officers'],quote),32)
                self.assertEqual(game.export_save(),before)
                while game.state.turn < order['departure_turn']:
                    game._complete_turn(game.state)
                self.assertEqual((game.state.month,game.state.day),(7,1))
                source.grain=31
                declined=dict(orders=[deepcopy(order)])
                before=game.export_save()
                self.assertFalse(ai.depart(source,declined),
                    'Departure rechecks the actual rainy-month loading budget after earlier city spending')
                self.assertFalse(declined['orders'])
                self.assertEqual(game.export_save(),before)
                source.grain=32
                self.assertTrue(ai.depart(source,dict(orders=[deepcopy(order)])))
                march=game.state.extension['travel']['marches'][0]
                self.assertEqual((march['departure_month'],march['quote']['days']),(7,40))
                self.assertEqual(march['supply']['loaded'],32)
                self.assertEqual(march['supply']['consumed'],0)
                self.assertEqual(source.grain,0)
                # This fixture calls the shared departure service directly,
                # outside command()'s governor synchronization boundary.
                treasures.synchronize(game,game.state)
                game.validate(game.state)

    def test_due_column_with_insufficient_current_grain_is_cancelled_without_side_effects(self):
        game=self.new(troops=100)
        source,target=(game.state.cities[k] for k in ('nanyang','xiangyang'))
        ai=StrategicAI(game,game.state)
        option=ai.attack_option(source,target)
        order=dict(source=source.id,target=target.id,mode=option['mode'],officers=option['officers'],
            departure_turn=game.state.turn,arrival_turn=game.state.turn+option['quote']['turns'],march_id=None)
        source.grain=15
        plan=dict(orders=[order])
        before=game.export_save()
        self.assertFalse(ai.depart(source,plan))
        self.assertFalse(plan['orders'])
        self.assertEqual(game.export_save(),before)

    def test_reinforcement_checks_each_selected_officers_actual_troops(self):
        data=deepcopy(strategic_catalog(second=100,troops=999).data)
        used={r['person_id'] for r in data['initial_officers']}
        actual=json.loads((ROOT/'game/data/campaigns/217-07.json').read_text())
        extra=next(r for r in actual['initial_officers'] if r['person_id'] not in used)
        data['initial_officers'].append(dict(extra,city='runan',troops=600,ruler=False))
        # Twenty days for each rear approach: the remaining 600-troop general
        # needs 14 grain, rather than the old fixed five-grain per-person fee.
        for route in data['travel_routes'][2:4]:
            route.update(days=20,distance_km=600,land_km=600)
        for backend in ('python','rust'):
            with self.subTest(backend=backend), using_backend(backend):
                game=Campaign(catalog_from_data(data));game.command('new',dict(faction='shu',seed=2026),0)
                source=game.state.cities['runan'];source.grain=13
                before=game.export_save()
                self.assertFalse(StrategicAI(game,game.state).reinforce(source,dict(target=None)))
                self.assertEqual(game.export_save(),before)
                source.grain=14
                ai=StrategicAI(game,game.state)
                self.assertTrue(ai.reinforce(source,dict(target=None)))
                march=game.state.extension['travel']['marches'][0]
                self.assertEqual(len(march['officers']),1)
                self.assertEqual(game.state.officers[march['officers'][0]].troops,600)
                self.assertEqual(march['quote']['days'],20)
                self.assertEqual(march['supply']['loaded'],14)
                self.assertEqual(march['supply']['consumed'],0)
                self.assertEqual(source.grain,0)
                self.assertEqual(game.state.rng.draws,0)
                game.validate(game.state)

    def test_segment_rations_forecast_friendly_stops_neutral_transit_and_rounding_credit(self):
        for backend in ('python','rust'):
            for neutral in (False,True):
                with self.subTest(backend=backend,neutral=neutral), using_backend(backend):
                    data=deepcopy(strategic_catalog().data)
                    pairs=[('runan','nanyang',20),('nanyang','yingchuan',20),('yingchuan','xiangyang',10)]
                    data['links']=[[a,b] for a,b,_ in pairs]
                    data['travel_routes']=[dict(id=f'segments:{a}:{b}',**{'from':a,'to':b},mode='land',
                        terrain='plain',days=days,distance_km=days*30,land_km=days*30,sea_km=0) for a,b,days in pairs]
                    if neutral:
                        data['initial_owners']['nanyang']='neutral'
                        for row in data['initial_officers']:
                            if row['city']=='nanyang':row['city']='runan'
                        next(f for f in data['factions'] if f['id']=='wei')['city']='runan'
                    game=Campaign(catalog_from_data(data));game.command('new',dict(faction='shu',seed=2026),0)
                    source,middle,target=(game.state.cities[k] for k in ('runan','nanyang','yingchuan'))
                    ident=next(i for i in source.roster.officer_ids if game.state.officers[i].troops==600)
                    quote=game._travel_path(game.state,source.id,target.id,'wei','land')
                    self.assertEqual(quote['path'],['runan','nanyang','yingchuan'])
                    source.grain=14;middle.grain=0
                    ai=StrategicAI(game,game.state)
                    self.assertEqual(march_grain(game.state,[ident],quote),28 if neutral else 14)
                    self.assertFalse(ai.provisioned(source,[ident],quote))
                    if neutral:
                        source.grain=28
                        self.assertTrue(ai.provisioned(source,[ident],quote),'Neutral transit cannot refill but fully carried grain can pass')
                    else:
                        middle.grain=13
                        self.assertFalse(ai.provisioned(source,[ident],quote),'A known shortage at the next friendly stop prevents an intentional AI starvation march')
                        middle.grain=14
                        before=game.export_save()
                        self.assertTrue(ai.provisioned(source,[ident],quote))
                        self.assertEqual(game.export_save(),before,'Route budgeting never reserves supplies or changes RNG during planning')
            # A 300-soldier officer uses 400 ration units per day. One grain
            # loaded for the first one-day leg also covers the next one-day
            # leg, so the intermediate city can legitimately have no grain.
            with self.subTest(backend=backend,rounding=True), using_backend(backend):
                data=deepcopy(strategic_catalog().data)
                pairs=[('runan','nanyang',1),('nanyang','yingchuan',1)]
                data['links']=[[a,b] for a,b,_ in pairs]
                data['travel_routes']=[dict(id=f'credit:{a}:{b}',**{'from':a,'to':b},mode='land',terrain='plain',
                    days=days,distance_km=30,land_km=30,sea_km=0) for a,b,days in pairs]
                game=Campaign(catalog_from_data(data));game.command('new',dict(faction='shu',seed=2026),0)
                source=game.state.cities['runan'];source.grain=1;game.state.cities['nanyang'].grain=0
                ident=next(i for i in source.roster.officer_ids if game.state.officers[i].troops==300)
                quote=game._travel_path(game.state,'runan','yingchuan','wei','land')
                self.assertEqual(march_grain(game.state,[ident],quote),1)
                self.assertTrue(StrategicAI(game,game.state).provisioned(source,[ident],quote))

    def test_real_ai_reinforcement_waits_for_segment_food_then_refills_without_starvation(self):
        data=deepcopy(strategic_catalog(second=100,troops=999).data)
        used={r['person_id'] for r in data['initial_officers']}
        actual=json.loads((ROOT/'game/data/campaigns/217-07.json').read_text())
        extra=next(r for r in actual['initial_officers'] if r['person_id'] not in used)
        data['initial_officers'].append(dict(extra,city='runan',troops=600,ruler=False))
        pairs=[('runan','nanyang',20),('nanyang','yingchuan',20),('yingchuan','xiangyang',10)]
        data['links']=[[a,b] for a,b,_ in pairs]
        data['travel_routes']=[dict(id=f'ai-refill:{a}:{b}',**{'from':a,'to':b},mode='land',terrain='plain',
            days=days,distance_km=days*30,land_km=days*30,sea_km=0) for a,b,days in pairs]
        for backend in ('python','rust'):
            with self.subTest(backend=backend), using_backend(backend):
                game=Campaign(catalog_from_data(data));game.command('new',dict(faction='shu',seed=2026),0)
                source,middle,target=(game.state.cities[k] for k in ('runan','nanyang','yingchuan'))
                source.grain=14;middle.grain=13
                plan=dict(target='xiangyang')
                self.assertFalse(StrategicAI(game,game.state).reinforce(source,plan))
                self.assertFalse(game.state.extension['travel']['marches'])
                middle.grain=14
                self.assertTrue(StrategicAI(game,game.state).reinforce(source,plan))
                march=game.state.extension['travel']['marches'][0];ident=march['officers'][0]
                self.assertEqual((march['target'],march['quote']['days'],march['supply']['loaded']),('yingchuan',40,14))
                self.assertEqual(source.grain,0);self.assertEqual(middle.grain,14)
                initial=deepcopy(game.state.soldiers)
                for _ in range(4):
                    game._complete_turn(game.state)
                    game.validate(game.state)
                self.assertEqual(march['supply']['route_days'],40)
                self.assertEqual(march['supply']['received'],14)
                self.assertEqual(march['supply']['shortage_days'],0)
                self.assertEqual(march['supply']['lost'],0)
                self.assertEqual(middle.grain,0)
                self.assertEqual(game.state.soldiers,initial)
                self.assertEqual(game.state.rng.draws,0)
                game.command('arrivals',{},game.revision)
                self.assertIn(ident,game.state.cities[target.id].roster.officer_ids)
                self.assertFalse(game.state.extension['travel']['marches'])
                game.validate(game.state)

    def test_dangerous_shortcuts_are_rejected_without_random_weather_rolls(self):
        game=self.new(unsafe=True)
        ai=StrategicAI(game,game.state);before=game.export_save()
        self.assertIsNone(ai.attack_option(game.state.cities['nanyang'],game.state.cities['xiangyang']))
        self.assertEqual(game.export_save(),before)
        self.ai_turn(game)
        self.assertFalse([m for m in game.state.extension['travel']['marches'] if m['kind']=='attack'])
        self.assertEqual(game.state.rng.draws,0)

    def test_safe_longer_land_option_is_queued_instead_of_monsoon_shortcut(self):
        data=deepcopy(strategic_catalog(unsafe=True,troops=100).data)
        # A controlled northeast heading makes the storm-prone sea route
        # faster than the safe road, so choosing land is a real risk decision.
        data['city_coordinates']['nanyang']=[110,30]
        data['city_coordinates']['xiangyang']=[112,32]
        data['travel_routes'].append(dict(id='safe-longer-road',**{'from':'nanyang','to':'xiangyang'},
            mode='land',terrain='plain',days=50,distance_km=1500,land_km=1500,sea_km=0))
        game=Campaign(catalog_from_data(data));game.command('new',dict(faction='shu',seed=2026),0)
        ai=StrategicAI(game,game.state)
        option=ai.attack_option(game.state.cities['nanyang'],game.state.cities['xiangyang'])
        self.assertEqual(option['mode'],'land')
        self.assertEqual(option['quote']['routes'][0]['id'],'safe-longer-road')
        self.ai_turn(game)
        column=next(m for m in game.state.extension['travel']['marches'] if m['kind']=='attack')
        self.assertEqual(column['quote']['routes'][0]['id'],'safe-longer-road')
        self.assertEqual(column['risks'],[])
        self.assertEqual(game.state.rng.draws,0)

    def test_reinforcement_does_not_overbook_a_99_officer_city(self):
        game=self.new(defenders=99,troops=1)
        origin,target=game.state.cities['xiangyang'],game.state.cities['yingchuan']
        leader=game.state.extension['leaders']['shu']
        for ident in list(origin.roster.officer_ids):
            if ident==leader:
                continue
            origin.roster.officer_ids.remove(ident);target.roster.officer_ids.append(ident)
            game.state.officers[ident].faction_id='wei'
        self.assertEqual(len(target.roster.officer_ids),99)
        game.validate(game.state)
        self.ai_turn(game)
        self.assertFalse([m for m in game.state.extension['travel']['marches'] if m['kind']=='transfer' and m['target']=='yingchuan'])
        self.assertTrue(all(len(c.roster.officer_ids)<=99 for c in game.state.cities.values()))
        game.validate(game.state)

    def test_an_exposed_flank_retains_real_guards_after_shared_allocation(self):
        game=self.new(flank=True)
        self.ai_turn(game)
        city=game.state.cities['nanyang'];marching=game._march_ids(game.state)
        self.assertGreaterEqual(sum(game.state.officers[i].troops for i in city.roster.officer_ids if i not in marching),200)
        receipts=[r for r in game.state.extension['domestic']['reports']
                  if r['city']==city.id and r['kind']=='allocation']
        self.assertTrue(receipts)
        self.assertEqual(receipts[-1]['details']['soldiers'],250)
        self.assertEqual(city.reserves,0,'The military official puts all leftover reserves into actual local troops')
        game.validate(game.state)

    def test_impossible_attacks_and_zero_budget_do_not_create_an_army(self):
        for options in (dict(defenders=13,troops=999),dict(budget=0)):
            with self.subTest(options=options):
                game=self.new(**options)
                self.ai_turn(game)
                self.assertFalse([m for m in game.state.extension['travel']['marches'] if m['kind']=='attack'])
                self.assertFalse(game.state.extension['ai_strategy']['wei']['orders'])
                game.validate(game.state)

    def test_supply_and_difficulty_budgets_bound_actual_orders_without_bonus_resources(self):
        for level,expected in (('easy',0),('normal',1),('hard',1)):
            with self.subTest(difficulty=level):
                catalog=strategic_catalog()
                game=Campaign(catalog);game.command('new',dict(faction='shu',seed=2026,difficulty=level),0)
                before=deepcopy(game.state.soldiers)
                self.ai_turn(game)
                attacks=[m for m in game.state.extension['travel']['marches'] if m['kind']=='attack']
                self.assertEqual(len(attacks),expected,'Easy cannot assemble the two columns this defended objective needs')
                self.assertEqual(game.state.soldiers,before)
                # An idle AI may sell actual opening treasure. This is an
                # explicit asset conversion, never a difficulty gold bonus.
                sales=[event for event in game.state.extension['events']['items']
                       if event['kind']=='treasure_sold']
                sold={key:sum(event['details']['amount'] for event in sales if event['city_ids']==[key])
                      for key in game.state.cities}
                self.assertEqual(sum(sold.values()),game.state.extension['treasury']['ledger']['sold'])
                for key,city in game.state.cities.items():
                    self.assertEqual(city.gold,sold[key]*100)
                treasures.validate(game,game.state)
        game=self.new()
        for city in game.state.cities.values():city.grain=0
        self.ai_turn(game)
        self.assertFalse(game.state.extension['travel']['marches'])
        self.assertTrue(all(c.grain==0 for c in game.state.cities.values()))

    def test_strategy_receipts_reject_duplicate_officers_and_altered_arrival(self):
        game=self.new();self.ai_turn(game)
        for kind in ('duplicate','arrival','march'):
            state=deepcopy(game.state);plan=state.extension['ai_strategy']['wei']
            if kind=='duplicate':plan['orders'][1]['officers']=list(plan['orders'][0]['officers'])
            elif kind=='arrival':plan['orders'][1]['arrival_turn']+=1
            else:plan['orders'][0]['departure_turn']+=1
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                validate_strategies(game,state)

    def test_supply_delays_and_returning_columns_keep_immutable_strategy_receipts(self):
        game=self.new();self.ai_turn(game)
        state=deepcopy(game.state)
        march=next(m for m in state.extension['travel']['marches'] if m['owner']=='wei' and m['kind']=='attack')
        original=deepcopy(march['mission'])
        march['arrival_turn']+=2
        march['status']='waiting'
        validate_strategies(game,state)
        march['target']='runan';march['status']='returning'
        march['supply']['retreat_requested']=True
        validate_strategies(game,state)
        self.assertEqual(march['mission'],original,'Supply delays and actual return routes do not rewrite the attack order')
        for field,value in [('source','runan'),('target','nanjun'),('kind','transfer'),('mode','sea'),
                            ('departure_turn',original['departure_turn']+1),('arrival_turn',original['arrival_turn']+1)]:
            with self.subTest(field=field):
                bad=deepcopy(state)
                altered=next(m for m in bad.extension['travel']['marches'] if m['id']==march['id'])
                altered['mission'][field]=value
                with self.assertRaisesRegex(ValueError,'AI march does not match'):
                    validate_strategies(game,bad)

    def test_changed_city_ownership_cancels_an_unlaunched_column_legally(self):
        game=self.new();self.ai_turn(game)
        if game.state.phase=='arrivals':game.command('arrivals',{},game.revision)
        city=game.state.cities['yingchuan']
        for ident in list(city.roster.officer_ids):
            game.state.cities['runan'].roster.officer_ids.append(ident)
        city.roster.officer_ids.clear();city.owner='neutral'
        from remake.civil_staff import synchronize
        synchronize(game, game.state, checks=False)
        from remake import logistics, domestic
        logistics.synchronize(game,game.state)
        domestic.synchronize(game,game.state)
        treasures.synchronize(game,game.state)
        facilities.synchronize(game,game.state)
        game.validate(game.state);game=self.resume(game)
        self.ai_turn(game)
        plan=game.state.extension['ai_strategy']['wei']
        self.assertFalse([o for o in plan['orders'] if o['source']=='yingchuan' and o['march_id'] is None])
        validate_strategies(game,game.state)

    def test_sixteen_turn_campaign_is_deterministic_across_backends_and_conserves_troops(self):
        catalog=strategic_catalog(unsafe=True,budget=0)
        games=[]
        for backend in ('python','rust'):
            with using_backend(backend):
                game=Campaign(catalog);game.command('new',dict(faction='shu',seed=2026,difficulty='normal'),0)
                for turn in range(16):
                    if game.state.phase=='arrivals':game.command('arrivals',{},game.revision)
                    self.ai_turn(game)
                    game.validate(game.state)
                    self.assertTrue(all(c.gold>=0 and c.grain>=0 and c.reserves>=0 for c in game.state.cities.values()))
                    game=self.resume(game)
                games.append(game)
        self.assertEqual(canonical(games[0].to_dict()),canonical(games[1].to_dict()))
        self.assertEqual(games[0].state.rng.draws,0)
        self.assertEqual(games[0].state.soldiers['lost'],0)

    def test_sustained_actual_ai_war_economy_and_arrivals_survive_repeated_saves(self):
        data=deepcopy(strategic_catalog().data)
        data['initial_owners']['xiangyang']='wu'
        for row in data['initial_officers']:
            if row['person_id']=='san14-candidate-0952':row.update(city='nanjun',troops=180)
            if row['person_id']=='san14-candidate-0001':row.update(city='xiangyang',troops=900)
        data['links']=[p for p in data['links'] if set(p)!={'xiangyang','nanjun'}]
        data['travel_routes']=[r for r in data['travel_routes'] if {r['from'],r['to']}!={'xiangyang','nanjun'}]
        data['initial_city_resources']={key:dict(gold=1200,grain=3800,reserves=250) for key in data['active_cities']}
        catalog=catalog_from_data(data)
        results=[]
        for backend in ('python','rust'):
            with using_backend(backend):
                # With the faction-wide officials, seed3 produces actual
                # casualties. A surrender-only outcome would not exercise the
                # casualty/save ledger that this long replay must cover.
                game=Campaign(catalog);game.command('new',dict(faction='shu',seed=3),0)
                for _ in range(18):
                    if game.state.phase=='arrivals':game.command('arrivals',{},game.revision)
                    self.assertEqual(game.state.phase,'city')
                    self.ai_turn(game)
                    game.validate(game.state)
                    game=self.resume(game)
                if game.state.phase=='arrivals':game.command('arrivals',{},game.revision)
                self.assertTrue(game.state.settled_battles,'This long fixture executes real battles, not just an idle clock')
                self.assertGreater(game.state.soldiers['lost'],0)
                self.assertGreater(game.state.soldiers['recruited'],0)
                self.assertTrue(all(c.gold>=0 and c.grain>=0 and c.reserves>=0 for c in game.state.cities.values()))
                results.append(game.export_save())
        self.assertEqual(canonical(results[0]),canonical(results[1]))


if __name__=='__main__':unittest.main()
