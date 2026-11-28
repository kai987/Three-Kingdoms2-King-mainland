"""Map, custody, and paired controlled replay evidence for the wharf pilot."""

from argparse import ArgumentParser
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sys

from common import ROOT, catalog_paths, sha256, to_csv, to_json
from remake import grain_units, logistics, transport_capacity, transport_infrastructure as wharf
from remake import transport_coordination
from remake.campaign import digest
from v302_audit import Audit

sys.path.insert(0, str(ROOT/'tests'))
from test_remake_transport_infrastructure import advance, restore, world, D2


def maps(output):
    rows, openings = [], []
    source = json.loads((ROOT/'game/config/river-network.json').read_bytes())
    for node,(city,marker,position,*_) in wharf.SITES.items():
        if source['ports'][city]['node'] != marker or tuple(source['nodes'][marker]['position']) != position:
            raise ValueError(f'Wharf is disconnected from the authored map: {node}')
    for path in catalog_paths():
        base = world(enabled=False,scenario=path.stem,faction='observer')
        candidate = world(scenario=path.stem,faction='observer')
        initial = candidate.to_dict()
        initial['extension'].pop(wharf.FIELD)
        initial['extension'].pop(wharf.POOL)
        assert initial==base.to_dict(), f'Opening assets or RNG changed: {path}'
        for route,raw in candidate.catalog.infrastructure_routes.items():
            for origin,destination in ((raw['from'],raw['to']),(raw['to'],raw['from'])):
                present = {origin,destination} <= candidate.state.cities.keys()
                owner = candidate.state.cities[origin].owner if present else None
                span = wharf.sections(candidate,route,origin,candidate.state.month)
                with grain_units.using(candidate.state):
                    quote = wharf.quote(candidate,candidate.state,owner,route,origin,[500],90) if present else {'blocked':'inactive'}
                rows.append(dict(scenario=path.stem, catalog_sha256=base.catalog.sha256,
                   corridor=route,source=origin,destination=destination,owner=owner,
                   stage_modes=[s.mode for s in span], stage_work=[s.work for s in span],
                   available_500=not bool(quote['blocked']),reason=quote['blocked']))
        openings.append(dict(scenario=path.stem,catalog_sha256=base.catalog.sha256,
                             baseline_state_sha256=digest(base.to_dict()),rng=initial['rng'],
                             independent_wharves=len(candidate.state.extension[wharf.POOL]['nodes']),
                             reserve_storage=0,initial_staff=0))
    assert len(openings)==29
    to_csv(output/'map-directions.csv', rows)
    to_json(output/'opening-equivalence.json',openings)


def append(kind,row,stream):
    stream.write(json.dumps(dict(event=kind,**row),ensure_ascii=False,separators=(',',':'))+'\n')


class PostingRows(list):
    writerow = list.append


