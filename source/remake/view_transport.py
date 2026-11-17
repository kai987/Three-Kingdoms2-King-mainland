"""Optional worker wire cache; never part of campaign state or save data."""
from collections import OrderedDict
import hashlib
import json

SCHEMA = 'tk2-view-v1'
STATIC_FIELDS = frozenset(('title', 'links', 'rules', 'calendar_rules',
    'difficulties', 'notes', 'library_count', 'coverage', 'tactics',
    'map_presentation', 'road_additions', 'world',
    'scenario_id', 'faction_colors', 'sea_routes', 'travel_hazards',
    'added_city_ids', 'regional_roads', 'river_routes', 'city_label_offsets', 'city_history', 'scenarios',
    'travel_rules', 'coastal_city_ids'))
PERSON_STATE = frozenset(('year_state', 'faction', 'alive', 'location', 'intellect', 'study_gain', 'prisoner'))


class ViewTransport:
    """Per-tab catalog caches and a shared token for immutable opening previews."""
    def __init__(self):
        self.catalogs = OrderedDict()
        self._catalogs_without_scenarios = OrderedDict()
        self._scenario_previews = None
        self._scenarios_token = None

    def pack(self, value, source_sha, known='', *, known_scenarios=None, scenario_previews=None):
        if not isinstance(value, dict) or not {'catalog', 'game', 'revision'} <= value.keys():
            return value
        catalog = value['catalog']
        shared_scenarios = known_scenarios is not None and 'scenarios' in catalog
        catalogs = self._catalogs_without_scenarios if shared_scenarios else self.catalogs
        if shared_scenarios and (scenario_previews is None or self._scenario_previews is not scenario_previews
                                 or self._scenarios_token is None):
            # The browser runtime keeps its verified opening previews fixed for
            # the session. Cache the digest and keep the current view's list
            # available so clients with a stale token can receive it again.
            raw = json.dumps(catalog['scenarios'], sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(',', ':')).encode('utf-8')
            self._scenarios_token = hashlib.sha256(raw).hexdigest()
            self._scenario_previews = scenario_previews
        if source_sha not in catalogs:
            static = {key: field for key, field in catalog.items()
                      if key in STATIC_FIELDS and (key != 'scenarios' or not shared_scenarios)}
            static['library'] = [{key: field for key, field in row.items() if key not in PERSON_STATE}
                                 for row in catalog['library']]
            raw = json.dumps(static, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(',', ':')).encode('utf-8')
            token = hashlib.sha256(raw).hexdigest()
            catalogs[source_sha] = (token, static)
        catalogs.move_to_end(source_sha)
        while len(catalogs) > 2:
            catalogs.popitem(last=False)
        token, static = catalogs[source_sha]
        known_static, _, known_quotes = known.partition(':')
        game = value['game']
        # Read-only route quotes depend on ownership, active cities, player,
        # year/month, allied transit and discovered routes. Troops, gold, phase, RNG and revision
        # never enter route search. Catalog bytes fix geometry and all rules.
        allies = sorted({owner for pair in catalog.get('non_aggression', [])
                         if game is not None and game['player'] in pair
                         for owner in pair if owner != game['player']})
        route_key = [source_sha, None if game is None else [game['player'], game['year'], game['month'],
            [(key, city['owner']) for key, city in game['cities'].items()],
            game['extension']['travel']['discovered'], allies]]
        quote_token = hashlib.sha256(json.dumps(route_key, sort_keys=True,
            separators=(',', ':')).encode()).hexdigest()
        current = {key: field for key, field in catalog.items() if key not in STATIC_FIELDS}
        current['library'] = [{key: field for key, field in row.items() if key in PERSON_STATE or key == 'id'}
                              for row in catalog['library']]
        if known_quotes == quote_token:
            current.pop('travel_quotes', None)
        result = dict(transport=SCHEMA, catalog_token=token, quote_token=quote_token,
                      view=dict(value, catalog=current))
        if known_static != token:
            result['static_catalog'] = static
        if shared_scenarios:
            result['scenarios_token'] = self._scenarios_token
            if known_scenarios != self._scenarios_token:
                result['shared_scenarios'] = catalog['scenarios']
        return result
