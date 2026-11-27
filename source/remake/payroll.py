"""Monthly city payroll and once-per-turn loyalty effects."""

from .officers import deserialize_officer_ref, is_generated_ref, ref_sort_key


FIELD = 'payroll'
CLERK_GOLD = 5
CLERK_GRAIN = 10
_EXPERIENCE_PER_WAGE_BAND = 1_000
_WAGE_BAND_COUNT = 50
_FIELDS = {'owner', 'gold', 'grain', 'gold_paid', 'grain_paid', 'turns', 'stopped_turns'}


def _compound_wages(gold, grain, segments):
    """Apply each band's rate to the unrounded wage, including at rate changes."""
    numerator = denominator = 1
    for count, rate_numerator, rate_denominator in segments:
        for _ in range(count):
            numerator *= rate_numerator
            denominator *= rate_denominator
            yield ((gold * numerator + denominator // 2) // denominator,
                   (grain * numerator + denominator // 2) // denominator)


_STARTING_WAGES = ((5, 10), (5, 11))
_WAGES_BY_BAND = _STARTING_WAGES + tuple(_compound_wages(
    5, 11, ((13, 105, 100), (15, 1075, 1000), (_WAGE_BAND_COUNT - 30, 110, 100))))
# Existing shortage receipts retain the amounts due when that month closed.
_LEGACY_WAGE_GOLD = (*range(5, 13), 14, 17, 21, 25, 30, 36, 43, 52, 62, 74, 89, 107, 128)
_PREVIOUS_FIXED_RATE_WAGES = (
    tuple((5 + 7 * band // 15, 10 + band) for band in range(15))
    + ((12, 24),) + tuple(_compound_wages(12, 24, ((34, 10_721, 10_000),)))
)
_PREVIOUS_SEGMENTED_WAGES = _STARTING_WAGES + tuple(_compound_wages(
    5, 11, ((8, 110, 100), (5, 115, 100), (35, 120, 100))))
_RECEIPT_WAGES = frozenset(_WAGES_BY_BAND + _PREVIOUS_FIXED_RATE_WAGES + _PREVIOUS_SEGMENTED_WAGES) | frozenset(
    (gold, 2 * gold) for gold in _LEGACY_WAGE_GOLD)


def officer_wage(experience):
    gold, grain = _WAGES_BY_BAND[experience // _EXPERIENCE_PER_WAGE_BAND]
    return dict(gold=gold, grain=grain)


def wage(officer):
    if is_generated_ref(officer.runtime_id):
        return dict(gold=CLERK_GOLD, grain=CLERK_GRAIN)
    return officer_wage(officer.experience)



def _paid_roster(state, city):
    ruler = state.extension.get('leaders', {}).get(city.owner)
    for ident in city.roster.officer_ids:
        officer = state.officers[ident]
        if ident != ruler and officer.alive and officer.faction_id == city.owner:
            yield officer


def monthly_due(state, city):
    """Gross payroll for the same roster billed by pay_city."""
    due = dict(gold=0, grain=0)
    for officer in _paid_roster(state, city):
        amount = wage(officer)
        due['gold'] += amount['gold']
        due['grain'] += amount['grain']
    return due

def rules():
    return dict(experience_per_band=_EXPERIENCE_PER_WAGE_BAND,
                officer_wages=[dict(gold=gold, grain=grain) for gold, grain in _WAGES_BY_BAND])


def _stopped(row):
    return row['gold_paid'] == row['grain_paid'] == 0


def pay_city(state, city, previous, shortfalls):
    """Use each stockpile independently, sharing shortages proportionally."""
    roster = sorted(_paid_roster(state, city), key=lambda officer: ref_sort_key(officer.runtime_id))
    if not roster:
        return {}
    wages = [wage(officer) for officer in roster]
    totals = {field: sum(due[field] for due in wages) for field in ('gold', 'grain')}
    available = {field: min(getattr(city, field), total) for field, total in totals.items()}
    prefix = dict(gold=0, grain=0)
    receipts = {}
    for officer, due in zip(roster, wages):
        key = str(officer.runtime_id)
        row = dict(owner=city.owner, turns=0, stopped_turns=0, **due)
        for field in totals:
            before = prefix[field] * available[field] // totals[field]
            prefix[field] += due[field]
            row[field + '_paid'] = prefix[field] * available[field] // totals[field] - before
        if row['gold_paid'] < due['gold'] or row['grain_paid'] < due['grain']:
            prior = previous.get(key)
            if prior and prior['owner'] == city.owner:
                row['turns'] = prior['turns']
                if _stopped(row):
                    row['stopped_turns'] = prior['stopped_turns']
            shortfalls[key] = row
        receipts[officer.runtime_id] = row
    city.gold -= available['gold']
    city.grain -= available['grain']
    return receipts


def _loss(row):
    gold, grain = row['gold'], row['grain']
    denominator = 2 * gold * grain
    unpaid = (gold - row['gold_paid']) * grain + (grain - row['grain_paid']) * gold
    return (3 * unpaid + denominator - 1) // denominator


def prune(game, state):
    """Debt belongs to the employer that missed the payment."""
    ledger = state.extension.get(FIELD)
    if ledger is None:
        return
    rows = ledger['shortfalls']
    leaders = state.extension.get('leaders', {})
    for key, row in list(rows.items()):
        ident = deserialize_officer_ref(key, game.catalog.rules)
        officer = state.officers.get(ident)
        if (officer is None or not officer.alive or officer.faction_id != row['owner']
                or ident == leaders.get(row['owner'])):
            del rows[key]
    if not rows:
        del state.extension[FIELD]


def finish_turn(game, state):
    ledger = state.extension.get(FIELD)
    if ledger is None or ledger['last_turn'] >= state.turn:
        return
    prune(game, state)
    if FIELD not in state.extension:
        return
    ledger['last_turn'] = state.turn
    overdue = {}
    leaders = state.extension.get('leaders', {})
    for key, row in ledger['shortfalls'].items():
        row['turns'] += 1
        row['stopped_turns'] += int(_stopped(row))
        if row['stopped_turns'] < 4 and row['turns'] < 5:
            continue
        ident = deserialize_officer_ref(key, game.catalog.rules)
        officer = state.officers[ident]
        if officer.loyalty < 95:
            overdue.setdefault(row['owner'], []).append((ident, row))
    if not overdue:
        return
    from .succession import ruler_relatives
    governors = {row['governor'] for row in state.extension.get('treasury', {}).get('cities', {}).values()}
    for owner, candidates in overdue.items():
        candidates = [(ident, row) for ident, row in candidates if ident not in governors]
        if not candidates:
            continue
        relatives = ruler_relatives(state, leaders.get(owner), [ident for ident, _ in candidates])
        for ident, row in candidates:
            if ident not in relatives:
                officer = state.officers[ident]
                officer.loyalty = max(0, officer.loyalty - _loss(row))


def validate(game, state):
    if FIELD not in state.extension:
        return
    ledger = state.extension[FIELD]
    valid_int = lambda value, low, high: type(value) is int and low <= value <= high
    if (not isinstance(ledger, dict) or set(ledger) != {'last_turn', 'shortfalls'}
            or not valid_int(ledger['last_turn'], 0, state.turn)
            or not isinstance(ledger['shortfalls'], dict) or not ledger['shortfalls']
            or len(ledger['shortfalls']) > len(state.officers)):
        raise ValueError('Payroll ledger')
    for key, row in ledger['shortfalls'].items():
        ident = deserialize_officer_ref(key, game.catalog.rules)
        officer = state.officers.get(ident)
        if (str(ident) != key or not isinstance(row, dict) or set(row) != _FIELDS
                or officer is None or not officer.alive or row['owner'] != officer.faction_id
                or row['owner'] not in game.catalog.factions or row['owner'] == 'neutral'
                or not valid_int(row['turns'], 0, state.turn)
                or not valid_int(row['stopped_turns'], 0, row['turns'])
                or not _stopped(row) and row['stopped_turns'] != 0
                or type(row['gold']) is not int or type(row['grain']) is not int
                or (row['gold'], row['grain']) not in _RECEIPT_WAGES
                or is_generated_ref(ident) and (row['gold'], row['grain']) != (CLERK_GOLD, CLERK_GRAIN)
                or not valid_int(row['gold_paid'], 0, row['gold'])
                or not valid_int(row['grain_paid'], 0, row['grain'])
                or (row['gold_paid'], row['grain_paid']) == (row['gold'], row['grain'])):
            raise ValueError('Payroll shortfall')
