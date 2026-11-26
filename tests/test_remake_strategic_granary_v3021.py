"""Outstanding grain, physical priorities and candidate save boundaries."""
from dataclasses import replace
from random import Random
from unittest import TestCase
from unittest.mock import patch

from remake import (faction_economy, grain_units, granary_demand, granary_planning, logistics,
                    strategic_granary as reserve, transport_emergency as emergency, winter_weather)
from remake.campaign import Campaign
from remake.errors import GameError
from test_remake_regional_market import OWNER, SOURCE, TARGET
from test_remake_strategic_granary import book, command, start


def forecast(stock, timeline, conditional=None):
    gaps, end, before = faction_economy.balance(stock, timeline)
    return faction_economy.Forecast(1, next((turn for turn, missing in gaps if missing), None),
        gaps, 0, 0, before, {i: row[2] for i,row in enumerate(timeline,1)}, timeline, logistics.LIMIT-stock,
        gaps[0][1], conditional_receipts=conditional or {})


class CandidateDemandTests(TestCase):
    def test_dated_partial_and_sufficient_receipts(self):
        timeline = ((0,0,3_000),(0,10_000,0))
        demand = granary_demand.calculate(0,forecast(0,timeline))
        self.assertEqual(demand.after(0),(2,7_000))
        self.assertEqual(demand.after(2),(None,0))
        self.assertEqual(granary_demand.describe(demand)['covered'],3_000)
        self.assertIsNone(granary_demand.calculate(
            0,forecast(0,((0,0,10_000),(0,10_000,0)))).first)
        late = granary_demand.calculate(0,forecast(0,((0,0,0),(0,10_000,3_000),(0,3_000,0))))
        self.assertEqual(late.after(1),(2,10_000))
        self.assertEqual(late.after(2),(None,0))

    def test_risk_can_cover_only_payments_after_possible_arrival(self):
        timeline = ((0,0,0),(0,4_000,0),(0,0,0),(0,6_000,0))
        demand = granary_demand.calculate(0,forecast(0,timeline,{3:3_000}),holds=[(3,1_000)])
        self.assertEqual(demand.after(0),(2,6_000))
        self.assertEqual(demand.after(2),(4,2_000))
        self.assertEqual(granary_demand.describe(demand)['contingent_coverage'],4_000)
        self.assertEqual(granary_demand.describe(demand)['committed_inbound'],1_000)

    def test_one_thousand_flows_match_independent_fifo_installments(self):
        random = Random(30210)
        for _ in range(1_000):
            stock = random.randrange(15_000)
            timeline = tuple(tuple(random.randrange(15_000) for _ in range(3)) for x in range(9))
            holds = [(random.randrange(1,10),random.randrange(15000)) for _ in range(3)]
            risk = {random.randrange(1,10):random.randrange(15000) for _ in range(3)}
            demand = granary_demand.calculate(stock,forecast(stock,timeline,risk),holds=holds)
            actual = stock
            for index, (produced, bill, received) in enumerate(timeline,1):
                actual += produced
                debit = min(bill, actual)
                self.assertEqual(demand.remaining[index-1], (index, bill-debit))
                actual -= debit
                actual += received+risk.get(index,0)+sum(n for i,n in holds if i == index)
                self.assertEqual(demand.balance_at_end[index-1],actual)
            result = granary_demand.describe(demand)
            self.assertEqual(result['baseline'],result['covered']+result['contingent_coverage']+result['uncovered'])

    def test_existing_real_order_leaves_a_partial_demand_visible(self):
        game = start(version=3021, proactive=True)
        book(game, 3_000)
        command(game, 'dispatch', order=1)
        state = game.state
        convoy, = logistics._pool(state)['convoys']
        with grain_units.using(state):
            plan = granary_planning._plan(game,state,OWNER)
            first, = plan.cities[TARGET].convoy_receipts
            self.assertEqual(first['convoy'],convoy['id'])
            self.assertEqual(first['status'],'reliable')
            eta, expected = first['eta'], first['net']
            state.cities[TARGET].grain = 0
            timeline = tuple((0,10_000 if i==eta+1 else 0,expected if i==eta else 0)
                             for i in range(1,10))
            actual = forecast(0,timeline)
            plan.cities[TARGET] = replace(actual,convoy_receipts=[first])
            self.assertEqual(granary_demand.for_city(game,state,plan,TARGET).after(eta),(eta+1,10_000-expected))
            convoy['journeys'][-1]['supply']['waiting'] = True
            facts = granary_demand.inbound(game,state,convoy,expected)
            self.assertEqual(facts['status'],'blocked')
            self.assertIsNone(facts['conditional_eta'])
            actual_receipts = granary_planning._plan(game,state,OWNER).cities[TARGET]
            self.assertFalse(any(actual_receipts.receipts.values()))


