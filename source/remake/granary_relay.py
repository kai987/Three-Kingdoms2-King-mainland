"""Experimental one-hub relay. The second leg spends only an actual receipt."""
from . import command_books, faction_economy, logistics, strategic_granary as reserve
from .errors import GameError


def entries(state):
    return reserve.pool(state)['relays'] if reserve.enabled(state,'relay') else {}


def owned(state, row):
    return all(state.cities[row[field]].owner == row['owner'] for field in ('source','hub','target'))


def credit(state, city):
    return sum(row['received'] for row in entries(state).values() if row['hub']==city and owned(state,row))


def ready(state):
    return (row for row in entries(state).values() if row['received'] and owned(state,row))


def _close(state, row, event, **outcome):
    reserve.observe(state,event,**row,**outcome)
    del entries(state)[str(row['id'])]


def accept(state, order):
    row = entries(state).get(str(order['id']))
    if row is not None and order['target']==row['hub']:
        if not order['delivered_grain']:
            _close(state,row,'relay_cancelled',reason='empty_receipt')
            return
        row.update(received=order['delivered_grain'], received_turn=state.turn)
        reserve.observe(state,'relay_hub_receipt',**row)


def terminal(state, order):
    row = entries(state).get(str(order['id']))
    if row is not None and not row['received']:
        _close(state,row,'relay_cancelled',reason='first_leg_failed')


def synchronize(state):
    data = reserve.pool(state)
    retained = set(data['orders']) | {str(order['id']) for order in data['history']}
    for row in list(entries(state).values()):
        if str(row['id']) not in retained:
            _close(state,row,'relay_cancelled',reason='archived')
        elif not owned(state,row):
            _close(state,row,'relay_cancelled',reason='ownership')
        elif state.turn >= row['deadline']:
            _close(state,row,'relay_cancelled',reason='expired')
        elif row['received']:
            city = state.cities[row['hub']]
            # This amount is a custody earmark within the hub's actual stock.
            other = reserve.committed(state,city.id)
            held = reserve.staging_supply.held(state,city.id)
            room = max(0,city.grain-other-held-reserve.reserve_grain(state,city))
            if room < row['received']:
                row['received'] = room
                reserve.observe(state,'relay_credit_reduced',**row)
            if not row['received']:
                _close(state,row,'relay_cancelled',reason='hub_priority_use')


def validate(state):
    relays = reserve.pool(state)['relays']
    if not isinstance(relays,dict) or (relays and not reserve.enabled(state,'relay')):
        raise ValueError('Granary relay switch')
    ledger = reserve.pool(state)
    history = {row['id']:row for row in ledger['history']}
    hubs, targets = set(), set()
    for key, row in relays.items():
        if (not isinstance(row,dict) or set(row)!={'id','owner','source','hub','target','deadline','received','received_turn'}
                or type(row['id']) is not int or key!=str(row['id'])
                or len({row['source'],row['hub'],row['target']})!=3
                or any(row[field] not in state.cities for field in ('source','hub','target'))
                or not owned(state,row) or row['hub'] in hubs or row['target'] in targets
                or type(row['deadline']) is not int or row['deadline']<=state.turn
                or type(row['received']) is not int or not 0<=row['received']<=logistics.LIMIT):
            raise ValueError('Granary relay entry')
        first = ledger['orders'].get(key) or history.get(row['id'])
        if (not first or first['priority']!='relay' or first['owner']!=row['owner']
                or (first['source'],first['target'])!=(row['source'],row['hub'])
                or row['received_turn']!=first['delivered_turn']
                or (row['received_turn'] is None) != (row['received']==0)
                or row['received']>first['delivered_grain']):
            raise ValueError('Granary relay first leg')
        city = state.cities[row['hub']]
        if row['received'] > city.grain-reserve.reserve_grain(state,city)-reserve.committed(state,city.id)-reserve.staging_supply.held(state,city.id):
            raise ValueError('Granary relay stock')
        hubs.add(row['hub'])
        targets.add(row['target'])


