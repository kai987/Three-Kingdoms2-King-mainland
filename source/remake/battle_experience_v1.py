"""Versioned combat journal and deterministic experience settlement."""

from dataclasses import dataclass
from decimal import Decimal, localcontext

from .officers import MAX_BATTLE_PARTICIPANTS, OFFICER_TROOP_CAP, is_generated_ref, ref_sort_key


FIELD = 'experience_v1'
SIDES = ('attackers', 'defenders')
DIMENSIONS = ('participation', 'troopCommitment', 'kills', 'duelDamage', 'defection',
              'troopPreservation', 'damageTaken')


@dataclass(frozen=True)
class Settings:
    soldiers_per_point: int = 200
    minimum: int = 2
    guarantee: Decimal = Decimal('0.20')
    competition: Decimal = Decimal('0.80')
    conversion_troops: int = 2
    conversion_officers: int = 2000
    duel_score: int = 1000
    duel_received: int = 1000
    weights: tuple = (10, 10, 40, 10, 10, 5, 15)

    def __post_init__(self):
        if type(self.soldiers_per_point) is not int or self.soldiers_per_point < 1:
            raise ValueError('Invalid experience rate')
        if type(self.minimum) is not int or self.minimum < 2:
            raise ValueError('Invalid minimum experience')
        if len(self.weights) != len(DIMENSIONS):
            raise ValueError('Invalid experience dimensions')
        for field in ('guarantee', 'competition', 'conversion_troops', 'conversion_officers',
                      'duel_score', 'duel_received'):
            object.__setattr__(self, field, _rate(getattr(self, field)))
        object.__setattr__(self, 'weights', tuple(map(_rate, self.weights)))
        if self.guarantee + self.competition != 1:
            raise ValueError('Invalid experience side shares')


def _rate(value):
    if not isinstance(value, (int, float, Decimal)) or isinstance(value, bool):
        raise ValueError('Invalid experience coefficient')
    value = Decimal(str(value))
    if not value.is_finite() or value < 0:
        raise ValueError('Invalid experience coefficient')
    return value


DEFAULT = Settings()


def initialize(battle):
    battle['extended'][FIELD] = {
        'version': 1,
        'opening': [[unit['id'], side, unit['troops']] for side in SIDES for unit in battle[side]],
        'events': [],
    }


def append(journal, event):
    """Commit a sequential receipt. An exact replay has no effect."""
    events = journal['events']
    sequence = event['id']
    if type(sequence) is not int or sequence < 1:
        raise ValueError('Invalid experience event ID')
    if sequence <= len(events):
        if event != events[sequence - 1]:
            raise ValueError('Conflicting experience event ID')
    elif sequence == len(events) + 1:
        events.append(dict(event))
    else:
        raise ValueError('Missing experience event')


def record(battle, kind, **details):
    journal = battle['extended'].get(FIELD)
    if journal is None:
        return
    event = dict(id=len(journal['events']) + 1, day=battle['round'], kind=kind, **details)
    for role in ('actor', 'target'):
        if role in details:
            ident = details[role]
            side, unit = next((side, unit) for side in SIDES for unit in battle[side] if unit['id'] == ident)
            prior = details['amount'] if role == 'target' and kind in {'damage', 'loss'} else 0
            event[role + '_before'] = [side, unit['troops'] + prior]
    append(journal, event)