class CandidateProtectionTests(TestCase):
    def test_one_thousand_custody_values_partition_the_real_warehouse(self):
        game = start(version=3021, coordination=True)
        state, random = game.state, Random(30211)
        city = state.cities[SOURCE]
        for _ in range(1_000):
            city.grain = random.randrange(10_000)
            reserved = random.randrange(city.grain+1)
            reserve.change_reserve(state,city,reserved,'manual')
            book = faction_economy.Commitments()
            for label in ('march:1:0','granary:1','relay:2'):
                item = faction_economy.Commitment(label,OWNER,SOURCE,TARGET,random.randrange(1,15_000),3,1,9)
                book.held[item.commitment_id] = item
            held = reserve.protection(state,city,book=book)
            self.assertEqual(min(city.grain,book.amount(SOURCE)),held['committed'])
            self.assertEqual(city.grain,held['free']+held['strategic']+held['military']+held['unshipped']+held['relay'])
            self.assertGreaterEqual(min(held.values()),0)

    def test_priority_release_preserves_floor_and_creates_no_stock(self):
        game = start(version=3021, coordination=True)
        state = game.state
        source = state.cities[SOURCE]
        reserve.change_reserve(state,source,40_000,'manual')
        promises = faction_economy.Commitments()
        item = faction_economy.Commitment('march:9:0',OWNER,SOURCE,TARGET,8_000,3,1,9)
        promises.held[item.commitment_id] = item
        with patch.object(faction_economy,'pending',return_value=promises):
            before = source.grain
            with self.assertRaises(GameError):
                reserve.spend_for_dispatch(state,source,34_000,1,9_000)
            self.assertEqual(reserve.reserve_grain(state,source),40_000)
            reserve.spend_for_dispatch(state,source,25_000,1,9_000)
            self.assertEqual(source.grain,before)
            self.assertEqual(reserve.reserve_grain(state,source),17_000)
            self.assertEqual(reserve.reserve_row(state,source)['reason'],'cross_city_urgent')

    def test_real_order_roundtrip_preserves_version_cargo_and_existing_completions(self):
        for version in (302,3021):
            game = start(version=version)
            book(game)
            command(game,'dispatch',order=1)
            for compact in (False, True):
                saved = game.export_save(compact=compact)
                loaded = Campaign(game.catalog)
                loaded.load_save(saved,0)
                self.assertEqual(loaded.export_save(compact=compact),saved)
                self.assertEqual(loaded.state.extension[reserve.FIELD],version)
            before = game.export_save()
            if version == 3021:
                self.assertIn('demand',game.view()['catalog']['strategic_granary']['cities'][TARGET])
            self.assertEqual(game.export_save(),before)

    def test_source_escort_diagnostics_use_actual_qualification(self):
        game = start(version=3021, proactive=True)
        state = game.state
        events = []
        with reserve.observing(lambda kind,row: events.append((kind,row))), grain_units.using(state):
            plan = granary_planning._plan(game,state,OWNER)
            network = granary_planning.Network(game,state,OWNER,plan,automatic=True)
            for ident in state.cities[SOURCE].roster.officer_ids:
                state.extension['officer_actions'][str(ident)] = state.turn
            self.assertFalse(network.collect([TARGET],[SOURCE]))
        self.assertEqual(network.stats['source_evaluations'],1)
        event, = [row for kind,row in events if kind=='source_eligibility']
        self.assertEqual(event['reason'],'no_eligible_escort')
        self.assertGreater(event['exclusions'].get('officer_already_acted',0),0)

    def test_return_guard_keeps_enroute_and_unfunded_hostile_units_in_play(self):
        with winter_weather.experiment(5,adjustments=winter_weather.CORRECTIONS), emergency.experiment(3):
            game = start(version=3021, return_safety=True)
        book(game)
        command(game,'dispatch',order=1)
        row, = logistics._pool(game.state)['convoys']
        before = game.export_save()
        self.assertFalse(emergency.review_return_node(game,game.state,row,1))
        self.assertEqual(game.export_save(),before)