def forward(game,state,owner,plan):
    """Consume real hub stock only after revalidating the new leg."""
    from . import granary_planning
    sent = []
    for row in list(ready(state)):
        if row['owner'] != owner or not command_books.can_spend(state,owner,'dispatch_transport'):
            continue
        hub, target = row['hub'], row['target']
        forecast = plan.cities[target]
        needed = sum(gap for _,gap in forecast.gaps)
        if not needed:
            _close(state,row,'relay_cancelled',reason='need_covered')
            continue
        # The general plan already subtracts this earmark at the hub. Permit
        # only this same receipt as a source for the next candidate.
        network = granary_planning.Network(game,state,owner,plan,automatic=True)
        choices = network.collect([target],[hub],stock_credit={hub:row['received']}).get(target,())
        quotes = []
        for opt in choices:
            opt = dict(opt,limit=min(opt['limit'],row['received']-opt['rations']))
            quote = network.shipment(opt,needed,row['deadline'])
            if quote and quote['timely'] and quote['net']>=reserve.RULES['minimum_load']:
                quotes.append(quote)
        if not quotes:
            continue
        quote = min(quotes,key=granary_planning._rank)
        del entries(state)[str(row['id'])]
        order = reserve.reserve_order(state,owner,quote,'relay')
        try:
            reserve.launch(game,state,order,quote)
        except GameError as error:
            reserve._finish(state,order,'cancelled',str(error))
            entries(state)[str(row['id'])] = row
            continue
        reserve.observe(state,'relay_second_leg',**row,second_order=order['id'],
                        loaded=quote['load'],rations=quote['rations'])
        sent.append(order)
    return sent


def dispatch(game,state,owner,plan,network,unfilled,used):
    """Require both separately quoted and funded legs, capped to one hub."""
    from . import granary_planning
    if not reserve.enabled(state,'relay') or not unfilled or not command_books.can_spend(state,owner,'dispatch_transport'):
        return []
    registered = entries(state).values()
    existing = {row['target'] for row in registered}
    occupied = {row['hub'] for row in registered} | used
    available_hubs = [key for key,spec in network.profiles.items() if spec['roles']['hub'] and key not in occupied]
    if not available_hubs:
        return []
    # Highest-connectivity transshipment nodes are checked first. Each hub
    # must still provide an eligible second escort and truthful route.
    hubs = sorted(available_hubs,key=lambda key:(-network.profiles[key]['contacts'],key))[:reserve.RULES['relay_hubs']]
    targets = [key for key in unfilled if key not in existing and key not in hubs][:reserve.RULES['relay_targets']]
    if not targets:
        return []
    have = network.collect(hubs)
    potential = {key:max((quote['limit'] for quote in have.get(key,())),default=0) for key in hubs}
    downstream = network.collect(targets,hubs,stock_credit=potential)
    sent = []
    for key in targets:
        forecast = plan.cities[key]
        deadline = state.turn+forecast.zero_in
        bids = []
        for onward in downstream.get(key,()):
            hub = onward['source']
            if hub in occupied:
                continue
            for initial in have.get(hub,()):
                source = initial['source']
                if source in used or source==key or len(set(initial['path']+onward['path'][1:])) != len(initial['path'])+len(onward['path'])-1:
                    continue
                first = network.shipment(initial, sum(gap for _,gap in forecast.gaps)+onward['rations'], deadline)
                if first is None:
                    continue
                final = network.shipment(dict(onward,limit=min(onward['limit'],first['net']-onward['rations'])),
                                         sum(gap for _,gap in forecast.gaps),deadline)
                if (final is None or first['arrival_turn']+final['eta']>=deadline
                        or final['net']<reserve.RULES['minimum_load']):
                    continue
                rank = (first['risk']+final['risk'],first['rations']+final['rations'],-final['net'],
                        first['days']+final['days'],source,hub)
                bids.append((rank,first,final))
        if not bids or not command_books.can_spend(state,owner,'dispatch_transport'):
            continue
        _,first,final = min(bids,key=lambda bid:bid[0])
        order = reserve.reserve_order(state,owner,first,'relay')
        row = dict(id=order['id'],owner=owner,source=first['source'],hub=first['target'],
                   target=key,deadline=deadline,received=0,received_turn=None)
        entries(state)[str(order['id'])] = row
        try:
            reserve.launch(game,state,order,first)
        except GameError as error:
            reserve._finish(state,order,'cancelled',str(error))
            _close(state,row,'relay_cancelled',reason='first_leg_invalid')
            continue
        used.add(row['source'])
        occupied.add(row['hub'])
        reserve.observe(state,'relay_planned',**row,estimated_net=final['net'],
                        expected_turn=first['arrival_turn']+final['eta'])
        sent.append(order)
    return sent
