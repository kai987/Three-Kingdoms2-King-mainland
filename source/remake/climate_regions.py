"""Game climate geography independent of political and catalog boundaries."""
from functools import cached_property
from statistics import median

from .route_network import variants

# (eligible months, snow probability per ten days, Nov–Mar cold, guarantee)
REGIONS = {
    'liaodong': ((11, 12, 1, 2, 3), 60, (1, 3, 3, 2, 1), True),
    'northern_frontier': ((11, 12, 1, 2, 3), 50, (1, 2, 3, 2, 1), True),
    'northwest': ((11, 12, 1, 2, 3), 50, (1, 2, 3, 2, 1), True),
    'qinling_highlands': ((11, 12, 1, 2, 3), 60, (1, 2, 2, 2, 1), True),
    'north_china': ((12, 1, 2), 40, (0, 1, 2, 1, 0), False),
    'central_plains': ((12, 1, 2), 25, (0, 1, 1, 1, 0), False),
    'huai_north_jing': ((12, 1, 2), 15, (0, 0, 1, 0, 0), False),
    'southern_basins': ((), 0, (0, 0, 0, 0, 0), False),
    'southern_highlands': ((12, 1, 2), 10, (0, 0, 1, 0, 0), False),
    'lingnan': ((), 0, (0, 0, 0, 0, 0), False),
    'tropical_islands': ((), 0, (0, 0, 0, 0, 0), False),
}
WINTER_MONTHS = (11, 12, 1, 2, 3)
ISLANDS = frozenset({'yizhou', 'zhuya', 'luzon'})
SOUTHERN_HEIGHTS = frozenset({'yuexi', 'yunnan', 'jianning'})
# Explicit physical navigable reaches, with sensitivity in percent.
# Named rivers absent from the playable navigation graph are not invented.
FREEZE = {
    'yellow:jincheng:shuofang': ('northern_frontier', 150),
    'yellow:tongguan:hongnong': ('central_plains', 100),
    'yellow:hongnong:hedong': ('north_china', 100),
    'yellow:hedong:henan': ('central_plains', 100),
    'yellow:henan:henei': ('central_plains', 50),
    'yellow:henei:wei': ('north_china', 50),
    'yellow:wei:dongjun': ('north_china', 50),
    'yellow:dongjun:qinghe': ('north_china', 100),
    'yellow:qinghe:pingyuan': ('north_china', 100),
    'yellow:pingyuan:jinan': ('north_china', 50),
    'wei:fufeng:jingzhao': ('central_plains', 100),
    'wei:jingzhao:fengyi': ('central_plains', 100),
    'wei:fengyi:tongguan': ('central_plains', 50),
    'wo:qiao:huai': ('central_plains', 50),
    'huai:runan:wo': ('huai_north_jing', 50),
}
SAMPLES = 16


def classify(lon, lat, *, high=False, southern_height=False):
    if lat >= 38.8 and lon >= 119:
        return 'liaodong'
    if lon < 105.1 and lat >= 34.4:
        return 'northwest'
    if lat >= 38.1:
        return 'northern_frontier'
    if (high and 103 <= lon <= 113.1 and 31.6 <= lat <= 36.5):
        return 'qinling_highlands'
    if lat >= 36:
        return 'north_china'
    if lat >= 33.7:
        return 'central_plains'
    if lat >= 31.6 and lon >= 109.7:
        return 'huai_north_jing'
    if southern_height:
        return 'southern_highlands'
    if lat < 25.4:
        return 'lingnan'
    return 'southern_basins'


def _runs(sample):
    result = []
    for region in sample:
        if result and result[-1][0] == region:
            result[-1] = (region, result[-1][1] + 1)
        else:
            result.append((region, 1))
    return tuple(result)


class ClimateMap:
    def __init__(self, data):
        self.coordinates = data.get('city_coordinates', {})
        self.terrain = {row['id']: row.get('terrain') for row in data['cities']}
        self.routes = {r['id']: r for r in variants([*data.get('travel_routes', ()),
                                                      *data.get('exploration_routes', ())])}
        self._land = {}
        self.parts = {}

    @cached_property
    def cities(self):
        result = {}
        for key, terrain in sorted(self.terrain.items()):
            lon, lat = self.coordinates[key]
            high = terrain == 'mountain' or key in SOUTHERN_HEIGHTS
            region = ('tropical_islands' if key in ISLANDS else
                      classify(lon, lat, high=high, southern_height=key in SOUTHERN_HEIGHTS))
            result[key] = dict(climate_region_id=region, elevation_class='highland' if high else 'lowland',
                               snow_enabled=bool(REGIONS[region][1]), freeze_region_id=region)
        return result

    def land(self, ident, source, target, terrain):
        key = ident, source, target, terrain
        if key not in self._land:
            left, right = self.coordinates[source], self.coordinates[target]
            high = terrain == 'mountain' or ':ziwu' in ident
            southern = high and {source, target} <= SOUTHERN_HEIGHTS
            self._land[key] = _runs(classify(
                left[0] + (right[0] - left[0]) * (i + .5) / SAMPLES,
                left[1] + (right[1] - left[1]) * (i + .5) / SAMPLES,
                high=high, southern_height=southern) for i in range(SAMPLES))
        return self._land[key]

    @cached_property
    def reaches(self):
        samples = {}
        names = {}
        for raw in self.routes.values():
            waters = raw.get('river_segments', ())
            if not waters:
                continue
            left, right = (self.coordinates[k] for k in (raw['from'], raw['to']))
            total = sum(reach['distance_km'] for reach in waters)
            position = 0
            for reach in waters:
                ratio = (position + reach['distance_km'] / 2) / total
                position += reach['distance_km']
                ident = reach['reach_id']
                point = tuple(a+(b-a)*ratio for a,b in zip(left,right))
                samples.setdefault(ident, set()).add(point)
                names[ident] = reach['river_id']
        result = {}
        for ident, points in sorted(samples.items()):
            region = classify(*(median(values) for values in zip(*points)))
            freeze_region, sensitivity = FREEZE.get(ident, (region, 0))
            result[ident] = dict(river_id=names[ident], climate_region_id=region,
                                 freeze_region_id=freeze_region, freeze_sensitivity=sensitivity,
                                 mapping='selected_reach' if sensitivity else 'navigation_default_open')
        return result

    @cached_property
    def frozen_reaches(self):
        return {identity: row for identity, row in self.reaches.items() if row['freeze_sensitivity']}
