"""Geographic route estimates and monthly arrival queues, exclusive to v7.

Speeds, detours and the30-day month are authorial game rules. Screen pixels
never determine distances. An on-road force retains its home roster slot,
but is excluded from defense, recruitment, allocation and subsequent orders.
"""
from heapq import heappop, heappush
from itertools import count
from math import asin, ceil, cos, radians, sin, sqrt
from .errors import GameError
from .officers import integer, select_deployment, transfer_officers


def kilometers(a, b):
    lon1, lat1, lon2, lat2 = map(radians, (*a, *b))
    h = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2
    return 6371.009 * 2 * asin(min(1, sqrt(h)))


def build_routes(data, spec):
    coords = data['city_coordinates']
    terrains = {c['id']: c['terrain'] for c in data['cities']}
    sea = {frozenset((r['from'], r['to'])) for r in spec['existing_sea']}
    extra = {frozenset((r['from'], r['to'])): r for r in spec['connections']}
    result = []
    for a, b in data['links']:
        pair = frozenset((a, b))
        custom = extra.get(pair)
        # Existing over-sea links must never acquire a fictitious land option.
        if pair not in sea and not (custom and custom.get('sea_only')):
            terrain = 'mountain' if 'mountain' in (terrains[a], terrains[b]) else 'plain'
            if custom and custom.get('terrain'): terrain = custom['terrain']
            distance = round(kilometers(coords[a], coords[b]) * spec['rules']['detours'][terrain], 1)
            result.append(dict(id=f'{a}:{b}:land', **{'from': a, 'to': b}, mode='land', terrain=terrain,
                distance_km=distance, land_km=distance, sea_km=0, days=max(1, ceil(distance/spec['rules']['speeds'][terrain]))))
        if pair in sea or custom and custom['mode'] == 'sea':
            coastal = custom if custom and custom['mode']=='sea' else next(r for r in spec['existing_sea'] if {r['from'],r['to']}=={a,b})
            waypoints = coastal['geo']
            if coastal['from'] != a: waypoints = list(reversed(waypoints))
            land = round((kilometers(coords[a],waypoints[0])+kilometers(waypoints[-1],coords[b]))*spec['rules']['detours']['plain'],1)
            water = round(sum(kilometers(x,y) for x,y in zip(waypoints,waypoints[1:])),1)
            distance = round(land+water,1)
            days = max(1, ceil(land/spec['rules']['speeds']['plain'])+ceil(water/spec['rules']['speeds']['sea'])+spec['rules']['embark_days'])
            result.append(dict(id=f'{a}:{b}:sea', **{'from': a, 'to': b}, mode='sea', terrain='sea',
                               distance_km=distance, land_km=land, sea_km=water, days=days))
    return result


