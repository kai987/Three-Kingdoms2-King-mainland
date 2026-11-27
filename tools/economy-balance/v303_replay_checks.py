"""Check portable save, backend parity and historical convoy outcomes."""
from argparse import ArgumentParser
from contextlib import ExitStack
import json
from pathlib import Path

from common import ROOT, Catalog, HeadlessCampaign, git, to_json
from remake import command_books, diplomacy, logistics, march_core, march_supply, transport_capacity
from remake import winter_weather
from remake.campaign import canonical
from remake.errors import GameError
from v3021_report import file_sha
from v303_capacity_audit import checkpoint, replay_context
from v303_experiments import options


def checksum(game):
    from hashlib import sha256
    return sha256(canonical(game.to_dict()).encode()).hexdigest()


def journey_snapshot(state,ident):
    row=next((row for row in logistics._pool(state)['convoys'] if row['id']==ident),None)
    if row is None:
        return None
    book=row['journeys'][-1]['supply']
    return dict(owner=row['owner'],source=row['source'],target=row['original_target'],
        node=march_supply.current_city(row['journeys'][-1]),status=row['status'],reason=row['reason'],
        delivered=row['delivered']['grain'],initial_grain=row['initial_cargo']['grain'],
        original_bag=row['journeys'][0]['supply']['loaded'],bag=book['remaining'],cargo=row['cargo']['grain'],
        tick=book['clock_tick'],path=row['journeys'][-1]['quote']['path'],original_ids=row['original_officers'],
        troops=sum(state.officers[i].troops for i in row['officers']),
        hunger=sum(journey['supply']['lost'] for journey in row['journeys']),
        occupants=row['officers'],reserved_until_turn=row['journeys'][-1]['arrival_turn'])


def history(path,ident,turns):
    fixture=checkpoint(path)
    outcomes=[]
    for group in ('C0','C4'):
        events=[]
        def daily(event,row):
            if row.get('convoy_id',row.get('convoy'))==ident and event in (
                    'convoy_day','convoy_terminal','emergency_refill','emergency_decision','emergency_plan'):
                events.append(dict(event=event,**row))
        def receipts(event,row):
            if row.get('id')==ident and event in ('terminal','delivery','reroute','reroute_blocked'):
                events.append(dict(event=event,**row))
        with ExitStack() as stack:
            game=replay_context(stack,fixture,group)
            stack.enter_context(winter_weather.experiment(5 if fixture['weather'] else 0,
                adjustments=winter_weather.CORRECTIONS if fixture['weather'] else 0,detailed=True,observe=daily))
            stack.enter_context(transport_capacity.observing(receipts))
            beginning=journey_snapshot(game.state,ident)
            if beginning is None:
                raise ValueError(f'Shipment {ident} missing in {path.name}')
            markers=[]
            for _ in range(turns):
                game.command('observe_turn',{},game.revision)
                now=journey_snapshot(game.state,ident)
                markers.append(dict(turn=game.state.turn,snapshot=now))
                if now is None or beginning['troops']>0 and now['troops']==0:
                    break
            outcomes.append(dict(group=group,starting=beginning,finish=markers[-1],checkpoints=markers,
                                 final_state_sha256=checksum(game),events=events))
    if outcomes[0]['starting']!=outcomes[1]['starting']:
        raise ValueError('The paired historical case changed before continuing')
    return dict(scenario=fixture['scenario'],strategy=fixture['strategy'],weather=fixture['weather'],
        seed=fixture['seed'],turn=fixture['turn'],convoy=ident,checkpoint=path.name,
        checkpoint_sha256=file_sha(path),checkpoint_source=fixture['source'],
        runtime=git('rev-parse','HEAD').decode().strip(),outcomes=outcomes)


def backend(path,turns):
    fixture=checkpoint(path)
    states={}
    for group in ('C0','C4'):
        with ExitStack() as stack:
            game=replay_context(stack,fixture,group)
            traces=[]
            for _ in range(turns+1):
                traces.append(dict(turn=game.state.turn,state_sha256=checksum(game),rng=game.to_dict()['rng']))
                if len(traces)<=turns:
                    game.command('observe_turn',{},game.revision)
            states[group]=traces
    return dict(checkpoint_sha256=file_sha(path),backend=march_core.backend_status(),states=states)


def saves(opening,compatible):
    engine=HeadlessCampaign(Catalog(ROOT/'game/data/campaigns/200-01.json'),record_journal=False)
    imports=[]
    for path in compatible:
        data=json.loads(path.read_text(encoding='utf-8'))
        engine.load_save(data,engine.revision)
        match=checksum(engine)
        for compact in (False,True):
            other=HeadlessCampaign(engine.catalog,record_journal=False)
            other.load_save(engine.export_save(compact=compact),0)
            if checksum(other)!=match or transport_capacity.enabled(other.state):
                raise ValueError('Same-version Guandu changed during the format roundtrip')
        imports.append(dict(fixture=path.name,sha256=file_sha(path),state_sha256=match,
                            normal_roundtrip=True,compact_roundtrip=True))
    comparisons=[]
    source,target='lujiang','danyang'
    for group in ('C0','C4'):
        with ExitStack() as stack:
            engine=HeadlessCampaign(Catalog(ROOT/'game/data/campaigns/208-10.json'),record_journal=False)
            engine.load_save(json.loads(opening.read_text(encoding='utf-8')),0)
            start=checksum(engine)
            if options(group) is not None:
                stack.enter_context(transport_capacity.fixed_replay(engine.state,options(group)))
            state=engine.state
            city=state.cities[source]
            ident=logistics._eligible(engine,state,city)[0]
            books=command_books.remaining(state,'wu')
            before_stock=city.grain
            payload=dict(source=source,target=target,officers=[ident],route_mode='river',
                         cargo=dict(gold=0,grain=47_000,reserves=0))
            row=logistics.dispatch(engine,state,payload,'wu')
            engine.validate(state)
            bag=row['journeys'][0]['supply']['loaded']
            remaining=command_books.remaining(state,'wu')
            if before_stock-city.grain!=payload['cargo']['grain']+bag or books-remaining!=1:
                raise ValueError('Different warehouse or command debits')
            comparisons.append(dict(group=group,starting_state_sha256=start,grain=row['cargo']['grain'],
                independent_rations=bag,cargo_capacity=row['journeys'][0].get(transport_capacity.LOAD_FIELD),
                stock_debit=before_stock-city.grain,command_debit=books-remaining,actual_path=row['journeys'][0]['quote']['path']))
    if len({row['starting_state_sha256'] for row in comparisons})!=1:
        raise ValueError('Mismatched opening state in save comparison')
    return dict(compatible_guandu=imports,controlled_opening_sha256=file_sha(opening),transport_comparisons=comparisons)