def line(output, group, proof, origin, dest, faction, amount, *, options):
    relay=group in ('N1','N3')
    g=world(enabled=relay,faction=faction,**options)
    route=f'{origin}:{dest}:river'
    state=g.state
    opening=g.to_dict()
    if relay:
        opening['extension'].pop(wharf.FIELD)
        opening['extension'].pop(wharf.POOL)
    evidence=output/f'{proof}-{group}.jsonl.gz'
    cargo=[amount//2,amount-amount//2]
    stream=[]
    convoy=[]
    identity=dict(proof=proof,group=group,scenario=g.catalog.data['id'],seed=2026,from_city=origin,to_city=dest,
                  physical_route=route,requested=amount,opening_sha256=digest(opening),opening_rng=opening['rng'])
    with grain_units.using(state):
        if relay:
            forecast=wharf.quote(g,state,faction,route,origin,cargo,90)
            if not forecast['blocked']:
                payload=dict(action='dispatch',id=wharf._pool(state)['next_id'],route=route,source=origin,
                             batches=cargo,deadline=90,escort=forecast['escort'])
        else:
            policy=logistics._pool(state)['cities'][origin]['policy']
            people=wharf._people(g,state,state.cities[origin],policy,g._march_ids(state),automatic=False)
            if people:
                escort=people[0]
                forecast=wharf._direct_offer(g,state,origin,dest,amount,escort)
                payload=dict(source=origin,target=dest,officers=[escort],route_mode='river',
                             cargo=dict(logistics._empty_cargo(),grain=amount))
            else:
                forecast={'blocked':'staff'}
    if not forecast or forecast.get('blocked'):
        row=dict(identity,forecast=forecast or {'blocked':'route'},status='blocked',final_rng=g.to_dict()['rng'],
                 evidence=evidence.name,original_deadline=90)
        with gzip.open(evidence,'wt',encoding='utf-8',compresslevel=4) as f:
            append('opening_refusal',row,f)
        return dict(row,evidence_sha256=sha256(evidence.read_bytes()))

    postings=PostingRows()
    audit=Audit(postings)
    with (wharf.observing(lambda kind,row:stream.append((kind,row))),
          transport_capacity.observing(lambda kind,row:convoy.append((kind,row))),audit.install()):
        with audit.command(g,'dispatch'):
            g.command(wharf.COMMAND if relay else 'dispatch_transport',payload,g.revision)
        g=restore(g,True)
        for _ in range(12):
            if (not list(wharf.jobs(g.state)) if relay else not logistics._pool(g.state)['convoys']):
                break
            with audit.command(g,'settlement'):
                g.state=deepcopy(g.state)
                advance(g)
    assert audit.errors==0
    with gzip.open(evidence,'wt',encoding='utf-8',compresslevel=4) as f:
        for kind,row in stream if relay else convoy:
            append(kind,row,f)
        for row in postings:
            if row['city'] in (origin,dest):
                append('city_posting',row,f)
    if relay:
        done=g.state.extension[wharf.POOL]['history'][-1]
        grain=done['balances']
        assert grain['input']==sum(grain[k] for k in wharf.BALANCES[1:])
        assert done['terminal']['city']==origin and done['paid']==[0,1,2]
        assert set(row['mode'] for kind,row in stream if kind=='move' and not row['returning'])=={'land','river'}
        metrics=dict(loaded_rations=grain['input']-amount,delivery=grain['delivery'],
                     waiting_and_travel_rations=grain['meals'],route_loss=grain['route_loss'],
                     weather_loss=grain['weather_loss'],returned=grain['returned'],
                     last_delivery_day=done['arrival'],books=len(done['paid']),
                     officer_days=done['terminal']['tick']-done['created'],
                     slot_days=done['terminal']['tick']-done['created'],
                     reusable_tick=(logistics._pool(g.state)['receipts'][str(done['escort'])]-1)*10,
                     actual_return_tick=done['terminal']['tick'],
                     external_ration_refill=sum(row['grain'] for kind,row in stream if kind=='ration_refill'),
                     harbour_throughput=sum(row['entry']['grain'] for kind,row in stream
                                         if kind=='grain' and row['entry']['kind']=='unload'),
                     hunger_losses=done['metrics']['hunger_losses'])
    else:
        events={kind:row for kind,row in convoy if kind in ('departure','delivery','terminal')}
        metrics=direct_metrics(events)
    ledger_sites={'logistics._begin_journey','transport_emergency._take_local'}
    target_refill=-sum(row['delta'] for row in postings if row['city']==dest and row['resource']=='grain'
                       and row['site'] in ledger_sites and row['delta']<0)
    assert target_refill==metrics['external_ration_refill'], (target_refill,metrics['external_ration_refill'])
    metrics.update(target_return_provisions=target_refill,target_transport_net=metrics['delivery']-target_refill,
                   city_resource_mismatches=audit.errors,timely_grain=(metrics['delivery'] if metrics['last_delivery_day']<90 else 0),
                   original_deadline=90, officer_reuse_days=metrics['reusable_tick'],
                   net_per_book=metrics['delivery']/metrics['books'],
                   net_per_officer_day=metrics['delivery']/metrics['officer_days'])
    return dict(identity,forecast=forecast,status='complete',final_rng=g.to_dict()['rng'],
                evidence=evidence.name,evidence_sha256=sha256(evidence.read_bytes()),**metrics)


def direct_metrics(events):
    depart,receipt,end=(events[key] for key in ('departure','delivery','terminal'))
    ledger=end['cargo_receipt']
    assert logistics.valid_grain_receipt(ledger)
    assert end['rations']['loaded']+end['rations']['received']==(
        end['rations']['consumed']+end['rations']['to_cargo']+end['rations']['remaining'])
    dispatch_day=(depart['turn']-1)*10
    return dict(loaded_rations=depart['rations'],delivery=receipt['cargo']['grain'],
                waiting_and_travel_rations=ledger['escort_base_grain']+ledger['escort_extra_grain'],
                route_loss=ledger['cargo_route_loss'],weather_loss=ledger['cargo_weather_loss'],
                returned=ledger['cargo_returned']+end['rations']['remaining'],
                last_delivery_day=(receipt['turn']-1)*10,
                books=depart['command_books'],officer_days=end['end_tick']-dispatch_day,
                slot_days=end['end_tick']-dispatch_day, reusable_tick=(end['reusable_turn']-1)*10,
                actual_return_tick=end['end_tick'],external_ration_refill=end['rations']['received'],
                harbour_throughput=0,
                hunger_losses=end.get('hunger_losses',0))


def controls(output):
    controls=[]
    for id,(origin,dest,owner,amount) in {'R01':('fuling','badong','shu',13000),
                                          'R02':('cangwu','nanhai','wu',6000)}.items():
        for group in ('N0','N1','N2','N3'):
            opts = (dict(transport_capacity_rules_version=303, transport_capacity_options=D2,
                         transport_coordination_rules_version=30412,
                         transport_coordination_options={'features':{k:True for k in transport_coordination.CONSUMPTION_FEATURES}})
                    if group in ('N2','N3') else {})
            print(id,group,flush=True)
            controls.append(line(output,group,id,origin,dest,owner,amount,options=opts))
    for i in range(0,len(controls),2):
        assert controls[i]['opening_sha256']==controls[i+1]['opening_sha256']
    to_csv(output/'controlled-lines.csv',controls)
    to_json(output/'controlled-lines.json',controls)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('map','lines','all'))
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if args.phase in ('map','all'):
        maps(args.output)
    if args.phase in ('lines','all'):
        controls(args.output)


if __name__=='__main__':
    main()
