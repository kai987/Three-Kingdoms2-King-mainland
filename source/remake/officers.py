"""Modern officer/roster rules for the independent game, not a NES memory patch.

Source years describe game settings unless separately certified. Missing source
stats stay missing. Runtime IDs are never masked to a byte; ID255 is valid.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Iterable, Mapping


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{label} must be an integer in {low}..{high}')
    return value


def is_generated_ref(value):
    """Generated people have their own bounded namespace, never historic IDs."""
    if not isinstance(value, str) or re.fullmatch(r'clerk-[0-9]{6,7}', value) is None:
        return False
    number = int(value[6:])
    return 1 <= number <= 1000000 and value == f'clerk-{number:06d}'


def ref_sort_key(value):
    return (1, int(value[6:])) if is_generated_ref(value) else (0, value)


def parse_officer_ref(value, rules=None):
    if is_generated_ref(value):
        return value
    return integer(value, 0, (rules.runtime_capacity if rules else 1200)-1, 'runtime officer ID')


def deserialize_officer_ref(value, rules=None):
    """Only saved object keys use canonical decimal strings for historical IDs."""
    if is_generated_ref(value):
        return value
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise ValueError('Invalid saved officer reference')
    ident = parse_officer_ref(int(value), rules)
    if str(ident) != value:
        raise ValueError('Noncanonical saved officer reference')
    return ident


@dataclass(frozen=True)
class GameRules:
    city_officer_capacity: int = 99
    battle_officers_per_side: int = 10
    runtime_capacity: int = 1200

    def __post_init__(self):
        integer(self.city_officer_capacity, 1, 65534, 'city capacity')
        integer(self.battle_officers_per_side, 1, 10, 'battle capacity')
        integer(self.runtime_capacity, 1, 65535, 'runtime capacity')

    def officer_id(self, value):
        return parse_officer_ref(value, self)


class YearState(str, Enum):
    NOT_BORN = 'not_born'
    NOT_APPEARED = 'not_appeared'
    AVAILABLE = 'available'
    DEATH_YEAR_REVIEW = 'death_year_review'
    DEAD = 'dead'
    UNKNOWN = 'unknown'


@dataclass(frozen=True)
class PersonDefinition:
    person_id: str
    name: str
    birth_year: int | None
    service_year: int | None
    death_year: int | None
    chronology_basis: str = 'SAN14_game_settings'

    def __post_init__(self):
        if not self.person_id or not self.name:
            raise ValueError('Stable identity and name required')
        for key in ('birth_year', 'service_year', 'death_year'):
            value = getattr(self, key)
            if value is not None:
                integer(value, 1, 400, key)
        pairs = ((self.birth_year, self.service_year), (self.service_year, self.death_year),
                 (self.birth_year, self.death_year))
        if any(a is not None and b is not None and a > b for a, b in pairs):
            raise ValueError('Chronology order requires review; never silently repair')


def year_state(person: PersonDefinition, year: int) -> YearState:
    """A year-qualified person is not automatically recruited or assigned a city.

    Unknown months in the death year remain a separate review category. Known
    exclusion (unborn/dead) wins over another missing date; availability requires
    all three dates. An exact scenario may resolve the annual boundary separately.
    """
    integer(year, 1, 400, 'year')
    if person.birth_year is not None and year < person.birth_year:
        return YearState.NOT_BORN
    if person.death_year is not None and year > person.death_year:
        return YearState.DEAD
    if person.service_year is not None and year < person.service_year:
        return YearState.NOT_APPEARED
    if None in (person.birth_year, person.service_year, person.death_year):
        return YearState.UNKNOWN
    if year == person.death_year:
        return YearState.DEATH_YEAR_REVIEW
    return YearState.AVAILABLE


VIRTUE_WEIGHTS = {'care': 35, 'fairness': 30, 'integrity': 20, 'trust': 15}


def virtue_score(dimensions: Mapping[str, int]) -> int:
    """Authorial game rating, not a historical measurement or charisma mapping."""
    if set(dimensions) != set(VIRTUE_WEIGHTS):
        raise ValueError('All four independent virtue dimensions required')
    for value in dimensions.values():
        integer(value, 0, 100, 'virtue dimension')
    weighted = sum(dimensions[k] * w for k, w in VIRTUE_WEIGHTS.items())
    return max(10, min(99, (weighted + 50) // 100))


def compatible_stat(value: int | None) -> int | None:
    if value is None:
        return None
    return min(integer(value, 1, 100, 'SAN14 ability'), 99)


def experience_tier(experience: int) -> int:
    """Consistent starting tier; original thresholds, not age or rank."""
    integer(experience, 0, 49999, 'experience')
    return sum(experience >= t for t in (1000, 2000, 3500, 5000, 7500, 10000, 15000))


def recruitment_loyalty(leader_virtue: int, previous_loyalty: int) -> int:
    """Original CF3F byte subtraction and10..90 clamp; no faction mutation."""
    integer(leader_virtue, 1, 99, 'leader virtue')
    integer(previous_loyalty, 0, 100, 'previous loyalty')
    return max(10, min(90, (70 + leader_virtue // 10 - previous_loyalty) & 255))


def captured_loyalty(previous_loyalty: int) -> int:
    integer(previous_loyalty, 0, 100, 'previous loyalty')
    return max(10, 51 - abs(50 - previous_loyalty))


@dataclass(frozen=True)
class OfficerProfile:
    health_max: int | None
    martial_strength: int | None
    intellect: int | None
    virtue: int | None
    terrain_affinity: int | None
    source_stats: dict = field(default_factory=dict)
    basis: dict = field(default_factory=dict)

    def __post_init__(self):
        for key in ('health_max', 'martial_strength', 'intellect', 'virtue'):
            value = getattr(self, key)
            if value is not None:
                integer(value, 1, 99, key)
        if self.terrain_affinity is not None:
            integer(self.terrain_affinity, 0, 2, 'terrain affinity')

    @property
    def missing(self):
        return tuple(k for k in ('health_max', 'martial_strength', 'intellect',
                                  'virtue', 'terrain_affinity') if getattr(self, k) is None)


def convert_profile(*, san14_stats=None, legacy=None, health_max=None,
                    terrain_affinity=None, virtue_design=None) -> OfficerProfile:
    """Explicit SAN14 strength/intellect override a verified legacy fallback.

    Legacy values remain available when SAN14 abilities are not yet sourced.
    SAN14 charisma supplies virtue under the current campaign policy. Legacy
    virtue remains a fallback for isolated, older caller inputs without charisma.
    """
    raw = dict(san14_stats or {})
    old = dict(legacy or {})
    basis = {}

    def choose(key, san_key):
        if raw.get(san_key) is not None:
            basis[key] = f'SAN14.{san_key}; max99 compatibility scale'
            return compatible_stat(raw[san_key])
        if old.get(key) is not None:
            basis[key] = 'verified_legacy_record'
            return old[key]
        return None

    martial = choose('martial_strength', 'martial_strength')
    intellect = choose('intellect', 'intellect')
    health = health_max if health_max is not None else old.get('health')
    affinity = terrain_affinity if terrain_affinity is not None else old.get('terrain_affinity_code')
    virtue = compatible_stat(raw['charisma']) if raw.get('charisma') is not None else old.get('virtue')
    if raw.get('charisma') is not None:
        basis['virtue'] = 'SAN14.charisma; max99 compatibility scale'
    elif virtue is not None:
        basis['virtue'] = 'verified_legacy_record'
    elif virtue_design is not None and virtue_design.get('status') == 'configured_design':
        if not virtue_design.get('sources'):
            raise ValueError('Configured virtue requires source references')
        virtue = virtue_score(virtue_design['dimensions'])
        basis['virtue'] = 'history_informed_game_design; not a historical fact'
    elif virtue_design is not None and virtue_design.get('status') == 'configured_default':
        if (virtue_design.get('policy_id') != 'virtue-default-60-2026-10-21'
                or type(virtue_design.get('virtue')) is not int
                or virtue_design['virtue'] != 60
                or virtue_design.get('authority') != 'explicit_user_instruction'
                or virtue_design.get('is_historical_fact') is not False
                or virtue_design.get('dimensions') is not None
                or virtue_design.get('sources') != []):
            raise ValueError('Default virtue requires the explicit60 policy and truthful provenance')
        virtue = 60
        basis['virtue'] = 'explicit_user_default60; not a historical rating'
    basis['health_max'] = 'explicit_game_profile' if health_max is not None else 'legacy_or_missing'
    basis['terrain_affinity'] = 'explicit_game_profile' if terrain_affinity is not None else 'legacy_or_missing'
    return OfficerProfile(health, martial, intellect, virtue, affinity, raw, basis)


@dataclass
class RuntimeOfficer:
    runtime_id: int | str
    person_id: str
    profile: OfficerProfile
    health: int
    loyalty: int
    troops: int = 0
    weapon_id: int = 0
    armor_id: int = 0
    experience: int = 0
    tier: int = 0
    faction_id: str | None = None
    alive: bool = True


def appearance_values(profile, initialization=None, *, faction_id=None, is_ruler=False):
    """Read a first-appearance baseline; never use this to refresh a living unit.

    A table's initial health is not evidence of its original healing limit.
    The separate profile cap is this remake's retained compatibility policy.
    Original loyalty has a faction context; a ruler marker is not a subordinate
    loyalty value and unaligned/free appearances have no faction loyalty.
    """
    if initialization is None:
        return dict(health=profile.health_max,
                    loyalty=0 if faction_id is None else 100 if is_ruler else 80)
    if (not isinstance(initialization, dict)
            or initialization.get('schema') != 'tk2-officer-initialization-v1'):
        raise ValueError('Invalid officer initialization policy')
    health = integer(initialization.get('health'), 1, profile.health_max, 'initial health')
    default = integer(initialization.get('default_loyalty'), 0, 99, 'default loyalty')
    source = initialization.get('source_loyalty')
    if source is None:
        source = {}
    if not isinstance(source, dict):
        raise ValueError('Invalid original loyalty source')
    value, contexts = source.get('value'), source.get('faction_ids', [])
    if value is not None:
        integer(value, 0, 99, 'original subordinate loyalty')
    if (not isinstance(contexts, list)
            or any(not isinstance(key, str) or not key for key in contexts)
            or len(set(contexts)) != len(contexts)):
        raise ValueError('Invalid original loyalty context')
    loyalty = (0 if faction_id is None else 100 if is_ruler else
               value if value is not None and faction_id in contexts else default)
    return dict(health=health, loyalty=loyalty)


def initialize_officer(person: PersonDefinition, runtime_id: int, profile: OfficerProfile,
                       *, year: int, faction_id=None, is_ruler=False, loyalty=None,
                       troops=0, weapon_id=0, armor_id=0, experience=0,
                       resolve_death_year=False, rules=GameRules(), health=None) -> RuntimeOfficer:
    rules.officer_id(runtime_id)
    state = year_state(person, year)
    if state != YearState.AVAILABLE and not (state == YearState.DEATH_YEAR_REVIEW and resolve_death_year):
        raise ValueError(f'Officer not eligible for initialization: {state.value}')
    if profile.missing:
        raise ValueError('Missing configured fields: ' + ', '.join(profile.missing))
    if is_ruler and faction_id is None:
        raise ValueError('A ruler requires a faction')
    if faction_id is None:
        if loyalty not in (None, 0):
            raise ValueError('Free officer has no current faction loyalty')
        loyalty = 0
    elif is_ruler:
        if loyalty not in (None, 100):
            raise ValueError('Ruler loyalty uses the original100 sentinel')
        loyalty = 100
    else:
        integer(loyalty, 0, 99, 'scenario loyalty')
    integer(troops, 0, 1000, 'initial troops')
    from .facility_equipment import WEAPONS, ARMORS
    integer(weapon_id, 0, len(WEAPONS)-1, 'weapon')
    integer(armor_id, 0, len(ARMORS)-1, 'armor')
    tier = experience_tier(experience)
    health = profile.health_max if health is None else integer(health, 1, profile.health_max, 'initial health')
    return RuntimeOfficer(runtime_id, person.person_id, profile, health,
                          loyalty, troops, weapon_id, armor_id, experience, tier, faction_id)


class CapacityError(ValueError):
    pass


@dataclass
class CityRoster:
    city_id: str
    officer_ids: list[int | str] = field(default_factory=list)
    rules: GameRules = field(default_factory=GameRules)

    def __post_init__(self):
        self.officer_ids = list(self.officer_ids)
        self.validate()

    def validate(self):
        if not self.city_id:
            raise ValueError('Stable city key required')
        if len(set(self.officer_ids)) != len(self.officer_ids):
            raise ValueError('Duplicate officer in city roster')
        if len(self.officer_ids) > self.rules.city_officer_capacity:
            raise CapacityError('City capacity exceeded')
        for value in self.officer_ids:
            self.rules.officer_id(value)


def transfer_officers(source: CityRoster, destination: CityRoster, selected: Iterable[int]):
    """Validate the whole transaction before any writes; no overflow/drop/wrap."""
    ids = tuple(selected)
    source.validate()
    destination.validate()
    if len(set(ids)) != len(ids) or any(i not in source.officer_ids for i in ids):
        raise ValueError('Transfer requires unique source roster IDs')
    if source is destination or source.city_id == destination.city_id:
        if source is not destination:
            raise ValueError('Distinct objects cannot own the same city key')
        return ()
    if set(source.officer_ids) & set(destination.officer_ids):
        raise ValueError('An officer cannot belong to two city rosters')
    for i in ids:
        destination.rules.officer_id(i)
    if len(destination.officer_ids) + len(ids) > destination.rules.city_officer_capacity:
        raise CapacityError('Destination city is full; no transfer committed')
    source.officer_ids[:] = [i for i in source.officer_ids if i not in ids]
    destination.officer_ids.extend(ids)
    return ids


def select_deployment(city: CityRoster, selected: Iterable[int], officers: Mapping[int, RuntimeOfficer]):
    """Read-only selection: at most10 including commander; cancel costs nothing.

    The caller's first selected officer is commander. Minimum-one is a remake
    API precondition, not a claim that the full old sortie UI was reverified.
    """
    ids = tuple(selected)
    city.validate()
    if not 1 <= len(ids) <= city.rules.battle_officers_per_side:
        raise ValueError('Select1..10 officers including the commander')
    if len(set(ids)) != len(ids) or any(i not in city.officer_ids for i in ids):
        raise ValueError('Deploy only unique city members')
    for i in ids:
        officer = officers[i]
        if officer.runtime_id != i or not officer.alive or officer.health <= 0 or officer.troops <= 0:
            raise ValueError('Deployment requires a living, healthy officer with troops')
    if len({officers[i].faction_id for i in ids}) != 1 or officers[ids[0]].faction_id is None:
        raise ValueError('Selected officers require a single faction')
    return ids


def advance_year(people: Iterable[PersonDefinition], officers: Mapping[int, RuntimeOfficer],
                 cities: Iterable[CityRoster], previous_year: int, next_year: int):
    """Apply sourced year events without auto-recruiting or reviving anyone.

    Death-year membership remains a review boundary; absent an exact scenario
    date, removal occurs on entering the following year. A battle death is sticky.
    Event discovery never creates unconfigured RuntimeOfficers.
    Crossing an already-dead person's retirement year produces only a zero-effect
    calendar receipt. The campaign owns committing/deduplicating that receipt.
    """
    integer(previous_year, 1, 400, 'previous year')
    integer(next_year, previous_year + 1, 400, 'next year')
    definitions = tuple(people)
    by_person = {p.person_id: p for p in definitions}
    if len(by_person) != len(definitions):
        raise ValueError('Duplicate stable person ID')
    rosters = tuple(cities)
    if len({c.city_id for c in rosters}) != len(rosters):
        raise ValueError('Duplicate city key')
    seen = set()
    for city in rosters:
        city.validate()
        if seen.intersection(city.officer_ids):
            raise ValueError('An officer belongs to more than one city')
        for ident in city.officer_ids:
            if ident not in officers:
                raise ValueError('City member missing from runtime registry')
        seen.update(city.officer_ids)
    runtime_people = set()
    for ident, officer in officers.items():
        if ident != officer.runtime_id or officer.person_id not in by_person:
            raise ValueError('Runtime identity missing or mismatched')
        if officer.person_id in runtime_people:
            raise ValueError('A person cannot have two runtime records')
        runtime_people.add(officer.person_id)
    events = []
    for person in definitions:
        for key, value in (('birth', person.birth_year), ('service_eligible', person.service_year)):
            if value is not None and previous_year < value <= next_year:
                events.append({'year': value, 'event': key, 'person_id': person.person_id})
    deaths = [ident for ident, o in officers.items()
              if year_state(by_person[o.person_id], next_year) == YearState.DEAD
              and (o.alive or previous_year < by_person[o.person_id].death_year + 1 <= next_year)]
    for ident in deaths:
        officer = officers[ident]
        person = by_person[officer.person_id]
        if not officer.alive:
            events.append({'year': person.death_year + 1, 'event': 'remove_after_death_year',
                           'person_id': officer.person_id, 'runtime_id': ident,
                           'date_policy': 'unknown_month_year_end_boundary',
                           'already_dead': True, 'released_troops': 0, 'origin_city': None,
                           'resource_disposition': 'none; already-dead calendar receipt only'})
            continue
        released_troops = officer.troops
        origin_city = next((c.city_id for c in rosters if ident in c.officer_ids), None)
        officer.alive = False
        officer.faction_id = None
        officer.loyalty = 0
        officer.troops = 0
        for city in rosters:
            if ident in city.officer_ids:
                city.officer_ids.remove(ident)
        events.append({'year': person.death_year + 1, 'event': 'remove_after_death_year',
                       'person_id': officer.person_id, 'runtime_id': ident,
                       'date_policy': 'unknown_month_year_end_boundary',
                       'released_troops': released_troops, 'origin_city': origin_city,
                       'resource_disposition': 'explicit_settlement_event; caller must allocate released troops'})
    return tuple(sorted(events, key=lambda e: (e['year'], e['person_id'], e['event'])))