def _amount(value, *, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('Invalid experience event quantity')
    return value


def _side(side):
    if side not in SIDES:
        raise ValueError('Invalid experience side')
    return side


def _identity(ident):
    if type(ident) is int and 0 <= ident < 65535 or is_generated_ref(ident):
        return ident
    raise ValueError('Invalid experience officer')


def _union(left, right):
    merged = []
    for start, end in sorted([*left, *right]):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _count(spans):
    return sum(end - start for start, end in spans)


def _overlap(left, right):
    return sum(max(0, min(b, d) - max(a, c)) for a, b in left for c, d in right)


def _take(spans, amount):
    """Remove a deterministic suffix, splitting the last batch if needed."""
    removed = []
    while amount:
        start, end = spans.pop()
        split = max(start, end - amount)
        removed.append((split, end))
        if split > start:
            spans.append((start, split))
        amount -= end - split
    return removed


@dataclass
class Contribution:
    committed: tuple = ()
    engaged: bool = False
    kills: int = 0
    losses: int = 0
    preservation_losses: int = 0
    ordinary: int = 0
    duel_hp: int = 0
    received_hp: int = 0
    duel: Decimal = Decimal(0)
    received: Decimal = Decimal(0)
    converts: int = 0
    converted_troops: int = 0

    @property
    def troops(self):
        return _count(self.committed)

    def raw(self, settings):
        troops = self.troops
        return (Decimal(1), Decimal(troops), Decimal(self.kills), self.duel,
                self.converts * settings.conversion_officers + self.converted_troops * settings.conversion_troops,
                Decimal(troops - self.preservation_losses) / troops if troops else Decimal(0),
                Decimal(troops * self.ordinary).sqrt() + settings.duel_received * self.received)


@dataclass
class Column:
    side: str
    troops: list
    present: bool = True


class Replay:
    """Fold receipts with interval IDs. No object is created per soldier."""

    def __init__(self, journal):
        if (not isinstance(journal, dict) or set(journal) != {'version', 'opening', 'events'}
                or type(journal['version']) is not int or journal['version'] != 1
                or not isinstance(journal['opening'], list) or not isinstance(journal['events'], list)):
            raise ValueError('Invalid battle experience journal')
        self.columns = {}
        self.rows = {}
        self.duel_stages = {}
        self.total = 0
        self.engaged = []
        self.losses = dict.fromkeys(SIDES, 0)
        for ident, side, strength in journal['opening']:
            self.arrive(ident, side, strength)
        self.opening = {side: sum(col.side == side for col in self.columns.values()) for side in SIDES}
        day = 1
        for sequence, event in enumerate(journal['events'], 1):
            if not isinstance(event, dict) or type(event.get('id')) is not int or event['id'] != sequence:
                raise ValueError('Invalid battle experience sequence')
            current = _amount(event['day'], minimum=1)
            if current < day:
                raise ValueError('Battle experience events are out of order')
            day = current
            for role in ('actor', 'target'):
                if role + '_before' in event:
                    column = self.column(event[role])
                    if event[role + '_before'] != [column.side, _count(column.troops)]:
                        raise ValueError('Battle experience event does not match the previous position')
            cause_event = event.get('cause_event')
            if cause_event is not None:
                if not 1 <= _amount(cause_event) < sequence:
                    raise ValueError('Invalid causal experience event')
                cause = journal['events'][cause_event - 1]
                if (event['kind'] != 'defeat' or cause['kind'] != 'duel'
                        or (cause['actor'], cause['target']) != (event['actor'], event['target'])):
                    raise ValueError('Invalid duel defeat cause')
            self.apply(event['kind'], {k: v for k, v in event.items()
                if k not in {'id', 'day', 'kind', 'actor_before', 'target_before', 'cause', 'cause_event'}})
        self.day = day

    def arrive(self, ident, side, amount):
        _identity(ident)
        _side(side)
        if ident in self.columns:
            col = self.columns[ident]
            if col.side != side or col.present or amount != _count(col.troops):
                raise ValueError('Invalid returning experience column')
            col.present = True
            return
        self.columns[ident] = Column(side, [])
        self.replenish(ident, amount)

    def column(self, ident):
        if ident not in self.columns or not self.columns[ident].present:
            raise ValueError('Experience event uses an absent officer')
        return self.columns[ident]

    def replenish(self, ident, amount):
        col = self.column(ident)
        if _count(col.troops) + _amount(amount) > OFFICER_TROOP_CAP:
            raise ValueError('Experience column exceeds officer capacity')
        if amount:
            col.troops.append((self.total, self.total + amount))
            self.total += amount

    def row(self, ident):
        col = self.column(ident)
        return self.rows.setdefault((ident, col.side), Contribution())

    def engage(self, ident):
        col = self.column(ident)
        row = self.row(ident)
        row.engaged = True
        row.committed = tuple(_union(row.committed, col.troops))
        self.engaged = _union(self.engaged, col.troops)
        return row

    def opponents(self, actor, target):
        return self.column(actor).side != self.column(target).side

    def lose(self, target, amount, *, ordinary=False):
        col = self.column(target)
        if _amount(amount, minimum=1) > _count(col.troops):
            raise ValueError('Experience casualty exceeds available troops')
        row = self.row(target)
        row.losses += amount
        row.preservation_losses += _overlap(row.committed, _take(col.troops, amount))
        if ordinary:
            row.ordinary += amount
        self.losses[col.side] += amount

    def damage(self, actor, target, amount, ordinary):
        if type(ordinary) is not bool or not self.opponents(actor, target):
            raise ValueError('Invalid opposing troop damage')
        self.engage(actor).kills += _amount(amount, minimum=1)
        self.engage(target)
        self.lose(target, amount, ordinary=ordinary)

    def duel_hit(self, actor, target, amount, maximum, hp_before=None):
        maximum = _amount(maximum, minimum=1)
        hp = maximum if hp_before is None else _amount(hp_before, minimum=1)
        if not self.opponents(actor, target) or not _amount(amount, minimum=1) <= hp <= maximum:
            raise ValueError('Invalid opposing duel damage')
        ratio = Decimal(amount) / maximum
        row, victim = self.engage(actor), self.engage(target)
        row.duel_hp += amount
        row.duel += ratio
        victim.received_hp += amount
        victim.received += ratio
        weights = self.duel_stages.setdefault(target, {})
        key = (actor, self.column(actor).side)
        weights[key] = weights.get(key, 0) + amount

    def defeat(self, actor, target, amount):
        if not self.opponents(actor, target) or _amount(amount) != _count(self.column(target).troops):
            raise ValueError('Invalid duel defeat')
        self.engage(actor)
        self.engage(target)
        weights = self.duel_stages.pop(target, {}) or {(actor, self.column(actor).side): 1}
        if amount:
            for key, points in apportion(amount, weights).items():
                self.rows[key].kills += points
            self.lose(target, amount)

    def conversion(self, actor, target, amount):
        col = self.column(target)
        if not self.opponents(actor, target) or _amount(amount) != _count(col.troops):
            raise ValueError('Invalid experience conversion')
        row = self.engage(actor)
        self.engage(target)
        row.converts += 1
        row.converted_troops += amount
        col.side = self.column(actor).side
        self.duel_stages.pop(target, None)

    def transfer(self, actor, target, amount):
        source, destination = self.column(actor), self.column(target)
        if (actor == target or source.side != destination.side or _amount(amount, minimum=1) > _count(source.troops)
                or amount + _count(destination.troops) > OFFICER_TROOP_CAP):
            raise ValueError('Invalid experience troop transfer')
        destination.troops.extend(_take(source.troops, amount))

    def effect(self, actor, target):
        if not self.opponents(actor, target):
            raise ValueError('Invalid opposing effect')
        self.engage(actor)
        self.engage(target)

    def retreat(self, ident):
        self.column(ident).present = False

    def apply(self, kind, details):
        methods = {'arrive': self.arrive, 'replenish': self.replenish, 'transfer': self.transfer,
                   'retreat': self.retreat, 'damage': self.damage, 'loss': self.lose,
                   'duel': self.duel_hit, 'defeat': self.defeat, 'conversion': self.conversion,
                   'effect': self.effect, 'defeat_self': self.lose}
        if kind not in methods:
            raise ValueError('Unknown battle experience event')
        methods[kind](**details)


def apportion(amount, weights):
    """Largest remainder with normalized quotas and stable officer IDs."""
    if not weights:
        return {}
    total = sum(weights.values())
    if not total:
        weights = dict.fromkeys(weights, 1)
        total = len(weights)
    quotas = {key: Decimal(amount) * weight / total for key, weight in weights.items()}
    floors = {key: int(quota) for key, quota in quotas.items()}
    order = sorted(weights, key=lambda key: (floors[key] - quotas[key],
                   ref_sort_key(key[0] if isinstance(key, tuple) else key),
                   key[1] if isinstance(key, tuple) else ''))
    for key in order[:amount - sum(floors.values())]:
        floors[key] += 1
    return floors


def _distribute_side(rows, amount, settings):
    raw = {ident: row.raw(settings) for ident, row in rows.items()}
    columns = list(zip(*raw.values()))
    totals = [sum(values) for values in columns]
    effective = sum(weight for weight, total in zip(settings.weights, totals) if total)
    normalized = {ident: tuple(value / total if total else Decimal(0)
                  for value, total in zip(values, totals)) for ident, values in raw.items()}
    weighted = {ident: tuple(n * w for n, w in zip(values, settings.weights))
                for ident, values in normalized.items()}
    shares = {ident: sum(values) / effective if effective else Decimal(1) / len(rows)
              for ident, values in weighted.items()}
    allocations = apportion(amount, shares)
    percentages = apportion(10000, shares)
    results = {}
    for ident, row in rows.items():
        results[ident] = dict(troops=row.troops, kills=row.kills, losses=row.losses,
            ordinary=row.ordinary, duel_hp=row.duel_hp, received_hp=row.received_hp,
            duel_ratio=float(row.duel), received_ratio=float(row.received),
            converts=row.converts, converted_troops=row.converted_troops,
            raw=list(map(float, raw[ident])), normalized=list(map(float, normalized[ident])),
            weighted=list(map(float, weighted[ident])), share=float(shares[ident]), exact=float(shares[ident]*amount),
            basis_points=percentages[ident], experience=allocations[ident])
    return results, float(effective)


def _round(value):
    return int(value + Decimal('0.5'))


def settle(journal, settings=DEFAULT):
    """Return the report without modifying battle or officer state."""
    with localcontext() as ctx:
        ctx.prec = 50
        replay = Replay(journal)
        groups = {side: {ident: row for (ident, served), row in replay.rows.items()
                         if served == side and row.engaged} for side in SIDES}
        troops = _count(replay.engaged)
        valid = any(groups.values())
        pool = max(settings.minimum, _round(Decimal(troops) / settings.soldiers_per_point)) if valid else 0
        scores = [sum(row.kills + row.converted_troops * settings.conversion_troops
                      + row.converts * settings.conversion_officers + row.duel * settings.duel_score
                      for row in groups[side].values()) for side in SIDES]
        first = (settings.guarantee / 2 + settings.competition * scores[0] / sum(scores)
                 if sum(scores) else Decimal('0.5'))
        first_points = max(1, min(pool - 1, _round(pool * first))) if valid else 0
        first_pct = _round(10000 * first) if valid else 0
        sides, awards = {}, {}
        for i, side in enumerate(SIDES):
            rows, amount = groups[side], (first_points if i == 0 else pool - first_points)
            results, weight = _distribute_side(rows, amount, settings) if rows else ({}, 0)
            for ident, result in results.items():
                awards[ident] = awards.get(ident, 0) + result['experience']
            sides[side] = dict(opening=replay.opening[side], losses=replay.losses[side],
                converts=sum(r.converts for r in rows.values()),
                converted_troops=sum(r.converted_troops for r in rows.values()),
                score=float(scores[i]), basis_points=(first_pct if i == 0 else 10000 - first_pct) if valid else 0,
                experience=amount, effective_weight=weight,
                officers=[dict(id=ident, eligible=ident in results,
                               **results.get(ident, dict(experience=0, basis_points=0)))
                          for ident in sorted(set(results) | {key for key, col in replay.columns.items()
                                                               if col.side == side}, key=ref_sort_key)])
        return dict(version=1, total_troops=troops, experience=pool,
                    participants=len(set().union(*groups.values())), dimensions=list(DIMENSIONS),
                    weights=list(map(float, settings.weights)), sides=sides), awards



def validate_reports(events):
    """Validate preserved battle receipts once at the save boundary."""
    for event in events['items']:
        if event['kind'] != 'battle_result' or 'experience' not in event['details']:
            continue
        report = event['details']['experience']
        if report['status'] != 'settled' or report['version'] != 1 or report['dimensions'] != list(DIMENSIONS):
            raise ValueError('Invalid settled experience receipt')
        pool = _amount(report['experience'])
        _amount(report['total_troops'])
        parts = report['sides']
        if set(parts) != set(SIDES) or sum(_amount(parts[side]['experience']) for side in SIDES) != pool:
            raise ValueError('Invalid settled experience totals')
        earned = {}
        valid = set()
        for side in parts.values():
            actual = []
            seen = set()
            if not isinstance(side['officers'], list) or len(side['officers']) > MAX_BATTLE_PARTICIPANTS:
                raise ValueError('Invalid settled experience officers')
            for row in side['officers']:
                ident = _identity(row['id'])
                if ident in seen or type(row['eligible']) is not bool:
                    raise ValueError('Invalid settled experience officer')
                seen.add(ident)
                points, share = _amount(row['experience']), _amount(row['basis_points'])
                if row['eligible']:
                    valid.add(ident)
                    actual.append(share)
                    earned[str(ident)] = earned.get(str(ident), 0) + points
                    for column in ('raw', 'normalized', 'weighted'):
                        values = row[column]
                        if not isinstance(values, list) or len(values) != len(DIMENSIONS) or not all(
                                type(value) in (str, int, float) and 0 <= float(value) <= 2**53 for value in values):
                            raise ValueError('Invalid settled experience scores')
                elif points or share:
                    raise ValueError('Idle officer awarded experience')
            if sum(row['experience'] for row in side['officers']) != side['experience'] or sum(actual) != (10000 if actual else 0):
                raise ValueError('Invalid settled experience distribution')
        if report['participants'] != len(valid) or set(report['applied']) != set(earned) or any(
                _amount(amount) > earned[ident] for ident, amount in report['applied'].items()):
            raise ValueError('Invalid applied experience receipt')
