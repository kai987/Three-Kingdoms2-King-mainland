"""Geographic route estimates and ten-day queues for travel-enabled catalogs.

Speeds, detours and the30-day month are authorial game rules. Compiled curves
use geographic endpoint calibration, never a global screen-pixel scale.
An on-road force retains its home roster slot,
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
    def _march_ids(self, state):
        return {i for r in state.extension.get('travel', {}).get('marches', []) for i in r['officers']}

    def _travel_modes(self):
        return ('fastest','land','sea','special','explore')

    def _known_routes(self, state):
        routes = self.catalog.data['travel_routes']
        if state is None:
            return routes
        discovered = set(state.extension['travel']['discovered'])
        return routes + [row for row in self.catalog.data.get('exploration_routes', [])
                         if row['id'] in discovered]

    def _exploration_route(self, source, target):
        coastal = set(self.catalog.data['travel_hazards']['coastal_cities'])
        if source == target or source not in coastal or target not in coastal:
            return None
        return next((row for row in self.catalog.data.get('exploration_routes', [])
                     if {row['from'],row['to']} == {source,target}), None)

    @staticmethod
    def _quote(path, legs):
        days = sum(row['days'] for row in legs)
        distance = round(sum(row['distance_km'] for row in legs),1)
        # Browser JSON.stringify writes integral numbers without a .0 suffix;
        # Current save checksums must survive browser download/upload roundtrips.
        if type(distance) is float and distance.is_integer():
            distance = int(distance)
        return dict(path=path,routes=legs,days=days,months=max(1,ceil(days/30)),turns=max(1,ceil(days/10)),
                    distance_km=distance,
                    grain_per_officer=5*len(legs),modes=sorted({row['mode'] for row in legs}))

    def _travel_path(self, state, source, target, owner, mode='fastest', *, adjacent=False):
        from .march_core import enabled, invoke, state_input
        if enabled():
            if mode not in self._travel_modes():
                raise GameError('请选择有效的行军路线。')
            return invoke('path', data=self.catalog.data, **state_input(state),
                          source=source, target=target, owner=owner, mode=mode,
                          adjacent=adjacent)
        return self._python_travel_path(state, source, target, owner, mode, adjacent=adjacent)

    def _python_travel_path(self, state, source, target, owner, mode='fastest', *, adjacent=False):
        from .route_hazards import evaluate_leg, route_allowed
        if mode not in self._travel_modes():
            raise GameError('请选择有效的行军路线。')
        if source == target or source not in state.cities or target not in state.cities:
            return None
        if not adjacent and state.cities[target].owner != owner:
            return None
        routes = self._known_routes(state)
        if mode in ('sea','special','explore'):
            if mode == 'explore':
                raw = self._exploration_route(source,target)
                if raw is None or any(row['mode']=='sea' and {row['from'],row['to']}=={source,target}
                                      for row in routes):
                    return None
                candidates = [raw]
            else:
                candidates = [row for row in routes if {row['from'],row['to']}=={source,target}
                              and (row['mode']=='sea' if mode=='sea' else row.get('special') in ('yinping','ziwu'))]
                # The current Yinping route is identified by its endpoint pair.
                if mode == 'special':
                    candidates += [row for row in routes if row not in candidates
                                   and {row['from'],row['to']}=={source,target}
                                   and {source,target}=={'yinping','shujun'} and row['mode']=='land']
            legs = [evaluate_leg(self.catalog.data,row,source,target,state.month)
                    for row in candidates if route_allowed(self.catalog.data,row,source,target)]
            if not legs:
                return None
            leg = min(legs,key=lambda row:(row['days'],row['distance_km'],row['id']))
            return self._quote([source,target],[leg])
        serial = count()
        queue = [(0,0,source,next(serial),[source],[])]
        seen = set()
        while queue:
            days,distance,here,_,path,legs = heappop(queue)
            if here in seen:
                continue
            seen.add(here)
            if here == target and legs:
                return self._quote(path,legs)
            for raw in routes:
                if here not in (raw['from'],raw['to']) or mode=='land' and raw['mode']=='sea':
                    continue
                nxt = raw['to'] if here==raw['from'] else raw['from']
                if nxt not in state.cities or nxt in seen:
                    continue
                if adjacent and (here!=source or nxt!=target):
                    continue
                if not adjacent and state.cities[nxt].owner not in (owner, 'neutral'):
                    continue
                if not route_allowed(self.catalog.data,raw,here,nxt):
                    continue
                leg = evaluate_leg(self.catalog.data,raw,here,nxt,state.month)
                heappush(queue,(days+leg['days'],distance+leg['distance_km'],nxt,next(serial),path+[nxt],legs+[leg]))
        return None

    def _march_risks(self, quote, rng=None):
        """One storm for the complete voyage, fixed valley hazards per leg."""
        result = []
        storm = None
        for index,leg in enumerate(quote['routes']):
            hazard = leg.get('hazard')
            if not hazard:
                continue
            if hazard['kind']=='monsoon_storm' and storm is not None:
                storm['legs'].append(index)
                continue
            if hazard['kind']=='monsoon_storm':
                low,high = hazard['loss_percent_min'],hazard['loss_percent_max']
                # Read-only previews never supply rng or select a loss roll.
                numerator = None if rng is None else 100-(low+rng.next()%(high-low+1))
                denominator = 100
            else:
                numerator = hazard['survival_numerator']
                denominator = hazard['survival_denominator']
            risk = dict(legs=[index],kind=hazard['kind'],survival_numerator=numerator,
                        survival_denominator=denominator,applied=False,before={},after={},lost=0)
            result.append(risk)
            if hazard['kind']=='monsoon_storm':
                storm = risk
        return result

    def _apply_march_risks(self, state, row):
        from .route_hazards import allocate_survivors
        ids = sorted(row['officers'])
        for risk in row['risks']:
            if risk['applied']:
                continue
            before = [state.officers[i].troops for i in ids]
            after = allocate_survivors(before,risk['survival_numerator'],risk['survival_denominator'])
            risk.update(applied=True,before={str(i):n for i,n in zip(ids,before)},
                        after={str(i):n for i,n in zip(ids,after)},lost=sum(before)-sum(after))
            for ident,troops in zip(ids,after):
                state.officers[ident].troops = troops
            state.soldiers['lost'] += risk['lost']
            label = row['quote']['routes'][risk['legs'][0]]['hazard']['label']
            self._note(state,f'行军{row["id"]}遭遇{label}，全程兵员由{sum(before)}减至{sum(after)}，伤亡{risk["lost"]}；减员只结算一次。')
            if row['owner']==state.player:
                self._emit_event(state,'march_weather',person_ids=[state.officers[i].person_id for i in ids[:1]],
                    city_ids=[row['source'],row['target']],factions=[row['owner']],
                    details=dict(march_id=row['id'],lost=risk['lost'],risks=[dict(kind=risk['kind'],
                    loss_percent=100*(risk['survival_denominator']-risk['survival_numerator'])//risk['survival_denominator'])]))
        return sum(state.officers[i].troops for i in ids)>0

    def _discover_march_route(self, state, row):
        if row['mode']!='explore':
            return
        route_id = row['quote']['routes'][0]['id']
        discovered = state.extension['travel']['discovered']
        if route_id not in discovered:
            discovered.append(route_id)
            source,target = (self.catalog.map_cities[row[k]]['name'] for k in ('source','target'))
            self._note(state,f'探索航行成功抵达{target}，发现{source}—{target}海路，现已显示在地图上。')
            self._emit_event(state,'route_discovered',city_ids=[row['source'],row['target']],
                factions=[row['owner']],details={'from':row['source'],'to':row['target']},audience='world')

    def _queue_march(self, state, source, target, ids, kind, mode='fastest'):
        quote = self._travel_path(state, source.id, target.id, source.owner, mode, adjacent=kind == 'attack')
        if not quote: raise GameError('没有满足海陆选择及本方连通条件的路线。')
        if not ids or len(ids) != len(set(ids)) or any(i in self._march_ids(state) for i in ids):
            raise GameError('请选择尚未出发且不重复的武将。')
        if kind == 'attack': ids = list(select_deployment(source.roster, ids, state.officers))
        elif len(target.roster.officer_ids)+len(ids)>self.catalog.rules.city_officer_capacity:
            raise GameError('目的城武将容量不足。')
        if mode=='explore' and not sum(state.officers[i].troops for i in ids):
            raise GameError('探索航行至少需要一名带兵武将。')
        grain = max(1, sum(state.officers[i].troops for i in ids)//25) if kind == 'attack' else len(ids)*quote['grain_per_officer']
        if source.grain < grain: raise GameError('行军粮食不足。')
        source.grain -= grain
        source.action_used = True
        state.extension['officer_actions'].update({str(i): state.turn for i in ids})
        travel = state.extension['travel']
        travel['counter'] += 1
        row = dict(id=travel['counter'], source=source.id, target=target.id, owner=source.owner,
                   officers=ids, kind=kind, mode=mode, departure_turn=state.turn,
                   arrival_turn=state.turn+quote['turns'], checked_turn=0, quote=quote)
        row.update(departure_year=state.year,departure_month=state.month,departure_day=state.day,
                   departure_troops={str(i):state.officers[i].troops for i in ids},
                   risks=self._march_risks(quote,state.rng))
        travel['marches'].append(row)
        self._note(state, f'{len(ids)}将从{self.catalog.map_cities[source.id]["name"]}出发，'
                   f'至{self.catalog.map_cities[target.id]["name"]}约{quote["distance_km"]}公里、{quote["days"]}日，'
                   f'{quote["turns"]}旬后到达（每旬10天），耗粮{grain}。')

    def _prune_marches(self, state):
        travel = state.extension['travel']
        for row in list(travel['marches']):
            source = state.cities[row['source']]
            row['officers'] = [i for i in row['officers'] if i in source.roster.officer_ids
                               and state.officers[i].alive and state.officers[i].faction_id == row['owner']]
            if not row['officers'] or source.owner != row['owner']:
                travel['marches'].remove(row)
                self._note(state, f'行军{row["id"]}因出发城失陷或人员退场取消。')
                if row['owner']==state.player:
                    self._emit_event(state,'march_returned',city_ids=[row['source'],row['target']],
                        factions=[row['owner']],details=dict(march_id=row['id'],reason='origin_changed'))

    def _arrivals(self, state, payload):
        if state.phase != 'arrivals': raise GameError('当前没有待处理的到达事件。')
        travel = state.extension['travel']
        self._prune_marches(state)
        for row in sorted(list(travel['marches']), key=lambda r: (r['arrival_turn'], r['id'])):
            if row not in travel['marches']: continue  # Earlier conquest may cancel a later column.
            if row['arrival_turn'] > state.turn or row['checked_turn'] == state.turn: continue
            row['checked_turn'] = state.turn
            source, target = (state.cities[row[k]] for k in ('source', 'target'))
            ids = row['officers']
            if row['kind']=='transfer' and any(state.cities[k].owner not in (row['owner'], 'neutral')
                                              for k in row['quote']['path'][1:-1]):
                travel['marches'].remove(row)
                self._note(state, f'调动{row["id"]}沿途城池易主，路线中断，部队返回出发城编制。')
                if row['owner']==state.player:
                    self._emit_event(state,'march_returned',city_ids=[source.id,target.id],factions=[row['owner']],
                        details=dict(march_id=row['id'],reason='route_blocked'))
                continue
            if row['kind']=='transfer' and target.owner!=row['owner']:
                travel['marches'].remove(row)
                self._note(state,f'目的城已易主，调动{row["id"]}取消，部队返回出发城编制。')
                if row['owner']==state.player:
                    self._emit_event(state,'march_returned',city_ids=[source.id,target.id],factions=[row['owner']],
                        details=dict(march_id=row['id'],reason='target_changed'))
                continue
            if row['risks'] and not self._apply_march_risks(state,row):
                travel['marches'].remove(row)
                self._note(state,f'行军{row["id"]}遭遇灾害后带兵全损，航行或进军失败；武将返回出发城编制，未发现新航路。')
                if row['owner']==state.player:
                    self._emit_event(state,'march_returned',city_ids=[source.id,target.id],factions=[row['owner']],
                        details=dict(march_id=row['id'],reason='army_lost'))
                continue
            if target.owner == row['owner']:
                if len(target.roster.officer_ids)+len(ids)>self.catalog.rules.city_officer_capacity:
                    self._note(state, f'{self.catalog.map_cities[target.id]["name"]}已满员，行军{row["id"]}等待下一旬入城。')
                    continue
                transfer_officers(source.roster, target.roster, ids)
                self._discover_march_route(state,row)
                travel['marches'].remove(row)
                state.extension['officer_actions'].update({str(i): state.turn for i in ids})
                self._note(state, f'行军{row["id"]}到达{self.catalog.map_cities[target.id]["name"]}，{len(ids)}将入城。')
                if row['owner']==state.player:
                    self._emit_event(state,'march_arrived',person_ids=[state.officers[i].person_id for i in ids[:1]],
                        city_ids=[source.id,target.id],factions=[row['owner']],details=dict(march_id=row['id'],officers=len(ids)))
            else:
                travel['marches'].remove(row)
                ids = [i for i in ids if state.officers[i].troops>0 and state.officers[i].health>0]
                if not ids: continue
                self._discover_march_route(state,row)
                self._start_expanded_battle(state, source, target, ids, paid=True)
                travel['battle_arrival'] = True
                if state.player in (source.owner, target.owner): return
                self._resolve_ai_battle(state)
                if state.phase == 'finished': return
                state.phase = 'arrivals'
        state.phase = 'city'

    def _resolve_ai_battle(self, state):
        """Both sides use real actions/effects, with a bounded number of turns."""
        from .campaign_expansion import TACTICS
        from .difficulty import get_settings
        from .tactical_ai import choose_action
        battle = state.battle
        used={'attackers':set(),'defenders':set()};side='attackers'
        terrain=self.catalog.map_cities[battle['target']]['terrain']
        settings=get_settings(state)
        for _ in range(200):
            if state.phase == 'result': break
            self._battle_result(state)
            if state.phase=='result':break
            live={key:{u['id'] for u in battle[key] if u['troops']>0} for key in used}
            if all(not live[key]-used[key] for key in used):
                used={key:set() for key in used};battle['round']+=1
                for support in battle['extended']['support'].values():support['energy']=min(18,support['energy']+4)
            foe='defenders' if side=='attackers' else 'attackers'
            if not live[side]-used[side]:side,foe=foe,side
            choice=choose_action(state,battle,side,foe,terrain,TACTICS,settings=settings,
                damage_percent=self.catalog.data['rules']['battle_damage_percent'],used=used[side])
            if choice is None:break
            self._perform_battle_action(state,choice,side,foe,finish=False)
            used[side].add(choice['actor'])
            side=foe
            self._battle_result(state)
        if state.phase=='battle': battle['outcome']='retreat';state.phase='result'
        self._expanded_settle(state,{'battle_id':battle['id']})

    def _travel_view(self, state):
        from .march_core import enabled, invoke, state_input
        if not enabled():
            return self._python_travel_view(state)
        # Reuse metadata construction without a second route search.
        result = self._python_travel_view(None)
        if state is not None:
            discovered = set(state.extension['travel']['discovered'])
            result['discovered_routes'] = [row for row in self.catalog.data.get('exploration_routes', [])
                                           if row['id'] in discovered]
            result['travel_quotes'] = invoke('batch', data=self.catalog.data,
                                            **state_input(state), player=state.player)
        return result

    def _python_travel_view(self, state):
        """Quote each friendly route tree once, without advancing saved RNG."""
        from .route_hazards import evaluate_leg, route_allowed
        quotes={}
        discovered=set(state.extension['travel']['discovered']) if state else set()
        result=dict(travel_rules=self.catalog.data['travel_rules'],travel_quotes=quotes,
                    travel_hazards=self.catalog.data['travel_hazards'],
                    discovered_routes=[r for r in self.catalog.data.get('exploration_routes',[]) if r['id'] in discovered],
                    coastal_city_ids=list(self.catalog.data['travel_hazards'].get('coastal_cities',[])))
        if state is None:
            return result
        routes=self._known_routes(state)
        adjacency={key:[] for key in state.cities}
        for raw in routes:
            for a,b in ((raw['from'],raw['to']),(raw['to'],raw['from'])):
                if a in adjacency and b in adjacency and route_allowed(self.catalog.data,raw,a,b):
                    adjacency[a].append(evaluate_leg(self.catalog.data,raw,a,b,state.month))
        known_sea={frozenset((r['from'],r['to'])) for r in routes if r['mode']=='sea'}
        explorations={key:[] for key in state.cities}
        for raw in self.catalog.data.get('exploration_routes',[]):
            if frozenset((raw['from'],raw['to'])) in known_sea:
                continue
            for a,b in ((raw['from'],raw['to']),(raw['to'],raw['from'])):
                if a in explorations and b in explorations and raw==self._exploration_route(a,b):
                    explorations[a].append(evaluate_leg(self.catalog.data,raw,a,b,state.month))
        for source,city in state.cities.items():
            if city.owner!=state.player:
                continue
            for mode in ('fastest','land'):
                serial=count();queue=[(0,0,source,next(serial),[source],[])];seen=set()
                while queue:
                    days,distance,here,_,path,legs=heappop(queue)
                    if here in seen:
                        continue
                    seen.add(here)
                    # Neutral cities can connect the tree, but only our own
                    # cities are transfer destinations. Direct attacks below
                    # are quoted independently of this transit search.
                    if legs and state.cities[here].owner==state.player:
                        quotes[f'{source}:{here}:{mode}']=self._quote(path,legs)
                    for leg in adjacency[here]:
                        target=leg['to']
                        if target in seen or state.cities[target].owner not in (state.player, 'neutral') or mode=='land' and leg['mode']=='sea':
                            continue
                        heappush(queue,(days+leg['days'],distance+leg['distance_km'],target,next(serial),path+[target],legs+[leg]))
                # Attacks remain direct city-to-city legs; friendly paths above
                # cannot tunnel through an enemy and emerge at another city.
                targets={leg['to'] for leg in adjacency[source] if state.cities[leg['to']].owner!=state.player}
                for target in targets:
                    options=[leg for leg in adjacency[source] if leg['to']==target and (mode!='land' or leg['mode']=='land')]
                    if options:
                        leg=min(options,key=lambda r:(r['days'],r['distance_km']))
                        quotes[f'{source}:{target}:{mode}']=self._quote([source,target],[leg])
            for mode in ('sea','special'):
                targets=({leg['to'] for leg in adjacency[source] if leg['mode']=='sea'} if mode=='sea'
                         else {leg['to'] for leg in adjacency[source] if leg.get('hazard') and
                               leg['hazard']['kind'] in ('yinping','ziwu_rain','ziwu_dry')})
                for target in targets:
                    options=[leg for leg in adjacency[source] if leg['to']==target and
                             (leg['mode']=='sea' if mode=='sea' else leg.get('hazard') and
                              leg['hazard']['kind'] in ('yinping','ziwu_rain','ziwu_dry'))]
                    leg=min(options,key=lambda r:(r['days'],r['distance_km']))
                    quotes[f'{source}:{target}:{mode}']=self._quote([source,target],[leg])
            for leg in explorations[source]:
                quotes[f'{source}:{leg["to"]}:explore']=self._quote([source,leg['to']],[leg])
        return result

    def _validate_travel(self, state):
        from .route_hazards import allocate_survivors, evaluate_leg, route_allowed
        x=state.extension['travel']
        if not isinstance(x,dict) or set(x)!={'counter','marches','battle_arrival','discovered'}:
            raise ValueError('hazard travel fields')
        integer(x['counter'],0,1000000,'march counter')
        if type(x['battle_arrival']) is not bool or x['battle_arrival'] and state.phase not in {'battle','result'}:
            raise ValueError('arrival continuation')
        exploration={row['id']:row for row in self.catalog.data.get('exploration_routes',[])}
        raw_routes={row['id']:row for row in self.catalog.data['travel_routes']}
        if raw_routes.keys() & exploration.keys():
            raise ValueError('ambiguous discovery route identity')
        discovered=x['discovered']
        if not isinstance(discovered,list) or len(discovered)!=len(set(discovered)):
            raise ValueError('discovered route list')
        for ident in discovered:
            if not isinstance(ident,str) or ident not in exploration:
                raise ValueError('unknown discovered route')
            raw=exploration[ident]
            if raw!=self._exploration_route(raw['from'],raw['to']) or any(raw[k] not in state.cities for k in ('from','to')):
                raise ValueError('unopened discovered coastline')
        all_routes={**raw_routes,**exploration}
        if not isinstance(x['marches'],list) or len(x['marches'])>1000:
            raise ValueError('march queue')
        seen,serials=set(),set()
        fields={'id','source','target','owner','officers','kind','mode','departure_turn','arrival_turn','checked_turn','quote',
                'departure_year','departure_month','departure_day','departure_troops','risks'}
        for row in x['marches']:
            if not isinstance(row,dict) or set(row)!=fields:
                raise ValueError('hazard march fields')
            integer(row['id'],1,x['counter'],'march id')
            if row['id'] in serials:
                raise ValueError('duplicate march id')
            serials.add(row['id'])
            if row['source']==row['target'] or any(row[k] not in state.cities for k in ('source','target')):
                raise ValueError('march city')
            source=state.cities[row['source']]
            if source.owner!=row['owner'] or row['owner'] not in self.catalog.factions or row['kind'] not in {'attack','transfer'}:
                raise ValueError('march ownership')
            ids=row['officers']
            if not isinstance(ids,list) or not ids or len(ids)!=len(set(ids)) or seen.intersection(ids) or not set(ids)<=set(source.roster.officer_ids):
                raise ValueError('march officers')
            for ident in ids:
                self.catalog.rules.officer_id(ident)
                if not state.officers[ident].alive or state.officers[ident].faction_id!=row['owner']:
                    raise ValueError('march officer membership')
            if row['kind']=='attack' and len(ids)>self.catalog.rules.battle_officers_per_side:
                raise ValueError('march deployment')
            seen.update(ids)
            integer(row['departure_turn'],1,state.turn,'march departure')
            integer(row['arrival_turn'],row['departure_turn']+1,1000000,'march arrival')
            integer(row['checked_turn'],0,state.turn,'march arrival cursor')
            integer(row['departure_year'],self.catalog.data['start_year'],state.year,'march departure year')
            integer(row['departure_month'],1,12,'march departure month')
            integer(row['departure_day'],1,21,'march departure day')
            if row['departure_day'] not in (1,11,21):
                raise ValueError('march departure ten-day period')
            departure=(((row['departure_year']-self.catalog.data['start_year'])*12
                       +row['departure_month']-self.catalog.data['start_month'])*3
                       +(row['departure_day']-1)//10+1)
            if departure!=row['departure_turn']:
                raise ValueError('march departure calendar')
            if row['mode'] not in self._travel_modes():
                raise ValueError('march mode')
            quote=row['quote']
            if not isinstance(quote,dict) or set(quote)!={'path','routes','days','months','turns','distance_km','grain_per_officer','modes'}:
                raise ValueError('march quote')
            for key in ('days','months','turns','grain_per_officer'):
                integer(quote[key],1,1000000,'march '+key)
            path,legs=quote['path'],quote['routes']
            if not isinstance(path,list) or len(path)<2 or len(path)!=len(set(path)) or any(k not in state.cities for k in path) or path[0]!=row['source'] or path[-1]!=row['target'] or not isinstance(legs,list) or len(legs)!=len(path)-1:
                raise ValueError('march path')
            for a,b,leg in zip(path,path[1:],legs):
                if not isinstance(leg,dict) or leg.get('id') not in all_routes:
                    raise ValueError('unknown march leg')
                raw=all_routes[leg['id']]
                if {raw['from'],raw['to']}!={a,b} or not route_allowed(self.catalog.data,raw,a,b):
                    raise ValueError('march direction')
                if row['mode']=='land' and raw['mode']=='sea':
                    raise ValueError('land march uses sea')
                if leg!=evaluate_leg(self.catalog.data,raw,a,b,row['departure_month']):
                    raise ValueError('altered departure weather or route')
                if leg['id'] in exploration and row['mode']!='explore' and leg['id'] not in discovered:
                    raise ValueError('undiscovered route used as known')
            if row['mode'] in ('sea','special','explore') or row['kind']=='attack':
                if len(legs)!=1:
                    raise ValueError('direct route mode needs one leg')
            if row['mode']=='sea' and legs[0]['mode']!='sea':
                raise ValueError('sea mode needs sea leg')
            if row['mode']=='special' and not legs[0].get('hazard',{}):
                raise ValueError('special mode needs valley hazard')
            if row['mode']=='special' and legs[0]['hazard']['kind'] not in ('yinping','ziwu_rain','ziwu_dry'):
                raise ValueError('special mode is not a valley')
            if row['mode']=='explore' and legs[0]['id'] not in exploration:
                raise ValueError('exploration needs coastal candidate')
            if quote!=self._quote(path,legs) or row['arrival_turn']!=row['departure_turn']+quote['turns']:
                raise ValueError('march ETA')
            manifest=row['departure_troops']
            if not isinstance(manifest,dict) or not manifest or not {str(i) for i in ids}<=manifest.keys():
                raise ValueError('march departure manifest')
            for text,amount in manifest.items():
                if not isinstance(text,str) or not text.isdigit() or str(int(text))!=text:
                    raise ValueError('march manifest identity')
                ident=self.catalog.rules.officer_id(int(text))
                if ident not in state.officers:
                    raise ValueError('unknown manifest officer')
                integer(amount,0,999,'departure troops')
                if ident not in ids and state.officers[ident].alive:
                    raise ValueError('live manifest officer omitted')
            expected=self._march_risks(quote)
            risks=row['risks']
            if not isinstance(risks,list) or len(risks)!=len(expected):
                raise ValueError('march risk count')
            applied=[]
            prior=dict(manifest)
            for actual,template in zip(risks,expected):
                if not isinstance(actual,dict) or set(actual)!=set(template):
                    raise ValueError('march risk fields')
                for key in ('legs','kind','survival_denominator'):
                    if actual[key]!=template[key]:
                        raise ValueError('march risk identity')
                numerator=actual['survival_numerator']
                integer(actual['survival_denominator'],1,1000000,'survival denominator')
                integer(numerator,0,actual['survival_denominator'],'survival numerator')
                if template['kind']=='monsoon_storm':
                    hazard=legs[template['legs'][0]]['hazard']
                    integer(numerator,100-hazard['loss_percent_max'],100-hazard['loss_percent_min'],'storm survival')
                elif numerator!=template['survival_numerator']:
                    raise ValueError('valley survival ratio')
                if type(actual['applied']) is not bool:
                    raise ValueError('march risk receipt')
                applied.append(actual['applied'])
                if not actual['applied']:
                    if actual['before']!={} or actual['after']!={} or actual['lost']!=0:
                        raise ValueError('unapplied march loss')
                    continue
                if state.turn<row['arrival_turn'] or not row['checked_turn']:
                    raise ValueError('march loss before arrival')
                before,after=actual['before'],actual['after']
                if not isinstance(before,dict) or not isinstance(after,dict) or set(before)!=set(after) or not {str(i) for i in ids}<=before.keys() or not before.keys()<=manifest.keys():
                    raise ValueError('march loss manifest')
                for text,amount in before.items():
                    integer(amount,0,999,'before attrition')
                    if amount!=prior[text]:
                        raise ValueError('march before troop receipt')
                ordered=sorted(before,key=int)
                expected_after=allocate_survivors([before[k] for k in ordered],numerator,actual['survival_denominator'])
                if after!={key:n for key,n in zip(ordered,expected_after)}:
                    raise ValueError('march casualty receipt')
                for amount in after.values():
                    integer(amount,0,999,'after attrition')
                integer(actual['lost'],0,1000000,'march lost troops')
                if actual['lost']!=sum(before.values())-sum(after.values()):
                    raise ValueError('march lost troop receipt')
                prior.update(after)
            if applied and any(applied)!=all(applied):
                raise ValueError('partially committed march hazards')
            for ident in ids:
                if state.officers[ident].troops!=prior[str(ident)]:
                    raise ValueError('inconsistent marching troop strength')
        if state.battle and seen.intersection(u['id'] for key in ('attackers','defenders') for u in state.battle[key]):
            raise ValueError('marching unit deployed twice')