def browser_fixture(output):
    """The shipped map and rules, with a quiet test window for a complete round trip."""
    game=HeadlessCampaign(Catalog(ROOT/'game/data/campaigns/208-10.json'),record_journal=False)
    game.command('new',dict(faction='wu',seed=2026,transport_capacity_rules_version=303),0)
    state=game.state
    source,target=(state.cities[key] for key in ('lujiang','danyang'))
    source.grain,target.grain=240_000,10_000
    for owner in sorted({city.owner for city in state.cities.values()}-{'wu','neutral'}):
        treaties=diplomacy._pool(state)
        key=diplomacy._pair('wu',owner)
        treaties['relations'][key]=85
        treaties['treaties'][key]=state.turn+18
    game.command('set_logistics',dict(city=source.id,policy=dict(
        enabled=True,target_city=target.id,reserve_grain=0,target_grain=200_000,max_grain=80_000,
        target_gold=0,target_reserves=0,target_officers=0,max_reserves=0)),game.revision)
    to_json(output,game.export_save(compact=True))


def physical_controls():
    catalog=Catalog(ROOT/'game/data/campaigns/209-06.json')
    controls=[]
    for policy in (50_000,100_000):
        game=HeadlessCampaign(catalog,record_journal=False)
        game.command('new',dict(faction='wu',seed=2026,transport_capacity_rules_version=303),0)
        source,target=(game.state.cities[k] for k in ('yulin','cangwu'))
        source.grain=130_000
        game.command('set_logistics',dict(city=source.id,policy=dict(
            enabled=True,target_city=target.id,reserve_grain=0,reserve_reserves=0,max_grain=policy)),game.revision)
        state=game.state
        source,target=state.cities[source.id],state.cities[target.id]
        settings=logistics._pool(state)['cities'][source.id]['policy']
        ident=min(logistics._eligible(game,state,source),key=lambda i:(state.officers[i].troops,logistics._key(i)))
        river=logistics._safe_path(game,state,source.id,target.id,'wu','river',settings)
        back=logistics.convoy_return(game,state,source,target,settings)[1]
        load=logistics.capacity_quote(game,state,source,target,[ident],river,120_000,0,back)
        assert load['physical_capacity']==100_000 and load['mode']=='river' and not load['blocked_reason']
        baseline=checksum(game)
        payload=dict(source=source.id,target=target.id,officers=[ident],route_mode='river',
                     cargo=dict(grain=load['max_cargo']+1,gold=0,reserves=0))
        try:
            game.command('dispatch_transport',payload,game.revision)
        except GameError:
            assert checksum(game)==baseline
        else:
            raise ValueError('An over-capacity river shipment was accepted')
        payload['cargo']['grain']-=1
        row=logistics.dispatch(game,state,payload,'wu')
        game.validate(state)
        proof=row['journeys'][0][transport_capacity.LOAD_FIELD]
        assert proof['total']==row['initial_cargo']['grain']+load['rations']
        assert proof['total']<=proof['limit'] and proof['policy_grain']==policy
        controls.append(dict(scenario='209-06',seed=2026,source=source.id,target=target.id,policy=policy,
                             quote=load,departure_load=proof,excess_rejected=True))
    return dict(source=git('rev-parse','HEAD').decode().strip(),checks=controls)


def main():
    parser=ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(required=True,dest='mode')
    for name in ('history','backend'):
        phase=sub.add_parser(name)
        phase.add_argument('checkpoint',type=Path)
        phase.add_argument('output',type=Path)
        phase.add_argument('--turns',type=int,default=9 if name=='history' else 4)
        if name=='history':
            phase.add_argument('--convoy',type=int,required=True)
    save=sub.add_parser('saves')
    save.add_argument('opening',type=Path)
    save.add_argument('output',type=Path)
    save.add_argument('compatible',type=Path,nargs='+')
    fixture=sub.add_parser('browser-fixture')
    fixture.add_argument('output',type=Path)
    control=sub.add_parser('physical')
    control.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.mode=='browser-fixture':
        browser_fixture(args.output)
        return
    if args.mode=='physical':
        to_json(args.output,physical_controls())
        return
    result=(history(args.checkpoint,args.convoy,args.turns) if args.mode=='history' else
            backend(args.checkpoint,args.turns) if args.mode=='backend' else saves(args.opening,args.compatible))
    to_json(args.output,result)


if __name__=='__main__':
    main()
