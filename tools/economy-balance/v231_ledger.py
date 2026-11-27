"""Supplement the two Red Cliffs long runs with actual channel-level postings."""
from argparse import ArgumentParser
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from unittest.mock import patch

from common import git, sha256, to_json
from remake import command_books, granary_planning, regional_market, winter_agriculture
import v231_observe


class DetailedObservation(v231_observe.CampaignObservation):
    def __init__(self, stream, *, flows):
        super().__init__(stream,flows=flows)
        self.stamp=None
        self.context=None
        self.dispatched={}

    def observe_transport(self,state,kind,row,values):
        super().observe_transport(state,kind,row,values)
        if kind not in ('transport_departed','transport_arrived'):
            return
        if row['target_march'] is not None:
            channel='army'
        elif 'regional' in row:
            channel='regional_market'
        elif 'strategic' in row:
            channel='strategic_granary'
        else:
            channel='ordinary'
        cargo=values.get('amounts')
        if cargo is None:
            cargo=row['cargo']
        arrival=kind=='transport_arrived'
        place=row['target'] if arrival else row['source']
        first=row['journeys'][0]
        region_order=(regional_market._orders(state).get(str(row['regional']['id']),{})
                      if channel=='regional_market' else {})
        action=dict(convoy=row['id'],event=kind,channel=channel,posted=self.stamp,turn=state.turn,
            date=[state.year,state.month,state.day],source=row['source'],target=row['target'],
            city=place,owner=state.cities[place].owner,grain=cargo['grain'],
            expedition=row['target_march'],strategic_order=row.get('strategic'),
            market_order=region_order.get('id'),gold_spent=region_order.get('purchase_gold',0) if not arrival else None,
            rations=first['supply']['loaded'] if not arrival else None,escorts=list(row['officers']),
            original_eta=row.get('original_eta',first['arrival_turn']))
        if kind=='transport_departed':
            self.dispatched[row['target']]=action
        self.write('convoy_transaction',action)

    def weather(self,kind,row):
        super().weather(kind,row)
        if kind!='agricultural_preparation' or self.context is None:
            return
        game,state,plan,method=self.context
        location=row['city']
        forecast=plan.cities[location]
        agriculture=winter_agriculture.ledger(state)
        region=winter_agriculture.region_for(game,location)
        routed=self.dispatched.get(location)
        if routed and routed['turn']!=state.turn:
            routed=None
        due=row['deadline']-state.turn
        receipts=sum(amount for when,amount in forecast.receipts.items() if when<=due)
        self.write('agriculture_preparation_detail',dict(**row,
            request_id=f"{row['owner']}/{location}/{row['deadline']}/{method}",
            weather_risk=winter_agriculture.risk_score(agriculture['regions'][region]) if agriculture else None,
            projected_multiplier=winter_agriculture.planning_multiplier(state,region,(state.year,6)),
            expected_risk_gap=forecast.agricultural_risk[1] if forecast.agricultural_risk else None,
            prior_reliable_receipts=receipts,source=routed['source'] if routed else None,
            convoy=routed['convoy'] if routed else None,dispatched_grain=routed['grain'] if routed else None,
            paid_gold=routed['gold_spent'] if routed else None,
            books_spent=(command_books.cost('dispatch_transport')+
                         (command_books.cost('trade_grain') if method=='market' else 0)) if routed else None,
            escort_ids=routed['escorts'] if routed else None,
            original_eta=routed['original_eta'] if routed else None,region=region))

    def after_command(self,game,old_state,checkpoint_dir):
        super().after_command(game,old_state,checkpoint_dir)
        state=game.state
        self.stamp=[state.year,state.month,state.day,state.turn]
        self.dispatched.clear()

    def attach(self,stack):
        super().attach(stack)

        def scoped(function,method):
            def invoke(game,state,owner,plan):
                old=self.context
                self.context=game,state,plan,method
                try:
                    return function(game,state,owner,plan)
                finally:
                    self.context=old
            return invoke

        for module,name,method in ((regional_market,'procure','market'),(granary_planning,'dispatch','granary')):
            stack.enter_context(patch.object(module,name,scoped(getattr(module,name),method)))


def record(output,case):
    with patch.object(v231_observe,'CampaignObservation',DetailedObservation):
        result=v231_observe.run(output,case)
    result['detail_observer_sha256']=sha256(Path(__file__).read_bytes())
    to_json(output/result['output']/'run-v231.json',result)
    print(case['group'],result['completed_turns'],result['outcome'],flush=True)
    return result['outcome']=='complete'


if __name__=='__main__':
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    source=git('rev-parse','HEAD').decode().strip()
    experiments=[row for row in v231_observe.cases('long',source)
                 if row['scenario']=='208-10' and row['strategy']==211 and row['group'] in ('F2','F4')]
    with ProcessPoolExecutor(max_workers=2) as pool:
        tasks=[pool.submit(record,args.output,row) for row in experiments]
        if not all(job.result() for job in tasks):
            raise SystemExit(1)
