"""Audit authored shoreline points against the campaign's actual actor locations."""
from argparse import ArgumentParser
from collections import Counter
import json
from pathlib import Path

from common import ROOT, catalog_paths, Catalog, git, open_game, sha256, to_csv, to_json
from remake import grain_units, logistics_rules, march_supply, transport_capacity


def authored_ports():
    path = ROOT/'game/config'
    river = json.loads((path/'river-network.json').read_text())
    sea = json.loads((path/'navigation-geometry.json').read_text())['ports']
    rows = []
    for city,port in sorted(river['ports'].items()):
        node = port['node']
        rows.append(dict(id=node,city=city,mode='river',position=river['nodes'][node]['position'],
                         approach=port['access']))
    for city,position in sorted(sea.items()):
        rows.append(dict(id=f'sea:{city}',city=city,mode='sea',position=position,approach=None))
    return rows,river


def route_inventory():
    counts, samples, checked, hub_access = Counter(), [], [], []
    fingerprints = {}
    for path in catalog_paths():
        engine = open_game(Catalog(path),2026)
        state = engine.state
        fingerprints[path.stem] = engine.catalog.sha256
        connections = {mode:[] for mode in ('land','pure_water')}
        with grain_units.using(state):
            routes, _, prepare = engine._python_route_graph(state, scoped=({},{}))
            for row in routes:
                for origin,target in ((row['from'],row['to']), (row['to'],row['from'])):
                    if origin not in state.cities or target not in state.cities:
                        continue
                    leg,_ = prepare(row,origin,target)
                    if leg is None:
                        continue
                    stages = logistics_rules.leg_parts(leg,engine.catalog.data['travel_rules'],locations=True)
                    ticks = sum(amount for _,amount,_ in stages)
                    if ticks != leg['days']*logistics_rules.DAY_TICKS:
                        raise ValueError(f'Directional work changed: {row["id"]} {origin}')
                    if leg['mode'] == 'land':
                        counts['land'] += 1
                        connections['land'].append((origin,target,row['id']))
                        continue
                    capacity = transport_capacity.physical(engine,state,engine._quote([origin,target],[leg]))
                    counts[capacity['mode']] += 1
                    if capacity['mode'] in ('river','sea'):
                        connections['pure_water'].append((origin,target,row['id']))
                    # Internal geometry points never occur as a target in the
                    # native directed journey, which settles only its path.
                    itinerary = engine._quote([origin,target],[leg])
                    def location(progress):
                        return march_supply.current_city(dict(quote=itinerary,supply={'route_days':progress}))
                    has_internal_location = any(location(day) is not None for day in range(1,leg['days']))
                    if has_internal_location:
                        raise ValueError(f'Unexpected non-endpoint custody: {row["id"]}')
                    water = [reach['river_id'] for reach in row.get('river_segments',())]
                    if path.stem=='209-06':
                        record=dict(scenario=path.stem,route=row['id'],origin=origin,target=target,
                            river_ids=sorted(set(water)), mode=leg['mode'], capacity=capacity['physical_capacity'],
                            stages=stages, declared_fixed_point_work=ticks,
                            authored_access=leg.get('land_access_days',0),
                            internal_location=has_internal_location,legal_split_at_shore=False)
                        checked.append(record)
                        if (row['id']=='yulin:cangwu:river'
                                or origin=='jincheng' and target=='shuofang'
                                or origin=='jiangyang' and target=='bajun'
                                or origin=='liaodong' and target=='donglai'
                                or origin=='cangwu' and target=='nanhai'):
                            samples.append(record)
        for city in sorted({name for start,end,_ in connections['pure_water'] for name in (start,end)}):
            land_in=[r for a,b,r in connections['land'] if b==city]
            land_out=[r for a,b,r in connections['land'] if a==city]
            water_in=[r for a,b,r in connections['pure_water'] if b==city]
            water_out=[r for a,b,r in connections['pure_water'] if a==city]
            if land_in and water_out or water_in and land_out:
                hub_access.append(dict(scenario=path.stem,city=city,owner=state.cities[city].owner,
                    road_into_hub=sorted(land_in),road_out_of_hub=sorted(land_out),
                    water_into_hub=sorted(water_in),water_out_of_hub=sorted(water_out)))
    return counts, checked, samples, fingerprints, hub_access


def build(output):
    ports,river = authored_ports()
    year_catalog = Catalog(ROOT/'game/data/campaigns/209-06.json')
    actor_locations = set(year_catalog.map_cities)
    river_nodes = set(river['nodes'])
    data = [dict(row,game_location=row['id'] in actor_locations,
                 parent_game_city=row['city'] in actor_locations,
                 legal_stock=False,legal_escort_stop=False,reason='geometry_only') for row in ports]
    counts, splits, samples, fingerprints, hubs = route_inventory()
    to_csv(output/'transshipment-node-census.csv',data)
    to_csv(output/'physical-node-connectivity-audit.csv',splits)
    to_csv(output/'route-split-parity.csv',samples)
    to_csv(output/'city-intermodal-connectivity.csv',hubs)
    result = dict(source=git('rev-parse','HEAD').decode().strip(),
        map_sha256=sha256((ROOT/'game/assets/map-campaign.png').read_bytes()),catalogs=fingerprints,
        current_city_ids=len(actor_locations),river_geometry_points=len(river_nodes),
        river_port_approaches=sum(row['mode']=='river' for row in data),
        sea_port_approaches=sum(row['mode']=='sea' for row in data),
        independently_legal_noncity_nodes=sum(row['legal_stock'] and row['legal_escort_stop'] for row in data),
        city_hubs_with_pure_water_access=sorted({row['city'] for row in hubs}),
        city_hub_scenario_pairs=len(hubs),
        water_directions=dict(counts),samples=samples,
        reason='Every navigable journey and every city warehouse is keyed to a campaign city. '
               'The authored shore joins and river reaches have geometry but no independent actor or cargo custody.')
    to_json(output/'topology-audit.json',result)
    return result


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    audited=build(args.output)
    print(json.dumps({key:audited[key] for key in ('current_city_ids','river_geometry_points','river_port_approaches',
                     'sea_port_approaches','independently_legal_noncity_nodes','city_hubs_with_pure_water_access',
                     'city_hub_scenario_pairs','water_directions')},ensure_ascii=False))
