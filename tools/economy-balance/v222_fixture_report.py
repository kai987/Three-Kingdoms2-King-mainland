"""Record an actual ordinary-convoy shipment and handoff in the controlled fixture."""
from argparse import ArgumentParser
from pathlib import Path
import sys

from common import ROOT, to_json

sys.path.insert(0,str(ROOT/'tests'))
from remake import command_books, convoy_relief, grain_units, logistics, march_supply, transport_emergency, winter_weather
from test_remake_transport_emergency import TransportEmergencyTests


def relief_case():
    test=TransportEmergencyTests()
    game=test.game()
    tracked=[]
    def observe(kind,record):
        if kind.startswith('emergency_') or kind in ('convoy_relief_request','convoy_relief_delivery','convoy_terminal'):
            tracked.append(dict(event=kind,**record))
    with grain_units.using(game.state), winter_weather.experiment(0,observe=observe,detailed=True):
        target=test.convoy(game,bag=148)
        state=test.blocked_node(game,target)
        assert not transport_emergency.withdraw(game,state,target,'nanjun','resource_full')
        donor=state.cities['jiangxia']
        planner=convoy_relief.Planner(game,state,'shu')
        choice,blocked=planner.quote(donor,target)
        assert choice,blocked
        before=dict(stock=donor.grain, books=command_books.remaining(state,'shu'),target_bag=transport_emergency.book(target)['remaining'])
        sender=logistics.dispatch(game,state,dict(source=donor.id,target='nanjun',target_convoy=target['id'],
            officers=choice['officers'],route_mode=choice['mode'],
            cargo=dict(gold=0,grain=choice['grain'],reserves=0)),'shu')
        debit=dict(grain=before['stock']-donor.grain,books=before['books']-command_books.remaining(state,'shu'),
            cargo=sender['cargo']['grain'],sender_rations=transport_emergency.book(sender)['remaining'],
            target_bag=transport_emergency.book(target)['remaining'])
        assert debit['books']==1 and debit['cargo']+debit['sender_rations']==debit['grain']
        assert before['target_bag']==debit['target_bag']
        for tick in range(11,14):
            for row in list(logistics._pool(state)['convoys']):
                logistics.advance_supply(game,state,row,absolute_tick=tick)
            logistics.rendezvous(game,state,tick=tick)
        receipt,=[item for item in sender['cargo_ledger'] if item['kind']=='convoy_supply']
        received,=[item for item in transport_emergency.book(target)['refills'] if item['kind']=='convoy']
        assert receipt['before']['grain']-receipt['after']['grain']==received['grain']==sender['delivered']['grain']
        assert receipt['day']==received['tick']
        assert march_supply.current_city(sender['journeys'][-1])==march_supply.current_city(target['journeys'][-1])=='nanjun'
        logistics.rendezvous(game,state,tick=13)
        assert len([item for item in sender['cargo_ledger'] if item['kind']=='convoy_supply'])==1
        game._complete_turn(state)
        logistics.process_arrivals(game,state)
        from remake import treasures
        treasures.synchronize(game,state)
        game.validate(state)
        exit_status=dict(phase=target['status'],city=target['target'],
            remaining_rations=transport_emergency.book(target)['remaining'],
            route_rations=target['emergency']['route_budget'])
        assert exit_status['phase']=='returning' and exit_status['remaining_rations']>=exit_status['route_rations']
        game._complete_turn(state)
        logistics.process_arrivals(game,state)
        treasures.synchronize(game,state)
        game.validate(state)
        received_terminal=[e for e in tracked if e['event']=='convoy_terminal']
        assert {e['convoy_id'] for e in received_terminal}=={target['id'],sender['id']}
        assert all(e['actual_position']=='jiangxia' for e in received_terminal)
        return dict(before=before,dispatch_debit=debit,actual_debit=receipt,actual_receipt=received,
                    recipient_exit=exit_status,sender_return_budget=choice['relief']['returning'],events=tracked,
                    verified_state=game.export_save(compact=True)['checksum'])


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    to_json(args.output,relief_case())
