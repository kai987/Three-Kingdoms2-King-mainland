"""Optional worker wire cache; never part of campaign state or save data."""
from collections import OrderedDict
import hashlib
import json

SCHEMA = 'tk2-view-v1'
STATIC_FIELDS = frozenset(('title', 'factions', 'links', 'rules', 'calendar_rules',
    'difficulties', 'notes', 'library_count', 'coverage', 'tactics',
    'map_presentation', 'road_additions', 'world',
    'scenario_id', 'faction_colors', 'sea_routes', 'travel_hazards',
    'added_city_ids', 'regional_roads', 'river_routes', 'city_label_offsets', 'city_history', 'scenarios',
    'travel_rules', 'coastal_city_ids'))
PERSON_STATE = frozenset(('year_state', 'faction', 'alive', 'location'))


class ViewTransport:
    """Two immutable catalogs, explicitly negotiated separately by each tab."""
    def __init__(self):
        self.catalogs = OrderedDict()

    def pack(self, value, source_sha, known=''):
        if not isinstance(value, dict) or not {'catalog', 'game', 'revision'} <= value.keys():
            return value
        catalog = value['catalog']
        if source_sha not in self.catalogs:
            static = {key: field for key, field in catalog.items() if key in STATIC_FIELDS}
            static['library'] = [{key: field for key, field in row.items() if key not in PERSON_STATE}
                                 for row in catalog['library']]
            raw = json.dumps(static, sort_keys=True, ensure_ascii=False,
                             allow_nan=False, separators=(',', ':')).encode('utf-8')
            token = hashlib.sha256(raw).hexdigest()
            self.catalogs[source_sha] = (token, static)
        self.catalogs.move_to_end(source_sha)
        while len(self.catalogs) > 2:
            self.catalogs.popitem(last=False)
        token, static = self.catalogs[source_sha]
        known_static, _, known_quotes = known.partition(':')
        game = value['game']
        # Read-only route quotes depend on ownership, active cities, player,
        # month and discovered routes. Troops, gold, phase, RNG and revision
        # never enter route search. Catalog bytes fix geometry and all rules.
        route_key = [source_sha, None if game is None else [game['player'], game['month'],
            [(key, city['owner']) for key, city in game['cities'].items()],
            game['extension']['travel']['discovered']]]
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
        return result