class TravelCampaign:
    @property
    def travelling(self):
        return bool(self.catalog.data.get('travel_rules'))

    def _march_ids(self, state):
        return {i for r in state.extension.get('travel', {}).get('marches', []) for i in r['officers']}

    def _travel_path(self, state, source, target, owner, mode='fastest', *, adjacent=False):
        if mode not in {'fastest', 'land'}: raise GameError('请选择有效的行军路线。')
        routes = self.catalog.data['travel_routes']
        serial = count()
        queue = [(0, 0, source, next(serial), [source], [])]
        seen = set()
        while queue:
            days, distance, here, _, path, legs = heappop(queue)
            if here in seen: continue
            seen.add(here)
            if here == target and legs:
                months = max(1, ceil(days/30))
                return dict(path=path, routes=legs, days=days, months=months,
                            distance_km=round(distance, 1), grain_per_officer=5*len(legs),
                            modes=sorted({r['mode'] for r in legs}))
            for route in routes:
                if here not in (route['from'], route['to']) or mode == 'land' and route['mode'] == 'sea': continue
                nxt = route['to'] if here == route['from'] else route['from']
                if nxt not in state.cities or nxt in seen: continue
                if adjacent and (here != source or nxt != target): continue
                if not adjacent and state.cities[nxt].owner != owner: continue
                heappush(queue, (days+route['days'], distance+route['distance_km'], nxt, next(serial), path+[nxt], legs+[route]))
        return None

    def _queue_march(self, state, source, target, ids, kind, mode='fastest'):
        quote = self._travel_path(state, source.id, target.id, source.owner, mode, adjacent=kind == 'attack')
        if not quote: raise GameError('没有满足海陆选择及本方连通条件的路线。')
        if not ids or len(ids) != len(set(ids)) or any(i in self._march_ids(state) for i in ids):
            raise GameError('请选择尚未出发且不重复的武将。')
        if kind == 'attack': ids = list(select_deployment(source.roster, ids, state.officers))
        elif len(target.roster.officer_ids)+len(ids)>self.catalog.rules.city_officer_capacity:
            raise GameError('目的城武将容量不足。')
        grain = max(1, sum(state.officers[i].troops for i in ids)//25) if kind == 'attack' else len(ids)*quote['grain_per_officer']
        if source.grain < grain: raise GameError('行军粮食不足。')
        source.grain -= grain
        source.action_used = True
        state.extension['officer_actions'].update({str(i): state.turn for i in ids})
        travel = state.extension['travel']
        travel['counter'] += 1
        row = dict(id=travel['counter'], source=source.id, target=target.id, owner=source.owner,
                   officers=ids, kind=kind, mode=mode, departure_turn=state.turn,
                   arrival_turn=state.turn+quote['months'], checked_turn=0, quote=quote)
        travel['marches'].append(row)
        self._note(state, f'{len(ids)}将从{self.catalog.map_cities[source.id]["name"]}出发，'
                   f'至{self.catalog.map_cities[target.id]["name"]}约{quote["distance_km"]}公里、{quote["days"]}日，'
                   f'{quote["months"]}个月回合后到达，耗粮{grain}。')

    def _prune_marches(self, state):
        if not self.travelling: return
        travel = state.extension['travel']
        for row in list(travel['marches']):
            source = state.cities[row['source']]
            row['officers'] = [i for i in row['officers'] if i in source.roster.officer_ids
                               and state.officers[i].alive and state.officers[i].faction_id == row['owner']]
            if not row['officers'] or source.owner != row['owner']:
                travel['marches'].remove(row)
                self._note(state, f'行军{row["id"]}因出发城失陷或人员退场取消。')

    def _arrivals(self, state, payload):
        if not self.travelling or state.phase != 'arrivals': raise GameError('当前没有待处理的到达事件。')
        travel = state.extension['travel']
        self._prune_marches(state)
        for row in sorted(list(travel['marches']), key=lambda r: (r['arrival_turn'], r['id'])):
            if row not in travel['marches']: continue  # Earlier conquest may cancel a later column.
            if row['arrival_turn'] > state.turn or row['checked_turn'] == state.turn: continue
            row['checked_turn'] = state.turn
            source, target = (state.cities[row[k]] for k in ('source', 'target'))
            ids = row['officers']
            if row['kind']=='transfer' and any(state.cities[k].owner!=row['owner'] for k in row['quote']['path'][1:-1]):
                travel['marches'].remove(row)
                self._note(state, f'调动{row["id"]}沿途城池易主，路线中断，部队返回出发城编制。')
                continue
            if target.owner == row['owner']:
                if len(target.roster.officer_ids)+len(ids)>self.catalog.rules.city_officer_capacity:
                    self._note(state, f'{self.catalog.map_cities[target.id]["name"]}已满员，行军{row["id"]}等待下月入城。')
                    continue
                transfer_officers(source.roster, target.roster, ids)
                travel['marches'].remove(row)
                state.extension['officer_actions'].update({str(i): state.turn for i in ids})
                self._note(state, f'行军{row["id"]}到达{self.catalog.map_cities[target.id]["name"]}，{len(ids)}将入城。')
            elif row['kind'] == 'transfer':
                travel['marches'].remove(row)
                self._note(state, f'目的城已易主，调动{row["id"]}取消，部队返回出发城编制。')
            else:
                travel['marches'].remove(row)
                ids = [i for i in ids if state.officers[i].troops>0 and state.officers[i].health>0]
                if not ids: continue
                self._start_expanded_battle(state, source, target, ids, paid=True)
                travel['battle_arrival'] = True
                if state.player in (source.owner, target.owner): return
                self._resolve_ai_battle(state)
                if state.phase == 'finished': return
                state.phase = 'arrivals'
        state.phase = 'city'

    def _resolve_ai_battle(self, state):
        """Same damage/settlement as the legacy AI; no second supply charge."""
        battle = state.battle
        for _ in range(200):
            if state.phase == 'result': break
            a = max((u for u in battle['attackers'] if u['troops']>0), key=lambda u:u['troops'])
            t = max((u for u in battle['defenders'] if u['troops']>0), key=lambda u:u['troops'])
            t['troops'] -= self._damage(state,a,t)
            if t['troops']>0: a['troops'] -= self._damage(state,t,a)
            self._battle_result(state)
        if state.phase=='battle': battle['outcome']='retreat';state.phase='result'
        self._expanded_settle(state,{'battle_id':battle['id']})

    def _travel_view(self, state):
        if not self.travelling: return {}
        quotes = {}
        if state:
            for source in state.cities.values():
                if source.owner != state.player: continue
                for target in state.cities.values():
                    if source.id == target.id: continue
                    adjacent = target.owner != state.player
                    if adjacent and frozenset((source.id, target.id)) not in self.catalog.links: continue
                    for mode in ('fastest', 'land'):
                        quote = self._travel_path(state, source.id, target.id, state.player, mode, adjacent=adjacent)
                        if quote: quotes[f'{source.id}:{target.id}:{mode}'] = quote
        return dict(travel_rules=self.catalog.data['travel_rules'], travel_quotes=quotes)

    def _validate_travel(self, state):
        if not self.travelling: return
        x = state.extension['travel']
        if not isinstance(x, dict) or set(x) != {'counter', 'marches', 'battle_arrival'}: raise ValueError('travel fields')
        integer(x['counter'], 0, 1000000, 'march counter')
        if type(x['battle_arrival']) is not bool or x['battle_arrival'] and state.phase not in {'battle', 'result'}:
            raise ValueError('arrival continuation')
        if not isinstance(x['marches'], list) or len(x['marches'])>1000: raise ValueError('march queue')
        seen, serials = set(), set()
        for row in x['marches']:
            if set(row) != {'id','source','target','owner','officers','kind','mode','departure_turn','arrival_turn','checked_turn','quote'}: raise ValueError('march fields')
            integer(row['id'], 1, x['counter'], 'march id')
            if row['id'] in serials: raise ValueError('duplicate march id')
            serials.add(row['id'])
            if row['source'] == row['target'] or row['source'] not in state.cities or row['target'] not in state.cities: raise ValueError('march city')
            source = state.cities[row['source']]
            if source.owner != row['owner'] or row['owner'] not in self.catalog.factions or row['kind'] not in {'attack','transfer'}: raise ValueError('march ownership')
            ids = row['officers']
            if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)) or seen.intersection(ids) or not set(ids)<=set(source.roster.officer_ids): raise ValueError('march officers')
            for ident in ids: self.catalog.rules.officer_id(ident)
            if row['kind']=='attack' and len(ids)>self.catalog.rules.battle_officers_per_side: raise ValueError('march deployment')
            seen.update(ids)
            integer(row['departure_turn'], 1, state.turn, 'march departure')
            integer(row['arrival_turn'], row['departure_turn']+1, 1000000, 'march arrival')
            integer(row['checked_turn'], 0, state.turn, 'march arrival cursor')
            # Validate route geometry against immutable catalog data, allowing
            # intermediate cities to have changed owner since departure.
            quote = row['quote']
            if not isinstance(quote,dict) or set(quote)!={'path','routes','days','months','distance_km','grain_per_officer','modes'}: raise ValueError('march quote')
            for key in ('days','months','grain_per_officer'): integer(quote[key],1,1000000,'march '+key)
            path, legs = quote['path'], quote['routes']
            if not isinstance(path,list) or not path or len(path)!=len(set(path)) or any(key not in state.cities for key in path) or path[0]!=row['source'] or path[-1]!=row['target'] or len(legs)!=len(path)-1: raise ValueError('march path')
            if row['mode'] not in {'fastest','land'}: raise ValueError('march mode')
            for a,b,leg in zip(path,path[1:],legs):
                if leg not in self.catalog.data['travel_routes'] or {leg['from'],leg['to']}!={a,b} or row['mode']=='land' and leg['mode']=='sea': raise ValueError('march leg')
            days = sum(r['days'] for r in legs)
            expected = dict(path=path,routes=legs,days=days,months=max(1,ceil(days/30)),distance_km=round(sum(r['distance_km'] for r in legs),1),grain_per_officer=5*len(legs),modes=sorted({r['mode'] for r in legs}))
            if quote!=expected or row['arrival_turn']!=row['departure_turn']+quote['months']: raise ValueError('march ETA')
            if row['kind']=='attack' and len(legs)!=1: raise ValueError('attack path')
        if state.battle and seen.intersection(u['id'] for k in ('attackers','defenders') for u in state.battle[k]): raise ValueError('marching unit deployed twice')
