"""Execute an affordable automatic purchase, real round trip and final sale."""
from argparse import ArgumentParser
from pathlib import Path
import sys

from common import ROOT, to_json
from remake import facilities, grain_market, market_pricing as pricing
from remake import regional_market as regional

sys.path.insert(0,str(ROOT/'tests'))
from test_remake_regional_market import OWNER, SOURCE, TARGET, advance, controlled, fill_market, item


def execute(*, drop_price=False):
    game=controlled(3)
    state=game.state
    state.player,state.phase='observer','ai'
    events=[]
    for city in state.cities.values():
        if city.owner==OWNER:
            city.gold,city.grain=40_000,500_000
    fill_market(state,SOURCE,280_000,100_000)
    fill_market(state,TARGET,0,100_000)
    facilities._pool(state)['cities'][SOURCE]['town']=3
    facilities._pool(state)['cities'][TARGET]['town']=1
    pricing.pool(state)['turn']=0
    pricing.refresh(state)
    with pricing.observing(lambda kind,row:events.append(dict(kind=kind,record=row))):
        regional.automatic_trade(game,state,OWNER,[])
        if drop_price:
            # Establish a real market sale at the same city before the next
            # strategic turn. The next snapshot must use the updated stock.
            grain_market.transfer(state,TARGET,'sell',270_000)
        for _ in range(2):
            advance(game)
            state.phase='ai'
            regional.automatic_trade(game,state,OWNER,[])
        state.phase='city'
        game.validate(state)
    order=item(game)
    if order['status']!=('awaiting_sale' if drop_price else 'sold'):
        raise ValueError(order)
    return dict(controlled=True,expected_scenario=state.year,date=[state.year,state.month,state.day],
        owner=OWNER,purchase=order['purchase_gold'],source=SOURCE,target=TARGET,
        source_remaining_market_quota=regional.quota_left(state,SOURCE,'buy'),
        destination_remaining_market_quota=regional.quota_left(state,TARGET,'sell'),
        order=order,events=events)


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    options=parser.parse_args()
    to_json(options.output,dict(profitable=execute(),repriced=execute(drop_price=True)))


if __name__=='__main__':
    main()
