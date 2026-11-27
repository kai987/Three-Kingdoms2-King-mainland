"""Calibrate and hold out V2.3 using the live regional weather kernel."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import gzip
import json
from pathlib import Path
from statistics import fmean, median
from types import SimpleNamespace

from common import Catalog, ROOT, TOOL_ROOT, git, sha256, to_csv, to_json
from remake import winter_agriculture as agriculture
from remake import winter_climate as climate
from remake import winter_weather as weather

W1 = ('monthly_snow_probability',)
W2 = (*W1, 'regional_snow_severity', 'regional_snow_depth', 'revised_cold_profile', 'spring_cold_exposure')
FEATURES = {
    'W1': W1, 'W2': W2, 'W2e': (*W2, 'exceptional_cold_wave'),
    'W3': (*W2, 'agricultural_climate'), 'W4': (*W2, 'agricultural_climate', 'agricultural_risk_planning'),
}
CALIBRATION_START = 100_000
HOLDOUT_START = 200_000
ICE_NAMES = ('open_days', 'floating_days', 'partial_days', 'frozen_days')
AGRICULTURE_MODULE = TOOL_ROOT/'source/remake/winter_agriculture_normals.py'


@lru_cache(maxsize=1)
def campaign():
    catalog = Catalog(ROOT/'game/data/campaigns/200-01.json')
    return SimpleNamespace(catalog=SimpleNamespace(
        data=dict(start_year=184, start_month=11), climate=catalog.climate))


def simulate(group, seed):
    game = campaign()
    state = SimpleNamespace(seed=seed, extension={})
    version = weather.CORRECTED if group == 'W0' else climate.VERSION
    weather.initialize(game, state, version, options=None if group == 'W0' else climate.flags(*FEATURES[group]))
    legacy = {'regions': {region: agriculture._row() for region in climate.REGIONS}}
    event_count, melt_tail, ice = Counter(), Counter(), defaultdict(Counter)

    def sample(kind, row):
        if kind == 'region':
            key = row['region']
            if row['severity'] and row['began'] == row['tick']:
                event_count[key] += 1
            if row['depth']:
                melt_tail[key] = row['tick']
            if group == 'W0' and row['month'] in agriculture.OBSERVATION_MONTHS:
                agriculture.observe(legacy, key, row['month'], row['tick'], row,
                                    frost=False, late=False, wave=False)
        elif kind == 'ice':
            ice[row['reach']][ICE_NAMES[row['state']]] += 1
    with weather.experiment(5, observe=sample):
        for tick in range(1, 241):
            weather.advance(game, state, tick)
    regions = legacy['regions'] if group == 'W0' else agriculture.ledger(state)['regions']
    weather_seed = weather.seed_for(seed)
    snow = []
    for key, row in regions.items():
        snow.append({**dict(group=group, seed=seed, version=version, weather_seed=weather_seed,
                            region=key, events=event_count[key], **row),
                     'mean_snow_depth': row['depth_sum']/(30*len(agriculture.OBSERVATION_MONTHS)),
                     'spring_risk_score': agriculture.risk_score(row), 'melt_last_day': melt_tail[key],
                     'remaining_snow_june30': state.extension[weather.POOL]['regions'][key]['depth']})
    return snow, [dict(group=group, seed=seed, reach=key, **{name: counts[name] for name in ICE_NAMES})
                  for key, counts in sorted(ice.items())]


def simulate_batch(batch):
    group, seeds = batch
    snow, ice = [], []
    for seed in seeds:
        a, b = simulate(group, seed)
        snow.extend(a)
        ice.extend(b)
    return snow, ice


def runs(start, count, groups, workers):
    batches = [(group, range(seed, min(seed+25, start+count)))
               for group in groups for seed in range(start, start+count, 25)]
    snow, ice = [], []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for index, (regional, rivers) in enumerate(pool.map(simulate_batch, batches), 1):
            snow.extend(regional)
            ice.extend(rivers)
            if index % 20 == 0 or index == len(batches):
                print(f'Weather batches {index}/{len(batches)}', flush=True)
    return snow, ice


def quantile(values, percentile):
    ordered = sorted(values)
    return ordered[max(0, (percentile*len(ordered)+99)//100-1)]


def calibrate(rows):
    by_region = defaultdict(list)
    for row in rows:
        by_region[row['region']].append(row)
    result = {}
    for region in climate.RISK_MONTHS:
        annual = by_region[region]
        risk = [row['spring_risk_score'] for row in annual]
        snow = [row['total_snowfall_units'] for row in annual]
        last_cover = [row['melt_last_day'] for row in annual]
        moisture = ((quantile(snow, 30), quantile(snow, 70))
                    if region != 'southern_basins' and quantile(snow, 70) > 0 else ())
        result[region] = tuple(quantile(risk, p) for p in (75, 90, 97)), moisture, quantile(last_cover, 75)
    return result


def metrics(rows, keys, names):
    by_key = defaultdict(list)
    for row in rows:
        by_key[tuple(row[key] for key in keys)].append(row)
    for key, observed in sorted(by_key.items()):
        key_data = dict(zip(keys, key))
        for name in names:
            numbers = [row[name] for row in observed]
            yield dict(**key_data, metric=name, samples=len(numbers), mean=fmean(numbers),
                       median=median(numbers), p10=quantile(numbers, 10), p90=quantile(numbers, 90),
                       p95=quantile(numbers, 95), maximum=max(numbers),
                       zero_fraction=sum(value == 0 for value in numbers)/len(numbers))


def agriculture_metrics(rows):
    regions = defaultdict(list)
    for row in rows:
        if row['group'] in ('W3', 'W4'):
            regions[row['group'], row['region']].append(row)
    for (group, region), years in sorted(regions.items()):
        count = Counter(row['agriculture_status'] for row in years)
        average = fmean(row['agriculture_multiplier'] for row in years)
        yield dict(group=group, region=region, samples=len(years),
                   **{status: count[status]/len(years)
                      for status in ('normal', 'moisture', 'mild', 'moderate', 'severe')},
                   mean_multiplier=average, annual_change_pct=(average-100)/3)


def save_csv_gzip(path, rows):
    import csv
    with gzip.open(path, 'wt', encoding='utf-8', compresslevel=5, newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def city_audit(output):
    catalog = Catalog(ROOT/'game/data/campaigns/200-01.json')
    rows = []
    for city_id, profile in catalog.climate.cities.items():
        lon, lat = catalog.climate.coordinates[city_id]
        rows.append(dict(city_id=city_id, longitude=lon, latitude=lat, terrain=catalog.climate.terrain[city_id],
                         region=profile['climate_region_id'], crop_region=agriculture.region_for(SimpleNamespace(catalog=catalog),city_id),
                         elevation=profile['elevation_class']))
    to_csv(output/'city-climate-audit.csv', rows)
    to_csv(output/'climate-region-monthly-probability.csv', [
        dict(group=group, region=region, month=month, probability=climate.snow_probability(state, region, month),
             severity=climate.severity_distribution(state, region), cold=climate.cold_normal(state, region, month),
             depth_limit=climate.snow_depth_limit(state, region), spring_probability=climate.spring_probability(state,region,month))
        for group, features in (('W0', ()), ('W1',W1), ('W2',W2), ('W2e',FEATURES['W2e']))
        for state in (SimpleNamespace(extension={'winter_weather': {'options': climate.flags(*features)}}),)
        for region in climate.REGIONS for month in range(1, 13)
    ])


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('calibrate', 'holdout'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--count', type=int, default=1000)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--write-normals', action='store_true')
    args = parser.parse_args()
    if args.count < 1 or args.workers < 1 or args.write_normals and (args.phase != 'calibrate' or args.count != 1000):
        parser.error('Frozen normals require all 1,000 calibration winters')
    args.output.mkdir(parents=True, exist_ok=True)
    training = args.phase == 'calibrate'
    start = CALIBRATION_START if training else HOLDOUT_START
    groups = ('W2',) if training else ('W0', 'W1', 'W2e', 'W3')
    snow, ice = runs(start, args.count, groups, args.workers)
    save_csv_gzip(args.output/f'{args.phase}-regional-winters.csv.gz', snow)
    save_csv_gzip(args.output/f'{args.phase}-river-winters.csv.gz', ice)
    for name, fields in (
        ('winter-event-frequency', ('events','winter_snow_days')),
        ('winter-snow-days', ('winter_snow_days',)),
        ('snowfall-severity-distribution', ('light_snow_days','heavy_snow_days','blizzard_days')),
        ('regional-snow-depth-statistics', ('max_snow_depth','mean_snow_depth','depth_sum')),
        ('snow-cover-duration', ('winter_snow_cover_days','snow_cover_days','deep_snow_days')),
        ('spring-melt-dates', ('melt_last_day','remaining_snow_june30')),
        ('spring-cold-exposure', ('spring_cold_days','cold_days','spring_risk_score','late_snow_days')),
        ('exceptional-cold-wave-events', ('exceptional_cold_days',)),
    ):
        to_csv(args.output/f'{args.phase}-{name}.csv', metrics(snow, ('group','region'), fields))
    to_csv(args.output/f'{args.phase}-river-ice-duration-comparison.csv',
           metrics(ice, ('group','reach'), ICE_NAMES))
    if training:
        normal = calibrate(snow)
        to_json(args.output/'agricultural-climate-calibration.json', normal)
        to_csv(args.output/'agricultural-climate-calibration.csv', [
            dict(region=key, p75=values[0][0], p90=values[0][1], p97=values[0][2],
                 moisture=values[1], latest_melt_day=values[2]) for key, values in normal.items()])
        if args.write_normals:
            rows = ''.join(f'    {key!r}: {value!r},\n' for key,value in normal.items())
            AGRICULTURE_MODULE.write_text(
                '"""Frozen V2.3 normals from seeds 100000–100999 in the W2 climate kernel."""\n'
                f'NORMALS = {{\n{rows}}}\n', encoding='utf-8')
    else:
        to_csv(args.output/'agricultural-climate-holdout.csv', agriculture_metrics(snow))
    to_json(args.output/f'{args.phase}-config.json', dict(
        source=git('rev-parse','HEAD').decode().strip(), runner_sha256=sha256(Path(__file__).read_bytes()),
        catalog_sha256=Catalog(ROOT/'game/data/campaigns/200-01.json').sha256,
        map_sha256=sha256((ROOT/'game/assets/map-campaign.png').read_bytes()),
        start_seed=start,samples_per_group=args.count,groups=groups, start_date=[184,11,1],days=240))
    city_audit(args.output)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
