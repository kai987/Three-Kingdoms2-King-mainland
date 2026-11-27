"""Bounded, deterministic allocation shared by live and shadow coordination."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class Candidate:
    demand: object
    channel: str
    source: str
    target: str
    escorts: tuple
    mode: str
    arrival: int
    conservative_arrival: int
    net: int
    conservative_net: int
    load: int
    rations: int
    days: int
    return_days: int
    command_books: int
    offer: object
    gold: int = 0

    @property
    def period(self):
        return self.days + (-self.days) % 10 + self.return_days + (-self.return_days) % 10

    @property
    def original_effect(self):
        tick = self.conservative_arrival if self.demand.priority <= 2 else self.arrival
        deadline = self.demand.original_deadline
        timely = tick <= deadline if self.demand.kind in ('march', 'convoy') else tick < deadline
        return min(self.demand.after(tick), self.conservative_net) if timely else 0

    @property
    def key(self):
        return self.demand.key, self.channel, self.source, self.target, self.mode, tuple(map(str, self.escorts))


def order(candidate, *, efficient):
    demand = candidate.demand
    at = candidate.conservative_arrival if demand.priority <= 2 else candidate.arrival
    delivered = min(candidate.net, demand.after(at))
    if demand.kind == 'march' and not delivered:
        delivered = min(candidate.net, demand.remaining)
    saving = min(delivered, candidate.original_effect)
    if efficient:
        cycle = candidate.period + 10 if candidate.mode else 1
        units = max(1, len(candidate.escorts) * cycle)
        follow = (-Fraction(delivered, candidate.command_books), -Fraction(delivered, units),
                  candidate.load + candidate.rations - delivered, candidate.gold, candidate.arrival)
    else:
        follow = (candidate.arrival, candidate.load + candidate.rations, candidate.gold)
    return (demand.priority, not saving, demand.original_deadline, -saving,
            -Fraction(delivered, max(1, demand.remaining)), *follow, candidate.key)


def compatible(first, second, books):
    return (first.demand.key != second.demand.key and first.source != second.source
            and not set(first.escorts).intersection(second.escorts)
            and first.command_books + second.command_books <= books)


def select(candidates, books, *, efficient, reserve_for_orders=0):
    usable = [row for row in candidates if row.command_books <=
              books - (reserve_for_orders if row.demand.priority >= 3 else 0)]
    if not usable:
        return None
    ranked = sorted(usable, key=lambda row: order(row, efficient=efficient))
    winner = ranked[0]
    if not efficient or winner.demand.priority > 2:
        return winner
    # One level of look-ahead. Preserve a later urgent target's sole escort
    # if the leading target has a comparable alternative in the same tier.
    peers = [row for row in ranked if row.demand.key == winner.demand.key
             and row.original_effect >= winner.original_effect
             and row.net >= winner.net]
    for row in ranked:
        if row.demand.priority > 2:
            break
        if (row.demand.key != winner.demand.key and row.original_effect and
                not compatible(winner, row, books)):
            alternatives = [peer for peer in peers if compatible(peer, row, books)]
            if alternatives:
                return alternatives[0]
    return winner
