"""Expand surveyed shared river reaches into ordinary playable city legs.

Each reach is authored once in river-network.json. Opposite directions reuse
its exact reversed points; a city has one land approach reused by every leg.
This compiler changes no current, weather, supply, AI or movement rules.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import re
from math import isfinite

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'game/config/river-network.json'


def _point(value):
    if (not isinstance(value, list) or len(value) != 2
            or any(type(n) not in (int, float) or not isfinite(n) for n in value)):
        raise ValueError('Invalid river network point')
    return value


def compile_network(spec, positions):
    if spec.get('schema') != 'tk2-river-network-v1':
        raise ValueError('Unknown shared river network')
    nodes, ports, rivers, reaches = (spec[key] for key in ('nodes', 'ports', 'rivers', 'reaches'))
    if len({row['id'] for row in reaches}) != len(reaches):
        raise ValueError('Duplicate shared river reach')
    reach_by_id = {row['id']: row for row in reaches}
    for identity, node in nodes.items():
        if not re.fullmatch(r'[a-z0-9][a-z0-9:_-]*', identity):
            raise ValueError('Invalid river node identity')
        _point(node['position']); _point(node['geo'])
    for identity, port in ports.items():
        if identity not in positions or port['node'] not in nodes:
            raise ValueError('Unknown river city or port')
        if port['access'][0] != positions[identity] or port['access'][-1] != nodes[port['node']]['position']:
            raise ValueError('River approach must join the city center and port')
        for point in port['access']:
            _point(point)
    for reach in reaches:
        if reach['river'] not in rivers or reach['from'] not in nodes or reach['to'] not in nodes:
            raise ValueError('Unknown river reach endpoint')
        if len(reach['points']) < 2 or reach['from'] == reach['to']:
            raise ValueError('Empty shared river reach')
        if (reach['points'][0] != nodes[reach['from']]['position']
                or reach['points'][-1] != nodes[reach['to']]['position']):
            raise ValueError('River reach must meet its shared junctions')
        for point in reach['points']:
            _point(point)
    routes, seen = [], set()
    for row in spec['connections']:
        a, b = row['from'], row['to']
        if a not in ports or b not in ports or a == b:
            raise ValueError('Invalid river city connection')
        identity = row.get('id', f'{a}:{b}:river')
        pair = frozenset((a, b))
        if pair in seen:
            raise ValueError('Duplicate playable river connection')
        seen.add(pair)
        current = ports[a]['node']
        draw = [dict(mode='land', access_id=a, points=deepcopy(ports[a]['access']))]
        geo, segments, references = [deepcopy(nodes[current]['geo'])], [], []
        for directed in row['reaches']:
            reverse = directed.startswith('-')
            reach = reach_by_id[directed[1:] if reverse else directed]
            start, end = (reach['to'], reach['from']) if reverse else (reach['from'], reach['to'])
            if current != start:
                raise ValueError('Disconnected shared river connection')
            river = rivers[reach['river']]
            draw.append(dict(mode='river', reach_id=reach['id'], river_id=reach['river'],
                             points=deepcopy(list(reversed(reach['points'])) if reverse else reach['points'])))
            segments.append(dict(reach_id=reach['id'], river_id=reach['river'],
                                 name_tc=river['name_tc'], name_ja=river['name_ja'],
                                 speed_key=river['speed_key'], distance_km=1,
                                 downstream_from=b if reverse else a))
            geo.append(deepcopy(nodes[end]['geo']))
            current = end
            references.extend(river['sources'])
        if not segments or current != ports[b]['node']:
            raise ValueError('River connection must finish at the destination port')
        draw.append(dict(mode='land', access_id=b, points=deepcopy(list(reversed(ports[b]['access'])))))
        routes.append(dict(id=identity, **{'from': a, 'to': b}, mode='river', terrain='river',
                           geo=geo, river_segments=segments, draw=draw,
                           history=dict(classification='historical_water_system_authorial_game_calibration',
                               basis='共用河段與城池接岸道路的遊戲概化；河道沿現有像素河流，港點與地理校準不是考證復原的古港。新河段沿用既有方向航速，內河不適用海路季風與海上風暴減員。',
                               sources=list(dict.fromkeys(references)))))
    return routes


def build():
    raw = SOURCE.read_bytes()
    spec = json.loads(raw)
    shared = json.loads((ROOT / 'game/config/campaigns/shared.json').read_text())['catalog']
    positions = {row['id']: row['position'] for row in shared['cities']}
    routes = compile_network(spec, positions)
    return dict(schema='tk2-river-network-compiled-v1', source_sha256=sha256(raw).hexdigest(),
                reach_count=len(spec['reaches']), routes=routes)


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False))
