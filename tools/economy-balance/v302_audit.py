"""Observe committed city postings at the actual resource write boundary.

Installed only inside the observer worker. A snapshot checks the postings;
stock differences are never used to fabricate transactions or transport costs.
"""
from collections import Counter
from contextlib import contextmanager
import sys
from unittest.mock import patch

from remake.campaign import City


RESOURCES = ('grain', 'gold')
CATEGORIES = {
    ('campaign', '_monthly_calendar'): 'regular_income',
    ('campaign', '_open_dated_cities'): 'city_founding_transfer',
    ('campaign', '_recruit'): 'recruitment',
    ('domestic', 'month_rollover'): 'civil_bonus',
    ('facilities', 'settle_harvest'): 'harvest_bonus',
    ('city_economy', 'settle_turn_grain'): 'city_consumption',
    ('payroll', '_settle_city'): 'payroll',
    ('logistics', 'dispatch'): 'convoy_load',
    ('logistics', '_unload'): 'convoy_delivery',
    ('logistics', '_dock'): 'convoy_receipt',
    ('logistics', '_begin_journey'): 'convoy_ration_transfer',
    ('transport_emergency', '_take_local'): 'convoy_emergency_refill',
    ('march_supply', 'resupply'): 'march_ration_transfer',
    ('city_development', 'develop'): 'city_development',
    ('strategic_ai', 'personnel_or_recruit'): 'recruitment',
    ('city_economy', 'frontier_maintenance'): 'outpost_maintenance',
    ('facilities', '_execute_trade'): 'market_exchange',
    ('battle_services', 'execute'): 'battle_services',
}


def _totals(state):
    return {(key, resource): getattr(city, resource)
            for key, city in state.cities.items() for resource in RESOURCES} if state else {}


class Audit:
    def __init__(self, writes):
        self.writes = writes
        self.summary = Counter()
        self.errors = 0
        self.writes_seen = self.writes_verified = 0
        self.pending = None

    @contextmanager
    def install(self):
        original = City.__setattr__
        observed = self

        def observe(city, field, value):
            watch = observed.pending
            if watch is not None and field in (*RESOURCES, 'owner'):
                previous = getattr(city, field, 0 if field in RESOURCES else None)
                if previous != value:
                    frame = sys._getframe(1)
                    module = frame.f_globals.get('__name__', '').rsplit('.', 1)[-1]
                    function = frame.f_code.co_name
                    if function == '__init__':
                        parent = frame.f_back
                        if parent:
                            module = parent.f_globals.get('__name__', '').rsplit('.', 1)[-1]
                            function = parent.f_code.co_name
                    category = CATEGORIES.get((module, function), f'{module}.{function}')
                    if module == 'facilities' and ('trade' in function or 'transaction' in function):
                        category = 'market_exchange'
                    watch.append((city.id, getattr(city, 'owner', None), field, previous, value,
                                  category, f'{module}.{function}'))
            original(city, field, value)

        with patch.object(City, '__setattr__', observe):
            yield

    @contextmanager
    def command(self, game, action):
        before = _totals(game.state) if action != 'new' else {}
        previous = game.state
        pending = []
        self.pending = pending
        try:
            yield
        finally:
            self.pending = None
        state = game.state
        if state is previous:
            return
        stamp = dict(command=action, turn=(previous or state).turn,
                     year=(previous or state).year, month=(previous or state).month, day=(previous or state).day)
        after, posted = _totals(state), Counter()
        for city, owner, field, balance_before, balance_after, category, site in pending:
            if field == 'owner':
                if balance_before is not None:
                    self.writes.writerow(dict(stamp, city=city, owner=owner, resource='ownership',
                        balance_before=balance_before, balance_after=balance_after, delta=None,
                        category='ownership_transfer', site=site))
                continue
            delta = balance_after - balance_before
            posted[city, field] += delta
            self.summary[category, field, 'credit' if delta > 0 else 'debit'] += abs(delta)
            self.writes_seen += 1
            self.writes.writerow(dict(stamp, city=city, owner=owner, resource=field,
                balance_before=balance_before, balance_after=balance_after, delta=delta,
                category=category, site=site))
        for city, field in before.keys() | after.keys() | posted.keys():
            expected = before.get((city, field), 0) + posted[city, field]
            actual = after.get((city, field), 0)
            if expected != actual:
                self.errors += 1
                self.writes.writerow(dict(stamp, city=city, owner=state.cities[city].owner if city in state.cities else None,
                    resource=field, balance_before=expected, balance_after=actual, delta=None,
                    category='audit_mismatch', site='command_boundary'))
        self.writes_verified += len(posted)

    def metrics(self):
        return dict(city_resource_mismatches=self.errors, city_postings=self.writes_seen,
                    city_resource_accounts_checked=self.writes_verified,
                    categories=[dict(category=category, resource=resource, direction=direction, amount=amount)
                                for (category, resource, direction), amount in sorted(self.summary.items())])
